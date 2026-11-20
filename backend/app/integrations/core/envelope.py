"""Canonical envelope and the message models that travel between layers.

    DecodedMessage     what a protocol adapter produces from wire bytes. Not
                       yet trusted: no client, no facility, no idempotency.
    CanonicalEnvelope  a DecodedMessage after authentication, facility
                       resolution and validation. The only thing handlers see.
    OutboundRequest    what HMS code asks the exchange to send.
    IntakeResult       what the exchange answers to the transport layer.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Canonical (HMS-internal) message types. Lower-case dotted names. These are
#: NOT vendor record/message names; adapters map vendor names onto them.
MESSAGE_TYPE_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){0,4}$"
_MESSAGE_TYPE = re.compile(MESSAGE_TYPE_PATTERN)


class Protocol(StrEnum):
    FIAS = "fias"
    HTNG = "htng"
    #: In-process protocol used only by tests and simulators.
    TEST = "test"


class Direction(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    RETRY_WAIT = "RETRY_WAIT"
    DEAD_LETTER = "DEAD_LETTER"
    REJECTED = "REJECTED"


class IntakeOutcome(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


def utcnow() -> datetime:
    return datetime.now(UTC)


class DecodedMessage(BaseModel):
    """Adapter output. `property_code` is the EXTERNAL property identifier as
    the vendor sent it (or as bound to the link); it is resolved to an HMS
    facility only by the exchange, never by the adapter."""

    model_config = ConfigDict(frozen=True)

    protocol: Protocol
    message_type: str = Field(pattern=MESSAGE_TYPE_PATTERN)
    schema_version: str = Field(min_length=1, max_length=64)
    property_code: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    external_message_id: str | None = Field(default=None, max_length=128)
    body: dict[str, Any] = Field(repr=False)


class CanonicalEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    external_message_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=200)
    #: Business entity whose messages must be processed in arrival order
    #: (e.g. one stay). None = no ordering constraint.
    ordering_key: str | None = Field(default=None, min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=64)
    facility_id: uuid.UUID
    client_id: uuid.UUID
    protocol: Protocol
    message_type: str = Field(pattern=MESSAGE_TYPE_PATTERN)
    direction: Direction
    schema_version: str = Field(min_length=1, max_length=64)
    received_at: datetime = Field(default_factory=utcnow)
    payload_ref: str | None = None
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: MessageStatus = MessageStatus.RECEIVED
    retry_count: int = Field(default=0, ge=0)
    error_category: str | None = None
    trace: dict[str, str] = Field(default_factory=dict)
    #: Canonical body. Excluded from repr so it cannot reach a log by accident.
    body: dict[str, Any] = Field(repr=False)

    @field_validator("received_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        return value.astimezone(UTC)

    def metadata(self) -> dict[str, Any]:
        """Everything except the body -- safe for logs and operational APIs."""
        return self.model_dump(mode="json", exclude={"body"})


class OutboundRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: Protocol
    message_type: str = Field(pattern=MESSAGE_TYPE_PATTERN)
    facility_id: uuid.UUID
    client_id: uuid.UUID
    correlation_id: str | None = Field(default=None, max_length=64)
    source_message_id: uuid.UUID | None = None
    body: dict[str, Any] = Field(repr=False)


class IntakeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: IntakeOutcome
    correlation_id: str
    message_id: uuid.UUID | None = None
    message_type: str | None = None
    error: dict[str, Any] | None = None

    @property
    def retryable(self) -> bool:
        """True when intake failed for a TRANSIENT reason (e.g. database down):
        the same bytes may succeed later and must not be treated as rejected.
        """
        return (
            self.outcome is IntakeOutcome.REJECTED
            and bool(self.error)
            and self.error.get("category") == "transient"
        )


def is_valid_message_type(value: str) -> bool:
    return bool(_MESSAGE_TYPE.fullmatch(value))
