"""ALERT domain models.

Sources:
  AM  = 4_ALARM_MANAGER_DOCUMENTATION.md §11 (typed field tables)
  CPA = COMPLETE_PROJECT_ANALYSIS_REPORT.md §8 "Alert Tables"
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AlertSeverity, IncidentStatus, LimitType, pg_enum


class DeviceIncident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AM §11 `deviceIncident`."""

    __tablename__ = "device_incident"
    __table_args__ = (
        Index("ix_device_incident_facility_id_created_on", "facility_id", "created_on"),
        Index("ix_device_incident_assigned_to_status", "assigned_to", "status"),
    )

    subject: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[IncidentStatus | None] = mapped_column(pg_enum(IncidentStatus))
    severity: Mapped[AlertSeverity | None] = mapped_column(pg_enum(AlertSeverity))
    # AM §11 documents `alertSeverity` ("Severity display") alongside
    # `severity`. Kept as free text — no enumerated values are documented.
    alert_severity: Mapped[str | None] = mapped_column(String(50))
    created_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    # AM §11 documents `assignedUser` as an embedded object.
    assigned_user: Mapped[dict | None] = mapped_column(JSONB)

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE")
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class ValueAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AM §11 `valueAlerts`.

    `status` is documented as an Integer (0=Active, 1=Resolved), not a string
    enum — preserved as-is rather than normalised.
    """

    __tablename__ = "value_alerts"
    __table_args__ = (
        Index("ix_value_alerts_device_id_timestamp", "device_id", "timestamp"),
        Index("ix_value_alerts_facility_id_status", "facility_id", "status"),
    )

    parameter: Mapped[str | None] = mapped_column(String(100))
    limit_type: Mapped[LimitType | None] = mapped_column(pg_enum(LimitType))
    limit_value: Mapped[float | None] = mapped_column(Numeric(18, 6))
    current_value: Mapped[float | None] = mapped_column(Numeric(18, 6))
    status: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unit: Mapped[str | None] = mapped_column(String(20))

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class LimitConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AM §11 `limitConfig`.

    CPA §20 lists "threshold config missing/duplicate" as a documented failure
    mode, which supports uniqueness on (device, parameter).
    """

    __tablename__ = "limit_config"
    __table_args__ = (UniqueConstraint("device_id", "parameter"),)

    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    high_limit: Mapped[float | None] = mapped_column(Numeric(18, 6))
    low_limit: Mapped[float | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(20))

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class AlertType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """CPA §8 `alertType`: id, name, description, severity, category, isActive.

    Not present in the per-service AM doc — only the CPA summary table.
    """

    __tablename__ = "alert_type"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[AlertSeverity | None] = mapped_column(pg_enum(AlertSeverity))
    category: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CurrentIncidentStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """CPA §8 `currentIncidentStatus`: id, name, statusCode, displayColor, isResolved."""

    __tablename__ = "current_incident_status"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status_code: Mapped[str | None] = mapped_column(String(50))
    display_color: Mapped[str | None] = mapped_column(String(30))
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
