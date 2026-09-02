"""Write endpoints for devices, firmware, incidents and limit configuration.

    POST   /devices                          register a device
    PATCH  /devices/{id}                     edit it
    POST   /devices/{id}/commission          config status -> commissioned
    POST   /devices/{id}/decommission        config status -> decommissioned
    POST   /devices/{id}/maintenance         config status -> under_maintenance
    POST   /firmware                         add a firmware build
    PATCH  /firmware/{id}                    edit / decommission a build
    POST   /firmware/{id}/assign             set expected version on devices
    PATCH  /incidents/{id}                   acknowledge / assign / resolve
    GET    /limit-configs                    list thresholds
    POST   /limit-configs                    create one
    PATCH  /limit-configs/{id}               edit one

RBAC: `caleido_network` write for devices, incidents and limit configs;
`firmware_management` write for firmware -- the same split the read side uses.

`device.authentication_code` is never accepted or returned by any of these.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.alert import IncidentDetail, IncidentRead, ValueAlertRead
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.device import DeviceDetail, DeviceRead, FirmwareRead
from app.schemas.health import ErrorResponse
from app.schemas.ops_write import (
    DeviceCreate,
    DeviceDecommissionBody,
    DeviceUpdate,
    FirmwareAssignBody,
    FirmwareCreate,
    FirmwareUpdate,
    IncidentUpdate,
    LimitConfigCreate,
    LimitConfigUpdate,
)
from app.services import access_write
from app.services import alert as alert_read
from app.services import device as device_read
from app.services import devices_write as service
from app.services.limit_config import LimitConfigRead, list_limit_configs

WRITE_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with current state"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}

NETWORK_WRITE = [Depends(require_permission("caleido_network", "write"))]
NETWORK_READ = [Depends(require_permission("caleido_network", "read"))]
FIRMWARE_WRITE = [Depends(require_permission("firmware_management", "write"))]

devices_write_router = APIRouter(prefix="/devices", tags=["devices"], responses=WRITE_RESPONSES)
firmware_write_router = APIRouter(prefix="/firmware", tags=["firmware"], responses=WRITE_RESPONSES)
incidents_write_router = APIRouter(
    prefix="/incidents", tags=["incidents"], responses=WRITE_RESPONSES
)
limit_configs_router = APIRouter(
    prefix="/limit-configs", tags=["alerts"], responses=WRITE_RESPONSES
)


def _device_detail(db, device_id: uuid.UUID) -> DeviceDetail:
    row = device_read.get_device(db, device_id)
    children = device_read.device_children(db, device_id)
    return DeviceDetail(
        **DeviceRead.model_validate(row).model_dump(),
        parent_device=device_read.device_parent(db, row["parent_device_id"]),
        child_devices=children,
        child_count=len(children),
    )


@devices_write_router.post(
    "",
    response_model=DeviceDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=NETWORK_WRITE,
    summary="Register a device",
    description=(
        "Creates the `device` row in the chosen room. A new device starts as "
        "`configured`; commissioning is the separate action below. "
        "`authentication_code` cannot be supplied -- it is a device credential."
    ),
)
def create_device(
    payload: DeviceCreate, db: DbSession, current_user: CurrentUser
) -> DeviceDetail:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    device = service.create_device(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return _device_detail(db, device.id)


@devices_write_router.patch(
    "/{device_id}",
    response_model=DeviceDetail,
    dependencies=NETWORK_WRITE,
    summary="Update a device",
)
def update_device(
    device_id: uuid.UUID, payload: DeviceUpdate, db: DbSession
) -> DeviceDetail:
    service.update_device(db, device_id, changes=payload.model_dump(exclude_unset=True))
    return _device_detail(db, device_id)


@devices_write_router.post(
    "/{device_id}/commission",
    response_model=DeviceDetail,
    dependencies=NETWORK_WRITE,
    summary="Commission a device",
)
def commission_device(device_id: uuid.UUID, db: DbSession) -> DeviceDetail:
    service.set_device_config_status(db, device_id, config_status="commissioned")
    return _device_detail(db, device_id)


@devices_write_router.post(
    "/{device_id}/decommission",
    response_model=DeviceDetail,
    dependencies=NETWORK_WRITE,
    summary="Decommission a device",
    description=(
        "Sets `device_config_status` to 'decommissioned'. The row is kept: "
        "`device_stat`, `device_alert` and `job_order_device` all reference it, "
        "so deleting it would destroy history."
    ),
)
def decommission_device(
    device_id: uuid.UUID, payload: DeviceDecommissionBody, db: DbSession
) -> DeviceDetail:
    service.set_device_config_status(db, device_id, config_status="decommissioned")
    return _device_detail(db, device_id)


@devices_write_router.post(
    "/{device_id}/maintenance",
    response_model=DeviceDetail,
    dependencies=NETWORK_WRITE,
    summary="Flag a device as under maintenance",
)
def device_under_maintenance(device_id: uuid.UUID, db: DbSession) -> DeviceDetail:
    service.set_device_config_status(db, device_id, config_status="under_maintenance")
    return _device_detail(db, device_id)


# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------


@firmware_write_router.post(
    "",
    response_model=FirmwareRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=FIRMWARE_WRITE,
    summary="Add a firmware build",
    description=(
        "One build per (device type, version): a duplicate is a 409. The file "
        "itself is referenced by `firmware_url` and `crc`; this API records the "
        "build, it does not host binaries."
    ),
)
def create_firmware(
    payload: FirmwareCreate, db: DbSession, current_user: CurrentUser
) -> FirmwareRead:
    row = service.create_firmware(
        db, data=payload.model_dump(), actor_id=current_user.id
    )
    return FirmwareRead.model_validate(device_read.get_firmware(db, row.id))


@firmware_write_router.patch(
    "/{firmware_id}",
    response_model=FirmwareRead,
    dependencies=FIRMWARE_WRITE,
    summary="Update or decommission a firmware build",
    description=(
        "Decommissioning is refused with 409 while any device still expects that "
        "version, so a device can never be left waiting for a retired build."
    ),
)
def update_firmware(
    firmware_id: uuid.UUID,
    payload: FirmwareUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> FirmwareRead:
    service.update_firmware(
        db,
        firmware_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return FirmwareRead.model_validate(device_read.get_firmware(db, firmware_id))


@firmware_write_router.post(
    "/{firmware_id}/assign",
    response_model=list[DeviceRead],
    dependencies=FIRMWARE_WRITE,
    summary="Assign a firmware build to devices",
    description=(
        "Sets `device.expected_firmware_version` on each device, in one "
        "transaction. That column IS the assignment -- the hub compares it with "
        "`current_firmware_version` and pulls the build. No command is queued, "
        "because the schema has no command or MQTT table. A device of the wrong "
        "device type is rejected."
    ),
)
def assign_firmware(
    firmware_id: uuid.UUID, payload: FirmwareAssignBody, db: DbSession
) -> list[DeviceRead]:
    service.assign_firmware(db, firmware_id, device_ids=payload.device_ids)
    return [
        DeviceRead.model_validate(device_read.get_device(db, device_id))
        for device_id in payload.device_ids
    ]


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


@incidents_write_router.patch(
    "/{incident_id}",
    response_model=IncidentDetail,
    dependencies=NETWORK_WRITE,
    summary="Acknowledge, assign or resolve an incident",
    description=(
        "Writes `device_incident.current_incident_status` (1 Unread, 2 Read, "
        "3 Assigned, 4 Resolved) and appends the matching `incident_history` "
        "row. Naming an assignee moves an unread incident to Assigned; moving "
        "back out of Resolved records the 'Reopened' event. Alert severity is "
        "NOT touched -- severity belongs to the alert, lifecycle to the incident."
    ),
)
def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> IncidentDetail:
    service.update_incident(
        db,
        incident_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    row = alert_read.get_incident(db, incident_id)
    history = alert_read.incident_history(db, incident_id)
    return IncidentDetail(
        **IncidentRead.model_validate(row).model_dump(),
        history=history,
        history_count=len(history),
    )


# ---------------------------------------------------------------------------
# Limit configuration
# ---------------------------------------------------------------------------


@limit_configs_router.get(
    "",
    response_model=Page[LimitConfigRead],
    dependencies=NETWORK_READ,
    summary="List value-alert limit configurations",
    description=(
        "`value_alert_limit_config` -- the thresholds behind `value_alert`. "
        "This table had no endpoint before Phase 3.0, which is why the Limit "
        "Config Alert screen could only show breaches, not the configuration."
    ),
)
def list_configs(
    db: DbSession,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    device_id: uuid.UUID | None = None,
    parameter: str | None = None,
) -> Page[LimitConfigRead]:
    page_size = min(page_size, MAX_PAGE_SIZE)
    rows, total = list_limit_configs(
        db, page=page, page_size=page_size, device_id=device_id, parameter=parameter
    )
    return Page[LimitConfigRead](
        items=[LimitConfigRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@limit_configs_router.post(
    "",
    response_model=LimitConfigRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=NETWORK_WRITE,
    summary="Create a limit configuration",
    description=(
        "`is_percentage_value` selects which pair of columns applies -- the "
        "percentage pair or the absolute pair -- and the low limit must be below "
        "the high one."
    ),
)
def create_config(
    payload: LimitConfigCreate, db: DbSession, current_user: CurrentUser
) -> LimitConfigRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_limit_config(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return LimitConfigRead.model_validate(row)


@limit_configs_router.patch(
    "/{config_id}",
    response_model=LimitConfigRead,
    dependencies=NETWORK_WRITE,
    summary="Update a limit configuration",
)
def update_config(
    config_id: uuid.UUID, payload: LimitConfigUpdate, db: DbSession
) -> LimitConfigRead:
    row = service.update_limit_config(
        db, config_id, changes=payload.model_dump(exclude_unset=True)
    )
    return LimitConfigRead.model_validate(row)
