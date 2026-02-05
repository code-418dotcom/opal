from fastapi import APIRouter
from sqlalchemy import text
from shared.db import SessionLocal
from shared.storage import get_blob_service_client
from shared.servicebus import get_client

router = APIRouter()


@router.get("/healthz")
def healthz():
    # DB
    db_ok = False
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Storage
    storage_ok = False
    try:
        c = get_blob_service_client()
        _ = c.get_account_information()
        storage_ok = True
    except Exception:
        storage_ok = False

    # Service Bus
    sb_ok = False
    try:
        c = get_client()
        # client opens successfully; avoid network heavy ops
        sb_ok = True
        c.close()
    except Exception:
        sb_ok = False

    return {
        "status": "ok" if (db_ok and storage_ok and sb_ok) else "degraded",
        "db": "ok" if db_ok else "fail",
        "storage": "ok" if storage_ok else "fail",
        "service_bus": "ok" if sb_ok else "fail",
    }
