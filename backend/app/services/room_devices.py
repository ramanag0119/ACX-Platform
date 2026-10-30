"""Room <-> OSS device mapping (BSS side of the OSS composition).

Device data is read from the externally owned OSS database through the OSS
microservice; HMS never writes to it. Rooms are HMS data. `room_device_map`
joins the two, and this module is the only place that reads or writes it:

* resolve a room / floor / building / facility to the OSS device ids in it,
  so `/devices?amenity_id=...` can ask OSS for exactly those devices;
* look up the room (and its floor / building) for OSS devices, so device
  responses carry the location HMS knows and OSS does not;
* count a room's devices for the occupancy view, without calling OSS;
* assign / unassign a device, writing only `room_device_map` in hms_db.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Amenity, Property, PropertyChain, RoomDeviceMap
from app.services import oss_client
from app.services.writes import Conflict, Invalid, require_exists, require_row, transaction

# Same location projection as the device service: amenity -> property_chain,
# whose level one is the building and level two the floor.
BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")

#: Device-list filters HMS answers from the mapping (OSS has no rooms).
LOCATION_FILTERS = ("amenity_id", "floor_id", "building_id", "facility_id")


def _located() -> Select:
    return (
        select(
            RoomDeviceMap.id,
            RoomDeviceMap.oss_device_id,
            RoomDeviceMap.amenity_id,
            Amenity.name.label("amenity_name"),
            Amenity.facility_id,
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            RoomDeviceMap.created_on,
        )
        .join(Amenity, Amenity.id == RoomDeviceMap.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def _where_location(stmt: Select, filters: dict[str, uuid.UUID | None]) -> Select:
    if filters.get("amenity_id"):
        stmt = stmt.where(RoomDeviceMap.amenity_id == filters["amenity_id"])
    if filters.get("floor_id"):
        stmt = stmt.where(FloorProp.id == filters["floor_id"])
    if filters.get("building_id"):
        stmt = stmt.where(BuildingProp.id == filters["building_id"])
    if filters.get("facility_id"):
        stmt = stmt.where(Amenity.facility_id == filters["facility_id"])
    return stmt


# ---------------------------------------------------------------------------
# reads used by the OSS proxy and occupancy
# ---------------------------------------------------------------------------

def device_ids_at(db: Session, **filters: uuid.UUID | None) -> list[uuid.UUID]:
    """OSS device ids mapped to the given room / floor / building / facility."""
    stmt = _where_location(_located(), filters).order_by(RoomDeviceMap.oss_device_id)
    return [r.oss_device_id for r in db.execute(stmt).all()]


def locations_for(db: Session, device_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Room / floor / building for each mapped OSS device id (unmapped: absent)."""
    if not device_ids:
        return {}
    rows = db.execute(
        _located().where(RoomDeviceMap.oss_device_id.in_(device_ids))
    ).mappings().all()
    return {
        r["oss_device_id"]: {
            "amenity_id": r["amenity_id"],
            "amenity_name": r["amenity_name"],
            "facility_id": r["facility_id"],
            "building_id": r["building_id"],
            "building_name": r["building_name"],
            "floor_id": r["floor_id"],
            "floor_name": r["floor_name"],
        }
        for r in rows
    }


def count_in_room(db: Session, amenity_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(RoomDeviceMap)
        .where(RoomDeviceMap.amenity_id == amenity_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# the mapping itself
# ---------------------------------------------------------------------------

def list_room_devices(
    db: Session, *, page: int, page_size: int, **filters: uuid.UUID | None
) -> tuple[list[dict], int]:
    stmt = _where_location(_located(), filters)
    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    rows = db.execute(
        stmt.order_by(Amenity.name, RoomDeviceMap.oss_device_id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).mappings().all()
    return [dict(r) for r in rows], total


def get_room_device(db: Session, map_id: uuid.UUID) -> dict:
    require_row(db, RoomDeviceMap, map_id, "Room device mapping")
    return dict(db.execute(_located().where(RoomDeviceMap.id == map_id)).mappings().one())


def assign_device(
    db: Session, *, amenity_id: uuid.UUID, oss_device_id: uuid.UUID, actor_id: uuid.UUID
) -> RoomDeviceMap:
    """Map an OSS device to a room. Writes hms_db only; OSS is only read, to
    confirm the device exists. Raises `oss_client.OssUnavailable` if OSS cannot
    be reached, so a mapping is never made to a device nobody has verified."""
    require_exists(db, Amenity, amenity_id, "Room")
    current = db.execute(
        select(RoomDeviceMap).where(RoomDeviceMap.oss_device_id == oss_device_id)
    ).scalar_one_or_none()
    if current is not None:
        raise Conflict(
            f"Device {oss_device_id} is already mapped to a room.",
            detail={"mapping_id": str(current.id), "amenity_id": str(current.amenity_id)},
        )
    status, _ = oss_client.forward("GET", f"/devices/{oss_device_id}")
    if status == 404:
        raise Invalid(f"Device {oss_device_id} does not exist in OSS.")
    if status != 200:
        raise oss_client.OssUnavailable(f"OSS answered {status} for the device lookup.")

    with transaction(db):
        row = RoomDeviceMap(
            amenity_id=amenity_id, oss_device_id=oss_device_id, created_by=actor_id
        )
        db.add(row)
    return row


def unassign_device(db: Session, map_id: uuid.UUID) -> None:
    row = require_row(db, RoomDeviceMap, map_id, "Room device mapping")
    with transaction(db):
        db.delete(row)
