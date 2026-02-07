from fastapi import APIRouter
from sqlalchemy import text
import logging

from shared.db import SessionLocal
from shared.storage import get_blob_service_client
from shared.servicebus import get_client

router = APIRouter()
LOG = logging.getLogger(__name__)


def _check_db() -> bool:
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception as e:
        LOG.error(f"DB health check failed: {e}")
        return False


def _check_storage() -> bool:
    try:
        c = get_blob_service_client()
        # Try to get a specific container we know exists
        # This definitely works with Storage Blob Data Contributor
        container_client = c.get_container_client("raw")
        _ = container_client.exists()
        return True
    except Exception as e:
        LOG.error(f"Storage health check failed: {e}")
        return False


def _check_servicebus() -> bool:
    try:
        c = get_client()
        c.close()
        return True
    except Exception as e:
        LOG.error(f"ServiceBus health check failed: {e}")
        return False


@router.get("/healthz")
def healthz():
    db_ok = _check_db()
    storage_ok = _check_storage()
    sb_ok = _check_servicebus()

    return {
        "status": "ok" if (db_ok and storage_ok and sb_ok) else "degraded",
        "db": "ok" if db_ok else "fail",
        "storage": "ok" if storage_ok else "fail",
        "service_bus": "ok" if sb_ok else "fail",
    }


@router.get("/readyz")
def readyz():
    db_ok = _check_db()
    storage_ok = _check_storage()
    sb_ok = _check_servicebus()
    
    if db_ok and storage_ok and sb_ok:
        return {"status": "ok"}
    
    return {
        "status": "not-ready",
        "db": db_ok,
        "storage": storage_ok,
        "service_bus": sb_ok,
    }
