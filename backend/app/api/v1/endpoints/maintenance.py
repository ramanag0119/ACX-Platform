"""Services Planning read and write APIs (`maintenance_request`).

    GET    /api/v1/maintenance-requests           list, filterable by tab
    GET    /api/v1/maintenance-requests/{id}      one request, fully assembled
    POST   /api/v1/maintenance-requests           create (rooms + assignees + rule)
    PATCH  /api/v1/maintenance-requests/{id}      edit, reassign, progress
    POST   /api/v1/maintenance-requests/{id}/cancel   -> service_status Canceled
    DELETE /api/v1/maintenance-requests/{id}      soft delete (status = 0)

The three Services Planning tabs are one endpoint filtered by
`request_type` (`scheduled` | `planned` | `disinfection`), because that is how
the schema models them -- a single table with an enum, not three tables.

RBAC: the `service_planning` module, read for GET and write for the mutations,
taken from the seeded `role_module` registry. Read and write live in one file
because they are one screen and share the assembly helper below.

DELETE is a SOFT delete. `maintenance_request` is referenced by its recurrence,
amenity and assignee rows -- all ON DELETE RESTRICT -- and by `parent_id` on its
own recurrence instances, so a physical delete is not possible without breaking
referential integrity. This matches how /holidays and the catalogue retire rows.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.health import ErrorResponse
from app.schemas.maintenance import (
    CancelBody,
    MaintenanceRequestCreate,
    MaintenanceRequestRead,
    MaintenanceRequestType,
    MaintenanceRequestUpdate,
)
from app.services import access_write
from app.services import maintenance as svc
from app.services import maintenance_write as write_svc

AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}
WRITE_RESPONSES = {
    **AUTH_RESPONSES,
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with current state"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}

PLANNING_READ = [Depends(require_permission("service_planning", "read"))]
PLANNING_WRITE = [Depends(require_permission("service_planning", "write"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

maintenance_requests_router = APIRouter(
    prefix="/maintenance-requests",
    tags=["service-planning"],
    dependencies=PLANNING_READ,
    responses=AUTH_RESPONSES,
)
maintenance_requests_write_router = APIRouter(
    prefix="/maintenance-requests",
    tags=["service-planning"],
    responses=WRITE_RESPONSES,
)


def _assemble(db, rows) -> list[MaintenanceRequestRead]:
    """Attach rooms, assignees and the recurrence rule to a page of requests.

    Three batched queries for the whole page, not per row.
    """
    ids = [row["id"] for row in rows]
    rooms = svc.rooms_for(db, ids)
    assignees = svc.assignees_for(db, ids)
    recurrences = svc.recurrences_for(db, ids)
    assembled = []
    for row in rows:
        request_rooms = rooms.get(row["id"], [])
        request_assignees = assignees.get(row["id"], [])
        assembled.append(
            MaintenanceRequestRead(
                **row,
                rooms=request_rooms,
                assignees=request_assignees,
                recurrence=recurrences.get(row["id"]),
                room_count=len(request_rooms),
                assignee_count=len(request_assignees),
            )
        )
    return assembled


def _one(db, request_id: uuid.UUID) -> MaintenanceRequestRead:
    """Return through the read projection so a write cannot widen the payload."""
    row = svc.get_maintenance_request(db, request_id)
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance request {request_id} does not exist.",
        )
    return _assemble(db, [row])[0]


@maintenance_requests_router.get(
    "",
    response_model=Page[MaintenanceRequestRead],
    summary="List planned services",
    description=(
        "One row per `maintenance_request`, with its rooms, assignees and "
        "recurrence rule attached. Filter `request_type` to pick a Services "
        "Planning tab. Soft-deleted rows (status = 0) are excluded unless "
        "`include_removed=true`."
    ),
)
def list_maintenance_requests(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    request_type: MaintenanceRequestType | None = Query(
        None, description="scheduled | planned | disinfection -- the tab"
    ),
    facility_id: uuid.UUID | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None, description="service_category.id"),
    request_status: int | None = Query(
        None, alias="status", ge=1, description="service_status.id: 1..5"
    ),
    assigned_to: uuid.UUID | None = Query(
        None, description="Via maintenance_request_assignee"
    ),
    amenity_id: uuid.UUID | None = Query(
        None, description="Via maintenance_request_amenity"
    ),
    is_recurring: bool | None = Query(None),
    start_date_from: date | None = Query(None),
    start_date_to: date | None = Query(None),
    include_removed: bool = Query(False, description="Include status = 0 rows"),
) -> Page[MaintenanceRequestRead]:
    rows, total = svc.list_maintenance_requests(
        db,
        page=page,
        page_size=page_size,
        request_type=request_type,
        facility_id=facility_id,
        department_id=department_id,
        category_id=category_id,
        request_status=request_status,
        assigned_to=assigned_to,
        amenity_id=amenity_id,
        is_recurring=is_recurring,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        include_removed=include_removed,
    )
    return Page[MaintenanceRequestRead](
        items=_assemble(db, rows), page=page, page_size=page_size, total=total
    )


@maintenance_requests_router.get(
    "/{request_id}",
    response_model=MaintenanceRequestRead,
    responses=NOT_FOUND,
    summary="Get one planned service",
)
def get_maintenance_request(
    request_id: uuid.UUID, db: DbSession
) -> MaintenanceRequestRead:
    return _one(db, request_id)


@maintenance_requests_write_router.post(
    "",
    response_model=MaintenanceRequestRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=PLANNING_WRITE,
    summary="Create a planned service",
    description=(
        "Inserts `maintenance_request` plus one `maintenance_request_amenity` "
        "per room, one `maintenance_request_assignee` per assignee and, when a "
        "recurrence is supplied, the 1:1 `maintenance_request_recurrence` row -- "
        "all in one transaction. The request opens at service_status Assigned "
        "when assignees are named, otherwise Pending. `is_recurring` and "
        "`is_room` are DERIVED, never sent."
    ),
)
def create_maintenance_request(
    payload: MaintenanceRequestCreate, db: DbSession, current_user: CurrentUser
) -> MaintenanceRequestRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    data = payload.model_dump()
    if payload.recurrence is not None:
        data["recurrence"] = payload.recurrence.model_dump()
    request = write_svc.create_maintenance_request(
        db, data=data, actor_id=current_user.id, facility_id=facility_id
    )
    return _one(db, request.id)


@maintenance_requests_write_router.patch(
    "/{request_id}",
    response_model=MaintenanceRequestRead,
    dependencies=PLANNING_WRITE,
    summary="Update a planned service",
    description=(
        "Only the fields sent are written. `amenity_ids` / `assignee_ids` "
        "REPLACE that list; `recurrence: null` drops the rule while omitting the "
        "key leaves it untouched. `completed_on` is stamped on reaching "
        "Completed and cleared on leaving it."
    ),
)
def update_maintenance_request(
    request_id: uuid.UUID,
    payload: MaintenanceRequestUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> MaintenanceRequestRead:
    changes = payload.model_dump(exclude_unset=True)
    if "recurrence" in changes and payload.recurrence is not None:
        changes["recurrence"] = payload.recurrence.model_dump()
    write_svc.update_maintenance_request(
        db, request_id, changes=changes, actor_id=current_user.id
    )
    return _one(db, request_id)


@maintenance_requests_write_router.post(
    "/{request_id}/cancel",
    response_model=MaintenanceRequestRead,
    dependencies=PLANNING_WRITE,
    summary="Cancel a planned service",
    description="Moves it to service_status Canceled; the row and links remain.",
)
def cancel_maintenance_request(
    request_id: uuid.UUID,
    payload: CancelBody,
    db: DbSession,
    current_user: CurrentUser,
) -> MaintenanceRequestRead:
    write_svc.cancel_maintenance_request(
        db, request_id, reason=payload.reason, actor_id=current_user.id
    )
    return _one(db, request_id)


@maintenance_requests_write_router.delete(
    "/{request_id}",
    response_model=MaintenanceRequestRead,
    dependencies=PLANNING_WRITE,
    summary="Remove a planned service (soft delete)",
    description=(
        "Sets `status = 0` and records `delete_comments`, and retires the room "
        "and assignee links with it. Nothing is physically deleted -- the child "
        "tables reference this row ON DELETE RESTRICT. The row disappears from "
        "the list unless `include_removed=true`."
    ),
)
def remove_maintenance_request(
    request_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    comments: str | None = Query(None, max_length=2000, description="Audit note"),
) -> MaintenanceRequestRead:
    write_svc.remove_maintenance_request(
        db, request_id, comments=comments, actor_id=current_user.id
    )
    return _one(db, request_id)
