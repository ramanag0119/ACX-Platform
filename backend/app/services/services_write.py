"""Write logic for service requests and the service catalogue.

Rules taken from the schema and the seeded IKANOS rows, not invented:

* `service_status` is the lookup: 1 Pending, 2 Assigned, 3 Partially completed,
  4 Completed, 5 Canceled. Nothing else is a valid status.
* Every seeded request with `completed_on` set is status 4, and no other status
  has it. So `completed_on` is stamped when a request reaches Completed and
  cleared if it moves back out of Completed.
* Assigning a request means both `assigned_to` and status Assigned -- every
  seeded row that carries an assignee sits at status 2 or beyond.
* `ref_number` follows the seeded `SR-YYYY-NNNN` format.
* `service_request.category_id` must belong to the request's `service_type`;
  the seeded rows never mix them.
* Item lines live in `service_request_item` with their own `quantity` and
  `price_per_unit`; the price is copied from `service_category_item` at
  creation time (the catalogue price is the only price the schema knows).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AppUser,
    Department,
    PromoCode,
    ServiceCategory,
    ServiceCategoryItem,
    ServiceRequest,
    ServiceRequestItem,
    ServiceStatus,
    ServiceType,
    Stay,
)
from app.services.writes import (
    Invalid,
    apply_changes,
    ensure_unique,
    next_yearly_reference,
    require_exists,
    require_row,
    transaction,
)

#: `service_status` ids, read from the seeded lookup rather than hardcoded text.
STATUS_PENDING = 1
STATUS_ASSIGNED = 2
STATUS_PARTIAL = 3
STATUS_COMPLETED = 4
STATUS_CANCELLED = 5


def _validate_status(db: Session, status_id: int | None) -> None:
    if status_id is None:
        return
    if db.get(ServiceStatus, status_id) is None:
        raise Invalid(f"Service status {status_id} does not exist.")


def _validate_category_matches_type(
    db: Session, category_id: uuid.UUID | None, service_type: int | None
) -> None:
    if category_id is None:
        return
    category = db.get(ServiceCategory, category_id)
    if category is None:
        raise Invalid(f"Service category {category_id} does not exist.")
    if service_type is not None and category.service_type != service_type:
        raise Invalid(
            "Service category belongs to a different service type "
            f"({category.service_type}), not {service_type}."
        )


def create_service_request(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> ServiceRequest:
    """Raise a request (the Tickets screen and the guest-side flow both land here)."""
    items: list[dict] = data.pop("items", None) or []

    with transaction(db):
        if db.get(ServiceType, data["service_type"]) is None:
            raise Invalid(f"Service type {data['service_type']} does not exist.")
        _validate_category_matches_type(db, data.get("category_id"), data["service_type"])
        require_exists(db, Amenity, data.get("amenity_id"), "Room")
        require_exists(db, Stay, data.get("stay_id"), "Stay")
        require_exists(db, Department, data.get("department_id"), "Department")
        require_exists(db, AppUser, data.get("assigned_to"), "Assignee")
        require_exists(db, AppUser, data.get("app_user_id"), "Requester")
        require_exists(db, PromoCode, data.get("promo_code_id"), "Promo code")
        _validate_status(db, data.get("status"))

        # An assignee implies the request is assigned, which is what every
        # seeded row with an assignee shows.
        if data.get("status") is None:
            data["status"] = STATUS_ASSIGNED if data.get("assigned_to") else STATUS_PENDING

        ref_number = data.pop("ref_number", None) or next_yearly_reference(
            db, ServiceRequest.ref_number, "SR", year=datetime.now(UTC).year
        )
        ensure_unique(db, ServiceRequest, ServiceRequest.ref_number, ref_number, "Reference")

        request = ServiceRequest(
            id=uuid.uuid4(),
            ref_number=ref_number,
            facility_id=data.pop("facility_id", None) or facility_id,
            request_source=data.pop("request_source", None) or "ikanos",
            created_by=actor_id,
            updated_by=actor_id,
            **data,
        )
        db.add(request)
        db.flush()

        for line in items:
            _add_item(db, request, line)
        _recalculate_amounts(db, request)

    db.refresh(request)
    return request


def _add_item(db: Session, request: ServiceRequest, line: dict) -> ServiceRequestItem:
    item_id = line.get("item_id")
    catalogue_item = None
    if item_id is not None:
        catalogue_item = db.get(ServiceCategoryItem, item_id)
        if catalogue_item is None:
            raise Invalid(f"Service item {item_id} does not exist.")

    row = ServiceRequestItem(
        id=uuid.uuid4(),
        service_request_id=request.id,
        item_id=item_id,
        category_id=line.get("category_id")
        or (catalogue_item.category_id if catalogue_item else request.category_id),
        quantity=line.get("quantity", 1),
        # The catalogue price is the only price in the schema. It is copied at
        # creation so a later catalogue change cannot rewrite history.
        price_per_unit=line.get("price_per_unit")
        or (catalogue_item.price_per_unit if catalogue_item else None),
        assigned_to=line.get("assigned_to"),
        status=line.get("status") or request.status,
    )
    db.add(row)
    return row


def _recalculate_amounts(db: Session, request: ServiceRequest) -> None:
    """Sum the request's item lines into `net_amount` / `total_amount`.

    Only quantity x price_per_unit, both stored columns. NO tax rate exists in
    the schema, so `total_tax` is left exactly as it is and never derived.
    """
    # The session runs with autoflush off, so pending item rows must be flushed
    # before they can be summed.
    db.flush()
    lines = db.execute(
        select(ServiceRequestItem).where(ServiceRequestItem.service_request_id == request.id)
    ).scalars().all()
    if not lines:
        return
    net = sum(
        (line.quantity or 0) * (line.price_per_unit or 0)
        for line in lines
        if line.price_per_unit is not None
    )
    request.net_amount = net
    tax = request.total_tax or 0
    request.total_amount = net + tax


def update_service_request(
    db: Session, request_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> ServiceRequest:
    """Edit, assign, or move a request through its status."""
    with transaction(db):
        request = require_row(db, ServiceRequest, request_id, "Service request")

        require_exists(db, AppUser, changes.get("assigned_to"), "Assignee")
        require_exists(db, Department, changes.get("department_id"), "Department")
        require_exists(db, Amenity, changes.get("amenity_id"), "Room")
        _validate_status(db, changes.get("status"))
        if "category_id" in changes:
            _validate_category_matches_type(
                db, changes["category_id"], changes.get("service_type", request.service_type)
            )

        # Assigning someone moves a still-pending request to Assigned.
        if changes.get("assigned_to") and "status" not in changes:
            if request.status in (None, STATUS_PENDING):
                changes["status"] = STATUS_ASSIGNED

        new_status = changes.get("status", request.status)
        apply_changes(request, changes)

        # `completed_on` tracks the Completed status, exactly as the seeded
        # rows do -- set on the way in, cleared on the way out.
        if new_status == STATUS_COMPLETED and request.completed_on is None:
            request.completed_on = datetime.now(UTC)
        elif new_status != STATUS_COMPLETED:
            request.completed_on = None

        request.updated_by = actor_id
        _recalculate_amounts(db, request)

    db.refresh(request)
    return request


def replace_service_request_items(
    db: Session, request_id: uuid.UUID, *, items: list[dict], actor_id: uuid.UUID
) -> ServiceRequest:
    with transaction(db):
        request = require_row(db, ServiceRequest, request_id, "Service request")
        db.execute(
            delete(ServiceRequestItem).where(
                ServiceRequestItem.service_request_id == request_id
            )
        )
        db.flush()
        for line in items:
            _add_item(db, request, line)
        request.updated_by = actor_id
        _recalculate_amounts(db, request)
    db.refresh(request)
    return request


def cancel_service_request(
    db: Session, request_id: uuid.UUID, *, reason: str | None, actor_id: uuid.UUID
) -> ServiceRequest:
    with transaction(db):
        request = require_row(db, ServiceRequest, request_id, "Service request")
        if request.status == STATUS_COMPLETED:
            raise Invalid("A completed service request cannot be cancelled.")
        request.status = STATUS_CANCELLED
        request.status_reason = reason
        request.completed_on = None
        request.updated_by = actor_id
    db.refresh(request)
    return request


# ---------------------------------------------------------------------------
# Catalogue: categories and items
# ---------------------------------------------------------------------------


def create_service_category(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> ServiceCategory:
    with transaction(db):
        if db.get(ServiceType, data["service_type"]) is None:
            raise Invalid(f"Service type {data['service_type']} does not exist.")
        ensure_unique(
            db, ServiceCategory, ServiceCategory.category_name,
            data["category_name"], "Service category",
        )
        row = ServiceCategory(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_service_category(
    db: Session, category_id: uuid.UUID, *, changes: dict
) -> ServiceCategory:
    with transaction(db):
        row = require_row(db, ServiceCategory, category_id, "Service category")
        if changes.get("category_name"):
            ensure_unique(
                db, ServiceCategory, ServiceCategory.category_name,
                changes["category_name"], "Service category", exclude_id=category_id,
            )
        if "service_type" in changes and db.get(ServiceType, changes["service_type"]) is None:
            raise Invalid(f"Service type {changes['service_type']} does not exist.")
        apply_changes(row, changes)
    db.refresh(row)
    return row


def create_service_item(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> ServiceCategoryItem:
    with transaction(db):
        category = db.get(ServiceCategory, data["category_id"])
        if category is None:
            raise Invalid(f"Service category {data['category_id']} does not exist.")
        require_exists(db, Amenity, data.get("amenity_id"), "Room")
        row = ServiceCategoryItem(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_service_item(
    db: Session, item_id: uuid.UUID, *, changes: dict
) -> ServiceCategoryItem:
    with transaction(db):
        row = require_row(db, ServiceCategoryItem, item_id, "Service item")
        if "category_id" in changes and db.get(ServiceCategory, changes["category_id"]) is None:
            raise Invalid(f"Service category {changes['category_id']} does not exist.")
        require_exists(db, Amenity, changes.get("amenity_id"), "Room")
        apply_changes(row, changes)
    db.refresh(row)
    return row
