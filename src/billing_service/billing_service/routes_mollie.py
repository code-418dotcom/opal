import logging
from fastapi import APIRouter, Request, HTTPException

from shared.db_sqlalchemy import (
    get_payment_by_mollie_id,
    update_payment_status,
    credit_tokens,
    get_token_package,
)
from shared.mollie_client import get_mollie_payment

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mollie", tags=["mollie"])


@router.post("/webhook")
async def mollie_webhook(request: Request):
    """
    Mollie calls this with { "id": "tr_..." } when payment status changes.
    We always fetch real status from Mollie API (never trust webhook body).
    Idempotent: only credits tokens once per payment.
    """
    form = await request.form()
    mollie_id = form.get("id")
    if not mollie_id:
        body = await request.json()
        mollie_id = body.get("id")
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
            LOG.info("Credited %d tokens to user %s (balance: %d)", pkg["tokens"], payment["user_id"], new_balance)

    return {"ok": True}
