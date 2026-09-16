"""HMS backend application entry point.

Phase 2.1 scope is the FastAPI foundation only: app initialisation, CORS,
centralised error handling, OpenAPI, and the two health endpoints. NO business
APIs exist yet -- facility, room, user, device, alert and dashboard routes all
come in a later phase.

    React frontend -> FastAPI -> SQLAlchemy -> PostgreSQL hms_db

Run locally:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_exception_handlers
from app.api.write_errors import install_write_error_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.schemas.health import LivenessResponse

API_VERSION = "0.3.0"


def create_app() -> FastAPI:
    """Build the application.

    A factory rather than a module-level singleton so tests can construct an
    isolated instance without importing global state.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=API_VERSION,
        description=(
            "HMS backend for IKANOS HMS Web: read APIs for the seeded "
            "PostgreSQL data plus the schema-supported write workflows."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Browser access from the local Vite dev server. Origins come from
    # settings so they can be overridden per environment via .env.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)
    # Phase 3.0 write services raise domain errors; map them to the same envelope.
    install_write_error_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get(
        "/health",
        response_model=LivenessResponse,
        tags=["health"],
        summary="Liveness",
    )
    def health() -> LivenessResponse:
        """Is the process up? Deliberately does not touch the database, so it
        stays meaningful when PostgreSQL is the thing that is down."""
        return LivenessResponse(
            status="ok",
            app=settings.APP_NAME,
            env=settings.APP_ENV,
            version=API_VERSION,
        )

    return app


app = create_app()
