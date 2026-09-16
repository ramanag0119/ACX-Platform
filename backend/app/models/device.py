"""Group G - devices, telemetry and IoT (14 tables).

Blueprint §5, tables 46-59.

Telemetry is IKANOS's generic EAV pair -- `device_param` (schema) plus
`device_stat` (values). The Phase 1 `energy_data`, `sensor_reading` and
`device_uptime` tables were invented and are gone.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    BigIntPk,
    HMSBase,
    IntLookupPk,
    SmallIntLookupPk,
    TimestampMixin,
    UUIDPk,
)
from app.models import enums
from app.models.facility import user_fk


class DeviceType(Base, TimestampMixin, SmallIntLookupPk):
    """The 4 Caleido device families. IKANOS `device_types`. USE.

    Seeded: Intellihub (HUB), Kleio (KLE), Mikos (MIK), AirQ (AIR).
    The Phase 1 enum values LOCK / SENSOR / SWITCH / CONTROLLER do not exist
    -- Kleio IS the lock.
    """

    __tablename__ = "device_type"

    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_short_code: Mapped[str | None] = mapped_column(
        enums.device_short_code, nullable=True
    )


class Firmware(HMSBase, UUIDPk):
    """Firmware binaries per device type. IKANOS `firmware`. ADAPT.

    `is_latest` is removed -- currency is `device.current_firmware_version`
    versus `device.expected_firmware_version`.
    """

    __tablename__ = "firmware"

    device_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    firmware_version: Mapped[str] = mapped_column(String(20), nullable=False)
    firmware_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    firmware_url: Mapped[str] = mapped_column(String(500), nullable=False)
    firmware_size: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    crc: Mapped[str] = mapped_column(Text, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decommission_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        enums.firmware_status, nullable=False, server_default="active"
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )


class Device(HMSBase, UUIDPk):
    """A physical device installed in a room.
    IKANOS `devices` + `device_metadata` (MERGE). ADAPT.

    `ip_address`, `mac_address` and `last_seen` are NOT columns: documented in
    CPA §8 but absent from the DB. `last_seen` is derivable from
    `device_health_stat.created_on` (blueprint §11.12 / OPEN DECISION list).
    """

    __tablename__ = "device"

    device_uid: Mapped[str | None] = mapped_column(
        String(16), nullable=True, unique=True
    )
    part_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manufacturer_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mfg_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Sensors carry their hub id here.
    parent_device_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    device_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    appliance_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authentication_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    health_status: Mapped[str | None] = mapped_column(
        enums.device_health_status, nullable=True, index=True
    )
    device_temperature: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    current_firmware_version: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=True
    )
    expected_firmware_version: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firmware.id", ondelete="CASCADE"), nullable=True
    )
    device_config_status: Mapped[str | None] = mapped_column(
        enums.device_config_status, nullable=True
    )
    is_power_off: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    installed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Hubless architecture flag.
    operational_mode: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_other_device: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    # MERGE: absorbed `device_metadata`.
    device_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("ix_device_metadata_gin", "metadata", postgresql_using="gin"),
    )


class DeviceParam(Base, TimestampMixin, IntLookupPk):
    """Telemetry parameter registry -- the schema half of the EAV model.
    IKANOS `device_params` (35 rows). USE.

    `unit` is the missing Y-axis unit of Dashboard gap D4.
    """

    __tablename__ = "device_param"

    device_type: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    param_name: Mapped[str] = mapped_column(String(50), nullable=False)
    data_type: Mapped[str | None] = mapped_column(enums.param_data_type, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)


class DeviceStat(HMSBase, BigIntPk):
    """Every telemetry reading. Powers Power View, Energy View and the device
    cards. IKANOS `device_stats`. USE.

    Replaces the invented `energy_data` and `sensor_reading` tables.
    """

    __tablename__ = "device_stat"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_param_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("device_param.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Value as text; `device_param.data_type` says how to read it.
    device_param_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_other_device: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_device_stat_device_id_timestamp", "device_id", "timestamp"),
        Index("ix_device_stat_timestamp_brin", "timestamp", postgresql_using="brin"),
    )


class DeviceCurrentStat(HMSBase, UUIDPk):
    """Latest snapshot per device as a single blob -- avoids a top-N-per-group
    query over `device_stat`. IKANOS `device_current_stats`. USE."""

    __tablename__ = "device_current_stat"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_other_device: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DeviceHealthStat(HMSBase, BigIntPk):
    """Heartbeat / health log per device. IKANOS `device_health_stats`. ADAPT.

    `response_time` and `error_detail` are removed -- neither exists [FACT].
    """

    __tablename__ = "device_health_stat"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    device_health_status: Mapped[str] = mapped_column(
        enums.device_health_status, nullable=False
    )
    device_temperature: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        Index("ix_device_health_stat_device_id_created_on", "device_id", "created_on"),
        Index(
            "ix_device_health_stat_created_on_brin",
            "created_on",
            postgresql_using="brin",
        ),
    )


class CommandType(Base, TimestampMixin, SmallIntLookupPk):
    """Command registry, optionally scoped to a device type.
    IKANOS `command_types`. USE."""

    __tablename__ = "command_type"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    device_type_id: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class DeviceCommand(HMSBase, UUIDPk):
    """Outbound command queue -- key issuance, lock/unlock, config push.
    IKANOS `device_commands`. USE."""

    __tablename__ = "device_command"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_type: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("command_type.id", ondelete="CASCADE"), nullable=False
    )
    command_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str | None] = mapped_column(
        enums.command_processing_status,
        nullable=True,
        server_default="Queued",
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class MqttBroker(HMSBase, UUIDPk):
    """MQTT broker connection per facility. IKANOS `mqtt_brokers`. USE.

    `broker_password` is stored in clear text in IKANOS. HMS must encrypt it
    at rest regardless (blueprint OPEN DECISION #14) -- that is an application
    concern, not a schema one, so the column type is unchanged.
    """

    __tablename__ = "mqtt_broker"

    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    broker_name: Mapped[str] = mapped_column(String(50), nullable=False)
    broker_ip: Mapped[str | None] = mapped_column(String(40), nullable=True)
    broker_vpn_ip: Mapped[str | None] = mapped_column(String(40), nullable=True)
    broker_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    broker_user_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    broker_password: Mapped[str | None] = mapped_column(String(50), nullable=True)


class MqttTopic(HMSBase, UUIDPk):
    """Topic per device per purpose. IKANOS `mqtt_topics`. USE."""

    __tablename__ = "mqtt_topic"

    mqtt_broker_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mqtt_broker.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    topic_name: Mapped[str] = mapped_column(String(50), nullable=False)
    topic_type: Mapped[str] = mapped_column(enums.mqtt_topic_type, nullable=False)


class OtherDevice(HMSBase, BigIntPk):
    """Third-party (non-Caleido) energy meter readings.
    IKANOS `other_devices`. ADAPT.

    REVIEW (blueprint §10 #4 / OPEN DECISION #8): no foreign keys at all --
    preserved as IKANOS has it. The `EC` column's purpose is undocumented.
    IKANOS has no created_on/updated_on here; they are added per §5.0.
    """

    __tablename__ = "other_device"

    msg_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(225), nullable=True)
    voltage: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    current: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    power: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    all_energy: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    thirty_day_energy: Mapped[float | None] = mapped_column(
        DOUBLE_PRECISION, nullable=True
    )
    today_energy: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    current_hour_energy: Mapped[float | None] = mapped_column(
        DOUBLE_PRECISION, nullable=True
    )
    ec: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    msg_string: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_other_device_device_name_timestamp", "device_name", "timestamp"),
    )


class BatteryLifeStat(HMSBase, BigIntPk):
    """Battery charge-cycle history. IKANOS `battery_life_stats`. USE.

    [INFER] IKANOS declares no FK on `device_id`; one is added here
    (blueprint §10 #8).
    """

    __tablename__ = "battery_life_stat"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cycle_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    initial_battery_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    latest_battery_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    battery_life: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)


class SensorOperationStat(Base, TimestampMixin):
    """Daily per-device operational percentage -- the real "Smart Rooms Online"
    source. IKANOS `sensor_operation_stats`. USE -- replaces `device_uptime`.

    `online_minutes` / `offline_minutes` / `uptime_percent` do not exist;
    IKANOS stores a single `operation_percentage`.
    """

    __tablename__ = "sensor_operation_stat"

    device_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("device.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stats_date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation_percentage: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
