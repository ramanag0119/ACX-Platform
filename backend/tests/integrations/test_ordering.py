"""Per-entity ordering, on BOTH repositories (memory, disposable MySQL)."""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest

from app.integrations.core.envelope import MessageStatus, Protocol
from app.integrations.core.errors import PermanentFailure, TransientFailure
from app.integrations.domain.stays import CHECK_IN, StayEventHandler

from .conftest import CTX, FACILITY_A, T0, build_stack, json_msg, make_envelope


def env(key, ordering, *, at=0, facility=FACILITY_A):
    e = make_envelope(key=key, facility=facility, received_at=T0 + timedelta(microseconds=at))
    return e.model_copy(update={"ordering_key": ordering})


def ids(claims):
    return [c.message.idempotency_key for c in claims]


def test_later_same_key_waits_for_earlier(repo):
    for i, k in enumerate(["a1", "a2", "a3"]):
        repo.accept(env(k, "stay:1", at=i), wire_bytes=None, max_attempts=3)
    repo.accept(env("b1", "stay:2", at=5), wire_bytes=None, max_attempts=3)
    repo.accept(env("n1", None, at=6), wire_bytes=None, max_attempts=3)
    first = repo.claim(worker_id="w", now=T0 + timedelta(seconds=1), lease_seconds=30, limit=10)
    assert sorted(ids(first)) == ["a1", "b1", "n1"]  # one per key, unordered ones free
    assert repo.claim(worker_id="w2", now=T0 + timedelta(seconds=1), lease_seconds=30, limit=10) == []
    a1 = next(c for c in first if c.message.idempotency_key == "a1")
    with repo.completion(a1, clock=lambda: T0 + timedelta(seconds=2)):
        pass
    assert ids(repo.claim(worker_id="w", now=T0 + timedelta(seconds=2), lease_seconds=30, limit=10)) == ["a2"]


def test_retry_wait_predecessor_blocks(repo):
    repo.accept(env("a1", "k", at=0), wire_bytes=None, max_attempts=3)
    repo.accept(env("a2", "k", at=1), wire_bytes=None, max_attempts=3)
    (c1,) = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=10)
    repo.record_failure(c1, now=T0, error=TransientFailure("x"), retry_at=T0 + timedelta(seconds=60))
    assert repo.claim(worker_id="w", now=T0 + timedelta(seconds=30), lease_seconds=30, limit=10) == []
    assert ids(repo.claim(worker_id="w", now=T0 + timedelta(seconds=60), lease_seconds=30, limit=10)) == ["a1"]


def test_dead_letter_blocks_until_redrive(repo):
    repo.accept(env("a1", "k", at=0), wire_bytes=None, max_attempts=3)
    repo.accept(env("a2", "k", at=1), wire_bytes=None, max_attempts=3)
    (c1,) = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=10)
    repo.record_failure(c1, now=T0, error=PermanentFailure("x"), retry_at=None)
    assert repo.claim(worker_id="w", now=T0 + timedelta(hours=1), lease_seconds=30, limit=10) == []
    repo.redrive(c1.message.message_id, facility_scope={FACILITY_A}, actor_id="u",
                 reason="fixed upstream data", now=T0 + timedelta(hours=1))
    assert ids(repo.claim(worker_id="w", now=T0 + timedelta(hours=1), lease_seconds=30, limit=10)) == ["a1"]


def test_same_key_other_facility_is_independent(repo):
    from .conftest import CLIENT_A, FACILITY_B  # noqa: F401

    repo.accept(env("a1", "k", at=0), wire_bytes=None, max_attempts=3)
    repo.accept(env("b1", "k", at=1, facility=FACILITY_B), wire_bytes=None, max_attempts=3)
    assert sorted(ids(repo.claim(worker_id="w", now=T0 + timedelta(seconds=1), lease_seconds=30, limit=10))) == ["a1", "b1"]


def test_expired_lease_predecessor_is_reclaimed_before_successor(repo):
    repo.accept(env("a1", "k", at=0), wire_bytes=None, max_attempts=3)
    repo.accept(env("a2", "k", at=1), wire_bytes=None, max_attempts=3)
    repo.claim(worker_id="dead", now=T0, lease_seconds=30, limit=1)
    later = repo.claim(worker_id="w", now=T0 + timedelta(seconds=31), lease_seconds=30, limit=10)
    assert ids(later) == ["a1"]


def test_unblocking_dead_letter_policy_can_be_relaxed():
    from app.integrations.processing.repository import InMemoryIntegrationRepository

    repo = InMemoryIntegrationRepository(dead_letter_blocks_ordering=False)
    repo.accept(env("a1", "k", at=0), wire_bytes=None, max_attempts=3)
    repo.accept(env("a2", "k", at=1), wire_bytes=None, max_attempts=3)
    (c1,) = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=10)
    repo.record_failure(c1, now=T0, error=PermanentFailure("x"), retry_at=None)
    assert ids(repo.claim(worker_id="w", now=T0 + timedelta(seconds=1), lease_seconds=30, limit=10)) == ["a2"]


def test_concurrent_workers_never_run_same_key_together(repo):
    for i in range(12):
        repo.accept(env(f"m{i:02d}", f"k{i % 3}", at=i), wire_bytes=None, max_attempts=3)
    running: dict[str, str] = {}
    order: list[str] = []
    lock = threading.Lock()
    errors: list[str] = []

    def worker(n):
        for _ in range(40):
            claims = repo.claim(worker_id=f"w{n}", now=T0 + timedelta(seconds=1), lease_seconds=30, limit=2)
            if not claims and len(order) >= 12:
                return
            for c in claims:
                key = c.message.ordering_key
                with lock:
                    if key in running:
                        errors.append(f"{key} ran concurrently")
                    running[key] = c.message.idempotency_key
                with repo.completion(c, clock=lambda: T0 + timedelta(seconds=2)):
                    pass
                with lock:
                    running.pop(key, None)
                    order.append(c.message.idempotency_key)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(order) == 12
    for k in range(3):
        per_key = [m for m in order if int(m[1:]) % 3 == k]
        assert per_key == sorted(per_key)


# --- gateway / handler wiring ---------------------------------------------------------
def test_gateway_stamps_ordering_key_from_handler(stack):
    stack.handlers["test.guest_arrival"].ordered_by = "room"
    r = stack.gateway.receive(json_msg("o1", body={"room": "101"}), protocol=Protocol.TEST,
                              client=stack.auth(), context=CTX)
    assert stack.repo.get(r.message_id, facility_scope=None).ordering_key == "room:101"


def test_worker_processes_same_room_in_arrival_order_across_failures():
    s = build_stack()
    h = s.handlers["test.guest_arrival"]
    h.ordered_by = "room"
    h.failures.append(TransientFailure("first attempt fails"))
    for i in range(3):
        s.clock.advance(0.001)
        s.gateway.receive(json_msg(f"r{i}", body={"room": "101", "n": i}), protocol=Protocol.TEST,
                          client=s.auth(), context=CTX)
    for _ in range(10):
        s.worker.run_once()
        s.clock.advance(15)
    assert [e.body["n"] for e in h.seen] == [0, 0, 1, 2]
    assert all(m.status is MessageStatus.SUCCEEDED for m in s.repo.list_messages(facility_scope=None))


@pytest.mark.parametrize("body,expected", [
    ({"external_stay_ref": "PMS-1"}, "stay:PMS-1"),
    ({"external_stay_ref": "  PMS-1 "}, "stay:PMS-1"),
    ({"external_stay_ref": ""}, None),
    ({}, None),
])
def test_stay_handler_orders_by_stay_reference(body, expected):
    assert StayEventHandler(CHECK_IN, adapter=None).ordering_key(body) == expected
