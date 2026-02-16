from fastapi import APIRouter
import logging

from shared.db_supabase import get_supabase_client
from shared.storage_unified import get_storage_client

router = APIRouter()
LOG = logging.getLogger(__name__)


def _check_db() -> bool:
    try:
        client = get_supabase_client()
        client.table("jobs").select("id").limit(1).execute()
        return True
    except Exception as e:
        LOG.error(f"DB health check failed: {e}")
        return False


def _check_storage() -> bool:
    try:
        from shared.config import settings
        if not settings.SUPABASE_URL or (not settings.SUPABASE_ANON_KEY and not settings.SUPABASE_SERVICE_ROLE_KEY):
            LOG.error("Storage health check skipped: Supabase not configured")
            return False
        client = get_storage_client()
        # Just test that the client was created
        return True
    except Exception as e:
        LOG.error(f"Storage health check failed: {e}")
        return False


@router.get("/healthz")
def healthz():
    db_ok = _check_db()
    storage_ok = _check_storage()

    return {
        "status": "ok" if (db_ok and storage_ok) else "degraded",
        "db": "ok" if db_ok else "fail",
        "storage": "ok" if storage_ok else "fail",
    }


@router.get("/readyz")
def readyz():
    db_ok = _check_db()
    storage_ok = _check_storage()

    if db_ok and storage_ok:
        return {"status": "ok"}

    return {
        "status": "not-ready",
        "db": db_ok,
        "storage": storage_ok,
    }
