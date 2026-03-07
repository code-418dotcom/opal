from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from shared.config import settings
from shared.db_sqlalchemy import (
    list_scene_templates,
    get_scene_template,
    create_scene_template,
    update_scene_template,
    delete_scene_template,
)
from shared.storage import generate_download_url, upload_file as storage_upload_file
from shared.util import new_id
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["scene-templates"])
LOG = logging.getLogger(__name__)


class CreateSceneTemplateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1)
    brand_profile_id: Optional[str] = None
    scene_type: Optional[str] = None


class UpdateSceneTemplateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt: Optional[str] = Field(None, min_length=1)
    brand_profile_id: Optional[str] = None
    scene_type: Optional[str] = None


class PreviewRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class SetPreviewIn(BaseModel):
    preview_blob_path: str = Field(..., min_length=1)


@router.post("/scene-templates", status_code=201)
def create(body: CreateSceneTemplateIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    template_id = new_id("st")
    data = {
        "id": template_id,
        "tenant_id": tenant_id,
        "name": body.name,
        "prompt": body.prompt,
        "brand_profile_id": body.brand_profile_id,
        "scene_type": body.scene_type,
    }
    result = create_scene_template(data)
    return result


@router.get("/scene-templates")
def list_all(
    tenant_id: str = Depends(get_tenant_from_api_key),
    brand_profile_id: Optional[str] = Query(None),
):
    templates = list_scene_templates(tenant_id, brand_profile_id=brand_profile_id)
    # Add preview_url (SAS) for templates that have a preview image
    for t in templates:
        if t.get("preview_blob_path"):
            try:
                t["preview_url"] = generate_download_url("outputs", t["preview_blob_path"])
            except Exception:
                t["preview_url"] = None
        else:
            t["preview_url"] = None
    return templates


@router.get("/scene-templates/{template_id}")
def get_one(template_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    st = get_scene_template(template_id, tenant_id)
    if not st:
        raise HTTPException(status_code=404, detail="Scene template not found")
    if st.get("preview_blob_path"):
        try:
            st["preview_url"] = generate_download_url("outputs", st["preview_blob_path"])
        except Exception:
            st["preview_url"] = None
    return st


@router.put("/scene-templates/{template_id}")
def update(template_id: str, body: UpdateSceneTemplateIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = update_scene_template(template_id, tenant_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Scene template not found")
    return result


@router.delete("/scene-templates/{template_id}", status_code=204)
def delete(template_id: str, tenant_id: str = Depends(get_tenant_from_api_key)):
    if not delete_scene_template(template_id, tenant_id):
        raise HTTPException(status_code=404, detail="Scene template not found")


@router.post("/scene-templates/preview")
def generate_preview(body: PreviewRequest, tenant_id: str = Depends(get_tenant_from_api_key)):
    """Generate a scene preview image from a prompt using the image generation provider."""
    try:
        from shared.image_generation import get_image_gen_provider
    except ImportError:
        raise HTTPException(status_code=503, detail="Image generation not available")

    from shared.settings_service import get_setting
    provider_name = settings.IMAGE_GEN_PROVIDER
    api_key_attr = f'{provider_name.upper().replace(".", "_")}_API_KEY'
    api_key = get_setting(api_key_attr)
    if not api_key:
        raise HTTPException(status_code=503, detail=f"No API key configured for {provider_name}")

    provider = get_image_gen_provider(provider_name, api_key=api_key)

    LOG.info("Generating scene preview for tenant=%s prompt=%.50s...", tenant_id, body.prompt)
    image_bytes = provider.generate(body.prompt)

    # Store preview in blob storage
    preview_id = new_id("prev")
    preview_path = f"{tenant_id}/scene-previews/{preview_id}.png"
    storage_upload_file(
        bucket="outputs",
        path=preview_path,
        data=image_bytes,
        content_type="image/png",
    )

    preview_url = generate_download_url("outputs", preview_path)
    LOG.info("Preview generated: %s (%d bytes)", preview_path, len(image_bytes))

    return {
        "preview_url": preview_url,
        "preview_blob_path": preview_path,
    }


@router.post("/scene-templates/{template_id}/set-preview")
def set_preview(template_id: str, body: SetPreviewIn, tenant_id: str = Depends(get_tenant_from_api_key)):
    """Attach a generated preview image to a scene template."""
    result = update_scene_template(template_id, tenant_id, {"preview_blob_path": body.preview_blob_path})
    if not result:
        raise HTTPException(status_code=404, detail="Scene template not found")
    if result.get("preview_blob_path"):
        try:
            result["preview_url"] = generate_download_url("outputs", result["preview_blob_path"])
        except Exception:
            result["preview_url"] = None
    return result
