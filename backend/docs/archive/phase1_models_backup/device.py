"""DEVICE domain models.

Source: 2_DEVICE_MANAGER_DOCUMENTATION.md §10 "Database Tables" — fully
typed field tables, so these entities are the best-documented in the model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    pg_enum,
    DeviceConfigStatus,
    DeviceStatus,
    DeviceType,
    JobOrderStatus,
    JobOrderType,
)


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DM §10 `device` — name is documented as unique."""

    __tablename__ = "device"
    __table_args__ = (
        UniqueConstraint("facility_id", "name"),
        Index("ix_device_facility_id_status", "facility_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[DeviceType | None] = mapped_column(pg_enum(DeviceType))
    device_config_status: Mapped[DeviceConfigStatus | None] = mapped_column(pg_enum(DeviceConfigStatus))
    firmware_version: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[DeviceStatus | None] = mapped_column(pg_enum(DeviceStatus))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    mac_address: Mapped[str | None] = mapped_column(String(64))

    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="SET NULL")
    )
    # Self-referential: a device may hang off a parent HUB device.
    hub_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    hub: Mapped["Device | None"] = relationship(remote_side="Device.id")


class Firmware(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DM §10 `firmware` — version documented as unique per device type."""

    __tablename__ = "firmware"
    __table_args__ = (UniqueConstraint("facility_id", "device_type", "version"),)

    version: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    is_latest: Mapped[bool] = mapped_column(default=False, nullable=False)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class JobOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DM §10 `jobOrder`."""

    __tablename__ = "job_order"
    __table_args__ = (Index("ix_job_order_facility_id_status", "facility_id", "status"),)

    job_type: Mapped[JobOrderType | None] = mapped_column(pg_enum(JobOrderType))
    status: Mapped[JobOrderStatus | None] = mapped_column(pg_enum(JobOrderStatus))

    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    devices: Mapped[list[Device]] = relationship(secondary="job_order_device")


class JobOrderDevice(Base):
    """Junction for the documented `jobOrder.devices` array (DM §10).

    Technically required: the documented field is an array of devices, which
    cannot be a plain column without losing referential integrity.
    """

    __tablename__ = "job_order_device"

    job_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_order.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), primary_key=True
    )
