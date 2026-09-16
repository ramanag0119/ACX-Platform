"""Response models for alerts, incidents and value alerts.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * **There is no `alert` table.** IKANOS has TWO distinct alert entities:
      - `device_alert`  -- the device event stream (BIGINT id, 9 seeded rows)
      - `value_alert`   -- a threshold breach against
                           `value_alert_limit_config` (UUID id, 3 seeded rows)
    They have different keys, different columns and different status models,
    so they are exposed as two resources rather than merged.

  * **There is no `alert_status`.** `device_alert` carries severity only.
    Alert lifecycle lives on the INCIDENT (`device_incident
    .current_incident_status` -> `incident_status`).

  * **The relationship runs incident -> alert**, via
    `device_incident.latest_alert_id -> device_alert.id`. There is no
    `incident_id` column on `device_alert`, so "the incident for an alert" is
    a REVERSE lookup returning 0..N incidents, not a single nested object.

  * `alert_severity` is a 2-value ENUM: `warning`, `critical`. `Info` does not
    exist. `alert_type` is an (id, name) lookup of 16 rows -- it carries NO
    severity of its own.

  * `value_alert.status` is a bare SMALLINT: 0 = Active, 1 = Resolved
    (NEEDS_REVIEW D8). It is not an ENUM and has no lookup table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# alert_type
# ---------------------------------------------------------------------------


class AlertTypeRead(ORMModel):
    """A row of `alert_type`. (id, name) ONLY -- severity is on the alert."""

    id: int = Field(examples=[13])
    name: str = Field(examples=["HubOffline"])
    created_on: datetime
    updated_on: datetime


class AlertTypeDetail(AlertTypeRead):
    alert_count: int = Field(description="device_alert rows of this type")
    incident_count: int = Field(description="device_incident rows of this type")


# ---------------------------------------------------------------------------
# device_alert
# ---------------------------------------------------------------------------


class AlertRead(ORMModel):
    """A row of `device_alert` -- the raw device event stream.

    Location is resolved through device -> amenity -> property_chain, the same
    path Phase 2.6 uses. There is no building/floor column on the alert.
    """

    id: int = Field(examples=[1], description="BIGINT identity, not a UUID")
    alert_type: int
    alert_type_name: str | None = Field(default=None, examples=["HubOffline"])
    alert_severity: str | None = Field(
        default=None, examples=["critical"], description="warning | critical only"
    )
    alert_data: dict | None = Field(
        default=None,
        description=(
            "The alert's own diagnostic payload written by the device "
            "(readings and thresholds). Exposed because it IS the alert's "
            "substance; it carries no credential."
        ),
    )
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = Field(default=None, examples=["Intellihub"])
    amenity_id: uuid.UUID
    amenity_name: str | None = Field(default=None, examples=["106"])
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    facility_id: uuid.UUID | None = Field(
        default=None,
        description="Resolved from the device -- `device_alert` has no facility column",
    )
    created_on: datetime
    updated_on: datetime


class AlertDetail(AlertRead):
    incidents: list["IncidentRef"] = Field(
        description=(
            "Incidents whose latest_alert_id points at this alert. A reverse "
            "lookup returning 0..N -- the alert holds no incident_id."
        )
    )
    incident_count: int


# ---------------------------------------------------------------------------
# device_incident
# ---------------------------------------------------------------------------


class IncidentRef(ORMModel):
    id: uuid.UUID
    subject: str | None = None
    current_incident_status: int | None = None
    status_name: str | None = Field(default=None, examples=["Assigned"])


class IncidentHistoryRead(ORMModel):
    """A row of `incident_history` -- the audit trail.

    This is where resolution time and notes actually live: `device_incident`
    has no `resolved_on` or `notes` column.
    """

    id: int
    incident_event_id: int
    incident_event_name: str | None = Field(default=None, examples=["Resolved"])
    incident_event_data: dict | None = Field(
        default=None, description="The transition note recorded by the actor"
    )
    created_by: UserRef | None = None
    created_on: datetime


class IncidentRead(ORMModel):
    """A row of `device_incident` -- the assignable, resolvable case."""

    id: uuid.UUID
    subject: str | None = None
    description: str | None = None
    alert_type: int
    alert_type_name: str | None = None
    current_incident_status: int | None = None
    status_name: str | None = Field(
        default=None, description="Unread | Read | Assigned | Resolved"
    )
    facility_id: uuid.UUID
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    amenity_id: uuid.UUID
    amenity_name: str | None = None
    latest_alert_id: int | None = Field(
        default=None, description="The device_alert that last fired"
    )
    latest_alert_severity: str | None = None
    assignee: UserRef | None = None
    updated_by_user: UserRef | None = None
    created_on: datetime
    updated_on: datetime


class IncidentDetail(IncidentRead):
    history: list[IncidentHistoryRead]
    history_count: int


# ---------------------------------------------------------------------------
# value_alert
# ---------------------------------------------------------------------------


class ValueAlertRead(ORMModel):
    """A row of `value_alert` -- a threshold breach on a telemetry parameter.

    A separate entity from `device_alert`: different key, different status
    model, and it resolves its parameter through `value_alert_limit_config`.
    """

    id: uuid.UUID
    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str = Field(description="Stored on the row as free text")
    device_type_id: int
    device_type_name: str | None = None
    amenity_id: uuid.UUID
    amenity_name: str | None = None
    facility_id: uuid.UUID
    limit_config_id: uuid.UUID
    parameter: str | None = Field(
        default=None,
        examples=["voltage"],
        description="From value_alert_limit_config -- not stored on the alert",
    )
    limit_type: str = Field(examples=["high"], description="Free text, not an ENUM")
    limit_value: str
    description: str
    status: int = Field(
        examples=[0], description="0 = Active, 1 = Resolved (integer, not an ENUM)"
    )
    device_status_id: int = Field(
        description="REVIEW: undocumented in IKANOS, no FK target identified"
    )
    timestamp: datetime
    created_on: datetime
    updated_on: datetime


class ValueAlertDetail(ValueAlertRead):
    nominal: int | None = None
    limit_low_value: int | None = None
    limit_high_value: int | None = None
    limit_low_percentage: int | None = None
    limit_high_percentage: int | None = None
    is_percentage_value: str | None = None
    limit_check: str | None = None
    remarks: str | None = None


AlertDetail.model_rebuild()
