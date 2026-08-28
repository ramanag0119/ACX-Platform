"""Response models for device telemetry: parameters, readings and snapshots.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * **There is no `telemetry` table.** IKANOS stores telemetry as a generic
    EAV pair:
        `device_param`  -- the parameter registry (35 rows: name, data_type, unit)
        `device_stat`   -- one row per parameter per reading (504 rows)
    Phase 2.6 deliberately left both out of scope; this phase delivers them.

  * **`device_stat.device_param_value` is VARCHAR(500)** -- every reading is
    stored as TEXT, not as a number. `device_param.data_type` says how to
    interpret it (Integer | Double | String | Date Time). Values are therefore
    returned as strings, exactly as stored. No numeric aggregation is offered
    over this table, because the column cannot support one safely.

  * **`device_param.param_name` is NOT unique.** The same name appears under
    several device types, and `relay_status` appears FOUR times for Intellihub
    (ids 30-33) with different data types and units. See the note on
    `DeviceParamRead`.

  * `device_current_stat` holds one JSONB snapshot per device -- the latest
    values, so a dashboard tile need not scan `device_stat`.

  * `other_device` is the third-party meter feed. Unlike `device_stat` its
    measurements ARE real numeric columns, but it has NO foreign keys at all,
    so it cannot be joined to a device, amenity or facility.

NEVER EXPOSED: `device.authentication_code`, `device.metadata`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# device_param -- the parameter registry
# ---------------------------------------------------------------------------


class DeviceParamRead(ORMModel):
    """A row of `device_param`.

    DATA-QUALITY NOTE, reported not corrected: for Intellihub the schema holds
    four rows named `relay_status` (ids 30, 31, 32, 33) carrying units
    `(none)`, `kvarh`, `kvar` and `kVA`. Ids 31-33 look like mislabelled
    reactive/apparent power rows -- Mikos has correctly-named equivalents at
    ids 20, 23, 24. The names are returned exactly as stored; renaming them
    would be a schema change.
    """

    id: int = Field(examples=[5])
    param_name: str = Field(examples=["voltage"])
    device_type: int
    device_type_name: str | None = Field(default=None, examples=["Mikos"])
    device_short_code: str | None = Field(default=None, examples=["MIK"])
    data_type: str | None = Field(
        default=None, examples=["Double"],
        description="Integer | Double | String | Date Time -- how to read the value",
    )
    unit: str | None = Field(
        default=None, examples=["V"],
        description="As stored. NULL where IKANOS records no unit.",
    )
    created_on: datetime
    updated_on: datetime


class DeviceParamDetail(DeviceParamRead):
    reading_count: int = Field(description="device_stat rows for this parameter")


# ---------------------------------------------------------------------------
# device_stat -- the readings
# ---------------------------------------------------------------------------


class DeviceStatRead(ORMModel):
    """A row of `device_stat` -- one parameter reading at one instant."""

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


# ---------------------------------------------------------------------------
# device_current_stat -- latest snapshot
# ---------------------------------------------------------------------------


class DeviceCurrentStatRead(ORMModel):
    """A row of `device_current_stat` -- the latest values as one JSON blob.

    `device_stats` is the device's own telemetry payload, which is the entire
    purpose of the row, so it is returned. It carries readings, not
    credentials -- unlike `device.metadata`, which stays excluded.
    """

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


# ---------------------------------------------------------------------------
# other_device -- third-party meters
# ---------------------------------------------------------------------------


class OtherDeviceReadingRead(ORMModel):
    """A row of `other_device` -- a third-party (non-Caleido) meter reading.

    This table has NO foreign keys, so `device_name` is free text and the
    reading cannot be joined to a device, room or facility. Its measurements,
    however, ARE real numeric columns -- unlike `device_stat`.
    """

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
