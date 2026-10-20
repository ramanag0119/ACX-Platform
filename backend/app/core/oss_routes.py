"""Single source of truth for which API paths belong to the OSS surface.

"Is this request OSS or BSS?" is answered here and nowhere else, so the dispatch
layer, the tests and the docs all agree. Prefixes are the v1 paths WITHOUT the
`/api/v1` mount prefix (the OSS microservice serves them without it).

Only device-derived reads are OSS. `/daily-data-points` is deliberately BSS
(mixed KPIs), and device WRITES (`/devices` POST/PATCH, `/incidents` PATCH,
`/limit-configs`) stay in HMS until the write path is approved -- so the proxy
below forwards GETs only.
"""

from __future__ import annotations

#: v1 path prefixes whose GET reads are served by the OSS microservice.
OSS_READ_PREFIXES: tuple[str, ...] = (
    "/device-types",
    "/devices",
    "/device-params",
    "/device-stats",
    "/device-current-stats",
    "/other-device-readings",
    "/alert-types",
    "/alerts",
    "/incidents",
    "/value-alerts",
    "/energy-stats",
)


def oss_subpath(path: str) -> str:
    """Strip the `/api/v1` mount prefix, giving the path the OSS service serves."""
    for prefix in ("/api/v1", ""):
        if prefix and path.startswith(prefix):
            return path[len(prefix):] or "/"
    return path


def is_oss_read_path(path: str) -> bool:
    """True when `path` (with or without /api/v1) is an OSS read prefix."""
    sub = oss_subpath(path)
    return any(sub == p or sub.startswith(p + "/") for p in OSS_READ_PREFIXES)
