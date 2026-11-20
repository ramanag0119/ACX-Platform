"""Correlation IDs.

An inbound correlation id is accepted only if it matches a conservative
pattern; anything else is replaced. That stops a vendor-supplied value from
injecting newlines or markup into logs and API responses.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

_SAFE = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")

_current: ContextVar[str | None] = ContextVar("integration_correlation_id", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def accept_correlation_id(candidate: str | None) -> str:
    """Return `candidate` when safe, else a fresh id."""
    if candidate and _SAFE.fullmatch(candidate):
        return candidate
    return new_correlation_id()


def current_correlation_id() -> str | None:
    return _current.get()


class correlation_scope:  # noqa: N801 - used as a context manager
    """`with correlation_scope(cid): ...` binds `cid` for the current task."""

    def __init__(self, correlation_id: str) -> None:
        self._cid = correlation_id
        self._token = None

    def __enter__(self) -> str:
        self._token = _current.set(self._cid)
        return self._cid

    def __exit__(self, *exc) -> None:
        _current.reset(self._token)
