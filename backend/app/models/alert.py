"""Group J - alerts, incidents and value limits (8 tables).

Blueprint §5, tables 67-74.

Alerts are the raw event stream; incidents are the deduplicated, assignable
case. That linkage (`device_incident.latest_alert_id`) was entirely missing
from the Phase 1 foundation.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import SmallInteger

from app.db.base import (
    Base,
    BigIntPk,
    HMSBase,
    SmallIntLookupPk,
    TimestampMixin,
    UUIDPk,
)
from app.models import enums
from app.models.facility import user_fk


class AlertType(Base, TimestampMixin, SmallIntLookupPk):
    """The alert catalogue. IKANOS `alert_types`. ADAPT -- reduced to (id, name).

    `severity`, `category`, `description` and `is_active` are REMOVED: they do
    not exist [FACT]. Severity lives on `device_alert.alert_severity`.

    16 seeded rows: BatteryLow, DeviceDisconnection, LoginAttemptsFailure,
    ImproperShaftMovement, DeviceOverheating, PreventiveMaintenance,
    MikosOvercurrentTrip, RoomAirQualityPoor, RoomInternalHot,
    AirConditioningFail, TamperingAttempt, DoorAjar, HubOffline, MikosOffline,
    LockOffline, AirqOffline.
    """

    __tablename__ = "alert_type"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


class IncidentStatus(Base, TimestampMixin, SmallIntLookupPk):
    """Current incident state. IKANOS `incident_statuses`. ADAPT -- (id, name).

    Seeded: Unread, Read, Assigned, Resolved. The Phase 1 `Open` value was
    invented; `status_code` / `display_color` / `is_resolved` do not exist.
    """

    __tablename__ = "incident_status"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


class IncidentEvent(Base, TimestampMixin, SmallIntLookupPk):
    """Vocabulary of transitions written to the incident audit trail.
    IKANOS `incident_events`. USE.

    Seeded: Unread, Read, Assigned, Resolved, Reopened. `Reopened` exists only
    as an EVENT, never as a status [FACT].
    """

    __tablename__ = "incident_event"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


class DeviceAlert(HMSBase, BigIntPk):
    """Raw alert stream from devices. IKANOS `device_alerts`. USE."""

    __tablename__ = "device_alert"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The affected room.
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("alert_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Only two values -- `Info` does not exist.
    alert_severity: Mapped[str | None] = mapped_column(
        enums.alert_severity, nullable=True
    )
    alert_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (Index("ix_device_alert_created_on", "created_on"),)


class DeviceIncident(HMSBase, UUIDPk):
    """The assignable, resolvable case raised from one or more alerts.
    IKANOS `device_incidents`. ADAPT.

    REMOVED (do not exist [FACT]): severity, alert_severity, notes,
    resolved_on, assigned_user. Severity comes from `device_alert`;
    resolution time and notes come from `incident_history`.
    """

    __tablename__ = "device_incident"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("alert_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # -> app_user, NOT the deleted `employee` table.
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True, index=True
    )
    latest_alert_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("device_alert.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    current_incident_status: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("incident_status.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (Index("ix_device_incident_created_on", "created_on"),)


class IncidentHistory(HMSBase, BigIntPk):
    """Audit trail of every incident transition. IKANOS `incident_history`. USE.

    This is where `resolved_on` and `notes` actually live -- as the `Resolved`
    event row and its `incident_event_data`.
    """

    __tablename__ = "incident_history"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device_incident.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_event_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("incident_event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class ValueAlertLimitConfig(HMSBase, UUIDPk):
    """Per-device-name, per-parameter limits. Backs the Limit Config Alert
    screen. IKANOS `value_alert_limit_config`. ADAPT.

    IKANOS keys by `device_name varchar`, not by id. That is preserved; a
    NULLABLE `device_id` is added as an explicit [INFER] so HMS can resolve to
    a real device without losing the name key.

    The Phase 1 `limit_type` enum (high/low) was wrong: one config row carries
    BOTH a low and a high limit, in BOTH percentage and absolute form.
    """

    __tablename__ = "value_alert_limit_config"

    parameter: Mapped[str] = mapped_column(String(50), nullable=False)
    device_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # [INFER] added; not present in IKANOS.
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device.id", ondelete="RESTRICT"), nullable=True
    )
    limit_check: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    is_percentage_value: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    nominal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_low_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_high_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_low_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_high_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remarks: Mapped[str] = mapped_column(Text, nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # [INFER] IKANOS declares no unique key on this table.
        UniqueConstraint(
            "device_name",
            "parameter",
            "facility_id",
            name="uq_value_alert_limit_config_device_name_parameter_facility_id",
        ),
    )


class ValueAlert(HMSBase, UUIDPk):
    """Threshold-breach alert on a telemetry parameter.
    IKANOS `value_alerts`. ADAPT.

    REMOVED: parameter, unit, current_value -- none exists [FACT].
    `parameter` is on the limit config; `unit` is on `device_param`.

    REVIEW (blueprint §10 #6): IKANOS declares NO foreign keys at all on this
    table. The six below are added as the approved [INFER].
    """

    __tablename__ = "value_alert"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_name: Mapped[str] = mapped_column(String(50), nullable=False)
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    limit_config_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("value_alert_limit_config.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # REVIEW: purpose undocumented in IKANOS; no FK target identified.
    device_status_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # `date` in IKANOS; widened to a timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    limit_value: Mapped[str] = mapped_column(String(50), nullable=False)
    # "low" or "high" -- a varchar in IKANOS, NOT an enum.
    limit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # 0 = Active, 1 = Resolved. Kept as an integer, as documented (NEEDS_REVIEW D8).
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0", index=True
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
