"""HMS OSS (device/operations) microservice entry point.

    HMS backend (:8000)  ──HTTP──▶  OSS service (:8001)  ──▶  OSS PostgreSQL

Serves the device / telemetry / alert / energy read surface from the existing
OSS database, mapping its (differently-shaped) rows into the exact API contract
the HMS frontend already consumes. Inter-service auth is the shared
OSS_SERVICE_TOKEN, optional in development and required in every other APP_ENV;
bind to a private interface via settings.HOST.

Run locally:  uvicorn app.main:app --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api.errors import install_exception_handlers
from app.api.health import router as health_router
from app.api.router import build_api_router
from app.api.security import require_service_token
from app.core.config import settings


def create_app() -> FastAPI:
    # The open, token-less mode is for a developer's trusted LAN only. Anywhere
    # else the data routes would be readable by anything that can reach the port.
    if settings.APP_ENV != "development" and not settings.OSS_SERVICE_TOKEN:
        raise RuntimeError(
            "OSS_SERVICE_TOKEN is not set. Set the same token in oss-service and "
            "backend before running outside development."
        )
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
    # OSS_SERVICE_TOKEN is set). Only this process's OSS_DOMAINS are mounted.
    app.include_router(
        build_api_router(settings.oss_domains),
        dependencies=[Depends(require_service_token)],
    )
    return app


app = create_app()
