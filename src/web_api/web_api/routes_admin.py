"""Admin routes for settings management, user management, and system info."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from shared.db_sqlalchemy import (
    list_admin_settings, get_admin_setting, upsert_admin_setting, delete_admin_setting,
    list_users, set_user_admin, set_user_token_balance, get_user_by_id,
)
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# ── Admin Auth Dependency ────────────────────────────────────────────

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin access. API key users are always admin."""
    if user.get("token_balance") == 999999:
        return user  # API key users are admin

    if user.get("user_id") == "anonymous":
        return user  # Dev mode is admin

    # Check is_admin flag from DB
    db_user = get_user_by_id(user["user_id"])
    if not db_user or not db_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


# ── Settings Endpoints ───────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    category: Optional[str] = Query(None),
    admin: dict = Depends(require_admin),
):
    """List all settings (secrets are masked)."""
    settings = list_admin_settings(category=category)
    return {"settings": settings}


class UpdateSettingIn(BaseModel):
    value: str
    category: Optional[str] = None
    is_secret: Optional[bool] = None
    description: Optional[str] = None


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    body: UpdateSettingIn,
    admin: dict = Depends(require_admin),
):
    """Create or update a setting."""
    result = upsert_admin_setting(
        key=key,
        value=body.value,
        user_id=admin["user_id"],
        category=body.category,
        is_secret=body.is_secret,
        description=body.description,
    )
    LOG.info("Admin setting '%s' updated by %s", key, admin["user_id"])
    return result


class CreateSettingIn(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r'^[A-Z][A-Z0-9_]*$')
    value: str = ''
    category: str = 'general'
    is_secret: bool = False
    description: Optional[str] = None


@router.post("/settings")
async def create_setting(
    body: CreateSettingIn,
    admin: dict = Depends(require_admin),
):
    """Create a new setting."""
    existing = get_admin_setting(body.key)
    if existing:
        raise HTTPException(status_code=409, detail=f"Setting '{body.key}' already exists")

    result = upsert_admin_setting(
        key=body.key,
        value=body.value,
        user_id=admin["user_id"],
        category=body.category,
        is_secret=body.is_secret,
        description=body.description,
    )
    LOG.info("Admin setting '%s' created by %s", body.key, admin["user_id"])
    return result


@router.delete("/settings/{key}")
async def remove_setting(
    key: str,
    admin: dict = Depends(require_admin),
):
    """Delete a setting."""
    deleted = delete_admin_setting(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Setting not found")
    LOG.info("Admin setting '%s' deleted by %s", key, admin["user_id"])
    return {"ok": True}


# ── User Management ─────────────────────────────────────────────────

@router.get("/users")
async def get_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_admin),
):
    """List all users."""
    users = list_users(limit=limit, offset=offset)
    return {"users": users, "limit": limit, "offset": offset}


class SetAdminIn(BaseModel):
    is_admin: bool


@router.put("/users/{user_id}/admin")
async def update_user_admin(
    user_id: str,
    body: SetAdminIn,
    admin: dict = Depends(require_admin),
):
    """Grant or revoke admin access for a user."""
    result = set_user_admin(user_id, body.is_admin)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    action = "granted" if body.is_admin else "revoked"
    LOG.info("Admin access %s for user %s by %s", action, user_id, admin["user_id"])
    return result


class SetTokenBalanceIn(BaseModel):
    token_balance: int = Field(..., ge=0)


@router.put("/users/{user_id}/tokens")
async def update_user_tokens(
    user_id: str,
    body: SetTokenBalanceIn,
    admin: dict = Depends(require_admin),
):
    """Set absolute token balance for a user."""
    result = set_user_token_balance(user_id, body.token_balance)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    LOG.info("Token balance set to %d for user %s by %s", body.token_balance, user_id, admin["user_id"])
    return result


# ── System Info ──────────────────────────────────────────────────────

@router.get("/system")
async def system_info(admin: dict = Depends(require_admin)):
    """Get system configuration overview (non-secret)."""
    from shared.config import settings as env_settings
    from shared.settings_service import get_setting
    return {
        "env_name": env_settings.ENV_NAME,
        "storage_backend": env_settings.STORAGE_BACKEND,
        "queue_backend": env_settings.QUEUE_BACKEND,
        "image_gen_provider": env_settings.IMAGE_GEN_PROVIDER,
        "upscale_provider": env_settings.UPSCALE_PROVIDER,
        "upscale_enabled": env_settings.UPSCALE_ENABLED,
        "bg_removal_provider": env_settings.BACKGROUND_REMOVAL_PROVIDER,
        "has_entra_config": bool(env_settings.ENTRA_ISSUER),
        "has_mollie_config": bool(get_setting('MOLLIE_API_KEY')),
        "has_shopify_config": bool(get_setting('SHOPIFY_API_KEY')),
        "has_fal_config": bool(get_setting('FAL_API_KEY')),
        "has_encryption_key": bool(get_setting('ENCRYPTION_KEY')),
        "public_base_url": get_setting('PUBLIC_BASE_URL'),
    }
