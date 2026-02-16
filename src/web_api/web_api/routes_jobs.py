from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from shared.db import SessionLocal
from shared.models import Job, JobItem, JobStatus, ItemStatus
from shared.util import new_id, new_correlation_id
from shared.queue_unified import send_job_message
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["jobs"])

# IMPORTANT:
# Do NOT create DB tables at import time. This can crash the whole app if DB is unavailable.
# Migrations later; for MVP we’ll do a *non-fatal* init in startup (see main.py).


class ItemIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_\-\.]+$')


class CreateJobIn(BaseModel):
    brand_profile_id: str = "default"
    items: list[ItemIn] = Field(..., min_length=1, max_length=100)


@router.post("/jobs")
def create_job(body: CreateJobIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    job_id = new_id("job")
    corr = new_correlation_id()

    with SessionLocal() as s:
        job = Job(
            id=job_id,
            tenant_id=tenant_id,
            brand_profile_id=body.brand_profile_id,
            status=JobStatus.created,
            correlation_id=corr,
        )
        s.add(job)

        created_items = []
        for it in body.items:
            item_id = new_id("item")
            item = JobItem(
                id=item_id,
                job_id=job_id,
                tenant_id=tenant_id,
                filename=it.filename,
                status=ItemStatus.created,
            )
            s.add(item)
            created_items.append({"item_id": item_id, "filename": it.filename})

        s.commit()

    return {"job_id": job_id, "correlation_id": corr, "items": created_items}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job or job.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")

        items = s.query(JobItem).filter(JobItem.job_id == job_id).all()
        return {
            "job_id": job.id,
            "tenant_id": job.tenant_id,
            "brand_profile_id": job.brand_profile_id,
            "status": job.status.value,
            "correlation_id": job.correlation_id,
            "items": [
                {
                    "item_id": i.id,
                    "filename": i.filename,
                    "status": i.status.value,
                    "raw_blob_path": i.raw_blob_path,
                    "output_blob_path": i.output_blob_path,
                    "error_message": i.error_message,
                }
                for i in items
            ],
        }


@router.post("/jobs/{job_id}/enqueue")
def enqueue_job(job_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job or job.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")

        items = s.query(JobItem).filter(JobItem.job_id == job_id).all()
        for it in items:
            if it.status in (ItemStatus.created, ItemStatus.uploaded):
                send_job_message(
                    {
                        "tenant_id": tenant_id,
                        "job_id": job_id,
                        "item_id": it.id,
                        "correlation_id": job.correlation_id,
                    }
                )

        job.status = JobStatus.processing
        s.commit()

    return {"ok": True}



