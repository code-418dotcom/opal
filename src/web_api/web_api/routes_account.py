"""Account profile routes — onboarding and profile management."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from shared.db_sqlalchemy import get_user_by_id, update_user_profile
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/account", tags=["account"])


class ProfileOut(BaseModel):
    display_name: Optional[str] = None
    email: str
    company_name: Optional[str] = None
    vat_number: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    onboarding_completed: bool = False


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile."""
    u = get_user_by_id(user["user_id"])
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return ProfileOut(**u).model_dump()


class ProfileUpdateIn(BaseModel):
    display_name: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)
    vat_number: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    onboarding_completed: Optional[bool] = None


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateIn,
    user: dict = Depends(get_current_user),
):
    """Update current user's profile. Used during onboarding and later edits."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    result = update_user_profile(user["user_id"], updates)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    LOG.info("Profile updated for user %s", user["user_id"])
    return ProfileOut(**result).model_dump()
