"""Query logic for stays, occupants, room allocations and invoices.

Reads live from PostgreSQL through the caller's session.

Person columns go through the shared narrow projection (id + name parts);
`password_hash`, contact details and the `metadata` bag are never selected.

`stay` has no `facility_id`, so facility/building/floor filters are EXISTS
subqueries over room_allocation -> amenity -> property_chain.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    AmenityType,
    AppUser,
    Invoice,
    Package,
    Property,
    PropertyChain,
    RoomAllocation,
    Stay,
    StayPackage,
    StayUser,
    UserDocument,
)

Booker = aliased(AppUser, name="booker")
Occupant = aliased(AppUser, name="occupant")
DocumentOwner = aliased(AppUser, name="document_owner")
BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


def _user_ref(user_id, first, last, emp_id=None) -> dict | None:
    if user_id is None:
        return None
    return {
        "id": user_id,
        "name": " ".join(p for p in (first, last) if p),
        "emp_id": emp_id,
    }


#: "In house" = checked in and not yet checked out. Two real columns, read
#: literally -- the schema encodes no occupancy rule of its own.
IN_HOUSE = and_(
    Stay.actual_checkin_time.is_not(None), Stay.actual_checkout_time.is_(None)
)


# ---------------------------------------------------------------------------
# stay
# ---------------------------------------------------------------------------


def _stay_stmt() -> Select:
    occupant_count = (
        select(func.count())
        .select_from(StayUser)
        .where(StayUser.stay_id == Stay.id)
        .scalar_subquery()
    )
    room_count = (
        select(func.count())
        .select_from(RoomAllocation)
        .where(RoomAllocation.stay_id == Stay.id)
        .scalar_subquery()
    )
    return (
        select(
            Stay.id,
            Stay.internal_stay_ref_number,
            Stay.external_stay_ref_number,
            Stay.status,
            Stay.document_approval_status,
            Stay.request_source,
            Stay.booking_user_id,
            Booker.first_name.label("booker_first_name"),
            Booker.last_name.label("booker_last_name"),
            Stay.no_of_rooms,
            Stay.no_of_guests,
            Stay.expected_checkin_time,
            Stay.expected_checkout_time,
            Stay.actual_checkin_time,
            Stay.actual_checkout_time,
            Stay.actual_checkin_time.is_not(None).label("is_checked_in"),
            IN_HOUSE.label("is_in_house"),
            Stay.gst,
            Stay.comments,
            Stay.checkout_initiated_by,
            occupant_count.label("occupant_count"),
            room_count.label("room_count"),
            Stay.created_on,
            Stay.updated_on,
        )
        .select_from(Stay)
        .outerjoin(Booker, Booker.id == Stay.booking_user_id)
    )


def _shape_stay(row) -> dict:
    data = dict(row)
    data["booker"] = _user_ref(
        data.pop("booking_user_id"),
        data.pop("booker_first_name"),
        data.pop("booker_last_name"),
    )
    return data


def _location_exists(*conditions):
    """EXISTS over room_allocation -> amenity -> property_chain."""
    return (
        select(RoomAllocation.id)
        .join(Amenity, Amenity.id == RoomAllocation.room_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .where(RoomAllocation.stay_id == Stay.id, *conditions)
        .exists()
    )


def list_stays(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    request_source: str | None = None,
    document_approval_status: str | None = None,
    booking_user_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    is_checked_in: bool | None = None,
    is_in_house: bool | None = None,
    ref_number: str | None = None,
    expected_checkin_from: datetime | None = None,
    expected_checkin_to: datetime | None = None,
    expected_checkout_from: datetime | None = None,
    expected_checkout_to: datetime | None = None,
):
    stmt = _stay_stmt().order_by(Stay.expected_checkin_time.desc())
    if status:
        stmt = stmt.where(Stay.status == status)
    if request_source:
        stmt = stmt.where(Stay.request_source == request_source)
    if document_approval_status:
        stmt = stmt.where(Stay.document_approval_status == document_approval_status)
    if booking_user_id:
        stmt = stmt.where(Stay.booking_user_id == booking_user_id)
    if guest_id:
        # Any occupant, not just the booker.
        stmt = stmt.where(
            select(StayUser.id)
            .where(StayUser.stay_id == Stay.id, StayUser.app_user_id == guest_id)
            .exists()
        )
    if facility_id:
        stmt = stmt.where(_location_exists(Amenity.facility_id == facility_id))
    if room_id:
        stmt = stmt.where(_location_exists(RoomAllocation.room_id == room_id))
    if building_id:
        stmt = stmt.where(_location_exists(PropertyChain.level_one_id == building_id))
    if floor_id:
        stmt = stmt.where(_location_exists(PropertyChain.level_two_id == floor_id))
    if is_checked_in is not None:
        column = Stay.actual_checkin_time
        stmt = stmt.where(column.is_not(None) if is_checked_in else column.is_(None))
    if is_in_house is not None:
        stmt = stmt.where(IN_HOUSE if is_in_house else ~IN_HOUSE)
    if ref_number:
        stmt = stmt.where(Stay.internal_stay_ref_number == ref_number)
    if expected_checkin_from:
        stmt = stmt.where(Stay.expected_checkin_time >= expected_checkin_from)
    if expected_checkin_to:
        stmt = stmt.where(Stay.expected_checkin_time <= expected_checkin_to)
    if expected_checkout_from:
        stmt = stmt.where(Stay.expected_checkout_time >= expected_checkout_from)
    if expected_checkout_to:
        stmt = stmt.where(Stay.expected_checkout_time <= expected_checkout_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return [_shape_stay(r) for r in rows], total


def get_stay(db: Session, stay_id: uuid.UUID):
    row = db.execute(_stay_stmt().where(Stay.id == stay_id)).mappings().one_or_none()
    return _shape_stay(row) if row is not None else None


def stay_exists(db: Session, stay_id: uuid.UUID) -> bool:
    return db.execute(
        select(func.count()).select_from(Stay).where(Stay.id == stay_id)
    ).scalar_one() > 0


# ---------------------------------------------------------------------------
# stay sub-resources
# ---------------------------------------------------------------------------


def stay_occupants(db: Session, stay_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(
            StayUser.id,
            StayUser.app_user_id,
            Occupant.first_name,
            Occupant.last_name,
            StayUser.room_id,
            Amenity.name.label("room_name"),
            StayUser.is_key_required,
            StayUser.status,
            StayUser.created_on,
        )
        .select_from(StayUser)
        .outerjoin(Occupant, Occupant.id == StayUser.app_user_id)
        .outerjoin(Amenity, Amenity.id == StayUser.room_id)
        .where(StayUser.stay_id == stay_id)
        .order_by(StayUser.created_on)
    ).all()
    return [
        {
            "id": r.id,
            "guest": _user_ref(r.app_user_id, r.first_name, r.last_name),
            "room_id": r.room_id,
            "room_name": r.room_name,
            "is_key_required": r.is_key_required,
            "status": r.status,
            "created_on": r.created_on,
        }
        for r in rows
    ]


def _allocation_stmt() -> Select:
    return (
        select(
            RoomAllocation.id,
            RoomAllocation.stay_id,
            RoomAllocation.room_id,
            Amenity.name.label("room_name"),
            AmenityType.name.label("amenity_type_name"),
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            Amenity.facility_id,
            RoomAllocation.package_id,
            Package.name.label("package_name"),
            RoomAllocation.status,
            RoomAllocation.created_on,
            RoomAllocation.updated_on,
        )
        .select_from(RoomAllocation)
        .join(Amenity, Amenity.id == RoomAllocation.room_id)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
        .outerjoin(Package, Package.id == RoomAllocation.package_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def stay_room_allocations(db: Session, stay_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        _allocation_stmt()
        .where(RoomAllocation.stay_id == stay_id)
        .order_by(RoomAllocation.created_on)
    ).mappings().all()
    return [dict(r) for r in rows]


def stay_packages(db: Session, stay_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(
            StayPackage.id,
            StayPackage.package_id,
            Package.name.label("package_name"),
            StayPackage.status,
        )
        .outerjoin(Package, Package.id == StayPackage.package_id)
        .where(StayPackage.stay_id == stay_id)
    ).mappings().all()
    return [dict(r) for r in rows]


def stay_documents(db: Session, stay_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(
            UserDocument.id,
            UserDocument.app_user_id,
            DocumentOwner.first_name,
            DocumentOwner.last_name,
            UserDocument.attachment_id,
            UserDocument.document_approval_status,
            UserDocument.status,
            UserDocument.created_on,
        )
        .select_from(UserDocument)
        .outerjoin(DocumentOwner, DocumentOwner.id == UserDocument.app_user_id)
        .where(UserDocument.stay_id == stay_id)
        .order_by(UserDocument.created_on)
    ).all()
    return [
        {
            "id": r.id,
            "guest": _user_ref(r.app_user_id, r.first_name, r.last_name),
            "attachment_id": r.attachment_id,
            "document_approval_status": r.document_approval_status,
            "status": r.status,
            "created_on": r.created_on,
        }
        for r in rows
    ]


def stay_invoice_refs(db: Session, stay_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(Invoice.id, Invoice.invoice_number, Invoice.total_amount)
        .where(Invoice.stay_id == stay_id)
        .order_by(Invoice.invoice_date)
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# invoice
# ---------------------------------------------------------------------------


def _invoice_stmt() -> Select:
    return (
        select(
            Invoice.id,
            Invoice.invoice_number,
            Invoice.invoice_date,
            Invoice.invoice_due_date,
            Invoice.stay_id,
            Stay.internal_stay_ref_number.label("stay_ref_number"),
            Invoice.billing_user_id,
            Invoice.billing_user_name,
            Invoice.billing_address,
            Invoice.facility_id,
            Invoice.facility_name,
            Invoice.facility_address,
            Invoice.net_amount,
            Invoice.total_tax,
            Invoice.total_amount,
            Invoice.created_on,
            Invoice.updated_on,
        )
        .select_from(Invoice)
        .outerjoin(Stay, Stay.id == Invoice.stay_id)
    )


def list_invoices(
    db: Session,
    *,
    page: int,
    page_size: int,
    stay_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    billing_user_id: uuid.UUID | None = None,
    invoice_number: str | None = None,
    invoice_date_from: datetime | None = None,
    invoice_date_to: datetime | None = None,
):
    stmt = _invoice_stmt().order_by(Invoice.invoice_date.desc())
    if stay_id:
        stmt = stmt.where(Invoice.stay_id == stay_id)
    if facility_id:
        stmt = stmt.where(Invoice.facility_id == facility_id)
    if billing_user_id:
        stmt = stmt.where(Invoice.billing_user_id == billing_user_id)
    if invoice_number:
        stmt = stmt.where(Invoice.invoice_number == invoice_number)
    if invoice_date_from:
        stmt = stmt.where(Invoice.invoice_date >= invoice_date_from)
    if invoice_date_to:
        stmt = stmt.where(Invoice.invoice_date <= invoice_date_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_invoice(db: Session, invoice_id: uuid.UUID):
    return db.execute(
        _invoice_stmt().where(Invoice.id == invoice_id)
    ).mappings().one_or_none()
