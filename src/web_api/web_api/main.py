import logging
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from shared.config import settings
from web_api.routes_health import router as health_router
from web_api.routes_jobs import router as jobs_router
from web_api.routes_uploads import router as uploads_router
from web_api.routes_downloads import router as downloads_router
from web_api.routes_brand_profiles import router as brand_profiles_router
from web_api.routes_scene_templates import router as scene_templates_router
from web_api.routes_billing import router as billing_router, public_router as billing_public_router
from web_api.routes_integrations import router as integrations_router, oauth_callback_router, gdpr_router
from web_api.routes_catalog import router as catalog_router
from web_api.routes_ab_tests import router as ab_tests_router
from web_api.routes_pixel_events import router as pixel_events_router, pixel_key_router
from web_api.routes_benchmarks import router as benchmarks_router
from web_api.routes_admin import router as admin_router
from web_api.routes_gdpr import router as gdpr_privacy_router, public_router as gdpr_public_router
from web_api.routes_api_keys import router as api_keys_router
from web_api.routes_preferences import router as preferences_router
from web_api.routes_account import router as account_router
from web_api.auth import get_current_user

log = logging.getLogger("opal")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """Run pending migrations on startup."""
    try:
        from shared.db_sqlalchemy import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as session:
            session.execute(text(
                "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS monthly_event_limit INT DEFAULT 1000"
            ))
            session.commit()
            log.info("Startup migration check complete")
    except Exception as e:
        log.warning("Startup migration check failed (non-fatal): %s", e)
    yield

app = FastAPI(title="Opal Web API", version="0.8.1", lifespan=lifespan)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Pixel-Key"],
)

app.include_router(health_router)
app.include_router(billing_public_router)  # Public endpoints (no auth)
app.include_router(gdpr_public_router)  # Public privacy info (no auth)
app.include_router(jobs_router, dependencies=[Depends(get_current_user)])
app.include_router(uploads_router, dependencies=[Depends(get_current_user)])
app.include_router(downloads_router, dependencies=[Depends(get_current_user)])
app.include_router(brand_profiles_router, dependencies=[Depends(get_current_user)])
app.include_router(scene_templates_router, dependencies=[Depends(get_current_user)])
app.include_router(billing_router, dependencies=[Depends(get_current_user)])
app.include_router(integrations_router, dependencies=[Depends(get_current_user)])
app.include_router(catalog_router, dependencies=[Depends(get_current_user)])
app.include_router(ab_tests_router, dependencies=[Depends(get_current_user)])
app.include_router(pixel_events_router)  # Pixel endpoint uses X-Pixel-Key header, no JWT
app.include_router(pixel_key_router, dependencies=[Depends(get_current_user)])  # Pixel key mgmt (auth required)
app.include_router(benchmarks_router, dependencies=[Depends(get_current_user)])
app.include_router(gdpr_privacy_router, dependencies=[Depends(get_current_user)])  # GDPR user data rights
app.include_router(api_keys_router, prefix="/v1", dependencies=[Depends(get_current_user)])
app.include_router(preferences_router, dependencies=[Depends(get_current_user)])
app.include_router(account_router, dependencies=[Depends(get_current_user)])
app.include_router(admin_router)  # Admin routes have their own require_admin dependency
app.include_router(oauth_callback_router)  # OAuth callbacks are browser redirects (state-verified, no auth header)
app.include_router(gdpr_router)  # Shopify GDPR webhooks are unauthenticated (HMAC-verified)
