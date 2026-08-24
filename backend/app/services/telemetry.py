"""Query logic for device telemetry: parameters, readings and snapshots.

Reads live from PostgreSQL. `device.authentication_code` and `device.metadata`
are never selected -- the projection is an explicit allow-list, matching
Phase 2.6.

`device_stat` values are returned as stored strings. No CAST or numeric
aggregation is applied to `device_param_value`, because the column is
VARCHAR(500) and holds several different data types.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    Device,
    DeviceCurrentStat,
    DeviceParam,
    DeviceStat,
    DeviceType,
    OtherDevice,
    Property,
    PropertyChain,
)

BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# device_param
# ---------------------------------------------------------------------------


def _param_stmt() -> Select:
    return select(
        DeviceParam.id,
        DeviceParam.param_name,
        DeviceParam.device_type,
        DeviceType.name.label("device_type_name"),
        DeviceType.device_short_code,
        DeviceParam.data_type,
        DeviceParam.unit,
        DeviceParam.created_on,
        DeviceParam.updated_on,
    ).join(DeviceType, DeviceType.id == DeviceParam.device_type)


def list_device_params(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_type: int | None = None,
    param_name: str | None = None,
    data_type: str | None = None,
    has_unit: bool | None = None,
):
    stmt = _param_stmt().order_by(DeviceParam.device_type, DeviceParam.id)
    if device_type is not None:
        stmt = stmt.where(DeviceParam.device_type == device_type)
    if param_name:
        stmt = stmt.where(DeviceParam.param_name == param_name)
    if data_type:
        stmt = stmt.where(DeviceParam.data_type == data_type)
    if has_unit is not None:
        column = DeviceParam.unit
        stmt = stmt.where(column.is_not(None) if has_unit else column.is_(None))
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_device_param(db: Session, param_id: int):
    return db.execute(
        _param_stmt().where(DeviceParam.id == param_id)
    ).mappings().one_or_none()


def param_reading_count(db: Session, param_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(DeviceStat)
        .where(DeviceStat.device_param_id == param_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# device_stat
# ---------------------------------------------------------------------------


def _stat_stmt() -> Select:
    return (
        select(
            DeviceStat.id,
            DeviceStat.device_id,
            Device.device_uid,
            Device.device_name,
            DeviceType.name.label("device_type_name"),
            # device_stat has no room/facility columns -- both come from the device.
            Device.amenity_id,
            Amenity.name.label("amenity_name"),
            Device.facility_id,
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            DeviceStat.device_param_id,
            DeviceParam.param_name,
            DeviceParam.data_type,
            DeviceParam.unit,
            DeviceStat.device_param_value,
            DeviceStat.timestamp,
            DeviceStat.is_other_device,
            DeviceStat.created_on,
        )
        .select_from(DeviceStat)
        .join(Device, Device.id == DeviceStat.device_id)
        .join(DeviceType, DeviceType.id == Device.device_type)
        .join(DeviceParam, DeviceParam.id == DeviceStat.device_param_id)
        .outerjoin(Amenity, Amenity.id == Device.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def list_device_stats(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_id: uuid.UUID | None = None,
    device_param_id: int | None = None,
    param_name: str | None = None,
    device_type: int | None = None,
    facility_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    timestamp_from: datetime | None = None,
    timestamp_to: datetime | None = None,
):
    stmt = _stat_stmt().order_by(DeviceStat.timestamp.desc(), DeviceStat.id.desc())
    if device_id:
        stmt = stmt.where(DeviceStat.device_id == device_id)
    if device_param_id is not None:
        stmt = stmt.where(DeviceStat.device_param_id == device_param_id)
    if param_name:
        # `param_name` is not unique, so this can span several parameter ids.
        stmt = stmt.where(DeviceParam.param_name == param_name)
    if device_type is not None:
        stmt = stmt.where(Device.device_type == device_type)
    if facility_id:
        stmt = stmt.where(Device.facility_id == facility_id)
    if amenity_id:
        stmt = stmt.where(Device.amenity_id == amenity_id)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    if floor_id:
        stmt = stmt.where(FloorProp.id == floor_id)
    if timestamp_from:
        stmt = stmt.where(DeviceStat.timestamp >= timestamp_from)
    if timestamp_to:
        stmt = stmt.where(DeviceStat.timestamp <= timestamp_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_device_stat(db: Session, stat_id: int):
    return db.execute(
        _stat_stmt().where(DeviceStat.id == stat_id)
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# device_current_stat
# ---------------------------------------------------------------------------


def _current_stat_stmt() -> Select:
    return (
        select(
            DeviceCurrentStat.id,
            DeviceCurrentStat.device_id,
            Device.device_uid,
            Device.device_name,
            DeviceType.name.label("device_type_name"),
            Device.amenity_id,
            Amenity.name.label("amenity_name"),
            Device.facility_id,
            DeviceCurrentStat.device_stats,
            DeviceCurrentStat.is_other_device,
            DeviceCurrentStat.created_on,
            DeviceCurrentStat.updated_on,
        )
        .select_from(DeviceCurrentStat)
        .join(Device, Device.id == DeviceCurrentStat.device_id)
        .join(DeviceType, DeviceType.id == Device.device_type)
        .outerjoin(Amenity, Amenity.id == Device.amenity_id)
    )


def list_device_current_stats(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    device_type: int | None = None,
):
    stmt = _current_stat_stmt().order_by(Device.device_name)
    if device_id:
        stmt = stmt.where(DeviceCurrentStat.device_id == device_id)
    if facility_id:
        stmt = stmt.where(Device.facility_id == facility_id)
    if amenity_id:
        stmt = stmt.where(Device.amenity_id == amenity_id)
    if device_type is not None:
        stmt = stmt.where(Device.device_type == device_type)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_device_current_stat(db: Session, current_stat_id: uuid.UUID):
    return db.execute(
        _current_stat_stmt().where(DeviceCurrentStat.id == current_stat_id)
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# other_device
# ---------------------------------------------------------------------------


def _other_device_stmt() -> Select:
    # `msg_string` (raw payload) is NOT selected -- unbounded device JSON.
    return select(
        OtherDevice.id,
        OtherDevice.msg_id,
        OtherDevice.device_name,
        OtherDevice.voltage,
        OtherDevice.current,
        OtherDevice.power,
        OtherDevice.power_factor,
        OtherDevice.all_energy,
        OtherDevice.thirty_day_energy,
        OtherDevice.today_energy,
        OtherDevice.current_hour_energy,
        OtherDevice.ec,
        OtherDevice.timestamp,
        OtherDevice.created_on,
    )


def list_other_device_readings(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_name: str | None = None,
    timestamp_from: datetime | None = None,
    timestamp_to: datetime | None = None,
):
    stmt = _other_device_stmt().order_by(OtherDevice.timestamp.desc())
    if device_name:
        stmt = stmt.where(OtherDevice.device_name == device_name)
    if timestamp_from:
        stmt = stmt.where(OtherDevice.timestamp >= timestamp_from)
    if timestamp_to:
        stmt = stmt.where(OtherDevice.timestamp <= timestamp_to)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_other_device_reading(db: Session, reading_id: int):
    return db.execute(
        _other_device_stmt().where(OtherDevice.id == reading_id)
    ).mappings().one_or_none()
