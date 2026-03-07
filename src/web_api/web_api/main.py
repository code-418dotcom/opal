import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from web_api.routes_health import router as health_router
from web_api.routes_jobs import router as jobs_router
from web_api.routes_uploads import router as uploads_router
from web_api.routes_downloads import router as downloads_router
from web_api.routes_brand_profiles import router as brand_profiles_router
from web_api.routes_scene_templates import router as scene_templates_router
from web_api.routes_billing import router as billing_router, public_router as billing_public_router
from web_api.routes_integrations import router as integrations_router, gdpr_router
from web_api.routes_admin import router as admin_router
from web_api.auth import get_current_user

log = logging.getLogger("opal")

app = FastAPI(title="Opal Web API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(health_router)
app.include_router(billing_public_router)  # Public endpoints (no auth)
app.include_router(jobs_router, dependencies=[Depends(get_current_user)])
app.include_router(uploads_router, dependencies=[Depends(get_current_user)])
app.include_router(downloads_router, dependencies=[Depends(get_current_user)])
app.include_router(brand_profiles_router, dependencies=[Depends(get_current_user)])
app.include_router(scene_templates_router, dependencies=[Depends(get_current_user)])
app.include_router(billing_router, dependencies=[Depends(get_current_user)])
app.include_router(integrations_router, dependencies=[Depends(get_current_user)])
app.include_router(admin_router)  # Admin routes have their own require_admin dependency
app.include_router(gdpr_router)  # GDPR webhooks are unauthenticated (HMAC-verified)
