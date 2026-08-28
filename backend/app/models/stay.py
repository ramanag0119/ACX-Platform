"""Group C - guests, stays and billing (7 tables).

Blueprint §5, tables 18-24.

`stay` is THE reservation. There is no `booking` table in IKANOS: booking,
check-in, check-out and cancellation are all states of one `stay` row.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import HMSBase, UUIDPk
from app.models import enums
from app.models.facility import attachment_fk, user_fk


class Stay(HMSBase, UUIDPk):
    """The reservation. IKANOS `stays`. ADAPT -- absorbs the Phase 1 `booking`.

    `stays` has no `facility_id` column in the dump. Facility scope is reached
    through room_allocation -> amenity -> facility (blueprint OPEN DECISION #6).
    """

    __tablename__ = "stay"

    internal_stay_ref_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    external_stay_ref_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    booking_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False, index=True
    )
    no_of_rooms: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="0"
    )
    no_of_guests: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    expected_checkin_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    expected_checkout_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actual_checkin_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_checkout_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    gst: Mapped[str | None] = mapped_column(String(20), nullable=True)
    checkout_initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    document_approval_status: Mapped[str] = mapped_column(
        enums.document_approval_status, nullable=False, server_default="pending"
    )
    status: Mapped[str | None] = mapped_column(
        enums.stay_status, nullable=True, server_default="pending", index=True
    )
    request_source: Mapped[str | None] = mapped_column(
        enums.request_source, nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
    # IKANOS column name `modified_by` is kept verbatim (it is not `updated_by`).
    modified_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class StayUser(HMSBase, UUIDPk):
    """Occupants of a stay, and which room each occupies.
    IKANOS `stay_users`. USE -- replaces the Phase 1 `occupant` table."""

    __tablename__ = "stay_user"

    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    stay_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_key_required: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class StayPackage(HMSBase, UUIDPk):
    """Package(s) purchased on a stay. IKANOS `stay_packages`. USE."""

    __tablename__ = "stay_package"

    stay_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )


class RoomAllocation(HMSBase, UUIDPk):
    """Which room(s) a stay is allocated, at which package. Re-allocation
    writes a new row. IKANOS `room_allocations`. USE."""

    __tablename__ = "room_allocation"

    stay_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class UserDocument(HMSBase, UUIDPk):
    """Guest ID proof and its approval state. IKANOS `user_documents`. USE.

    Document TYPE and NUMBER are not columns in IKANOS and are not added
    (blueprint OPEN DECISION #11).
    """

    __tablename__ = "user_document"

    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="CASCADE"), nullable=False
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # 3 values here vs 2 on stay.document_approval_status -- both verbatim [FACT].
    document_approval_status: Mapped[str | None] = mapped_column(
        enums.user_document_approval_status, nullable=True
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )


class Invoice(HMSBase, UUIDPk):
    """Stay invoice with a point-in-time billing and facility snapshot.
    IKANOS `invoices`. ADAPT.

    There is no `status` column in `invoices` [FACT]; the Phase 1
    `invoice.status` was documentation-derived. Payment state has no source
    -> blueprint §11.10 / OPEN DECISION #10.
    """

    __tablename__ = "invoice"

    invoice_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    invoice_due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    billing_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
    billing_user_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    facility_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facility_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    facility_image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    stay_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    net_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_tax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class ImportJob(HMSBase, UUIDPk):
    """Bulk CSV upload tracking for bookings and job orders.
    IKANOS `imports`. ADAPT (renamed)."""

    __tablename__ = "import_job"

    import_job_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_type: Mapped[str] = mapped_column(enums.import_entity_type, nullable=False)
    import_status: Mapped[str] = mapped_column(
        enums.import_status, nullable=False, server_default="queued", index=True
    )
    total_records: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    import_file_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_file_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
