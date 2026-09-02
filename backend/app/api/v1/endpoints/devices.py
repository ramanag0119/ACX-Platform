"""Device inventory, types, firmware and health read APIs (Phase 2.6).

    GET /api/v1/device-types      · /{id}          device_type (4 lookup rows)
    GET /api/v1/devices           · /{id}          device
    GET /api/v1/devices/{id}/health                device health, assembled
    GET /api/v1/firmware          · /{id}          firmware

RBAC, taken from the seeded `role_module` registry rather than assumed:

    /device-types, /devices  ->  `caleido_network`      (Device Mgmt screen)
    /firmware                ->  `firmware_management`  (Firmware Mgmt screen)

The database already draws the line: the Duty Manager role holds
`caleido_network` with read_access=true and write_access=FALSE, and holds no
`firmware_management` grant at all. So a Manager can view the device network
but cannot reach firmware -- enforced by data, not by a role-name check.

READ-ONLY. See docs/PHASE2_6_DEVICES.md for the blockers that make a safe
write path impossible from the current schema.

OUT OF SCOPE for this phase and deliberately not read: telemetry
(`device_stat`, `device_current_stat`), MQTT (`mqtt_broker`, `mqtt_topic`),
the command queue (`device_command`), alerts and incidents.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.device import (
    DeviceDetail,
    DeviceHealthRead,
    DeviceRead,
    DeviceRef,
    DeviceTypeDetail,
    DeviceTypeRead,
    FirmwareDetail,
    FirmwareRead,
)
from app.schemas.filters import (
    DeviceConfigStatus,
    DeviceHealthStatus,
    FirmwareStatus,
)
from app.schemas.health import ErrorResponse
from app.services import device as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

NETWORK_READ = [Depends(require_permission("caleido_network", "read"))]
FIRMWARE_READ = [Depends(require_permission("firmware_management", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

device_types_router = APIRouter(
    prefix="/device-types", tags=["devices"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
devices_router = APIRouter(
    prefix="/devices", tags=["devices"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
firmware_router = APIRouter(
    prefix="/firmware", tags=["firmware"],
    dependencies=FIRMWARE_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# device_type
# ---------------------------------------------------------------------------


@device_types_router.get(
    "",
    response_model=Page[DeviceTypeRead],
    summary="List device types",
    description=(
        "The 4 Caleido device families. There is no `device_model` table -- "
        "`device.model` is free text, so type and model are distinct."
    ),
)
def list_device_types(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[DeviceTypeRead]:
    rows, total = svc.list_device_types(db, page=page, page_size=page_size)
    return Page[DeviceTypeRead](
        items=[DeviceTypeRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@device_types_router.get(
    "/{device_type_id}",
    response_model=DeviceTypeDetail,
    responses=NOT_FOUND,
    summary="Get a device type",
)
def get_device_type(device_type_id: int, db: DbSession) -> DeviceTypeDetail:
    row = svc.get_device_type(db, device_type_id)
    if row is None:
        raise _missing("Device type", device_type_id)
    return DeviceTypeDetail(
        **DeviceTypeRead.model_validate(row).model_dump(),
        **svc.device_type_counts(db, device_type_id),
    )


# ---------------------------------------------------------------------------
# device
# ---------------------------------------------------------------------------


@devices_router.get(
    "",
    response_model=Page[DeviceRead],
    summary="List devices",
    description=(
        "Device location is `facility_id` + `amenity_id`; building and floor "
        "are resolved through amenity -> property_chain, as Phase 2.2 "
        "established. `authentication_code` and `metadata` are never returned."
    ),
)
def list_devices(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None, description="The room"),
    building_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    floor_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    device_type: int | None = Query(None, description="device_type.id"),
    health_status: DeviceHealthStatus | None = Query(
        None, description="device_health_status: Active | Inactive"
    ),
    device_config_status: DeviceConfigStatus | None = Query(
        None, description="device_config_status enum label"
    ),
    model: str | None = Query(None),
    manufacturer_name: str | None = Query(None),
    device_uid: str | None = Query(None, description="Exact match; unique"),
    parent_device_id: uuid.UUID | None = Query(None),
    is_standalone: bool | None = Query(None, description="parent_device_id IS NULL"),
    firmware_id: uuid.UUID | None = Query(
        None, description="Devices running this firmware"
    ),
    firmware_outdated: bool | None = Query(
        None, description="current_firmware_version <> expected_firmware_version"
    ),
) -> Page[DeviceRead]:
    rows, total = svc.list_devices(
        db, page=page, page_size=page_size, facility_id=facility_id,
        amenity_id=amenity_id, building_id=building_id, floor_id=floor_id,
        device_type=device_type, health_status=health_status,
        device_config_status=device_config_status, model=model,
        manufacturer_name=manufacturer_name, device_uid=device_uid,
        parent_device_id=parent_device_id, is_standalone=is_standalone,
        firmware_id=firmware_id, firmware_outdated=firmware_outdated,
    )
    return Page[DeviceRead](
        items=[DeviceRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@devices_router.get(
    "/{device_id}",
    response_model=DeviceDetail,
    responses=NOT_FOUND,
    summary="Get a device with its parent and children",
)
def get_device(device_id: uuid.UUID, db: DbSession) -> DeviceDetail:
    row = svc.get_device(db, device_id)
    if row is None:
        raise _missing("Device", device_id)
    children = svc.device_children(db, device_id)
    parent = svc.device_parent(db, row["parent_device_id"])
    return DeviceDetail(
        **DeviceRead.model_validate(row).model_dump(),
        parent_device=DeviceRef.model_validate(parent) if parent else None,
        child_devices=[DeviceRef.model_validate(c) for c in children],
        child_count=len(children),
    )


@devices_router.get(
    "/{device_id}/health",
    response_model=DeviceHealthRead,
    responses=NOT_FOUND,
    summary="Device health",
    description=(
        "Assembled from `device` (current state), `device_health_stat` "
        "(history), `battery_life_stat` and `sensor_operation_stat`. "
        "`last_reported_on` is DERIVED as MAX(device_health_stat.created_on) -- "
        "there is no `last_seen` column. No telemetry table is read."
    ),
)
def get_device_health(
    device_id: uuid.UUID,
    db: DbSession,
    sample_limit: int = Query(
        20, ge=1, le=MAX_PAGE_SIZE, description="Most recent health samples"
    ),
) -> DeviceHealthRead:
    data = svc.device_health(db, device_id, sample_limit=sample_limit)
    if data is None:
        raise _missing("Device", device_id)
    return DeviceHealthRead.model_validate(data)


# ---------------------------------------------------------------------------
# firmware
# ---------------------------------------------------------------------------


@firmware_router.get(
    "",
    response_model=Page[FirmwareRead],
    summary="List firmware releases",
    description=(
        "There is no `is_latest` column. Currency is determined per device by "
        "comparing current_firmware_version with expected_firmware_version -- "
        "see the `firmware_outdated` filter on /devices."
    ),
)
def list_firmware(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    device_type_id: int | None = Query(None),
    status_value: FirmwareStatus | None = Query(
        None, alias="status", description="firmware_status: active | decommissioned"
    ),
    firmware_version: str | None = Query(None),
) -> Page[FirmwareRead]:
    rows, total = svc.list_firmware(
        db, page=page, page_size=page_size, device_type_id=device_type_id,
        status=status_value, firmware_version=firmware_version,
    )
    return Page[FirmwareRead](
        items=[FirmwareRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@firmware_router.get(
    "/{firmware_id}",
    response_model=FirmwareDetail,
    responses=NOT_FOUND,
    summary="Get a firmware release",
)
def get_firmware(firmware_id: uuid.UUID, db: DbSession) -> FirmwareDetail:
    row = svc.get_firmware(db, firmware_id)
    if row is None:
        raise _missing("Firmware", firmware_id)
    return FirmwareDetail(
        **FirmwareRead.model_validate(row).model_dump(),
        **svc.firmware_usage(db, firmware_id),
    )
