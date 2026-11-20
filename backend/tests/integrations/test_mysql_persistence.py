"""MySQL-specific persistence behaviour (DISPOSABLE database only).

Skipped unless INTEGRATION_TEST_MYSQL_URL is set; refuses the HMS database name.
"""

from __future__ import annotations

import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.integrations.core.envelope import IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.errors import LeaseLost, PermanentFailure
from app.integrations.core.hashing import payload_hash
from app.integrations.processing.repository import OutboxDraft
from app.integrations.processing.sql_repository import SqlIntegrationRepository, table_presence
from app.integrations.security.clients import generate_secret
from app.integrations.security.facility import CaseSensitivity
from app.integrations.security.sql_stores import SqlClientStore, SqlFacilityMappingStore

from .conftest import CLIENT_A, FACILITY_A, T0, make_envelope, reset_mysql_schema, seed_mysql_clients


@pytest.fixture
def engine(mysql_engine):
    reset_mysql_schema(mysql_engine)
    seed_mysql_clients(mysql_engine, {"pms-a": generate_secret(), "pms-b": generate_secret(),
                                      "pms-off": generate_secret()})
    return mysql_engine


@pytest.fixture
def repo(engine):
    return SqlIntegrationRepository(engine)


def test_mysql_json_type_reorders_keys_which_is_why_bodies_are_stored_as_text(engine):
    with engine.connect() as c:
        reordered = c.execute(text("SELECT CAST(:doc AS JSON)"), {"doc": '{"zz":1,"a":2}'}).scalar_one()
    assert reordered.replace(" ", "") == '{"a":2,"zz":1}'  # MySQL changed the byte order


def test_body_hash_is_stable_through_mysql_storage(repo):
    body = {"zz": 1, "a": {"y": 2.5, "x": "é"}, "list": [3, 1, 2]}
    out = repo.accept(make_envelope(body=body), wire_bytes=None, max_attempts=3)
    stored = repo.load_body(out.message_id)
    assert stored == body and payload_hash(stored) == payload_hash(body)
    with repo._engine.connect() as c:  # noqa: SLF001
        col_type = c.execute(text(
            "SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME='integration_inbound_payloads' AND COLUMN_NAME='body_canonical'")).scalar_one()
    assert col_type == "longtext"


def test_unknown_facility_fk_is_an_integrity_error_not_a_duplicate(repo):
    env = make_envelope(facility=uuid.uuid4())
    with pytest.raises(PermanentFailure) as exc:
        repo.accept(env, wire_bytes=None, max_attempts=3)
    assert exc.value.code == "integrity_violation" and exc.value.detail["mysql_errno"] == 1452
    assert repo.list_messages(facility_scope=None) == []


def test_unique_idempotency_constraint_exists_in_database(engine):
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT INDEX_NAME, NON_UNIQUE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() "
            "AND TABLE_NAME='integration_idempotency_keys' AND INDEX_NAME LIKE 'uq_%'")).all()
    assert rows and all(r.NON_UNIQUE == 0 for r in rows)


def test_concurrent_duplicate_intake_creates_exactly_one_message(repo):
    barrier = threading.Barrier(8)
    results, errors = [], []

    def worker():
        barrier.wait()
        try:
            results.append(repo.accept(make_envelope(key="race"), wire_bytes=None, max_attempts=3))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert sum(r.outcome is IntakeOutcome.ACCEPTED for r in results) == 1
    assert len({r.message_id for r in results}) == 1
    assert len(repo.list_messages(facility_scope=None)) == 1


def test_lost_insert_race_resolves_via_duplicate_key_error(repo, monkeypatch):
    """Force the race deterministically: the pre-check misses the existing row,
    so the INSERT hits MySQL error 1062 on the idempotency key and must be
    resolved as DUPLICATE / CONFLICT -- never as a generic integrity failure."""
    first = repo.accept(make_envelope(key="race2"), wire_bytes=None, max_attempts=3)
    real = SqlIntegrationRepository._idem_row
    calls = {"n": 0}

    def blind_once(s, envelope):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(s, envelope)

    monkeypatch.setattr(SqlIntegrationRepository, "_idem_row", staticmethod(blind_once))
    dup = repo.accept(make_envelope(key="race2"), wire_bytes=None, max_attempts=3)
    assert dup.outcome is IntakeOutcome.DUPLICATE and dup.message_id == first.message_id
    calls["n"] = 0
    from app.integrations.core.errors import IdempotencyConflict

    with pytest.raises(IdempotencyConflict):
        repo.accept(make_envelope(key="race2", body={"room": "other"}), wire_bytes=None, max_attempts=3)
    assert len(repo.list_messages(facility_scope=None)) == 1


def test_concurrent_workers_never_claim_the_same_message(repo):
    for i in range(40):
        repo.accept(make_envelope(key=f"k{i}"), wire_bytes=None, max_attempts=3)
    claimed: list[uuid.UUID] = []
    lock = threading.Lock()
    barrier = threading.Barrier(6)

    def worker(n):
        barrier.wait()
        while True:
            got = repo.claim(worker_id=f"w{n}", now=T0, lease_seconds=30, limit=3)
            if not got:
                return
            with lock:
                claimed.extend(c.message.message_id for c in got)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(claimed) == 40 and len(set(claimed)) == 40


def test_claim_query_uses_next_attempt_index(engine):
    with engine.connect() as c:
        plan = c.execute(text(
            "EXPLAIN SELECT id FROM integration_inbound_messages WHERE next_attempt_at <= :n "
            "AND status IN ('PENDING','RETRY_WAIT','PROCESSING') ORDER BY next_attempt_at, id "
            "LIMIT 10 FOR UPDATE SKIP LOCKED"), {"n": "2026-11-19 12:00:00"}).mappings().all()
    keys = {str(row.get("possible_keys")) for row in plan}
    assert any("next_attempt_at" in k for k in keys)


def _effects(engine) -> int:
    with engine.connect() as c:
        return c.execute(text("SELECT COUNT(*) FROM test_domain_effects")).scalar_one()


def test_domain_write_commits_atomically_with_success(repo, engine):
    repo.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with repo.completion(claim, clock=lambda: T0) as ctx:
        ctx.session.execute(text("INSERT INTO test_domain_effects (message_id) VALUES (:m)"),
                            {"m": str(claim.message.message_id)})
        ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
    assert _effects(engine) == 1
    assert repo.get(claim.message.message_id, facility_scope=None).status is MessageStatus.SUCCEEDED


def test_hms_service_style_commit_inside_handler_is_still_rolled_back_on_lease_loss(repo, engine):
    """HMS write services call db.commit() themselves (services/writes.py).
    With the savepoint-joined session that only releases a SAVEPOINT; if the
    lease is lost before the real commit, the domain write disappears too."""
    repo.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    times = iter([T0, T0 + timedelta(seconds=60)])
    with pytest.raises(LeaseLost):
        with repo.completion(claim, clock=lambda: next(times)) as ctx:
            ctx.session.execute(text("INSERT INTO test_domain_effects (message_id) VALUES ('x')"))
            ctx.session.commit()  # what stays_write.transaction() does
            ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
    assert _effects(engine) == 0
    assert repo.list_outbox(facility_scope=None) == []


def test_handler_failure_after_service_commit_rolls_back_domain_write(repo, engine):
    repo.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with pytest.raises(RuntimeError):
        with repo.completion(claim, clock=lambda: T0) as ctx:
            ctx.session.execute(text("INSERT INTO test_domain_effects (message_id) VALUES ('x')"))
            ctx.session.commit()
            raise RuntimeError("later step failed")
    assert _effects(engine) == 0


def test_fenced_row_is_locked_during_handler_so_others_cannot_reclaim(repo, engine):
    repo.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    claim = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)[0]
    with repo.completion(claim, clock=lambda: T0):
        # Even "after expiry", SKIP LOCKED skips the row we hold.
        assert repo.claim(worker_id="other", now=T0 + timedelta(minutes=5), lease_seconds=30, limit=5) == []


def test_restart_recovery_with_new_repository_instance(engine):
    first = SqlIntegrationRepository(engine)
    first.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    first.claim(worker_id="crashed", now=T0, lease_seconds=30, limit=1)
    # "process restart": brand-new repository object, same database
    second = SqlIntegrationRepository(engine)
    recovered = second.claim(worker_id="fresh", now=T0 + timedelta(seconds=31), lease_seconds=30, limit=5)
    assert len(recovered) == 1 and recovered[0].message.attempt_count == 2


def test_wire_payload_stored_only_when_given(repo):
    a = repo.accept(make_envelope(key="w1"), wire_bytes=b"\x02raw\x03", max_attempts=3)
    b = repo.accept(make_envelope(key="w2"), wire_bytes=None, max_attempts=3)
    assert repo.stored_wire_bytes(a.message_id) == b"\x02raw\x03"
    assert repo.stored_wire_bytes(b.message_id) is None


def test_table_presence_probe(engine):
    assert all(table_presence(engine).values())


def test_status_check_constraint_enforced(engine):
    repo = SqlIntegrationRepository(engine)
    out = repo.accept(make_envelope(), wire_bytes=None, max_attempts=3)
    from sqlalchemy.exc import OperationalError

    with pytest.raises(OperationalError):
        with engine.begin() as c:
            c.execute(text("UPDATE integration_inbound_messages SET status='BOGUS' WHERE id=:i"),
                      {"i": str(out.message_id)})


# --- stores ---------------------------------------------------------------
def test_sql_client_store_is_exact_and_fails_closed(engine):
    store = SqlClientStore(engine)
    assert store.get_by_code("pms-a").id == CLIENT_A
    assert store.get_by_code("PMS-A") is None  # ci collation must not widen matches
    assert store.get_by_code("pms-off").enabled is False
    with engine.begin() as c:
        c.execute(text("UPDATE integration_clients SET protocols='fias,carrier-pigeon' WHERE client_code='pms-a'"))
    assert store.get_by_code("pms-a").enabled is False


def test_mapping_store_uses_binary_collation_for_exact_policy(engine):
    store = SqlFacilityMappingStore(engine)
    assert [m.facility_id for m in store.find(CLIENT_A, "HOTEL-A", CaseSensitivity.EXACT)] == [FACILITY_A]
    assert store.find(CLIENT_A, "hotel-a", CaseSensitivity.EXACT) == []
    with engine.connect() as c:
        collation = c.execute(text(
            "SELECT COLLATION_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND "
            "TABLE_NAME='integration_facility_mappings' AND COLUMN_NAME='normalized_property_code'")).scalar_one()
    assert collation == "utf8mb4_bin"
    assert store.facilities_for_client(CLIENT_A) == {FACILITY_A}  # disabled mapping excluded
