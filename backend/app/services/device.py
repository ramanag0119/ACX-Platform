"""Query logic for device inventory, types, firmware and health.

Reads live from PostgreSQL through the caller's session.

Two columns are excluded at the query level and never selected:
`device.authentication_code` (a device credential) and `device.metadata`
(an unbounded bag). The projection is an explicit allow-list, so a column
added later cannot leak by default.

Telemetry (`device_stat`, `device_current_stat`), MQTT and the command queue
are deliberately NOT read here -- they belong to later phases.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    BatteryLifeStat,
    Device,
    DeviceHealthStat,
    DeviceType,
    Firmware,
    Property,
    PropertyChain,
    SensorOperationStat,
)

# Location is resolved through the Phase 2.2 projection: a device sits in an
# amenity, the amenity sits on a property_chain, and the chain names the
# building (level one) and floor (level two).
BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")

# `firmware` appears twice on a device: what it runs, and what it should run.
CurrentFw = aliased(Firmware, name="current_firmware")
ExpectedFw = aliased(Firmware, name="expected_firmware")


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# device_type
# ---------------------------------------------------------------------------


def list_device_types(db: Session, *, page: int, page_size: int):
    stmt = select(DeviceType).order_by(DeviceType.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_device_type(db: Session, device_type_id: int) -> DeviceType | None:
    return db.get(DeviceType, device_type_id)


def device_type_counts(db: Session, device_type_id: int) -> dict[str, int]:
    return {
        "device_count": db.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.device_type == device_type_id)
        ).scalar_one(),
        "firmware_count": db.execute(
            select(func.count())
            .select_from(Firmware)
            .where(Firmware.device_type_id == device_type_id)
        ).scalar_one(),
    }


# ---------------------------------------------------------------------------
# firmware
# ---------------------------------------------------------------------------


def _firmware_stmt() -> Select:
    return select(
        Firmware.id,
        Firmware.firmware_version,
        Firmware.device_type_id,
        DeviceType.name.label("device_type_name"),
        Firmware.firmware_filename,
        Firmware.firmware_url,
        Firmware.firmware_size,
        Firmware.crc,
        Firmware.release_date,
        Firmware.release_notes,
        Firmware.decommission_reason,
        Firmware.status,
        Firmware.created_on,
        Firmware.updated_on,
    ).join(DeviceType, DeviceType.id == Firmware.device_type_id)


def list_firmware(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_type_id: int | None = None,
    status: str | None = None,
    firmware_version: str | None = None,
):
    stmt = _firmware_stmt().order_by(Firmware.device_type_id, Firmware.firmware_version)
    if device_type_id is not None:
        stmt = stmt.where(Firmware.device_type_id == device_type_id)
    if status:
        stmt = stmt.where(Firmware.status == status)
    if firmware_version:
        stmt = stmt.where(Firmware.firmware_version == firmware_version)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_firmware(db: Session, firmware_id: uuid.UUID):
    return db.execute(
        _firmware_stmt().where(Firmware.id == firmware_id)
    ).mappings().one_or_none()


def firmware_usage(db: Session, firmware_id: uuid.UUID) -> dict[str, int]:
    return {
        "devices_running": db.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.current_firmware_version == firmware_id)
        ).scalar_one(),
        "devices_expecting": db.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.expected_firmware_version == firmware_id)
        ).scalar_one(),
    }


# ---------------------------------------------------------------------------
# device
# ---------------------------------------------------------------------------


def _device_stmt() -> Select:
    """Explicit allow-list. `authentication_code` and `metadata` are absent
    on purpose and must stay absent."""
    up_to_date = case(
        (
            Device.current_firmware_version.is_(None)
            | Device.expected_firmware_version.is_(None),
            None,
        ),
        else_=Device.current_firmware_version == Device.expected_firmware_version,
    )
    return (
        select(
            Device.id,
            Device.device_uid,
            Device.device_name,
            Device.appliance_name,
            Device.part_number,
            Device.model,
            Device.manufacturer_name,
            Device.mfg_date,
            Device.installed_on,
            Device.device_type,
            DeviceType.name.label("device_type_name"),
            DeviceType.device_short_code,
            Device.facility_id,
            Device.amenity_id,
            Amenity.name.label("amenity_name"),
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            Device.parent_device_id,
            Device.health_status,
            Device.device_config_status,
            Device.device_temperature,
            Device.is_power_off,
            Device.operational_mode,
            Device.is_other_device,
            Device.status,
            Device.current_firmware_version,
            CurrentFw.firmware_version.label("current_firmware"),
            Device.expected_firmware_version,
            ExpectedFw.firmware_version.label("expected_firmware"),
            up_to_date.label("firmware_up_to_date"),
            Device.created_on,
            Device.updated_on,
        )
        .select_from(Device)
        .join(DeviceType, DeviceType.id == Device.device_type)
        .join(Amenity, Amenity.id == Device.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
        .outerjoin(CurrentFw, CurrentFw.id == Device.current_firmware_version)
        .outerjoin(ExpectedFw, ExpectedFw.id == Device.expected_firmware_version)
    )


def list_devices(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    device_type: int | None = None,
    health_status: str | None = None,
    device_config_status: str | None = None,
    model: str | None = None,
    manufacturer_name: str | None = None,
    device_uid: str | None = None,
    parent_device_id: uuid.UUID | None = None,
    is_standalone: bool | None = None,
    firmware_id: uuid.UUID | None = None,
    firmware_outdated: bool | None = None,
):
    stmt = _device_stmt().order_by(Amenity.name, Device.device_name)
    if facility_id:
        stmt = stmt.where(Device.facility_id == facility_id)
    if amenity_id:
        stmt = stmt.where(Device.amenity_id == amenity_id)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    if floor_id:
        stmt = stmt.where(FloorProp.id == floor_id)
    if device_type is not None:
        stmt = stmt.where(Device.device_type == device_type)
    if health_status:
        stmt = stmt.where(Device.health_status == health_status)
    if device_config_status:
        stmt = stmt.where(Device.device_config_status == device_config_status)
    if model:
        stmt = stmt.where(Device.model == model)
    if manufacturer_name:
        stmt = stmt.where(Device.manufacturer_name == manufacturer_name)
    if device_uid:
        stmt = stmt.where(Device.device_uid == device_uid)
    if parent_device_id:
        stmt = stmt.where(Device.parent_device_id == parent_device_id)
    if is_standalone is not None:
        column = Device.parent_device_id
        stmt = stmt.where(column.is_(None) if is_standalone else column.is_not(None))
    if firmware_id:
        stmt = stmt.where(Device.current_firmware_version == firmware_id)
    if firmware_outdated is not None:
        mismatch = Device.current_firmware_version != Device.expected_firmware_version
        stmt = stmt.where(mismatch if firmware_outdated else ~mismatch)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_device(db: Session, device_id: uuid.UUID):
    return db.execute(
        _device_stmt().where(Device.id == device_id)
    ).mappings().one_or_none()


def _device_refs(db: Session, stmt: Select) -> list[dict]:
    rows = db.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def device_children(db: Session, device_id: uuid.UUID) -> list[dict]:
    stmt = (
        select(
            Device.id,
            Device.device_uid,
            Device.device_name,
            Device.device_type,
            DeviceType.name.label("device_type_name"),
        )
        .join(DeviceType, DeviceType.id == Device.device_type)
        .where(Device.parent_device_id == device_id)
        .order_by(Device.device_type)
    )
    return _device_refs(db, stmt)


def device_parent(db: Session, parent_id: uuid.UUID | None) -> dict | None:
    if parent_id is None:
        return None
    stmt = (
        select(
            Device.id,
            Device.device_uid,
            Device.device_name,
            Device.device_type,
            DeviceType.name.label("device_type_name"),
        )
        .join(DeviceType, DeviceType.id == Device.device_type)
        .where(Device.id == parent_id)
    )
    rows = _device_refs(db, stmt)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def device_health(db: Session, device_id: uuid.UUID, *, sample_limit: int) -> dict | None:
    """Assemble the health picture from the tables that actually hold it."""
    device = db.execute(
        select(
            Device.id,
            Device.device_uid,
            Device.device_name,
            DeviceType.name.label("device_type_name"),
            Device.health_status,
            Device.device_config_status,
            Device.device_temperature,
            Device.is_power_off,
            Device.operational_mode,
        )
        .join(DeviceType, DeviceType.id == Device.device_type)
        .where(Device.id == device_id)
    ).mappings().one_or_none()
    if device is None:
        return None

    last_reported_on = db.execute(
        select(func.max(DeviceHealthStat.created_on)).where(
            DeviceHealthStat.device_id == device_id
        )
    ).scalar_one_or_none()

    sample_count = db.execute(
        select(func.count())
        .select_from(DeviceHealthStat)
        .where(DeviceHealthStat.device_id == device_id)
    ).scalar_one()

    samples = db.execute(
        select(
            DeviceHealthStat.id,
            DeviceHealthStat.device_health_status,
            DeviceHealthStat.device_temperature,
            DeviceHealthStat.created_on,
        )
        .where(DeviceHealthStat.device_id == device_id)
        .order_by(DeviceHealthStat.created_on.desc())
        .limit(sample_limit)
    ).mappings().all()

    battery = db.execute(
        select(
            BatteryLifeStat.cycle_number,
            BatteryLifeStat.initial_battery_percentage,
            BatteryLifeStat.latest_battery_percentage,
            BatteryLifeStat.battery_life,
            BatteryLifeStat.created_on,
        )
        .where(BatteryLifeStat.device_id == device_id)
        .order_by(BatteryLifeStat.cycle_number.desc())
    ).mappings().all()

    operation = db.execute(
        select(
            SensorOperationStat.stats_date,
            SensorOperationStat.operation_percentage,
        )
        .where(SensorOperationStat.device_id == device_id)
        .order_by(SensorOperationStat.stats_date.desc())
    ).mappings().all()

    return {
        **dict(device),
        "device_id": device["id"],
        "last_reported_on": last_reported_on,
        "health_sample_count": sample_count,
        "recent_samples": [dict(s) for s in samples],
        "battery_cycles": [dict(b) for b in battery],
        "operation_history": [dict(o) for o in operation],
    }
