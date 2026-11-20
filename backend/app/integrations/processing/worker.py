"""Inbound worker and outbox relay.

InboundWorker.run_once():
    claim due messages (lease + token) -> for each:
        open fenced completion -> dispatch -> handler writes on the fenced
        session + emits outbox drafts -> completion re-fences and marks
        SUCCEEDED atomically with the outbox rows
    on failure: classify -> RetryPolicy -> RETRY_WAIT or DEAD_LETTER (fenced)
    on LeaseLost: drop the result (another worker owns the message now)

TRANSACTIONAL COUPLING WITH HMS SERVICES. The existing HMS write services
(e.g. app/services/stays_write.py) commit inside `transaction(db)`. When a
domain adapter calls one with the fenced session, that commit also commits the
staged SUCCEEDED status and outbox rows -- so the domain change, the status
and the outbox land together -- and a failure rolls all of them back. The
fence row lock is held until that commit, so no other worker can re-claim the
message meanwhile.

Restart recovery needs no special code: a message left PROCESSING by a dead
worker becomes claimable once its lease expires.
"""

from __future__ import annotations

import logging
import socket
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.integrations.core.correlation import correlation_scope
from app.integrations.core.envelope import CanonicalEnvelope, Direction, MessageStatus, OutboundRequest, utcnow
from app.integrations.core.errors import IntegrationError, LeaseLost, classify
from app.integrations.core.retry import RetryPolicy
from app.integrations.exchange.dispatcher import MessageDispatcher
from app.integrations.exchange.registry import AdapterRegistry, HandlerContext
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.repository import Claim, IntegrationRepository, OutboxClaim

logger = logging.getLogger("hms.integrations.worker")


def default_worker_id(prefix: str = "worker") -> str:
    return f"{prefix}:{socket.gethostname()[:32]}:{uuid.uuid4().hex[:8]}"


@dataclass
class RunSummary:
    claimed: int = 0
    succeeded: int = 0
    retried: int = 0
    dead_lettered: int = 0
    lease_lost: int = 0
    unrecorded: int = 0


def envelope_from_claim(claim: Claim, body: dict) -> CanonicalEnvelope:
    m = claim.message
    return CanonicalEnvelope(
        message_id=m.message_id,
        external_message_id=m.external_message_id,
        idempotency_key=m.idempotency_key,
        ordering_key=m.ordering_key,
        correlation_id=m.correlation_id,
        facility_id=m.facility_id,
        client_id=m.client_id,
        protocol=m.protocol,
        message_type=m.message_type,
        direction=m.direction,
        schema_version=m.schema_version,
        received_at=m.received_at,
        payload_hash=m.payload_hash,
        status=MessageStatus.PROCESSING,
        retry_count=max(0, m.attempt_count - 1),
        body=body,
    )


class InboundWorker:
    def __init__(
        self,
        *,
        repository: IntegrationRepository,
        dispatcher: MessageDispatcher,
        policy: RetryPolicy,
        worker_id: str | None = None,
        lease_seconds: int = 60,
        clock: Callable[[], datetime] = utcnow,
        metrics: IntegrationMetrics | None = None,
    ) -> None:
        self._repo = repository
        self._dispatcher = dispatcher
        self._policy = policy
        self.worker_id = worker_id or default_worker_id("inbound")
        self._lease_seconds = lease_seconds
        self._clock = clock
        self._metrics = metrics or IntegrationMetrics()

    def run_once(self, *, limit: int = 10) -> RunSummary:
        summary = RunSummary()
        now = self._clock()
        self._metrics.heartbeat("inbound_worker", now)
        claims = self._repo.claim(
            worker_id=self.worker_id, now=now, lease_seconds=self._lease_seconds, limit=limit
        )
        summary.claimed = len(claims)
        for claim in claims:
            self._process(claim, summary)
        return summary

    def _process(self, claim: Claim, summary: RunSummary) -> None:
        msg = claim.message
        with correlation_scope(msg.correlation_id):
            try:
                body = self._repo.load_body(msg.message_id)
                envelope = envelope_from_claim(claim, body)
                with self._repo.completion(claim, clock=self._clock) as completion:
                    ctx = HandlerContext(session=completion.session)
                    self._dispatcher.dispatch(envelope, ctx)
                    for draft in ctx.outbox:
                        completion.add_outbox(draft)
                    for audit in ctx.audits:
                        completion.add_audit(audit)
                summary.succeeded += 1
                self._metrics.inc("processed_succeeded", message_type=msg.message_type)
                return
            except LeaseLost:
                summary.lease_lost += 1
                self._metrics.inc("lease_lost", message_type=msg.message_type)
                logger.warning("lease lost message_id=%s worker=%s", msg.message_id, self.worker_id)
                return
            except Exception as exc:  # noqa: BLE001
                error = classify(exc)

            self._fail(claim, error, summary)

    def _fail(self, claim: Claim, error: IntegrationError, summary: RunSummary) -> None:
        msg = claim.message
        now = self._clock()
        decision = self._policy.decide(error, attempts_made=msg.attempt_count, now=now)
        if decision.retry and msg.attempt_count >= msg.max_attempts:
            decision = type(decision)(False, None, "max_attempts_exhausted")
        try:
            status = self._repo.record_failure(
                claim, now=now, error=error, retry_at=decision.next_attempt_at if decision.retry else None
            )
        except LeaseLost:
            summary.lease_lost += 1
            self._metrics.inc("lease_lost", message_type=msg.message_type)
            return
        except Exception as exc:  # noqa: BLE001 - e.g. database unavailable
            # The outcome could not be recorded. The message stays PROCESSING
            # and is re-claimed when its lease expires -- delayed, never lost.
            # Do not abort the rest of the batch.
            summary.unrecorded += 1
            self._metrics.inc("failure_unrecorded", type=type(exc).__name__)
            logger.warning("could not record failure message_id=%s type=%s; lease expiry will recover it",
                           msg.message_id, type(exc).__name__)
            return
        if status is MessageStatus.RETRY_WAIT:
            summary.retried += 1
            self._metrics.inc("processed_retry", message_type=msg.message_type, code=error.code)
        else:
            summary.dead_lettered += 1
            self._metrics.inc("processed_dead_letter", message_type=msg.message_type, code=error.code)
        logger.info(
            "message failed message_id=%s code=%s category=%s -> %s (%s)",
            msg.message_id, error.code, error.category, status, decision.reason,
        )


class OutboundSender:
    """Delivers encoded bytes to a vendor. Implemented per transport."""

    def send(self, payload: bytes, *, claim: OutboxClaim) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class OutboxRelay:
    def __init__(
        self,
        *,
        repository: IntegrationRepository,
        adapters: AdapterRegistry,
        senders: dict,
        policy: RetryPolicy,
        worker_id: str | None = None,
        lease_seconds: int = 60,
        clock: Callable[[], datetime] = utcnow,
        metrics: IntegrationMetrics | None = None,
    ) -> None:
        self._repo = repository
        self._adapters = adapters
        self._senders = senders
        self._policy = policy
        self.worker_id = worker_id or default_worker_id("outbox")
        self._lease_seconds = lease_seconds
        self._clock = clock
        self._metrics = metrics or IntegrationMetrics()

    def run_once(self, *, limit: int = 10) -> RunSummary:
        summary = RunSummary()
        now = self._clock()
        self._metrics.heartbeat("outbox_relay", now)
        # Claim only rows this relay can deliver. A row of a protocol without a
        # sender stays PENDING (visible as "queued, no sender") instead of being
        # dead-lettered with sender_not_configured.
        claims = self._repo.claim_outbox(
            worker_id=self.worker_id, now=now, lease_seconds=self._lease_seconds, limit=limit,
            protocols=frozenset(str(p) for p in self._senders),
        )
        summary.claimed = len(claims)
        for claim in claims:
            rec = claim.record
            try:
                body = self._repo.load_outbox_body(rec.outbox_id)
                adapter = self._adapters.get(rec.protocol, Direction.OUTBOUND)
                sender = self._senders.get(rec.protocol)
                if sender is None:
                    raise IntegrationError(
                        "No outbound sender is configured for this protocol.",
                        code="sender_not_configured",
                    )
                payload = adapter.encode(
                    OutboundRequest(
                        protocol=rec.protocol,
                        message_type=rec.message_type,
                        facility_id=rec.facility_id,
                        client_id=rec.client_id,
                        correlation_id=rec.correlation_id,
                        source_message_id=rec.source_message_id,
                        body=body,
                    )
                )
                sender.send(payload, claim=claim)
                self._repo.mark_outbox_sent(claim, now=self._clock())
                summary.succeeded += 1
                self._metrics.inc("outbox_sent", protocol=str(rec.protocol))
            except LeaseLost:
                summary.lease_lost += 1
            except Exception as exc:  # noqa: BLE001
                error = classify(exc)
                now = self._clock()
                decision = self._policy.decide(error, attempts_made=rec.attempt_count, now=now)
                if decision.retry and rec.attempt_count >= rec.max_attempts:
                    decision = type(decision)(False, None, "max_attempts_exhausted")
                try:
                    status = self._repo.record_outbox_failure(
                        claim, now=now, error=error,
                        retry_at=decision.next_attempt_at if decision.retry else None,
                    )
                except LeaseLost:
                    summary.lease_lost += 1
                    continue
                if decision.retry:
                    summary.retried += 1
                else:
                    summary.dead_lettered += 1
                self._metrics.inc("outbox_failed", protocol=str(rec.protocol), status=status, code=error.code)
        return summary
