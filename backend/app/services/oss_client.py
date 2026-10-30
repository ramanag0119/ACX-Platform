"""Client for the OSS (device/operations) microservice.

HMS forwards OSS-surfaced reads here. This is the ONLY place that knows how to
reach the OSS service, so timeouts, the optional service token and the failure
policy live in one spot.

FAILURE POLICY: a transport error or timeout raises `OssUnavailable`; the
caller returns a clear 503. A 4xx/5xx from OSS itself is passed through.

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

