"""Single source of truth for which API paths belong to the OSS surface.

"Is this request OSS or BSS?" is answered here and nowhere else, so the dispatch
layer, the tests and the docs all agree. Prefixes are the v1 paths WITHOUT the
`/api/v1` mount prefix (the OSS microservice serves them without it).

Only device-derived reads are OSS. `/daily-data-points` is deliberately BSS
(mixed KPIs), and device WRITES (`/devices` POST/PATCH, `/limit-configs`) stay
in HMS until the write path is approved -- so the proxy below forwards GETs only.

`/incidents` and `/value-alerts` are BSS too. OSS has no incident table and no
threshold-breach table, so it could never answer them; in HMS they sit beside
the data that drives them -- incidents are acknowledged, assigned and resolved
by HMS staff (`PATCH /incidents`), and value alerts are breaches of the
HMS-owned `/limit-configs`.
"""

from __future__ import annotations

#: v1 path prefixes whose GET reads are served by the OSS microservices,
#: grouped by the OSS domain (one PM2 process each) that serves them.
OSS_DOMAIN_PREFIXES: dict[str, tuple[str, ...]] = {
    "device": ("/device-types", "/devices"),
    "telemetry": (
        "/device-params",
        "/device-stats",
        "/device-current-stats",
        "/other-device-readings",
    ),
    "alert": ("/alert-types", "/alerts"),
    "energy": ("/energy-stats",),
}

#: Every OSS read prefix, regardless of domain.
OSS_READ_PREFIXES: tuple[str, ...] = tuple(
    p for prefixes in OSS_DOMAIN_PREFIXES.values() for p in prefixes
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


def oss_domain_for(path: str) -> str | None:
    """The OSS domain serving `path` (with or without /api/v1), else None."""
    sub = oss_subpath(path)
    for domain, prefixes in OSS_DOMAIN_PREFIXES.items():
        if any(sub == p or sub.startswith(p + "/") for p in prefixes):
            return domain
    return None
