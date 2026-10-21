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
from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, and_, case, func, or_, select
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
    RoomStatusConditionApplicability,
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


def list_amenity_conditions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    room_status: str | None = None,
    amenity_id: uuid.UUID | None = None,
):
    if amenity_id is not None:
        items = get_applicable_conditions_for_room(db, amenity_id)
        return items, len(items)

    if room_status is not None:
        items = list_applicable_conditions_by_status(db, room_status)
        return items, len(items)

    stmt = (
        select(
            AmenityCondition.id,
            AmenityCondition.name,
            func.coalesce(AmenityCondition.display_name, AmenityCondition.name).label("display_name"),
            AmenityCondition.created_on,
            AmenityCondition.updated_on,
            AmenityCondition.is_active,
        )
        .where(AmenityCondition.is_active == True)
        .order_by(AmenityCondition.id)
    )
    total = _count(db, stmt)
    rows = [dict(r) for r in db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()]
    return rows, total



# ---------------------------------------------------------------------------
# occupancy
# ---------------------------------------------------------------------------


def _in_house_exists():
    return (
        select(RoomAllocation.id)
        .join(Stay, Stay.id == RoomAllocation.stay_id)
        .where(RoomAllocation.room_id == Amenity.id, IN_HOUSE)
        .exists()
    )


# Fallback condition constants for backward compatibility
CONDITION_NEED_MAINTENANCE = 1  # "Dirty"
CONDITION_LOW_BATTERY = 2       # "Low battery"
CONDITION_UNDER_MAINTENANCE = 3 # "Under maintenance"
CONDITION_SANITATION = 4        # "Sanitation"
CONDITION_READY_TO_OCCUPY = 5   # "Ready for occupant"

CONDITION_DISPLAY_NAMES = {
    CONDITION_NEED_MAINTENANCE: "Need Maintenance",
    CONDITION_LOW_BATTERY: "Low Battery",
    CONDITION_UNDER_MAINTENANCE: "Under Maintenance",
    CONDITION_SANITATION: "Sanitation",
    CONDITION_READY_TO_OCCUPY: "Ready to Occupy",
}

CONDITION_NAME_TO_ID = {
    "need maintenance": CONDITION_NEED_MAINTENANCE,
    "dirty": CONDITION_NEED_MAINTENANCE,
    "low battery": CONDITION_LOW_BATTERY,
    "under maintenance": CONDITION_UNDER_MAINTENANCE,
    "sanitation": CONDITION_SANITATION,
    "ready to occupy": CONDITION_READY_TO_OCCUPY,
    "ready for occupant": CONDITION_READY_TO_OCCUPY,
}


def determine_room_status_for_applicability(db: Session, amenity_id: uuid.UUID) -> str:
    """Determine the authoritative room status for condition applicability lookup."""
    in_house = db.execute(
        select(Stay.id)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id == amenity_id,
            Stay.actual_checkin_time.is_not(None),
            Stay.actual_checkout_time.is_(None),
        )
    ).first() is not None
    if in_house:
        return "Occupied"

    status_val = db.execute(
        select(Amenity.status).where(Amenity.id == amenity_id)
    ).scalar_one_or_none()

    if status_val == 1:
        return "Occupied"

    pending_alloc = db.execute(
        select(Stay.id)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id == amenity_id,
            Stay.status == "pending",
            Stay.actual_checkin_time.is_(None),
            Stay.actual_checkout_time.is_(None),
        )
    ).first() is not None
    if pending_alloc or status_val == 3:
        return "Allocated"

    blocking = db.execute(
        select(AmenityConditionStatus.amenity_id)
        .join(
            RoomStatusConditionApplicability,
            RoomStatusConditionApplicability.condition_id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id == amenity_id,
            AmenityConditionStatus.status == 1,
            RoomStatusConditionApplicability.is_active == True,
            or_(
                RoomStatusConditionApplicability.blocks_readiness == True,
                RoomStatusConditionApplicability.blocks_checkin == True,
            ),
        )
    ).first() is not None
    if blocking or status_val == 2:
        return "Unavailable"

    ready = db.execute(
        select(AmenityConditionStatus.amenity_id)
        .join(
            AmenityCondition,
            AmenityCondition.id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id == amenity_id,
            AmenityConditionStatus.status == 1,
            AmenityCondition.is_active == True,
            func.lower(AmenityCondition.name).ilike("%ready%"),
        )
    ).first() is not None
    if ready:
        return "Ready to Occupy"

    return "Available"


def list_applicable_conditions_by_status(db: Session, status_name: str) -> list[dict]:
    """Retrieve only active condition options applicable to the specified status."""
    status_clean = status_name.strip()
    status_candidates = [status_clean]
    if status_clean.lower() == "allocated":
        status_candidates.append("Allotted")
    elif status_clean.lower() == "allotted":
        status_candidates.append("Allocated")
    elif status_clean.lower() == "ready to occupy":
        status_candidates.append("Available")

    stmt = (
        select(
            AmenityCondition.id,
            AmenityCondition.name,
            func.coalesce(AmenityCondition.display_name, AmenityCondition.name).label("display_name"),
            AmenityCondition.created_on,
            AmenityCondition.updated_on,
            AmenityCondition.is_active,
            RoomStatusConditionApplicability.is_applicable,
            RoomStatusConditionApplicability.blocks_checkin,
            RoomStatusConditionApplicability.blocks_readiness,
        )
        .join(
            RoomStatusConditionApplicability,
            RoomStatusConditionApplicability.condition_id == AmenityCondition.id,
        )
        .where(
            func.lower(RoomStatusConditionApplicability.room_status).in_([s.lower() for s in status_candidates]),
            RoomStatusConditionApplicability.is_applicable == True,
            RoomStatusConditionApplicability.is_active == True,
            AmenityCondition.is_active == True,
        )
        .order_by(AmenityCondition.id)
    )

    rows = db.execute(stmt).mappings().all()
    seen_ids = set()
    result = []
    for r in rows:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            result.append(dict(r))
    return result


def get_applicable_conditions_for_room(db: Session, amenity_id: uuid.UUID) -> list[dict]:
    """Retrieve active applicable conditions for a specific room based on its DB status."""
    canonical_status = determine_room_status_for_applicability(db, amenity_id)
    return list_applicable_conditions_by_status(db, canonical_status)


def _blocking_condition_exists():
    return (
        select(AmenityConditionStatus.amenity_id)
        .join(
            RoomStatusConditionApplicability,
            RoomStatusConditionApplicability.condition_id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id == Amenity.id,
            AmenityConditionStatus.status == 1,
            RoomStatusConditionApplicability.is_active == True,
            or_(
                RoomStatusConditionApplicability.blocks_readiness == True,
                RoomStatusConditionApplicability.blocks_checkin == True,
            ),
        )
        .exists()
    )


def _ready_condition_exists():
    return (
        select(AmenityConditionStatus.amenity_id)
        .join(
            AmenityCondition,
            AmenityCondition.id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id == Amenity.id,
            AmenityConditionStatus.status == 1,
            or_(
                func.lower(AmenityCondition.name).ilike("%ready%"),
                func.lower(AmenityCondition.name).ilike("%battery%"),
            ),
        )
        .exists()
    )


def _pending_allocation_exists():
    return (
        select(RoomAllocation.id)
        .join(Stay, Stay.id == RoomAllocation.stay_id)
        .where(
            RoomAllocation.room_id == Amenity.id,
            Stay.status == "pending",
            Stay.actual_checkin_time.is_(None),
            Stay.actual_checkout_time.is_(None),
        )
        .exists()
    )


def _authoritative_occupancy_status_id_expr():
    return case(
        (or_(Amenity.status == 1, _in_house_exists()), 1),
        (or_(Amenity.status == 3, _pending_allocation_exists()), 3),
        (or_(Amenity.status == 2, _blocking_condition_exists()), 2),
        (Amenity.status == 0, 0),
        else_=None,
    )


def _authoritative_occupancy_status_expr():
    return case(
        (or_(Amenity.status == 1, _in_house_exists()), "Occupied"),
        (or_(Amenity.status == 3, _pending_allocation_exists()), "Allotted"),
        (or_(Amenity.status == 2, _blocking_condition_exists()), "Unavailable"),
        (Amenity.status == 0, "Available"),
        else_=None,
    )


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
            _authoritative_occupancy_status_expr().label("occupancy_status"),
            _authoritative_occupancy_status_id_expr().label("occupancy_status_id"),
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
        .outerjoin(Package, Package.id == Amenity.package_id)
        .outerjoin(AmenityStatus, AmenityStatus.id == Amenity.status)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
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
            Stay.expected_checkin_time,
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
                "expected_checkin_time": r.expected_checkin_time,
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
            func.coalesce(AmenityCondition.display_name, AmenityCondition.name).label("display_name"),
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
    for amenity_id, cid, name, display_name, created, updated in rows:
        out[amenity_id].append(
            {
                "id": cid,
                "name": name,
                "display_name": display_name,
                "created_on": created,
                "updated_on": updated,
            }
        )
    return out


def _enrich(db: Session, rows: list[dict]) -> list[dict]:
    ids = [r["amenity_id"] for r in rows]
    conditions = _conditions_for(db, ids)
    current = _current_stays(db, ids)

    # Master data fallback for rooms without active conditions
    cond_master = {
        c.id: c.display_name or c.name
        for c in db.execute(select(AmenityCondition)).scalars().all()
    }

    for row in rows:
        room_conds = conditions.get(row["amenity_id"], [])
        row["conditions"] = room_conds
        row["current_stay"] = current.get(row["amenity_id"])
        if room_conds:
            prim = room_conds[0]
            row["room_status_id"] = prim["id"]
            # Authoritative database display_name from the active condition
            row["room_status"] = prim.get("display_name") or prim.get("name")
        else:
            if row.get("current_stay") or row.get("occupancy_status") == "Occupied":
                row["room_status_id"] = None
                row["room_status"] = None
            elif row.get("status") == 2 or row.get("occupancy_status") == "Unavailable":
                row["room_status_id"] = CONDITION_UNDER_MAINTENANCE
                row["room_status"] = cond_master.get(CONDITION_UNDER_MAINTENANCE, "Under Maintenance")
            else:
                row["room_status_id"] = CONDITION_READY_TO_OCCUPY
                row["room_status"] = cond_master.get(CONDITION_READY_TO_OCCUPY, "Ready to Occupy")
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
    occupancy_status: str | None = None,
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
    if occupancy_status:
        norm = occupancy_status.strip().lower()
        if occupancy_status in ("Unknown", "Not Set"):
            stmt = stmt.where(_authoritative_occupancy_status_expr().is_(None))
        elif occupancy_status in ("Available", "Occupied", "Allotted", "Unavailable"):
            stmt = stmt.where(_authoritative_occupancy_status_expr() == occupancy_status)
        elif norm in CONDITION_NAME_TO_ID:
            cid = CONDITION_NAME_TO_ID[norm]
            stmt = stmt.where(
                select(AmenityConditionStatus.amenity_id)
                .where(
                    AmenityConditionStatus.amenity_id == Amenity.id,
                    AmenityConditionStatus.amenity_condition_id == cid,
                    AmenityConditionStatus.status == 1,
                )
                .exists()
            )
        else:
            stmt = stmt.where(_authoritative_occupancy_status_expr() == occupancy_status)
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


def get_occupancy_summary(
    db: Session,
    *,
    facility_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    amenity_type_id: uuid.UUID | None = None,
    amenity_category: str | None = "room",
    target_date: date | None = None,
) -> dict:
    if target_date is None:
        target_date = datetime.now().date()

    day_start = datetime.combine(target_date, time.min)
    day_end = datetime.combine(target_date, time.max)

    # Base query for rooms
    room_base = select(Amenity.id).join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
    if amenity_category:
        room_base = room_base.where(AmenityType.amenity_category == amenity_category)
    if facility_id:
        room_base = room_base.where(Amenity.facility_id == facility_id)
    if building_id or floor_id:
        room_base = room_base.outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        if building_id:
            room_base = room_base.where(PropertyChain.level_one_id == building_id)
        if floor_id:
            room_base = room_base.where(PropertyChain.level_two_id == floor_id)
    if amenity_type_id:
        room_base = room_base.where(Amenity.amenity_type_id == amenity_type_id)

    room_ids_subquery = room_base.scalar_subquery()
    status_expr = _authoritative_occupancy_status_expr()

    # Query room counts in one aggregation
    agg_stmt = (
        select(
            func.count().label("total"),
            func.count().filter(status_expr == "Occupied").label("occupied"),
            func.count().filter(status_expr == "Available").label("available"),
            func.count().filter(status_expr == "Allotted").label("allotted"),
            func.count().filter(status_expr == "Unavailable").label("unavailable"),
            func.count().filter(status_expr.is_(None)).label("unknown"),
        )
        .select_from(Amenity)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
    )
    if amenity_category:
        agg_stmt = agg_stmt.where(AmenityType.amenity_category == amenity_category)
    if facility_id:
        agg_stmt = agg_stmt.where(Amenity.facility_id == facility_id)
    if building_id or floor_id:
        agg_stmt = agg_stmt.outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        if building_id:
            agg_stmt = agg_stmt.where(PropertyChain.level_one_id == building_id)
        if floor_id:
            agg_stmt = agg_stmt.where(PropertyChain.level_two_id == floor_id)
    if amenity_type_id:
        agg_stmt = agg_stmt.where(Amenity.amenity_type_id == amenity_type_id)

    agg = db.execute(agg_stmt).mappings().one()
    total = agg["total"] or 0
    occupied = agg["occupied"] or 0
    available = agg["available"] or 0
    allotted = agg["allotted"] or 0
    unavailable = agg["unavailable"] or 0
    unknown = agg["unknown"] or 0

    def pct(val: int) -> float:
        return round((val / total) * 100, 1) if total > 0 else 0.0

    # Daily metrics for target_date
    realized_in = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            Stay.actual_checkin_time >= day_start,
            Stay.actual_checkin_time <= day_end,
        )
    ).scalar_one() or 0

    realized_out = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            Stay.actual_checkout_time >= day_start,
            Stay.actual_checkout_time <= day_end,
        )
    ).scalar_one() or 0

    expected_in = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            Stay.expected_checkin_time >= day_start,
            Stay.expected_checkin_time <= day_end,
        )
    ).scalar_one() or 0

    expected_out = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            Stay.expected_checkout_time >= day_start,
            Stay.expected_checkout_time <= day_end,
        )
    ).scalar_one() or 0

    current_status = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            IN_HOUSE,
        )
    ).scalar_one() or 0

    sod_occupied = db.execute(
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(Stay)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id.in_(room_ids_subquery),
            Stay.actual_checkin_time < day_start,
            or_(
                Stay.actual_checkout_time.is_(None),
                Stay.actual_checkout_time >= day_start,
            ),
        )
    ).scalar_one() or 0

    db_statuses = db.execute(select(AmenityStatus).order_by(AmenityStatus.id)).scalars().all()
    counts_dict = {
        "Occupied": occupied,
        "Available": available,
        "Allotted": allotted,
        "Unavailable": unavailable,
    }

    by_status = [
        {
            "status_id": s.id,
            "status": s.amenity_status_name,
            "count": counts_dict.get(s.amenity_status_name, 0),
            "percent": pct(counts_dict.get(s.amenity_status_name, 0)),
        }
        for s in db_statuses
    ]
    if unknown > 0:
        by_status.append({
            "status_id": None,
            "status": "Unknown",
            "count": unknown,
            "percent": pct(unknown),
        })

    return {
        "total_rooms": total,
        "occupied": occupied,
        "available": available,
        "allotted": allotted,
        "unavailable": unavailable,
        "unknown": unknown,
        "unclassified": unknown,
        "occupied_percent": pct(occupied),
        "available_percent": pct(available),
        "allotted_percent": pct(allotted),
        "unavailable_percent": pct(unavailable),
        "unknown_percent": pct(unknown),
        "unclassified_percent": pct(unknown),
        "by_status": by_status,
        "daily_metrics": {
            "target_date": target_date,
            "start_of_day": sod_occupied,
            "start_of_day_percent": pct(sod_occupied),
            "realized_check_in": realized_in,
            "realized_check_in_percent": pct(realized_in),
            "realized_check_out": realized_out,
            "realized_check_out_percent": pct(realized_out),
            "current_status": current_status,
            "current_status_percent": pct(current_status),
            "expected_check_in": expected_in,
            "expected_check_in_percent": pct(expected_in),
            "expected_check_out": expected_out,
            "expected_check_out_percent": pct(expected_out),
            "end_of_day": available,
            "end_of_day_percent": pct(available),
        },
    }


def get_occupancy_daily_series(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    facility_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    amenity_category: str | None = "room",
) -> list[dict]:
    if date_from > date_to:
        raise ValueError("date_from cannot be after date_to")

    # Base query for room count
    room_base = select(Amenity.id).join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
    if amenity_category:
        room_base = room_base.where(AmenityType.amenity_category == amenity_category)
    if facility_id:
        room_base = room_base.where(Amenity.facility_id == facility_id)
    if building_id or floor_id:
        room_base = room_base.outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        if building_id:
            room_base = room_base.where(PropertyChain.level_one_id == building_id)
        if floor_id:
            room_base = room_base.where(PropertyChain.level_two_id == floor_id)

    total_rooms = db.execute(select(func.count()).select_from(room_base.subquery())).scalar_one() or 0
    room_ids_subquery = room_base.scalar_subquery()

    days_count = (date_to - date_from).days + 1
    series = []
    for d_idx in range(days_count):
        cur_date = date_from + timedelta(days=d_idx)
        cur_start = datetime.combine(cur_date, time.min)
        cur_end = datetime.combine(cur_date, time.max)

        cin = db.execute(
            select(func.count(func.distinct(RoomAllocation.room_id)))
            .select_from(Stay)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id.in_(room_ids_subquery),
                Stay.actual_checkin_time >= cur_start,
                Stay.actual_checkin_time <= cur_end,
            )
        ).scalar_one() or 0

        cout = db.execute(
            select(func.count(func.distinct(RoomAllocation.room_id)))
            .select_from(Stay)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id.in_(room_ids_subquery),
                Stay.actual_checkout_time >= cur_start,
                Stay.actual_checkout_time <= cur_end,
            )
        ).scalar_one() or 0

        in_house_on_day = db.execute(
            select(func.count(func.distinct(RoomAllocation.room_id)))
            .select_from(Stay)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id.in_(room_ids_subquery),
                Stay.actual_checkin_time.is_not(None),
                Stay.actual_checkin_time <= cur_end,
                or_(
                    Stay.actual_checkout_time.is_(None),
                    Stay.actual_checkout_time >= cur_start,
                ),
            )
        ).scalar_one() or 0

        avail = max(0, total_rooms - in_house_on_day)
        occ_pct = round((in_house_on_day / total_rooms) * 100, 1) if total_rooms > 0 else 0.0
        has_data = (cin > 0 or cout > 0 or in_house_on_day > 0)

        series.append({
            "metric_date": cur_date,
            "total_rooms": total_rooms,
            "occupied_rooms": in_house_on_day,
            "available_rooms": avail,
            "occupancy_percent": occ_pct,
            "check_ins": cin,
            "check_outs": cout,
            "has_data": has_data,
        })
    return series
