"""Device telemetry read APIs (Phase 2.9).

    GET /api/v1/device-params         · /{id}     device_param (35 rows)
    GET /api/v1/device-stats          · /{id}     device_stat  (the readings)
    GET /api/v1/device-current-stats  · /{id}     device_current_stat
    GET /api/v1/other-device-readings · /{id}     other_device (3rd-party meters)

NOT IMPLEMENTED, and why:

    /telemetry -- Schema does not contain this concept. There is no telemetry
                  table. IKANOS stores readings as the EAV pair
                  `device_param` + `device_stat`, which is what these routes
                  expose under their real table names.

VALUES ARE TEXT. `device_stat.device_param_value` is VARCHAR(500) and holds
Integer, Double, String or Date Time values depending on
`device_param.data_type`. Readings are returned exactly as stored, and no
numeric aggregation is offered over this table -- the column cannot support
one safely.

RBAC: `read` on `caleido_network`, the same module Phase 2.6 uses for the
device network. There is no `telemetry` or `device_stats` module in the 18-row
registry.

READ-ONLY. No ingestion, no MQTT, no WebSockets, no device commands.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import ParamDataType
from app.schemas.health import ErrorResponse
from app.schemas.telemetry import (
    DeviceCurrentStatRead,
    DeviceParamDetail,
    DeviceParamRead,
    DeviceStatRead,
    OtherDeviceReadingRead,
)
from app.services import telemetry as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

NETWORK_READ = [Depends(require_permission("caleido_network", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

device_params_router = APIRouter(
    prefix="/device-params", tags=["telemetry"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
device_stats_router = APIRouter(
    prefix="/device-stats", tags=["telemetry"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
device_current_stats_router = APIRouter(
    prefix="/device-current-stats", tags=["telemetry"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
other_device_readings_router = APIRouter(
    prefix="/other-device-readings", tags=["telemetry"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# device_param
# ---------------------------------------------------------------------------


@device_params_router.get(
    "",
    response_model=Page[DeviceParamRead],
    summary="List device parameters",
    description=(
        "The telemetry parameter registry: 35 rows carrying name, data type "
        "and unit per device type. `param_name` is NOT unique -- Intellihub "
        "has four rows named `relay_status`."
    ),
)
def list_device_params(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    device_type: int | None = Query(None, description="device_type.id"),
    param_name: str | None = Query(None),
    data_type: ParamDataType | None = Query(
        None, description="param_data_type: Integer | Double | String | Date Time"
    ),
    has_unit: bool | None = Query(None, description="Filter on unit IS NULL"),
) -> Page[DeviceParamRead]:
    rows, total = svc.list_device_params(
        db, page=page, page_size=page_size, device_type=device_type,
        param_name=param_name, data_type=data_type, has_unit=has_unit,
    )
    return Page[DeviceParamRead](
        items=[DeviceParamRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@device_params_router.get(
    "/{param_id}",
    response_model=DeviceParamDetail,
    responses=NOT_FOUND,
    summary="Get a device parameter",
)
def get_device_param(param_id: int, db: DbSession) -> DeviceParamDetail:
    row = svc.get_device_param(db, param_id)
    if row is None:
        raise _missing("Device parameter", param_id)
    return DeviceParamDetail(
        **DeviceParamRead.model_validate(row).model_dump(),
        reading_count=svc.param_reading_count(db, param_id),
    )


# ---------------------------------------------------------------------------
# device_stat
# ---------------------------------------------------------------------------


@device_stats_router.get(
    "",
    response_model=Page[DeviceStatRead],
    summary="List telemetry readings",
    description=(
        "`device_stat` rows. Values are returned as stored strings -- read "
        "them with `data_type`. Room, facility, building and floor are "
        "resolved from the device; `device_stat` carries none of them."
    ),
)
def list_device_stats(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    device_id: uuid.UUID | None = Query(None),
    device_param_id: int | None = Query(None),
    param_name: str | None = Query(
        None, description="Not unique -- may span several parameter ids"
    ),
    device_type: int | None = Query(None),
    facility_id: uuid.UUID | None = Query(None, description="Via the device"),
    amenity_id: uuid.UUID | None = Query(None, description="Via the device"),
    building_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    floor_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    timestamp_from: datetime | None = Query(None),
    timestamp_to: datetime | None = Query(None),
) -> Page[DeviceStatRead]:
    rows, total = svc.list_device_stats(
        db, page=page, page_size=page_size, device_id=device_id,
        device_param_id=device_param_id, param_name=param_name,
        device_type=device_type, facility_id=facility_id, amenity_id=amenity_id,
        building_id=building_id, floor_id=floor_id,
        timestamp_from=timestamp_from, timestamp_to=timestamp_to,
    )
    return Page[DeviceStatRead](
        items=[DeviceStatRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@device_stats_router.get(
    "/{stat_id}",
    response_model=DeviceStatRead,
    responses=NOT_FOUND,
    summary="Get a telemetry reading",
)
def get_device_stat(stat_id: int, db: DbSession) -> DeviceStatRead:
    row = svc.get_device_stat(db, stat_id)
    if row is None:
        raise _missing("Device stat", stat_id)
    return DeviceStatRead.model_validate(row)


# ---------------------------------------------------------------------------
# device_current_stat
# ---------------------------------------------------------------------------


@device_current_stats_router.get(
    "",
    response_model=Page[DeviceCurrentStatRead],
    summary="List latest device snapshots",
    description=(
        "One JSON snapshot per device, so a tile need not scan `device_stat`."
    ),
)
def list_device_current_stats(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    device_id: uuid.UUID | None = Query(None),
    facility_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None),
    device_type: int | None = Query(None),
) -> Page[DeviceCurrentStatRead]:
    rows, total = svc.list_device_current_stats(
        db, page=page, page_size=page_size, device_id=device_id,
        facility_id=facility_id, amenity_id=amenity_id, device_type=device_type,
    )
    return Page[DeviceCurrentStatRead](
        items=[DeviceCurrentStatRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@device_current_stats_router.get(
    "/{current_stat_id}",
    response_model=DeviceCurrentStatRead,
    responses=NOT_FOUND,
    summary="Get a device snapshot",
)
def get_device_current_stat(
    current_stat_id: uuid.UUID, db: DbSession
) -> DeviceCurrentStatRead:
    row = svc.get_device_current_stat(db, current_stat_id)
    if row is None:
        raise _missing("Device snapshot", current_stat_id)
    return DeviceCurrentStatRead.model_validate(row)


# ---------------------------------------------------------------------------
# other_device
# ---------------------------------------------------------------------------


@other_device_readings_router.get(
    "",
    response_model=Page[OtherDeviceReadingRead],
    summary="List third-party meter readings",
    description=(
        "`other_device` rows. This table has NO foreign keys, so a reading "
        "cannot be joined to a device, room or facility -- `device_name` is "
        "free text. Its measurements ARE numeric columns, unlike device_stat. "
        "The raw `msg_string` payload is withheld."
    ),
)
def list_other_device_readings(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    device_name: str | None = Query(None, description="Free text, exact match"),
    timestamp_from: datetime | None = Query(None),
    timestamp_to: datetime | None = Query(None),
) -> Page[OtherDeviceReadingRead]:
    rows, total = svc.list_other_device_readings(
        db, page=page, page_size=page_size, device_name=device_name,
        timestamp_from=timestamp_from, timestamp_to=timestamp_to,
    )
    return Page[OtherDeviceReadingRead](
        items=[OtherDeviceReadingRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@other_device_readings_router.get(
    "/{reading_id}",
    response_model=OtherDeviceReadingRead,
    responses=NOT_FOUND,
    summary="Get a third-party meter reading",
)
def get_other_device_reading(reading_id: int, db: DbSession) -> OtherDeviceReadingRead:
    row = svc.get_other_device_reading(db, reading_id)
    if row is None:
        raise _missing("Meter reading", reading_id)
    return OtherDeviceReadingRead.model_validate(row)
