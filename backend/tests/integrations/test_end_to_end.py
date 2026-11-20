"""End-to-end flows on TEST fixtures only (no vendor, no live HMS writes).

FIAS-style:  simulator --TCP--> TcpLink --> LinkPump --> ExchangeGateway
             --> repository (memory AND MySQL) --> worker --> handler
             --> outbox --> relay --> TcpLink --> simulator
HTNG-style:  SOAP bytes --> ExchangeGateway --> worker --> outbox --> relay
             --> SoapTransport --> mock vendor test endpoint

This is SIMULATOR evidence. It proves the framework's plumbing, not
interoperability with any real PMS.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET

import httpx
import pytest

from app.integrations.adapters.base import TransportContext
from app.integrations.adapters.htng.sender import HtngSoapSender
from app.integrations.core.envelope import Direction, IntakeOutcome, MessageStatus, Protocol
from app.integrations.processing.repository import OutboxDraft
from app.integrations.simulators.fias_simulator import FiasTestSimulator, SimulatorDisabled
from app.integrations.simulators.fixtures import (
    TEST_XML_NS,
    generic_arrival_soap,
    provisional_test_framer,
    synthetic_receipt_record,
)
from app.integrations.transport.soap import SoapEndpoint, SoapTransport, build_soap_envelope, parse_soap
from app.integrations.transport.tcp import LinkOutboundSender, LinkPump, ReconnectPolicy, TcpLink, TcpSettings

from .conftest import build_stack


def test_simulator_requires_explicit_opt_in_and_loopback():
    async def go():
        with pytest.raises(SimulatorDisabled):
            await FiasTestSimulator(enabled=False).start()
        with pytest.raises(SimulatorDisabled):
            await FiasTestSimulator(host="0.0.0.0", enabled=True).start()  # noqa: S104 - asserts refusal
        with pytest.raises(SimulatorDisabled):
            await FiasTestSimulator(host="10.1.2.3", enabled=True).start()
    asyncio.run(go())


def test_simulator_disabled_by_default_setting():
    from app.integrations.config import IntegrationSettings

    assert IntegrationSettings().SIMULATOR_ENABLED is False


def test_fias_style_tcp_flow_end_to_end(repo):
    stack = build_stack(repo)
    arrival = stack.handlers["test.guest_arrival"]
    arrival.emit = None
    arrival.before_return = lambda env, ctx: ctx.emit(
        OutboxDraft(Protocol.FIAS, "test.room_state", {"room": env.body["room"], "state": "occupied"},
                    env.correlation_id))
    client = stack.auth("pms-a", Protocol.FIAS)

    async def go():
        sim = FiasTestSimulator(enabled=True)
        port = await sim.start()
        link = TcpLink(TcpSettings(host="127.0.0.1", port=port, read_timeout=0.2,
                                   reconnect=ReconnectPolicy(base_delay_seconds=0.05)), provisional_test_framer)
        stop = asyncio.Event()
        ctx = TransportContext(transport="tcp", peer=f"127.0.0.1:{port}")
        results = []

        def receive(frame):
            r = stack.gateway.receive(frame, protocol=Protocol.FIAS, client=client, context=ctx)
            results.append(r)
            return r

        pump = LinkPump(link, receive, responder=lambda r: synthetic_receipt_record(r, r.message_id.hex
                                                                                       if r.message_id else "none"))
        link_task = asyncio.create_task(link.run())
        pump_task = asyncio.create_task(pump.run(stop=stop))
        await link.wait_connected(3)
        await sim.wait_for_client(3)

        # partial writes, two records in one write, a duplicate, and junk
        await sim.send_raw(b"\x02ZA|MIa-1|PCHOTEL-A|RN101|GNJane Roe|SRres-1|")
        await asyncio.sleep(0.05)
        await sim.send_raw(b"\x03\x02ZD|MId-1|PCHOTEL-A|RN101|SRres-1|\x03")
        await sim.send_record(b"ZA|MIa-1|PCHOTEL-A|RN101|GNJane Roe|SRres-1|")  # duplicate
        await sim.send_record(b"ZA|MIa-2|PCHOTEL-B|RN102|SRres-2|")  # facility not mapped for client A
        await sim.send_record(b"garbage")

        for _ in range(200):
            if len(results) >= 5:
                break
            await asyncio.sleep(0.02)
        outcomes = [r.outcome for r in results]
        assert outcomes[:3] == [IntakeOutcome.ACCEPTED, IntakeOutcome.ACCEPTED, IntakeOutcome.DUPLICATE]
        assert outcomes[3:] == [IntakeOutcome.REJECTED, IntakeOutcome.REJECTED]
        assert results[3].error["category"] == "security"

        stack.clock.advance(1)  # real time passes between intake and processing (G5 stamps)
        summary = await asyncio.to_thread(stack.worker.run_once)
        assert summary.succeeded == 2
        loop = asyncio.get_running_loop()
        stack.relay._senders[Protocol.FIAS] = LinkOutboundSender(link, loop)
        sent = await asyncio.to_thread(stack.relay.run_once)
        assert sent.succeeded == 1

        for _ in range(100):
            if any(f.startswith(b"ZS|") for f in sim.received):
                break
            await asyncio.sleep(0.02)
        assert b"ZS|RN101|SToccupied|" in sim.received
        receipts = [f for f in sim.received if f.startswith(b"ZK|")]
        assert len(receipts) == 5 and receipts[0].endswith(b"|OKok|") and receipts[3].endswith(b"|OKrejected|")

        stop.set()
        await link.stop()
        await asyncio.wait_for(asyncio.gather(link_task, pump_task), 3)
        await sim.stop()

    asyncio.run(asyncio.wait_for(go(), 20))

    msgs = stack.repo.list_messages(facility_scope=None)
    assert len(msgs) == 2 and all(m.status is MessageStatus.SUCCEEDED for m in msgs)
    assert arrival.seen[0].body["guest_name"] == "Jane Roe"
    assert stack.repo.list_outbox(facility_scope=None)[0].status == "SENT"


def test_link_sender_failure_is_retried_when_link_down(repo):
    stack = build_stack(repo)
    from app.integrations.core.envelope import OutboundRequest

    from .conftest import CLIENT_A, FACILITY_A

    stack.gateway.request_outbound(OutboundRequest(protocol=Protocol.FIAS, message_type="test.room_state",
                                                   facility_id=FACILITY_A, client_id=CLIENT_A,
                                                   body={"room": "101", "state": "clean"}))

    async def go():
        link = TcpLink(TcpSettings(host="127.0.0.1", port=1), provisional_test_framer)  # never started
        stack.relay._senders[Protocol.FIAS] = LinkOutboundSender(link, asyncio.get_running_loop(), timeout=1)
        return await asyncio.to_thread(stack.relay.run_once)

    summary = asyncio.run(go())
    assert summary.retried == 1
    assert stack.repo.list_outbox(facility_scope=None)[0].status == "RETRY_WAIT"


def test_htng_style_soap_flow_end_to_end(repo):
    stack = build_stack(repo)
    arrival = stack.handlers["test.guest_arrival"]
    arrival.emit = OutboxDraft(Protocol.HTNG, "test.room_state", {"room": "101", "state": "occupied"}, None)
    client = stack.auth("pms-a", Protocol.HTNG)

    raw = generic_arrival_soap(message_ref="x-1", property_code="HOTEL-A", room="101", stay_ref="s-1")
    r = stack.gateway.receive(raw, protocol=Protocol.HTNG, client=client, context=TransportContext("http-soap"))
    assert r.outcome is IntakeOutcome.ACCEPTED
    assert stack.worker.run_once().succeeded == 1

    vendor_inbox = []

    def vendor(request: httpx.Request) -> httpx.Response:  # TEST vendor endpoint
        vendor_inbox.append((request.headers["SOAPAction"], parse_soap(request.content).body))
        return httpx.Response(200, content=build_soap_envelope(ET.Element(f"{{{TEST_XML_NS}}}Receipt")))

    adapter = stack.gateway.adapters.get(Protocol.HTNG, Direction.OUTBOUND)
    stack.relay._senders[Protocol.HTNG] = HtngSoapSender(
        SoapTransport(httpx.Client(transport=httpx.MockTransport(vendor))),
        SoapEndpoint(url="https://vendor-test.invalid/soap"),
        adapter,
    )
    assert stack.relay.run_once().succeeded == 1
    action, body = vendor_inbox[0]
    assert action == '"urn:acx:test:generic-xml:v1#RoomStateNotice"'
    assert body.find(f"{{{TEST_XML_NS}}}State").text == "occupied"
    assert stack.repo.list_outbox(facility_scope=None)[0].status == "SENT"
