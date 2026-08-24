"""Centralised error handling.

Every error the API returns uses one envelope, so a client never has to guess
which shape it is parsing:

    {"error": {"code": "not_found", "message": "...", "detail": ...}}

Unexpected exceptions are logged in full server-side but never leak their type,
message or traceback to the client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("hms.api")

#: HTTP status -> stable machine-readable code.
_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(
    status_code: int, message: str, *, code: str | None = None, detail=None
) -> JSONResponse:
    """Build the single error envelope used by every handler."""
    body: dict = {
        "error": {
            "code": code or _STATUS_CODES.get(status_code, "error"),
            "message": message,
        }
    }
    if detail is not None:
        body["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


def install_exception_handlers(app: FastAPI) -> None:
    """Register the handlers on the application."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        detail = None if isinstance(exc.detail, str) else exc.detail
        return error_response(exc.status_code, message, detail=detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return error_response(
            422,
            "Request validation failed.",
            detail=[
                {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
                for e in exc.errors()
            ],
        )

    @app.exception_handler(DataError)
    async def _bad_value(request: Request, exc: DataError):
        # PostgreSQL rejected a VALUE, not the connection: text that is not a
        # label of an enum type, a malformed timestamp, a number out of range.
        # That is a bad request, so it must not be reported as a database
        # outage -- a client shown 503 retries a request that can never work.
        # Endpoints declare their enum filters as Literal so this is a
        # backstop; it is what catches any filter that does not.
        logger.warning(
            "rejected value on %s %s: %s",
            request.method, request.url.path, exc.orig,
        )
        return error_response(
            422,
            "A query value is not valid for its column.",
            detail=[{"loc": ["query"], "msg": "invalid value", "type": "value_error"}],
        )

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(request: Request, exc: SQLAlchemyError):
        # The database is the dependency most likely to be down, so it gets a
        # 503 rather than a 500: the request is fine, the backend is not ready.
        logger.exception("database error on %s %s", request.method, request.url.path)
        return error_response(503, "Database is unavailable.")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error.")
