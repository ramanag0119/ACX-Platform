"""NOTIFICATION domain models.

Source: 5_NOTIFICATION_ENGINE_DOCUMENTATION.md §8 (typed field tables).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationType, pg_enum


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """NE §8 `notification`.

    `referenceId` is documented as "Related entity ID (alert, booking, etc.)" —
    a polymorphic pointer, so no FK is declared. See NEEDS_REVIEW.
    """

    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_user_id_is_read", "user_id", "is_read"),
        Index("ix_notification_facility_id_created_on", "facility_id", "created_on"),
    )

    title: Mapped[str | None] = mapped_column(String(300))
    message: Mapped[str | None] = mapped_column(Text)
    type: Mapped[NotificationType | None] = mapped_column(pg_enum(NotificationType))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class FcmToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """NE §8 `fcmToken`."""

    __tablename__ = "fcm_token"
    __table_args__ = (Index("ix_fcm_token_user_id", "user_id"),)

    token: Mapped[str] = mapped_column(Text, nullable=False)
    device_type: Mapped[str | None] = mapped_column(String(50))
    registered_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )
