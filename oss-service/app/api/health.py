"""Health endpoints for the OSS service.

    GET /health           liveness (does NOT touch the OSS database)
    GET /health/db        readiness: probes the OSS database if configured

Mirrors the HMS health contract so operators read one shape across services.
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import OssDbNotConfigured, get_db
from app.schemas.health import DatabaseHealthResponse, LivenessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LivenessResponse, summary="Liveness")
def health() -> LivenessResponse:
    """Is the process up? Deliberately does not touch the OSS database."""
    return LivenessResponse(
        status="ok",
        app=settings.APP_NAME,
        env=settings.APP_ENV,
        version="0.1.0",
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="OSS database readiness",
    responses={503: {"description": "OSS database unconfigured or unavailable"}},
)
def health_db() -> DatabaseHealthResponse:
    """Probe the OSS database. 503 (via the handler) when unconfigured/down."""
    gen = get_db()  # raises OssDbNotConfigured -> 503 if OSS_DATABASE_URL unset
    db = next(gen)
    try:
        started = time.perf_counter()
        row = db.execute(
            text("SELECT current_database(), current_schema(), version()")
        ).one()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return DatabaseHealthResponse(
            status="ok",
            database=row[0],
            schema_name=row[1],
            server_version=str(row[2]).split(" ")[1] if row[2] else "unknown",
            alembic_revision=None,  # the OSS DB is owned externally; not Alembic-managed here
            latency_ms=latency_ms,
        )
    finally:
        gen.close()
