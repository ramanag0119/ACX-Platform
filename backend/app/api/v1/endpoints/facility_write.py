"""Facility, room-catalogue and marketing endpoints (reads + writes).

Reads added here for tables that previously had none:

    GET  /amenity-types      GET /packages      GET /features
    GET  /offers             GET /events        GET /holidays
    GET  /occasion-types

Writes:

    PATCH /facilities/{id}                 facility setup
    POST/PATCH /rooms                      a room IS an `amenity`
    POST/PATCH /amenity-types
    POST/PATCH /packages                   including its `package_feature` rows
    POST/PATCH /features
    POST/PATCH /offers                     `promo_code` + `promo_code_amenity`
    POST/PATCH /events                     `facility_event`
    POST/PATCH /holidays                   `occasion`

RBAC follows the screen each table belongs to: `facility_management` for the
facility, rooms and the catalogue; `offers`, `events` and `holidays` for the
three marketing screens -- all real `role_module` names.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.facility import FacilityRead, RoomRead
from app.schemas.health import ErrorResponse
from app.schemas.ops_write import (
    AmenityTypeCreate,
    AmenityTypeUpdate,
    FacilityEventCreate,
    FacilityEventUpdate,
    FacilityUpdate,
    FeatureCreate,
    FeatureUpdate,
    OccasionCreate,
    OccasionUpdate,
    PackageCreate,
    PackageUpdate,
    PromoCodeCreate,
    PromoCodeUpdate,
    RoomCreate,
    RoomUpdate,
)
from app.services import access_write
from app.services import catalog
from app.services import facility as facility_read
from app.services import facility_write as service
from app.services.catalog import (
    AmenityTypeRead,
    FacilityEventRead,
    FeatureRead,
    OccasionRead,
    OccasionTypeRead,
    PackageRead,
    PromoCodeRead,
)

RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with existing data"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}

FACILITY_READ = [Depends(require_permission("facility_management", "read"))]
FACILITY_WRITE = [Depends(require_permission("facility_management", "write"))]
OFFERS_READ = [Depends(require_permission("offers", "read"))]
OFFERS_WRITE = [Depends(require_permission("offers", "write"))]
EVENTS_READ = [Depends(require_permission("events", "read"))]
EVENTS_WRITE = [Depends(require_permission("events", "write"))]
HOLIDAYS_READ = [Depends(require_permission("holidays", "read"))]
HOLIDAYS_WRITE = [Depends(require_permission("holidays", "write"))]

facilities_write_router = APIRouter(prefix="/facilities", tags=["facilities"], responses=RESPONSES)
rooms_write_router = APIRouter(prefix="/rooms", tags=["rooms"], responses=RESPONSES)
amenity_types_router = APIRouter(prefix="/amenity-types", tags=["rooms"], responses=RESPONSES)
packages_router = APIRouter(prefix="/packages", tags=["rooms"], responses=RESPONSES)
features_router = APIRouter(prefix="/features", tags=["rooms"], responses=RESPONSES)
offers_router = APIRouter(prefix="/offers", tags=["offers"], responses=RESPONSES)
events_router = APIRouter(prefix="/events", tags=["events"], responses=RESPONSES)
holidays_router = APIRouter(prefix="/holidays", tags=["holidays"], responses=RESPONSES)


def _page_args(page: int, page_size: int) -> tuple[int, int]:
    return page, min(page_size, MAX_PAGE_SIZE)


def _found(row, label: str, row_id):
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} {row_id} does not exist.")
    return row


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------


@facilities_write_router.patch(
    "/{facility_id}",
    response_model=FacilityRead,
    dependencies=FACILITY_WRITE,
    summary="Update facility setup",
)
def update_facility(
    facility_id: uuid.UUID, payload: FacilityUpdate, db: DbSession
) -> FacilityRead:
    service.update_facility(db, facility_id, changes=payload.model_dump(exclude_unset=True))
    return FacilityRead.model_validate(facility_read.get_facility(db, facility_id))


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


@rooms_write_router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=FACILITY_WRITE,
    summary="Create a room",
    description=(
        "A room IS an `amenity`. `amenity_type_id` and `package_id` are NOT NULL "
        "in the schema, so both must already exist. `property_chain_id` is what "
        "places the room on a building and floor -- those are projections over "
        "`property_chain`, not tables. New rooms start Unavailable, the column's "
        "own default, until they are made ready."
    ),
)
def create_room(
    payload: RoomCreate, db: DbSession, current_user: CurrentUser
) -> RoomRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    room = service.create_room(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return RoomRead.model_validate(facility_read.get_room(db, room.id))


@rooms_write_router.patch(
    "/{room_id}",
    response_model=RoomRead,
    dependencies=FACILITY_WRITE,
    summary="Update a room",
    description=(
        "Room STATUS is not set here: it belongs to the occupancy workflow "
        "(PATCH /occupancy/{amenity_id}), which also guards against releasing a "
        "room a live stay still holds."
    ),
)
def update_room(room_id: uuid.UUID, payload: RoomUpdate, db: DbSession) -> RoomRead:
    service.update_room(db, room_id, changes=payload.model_dump(exclude_unset=True))
    return RoomRead.model_validate(facility_read.get_room(db, room_id))


# ---------------------------------------------------------------------------
# Amenity types
# ---------------------------------------------------------------------------


@amenity_types_router.get(
    "",
    response_model=Page[AmenityTypeRead],
    dependencies=FACILITY_READ,
    summary="List amenity types",
)
def list_amenity_types(
    db: DbSession, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> Page[AmenityTypeRead]:
    page, page_size = _page_args(page, page_size)
    rows, total = catalog.list_amenity_types(db, page=page, page_size=page_size)
    return Page[AmenityTypeRead](
        items=[AmenityTypeRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@amenity_types_router.post(
    "",
    response_model=AmenityTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=FACILITY_WRITE,
    summary="Create an amenity type",
)
def create_amenity_type(
    payload: AmenityTypeCreate, db: DbSession, current_user: CurrentUser
) -> AmenityTypeRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_amenity_type(
        db, data=payload.model_dump(),
        actor_id=current_user.id, facility_id=facility_id,
    )
    return AmenityTypeRead.model_validate(row)


@amenity_types_router.patch(
    "/{amenity_type_id}",
    response_model=AmenityTypeRead,
    dependencies=FACILITY_WRITE,
    summary="Update an amenity type",
)
def update_amenity_type(
    amenity_type_id: uuid.UUID, payload: AmenityTypeUpdate, db: DbSession
) -> AmenityTypeRead:
    row = service.update_amenity_type(
        db, amenity_type_id, changes=payload.model_dump(exclude_unset=True)
    )
    return AmenityTypeRead.model_validate(row)


# ---------------------------------------------------------------------------
# Packages and features
# ---------------------------------------------------------------------------


@packages_router.get(
    "",
    response_model=Page[PackageRead],
    dependencies=FACILITY_READ,
    summary="List packages",
    description=(
        "`package` plus its `package_feature` names and room count. Retired "
        "packages (status = 0) are excluded unless `include_removed=true`."
    ),
)
def list_packages(
    db: DbSession,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    is_sub_package: bool | None = None,
    include_removed: bool = Query(False, description="Include status = 0 rows"),
) -> Page[PackageRead]:
    page, page_size = _page_args(page, page_size)
    items, total = catalog.list_packages(
        db,
        page=page,
        page_size=page_size,
        is_sub_package=is_sub_package,
        include_removed=include_removed,
    )
    return Page[PackageRead](items=items, page=page, page_size=page_size, total=total)


@packages_router.post(
    "",
    response_model=PackageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=FACILITY_WRITE,
    summary="Create a package",
)
def create_package(
    payload: PackageCreate, db: DbSession, current_user: CurrentUser
) -> PackageRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_package(
        db, data=payload.model_dump(),
        actor_id=current_user.id, facility_id=facility_id,
    )
    return _found(catalog.get_package(db, row.id), "Package", row.id)


@packages_router.patch(
    "/{package_id}",
    response_model=PackageRead,
    dependencies=FACILITY_WRITE,
    summary="Update a package (status = 0 is the delete)",
    description=(
        "The catalogue tables have no DELETE route -- `amenity.package_id` is "
        "NOT NULL and references this row, so retiring a package is "
        "`status = 0`, exactly as /holidays and /firmware work. A retired "
        "package leaves GET /packages. Rooms still assigned to it block the "
        "retire with 409 rather than being left pointing at a dead package."
    ),
)
def update_package(
    package_id: uuid.UUID, payload: PackageUpdate, db: DbSession, current_user: CurrentUser
) -> PackageRead:
    service.update_package(
        db, package_id, changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return _found(catalog.get_package(db, package_id), "Package", package_id)


@features_router.get(
    "",
    response_model=Page[FeatureRead],
    dependencies=FACILITY_READ,
    summary="List room features",
    description="`feature` -- the Room Amenities tab of Facility Management.",
)
def list_features(
    db: DbSession, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> Page[FeatureRead]:
    page, page_size = _page_args(page, page_size)
    rows, total = catalog.list_features(db, page=page, page_size=page_size)
    return Page[FeatureRead](
        items=[FeatureRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@features_router.post(
    "",
    response_model=FeatureRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=FACILITY_WRITE,
    summary="Create a room feature",
)
def create_feature(
    payload: FeatureCreate, db: DbSession, current_user: CurrentUser
) -> FeatureRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_feature(
        db, data=payload.model_dump(),
        actor_id=current_user.id, facility_id=facility_id,
    )
    return FeatureRead.model_validate(row)


@features_router.patch(
    "/{feature_id}",
    response_model=FeatureRead,
    dependencies=FACILITY_WRITE,
    summary="Update a room feature",
)
def update_feature(
    feature_id: uuid.UUID, payload: FeatureUpdate, db: DbSession
) -> FeatureRead:
    row = service.update_feature(
        db, feature_id, changes=payload.model_dump(exclude_unset=True)
    )
    return FeatureRead.model_validate(row)


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


@offers_router.get(
    "",
    response_model=Page[PromoCodeRead],
    dependencies=OFFERS_READ,
    summary="List offers",
    description="`promo_code` plus the room names from `promo_code_amenity`.",
)
def list_offers(
    db: DbSession, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> Page[PromoCodeRead]:
    page, page_size = _page_args(page, page_size)
    items, total = catalog.list_promo_codes(db, page=page, page_size=page_size)
    return Page[PromoCodeRead](items=items, page=page, page_size=page_size, total=total)


@offers_router.post(
    "",
    response_model=PromoCodeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=OFFERS_WRITE,
    summary="Create an offer",
)
def create_offer(
    payload: PromoCodeCreate, db: DbSession, current_user: CurrentUser
) -> PromoCodeRead:
    row = service.create_promo_code(
        db, data=payload.model_dump(), actor_id=current_user.id
    )
    return _found(catalog.get_promo_code(db, row.id), "Offer", row.id)


@offers_router.patch(
    "/{offer_id}",
    response_model=PromoCodeRead,
    dependencies=OFFERS_WRITE,
    summary="Update an offer",
)
def update_offer(
    offer_id: uuid.UUID, payload: PromoCodeUpdate, db: DbSession, current_user: CurrentUser
) -> PromoCodeRead:
    service.update_promo_code(
        db, offer_id, changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return _found(catalog.get_promo_code(db, offer_id), "Offer", offer_id)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@events_router.get(
    "",
    response_model=Page[FacilityEventRead],
    dependencies=EVENTS_READ,
    summary="List events",
)
def list_events(
    db: DbSession, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> Page[FacilityEventRead]:
    page, page_size = _page_args(page, page_size)
    rows, total = catalog.list_events(db, page=page, page_size=page_size)
    return Page[FacilityEventRead](
        items=[FacilityEventRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@events_router.post(
    "",
    response_model=FacilityEventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=EVENTS_WRITE,
    summary="Create an event",
    description=(
        "`interested_attendees` is not settable: it is a guest-app counter, not "
        "an operator field."
    ),
)
def create_event(
    payload: FacilityEventCreate, db: DbSession, current_user: CurrentUser
) -> FacilityEventRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_event(
        db, data=payload.model_dump(),
        actor_id=current_user.id, facility_id=facility_id,
    )
    return FacilityEventRead.model_validate(row)


@events_router.patch(
    "/{event_id}",
    response_model=FacilityEventRead,
    dependencies=EVENTS_WRITE,
    summary="Update an event",
)
def update_event(
    event_id: uuid.UUID, payload: FacilityEventUpdate, db: DbSession
) -> FacilityEventRead:
    row = service.update_event(
        db, event_id, changes=payload.model_dump(exclude_unset=True)
    )
    return FacilityEventRead.model_validate(row)


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------


@holidays_router.get(
    "",
    response_model=Page[OccasionRead],
    dependencies=HOLIDAYS_READ,
    summary="List holidays and occasions",
)
def list_holidays(
    db: DbSession, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> Page[OccasionRead]:
    page, page_size = _page_args(page, page_size)
    items, total = catalog.list_occasions(db, page=page, page_size=page_size)
    return Page[OccasionRead](items=items, page=page, page_size=page_size, total=total)


@holidays_router.get(
    "/types",
    response_model=list[OccasionTypeRead],
    dependencies=HOLIDAYS_READ,
    summary="List occasion types",
)
def list_occasion_types(db: DbSession) -> list[OccasionTypeRead]:
    return catalog.list_occasion_types(db)


@holidays_router.post(
    "",
    response_model=OccasionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=HOLIDAYS_WRITE,
    summary="Create a holiday or occasion",
    description=(
        "`month` and `day_of_month` are NOT NULL in `occasion` and are derived "
        "from the start date, which is what makes a repeatable occasion recur."
    ),
)
def create_holiday(
    payload: OccasionCreate, db: DbSession, current_user: CurrentUser
) -> OccasionRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_occasion(
        db, data=payload.model_dump(),
        actor_id=current_user.id, facility_id=facility_id,
    )
    return _found(catalog.get_occasion(db, row.id), "Occasion", row.id)


@holidays_router.patch(
    "/{occasion_id}",
    response_model=OccasionRead,
    dependencies=HOLIDAYS_WRITE,
    summary="Update a holiday or occasion",
)
def update_holiday(
    occasion_id: uuid.UUID, payload: OccasionUpdate, db: DbSession
) -> OccasionRead:
    service.update_occasion(db, occasion_id, changes=payload.model_dump(exclude_unset=True))
    return _found(catalog.get_occasion(db, occasion_id), "Occasion", occasion_id)
