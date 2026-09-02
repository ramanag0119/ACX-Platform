"""Response models for device inventory, device types, firmware and health.

Every field maps to a real column or is an explicitly-named value derived from
a real foreign key.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * `device_type` is a 4-row lookup: Intellihub(HUB), AirQ(AIR), Mikos(MIK),
    Kleio(KLE). **There is no `device_model` table** -- `device.model` is a
    plain VARCHAR(20), so type and model are genuinely different things and
    both are preserved.
  * **There is no `device_status` table.** Status is carried by ENUM and
    boolean columns on `device` itself -- see `DeviceRead`.
  * **There is no `serial_number` column.** The unique device identifier is
    `device_uid`; `part_number` is a separate, non-unique manufacturer field.
  * **Device location is `facility_id` + `amenity_id` only.** There is no
    property/building/floor column on `device`. Building and floor are resolved
    through amenity -> property_chain, exactly as Phase 2.2 established.
  * **There is no `last_seen` column** (the blueprint removed it as
    undocumented). `last_reported_on` in the health response is DERIVED as
    MAX(device_health_stat.created_on) and is labelled as such.

NEVER EXPOSED: `device.authentication_code` (a device credential) and
`device.metadata` (an unbounded bag that may hold anything).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# device_type
# ---------------------------------------------------------------------------


class DeviceTypeRead(ORMModel):
    """A row of `device_type`. Four families, seeded from IKANOS."""

    id: int = Field(examples=[1])
    name: str | None = Field(default=None, examples=["Intellihub"])
    device_short_code: str | None = Field(
        default=None, examples=["HUB"], description="HUB | AIR | MIK | KLE"
    )
    created_on: datetime
    updated_on: datetime


class DeviceTypeDetail(DeviceTypeRead):
    device_count: int = Field(description="Devices of this type")
    firmware_count: int = Field(description="Firmware releases for this type")


# ---------------------------------------------------------------------------
# firmware
# ---------------------------------------------------------------------------


class FirmwareRead(ORMModel):
    """A row of `firmware`.

    There is no `is_latest` column: currency is determined by comparing
    `device.current_firmware_version` with `device.expected_firmware_version`.
    """

    id: uuid.UUID
    firmware_version: str = Field(examples=["2.4.1"])
    device_type_id: int
    device_type_name: str | None = Field(default=None, examples=["Intellihub"])
    firmware_filename: str
    firmware_url: str
    firmware_size: Decimal | None = None
    crc: str
    release_date: datetime | None = None
    release_notes: str | None = None
    decommission_reason: str | None = None
    status: str = Field(examples=["active"], description="active | decommissioned")
    created_on: datetime
    updated_on: datetime


class FirmwareDetail(FirmwareRead):
    devices_running: int = Field(
        description="Devices whose current_firmware_version is this release"
    )
    devices_expecting: int = Field(
        description="Devices whose expected_firmware_version is this release"
    )


# ---------------------------------------------------------------------------
# device
# ---------------------------------------------------------------------------


class DeviceRef(ORMModel):
    """A minimal device reference, used for parent/child links."""

    id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type: int
    device_type_name: str | None = None


class DeviceRead(ORMModel):
    """A row of `device`.

    STATUS REPRESENTATION -- four independent columns, not one status field:

      `health_status`        ENUM  Active | Inactive        (the only
                                   connectivity signal in the schema)
      `device_config_status` ENUM  configured | bad_configuration |
                                   commissioned | decommissioned |
                                   under_maintenance | missing
      `is_power_off`         BOOL
      `status`               SMALLINT soft-delete flag, semantics undocumented
    """

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
    mfg_date: datetime
    installed_on: datetime | None = None

    device_type: int
    device_type_name: str | None = Field(default=None, examples=["Intellihub"])
    device_short_code: str | None = Field(default=None, examples=["HUB"])

    # Location -- only these two are columns on `device`.
    facility_id: uuid.UUID
    amenity_id: uuid.UUID
    amenity_name: str | None = Field(default=None, examples=["101"])
    # Resolved through amenity -> property_chain (Phase 2.2 projection).
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


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


class DeviceHealthSample(ORMModel):
    """A row of `device_health_stat`. Health only -- not telemetry."""

    id: int
    device_health_status: str = Field(examples=["Active"])
    device_temperature: Decimal
    created_on: datetime


class BatteryCycle(ORMModel):
    """A row of `battery_life_stat`. Seeded for Kleio locks only."""

    cycle_number: int
    initial_battery_percentage: Decimal | None = None
    latest_battery_percentage: Decimal | None = None
    battery_life: Decimal | None = None
    created_on: datetime


class OperationSample(ORMModel):
    """A row of `sensor_operation_stat`: one operational percentage per day."""

    stats_date: date
    operation_percentage: Decimal


class DeviceHealthRead(BaseModel):
    """Everything the schema actually knows about one device's health.

    Assembled from `device` (current state), `device_health_stat` (history),
    `battery_life_stat` (battery) and `sensor_operation_stat` (daily operating
    percentage). No telemetry table is read.
    """

    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = None

    # Current state, straight off the `device` row.
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
