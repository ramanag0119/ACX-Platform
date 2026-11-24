"""OSS -> contract adapters for energy statistics.

SOURCE, AND WHY IT IS `active_power` RATHER THAN `active_energy`
----------------------------------------------------------------
`insp_device_performance.param_data` carries both signals for metering devices
(IntelliHub, Mikos). Only one of them has a unit that can be VERIFIED from the
payload, so only one is safe to build consumption on.

`active_power` is provably kW. Every metering reading satisfies the electrical
identities, checked against live `insp_iot` data on 2026-11-17::

    V * I / 1000  ~= apparent_power     235.0 * 0.156 / 1000 = 0.0362  vs 0.0359
    apparent_power * power_factor ~= active_power   0.0359 * 0.8085 = 0.0291
                                                            vs active_power 0.0295

Those only balance when the power fields are kilo-units, so kW is READ FROM the
payload, not assumed.

`active_energy` is a cumulative counter whose scale could NOT be established.
Integrating `active_power` over the same window and comparing against the
counter's own delta gives::

    device 0102110000000001   counter 2.59186   integral 0.25922   ratio 10.00
    device 0302110000000001   counter 0.26105   integral 0.02461   ratio 10.61

A ~10x disagreement that is itself inconsistent between devices. Nothing in the
payload or in OSS states the counter's unit, so using it would mean hardcoding
an unverified scale factor. It is therefore NOT used, and no conversion factor
appears anywhere below.

`energy_unit` is returned as NULL for the same reason: the integral is
power x time, so it is kWh *if* `active_power` is kW -- which the identities
above support but no field in OSS actually declares. The number is reported;
the label is left to whoever owns the meter configuration.

THE CALCULATION
---------------
Per device, consecutive readings form intervals. Each interval contributes
trapezoidal energy and is attributed to the IST hour of its LATER reading::

    energy(i) = (active_power[i] + active_power[i-1]) / 2 * dt_hours
    bucket(i) = date_trunc('hour', recorded_at[i] AT TIME ZONE 'Asia/Kolkata')

Hourly grouping is in IST because that is how the database stores and how the
facility reads its day; `Asia/Kolkata` is used rather than a hardcoded +05:30 so
the boundary stays correct if the zone definition ever changes (India observes
no DST today, so the two agree).

An interval longer than `MAX_INTERVAL_HOURS` is DROPPED rather than integrated.
A gap means the device stopped reporting, and a trapezoid across an outage
would invent consumption for a period nobody measured -- the one failure mode
that silently inflates a billing-adjacent number. Readings arrive ~60s apart,
so this discards only genuine outages.

The first reading of each device has no predecessor and so contributes no
interval; this is arithmetic, not data loss.

WHAT IS NOT SUPPORTED
---------------------
OSS is site/customer-scoped and has no room concept, so `facility_id`,
`amenity_id`, `building_id` and `floor_id` filters raise `AdapterNotMapped`
(503) exactly as the device adapter does, rather than silently ignoring a
filter and returning the wrong rows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Numeric, and_, cast, func, select
from sqlalchemy.orm import Session

from app.adapters.base import AdapterNotMapped
from app.db.tables import insp_device, insp_device_performance

P = insp_device_performance
D = insp_device

#: The parameter consumption is derived from. The ONLY energy-related key read.
POWER_PARAM = "active_power"

#: IST. The database stores IST and the business reads its day in IST.
IST_ZONE = "Asia/Kolkata"
IST = timezone(timedelta(hours=5, minutes=30))

#: `hour` epoch. IKANOS `energy_stat` counts hours from 2000-01-01 **UTC**, but
#: IST hour boundaries sit 30 minutes off every UTC hour (16:00 IST = 10:30
#: UTC), so an IST bucket CANNOT be represented exactly on a UTC-hour index --
#: flooring it would report the 16:00 IST bucket as 15:30 IST.
#:
#: Since grouping is mandated in IST, the index is counted from 2000-01-01
#: **IST** instead. `hour` and `hour_timestamp` then round-trip exactly and
#: both mean the same IST hour. The consequence, stated plainly: an OSS energy
#: row's `hour` is NOT directly comparable to a BSS `energy_stat.hour` -- the
#: two differ by the 5h30m offset. `hour_timestamp` is offset-aware and is the
#: unambiguous field; prefer it when comparing across the two sources.
HOUR_EPOCH = datetime(2000, 1, 1, tzinfo=IST)

#: Intervals longer than this are an outage, not a measurement. See module docs.
MAX_INTERVAL_HOURS = 1.0

#: Filters OSS cannot answer -- it has no rooms (INTEGRATION_MAPPING decision 1).
_LOCATION_FILTERS = ("facility_id", "amenity_id", "building_id", "floor_id")

_GROUP_BY = ("hour", "day", "device")


def _reject_location_filters(filters: dict[str, Any]) -> None:
    present = [k for k in _LOCATION_FILTERS if filters.get(k)]
    if present:
        raise AdapterNotMapped(
            f"energy filtered by {', '.join(present)} (OSS is site-scoped and has "
            "no room/amenity linkage; map devices to rooms in HMS instead)"
        )


def _hour_index(bucket_ist: datetime) -> int:
    """Hours since the IST epoch for an IST hour-start.

    `date_trunc(... AT TIME ZONE 'Asia/Kolkata')` returns a NAIVE timestamp
    already expressed in IST, so the zone is attached rather than converted --
    converting it would shift the bucket by the offset twice.
    """
    if bucket_ist.tzinfo is None:
        bucket_ist = bucket_ist.replace(tzinfo=IST)
    return int((bucket_ist - HOUR_EPOCH).total_seconds() // 3600)


def _hourly_rows(db: Session, filters: dict[str, Any]) -> list[dict]:
    """Per (device, IST hour) consumption, newest bucket first."""
    power = cast(P.c.param_data[POWER_PARAM].astext, Numeric)
    window = {"partition_by": P.c.device_uid, "order_by": P.c.recorded_at}

    base = select(
        P.c.device_uid.label("device_uid"),
        P.c.recorded_at.label("recorded_at"),
        power.label("p"),
        func.lag(power).over(**window).label("prev_p"),
        func.lag(P.c.recorded_at).over(**window).label("prev_at"),
    ).where(P.c.param_data.has_key(POWER_PARAM))

    if filters.get("device_uid"):
        base = base.where(P.c.device_uid == filters["device_uid"])
    s = base.subquery("s")

    dt_hours = (
        func.extract("epoch", s.c.recorded_at - s.c.prev_at) / 3600.0
    ).label("dt_h")
    bucket = func.date_trunc(
        "hour", func.timezone(IST_ZONE, s.c.recorded_at)
    ).label("bucket")

    stmt = (
        select(
            s.c.device_uid,
            bucket,
            func.sum(((s.c.p + s.c.prev_p) / 2.0) * dt_hours).label("energy"),
            func.min(s.c.recorded_at).label("first_at"),
            func.max(s.c.recorded_at).label("last_at"),
            func.count().label("intervals"),
        )
        .where(
            and_(
                s.c.prev_at.is_not(None),
                s.c.p.is_not(None),
                s.c.prev_p.is_not(None),
                dt_hours > 0,
                dt_hours <= MAX_INTERVAL_HOURS,
            )
        )
        .group_by(s.c.device_uid, bucket)
        .order_by(bucket.desc(), s.c.device_uid)
    )

    names = dict(
        db.execute(select(D.c.device_uid, D.c.device_name)).all()
    )

    rows: list[dict] = []
    for r in db.execute(stmt).mappings():
        hour_index = _hour_index(r["bucket"])
        rows.append(
            {
                # `device_name` is free text in the HMS contract; fall back to the
                # uid rather than inventing a label when OSS has no name.
                "device_name": names.get(r["device_uid"]) or r["device_uid"],
                "device_uid": r["device_uid"],
                "facility_id": None,
                "amenity_id": None,
                "amenity_name": None,
                "building_id": None,
                "building_name": None,
                "floor_id": None,
                "floor_name": None,
                "hour": hour_index,
                "hour_timestamp": HOUR_EPOCH + timedelta(hours=hour_index),
                "energy_consumed": round(float(r["energy"]), 6),
                "energy_unit": None,
                "reading_count": int(r["intervals"]),
                # Real observation times from the bucket -- nothing synthesised.
                "created_on": r["first_at"],
                "updated_on": r["last_at"],
            }
        )
    return rows


def _apply_hour_bounds(rows: list[dict], filters: dict[str, Any]) -> list[dict]:
    """`hour_from` / `hour_to`, matching the HMS filter contract."""
    def _int(key: str) -> int | None:
        raw = filters.get(key)
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise AdapterNotMapped(f"energy filter {key} must be an integer hour index") from exc

    lo, hi = _int("hour_from"), _int("hour_to")
    if lo is not None:
        rows = [r for r in rows if r["hour"] >= lo]
    if hi is not None:
        rows = [r for r in rows if r["hour"] <= hi]

    name = filters.get("device_name")
    if name:
        rows = [r for r in rows if r["device_name"] == name]
    return rows


def list_energy_stats(db: Session, *, page: int, page_size: int, **filters):
    _reject_location_filters(filters)
    rows = _apply_hour_bounds(_hourly_rows(db, filters), filters)
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def energy_summary(db: Session, *, group_by: str, **filters):
    _reject_location_filters(filters)
    if group_by not in _GROUP_BY:
        # `amenity` is deliberately absent: OSS has no rooms.
        raise AdapterNotMapped(
            f"energy summary grouped by {group_by!r} "
            f"(OSS supports {', '.join(_GROUP_BY)})"
        )

    rows = _apply_hour_bounds(_hourly_rows(db, filters), filters)

    buckets: dict[str, dict] = {}
    for r in rows:
        if group_by == "hour":
            key, label = r["hour_timestamp"].isoformat(), None
        elif group_by == "day":
            key = (r["hour_timestamp"].astimezone(IST)).date().isoformat()
            label = None
        else:  # device
            key, label = r["device_name"], r["device_name"]
        b = buckets.setdefault(
            key,
            {"bucket": key, "bucket_label": label,
             "total_energy_consumed": 0.0, "reading_count": 0},
        )
        b["total_energy_consumed"] += r["energy_consumed"]
        b["reading_count"] += r["reading_count"]

    ordered = sorted(buckets.values(), key=lambda b: b["bucket"])
    for b in ordered:
        b["total_energy_consumed"] = round(b["total_energy_consumed"], 6)

    return {
        "group_by": group_by,
        "bucket_count": len(ordered),
        "total_energy_consumed": round(
            sum(b["total_energy_consumed"] for b in ordered), 6
        ),
        "reading_count": sum(b["reading_count"] for b in ordered),
        # Null for the reason given in the module docstring: the unit is not
        # declared anywhere in OSS and is not inferred here.
        "energy_unit": None,
        "buckets": ordered,
    }
