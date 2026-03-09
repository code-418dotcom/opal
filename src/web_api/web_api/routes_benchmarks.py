"""Image benchmarking routes.

Analyze product images for quality, compare against category averages,
and generate improvement suggestions.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel

from shared.db_sqlalchemy import (
    create_image_benchmark,
    get_image_benchmark,
    list_image_benchmarks,
    get_category_benchmarks,
    get_category_benchmark,
    get_job_item,
)
from shared.image_scoring import score_image
from shared.storage import download_file
from shared.util import new_id
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])


class AnalyzeIn(BaseModel):
    job_item_id: Optional[str] = None
    image_url: Optional[str] = None
    product_title: Optional[str] = None
    product_id: Optional[str] = None
    integration_id: Optional[str] = None
    category: str = "general"
    image_count: int = 1


def _store_and_respond(image_bytes, user, category, image_count, image_url=None,
                       integration_id=None, product_id=None, product_title=None,
                       job_item_id=None):
    """Score image, persist benchmark, return response."""
    result = score_image(image_bytes, image_count=image_count, category=category)
    cat_bench = get_category_benchmark(category)

    benchmark = create_image_benchmark({
        "id": new_id("bench"),
        "user_id": user["user_id"],
        "integration_id": integration_id,
        "product_id": product_id,
        "product_title": product_title,
        "image_url": image_url,
        "job_item_id": job_item_id,
        "scores": result["scores"],
        "overall_score": result["overall_score"],
        "suggestions": result["suggestions"],
        "category": category,
    })

    return {
        **benchmark,
        "category_avg": cat_bench["avg_scores"] if cat_bench else None,
    }


@router.post("/analyze")
async def analyze_image(
    body: AnalyzeIn,
    user: dict = Depends(get_current_user),
):
    """Analyze a product image by job_item_id or image_url."""
    image_bytes = None
    image_url = None

    if body.job_item_id:
        item = get_job_item(body.job_item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Job item not found")
        blob_path = item.get("output_blob_path") or item.get("raw_blob_path")
        if not blob_path:
            raise HTTPException(status_code=400, detail="Job item has no image")
        try:
            image_bytes = download_file("outputs", blob_path)
        except Exception:
            try:
                image_bytes = download_file("raw", blob_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Cannot download image: {e}")
        image_url = blob_path
    elif body.image_url:
        import httpx
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(body.image_url)
                resp.raise_for_status()
                image_bytes = resp.content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot fetch image: {e}")
        image_url = body.image_url
    else:
        raise HTTPException(status_code=400, detail="Provide job_item_id or image_url")

    return _store_and_respond(
        image_bytes, user, body.category, body.image_count,
        image_url=image_url,
        integration_id=body.integration_id,
        product_id=body.product_id,
        product_title=body.product_title,
        job_item_id=body.job_item_id,
    )


@router.post("/analyze-upload")
async def analyze_upload(
    file: UploadFile = File(...),
    category: str = Form("general"),
    image_count: int = Form(1),
    product_title: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Analyze a directly uploaded product image."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    return _store_and_respond(
        image_bytes, user, category, image_count,
        product_title=product_title or None,
    )


@router.get("")
async def list_benchmarks(
    integration_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """List user's image benchmarks."""
    benchmarks = list_image_benchmarks(
        user["user_id"],
        integration_id=integration_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return {"benchmarks": benchmarks}


@router.get("/categories")
async def list_categories(
    user: dict = Depends(get_current_user),
):
    """List available category benchmarks with averages."""
    categories = get_category_benchmarks()
    return {"categories": categories}


@router.get("/{benchmark_id}")
async def get_benchmark(
    benchmark_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single benchmark result."""
    bm = get_image_benchmark(benchmark_id, user["user_id"])
    if not bm:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    cat_bench = get_category_benchmark(bm["category"] or "general")
    return {
        **bm,
        "category_avg": cat_bench["avg_scores"] if cat_bench else None,
    }
