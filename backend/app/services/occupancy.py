"""Query logic for the room-centric occupancy view.

There is no `occupancy` table. Each row here is an `amenity` joined to its
status lookup, its active conditions, and -- when one exists -- the stay
currently in house in that room.

`amenity.status` and the stay graph are independent in the schema. This module
reports both as stored and never reconciles them.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    AppUser,
    Device,
    Package,
    Property,
    PropertyChain,
    RoomAllocation,
    Stay,
    StayUser,
)

BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")

#: Same literal reading of the two timestamp columns used by the stay service.
IN_HOUSE = and_(
    Stay.actual_checkin_time.is_not(None), Stay.actual_checkout_time.is_(None)
)


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


def _user_ref(user_id, first, last) -> dict | None:
    if user_id is None:
        return None
    return {
        "id": user_id,
        "name": " ".join(p for p in (first, last) if p),
        "emp_id": None,
    }


# ---------------------------------------------------------------------------
# lookups
# ---------------------------------------------------------------------------


def list_amenity_statuses(db: Session, *, page: int, page_size: int):
    stmt = select(AmenityStatus).order_by(AmenityStatus.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def list_amenity_conditions(db: Session, *, page: int, page_size: int):
    stmt = select(AmenityCondition).order_by(AmenityCondition.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


# ---------------------------------------------------------------------------
# occupancy
# ---------------------------------------------------------------------------


def _occupancy_stmt() -> Select:
    allocation_count = (
        select(func.count())
        .select_from(RoomAllocation)
        .where(RoomAllocation.room_id == Amenity.id)
        .scalar_subquery()
    )
    return (
        select(
            Amenity.id.label("amenity_id"),
            Amenity.name.label("room_name"),
            Amenity.amenity_type_id,
            AmenityType.name.label("amenity_type_name"),
            AmenityType.amenity_category,
            Amenity.package_id,
            Package.name.label("package_name"),
            Amenity.status,
            AmenityStatus.amenity_status_name.label("status_name"),
            Amenity.facility_id,
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            Amenity.is_dnd,
            Amenity.power_save_mode,
            allocation_count.label("allocation_count"),
        )
        .select_from(Amenity)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
        .join(Package, Package.id == Amenity.package_id)
        .outerjoin(AmenityStatus, AmenityStatus.id == Amenity.status)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def _in_house_exists():
    return (
        select(RoomAllocation.id)
        .join(Stay, Stay.id == RoomAllocation.stay_id)
        .where(RoomAllocation.room_id == Amenity.id, IN_HOUSE)
        .exists()
    )


def _current_stays(db: Session, amenity_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """The in-house stay per room, in one query rather than N."""
    if not amenity_ids:
        return {}
    rows = db.execute(
        select(
            RoomAllocation.room_id,
            Stay.id.label("stay_id"),
            Stay.internal_stay_ref_number,
            Stay.status,
            Stay.booking_user_id,
            AppUser.first_name,
            AppUser.last_name,
            Stay.expected_checkout_time,
            Stay.actual_checkin_time,
            Stay.no_of_guests,
        )
        .select_from(RoomAllocation)
        .join(Stay, Stay.id == RoomAllocation.stay_id)
        .outerjoin(AppUser, AppUser.id == Stay.booking_user_id)
        .where(RoomAllocation.room_id.in_(amenity_ids), IN_HOUSE)
        .order_by(Stay.actual_checkin_time.desc())
    ).all()

    out: dict[uuid.UUID, dict] = {}
    for r in rows:
        # Most recent check-in wins if a room somehow has two in-house stays.
        out.setdefault(
            r.room_id,
            {
                "stay_id": r.stay_id,
                "internal_stay_ref_number": r.internal_stay_ref_number,
                "status": r.status,
                "booker": _user_ref(r.booking_user_id, r.first_name, r.last_name),
                "expected_checkout_time": r.expected_checkout_time,
                "actual_checkin_time": r.actual_checkin_time,
                "no_of_guests": r.no_of_guests,
            },
        )
    return out


def _conditions_for(db: Session, amenity_ids: list[uuid.UUID]) -> dict[uuid.UUID, list]:
    if not amenity_ids:
        return {}
    rows = db.execute(
        select(
            AmenityConditionStatus.amenity_id,
            AmenityCondition.id,
            AmenityCondition.name,
            AmenityCondition.created_on,
            AmenityCondition.updated_on,
        )
        .join(
            AmenityCondition,
            AmenityCondition.id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id.in_(amenity_ids),
            AmenityConditionStatus.status == 1,
        )
        .order_by(AmenityCondition.id)
    ).all()
    out: dict[uuid.UUID, list] = defaultdict(list)
    for amenity_id, cid, name, created, updated in rows:
        out[amenity_id].append(
            {"id": cid, "name": name, "created_on": created, "updated_on": updated}
        )
    return out


def _enrich(db: Session, rows: list[dict]) -> list[dict]:
    ids = [r["amenity_id"] for r in rows]
    conditions = _conditions_for(db, ids)
    current = _current_stays(db, ids)
    for row in rows:
        row["conditions"] = conditions.get(row["amenity_id"], [])
        row["current_stay"] = current.get(row["amenity_id"])
    return rows


def list_occupancy(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    amenity_type_id: uuid.UUID | None = None,
    amenity_category: str | None = None,
    status: int | None = None,
    condition_id: int | None = None,
    is_occupied: bool | None = None,
):
    stmt = _occupancy_stmt().order_by(Amenity.name)
    if facility_id:
        stmt = stmt.where(Amenity.facility_id == facility_id)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    if floor_id:
        stmt = stmt.where(FloorProp.id == floor_id)
    if amenity_type_id:
        stmt = stmt.where(Amenity.amenity_type_id == amenity_type_id)
    if amenity_category:
        stmt = stmt.where(AmenityType.amenity_category == amenity_category)
    if status is not None:
        stmt = stmt.where(Amenity.status == status)
    if condition_id is not None:
        stmt = stmt.where(
            select(AmenityConditionStatus.amenity_id)
            .where(
                AmenityConditionStatus.amenity_id == Amenity.id,
                AmenityConditionStatus.amenity_condition_id == condition_id,
                AmenityConditionStatus.status == 1,
            )
            .exists()
        )
    if is_occupied is not None:
        # Occupancy by the STAY graph, not by amenity.status -- the two differ.
        exists = _in_house_exists()
        stmt = stmt.where(exists if is_occupied else ~exists)

    total = _count(db, stmt)
    rows = [
        dict(r)
        for r in db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    ]
    return _enrich(db, rows), total


def get_occupancy(db: Session, amenity_id: uuid.UUID):
    row = db.execute(
        _occupancy_stmt().where(Amenity.id == amenity_id)
    ).mappings().one_or_none()
    if row is None:
        return None
    enriched = _enrich(db, [dict(row)])[0]

    occupants: list[dict] = []
    if enriched["current_stay"]:
        rows = db.execute(
            select(
                StayUser.app_user_id,
                AppUser.first_name,
                AppUser.last_name,
                StayUser.is_key_required,
            )
            .outerjoin(AppUser, AppUser.id == StayUser.app_user_id)
            .where(
                StayUser.stay_id == enriched["current_stay"]["stay_id"],
                StayUser.room_id == amenity_id,
            )
        ).all()
        occupants = [
            {
                "guest": _user_ref(r.app_user_id, r.first_name, r.last_name),
                "is_key_required": r.is_key_required,
            }
            for r in rows
        ]

    enriched["occupants"] = occupants
    enriched["device_count"] = db.execute(
        select(func.count()).select_from(Device).where(Device.amenity_id == amenity_id)
    ).scalar_one()
    return enriched
