"""Read logic for Services Planning (`maintenance_request` and friends).

FOUR TABLES, NOT ONE. IKANOS splits a planned service across:

    maintenance_request              the request itself
    maintenance_request_recurrence   its recurrence rule (1:1, optional)
    maintenance_request_amenity      the rooms it covers (0..N)
    maintenance_request_assignee     the staff assigned (0..N)

The three Services Planning tabs are the `maintenance_request_type` enum --
`scheduled`, `planned`, `disinfection` -- not three separate tables.

TWO INDEPENDENT STATUS COLUMNS, deliberately kept apart:

    maintenance_request_status  FK -> service_status (1 Pending .. 5 Canceled)
    status                      the soft-delete flag (1 live, 0 removed)

There is NO `service_type_id` on `maintenance_request`; the model's own
docstring records that the Phase 1 column had no IKANOS counterpart. The link
to the catalogue is `category_id` -> `service_category` and `item_id` ->
`service_category_item`, so "Facility Services" on the form is a category and
"Service Type" is read from that category's `service_type`.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AppUser,
    Department,
    MaintenanceRequest,
    MaintenanceRequestAmenity,
    MaintenanceRequestAssignee,
    MaintenanceRequestRecurrence,
    ServiceCategory,
    ServiceCategoryItem,
    ServiceStatus,
    ServiceType,
)

#: `days_of_week` is a BITMASK, not a day number: the one seeded recurrence row
#: stores 18, which is Monday (2) + Thursday (16). Sunday is the low bit, which
#: is the order `occasion`/scheduler rows elsewhere in the schema also use.
WEEKDAY_BITS = [
    (1, "Sun"), (2, "Mon"), (4, "Tue"), (8, "Wed"),
    (16, "Thu"), (32, "Fri"), (64, "Sat"),
]


def decode_days_of_week(mask: int | None) -> list[str]:
    """Turn the stored bitmask into day labels. Empty when nothing is set."""
    if not mask:
        return []
    return [label for bit, label in WEEKDAY_BITS if mask & bit]


def encode_days_of_week(days: list[str] | None) -> int | None:
    """Inverse of `decode_days_of_week`, for the write path."""
    if not days:
        return None
    wanted = {day.strip().lower()[:3] for day in days}
    mask = sum(bit for bit, label in WEEKDAY_BITS if label.lower() in wanted)
    return mask or None


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


def _request_stmt() -> Select:
    """One row per request, with every display name resolved by the database.

    `service_type` is reached THROUGH the category, because the request table
    has no service-type column of its own.
    """
    return (
        select(
            MaintenanceRequest.id,
            MaintenanceRequest.maintenance_request_type,
            MaintenanceRequest.maintenance_start_date,
            MaintenanceRequest.maintenance_end_date,
            MaintenanceRequest.maintenance_start_time,
            MaintenanceRequest.maintenance_end_time,
            MaintenanceRequest.is_recurring,
            MaintenanceRequest.department_id,
            Department.department_name.label("department_name"),
            MaintenanceRequest.category_id,
            ServiceCategory.category_name.label("category_name"),
            ServiceCategory.service_type.label("service_type"),
            ServiceType.name.label("service_type_name"),
            MaintenanceRequest.item_id,
            ServiceCategoryItem.item_name.label("item_name"),
            MaintenanceRequest.facility_id,
            MaintenanceRequest.completed_on,
            MaintenanceRequest.is_room,
            MaintenanceRequest.non_room_comments,
            MaintenanceRequest.parent_id,
            MaintenanceRequest.maintenance_request_status,
            ServiceStatus.name.label("status_name"),
            MaintenanceRequest.status_reason,
            MaintenanceRequest.delete_comments,
            MaintenanceRequest.under_maintenance,
            MaintenanceRequest.status,
            MaintenanceRequest.created_on,
            MaintenanceRequest.updated_on,
        )
        .select_from(MaintenanceRequest)
        .outerjoin(Department, Department.id == MaintenanceRequest.department_id)
        .outerjoin(ServiceCategory, ServiceCategory.id == MaintenanceRequest.category_id)
        .outerjoin(ServiceType, ServiceType.id == ServiceCategory.service_type)
        .outerjoin(
            ServiceCategoryItem, ServiceCategoryItem.id == MaintenanceRequest.item_id
        )
        .outerjoin(
            ServiceStatus,
            ServiceStatus.id == MaintenanceRequest.maintenance_request_status,
        )
    )


def list_maintenance_requests(
    db: Session,
    *,
    page: int,
    page_size: int,
    request_type: str | None = None,
    facility_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    request_status: int | None = None,
    assigned_to: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    is_recurring: bool | None = None,
    start_date_from=None,
    start_date_to=None,
    include_removed: bool = False,
):
    stmt = _request_stmt().order_by(
        MaintenanceRequest.maintenance_start_date.desc().nullslast(),
        MaintenanceRequest.created_on.desc(),
    )
    # Soft-deleted rows stay out unless explicitly asked for, the same rule the
    # rest of the catalogue read endpoints follow.
    if not include_removed:
        stmt = stmt.where(MaintenanceRequest.status == 1)
    if request_type:
        stmt = stmt.where(MaintenanceRequest.maintenance_request_type == request_type)
    if facility_id:
        stmt = stmt.where(MaintenanceRequest.facility_id == facility_id)
    if department_id:
        stmt = stmt.where(MaintenanceRequest.department_id == department_id)
    if category_id:
        stmt = stmt.where(MaintenanceRequest.category_id == category_id)
    if request_status is not None:
        stmt = stmt.where(
            MaintenanceRequest.maintenance_request_status == request_status
        )
    if is_recurring is not None:
        stmt = stmt.where(MaintenanceRequest.is_recurring == (1 if is_recurring else 0))
    if start_date_from:
        stmt = stmt.where(MaintenanceRequest.maintenance_start_date >= start_date_from)
    if start_date_to:
        stmt = stmt.where(MaintenanceRequest.maintenance_start_date <= start_date_to)
    if assigned_to:
        stmt = stmt.where(
            select(MaintenanceRequestAssignee.id)
            .where(
                MaintenanceRequestAssignee.maintenance_request_id
                == MaintenanceRequest.id,
                MaintenanceRequestAssignee.app_user_id == assigned_to,
                MaintenanceRequestAssignee.status == 1,
            )
            .exists()
        )
    if amenity_id:
        stmt = stmt.where(
            select(MaintenanceRequestAmenity.id)
            .where(
                MaintenanceRequestAmenity.maintenance_request_id
                == MaintenanceRequest.id,
                MaintenanceRequestAmenity.amenity_id == amenity_id,
                MaintenanceRequestAmenity.status == 1,
            )
            .exists()
        )

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_maintenance_request(db: Session, request_id: uuid.UUID):
    return (
        db.execute(_request_stmt().where(MaintenanceRequest.id == request_id))
        .mappings()
        .one_or_none()
    )


def rooms_for(db: Session, request_ids: list[uuid.UUID]) -> dict:
    """Rooms per request, batched -- one query for a whole page."""
    if not request_ids:
        return {}
    rows = db.execute(
        select(
            MaintenanceRequestAmenity.maintenance_request_id,
            MaintenanceRequestAmenity.amenity_id,
            Amenity.name.label("room_name"),
        )
        .join(Amenity, Amenity.id == MaintenanceRequestAmenity.amenity_id)
        .where(
            MaintenanceRequestAmenity.maintenance_request_id.in_(request_ids),
            MaintenanceRequestAmenity.status == 1,
        )
        .order_by(Amenity.name)
    ).mappings().all()
    grouped: dict = defaultdict(list)
    for row in rows:
        grouped[row["maintenance_request_id"]].append(
            {"amenity_id": row["amenity_id"], "room_name": row["room_name"]}
        )
    return grouped


def assignees_for(db: Session, request_ids: list[uuid.UUID]) -> dict:
    """Assigned staff per request. Only (id, name, emp_id) -- the same `UserRef`
    shape every other endpoint returns, so no contact detail leaks."""
    if not request_ids:
        return {}
    rows = db.execute(
        select(
            MaintenanceRequestAssignee.maintenance_request_id,
            AppUser.id,
            AppUser.first_name,
            AppUser.last_name,
            AppUser.emp_id,
        )
        .join(AppUser, AppUser.id == MaintenanceRequestAssignee.app_user_id)
        .where(
            MaintenanceRequestAssignee.maintenance_request_id.in_(request_ids),
            MaintenanceRequestAssignee.status == 1,
        )
        .order_by(AppUser.first_name)
    ).mappings().all()
    grouped: dict = defaultdict(list)
    for row in rows:
        name = " ".join(filter(None, [row["first_name"], row["last_name"]]))
        grouped[row["maintenance_request_id"]].append(
            {"id": row["id"], "name": name, "emp_id": row["emp_id"]}
        )
    return grouped


def recurrences_for(db: Session, request_ids: list[uuid.UUID]) -> dict:
    """The 1:1 recurrence rule, where one exists."""
    if not request_ids:
        return {}
    rows = db.execute(
        select(MaintenanceRequestRecurrence).where(
            MaintenanceRequestRecurrence.maintenance_request_id.in_(request_ids)
        )
    ).scalars().all()
    return {
        row.maintenance_request_id: {
            "recurrence_type": row.recurrence_type,
            "days_of_week": row.days_of_week,
            "day_labels": decode_days_of_week(row.days_of_week),
            "max_no_of_occurrences": row.max_no_of_occurrences,
        }
        for row in rows
    }
