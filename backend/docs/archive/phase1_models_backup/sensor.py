"""SENSOR / HEALTH domain models.

Sources:
  SDP = 8_SENSOR_DATA_PROCESSOR_DOCUMENTATION.md §9
  HM  = 9_HEALTH_MONITOR_DOCUMENTATION.md §10
Both provide fully typed field tables.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AggregateInterval, DeviceStatus, pg_enum


class EnergyData(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SDP §9 `energyData` — raw meter readings."""

    __tablename__ = "energy_data"
    __table_args__ = (Index("ix_energy_data_device_id_timestamp", "device_id", "timestamp"),)

    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    energy: Mapped[float | None] = mapped_column(Numeric(18, 6))
    power: Mapped[float | None] = mapped_column(Numeric(18, 6))
    current: Mapped[float | None] = mapped_column(Numeric(18, 6))
    voltage: Mapped[float | None] = mapped_column(Numeric(18, 6))

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class SensorReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SDP §9 `sensorReading` — environmental readings."""

    __tablename__ = "sensor_reading"
    __table_args__ = (
        Index("ix_sensor_reading_device_id_timestamp", "device_id", "timestamp"),
    )

    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    temperature: Mapped[float | None] = mapped_column(Numeric(10, 3))
    humidity: Mapped[float | None] = mapped_column(Numeric(10, 3))
    motion: Mapped[bool | None] = mapped_column(Boolean)
    light_level: Mapped[float | None] = mapped_column(Numeric(12, 3))

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class EnergyAggregate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SDP §9 `energyAggregate` — interval rollups."""

    __tablename__ = "energy_aggregate"
    __table_args__ = (
        Index(
            "ix_energy_aggregate_device_id_interval_timestamp",
            "device_id",
            "interval",
            "timestamp",
        ),
    )

    interval: Mapped[AggregateInterval | None] = mapped_column(pg_enum(AggregateInterval))
    avg_power: Mapped[float | None] = mapped_column(Numeric(18, 6))
    max_power: Mapped[float | None] = mapped_column(Numeric(18, 6))
    total_energy: Mapped[float | None] = mapped_column(Numeric(18, 6))
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class DeviceHealthLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """HM §10 `deviceHealthLog`."""

    __tablename__ = "device_health_log"
    __table_args__ = (
        Index("ix_device_health_log_device_id_timestamp", "device_id", "timestamp"),
    )

    status: Mapped[DeviceStatus | None] = mapped_column(pg_enum(DeviceStatus))
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_time: Mapped[float | None] = mapped_column(Numeric(12, 3))
    error_detail: Mapped[str | None] = mapped_column(Text)

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


class DeviceUptime(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """HM §10 `deviceUptime` — one row per device per calendar date."""

    __tablename__ = "device_uptime"
    __table_args__ = (UniqueConstraint("device_id", "date"),)

    date: Mapped[date | None] = mapped_column(Date)
    online_minutes: Mapped[float | None] = mapped_column(Numeric(10, 2))
    offline_minutes: Mapped[float | None] = mapped_column(Numeric(10, 2))
    uptime_percent: Mapped[float | None] = mapped_column(Numeric(6, 3))

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )
