from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from shared.db_sqlalchemy import get_job_item, get_job_by_id
from shared.storage import generate_download_url
from shared.export_presets import list_presets, get_preset
from web_api.auth import get_tenant_from_api_key, get_current_user

router = APIRouter(prefix="/v1", tags=["downloads"])


@router.get("/downloads/{item_id}")
def get_download_url(
    item_id: str,
    bucket: str = Query(default="outputs", pattern="^(raw|outputs|exports)$"),
    tenant_id: str = Depends(get_tenant_from_api_key)
):
    """Generate a SAS download URL for a processed item's output"""
    item = get_job_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get the blob path based on bucket
    if bucket == "outputs":
        blob_path = item.get("output_blob_path")
        if not blob_path:
            raise HTTPException(status_code=404, detail="Output not ready yet")
    elif bucket == "raw":
        blob_path = item.get("raw_blob_path")
        if not blob_path:
            raise HTTPException(status_code=404, detail="Raw file not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid bucket")

    # Generate download URL
    download_url = generate_download_url(bucket=bucket, path=blob_path)

    return {"download_url": download_url}


@router.get("/downloads/jobs/{job_id}/export")
def get_export_download_url(
    job_id: str,
    tenant_id: str = Depends(get_tenant_from_api_key)
):
    """Generate a SAS download URL for a job's export ZIP."""
    job = get_job_by_id(job_id, tenant_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    export_path = job.get("export_blob_path")
    if not export_path:
        raise HTTPException(status_code=404, detail="Export not ready yet")

    download_url = generate_download_url(bucket="exports", path=export_path)
    return {"download_url": download_url}


@router.get("/export-presets")
def get_export_presets():
    """List available marketplace export presets (platform-specific sizes)."""
    return {"presets": list_presets()}


class FormatExportIn(BaseModel):
    format_keys: list[str] = Field(..., min_length=1, max_length=20)


@router.post("/downloads/jobs/{job_id}/export-formats")
def request_format_export(
    job_id: str,
    body: FormatExportIn,
    user: dict = Depends(get_current_user),
):
    """Request a ZIP export with images resized for specific platforms.

    Returns immediately. The export is processed by the export worker.
    Poll GET /v1/downloads/jobs/{job_id}/export-formats/{export_id} for status.
    """
    job = get_job_by_id(job_id, user["tenant_id"])
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate format keys
    valid_keys = []
    for key in body.format_keys:
        if get_preset(key):
            valid_keys.append(key)
    if not valid_keys:
        raise HTTPException(status_code=400, detail="No valid format keys provided")

    # Queue format export via export worker
    from shared.queue_database import send_export_message
    send_export_message({
        "job_id": job_id,
        "tenant_id": user["tenant_id"],
        "format_keys": valid_keys,
    })

    return {
        "status": "queued",
        "job_id": job_id,
        "format_keys": valid_keys,
    }
