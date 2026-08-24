"""Group I - access control and digital keys (4 tables).

Blueprint §5, tables 63-66.

This is the Default Key Settings module, which had zero database support in
the Phase 1 foundation.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String
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


class KeyType(Base, TimestampMixin, SmallIntLookupPk):
    """Key classification. IKANOS `key_types`. USE.

    Seeded: Primary, Shared, Staff, Default. The `Default` row is what the
    Default Key Settings module and `facility.default_key_user` refer to.
    """

    __tablename__ = "key_type"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


class AccessKey(HMSBase, UUIDPk):
    """An issued digital key -- app key and keypad key.
    IKANOS `keys`. ADAPT (renamed: `keys`/`key` is ambiguous in PostgreSQL)."""

    __tablename__ = "access_key"

    user_device_acl_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_device_acl.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    app_key: Mapped[str] = mapped_column(String(10), nullable=False)
    keypad_key: Mapped[str] = mapped_column(String(10), nullable=False)
    key_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("key_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stay.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Staff key issued for maintenance access.
    maintenance_request_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("maintenance_request.id", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class UserDeviceAcl(HMSBase, UUIDPk):
    """Time-boxed grant of a user's access to a device in a room.
    IKANOS `user_device_acl`. USE.

    `end_time` is the mechanism behind automatic key expiry at checkout.
    """

    __tablename__ = "user_device_acl"

    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    device_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amenity_type_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
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
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )


class LockActivityLog(HMSBase, BigIntPk):
    """Every lock and unlock event. IKANOS `lock_activity_log`. USE.

    Feeds the Kleio "Lock Status" reading.
    """

    __tablename__ = "lock_activity_log"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True, index=True
    )
    event: Mapped[str | None] = mapped_column(enums.lock_event, nullable=True)
    unlock_mode: Mapped[str | None] = mapped_column(
        enums.lock_unlock_mode, nullable=True
    )
    lock_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stay.id", ondelete="CASCADE"), nullable=True
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_type: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("key_type.id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_lock_activity_log_lock_id_timestamp", "lock_id", "timestamp"),
    )
