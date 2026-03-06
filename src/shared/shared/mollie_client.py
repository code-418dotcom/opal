"""Thin Mollie payments client using httpx."""
import logging
from typing import Optional
import httpx

from shared.settings_service import get_setting

LOG = logging.getLogger(__name__)

MOLLIE_BASE = "https://api.mollie.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_setting('MOLLIE_API_KEY')}",
        "Content-Type": "application/json",
    }


def create_mollie_payment(
    amount_cents: int,
    currency: str,
    description: str,
    redirect_url: str,
    webhook_url: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a Mollie payment. Returns {"id": "tr_...", "checkout_url": "https://..."}."""
    amount_str = f"{amount_cents / 100:.2f}"
    body: dict = {
        "amount": {"currency": currency, "value": amount_str},
        "description": description,
        "redirectUrl": redirect_url,
    }
    if webhook_url:
        body["webhookUrl"] = webhook_url
    if metadata:
        body["metadata"] = metadata

    resp = httpx.post(f"{MOLLIE_BASE}/payments", json=body, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    LOG.info("Created Mollie payment %s", data["id"])
    return {
        "id": data["id"],
        "checkout_url": data["_links"]["checkout"]["href"],
    }


def get_mollie_payment(payment_id: str) -> dict:
    """Fetch payment status from Mollie. Returns {"id", "status", "metadata"}."""
    resp = httpx.get(f"{MOLLIE_BASE}/payments/{payment_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return {
        "id": data["id"],
        "status": data["status"],
        "metadata": data.get("metadata"),
    }
