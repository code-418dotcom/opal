import logging
import secrets
from typing import Optional

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
import jwt

from shared.config import settings
from shared.db_sqlalchemy import (
    get_user_by_entra_subject, get_user_by_email, link_entra_subject,
    create_user, user_count, admin_exists, promote_first_user_to_admin,
)
from shared.util import new_id

LOG = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

# Cache JWKS client (Entra publishes signing keys at OIDC discovery endpoint)
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None and settings.ENTRA_ISSUER:
        # Derive JWKS URI from OIDC discovery rather than hardcoding.
        # External ID issuers use <tenant-id>.ciamlogin.com but JWKS lives
        # under <domain>.ciamlogin.com — safest to use the tenant ID form.
        jwks_uri = f"{settings.ENTRA_ISSUER}/discovery/v2.0/keys"
        if settings.ENTRA_TENANT_ID:
            tid = settings.ENTRA_TENANT_ID.strip()
            base = f"https://{tid}.ciamlogin.com/{tid}"
            jwks_uri = f"{base}/discovery/v2.0/keys"
        _jwks_client = jwt.PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client


def get_valid_api_keys() -> set:
    if not settings.API_KEYS:
        return set()
    keys = [k.strip() for k in settings.API_KEYS.split(',') if k.strip()]
    return set(keys)


async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """
    Resolve authenticated user. Tries JWT first, then API key.
    Returns: { user_id, tenant_id, email, token_balance }
    """
    from web_api.rate_limit import check_rate_limit

    # Path 1: Bearer JWT (Entra External ID)
    if credentials and credentials.credentials:
        user = await _resolve_jwt_user(credentials.credentials)
        check_rate_limit(user["user_id"])
        return user

    # Path 2: API key (programmatic access)
    if api_key:
        user = _resolve_api_key_user(api_key)
        check_rate_limit(user["user_id"])
        return user

    # Path 3: No auth configured (dev mode)
    valid_keys = get_valid_api_keys()
    if not valid_keys and not settings.ENTRA_ISSUER:
        return {"user_id": "anonymous", "tenant_id": "default", "email": "", "token_balance": 999999}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication. Provide Authorization: Bearer <token> or X-API-Key header.",
    )


async def _resolve_jwt_user(token: str) -> dict:
    """Validate Entra JWT and JIT-provision user on first login."""
    jwks = _get_jwks_client()
    if not jwks:
        raise HTTPException(status_code=500, detail="Auth not configured (ENTRA_ISSUER missing)")

    try:
        signing_key = jwks.get_signing_key_from_jwt(token)
        # Accept both raw client ID and Application ID URI as audience
        # (MSAL requests scope api://{clientId}/access → aud = api://{clientId})
        valid_audiences = [settings.ENTRA_CLIENT_ID, f"api://{settings.ENTRA_CLIENT_ID}"]
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer=settings.ENTRA_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        # Debug: log the actual audience from the token for diagnosis
        try:
            unverified = jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_exp": False, "verify_iss": False})
            LOG.warning("JWT validation failed: %s | token aud=%s iss=%s | expected aud=%s iss=%s",
                        e, unverified.get("aud"), unverified.get("iss"), valid_audiences, settings.ENTRA_ISSUER)
        except Exception:
            LOG.warning("JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")

    subject = payload["sub"]
    email = payload.get("email") or payload.get("preferred_username", "")

    # JIT user provisioning — create on first login
    user = get_user_by_entra_subject(subject)
    if not user and email:
        # Check if a pre-created user exists with this email (e.g. admin bootstrap)
        user = get_user_by_email(email)
        if user:
            link_entra_subject(user["id"], subject)
            LOG.info("Linked Entra subject to existing user: %s", user["id"])
    if not user:
        # First user ever gets admin automatically
        is_first = user_count() == 0
        user = create_user({
            "id": new_id("user"),
            "entra_subject_id": subject,
            "email": email,
            "tenant_id": f"tenant_{subject[:8]}",
            "display_name": payload.get("name", ""),
            "token_balance": 50,
            "is_admin": is_first,
        })
        LOG.info("JIT-provisioned user: %s%s", user["id"], " [ADMIN]" if is_first else "")

    # Safety net: if no admin exists at all (e.g. users created before is_admin
    # column existed), promote the earliest user now.
    if not user.get("is_admin") and not admin_exists():
        promoted = promote_first_user_to_admin()
        if promoted:
            LOG.info("Admin bootstrap: promoted %s to admin", promoted["id"])
            # If we just promoted *this* user, update the dict
            if promoted["id"] == user["id"]:
                user = promoted

    return {
        "user_id": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "token_balance": user["token_balance"],
        "is_admin": user.get("is_admin", False),
    }


def _resolve_api_key_user(api_key: str) -> dict:
    """Validate static API key (backward-compatible)."""
    valid_keys = get_valid_api_keys()
    # Constant-time comparison to prevent timing attacks
    if not any(secrets.compare_digest(api_key, key) for key in valid_keys):
        raise HTTPException(status_code=403, detail="Invalid API key")

    tenant = api_key.split('_')[0] if '_' in api_key else "default"
    return {"user_id": "apikey", "tenant_id": tenant, "email": "", "token_balance": 999999}


# Backward-compatible dependency — existing routes use this name
async def get_tenant_from_api_key(
    user: dict = Depends(get_current_user),
) -> str:
    """Returns tenant_id. Drop-in replacement for the old dependency."""
    return user["tenant_id"]


# Legacy — kept for router-level dependency (main.py)
async def verify_api_key(
    user: dict = Depends(get_current_user),
) -> str:
    """Router-level auth check. Returns user_id."""
    return user["user_id"]
