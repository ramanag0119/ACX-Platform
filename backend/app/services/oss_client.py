"""Client for the OSS (device/operations) microservice.

HMS forwards OSS-surfaced reads here and composes the few BSS views that need a
device figure (occupancy's per-room device_count). This is the ONLY place that
knows how to reach the OSS service, so timeouts, the optional service token and
the failure policy live in one spot.

FAILURE POLICY (deliberate):
  * Forwarded routes -- raise `OssUnavailable`; the caller returns a clear 503.
  * Composition (device_count) -- return None, meaning "unknown". It is NEVER
    coerced to 0: an unreachable OSS must not look like a room with no devices.

SECURITY: no inter-service auth by default (trusted-LAN PoC). If
`settings.OSS_SERVICE_TOKEN` is set, it is sent as `X-OSS-Service-Token` so an
operator can turn on an equivalent control without code changes. The token is
never logged.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("hms.oss")


class OssUnavailable(RuntimeError):
    """The OSS microservice could not be reached or timed out."""


def _headers() -> dict[str, str]:
    token = getattr(settings, "OSS_SERVICE_TOKEN", None)
    return {"X-OSS-Service-Token": token} if token else {}


def forward(
    method: str,
    subpath: str,
    *,
    params: Any = None,
    json: Any = None,
) -> tuple[int, Any]:
    """Forward a request to the OSS service. Returns (status_code, parsed_body).

    Raises `OssUnavailable` on transport error/timeout (never on a 4xx/5xx the
    OSS service itself returned -- those are passed through so HMS relays the
    real status and error envelope).
    """
    url = f"{settings.OSS_SERVICE_URL.rstrip('/')}{subpath}"
    try:
        with httpx.Client(timeout=settings.OSS_TIMEOUT_SECONDS) as client:
            resp = client.request(method, url, params=params, json=json, headers=_headers())
    except httpx.HTTPError as exc:
        logger.warning("OSS service unreachable for %s %s: %s", method, subpath, exc)
        raise OssUnavailable("OSS service is unreachable.") from exc
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body


def device_count(amenity_id) -> int | None:
    """Devices installed in a room, read from OSS. None = UNKNOWN (never 0).

    Uses the OSS devices list `total` for the amenity. Any failure -- transport
    error, OSS 5xx, adapter-not-mapped, or a missing `total` -- yields None so
    the occupancy view can render "unknown" rather than a fabricated zero.
    """
    try:
        status, body = forward(
            "GET",
            "/devices",
            params={"amenity_id": str(amenity_id), "page": 1, "page_size": 1},
        )
    except OssUnavailable:
        return None
    if status != 200 or not isinstance(body, dict):
        return None
    total = body.get("total")
    return total if isinstance(total, int) else None
