"""Response models for the system/health endpoints.

Declaring them explicitly is what gives Swagger real schemas instead of a bare
`{}` for these routes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """`GET /health` — the process is up. Does not touch the database."""

    status: str = Field(examples=["ok"])
    app: str = Field(examples=["HMS Backend"])
    env: str = Field(examples=["development"])
    version: str = Field(examples=["0.2.1"])


class DatabaseHealthResponse(BaseModel):
    """`GET /api/v1/health/db` — every field is read live from PostgreSQL."""

    status: str = Field(examples=["ok"])
    database: str = Field(examples=["hms_db"], description="SELECT current_database()")
    schema_name: str = Field(examples=["public"])
    server_version: str = Field(examples=["16.12"], description="PostgreSQL version")
    alembic_revision: str | None = Field(
        default=None, examples=["0e2687233b59"], description="Applied migration head"
    )
    latency_ms: float = Field(
        examples=[1.83], description="Round-trip time of the probe query"
    )


class ErrorBody(BaseModel):
    code: str = Field(examples=["service_unavailable"])
    message: str = Field(examples=["Database is unavailable."])
    detail: object | None = None


class ErrorResponse(BaseModel):
    """The single error envelope used by every endpoint."""

    error: ErrorBody
