"""Query logic for the facility and property hierarchy.

Every function here reads live from PostgreSQL through the caller's session.
There is no cache, no fixture and no fallback data path.

The building/floor projections deserve a note. `property_chain` is a
materialised path -- one row per (building, floor) pair -- so:

    buildings = DISTINCT property rows referenced by level_one_id
    floors    = DISTINCT property rows referenced by level_two_id

`level_three_id` exists in the schema and is currently NULL in every row
(the seeded `property_type.levels` is 2). It is therefore not surfaced by
these endpoints rather than being guessed at.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    Facility,
    Package,
    Property,
    PropertyChain,
    PropertyType,
)

# `property` aliased twice: the same table supplies both levels of a chain.
BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")


def _count(db: Session, stmt: Select) -> int:
    """Total rows a filtered statement would return, before paging."""
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------


def list_facilities(db: Session, *, page: int, page_size: int, facility_uid: str | None = None):
    stmt = select(Facility).order_by(Facility.name)
    if facility_uid:
        stmt = stmt.where(Facility.facility_uid == facility_uid)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_facility(db: Session, facility_id: uuid.UUID) -> Facility | None:
    return db.get(Facility, facility_id)


def facility_counts(db: Session, facility_id: uuid.UUID) -> dict[str, int]:
    properties = db.execute(
        select(func.count()).select_from(Property).where(Property.facility_id == facility_id)
    ).scalar_one()
    amenities = db.execute(
        select(func.count()).select_from(Amenity).where(Amenity.facility_id == facility_id)
    ).scalar_one()
    return {"property_count": properties, "amenity_count": amenities}


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------


def _property_stmt() -> Select:
    return (
        select(
            Property.id,
            Property.property_name,
            Property.property_type_id,
            PropertyType.property_type_name,
            PropertyType.levels.label("property_type_levels"),
            Property.facility_id,
            Property.status,
            Property.created_on,
            Property.updated_on,
        )
        .join(PropertyType, PropertyType.id == Property.property_type_id)
    )


def list_properties(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    property_type_id: uuid.UUID | None = None,
):
    stmt = _property_stmt().order_by(Property.property_name)
    if facility_id:
        stmt = stmt.where(Property.facility_id == facility_id)
    if property_type_id:
        stmt = stmt.where(Property.property_type_id == property_type_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_property(db: Session, property_id: uuid.UUID):
    return db.execute(
        _property_stmt().where(Property.id == property_id)
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# Buildings -- properties at property_chain.level_one_id
# ---------------------------------------------------------------------------


def _building_stmt() -> Select:
    floor_count = func.count(func.distinct(PropertyChain.level_two_id))
    room_count = func.count(func.distinct(Amenity.id))
    return (
        select(
            BuildingProp.id,
            BuildingProp.property_name.label("name"),
            BuildingProp.facility_id,
            BuildingProp.property_type_id,
            PropertyType.property_type_name,
            BuildingProp.status,
            floor_count.label("floor_count"),
            room_count.label("room_count"),
        )
        .select_from(PropertyChain)
        .join(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .join(PropertyType, PropertyType.id == BuildingProp.property_type_id)
        .outerjoin(Amenity, Amenity.property_chain_id == PropertyChain.id)
        .group_by(
            BuildingProp.id,
            BuildingProp.property_name,
            BuildingProp.facility_id,
            BuildingProp.property_type_id,
            PropertyType.property_type_name,
            BuildingProp.status,
        )
    )


def list_buildings(
    db: Session, *, page: int, page_size: int, facility_id: uuid.UUID | None = None
):
    stmt = _building_stmt().order_by(BuildingProp.property_name)
    if facility_id:
        stmt = stmt.where(BuildingProp.facility_id == facility_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_building(db: Session, building_id: uuid.UUID):
    """None when the property exists but is not used as a building."""
    return db.execute(
        _building_stmt().where(BuildingProp.id == building_id)
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# Floors -- properties at property_chain.level_two_id
# ---------------------------------------------------------------------------


def _floor_stmt() -> Select:
    room_count = func.count(func.distinct(Amenity.id))
    return (
        select(
            FloorProp.id,
            FloorProp.property_name.label("name"),
            FloorProp.facility_id,
            PropertyChain.id.label("property_chain_id"),
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.status,
            room_count.label("room_count"),
        )
        .select_from(PropertyChain)
        .join(FloorProp, FloorProp.id == PropertyChain.level_two_id)
        .join(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(Amenity, Amenity.property_chain_id == PropertyChain.id)
        .group_by(
            FloorProp.id,
            FloorProp.property_name,
            FloorProp.facility_id,
            PropertyChain.id,
            BuildingProp.id,
            BuildingProp.property_name,
            FloorProp.status,
        )
    )


def list_floors(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
):
    stmt = _floor_stmt().order_by(BuildingProp.property_name, FloorProp.property_name)
    if facility_id:
        stmt = stmt.where(FloorProp.facility_id == facility_id)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_floor(db: Session, floor_id: uuid.UUID):
    return db.execute(_floor_stmt().where(FloorProp.id == floor_id)).mappings().one_or_none()


# ---------------------------------------------------------------------------
# Rooms (= amenity)
# ---------------------------------------------------------------------------


def _room_stmt() -> Select:
    return (
        select(
            Amenity.id,
            Amenity.name,
            Amenity.facility_id,
            Amenity.amenity_type_id,
            AmenityType.name.label("amenity_type_name"),
            AmenityType.amenity_category,
            Amenity.package_id,
            Package.name.label("package_name"),
            Amenity.status,
            AmenityStatus.amenity_status_name.label("status_name"),
            Amenity.property_chain_id,
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            Amenity.parent_amenity_id,
            Amenity.is_dnd,
            Amenity.power_save_mode,
            Amenity.created_on,
            Amenity.updated_on,
        )
        .select_from(Amenity)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
        .join(Package, Package.id == Amenity.package_id)
        .outerjoin(AmenityStatus, AmenityStatus.id == Amenity.status)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def _conditions_for(db: Session, amenity_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict]]:
    """Active conditions for a page of rooms, in one query rather than N."""
    if not amenity_ids:
        return {}
    rows = db.execute(
        select(
            AmenityConditionStatus.amenity_id,
            AmenityCondition.id,
            AmenityCondition.name,
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
    out: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for amenity_id, condition_id, name in rows:
        out[amenity_id].append({"id": condition_id, "name": name})
    return out


def list_rooms(
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
):
    stmt = _room_stmt().order_by(Amenity.name)
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

    total = _count(db, stmt)
    rows = [dict(r) for r in db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()]
    conditions = _conditions_for(db, [r["id"] for r in rows])
    for row in rows:
        row["conditions"] = conditions.get(row["id"], [])
    return rows, total


def get_room(db: Session, room_id: uuid.UUID):
    row = db.execute(_room_stmt().where(Amenity.id == room_id)).mappings().one_or_none()
    if row is None:
        return None
    row = dict(row)
    row["conditions"] = _conditions_for(db, [row["id"]]).get(row["id"], [])
    return row
