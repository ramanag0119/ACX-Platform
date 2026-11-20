"""MySQL implementation of `IntegrationRepository`.

Concurrency design (validated against MySQL 8.4 in
tests/integrations/test_mysql_persistence.py):

* Claiming uses `SELECT ... FOR UPDATE SKIP LOCKED` ordered by
  `next_attempt_at` (indexed). Claimable rows are exactly those with a
  non-NULL `next_attempt_at` in the past: PENDING rows get it at intake,
  RETRY_WAIT rows get the retry time, and PROCESSING rows get their lease
  expiry -- so an abandoned lease becomes claimable with no extra query.
* Every claim writes a fresh random lease token. Completion and failure
  recording re-read the row `FOR UPDATE` and require the same token AND an
  unexpired lease (fencing). A late worker gets `LeaseLost`.
* Completion runs on a connection-level transaction with the session joined in
  `create_savepoint` mode. An HMS write service that calls `db.commit()` on
  that session only releases a SAVEPOINT; the real COMMIT -- domain change,
  SUCCEEDED status and outbox rows together -- happens only after the
  re-fence succeeds. A lost lease therefore rolls the domain change back too.
* Idempotency: unique (client_id, facility_id, idempotency_key). A concurrent
  duplicate insert surfaces as MySQL error 1062 ON THAT CONSTRAINT and is
  resolved by re-reading; any other integrity error (e.g. 1452, unknown
  facility) is raised, never treated as a duplicate.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.integrations.core.envelope import Direction, IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.errors import (
    ErrorCategory,
    IdempotencyConflict,
    InvalidTransition,
    LeaseLost,
    NotFoundInScope,
    PermanentFailure,
)
from app.integrations.core.hashing import canonical_json, idempotency_fingerprint, sha256_hex
from app.integrations.core.lifecycle import assert_transition
from app.integrations.processing.repository import (
    AcceptOutcome,
    AuditEvent,
    Claim,
    CompletionContext,
    IntegrationRepository,
    OutboxClaim,
    OutboxDraft,
    OutboxRecord,
    OutboxStatus,
    StoredMessage,
    blocking_statuses,
    body_bytes_for,
    outbox_dead_letter_audit,
    validate_redrive_reason,
)
from app.integrations.processing.sql_models import (
    AuditEventRow,
    IdempotencyKeyRow,
    InboundMessageRow,
    InboundPayloadRow,
    OutboxMessageRow,
)

#: MySQL reports a duplicate as "... for key '<table>.<index>'". The unique
#: constraint's generated name exceeds MySQL's 64-character identifier limit,
#: so SQLAlchemy truncates it with a hash suffix -- match the table plus the
#: "uq_" prefix instead of the full name. The table's only other unique index
#: is its AUTO_INCREMENT primary key, which cannot collide.
IDEMPOTENCY_KEY_MARKER = "integration_idempotency_keys.uq_"
MYSQL_DUPLICATE_KEY = 1062


def _mysql_errno(exc: IntegrityError) -> int | None:
    args = getattr(getattr(exc, "orig", None), "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def is_idempotency_duplicate(exc: IntegrityError) -> bool:
    """True only for a duplicate on THE idempotency unique key."""
    args = getattr(getattr(exc, "orig", None), "args", ())
    text = str(args[1]) if len(args) > 1 else ""
    return _mysql_errno(exc) == MYSQL_DUPLICATE_KEY and IDEMPOTENCY_KEY_MARKER in text


def _tolerant(enum_cls, value):
    """Enum member when the stored value is valid, else the raw string. Used by
    READ-ONLY views so one corrupt row cannot turn a listing into HTTP 500."""
    try:
        return enum_cls(value)
    except ValueError:
        return value


def _to_view(row: InboundMessageRow) -> StoredMessage:
    """Read-only mapping for operator / dashboard listings (no enum conversion
    failure). The worker path keeps the strict `_to_stored`."""
    return StoredMessage(
        message_id=row.id,
        client_id=row.client_id,
        facility_id=row.facility_id,
        protocol=_tolerant(Protocol, row.protocol),
        direction=_tolerant(Direction, row.direction),
        message_type=row.message_type,
        external_message_id=row.external_message_id,
        idempotency_key=row.idempotency_key,
        ordering_key=row.ordering_key,
        correlation_id=row.correlation_id,
        schema_version=row.schema_version,
        payload_hash=row.payload_hash,
        status=_tolerant(MessageStatus, row.status),
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        next_attempt_at=row.next_attempt_at,
        lease_owner=row.lease_owner,
        lease_expires_at=row.lease_expires_at,
        last_error_code=row.last_error_code,
        last_error_category=row.last_error_category,
        received_at=row.received_on,
        completed_at=row.completed_on,
    )


#: Error code given to a stored row the worker cannot interpret (e.g. an
#: unknown `direction` or `protocol` value written outside the gateway).
INVALID_STORED_RECORD = "invalid_stored_record"


def _to_stored(row: InboundMessageRow) -> StoredMessage:
    return StoredMessage(
        message_id=row.id,
        client_id=row.client_id,
        facility_id=row.facility_id,
        protocol=Protocol(row.protocol),
        direction=Direction(row.direction),
        message_type=row.message_type,
        external_message_id=row.external_message_id,
        idempotency_key=row.idempotency_key,
        ordering_key=row.ordering_key,
        correlation_id=row.correlation_id,
        schema_version=row.schema_version,
        payload_hash=row.payload_hash,
        status=MessageStatus(row.status),
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        next_attempt_at=row.next_attempt_at,
        lease_owner=row.lease_owner,
        lease_expires_at=row.lease_expires_at,
        last_error_code=row.last_error_code,
        last_error_category=row.last_error_category,
        received_at=row.received_on,
        completed_at=row.completed_on,
    )


def _to_outbox(row: OutboxMessageRow) -> OutboxRecord:
    return OutboxRecord(
        outbox_id=row.id,
        source_message_id=row.source_message_id,
        client_id=row.client_id,
        facility_id=row.facility_id,
        protocol=Protocol(row.protocol),
        message_type=row.message_type,
        correlation_id=row.correlation_id,
        payload_hash=row.payload_hash,
        status=row.status,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        next_attempt_at=row.next_attempt_at,
        last_error_code=row.last_error_code,
        created_at=row.created_on,
        sent_at=row.sent_on,
    )


def _to_audit(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        action=row.action,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        facility_id=row.facility_id,
        message_id=row.message_id,
        reason=row.reason,
        detail=row.detail or {},
        occurred_at=row.occurred_on,
    )


class SqlIntegrationRepository(IntegrationRepository):
    def __init__(self, engine: Engine, *, dead_letter_blocks_ordering: bool = True) -> None:
        self._engine = engine
        self._blocking = [str(s) for s in blocking_statuses(dead_letter_blocks_ordering)]

    @contextmanager
    def _tx(self) -> Iterator[Session]:
        with Session(self._engine, expire_on_commit=False) as session:
            with session.begin():
                yield session

    # ---------------------------------------------------------------- intake
    def accept(self, envelope, *, wire_bytes, max_attempts):
        body = body_bytes_for(envelope)
        fingerprint = idempotency_fingerprint(envelope.message_type, envelope.body)
        try:
            return self._accept_once(envelope, body, fingerprint, wire_bytes, max_attempts)
        except IntegrityError as exc:
            if not is_idempotency_duplicate(exc):
                raise PermanentFailure(
                    "The message violates a database constraint.",
                    code="integrity_violation",
                    detail={"mysql_errno": _mysql_errno(exc)},
                ) from None
        # Lost the insert race to a concurrent duplicate: re-read its row.
        with self._tx() as s:
            existing = self._idem_row(s, envelope)
            if existing is None:  # pragma: no cover - would need a concurrent delete
                raise PermanentFailure("Idempotency race could not be resolved.", code="idempotency_race")
            return self._compare(existing, fingerprint)

    @staticmethod
    def _idem_row(s: Session, envelope) -> IdempotencyKeyRow | None:
        return s.execute(
            select(IdempotencyKeyRow).where(
                IdempotencyKeyRow.client_id == envelope.client_id,
                IdempotencyKeyRow.facility_id == envelope.facility_id,
                IdempotencyKeyRow.idempotency_key == envelope.idempotency_key,
            )
        ).scalar_one_or_none()

    @staticmethod
    def _compare(existing: IdempotencyKeyRow, fingerprint: str) -> AcceptOutcome:
        if existing.fingerprint == fingerprint:
            return AcceptOutcome(IntakeOutcome.DUPLICATE, existing.message_id)
        raise IdempotencyConflict(
            "Idempotency key was already used with different content.",
            detail={"message_id": str(existing.message_id)},
        )

    def _accept_once(self, envelope, body, fingerprint, wire_bytes, max_attempts) -> AcceptOutcome:
        with self._tx() as s:
            existing = self._idem_row(s, envelope)
            if existing is not None:
                return self._compare(existing, fingerprint)
            s.add(
                InboundMessageRow(
                    id=envelope.message_id,
                    client_id=envelope.client_id,
                    facility_id=envelope.facility_id,
                    protocol=str(envelope.protocol),
                    direction=str(envelope.direction),
                    message_type=envelope.message_type,
                    external_message_id=envelope.external_message_id,
                    idempotency_key=envelope.idempotency_key,
                    ordering_key=envelope.ordering_key,
                    correlation_id=envelope.correlation_id,
                    schema_version=envelope.schema_version,
                    payload_hash=envelope.payload_hash,
                    status=str(MessageStatus.PENDING),
                    attempt_count=0,
                    max_attempts=max_attempts,
                    next_attempt_at=envelope.received_at,
                    received_on=envelope.received_at,
                )
            )
            s.flush()
            s.add(
                InboundPayloadRow(
                    message_id=envelope.message_id,
                    body_canonical=body.decode("utf-8"),
                    wire_payload=bytes(wire_bytes) if wire_bytes is not None else None,
                )
            )
            s.add(
                IdempotencyKeyRow(
                    client_id=envelope.client_id,
                    facility_id=envelope.facility_id,
                    idempotency_key=envelope.idempotency_key,
                    fingerprint=fingerprint,
                    message_id=envelope.message_id,
                )
            )
            s.flush()
            return AcceptOutcome(IntakeOutcome.ACCEPTED, envelope.message_id)

    # ---------------------------------------------------------------- worker
    def claim(self, *, worker_id, now, lease_seconds, limit):
        expires = now + timedelta(seconds=lease_seconds)
        claims: list[Claim] = []
        with self._tx() as s:
            rows = s.execute(
                select(InboundMessageRow)
                .where(
                    InboundMessageRow.next_attempt_at <= now,
                    InboundMessageRow.status.in_(("PENDING", "RETRY_WAIT", "PROCESSING")),
                    self._not_blocked(),
                )
                .order_by(InboundMessageRow.next_attempt_at, InboundMessageRow.id)
                .limit(limit)
                .with_for_update(skip_locked=True, of=InboundMessageRow)
            ).scalars().all()
            for row in rows:
                try:
                    _to_stored(row)
                except ValueError:
                    # A row the worker cannot interpret (unknown protocol /
                    # direction written outside the gateway) used to raise
                    # here, roll back the WHOLE claim and stall every message
                    # behind it on every poll. Quarantine it explicitly instead:
                    # DEAD_LETTER with a dedicated code, audited, nothing deleted.
                    self._quarantine(s, row, now)
                    continue
                assert_transition(row.status, MessageStatus.PROCESSING)
                token = uuid.uuid4().hex
                row.status = str(MessageStatus.PROCESSING)
                row.attempt_count += 1
                row.lease_owner = worker_id[:96]
                row.lease_token = token
                row.lease_expires_at = expires
                row.next_attempt_at = expires
                s.flush()
                claims.append(Claim(_to_stored(row), token, expires, worker_id))
        return claims

    @staticmethod
    def _quarantine(s: Session, row: InboundMessageRow, now) -> None:
        previous = {"protocol": str(row.protocol)[:16], "direction": str(row.direction)[:16], "status": row.status}
        row.status = str(MessageStatus.DEAD_LETTER)
        row.lease_owner = row.lease_token = None
        row.lease_expires_at = None
        row.next_attempt_at = None
        row.last_error_code = INVALID_STORED_RECORD
        row.last_error_category = str(ErrorCategory.VALIDATION)
        row.completed_on = now
        s.add(AuditEventRow(occurred_on=now, actor_type="system", actor_id=None,
                            action="message.quarantined", facility_id=row.facility_id, message_id=row.id,
                            reason=None, detail={"code": INVALID_STORED_RECORD, "stored": previous}))
        s.flush()

    def _not_blocked(self):
        """No EARLIER unfinished message with the same (client, facility, key).

        The subquery is a non-locking consistent read (MySQL locks subquery
        rows only if the subquery itself says FOR UPDATE) and `OF` limits row
        locks to the claimed table. A predecessor that is PENDING, held by
        another worker or waiting to retry is always seen as unfinished, so
        two workers never run same-key messages at the same time."""
        p = aliased(InboundMessageRow)
        m = InboundMessageRow
        earlier = exists().where(
            p.client_id == m.client_id, p.facility_id == m.facility_id,
            p.ordering_key == m.ordering_key, p.status.in_(self._blocking),
            or_(p.received_on < m.received_on, and_(p.received_on == m.received_on, p.id < m.id)),
        )
        return or_(m.ordering_key.is_(None), ~earlier)

    def load_body(self, message_id):
        with self._tx() as s:
            row = s.get(InboundPayloadRow, message_id)
            if row is None:
                raise PermanentFailure("Message payload is missing.", code="payload_missing")
            return json.loads(row.body_canonical)

    @staticmethod
    def _fenced_row(s: Session, message_id, token, now) -> InboundMessageRow:
        row = s.execute(
            select(InboundMessageRow)
            .where(InboundMessageRow.id == message_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if (
            row is None
            or row.status != str(MessageStatus.PROCESSING)
            or row.lease_token != token
            or row.lease_expires_at is None
            or row.lease_expires_at <= now
        ):
            raise LeaseLost("Worker lease expired or was taken over.")
        return row

    @contextmanager
    def completion(self, claim, *, clock) -> Iterator[CompletionContext]:
        message_id = claim.message.message_id
        with self._engine.connect() as conn:
            outer = conn.begin()
            session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
            try:
                self._fenced_row(session, message_id, claim.lease_token, clock())
                ctx = CompletionContext(session=session)
                yield ctx
                now = clock()
                row = self._fenced_row(session, message_id, claim.lease_token, now)
                for draft in ctx.outbox:
                    self._add_outbox(
                        session, draft,
                        client_id=row.client_id, facility_id=row.facility_id,
                        source_message_id=row.id, max_attempts=row.max_attempts, now=now,
                    )
                for audit in ctx.audits:
                    session.add(AuditEventRow(
                        occurred_on=now, actor_type=audit.actor_type,
                        actor_id=audit.actor_id[:64] if audit.actor_id else None,
                        action=audit.action, facility_id=row.facility_id, message_id=row.id,
                        reason=None, detail=audit.detail or None,
                    ))
                assert_transition(row.status, MessageStatus.SUCCEEDED)
                row.status = str(MessageStatus.SUCCEEDED)
                row.lease_owner = None
                row.lease_token = None
                row.lease_expires_at = None
                row.next_attempt_at = None
                row.last_error_code = None
                row.last_error_category = None
                row.completed_on = now
                session.flush()
                session.commit()  # releases the savepoint (if any)
                outer.commit()    # the real COMMIT
            except BaseException:
                session.rollback()
                if outer.is_active:
                    outer.rollback()
                raise
            finally:
                session.close()

    def record_failure(self, claim, *, now, error, retry_at):
        target = MessageStatus.RETRY_WAIT if retry_at is not None else MessageStatus.DEAD_LETTER
        with self._tx() as s:
            row = self._fenced_row(s, claim.message.message_id, claim.lease_token, now)
            assert_transition(row.status, target)
            row.status = str(target)
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            row.next_attempt_at = retry_at
            row.last_error_code = error.code[:64]
            row.last_error_category = str(error.category)
            row.completed_on = now if target is MessageStatus.DEAD_LETTER else None
        return target

    # ------------------------------------------------------------- operators
    @staticmethod
    def _scope(stmt, column, scope):
        if scope is None:
            return stmt
        if not scope:
            return stmt.where(False)
        return stmt.where(column.in_(list(scope)))

    def get(self, message_id, *, facility_scope):
        with self._tx() as s:
            row = s.execute(
                self._scope(
                    select(InboundMessageRow).where(InboundMessageRow.id == message_id),
                    InboundMessageRow.facility_id,
                    facility_scope,
                )
            ).scalar_one_or_none()
            if row is None:
                raise NotFoundInScope("Message not found.")
            return _to_view(row)

    def list_messages(self, *, facility_scope, statuses=None, limit=50):
        stmt = select(InboundMessageRow)
        if statuses:
            stmt = stmt.where(InboundMessageRow.status.in_([str(x) for x in statuses]))
        stmt = self._scope(stmt, InboundMessageRow.facility_id, facility_scope)
        stmt = stmt.order_by(InboundMessageRow.received_on.desc(), InboundMessageRow.id.desc()).limit(limit)
        with self._tx() as s:
            return [_to_view(r) for r in s.execute(stmt).scalars().all()]

    def redrive(self, message_id, *, facility_scope, actor_id, reason, now):
        reason = validate_redrive_reason(reason)
        with self._tx() as s:
            row = s.execute(
                self._scope(
                    select(InboundMessageRow).where(InboundMessageRow.id == message_id),
                    InboundMessageRow.facility_id,
                    facility_scope,
                ).with_for_update()
            ).scalar_one_or_none()
            if row is None:
                raise NotFoundInScope("Message not found.")
            if row.status != str(MessageStatus.DEAD_LETTER):
                raise InvalidTransition(
                    "Only dead-lettered messages can be redriven.", detail={"status": row.status}
                )
            assert_transition(row.status, MessageStatus.PENDING)
            previous_error = row.last_error_code
            row.status = str(MessageStatus.PENDING)
            row.attempt_count = 0
            row.next_attempt_at = now
            row.completed_on = None
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            s.add(
                AuditEventRow(
                    occurred_on=now,
                    actor_type="user",
                    actor_id=str(actor_id)[:64],
                    action="message.redrive",
                    facility_id=row.facility_id,
                    message_id=row.id,
                    reason=reason,
                    detail={"previous_error_code": previous_error},
                )
            )
            s.flush()
            return _to_view(row)

    def counts_by_status(self, *, facility_scope):
        stmt = select(InboundMessageRow.status, func.count()).group_by(InboundMessageRow.status)
        stmt = self._scope(stmt, InboundMessageRow.facility_id, facility_scope)
        with self._tx() as s:
            return {status: int(n) for status, n in s.execute(stmt).all()}

    def purge_completed(self, *, before, now, batch_size: int = 1000):
        """Deletes in bounded batches so no single transaction holds many locks.
        Payloads and idempotency keys go with their message (ON DELETE CASCADE)."""
        counts = {"inbound": 0, "outbox": 0}
        for model, status, column, key in (
            (OutboxMessageRow, OutboxStatus.SENT, OutboxMessageRow.sent_on, "outbox"),
            (InboundMessageRow, str(MessageStatus.SUCCEEDED), InboundMessageRow.completed_on, "inbound"),
        ):
            while True:
                with self._tx() as s:
                    ids = s.execute(
                        select(model.id).where(model.status == status, column < before)
                        .limit(batch_size).with_for_update(skip_locked=True)
                    ).scalars().all()
                    if not ids:
                        break
                    s.execute(delete(model).where(model.id.in_(ids)))
                    counts[key] += len(ids)
        with self._tx() as s:
            s.add(AuditEventRow(occurred_on=now, actor_type="system", actor_id=None, action="retention.purge",
                                facility_id=None, message_id=None, reason=None,
                                detail={**counts, "before": before.isoformat()}))
        return counts

    def facility_health(self, *, facility_scope, now, window):
        from app.integrations.processing.health import from_sql

        return from_sql(self._engine, scope=facility_scope, now=now, window=window)

    def protocol_activity(self, *, facility_scope):
        from app.integrations.processing.activity import activity_from_sql

        return activity_from_sql(self._engine, scope=facility_scope)

    def backlog(self, *, facility_scope, now):
        from app.integrations.processing.activity import backlog_from_sql

        return backlog_from_sql(self._engine, scope=facility_scope, now=now)

    def metrics(self, query, *, facility_scope):
        from app.integrations.processing.activity import metrics_from_sql

        return metrics_from_sql(self._engine, query, scope=facility_scope)

    def search_messages(self, query, *, facility_scope):
        from app.integrations.processing.activity import search_sql

        # Read-only listing: tolerant mapping, so one corrupt row cannot turn
        # the dashboard's message search into HTTP 500.
        return search_sql(self._engine, query, scope=facility_scope, to_stored=_to_view)

    # ----------------------------------------------------------------- outbox
    @staticmethod
    def _add_outbox(s, draft: OutboxDraft, *, client_id, facility_id, source_message_id, max_attempts, now):
        body = canonical_json(draft.body)
        outbox_id = uuid.uuid4()
        s.add(
            OutboxMessageRow(
                id=outbox_id,
                source_message_id=source_message_id,
                client_id=client_id,
                facility_id=facility_id,
                protocol=str(draft.protocol),
                message_type=draft.message_type,
                correlation_id=draft.correlation_id or uuid.uuid4().hex,
                body_canonical=body.decode("utf-8"),
                payload_hash=sha256_hex(body),
                status=OutboxStatus.PENDING,
                attempt_count=0,
                max_attempts=max_attempts,
                next_attempt_at=now,
                created_on=now,
            )
        )
        return outbox_id

    def enqueue_outbox(self, draft, *, client_id, facility_id, source_message_id, max_attempts, now):
        with self._tx() as s:
            outbox_id = self._add_outbox(
                s, draft, client_id=client_id, facility_id=facility_id,
                source_message_id=source_message_id, max_attempts=max_attempts, now=now,
            )
            s.flush()
        return outbox_id

    def claim_outbox(self, *, worker_id, now, lease_seconds, limit, protocols=None):
        expires = now + timedelta(seconds=lease_seconds)
        claims: list[OutboxClaim] = []
        conditions = [
            OutboxMessageRow.next_attempt_at <= now,
            OutboxMessageRow.status.in_(("PENDING", "RETRY_WAIT", "PROCESSING")),
        ]
        if protocols is not None:
            if not protocols:
                return []
            conditions.append(OutboxMessageRow.protocol.in_(sorted(str(p) for p in protocols)))
        with self._tx() as s:
            rows = s.execute(
                select(OutboxMessageRow)
                .where(*conditions)
                .order_by(OutboxMessageRow.next_attempt_at, OutboxMessageRow.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).scalars().all()
            for row in rows:
                token = uuid.uuid4().hex
                row.status = OutboxStatus.PROCESSING
                row.attempt_count += 1
                row.lease_owner = worker_id[:96]
                row.lease_token = token
                row.lease_expires_at = expires
                row.next_attempt_at = expires
                s.flush()
                claims.append(OutboxClaim(_to_outbox(row), token, expires, worker_id))
        return claims

    def load_outbox_body(self, outbox_id):
        with self._tx() as s:
            row = s.get(OutboxMessageRow, outbox_id)
            if row is None:
                raise PermanentFailure("Outbox message is missing.", code="outbox_missing")
            return json.loads(row.body_canonical)

    @staticmethod
    def _fenced_outbox(s: Session, claim: OutboxClaim, now) -> OutboxMessageRow:
        row = s.execute(
            select(OutboxMessageRow)
            .where(OutboxMessageRow.id == claim.record.outbox_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if (
            row is None
            or row.status != OutboxStatus.PROCESSING
            or row.lease_token != claim.lease_token
            or row.lease_expires_at is None
            or row.lease_expires_at <= now
        ):
            raise LeaseLost("Outbox lease expired or was taken over.")
        return row

    def mark_outbox_sent(self, claim, *, now):
        with self._tx() as s:
            row = self._fenced_outbox(s, claim, now)
            row.status = OutboxStatus.SENT
            row.sent_on = now
            row.next_attempt_at = None
            row.lease_owner = row.lease_token = None
            row.lease_expires_at = None
            row.last_error_code = None

    def record_outbox_failure(self, claim, *, now, error, retry_at):
        status = OutboxStatus.RETRY_WAIT if retry_at is not None else OutboxStatus.DEAD_LETTER
        with self._tx() as s:
            row = self._fenced_outbox(s, claim, now)
            row.status = status
            row.next_attempt_at = retry_at
            row.lease_owner = row.lease_token = None
            row.lease_expires_at = None
            row.last_error_code = error.code[:64]
            if status == OutboxStatus.DEAD_LETTER:
                # Same transaction as the status change (the trail cannot disagree).
                ev = outbox_dead_letter_audit(_to_outbox(row), error, now)
                s.add(AuditEventRow(occurred_on=now, actor_type=ev.actor_type, actor_id=None, action=ev.action,
                                    facility_id=ev.facility_id, message_id=ev.message_id, reason=None,
                                    detail=ev.detail))
        return status

    def list_outbox(self, *, facility_scope, statuses=None, limit=50):
        stmt = select(OutboxMessageRow)
        if statuses:
            stmt = stmt.where(OutboxMessageRow.status.in_(list(statuses)))
        stmt = self._scope(stmt, OutboxMessageRow.facility_id, facility_scope)
        stmt = stmt.order_by(OutboxMessageRow.created_on.desc(), OutboxMessageRow.id.desc()).limit(limit)
        with self._tx() as s:
            return [_to_outbox(r) for r in s.execute(stmt).scalars().all()]

    # ------------------------------------------------------------------ audit
    def record_audit(self, event: AuditEvent) -> None:
        with self._tx() as s:
            s.add(
                AuditEventRow(
                    occurred_on=event.occurred_at,
                    actor_type=event.actor_type,
                    actor_id=event.actor_id[:64] if event.actor_id else None,
                    action=event.action,
                    facility_id=event.facility_id,
                    message_id=event.message_id,
                    reason=event.reason,
                    detail=event.detail or None,
                )
            )

    def list_audit(self, *, facility_scope, limit=50):
        stmt = select(AuditEventRow)
        stmt = self._scope(stmt, AuditEventRow.facility_id, facility_scope)
        stmt = stmt.order_by(AuditEventRow.id.desc()).limit(limit)
        with self._tx() as s:
            return [_to_audit(r) for r in s.execute(stmt).scalars().all()]

    # -------------------------------------------------------------- diagnostics
    def stored_wire_bytes(self, message_id: uuid.UUID) -> bytes | None:
        with self._tx() as s:
            row = s.get(InboundPayloadRow, message_id)
            return row.wire_payload if row else None


def table_presence(engine: Engine) -> dict[str, bool]:
    """Which integration tables exist -- used by readiness, never creates them."""
    from sqlalchemy import inspect

    from app.integrations.processing.sql_models import INTEGRATION_TABLES

    names = set(inspect(engine).get_table_names())
    return {t.name: t.name in names for t in INTEGRATION_TABLES}


__all__ = ["SqlIntegrationRepository", "table_presence", "is_idempotency_duplicate", "Any"]
