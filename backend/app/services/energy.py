"""Query logic for energy statistics and the daily KPI series.

The ONLY arithmetic performed anywhere in this module is SUM and COUNT over
`energy_stat.energy_consumed`. No tariff, currency, carbon factor, baseline or
efficiency ratio is applied, because the schema stores none and no calculation
rule is documented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    DailyDualDataPoint,
    DeviceParam,
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

#: `energy_stat.energy_consumed` is the stored ACTIVE energy reading, and
#: `device_param` is the telemetry parameter registry that records each
#: parameter's unit. This is the `param_name` that describes it.
ACTIVE_ENERGY_PARAM = "active_energy"


def active_energy_unit(db: Session) -> str | None:
    """The unit `energy_stat.energy_consumed` is recorded in.

    RESOLVED FROM CONFIGURATION, NOT PER READING, and deliberately so.
    `energy_stat` has no unit column and cannot be joined to `device`: its
    `device_name` is free text and none of its values match `device.device_name`
    or `device.device_uid`. So there is no path from a reading to the device
    type that would carry a per-row unit. What the schema does register is the
    unit of the `active_energy` parameter itself, in `device_param`.

    Returns None when the registry holds no unit for the parameter, or when
    device types disagree on it -- one label cannot honestly describe every
    reading in that case, and a null keeps the caller from implying otherwise.
    """
    units = (
        db.execute(
            select(DeviceParam.unit)
            .where(DeviceParam.param_name == ACTIVE_ENERGY_PARAM)
            .where(DeviceParam.unit.is_not(None))
            .distinct()
        )
        .scalars()
        .all()
    )
    return units[0] if len(units) == 1 else None


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
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """SUM/COUNT rollup. IKANOS stores energy hourly only; day and per-room
    views are aggregated here at query time, never precomputed.

    `date_from` / `date_to` are the caller-facing way to bound the period. They
    are converted to the stored `hour` (hours elapsed from 2000) with
    `timestamp_to_hour`, so the filter runs against the real stored column and
    uses `ix_energy_stat_amenity_id_hour` rather than computing a timestamp per
    row. Callers that already hold raw hour numbers can still pass
    `hour_from` / `hour_to`; when both forms are given the NARROWER bound wins,
    so neither can silently widen the other's window.

    Every figure returned -- `total_energy_consumed`, `reading_count` and the
    buckets -- is summed from the rows this filter selects. There is no
    all-time aggregate in the response.
    """
    if group_by not in GROUP_BY_CHOICES:
        raise ValueError(f"group_by must be one of {GROUP_BY_CHOICES}")

    if date_from is not None:
        bound = timestamp_to_hour(date_from)
        hour_from = bound if hour_from is None else max(hour_from, bound)
    if date_to is not None:
        bound = timestamp_to_hour(date_to)
        hour_to = bound if hour_to is None else min(hour_to, bound)
    if hour_from is not None and hour_to is not None and hour_from > hour_to:
        raise ValueError("date_from/hour_from must not be later than date_to/hour_to")

    total_energy = func.sum(EnergyStat.energy_consumed).label("total_energy_consumed")
    reading_count = func.count().label("reading_count")

    if group_by == "hour":
        key, label = EnergyStat.hour, None
    elif group_by == "day":
        # Whole days since the epoch: FLOOR division of the stored hour.
        #
        # `//` is deliberate. `cast(hour / 24, Integer)` looks equivalent but is
        # not: SQLAlchemy renders `/` as true division
        # (`hour / CAST(24 AS NUMERIC)`) and PostgreSQL ROUNDS when casting
        # numeric to integer, so hour 233388 (2026-08-16 12:00) produced 9724.5
        # -> 9725 and was reported under 2026-08-17. Every reading from midday
        # onward was attributed to the following day, and two calendar days of
        # data collapsed into one bucket. `//` emits plain integer division,
        # which truncates; `hour` is never negative, so truncation is floor.
        key, label = EnergyStat.hour // 24, None
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
        # Read from `device_param`, never a literal -- see active_energy_unit.
        "energy_unit": active_energy_unit(db),
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


def caleido_at_work(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    facility_id: uuid.UUID | None = None,
) -> list[dict]:
    """The Caleido At Work rings, one aggregated row per metric.

    WHY THIS EXISTS. The dashboard needs four ratios. It used to fetch a PAGE
    of raw `daily_dual_data_point` rows -- every metric type, up to twenty rows
    -- and then pick the newest row per type and divide dp_1 by dp_2 in the
    browser. That put both the record selection and the percentage in the
    frontend, over a dataset it had to receive in full to choose from.

    The business rule is unchanged and is NOT reinvented here: these are daily
    snapshots, so the ring shows the MOST RECENT snapshot inside the selected
    window, never an average or a sum across days. `DISTINCT ON (metric_type)`
    with a descending date order is that rule expressed once, in SQL, so the
    database returns one row per metric instead of a page to sift through.

    dp_1 is the numerator ("online", "resolved", ...) and dp_2 the denominator,
    exactly as the table stores them. The percentage is computed from those two
    stored values and nothing else -- no constant, no fallback, no default.
    """
    stmt = (
        select(
            DailyDualDataPoint.metric_type,
            DailyDualDataPoint.metric_date,
            DailyDualDataPoint.dp_1,
            DailyDualDataPoint.dp_2,
        )
        .distinct(DailyDualDataPoint.metric_type)
        .order_by(
            DailyDualDataPoint.metric_type,
            DailyDualDataPoint.metric_date.desc(),
        )
    )
    if facility_id:
        stmt = stmt.where(DailyDualDataPoint.facility_id == facility_id)
    if date_from:
        stmt = stmt.where(DailyDualDataPoint.metric_date >= date_from)
    if date_to:
        stmt = stmt.where(DailyDualDataPoint.metric_date <= date_to)

    metrics = []
    for row in db.execute(stmt).mappings().all():
        numerator = float(row["dp_1"])
        denominator = float(row["dp_2"])
        metrics.append(
            {
                "metric_type": row["metric_type"],
                "metric_date": row["metric_date"],
                "dp_1": numerator,
                "dp_2": denominator,
                # floor(x + 0.5), not round(): Python's round() is
                # banker's rounding, so round(2.5) is 2 and the ring would
                # disagree with the value the browser used to show for the
                # same stored pair. Percentages here are never negative.
                "percentage": (
                    int((numerator / denominator) * 100 + 0.5) if denominator > 0 else 0
                ),
            }
        )
    return metrics


def get_daily_data_point(db: Session, metric_date: date, metric_type: str):
    """Looked up by the real composite key -- there is no single id."""
    return db.execute(
        select(DailyDualDataPoint).where(
            DailyDualDataPoint.metric_date == metric_date,
            DailyDualDataPoint.metric_type == metric_type,
        )
    ).scalar_one_or_none()
