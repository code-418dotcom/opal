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


# ── Customers ──────────────────────────────────────────────────────

def create_mollie_customer(name: str, email: str, metadata: Optional[dict] = None) -> dict:
    """Create a Mollie customer for recurring payments."""
    body: dict = {"name": name, "email": email}
    if metadata:
        body["metadata"] = metadata
    resp = httpx.post(f"{MOLLIE_BASE}/customers", json=body, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    LOG.info("Created Mollie customer %s", data["id"])
    return {"id": data["id"]}


def get_mollie_customer(customer_id: str) -> dict:
    """Get Mollie customer details."""
    resp = httpx.get(f"{MOLLIE_BASE}/customers/{customer_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── First Payment (Mandate) ──────────────────────────────────────

def create_first_payment(
    customer_id: str,
    amount_cents: int,
    currency: str,
    description: str,
    redirect_url: str,
    webhook_url: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a first payment to establish a mandate for recurring billing.

    Uses sequenceType="first" so Mollie saves the payment method for future charges.
    """
    amount_str = f"{amount_cents / 100:.2f}"
    body: dict = {
        "amount": {"currency": currency, "value": amount_str},
        "description": description,
        "redirectUrl": redirect_url,
        "sequenceType": "first",
        "customerId": customer_id,
    }
    if webhook_url:
        body["webhookUrl"] = webhook_url
    if metadata:
        body["metadata"] = metadata

    resp = httpx.post(f"{MOLLIE_BASE}/payments", json=body, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    LOG.info("Created first payment %s for customer %s", data["id"], customer_id)
    return {
        "id": data["id"],
        "checkout_url": data["_links"]["checkout"]["href"],
    }


# ── Subscriptions ────────────────────────────────────────────────

def create_mollie_subscription(
    customer_id: str,
    amount_cents: int,
    currency: str,
    interval: str,
    description: str,
    webhook_url: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a recurring subscription for a customer."""
    amount_str = f"{amount_cents / 100:.2f}"
    body: dict = {
        "amount": {"currency": currency, "value": amount_str},
        "interval": interval,
        "description": description,
    }
    if webhook_url:
        body["webhookUrl"] = webhook_url
    if metadata:
        body["metadata"] = metadata

    resp = httpx.post(
        f"{MOLLIE_BASE}/customers/{customer_id}/subscriptions",
        json=body, headers=_headers(), timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    LOG.info("Created subscription %s for customer %s", data["id"], customer_id)
    return {
        "id": data["id"],
        "status": data["status"],
        "next_payment_date": data.get("nextPaymentDate"),
    }


def cancel_mollie_subscription(customer_id: str, subscription_id: str) -> dict:
    """Cancel a subscription."""
    resp = httpx.delete(
        f"{MOLLIE_BASE}/customers/{customer_id}/subscriptions/{subscription_id}",
        headers=_headers(), timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    LOG.info("Canceled subscription %s", subscription_id)
    return {"id": data["id"], "status": data["status"]}


def get_mollie_subscription(customer_id: str, subscription_id: str) -> dict:
    """Get subscription details."""
    resp = httpx.get(
        f"{MOLLIE_BASE}/customers/{customer_id}/subscriptions/{subscription_id}",
        headers=_headers(), timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
