"""Dispatch layer: forward OSS read routes to the OSS microservice.

Mounted ONLY when `settings.OSS_ENABLED` is true, in place of the local device/
telemetry/alert/energy-stats read routers. Each proxy router keeps the SAME path
and the SAME `require_permission` gate as the local router it replaces, so HMS
still authenticates and authorises every caller BEFORE forwarding -- the
security boundary does not move. The request is then relayed to the OSS service
and its response (status + error envelope) is passed back verbatim.

`/devices` is the one composed route: OSS has no rooms, so HMS answers the
location filters (room / floor / building / facility) from its own
`room_device_map`, asks OSS for exactly those devices, and fills each device's
room, floor and building from the BSS before replying.

Only GET reads are proxied. The OSS database is read-only for HMS, so no write
is ever forwarded. Reads rely on OSS-side validation plus the RBAC gate here.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("hms.oss")

from app.api.deps import DbSession, require_permission
from app.api.errors import error_response
from app.core.config import settings
from app.core.oss_routes import oss_subpath
from app.schemas.common import DEFAULT_PAGE_SIZE
from app.services import device_type_map, oss_client, oss_fallback
from app.services import room_devices

#: Tells the caller which path answered. The body is identical either way, so
#: nothing in the frontend had to change to read this.
SOURCE_HEADER = "X-HMS-Data-Source"
LIVE, STORED = "live", "stored"


def _json(status: int, body: Any, source: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=body, headers={SOURCE_HEADER: source}
    )


#: OSS's own code for "this resource has no source in insp_iot".
NO_OSS_SOURCE = "oss_adapter_not_mapped"


def _has_no_oss_source(status: int, body: Any) -> bool:
    """True when OSS replied that it structurally cannot serve this resource."""
    return (
        status == 503
        and isinstance(body, dict)
        and body.get("error", {}).get("code") == NO_OSS_SOURCE
    )


def _stored(db, subpath: str, params: Any) -> JSONResponse:
    """Serve from BSS when OSS cannot answer. 503 if there is no stored form."""
    clean = subpath.rstrip("/")
    if not settings.OSS_FALLBACK_TO_STORED:
        # Strict mode: OSS data comes from OSS or not at all. Required before
        # the stored copies are dropped -- see config.OSS_FALLBACK_TO_STORED.
        return error_response(
            503,
            "OSS service is unavailable.",
            code="oss_unavailable",
        )
    if not oss_fallback.supports(clean):
        # Detail routes keep failing loudly: an OSS id does not identify a BSS
        # row, so there is nothing honest to return. See oss_fallback docstring.
        return error_response(
            503, "OSS service is unavailable.", code="oss_unavailable"
        )
    try:
        return _json(200, oss_fallback.serve(db, clean, list(params)), STORED)
    except oss_fallback.FallbackFilterError as exc:
        return error_response(422, str(exc), code="validation_error")
    except SQLAlchemyError:
        # The stored copy could not be read either -- e.g. `energy_stat` still
        # lacks the `device_id` column its model declares, because the Priority-4
        # migration branch has never been applied. Reported as its own code so
        # it is not mistaken for "OSS is down" or for a database outage.
        logger.exception("stored fallback failed for %s", clean)
        db.rollback()
        return error_response(
            503,
            "OSS service is unavailable and the stored copy could not be read.",
            code="stored_unavailable",
        )


def _relay(
    subpath: str, params: Any, db=None, stored_params: Any = None
) -> JSONResponse | tuple[int, Any]:
    """Live OSS read, falling back to stored BSS data when OSS is unreachable.

    Only a transport failure falls back. A 4xx/5xx the OSS service itself
    returned is passed through unchanged -- OSS answered, and masking its
    answer with stale rows would hide a real error.

    `stored_params` carries the caller's ORIGINAL query. `params` may have been
    rewritten for OSS (a BSS `device_type` id turned into a name), and feeding
    that rewrite to a BSS service would fail validation -- the stored path wants
    the ids it already understands.
    """
    fallback_params = params if stored_params is None else stored_params
    try:
        status, body = oss_client.forward("GET", subpath, params=params)
    except oss_client.OssUnavailable:
        if db is None:
            return error_response(
                503, "OSS service is unavailable.", code="oss_unavailable"
            )
        return _stored(db, subpath, fallback_params)

    if db is not None and settings.OSS_FALLBACK_TO_STORED and _has_no_oss_source(status, body):
        # OSS answered, and its answer is "I structurally have no source for
        # this" -- `/other-device-readings` has no third-party-meter table in
        # insp_iot at all. That is permanent, not transient, so the stored copy
        # is the best available data rather than stale data masking an outage.
        # Any OTHER 4xx/5xx still passes through untouched: a real error must
        # stay visible.
        stored = _stored(db, subpath, fallback_params)
        if stored.status_code == 200:
            return stored
    return status, body


def _translate_device_type(db, params) -> list[tuple[str, str]]:
    """Send OSS the device-type NAME where the caller sent a BSS id.

    The OSS ordinal is positional and is not comparable to `device_type.id`
    (BSS 2 = AirQ, OSS 2 = IntelliHub), so forwarding the number unchanged
    returns the wrong devices. The name is the only stable key; OSS matches it
    case-insensitively. A value that is not a known BSS id is forwarded
    untouched rather than dropped.
    """
    out: list[tuple[str, str]] = []
    for key, value in params:
        if key in ("device_type", "device_type_id"):
            name = device_type_map.name_for_bss_id(db, value)
            if name is not None:
                out.append((key, name))
                continue
        out.append((key, value))
    return out


def _to_bss_device_types(db, subpath: str, body):
    """Rewrite OSS device-type ids/names in a response to their BSS values."""
    if subpath.rstrip("/") == "/device-types":
        return device_type_map.device_types_as_bss(db, body)
    return device_type_map.apply_to_body(db, body)


def _build(prefix: str, module: str, permission: str = "read") -> APIRouter:
    router = APIRouter(
        prefix=prefix,
        tags=["oss-proxy"],
        dependencies=[Depends(require_permission(module, permission))],
    )

    def _proxy(request: Request, db: DbSession):
        # multi_items keeps repeated keys (?status=1&status=2); a dict
        # would silently keep only the last value.
        subpath = oss_subpath(request.url.path)
        original = request.query_params.multi_items()
        params = _translate_device_type(db, original)
        result = _relay(subpath, params, db, stored_params=original)
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        if status == 200:
            body = _to_bss_device_types(db, subpath, body)
        return _json(status, body, LIVE)

    # Root (list) and any sub-path (/{id}, /{id}/health, /summary, ...).
    router.add_api_route("", _proxy, methods=["GET"])
    router.add_api_route("/{rest:path}", _proxy, methods=["GET"])
    return router


# ---------------------------------------------------------------------------
# /devices: OSS device data + HMS room data
# ---------------------------------------------------------------------------

def _with_locations(db, devices: list[dict]) -> None:
    """Fill room / floor / building on OSS devices from `room_device_map`.
    Unmapped devices keep the nulls OSS sent: HMS does not know their room."""
    locations = room_devices.locations_for(db, [uuid.UUID(d["id"]) for d in devices])
    for device in devices:
        location = locations.get(uuid.UUID(device["id"]))
        if location:
            device.update({k: str(v) if isinstance(v, uuid.UUID) else v
                           for k, v in location.items()})


def _build_devices(module: str) -> APIRouter:
    router = APIRouter(
        prefix="/devices",
        tags=["oss-proxy"],
        dependencies=[Depends(require_permission(module, "read"))],
    )

    def list_devices(request: Request, db: DbSession):
        params = request.query_params
        try:
            location = {
                key: uuid.UUID(params[key])
                for key in room_devices.LOCATION_FILTERS if params.get(key)
            }
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", DEFAULT_PAGE_SIZE))
        except ValueError:
            return error_response(
                422, "Location filters must be UUIDs; page and page_size integers.",
                code="validation_error",
            )
        without_location = [
            (k, v) for k, v in params.multi_items()
            if k not in room_devices.LOCATION_FILTERS
        ]
        forwarded = _translate_device_type(db, without_location)
        if location:
            device_ids = room_devices.device_ids_at(db, **location)
            if not device_ids:
                # Nothing installed there; OSS would only be asked for nothing.
                return {"items": [], "page": page, "page_size": page_size, "total": 0}
            forwarded.append(("device_ids", ",".join(str(i) for i in device_ids)))

        # On the stored path the caller's ORIGINAL query is used, location
        # filters included: BSS `device` carries `amenity_id` / `facility_id`
        # itself, so the room filter is answered directly instead of through
        # `room_device_map` + `device_ids`, which only exist for OSS.
        result = _relay(
            "/devices", forwarded, db, stored_params=params.multi_items()
        )
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        if status == 200:
            _with_locations(db, body["items"])
            body = device_type_map.apply_to_body(db, body)
        return _json(status, body, LIVE)

    def device_sub_path(rest: str, request: Request, db: DbSession):
        result = _relay(f"/devices/{rest}", request.query_params.multi_items())
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        if status == 200 and "/" not in rest.strip("/"):
            _with_locations(db, [body])  # device detail
        if status == 200:
            body = device_type_map.apply_to_body(db, body)
        return _json(status, body, LIVE)

    router.add_api_route("", list_devices, methods=["GET"])
    router.add_api_route("/{rest:path}", device_sub_path, methods=["GET"])
    return router


# caleido_network-gated device/telemetry/alert reads.
_NETWORK = "caleido_network"
oss_proxy_routers: list[APIRouter] = [
    _build("/device-types", _NETWORK),
    _build_devices(_NETWORK),
    _build("/device-params", _NETWORK),
    _build("/device-stats", _NETWORK),
    _build("/device-current-stats", _NETWORK),
    _build("/other-device-readings", _NETWORK),
    _build("/alert-types", _NETWORK),
    _build("/alerts", _NETWORK),
    # energy-stats is reports-gated, matching the local energy router.
    _build("/energy-stats", "reports"),
]
