from fastapi import APIRouter
from sqlalchemy import text
from shared.db import SessionLocal
from shared.storage import get_blob_service_client
from shared.servicebus import get_client

router = APIRouter()


def _check_db() -> bool:
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_storage() -> bool:
    try:
        c = get_blob_service_client()
        _ = c.get_account_information()
        return True
    except Exception:
        return False


def _check_servicebus() -> bool:
    try:
        c = get_client()
        c.close()
        return True
    except Exception:
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
    """
    Readiness should be strict: if dependencies aren't reachable, return degraded.
    Your ingress/probes can use this later.
    """
    db_ok = _check_db()
    storage_ok = _check_storage()
    sb_ok = _check_servicebus()

    if db_ok and storage_ok and sb_ok:
        return {"status": "ok"}

    # Keeping response body helpful; if you want 503, we can switch to Response(status_code=503)
    return {
        "status": "not-ready",
        "db": db_ok,
        "storage": storage_ok,
        "service_bus": sb_ok,
    }
