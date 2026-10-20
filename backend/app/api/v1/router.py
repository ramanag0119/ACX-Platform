"""Aggregate router for API version 1.

Every v1 endpoint module is included here, and `app.main` mounts this single
router under `settings.API_V1_PREFIX`. Adding a business module in a later
phase means one import and one `include_router` line -- nothing in `main.py`
has to change.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    access, access_write, alerts, auth, devices, devices_write, energy,
    facilities, facility_write, health, job_orders, maintenance, notifications,
    occupancy, oss_proxy, reports, services, services_write, stays, stays_write,
    telemetry,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)

# Phase 2.4 -- HMS Web authentication (Admin + Manager only).
api_router.include_router(auth.router)

# Phase 2.2 -- facility and property hierarchy (read-only).
api_router.include_router(facilities.facilities_router)
api_router.include_router(facilities.properties_router)
api_router.include_router(facilities.buildings_router)
api_router.include_router(facilities.floors_router)
api_router.include_router(facilities.rooms_router)
api_router.include_router(facilities.countries_router)

# Phase 2.3 -- users, roles, modules and permissions (read-only).
api_router.include_router(access.users_router)
api_router.include_router(access.roles_router)
api_router.include_router(access.modules_router)
api_router.include_router(access.permissions_router)

# Phase 3.0 -- user, role, permission, department and job-function writes.
api_router.include_router(access_write.users_write_router)
api_router.include_router(access_write.roles_write_router)
api_router.include_router(access_write.departments_router)
api_router.include_router(access_write.job_functions_router)

# Phase 2.5 -- service catalogue and service requests (read-only).
api_router.include_router(services.service_types_router)
api_router.include_router(services.service_statuses_router)
api_router.include_router(services.service_categories_router)
api_router.include_router(services.service_items_router)
api_router.include_router(services.service_requests_router)

# Phase 3.0 -- service request and catalogue writes.
api_router.include_router(services_write.service_requests_write_router)
api_router.include_router(services_write.service_categories_write_router)
api_router.include_router(services_write.service_items_write_router)

# Services Planning -- maintenance_request + recurrence / amenity / assignee.
api_router.include_router(maintenance.maintenance_requests_router)
api_router.include_router(maintenance.maintenance_requests_write_router)

# Job Order Management -- job_order + job_order_amenity / job_order_device.
api_router.include_router(job_orders.job_orders_router)
api_router.include_router(job_orders.job_orders_write_router)

# Reporting -- read-only projections over the modules above, plus export.
api_router.include_router(reports.reports_router)

# Phase 3.0 -- stay lifecycle, allocation, occupants and room state writes.
api_router.include_router(stays_write.stays_write_router)
api_router.include_router(stays_write.allocations_router)
api_router.include_router(stays_write.occupants_router)
api_router.include_router(stays_write.occupancy_write_router)

# Phase 2.6 -- device inventory, types and health (read-only).
# OSS dispatch: when OSS_ENABLED these reads are forwarded to the OSS
# microservice by `oss_proxy` instead (see the block at the end of this file).
if not settings.OSS_ENABLED:
    api_router.include_router(devices.device_types_router)
    api_router.include_router(devices.devices_router)

# Phase 3.0 -- device, incident and limit-config writes.
api_router.include_router(devices_write.devices_write_router)
api_router.include_router(devices_write.incidents_write_router)
api_router.include_router(devices_write.limit_configs_router)

# Phase 3.0 -- facility, room catalogue and marketing (reads + writes).
api_router.include_router(facility_write.facilities_write_router)
api_router.include_router(facility_write.rooms_write_router)
api_router.include_router(facility_write.amenity_types_router)
api_router.include_router(facility_write.packages_router)
api_router.include_router(facility_write.features_router)
api_router.include_router(facility_write.offers_router)
api_router.include_router(facility_write.events_router)
api_router.include_router(facility_write.holidays_router)

# Phase 2.7 -- alerts, incidents and value alerts (read-only).
# OSS dispatch: forwarded to the OSS microservice when OSS_ENABLED.
if not settings.OSS_ENABLED:
    api_router.include_router(alerts.alert_types_router)
    api_router.include_router(alerts.alerts_router)
    api_router.include_router(alerts.incidents_router)
    api_router.include_router(alerts.value_alerts_router)

# Phase 2.7 -- notification dispatch and the in-app activity feed (read-only).
api_router.include_router(notifications.notification_templates_router)
api_router.include_router(notifications.notifications_router)
api_router.include_router(notifications.activities_router)

# Phase 2.8 -- stays (reservations), invoices and room occupancy (read-only).
api_router.include_router(stays.stays_router)
api_router.include_router(stays.invoices_router)
api_router.include_router(occupancy.occupancy_router)
api_router.include_router(occupancy.amenity_statuses_router)
api_router.include_router(occupancy.amenity_conditions_router)

# Phase 2.9 -- device telemetry (read-only).
# OSS dispatch: forwarded to the OSS microservice when OSS_ENABLED.
if not settings.OSS_ENABLED:
    api_router.include_router(telemetry.device_params_router)
    api_router.include_router(telemetry.device_stats_router)
    api_router.include_router(telemetry.device_current_stats_router)
    api_router.include_router(telemetry.other_device_readings_router)

# Phase 2.9 -- energy statistics and daily KPIs (read-only).
# energy-stats is device-derived (OSS); daily-data-points is mixed KPIs and
# ALWAYS stays BSS (served locally regardless of OSS_ENABLED).
if not settings.OSS_ENABLED:
    api_router.include_router(energy.energy_stats_router)
api_router.include_router(energy.daily_data_points_router)

# OSS dispatch layer -- forwards device/telemetry/alert/energy-stats READS to
# the OSS microservice with the same RBAC gates. Mounted only when enabled, in
# place of the local read routers guarded above.
if settings.OSS_ENABLED:
    for _oss_router in oss_proxy.oss_proxy_routers:
        api_router.include_router(_oss_router)
