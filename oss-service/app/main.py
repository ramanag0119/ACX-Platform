"""HMS OSS (device/operations) microservice entry point.

    HMS backend (:8000)  ──HTTP──▶  OSS service (:8001)  ──▶  OSS PostgreSQL

Serves the device / telemetry / alert / energy read surface from the existing
OSS database, mapping its (differently-shaped) rows into the exact API contract
the HMS frontend already consumes. No inter-service auth (trusted LAN); bind to
a private interface via settings.HOST.

Run locally:  uvicorn app.main:app --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api.errors import install_exception_handlers
from app.api.health import router as health_router
from app.api.router import api_router
from app.api.security import require_service_token
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "OSS device/operations microservice for HMS. Reads the external OSS "
            "PostgreSQL and returns the HMS device/telemetry/alert/energy contract."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    install_exception_handlers(app)
    app.include_router(health_router)  # ungated: liveness/readiness probes
    # Data routes carry the optional service-token guard (no-op unless
    # OSS_SERVICE_TOKEN is set).
    app.include_router(api_router, dependencies=[Depends(require_service_token)])
    return app


app = create_app()
