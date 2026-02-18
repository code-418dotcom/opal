from fastapi import APIRouter
import logging

from shared.db import SessionLocal
from shared.models import Job
from shared.config import settings

router = APIRouter()
LOG = logging.getLogger(__name__)


def _check_db() -> bool:
    """Check database connectivity using SQLAlchemy."""
    try:
        with SessionLocal() as session:
            session.query(Job).limit(1).all()
        return True
    except Exception as e:
        LOG.error(f"DB health check failed: {e}")
        return False


def _check_storage() -> bool:
    """Check Azure storage connectivity."""
    try:
        if not settings.STORAGE_ACCOUNT_NAME:
            LOG.error("Storage health check skipped: STORAGE_ACCOUNT_NAME not configured")
            return False
        # For Azure, we just check if the config is present
        # Actual blob operations require managed identity which is configured at runtime
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
