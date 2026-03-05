import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from shared.config import settings
from shared.db_sqlalchemy import (
    list_token_packages,
    get_token_package,
    create_payment,
    credit_tokens,
    list_token_transactions,
    get_user_by_id,
)
from shared.mollie_client import create_mollie_payment
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/balance")
def get_balance(user: dict = Depends(get_current_user)):
    u = get_user_by_id(user["user_id"])
    balance = u["token_balance"] if u else 0
    return {"token_balance": balance}


@router.get("/packages")
def get_packages():
    """List available token packages (public endpoint)."""
    return {"packages": list_token_packages(active_only=True)}


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
    if not settings.MOLLIE_API_KEY:
        raise HTTPException(status_code=503, detail="Payment provider not configured")

    webhook_url = f"{settings.PUBLIC_BASE_URL}/v1/mollie/webhook"
    mollie = create_mollie_payment(
        amount_cents=pkg["price_cents"],
        currency=pkg["currency"],
        description=f"Opal {pkg['name']} — {pkg['tokens']} tokens",
        redirect_url=body.redirect_url,
        webhook_url=webhook_url,
        metadata={"payment_id": payment_id, "user_id": user["user_id"]},
    )

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


@router.get("/transactions")
def get_transactions(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    txs = list_token_transactions(user["user_id"], limit=limit, offset=offset)
    return {"transactions": txs, "limit": limit, "offset": offset}
