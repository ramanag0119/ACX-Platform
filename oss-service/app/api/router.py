"""Aggregate router for the OSS service.

Device, telemetry, alert and energy read routers. These are the OSS surface the
HMS backend forwards to; they carry NO `require_permission` gate -- HMS has
already authenticated and authorised the caller before forwarding (trusted-LAN
PoC). Paths mirror the HMS contract exactly (minus the `/api/v1` prefix, which
HMS adds) so the forwarded response is byte-identical to today's.
"""

from fastapi import APIRouter

from app.api import alerts, devices, energy, telemetry

api_router = APIRouter()

# Devices + health + types
api_router.include_router(devices.device_types_router)
api_router.include_router(devices.devices_router)

# Telemetry (EAV: params + readings + snapshot + third-party meters)
api_router.include_router(telemetry.device_params_router)
api_router.include_router(telemetry.device_stats_router)
api_router.include_router(telemetry.device_current_stats_router)
api_router.include_router(telemetry.other_device_readings_router)

# Alerts, incidents, value alerts
api_router.include_router(alerts.alert_types_router)
api_router.include_router(alerts.alerts_router)
api_router.include_router(alerts.incidents_router)
api_router.include_router(alerts.value_alerts_router)

# Energy (device-derived only; /daily-data-points stays in HMS/BSS)
api_router.include_router(energy.energy_stats_router)
