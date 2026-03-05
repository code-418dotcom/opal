"""Settings service: reads from admin_settings DB table first, falls back to env vars.

Usage:
    from shared.settings_service import get_setting
    api_key = get_setting("SHOPIFY_API_KEY")  # checks DB, then env/config
"""
import logging
from typing import Optional

from .config import settings as env_settings

LOG = logging.getLogger(__name__)


def get_setting(key: str) -> str:
    """Get a setting value. Priority: DB admin_settings > env var > empty string."""
    # Try DB first
    try:
        from .db_sqlalchemy import get_admin_setting_value
        db_value = get_admin_setting_value(key)
        if db_value:
            return db_value
    except Exception:
        pass  # DB not available, fall through to env

    # Fall back to env var / pydantic settings
    return getattr(env_settings, key, '') or ''
