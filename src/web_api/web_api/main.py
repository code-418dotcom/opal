import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from web_api.routes_health import router as health_router
from web_api.routes_jobs import router as jobs_router
from web_api.routes_uploads import router as uploads_router
from web_api.routes_downloads import router as downloads_router
from web_api.routes_brand_profiles import router as brand_profiles_router
from web_api.auth import verify_api_key

log = logging.getLogger("opal")

app = FastAPI(title="Opal Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router, dependencies=[Depends(verify_api_key)])
app.include_router(uploads_router, dependencies=[Depends(verify_api_key)])
app.include_router(downloads_router, dependencies=[Depends(verify_api_key)])
app.include_router(brand_profiles_router, dependencies=[Depends(verify_api_key)])


@app.on_event("startup")
def _startup_db_init() -> None:
    """
    Verify Supabase connection on startup.
    """
    try:
        from shared.db_supabase import get_supabase_client
        client = get_supabase_client()
        log.info("Supabase client initialized successfully")
    except Exception:
        log.exception("Supabase init failed (non-fatal). App will start in degraded mode.")
