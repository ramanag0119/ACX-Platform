"""Response models for energy statistics.

Copied from the HMS backend (`backend/app/schemas/energy.py`). The OSS service
serves only the device-derived energy surface (`EnergyStatRead`,
`EnergySummaryRead`); the `daily_dual_data_point` / Caleido-At-Work shapes are
retained here for contract fidelity but their endpoint stays in HMS/BSS.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EnergyStatRead(ORMModel):
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


class CaleidoMetricRead(BaseModel):
    metric_type: str = Field(examples=["smart room"])
    metric_date: date = Field(description="The snapshot this ring represents")
    dp_1: float = Field(description="Numerator as stored, e.g. rooms online")
    dp_2: float = Field(description="Denominator as stored, e.g. rooms total")
    percentage: int = Field(
        examples=[79],
        description="dp_1 / dp_2 as a whole percent; 0 when dp_2 is 0",
    )


class CaleidoAtWorkRead(BaseModel):
    metrics: list[CaleidoMetricRead]


class DailyDataPointRead(ORMModel):
    metric_date: date
    metric_type: str = Field(examples=["smart room"])
    dp_1: Decimal = Field(description="Numerator, e.g. rooms online")
    dp_2: Decimal = Field(description="Denominator, e.g. rooms total")
    facility_id: uuid.UUID = Field(
        description="NOT part of the primary key -- the table is single-facility as built"
    )
    created_on: datetime
    updated_on: datetime
