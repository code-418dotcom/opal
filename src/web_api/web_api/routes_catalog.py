"""Bulk catalog processing: estimate, start, monitor, cancel."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

from shared.db_sqlalchemy import (
    create_catalog_job, get_catalog_job, list_catalog_jobs, update_catalog_job,
    increment_catalog_job_counts, create_catalog_job_products,
    get_catalog_job_products, update_catalog_job_product,
    get_pending_catalog_products,
    get_integration, get_integration_with_token, get_integration_cost,
    create_job_record, create_job_item_records, update_job_status, debit_tokens,
    get_job_by_id, get_job_items,
)
from shared.encryption import decrypt
from shared.storage import upload_file, build_raw_blob_path, download_file
from shared.queue_database import send_job_message
from shared.util import new_id, new_correlation_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])


# ── Estimate ──────────────────────────────────────────────────────────

@router.get("/{integration_id}/estimate")
async def estimate_catalog(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    """Count products and images, estimate token cost for full catalog processing."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    client = await _get_provider_client(integ)
    products = await _fetch_all_products(client, integ["provider"])

    total_images = sum(len(p.get("images", [])) for p in products)
    products_with_images = [p for p in products if p.get("images")]

    cost_per_image = get_integration_cost(integ["provider"], "process_image")

    return {
        "total_products": len(products),
        "products_with_images": len(products_with_images),
        "total_images": total_images,
        "cost_per_image": cost_per_image,
        "tokens_required": total_images * cost_per_image,
        "products": [
            {
                "id": str(_product_id(p, integ["provider"])),
                "title": _product_title(p, integ["provider"]),
                "image_count": len(p.get("images", [])),
            }
            for p in products_with_images
        ],
    }


# ── Start Catalog Job ────────────────────────────────────────────────

class CatalogStartIn(BaseModel):
    brand_profile_id: str = "default"
    auto_push_back: bool = False
    product_ids: list[str] | None = None  # None = all products
    processing_options: dict = Field(default_factory=lambda: {
        "remove_background": True,
        "generate_scene": True,
        "upscale": False,
    })


@router.post("/{integration_id}/start")
async def start_catalog_job(
    integration_id: str,
    body: CatalogStartIn,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Start bulk catalog processing. Creates a catalog job and processes products in background."""
    integ = get_integration(integration_id, user["user_id"])
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    client = await _get_provider_client(integ)
    all_products = await _fetch_all_products(client, integ["provider"])

    # Filter to selected products if specified
    if body.product_ids:
        selected_ids = set(body.product_ids)
        products = [p for p in all_products if str(_product_id(p, integ["provider"])) in selected_ids]
    else:
        products = all_products

    # Only products with images
    products = [p for p in products if p.get("images")]
    if not products:
        raise HTTPException(status_code=400, detail="No products with images found")

    total_images = sum(len(p.get("images", [])) for p in products)
    cost_per_image = get_integration_cost(integ["provider"], "process_image")
    tokens_required = total_images * cost_per_image

    # Check token balance (skip for API key users)
    if user["user_id"] != "apikey" and tokens_required > 0:
        from shared.db_sqlalchemy import get_user_by_id
        u = get_user_by_id(user["user_id"])
        if not u or u["token_balance"] < tokens_required:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. Need {tokens_required}, have {u['token_balance'] if u else 0}.",
            )

    # Create catalog job
    catalog_job_id = new_id("catjob")
    catalog_job = create_catalog_job({
        "id": catalog_job_id,
        "user_id": user["user_id"],
        "integration_id": integration_id,
        "status": "processing",
        "total_products": len(products),
        "total_images": total_images,
        "tokens_estimated": tokens_required,
        "settings": {
            "brand_profile_id": body.brand_profile_id,
            "auto_push_back": body.auto_push_back,
            "processing_options": body.processing_options,
            "provider": integ["provider"],
        },
    })

    # Create product entries
    product_records = []
    for p in products:
        pid = str(_product_id(p, integ["provider"]))
        product_records.append({
            "id": new_id("catprod"),
            "catalog_job_id": catalog_job_id,
            "product_id": pid,
            "product_title": _product_title(p, integ["provider"]),
            "image_count": len(p.get("images", [])),
        })
    create_catalog_job_products(product_records)

    # Process in background
    background_tasks.add_task(
        _process_catalog_job,
        catalog_job_id=catalog_job_id,
        integration_id=integration_id,
        user_id=user["user_id"],
        tenant_id=user["tenant_id"],
    )

    return {
        "catalog_job_id": catalog_job_id,
        "total_products": len(products),
        "total_images": total_images,
        "tokens_estimated": tokens_required,
    }


# ── Status & Cancel ──────────────────────────────────────────────────

@router.get("/{integration_id}/jobs")
async def list_catalog_jobs_endpoint(
    integration_id: str,
    user: dict = Depends(get_current_user),
):
    """List catalog jobs for this integration."""
    jobs = list_catalog_jobs(user["user_id"])
    # Filter to this integration
    jobs = [j for j in jobs if j["integration_id"] == integration_id]
    return {"catalog_jobs": jobs}


@router.get("/{integration_id}/jobs/{catalog_job_id}")
async def get_catalog_job_status(
    integration_id: str,
    catalog_job_id: str,
    user: dict = Depends(get_current_user),
):
    """Get detailed status of a catalog job including per-product progress."""
    cj = get_catalog_job(catalog_job_id, user["user_id"])
    if not cj:
        raise HTTPException(status_code=404, detail="Catalog job not found")

    products = get_catalog_job_products(catalog_job_id)
    return {**cj, "products": products}


@router.post("/{integration_id}/jobs/{catalog_job_id}/cancel")
async def cancel_catalog_job(
    integration_id: str,
    catalog_job_id: str,
    user: dict = Depends(get_current_user),
):
    """Cancel a running catalog job. Already-queued items will still process."""
    cj = get_catalog_job(catalog_job_id, user["user_id"])
    if not cj:
        raise HTTPException(status_code=404, detail="Catalog job not found")
    if cj["status"] not in ("created", "processing"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in {cj['status']} state")

    update_catalog_job(catalog_job_id, {"status": "canceled"})
    return {"ok": True, "catalog_job_id": catalog_job_id}


# ── Background Processing ────────────────────────────────────────────

async def _process_catalog_job(
    catalog_job_id: str,
    integration_id: str,
    user_id: str,
    tenant_id: str,
):
    """Process all products in a catalog job. Runs as a background task."""
    import httpx

    try:
        cj = get_catalog_job(catalog_job_id, user_id)
        if not cj or cj["status"] == "canceled":
            return

        settings = cj["settings"]
        provider = settings["provider"]
        brand_profile_id = settings.get("brand_profile_id", "default")
        processing_options = settings.get("processing_options", {})
        auto_push_back = settings.get("auto_push_back", False)

        integ = get_integration_with_token(integration_id, user_id)
        if not integ:
            update_catalog_job(catalog_job_id, {"status": "failed", "error_message": "Integration not found"})
            return

        client = await _get_provider_client(integ)
        cost_per_image = get_integration_cost(provider, "process_image")

        # Process products in batches
        while True:
            # Re-check cancellation
            cj = get_catalog_job(catalog_job_id, user_id)
            if not cj or cj["status"] == "canceled":
                return

            pending = get_pending_catalog_products(catalog_job_id, limit=5)
            if not pending:
                break

            for product_entry in pending:
                # Re-check cancellation per product
                cj_check = get_catalog_job(catalog_job_id, user_id)
                if not cj_check or cj_check["status"] == "canceled":
                    return

                await _process_single_product(
                    product_entry=product_entry,
                    catalog_job_id=catalog_job_id,
                    client=client,
                    provider=provider,
                    integ=integ,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    brand_profile_id=brand_profile_id,
                    processing_options=processing_options,
                    cost_per_image=cost_per_image,
                    auto_push_back=auto_push_back,
                )

        # Mark catalog job complete
        cj = get_catalog_job(catalog_job_id, user_id)
        if cj and cj["status"] == "processing":
            final_status = "completed" if cj["failed_count"] == 0 else "completed"
            update_catalog_job(catalog_job_id, {"status": final_status})
            LOG.info("Catalog job %s completed: %d processed, %d failed",
                     catalog_job_id, cj["processed_count"], cj["failed_count"])

    except Exception as e:
        LOG.error("Catalog job %s failed: %s", catalog_job_id, e, exc_info=True)
        update_catalog_job(catalog_job_id, {"status": "failed", "error_message": "Catalog processing failed unexpectedly"})


async def _process_single_product(
    product_entry: dict,
    catalog_job_id: str,
    client,
    provider: str,
    integ: dict,
    user_id: str,
    tenant_id: str,
    brand_profile_id: str,
    processing_options: dict,
    cost_per_image: int,
    auto_push_back: bool,
):
    """Process a single product's images."""
    import httpx

    product_id = product_entry["product_id"]
    update_catalog_job_product(product_entry["id"], {"status": "processing"})

    try:
        # Fetch product images from store
        images = await _fetch_product_images(client, provider, int(product_id))
        if not images:
            update_catalog_job_product(product_entry["id"], {"status": "skipped", "error_message": "No images"})
            increment_catalog_job_counts(catalog_job_id, skipped=1)
            return

        # Debit tokens
        total_cost = cost_per_image * len(images)
        if user_id != "apikey" and total_cost > 0:
            new_balance = debit_tokens(
                user_id=user_id,
                amount=total_cost,
                description=f"Catalog: {product_entry.get('product_title', product_id)} ({len(images)} images)",
            )
            if new_balance is None:
                update_catalog_job_product(product_entry["id"], {
                    "status": "failed",
                    "error_message": "Insufficient tokens",
                })
                increment_catalog_job_counts(catalog_job_id, failed=1)
                # Cancel remaining — no tokens left
                update_catalog_job(catalog_job_id, {
                    "status": "failed",
                    "error_message": "Insufficient tokens to continue processing",
                })
                return

        # Create pipeline job
        job_id = new_id("job")
        corr = new_correlation_id()

        create_job_record({
            "id": job_id,
            "tenant_id": tenant_id,
            "brand_profile_id": brand_profile_id,
            "status": "created",
            "correlation_id": corr,
            "processing_options": processing_options,
        })

        # Download images and upload to blob storage
        items_data = []
        async with httpx.AsyncClient(timeout=30) as http:
            for img in images:
                item_id = new_id("item")
                img_url = _image_url(img, provider)
                img_ext_id = _image_id(img, provider)
                filename = f"{provider}_{product_id}_{img_ext_id}.jpg"
                raw_path = build_raw_blob_path(tenant_id, job_id, item_id, filename)

                try:
                    resp = await http.get(img_url)
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    upload_file("raw", raw_path, resp.content, content_type)

                    items_data.append({
                        "id": item_id,
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "filename": filename,
                        "status": "uploaded",
                        "raw_blob_path": raw_path,
                    })
                except Exception as e:
                    LOG.warning("Failed to download image %s for product %s: %s", img_ext_id, product_id, e)

        if not items_data:
            update_catalog_job_product(product_entry["id"], {
                "status": "failed",
                "error_message": "Failed to download images",
            })
            increment_catalog_job_counts(catalog_job_id, failed=1)
            return

        create_job_item_records(items_data)

        # Enqueue for processing
        for item in items_data:
            send_job_message({
                "tenant_id": tenant_id,
                "job_id": job_id,
                "item_id": item["id"],
                "correlation_id": corr,
                "processing_options": processing_options,
            })
        update_job_status(job_id, "processing")

        # Update product entry
        update_catalog_job_product(product_entry["id"], {
            "status": "completed",
            "job_id": job_id,
        })
        increment_catalog_job_counts(catalog_job_id, processed=1, tokens=total_cost)

        LOG.info("Catalog product %s: job %s created with %d items", product_id, job_id, len(items_data))

        # Auto push-back: wait for pipeline to finish, then push images back to store
        if auto_push_back:
            await _wait_and_push_back(
                job_id=job_id,
                tenant_id=tenant_id,
                product_id=product_id,
                images=images,
                items_data=items_data,
                client=client,
                provider=provider,
            )

    except Exception as e:
        LOG.error("Failed to process catalog product %s: %s", product_id, e, exc_info=True)
        update_catalog_job_product(product_entry["id"], {
            "status": "failed",
            "error_message": "Product processing failed unexpectedly",
        })
        increment_catalog_job_counts(catalog_job_id, failed=1)


# ── Auto Push-Back ────────────────────────────────────────────────────

async def _wait_and_push_back(
    job_id: str,
    tenant_id: str,
    product_id: str,
    images: list,
    items_data: list,
    client,
    provider: str,
):
    """Wait for a pipeline job to finish, then push processed images back to the store."""
    import asyncio

    # Poll job status (max 10 min, check every 5s)
    for _ in range(120):
        await asyncio.sleep(5)
        job = get_job_by_id(job_id, tenant_id)
        if not job:
            break
        if job["status"] in ("completed", "partial", "failed"):
            break
    else:
        LOG.warning("Push-back timeout for job %s product %s", job_id, product_id)
        return

    # Get completed items with output
    completed_items = get_job_items(job_id)
    items_with_output = [it for it in completed_items if it.get("output_blob_path") and it["status"] == "completed"]

    if not items_with_output:
        LOG.info("No completed items to push back for product %s", product_id)
        return

    # Build a mapping from our items to original store images
    # items_data has filename like "{provider}_{product_id}_{image_ext_id}.jpg"
    # We need to match back to the original image for replacement
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)

    pushed = 0
    for item in items_with_output:
        try:
            image_bytes = download_file("outputs", item["output_blob_path"])
            filename = f"opal_{item['filename']}"

            # Extract original image ext ID from filename pattern: {provider}_{product_id}_{img_ext_id}.jpg
            parts = item["filename"].rsplit("_", 1)
            original_img_id = parts[-1].replace(".jpg", "") if len(parts) > 1 else None

            if provider_str == "shopify" and original_img_id:
                try:
                    await client.update_image(int(product_id), int(original_img_id), image_bytes, filename)
                    pushed += 1
                except Exception:
                    # Fallback: add as new image
                    await client.upload_image(int(product_id), image_bytes, filename)
                    pushed += 1
            elif provider_str == "etsy":
                # Etsy doesn't support image update — upload as new
                await client.upload_image(int(product_id), image_bytes, filename)
                pushed += 1
            elif provider_str == "woocommerce":
                await client.upload_image(int(product_id), image_bytes, filename)
                pushed += 1
        except Exception as e:
            LOG.warning("Push-back failed for item %s product %s: %s", item["id"], product_id, e)

    LOG.info("Auto push-back: %d/%d images pushed for product %s", pushed, len(items_with_output), product_id)


# ── Provider Helpers ──────────────────────────────────────────────────

async def _get_provider_client(integ: dict):
    """Create the appropriate client for the integration's provider."""
    provider = integ["provider"]
    if isinstance(provider, str):
        provider_str = provider
    else:
        provider_str = provider.value if hasattr(provider, 'value') else str(provider)

    token = decrypt(integ["access_token_encrypted"])

    if provider_str == "shopify":
        from shared.shopify_client import ShopifyClient
        return ShopifyClient(integ["store_url"], token)
    elif provider_str == "etsy":
        import json
        from shared.etsy_client import EtsyClient
        token_data = json.loads(token)
        return EtsyClient(token_data["access_token"], integ["store_url"])
    elif provider_str == "woocommerce":
        import json
        from shared.woocommerce_client import WooCommerceClient
        token_data = json.loads(token)
        return WooCommerceClient(integ["store_url"], token_data["consumer_key"], token_data["consumer_secret"])
    else:
        raise ValueError(f"Unknown provider: {provider_str}")


async def _fetch_all_products(client, provider: str) -> list:
    """Fetch all products from a store, handling pagination."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    all_products = []

    if provider_str == "shopify":
        page_info = None
        while True:
            result = await client.get_products(limit=250, page_info=page_info)
            all_products.extend(result["products"])
            page_info = result.get("next_page_info")
            if not page_info:
                break
    elif provider_str == "etsy":
        offset = 0
        while True:
            result = await client.get_listings(limit=100, offset=offset)
            listings = result.get("listings", [])
            all_products.extend(listings)
            if len(listings) < 100:
                break
            offset += len(listings)
    elif provider_str == "woocommerce":
        page = 1
        while True:
            result = await client.get_products(per_page=100, page=page)
            products = result.get("products", [])
            all_products.extend(products)
            if page >= result.get("total_pages", 1):
                break
            page += 1

    return all_products


async def _fetch_product_images(client, provider: str, product_id: int) -> list:
    """Fetch images for a single product."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)

    if provider_str == "shopify":
        return await client.get_product_images(product_id)
    elif provider_str == "etsy":
        return await client.get_listing_images(product_id)
    elif provider_str == "woocommerce":
        return await client.get_product_images(product_id)
    return []


def _product_id(product: dict, provider: str) -> str:
    """Extract product ID from product dict."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    if provider_str == "shopify":
        return str(product.get("id", ""))
    elif provider_str == "etsy":
        return str(product.get("listing_id", ""))
    elif provider_str == "woocommerce":
        return str(product.get("id", ""))
    return ""


def _product_title(product: dict, provider: str) -> str:
    """Extract product title from product dict."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    if provider_str == "shopify":
        return product.get("title", "")
    elif provider_str == "etsy":
        return product.get("title", "")
    elif provider_str == "woocommerce":
        return product.get("name", "")
    return ""


def _image_url(image: dict, provider: str) -> str:
    """Extract image URL from image dict."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    if provider_str == "shopify":
        return image.get("src", "")
    elif provider_str == "etsy":
        return image.get("url_fullxfull", "")
    elif provider_str == "woocommerce":
        return image.get("src", "")
    return ""


def _image_id(image: dict, provider: str) -> str:
    """Extract image ID from image dict."""
    provider_str = provider.value if hasattr(provider, 'value') else str(provider)
    if provider_str == "shopify":
        return str(image.get("id", ""))
    elif provider_str == "etsy":
        return str(image.get("listing_image_id", ""))
    elif provider_str == "woocommerce":
        return str(image.get("id", ""))
    return ""
