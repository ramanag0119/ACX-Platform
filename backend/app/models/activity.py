"""Group K - activity feed and notification dispatch (9 tables).

Blueprint §5, tables 75-83.

IKANOS separates two concerns the Phase 1 `notification` table conflated:

  (a) the in-app feed  -- activity -> activity_notifier, per-user read state
  (b) the dispatch queue -- notification -> notification_receiver ->
      notification_result, one row per channel per recipient

The Header bell reads (a). Email / SMS / push delivery is (b).
`activity.activity_response_ids` links a feed item to the dispatch rows it
produced.
"""

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

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


class EntityType(Base, TimestampMixin, SmallIntLookupPk):
    """IKANOS `entity_types`. USE.

    Seeded: Booking, Occupancy, Service Requests, Maintenance Requests,
    Default Key. This is the REAL notification-type axis; the Phase 1
    `notification_type` enum (alert/service/booking/system/event) was invented.
    """

    __tablename__ = "entity_type"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)


class ActivityType(Base, TimestampMixin, SmallIntLookupPk):
    """In-app activity taxonomy. IKANOS `activity_types`. USE."""

    __tablename__ = "activity_type"

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("entity_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    is_subscribable: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="true"
    )


class Activity(HMSBase, BigIntPk):
    """One business event worth telling someone about.
    IKANOS `activities` + `activity_data` (MERGE). ADAPT."""

    __tablename__ = "activity"

    activity_type_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("activity_type.id", ondelete="CASCADE"), nullable=False
    )
    entity_type_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("entity_type.id", ondelete="CASCADE"), nullable=False
    )
    # Polymorphic -- points at a booking, a room, a ticket. No FK is possible,
    # by design (confirms NEEDS_REVIEW D9).
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Who caused it.
    actor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stay.id", ondelete="CASCADE"), nullable=True
    )
    # Comma-separated dispatch notification ids.
    activity_response_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    # MERGE: absorbed `activity_data` (1:1 on the PK).
    data_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_activity_entity_type_id_entity_id", "entity_type_id", "entity_id"),
        Index("ix_activity_created_on", "created_on"),
    )


class ActivityNotifier(Base, TimestampMixin):
    """Per-user delivery of a feed item, with read state.
    THIS IS THE HEADER NOTIFICATION LIST. IKANOS `activity_notifiers`. USE."""

    __tablename__ = "activity_notifier"

    activity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("activity.id", ondelete="CASCADE"), primary_key=True
    )
    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        user_fk(ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    # enum('0','1','2') in IKANOS: 0 unread / 1 read / 2 clear.
    status: Mapped[str] = mapped_column(
        enums.activity_notifier_status, nullable=False, index=True
    )
    # Selects the message template. Label meanings are undocumented -> REVIEW.
    user_type: Mapped[str | None] = mapped_column(
        enums.activity_notifier_user_type, nullable=True, index=True
    )
    notification_type: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, index=True
    )


class ActivityRoleAssociation(Base, TimestampMixin):
    """Which roles are notified of which activity type.
    IKANOS `activity_role_association`. USE."""

    __tablename__ = "activity_role_association"

    activity_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("activity_type.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("role.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )


class NotificationTemplate(HMSBase, UUIDPk):
    """Message template per channel. IKANOS `templates`. ADAPT (renamed)."""

    __tablename__ = "notification_template"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(enums.notification_channel, nullable=False)
    path: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        # [INFER] IKANOS declares no unique key on this table.
        UniqueConstraint("name", "type", name="uq_notification_template_name_type"),
    )


class Notification(HMSBase, BigIntPk):
    """Dispatch queue entry -- one outbound message to render and send.
    IKANOS `notifications` + `notification_params` (MERGE). ADAPT."""

    __tablename__ = "notification"

    # A SERVICE NAME STRING in IKANOS, not a user FK [FACT].
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        enums.notification_status, nullable=False, index=True
    )
    # The originating activity.id.
    reference_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("notification_template.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # MERGE: absorbed `notification_params`.
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class NotificationReceiver(HMSBase, BigIntPk):
    """One recipient of one notification, with contact snapshot.
    IKANOS `notification_receivers`. USE.

    IKANOS has no created_on/updated_on here; they are added per §5.0.
    """

    __tablename__ = "notification_receiver"

    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True, index=True
    )
    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("notification.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    device_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class NotificationResult(HMSBase, BigIntPk):
    """Delivery outcome per recipient per channel.
    IKANOS `notification_results`. USE.

    [INFER] IKANOS declares no FK on `receiver_id`; one is added.
    IKANOS has no updated_on here (append-only); it is added per §5.0.
    """

    __tablename__ = "notification_result"

    receiver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("notification_receiver.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        enums.notification_channel, nullable=False, index=True
    )
    # Provider status string.
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_notification_result_created_on", "created_on"),)
