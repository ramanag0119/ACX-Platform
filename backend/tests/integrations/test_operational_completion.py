"""Operational-completion regression tests (docs/HTNG_FIAS_OPERATIONAL_COMPLETION_REPORT.md).

Covers the defects fixed in that sprint:

* "Backlog stalled" was derived from the age of the oldest UNFINISHED message,
  so a retry legitimately scheduled for later, or a message under a live
  worker lease, was reported as a stall. The status is now derived from DUE
  work (`next_attempt_at` passed) -- and a genuinely old due backlog still
  reads "stalled".
* Outbound: the relay claimed every protocol and dead-lettered rows it had no
  sender for; it now claims only deliverable protocols. Outbox dead letters are
  audited. The service registers an HTNG sender only for an https endpoint and
  a non-BLOCKED adapter.
* One stored row with an unknown direction / protocol made the worker's claim
  raise (whole batch rolled back on every poll) and the dashboard search
  answer 500. It is now quarantined (DEAD_LETTER, audited) / listed tolerantly.
* FIAS link lifecycle wiring (LinkSupervisor) and its production builder,
  which refuses without a verified specification (HF-11) and framing (HF-06).

Everything here is synthetic: the HTTP receiver is a local mock on 127.0.0.1,
the FIAS peer is the loopback TEST simulator, the framing and record set are
the PROVISIONAL TEST fixtures. Nothing here is vendor evidence.
"""

from __future__ import annotations

import asyncio
import queue
import socket
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.integrations import observability as obs
from app.integrations.adapters.base import AdapterReadiness, AdapterStatus, TransportContext
from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry
from app.integrations.adapters.htng.sender import HtngSoapSender
from app.integrations.config import IntegrationSettings
from app.integrations.core.envelope import CanonicalEnvelope, Direction, IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.errors import PermanentFailure, TransientFailure
from app.integrations.core.hashing import payload_hash
from app.integrations.core.retry import RetryPolicy
from app.integrations.exchange.registry import AdapterRegistry
from app.integrations.processing.repository import OutboxDraft, OutboxStatus
from app.integrations.processing.worker import OutboxRelay
from app.integrations.service import build_outbound_senders
from app.integrations.simulators.fias_simulator import FiasTestSimulator
from app.integrations.simulators.fixtures import provisional_test_framer
from app.integrations.transport.link_runtime import LinkNotStartable, LinkSupervisor, build_fias_link_supervisor
from app.integrations.transport.soap import SoapEndpoint, SoapTransport
from app.integrations.transport.tcp import ReconnectPolicy, TcpLink, TcpSettings
from app.integrations.transport.tcp_server import TcpListenerLink

from .conftest import CLIENT_A, FACILITY_A, T0, Clock, RecordingSender, build_stack
from .test_observability import runtime_for

STALL = 900


def _env(key: str, *, at, protocol=Protocol.FIAS, ordering_key=None, facility=FACILITY_A) -> CanonicalEnvelope:
    body = {"room": "101", "key": key}
    return CanonicalEnvelope(
        idempotency_key=key, correlation_id=f"corr-{key}", facility_id=facility, client_id=CLIENT_A,
        protocol=protocol, message_type="test.guest_arrival", direction=Direction.INBOUND,
        schema_version="t/1", received_at=at, payload_hash=payload_hash(body), body=body,
        ordering_key=ordering_key,
    )


def _processing(repo, now, protocol="fias"):
    view = obs.build_overview(runtime_for(repo), facility_scope=None, now=now, stall_seconds=STALL)
    return view["protocols"][protocol]


# ======================================================== backlog / stall truth
def test_empty_backlog_is_idle_not_stalled(repo):
    p = _processing(repo, T0)["processing"]
    assert p["status"] == "idle" and p["classification"] == "due_work"
    assert (p["due_now"], p["scheduled"], p["in_progress"]) == (0, 0, 0)


def test_fresh_pending_is_within_threshold_and_old_pending_is_stalled(repo):
    repo.accept(_env("p1", at=T0), wire_bytes=None, max_attempts=5)
    within = _processing(repo, T0 + timedelta(seconds=60))["processing"]
    assert within["status"] == "backlog_within_threshold"
    assert within["due_now"] == 1 and within["oldest_due_age_seconds"] == 60.0
    stalled = _processing(repo, T0 + timedelta(hours=2))["processing"]
    assert stalled["status"] == "backlog_stalled"  # a genuine old backlog stays visibly stalled
    assert stalled["oldest_due_age_seconds"] == 7200.0


def test_future_retry_is_waiting_not_stalled(repo):
    """Root cause of the false 'Backlog stalled': a RETRY_WAIT row scheduled in
    the future counted as backlog age since it was received."""
    repo.accept(_env("r1", at=T0), wire_bytes=None, max_attempts=5)
    (claim,) = repo.claim(worker_id="w", now=T0, lease_seconds=30, limit=1)
    repo.record_failure(claim, now=T0, error=TransientFailure("t", code="hms_unavailable"),
                        retry_at=T0 + timedelta(days=1))
    e = _processing(repo, T0 + timedelta(hours=3))
    p = e["processing"]
    assert p["status"] == "waiting_for_retry", p
    assert (p["due_now"], p["scheduled"]) == (0, 1)
    assert p["oldest_pending_age_seconds"] == 3 * 3600.0  # still reported, no longer decisive
    # Once the retry time has passed and nobody picks it up, it IS a stall.
    late = _processing(repo, T0 + timedelta(days=1, hours=1))["processing"]
    assert late["status"] == "backlog_stalled" and late["oldest_due_age_seconds"] == 3600.0


def test_live_lease_is_processing_and_abandoned_lease_is_stalled(repo):
    repo.accept(_env("l1", at=T0), wire_bytes=None, max_attempts=5)
    repo.claim(worker_id="w", now=T0, lease_seconds=3600, limit=1)
    live = _processing(repo, T0 + timedelta(minutes=30))["processing"]
    assert live["status"] == "processing" and live["in_progress"] == 1
    abandoned = _processing(repo, T0 + timedelta(hours=3))["processing"]
    assert abandoned["status"] == "backlog_stalled"
    assert abandoned["oldest_due_age_seconds"] == 2 * 3600.0  # since the lease expired


def test_message_blocked_behind_dead_letter_is_reported(repo):
    repo.accept(_env("o1", at=T0, ordering_key="stay:S1"), wire_bytes=None, max_attempts=5)
    repo.accept(_env("o2", at=T0 + timedelta(seconds=1), ordering_key="stay:S1"), wire_bytes=None, max_attempts=5)
    (claim,) = repo.claim(worker_id="w", now=T0 + timedelta(seconds=2), lease_seconds=30, limit=1)
    repo.record_failure(claim, now=T0 + timedelta(seconds=2), error=PermanentFailure("x", code="hms_business_rule"),
                        retry_at=None)
    assert repo.claim(worker_id="w", now=T0 + timedelta(hours=1), lease_seconds=30, limit=5) == []
    p = _processing(repo, T0 + timedelta(hours=1))["processing"]
    assert p["ordering_blocked"] == 1 and p["status"] == "backlog_stalled"  # needs an operator redrive


def test_worker_restart_recovers_backlog_and_status_returns_to_idle(repo):
    """Backlog recovery evidence: worker 1 dies holding a lease; after expiry a
    new worker re-claims and completes; the status follows the real state."""
    stack = build_stack(repo, clock=Clock(T0))
    # A synthetic FIAS record (PROVISIONAL TEST record set) through the real gateway.
    r = stack.gateway.receive(b"ZA|MIrec-1|PCHOTEL-A|RN7|SRres-7|", protocol=Protocol.FIAS,
                              client=stack.auth("pms-a", Protocol.FIAS), context=TransportContext(transport="tcp"))
    assert r.outcome is IntakeOutcome.ACCEPTED
    rt = runtime_for(repo)

    def fias(now):
        return obs.build_overview(rt, facility_scope=None, now=now, stall_seconds=STALL)["protocols"]["fias"]

    assert repo.claim(worker_id="dead-worker", now=T0, lease_seconds=60, limit=1)  # then the process dies
    assert fias(T0 + timedelta(seconds=30))["processing"]["status"] == "processing"  # lease still live
    dead = fias(T0 + timedelta(hours=1))["processing"]
    assert dead["status"] == "backlog_stalled" and dead["due_now"] == 1  # abandoned lease is visible
    stack.clock.now = T0 + timedelta(hours=1)
    summary = stack.worker.run_once()  # a fresh worker after the lease expired
    assert summary.claimed == 1 and summary.succeeded == 1
    stored = repo.get(r.message_id, facility_scope=None)
    assert stored.status is MessageStatus.SUCCEEDED and stored.attempt_count == 2
    after = fias(T0 + timedelta(hours=1, seconds=1))
    assert after["processing"]["status"] == "idle"
    assert after["messages"]["inbound"]["succeeded"] == 1  # recovered, not deleted or reset


# ============================================================== outbound state
def _enqueue(repo, protocol, *, at=T0, mtype="test.receipt", body=None, max_attempts=3):
    return repo.enqueue_outbox(OutboxDraft(protocol, mtype, body or {"outcome": "ok"}, f"corr-{protocol}"),
                               client_id=CLIENT_A, facility_id=FACILITY_A, source_message_id=None,
                               max_attempts=max_attempts, now=at)


def test_outbound_queue_without_sender_is_reported_as_queued_not_stalled(repo):
    _enqueue(repo, Protocol.HTNG)
    o = _processing(repo, T0 + timedelta(hours=5), protocol="htng")["outbound_processing"]
    assert o["status"] == "queued_no_sender"
    assert o["sender_configured"] is False and "HF-24" in o["sender_reason"]
    assert (o["unfinished"], o["due_now"]) == (1, 1)


def test_outbound_with_configured_sender_reports_real_backlog(repo):
    _enqueue(repo, Protocol.HTNG)
    rt = runtime_for(repo, settings=IntegrationSettings(HTNG_OUTBOUND_ENDPOINT_URL="https://vendor.example.invalid/soap"))
    view = obs.build_overview(rt, facility_scope=None, now=T0 + timedelta(hours=1), stall_seconds=STALL)
    o = view["protocols"]["htng"]["outbound_processing"]
    assert o["sender_configured"] is True and o["status"] == "backlog_stalled"
    assert o["relay_heartbeat_observed"] is False  # the relay runs in another process


def test_production_htng_adapter_never_gets_a_sender():
    registry = AdapterRegistry()
    registry.register(HTNGAdapter(SchemaRegistry()))  # production: empty registry -> BLOCKED
    rt = SimpleNamespace(settings=IntegrationSettings(HTNG_OUTBOUND_ENDPOINT_URL="https://vendor.example.invalid/x"),
                         gateway=SimpleNamespace(adapters=registry), htng_adapter=HTNGAdapter(SchemaRegistry()))
    configured, reason = obs.outbound_sender("htng", rt)
    assert configured is False and "HF-07" in reason
    senders, notes = build_outbound_senders(rt)
    assert senders == {} and any("BLOCKED" in n for n in notes)


def test_no_endpoint_means_no_sender_and_an_explicit_note():
    stack = build_stack()
    rt = SimpleNamespace(settings=IntegrationSettings(), htng_adapter=stack.gateway.adapters.get(
        Protocol.HTNG, Direction.OUTBOUND))
    senders, notes = build_outbound_senders(rt)
    assert senders == {} and any("HF-24" in n for n in notes) and any(n.startswith("fias:") for n in notes)


def test_relay_claims_only_deliverable_protocols(repo):
    """Before: a row of a protocol without a sender was dead-lettered
    (sender_not_configured). Now it stays PENDING."""
    stack = build_stack(repo)
    _enqueue(repo, Protocol.TEST)
    _enqueue(repo, Protocol.FIAS)
    summary = stack.relay.run_once()
    assert summary.succeeded == 1 and summary.dead_lettered == 0
    statuses = {str(r.protocol): r.status for r in repo.list_outbox(facility_scope=None)}
    assert statuses == {"test": OutboxStatus.SENT, "fias": OutboxStatus.PENDING}


def test_outbox_dead_letter_is_audited(repo):
    stack = build_stack(repo)
    stack.relay._senders[Protocol.TEST] = RecordingSender([], failures=[PermanentFailure("no", code="soap_fault_client")])
    _enqueue(repo, Protocol.TEST)
    assert stack.relay.run_once().dead_lettered == 1
    events = [e for e in repo.list_audit(facility_scope=None) if e.action == "outbox.dead_letter"]
    assert len(events) == 1
    assert events[0].detail["error_code"] == "soap_fault_client" and "body" not in events[0].detail


# =========================================== HTNG outbound against a mock SOAP receiver
OK_BODY = (b'<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
           b'<soap:Body><t:Receipt xmlns:t="urn:acx:test:generic-xml:v1"><t:Outcome>ok</t:Outcome></t:Receipt>'
           b'</soap:Body></soap:Envelope>')
CLIENT_FAULT = (b'<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
                b'<soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>bad request</faultstring>'
                b'</soap:Fault></soap:Body></soap:Envelope>')


class MockSoapReceiver:
    """Disposable local HTTP receiver on 127.0.0.1. `plan` items:
    ("ok",) | ("status", code) | ("fault",) | ("sleep", seconds)."""

    def __init__(self) -> None:
        self.plan: queue.Queue = queue.Queue()
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence
                pass

            def do_POST(self):  # noqa: N802
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.requests.append({"headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
                step = outer.plan.get_nowait() if not outer.plan.empty() else ("ok",)
                if step[0] == "sleep":
                    time.sleep(step[1])
                    step = ("ok",)
                if step[0] == "ok":
                    code, payload = 200, OK_BODY
                elif step[0] == "fault":
                    code, payload = 500, CLIENT_FAULT
                else:
                    code, payload = step[1], b""
                self.send_response(code)
                self.send_header("Content-Type", "text/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/soap"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def receiver():
    r = MockSoapReceiver()
    yield r
    r.close()


def _htng_relay(repo, receiver, clock, *, timeout=2.0):
    stack = build_stack(repo, clock=clock)
    adapter = stack.gateway.adapters.get(Protocol.HTNG, Direction.OUTBOUND)  # TEST profile, TEST_ONLY
    endpoint = SoapEndpoint(url=receiver.url, timeout_seconds=timeout, allow_insecure_loopback=True)
    sender = HtngSoapSender(SoapTransport(), endpoint, adapter)
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1, max_delay_seconds=2)
    return OutboxRelay(repository=repo, adapters=stack.gateway.adapters, senders={Protocol.HTNG: sender},
                       policy=policy, worker_id="relay", lease_seconds=30, clock=clock)


def _room_state(repo, clock, max_attempts=3):
    return repo.enqueue_outbox(OutboxDraft(Protocol.HTNG, "test.room_state", {"room": "101", "state": "occupied"},
                                           "corr-out-1"),
                               client_id=CLIENT_A, facility_id=FACILITY_A, source_message_id=None,
                               max_attempts=max_attempts, now=clock())


def _outbox(repo, outbox_id):
    return next(r for r in repo.list_outbox(facility_scope=None) if r.outbox_id == outbox_id)


def test_htng_outbound_delivers_to_mock_receiver(repo, receiver):
    clock = Clock(T0)
    relay = _htng_relay(repo, receiver, clock)
    oid = _room_state(repo, clock)
    assert relay.run_once().succeeded == 1
    rec = _outbox(repo, oid)
    assert rec.status == OutboxStatus.SENT and rec.sent_at == T0
    (req,) = receiver.requests
    assert req["headers"]["soapaction"] == '"urn:acx:test:generic-xml:v1#RoomStateNotice"'
    assert req["headers"]["x-correlation-id"] == "corr-out-1"
    assert b"<" in req["body"] and b"RoomStateNotice" in req["body"] and b"occupied" in req["body"]


def test_htng_outbound_retries_5xx_then_succeeds(repo, receiver):
    clock = Clock(T0)
    relay = _htng_relay(repo, receiver, clock)
    oid = _room_state(repo, clock)
    receiver.plan.put(("status", 503))
    assert relay.run_once().retried == 1
    rec = _outbox(repo, oid)
    assert rec.status == OutboxStatus.RETRY_WAIT and rec.last_error_code == "soap_http_5xx"
    assert relay.run_once().claimed == 0  # not due yet: back-off respected
    clock.advance(5)
    assert relay.run_once().succeeded == 1  # outbox replay after the receiver recovers
    assert _outbox(repo, oid).status == OutboxStatus.SENT and len(receiver.requests) == 2


def test_htng_outbound_timeout_is_transient(repo, receiver):
    clock = Clock(T0)
    relay = _htng_relay(repo, receiver, clock, timeout=0.3)
    oid = _room_state(repo, clock)
    receiver.plan.put(("sleep", 1.0))
    assert relay.run_once().retried == 1
    assert _outbox(repo, oid).last_error_code == "soap_timeout"


def test_htng_outbound_client_fault_is_dead_lettered_and_audited(repo, receiver):
    clock = Clock(T0)
    relay = _htng_relay(repo, receiver, clock)
    oid = _room_state(repo, clock)
    receiver.plan.put(("fault",))
    assert relay.run_once().dead_lettered == 1
    rec = _outbox(repo, oid)
    assert rec.status == OutboxStatus.DEAD_LETTER and rec.last_error_code == "soap_fault_client"
    assert any(e.action == "outbox.dead_letter" for e in repo.list_audit(facility_scope=None))


def test_htng_outbound_retry_exhaustion_dead_letters(repo, receiver):
    clock = Clock(T0)
    relay = _htng_relay(repo, receiver, clock)
    oid = _room_state(repo, clock, max_attempts=2)
    for _ in range(3):
        receiver.plan.put(("status", 503))
    relay.run_once()
    clock.advance(10)
    relay.run_once()
    rec = _outbox(repo, oid)
    assert rec.status == OutboxStatus.DEAD_LETTER and rec.attempt_count == 2


# ========================================================= corrupt stored rows
def _sql_only(repo):
    from app.integrations.processing.sql_repository import SqlIntegrationRepository

    if not isinstance(repo, SqlIntegrationRepository):
        pytest.skip("stored-row corruption only exists in the SQL store")
    return repo


def test_invalid_stored_row_is_quarantined_not_blocking_the_worker(repo):
    repo = _sql_only(repo)
    from sqlalchemy import text

    bad = _env("bad", at=T0)
    good = _env("good", at=T0 + timedelta(seconds=1))
    repo.accept(bad, wire_bytes=None, max_attempts=5)
    repo.accept(good, wire_bytes=None, max_attempts=5)
    with repo._engine.begin() as conn:  # noqa: SLF001 - simulate a row written outside the gateway
        conn.execute(text("UPDATE integration_inbound_messages SET direction='sideways' WHERE id=:id"),
                      {"id": str(bad.message_id)})
    claims = repo.claim(worker_id="w", now=T0 + timedelta(seconds=5), lease_seconds=30, limit=5)
    assert [c.message.message_id for c in claims] == [good.message_id]  # the batch is not lost
    q = repo.get(bad.message_id, facility_scope=None)
    assert str(q.status) == "DEAD_LETTER" and q.last_error_code == "invalid_stored_record"
    assert q.last_error_category == "validation"
    audit = [e for e in repo.list_audit(facility_scope=None) if e.action == "message.quarantined"]
    assert len(audit) == 1 and audit[0].detail["stored"]["direction"] == "sideways"


def test_dashboard_search_tolerates_an_invalid_stored_row(repo):
    repo = _sql_only(repo)
    from sqlalchemy import text

    from app.integrations.processing.activity import MessageQuery

    bad = _env("bad2", at=T0)
    repo.accept(bad, wire_bytes=None, max_attempts=5)
    with repo._engine.begin() as conn:  # noqa: SLF001
        conn.execute(text("UPDATE integration_inbound_messages SET direction='sideways' WHERE id=:id"),
                      {"id": str(bad.message_id)})
    rows, total = repo.search_messages(MessageQuery(received_from=T0 - timedelta(hours=1),
                                                    received_to=T0 + timedelta(hours=1)), facility_scope=None)
    assert total == 1 and obs.message_item(rows[0])["direction"] == "sideways"


# ============================================================ configuration
@pytest.mark.parametrize("kwargs, message", [
    (dict(HTNG_OUTBOUND_ENDPOINT_URL="http://vendor.example.invalid/x"), "https"),
    (dict(FIAS_LINK_ENABLED=True, FIAS_LINK_PORT=5010, FIAS_LINK_HOST="h",
          FIAS_LINK_CLIENT_CODE="c", FIAS_LINK_CLIENT_SECRET="s"), "INTEGRATION_ENABLED"),
    (dict(ENABLED=True, FIAS_LINK_ENABLED=True, FIAS_LINK_HOST="h",
          FIAS_LINK_CLIENT_CODE="c", FIAS_LINK_CLIENT_SECRET="s"), "PORT"),
    (dict(ENABLED=True, FIAS_LINK_ENABLED=True, FIAS_LINK_PORT=5010,
          FIAS_LINK_CLIENT_CODE="c", FIAS_LINK_CLIENT_SECRET="s"), "HOST"),
    (dict(ENABLED=True, FIAS_LINK_ENABLED=True, FIAS_LINK_MODE="listener", FIAS_LINK_PORT=5010,
          FIAS_LINK_CLIENT_CODE="c", FIAS_LINK_CLIENT_SECRET="s"), "ALLOWED_PEERS"),
    (dict(ENABLED=True, FIAS_LINK_ENABLED=True, FIAS_LINK_PORT=5010, FIAS_LINK_HOST="h"), "CLIENT_CODE"),
])
def test_unsafe_outbound_and_link_settings_are_refused(kwargs, message):
    with pytest.raises(ValidationError, match=message):
        IntegrationSettings(**kwargs)


def test_defaults_keep_every_new_switch_off():
    s = IntegrationSettings()
    assert s.HTNG_OUTBOUND_ENDPOINT_URL is None and s.FIAS_LINK_ENABLED is False


# ========================================================= FIAS link lifecycle
def _link_settings(**kw):
    base = dict(ENABLED=True, FIAS_LINK_ENABLED=True, FIAS_LINK_HOST="127.0.0.1", FIAS_LINK_PORT=5999,
                FIAS_LINK_CLIENT_CODE="pms-a", FIAS_LINK_CLIENT_SECRET="x" * 40)
    base.update(kw)
    return IntegrationSettings(**base)


def test_production_fias_link_refuses_without_verified_specification():
    registry = AdapterRegistry()
    registry.register(FIASAdapter())  # production: PRODUCTION_SPECIFICATION is None -> BLOCKED
    rt = SimpleNamespace(settings=_link_settings(), gateway=SimpleNamespace(adapters=registry))
    with pytest.raises(LinkNotStartable, match="HF-11"):
        build_fias_link_supervisor(rt)


def test_test_only_fias_adapter_is_not_accepted_for_a_production_link():
    stack = build_stack()  # FIAS adapter on the PROVISIONAL TEST spec -> TEST_ONLY
    rt = SimpleNamespace(settings=_link_settings(), gateway=stack.gateway)
    with pytest.raises(LinkNotStartable, match="not READY"):
        build_fias_link_supervisor(rt)


def test_fias_link_refuses_without_verified_framing_even_with_a_ready_adapter():
    """A READY adapter is impossible today; a status double isolates the HF-06 check."""
    ready = AdapterStatus(Protocol.FIAS, AdapterReadiness.READY, "double", ("x",), ())
    rt = SimpleNamespace(settings=_link_settings(),
                         gateway=SimpleNamespace(adapters=SimpleNamespace(statuses=lambda: [ready])))
    with pytest.raises(LinkNotStartable, match="HF-06"):
        build_fias_link_supervisor(rt)


def test_disabled_fias_link_is_never_built():
    rt = SimpleNamespace(settings=IntegrationSettings(), gateway=None)
    with pytest.raises(LinkNotStartable, match="not enabled"):
        build_fias_link_supervisor(rt)


def _wait(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_link_supervisor_client_mode_receive_reconnect_and_graceful_stop():
    """Synthetic TEST profile only: provisional framing and record set, loopback simulator."""
    stack = build_stack()
    client = stack.auth("pms-a", Protocol.FIAS)
    ctx = TransportContext(transport="tcp", peer="127.0.0.1")
    results = []

    def receive(frame):
        r = stack.gateway.receive(frame, protocol=Protocol.FIAS, client=client, context=ctx)
        results.append(r)
        return r

    async def scenario():
        sim = FiasTestSimulator(enabled=True)
        port = await sim.start()
        sup = LinkSupervisor(name="fias-test", mode="client", receive=receive, link_factory=lambda: TcpLink(
            TcpSettings(host="127.0.0.1", port=port, read_timeout=0.2,
                        reconnect=ReconnectPolicy(base_delay_seconds=0.05, max_delay_seconds=0.1)),
            provisional_test_framer))
        await asyncio.to_thread(sup.start)
        await sim.wait_for_client(3)
        await sim.send_record(b"ZA|MIs-1|PCHOTEL-A|RN101|SRres-1|")
        await sim.send_raw(b"\x02ZA|MIs-2|PCHOT")  # partial frame...
        await asyncio.sleep(0.05)
        await sim.send_raw(b"EL-A|RN102|SRres-2|\x03")  # ...completed by the next read
        await asyncio.to_thread(_wait, lambda: len(results) >= 2)
        assert [r.outcome for r in results[:2]] == [IntakeOutcome.ACCEPTED, IntakeOutcome.ACCEPTED]
        assert sup.health()["state"] == "connected" and sup.health()["frames_processed"] == 2
        # connection loss -> automatic reconnect -> traffic resumes
        await sim.drop_clients()
        await sim.wait_for_client(5)
        assert await asyncio.to_thread(_wait, lambda: sup.health()["state"] == "connected")
        await sim.send_record(b"ZA|MIs-3|PCHOTEL-A|RN103|SRres-3|")
        assert await asyncio.to_thread(_wait, lambda: len(results) >= 3)
        assert results[2].outcome is IntakeOutcome.ACCEPTED and sup.health()["connections"] >= 2
        assert await asyncio.to_thread(sup.stop)
        assert sup.health()["state"] == "closed" and sup.running is False
        await sim.stop()

    asyncio.run(scenario())
    rows = stack.repo.list_messages(facility_scope=None)
    assert len(rows) == 3 and all(str(m.protocol) == "fias" for m in rows)


def test_link_supervisor_listener_mode_allow_list_and_stop():
    stack = build_stack()
    client = stack.auth("pms-a", Protocol.FIAS)
    ctx = TransportContext(transport="tcp")

    def receive(frame):
        return stack.gateway.receive(frame, protocol=Protocol.FIAS, client=client, context=ctx)

    def make(allowed):
        return LinkSupervisor(name="fias-listener", mode="listener", receive=receive, link_factory=lambda: TcpListenerLink(
            "127.0.0.1", 0, provisional_test_framer, allowed_peers=allowed, read_timeout=0.2))

    # Not allow-listed: the connection is closed and nothing is stored.
    denied = make(["10.0.0.0/8"])
    denied.start()
    with socket.create_connection(("127.0.0.1", denied.port), timeout=2) as s:
        s.sendall(b"\x02ZA|MId-1|PCHOTEL-A|RN101|SRres-9|\x03")
        s.settimeout(2)
        try:
            assert s.recv(16) == b""  # closed by the listener ...
        except ConnectionResetError:
            pass  # ... or reset, depending on timing: either way the peer is refused
    assert _wait(lambda: denied.health().get("rejected_peers", 0) == 1)
    assert denied.stop()
    assert stack.repo.list_messages(facility_scope=None) == []

    allowed = make(["127.0.0.1/32"])
    allowed.start()
    with socket.create_connection(("127.0.0.1", allowed.port), timeout=2) as s:
        s.sendall(b"\x02ZA|MIl-1|PCHOTEL-A|RN101|SRres-1|\x03\x02ZA|MIl-2|PCHOTEL-A|RN102|SRres-2|\x03")
        assert _wait(lambda: len(stack.repo.list_messages(facility_scope=None)) == 2)
    assert allowed.stop() and allowed.health()["state"] == "closed"
