from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from shared.db_sqlalchemy import (
    create_job_record,
    create_job_item_records,
    get_job_by_id,
    get_job_items,
    update_job_status,
    list_jobs,
    get_brand_profile,
    get_scene_template,
    debit_tokens,
)
from shared.util import new_id, new_correlation_id
from shared.queue_database import send_job_message
from web_api.auth import get_tenant_from_api_key, get_current_user

router = APIRouter(prefix="/v1", tags=["jobs"])


class ItemIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-\.]+$')
    scene_prompt: str | None = None
    scene_count: int = Field(default=1, ge=1, le=10)
    scene_types: list[str] | None = None
    scene_template_ids: list[str] | None = None
    use_saved_background: bool = False


class ProcessingOptions(BaseModel):
    """Configure which AI processing steps to apply"""
    remove_background: bool = True
    generate_scene: bool = True
    upscale: bool = True


class CreateJobIn(BaseModel):
    brand_profile_id: str = "default"
    items: list[ItemIn] = Field(..., min_length=1, max_length=100)
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    callback_url: str | None = None


@router.post("/jobs")
def create_job(
    body: CreateJobIn,
    tenant_id: str = Depends(get_tenant_from_api_key),
    user: dict = Depends(get_current_user),
):
    # Validate brand profile exists (skip for backward-compat "default")
    if body.brand_profile_id != "default":
        bp = get_brand_profile(body.brand_profile_id, tenant_id)
        if not bp:
            raise HTTPException(status_code=404, detail="Brand profile not found")

    # Token deduction (skip for API key users who have unlimited balance)
    if user["token_balance"] != 999999:
        total_items = sum(
            len(it.scene_template_ids) if it.scene_template_ids else it.scene_count
            for it in body.items
        )
        cost = max(total_items, 1)  # 1 token per output image
        new_balance = debit_tokens(
            user_id=user["user_id"],
            amount=cost,
            description=f"Job: {cost} image(s)",
        )
        if new_balance is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient token balance. This job costs {cost} token(s).",
            )

    job_id = new_id("job")
    corr = new_correlation_id()

    # Create job record
    job_data = {
        "id": job_id,
        "tenant_id": tenant_id,
        "brand_profile_id": body.brand_profile_id,
        "status": "created",
        "correlation_id": corr,
        "processing_options": body.processing_options.model_dump(),
        "callback_url": body.callback_url,
    }
    create_job_record(job_data)

    # Apply brand profile defaults when no explicit scene options provided
    bp = None
    if body.brand_profile_id != "default":
        bp = get_brand_profile(body.brand_profile_id, tenant_id)

    # Create job items (fan out for multi-scene)
    from shared.scene_types import DEFAULT_SCENE_TYPES

    items_data = []
    created_items = []
    for it in body.items:
        # Scene template mode: each template ID becomes a scene
        if it.scene_template_ids:
            templates = []
            for tid in it.scene_template_ids:
                tmpl = get_scene_template(tid, tenant_id)
                if not tmpl:
                    raise HTTPException(status_code=404, detail=f"Scene template not found: {tid}")
                templates.append(tmpl)

            for scene_idx, tmpl in enumerate(templates):
                item_id = new_id("item")
                saved_bg = tmpl.get("preview_blob_path") if it.use_saved_background else None
                items_data.append({
                    "id": item_id,
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "filename": it.filename,
                    "status": "created",
                    "scene_prompt": tmpl["prompt"],
                    "scene_index": scene_idx if len(templates) > 1 else None,
                    "scene_type": tmpl.get("scene_type"),
                    "saved_background_path": saved_bg,
                })
                created_items.append({
                    "item_id": item_id,
                    "filename": it.filename,
                    "scene_index": scene_idx if len(templates) > 1 else None,
                    "scene_type": tmpl.get("scene_type"),
                })
            continue

        # Apply brand profile defaults if no explicit scene config
        scene_count = it.scene_count
        scene_types = it.scene_types
        if bp and scene_count == 1 and not scene_types:
            if bp.get("default_scene_count") and bp["default_scene_count"] > 1:
                scene_count = bp["default_scene_count"]
            if bp.get("default_scene_types"):
                scene_types = bp["default_scene_types"]

        if scene_types and len(scene_types) != scene_count:
            raise HTTPException(
                status_code=422,
                detail=f"scene_types length ({len(scene_types)}) must equal scene_count ({scene_count})"
            )

        for scene_idx in range(scene_count):
            item_id = new_id("item")
            scene_type = None
            scene_prompt = it.scene_prompt

            if scene_count > 1:
                if scene_types:
                    scene_type = scene_types[scene_idx]
                else:
                    scene_type = DEFAULT_SCENE_TYPES[scene_idx % len(DEFAULT_SCENE_TYPES)]

            items_data.append({
                "id": item_id,
                "job_id": job_id,
                "tenant_id": tenant_id,
                "filename": it.filename,
                "status": "created",
                "scene_prompt": scene_prompt,
                "scene_index": scene_idx if scene_count > 1 else None,
                "scene_type": scene_type,
            })
            created_items.append({
                "item_id": item_id,
                "filename": it.filename,
                "scene_index": scene_idx if scene_count > 1 else None,
                "scene_type": scene_type,
            })

    if items_data:
        create_job_item_records(items_data)

    return {
        "job_id": job_id,
        "correlation_id": corr,
        "items": created_items,
        "processing_options": body.processing_options.model_dump()
    }


@router.get("/jobs")
def list_all_jobs(
    tenant_id: str = Depends(get_tenant_from_api_key),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    jobs = list_jobs(tenant_id, status=status, limit=limit, offset=offset)
    return {"jobs": jobs, "limit": limit, "offset": offset}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    job = get_job_by_id(job_id, tenant_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = get_job_items(job_id)
    return {
        "job_id": job["id"],
        "tenant_id": job["tenant_id"],
        "brand_profile_id": job["brand_profile_id"],
        "status": job["status"],
        "correlation_id": job["correlation_id"],
        "export_blob_path": job.get("export_blob_path"),
        "items": [
            {
                "item_id": i["id"],
                "filename": i["filename"],
                "status": i["status"],
                "raw_blob_path": i.get("raw_blob_path"),
                "output_blob_path": i.get("output_blob_path"),
                "error_message": i.get("error_message"),
                "scene_prompt": i.get("scene_prompt"),
                "scene_index": i.get("scene_index"),
                "scene_type": i.get("scene_type"),
                "saved_background_path": i.get("saved_background_path"),
            }
            for i in items
        ],
    }


@router.post("/jobs/{job_id}/enqueue")
def enqueue_job(job_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    job = get_job_by_id(job_id, tenant_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = get_job_items(job_id)
    for it in items:
        if it["status"] in ("created", "uploaded"):
            send_job_message(
                {
                    "tenant_id": tenant_id,
                    "job_id": job_id,
                    "item_id": it["id"],
                    "correlation_id": job["correlation_id"],
                    "processing_options": job.get("processing_options") or {},
                }
            )

    update_job_status(job_id, "processing")

    return {"ok": True}



