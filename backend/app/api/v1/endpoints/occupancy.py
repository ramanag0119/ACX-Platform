"""Room occupancy read APIs (Phase 2.8).

    GET /api/v1/occupancy              · /{amenity_id}   room-centric view
    GET /api/v1/amenity-statuses                         amenity_status lookup
    GET /api/v1/amenity-conditions                       amenity_condition lookup

There is no `occupancy` table. Each row is an `amenity` joined to its status
lookup, its active conditions, and the stay currently in house in that room.
`{amenity_id}` is the room's amenity id, not an invented occupancy id.

TWO INDEPENDENT SOURCES OF TRUTH, NOT RECONCILED. A room's state is carried
both by `amenity.status` and by the stay/allocation graph, and nothing in the
schema keeps them in step -- in the seeded data 5 amenities are flagged
Occupied while only 3 have a guest actually in house. Both are reported as
stored: `status_name` from the amenity row, `current_stay` derived from
`actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL`. Silently
picking one would hide a real data-integrity question.

RBAC: `read` on `occupancy`. Housekeeping holds this module read-only, which
is why the occupancy view is separated from the `bookings`-gated stay APIs.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import AmenityCategory
from app.schemas.health import ErrorResponse
from app.schemas.occupancy import (
    AmenityConditionRead,
    AmenityStatusRead,
    OccupancyDetail,
    OccupancyRead,
)
from app.services import occupancy as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

OCCUPANCY_READ = [Depends(require_permission("occupancy", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

occupancy_router = APIRouter(
    prefix="/occupancy", tags=["occupancy"],
    dependencies=OCCUPANCY_READ, responses=AUTH_RESPONSES,
)
amenity_statuses_router = APIRouter(
    prefix="/amenity-statuses", tags=["occupancy"],
    dependencies=OCCUPANCY_READ, responses=AUTH_RESPONSES,
)
amenity_conditions_router = APIRouter(
    prefix="/amenity-conditions", tags=["occupancy"],
    dependencies=OCCUPANCY_READ, responses=AUTH_RESPONSES,
)


@occupancy_router.get(
    "",
    response_model=Page[OccupancyRead],
    summary="Room occupancy",
    description=(
        "One row per amenity. `status_name` is what the amenity row says; "
        "`current_stay` is what the stay graph says. They can disagree and "
        "are not reconciled -- filter with `is_occupied` to query the stay "
        "graph, or `status` to query the amenity flag."
    ),
)
def list_occupancy(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    building_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    floor_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    amenity_type_id: uuid.UUID | None = Query(None),
    amenity_category: AmenityCategory | None = Query(
        None, description="amenity_category: room | restaurant | others"
    ),
    status_value: int | None = Query(
        None, alias="status",
        description="amenity_status.id: 0 Available, 1 Occupied, "
                    "2 Unavailable, 3 Allotted",
    ),
    condition_id: int | None = Query(
        None, description="amenity_condition.id, active conditions only"
    ),
    is_occupied: bool | None = Query(
        None,
        description="By the STAY graph (a guest is in house), not by amenity.status",
    ),
) -> Page[OccupancyRead]:
    rows, total = svc.list_occupancy(
        db, page=page, page_size=page_size, facility_id=facility_id,
        building_id=building_id, floor_id=floor_id,
        amenity_type_id=amenity_type_id, amenity_category=amenity_category,
        status=status_value, condition_id=condition_id, is_occupied=is_occupied,
    )
    return Page[OccupancyRead](
        items=[OccupancyRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@occupancy_router.get(
    "/{amenity_id}",
    response_model=OccupancyDetail,
    responses=NOT_FOUND,
    summary="Occupancy for one room",
    description="The path parameter is the room's amenity id.",
)
def get_occupancy(amenity_id: uuid.UUID, db: DbSession) -> OccupancyDetail:
    row = svc.get_occupancy(db, amenity_id)
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Room {amenity_id} does not exist.",
        )
    return OccupancyDetail.model_validate(row)


@amenity_statuses_router.get(
    "",
    response_model=Page[AmenityStatusRead],
    summary="List amenity statuses",
    description="Available (id 0), Occupied, Unavailable, Allotted.",
)
def list_amenity_statuses(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[AmenityStatusRead]:
    rows, total = svc.list_amenity_statuses(db, page=page, page_size=page_size)
    return Page[AmenityStatusRead](
        items=[AmenityStatusRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@amenity_conditions_router.get(
    "",
    response_model=Page[AmenityConditionRead],
    summary="List amenity conditions",
    description="Dirty, Low battery, Under maintenance, Sanitation.",
)
def list_amenity_conditions(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[AmenityConditionRead]:
    rows, total = svc.list_amenity_conditions(db, page=page, page_size=page_size)
    return Page[AmenityConditionRead](
        items=[AmenityConditionRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )
