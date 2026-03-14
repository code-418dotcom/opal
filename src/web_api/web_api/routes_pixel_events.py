"""Pixel event ingestion: receive batched storefront events from the Shopify web pixel.

Auth: X-Pixel-Key header (not user JWT — pixel runs in storefront sandbox).
Events are attributed to the correct variant via timestamp lookup in ab_test_variant_log.
"""
import logging
import math
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from shared.db_sqlalchemy import (
    get_integration_by_pixel_key,
    get_integration,
    ensure_pixel_key,
    find_running_test,
    get_active_variant_at,
    increment_ab_test_metric,
    get_ab_test_aggregated_metrics,
    update_ab_test,
    get_monthly_view_count,
    get_integration_event_limit,
    update_integration_event_limit,
)
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ab-tests", tags=["ab-tests-pixel"])


# ── Schemas ───────────────────────────────────────────────────────────

class PixelEvent(BaseModel):
    event_type: Literal["view", "add_to_cart", "conversion"]
    product_id: str
    variant_id: Optional[str] = None
    timestamp: str  # ISO 8601
    revenue_cents: Optional[int] = None  # only for conversions


class PixelEventsIn(BaseModel):
    shop_domain: str
    events: list[PixelEvent] = Field(..., max_length=50)


# ── Endpoint ──────────────────────────────────────────────────────────

@router.post("/pixel-events", status_code=202)
async def receive_pixel_events(
    body: PixelEventsIn,
    x_pixel_key: str = Header(..., alias="X-Pixel-Key"),
):
    """Receive batched events from the Shopify web pixel.

    Auth: X-Pixel-Key header validated against integration's pixel_key.
    No user JWT — this is called from the storefront sandbox.

    Returns 202 Accepted (fire-and-forget from pixel's perspective).
    """
    # 1. Validate pixel key → find integration
    integration = get_integration_by_pixel_key(x_pixel_key)
    if not integration:
        raise HTTPException(status_code=401, detail="Invalid pixel key")

    integration_id = integration["id"]
    processed = 0
    skipped = 0

    # 2. Check monthly view limit
    event_limit = get_integration_event_limit(integration_id)
    if event_limit is not None:
        monthly_views = get_monthly_view_count(integration_id)
        if monthly_views >= event_limit:
            LOG.info("Pixel events: integration=%s over monthly limit (%d/%d), dropping batch",
                     integration_id, monthly_views, event_limit)
            return {"accepted": 0, "skipped": len(body.events), "limit_reached": True}

    # 3. Process each event
    is_free_tier = event_limit is not None
    for event in body.events:
        # Find running test for this product
        test = find_running_test(integration_id, event.product_id)
        if not test:
            skipped += 1
            continue

        # Free tier: skip events for tests running longer than 30 days
        if is_free_tier and test.get("started_at"):
            days_running = (datetime.utcnow() - test["started_at"]).days
            if days_running >= 30:
                skipped += 1
                continue

        # Parse event timestamp
        try:
            event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        except ValueError:
            LOG.warning("Invalid timestamp in pixel event: %s", event.timestamp)
            skipped += 1
            continue

        # Determine which variant was active at event time
        variant = get_active_variant_at(test["id"], event_time)
        if not variant:
            # No variant log entry found — use current active variant as fallback
            variant = test["active_variant"]

        # Date for metric rollup (UTC date of the event)
        event_date = event_time.strftime("%Y-%m-%d")

        # Increment the appropriate metric
        if event.event_type == "view":
            increment_ab_test_metric(test["id"], variant, event_date, views=1)
        elif event.event_type == "add_to_cart":
            increment_ab_test_metric(test["id"], variant, event_date, add_to_carts=1)
        elif event.event_type == "conversion":
            revenue = event.revenue_cents or 0
            increment_ab_test_metric(test["id"], variant, event_date, conversions=1, revenue_cents=revenue)

        processed += 1

    # 3. Check auto-conclude for any tests that received events
    # (lightweight — only runs significance check, not a full background job)
    _check_auto_conclude_batch(integration_id, body.events)

    LOG.info("Pixel events: integration=%s processed=%d skipped=%d",
             integration_id, processed, skipped)

    return {"accepted": processed, "skipped": skipped}


# ── Auto-conclude ─────────────────────────────────────────────────────

MIN_VIEWS_FOR_AUTO_CONCLUDE = 200
CONFIDENCE_THRESHOLD = 0.05  # p-value


def _check_auto_conclude_batch(integration_id: str, events: list[PixelEvent]) -> None:
    """Check if any tests that received events should be auto-concluded.

    Only checks tests with enough data to potentially be significant.
    Runs inline (not background) since it's a fast DB query.
    """
    # Deduplicate product IDs from this batch
    product_ids = {e.product_id for e in events}

    for product_id in product_ids:
        test = find_running_test(integration_id, product_id)
        if not test or not test.get("auto_conclude"):
            continue

        aggregated = get_ab_test_aggregated_metrics(test["id"])
        a = aggregated.get("a", {})
        b = aggregated.get("b", {})

        total_views = a.get("views", 0) + b.get("views", 0)
        if total_views < MIN_VIEWS_FOR_AUTO_CONCLUDE:
            continue

        significance = _compute_significance_quick(aggregated)
        if significance["confident"] and significance["recommended_winner"]:
            LOG.info("Auto-concluding test %s: winner=%s p=%.4f",
                     test["id"], significance["recommended_winner"], significance["p_value"])
            update_ab_test(test["id"], {
                "status": "concluded",
                "winner": significance["recommended_winner"],
                "ended_at": datetime.utcnow(),
            })


def _compute_significance_quick(aggregated: dict) -> dict:
    """Minimal significance check (same z-test as routes_ab_tests._compute_significance)."""
    a = aggregated.get("a", {})
    b = aggregated.get("b", {})

    views_a = a.get("views", 0)
    views_b = b.get("views", 0)
    conv_a = a.get("conversions", 0)
    conv_b = b.get("conversions", 0)

    if views_a < 10 or views_b < 10:
        return {"confident": False, "p_value": None, "recommended_winner": None}

    rate_a = conv_a / views_a
    rate_b = conv_b / views_b

    total_views = views_a + views_b
    total_conv = conv_a + conv_b
    pooled_rate = total_conv / total_views if total_views > 0 else 0

    if pooled_rate <= 0 or pooled_rate >= 1:
        return {"confident": False, "p_value": None, "recommended_winner": None}

    se = math.sqrt(pooled_rate * (1 - pooled_rate) * (1 / views_a + 1 / views_b))
    if se == 0:
        return {"confident": False, "p_value": None, "recommended_winner": None}

    z_score = (rate_b - rate_a) / se
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    confident = p_value < CONFIDENCE_THRESHOLD

    recommended = None
    if confident:
        recommended = "b" if rate_b > rate_a else "a"

    return {"confident": confident, "p_value": p_value, "recommended_winner": recommended}


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ── Pixel key management (auth-protected) ────────────────────────────

pixel_key_router = APIRouter(prefix="/v1/ab-tests", tags=["ab-tests-pixel"])


@pixel_key_router.get("/pixel-key/{integration_id}")
async def get_pixel_key(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    """Get or create a pixel key for an integration."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    key = ensure_pixel_key(integration_id)
    return {"pixel_key": key, "integration_id": integration_id}


class UpdateEventLimitIn(BaseModel):
    monthly_event_limit: Optional[int] = None  # None = unlimited


@pixel_key_router.put("/event-limit/{integration_id}")
async def set_event_limit(
    integration_id: str,
    body: UpdateEventLimitIn,
    user: dict = Depends(get_current_user),
):
    """Set the monthly event limit for an integration. null = unlimited (paid plans)."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    update_integration_event_limit(integration_id, body.monthly_event_limit)
    return {"ok": True, "monthly_event_limit": body.monthly_event_limit}


@pixel_key_router.get("/view-usage/{integration_id}")
async def get_view_usage(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    """Get monthly view usage and limit for an integration."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    monthly_views = get_monthly_view_count(integration_id)
    monthly_limit = get_integration_event_limit(integration_id)
    return {
        "monthly_views": monthly_views,
        "monthly_limit": monthly_limit,
    }
