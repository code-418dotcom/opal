"""Generic integration routes + Shopify-specific OAuth and product endpoints."""
import logging
import secrets
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field

from shared.config import settings
from shared.settings_service import get_setting
from shared.db_sqlalchemy import (
    create_integration, get_integration, get_integration_with_token,
    list_integrations, update_integration_status, delete_integration,
    get_integration_cost, debit_tokens,
)
from shared.encryption import encrypt, decrypt
from shared.shopify_client import (
    build_oauth_url, exchange_token, verify_hmac, verify_webhook_hmac, ShopifyClient,
)
from shared.storage import download_file
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])

# In-memory OAuth state store (short-lived, per-instance)
# In production, use Redis or DB for multi-instance deployments
_oauth_states: dict[str, dict] = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


# ── Generic Integration Endpoints ────────────────────────────────────

@router.get("")
async def list_user_integrations(
    provider: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    integrations = list_integrations(user["user_id"], provider=provider)
    return {"integrations": integrations}


@router.delete("/{integration_id}")
async def disconnect_integration(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    deleted = delete_integration(integration_id, user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"ok": True}


@router.get("/costs")
async def get_costs(
    provider: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Get token costs for integration actions."""
    process_cost = get_integration_cost(provider, "process_image")
    pushback_cost = get_integration_cost(provider, "push_back")
    return {"process_image": process_cost, "push_back": pushback_cost}


# ── Shopify OAuth ────────────────────────────────────────────────────

class ShopifyConnectIn(BaseModel):
    shop: str = Field(..., pattern=r'^[a-zA-Z0-9\-]+\.myshopify\.com$')


@router.post("/shopify/connect")
async def shopify_connect(
    body: ShopifyConnectIn,
    user: dict = Depends(get_current_user),
):
    """Start Shopify OAuth flow. Returns URL to redirect user to."""
    if not get_setting('SHOPIFY_API_KEY') or not get_setting('SHOPIFY_API_SECRET'):
        raise HTTPException(status_code=503, detail="Shopify integration not configured")

    # Clean up expired states to prevent memory leaks
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if now - v.get("created_at", 0) > _OAUTH_STATE_TTL]
    for k in expired:
        del _oauth_states[k]

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "shop": body.shop,
        "created_at": now,
    }

    redirect_uri = f"{get_setting('PUBLIC_BASE_URL')}/v1/integrations/shopify/callback"
    auth_url = build_oauth_url(body.shop, state, redirect_uri)
    return {"auth_url": auth_url}


@router.get("/shopify/callback")
async def shopify_callback(
    code: str = Query(...),
    state: str = Query(...),
    shop: str = Query(...),
    hmac: str = Query("", alias="hmac"),
    timestamp: str = Query(""),
    host: str = Query(""),
):
    """Handle Shopify OAuth callback. Exchanges code for token and stores integration."""
    # Verify HMAC FIRST before any state or business logic
    query_params = {"code": code, "shop": shop, "state": state, "timestamp": timestamp}
    if host:
        query_params["host"] = host
    if not verify_hmac({**query_params, "hmac": hmac}):
        raise HTTPException(status_code=400, detail="Invalid HMAC signature")

    # Validate state (with TTL check)
    oauth_data = _oauth_states.pop(state, None)
    if not oauth_data or time.time() - oauth_data.get("created_at", 0) > _OAUTH_STATE_TTL:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if shop != oauth_data["shop"]:
        raise HTTPException(status_code=400, detail="Shop mismatch")

    # Exchange code for permanent token
    token_data = await exchange_token(shop, code)
    access_token = token_data["access_token"]
    scopes = token_data.get("scope", "")

    # Get shop info for metadata
    client = ShopifyClient(shop, access_token)
    try:
        shop_info = await client.get_shop_info()
        metadata = {
            "shop_name": shop_info.get("name"),
            "shop_email": shop_info.get("email"),
            "shop_domain": shop_info.get("domain"),
            "shop_plan": shop_info.get("plan_name"),
        }
    except Exception:
        metadata = {}

    # Store integration with encrypted token
    create_integration({
        "id": new_id("integ"),
        "user_id": oauth_data["user_id"],
        "tenant_id": oauth_data["tenant_id"],
        "provider": "shopify",
        "store_url": shop,
        "access_token_encrypted": encrypt(access_token),
        "scopes": scopes,
        "provider_metadata": metadata,
    })

    # Redirect to frontend integrations page
    frontend_url = settings.CORS_ALLOWED_ORIGINS.split(",")[0].strip()
    return _redirect_response(f"{frontend_url}?tab=integrations&shopify=connected")


def _redirect_response(url: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url, status_code=302)


# ── Shopify Products ─────────────────────────────────────────────────

@router.get("/{integration_id}/products")
async def list_products(
    integration_id: str,
    limit: int = Query(50, ge=1, le=250),
    page_info: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List products from connected Shopify store."""
    client = await _get_shopify_client(integration_id, user["user_id"])
    result = await client.get_products(limit=limit, page_info=page_info)
    return result


@router.get("/{integration_id}/products/{product_id}/images")
async def list_product_images(
    integration_id: str,
    product_id: int,
    user: dict = Depends(get_current_user),
):
    """List images for a specific Shopify product."""
    client = await _get_shopify_client(integration_id, user["user_id"])
    images = await client.get_product_images(product_id)
    return {"images": images}


# ── Process & Push Back ──────────────────────────────────────────────

class ProcessImagesIn(BaseModel):
    product_id: int
    image_ids: list[int] | None = None  # None = all images
    brand_profile_id: str = "default"
    processing_options: dict = Field(default_factory=lambda: {
        "remove_background": True,
        "generate_scene": True,
        "upscale": True,
    })


@router.post("/{integration_id}/process")
async def process_images(
    integration_id: str,
    body: ProcessImagesIn,
    user: dict = Depends(get_current_user),
):
    """Download images from Shopify, create an Opal job to process them."""
    from shared.db_sqlalchemy import create_job_record, create_job_item_records
    from shared.storage import upload_file, build_raw_blob_path
    from shared.queue_database import send_job_message

    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    client = await _get_shopify_client(integration_id, user["user_id"])

    # Get images to process
    all_images = await client.get_product_images(body.product_id)
    if body.image_ids:
        images = [img for img in all_images if img["id"] in body.image_ids]
    else:
        images = all_images

    if not images:
        raise HTTPException(status_code=400, detail="No images to process")

    # Check token cost
    cost_per_image = get_integration_cost("shopify", "process_image")
    total_cost = cost_per_image * len(images)

    if user["user_id"] != "apikey" and total_cost > 0:
        new_balance = debit_tokens(
            user_id=user["user_id"],
            amount=total_cost,
            description=f"Shopify: {len(images)} image(s) from {integ['store_url']}",
        )
        if new_balance is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. This costs {total_cost} token(s).",
            )

    # Create job
    from shared.util import new_correlation_id
    job_id = new_id("job")
    corr = new_correlation_id()

    create_job_record({
        "id": job_id,
        "tenant_id": user["tenant_id"],
        "brand_profile_id": body.brand_profile_id,
        "status": "created",
        "correlation_id": corr,
        "processing_options": body.processing_options,
    })

    # Download images from Shopify and upload to blob storage
    import httpx
    items_data = []
    created_items = []

    async with httpx.AsyncClient(timeout=30) as http:
        for img in images:
            item_id = new_id("item")
            filename = f"shopify_{body.product_id}_{img['id']}.jpg"
            raw_path = build_raw_blob_path(user["tenant_id"], job_id, item_id, filename)

            # Download from Shopify CDN
            resp = await http.get(img["src"])
            resp.raise_for_status()
            image_bytes = resp.content

            # Upload to our blob storage
            content_type = resp.headers.get("content-type", "image/jpeg")
            upload_file("raw", raw_path, image_bytes, content_type)

            items_data.append({
                "id": item_id,
                "job_id": job_id,
                "tenant_id": user["tenant_id"],
                "filename": filename,
                "status": "uploaded",
                "raw_blob_path": raw_path,
            })
            created_items.append({
                "item_id": item_id,
                "filename": filename,
                "shopify_image_id": img["id"],
                "shopify_product_id": body.product_id,
            })

    create_job_item_records(items_data)

    # Enqueue all items for processing
    from shared.db_sqlalchemy import update_job_status
    for item in items_data:
        send_job_message({
            "tenant_id": user["tenant_id"],
            "job_id": job_id,
            "item_id": item["id"],
            "correlation_id": corr,
            "processing_options": body.processing_options,
        })
    update_job_status(job_id, "processing")

    return {
        "job_id": job_id,
        "correlation_id": corr,
        "items": created_items,
        "integration_id": integration_id,
    }


class PushBackIn(BaseModel):
    job_id: str
    items: list[dict] = Field(
        ...,
        description="List of {item_id, shopify_product_id, shopify_image_id?, mode: 'replace'|'add'}",
    )


@router.post("/{integration_id}/push-back")
async def push_back_images(
    integration_id: str,
    body: PushBackIn,
    user: dict = Depends(get_current_user),
):
    """Push processed images back to Shopify."""
    from shared.db_sqlalchemy import get_job_item

    client = await _get_shopify_client(integration_id, user["user_id"])

    # Check push-back cost
    cost_per_image = get_integration_cost("shopify", "push_back")
    total_cost = cost_per_image * len(body.items)

    if user["user_id"] != "apikey" and total_cost > 0:
        new_balance = debit_tokens(
            user_id=user["user_id"],
            amount=total_cost,
            description=f"Shopify push-back: {len(body.items)} image(s)",
        )
        if new_balance is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. This costs {total_cost} token(s).",
            )

    results = []
    for item_spec in body.items:
        item_id = item_spec["item_id"]
        product_id = item_spec["shopify_product_id"]
        image_id = item_spec.get("shopify_image_id")
        mode = item_spec.get("mode", "add")

        # Get processed image from our storage (with tenant isolation)
        job_item = get_job_item(item_id)
        if not job_item or job_item.get("tenant_id") != user["tenant_id"]:
            results.append({"item_id": item_id, "status": "error", "error": "Item not found"})
            continue
        if not job_item.get("output_blob_path"):
            results.append({"item_id": item_id, "status": "error", "error": "No output image"})
            continue

        image_bytes = download_file("outputs", job_item["output_blob_path"])
        filename = f"opal_{job_item['filename']}"

        try:
            if mode == "replace" and image_id:
                shopify_img = await client.update_image(product_id, image_id, image_bytes, filename)
            else:
                shopify_img = await client.upload_image(product_id, image_bytes, filename)

            results.append({
                "item_id": item_id,
                "status": "success",
                "shopify_image_id": shopify_img["id"],
                "mode": mode,
            })
        except Exception as e:
            LOG.error("Push-back failed for item %s: %s", item_id, e)
            results.append({"item_id": item_id, "status": "error", "error": "Failed to push image"})

    return {"results": results}


# ── Shopify GDPR Mandatory Webhooks ──────────────────────────────────

gdpr_router = APIRouter(prefix="/v1/integrations/shopify/webhooks", tags=["shopify-gdpr"])


@gdpr_router.post("/customers/data_request")
async def customer_data_request(request: Request):
    """Shopify GDPR: Customer data request. We store minimal data."""
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    LOG.info("Shopify GDPR customer data request received")
    return {"ok": True}


@gdpr_router.post("/customers/redact")
async def customer_redact(request: Request):
    """Shopify GDPR: Customer data erasure. Remove customer-related data.
    We don't store Shopify customer data directly — our integrations are
    linked to the Opal user, not individual Shopify customers."""
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    data = json.loads(body)
    shop_domain = data.get("shop_domain", "")
    LOG.info("Shopify GDPR customer redact for shop %s — no customer PII stored", shop_domain)
    return {"ok": True}


@gdpr_router.post("/shop/redact")
async def shop_redact(request: Request):
    """Shopify GDPR: Shop data erasure. Remove all data for uninstalled shop."""
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook_hmac(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    data = json.loads(body)
    shop_domain = data.get("shop_domain", "")
    LOG.info("Shopify GDPR shop redact for %s", shop_domain)

    # Delete all integrations for this shop across all users
    from shared.db_sqlalchemy import delete_integrations_by_store
    deleted_count = delete_integrations_by_store("shopify", shop_domain)
    LOG.info("Shopify GDPR shop redact: deleted %d integration(s) for %s", deleted_count, shop_domain)
    return {"ok": True}


# ── Helpers ──────────────────────────────────────────────────────────

async def _get_shopify_client(integration_id: str, user_id: str) -> ShopifyClient:
    """Get an authenticated ShopifyClient for the given integration."""
    integ = get_integration_with_token(integration_id, user_id)
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integ["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Integration is {integ['status']}")
    if integ["provider"] != "shopify":
        raise HTTPException(status_code=400, detail="Not a Shopify integration")

    access_token = decrypt(integ["access_token_encrypted"])
    return ShopifyClient(integ["store_url"], access_token)
