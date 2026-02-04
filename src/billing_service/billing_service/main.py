from fastapi import FastAPI
from billing_service.routes_health import router as health_router
from billing_service.routes_mollie import router as mollie_router

app = FastAPI(title="Opal Billing Service", version="0.1.0")

app.include_router(health_router)
app.include_router(mollie_router)
