from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus
from shared.storage import (
    build_raw_blob_path,
    generate_write_sas,
)
from shared.servicebus import send_job_message
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
    with SessionLocal() as s:
        job = s.get(Job, body.job_id)
        item = s.get(JobItem, body.item_id)

        if not job or job.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
        if not item or item.tenant_id != tenant_id or item.job_id != body.job_id:
            raise HTTPException(status_code=404, detail="Item not found")

        raw_path = build_raw_blob_path(tenant_id, body.job_id, body.item_id, body.filename)
        sas_url = generate_write_sas(container="raw", blob_path=raw_path)

        item.raw_blob_path = raw_path
        s.commit()

    return {"upload_url": sas_url, "raw_blob_path": raw_path}


@router.post("/uploads/complete")
def upload_complete(body: UploadComplete, tenant_id: str = Depends(get_tenant_from_api_key)):
    with SessionLocal() as s:
        job = s.get(Job, body.job_id)
        item = s.get(JobItem, body.item_id)

        if not job or job.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
        if not item or item.tenant_id != tenant_id or item.job_id != body.job_id:
            raise HTTPException(status_code=404, detail="Item not found")

        item.status = ItemStatus.uploaded

        s.commit()

    return {"ok": True}

