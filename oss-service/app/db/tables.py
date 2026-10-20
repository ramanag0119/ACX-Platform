"""Explicit SQLAlchemy Core table definitions for the OSS `insp_iot` schema.

Only the columns the adapters actually read are declared (read-only). Declaring
them explicitly -- rather than reflecting on every request -- keeps queries
cheap, makes exactly what we touch auditable, and lets adapters build
parameterised `select()` statements. Column names/types are transcribed from the
verified discovery output (`tools/discover_schema.py`).

Nothing here is used to create, alter or drop anything: these Table objects are
query metadata only.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

insp_device = Table(
    "insp_device", metadata,
    Column("device_id", UUID(as_uuid=True), primary_key=True),
    Column("device_uid", Text),
    Column("serial_number", Text),
    Column("device_name", Text),
    Column("device_type", Text),
    Column("node_type", Text),
    Column("parent_device_id", UUID(as_uuid=True)),
    Column("is_gateway", Boolean),
    Column("appliance", Text),
    Column("manufacturer", Text),
    Column("model", Text),
    Column("model_number", Text),
    Column("firmware_version", Text),
    Column("site_id", UUID(as_uuid=True)),
    Column("status", Text),
    Column("created_dtm_utc", DateTime),
    Column("updated_dtm_utc", DateTime),
)

insp_device_health = Table(
    "insp_device_health", metadata,
    Column("record_id", UUID(as_uuid=True), primary_key=True),
    Column("time", DateTime, primary_key=True),
    Column("device_uid", Text),
    Column("health_status", SmallInteger),
    Column("temperature", Numeric(6, 2)),
    Column("recorded_at", DateTime),
    Column("device_id", UUID(as_uuid=True)),
    Column("created_dtm_utc", DateTime),
)

insp_device_state = Table(
    "insp_device_state", metadata,
    Column("device_state_id", UUID(as_uuid=True), primary_key=True),
    Column("device_id", UUID(as_uuid=True)),
    Column("device_state_type_id", Integer),
    Column("state_effective_dtm_utc", DateTime),
)

insp_device_state_type = Table(
    "insp_device_state_type", metadata,
    Column("device_state_type_id", Integer, primary_key=True),
    Column("device_state_name", Text),
)

insp_device_performance = Table(
    "insp_device_performance", metadata,
    Column("record_id", UUID(as_uuid=True), primary_key=True),
    Column("time", DateTime, primary_key=True),
    Column("device_uid", Text),
    Column("recorded_at", DateTime),
    Column("received_at", DateTime),
    Column("param_data", JSONB),
    Column("device_id", UUID(as_uuid=True)),
    Column("created_dtm_utc", DateTime),
    Column("updated_dtm_utc", DateTime),
)

insp_device_alert = Table(
    "insp_device_alert", metadata,
    Column("record_id", UUID(as_uuid=True), primary_key=True),
    Column("time", DateTime, primary_key=True),
    Column("device_uid", Text),
    Column("alert_type", SmallInteger),
    Column("alert_severity", Text),
    Column("alert_data", JSONB),
    Column("recorded_at", DateTime),
    Column("device_id", UUID(as_uuid=True)),
    Column("created_dtm_utc", DateTime),
    Column("updated_dtm_utc", DateTime),
)

insp_site = Table(
    "insp_site", metadata,
    Column("site_id", UUID(as_uuid=True), primary_key=True),
    Column("site_name", Text),
    Column("customer_id", UUID(as_uuid=True)),
)
