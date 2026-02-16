from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from shared.db_supabase import (
    create_job_record,
    create_job_item_records,
    get_job_by_id,
    get_job_items,
    update_job_status,
)
from shared.util import new_id, new_correlation_id
from shared.queue_unified import send_job_message
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["jobs"])


class ItemIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-\.]+$')


class CreateJobIn(BaseModel):
    brand_profile_id: str = "default"
    items: list[ItemIn] = Field(..., min_length=1, max_length=100)


@router.post("/jobs")
def create_job(body: CreateJobIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    job_id = new_id("job")
    corr = new_correlation_id()

    # Create job record
    job_data = {
        "id": job_id,
        "tenant_id": tenant_id,
        "brand_profile_id": body.brand_profile_id,
        "status": "created",
        "correlation_id": corr,
    }
    create_job_record(job_data)

    # Create job items
    items_data = []
    created_items = []
    for it in body.items:
        item_id = new_id("item")
        items_data.append({
            "id": item_id,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "filename": it.filename,
            "status": "created",
        })
        created_items.append({"item_id": item_id, "filename": it.filename})

    if items_data:
        create_job_item_records(items_data)

    return {"job_id": job_id, "correlation_id": corr, "items": created_items}


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
        "items": [
            {
                "item_id": i["id"],
                "filename": i["filename"],
                "status": i["status"],
                "raw_blob_path": i.get("raw_blob_path"),
                "output_blob_path": i.get("output_blob_path"),
                "error_message": i.get("error_message"),
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
                }
            )

    update_job_status(job_id, "processing")

    return {"ok": True}



