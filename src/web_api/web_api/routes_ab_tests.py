"""A/B image testing: create tests, swap variants, record metrics, conclude."""
import logging
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from shared.db_sqlalchemy import (
    create_ab_test, get_ab_test, list_ab_tests, update_ab_test,
    get_ab_test_metrics, upsert_ab_test_metric, get_ab_test_aggregated_metrics,
    get_integration, get_integration_with_token, get_job_item,
    create_variant_log_entry,
)
from shared.encryption import decrypt
from shared.storage import download_file
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ab-tests", tags=["ab-tests"])


# ── Create ────────────────────────────────────────────────────────────

class CreateABTestIn(BaseModel):
    integration_id: str
    product_id: str
    product_title: str = ""
    # Either job_item_ids (Opal processed images) or image_urls (e.g. Shopify CDN)
    variant_a_job_item_id: str | None = None
    variant_b_job_item_id: str | None = None
    variant_a_image_url: str | None = None
    variant_b_image_url: str | None = None
    variant_a_label: str = "Variant A"
    variant_b_label: str = "Variant B"
    original_image_id: str | None = None


@router.post("")
async def create_test(
    body: CreateABTestIn,
    user: dict = Depends(get_current_user),
):
    """Create a new A/B test for a product image."""
    # Validate integration
    integ = get_integration(body.integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Each variant needs either a job_item_id or an image_url
    has_a = body.variant_a_job_item_id or body.variant_a_image_url
    has_b = body.variant_b_job_item_id or body.variant_b_image_url
    if not has_a or not has_b:
        raise HTTPException(status_code=400, detail="Both variants must have either a job_item_id or image_url")

    # Validate job items if provided
    if body.variant_a_job_item_id:
        item_a = get_job_item(body.variant_a_job_item_id)
        if not item_a or not item_a.get("output_blob_path"):
            raise HTTPException(status_code=400, detail="Variant A image not found or not processed")
    if body.variant_b_job_item_id:
        item_b = get_job_item(body.variant_b_job_item_id)
        if not item_b or not item_b.get("output_blob_path"):
            raise HTTPException(status_code=400, detail="Variant B image not found or not processed")

    test = create_ab_test({
        "id": new_id("abtest"),
        "user_id": user["user_id"],
        "integration_id": body.integration_id,
        "product_id": body.product_id,
        "product_title": body.product_title,
        "variant_a_job_item_id": body.variant_a_job_item_id,
        "variant_b_job_item_id": body.variant_b_job_item_id,
        "variant_a_image_url": body.variant_a_image_url,
        "variant_b_image_url": body.variant_b_image_url,
        "variant_a_label": body.variant_a_label,
        "variant_b_label": body.variant_b_label,
        "original_image_id": body.original_image_id,
        "active_variant": "a",
        "status": "created",
    })

    return test


# ── List & Get ────────────────────────────────────────────────────────

@router.get("")
async def list_tests(
    integration_id: str | None = Query(None),
    status: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    tests = list_ab_tests(user["user_id"], integration_id=integration_id, status=status)
    return {"tests": tests}


@router.get("/{test_id}")
async def get_test(
    test_id: str,
    user: dict = Depends(get_current_user),
):
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    metrics = get_ab_test_aggregated_metrics(test_id)
    daily_metrics = get_ab_test_metrics(test_id)

    # Compute statistical significance
    significance = _compute_significance(metrics)

    return {
        **test,
        "metrics": metrics,
        "daily_metrics": daily_metrics,
        "significance": significance,
    }


# ── Start / Swap / Conclude ──────────────────────────────────────────

class StartTestIn(BaseModel):
    skip_push: bool = False  # True when the caller handles image push (e.g. Shopify app)


@router.post("/{test_id}/start")
async def start_test(
    test_id: str,
    body: StartTestIn = StartTestIn(),
    user: dict = Depends(get_current_user),
):
    """Start a test: push variant A to the store as the live image."""
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test["status"] not in ("created",):
        raise HTTPException(status_code=400, detail=f"Cannot start test in {test['status']} state")

    # Push variant A to the store (unless caller handles it)
    if not body.skip_push:
        await _push_variant_to_store(test, "a", user["user_id"])

    update_ab_test(test_id, {
        "status": "running",
        "active_variant": "a",
        "started_at": datetime.utcnow(),
    })

    # Log variant activation for pixel event attribution
    create_variant_log_entry(test_id, "a")

    return {"ok": True, "active_variant": "a"}


class SwapTestIn(BaseModel):
    skip_push: bool = False


@router.post("/{test_id}/swap")
async def swap_variant(
    test_id: str,
    body: SwapTestIn = SwapTestIn(),
    user: dict = Depends(get_current_user),
):
    """Swap which variant is live on the store."""
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test["status"] != "running":
        raise HTTPException(status_code=400, detail="Test is not running")

    new_variant = "b" if test["active_variant"] == "a" else "a"

    if not body.skip_push:
        await _push_variant_to_store(test, new_variant, user["user_id"])

    update_ab_test(test_id, {"active_variant": new_variant})

    # Log variant activation for pixel event attribution
    create_variant_log_entry(test_id, new_variant)

    return {"ok": True, "active_variant": new_variant}


class ConcludeIn(BaseModel):
    winner: str = Field(..., pattern=r'^[ab]$')


@router.post("/{test_id}/conclude")
async def conclude_test(
    test_id: str,
    body: ConcludeIn,
    user: dict = Depends(get_current_user),
):
    """End the test, pick a winner, and set the winning variant as permanent."""
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test["status"] != "running":
        raise HTTPException(status_code=400, detail="Test is not running")

    # Push the winner to the store
    await _push_variant_to_store(test, body.winner, user["user_id"])

    update_ab_test(test_id, {
        "status": "concluded",
        "winner": body.winner,
        "active_variant": body.winner,
        "ended_at": datetime.utcnow(),
    })

    return {"ok": True, "winner": body.winner}


@router.post("/{test_id}/cancel")
async def cancel_test(
    test_id: str,
    user: dict = Depends(get_current_user),
):
    """Cancel a test. If original_image_id is set, restore it."""
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test["status"] not in ("created", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel test in {test['status']} state")

    update_ab_test(test_id, {
        "status": "canceled",
        "ended_at": datetime.utcnow(),
    })

    return {"ok": True}


# ── Metrics ───────────────────────────────────────────────────────────

class MetricIn(BaseModel):
    variant: str = Field(..., pattern=r'^[ab]$')
    date: str  # ISO date string YYYY-MM-DD
    views: int = 0
    clicks: int = 0
    add_to_carts: int = 0
    conversions: int = 0
    revenue_cents: int = 0


@router.post("/{test_id}/metrics")
async def record_metric(
    test_id: str,
    body: MetricIn,
    user: dict = Depends(get_current_user),
):
    """Record or update metrics for a variant on a specific date."""
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    metric = upsert_ab_test_metric({
        "id": new_id("abm"),
        "ab_test_id": test_id,
        "variant": body.variant,
        "date": body.date,
        "views": body.views,
        "clicks": body.clicks,
        "add_to_carts": body.add_to_carts,
        "conversions": body.conversions,
        "revenue_cents": body.revenue_cents,
    })

    return metric


@router.get("/{test_id}/metrics")
async def get_metrics(
    test_id: str,
    user: dict = Depends(get_current_user),
):
    test = get_ab_test(test_id, user["user_id"])
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    daily = get_ab_test_metrics(test_id)
    aggregated = get_ab_test_aggregated_metrics(test_id)
    significance = _compute_significance(aggregated)

    return {
        "daily": daily,
        "aggregated": aggregated,
        "significance": significance,
    }


# ── Helpers ───────────────────────────────────────────────────────────

async def _push_variant_to_store(test: dict, variant: str, user_id: str):
    """Push a variant image to the store as the product's primary image."""
    import httpx

    item_id = test.get(f"variant_{variant}_job_item_id")
    image_url = test.get(f"variant_{variant}_image_url")

    if item_id:
        item = get_job_item(item_id)
        if not item or not item.get("output_blob_path"):
            raise HTTPException(status_code=400, detail=f"Variant {variant} image not available")
        image_bytes = download_file("outputs", item["output_blob_path"])
        filename = f"opal_ab_{variant}_{item['filename']}"
    elif image_url:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            image_bytes = resp.content
        # Extract filename from URL
        url_path = image_url.split("?")[0].split("/")[-1]
        filename = f"opal_ab_{variant}_{url_path}"
    else:
        raise HTTPException(status_code=400, detail=f"Variant {variant} has no image source")

    integ = get_integration_with_token(test["integration_id"], user_id)
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    provider = integ["provider"]
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    token = decrypt(integ["access_token_encrypted"])
    product_id = int(test["product_id"])

    if provider_str == "shopify":
        from shared.shopify_client import ShopifyClient
        client = ShopifyClient(integ["store_url"], token)
        original_id = test.get("original_image_id")
        if original_id:
            try:
                await client.update_image(product_id, int(original_id), image_bytes, filename)
                return
            except Exception:
                pass
        # Fallback: upload as new image at position 1
        await client.upload_image(product_id, image_bytes, filename, position=1)

    elif provider_str == "etsy":
        import json
        from shared.etsy_client import EtsyClient
        token_data = json.loads(token)
        client = EtsyClient(token_data["access_token"], integ["store_url"])
        await client.upload_image(product_id, image_bytes, filename, rank=1)

    elif provider_str == "woocommerce":
        import json
        from shared.woocommerce_client import WooCommerceClient
        token_data = json.loads(token)
        client = WooCommerceClient(integ["store_url"], token_data["consumer_key"], token_data["consumer_secret"])
        await client.upload_image(product_id, image_bytes, filename)

    LOG.info("A/B test %s: pushed variant %s to %s product %s",
             test["id"], variant, provider_str, test["product_id"])


def _compute_significance(aggregated: dict) -> dict:
    """Compute statistical significance using a z-test on conversion rates.

    Returns confidence level and recommendation.
    """
    a = aggregated.get("a", {})
    b = aggregated.get("b", {})

    views_a = a.get("views", 0) or a.get("clicks", 0)
    views_b = b.get("views", 0) or b.get("clicks", 0)
    conv_a = a.get("conversions", 0)
    conv_b = b.get("conversions", 0)

    if views_a < 10 or views_b < 10:
        return {
            "confident": False,
            "message": "Not enough data yet. Need at least 10 views per variant.",
            "p_value": None,
            "lift_percent": None,
            "recommended_winner": None,
        }

    rate_a = conv_a / views_a
    rate_b = conv_b / views_b

    # Pooled proportion z-test
    total_views = views_a + views_b
    total_conv = conv_a + conv_b
    pooled_rate = total_conv / total_views if total_views > 0 else 0

    se = math.sqrt(pooled_rate * (1 - pooled_rate) * (1/views_a + 1/views_b)) if pooled_rate > 0 and pooled_rate < 1 else 0

    if se == 0:
        z_score = 0.0
    else:
        z_score = (rate_b - rate_a) / se

    # Approximate p-value from z-score (two-tailed)
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))

    lift = ((rate_b - rate_a) / rate_a * 100) if rate_a > 0 else None
    confident = p_value < 0.05

    if not confident:
        recommended = None
    elif rate_b > rate_a:
        recommended = "b"
    else:
        recommended = "a"

    return {
        "confident": confident,
        "message": f"{'Statistically significant' if confident else 'Not yet significant'} (p={p_value:.4f})",
        "p_value": round(p_value, 4),
        "lift_percent": round(lift, 1) if lift is not None else None,
        "recommended_winner": recommended,
        "conversion_rate_a": round(rate_a * 100, 2),
        "conversion_rate_b": round(rate_b * 100, 2),
    }


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF using the error function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
