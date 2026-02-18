from fastapi import APIRouter, HTTPException, Depends, Query
from shared.db_sqlalchemy import get_job_item
from shared.storage_unified import generate_download_url
from web_api.auth import get_tenant_from_api_key

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
