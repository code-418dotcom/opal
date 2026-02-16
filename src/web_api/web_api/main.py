import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from web_api.routes_health import router as health_router
from web_api.routes_jobs import router as jobs_router
from web_api.routes_uploads import router as uploads_router
from web_api.auth import verify_api_key

log = logging.getLogger("opal")

app = FastAPI(title="Opal Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router, dependencies=[Depends(verify_api_key)])
app.include_router(uploads_router, dependencies=[Depends(verify_api_key)])


@app.on_event("startup")
def _startup_db_init() -> None:
    """
    MVP-only: attempt to create tables on startup.
    CRITICAL: This must never crash the app if DB is unavailable.
    """
    try:
        from shared.db import engine
        from shared.models import Base

        Base.metadata.create_all(bind=engine)
        log.info("DB init: tables ensured.")
    except Exception:
        log.exception("DB init failed (non-fatal). App will start in degraded mode.")
