from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
import logging

from shared.db_sqlalchemy import get_job_by_id, get_job_item, update_job_item, get_job_items_by_filename
from shared.storage import (
    build_raw_blob_path,
    generate_upload_url,
    upload_file as storage_upload_file,
)
from shared.queue_database import send_job_message, send_job_messages_batch
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["uploads"])
LOG = logging.getLogger(__name__)


class SasRequest(BaseModel):
    job_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    item_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-]+\.(jpg|jpeg|png|webp|tiff|bmp)$')
    content_type: str = "application/octet-stream"


class ProcessingOptions(BaseModel):
    """Configure which AI processing steps to apply"""
    remove_background: bool = True
    generate_scene: bool = True
    upscale: bool = False


class UploadComplete(BaseModel):
    job_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    item_id: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9_\-]+$')
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-]+\.(jpg|jpeg|png|webp|tiff|bmp)$')
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)


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

    # Set raw_blob_path on this item AND all siblings with same filename (multi-scene)
    siblings = get_job_items_by_filename(body.job_id, body.filename)
    for sibling in siblings:
        update_job_item(sibling["id"], {"raw_blob_path": raw_path})

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

    # Set raw_blob_path on this item AND all siblings with same filename (multi-scene)
    siblings = get_job_items_by_filename(job_id, item["filename"])
    for sibling in siblings:
        update_job_item(sibling["id"], {"raw_blob_path": raw_path, "status": "uploaded"})

    return {"ok": True, "raw_blob_path": raw_path}


@router.post("/uploads/complete")
def upload_complete(body: UploadComplete, tenant_id: str = Depends(get_tenant_from_api_key)):
    job = get_job_by_id(body.job_id, tenant_id)
    item = get_job_item(body.item_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not item or item["tenant_id"] != tenant_id or item["job_id"] != body.job_id:
        raise HTTPException(status_code=404, detail="Item not found")

    # Mark all siblings (multi-scene) as uploaded and send queue messages
    siblings = get_job_items_by_filename(body.job_id, body.filename)
    if not siblings:
        siblings = [item]

    for sibling in siblings:
        update_job_item(sibling["id"], {"status": "uploaded"})

    LOG.info("Upload complete: job_id=%s item_id=%s tenant_id=%s siblings=%d",
             body.job_id, body.item_id, tenant_id, len(siblings))

    messages = []
    for sibling in siblings:
        msg = {
            "tenant_id": tenant_id,
            "job_id": body.job_id,
            "item_id": sibling["id"],
            "correlation_id": job["correlation_id"],
            "processing_options": body.processing_options.model_dump(),
        }
        if sibling.get("saved_background_path"):
            msg["saved_background_path"] = sibling["saved_background_path"]
        messages.append(msg)

    try:
        send_job_messages_batch(messages)
        LOG.info("Queued %d messages for job_id=%s", len(messages), body.job_id)
    except Exception as e:
        LOG.error("Failed to send batch queue messages for job_id=%s: %s", body.job_id, e, exc_info=True)

    return {"ok": True}

