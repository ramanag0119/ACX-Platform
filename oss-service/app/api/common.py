"""Helpers shared by the OSS read routers.

Every list route takes the same shape -- pass the caller's query string through
to the adapter minus the pagination keys -- and every detail route turns an
adapter's `None` into a 404. Both lived as near-identical private copies in
`devices`, `telemetry`, `alerts` and `energy`; they are defined once here.

`query_filters` is a dependency *factory* rather than a plain function called
from the handler body. That matters: FastAPI resolves a route's dependencies in
the order they appear in its signature, so declaring the filters dependency
before `db` makes a malformed query value fail validation (422) before
`get_db` can raise `OssDbNotConfigured` (503). Parsing inside the handler body
gave the opposite -- and wrong -- order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import HTTPException, Request, status

#: Query keys that are route parameters rather than adapter filters.
PAGINATION_KEYS = ("page", "page_size")


def query_filters(drop: Iterable[str] = PAGINATION_KEYS) -> Callable[[Request], dict]:
    """Dependency yielding the pass-through query filters, minus `drop`."""
    excluded = set(drop)

    def _dependency(request: Request) -> dict:
        return {k: v for k, v in request.query_params.items() if k not in excluded}

    return _dependency


def require_found(obj, what: str = "Resource"):
    """404 when the adapter found nothing, instead of failing response validation."""
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found.")
    return obj
