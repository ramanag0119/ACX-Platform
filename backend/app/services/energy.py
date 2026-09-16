"""Query logic for energy statistics and the daily KPI series.

The ONLY arithmetic performed anywhere in this module is SUM and COUNT over
`energy_stat.energy_consumed`. No tariff, currency, carbon factor, baseline or
efficiency ratio is applied, because the schema stores none and no calculation
rule is documented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, Integer, cast, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    DailyDualDataPoint,
    EnergyStat,
    Property,
    PropertyChain,
)

BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")

#: IKANOS column comment on `energy_stat.hour`: "hours elapsed from 2000".
#: Verified against the data -- hour 233388 is 2026-08-16 12:00 UTC.
ENERGY_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)

GROUP_BY_CHOICES = ("hour", "day", "amenity", "device")


def hour_to_timestamp(hour: int) -> datetime:
    return ENERGY_EPOCH + timedelta(hours=int(hour))


def timestamp_to_hour(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int((moment - ENERGY_EPOCH).total_seconds() // 3600)


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# energy_stat
# ---------------------------------------------------------------------------


def _energy_stmt() -> Select:
    return (
        select(
            EnergyStat.device_name,
            EnergyStat.facility_id,
            EnergyStat.amenity_id,
            Amenity.name.label("amenity_name"),
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            EnergyStat.hour,
            EnergyStat.energy_consumed,
            EnergyStat.created_on,
            EnergyStat.updated_on,
        )
        .select_from(EnergyStat)
        .join(Amenity, Amenity.id == EnergyStat.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def _apply_energy_filters(
    stmt: Select,
    *,
    facility_id: uuid.UUID | None,
    amenity_id: uuid.UUID | None,
    building_id: uuid.UUID | None,
    floor_id: uuid.UUID | None,
    device_name: str | None,
    hour_from: int | None,
    hour_to: int | None,
) -> Select:
    if facility_id:
        stmt = stmt.where(EnergyStat.facility_id == facility_id)
    if amenity_id:
        stmt = stmt.where(EnergyStat.amenity_id == amenity_id)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    if floor_id:
        stmt = stmt.where(FloorProp.id == floor_id)
    if device_name:
        stmt = stmt.where(EnergyStat.device_name == device_name)
    if hour_from is not None:
        stmt = stmt.where(EnergyStat.hour >= hour_from)
    if hour_to is not None:
        stmt = stmt.where(EnergyStat.hour <= hour_to)
    return stmt


def list_energy_stats(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    device_name: str | None = None,
    hour_from: int | None = None,
    hour_to: int | None = None,
):
    stmt = _apply_energy_filters(
        _energy_stmt().order_by(EnergyStat.hour.desc(), EnergyStat.device_name),
        facility_id=facility_id, amenity_id=amenity_id, building_id=building_id,
        floor_id=floor_id, device_name=device_name,
        hour_from=hour_from, hour_to=hour_to,
    )
    total = _count(db, stmt)
    rows = [
        {**dict(r), "hour_timestamp": hour_to_timestamp(r["hour"])}
        for r in db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    ]
    return rows, total


def energy_summary(
    db: Session,
    *,
    group_by: str,
    facility_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    device_name: str | None = None,
    hour_from: int | None = None,
    hour_to: int | None = None,
) -> dict:
    """SUM/COUNT rollup. IKANOS stores energy hourly only; day and per-room
    views are aggregated here at query time, never precomputed."""
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"group_by must be one of {GROUP_BY_CHOICES}")

    total_energy = func.sum(EnergyStat.energy_consumed).label("total_energy_consumed")
    reading_count = func.count().label("reading_count")

    if group_by == "hour":
        key, label = EnergyStat.hour, None
    elif group_by == "day":
        # Whole days since the epoch: integer division of the stored hour.
        key, label = cast(EnergyStat.hour / 24, Integer), None
    elif group_by == "amenity":
        key, label = EnergyStat.amenity_id, Amenity.name
    else:
        key, label = EnergyStat.device_name, None

    columns = [key.label("bucket"), total_energy, reading_count]
    if label is not None:
        columns.insert(1, label.label("bucket_label"))

    stmt = (
        select(*columns)
        .select_from(EnergyStat)
        .join(Amenity, Amenity.id == EnergyStat.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )
    stmt = _apply_energy_filters(
        stmt, facility_id=facility_id, amenity_id=amenity_id,
        building_id=building_id, floor_id=floor_id, device_name=device_name,
        hour_from=hour_from, hour_to=hour_to,
    )
    group_cols = [key] + ([label] if label is not None else [])
    stmt = stmt.group_by(*group_cols).order_by(key)

    buckets = []
    for row in db.execute(stmt).mappings().all():
        raw = row["bucket"]
        if group_by == "hour":
            bucket = hour_to_timestamp(raw).isoformat()
        elif group_by == "day":
            bucket = (ENERGY_EPOCH + timedelta(days=int(raw))).date().isoformat()
        else:
            bucket = str(raw)
        buckets.append(
            {
                "bucket": bucket,
                "bucket_label": row.get("bucket_label"),
                "total_energy_consumed": float(row["total_energy_consumed"] or 0),
                "reading_count": row["reading_count"],
            }
        )

    return {
        "group_by": group_by,
        "bucket_count": len(buckets),
        "total_energy_consumed": round(
            sum(b["total_energy_consumed"] for b in buckets), 6
        ),
        "reading_count": sum(b["reading_count"] for b in buckets),
        "buckets": buckets,
    }


# ---------------------------------------------------------------------------
# daily_dual_data_point
# ---------------------------------------------------------------------------


def list_daily_data_points(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    metric_type: str | None = None,
    metric_date_from: date | None = None,
    metric_date_to: date | None = None,
):
    stmt = select(DailyDualDataPoint).order_by(
        DailyDualDataPoint.metric_date.desc(), DailyDualDataPoint.metric_type
    )
    if facility_id:
        stmt = stmt.where(DailyDualDataPoint.facility_id == facility_id)
    if metric_type:
        stmt = stmt.where(DailyDualDataPoint.metric_type == metric_type)
    if metric_date_from:
        stmt = stmt.where(DailyDualDataPoint.metric_date >= metric_date_from)
    if metric_date_to:
        stmt = stmt.where(DailyDualDataPoint.metric_date <= metric_date_to)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_daily_data_point(db: Session, metric_date: date, metric_type: str):
    """Looked up by the real composite key -- there is no single id."""
    return db.execute(
        select(DailyDualDataPoint).where(
            DailyDualDataPoint.metric_date == metric_date,
            DailyDualDataPoint.metric_type == metric_type,
        )
    ).scalar_one_or_none()
