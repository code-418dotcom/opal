from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from shared.db_supabase import get_job_by_id, get_job_item, update_job_item
from shared.storage_unified import (
    build_raw_blob_path,
    generate_upload_url,
    upload_file as storage_upload_file,
)
from shared.queue_unified import send_job_message
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["uploads"])


class SasRequest(BaseModel):
    job_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    item_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-\.]+$')
    content_type: str = "application/octet-stream"


class UploadComplete(BaseModel):
    job_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    item_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-\.]+$')


@router.post("/uploads/sas")
def get_upload_sas(body: SasRequest, tenant_id: str = Depends(get_tenant_from_api_key)):
    job = get_job_by_id(body.job_id, tenant_id)
    item = get_job_item(body.item_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not item or item["tenant_id"] != tenant_id or item["job_id"] != body.job_id:
        raise HTTPException(status_code=404, detail="Item not found")

    raw_path = build_raw_blob_path(tenant_id, body.job_id, body.item_id, body.filename)
    upload_url = generate_upload_url(bucket="raw", path=raw_path)

    update_job_item(body.item_id, {"raw_blob_path": raw_path})

    return {"upload_url": upload_url, "raw_blob_path": raw_path}


@router.post("/uploads/direct")
async def upload_direct(
    file: UploadFile = File(...),
    job_id: str = Form(...),
    item_id: str = Form(...),
    tenant_id: str = Depends(get_tenant_from_api_key)
):
    """
    Direct upload endpoint - accepts file and uploads to storage backend
    """
    job = get_job_by_id(job_id, tenant_id)
    item = get_job_item(item_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not item or item["tenant_id"] != tenant_id or item["job_id"] != job_id:
        raise HTTPException(status_code=404, detail="Item not found")

    # Build storage path
    raw_path = build_raw_blob_path(tenant_id, job_id, item_id, file.filename or item["filename"])

    # Read file content
    file_content = await file.read()

    # Upload to storage
    storage_upload_file(
        bucket="raw",
        path=raw_path,
        data=file_content,
        content_type=file.content_type or "application/octet-stream"
    )

    # Update item status
    update_job_item(item_id, {"raw_blob_path": raw_path, "status": "uploaded"})

    return {"ok": True, "raw_blob_path": raw_path}


@router.post("/uploads/complete")
def upload_complete(body: UploadComplete, tenant_id: str = Depends(get_tenant_from_api_key)):
    job = get_job_by_id(body.job_id, tenant_id)
    item = get_job_item(body.item_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not item or item["tenant_id"] != tenant_id or item["job_id"] != body.job_id:
        raise HTTPException(status_code=404, detail="Item not found")

    update_job_item(body.item_id, {"status": "uploaded"})

    # Send message to queue to trigger processing
    send_job_message({
        "tenant_id": tenant_id,
        "job_id": body.job_id,
        "item_id": body.item_id,
        "correlation_id": job["correlation_id"],
    })

    return {"ok": True}

