"""FIAS-style certification scenarios.

TEST ASSUMPTION: frames use the SYNTHETIC grammar and "ZA" records of
app/integrations/simulators/fixtures.py (STX/ETX test markers). They are NOT FIAS
records, framing, ACK bytes or heartbeats; those official contracts are BLOCKED.
Reuses: FiasTestSimulator, TcpLink, LinkPump, FIASAdapter, ExchangeGateway, worker.
"""

from __future__ import annotations

import asyncio

from app.integrations.adapters.base import TransportContext
from app.integrations.core.envelope import IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.errors import AuthenticationFailed, PermanentFailure
from app.integrations.simulators.fias_simulator import FiasTestSimulator
from app.integrations.simulators.fixtures import TEST_END_MARKER, TEST_START_MARKER, provisional_test_framer
from app.integrations.transport.tcp import LinkPump, ReconnectPolicy, TcpLink, TcpSettings

from ..conftest import build_stack
from .core import Category, scenario

T, E = Category.TRANSPORT, Category.ENGINE
STX, ETX = TEST_START_MARKER, TEST_END_MARKER


def frame(ref, prop="HOTEL-A", room="101"):
    return f"ZA|MI{ref}|PC{prop}|RN{room}|SRSYN-1|".encode()


def fias_stack(ctx):
    s = build_stack()
    ctx.secrets.extend(s.secrets.values())
    ctx.evidence.adapter = "FIASAdapter(ACX-SYNTHETIC-TEST/0, PROVISIONAL)"
    return s, s.auth("pms-a", Protocol.FIAS)


def intake(s, client, raw, bound=None):
    return s.gateway.receive(raw, protocol=Protocol.FIAS, client=client,
                             context=TransportContext(transport="direct", bound_property_code=bound))


def tcp(ctx, s, client, script, *, expect_results, bound=None, max_frame=8192):
    """Drive frames through the REAL simulator + TcpLink + LinkPump; return final intake results."""
    results = []

    async def go():
        sim = FiasTestSimulator(enabled=True)
        port = await sim.start()
        link = TcpLink(TcpSettings(host="127.0.0.1", port=port, read_timeout=0.2,
                                   reconnect=ReconnectPolicy(base_delay_seconds=0.05)),
                       lambda: provisional_test_framer(max_frame))
        stop = asyncio.Event()

        def receive(raw):
            r = s.gateway.receive(raw, protocol=Protocol.FIAS, client=client,
                                  context=TransportContext(transport="tcp", bound_property_code=bound))
            if not r.retryable:
                results.append(r)
            return r

        async def fast(_):
            await asyncio.sleep(0.01)

        pump = LinkPump(link, receive, sleep=fast)
        tasks = [asyncio.create_task(link.run()), asyncio.create_task(pump.run(stop=stop))]
        await link.wait_connected(3)
        await sim.wait_for_client(3)
        await script(sim, link)
        for _ in range(400):
            if len(results) >= expect_results:
                break
            await asyncio.sleep(0.02)
        stop.set()
        await link.stop()
        await asyncio.wait_for(asyncio.gather(*tasks), 5)
        await sim.stop()
        return pump, link

    pump, link = asyncio.run(asyncio.wait_for(go(), 30))
    ctx.evidence.response = {"outcomes": [str(r.outcome) for r in results],
                             "intake_retries": pump.intake_retries, "link": link.health.as_dict()}
    if results:
        ctx.evidence.correlation_id = results[0].correlation_id
    return results, pump, link


@scenario("FIAS-SYN-001", "fias", T, "Valid synthetic frame accepted over TCP and processed",
          expected={"intake": "accepted", "processing": "SUCCEEDED"}, evidence=("response", "processing_result"))
def _valid(ctx):
    s, c = fias_stack(ctx)

    async def script(sim, link):
        await sim.send_record(frame("v-1"))

    res, _, _ = tcp(ctx, s, c, script, expect_results=1)
    s.clock.advance(1)
    s.worker.run_once()
    st = s.repo.list_messages(facility_scope=None)[0].status
    ctx.evidence.processing_result = str(st)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED] and st is MessageStatus.SUCCEEDED, str(ctx.evidence.response))


@scenario("FIAS-SYN-002", "fias", T, "Multiple frames in one TCP write all accepted in order",
          expected={"outcomes": ["accepted", "accepted", "accepted"]}, evidence=("response",))
def _multi(ctx):
    s, c = fias_stack(ctx)

    async def script(sim, link):
        await sim.send_raw(b"".join(STX + frame(f"m-{i}") + ETX for i in range(3)))

    res, _, _ = tcp(ctx, s, c, script, expect_results=3)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED] * 3, str(ctx.evidence.response))


@scenario("FIAS-SYN-003", "fias", T, "Frame split across several TCP writes reassembled",
          expected={"outcomes": ["accepted"]}, evidence=("response",))
def _partial(ctx):
    s, c = fias_stack(ctx)
    data = STX + frame("p-1") + ETX

    async def script(sim, link):
        for i in range(0, len(data), 5):
            await sim.send_raw(data[i:i + 5])
            await asyncio.sleep(0.01)

    res, _, _ = tcp(ctx, s, c, script, expect_results=1)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED], str(ctx.evidence.response))


@scenario("FIAS-SYN-004", "fias", T, "Malformed frame rejected permanently; link continues",
          expected={"outcomes": ["rejected", "accepted"], "retryable": False}, evidence=("response", "failure_code"))
def _malformed(ctx):
    s, c = fias_stack(ctx)

    async def script(sim, link):
        await sim.send_record(b"garbage")
        await sim.send_record(frame("after-bad"))

    res, pump, _ = tcp(ctx, s, c, script, expect_results=2)
    ctx.evidence.failure_code = res[0].error["code"] if res and res[0].error else None
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.REJECTED, IntakeOutcome.ACCEPTED], str(ctx.evidence.response))
    ctx.expect(pump.intake_retries == 0 and not res[0].retryable, "malformed frame was retried")


@scenario("FIAS-SYN-005", "fias", T, "Unsupported encoding: non-ASCII byte rejected; non-ASCII-compatible grammar refused",
          expected={"frame": "bad_encoding", "grammar": "ValueError"}, evidence=("failure_code",))
def _encoding(ctx):
    from app.integrations.adapters.fias.spec import VerificationStatus, WireGrammar

    s, c = fias_stack(ctx)
    r = intake(s, c, b"ZA|MIe-1|PCHOTEL-A|RN101|SR\xe9|")
    ctx.evidence.failure_code = r.error["code"] if r.error else None
    try:
        WireGrammar("utf-16", 2, b"|", 2, VerificationStatus.PROVISIONAL_TEST, "x")
        grammar_refused = False
    except ValueError:
        grammar_refused = True
    ctx.expect(ctx.evidence.failure_code == "bad_encoding" and grammar_refused, "encoding not enforced")


@scenario("FIAS-SYN-006", "fias", T, "Oversized frame dropped and counted; link stays up",
          expected={"outcomes": ["accepted"], "framing_errors": ">=1"}, evidence=("response",))
def _oversize(ctx):
    s, c = fias_stack(ctx)

    async def script(sim, link):
        await sim.send_raw(STX + b"Z" * 300 + ETX)
        await sim.send_record(frame("ok-1"))

    res, _, link = tcp(ctx, s, c, script, expect_results=1, max_frame=128)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED] and link.health.framing_errors >= 1,
               str(ctx.evidence.response))


@scenario("FIAS-SYN-007", "fias", E, "Duplicate message detected", expected={"second": "duplicate"},
          evidence=("processing_result",))
def _dup(ctx):
    s, c = fias_stack(ctx)
    intake(s, c, frame("d-1"))
    r = intake(s, c, frame("d-1"))
    ctx.evidence.processing_result = str(r.outcome)
    ctx.expect(r.outcome is IntakeOutcome.DUPLICATE and len(s.repo.list_messages(facility_scope=None)) == 1, "not deduplicated")


@scenario("FIAS-SYN-008", "fias", E, "Same-entity messages processed strictly in arrival order (incl. same-instant arrivals)",
          expected={"order": ["o-0", "o-1", "o-2", "o-3"]}, evidence=("observations",))
def _order(ctx):
    s, c = fias_stack(ctx)
    h = s.handlers["test.guest_arrival"]
    h.ordered_by = "room"
    for i in range(4):
        intake(s, c, frame(f"o-{i}"))  # frozen clock: all arrive at the same instant
    s.clock.advance(1)
    for _ in range(6):
        s.worker.run_once()
    order = [e.body["message_ref"] for e in h.seen]
    ctx.evidence.observations.append(f"processed order: {order}")
    ctx.expect(order == ["o-0", "o-1", "o-2", "o-3"], f"order {order}")


@scenario("FIAS-SYN-009", "fias", T, "Connection interruption: partial frame discarded, resent frame accepted",
          expected={"outcomes": ["accepted"], "connections": 2}, evidence=("response",))
def _interrupt(ctx):
    s, c = fias_stack(ctx)

    async def script(sim, link):
        await sim.send_raw(STX + frame("cut-1")[:8])  # partial, then the line drops
        await asyncio.sleep(0.05)
        await sim.drop_clients()
        for _ in range(200):
            if link.health.connections >= 2 and sim._streams:  # noqa: SLF001 - test-only
                break
            await asyncio.sleep(0.02)
        await sim.send_record(frame("cut-1"))

    res, _, link = tcp(ctx, s, c, script, expect_results=1)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED] and link.health.connections == 2, str(ctx.evidence.response))


@scenario("FIAS-SYN-010", "fias", T, "Reconnection after peer disconnect restores the link",
          expected={"connections": ">=2", "state_after": "connected"}, evidence=("response",))
def _reconnect(ctx):
    s, c = fias_stack(ctx)
    seen = {}

    async def script(sim, link):
        await sim.drop_clients()
        for _ in range(200):
            if link.health.connections >= 2 and str(link.health.state) == "connected":
                break
            await asyncio.sleep(0.02)
        seen["state"] = str(link.health.state)
        await sim.send_record(frame("re-1"))

    res, _, link = tcp(ctx, s, c, script, expect_results=1)
    ctx.expect(link.health.connections >= 2 and seen.get("state") == "connected" and len(res) == 1, str(ctx.evidence.response))


@scenario("FIAS-SYN-011", "fias", E, "Database outage during intake: frame retried by the pump, not lost",
          expected={"outcomes": ["accepted"], "intake_retries": 2}, evidence=("response",))
def _outage(ctx):
    s, c = fias_stack(ctx)
    real = s.repo.accept
    left = {"n": 2}

    def flaky(envelope, **kw):
        if left["n"]:
            left["n"] -= 1
            raise ConnectionError("database down")
        return real(envelope, **kw)

    s.repo.accept = flaky

    async def script(sim, link):
        await sim.send_record(frame("db-1"))

    res, pump, _ = tcp(ctx, s, c, script, expect_results=1)
    ctx.expect([r.outcome for r in res] == [IntakeOutcome.ACCEPTED] and pump.intake_retries == 2, str(ctx.evidence.response))


@scenario("FIAS-SYN-012", "fias", E, "Worker crash: lease expiry hands the message to a healthy worker",
          expected={"crashed_claims": 1, "final": "SUCCEEDED"}, evidence=("retry_dlq",))
def _crash(ctx):
    s, c = fias_stack(ctx)
    intake(s, c, frame("w-1"))
    crashed = s.repo.claim(worker_id="crashed", now=s.clock(), lease_seconds=30, limit=5)
    early = s.worker.run_once().claimed
    s.clock.advance(31)
    s.worker.run_once()
    m = s.repo.list_messages(facility_scope=None)[0]
    ctx.evidence.retry_dlq = {"crashed_claims": len(crashed), "claimed_before_expiry": early,
                              "final": str(m.status), "attempts": m.attempt_count}
    ctx.expect(len(crashed) == 1 and early == 0 and m.status is MessageStatus.SUCCEEDED and m.attempt_count == 2,
               str(ctx.evidence.retry_dlq))


@scenario("FIAS-SYN-013", "fias", E, "Wrong property on a property-bound link rejected (security)",
          expected={"code": "link_property_mismatch"}, evidence=("failure_code",))
def _wrong_property(ctx):
    s, c = fias_stack(ctx)
    r = intake(s, c, frame("x-1", prop="HOTEL-B"), bound="HOTEL-A")
    ctx.evidence.failure_code = r.error["code"] if r.error else None
    ctx.evidence.failure_category = r.error["category"] if r.error else None
    ctx.expect(r.outcome is IntakeOutcome.REJECTED and ctx.evidence.failure_code == "link_property_mismatch", str(r.error))


@scenario("FIAS-SYN-014", "fias", E, "Invalid client credentials refused for the FIAS protocol",
          expected={"error": "AuthenticationFailed"}, evidence=("observations",))
def _bad_client(ctx):
    s, _ = fias_stack(ctx)
    try:
        s.gateway.authenticate("pms-a", "w" * 40, protocol=Protocol.FIAS)
        refused = False
    except AuthenticationFailed:
        refused = True
    ctx.evidence.observations.append("link-level authentication handshake semantics are vendor-defined (HF-06); "
                              "this validates the engine's client authentication only")
    ctx.expect(refused, "invalid credentials accepted")


@scenario("FIAS-SYN-015", "fias", E, "Dead-letter then audited redrive recovers the message",
          expected={"after_failure": "DEAD_LETTER", "audit": "message.redrive", "final": "SUCCEEDED"},
          evidence=("retry_dlq", "audit_actions"))
def _dlq(ctx):
    s, c = fias_stack(ctx)
    s.handlers["test.guest_arrival"].failures.append(PermanentFailure("synthetic permanent failure"))
    r = intake(s, c, frame("q-1"))
    s.worker.run_once()
    dead = s.repo.get(r.message_id, facility_scope=None).status
    s.repo.redrive(r.message_id, facility_scope={s.repo.get(r.message_id, facility_scope=None).facility_id},
                   actor_id="cert-operator", reason="certification redrive test", now=s.clock())
    s.worker.run_once()
    final = s.repo.get(r.message_id, facility_scope=None).status
    ctx.evidence.audit_actions = [e.action for e in s.repo.list_audit(facility_scope=None)]
    ctx.evidence.retry_dlq = {"after_failure": str(dead), "final": str(final)}
    ctx.expect(dead is MessageStatus.DEAD_LETTER and final is MessageStatus.SUCCEEDED
               and "message.redrive" in ctx.evidence.audit_actions, str(ctx.evidence.retry_dlq))


@scenario("FIAS-OFF-001", "fias", Category.VENDOR, "Official FIAS record contracts (records, fields, samples)",
          expected={"all_cases": "pass"}, requires=("vendor",), blocked_by=("HF-11",))
def _off_records(ctx):  # pragma: no cover
    raise AssertionError("unreachable")


@scenario("FIAS-OFF-002", "fias", Category.VENDOR, "Official FIAS framing and ACK/NAK behaviour",
          expected={"ack": "per manual"}, requires=("vendor",), blocked_by=("HF-06",))
def _off_ack(ctx):  # pragma: no cover
    raise AssertionError("unreachable")


@scenario("FIAS-OFF-003", "fias", Category.VENDOR, "Official FIAS heartbeat, link start-up and resync",
          expected={"link": "per manual"}, requires=("vendor",), blocked_by=("HF-06",))
def _off_link(ctx):  # pragma: no cover
    raise AssertionError("unreachable")
