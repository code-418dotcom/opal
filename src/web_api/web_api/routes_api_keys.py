"""User API key management — generate, list, revoke personal API keys."""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from shared.db import SessionLocal
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/account/api-keys", tags=["api-keys"])

MAX_KEYS_PER_USER = 5
KEY_PREFIX = "opal_"


class CreateKeyIn(BaseModel):
    name: str = Field(default="", max_length=128)


class CreateKeyOut(BaseModel):
    key: str
    id: str
    name: str
    prefix: str
    created_at: str


class KeyInfo(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: str
    last_used_at: Optional[str] = None
    is_active: bool


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.post("", response_model=CreateKeyOut, status_code=201)
def create_api_key(body: CreateKeyIn, user: dict = Depends(get_current_user)):
    """Generate a new API key. The plain key is returned only once."""
    user_id = user["user_id"]

    with SessionLocal() as session:
        # Check active key count
        row = session.execute(
            text("SELECT COUNT(*) AS cnt FROM user_api_keys WHERE user_id = :uid AND is_active = TRUE"),
            {"uid": user_id},
        ).mappings().first()
        if row["cnt"] >= MAX_KEYS_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum of {MAX_KEYS_PER_USER} active API keys allowed",
            )

        # Generate key
        raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
        key_hash = _hash_key(raw_key)
        prefix = raw_key[:8]
        key_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        session.execute(
            text("""
                INSERT INTO user_api_keys (id, user_id, key_hash, key_prefix, name, is_active, created_at)
                VALUES (:id, :user_id, :key_hash, :key_prefix, :name, TRUE, :created_at)
            """),
            {
                "id": key_id,
                "user_id": user_id,
                "key_hash": key_hash,
                "key_prefix": prefix,
                "name": body.name,
                "created_at": now,
            },
        )
        session.commit()

    return CreateKeyOut(
        key=raw_key,
        id=key_id,
        name=body.name,
        prefix=prefix,
        created_at=now.isoformat(),
    )


@router.get("", response_model=list[KeyInfo])
def list_api_keys(user: dict = Depends(get_current_user)):
    """List all API keys for the current user."""
    with SessionLocal() as session:
        rows = session.execute(
            text("""
                SELECT id, name, key_prefix, created_at, last_used_at, is_active
                FROM user_api_keys
                WHERE user_id = :uid
                ORDER BY created_at DESC
            """),
            {"uid": user["user_id"]},
        ).mappings().all()

    return [
        KeyInfo(
            id=str(r["id"]),
            name=r["name"] or "",
            prefix=r["key_prefix"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
            last_used_at=r["last_used_at"].isoformat() if r["last_used_at"] else None,
            is_active=r["is_active"],
        )
        for r in rows
    ]


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(key_id: str, user: dict = Depends(get_current_user)):
    """Soft-delete (revoke) an API key."""
    with SessionLocal() as session:
        result = session.execute(
            text("""
                UPDATE user_api_keys SET is_active = FALSE
                WHERE id = :kid AND user_id = :uid AND is_active = TRUE
            """),
            {"kid": key_id, "uid": user["user_id"]},
        )
        session.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return None
