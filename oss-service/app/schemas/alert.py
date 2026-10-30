"""Response models for alerts, incidents and value alerts.

Copied verbatim from the HMS backend (`backend/app/schemas/alert.py`). Keep in
sync with HMS.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AlertTypeRead(ORMModel):
    id: int = Field(examples=[13], description="Stored alert_type code (OSS has no type table)")
    name: str = Field(examples=["HubOffline"], description="As stored; OSS has no type-name lookup")
    # WIDENED FOR OSS: derived from DISTINCT alert_type codes, no timestamps.
    created_on: datetime | None = None
    updated_on: datetime | None = None


class AlertTypeDetail(AlertTypeRead):
    alert_count: int = Field(description="device_alert rows of this type")
    # WIDENED FOR OSS: incidents are unsupported, so this is null (unknown),
    # never a fabricated 0.
    incident_count: int | None = Field(
        default=None, description="null = unknown (no device_incident table in OSS)"
    )


class AlertRead(ORMModel):
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
    # WIDENED FOR OSS: insp_device_alert.device_id is NULL (alerts link by
    # device_uid); the real device_id is resolved from the device when possible,
    # else null.
    device_id: uuid.UUID | None = None
    device_uid: str | None = None
    device_name: str | None = None
    device_type_name: str | None = Field(default=None, examples=["Intellihub"])
    # WIDENED FOR OSS: no room/amenity concept in OSS.
    amenity_id: uuid.UUID | None = None
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


class IncidentRef(ORMModel):
    id: uuid.UUID
    subject: str | None = None
    current_incident_status: int | None = None
    status_name: str | None = Field(default=None, examples=["Assigned"])


class IncidentHistoryRead(ORMModel):
    id: int
    incident_event_id: int
    incident_event_name: str | None = Field(default=None, examples=["Resolved"])
    incident_event_data: dict | None = Field(
        default=None, description="The transition note recorded by the actor"
    )
    created_by: UserRef | None = None
    created_on: datetime


class IncidentRead(ORMModel):
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


class ValueAlertRead(ORMModel):
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
