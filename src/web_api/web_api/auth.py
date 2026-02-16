import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from shared.config import settings

LOG = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


def get_valid_api_keys() -> set:
    if not settings.API_KEYS:
        LOG.warning("No API keys configured. API authentication disabled.")
        return set()

    keys = [k.strip() for k in settings.API_KEYS.split(',') if k.strip()]
    return set(keys)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    valid_keys = get_valid_api_keys()

    if not valid_keys:
        return "anonymous"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header."
        )

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key


async def get_tenant_from_api_key(api_key: str = Security(verify_api_key)) -> str:
    if api_key == "anonymous":
        return "default"

    key_prefix = api_key.split('_')[0] if '_' in api_key else "default"
    return key_prefix
