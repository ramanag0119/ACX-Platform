"""HMS business integration against the REAL stay services, on a DISPOSABLE MySQL.

Runs only when INTEGRATION_TEST_HMS_DB_URL points at a disposable database (its
name must not be the configured HMS database). The fixture builds the HMS schema
with the test-only shim (tests/integrations/hms_schema_shim.py), loads the
repository's own seed (`python -m seeds.run_seed`) into it, and creates the
candidate integration tables alongside.

The live-write gate is opened ONLY inside this test, with a TEST-ONLY approval
register. Production gating (domain/approvals.py) is not touched: no decision is
approved there, and nothing here talks to the HMS database.

Flow under test (no mocks of HMS code):
    TEST adapter -> ExchangeGateway -> SqlIntegrationRepository -> InboundWorker
    -> StayEventHandler -> StayDomainAdapter -> app.services.stays_write.check_in/out
    (on the fenced, savepoint-joined session) -> real stay / amenity rows
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.integrations.core.envelope import MessageStatus, Protocol
from app.integrations.core.retry import RetryPolicy
from app.integrations.domain import approvals
from app.integrations.domain.approvals import Decision, DecisionStatus, LiveWriteGate
from app.integrations.domain.stays import CHECK_IN, CHECK_OUT, StayDomainAdapter, StayEventHandler
from app.integrations.exchange.dispatcher import MessageDispatcher
from app.integrations.exchange.gateway import ExchangeGateway
from app.integrations.exchange.registry import AdapterRegistry, HandlerRegistry
from app.integrations.processing.sql_models import create_integration_tables
from app.integrations.processing.sql_repository import SqlIntegrationRepository
from app.integrations.processing.worker import InboundWorker
from app.integrations.security.clients import (
    ClientAuthenticator,
    InMemoryClientStore,
    IntegrationClient,
    generate_secret,
    hash_secret,
)
from app.integrations.security.facility import FacilityMapping, FacilityResolver, InMemoryFacilityMappingStore

from .conftest import CTX, Clock, JsonTestAdapter
from .hms_schema_shim import create_hms_schema

ENV = "INTEGRATION_TEST_HMS_DB_URL"
CLIENT = uuid.UUID("cccccccc-0000-4000-8000-0000000000e2")


def hms_engine_impl():
    """Shared by the module-scoped `hms_engine` fixture in conftest.py."""
    url = os.environ.get(ENV)
    if not url:
        pytest.skip(f"{ENV} not set; needs a DISPOSABLE MySQL database for the seeded HMS schema")
    parsed = make_url(url)
    if parsed.database in (None, "", app_settings.MYSQL_DATABASE, "inspironics_app"):
        pytest.fail("refusing to build/seed the HMS schema in the configured HMS database")
    engine = create_engine(url, isolation_level="READ COMMITTED",
                           connect_args={"init_command": "SET time_zone = '+00:00'"})
    create_hms_schema(engine)
    seed_env = {**os.environ, "MYSQL_HOST": parsed.host, "MYSQL_PORT": str(parsed.port or 3306),
                "MYSQL_USER": parsed.username, "MYSQL_PASSWORD": parsed.password or "",
                "MYSQL_DATABASE": parsed.database, "MYSQL_SSL_VERIFY_CERT": "false", "DEBUG": "false"}
    done = subprocess.run([sys.executable, "-m", "seeds.run_seed"], env=seed_env,  # noqa: S603
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr[-2000:]
    create_integration_tables(engine)
    yield engine
    engine.dispose()


class ExternalRefResolver:
    """TEST-ONLY resolver: `stay.external_stay_ref_number` within the facility.
    Whether this column is the right key is decision HF-02 / HF-31."""

    def resolve_stay(self, session, *, client_id, facility_id, external_ref):
        from app.models import Amenity, RoomAllocation, Stay

        return session.execute(
            select(Stay.id).join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .join(Amenity, Amenity.id == RoomAllocation.room_id)
            .where(Stay.external_stay_ref_number == external_ref, Amenity.facility_id == facility_id)
            .limit(1)
        ).scalar_one_or_none()


def _test_only_register():
    return {d: Decision(d, x.subject, DecisionStatus.APPROVED, evidence="TEST ONLY - disposable database")
            for d, x in approvals.DECISIONS.items()}


@pytest.fixture
def world(hms_engine):
    with hms_engine.begin() as c:
        for t in ("integration_audit_events", "integration_outbox_messages", "integration_idempotency_keys",
                  "integration_inbound_payloads", "integration_inbound_messages"):
            c.execute(text(f"DELETE FROM {t}"))  # noqa: S608 - fixed table-name constants
        facility_id = uuid.UUID(c.execute(text("SELECT id FROM facility LIMIT 1")).scalar_one())
        actor = uuid.UUID(c.execute(text("SELECT id FROM app_user WHERE user_name='system'")).scalar_one())
        if not c.execute(text("SELECT COUNT(*) FROM integration_clients WHERE id=:i"), {"i": str(CLIENT)}).scalar_one():
            c.execute(text("INSERT INTO integration_clients (id, client_code, secret_hash, enabled, protocols) "
                           "VALUES (:i, 'pms-e2e', :h, 1, 'test')"), {"i": str(CLIENT), "h": hash_secret(generate_secret())})
    secret = generate_secret()
    clock = Clock(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    repo = SqlIntegrationRepository(hms_engine)
    adapter = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=True, register=_test_only_register()),
                                resolver=ExternalRefResolver(), actor_id=actor)
    handlers = HandlerRegistry()
    handlers.register(StayEventHandler(CHECK_IN, adapter))
    handlers.register(StayEventHandler(CHECK_OUT, adapter))
    adapters = AdapterRegistry()
    adapters.register(JsonTestAdapter(inbound=(CHECK_IN, CHECK_OUT), outbound=()))
    gateway = ExchangeGateway(
        adapters=adapters, handlers=handlers,
        authenticator=ClientAuthenticator(InMemoryClientStore([IntegrationClient(
            CLIENT, "pms-e2e", True, frozenset({Protocol.TEST}), hash_secret(secret))])),
        resolver=FacilityResolver(InMemoryFacilityMappingStore([FacilityMapping(CLIENT, "HOTEL-E2E", facility_id)])),
        repository=repo, clock=clock,
    )
    worker = InboundWorker(repository=repo, dispatcher=MessageDispatcher(handlers),
                           policy=RetryPolicy(max_attempts=3, base_delay_seconds=10, max_delay_seconds=60),
                           worker_id="e2e", lease_seconds=30, clock=clock)
    client = gateway.authenticate("pms-e2e", secret, protocol=Protocol.TEST)
    return hms_engine, gateway, worker, repo, client, clock, facility_id


def send(world, msg_id, mtype, ref):
    import json

    _, gateway, _, _, client, clock, _ = world
    clock.advance(0.001)
    raw = json.dumps({"type": mtype, "id": msg_id, "property": "HOTEL-E2E",
                      "body": {"external_stay_ref": ref}}).encode()
    return gateway.receive(raw, protocol=Protocol.TEST, client=client, context=CTX)


def stay(engine, ref):
    with engine.connect() as c:
        return c.execute(text(
            "SELECT s.status, s.actual_checkin_time, s.actual_checkout_time, st.amenity_status_name "
            "FROM stay s JOIN room_allocation ra ON ra.stay_id = s.id JOIN amenity a ON a.id = ra.room_id "
            "JOIN amenity_status st ON st.id = a.status WHERE s.external_stay_ref_number = :r"), {"r": ref}).one()


def reset_stay(engine, ref, status, checkin, checkout, room_status):
    with engine.begin() as c:
        c.execute(text("UPDATE stay SET status=:s, actual_checkin_time=:i, actual_checkout_time=:o "
                       "WHERE external_stay_ref_number=:r"), {"s": status, "i": checkin, "o": checkout, "r": ref})
        c.execute(text("UPDATE amenity a JOIN room_allocation ra ON ra.room_id=a.id JOIN stay s ON s.id=ra.stay_id "
                       "SET a.status=(SELECT id FROM amenity_status WHERE amenity_status_name=:n) "
                       "WHERE s.external_stay_ref_number=:r"), {"n": room_status, "r": ref})
        c.execute(text("DELETE acs FROM amenity_condition_status acs JOIN room_allocation ra ON ra.room_id=acs.amenity_id "
                       "JOIN stay s ON s.id=ra.stay_id WHERE s.external_stay_ref_number=:r"), {"r": ref})


def statuses(repo):
    return {m.external_message_id: (m.status, m.last_error_code) for m in repo.list_messages(facility_scope=None)}


def test_real_check_in_then_check_out_through_worker_with_atomic_audit(world):
    engine, _, worker, repo, _, _, facility_id = world
    reset_stay(engine, "PMS-0003", "pending", None, None, "Allotted")
    assert send(world, "e2e-1", CHECK_OUT, "PMS-0003").outcome.value == "accepted"  # arrives first...
    assert send(world, "e2e-0", CHECK_IN, "PMS-0003").outcome.value == "accepted"
    # ...ordering is by arrival, so check-out runs first and is rejected by HMS rules
    worker.run_once()
    st = statuses(repo)
    assert st["e2e-1"] == (MessageStatus.DEAD_LETTER, "hms_business_rule")
    worker.run_once()  # check-in still waits: its same-stay predecessor is dead-lettered
    assert statuses(repo)["e2e-0"][0] is MessageStatus.PENDING

    # Correct order this time.
    reset_stay(engine, "PMS-0003", "pending", None, None, "Allotted")
    with engine.begin() as c:
        c.execute(text("DELETE FROM integration_inbound_messages"))
    send(world, "e2e-2", CHECK_IN, "PMS-0003")
    send(world, "e2e-3", CHECK_OUT, "PMS-0003")
    worker.run_once()
    worker.run_once()
    st = statuses(repo)
    assert st["e2e-2"][0] is MessageStatus.SUCCEEDED and st["e2e-3"][0] is MessageStatus.SUCCEEDED
    status, checkin, checkout, room = stay(engine, "PMS-0003")
    assert status == "checked out" and checkin is not None and checkout is not None
    assert room in ("Available", "Unavailable")  # HMS rule: depends on blocking conditions
    actions = [e.action for e in repo.list_audit(facility_scope={facility_id})]
    assert actions[:2] == ["domain.stay.check_out", "domain.stay.check_in"]


def test_repeated_check_in_is_noop_and_real_hms_conflict_dead_letters(world):
    engine, _, worker, repo, _, _, facility_id = world
    reset_stay(engine, "PMS-0001", "active", datetime(2026, 8, 15, 12, tzinfo=UTC), None, "Occupied")
    reset_stay(engine, "PMS-0004", "checked out", datetime(2026, 8, 8, 12, tzinfo=UTC),
               datetime(2026, 8, 10, 12, tzinfo=UTC), "Available")
    send(world, "dup-in", CHECK_IN, "PMS-0001")
    send(world, "late-in", CHECK_IN, "PMS-0004")
    send(world, "unknown", CHECK_IN, "PMS-9999")
    worker.run_once()
    st = statuses(repo)
    assert st["dup-in"][0] is MessageStatus.SUCCEEDED
    assert st["late-in"] == (MessageStatus.DEAD_LETTER, "hms_business_rule")
    assert st["unknown"] == (MessageStatus.RETRY_WAIT, "stay_not_found")
    audit = [e for e in repo.list_audit(facility_scope={facility_id}) if e.action == "domain.stay.check_in"]
    assert audit and audit[0].detail["already_applied"] is True
    assert stay(engine, "PMS-0001")[0] == "active"


def test_lost_lease_rolls_back_the_real_hms_check_in(world):
    engine, _, worker, repo, _, clock, _ = world
    reset_stay(engine, "PMS-0003", "pending", None, None, "Allotted")
    send(world, "lease-1", CHECK_IN, "PMS-0003")
    real_completion = repo.completion

    def slow_completion(claim, *, clock):
        times = iter([clock(), clock() + timedelta(seconds=120)])  # handler "overruns" its lease
        return real_completion(claim, clock=lambda: next(times))

    repo.completion = slow_completion
    summary = worker.run_once()
    assert summary.lease_lost == 1
    status, checkin, _, room = stay(engine, "PMS-0003")
    assert status == "pending" and checkin is None and room == "Allotted"  # HMS write rolled back
    repo.completion = real_completion
    clock.advance(31)
    assert worker.run_once().succeeded == 1  # recovered after lease expiry
    assert stay(engine, "PMS-0003")[0] == "active"


def test_production_register_still_blocks_the_same_flow(world):
    engine, _, _, _, _, _, _ = world
    adapter = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=True), resolver=ExternalRefResolver(),
                                actor_id=uuid.uuid4())
    from app.integrations.core.errors import ApprovalRequired

    from .conftest import make_envelope

    env = make_envelope(mtype=CHECK_IN, body={"external_stay_ref": "PMS-0003"})
    with Session(engine) as s, pytest.raises(ApprovalRequired):
        adapter.apply(env, s)
