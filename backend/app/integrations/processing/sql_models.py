"""SQLAlchemy models for the integration tables (MySQL 8).

STATUS: CANDIDATE SCHEMA -- NOT APPROVED (HF-39). These tables do not exist in
the HMS database. The DDL is proposed in
`backend/migrations/drafts/integration_tables_candidate.py` and
`docs/HTNG_FIAS_DATABASE_DESIGN.md`; it has only been applied to disposable
test databases.

They are declared on a SEPARATE `MetaData` (`INTEGRATION_METADATA`) on purpose:
the HMS `Base.metadata` drives Alembic autogenerate and schema verification,
and an unapproved table must not appear there.

`facility` is declared here as a one-column stub ONLY so foreign keys resolve.
It is never created from this metadata: use `create_integration_tables()`,
which creates the integration tables and nothing else.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.base import NAMING_CONVENTION
from app.db.types import GUID, JSONB, NOW, UTCDateTime

INTEGRATION_METADATA = MetaData(naming_convention=NAMING_CONVENTION)

#: FK target stub -- see module docstring. Matches facility.id (CHAR(36) on MySQL).
FACILITY_STUB = Table("facility", INTEGRATION_METADATA, Column("id", GUID(), primary_key=True))

LongText = Text().with_variant(mysql.LONGTEXT(), "mysql")
MediumBlob = LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql")

MESSAGE_STATUSES = ("RECEIVED", "VALIDATED", "PENDING", "PROCESSING", "SUCCEEDED", "RETRY_WAIT", "DEAD_LETTER", "REJECTED")
OUTBOX_STATUSES = ("PENDING", "PROCESSING", "SENT", "RETRY_WAIT", "DEAD_LETTER")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class IntegrationBase(DeclarativeBase):
    metadata = INTEGRATION_METADATA


class IntegrationClientRow(IntegrationBase):
    __tablename__ = "integration_clients"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    client_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    #: "sha256$<hex>" -- see security/clients.py. Never the secret.
    secret_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    #: Previous secret during a rotation overlap; ignored after secondary_expires_on.
    secondary_secret_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    secondary_expires_on: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    #: Comma-separated Protocol values, e.g. "fias" or "fias,htng".
    protocols: Mapped[str] = mapped_column(String(64), nullable=False)
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)
    updated_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW, onupdate=NOW)


class FacilityMappingRow(IntegrationBase):
    __tablename__ = "integration_facility_mappings"
    __table_args__ = (
        UniqueConstraint("client_id", "normalized_property_code"),
        Index(None, "facility_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_clients.id", ondelete="RESTRICT"), nullable=False
    )
    external_property_code: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Equal to external_property_code under the EXACT policy (HF-05 pending).
    #: Binary collation: MySQL's default utf8mb4_0900_ai_ci is case- and
    #: accent-INSENSITIVE, which would silently decide HF-05 in the database
    #: (both for lookups and for the unique key).
    normalized_property_code: Mapped[str] = mapped_column(
        String(32).with_variant(mysql.VARCHAR(32, collation="utf8mb4_bin"), "mysql"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("facility.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)
    updated_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW, onupdate=NOW)


class InboundMessageRow(IntegrationBase):
    __tablename__ = "integration_inbound_messages"
    __table_args__ = (
        CheckConstraint(_in("status", MESSAGE_STATUSES), name="status_valid"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        # Claim query: WHERE next_attempt_at <= :now ORDER BY next_attempt_at.
        # Terminal rows have next_attempt_at NULL, so they drop out of the scan.
        Index(None, "next_attempt_at"),
        Index(None, "facility_id", "status", "received_on"),
        Index(None, "correlation_id"),
        # Ordering predicate: earlier unfinished message with the same key.
        Index(None, "client_id", "facility_id", "ordering_key", "received_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_clients.id", ondelete="RESTRICT"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("facility.id", ondelete="RESTRICT"), nullable=False
    )
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(128), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    ordering_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(96), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    received_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_on: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)
    updated_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW, onupdate=NOW)


class InboundPayloadRow(IntegrationBase):
    """Sensitive storage, separated from diagnostic metadata.

    `body_canonical` is the canonical JSON text whose SHA-256 is the message's
    payload_hash; it is TEXT, not JSON, so MySQL cannot re-order it.
    `wire_payload` is kept only when INTEGRATION_STORE_RAW_WIRE_PAYLOAD is on.
    Encryption at rest and `retain_until` purging are pending HF-21.
    """

    __tablename__ = "integration_inbound_payloads"

    message_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_inbound_messages.id", ondelete="CASCADE"), primary_key=True
    )
    body_canonical: Mapped[str] = mapped_column(LongText, nullable=False)
    wire_payload: Mapped[bytes | None] = mapped_column(MediumBlob, nullable=True)
    retain_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)


class IdempotencyKeyRow(IntegrationBase):
    __tablename__ = "integration_idempotency_keys"
    __table_args__ = (UniqueConstraint("client_id", "facility_id", "idempotency_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_clients.id", ondelete="RESTRICT"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("facility.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    #: sha256 of canonical {message_type, body}; see core/hashing.py.
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_inbound_messages.id", ondelete="CASCADE"), nullable=False
    )
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)


class OutboxMessageRow(IntegrationBase):
    __tablename__ = "integration_outbox_messages"
    __table_args__ = (
        CheckConstraint(_in("status", OUTBOX_STATUSES), name="status_valid"),
        Index(None, "next_attempt_at"),
        Index(None, "facility_id", "status", "created_on"),
        Index(None, "source_message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("integration_inbound_messages.id", ondelete="SET NULL"), nullable=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("integration_clients.id", ondelete="RESTRICT"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("facility.id", ondelete="RESTRICT"), nullable=False
    )
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body_canonical: Mapped[str] = mapped_column(LongText, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(96), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW)
    sent_on: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    updated_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=NOW, onupdate=NOW)


class AuditEventRow(IntegrationBase):
    """Append-only. Retention / immutability policy pending HF-23."""

    __tablename__ = "integration_audit_events"
    __table_args__ = (
        Index(None, "facility_id", "occurred_on"),
        Index(None, "message_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_on: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    #: No FK: audit rows must outlive the rows they describe.
    facility_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Metadata only (codes, ids). Never payload values.
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


#: Creation order (parents first). The facility stub is deliberately absent.
INTEGRATION_TABLES = [
    IntegrationClientRow.__table__,
    FacilityMappingRow.__table__,
    InboundMessageRow.__table__,
    InboundPayloadRow.__table__,
    IdempotencyKeyRow.__table__,
    OutboxMessageRow.__table__,
    AuditEventRow.__table__,
]


def create_integration_tables(bind: Engine | Connection) -> None:
    """Create ONLY the integration tables. For disposable/test databases."""
    INTEGRATION_METADATA.create_all(bind, tables=INTEGRATION_TABLES)


def drop_integration_tables(bind: Engine | Connection) -> None:
    INTEGRATION_METADATA.drop_all(bind, tables=list(reversed(INTEGRATION_TABLES)))
