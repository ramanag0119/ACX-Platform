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

from sqlalchemy import Select, func, select, text, update
from sqlalchemy.orm import Session, aliased

from app.models import (
    AccessKey,
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    AppUser,
    Facility,
    Package,
    Property,
    PropertyChain,
    PropertyType,
)
from app.services.writes import Invalid, require_row, transaction

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
            func.coalesce(AmenityCondition.display_name, AmenityCondition.name).label("display_name"),
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
    for amenity_id, condition_id, name, display_name in rows:
        out[amenity_id].append({"id": condition_id, "name": name, "display_name": display_name})
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
    cond_master = {
        c.id: c.display_name or c.name
        for c in db.execute(select(AmenityCondition)).scalars().all()
    }
    for row in rows:
        conds = conditions.get(row["id"], [])
        row["conditions"] = conds
        if conds:
            row["room_status_id"] = conds[0]["id"]
            row["room_status"] = conds[0].get("display_name") or conds[0].get("name")
        else:
            if row.get("status") == 1:
                row["room_status_id"] = None
                row["room_status"] = None
            elif row.get("status") == 2:
                row["room_status_id"] = 3
                row["room_status"] = cond_master.get(3, "Under Maintenance")
            else:
                row["room_status_id"] = 5
                row["room_status"] = cond_master.get(5, "Ready to Occupy")
        st = row.get("status")
        row["occupancy_status"] = "Occupied" if st == 1 else ("Allotted" if st == 3 else ("Unavailable" if st == 2 else "Available"))
    return rows, total


def get_room(db: Session, room_id: uuid.UUID):
    row = db.execute(_room_stmt().where(Amenity.id == room_id)).mappings().one_or_none()
    if row is None:
        return None
    row = dict(row)
    conds = _conditions_for(db, [row["id"]]).get(row["id"], [])
    row["conditions"] = conds
    cond_master = {
        c.id: c.display_name or c.name
        for c in db.execute(select(AmenityCondition)).scalars().all()
    }
    if conds:
        row["room_status_id"] = conds[0]["id"]
        row["room_status"] = conds[0].get("display_name") or conds[0].get("name")
    else:
        if row.get("status") == 1:
            row["room_status_id"] = None
            row["room_status"] = None
        elif row.get("status") == 2:
            row["room_status_id"] = 3
            row["room_status"] = cond_master.get(3, "Under Maintenance")
        else:
            row["room_status_id"] = 5
            row["room_status"] = cond_master.get(5, "Ready to Occupy")
    st = row.get("status")
    row["occupancy_status"] = "Occupied" if st == 1 else ("Allotted" if st == 3 else ("Unavailable" if st == 2 else "Available"))
    return row


def list_countries(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 250,
    search: str | None = None,
) -> tuple[list, int]:
    from sqlalchemy import or_
    from app.models.facility import Country

    stmt = select(Country).order_by(Country.nice_name)
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Country.nice_name).like(q),
                func.lower(Country.name).like(q),
                Country.phone_code.like(f"%{search.strip().lstrip('+')}%"),
                func.lower(Country.iso_code).like(q),
            )
        )
    total = _count(db, stmt)
    rows = list(db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all())
    return rows, total


def get_gender_options(db: Session) -> list[dict[str, str]]:
    """Return gender options authoritatively defined in PostgreSQL's `gender` enum."""
    from sqlalchemy import text

    result = db.execute(
        text(
            "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
            "JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = 'public' AND t.typname = 'gender' ORDER BY e.enumsortorder"
        )
    ).fetchall()
    if not result:
        return [
            {"value": "male", "label": "Male"},
            {"value": "female", "label": "Female"},
            {"value": "other", "label": "Other"},
        ]
    return [{"value": r[0], "label": r[0].title()} for r in result]


# ---------------------------------------------------------------------------
# Default Key Settings
# ---------------------------------------------------------------------------


def get_key_settings(db: Session, facility_id: uuid.UUID) -> dict:
    facility = require_row(db, Facility, facility_id, "Facility")
    manager_name = None
    manager_email = None
    if facility.default_key_user:
        manager = db.get(AppUser, facility.default_key_user)
        if manager:
            name_parts = [manager.first_name, manager.last_name]
            manager_name = " ".join([p for p in name_parts if p])
            manager_email = manager.email

    active_keys_count = db.execute(
        select(func.count())
        .select_from(AccessKey)
        .where(AccessKey.key_type == 4, AccessKey.status == 1)
    ).scalar() or 0

    return {
        "facility_id": facility.id,
        "default_key_user": facility.default_key_user,
        "manager_name": manager_name,
        "manager_email": manager_email,
        "active_keys_count": active_keys_count,
    }


def update_key_settings(
    db: Session, facility_id: uuid.UUID, *, default_key_user: uuid.UUID | None, actor_id: uuid.UUID
) -> dict:
    with transaction(db):
        facility = require_row(db, Facility, facility_id, "Facility")
        if default_key_user is not None:
            user = db.get(AppUser, default_key_user)
            if not user:
                raise Invalid("Selected manager user does not exist.")
            if user.is_staff != 1:
                raise Invalid("Selected manager must be an active staff member.")
        facility.default_key_user = default_key_user
    db.refresh(facility)
    return get_key_settings(db, facility_id)


def reset_key_settings(db: Session, facility_id: uuid.UUID, actor_id: uuid.UUID) -> dict:
    """Revoke all default keys and reset designated default key manager."""
    with transaction(db):
        facility = require_row(db, Facility, facility_id, "Facility")
        facility.default_key_user = None
        # Revoke all active default keys (key_type=4)
        db.execute(
            update(AccessKey)
            .where(AccessKey.key_type == 4, AccessKey.status == 1)
            .values(status=0)
        )
    db.refresh(facility)
    return get_key_settings(db, facility_id)

