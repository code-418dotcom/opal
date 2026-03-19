"""Generic integration routes + Shopify/WooCommerce/Etsy OAuth and product endpoints."""
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
    create_imported_image, get_imported_images_for_product,
    get_imported_image, get_imported_image_by_id, list_imported_products,
    get_integration_by_store_url,
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
oauth_callback_router = APIRouter(prefix="/v1/integrations", tags=["integrations-oauth"])

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


# ── Shopify App Auto-Provision ────────────────────────────────────────


class ShopifyAppProvisionIn(BaseModel):
    store_url: str = Field(..., description="Shopify shop domain, e.g. my-store.myshopify.com")


@router.post("/shopify-app-provision")
async def shopify_app_provision(
    body: ShopifyAppProvisionIn,
    user: dict = Depends(get_current_user),
):
    """Auto-provision an integration for a Shopify shop installed via the App Store.

    Called by the Shopify embedded app when a merchant installs but doesn't have
    an existing Opal integration. Creates a minimal integration without OAuth token
    (pixel tracking doesn't need store API access).
    """
    # Check if integration already exists for this shop
    existing = get_integration_by_store_url(body.store_url)
    if existing:
        return existing

    # Create new integration
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    integ = create_integration({
        "id": new_id("integ"),
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "provider": "shopify",
        "store_url": body.store_url,
        "provider_metadata": {"source": "shopify_app", "provisioned_at": now.isoformat()},
    })
    LOG.info("Auto-provisioned integration %s for shop %s", integ["id"], body.store_url)
    return integ


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


@oauth_callback_router.get("/shopify/callback")
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


# ── Import Product Images ────────────────────────────────────────────

@router.post("/{integration_id}/import/{product_id}")
async def import_product_images(
    integration_id: str,
    product_id: int,
    user: dict = Depends(get_current_user),
):
    """Download product images from store and save to blob storage for re-use."""
    from shared.storage import upload_file
    import httpx

    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check which images are already imported
    existing = get_imported_images_for_product(integration_id, str(product_id))
    existing_ids = {img["provider_image_id"] for img in existing}

    # Get images from store
    client = await _get_shopify_client(integration_id, user["user_id"])
    all_images = await client.get_product_images(product_id)

    # Filter out already-imported images
    to_import = [img for img in all_images if str(img["id"]) not in existing_ids]

    if not to_import:
        return {"imported": 0, "total": len(all_images), "images": existing}

    imported = []
    async with httpx.AsyncClient(timeout=30) as http:
        for img in to_import:
            try:
                resp = await http.get(img["src"])
                resp.raise_for_status()
                image_bytes = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg")

                # Store in blob: imports/{tenant_id}/{integration_id}/{product_id}/{image_id}.jpg
                ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
                blob_path = f"imports/{user['tenant_id']}/{integration_id}/{product_id}/{img['id']}.{ext}"
                filename = f"product_{product_id}_img_{img['id']}.{ext}"

                upload_file("raw", blob_path, image_bytes, content_type)

                record = create_imported_image({
                    "id": new_id("imp"),
                    "user_id": user["user_id"],
                    "tenant_id": user["tenant_id"],
                    "integration_id": integration_id,
                    "provider_product_id": str(product_id),
                    "provider_image_id": str(img["id"]),
                    "blob_path": blob_path,
                    "filename": filename,
                    "original_url": img["src"],
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "file_size": len(image_bytes),
                    "content_type": content_type,
                })
                imported.append(record)
            except Exception as e:
                LOG.warning("Failed to import image %s for product %s: %s", img["id"], product_id, e)

    all_imported = existing + imported
    return {"imported": len(imported), "total": len(all_images), "images": all_imported}


@router.get("/{integration_id}/imported")
async def list_imported(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    """List all products that have imported images."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    products = list_imported_products(user["user_id"], integration_id)
    return {"products": products}


@router.get("/{integration_id}/imported/{product_id}")
async def get_imported_product_images(
    integration_id: str,
    product_id: int,
    user: dict = Depends(get_current_user),
):
    """Get imported images for a specific product with download URLs."""
    from shared.storage import generate_download_url
    images = get_imported_images_for_product(integration_id, str(product_id))
    for img in images:
        img["download_url"] = generate_download_url("raw", img["blob_path"])
    return {"images": images}


class PushOriginalIn(BaseModel):
    imported_image_ids: list[str]
    mode: str = Field(default="replace", pattern=r'^(replace|add)$')


@router.post("/{integration_id}/push-original")
async def push_original_images(
    integration_id: str,
    body: PushOriginalIn,
    user: dict = Depends(get_current_user),
):
    """Push imported original images back to the store (restore originals)."""
    client = await _get_shopify_client(integration_id, user["user_id"])

    results = []
    for imp_id in body.imported_image_ids:
        imp = None
        # Look up the imported image
        from shared.db_sqlalchemy import get_imported_image_by_id
        imp = get_imported_image_by_id(imp_id, user["user_id"])
        if not imp:
            results.append({"id": imp_id, "status": "error", "error": "Not found"})
            continue

        try:
            image_bytes = download_file("raw", imp["blob_path"])
            product_id = int(imp["provider_product_id"])
            image_id = int(imp["provider_image_id"]) if body.mode == "replace" else None
            filename = imp["filename"]

            if body.mode == "replace" and image_id:
                shopify_img = await client.update_image(product_id, image_id, image_bytes, filename)
            else:
                shopify_img = await client.upload_image(product_id, image_bytes, filename)

            results.append({"id": imp_id, "status": "success", "shopify_image_id": shopify_img["id"]})
        except Exception as e:
            LOG.error("Push original failed for %s: %s", imp_id, e, exc_info=True)
            results.append({"id": imp_id, "status": "error", "error": "Failed to push image to store"})

    return {"results": results}


# ── Process & Push Back ──────────────────────────────────────────────

class ProcessImagesIn(BaseModel):
    product_id: int
    image_ids: list[int] | None = None  # None = all images
    brand_profile_id: str = "default"
    processing_options: dict = Field(default_factory=lambda: {
        "remove_background": True,
        "generate_scene": True,
        "upscale": False,
    })
    scene_count: int = Field(default=1, ge=1, le=10)
    scene_template_ids: list[str] | None = None
    use_saved_background: bool = False
    angle_types: list[str] | None = None


@router.post("/{integration_id}/process")
async def process_images(
    integration_id: str,
    body: ProcessImagesIn,
    user: dict = Depends(get_current_user),
):
    """Download images from store, create an Opal job with scene/angle fan-out."""
    from shared.db_sqlalchemy import (
        create_job_record, create_job_item_records, update_job_status,
        get_brand_profile, get_scene_template,
    )
    from shared.storage import upload_file, build_raw_blob_path
    from shared.queue_database import send_job_message
    from shared.util import new_correlation_id

    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Validate angle_types
    if body.angle_types:
        from shared.scene_types import ANGLE_PROMPTS
        invalid = [a for a in body.angle_types if a not in ANGLE_PROMPTS]
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid angle_types: {invalid}. Valid: {list(ANGLE_PROMPTS.keys())}",
            )

    client = await _get_shopify_client(integration_id, user["user_id"])

    # Get images to process
    all_images = await client.get_product_images(body.product_id)
    if body.image_ids:
        images = [img for img in all_images if img["id"] in body.image_ids]
    else:
        images = all_images

    if not images:
        raise HTTPException(status_code=400, detail="No images to process")

    # Calculate fan-out multiplier for scenes × angles
    angle_list = body.angle_types or [None]
    scene_count = body.scene_count

    # Resolve scene templates
    templates = []
    if body.scene_template_ids:
        for tid in body.scene_template_ids:
            tmpl = get_scene_template(tid, user.get("tenant_id", ""))
            if not tmpl:
                raise HTTPException(status_code=404, detail=f"Scene template not found: {tid}")
            templates.append(tmpl)
        scene_count = len(templates)

    items_per_image = scene_count * len(angle_list)
    total_items = len(images) * items_per_image

    # Token cost with half-credit for single-step
    opts = body.processing_options
    steps_enabled = sum([
        opts.get("remove_background", True),
        opts.get("generate_scene", True),
        opts.get("upscale", False),
    ])
    if steps_enabled <= 1:
        total_cost = max(1, -(-total_items // 2))
    else:
        total_cost = max(total_items, 1)

    if user["user_id"] != "apikey" and total_cost > 0:
        new_balance = debit_tokens(
            user_id=user["user_id"],
            amount=total_cost,
            description=f"Store: {total_items} image(s) from {integ['store_url']}",
        )
        if new_balance is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. This job costs {total_cost} token(s).",
            )

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

    # Resolve default scene types for multi-scene
    from shared.scene_types import DEFAULT_SCENE_TYPES

    # Download images and fan out items for scene × angle combinations
    # Check for cached imports first to avoid re-downloading
    import httpx
    items_data = []
    created_items = []

    cached_imports = {
        imp["provider_image_id"]: imp
        for imp in get_imported_images_for_product(integration_id, str(body.product_id))
    }

    async with httpx.AsyncClient(timeout=30) as http:
        for img in images:
            filename = f"shopify_{body.product_id}_{img['id']}.jpg"

            # Use cached import if available, otherwise download from store
            cached = cached_imports.get(str(img["id"]))
            if cached:
                image_bytes = download_file("raw", cached["blob_path"])
                content_type = cached.get("content_type", "image/jpeg")
            else:
                resp = await http.get(img["src"])
                resp.raise_for_status()
                image_bytes = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg")

            multi = items_per_image > 1
            idx = 0

            if templates:
                # Template mode
                for tmpl in templates:
                    saved_bg = tmpl.get("preview_blob_path") if body.use_saved_background else None
                    for angle in angle_list:
                        item_id = new_id("item")
                        raw_path = build_raw_blob_path(user["tenant_id"], job_id, item_id, filename)
                        upload_file("raw", raw_path, image_bytes, content_type)

                        items_data.append({
                            "id": item_id,
                            "job_id": job_id,
                            "tenant_id": user["tenant_id"],
                            "filename": filename,
                            "status": "uploaded",
                            "raw_blob_path": raw_path,
                            "scene_prompt": tmpl["prompt"],
                            "scene_index": idx if multi else None,
                            "scene_type": tmpl.get("scene_type"),
                            "saved_background_path": saved_bg,
                            "angle_type": angle,
                        })
                        created_items.append({
                            "item_id": item_id,
                            "filename": filename,
                            "shopify_image_id": img["id"],
                            "shopify_product_id": body.product_id,
                            "scene_index": idx if multi else None,
                            "scene_type": tmpl.get("scene_type"),
                            "angle_type": angle,
                        })
                        idx += 1
            else:
                # Scene count mode
                for scene_idx in range(body.scene_count):
                    scene_type = None
                    if body.scene_count > 1:
                        scene_type = DEFAULT_SCENE_TYPES[scene_idx % len(DEFAULT_SCENE_TYPES)]

                    for angle in angle_list:
                        item_id = new_id("item")
                        raw_path = build_raw_blob_path(user["tenant_id"], job_id, item_id, filename)
                        upload_file("raw", raw_path, image_bytes, content_type)

                        items_data.append({
                            "id": item_id,
                            "job_id": job_id,
                            "tenant_id": user["tenant_id"],
                            "filename": filename,
                            "status": "uploaded",
                            "raw_blob_path": raw_path,
                            "scene_index": idx if multi else None,
                            "scene_type": scene_type,
                            "angle_type": angle,
                        })
                        created_items.append({
                            "item_id": item_id,
                            "filename": filename,
                            "shopify_image_id": img["id"],
                            "shopify_product_id": body.product_id,
                            "scene_index": idx if multi else None,
                            "scene_type": scene_type,
                            "angle_type": angle,
                        })
                        idx += 1

    create_job_item_records(items_data)

    # Enqueue all items for processing
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


# ── WooCommerce OAuth ────────────────────────────────────────────────

class WooCommerceConnectIn(BaseModel):
    store_url: str = Field(..., description="Full WooCommerce store URL, e.g. https://example.com")


@router.post("/woocommerce/connect")
async def woocommerce_connect(
    body: WooCommerceConnectIn,
    user: dict = Depends(get_current_user),
):
    """Start WooCommerce REST API key authorization flow."""
    from shared.woocommerce_client import build_oauth_url as wc_build_oauth_url

    state = secrets.token_urlsafe(32)
    now = time.time()
    _oauth_states[state] = {
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "store_url": body.store_url.rstrip("/"),
        "provider": "woocommerce",
        "created_at": now,
    }

    redirect_uri = f"{get_setting('PUBLIC_BASE_URL')}/v1/integrations/woocommerce/callback"
    auth_url = wc_build_oauth_url(body.store_url, state, redirect_uri)
    return {"auth_url": auth_url}


@oauth_callback_router.post("/woocommerce/callback")
async def woocommerce_callback(request: Request):
    """Handle WooCommerce REST API key callback."""
    data = await request.json()
    state = data.get("user_id", "")  # WooCommerce maps our state token to "user_id"
    consumer_key = data.get("consumer_key", "")
    consumer_secret = data.get("consumer_secret", "")

    oauth_data = _oauth_states.pop(state, None)
    if not oauth_data or oauth_data.get("provider") != "woocommerce":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if time.time() - oauth_data.get("created_at", 0) > _OAUTH_STATE_TTL:
        raise HTTPException(status_code=400, detail="Expired OAuth state")

    # Store both keys as encrypted JSON
    import json
    token_payload = json.dumps({"consumer_key": consumer_key, "consumer_secret": consumer_secret})

    create_integration({
        "id": new_id("integ"),
        "user_id": oauth_data["user_id"],
        "tenant_id": oauth_data["tenant_id"],
        "provider": "woocommerce",
        "store_url": oauth_data["store_url"],
        "access_token_encrypted": encrypt(token_payload),
        "scopes": "read_write",
        "provider_metadata": {"store_url": oauth_data["store_url"]},
    })

    return {"ok": True}


# ── WooCommerce Products ────────────────────────────────────────────

@router.get("/{integration_id}/wc-products")
async def list_wc_products(
    integration_id: str,
    per_page: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    user: dict = Depends(get_current_user),
):
    """List products from connected WooCommerce store."""
    client = await _get_woocommerce_client(integration_id, user["user_id"])
    return await client.get_products(per_page=per_page, page=page)


@router.get("/{integration_id}/wc-products/{product_id}/images")
async def list_wc_product_images(
    integration_id: str,
    product_id: int,
    user: dict = Depends(get_current_user),
):
    """List images for a specific WooCommerce product."""
    client = await _get_woocommerce_client(integration_id, user["user_id"])
    images = await client.get_product_images(product_id)
    return {"images": images}


# ── Etsy OAuth ───────────────────────────────────────────────────────

class EtsyConnectIn(BaseModel):
    shop_id: str = Field(..., description="Etsy shop ID")


@router.post("/etsy/connect")
async def etsy_connect(
    body: EtsyConnectIn,
    user: dict = Depends(get_current_user),
):
    """Start Etsy OAuth2 PKCE flow."""
    if not get_setting("ETSY_API_KEY"):
        raise HTTPException(status_code=503, detail="Etsy integration not configured")

    from shared.etsy_client import build_oauth_url as etsy_build_oauth_url

    state = secrets.token_urlsafe(32)
    now = time.time()
    _oauth_states[state] = {
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "shop_id": body.shop_id,
        "provider": "etsy",
        "created_at": now,
    }

    redirect_uri = f"{get_setting('PUBLIC_BASE_URL')}/v1/integrations/etsy/callback"
    auth_url, code_verifier = etsy_build_oauth_url(state, redirect_uri)
    _oauth_states[state]["code_verifier"] = code_verifier
    return {"auth_url": auth_url}


@oauth_callback_router.get("/etsy/callback")
async def etsy_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Etsy OAuth2 callback."""
    oauth_data = _oauth_states.pop(state, None)
    if not oauth_data or oauth_data.get("provider") != "etsy":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if time.time() - oauth_data.get("created_at", 0) > _OAUTH_STATE_TTL:
        raise HTTPException(status_code=400, detail="Expired OAuth state")

    from shared.etsy_client import exchange_token as etsy_exchange_token

    redirect_uri = f"{get_setting('PUBLIC_BASE_URL')}/v1/integrations/etsy/callback"
    token_data = await etsy_exchange_token(code, redirect_uri, code_verifier=oauth_data["code_verifier"])

    import json
    token_payload = json.dumps({
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
    })

    create_integration({
        "id": new_id("integ"),
        "user_id": oauth_data["user_id"],
        "tenant_id": oauth_data["tenant_id"],
        "provider": "etsy",
        "store_url": oauth_data["shop_id"],
        "access_token_encrypted": encrypt(token_payload),
        "scopes": "listings_r listings_w images_r images_w",
        "provider_metadata": {"shop_id": oauth_data["shop_id"]},
    })

    frontend_url = settings.CORS_ALLOWED_ORIGINS.split(",")[0].strip()
    return _redirect_response(f"{frontend_url}?tab=integrations&etsy=connected")


# ── Etsy Listings ────────────────────────────────────────────────────

@router.get("/{integration_id}/etsy-listings")
async def list_etsy_listings(
    integration_id: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """List listings from connected Etsy shop."""
    client = await _get_etsy_client(integration_id, user["user_id"])
    return await client.get_listings(limit=limit, offset=offset)


@router.get("/{integration_id}/etsy-listings/{listing_id}/images")
async def list_etsy_listing_images(
    integration_id: str,
    listing_id: int,
    user: dict = Depends(get_current_user),
):
    """List images for a specific Etsy listing."""
    client = await _get_etsy_client(integration_id, user["user_id"])
    images = await client.get_listing_images(listing_id)
    return {"images": images}


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


async def _get_woocommerce_client(integration_id: str, user_id: str):
    """Get an authenticated WooCommerceClient for the given integration."""
    from shared.woocommerce_client import WooCommerceClient

    integ = get_integration_with_token(integration_id, user_id)
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integ["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Integration is {integ['status']}")
    if integ["provider"] != "woocommerce":
        raise HTTPException(status_code=400, detail="Not a WooCommerce integration")

    import json
    token_data = json.loads(decrypt(integ["access_token_encrypted"]))
    return WooCommerceClient(
        integ["store_url"],
        token_data["consumer_key"],
        token_data["consumer_secret"],
    )


async def _get_etsy_client(integration_id: str, user_id: str):
    """Get an authenticated EtsyClient for the given integration."""
    from shared.etsy_client import EtsyClient

    integ = get_integration_with_token(integration_id, user_id)
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integ["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Integration is {integ['status']}")
    if integ["provider"] != "etsy":
        raise HTTPException(status_code=400, detail="Not an Etsy integration")

    import json
    token_data = json.loads(decrypt(integ["access_token_encrypted"]))
    return EtsyClient(token_data["access_token"], integ["store_url"])
