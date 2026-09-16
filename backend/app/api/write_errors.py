"""Turn write-service domain errors into the standard HTTP envelope.

Services raise `NotFound` / `Conflict` / `Invalid`; endpoints stay free of
try/except by depending on this one handler. The envelope is the same one
`app/api/errors.py` has produced since Phase 2.1 -- no second error format.
"""

from __future__ import annotations

from fastapi import FastAPI, Request

from app.api.errors import error_response
from app.services.writes import Conflict, Invalid, NotFound, WriteError

_STATUS = {NotFound: 404, Conflict: 409, Invalid: 422}


def install_write_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(WriteError)
    async def _write_error(request: Request, exc: WriteError):  # noqa: ARG001
        status_code = next(
            (code for cls, code in _STATUS.items() if isinstance(exc, cls)), 400
        )
        return error_response(status_code, exc.message, detail=exc.detail)
