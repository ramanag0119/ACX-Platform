"""Centralised error handling for the OSS service.

Uses the SAME envelope the HMS backend produces, so a response forwarded
through HMS to the frontend has one consistent shape:

    {"error": {"code": "not_found", "message": "...", "detail": ...}}

Unexpected exceptions are logged server-side but never leak their type,
message or traceback to the caller.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.base import AdapterNotMapped
from app.db.session import OssDbNotConfigured

logger = logging.getLogger("oss.api")

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
    @app.exception_handler(OssDbNotConfigured)
    async def _not_configured(request: Request, exc: OssDbNotConfigured):
        # The service is up but has no OSS database wired in yet. This is the
        # scaffold state; it is a 503 (dependency not ready), not a 500.
        logger.warning("OSS data route hit before the OSS database was configured")
        return error_response(
            503,
            "OSS data layer is not configured yet (OSS_DATABASE_URL unset).",
            code="oss_not_configured",
        )

    @app.exception_handler(AdapterNotMapped)
    async def _not_mapped(request: Request, exc: AdapterNotMapped):
        # The OSS schema has not been mapped to the contract yet (pre-discovery).
        # 503 (dependency not ready) with a precise, non-fabricated message.
        logger.warning("OSS adapter not mapped: %s", exc.resource)
        return error_response(
            503,
            str(exc),
            code="oss_adapter_not_mapped",
            detail={"resource": exc.resource},
        )

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
        logger.warning("rejected value on %s %s", request.method, request.url.path)
        return error_response(
            422,
            "A query value is not valid for its column.",
            detail=[{"loc": ["query"], "msg": "invalid value", "type": "value_error"}],
        )

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(request: Request, exc: SQLAlchemyError):
        logger.exception("OSS database error on %s %s", request.method, request.url.path)
        return error_response(503, "OSS database is unavailable.")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error.")
