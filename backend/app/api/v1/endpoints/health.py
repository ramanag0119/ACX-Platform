"""Health endpoints: database readiness and the running API version.

Every value `/health/db` returns is read live from PostgreSQL on each request. There
is no cached or hardcoded status: if the database is unreachable, the endpoint
answers 503 rather than reporting "ok".
"""

from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.core.config import settings
from app.core.version import API_VERSION
from app.schemas.health import DatabaseHealthResponse, ErrorResponse, VersionResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/version", response_model=VersionResponse, summary="API version")
def api_version() -> VersionResponse:
    """The version this API process is running, for the About screen.

    Served under the v1 prefix, unlike `/health`, so the frontend reaches it
    through its configured API base with no extra proxy rule.
    """
    return VersionResponse(app=settings.APP_NAME, version=API_VERSION)


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    summary="Database readiness",
    responses={503: {"model": ErrorResponse, "description": "Database unreachable"}},
)
def database_health(db: DbSession) -> DatabaseHealthResponse:
    """Probe PostgreSQL with a real query and report what it answered.

    The probe itself is `SELECT 1`; the remaining reads are single-row lookups,
    so the endpoint stays cheap enough to be polled by a load balancer.
    """
    started = perf_counter()
    try:
        # The actual liveness probe -- a real round trip to PostgreSQL.
        db.execute(text("SELECT 1")).scalar_one()
        latency_ms = round((perf_counter() - started) * 1000, 2)

        database = db.execute(text("SELECT current_database()")).scalar_one()
        server_version = db.execute(text("SHOW server_version")).scalar_one()
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        # Surfaced as 503: the request was fine, the dependency is not ready.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc

    return DatabaseHealthResponse(
        status="ok",
        database=database,
        schema_name=settings.POSTGRES_SCHEMA,
        server_version=server_version,
        alembic_revision=revision,
        latency_ms=latency_ms,
    )
