"""Response models for the OSS system/health endpoints.

Copied from the HMS backend health contract so operators read one shape.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    """`GET /health` — the process is up. Does not touch the database."""

    status: str = Field(examples=["ok"])
    app: str = Field(examples=["HMS OSS Service"])
    env: str = Field(examples=["development"])
    version: str = Field(examples=["0.1.0"])


class DatabaseHealthResponse(BaseModel):
    """`GET /health/db` — every field is read live from the OSS PostgreSQL."""

    status: str = Field(examples=["ok"])
    database: str = Field(examples=["inspironics"], description="SELECT current_database()")
    schema_name: str = Field(examples=["public"])
    server_version: str = Field(examples=["16.12"], description="PostgreSQL version")
    alembic_revision: str | None = Field(
        default=None, description="OSS DB is externally owned; not Alembic-managed here"
    )
    latency_ms: float = Field(examples=[1.83], description="Round-trip time of the probe query")


class ErrorBody(BaseModel):
    code: str = Field(examples=["service_unavailable"])
    message: str = Field(examples=["OSS database is unavailable."])
    detail: object | None = None


class ErrorResponse(BaseModel):
    """The single error envelope used by every endpoint."""

    error: ErrorBody
