"""Job Order Management read and write APIs (`job_order`).

    GET    /api/v1/job-orders            list, filterable and searchable
    GET    /api/v1/job-orders/{id}       one job order, fully assembled
    POST   /api/v1/job-orders            create (rooms + devices in one txn)
    PATCH  /api/v1/job-orders/{id}       edit, reassign, complete
    DELETE /api/v1/job-orders/{id}       soft delete (status = 0)

Three tables back this screen -- `job_order`, `job_order_amenity` and
`job_order_device` (blueprint §5, tables 60-62). All three already held seeded
rows; what was missing was a router, which is why the screen showed a
"not connected" notice.

RBAC: the `job_order` module, read for GET and write for the mutations. That
name is the real `role_module.module_name` seeded in `people.py` (granted to
both the Admin and Manager roles) and is already the module the frontend route
`/config/job-order` maps to -- nothing new was registered.

Read and write live in one file because they are one screen and share the
assembly helper below, exactly as `maintenance.py` does.

DELETE is a SOFT delete. Both link tables reference `job_order.id` ON DELETE
RESTRICT, so a physical delete would require destroying the record of which
rooms and devices the job covered. `status = 0` matches how /holidays, the
catalogue and /maintenance-requests retire rows.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, UserRef
from app.schemas.health import ErrorResponse
from app.schemas.job_order import (
    JobOrderCreate,
    JobOrderRead,
    JobOrderStatus,
    JobOrderTypeOfWork,
    JobOrderUpdate,
)
from app.services import job_order as svc
from app.services import job_order_write as write_svc

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

JOB_ORDER_READ = [Depends(require_permission("job_order", "read"))]
JOB_ORDER_WRITE = [Depends(require_permission("job_order", "write"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

job_orders_router = APIRouter(
    prefix="/job-orders",
    tags=["job-orders"],
    dependencies=JOB_ORDER_READ,
    responses=AUTH_RESPONSES,
)
job_orders_write_router = APIRouter(
    prefix="/job-orders", tags=["job-orders"], responses=WRITE_RESPONSES
)


def _assemble(db, rows) -> list[JobOrderRead]:
    """Attach rooms and devices to a page of job orders.

    Two batched queries for the whole page, not two per row.
    """
    ids = [row["id"] for row in rows]
    rooms = svc.rooms_for(db, ids)
    devices = svc.devices_for(db, ids)
    assembled = []
    for row in rows:
        data = dict(row)
        first = data.pop("assignee_first_name", None)
        last = data.pop("assignee_last_name", None)
        emp_id = data.pop("assignee_emp_id", None)
        assignee = None
        if data.get("assigned_to") is not None:
            assignee = UserRef(
                id=data["assigned_to"],
                name=" ".join(part for part in (first, last) if part) or "Unknown",
                emp_id=emp_id,
            )
        job_rooms = rooms.get(row["id"], [])
        job_devices = devices.get(row["id"], [])
        assembled.append(
            JobOrderRead(
                **data,
                assignee=assignee,
                rooms=job_rooms,
                devices=job_devices,
                room_count=len(job_rooms),
                device_count=len(job_devices),
            )
        )
    return assembled


def _one(db, job_order_id: uuid.UUID) -> JobOrderRead:
    """Return through the read projection so a write cannot widen the payload."""
    row = svc.get_job_order(db, job_order_id)
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Job order {job_order_id} does not exist.",
        )
    return _assemble(db, [row])[0]


@job_orders_router.get(
    "",
    response_model=Page[JobOrderRead],
    summary="List job orders",
    description=(
        "One row per `job_order`, with its rooms (`job_order_amenity`) and "
        "devices (`job_order_device`) attached. `facility_id` filters THROUGH "
        "the rooms, because `job_order` has no facility column of its own. "
        "Soft-deleted rows (status = 0) are excluded unless `include_removed=true`."
    ),
)
def list_job_orders(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    job_order_status: JobOrderStatus | None = Query(None, description="Work lifecycle"),
    type_of_work: JobOrderTypeOfWork | None = Query(None),
    assigned_to: uuid.UUID | None = Query(None, description="app_user.id"),
    amenity_id: uuid.UUID | None = Query(None, description="Via job_order_amenity"),
    device_id: uuid.UUID | None = Query(None, description="Via job_order_device"),
    facility_id: uuid.UUID | None = Query(None, description="Via the job's rooms"),
    search: str | None = Query(None, description="order_reference or description"),
    include_removed: bool = Query(False, description="Include status = 0 rows"),
) -> Page[JobOrderRead]:
    rows, total = svc.list_job_orders(
        db,
        page=page,
        page_size=page_size,
        job_order_status=job_order_status,
        type_of_work=type_of_work,
        assigned_to=assigned_to,
        amenity_id=amenity_id,
        device_id=device_id,
        facility_id=facility_id,
        search=search,
        include_removed=include_removed,
    )
    return Page[JobOrderRead](
        items=_assemble(db, rows), page=page, page_size=page_size, total=total
    )


@job_orders_router.get(
    "/{job_order_id}",
    response_model=JobOrderRead,
    responses=NOT_FOUND,
    summary="Get one job order",
)
def get_job_order(job_order_id: uuid.UUID, db: DbSession) -> JobOrderRead:
    return _one(db, job_order_id)


@job_orders_write_router.post(
    "",
    response_model=JobOrderRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=JOB_ORDER_WRITE,
    summary="Create a job order",
    description=(
        "Inserts `job_order` plus one `job_order_amenity` per room and one "
        "`job_order_device` per device, in one transaction. `amenity_ids` and "
        "`device_ids` are real `amenity.id` / `device.id` UUIDs -- a room number "
        "or a device-type name is rejected by UUID parsing.\n\n"
        "`order_reference` is optional and continues the seeded `JO-YYYY-NNNN` "
        "sequence when omitted. The NOT NULL `authentication_code` column is "
        "derived from the reference server-side -- it is the technician's on-site "
        "code, so it is neither accepted from the client nor returned in any "
        "response. `job_order_status` always opens at `pending`."
    ),
)
def create_job_order(
    payload: JobOrderCreate, db: DbSession, current_user: CurrentUser
) -> JobOrderRead:
    job = write_svc.create_job_order(
        db, data=payload.model_dump(), actor_id=current_user.id
    )
    return _one(db, job.id)


@job_orders_write_router.patch(
    "/{job_order_id}",
    response_model=JobOrderRead,
    dependencies=JOB_ORDER_WRITE,
    summary="Update a job order",
    description=(
        "Only the fields sent are written. `amenity_ids` / `device_ids` REPLACE "
        "that whole list; omitting them leaves the existing links untouched. "
        "`completed_on` is stamped on reaching `completed` and cleared on "
        "leaving it. A removed job order cannot be edited (409)."
    ),
)
def update_job_order(
    job_order_id: uuid.UUID,
    payload: JobOrderUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> JobOrderRead:
    write_svc.update_job_order(
        db,
        job_order_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return _one(db, job_order_id)


@job_orders_write_router.delete(
    "/{job_order_id}",
    response_model=JobOrderRead,
    dependencies=JOB_ORDER_WRITE,
    summary="Remove a job order (soft delete)",
    description=(
        "Sets `status = 0`. Nothing is physically deleted -- `job_order_amenity` "
        "and `job_order_device` reference this row ON DELETE RESTRICT, and the "
        "links are kept so the record of what the job covered survives. The row "
        "disappears from the list unless `include_removed=true`."
    ),
)
def remove_job_order(job_order_id: uuid.UUID, db: DbSession) -> JobOrderRead:
    write_svc.remove_job_order(db, job_order_id)
    return _one(db, job_order_id)
