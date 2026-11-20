"""Durable-processing contract, run against BOTH repositories (memory, MySQL).

Covers lifecycle, idempotency, leases/fencing, retry, DLQ, redrive, outbox
atomicity, restart recovery and facility scoping.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.integrations.core.envelope import IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.errors import (
    IdempotencyConflict,
    InvalidTransition,
    LeaseLost,
    NotFoundInScope,
    TransientFailure,
    ValidationFailed,
)
from app.integrations.core.hashing import payload_hash
from app.integrations.processing.repository import AuditEvent, OutboxDraft

from .conftest import CLIENT_A, CLIENT_B, FACILITY_A, FACILITY_B, T0, make_envelope


def clock_at(t):
    return lambda: t


def accept(repo, **kw):
    return repo.accept(make_envelope(**kw), wire_bytes=None, max_attempts=3)


# --- intake / idempotency ---------------------------------------------------------
def test_accept_persists_pending_with_body(repo):
    out = accept(repo, body={"room": "101", "nested": {"b": 2, "a": 1}})
    assert out.outcome is IntakeOutcome.ACCEPTED
    msg = repo.get(out.message_id, facility_scope=None)
    assert msg.status is MessageStatus.PENDING and msg.attempt_count == 0 and msg.next_attempt_at == T0
    body = repo.load_body(out.message_id)
    assert body == {"room": "101", "nested": {"a": 1, "b": 2}}
    assert payload_hash(body) == msg.payload_hash  # hash stable after storage


def test_duplicate_and_conflict(repo):
    first = accept(repo, key="k")
    dup = accept(repo, key="k")
    assert dup.outcome is IntakeOutcome.DUPLICATE and dup.message_id == first.message_id
    with pytest.raises(IdempotencyConflict):
        accept(repo, key="k", body={"room": "999"})
    assert len(repo.list_messages(facility_scope=None)) == 1


def test_idempotency_scoped_by_client_and_facility(repo):
    a = accept(repo, key="k", facility=FACILITY_A, client=CLIENT_A)
    b = accept(repo, key="k", facility=FACILITY_B, client=CLIENT_A)
    c = accept(repo, key="k", facility=FACILITY_A, client=CLIENT_B)
    assert len({a.message_id, b.message_id, c.message_id}) == 3
    assert all(x.outcome is IntakeOutcome.ACCEPTED for x in (a, b, c))


def test_envelope_hash_mismatch_rejected(repo):
    env = make_envelope().model_copy(update={"payload_hash": "0" * 64})
    with pytest.raises(ValidationFailed):
        repo.accept(env, wire_bytes=None, max_attempts=3)


# --- claiming / leases ---------------------------------------------------------
def test_claim_sets_lease_and_is_exclusive(repo):
    accept(repo, key="1")
    accept(repo, key="2")
    c1 = repo.claim(worker_id="w1", now=T0, lease_seconds=30, limit=1)
    c2 = repo.claim(worker_id="w2", now=T0, lease_seconds=30, limit=10)
    assert len(c1) == 1 and len(c2) == 1
    assert c1[0].message.message_id != c2[0].message.message_id
    assert c1[0].message.status is MessageStatus.PROCESSING and c1[0].message.attempt_count == 1
    assert repo.claim(worker_id="w3", now=T0, lease_seconds=30, limit=10) == []


def test_not_due_messages_are_not_claimed(repo):
    accept(repo, key="1", received_at=T0 + timedelta(minutes=5))
    assert repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=10) == []


def test_completion_marks_succeeded_with_outbox_atomically(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with repo.completion(claim, clock=clock_at(T0 + timedelta(seconds=5))) as ctx:
        ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {"ok": True}, "c"))
    msg = repo.get(claim.message.message_id, facility_scope=None)
    assert msg.status is MessageStatus.SUCCEEDED and msg.next_attempt_at is None and msg.lease_owner is None
    out = repo.list_outbox(facility_scope=None)
    assert len(out) == 1 and out[0].source_message_id == msg.message_id and out[0].facility_id == FACILITY_A
    assert repo.claim(worker_id="w", now=T0 + timedelta(hours=1), lease_seconds=30, limit=10) == []


def test_handler_exception_leaves_no_outbox_and_no_status_change(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with pytest.raises(RuntimeError):
        with repo.completion(claim, clock=clock_at(T0)) as ctx:
            ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
            raise RuntimeError("handler blew up")
    assert repo.list_outbox(facility_scope=None) == []
    assert repo.get(claim.message.message_id, facility_scope=None).status is MessageStatus.PROCESSING


def test_expired_worker_cannot_commit(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with pytest.raises(LeaseLost):
        with repo.completion(claim, clock=clock_at(T0 + timedelta(seconds=31))):
            pass
    with pytest.raises(LeaseLost):
        repo.record_failure(claim, now=T0 + timedelta(seconds=31), error=TransientFailure("x"), retry_at=None)


def test_handler_overrunning_lease_is_fenced_at_commit_and_outbox_discarded(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    times = iter([T0, T0 + timedelta(seconds=45)])
    with pytest.raises(LeaseLost):
        with repo.completion(claim, clock=lambda: next(times)) as ctx:
            ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
    assert repo.list_outbox(facility_scope=None) == []


def test_takeover_after_lease_expiry_fences_the_old_worker(repo):
    accept(repo)
    old = repo.claim(worker_id="old", now=T0, lease_seconds=30, limit=1)[0]
    later = T0 + timedelta(seconds=31)
    new = repo.claim(worker_id="new", now=later, lease_seconds=30, limit=1)[0]  # restart recovery
    assert new.message.message_id == old.message.message_id and new.message.attempt_count == 2
    with pytest.raises(LeaseLost):
        with repo.completion(old, clock=clock_at(later)):
            pass
    with repo.completion(new, clock=clock_at(later)):
        pass
    assert repo.get(new.message.message_id, facility_scope=None).status is MessageStatus.SUCCEEDED


# --- retry / DLQ / redrive ---------------------------------------------------------
def test_retry_wait_then_reclaim(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    retry_at = T0 + timedelta(seconds=60)
    status = repo.record_failure(claim, now=T0, error=TransientFailure("down"), retry_at=retry_at)
    assert status is MessageStatus.RETRY_WAIT
    msg = repo.get(claim.message.message_id, facility_scope=None)
    assert msg.next_attempt_at == retry_at and msg.last_error_code == "transient_failure"
    assert repo.claim(worker_id="w", now=T0 + timedelta(seconds=59), lease_seconds=30, limit=1) == []
    again = repo.claim(worker_id="w", now=retry_at, lease_seconds=30, limit=1)
    assert again[0].message.attempt_count == 2


def test_dead_letter_and_authorised_redrive(repo):
    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    repo.record_failure(claim, now=T0, error=TransientFailure("x"), retry_at=None)
    msg = repo.get(claim.message.message_id, facility_scope=None)
    assert msg.status is MessageStatus.DEAD_LETTER and msg.completed_at == T0
    assert repo.claim(worker_id="w", now=T0 + timedelta(days=1), lease_seconds=30, limit=10) == []

    with pytest.raises(ValidationFailed):
        repo.redrive(msg.message_id, facility_scope={FACILITY_A}, actor_id="u1", reason="  short ", now=T0)
    with pytest.raises(NotFoundInScope):
        repo.redrive(msg.message_id, facility_scope={FACILITY_B}, actor_id="u1", reason="vendor fixed data", now=T0)

    later = T0 + timedelta(minutes=5)
    redriven = repo.redrive(msg.message_id, facility_scope={FACILITY_A}, actor_id="u1",
                            reason="vendor fixed data", now=later)
    assert redriven.status is MessageStatus.PENDING and redriven.attempt_count == 0
    audit = repo.list_audit(facility_scope={FACILITY_A})
    assert audit[0].action == "message.redrive" and audit[0].actor_id == "u1"
    assert audit[0].reason == "vendor fixed data" and audit[0].message_id == msg.message_id
    assert repo.list_audit(facility_scope={FACILITY_B}) == []
    assert repo.claim(worker_id="w", now=later, lease_seconds=30, limit=1)[0].message.message_id == msg.message_id


def test_only_dead_letters_can_be_redriven(repo):
    out = accept(repo)
    with pytest.raises(InvalidTransition):
        repo.redrive(out.message_id, facility_scope={FACILITY_A}, actor_id="u", reason="not allowed now", now=T0)


# --- scoping / listing ---------------------------------------------------------
def test_listing_and_counts_are_facility_scoped(repo):
    accept(repo, key="a1")
    accept(repo, key="a2")
    accept(repo, key="b1", facility=FACILITY_B, client=CLIENT_B)
    assert len(repo.list_messages(facility_scope={FACILITY_A})) == 2
    assert len(repo.list_messages(facility_scope={FACILITY_B})) == 1
    assert repo.list_messages(facility_scope=set()) == []
    assert repo.counts_by_status(facility_scope={FACILITY_A}) == {"PENDING": 2}
    assert len(repo.list_messages(facility_scope=None, statuses={MessageStatus.DEAD_LETTER})) == 0
    with pytest.raises(NotFoundInScope):
        repo.get(repo.list_messages(facility_scope={FACILITY_B})[0].message_id, facility_scope={FACILITY_A})


# --- outbox ---------------------------------------------------------------
def test_outbox_claim_send_and_fencing(repo):
    oid = repo.enqueue_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {"x": 1}, "c"), client_id=CLIENT_A,
                              facility_id=FACILITY_A, source_message_id=None, max_attempts=3, now=T0)
    c = repo.claim_outbox(worker_id="r", now=T0, lease_seconds=30, limit=5)
    assert len(c) == 1 and c[0].record.outbox_id == oid
    assert repo.claim_outbox(worker_id="r2", now=T0, lease_seconds=30, limit=5) == []
    assert repo.load_outbox_body(oid) == {"x": 1}
    with pytest.raises(LeaseLost):
        repo.mark_outbox_sent(c[0], now=T0 + timedelta(seconds=31))
    c2 = repo.claim_outbox(worker_id="r2", now=T0 + timedelta(seconds=31), lease_seconds=30, limit=5)[0]
    with pytest.raises(LeaseLost):
        repo.mark_outbox_sent(c[0], now=T0 + timedelta(seconds=31))
    repo.mark_outbox_sent(c2, now=T0 + timedelta(seconds=32))
    rec = repo.list_outbox(facility_scope={FACILITY_A})[0]
    assert rec.status == "SENT" and rec.attempt_count == 2
    assert repo.list_outbox(facility_scope={FACILITY_B}) == []


def test_outbox_failure_retry_and_dead_letter(repo):
    repo.enqueue_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None), client_id=CLIENT_A,
                        facility_id=FACILITY_A, source_message_id=None, max_attempts=3, now=T0)
    c = repo.claim_outbox(worker_id="r", now=T0, lease_seconds=30, limit=1)[0]
    assert repo.record_outbox_failure(c, now=T0, error=TransientFailure("x"), retry_at=T0 + timedelta(seconds=5)) == "RETRY_WAIT"
    c = repo.claim_outbox(worker_id="r", now=T0 + timedelta(seconds=5), lease_seconds=30, limit=1)[0]
    assert repo.record_outbox_failure(c, now=T0, error=TransientFailure("x"), retry_at=None) == "DEAD_LETTER"
    assert repo.list_outbox(facility_scope=None, statuses={"DEAD_LETTER"})[0].last_error_code == "transient_failure"


def test_audit_records_are_metadata_only(repo):
    repo.record_audit(AuditEvent("client.authentication_failed", "client", "pms-x", None, None, None,
                                 {"reason": "invalid_secret"}, T0))
    events = repo.list_audit(facility_scope=None)
    assert events[0].detail == {"reason": "invalid_secret"}
    assert repo.list_audit(facility_scope={FACILITY_A}) == []


def test_handler_audit_is_written_atomically_with_success(repo):
    from app.integrations.processing.repository import AuditDraft

    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with repo.completion(claim, clock=clock_at(T0)) as ctx:
        ctx.add_audit(AuditDraft("domain.stay.check_in", "system", "actor-1", {"stay_id": "s"}))
    (event,) = repo.list_audit(facility_scope={FACILITY_A})
    assert event.action == "domain.stay.check_in" and event.message_id == claim.message.message_id
    assert event.facility_id == FACILITY_A and event.detail == {"stay_id": "s"}


def test_handler_audit_is_discarded_with_lost_lease(repo):
    from app.integrations.processing.repository import AuditDraft

    accept(repo)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    times = iter([T0, T0 + timedelta(seconds=60)])
    with pytest.raises(LeaseLost):
        with repo.completion(claim, clock=lambda: next(times)) as ctx:
            ctx.add_audit(AuditDraft("domain.stay.check_in", "system", None, {}))
    assert repo.list_audit(facility_scope=None) == []
