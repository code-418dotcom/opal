from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from shared.db_sqlalchemy import (
    get_brand_profile,
    list_brand_profiles,
    create_brand_profile,
    update_brand_profile,
    delete_brand_profile,
    list_brand_reference_images,
    create_brand_reference_image,
    delete_brand_reference_image,
    update_reference_image_style,
)
from shared.storage import generate_upload_url, generate_download_url, build_raw_blob_path
from shared.util import new_id
from web_api.auth import get_tenant_from_api_key, get_current_user

router = APIRouter(prefix="/v1", tags=["brand-profiles"])


class CreateBrandProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    default_scene_prompt: Optional[str] = None
    style_keywords: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    mood: Optional[str] = None
    product_category: Optional[str] = Field(None, max_length=100)
    default_scene_count: Optional[int] = Field(None, ge=1, le=10)
    default_scene_types: Optional[List[str]] = None


class UpdateBrandProfileIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    default_scene_prompt: Optional[str] = None
    style_keywords: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    mood: Optional[str] = None
    product_category: Optional[str] = Field(None, max_length=100)
    default_scene_count: Optional[int] = Field(None, ge=1, le=10)
    default_scene_types: Optional[List[str]] = None


@router.post("/brand-profiles", status_code=201)
def create(body: CreateBrandProfileIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    profile_id = new_id("bp")
    data = {
        "id": profile_id,
        "tenant_id": tenant_id,
        "name": body.name,
        "default_scene_prompt": body.default_scene_prompt,
        "style_keywords": body.style_keywords,
        "color_palette": body.color_palette,
        "mood": body.mood,
        "product_category": body.product_category,
        "default_scene_count": body.default_scene_count,
        "default_scene_types": body.default_scene_types,
    }
    result = create_brand_profile(data)
    return result


@router.get("/brand-profiles")
def list_all(tenant_id: str = Depends(get_tenant_from_api_key)):
    return list_brand_profiles(tenant_id)


@router.get("/brand-profiles/{profile_id}")
def get_one(profile_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    bp = get_brand_profile(profile_id, tenant_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return bp


@router.put("/brand-profiles/{profile_id}")
def update(profile_id: str, body: UpdateBrandProfileIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = update_brand_profile(profile_id, tenant_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return result


@router.delete("/brand-profiles/{profile_id}", status_code=204)
def delete(profile_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    if not delete_brand_profile(profile_id, tenant_id):
        raise HTTPException(status_code=404, detail="Brand profile not found")


# ── Reference Images ───────────────────────────────────────────────

@router.get("/brand-profiles/{profile_id}/reference-images")
def list_references(
    profile_id: str,
    user: dict = Depends(get_current_user),
):
    """List reference images for a brand profile."""
    bp = get_brand_profile(profile_id, user["tenant_id"])
    if not bp:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    images = list_brand_reference_images(profile_id, user["tenant_id"])

    # Add download URLs for each image
    for img in images:
        if img.get("blob_path"):
            try:
                img["download_url"] = generate_download_url("raw", img["blob_path"])
            except Exception:
                img["download_url"] = None

    return {"reference_images": images}


class UploadReferenceIn(BaseModel):
    filename: str = Field(..., pattern=r'^[a-zA-Z0-9_\-]+\.(jpg|jpeg|png|webp)$')


@router.post("/brand-profiles/{profile_id}/reference-images")
def upload_reference(
    profile_id: str,
    body: UploadReferenceIn,
    user: dict = Depends(get_current_user),
):
    """Get a SAS URL to upload a reference image and register it."""
    bp = get_brand_profile(profile_id, user["tenant_id"])
    if not bp:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    # Limit to 5 reference images per profile
    existing = list_brand_reference_images(profile_id, user["tenant_id"])
    if len(existing) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 reference images per brand profile")

    image_id = new_id("bref")
    blob_path = f"{user['tenant_id']}/brand-refs/{profile_id}/{image_id}/{body.filename}"

    upload_url = generate_upload_url("raw", blob_path)

    ref = create_brand_reference_image({
        "id": image_id,
        "brand_profile_id": profile_id,
        "tenant_id": user["tenant_id"],
        "blob_path": blob_path,
    })

    return {
        "upload_url": upload_url,
        "reference_image": ref,
    }


@router.post("/brand-profiles/{profile_id}/reference-images/{image_id}/analyze")
def analyze_reference(
    profile_id: str,
    image_id: str,
    user: dict = Depends(get_current_user),
):
    """Trigger style extraction for a reference image."""
    from shared.style_extraction import extract_style
    from shared.storage import download_file

    bp = get_brand_profile(profile_id, user["tenant_id"])
    if not bp:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    images = list_brand_reference_images(profile_id, user["tenant_id"])
    ref = next((img for img in images if img["id"] == image_id), None)
    if not ref:
        raise HTTPException(status_code=404, detail="Reference image not found")

    # Download and analyze
    image_bytes = download_file("raw", ref["blob_path"])
    style = extract_style(image_bytes)

    update_reference_image_style(image_id, style)

    return {"extracted_style": style}


@router.delete("/brand-profiles/{profile_id}/reference-images/{image_id}", status_code=204)
def delete_reference(
    profile_id: str,
    image_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a reference image."""
    if not delete_brand_reference_image(image_id, user["tenant_id"]):
        raise HTTPException(status_code=404, detail="Reference image not found")
