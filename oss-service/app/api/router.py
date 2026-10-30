"""Aggregate router for the OSS service.

Device, telemetry, alert and energy read routers. These are the OSS surface the
HMS backend forwards to; they carry NO `require_permission` gate -- HMS has
already authenticated and authorised the caller before forwarding (trusted-LAN
PoC). Paths mirror the HMS contract exactly (minus the `/api/v1` prefix, which
HMS adds) so the forwarded response is byte-identical to today's.

Each domain can run as its own process (one PM2 app per domain, see
ecosystem.config.js): `settings.OSS_DOMAINS` picks which domains a process
serves. The default serves all four, as a single service.
"""

from fastapi import APIRouter

from app.api import alerts, devices, energy, telemetry

DOMAIN_ROUTERS: dict[str, list[APIRouter]] = {
    # Devices + health + types
    "device": [
        devices.device_types_router,
        devices.devices_router,
    ],
    # Telemetry (EAV: params + readings + snapshot + third-party meters)
    "telemetry": [
        telemetry.device_params_router,
        telemetry.device_stats_router,
        telemetry.device_current_stats_router,
        telemetry.other_device_readings_router,
    ],
    # Alerts (incidents and value alerts are HMS data; OSS has no table for them)
    "alert": [
        alerts.alert_types_router,
        alerts.alerts_router,
    ],
    # Energy (device-derived only; /daily-data-points stays in HMS/BSS)
    "energy": [
        energy.energy_stats_router,
    ],
}


def build_api_router(domains: list[str]) -> APIRouter:
    """Router serving only `domains`; an unknown domain fails at startup."""
    unknown = sorted(set(domains) - DOMAIN_ROUTERS.keys())
    if unknown:
        raise ValueError(
            f"Unknown OSS_DOMAINS {unknown}; expected some of {sorted(DOMAIN_ROUTERS)}."
        )
    router = APIRouter()
    for domain in domains:
        for domain_router in DOMAIN_ROUTERS[domain]:
            router.include_router(domain_router)
    return router


api_router = build_api_router(list(DOMAIN_ROUTERS))
