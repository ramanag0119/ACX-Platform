"""Response models for device inventory, device types, firmware and health.

Copied verbatim from the HMS backend (`backend/app/schemas/device.py`) so the
OSS service emits the identical device contract. Keep in sync with HMS.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DeviceTypeRead(ORMModel):
    id: int = Field(examples=[1], description="Derived stable ordinal (OSS has no type table)")
    name: str | None = Field(default=None, examples=["IntelliHub"])
    device_short_code: str | None = Field(
        default=None, examples=["HUB"], description="HUB | AIR | MIK | KLE (mapped from name)"
    )
    # WIDENED FOR OSS: the registry is derived from DISTINCT device_type text,
    # which carries no timestamps -> nullable.
    created_on: datetime | None = None
    updated_on: datetime | None = None


class DeviceTypeDetail(DeviceTypeRead):
    device_count: int = Field(description="Devices of this type")
    firmware_count: int = Field(description="Firmware releases for this type")


class DeviceRef(ORMModel):
    id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    # Widened to Optional for OSS: device type is a derived ordinal over the
    # free-text `insp_device.device_type`; null when the device has no type.
    device_type: int | None = None
    device_type_name: str | None = None


class DeviceRead(ORMModel):
    id: uuid.UUID
    device_uid: str | None = Field(
        default=None, examples=["DEV101HUB"], description="Unique; there is no serial_number"
    )
    device_name: str | None = Field(default=None, examples=["101HUB"])
    appliance_name: str | None = Field(default=None, examples=["Room Controller"])
    part_number: str | None = None
    model: str | None = Field(
        default=None, examples=["MDL-1"], description="Free text -- no device_model table"
    )
    manufacturer_name: str | None = Field(default=None, examples=["Caleido"])
    # WIDENED FOR OSS (documented compatibility decision): OSS has no
    # manufacture date, so this is nullable when served from OSS.
    mfg_date: datetime | None = None
    installed_on: datetime | None = None

    # WIDENED FOR OSS: OSS has no device-type table; `device_type` is a derived
    # ordinal over the free-text `insp_device.device_type`, null if absent.
    device_type: int | None = None
    device_type_name: str | None = Field(default=None, examples=["IntelliHub"])
    device_short_code: str | None = Field(default=None, examples=["HUB"])

    # WIDENED FOR OSS: OSS is site/customer-scoped and has no room/amenity. Both
    # are nullable when served from OSS (facility_id <- site_id when present;
    # amenity_id has no OSS source). See docs/DESIGN_AND_READINESS.md.
    facility_id: uuid.UUID | None = None
    amenity_id: uuid.UUID | None = None
    amenity_name: str | None = Field(default=None, examples=["101"])
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None

    parent_device_id: uuid.UUID | None = Field(
        default=None, description="Sensors carry their hub id here"
    )

    health_status: str | None = Field(default=None, examples=["Active"])
    device_config_status: str | None = Field(default=None, examples=["commissioned"])
    device_temperature: Decimal | None = Field(
        default=None, description="Latest internal temperature of the device"
    )
    is_power_off: bool | None = None
    operational_mode: int | None = Field(
        default=None, description="Hubless-architecture flag"
    )
    is_other_device: int | None = Field(default=None, description="1 = third-party")
    status: int | None = Field(default=None, description="Soft-delete flag")

    current_firmware_version: uuid.UUID | None = None
    current_firmware: str | None = Field(default=None, examples=["2.4.1"])
    expected_firmware_version: uuid.UUID | None = None
    expected_firmware: str | None = Field(default=None, examples=["2.5.0"])
    firmware_up_to_date: bool | None = Field(
        default=None,
        description=(
            "Derived: current_firmware_version == expected_firmware_version. "
            "There is no `is_latest` column in the schema."
        ),
    )

    created_on: datetime
    updated_on: datetime


class DeviceDetail(DeviceRead):
    parent_device: DeviceRef | None = None
    child_devices: list[DeviceRef]
    child_count: int


class DeviceHealthSample(ORMModel):
    id: int = Field(description="Derived ordinal within the sample set (OSS PK is a UUID)")
    # WIDENED FOR OSS: health_status/temperature are nullable in insp_device_health.
    device_health_status: str | None = Field(default=None, examples=["Active"])
    device_temperature: Decimal | None = None
    created_on: datetime


class BatteryCycle(ORMModel):
    cycle_number: int
    initial_battery_percentage: Decimal | None = None
    latest_battery_percentage: Decimal | None = None
    battery_life: Decimal | None = None
    created_on: datetime


class OperationSample(ORMModel):
    stats_date: date
    operation_percentage: Decimal


class DeviceHealthRead(BaseModel):
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = None

    health_status: str | None = Field(
        default=None,
        description="Active | Inactive -- the only connectivity signal that exists",
    )
    device_config_status: str | None = None
    device_temperature: Decimal | None = None
    is_power_off: bool | None = None
    operational_mode: int | None = None

    last_reported_on: datetime | None = Field(
        default=None,
        description=(
            "DERIVED: MAX(device_health_stat.created_on). There is no "
            "`last_seen` column in the schema."
        ),
    )
    health_sample_count: int

    recent_samples: list[DeviceHealthSample]
    battery_cycles: list[BatteryCycle] = Field(
        default_factory=list, description="Empty for device types without a battery"
    )
    operation_history: list[OperationSample] = Field(default_factory=list)
