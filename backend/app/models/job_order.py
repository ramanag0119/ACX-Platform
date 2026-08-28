"""Group H - job orders (3 tables).

Blueprint §5, tables 60-62.

IKANOS `caleido.jobs` is renamed `job_order` to resolve the collision with
`caleido_scheduler.jobs`, which becomes `scheduler_job`.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, TimestampMixin, UUIDPk
from app.models import enums
from app.models.facility import user_fk


class JobOrder(HMSBase, UUIDPk):
    """Field work order. IKANOS `caleido.jobs`. ADAPT.

    `jobs` has no `facility_id` [FACT] -- scope is reached via
    `job_order_amenity -> amenity` (blueprint OPEN DECISION #6).
    """

    __tablename__ = "job_order"

    order_reference: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type_of_work: Mapped[str] = mapped_column(
        enums.job_order_type_of_work, nullable=False
    )
    work_commence: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    estimated_completion_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Technician on-site code.
    authentication_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # [FACT] jobs.assigned_to -> users.user_id, NOT an employee table.
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True, index=True
    )
    job_order_status: Mapped[str] = mapped_column(
        enums.job_order_status, nullable=False, server_default="pending", index=True
    )
    completed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class JobOrderDevice(Base, TimestampMixin):
    """Devices covered by a job order. IKANOS `job_devices`. USE.

    The only Phase 1 table that was already structurally correct.
    """

    __tablename__ = "job_order_device"

    job_order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_order.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )


class JobOrderAmenity(Base, TimestampMixin):
    """Rooms covered by a job order. IKANOS `job_amenities`. USE."""

    __tablename__ = "job_order_amenity"

    job_order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_order.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
