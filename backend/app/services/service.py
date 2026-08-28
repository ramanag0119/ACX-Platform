"""Query logic for the service catalogue and service requests.

Reads live from PostgreSQL through the caller's session.

Person columns are projected through a narrow allow-list (`id`, name parts,
`emp_id`) -- `password_hash` and the `metadata` bag are never selected, exactly
as in `app.services.access`.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    AppUser,
    Department,
    ServiceCategory,
    ServiceCategoryItem,
    ServiceRequest,
    ServiceRequestItem,
    ServiceStatus,
    ServiceType,
    Stay,
)

# `app_user` appears twice on a request: the requester and the assignee.
Requester = aliased(AppUser, name="requester")
Assignee = aliased(AppUser, name="assignee")
ItemAssignee = aliased(AppUser, name="item_assignee")


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


def _user_ref(user_id, first, last, emp_id) -> dict | None:
    if user_id is None:
        return None
    name = " ".join(part for part in (first, last) if part)
    return {"id": user_id, "name": name, "emp_id": emp_id}


# ---------------------------------------------------------------------------
# service_type
# ---------------------------------------------------------------------------


def list_service_types(db: Session, *, page: int, page_size: int):
    stmt = select(ServiceType).order_by(ServiceType.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_service_type(db: Session, service_type_id: int) -> ServiceType | None:
    return db.get(ServiceType, service_type_id)


def service_type_counts(db: Session, service_type_id: int) -> dict[str, int]:
    return {
        "category_count": db.execute(
            select(func.count())
            .select_from(ServiceCategory)
            .where(ServiceCategory.service_type == service_type_id)
        ).scalar_one(),
        "request_count": db.execute(
            select(func.count())
            .select_from(ServiceRequest)
            .where(ServiceRequest.service_type == service_type_id)
        ).scalar_one(),
    }


# ---------------------------------------------------------------------------
# service_status
# ---------------------------------------------------------------------------


def list_service_statuses(db: Session, *, page: int, page_size: int):
    stmt = select(ServiceStatus).order_by(ServiceStatus.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_service_status(db: Session, status_id: int) -> ServiceStatus | None:
    return db.get(ServiceStatus, status_id)


# ---------------------------------------------------------------------------
# service_category
# ---------------------------------------------------------------------------


def _category_stmt() -> Select:
    return select(
        ServiceCategory.id,
        ServiceCategory.category_name,
        ServiceCategory.description,
        ServiceCategory.service_type,
        ServiceType.name.label("service_type_name"),
        ServiceCategory.service_category_key,
        ServiceCategory.category_icon,
        ServiceCategory.facility_id,
        ServiceCategory.status,
        ServiceCategory.created_on,
        ServiceCategory.updated_on,
    ).join(ServiceType, ServiceType.id == ServiceCategory.service_type)


def list_service_categories(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    service_type: int | None = None,
    status: int | None = None,
):
    stmt = _category_stmt().order_by(ServiceCategory.service_type, ServiceCategory.category_name)
    if facility_id:
        stmt = stmt.where(ServiceCategory.facility_id == facility_id)
    if service_type is not None:
        stmt = stmt.where(ServiceCategory.service_type == service_type)
    if status is not None:
        stmt = stmt.where(ServiceCategory.status == status)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_service_category(db: Session, category_id: uuid.UUID):
    return db.execute(
        _category_stmt().where(ServiceCategory.id == category_id)
    ).mappings().one_or_none()


def category_item_count(db: Session, category_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(ServiceCategoryItem)
        .where(ServiceCategoryItem.category_id == category_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# service_category_item
# ---------------------------------------------------------------------------


def _item_stmt() -> Select:
    return (
        select(
            ServiceCategoryItem.id,
            ServiceCategoryItem.item_name,
            ServiceCategoryItem.description,
            ServiceCategoryItem.category_id,
            ServiceCategory.category_name,
            ServiceCategory.service_type,
            ServiceType.name.label("service_type_name"),
            ServiceCategoryItem.price_per_unit,
            ServiceCategoryItem.amenity_id,
            ServiceCategoryItem.item_icon,
            ServiceCategoryItem.facility_id,
            ServiceCategoryItem.status,
            ServiceCategoryItem.created_on,
            ServiceCategoryItem.updated_on,
        )
        .join(ServiceCategory, ServiceCategory.id == ServiceCategoryItem.category_id)
        .join(ServiceType, ServiceType.id == ServiceCategory.service_type)
    )


def list_service_items(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    service_type: int | None = None,
    amenity_id: uuid.UUID | None = None,
    status: int | None = None,
    has_price: bool | None = None,
):
    stmt = _item_stmt().order_by(ServiceCategoryItem.item_name)
    if facility_id:
        stmt = stmt.where(ServiceCategoryItem.facility_id == facility_id)
    if category_id:
        stmt = stmt.where(ServiceCategoryItem.category_id == category_id)
    if service_type is not None:
        stmt = stmt.where(ServiceCategory.service_type == service_type)
    if amenity_id:
        stmt = stmt.where(ServiceCategoryItem.amenity_id == amenity_id)
    if status is not None:
        stmt = stmt.where(ServiceCategoryItem.status == status)
    if has_price is not None:
        column = ServiceCategoryItem.price_per_unit
        stmt = stmt.where(column.is_not(None) if has_price else column.is_(None))
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_service_item(db: Session, item_id: uuid.UUID):
    return db.execute(
        _item_stmt().where(ServiceCategoryItem.id == item_id)
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# service_request
# ---------------------------------------------------------------------------


def _request_stmt() -> Select:
    return (
        select(
            ServiceRequest.id,
            ServiceRequest.ref_number,
            ServiceRequest.description,
            ServiceRequest.service_type,
            ServiceType.name.label("service_type_name"),
            ServiceRequest.category_id,
            ServiceCategory.category_name,
            ServiceRequest.status,
            ServiceStatus.name.label("status_name"),
            ServiceRequest.status_reason,
            ServiceRequest.request_source,
            ServiceRequest.facility_id,
            ServiceRequest.amenity_id,
            Amenity.name.label("amenity_name"),
            ServiceRequest.stay_id,
            Stay.internal_stay_ref_number.label("stay_ref_number"),
            ServiceRequest.department_id,
            Department.department_name,
            ServiceRequest.app_user_id,
            Requester.first_name.label("requester_first_name"),
            Requester.last_name.label("requester_last_name"),
            Requester.emp_id.label("requester_emp_id"),
            ServiceRequest.assigned_to,
            Assignee.first_name.label("assignee_first_name"),
            Assignee.last_name.label("assignee_last_name"),
            Assignee.emp_id.label("assignee_emp_id"),
            ServiceRequest.promo_code_id,
            ServiceRequest.net_amount,
            ServiceRequest.total_tax,
            ServiceRequest.total_amount,
            ServiceRequest.expected_date,
            ServiceRequest.completed_on,
            ServiceRequest.created_on,
            ServiceRequest.updated_on,
        )
        .select_from(ServiceRequest)
        .join(ServiceType, ServiceType.id == ServiceRequest.service_type)
        .outerjoin(ServiceCategory, ServiceCategory.id == ServiceRequest.category_id)
        .outerjoin(ServiceStatus, ServiceStatus.id == ServiceRequest.status)
        .outerjoin(Amenity, Amenity.id == ServiceRequest.amenity_id)
        .outerjoin(Stay, Stay.id == ServiceRequest.stay_id)
        .outerjoin(Department, Department.id == ServiceRequest.department_id)
        .outerjoin(Requester, Requester.id == ServiceRequest.app_user_id)
        .outerjoin(Assignee, Assignee.id == ServiceRequest.assigned_to)
    )


def _shape_request(row) -> dict:
    data = dict(row)
    data["requester"] = _user_ref(
        data.pop("app_user_id"),
        data.pop("requester_first_name"),
        data.pop("requester_last_name"),
        data.pop("requester_emp_id"),
    )
    data["assignee"] = _user_ref(
        data.pop("assigned_to"),
        data.pop("assignee_first_name"),
        data.pop("assignee_last_name"),
        data.pop("assignee_emp_id"),
    )
    return data


def list_service_requests(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    service_type: int | None = None,
    status: int | None = None,
    category_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    app_user_id: uuid.UUID | None = None,
    stay_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    request_source: str | None = None,
    unassigned: bool | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _request_stmt().order_by(ServiceRequest.created_on.desc())
    if facility_id:
        stmt = stmt.where(ServiceRequest.facility_id == facility_id)
    if service_type is not None:
        stmt = stmt.where(ServiceRequest.service_type == service_type)
    if status is not None:
        stmt = stmt.where(ServiceRequest.status == status)
    if category_id:
        stmt = stmt.where(ServiceRequest.category_id == category_id)
    if assigned_to:
        stmt = stmt.where(ServiceRequest.assigned_to == assigned_to)
    if app_user_id:
        stmt = stmt.where(ServiceRequest.app_user_id == app_user_id)
    if stay_id:
        stmt = stmt.where(ServiceRequest.stay_id == stay_id)
    if amenity_id:
        stmt = stmt.where(ServiceRequest.amenity_id == amenity_id)
    if department_id:
        stmt = stmt.where(ServiceRequest.department_id == department_id)
    if request_source:
        stmt = stmt.where(ServiceRequest.request_source == request_source)
    if unassigned is not None:
        column = ServiceRequest.assigned_to
        stmt = stmt.where(column.is_(None) if unassigned else column.is_not(None))
    if created_from:
        stmt = stmt.where(ServiceRequest.created_on >= created_from)
    if created_to:
        stmt = stmt.where(ServiceRequest.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return [_shape_request(r) for r in rows], total


def get_service_request(db: Session, request_id: uuid.UUID):
    row = db.execute(
        _request_stmt().where(ServiceRequest.id == request_id)
    ).mappings().one_or_none()
    return _shape_request(row) if row is not None else None


def request_items(db: Session, request_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict]]:
    """Line items for a set of requests, in one query rather than N."""
    if not request_ids:
        return {}
    rows = db.execute(
        select(
            ServiceRequestItem.service_request_id,
            ServiceRequestItem.id,
            ServiceRequestItem.item_id,
            ServiceCategoryItem.item_name,
            ServiceRequestItem.category_id,
            ServiceCategory.category_name,
            ServiceRequestItem.quantity,
            ServiceRequestItem.price_per_unit,
            ServiceRequestItem.assigned_to,
            ItemAssignee.first_name,
            ItemAssignee.last_name,
            ItemAssignee.emp_id,
            ServiceRequestItem.status,
            ServiceStatus.name.label("status_name"),
            ServiceRequestItem.created_on,
            ServiceRequestItem.updated_on,
        )
        .select_from(ServiceRequestItem)
        .outerjoin(
            ServiceCategoryItem, ServiceCategoryItem.id == ServiceRequestItem.item_id
        )
        .outerjoin(ServiceCategory, ServiceCategory.id == ServiceRequestItem.category_id)
        .outerjoin(ServiceStatus, ServiceStatus.id == ServiceRequestItem.status)
        .outerjoin(ItemAssignee, ItemAssignee.id == ServiceRequestItem.assigned_to)
        .where(ServiceRequestItem.service_request_id.in_(request_ids))
        .order_by(ServiceRequestItem.created_on)
    ).all()

    out: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for r in rows:
        out[r.service_request_id].append(
            {
                "id": r.id,
                "item_id": r.item_id,
                "item_name": r.item_name,
                "category_id": r.category_id,
                "category_name": r.category_name,
                "quantity": r.quantity,
                "price_per_unit": r.price_per_unit,
                "assigned_to": _user_ref(
                    r.assigned_to, r.first_name, r.last_name, r.emp_id
                ),
                "status": r.status,
                "status_name": r.status_name,
                "created_on": r.created_on,
                "updated_on": r.updated_on,
            }
        )
    return out
