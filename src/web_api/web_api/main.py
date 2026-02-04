from fastapi import FastAPI
from web_api.routes_health import router as health_router
from web_api.routes_jobs import router as jobs_router
from web_api.routes_uploads import router as uploads_router

app = FastAPI(title="Opal Web API", version="0.1.0")

app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(uploads_router)
