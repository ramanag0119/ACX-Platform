"""Write logic for Services Planning.

Rules taken from the schema and the three seeded rows, not invented:

* `maintenance_request_type` is the enum `scheduled | planned | disinfection` --
  the three Services Planning tabs. Nothing else is a valid type.
* `maintenance_request_status` is a FK to `service_status`: 1 Pending,
  2 Assigned, 3 Partially completed, 4 Completed, 5 Canceled. A new request
  opens at Pending, and naming assignees moves it to Assigned -- exactly what
  the seeded rows show (the row with assignees and no completion sits at 2, the
  completed one at 4 with `completed_on` stamped).
* `completed_on` is stamped on reaching Completed and cleared on leaving it, the
  same invariant `services_write` enforces for `service_request`.
* `item_id` must belong to `category_id`; the seeded rows never mix them.
* `is_recurring` and `maintenance_request_recurrence` move together: the flag is
  derived from whether a rule was supplied, so the two can never disagree.
  `recurrence_type` has exactly one label in the enum, `weekly`.
* `is_room` is derived: 1 when rooms are attached, 0 when the request carries
  `non_room_comments` instead. The seeded rows all have is_room = 1 with rooms.
* DELETE is the project's soft delete -- `status = 0` plus `delete_comments` --
  because `maintenance_request` is referenced by its own recurrence, amenity and
  assignee rows (all ON DELETE RESTRICT). Nothing is physically removed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
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
)
from app.services.maintenance import encode_days_of_week
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    require_exists,
    require_row,
    transaction,
)

#: `service_status` ids, the same lookup the service-request writes use.
STATUS_PENDING = 1
STATUS_ASSIGNED = 2
STATUS_COMPLETED = 4
STATUS_CANCELLED = 5

LIVE = 1
REMOVED = 0


def _validate_status(db: Session, status_id: int | None) -> None:
    if status_id is None:
        return
    if db.get(ServiceStatus, status_id) is None:
        raise Invalid(f"Service status {status_id} does not exist.")


def _validate_item_matches_category(
    db: Session, item_id: uuid.UUID | None, category_id: uuid.UUID | None
) -> None:
    """An item belongs to exactly one category; the pair must agree."""
    if item_id is None:
        return
    item = db.get(ServiceCategoryItem, item_id)
    if item is None:
        raise Invalid(f"Service item {item_id} does not exist.")
    if category_id is not None and item.category_id != category_id:
        raise Invalid(
            f"Service item {item_id} belongs to category {item.category_id}, "
            f"not {category_id}."
        )


def _validate_rooms(db: Session, amenity_ids: list[uuid.UUID]) -> None:
    for amenity_id in amenity_ids:
        if db.get(Amenity, amenity_id) is None:
            raise Invalid(f"Room {amenity_id} does not exist.")


def _validate_assignees(db: Session, user_ids: list[uuid.UUID]) -> None:
    for user_id in user_ids:
        user = db.get(AppUser, user_id)
        if user is None:
            raise Invalid(f"User {user_id} does not exist.")
        # Planning work is assigned to staff; a guest is not assignable.
        if not user.is_staff:
            raise Invalid(f"User {user_id} is not staff and cannot be assigned.")


def _replace_rooms(
    db: Session,
    request_id: uuid.UUID,
    amenity_ids: list[uuid.UUID],
    actor_id: uuid.UUID,
) -> None:
    """Set the room list to exactly `amenity_ids`.

    Existing rows are retired with `status = 0` rather than deleted: the link
    table is ON DELETE RESTRICT and its rows are audit history.
    """
    existing = db.execute(
        select(MaintenanceRequestAmenity).where(
            MaintenanceRequestAmenity.maintenance_request_id == request_id
        )
    ).scalars().all()
    wanted = set(amenity_ids)
    for row in existing:
        if row.amenity_id in wanted:
            row.status = LIVE
            wanted.discard(row.amenity_id)
        else:
            row.status = REMOVED
    for amenity_id in amenity_ids:
        if amenity_id in wanted:
            db.add(
                MaintenanceRequestAmenity(
                    maintenance_request_id=request_id,
                    amenity_id=amenity_id,
                    status=LIVE,
                    created_by=actor_id,
                )
            )
            wanted.discard(amenity_id)


def _replace_assignees(
    db: Session,
    request_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    actor_id: uuid.UUID,
) -> None:
    """Same reactivate-or-retire rule as the rooms."""
    existing = db.execute(
        select(MaintenanceRequestAssignee).where(
            MaintenanceRequestAssignee.maintenance_request_id == request_id
        )
    ).scalars().all()
    wanted = set(user_ids)
    for row in existing:
        if row.app_user_id in wanted:
            row.status = LIVE
            wanted.discard(row.app_user_id)
        else:
            row.status = REMOVED
    for user_id in user_ids:
        if user_id in wanted:
            db.add(
                MaintenanceRequestAssignee(
                    maintenance_request_id=request_id,
                    app_user_id=user_id,
                    status=LIVE,
                    created_by=actor_id,
                )
            )
            wanted.discard(user_id)


def _set_recurrence(
    db: Session, request: MaintenanceRequest, recurrence: dict | None
) -> None:
    """Create, update or drop the 1:1 rule, keeping `is_recurring` in step."""
    row = db.get(MaintenanceRequestRecurrence, request.id)
    if recurrence is None:
        if row is not None:
            db.delete(row)
        request.is_recurring = 0
        return

    mask = recurrence.get("days_of_week")
    if mask is None:
        mask = encode_days_of_week(recurrence.get("day_labels"))
    values = {
        "recurrence_type": recurrence.get("recurrence_type", "weekly"),
        "days_of_week": mask,
        "max_no_of_occurrences": recurrence.get("max_no_of_occurrences"),
    }
    if row is None:
        db.add(
            MaintenanceRequestRecurrence(
                maintenance_request_id=request.id, **values
            )
        )
    else:
        for key, value in values.items():
            setattr(row, key, value)
    request.is_recurring = 1


def create_maintenance_request(
    db: Session,
    *,
    data: dict,
    actor_id: uuid.UUID,
    facility_id: uuid.UUID,
) -> MaintenanceRequest:
    rooms: list[uuid.UUID] = data.pop("amenity_ids", None) or []
    assignees: list[uuid.UUID] = data.pop("assignee_ids", None) or []
    recurrence: dict | None = data.pop("recurrence", None)

    require_exists(db, Department, data.get("department_id"), "Department")
    require_exists(db, ServiceCategory, data.get("category_id"), "Service category")
    _validate_item_matches_category(db, data.get("item_id"), data.get("category_id"))
    _validate_rooms(db, rooms)
    _validate_assignees(db, assignees)

    start = data.get("maintenance_start_date")
    end = data.get("maintenance_end_date")
    if start and end and end < start:
        raise Invalid("maintenance_end_date cannot be before maintenance_start_date.")

    with transaction(db):
        request = MaintenanceRequest(
            **data,
            facility_id=facility_id,
            # Assigning at creation opens the request at Assigned, matching the
            # seeded rows; otherwise it opens at Pending.
            maintenance_request_status=STATUS_ASSIGNED if assignees else STATUS_PENDING,
            is_room=1 if rooms else 0,
            status=LIVE,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(request)
        db.flush()

        if rooms:
            _replace_rooms(db, request.id, rooms, actor_id)
        if assignees:
            _replace_assignees(db, request.id, assignees, actor_id)
        _set_recurrence(db, request, recurrence)

    return request


def update_maintenance_request(
    db: Session,
    request_id: uuid.UUID,
    *,
    changes: dict,
    actor_id: uuid.UUID,
) -> MaintenanceRequest:
    request = require_row(db, MaintenanceRequest, request_id, "Maintenance request")
    if request.status == REMOVED:
        raise Conflict("This planned service has been removed and cannot be edited.")

    rooms = changes.pop("amenity_ids", None)
    assignees = changes.pop("assignee_ids", None)
    # `recurrence` present-and-null means "drop the rule"; absent means
    # "leave it alone", which is why exclude_unset matters at the endpoint.
    has_recurrence_key = "recurrence" in changes
    recurrence = changes.pop("recurrence", None)

    if "department_id" in changes:
        require_exists(db, Department, changes["department_id"], "Department")
    category_id = changes.get("category_id", request.category_id)
    if "category_id" in changes:
        require_exists(db, ServiceCategory, changes["category_id"], "Service category")
    if "item_id" in changes:
        _validate_item_matches_category(db, changes["item_id"], category_id)
    if "maintenance_request_status" in changes:
        _validate_status(db, changes["maintenance_request_status"])
    if rooms is not None:
        _validate_rooms(db, rooms)
    if assignees is not None:
        _validate_assignees(db, assignees)

    start = changes.get("maintenance_start_date", request.maintenance_start_date)
    end = changes.get("maintenance_end_date", request.maintenance_end_date)
    if start and end and end < start:
        raise Invalid("maintenance_end_date cannot be before maintenance_start_date.")

    with transaction(db):
        apply_changes(request, changes)

        if rooms is not None:
            _replace_rooms(db, request.id, rooms, actor_id)
            request.is_room = 1 if rooms else 0
        if assignees is not None:
            _replace_assignees(db, request.id, assignees, actor_id)
            # First assignment moves an untouched request to Assigned.
            if assignees and request.maintenance_request_status == STATUS_PENDING:
                request.maintenance_request_status = STATUS_ASSIGNED
        if has_recurrence_key:
            _set_recurrence(db, request, recurrence)

        # Same completion invariant as `service_request`.
        if request.maintenance_request_status == STATUS_COMPLETED:
            if request.completed_on is None:
                request.completed_on = datetime.now(UTC)
        else:
            request.completed_on = None

        request.updated_by = actor_id

    return request


def cancel_maintenance_request(
    db: Session,
    request_id: uuid.UUID,
    *,
    reason: str | None,
    actor_id: uuid.UUID,
) -> MaintenanceRequest:
    """Move the request to Canceled, leaving the row and its links in place."""
    request = require_row(db, MaintenanceRequest, request_id, "Maintenance request")
    if request.maintenance_request_status == STATUS_COMPLETED:
        raise Conflict("A completed planned service cannot be cancelled.")
    with transaction(db):
        request.maintenance_request_status = STATUS_CANCELLED
        request.status_reason = reason
        request.completed_on = None
        request.updated_by = actor_id
    return request


def remove_maintenance_request(
    db: Session,
    request_id: uuid.UUID,
    *,
    comments: str | None,
    actor_id: uuid.UUID,
) -> MaintenanceRequest:
    """The project's soft delete: `status = 0`, with the reason recorded.

    A hard DELETE is impossible without breaking referential integrity --
    `maintenance_request_recurrence`, `_amenity` and `_assignee` all reference
    this row ON DELETE RESTRICT, and a recurrence instance may point at it via
    `parent_id`. The row keeps its history and drops out of every list.
    """
    request = require_row(db, MaintenanceRequest, request_id, "Maintenance request")
    if request.status == REMOVED:
        raise Conflict("This planned service has already been removed.")
    with transaction(db):
        request.status = REMOVED
        request.delete_comments = comments
        request.updated_by = actor_id
        # Its links go with it, so nothing dangles in the join tables.
        for row in db.execute(
            select(MaintenanceRequestAmenity).where(
                MaintenanceRequestAmenity.maintenance_request_id == request_id
            )
        ).scalars().all():
            row.status = REMOVED
        for row in db.execute(
            select(MaintenanceRequestAssignee).where(
                MaintenanceRequestAssignee.maintenance_request_id == request_id
            )
        ).scalars().all():
            row.status = REMOVED
    return request
