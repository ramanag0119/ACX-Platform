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
room, floor and building from hms_db before replying.

Only GET reads are proxied. The OSS database is read-only for HMS, so no write
is ever forwarded. Reads rely on OSS-side validation plus the RBAC gate here.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import DbSession, require_permission
from app.api.errors import error_response
from app.core.oss_routes import oss_subpath
from app.schemas.common import DEFAULT_PAGE_SIZE
from app.services import oss_client
from app.services import room_devices


def _relay(subpath: str, params: Any) -> JSONResponse | tuple[int, Any]:
    try:
        return oss_client.forward("GET", subpath, params=params)
    except oss_client.OssUnavailable:
        return error_response(503, "OSS service is unavailable.", code="oss_unavailable")


def _build(prefix: str, module: str, permission: str = "read") -> APIRouter:
    router = APIRouter(
        prefix=prefix,
        tags=["oss-proxy"],
        dependencies=[Depends(require_permission(module, permission))],
    )

    def _proxy(request: Request):
        # multi_items keeps repeated keys (?status=1&status=2); a dict
        # would silently keep only the last value.
        result = _relay(oss_subpath(request.url.path), request.query_params.multi_items())
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        return JSONResponse(status_code=status, content=body)

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
        forwarded = [
            (k, v) for k, v in params.multi_items()
            if k not in room_devices.LOCATION_FILTERS
        ]
        if location:
            device_ids = room_devices.device_ids_at(db, **location)
            if not device_ids:
                # Nothing installed there; OSS would only be asked for nothing.
                return {"items": [], "page": page, "page_size": page_size, "total": 0}
            forwarded.append(("device_ids", ",".join(str(i) for i in device_ids)))

        result = _relay("/devices", forwarded)
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        if status == 200:
            _with_locations(db, body["items"])
        return JSONResponse(status_code=status, content=body)

    def device_sub_path(rest: str, request: Request, db: DbSession):
        result = _relay(f"/devices/{rest}", request.query_params.multi_items())
        if isinstance(result, JSONResponse):
            return result
        status, body = result
        if status == 200 and "/" not in rest.strip("/"):
            _with_locations(db, [body])  # device detail
        return JSONResponse(status_code=status, content=body)

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
