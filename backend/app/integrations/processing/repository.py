"""Repository contracts for durable processing, plus an in-memory implementation.

Two implementations satisfy these contracts and are run through the SAME
contract test-suite (tests/integrations/test_repository_contract.py):

* `InMemoryIntegrationRepository` -- unit tests, simulators, local runs.
* `SqlIntegrationRepository` (processing/sql_repository.py) -- MySQL.

Facility scope: every read/redrive used by operators takes `facility_scope`
(a set of facility ids). `None` means "system" and is only used by workers.
An out-of-scope record raises `NotFoundInScope`, exactly like a missing one.

Fencing: a `Claim` carries a lease token. Completion and failure recording
re-check the token and the lease expiry; a worker whose lease expired (and
whose message may already be re-claimed) gets `LeaseLost` and its result --
including any outbox rows -- is discarded.
"""

from __future__ import annotations

import copy
import json
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from app.integrations.core.envelope import (
    CanonicalEnvelope,
    Direction,
    IntakeOutcome,
    MessageStatus,
    Protocol,
)
from app.integrations.core.errors import (
    IdempotencyConflict,
    IntegrationError,
    InvalidTransition,
    LeaseLost,
    NotFoundInScope,
    ValidationFailed,
)
from app.integrations.core.hashing import canonical_json, idempotency_fingerprint, sha256_hex
from app.integrations.core.lifecycle import assert_transition

REDRIVE_REASON_MIN = 10
REDRIVE_REASON_MAX = 500


class OutboxStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    RETRY_WAIT = "RETRY_WAIT"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class StoredMessage:
    message_id: uuid.UUID
    client_id: uuid.UUID
    facility_id: uuid.UUID
    protocol: Protocol
    direction: Direction
    message_type: str
    external_message_id: str | None
    idempotency_key: str
    ordering_key: str | None
    correlation_id: str
    schema_version: str
    payload_hash: str
    status: MessageStatus
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    lease_owner: str | None
    lease_expires_at: datetime | None
    last_error_code: str | None
    last_error_category: str | None
    received_at: datetime
    completed_at: datetime | None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "message_id": str(self.message_id),
            "client_id": str(self.client_id),
            "facility_id": str(self.facility_id),
            "protocol": str(self.protocol),
            "direction": str(self.direction),
            "message_type": self.message_type,
            "external_message_id": self.external_message_id,
            "correlation_id": self.correlation_id,
            "ordering_key": self.ordering_key,
            "schema_version": self.schema_version,
            "payload_hash": self.payload_hash,
            "status": str(self.status),
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "next_attempt_at": _iso(self.next_attempt_at),
            "lease_owner": self.lease_owner,
            "lease_expires_at": _iso(self.lease_expires_at),
            "last_error_code": self.last_error_code,
            "last_error_category": self.last_error_category,
            "received_at": _iso(self.received_at),
            "completed_at": _iso(self.completed_at),
        }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class Claim:
    message: StoredMessage
    lease_token: str
    lease_expires_at: datetime
    worker_id: str


@dataclass(frozen=True)
class AcceptOutcome:
    outcome: IntakeOutcome
    message_id: uuid.UUID


@dataclass(frozen=True)
class OutboxDraft:
    protocol: Protocol
    message_type: str
    body: dict[str, Any] = field(repr=False)
    correlation_id: str | None = None


@dataclass(frozen=True)
class OutboxRecord:
    outbox_id: uuid.UUID
    source_message_id: uuid.UUID | None
    client_id: uuid.UUID
    facility_id: uuid.UUID
    protocol: Protocol
    message_type: str
    correlation_id: str
    payload_hash: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    sent_at: datetime | None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "outbox_id": str(self.outbox_id),
            "source_message_id": str(self.source_message_id) if self.source_message_id else None,
            "client_id": str(self.client_id),
            "facility_id": str(self.facility_id),
            "protocol": str(self.protocol),
            "message_type": self.message_type,
            "correlation_id": self.correlation_id,
            "payload_hash": self.payload_hash,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "next_attempt_at": _iso(self.next_attempt_at),
            "last_error_code": self.last_error_code,
            "created_at": _iso(self.created_at),
            "sent_at": _iso(self.sent_at),
        }


@dataclass(frozen=True)
class OutboxClaim:
    record: OutboxRecord
    lease_token: str
    lease_expires_at: datetime
    worker_id: str


@dataclass(frozen=True)
class AuditDraft:
    """An audit event raised by a handler. Facility, message id and time are
    filled in by the repository, and it is written in the SAME transaction as
    the handler's domain change, so the trail cannot disagree with the data."""

    action: str
    actor_type: str
    actor_id: str | None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    action: str
    actor_type: str  # "user" | "client" | "system"
    actor_id: str | None
    facility_id: uuid.UUID | None
    message_id: uuid.UUID | None
    reason: str | None
    detail: dict[str, Any]
    occurred_at: datetime


class CompletionContext:
    """Handed to the handler while its claim is fenced.

    `session` is the SQLAlchemy session holding the fence (None in memory).
    Domain work done on that session commits atomically with the SUCCEEDED
    status and the outbox rows.
    """

    def __init__(self, session: Any | None) -> None:
        self.session = session
        self.outbox: list[OutboxDraft] = []
        self.audits: list[AuditDraft] = []

    def add_outbox(self, draft: OutboxDraft) -> None:
        self.outbox.append(draft)

    def add_audit(self, draft: "AuditDraft") -> None:
        self.audits.append(draft)


def outbox_dead_letter_audit(record: "OutboxRecord", error, now: datetime) -> AuditEvent:
    """Audit row for an outbound message that was given up. Metadata only:
    identifiers and the error code -- never the body."""
    return AuditEvent(
        action="outbox.dead_letter",
        actor_type="system",
        actor_id=None,
        facility_id=record.facility_id,
        message_id=record.source_message_id,
        reason=None,
        detail={"outbox_id": str(record.outbox_id), "protocol": str(record.protocol),
                "error_code": getattr(error, "code", None), "attempts": record.attempt_count},
        occurred_at=now,
    )


def validate_redrive_reason(reason: str | None) -> str:
    text = (reason or "").strip()
    if not (REDRIVE_REASON_MIN <= len(text) <= REDRIVE_REASON_MAX):
        raise ValidationFailed(
            f"A redrive reason of {REDRIVE_REASON_MIN}-{REDRIVE_REASON_MAX} characters is required.",
            code="redrive_reason_required",
        )
    return text


def body_bytes_for(envelope: CanonicalEnvelope) -> bytes:
    """Canonical body bytes; their hash must equal envelope.payload_hash."""
    data = canonical_json(envelope.body)
    if sha256_hex(data) != envelope.payload_hash:
        raise ValidationFailed("Envelope payload hash does not match its body.", code="payload_hash_mismatch")
    return data


class IntegrationRepository(ABC):
    """Inbound queue + idempotency + outbox + audit, one storage backend."""

    # -- intake ---------------------------------------------------------
    @abstractmethod
    def accept(
        self, envelope: CanonicalEnvelope, *, wire_bytes: bytes | None, max_attempts: int
    ) -> AcceptOutcome: ...

    # -- worker ---------------------------------------------------------
    @abstractmethod
    def claim(self, *, worker_id: str, now: datetime, lease_seconds: int, limit: int) -> list[Claim]: ...

    @abstractmethod
    def load_body(self, message_id: uuid.UUID) -> dict[str, Any]: ...

    @abstractmethod
    def completion(self, claim: Claim, *, clock: Callable[[], datetime]) -> Any:
        """Context manager yielding a CompletionContext.

        The lease is checked on entry AND again on exit with a fresh `clock()`
        reading, so a handler that overran its lease cannot commit."""

    @abstractmethod
    def record_failure(
        self, claim: Claim, *, now: datetime, error: IntegrationError, retry_at: datetime | None
    ) -> MessageStatus: ...

    # -- operators (facility scoped) --------------------------------------
    @abstractmethod
    def get(self, message_id: uuid.UUID, *, facility_scope: set[uuid.UUID] | None) -> StoredMessage: ...

    @abstractmethod
    def list_messages(
        self,
        *,
        facility_scope: set[uuid.UUID] | None,
        statuses: set[MessageStatus] | None = None,
        limit: int = 50,
    ) -> list[StoredMessage]: ...

    @abstractmethod
    def redrive(
        self,
        message_id: uuid.UUID,
        *,
        facility_scope: set[uuid.UUID],
        actor_id: str,
        reason: str,
        now: datetime,
    ) -> StoredMessage: ...

    @abstractmethod
    def counts_by_status(self, *, facility_scope: set[uuid.UUID] | None) -> dict[str, int]: ...

    @abstractmethod
    def purge_completed(self, *, before: datetime, now: datetime) -> dict[str, int]:
        """Delete SUCCEEDED inbound (with payload + idempotency key) and SENT
        outbound rows completed before `before`. Pending, retrying and
        dead-lettered rows are never purged. Writes one audit event."""

    @abstractmethod
    def facility_health(
        self, *, facility_scope: set[uuid.UUID] | None, now: datetime, window: timedelta
    ) -> list: ...

    @abstractmethod
    def protocol_activity(self, *, facility_scope: set[uuid.UUID] | None) -> dict:
        """protocol -> processing.activity.ProtocolActivity (read-only)."""

    @abstractmethod
    def search_messages(self, query: Any, *, facility_scope: set[uuid.UUID] | None) -> tuple[list, bool]:
        """(page of StoredMessage, total matching rows) for a processing.activity.MessageQuery."""

    # -- outbox -----------------------------------------------------------
    @abstractmethod
    def enqueue_outbox(
        self,
        draft: OutboxDraft,
        *,
        client_id: uuid.UUID,
        facility_id: uuid.UUID,
        source_message_id: uuid.UUID | None,
        max_attempts: int,
        now: datetime,
    ) -> uuid.UUID: ...

    def backlog(self, *, facility_scope: set[uuid.UUID] | None, now: datetime) -> dict:
        """Per protocol: what unfinished work is waiting for (activity.BacklogSnapshot).
        Read-only. Implementations that cannot compute it raise NotImplementedError,
        and the overview then falls back to the received-age classification."""
        raise NotImplementedError

    def metrics(self, query: Any, *, facility_scope: set[uuid.UUID] | None) -> dict:
        """Windowed, server-side aggregates for one protocol (activity.MetricsQuery).
        Read-only. NotImplementedError = the store cannot aggregate."""
        raise NotImplementedError

    @abstractmethod
    def claim_outbox(
        self, *, worker_id: str, now: datetime, lease_seconds: int, limit: int,
        protocols: frozenset[str] | None = None,
    ) -> list[OutboxClaim]:
        """Claim due outbox rows. `protocols` restricts the claim to protocols the
        caller can actually deliver; rows of other protocols are left untouched
        (they stay PENDING instead of being dead-lettered for want of a sender)."""

    @abstractmethod
    def load_outbox_body(self, outbox_id: uuid.UUID) -> dict[str, Any]: ...

    @abstractmethod
    def mark_outbox_sent(self, claim: OutboxClaim, *, now: datetime) -> None: ...

    @abstractmethod
    def record_outbox_failure(
        self, claim: OutboxClaim, *, now: datetime, error: IntegrationError, retry_at: datetime | None
    ) -> str: ...

    @abstractmethod
    def list_outbox(
        self, *, facility_scope: set[uuid.UUID] | None, statuses: set[str] | None = None, limit: int = 50
    ) -> list[OutboxRecord]: ...

    # -- audit --------------------------------------------------------------
    @abstractmethod
    def record_audit(self, event: AuditEvent) -> None: ...

    @abstractmethod
    def list_audit(
        self, *, facility_scope: set[uuid.UUID] | None, limit: int = 50
    ) -> list[AuditEvent]: ...


# ===========================================================================
# In-memory implementation
# ===========================================================================


BLOCKING_STATUSES = frozenset({MessageStatus.PENDING, MessageStatus.PROCESSING, MessageStatus.RETRY_WAIT})


def blocking_statuses(dead_letter_blocks: bool) -> frozenset[MessageStatus]:
    """Statuses of an EARLIER same-key message that hold a later one back.

    A dead-lettered predecessor blocks by default: running a check-out after
    its check-in failed would be wrong. The operator releases the chain by
    redriving the dead letter. Final policy: HF-27."""
    extra = {MessageStatus.DEAD_LETTER} if dead_letter_blocks else set()
    return frozenset(BLOCKING_STATUSES | extra)


class InMemoryIntegrationRepository(IntegrationRepository):
    def __init__(self, *, dead_letter_blocks_ordering: bool = True) -> None:
        self._blocking = blocking_statuses(dead_letter_blocks_ordering)
        self._lock = threading.RLock()
        self._messages: dict[uuid.UUID, StoredMessage] = {}
        self._lease_tokens: dict[uuid.UUID, str] = {}
        self._bodies: dict[uuid.UUID, bytes] = {}
        self._wire: dict[uuid.UUID, bytes] = {}
        self._idem: dict[tuple[uuid.UUID, uuid.UUID, str], tuple[str, uuid.UUID]] = {}
        self._outbox: dict[uuid.UUID, OutboxRecord] = {}
        self._outbox_bodies: dict[uuid.UUID, bytes] = {}
        self._outbox_tokens: dict[uuid.UUID, str] = {}
        self._audit: list[AuditEvent] = []

    # -- intake -------------------------------------------------------------
    def accept(self, envelope, *, wire_bytes, max_attempts):
        body = body_bytes_for(envelope)
        fingerprint = idempotency_fingerprint(envelope.message_type, envelope.body)
        key = (envelope.client_id, envelope.facility_id, envelope.idempotency_key)
        with self._lock:
            existing = self._idem.get(key)
            if existing is not None:
                stored_fp, stored_id = existing
                if stored_fp == fingerprint:
                    return AcceptOutcome(IntakeOutcome.DUPLICATE, stored_id)
                raise IdempotencyConflict(
                    "Idempotency key was already used with different content.",
                    detail={"message_id": str(stored_id)},
                )
            if envelope.message_id in self._messages:
                raise IdempotencyConflict("Message id already exists.")
            self._idem[key] = (fingerprint, envelope.message_id)
            self._messages[envelope.message_id] = StoredMessage(
                message_id=envelope.message_id,
                client_id=envelope.client_id,
                facility_id=envelope.facility_id,
                protocol=envelope.protocol,
                direction=envelope.direction,
                message_type=envelope.message_type,
                external_message_id=envelope.external_message_id,
                idempotency_key=envelope.idempotency_key,
                ordering_key=envelope.ordering_key,
                correlation_id=envelope.correlation_id,
                schema_version=envelope.schema_version,
                payload_hash=envelope.payload_hash,
                status=MessageStatus.PENDING,
                attempt_count=0,
                max_attempts=max_attempts,
                next_attempt_at=envelope.received_at,
                lease_owner=None,
                lease_expires_at=None,
                last_error_code=None,
                last_error_category=None,
                received_at=envelope.received_at,
                completed_at=None,
            )
            self._bodies[envelope.message_id] = body
            if wire_bytes is not None:
                self._wire[envelope.message_id] = bytes(wire_bytes)
            return AcceptOutcome(IntakeOutcome.ACCEPTED, envelope.message_id)

    # -- worker -------------------------------------------------------------
    def claim(self, *, worker_id, now, lease_seconds, limit):
        claims: list[Claim] = []
        with self._lock:
            due = sorted(
                (m for m in self._messages.values()
                 if m.next_attempt_at is not None and m.next_attempt_at <= now
                 and m.status in (MessageStatus.PENDING, MessageStatus.RETRY_WAIT, MessageStatus.PROCESSING)),
                key=lambda m: (m.next_attempt_at, str(m.message_id)),
            )
            due = [m for m in due if not self._blocked(m)]
            for msg in due[:limit]:
                assert_transition(msg.status, MessageStatus.PROCESSING)
                token = uuid.uuid4().hex
                expires = now + timedelta(seconds=lease_seconds)
                updated = replace(
                    msg,
                    status=MessageStatus.PROCESSING,
                    attempt_count=msg.attempt_count + 1,
                    lease_owner=worker_id,
                    lease_expires_at=expires,
                    # An expired lease makes the message claimable again.
                    next_attempt_at=expires,
                )
                self._messages[msg.message_id] = updated
                self._lease_tokens[msg.message_id] = token
                claims.append(Claim(updated, token, expires, worker_id))
        return claims

    def _blocked(self, msg: StoredMessage) -> bool:
        if msg.ordering_key is None:
            return False
        mine = (msg.received_at, str(msg.message_id))
        return any(
            o.ordering_key == msg.ordering_key and o.client_id == msg.client_id
            and o.facility_id == msg.facility_id and (o.received_at, str(o.message_id)) < mine
            and o.status in self._blocking
            for o in self._messages.values()
        )

    def load_body(self, message_id):
        with self._lock:
            return json.loads(self._bodies[message_id])

    def _fence(self, claim: Claim, now: datetime) -> StoredMessage:
        current = self._messages.get(claim.message.message_id)
        if (
            current is None
            or current.status is not MessageStatus.PROCESSING
            or self._lease_tokens.get(current.message_id) != claim.lease_token
            or current.lease_expires_at is None
            or current.lease_expires_at <= now
        ):
            raise LeaseLost("Worker lease expired or was taken over.")
        return current

    @contextmanager
    def completion(self, claim, *, clock) -> Iterator[CompletionContext]:
        with self._lock:
            self._fence(claim, clock())
            ctx = CompletionContext(session=None)
            yield ctx
            # Re-fence: the handler may have run past the lease.
            now = clock()
            current = self._fence(claim, now)
            snapshot_outbox = dict(self._outbox)
            snapshot_bodies = dict(self._outbox_bodies)
            try:
                for draft in ctx.outbox:
                    self.enqueue_outbox(
                        draft,
                        client_id=current.client_id,
                        facility_id=current.facility_id,
                        source_message_id=current.message_id,
                        max_attempts=current.max_attempts,
                        now=now,
                    )
            except Exception:
                self._outbox, self._outbox_bodies = snapshot_outbox, snapshot_bodies
                raise
            for audit in ctx.audits:
                self._audit.append(AuditEvent(
                    action=audit.action, actor_type=audit.actor_type, actor_id=audit.actor_id,
                    facility_id=current.facility_id, message_id=current.message_id, reason=None,
                    detail=dict(audit.detail), occurred_at=now,
                ))
            assert_transition(current.status, MessageStatus.SUCCEEDED)
            self._messages[current.message_id] = replace(
                current,
                status=MessageStatus.SUCCEEDED,
                lease_owner=None,
                lease_expires_at=None,
                next_attempt_at=None,
                last_error_code=None,
                last_error_category=None,
                completed_at=now,
            )
            self._lease_tokens.pop(current.message_id, None)

    def record_failure(self, claim, *, now, error, retry_at):
        with self._lock:
            current = self._fence(claim, now)
            target = MessageStatus.RETRY_WAIT if retry_at is not None else MessageStatus.DEAD_LETTER
            assert_transition(current.status, target)
            self._messages[current.message_id] = replace(
                current,
                status=target,
                lease_owner=None,
                lease_expires_at=None,
                next_attempt_at=retry_at,
                last_error_code=error.code,
                last_error_category=str(error.category),
                completed_at=now if target is MessageStatus.DEAD_LETTER else None,
            )
            self._lease_tokens.pop(current.message_id, None)
            return target

    # -- operators ------------------------------------------------------------
    @staticmethod
    def _in_scope(facility_id, scope) -> bool:
        return scope is None or facility_id in scope

    def get(self, message_id, *, facility_scope):
        with self._lock:
            msg = self._messages.get(message_id)
            if msg is None or not self._in_scope(msg.facility_id, facility_scope):
                raise NotFoundInScope("Message not found.")
            return msg

    def list_messages(self, *, facility_scope, statuses=None, limit=50):
        with self._lock:
            rows = [
                m for m in self._messages.values()
                if self._in_scope(m.facility_id, facility_scope)
                and (statuses is None or m.status in statuses)
            ]
        rows.sort(key=lambda m: (m.received_at, str(m.message_id)), reverse=True)
        return rows[:limit]

    def redrive(self, message_id, *, facility_scope, actor_id, reason, now):
        reason = validate_redrive_reason(reason)
        with self._lock:
            msg = self.get(message_id, facility_scope=facility_scope)
            if msg.status is not MessageStatus.DEAD_LETTER:
                raise InvalidTransition(
                    "Only dead-lettered messages can be redriven.",
                    detail={"status": str(msg.status)},
                )
            assert_transition(msg.status, MessageStatus.PENDING)
            updated = replace(
                msg,
                status=MessageStatus.PENDING,
                attempt_count=0,
                next_attempt_at=now,
                completed_at=None,
                lease_owner=None,
                lease_expires_at=None,
            )
            self._messages[message_id] = updated
            self._audit.append(
                AuditEvent(
                    action="message.redrive",
                    actor_type="user",
                    actor_id=actor_id,
                    facility_id=msg.facility_id,
                    message_id=message_id,
                    reason=reason,
                    detail={"previous_error_code": msg.last_error_code},
                    occurred_at=now,
                )
            )
            return updated

    def counts_by_status(self, *, facility_scope):
        counts: dict[str, int] = {}
        with self._lock:
            for m in self._messages.values():
                if self._in_scope(m.facility_id, facility_scope):
                    counts[str(m.status)] = counts.get(str(m.status), 0) + 1
        return counts

    def purge_completed(self, *, before, now):
        with self._lock:
            gone = [m.message_id for m in self._messages.values()
                    if m.status is MessageStatus.SUCCEEDED and m.completed_at and m.completed_at < before]
            for mid in gone:
                del self._messages[mid]
                self._bodies.pop(mid, None)
                self._wire.pop(mid, None)
            self._idem = {k: v for k, v in self._idem.items() if v[1] not in set(gone)}
            sent = [r.outbox_id for r in self._outbox.values()
                    if r.status == OutboxStatus.SENT and r.sent_at and r.sent_at < before]
            for oid in sent:
                del self._outbox[oid]
                self._outbox_bodies.pop(oid, None)
            counts = {"inbound": len(gone), "outbox": len(sent)}
            self._audit.append(AuditEvent("retention.purge", "system", None, None, None, None,
                                          {**counts, "before": before.isoformat()}, now))
            return counts

    def facility_health(self, *, facility_scope, now, window):
        from app.integrations.processing.health import from_memory

        with self._lock:
            return from_memory(list(self._messages.values()), list(self._outbox.values()),
                               scope=facility_scope, now=now, window=window)

    def protocol_activity(self, *, facility_scope):
        from app.integrations.processing.activity import activity_from_memory

        with self._lock:
            return activity_from_memory(list(self._messages.values()), list(self._outbox.values()),
                                        scope=facility_scope)

    def search_messages(self, query, *, facility_scope):
        from app.integrations.processing.activity import search_memory

        with self._lock:
            return search_memory(list(self._messages.values()), query, scope=facility_scope)

    # -- outbox -----------------------------------------------------------------
    def enqueue_outbox(self, draft, *, client_id, facility_id, source_message_id, max_attempts, now):
        body = canonical_json(draft.body)
        outbox_id = uuid.uuid4()
        with self._lock:
            self._outbox[outbox_id] = OutboxRecord(
                outbox_id=outbox_id,
                source_message_id=source_message_id,
                client_id=client_id,
                facility_id=facility_id,
                protocol=draft.protocol,
                message_type=draft.message_type,
                correlation_id=draft.correlation_id or uuid.uuid4().hex,
                payload_hash=sha256_hex(body),
                status=OutboxStatus.PENDING,
                attempt_count=0,
                max_attempts=max_attempts,
                next_attempt_at=now,
                last_error_code=None,
                created_at=now,
                sent_at=None,
            )
            self._outbox_bodies[outbox_id] = body
        return outbox_id

    def backlog(self, *, facility_scope, now):
        from app.integrations.processing.activity import backlog_from_memory

        with self._lock:
            messages = list(self._messages.values())
            outbox = list(self._outbox.values())
        return backlog_from_memory(messages, outbox, scope=facility_scope, now=now)

    def metrics(self, query, *, facility_scope):
        from app.integrations.processing.activity import metrics_from_memory

        with self._lock:
            messages = list(self._messages.values())
            outbox = list(self._outbox.values())
        return metrics_from_memory(messages, outbox, query, scope=facility_scope)

    def claim_outbox(self, *, worker_id, now, lease_seconds, limit, protocols=None):
        claims: list[OutboxClaim] = []
        wanted = None if protocols is None else {str(p) for p in protocols}
        with self._lock:
            due = sorted(
                (r for r in self._outbox.values()
                 if r.next_attempt_at is not None and r.next_attempt_at <= now
                 and (wanted is None or str(r.protocol) in wanted)
                 and r.status in (OutboxStatus.PENDING, OutboxStatus.RETRY_WAIT, OutboxStatus.PROCESSING)),
                key=lambda r: (r.next_attempt_at, str(r.outbox_id)),
            )
            for rec in due[:limit]:
                token = uuid.uuid4().hex
                expires = now + timedelta(seconds=lease_seconds)
                updated = replace(
                    rec, status=OutboxStatus.PROCESSING, attempt_count=rec.attempt_count + 1,
                    next_attempt_at=expires,
                )
                self._outbox[rec.outbox_id] = updated
                self._outbox_tokens[rec.outbox_id] = token
                claims.append(OutboxClaim(updated, token, expires, worker_id))
        return claims

    def load_outbox_body(self, outbox_id):
        with self._lock:
            return json.loads(self._outbox_bodies[outbox_id])

    def _fence_outbox(self, claim: OutboxClaim, now: datetime) -> OutboxRecord:
        current = self._outbox.get(claim.record.outbox_id)
        if (
            current is None
            or current.status != OutboxStatus.PROCESSING
            or self._outbox_tokens.get(current.outbox_id) != claim.lease_token
            or claim.lease_expires_at <= now
        ):
            raise LeaseLost("Outbox lease expired or was taken over.")
        return current

    def mark_outbox_sent(self, claim, *, now):
        with self._lock:
            current = self._fence_outbox(claim, now)
            self._outbox[current.outbox_id] = replace(
                current, status=OutboxStatus.SENT, sent_at=now, next_attempt_at=None, last_error_code=None
            )
            self._outbox_tokens.pop(current.outbox_id, None)

    def record_outbox_failure(self, claim, *, now, error, retry_at):
        with self._lock:
            current = self._fence_outbox(claim, now)
            status = OutboxStatus.RETRY_WAIT if retry_at is not None else OutboxStatus.DEAD_LETTER
            self._outbox[current.outbox_id] = replace(
                current, status=status, next_attempt_at=retry_at, last_error_code=error.code
            )
            self._outbox_tokens.pop(current.outbox_id, None)
            if status == OutboxStatus.DEAD_LETTER:
                self._audit.append(outbox_dead_letter_audit(current, error, now))
            return status

    def list_outbox(self, *, facility_scope, statuses=None, limit=50):
        with self._lock:
            rows = [
                r for r in self._outbox.values()
                if self._in_scope(r.facility_id, facility_scope)
                and (statuses is None or r.status in statuses)
            ]
        rows.sort(key=lambda r: (r.created_at, str(r.outbox_id)), reverse=True)
        return rows[:limit]

    # -- audit --------------------------------------------------------------------
    def record_audit(self, event):
        with self._lock:
            self._audit.append(copy.deepcopy(event))

    def list_audit(self, *, facility_scope, limit=50):
        with self._lock:
            rows = [e for e in self._audit if facility_scope is None or e.facility_id in facility_scope]
        return list(reversed(rows))[:limit]

    # -- test introspection ---------------------------------------------------
    def stored_wire_bytes(self, message_id: uuid.UUID) -> bytes | None:
        with self._lock:
            return self._wire.get(message_id)
