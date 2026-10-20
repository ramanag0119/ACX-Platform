"""Dispatch layer: forward OSS read routes to the OSS microservice.

Mounted ONLY when `settings.OSS_ENABLED` is true, in place of the local device/
telemetry/alert/energy-stats read routers. Each proxy router keeps the SAME path
and the SAME `require_permission` gate as the local router it replaces, so HMS
still authenticates and authorises every caller BEFORE forwarding -- the
security boundary does not move. The request is then relayed to the OSS service
and its response (status + error envelope) is passed back verbatim.

Only GET reads are proxied. Device writes stay in HMS until the write path is
approved (see docs). Full HMS-side Pydantic body validation is reintroduced per
endpoint when the write path is built; reads rely on OSS-side validation plus
the RBAC gate here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.api.errors import error_response
from app.core.oss_routes import oss_subpath
from app.services import oss_client


def _build(prefix: str, module: str, permission: str = "read") -> APIRouter:
    router = APIRouter(
        prefix=prefix,
        tags=["oss-proxy"],
        dependencies=[Depends(require_permission(module, permission))],
    )

    def _proxy(request: Request):
        subpath = oss_subpath(request.url.path)
        try:
            status, body = oss_client.forward(
                "GET", subpath, params=dict(request.query_params)
            )
        except oss_client.OssUnavailable:
            return error_response(
                503, "OSS service is unavailable.", code="oss_unavailable"
            )
        return JSONResponse(status_code=status, content=body)

    # Root (list) and any sub-path (/{id}, /{id}/health, /summary, ...).
    router.add_api_route("", _proxy, methods=["GET"])
    router.add_api_route("/{rest:path}", _proxy, methods=["GET"])
    return router


# caleido_network-gated device/telemetry/alert reads.
_NETWORK = "caleido_network"
oss_proxy_routers: list[APIRouter] = [
    _build("/device-types", _NETWORK),
    _build("/devices", _NETWORK),
    _build("/device-params", _NETWORK),
    _build("/device-stats", _NETWORK),
    _build("/device-current-stats", _NETWORK),
    _build("/other-device-readings", _NETWORK),
    _build("/alert-types", _NETWORK),
    _build("/alerts", _NETWORK),
    _build("/incidents", _NETWORK),
    _build("/value-alerts", _NETWORK),
    # energy-stats is reports-gated, matching the local energy router.
    _build("/energy-stats", "reports"),
]
