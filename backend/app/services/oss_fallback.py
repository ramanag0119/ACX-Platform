"""Serve OSS-surfaced reads from stored BSS data when OSS is unreachable.

WHY
---
With `OSS_ENABLED=true` the device / telemetry / alert / energy reads are
forwarded to the OSS microservices. Those run as separate PM2 processes against
FleetXplorer, so they can legitimately be down -- a restart, a network blip, a
machine that has not come up yet -- while HMS itself is perfectly healthy.

Previously any such failure produced `503 oss_unavailable` and the screen went
blank. HMS still holds the last data it was serving before the cutover, so the
useful behaviour is: show LIVE data when OSS answers, fall back to STORED data
when it does not, and resume live automatically the moment OSS returns. There
is no cached state and no retry timer -- each request simply tries live first,
so recovery needs no intervention.

HOW
---
Nothing is reimplemented. Each OSS prefix is mapped to the SAME service
function the local BSS router already calls, and the SAME response schema, so a
stored response is shape-identical to a live one. Query filters are coerced
with the service function's own type annotations, so `?device_type=2` means
exactly what it means on the local route.

Responses carry `X-HMS-Data-Source: live | stored` so a caller (or an operator
reading the network tab) can tell which path answered. The body is unchanged,
so no frontend type or table had to change.

DELIBERATELY LIST-ONLY
----------------------
Detail routes (`/devices/{id}`, `/alerts/{id}`, ...) are NOT backed by this
fallback, and that is correctness rather than an omission: an id minted by OSS
identifies a row in `insp_iot` and does not exist in the BSS MySQL, so a
"stored" lookup by that id could only ever 404 -- or, worse, collide with an
unrelated BSS row. Detail routes keep returning the explicit 503 while OSS is
down.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, get_type_hints

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.schemas.alert import AlertRead, AlertTypeRead
from app.schemas.common import DEFAULT_PAGE_SIZE, Page
from app.schemas.device import DeviceRead, DeviceTypeRead
from app.schemas.energy import EnergyStatRead
from app.schemas.telemetry import (
    DeviceCurrentStatRead,
    DeviceParamRead,
    DeviceStatRead,
    OtherDeviceReadingRead,
)
from app.services import alert as alert_svc
from app.services import device as device_svc
from app.services import energy as energy_svc
from app.services import telemetry as telemetry_svc

#: Query keys that are route parameters, never service filters.
_PAGINATION = {"page", "page_size"}


class FallbackFilterError(ValueError):
    """A query value is not valid for the stored-data service signature."""


@dataclass(frozen=True)
class _Stored:
    """How one OSS prefix is served from BSS."""

    service: Callable[..., tuple[list[Any], int]]
    schema: type


#: OSS read prefix -> the local service + schema already used by its BSS route.
REGISTRY: dict[str, _Stored] = {
    "/device-types": _Stored(device_svc.list_device_types, DeviceTypeRead),
    "/devices": _Stored(device_svc.list_devices, DeviceRead),
    "/device-params": _Stored(telemetry_svc.list_device_params, DeviceParamRead),
    "/device-stats": _Stored(telemetry_svc.list_device_stats, DeviceStatRead),
    "/device-current-stats": _Stored(
        telemetry_svc.list_device_current_stats, DeviceCurrentStatRead
    ),
    "/other-device-readings": _Stored(
        telemetry_svc.list_other_device_readings, OtherDeviceReadingRead
    ),
    "/alert-types": _Stored(alert_svc.list_alert_types, AlertTypeRead),
    "/alerts": _Stored(alert_svc.list_alerts, AlertRead),
    "/energy-stats": _Stored(energy_svc.list_energy_stats, EnergyStatRead),
}


def supports(subpath: str) -> bool:
    """True when `subpath` is a list root this module can serve from BSS."""
    return subpath.rstrip("/") in REGISTRY


@lru_cache(maxsize=None)
def _hints(service: Callable) -> dict[str, Any]:
    """Resolved type hints for a service function.

    `get_type_hints` rather than `signature().annotation`: every service module
    uses `from __future__ import annotations`, so the raw annotations are
    STRINGS ("uuid.UUID | None") that no validator can use. Resolving them is
    what makes `?amenity_id=<uuid>` reach the query as a real UUID instead of
    silently failing to match. Cached because resolution is not free and the
    set of services is fixed.
    """
    try:
        return get_type_hints(service)
    except Exception:  # pragma: no cover - a hint we cannot resolve is not fatal
        return {}


def _coerce(service: Callable, params: list[tuple[str, str]]) -> dict[str, Any]:
    """Filters the service accepts, converted using its own annotations.

    A key the service does not declare is dropped: OSS-only filters such as
    `device_ids` or `q` have no BSS equivalent and must not be forwarded.
    """
    accepted = inspect.signature(service).parameters
    hints = _hints(service)
    out: dict[str, Any] = {}

    for key, raw in params:
        if key in _PAGINATION or key not in accepted:
            continue
        annotation = hints.get(key)
        if annotation is None:
            out[key] = raw
            continue
        try:
            out[key] = TypeAdapter(annotation).validate_python(raw)
        except ValidationError as exc:
            raise FallbackFilterError(
                f"{key}={raw!r} is not valid for the stored-data query"
            ) from exc
    return out


def _int_param(params: list[tuple[str, str]], key: str, default: int) -> int:
    for k, v in params:
        if k == key:
            try:
                return max(1, int(v))
            except (TypeError, ValueError):
                return default
    return default


def serve(db: Session, subpath: str, params: list[tuple[str, str]]) -> dict:
    """Serve `subpath` from stored BSS data. Returns the JSON-ready page body.

    Raises `KeyError` if the prefix has no stored equivalent (guard with
    `supports()`), or `FallbackFilterError` for an unusable filter value.
    """
    entry = REGISTRY[subpath.rstrip("/")]
    page = _int_param(params, "page", 1)
    page_size = _int_param(params, "page_size", DEFAULT_PAGE_SIZE)

    rows, total = entry.service(
        db, page=page, page_size=page_size, **_coerce(entry.service, params)
    )
    body = Page[entry.schema](
        items=[entry.schema.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
    return body.model_dump(mode="json")
