"""Round 3 hardening: outage recovery (D4/D5), settings validation (D6),
header injection and secret exposure checks."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import ValidationError

from app.integrations.config import IntegrationSettings
from app.integrations.core.envelope import IntakeOutcome, IntakeResult, MessageStatus, Protocol
from app.integrations.core.errors import TransientFailure
from app.integrations.transport.tcp import LinkPump

from .conftest import CTX, build_stack, json_msg


# --- D4: a database outage during TCP intake must not drop frames ----------------------
class FakeLink:
    def __init__(self, frames):
        self.inbound: asyncio.Queue[bytes] = asyncio.Queue()
        for f in frames:
            self.inbound.put_nowait(f)
        self.sent: list[bytes] = []

    async def send(self, payload):
        self.sent.append(payload)


def transient():
    return IntakeResult(outcome=IntakeOutcome.REJECTED, correlation_id="c",
                        error={"code": "transient_failure", "category": "transient", "message": "db down"})


def accepted(frame):
    return IntakeResult(outcome=IntakeOutcome.ACCEPTED, correlation_id="c", message_type=frame.decode())


def test_intake_result_retryable_only_for_transient_rejections():
    assert transient().retryable is True
    assert accepted(b"x").retryable is False
    security = IntakeResult(outcome=IntakeOutcome.REJECTED, correlation_id="c",
                            error={"code": "x", "category": "security", "message": "no"})
    assert security.retryable is False


async def _no_sleep(_):
    await asyncio.sleep(0)


def test_pump_retries_same_frame_through_outage_and_keeps_order():
    calls: list[bytes] = []
    outage = {"left": 3}

    def receive(frame):
        calls.append(frame)
        if frame == b"f1" and outage["left"]:
            outage["left"] -= 1
            return transient()
        return accepted(frame)

    async def go():
        link = FakeLink([b"f1", b"f2"])
        stop = asyncio.Event()
        pump = LinkPump(link, receive, responder=lambda r: r.message_type.encode(), sleep=_no_sleep)
        task = asyncio.create_task(pump.run(stop=stop))
        for _ in range(200):
            if pump.processed == 2:
                break
            await asyncio.sleep(0.005)
        stop.set()
        await asyncio.wait_for(task, 2)
        return pump, link

    pump, link = asyncio.run(go())
    assert calls == [b"f1", b"f1", b"f1", b"f1", b"f2"]  # f2 never overtakes f1
    assert pump.processed == 2 and pump.intake_retries == 3
    assert link.sent == [b"f1", b"f2"]  # no reply until the frame is really accepted


def test_pump_survives_intake_exceptions():
    state = {"n": 0}

    def receive(frame):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("driver crashed")
        return accepted(frame)

    async def go():
        link = FakeLink([b"f1"])
        stop = asyncio.Event()
        pump = LinkPump(link, receive, sleep=_no_sleep)
        task = asyncio.create_task(pump.run(stop=stop))
        for _ in range(200):
            if pump.processed:
                break
            await asyncio.sleep(0.005)
        stop.set()
        await asyncio.wait_for(task, 2)
        return pump

    pump = asyncio.run(go())
    assert pump.processed == 1 and pump.intake_retries == 1


def test_pump_stop_during_outage_leaves_frame_unacknowledged():
    async def go():
        link = FakeLink([b"f1"])
        stop = asyncio.Event()

        async def slow_sleep(_):
            await asyncio.sleep(0.05)

        pump = LinkPump(link, lambda f: transient(), responder=lambda r: b"ack", sleep=slow_sleep)
        task = asyncio.create_task(pump.run(stop=stop))
        await asyncio.sleep(0.02)
        stop.set()
        await asyncio.wait_for(task, 2)
        return pump, link

    pump, link = asyncio.run(go())
    assert pump.processed == 0 and pump.unprocessed_on_stop == 1 and link.sent == []


def test_gateway_reports_database_outage_as_retryable(stack):
    def down(*a, **k):
        raise ConnectionError("db down")

    stack.repo.accept = down
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.retryable


# --- D5: database failure while recording a failure must not abort the batch ------------
def test_worker_continues_batch_when_failure_cannot_be_recorded():
    s = build_stack()
    h = s.handlers["test.guest_arrival"]
    h.failures.append(TransientFailure("first message fails"))
    for i in range(2):
        s.clock.advance(0.001)
        s.gateway.receive(json_msg(f"m{i}"), protocol=Protocol.TEST, client=s.auth(), context=CTX)
    real = s.repo.record_failure

    def db_down(*a, **k):
        raise ConnectionError("db down")

    s.repo.record_failure = db_down
    summary = s.worker.run_once()
    assert summary.claimed == 2 and summary.unrecorded == 1 and summary.succeeded == 1
    stuck = [m for m in s.repo.list_messages(facility_scope=None) if m.status is MessageStatus.PROCESSING]
    assert len(stuck) == 1  # not lost: still PROCESSING with a lease
    s.repo.record_failure = real
    s.clock.advance(31)  # lease expiry -> recovered
    assert s.worker.run_once().succeeded == 1
    assert all(m.status is MessageStatus.SUCCEEDED for m in s.repo.list_messages(facility_scope=None))
    assert s.metrics.get("failure_unrecorded", type="ConnectionError") == 1


# --- D6: inconsistent settings are rejected at load time ---------------------------------
@pytest.mark.parametrize("kwargs", [
    {"RETRY_BASE_SECONDS": 100, "RETRY_MAX_SECONDS": 10},
    {"HTNG_INBOUND_ENABLED": True},
    {"LIVE_DOMAIN_WRITES": True},
    {"ACTOR_USER_ID": "not-a-uuid"},
])
def test_inconsistent_settings_rejected(kwargs):
    with pytest.raises(ValidationError):
        IntegrationSettings(**kwargs)


def test_defaults_are_all_off():
    s = IntegrationSettings()
    assert not any([s.ENABLED, s.LIVE_DOMAIN_WRITES, s.STORE_RAW_WIRE_PAYLOAD, s.SIMULATOR_ENABLED,
                    s.HTNG_INBOUND_ENABLED]) and s.RETENTION_DAYS is None and s.HTNG_RATE_LIMIT_PER_MINUTE is None


# --- header injection / secret exposure ---------------------------------------------------
def test_unsafe_correlation_header_is_not_echoed(env):
    from .test_api import PREFIX, hdr, soap

    stack, client, _, _ = env
    r = client.post(f"{PREFIX}/htng/inbound", content=soap("h1"),
                    headers={**hdr(stack), "X-Correlation-ID": "abc\tinjected"})
    assert r.status_code == 200 and r.headers["X-Correlation-ID"] != "abc\tinjected"
    r = client.post(f"{PREFIX}/htng/inbound", content=soap("h2"),
                    headers={**hdr(stack), "X-Correlation-ID": "safe-id-1"})
    assert r.headers["X-Correlation-ID"] == "safe-id-1"


def test_no_secret_material_in_openapi_or_operator_responses(env):
    from .test_api import PREFIX, seed

    stack, client, _, _ = env
    seed(stack, 1)
    stack.worker.run_once()
    spec = json.dumps(client.get("/openapi.json").json()["components"]["schemas"]).lower()
    assert "secret_hash" not in spec and "secondary_secret" not in spec
    blob = ""
    for path in ("/messages", "/outbox", "/audit", "/metrics", "/adapters", "/facilities/health"):
        blob += client.get(PREFIX + path).text
    for s in stack.secrets.values():
        assert s not in blob
    assert "sha256$" not in blob
