import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from shared.settings_service import get_setting
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
)
from shared.mollie_client import create_mollie_payment, get_mollie_payment
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])

# Public router — no auth dependency (mounted separately in main.py)
public_router = APIRouter(prefix="/v1/billing", tags=["billing"])


@public_router.get("/packages")
def get_packages():
    """List available token packages (public endpoint, no auth)."""
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


@router.post("/purchase")
def purchase_tokens(body: PurchaseIn, user: dict = Depends(get_current_user)):
    pkg = get_token_package(body.package_id)
    if not pkg or not pkg.get("active"):
        raise HTTPException(status_code=404, detail="Package not found")

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
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e}")

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

    # Fetch real status from Mollie
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

    return {"ok": True}
