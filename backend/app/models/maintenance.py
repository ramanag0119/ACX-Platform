"""Group F - maintenance and Services Planning (4 tables).

Blueprint §5, tables 42-45.

Replaces the Phase 1 flat `maintenance_schedule`: IKANOS splits the request,
its recurrence rule, its rooms and its assignees across four tables.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, TimestampMixin, UUIDPk
from app.models import enums
from app.models.facility import user_fk


class MaintenanceRequest(HMSBase, UUIDPk):
    """Scheduled, planned and disinfection maintenance.
    IKANOS `service_maintenance_requests`. ADAPT.

    There is no `service_type_id` column: the Phase 1
    `maintenance_schedule.service_type_id` (a UUID with no FK) has no IKANOS
    counterpart. The real link is `category_id` / `item_id`.
    `maintenance_start_time` is a real timestamp, not a VARCHAR.
    """

    __tablename__ = "maintenance_request"

    # The 3 Services Planning tabs.
    maintenance_request_type: Mapped[str] = mapped_column(
        enums.maintenance_request_type, nullable=False
    )
    maintenance_start_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, index=True
    )
    maintenance_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maintenance_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    maintenance_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_recurring: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="0"
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("department.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category_item.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    completed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_room: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    non_room_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A recurrence instance points at its template.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_request.id", ondelete="RESTRICT"),
        nullable=True,
    )
    maintenance_request_status: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("service_status.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delete_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Takes the room out of service.
    under_maintenance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Soft-delete flag, distinct from `maintenance_request_status`.
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1", index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class MaintenanceRequestRecurrence(Base, TimestampMixin):
    """Recurrence rule. 1:1, present only when the request recurs.
    IKANOS `maintenance_request_recurrence`. USE.

    Replaces the Phase 1 `maintenance_schedule.days[]` array column.
    """

    __tablename__ = "maintenance_request_recurrence"

    maintenance_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_request.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    recurrence_type: Mapped[str] = mapped_column(enums.recurrence_type, nullable=False)
    days_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_no_of_occurrences: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )


class MaintenanceRequestAmenity(HMSBase, UUIDPk):
    """Rooms covered by a maintenance request.
    IKANOS `service_maintenance_request_amenities`. USE.

    IKANOS uses a surrogate PK here, not a composite -- preserved.
    """

    __tablename__ = "maintenance_request_amenity"

    maintenance_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_request.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class MaintenanceRequestAssignee(HMSBase, UUIDPk):
    """Staff assigned to a maintenance request -- many per request.
    IKANOS `service_maintenance_request_assignees`. USE.

    This is why the Phase 1 single-valued `maintenance_schedule.assigned_to`
    was wrong: assignment is many-to-many.
    """

    __tablename__ = "maintenance_request_assignee"

    maintenance_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_request.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
