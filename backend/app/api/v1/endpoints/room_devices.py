"""Room <-> OSS device mapping.

    GET    /room-devices          list mappings (filter by room/floor/building/facility)
    GET    /room-devices/{id}     one mapping
    POST   /room-devices          install an OSS device in a room
    DELETE /room-devices/{id}     remove it from the room

The mapping is HMS (BSS) data in hms_db. The OSS database is only ever read --
to confirm the device exists before it is mapped.

RBAC: `caleido_network` read / write, the same grant as the device screens.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.api.errors import error_response
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, paginate
from app.schemas.health import ErrorResponse
from app.schemas.room_device import RoomDeviceCreate, RoomDeviceRead
from app.services import oss_client
from app.services import room_devices as service

RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
}

room_devices_router = APIRouter(prefix="/room-devices", tags=["devices"], responses=RESPONSES)

NETWORK_READ = [Depends(require_permission("caleido_network", "read"))]
NETWORK_WRITE = [Depends(require_permission("caleido_network", "write"))]


@room_devices_router.get(
    "", response_model=Page[RoomDeviceRead], dependencies=NETWORK_READ,
    summary="List room device mappings",
)
def list_room_devices(
    db: DbSession,
    amenity_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    rows, total = service.list_room_devices(
        db, page=page, page_size=page_size, amenity_id=amenity_id,
        floor_id=floor_id, building_id=building_id, facility_id=facility_id,
    )
    return paginate(rows, page=page, page_size=page_size, total=total)


@room_devices_router.get(
    "/{map_id}", response_model=RoomDeviceRead, dependencies=NETWORK_READ,
    summary="Get a room device mapping",
)
def get_room_device(map_id: uuid.UUID, db: DbSession):
    return service.get_room_device(db, map_id)


@room_devices_router.post(
    "",
    response_model=RoomDeviceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=NETWORK_WRITE,
    summary="Install an OSS device in a room",
    responses={
        409: {"model": ErrorResponse, "description": "Device is already mapped to a room"},
        422: {"model": ErrorResponse, "description": "Room or OSS device does not exist"},
        503: {"model": ErrorResponse, "description": "OSS unreachable; device not verified"},
    },
)
def assign_device(payload: RoomDeviceCreate, db: DbSession, current_user: CurrentUser):
    try:
        row = service.assign_device(
            db, amenity_id=payload.amenity_id, oss_device_id=payload.oss_device_id,
            actor_id=current_user.id,
        )
    except oss_client.OssUnavailable:
        return error_response(
            503, "OSS service is unavailable; the device could not be verified.",
            code="oss_unavailable",
        )
    return service.get_room_device(db, row.id)


@room_devices_router.delete(
    "/{map_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=NETWORK_WRITE,
    summary="Remove an OSS device from its room",
)
def unassign_device(map_id: uuid.UUID, db: DbSession) -> None:
    service.unassign_device(db, map_id)
