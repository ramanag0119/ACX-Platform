"""Facility and property hierarchy read APIs (Phase 2.2).

Read-only. Every response is assembled from live PostgreSQL rows via the
request-scoped session; there is no mock or fallback data path.

    GET /api/v1/facilities        facility
    GET /api/v1/properties        property
    GET /api/v1/buildings         property at property_chain.level_one_id
    GET /api/v1/floors            property at property_chain.level_two_id
    GET /api/v1/rooms             amenity

Each also has a `/{id}` detail route that answers 404 through the Phase 2.1
error envelope when the row does not exist.

Phase 2.4: every route below requires `read` on the `facility_management`
module. 401 without a valid token, 403 without the grant.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.facility import (
    BuildingRead,
    FacilityDetail,
    FacilityRead,
    FloorRead,
    PropertyRead,
    RoomRead,
)
from app.schemas.filters import AmenityCategory
from app.schemas.health import ErrorResponse
from app.services import facility as service

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

# Phase 2.4 -- these resources are the Facility Management screen, whose
# sidebar module is `facility_management` in the seeded `role_module`
# registry. Read access is required; the grant itself comes from the
# database, not from this file.
FACILITY_READ = [Depends(require_permission("facility_management", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(
    DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page"
)

facilities_router = APIRouter(
    prefix="/facilities", tags=["facilities"],
    dependencies=FACILITY_READ, responses=AUTH_RESPONSES,
)
properties_router = APIRouter(
    prefix="/properties", tags=["properties"],
    dependencies=FACILITY_READ, responses=AUTH_RESPONSES,
)
buildings_router = APIRouter(
    prefix="/buildings", tags=["buildings"],
    dependencies=FACILITY_READ, responses=AUTH_RESPONSES,
)
floors_router = APIRouter(
    prefix="/floors", tags=["floors"],
    dependencies=FACILITY_READ, responses=AUTH_RESPONSES,
)
rooms_router = APIRouter(
    prefix="/rooms", tags=["rooms"],
    dependencies=FACILITY_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------


@facilities_router.get("", response_model=Page[FacilityRead], summary="List facilities")
def list_facilities(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_uid: str | None = Query(None, description="Exact match on facility_uid"),
) -> Page[FacilityRead]:
    rows, total = service.list_facilities(
        db, page=page, page_size=page_size, facility_uid=facility_uid
    )
    return Page[FacilityRead](
        items=[FacilityRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@facilities_router.get(
    "/{facility_id}",
    response_model=FacilityDetail,
    responses=NOT_FOUND,
    summary="Get a facility",
)
def get_facility(facility_id: uuid.UUID, db: DbSession) -> FacilityDetail:
    row = service.get_facility(db, facility_id)
    if row is None:
        raise _missing("Facility", facility_id)
    return FacilityDetail(
        **FacilityRead.model_validate(row).model_dump(),
        **service.facility_counts(db, facility_id),
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@properties_router.get("", response_model=Page[PropertyRead], summary="List properties")
def list_properties(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    property_type_id: uuid.UUID | None = Query(None),
) -> Page[PropertyRead]:
    rows, total = service.list_properties(
        db,
        page=page,
        page_size=page_size,
        facility_id=facility_id,
        property_type_id=property_type_id,
    )
    return Page[PropertyRead](
        items=[PropertyRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@properties_router.get(
    "/{property_id}",
    response_model=PropertyRead,
    responses=NOT_FOUND,
    summary="Get a property",
)
def get_property(property_id: uuid.UUID, db: DbSession) -> PropertyRead:
    row = service.get_property(db, property_id)
    if row is None:
        raise _missing("Property", property_id)
    return PropertyRead.model_validate(row)


# ---------------------------------------------------------------------------
# Buildings -- level one of the property chain
# ---------------------------------------------------------------------------


@buildings_router.get(
    "",
    response_model=Page[BuildingRead],
    summary="List buildings",
    description=(
        "There is no `building` table. A building is a `property` row referenced "
        "as `property_chain.level_one_id`, so `id` here is a property id."
    ),
)
def list_buildings(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
) -> Page[BuildingRead]:
    rows, total = service.list_buildings(
        db, page=page, page_size=page_size, facility_id=facility_id
    )
    return Page[BuildingRead](
        items=[BuildingRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@buildings_router.get(
    "/{building_id}",
    response_model=BuildingRead,
    responses=NOT_FOUND,
    summary="Get a building",
)
def get_building(building_id: uuid.UUID, db: DbSession) -> BuildingRead:
    row = service.get_building(db, building_id)
    if row is None:
        raise _missing("Building", building_id)
    return BuildingRead.model_validate(row)


# ---------------------------------------------------------------------------
# Floors -- level two of the property chain
# ---------------------------------------------------------------------------


@floors_router.get(
    "",
    response_model=Page[FloorRead],
    summary="List floors",
    description=(
        "There is no `floor` table. A floor is a `property` row referenced as "
        "`property_chain.level_two_id`, so `id` here is a property id."
    ),
)
def list_floors(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    building_id: uuid.UUID | None = Query(None, description="Filter to one building"),
) -> Page[FloorRead]:
    rows, total = service.list_floors(
        db,
        page=page,
        page_size=page_size,
        facility_id=facility_id,
        building_id=building_id,
    )
    return Page[FloorRead](
        items=[FloorRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@floors_router.get(
    "/{floor_id}", response_model=FloorRead, responses=NOT_FOUND, summary="Get a floor"
)
def get_floor(floor_id: uuid.UUID, db: DbSession) -> FloorRead:
    row = service.get_floor(db, floor_id)
    if row is None:
        raise _missing("Floor", floor_id)
    return FloorRead.model_validate(row)


# ---------------------------------------------------------------------------
# Rooms (= amenity)
# ---------------------------------------------------------------------------


@rooms_router.get(
    "",
    response_model=Page[RoomRead],
    summary="List rooms",
    description=(
        "Rooms are `amenity` rows. The table also holds non-room spaces "
        "(restaurant, gym, conference); filter with `amenity_category=room` "
        "for guest rooms only."
    ),
)
def list_rooms(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    building_id: uuid.UUID | None = Query(None),
    floor_id: uuid.UUID | None = Query(None),
    amenity_type_id: uuid.UUID | None = Query(None),
    amenity_category: AmenityCategory | None = Query(
        None, description="amenity_category: room | restaurant | others"
    ),
    status_id: int | None = Query(
        None,
        alias="status",
        description="amenity_status id: 0 Available, 1 Occupied, "
        "2 Unavailable, 3 Allotted",
    ),
) -> Page[RoomRead]:
    rows, total = service.list_rooms(
        db,
        page=page,
        page_size=page_size,
        facility_id=facility_id,
        building_id=building_id,
        floor_id=floor_id,
        amenity_type_id=amenity_type_id,
        amenity_category=amenity_category,
        status=status_id,
    )
    return Page[RoomRead](
        items=[RoomRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@rooms_router.get(
    "/{room_id}", response_model=RoomRead, responses=NOT_FOUND, summary="Get a room"
)
def get_room(room_id: uuid.UUID, db: DbSession) -> RoomRead:
    row = service.get_room(db, room_id)
    if row is None:
        raise _missing("Room", room_id)
    return RoomRead.model_validate(row)
