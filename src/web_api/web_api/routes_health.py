from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    """
    Liveness probe: MUST be cheap and MUST NOT depend on external services.
    If this fails, the process is not running.
    """
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    """
    Readiness probe: checks dependencies.
    If this fails, the app is running but not ready to serve real traffic.
    """
    # Import heavy deps lazily to avoid crashing the app at import time
    from sqlalchemy import text
    from shared.db import SessionLocal
    from shared.storage import get_blob_service_client
    from shared.servicebus import get_client
    from shared.config import get_settings

    settings = get_settings()

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
        sb_ok = True
        c.close()
    except Exception:
        sb_ok = False

    # AML (optional)
    aml_ok = True
    if settings.aml_configured():
        aml_ok = True
    else:
        # Not configured is not a readiness failure for now (until you wire AML calls)
        aml_ok = True

    status = "ok" if (db_ok and storage_ok and sb_ok and aml_ok) else "degraded"

    return {
        "status": status,
        "db": "ok" if db_ok else "fail",
        "storage": "ok" if storage_ok else "fail",
        "service_bus": "ok" if sb_ok else "fail",
        "aml": "ok" if aml_ok else "fail",
    }
