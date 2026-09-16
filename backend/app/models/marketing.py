"""Group M - marketing, events and occasions (5 tables).

Blueprint §5, tables 86-90.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, SmallIntLookupPk, TimestampMixin, UUIDPk
from app.models.facility import attachment_fk, user_fk


class PromoCode(HMSBase, UUIDPk):
    """Discount offer. IKANOS `promo_codes`. ADAPT -- replaces Phase 1 `offer`.

    All 8 discount columns the Phase 1 `offer` table lacked are here.
    `PUT /offers/{ID}/withdraw` maps to `status`.
    `promo_codes` has no `facility_id` [FACT]; scope is via
    `promo_code_amenity` (blueprint OPEN DECISION #6).
    """

    __tablename__ = "promo_code"

    offer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    promo_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expiry_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    discount_percentage: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_discount_value: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    min_order_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    promo_code_icon: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    promo_code_description: Mapped[str | None] = mapped_column(
        String(250), nullable=True
    )
    offered_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # The "withdrawn" state.
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1", index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class PromoCodeAmenity(Base, TimestampMixin):
    """Which rooms an offer applies to. IKANOS `promo_code_amenities`. USE."""

    __tablename__ = "promo_code_amenity"

    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("promo_code.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class FacilityEvent(HMSBase, UUIDPk):
    """A hotel event. IKANOS `facility_events`. ADAPT -- replaces Phase 1 `event`.

    `venue` is a free-text string, NOT an `amenity` FK [FACT].
    """

    __tablename__ = "facility_event"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chief_guests: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_attendees: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    interested_attendees: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="0"
    )
    start_date_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    end_date_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    # Backs PUT /events/{ID}/cancel.
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class OccasionType(Base, TimestampMixin, SmallIntLookupPk):
    """IKANOS `occasion_types`. USE.

    Seeded: Festival, Birthday, Marriage anniversary, Holiday.
    """

    __tablename__ = "occasion_type"

    occasion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notification_template: Mapped[str | None] = mapped_column(Text, nullable=True)


class Occasion(HMSBase, UUIDPk):
    """A dated occasion. `occasion_type = 'Holiday'` IS the Holidays module.
    IKANOS `occasions`. USE -- replaces the Phase 1 `holiday` table.

    REVIEW (blueprint §11.5 / OPEN DECISION #5) [CONFLICT]: there is NO
    `lock_message` column [FACT], yet the HMS Holidays screen is built
    entirely around one. `notification_template` is the nearest field -- it is
    the message pushed to hubs when `notify_to_hub` is set. Mapped as [INFER];
    NOT resolved, and no `lock_message` column has been invented.
    """

    __tablename__ = "occasion"

    occasion_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occasion_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("occasion_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_repeatable: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="false"
    )
    notification_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # For personal occasions (birthday, anniversary).
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )
    # Pushes the occasion to in-room hubs.
    notify_to_hub: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="true"
    )
    occasion_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    occasion_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )
