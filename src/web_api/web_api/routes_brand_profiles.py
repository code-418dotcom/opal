from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from shared.db_sqlalchemy import (
    get_brand_profile,
    list_brand_profiles,
    create_brand_profile,
    update_brand_profile,
    delete_brand_profile,
)
from shared.util import new_id
from web_api.auth import get_tenant_from_api_key

router = APIRouter(prefix="/v1", tags=["brand-profiles"])


class CreateBrandProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    default_scene_prompt: Optional[str] = None
    style_keywords: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    mood: Optional[str] = None
    default_scene_count: Optional[int] = Field(None, ge=1, le=10)
    default_scene_types: Optional[List[str]] = None


class UpdateBrandProfileIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    default_scene_prompt: Optional[str] = None
    style_keywords: Optional[List[str]] = None
    color_palette: Optional[List[str]] = None
    mood: Optional[str] = None
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
