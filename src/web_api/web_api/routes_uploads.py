from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus
from shared.storage import (
    build_raw_blob_path,
    generate_write_sas,
)
from shared.servicebus import send_job_message

router = APIRouter(prefix="/v1", tags=["uploads"])


class SasRequest(BaseModel):
    tenant_id: str
    job_id: str
    item_id: str
    filename: str
    content_type: str = "application/octet-stream"


class UploadComplete(BaseModel):
    tenant_id: str
    job_id: str
    item_id: str
    filename: str


@router.post("/uploads/sas")
def get_upload_sas(body: SasRequest):
    with SessionLocal() as s:
        job = s.get(Job, body.job_id)
        item = s.get(JobItem, body.item_id)
        
        if not job or job.tenant_id != body.tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
        if not item or item.tenant_id != body.tenant_id or item.job_id != body.job_id:
            raise HTTPException(status_code=404, detail="Item not found")
        
        raw_path = build_raw_blob_path(body.tenant_id, body.job_id, body.item_id, body.filename)
        sas_url = generate_write_sas(container="raw", blob_path=raw_path)
        
        item.raw_blob_path = raw_path
        s.commit()
    
    return {"upload_url": sas_url, "raw_blob_path": raw_path}


@router.post("/uploads/complete")
def upload_complete(body: UploadComplete):
    with SessionLocal() as s:
        job = s.get(Job, body.job_id)
        item = s.get(JobItem, body.item_id)
        
        if not job or job.tenant_id != body.tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
        if not item or item.tenant_id != body.tenant_id or item.job_id != body.job_id:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item.status = ItemStatus.uploaded
        
        # CRITICAL FIX: Extract correlation_id BEFORE session closes
        correlation_id = job.correlation_id
        
        s.commit()
    
    # Now send message with the extracted value
    send_job_message(
        {
            "tenant_id": body.tenant_id,
            "job_id": body.job_id,
            "item_id": body.item_id,
            "correlation_id": correlation_id,
        }
    )
    
    return {"ok": True}
