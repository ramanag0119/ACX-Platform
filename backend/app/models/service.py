"""Group E - services, tickets and the service catalogue (8 tables).

Blueprint §5, tables 34-41.

The catalogue is generic, not food-specific: the Phase 1 `food_category` /
`food_menu` tables have no IKANOS counterpart.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, SmallIntLookupPk, TimestampMixin, UUIDPk
from app.models import enums
from app.models.facility import attachment_fk, user_fk


class ServiceType(Base, TimestampMixin, SmallIntLookupPk):
    """Top-level service taxonomy. IKANOS `service_types`. USE.

    The 7 seeded rows ARE the 7 Services Tracking tabs: Room Service,
    Travel Desk, Business Center, Food Order, Facility Maintenance Service,
    Health & Fitness, Sanitation Maintenance Service.
    """

    __tablename__ = "service_type"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


class ServiceStatus(Base, TimestampMixin, SmallIntLookupPk):
    """Service and maintenance lifecycle vocabulary.
    IKANOS `service_statuses`. USE.

    Seeded: Pending, Assigned, Partially completed, Completed, Canceled.
    """

    __tablename__ = "service_status"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


class ServiceCategory(HMSBase, UUIDPk):
    """Category within a service type. IKANOS `service_categories`. USE --
    replaces the Phase 1 `food_category`."""

    __tablename__ = "service_category"

    service_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("service_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_icon: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    service_category_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class ServiceCategoryItem(HMSBase, UUIDPk):
    """A purchasable / requestable item. Carries the ONLY price in the schema.
    IKANOS `service_category_items` + `service_item_metadata` (MERGE). ADAPT --
    replaces the Phase 1 `food_menu`.

    `food_code`, `is_veg`, `is_spicy` are not columns; they belong in
    `metadata` (blueprint §5 table 37).
    """

    __tablename__ = "service_category_item"

    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    item_icon: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    # MERGE: absorbed `service_item_metadata`.
    item_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_service_category_item_metadata_gin", "metadata", postgresql_using="gin"
        ),
    )


class ServiceRequest(HMSBase, UUIDPk):
    """A service ticket. Drives Services Tracking and the Tickets module.
    IKANOS `service_requests`. ADAPT.

    `assigned_to` targets `app_user`, not the deleted `employee` table.
    There is no `priority` column in IKANOS (OPEN DECISION #13).
    """

    __tablename__ = "service_request"

    service_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("service_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ref_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True, unique=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("department.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("promo_code.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # IKANOS `user_id` -- the requesting guest.
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    request_source: Mapped[str | None] = mapped_column(
        enums.request_source, nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    net_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_tax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    expected_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("service_status.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (Index("ix_service_request_created_on", "created_on"),)


class ServiceRequestItem(HMSBase, UUIDPk):
    """Line items on a ticket. IKANOS `service_request_items`. USE.

    Explains the "Partially completed" status: a ticket is partial when its
    items differ in status.
    """

    __tablename__ = "service_request_item"

    service_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_request.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category_item.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("service_status.id", ondelete="RESTRICT"),
        nullable=True,
    )


class RoomServiceRequest(HMSBase, UUIDPk):
    """Lightweight in-room service call raised from the guest app.
    IKANOS `room_service_requests`. USE.

    REVIEW (blueprint §10 #2 / OPEN DECISION #7): this may be a Porta-only
    entity. It carries its OWN 4-value status vocabulary, separate from
    `service_status`.
    """

    __tablename__ = "room_service_request"

    guest_room_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    service_request_status: Mapped[str | None] = mapped_column(
        enums.room_service_request_status, nullable=True, server_default="unassigned"
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class RoomServiceRequestItem(HMSBase, UUIDPk):
    """Items on a room service call.
    IKANOS `room_service_request_items`. ADAPT.

    REVIEW (blueprint §10 #3): IKANOS `faciliti_service_id` has NO FK target
    table anywhere in the dump. Repointed to `service_category_item` as an
    explicit [INFER] recorded in the approved blueprint.
    """

    __tablename__ = "room_service_request_item"

    room_service_request_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("room_service_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_category_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_category_item.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_processed: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="0"
    )
