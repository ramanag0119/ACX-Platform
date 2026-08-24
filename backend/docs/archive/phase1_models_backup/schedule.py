"""SCHEDULE domain models.

Source: 7_SCHEDULE_HANDLER_DOCUMENTATION.md §10 (typed field tables).
"""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ScheduledTaskStatus, ScheduledTaskType, pg_enum


class MaintenanceSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SH §10 `maintenanceSchedule`.

    `days` is documented as an array of MON-SUN, stored as a PostgreSQL text
    array (scalar values — no FK needed).

    `serviceTypeId` references a maintenance service type. FM §9 documents a
    /maintenance/service-types CRUD API but no field table for that entity,
    so the column is kept without an FK. See NEEDS_REVIEW.
    """

    __tablename__ = "maintenance_schedule"
    __table_args__ = (
        Index(
            "ix_maintenance_schedule_facility_id_is_active",
            "facility_id",
            "is_active",
        ),
    )

    days: Mapped[list[str] | None] = mapped_column(ARRAY(String(3)))
    start_time: Mapped[str | None] = mapped_column(String(20))
    from_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    to_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    service_type_id: Mapped[uuid.UUID | None] = mapped_column()
    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="CASCADE")
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("department.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class ScheduledTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SH §10 `scheduledTask`.

    `targetEntity` is documented as "Related entity (room, stay, etc.)" —
    polymorphic, so no FK is declared. See NEEDS_REVIEW.
    """

    __tablename__ = "scheduled_task"
    __table_args__ = (
        Index(
            "ix_scheduled_task_facility_id_scheduled_at_status",
            "facility_id",
            "scheduled_at",
            "status",
        ),
    )

    type: Mapped[ScheduledTaskType | None] = mapped_column(pg_enum(ScheduledTaskType))
    target_entity: Mapped[uuid.UUID | None] = mapped_column()
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ScheduledTaskStatus | None] = mapped_column(pg_enum(ScheduledTaskStatus))
    last_executed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recur_pattern: Mapped[str | None] = mapped_column(String(200))

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )
