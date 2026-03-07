import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from shared.config import settings as app_settings
from shared.settings_service import get_setting
from web_api.rate_limit import check_ip_rate_limit
from shared.db_sqlalchemy import (
    list_token_packages,
    get_token_package,
    create_payment,
    get_payment_by_id,
    get_payment_by_mollie_id,
    update_payment_status,
    credit_tokens,
    list_token_transactions,
    get_user_by_id,
    list_subscription_plans,
    get_subscription_plan,
    create_user_subscription,
    get_user_subscription,
    update_subscription,
    get_user_mollie_customer_id,
    set_user_mollie_customer_id,
)
from shared.mollie_client import (
    create_mollie_payment, get_mollie_payment,
    create_mollie_customer, create_first_payment,
    create_mollie_subscription, cancel_mollie_subscription,
)
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])

# Public router — no auth dependency (mounted separately in main.py)
public_router = APIRouter(prefix="/v1/billing", tags=["billing"])


@public_router.get("/packages")
def get_packages(request: Request):
    """List available token packages (public endpoint, no auth)."""
    check_ip_rate_limit(request)
    return {"packages": list_token_packages(active_only=True)}


@router.get("/balance")
def get_balance(user: dict = Depends(get_current_user)):
    u = get_user_by_id(user["user_id"])
    balance = u["token_balance"] if u else 0
    is_admin = u.get("is_admin", False) if u else user.get("is_admin", False)
    return {"token_balance": balance, "is_admin": is_admin}


class PurchaseIn(BaseModel):
    package_id: str
    redirect_url: str  # where to redirect after Mollie checkout


def _validate_redirect_url(url: str) -> bool:
    """Validate redirect URL against CORS allowed origins to prevent open redirects."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = [o.strip() for o in app_settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
    return any(origin == a for a in allowed)


@router.post("/purchase")
def purchase_tokens(body: PurchaseIn, user: dict = Depends(get_current_user)):
    pkg = get_token_package(body.package_id)
    if not pkg or not pkg.get("active"):
        raise HTTPException(status_code=404, detail="Package not found")

    # Validate redirect URL to prevent open redirect attacks
    if not _validate_redirect_url(body.redirect_url):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")

    payment_id = new_id("pay")

    # Create Mollie payment
    if not get_setting('MOLLIE_API_KEY'):
        raise HTTPException(status_code=503, detail="Payment provider not configured")

    public_base = get_setting('PUBLIC_BASE_URL')
    webhook_url = f"{public_base}/v1/billing/mollie/webhook" if public_base else None

    # Append payment_id to redirect URL so frontend can poll status on return
    separator = "&" if "?" in body.redirect_url else "?"
    redirect_with_id = f"{body.redirect_url}{separator}payment_id={payment_id}"

    try:
        mollie = create_mollie_payment(
            amount_cents=pkg["price_cents"],
            currency=pkg["currency"],
            description=f"Opal {pkg['name']} — {pkg['tokens']} tokens",
            redirect_url=redirect_with_id,
            webhook_url=webhook_url,
            metadata={"payment_id": payment_id, "user_id": user["user_id"]},
        )
    except Exception as e:
        LOG.error("Mollie payment creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error")

    # Store payment record
    create_payment({
        "id": payment_id,
        "user_id": user["user_id"],
        "package_id": body.package_id,
        "mollie_payment_id": mollie["id"],
        "amount_cents": pkg["price_cents"],
        "currency": pkg["currency"],
    })

    return {"payment_url": mollie["checkout_url"], "payment_id": payment_id}


@router.get("/usage")
def get_usage(user: dict = Depends(get_current_user)):
    """Usage summary: token balance, total spent, recent transactions."""
    u = get_user_by_id(user["user_id"])
    txs = list_token_transactions(user["user_id"], limit=200)
    total_spent = sum(-tx["amount"] for tx in txs if tx["amount"] < 0)
    total_purchased = sum(tx["amount"] for tx in txs if tx["type"] == "purchase")
    total_jobs = sum(1 for tx in txs if tx["type"] == "usage")
    return {
        "token_balance": u["token_balance"] if u else 0,
        "total_tokens_spent": total_spent,
        "total_tokens_purchased": total_purchased,
        "total_jobs": total_jobs,
    }


@router.get("/transactions")
def get_transactions(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    txs = list_token_transactions(user["user_id"], limit=limit, offset=offset)
    return {"transactions": txs, "limit": limit, "offset": offset}


@router.get("/payments/{payment_id}")
def get_payment_status(payment_id: str, user: dict = Depends(get_current_user)):
    """Check payment status. Only the owning user can view their payment."""
    payment = get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your payment")
    return payment


# ── Mollie Webhook ──────────────────────────────────────────────────
# Public endpoint — Mollie sends POST with payment ID when status changes.
# No auth (Mollie can't authenticate), but we always verify by fetching
# the real status from Mollie API.

@public_router.post("/mollie/webhook")
async def mollie_webhook(request: Request):
    """
    Mollie calls this with { "id": "tr_..." } when payment status changes.
    We always fetch real status from Mollie API (never trust webhook body).
    Idempotent: only credits tokens once per payment.
    """
    check_ip_rate_limit(request, limit=60)
    # Mollie sends form-encoded or JSON
    content_type = request.headers.get("content-type", "")
    mollie_id = None
    if "form" in content_type:
        form = await request.form()
        mollie_id = form.get("id")
    if not mollie_id:
        try:
            body = await request.json()
            mollie_id = body.get("id")
        except Exception:
            pass
    if not mollie_id:
        raise HTTPException(status_code=400, detail="Missing payment id")

    # Validate mollie_id format to prevent abuse (Mollie IDs are tr_ + alphanumeric)
    if not mollie_id.startswith("tr_") or len(mollie_id) > 40:
        LOG.warning("Webhook called with invalid Mollie ID format: %s", mollie_id[:50])
        return {"ok": True}

    # Security: we ALWAYS fetch real status from Mollie API (never trust webhook body).
    # This is Mollie's recommended verification approach — the webhook only tells us
    # which payment to check, not the actual status.
    try:
        mollie_payment = get_mollie_payment(mollie_id)
    except Exception as e:
        LOG.error("Failed to fetch Mollie payment %s: %s", mollie_id, e)
        raise HTTPException(status_code=502, detail="Could not verify payment with Mollie")

    mollie_status = mollie_payment["status"]
    LOG.info("Mollie webhook: %s status=%s", mollie_id, mollie_status)

    # Look up our payment record
    payment = get_payment_by_mollie_id(mollie_id)
    if not payment:
        LOG.warning("No payment record for Mollie ID %s", mollie_id)
        return {"ok": True}  # return 200 to avoid retries

    # Idempotent: if already paid, skip
    if payment["status"] == "paid":
        return {"ok": True, "note": "already processed"}

    # Map Mollie status to our status
    status_map = {
        "paid": "paid",
        "failed": "failed",
        "expired": "expired",
        "canceled": "expired",
    }
    new_status = status_map.get(mollie_status)
    if not new_status:
        return {"ok": True, "note": f"ignored status {mollie_status}"}

    update_payment_status(payment["id"], new_status)

    # Credit tokens if paid
    if new_status == "paid":
        pkg = get_token_package(payment["package_id"])
        if pkg:
            new_balance = credit_tokens(
                user_id=payment["user_id"],
                amount=pkg["tokens"],
                tx_type="purchase",
                description=f"Purchased {pkg['name']} package",
                reference_id=mollie_id,
            )
            LOG.info("Credited %d tokens to user %s (balance: %d)",
                     pkg["tokens"], payment["user_id"], new_balance)

        # Check if this was a first payment for a subscription
        payment_metadata = mollie_payment.get("metadata") or {}
        sub_id = payment_metadata.get("subscription_id")
        if sub_id:
            _activate_subscription(sub_id, payment_metadata)

    return {"ok": True}


def _activate_subscription(sub_id: str, metadata: dict) -> None:
    """After first payment succeeds, create the actual Mollie subscription."""
    from shared.db_sqlalchemy import get_user_subscription as _get_sub
    sub = _get_sub(metadata.get("user_id", ""))
    if not sub or sub["id"] != sub_id or sub["status"] == "active":
        return

    plan = get_subscription_plan(sub["plan_id"])
    if not plan:
        return

    public_base = get_setting('PUBLIC_BASE_URL')
    webhook_url = f"{public_base}/v1/billing/mollie/webhook" if public_base else None

    try:
        mollie_sub = create_mollie_subscription(
            customer_id=sub["mollie_customer_id"],
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            interval=plan["interval"],
            description=f"Opal {plan['name']} Monthly",
            webhook_url=webhook_url,
            metadata={"subscription_id": sub_id, "user_id": metadata.get("user_id")},
        )
        now = datetime.utcnow()
        update_subscription(sub_id, {
            "mollie_subscription_id": mollie_sub["id"],
            "status": "active",
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
        })
        LOG.info("Subscription %s activated with Mollie sub %s", sub_id, mollie_sub["id"])
    except Exception as e:
        LOG.error("Failed to create Mollie subscription for %s: %s", sub_id, e)


# ── Subscription Endpoints ─────────────────────────────────────────

@public_router.get("/subscription-plans")
def get_subscription_plans(request: Request):
    """List available subscription plans (public)."""
    check_ip_rate_limit(request)
    return {"plans": list_subscription_plans(active_only=True)}


@router.get("/subscription")
def get_my_subscription(user: dict = Depends(get_current_user)):
    """Get current user's active subscription."""
    sub = get_user_subscription(user["user_id"])
    if not sub:
        return {"subscription": None}

    # Include plan details
    plan = get_subscription_plan(sub["plan_id"])
    return {"subscription": {**sub, "plan": plan}}


class SubscribeIn(BaseModel):
    plan_id: str
    redirect_url: str


@router.post("/subscribe")
def subscribe(body: SubscribeIn, user: dict = Depends(get_current_user)):
    """Start a subscription. Creates a Mollie first payment to establish mandate."""
    plan = get_subscription_plan(body.plan_id)
    if not plan or not plan.get("active"):
        raise HTTPException(status_code=404, detail="Plan not found")

    if not _validate_redirect_url(body.redirect_url):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")

    if not get_setting('MOLLIE_API_KEY'):
        raise HTTPException(status_code=503, detail="Payment provider not configured")

    # Check for existing active subscription
    existing = get_user_subscription(user["user_id"])
    if existing and existing["status"] == "active":
        raise HTTPException(status_code=400, detail="Already have an active subscription. Cancel first.")

    # Get or create Mollie customer
    customer_id = get_user_mollie_customer_id(user["user_id"])
    if not customer_id:
        try:
            customer = create_mollie_customer(
                name=user.get("email", ""),
                email=user.get("email", ""),
                metadata={"user_id": user["user_id"]},
            )
            customer_id = customer["id"]
            set_user_mollie_customer_id(user["user_id"], customer_id)
        except Exception as e:
            LOG.error("Failed to create Mollie customer: %s", e)
            raise HTTPException(status_code=502, detail="Payment provider error")

    # Create first payment (establishes mandate)
    sub_id = new_id("sub")
    public_base = get_setting('PUBLIC_BASE_URL')
    webhook_url = f"{public_base}/v1/billing/mollie/webhook" if public_base else None

    separator = "&" if "?" in body.redirect_url else "?"
    redirect_with_id = f"{body.redirect_url}{separator}subscription_id={sub_id}"

    try:
        payment = create_first_payment(
            customer_id=customer_id,
            amount_cents=plan["price_cents"],
            currency=plan["currency"],
            description=f"Opal {plan['name']} Subscription — First Payment",
            redirect_url=redirect_with_id,
            webhook_url=webhook_url,
            metadata={"subscription_id": sub_id, "user_id": user["user_id"], "plan_id": plan["id"]},
        )
    except Exception as e:
        LOG.error("Mollie first payment failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error")

    # Store payment record for webhook handling
    create_payment({
        "id": new_id("pay"),
        "user_id": user["user_id"],
        "package_id": plan["id"],
        "mollie_payment_id": payment["id"],
        "amount_cents": plan["price_cents"],
        "currency": plan["currency"],
    })

    # Create pending subscription
    create_user_subscription({
        "id": sub_id,
        "user_id": user["user_id"],
        "plan_id": plan["id"],
        "mollie_customer_id": customer_id,
        "status": "pending",
    })

    return {"payment_url": payment["checkout_url"], "subscription_id": sub_id}


@router.post("/subscription/cancel")
def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel the current subscription."""
    sub = get_user_subscription(user["user_id"])
    if not sub or sub["status"] != "active":
        raise HTTPException(status_code=404, detail="No active subscription")

    if sub.get("mollie_customer_id") and sub.get("mollie_subscription_id"):
        try:
            cancel_mollie_subscription(sub["mollie_customer_id"], sub["mollie_subscription_id"])
        except Exception as e:
            LOG.error("Mollie cancel failed: %s", e)
            raise HTTPException(status_code=502, detail="Failed to cancel with payment provider")

    update_subscription(sub["id"], {"status": "canceled"})
    LOG.info("Subscription %s canceled for user %s", sub["id"], user["user_id"])
    return {"ok": True, "subscription_id": sub["id"]}
