"""Optional service-to-service authentication for OSS data routes.

Default: OFF. The OSS service is a trusted-LAN PoC with no inter-service auth,
so when `OSS_SERVICE_TOKEN` is unset this dependency is a no-op.

When an operator sets `OSS_SERVICE_TOKEN` (the formally-approved "equivalent
control"), every data route requires a matching `X-OSS-Service-Token` header.
HMS's `oss_client` sends it automatically when its own `OSS_SERVICE_TOKEN` is
configured. The token value is never logged.

Health endpoints are intentionally NOT gated, so liveness/readiness probes work
regardless of the token setting.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_service_token(x_oss_service_token: str | None = Header(default=None)) -> None:
    expected = settings.OSS_SERVICE_TOKEN
    if not expected:
        return  # PoC / trusted-LAN: no control configured.
    if not x_oss_service_token or not hmac.compare_digest(x_oss_service_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing OSS service token.",
        )
