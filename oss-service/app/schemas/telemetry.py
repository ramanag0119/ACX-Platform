"""Response models for device telemetry: parameters, readings and snapshots.

Copied verbatim from the HMS backend (`backend/app/schemas/telemetry.py`).
Keep in sync with HMS.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DeviceParamRead(ORMModel):
    id: int = Field(examples=[5], description="Derived ordinal over DISTINCT param_data keys")
    param_name: str = Field(examples=["voltage"])
    # WIDENED FOR OSS: derived params are not tied to a device-type registry.
    device_type: int | None = None
    device_type_name: str | None = Field(default=None, examples=["Mikos"])
    device_short_code: str | None = Field(default=None, examples=["MIK"])
    data_type: str | None = Field(
        default=None, examples=["Double"],
        description="Inferred from the JSON value (Integer | Double | String)",
    )
    unit: str | None = Field(
        default=None, examples=["V"],
        description="OSS param_data carries no unit -> null.",
    )
    # WIDENED FOR OSS: derived registry has no timestamps.
    created_on: datetime | None = None
    updated_on: datetime | None = None


class DeviceParamDetail(DeviceParamRead):
    reading_count: int = Field(description="device_stat rows for this parameter")


class DeviceStatRead(ORMModel):
    id: int = Field(description="BIGINT identity")
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = None
    amenity_id: uuid.UUID | None = Field(
        default=None, description="Resolved from the device; device_stat has no room column"
    )
    amenity_name: str | None = None
    facility_id: uuid.UUID | None = Field(
        default=None, description="Resolved from the device"
    )
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    device_param_id: int
    param_name: str | None = Field(default=None, examples=["active_energy"])
    data_type: str | None = Field(default=None, examples=["Double"])
    unit: str | None = Field(default=None, examples=["kWh"])
    device_param_value: str | None = Field(
        default=None,
        examples=["37.140"],
        description=(
            "Returned as stored. The column is VARCHAR(500); interpret it "
            "using `data_type`. No server-side numeric conversion is applied."
        ),
    )
    timestamp: datetime = Field(description="When the device took the reading")
    is_other_device: int | None = None
    created_on: datetime


class DeviceCurrentStatRead(ORMModel):
    id: uuid.UUID
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = None
    amenity_id: uuid.UUID | None = None
    amenity_name: str | None = None
    facility_id: uuid.UUID | None = None
    device_stats: dict | None = Field(
        default=None, description="Latest-value payload written by the device"
    )
    is_other_device: int | None = None
    created_on: datetime
    updated_on: datetime


class OtherDeviceReadingRead(ORMModel):
    id: int = Field(description="BIGINT identity")
    msg_id: str | None = None
    device_name: str | None = Field(
        default=None, examples=["MAINS-EB-01"], description="Free text; no FK exists"
    )
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    power_factor: float | None = None
    all_energy: float | None = None
    thirty_day_energy: float | None = None
    today_energy: float | None = None
    current_hour_energy: float | None = None
    ec: float | None = Field(
        default=None, description="REVIEW: undocumented in IKANOS; returned as stored"
    )
    timestamp: datetime
    created_on: datetime
