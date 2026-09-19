"""Response models for energy statistics and the daily KPI series.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * `energy_stat` is the ONLY table storing a numeric energy measurement:
    `energy_consumed DOUBLE PRECISION`. Its primary key is the four-column
    natural key `(device_name, facility_id, amenity_id, hour)`, so there is no
    single id and therefore **no `/energy-stats/{id}` detail route**.

  * **`energy_stat` stores NO unit.** `device_param` records kWh for
    `active_energy`, but that is a different table and nothing links the two.
    The value is returned raw and its unit is reported as unknown.

  * **`energy_stat.hour` is not a timestamp.** The IKANOS column comment reads
    "hours elapsed from 2000", and the data confirms it: hour 233388 is
    2026-08-16 12:00 UTC. Both the raw integer and the derived UTC timestamp
    are returned, the latter clearly labelled as derived.

  * **`energy_stat` has no device foreign key.** It is keyed by
    `device_name VARCHAR(11)`, so an energy row cannot be joined to `device`.

  * `daily_dual_data_point` holds the dashboard KPI pairs. `metric_type` is a
    5-value enum and dp_1/dp_2 are a numerator/denominator pair -- which is why
    the Dashboard rings read "n of m". Its PK is
    `(metric_date, metric_type)` and EXCLUDES facility_id, so the table cannot
    hold two facilities.

=== NOT COMPUTED, DELIBERATELY ===

There is no tariff, currency, carbon-factor, baseline or efficiency column
anywhere in the schema, and no calculation rule is documented. Cost, CO2,
savings, efficiency and monetary value are therefore NOT derived and NOT
returned. The only arithmetic offered is SUM/COUNT over the stored
`energy_consumed`, which introduces no constant of any kind.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# energy_stat
# ---------------------------------------------------------------------------


class EnergyStatRead(ORMModel):
    """One hourly energy row, exactly as stored."""

    device_name: str = Field(
        examples=["101-mik"],
        description="Free text, varchar(11). There is no FK to `device`.",
    )
    facility_id: uuid.UUID
    amenity_id: uuid.UUID
    amenity_name: str | None = Field(default=None, examples=["101"])
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    hour: int = Field(
        examples=[233388],
        description="Hours elapsed since 2000-01-01 UTC, as IKANOS stores it",
    )
    hour_timestamp: datetime = Field(
        description="DERIVED from `hour` using the documented 2000-01-01 epoch"
    )
    energy_consumed: float = Field(
        examples=[0.42],
        description="Raw stored value. `energy_stat` carries NO unit column.",
    )
    energy_unit: None = Field(
        default=None,
        description="Always null: no unit is stored on this table. Do not assume kWh.",
    )
    created_on: datetime
    updated_on: datetime


class EnergySummaryBucket(ORMModel):
    """One aggregation bucket.

    The only arithmetic is SUM and COUNT over `energy_consumed`. No tariff,
    carbon factor or baseline is applied, because none exists in the schema.
    """

    bucket: str = Field(
        examples=["2026-08-16"],
        description="Bucket key: hour timestamp, date, amenity id or device name",
    )
    bucket_label: str | None = Field(
        default=None, examples=["101"], description="Room name where applicable"
    )
    total_energy_consumed: float = Field(description="SUM(energy_consumed), unitless")
    reading_count: int = Field(description="COUNT(*) of hourly rows in the bucket")


class EnergySummaryRead(BaseModel):
    """Query-time rollup of `energy_stat`.

    IKANOS stores energy hourly only; daily and per-room views are aggregated
    on read. Nothing is precomputed or stored.
    """

    group_by: str = Field(examples=["day"], description="hour | day | amenity | device")
    bucket_count: int
    total_energy_consumed: float = Field(description="SUM across every bucket")
    reading_count: int
    energy_unit: str | None = Field(
        default=None,
        examples=["kWh"],
        description=(
            "The unit `energy_consumed` is recorded in, read from `device_param` "
            "where `param_name = 'active_energy'`. `energy_stat` itself stores no "
            "unit and cannot be joined to `device` (`device_name` is free text), "
            "so this describes the PARAMETER's configured unit rather than a "
            "per-reading one. Null when the registry has no unit for the "
            "parameter or when device types disagree on it."
        ),
    )
    buckets: list[EnergySummaryBucket]


# ---------------------------------------------------------------------------
# daily_dual_data_point
# ---------------------------------------------------------------------------


class CaleidoMetricRead(BaseModel):
    """One Caleido At Work ring: the newest daily snapshot in the window.

    Dashboard-shaped on purpose -- the ratio the ring draws, already resolved.
    `dp_1` / `dp_2` are carried through because the ring prints them as its
    "n / m" caption; nothing else from `daily_dual_data_point` is exposed.
    """

    metric_type: str = Field(examples=["smart room"])
    metric_date: date = Field(description="The snapshot this ring represents")
    dp_1: float = Field(description="Numerator as stored, e.g. rooms online")
    dp_2: float = Field(description="Denominator as stored, e.g. rooms total")
    percentage: int = Field(
        examples=[79],
        description="dp_1 / dp_2 as a whole percent; 0 when dp_2 is 0",
    )


class CaleidoAtWorkRead(BaseModel):
    """The Caleido At Work widget's whole payload: one row per metric.

    At most one row per `metric_type`, so the caller renders what it is given
    rather than selecting a record out of a page.
    """

    metrics: list[CaleidoMetricRead]


class DailyDataPointRead(ORMModel):
    """A row of `daily_dual_data_point` -- one KPI pair for one day.

    `metric_type` is the Caleido At Work KPI set: smart room, service request,
    checkout, booking, guest room.
    """

    metric_date: date
    metric_type: str = Field(examples=["smart room"])
    dp_1: Decimal = Field(description="Numerator, e.g. rooms online")
    dp_2: Decimal = Field(description="Denominator, e.g. rooms total")
    facility_id: uuid.UUID = Field(
        description="NOT part of the primary key -- the table is single-facility as built"
    )
    created_on: datetime
    updated_on: datetime
