"""Accelerated sprint: regression tests for gaps G1–G4 (see HTNG_FIAS_ACCELERATED_SPRINT_REPORT.md)."""

from __future__ import annotations

import asyncio

import pytest

from app.integrations.core.envelope import Direction, IntakeOutcome, Protocol
from app.integrations.transport.tcp import LinkPump

from .conftest import CTX, build_stack, json_msg


# --- G1: a poison message must not be retried forever ------------------------------------
def _poison_stack():
    s = build_stack()
    adapter = s.gateway.adapters.get(Protocol.TEST, Direction.INBOUND)

    def broken_decode(raw, context):
        raise AttributeError("mapper bug on this payload")

    adapter.decode = broken_decode
    return s


def test_unexpected_intake_validation_error_is_permanent_not_retryable():
    s = _poison_stack()
    r = s.gateway.receive(json_msg(), protocol=Protocol.TEST, client=s.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED
    assert r.retryable is False, "poison message would be retried forever by the TCP pump"
    assert r.error["code"] == "intake_unexpected_error" and "mapper bug" not in str(r.error)


def test_persistence_outage_is_still_retryable():
    s = build_stack()

    def down(*a, **k):
        raise ConnectionError("db down")

    s.repo.accept = down
    r = s.gateway.receive(json_msg(), protocol=Protocol.TEST, client=s.auth(), context=CTX)
    assert r.retryable is True


def test_pump_moves_past_a_poison_frame():
    s = _poison_stack()
    seen = []

    class Link:
        inbound: asyncio.Queue

        async def send(self, payload):
            seen.append(payload)

    async def go():
        link = Link()
        link.inbound = asyncio.Queue()
        link.inbound.put_nowait(b"poison")
        link.inbound.put_nowait(b"next")
        stop = asyncio.Event()
        calls = []

        def receive(frame):
            calls.append(frame)
            return s.gateway.receive(frame, protocol=Protocol.TEST, client=s.auth(), context=CTX)

        async def no_sleep(_):
            await asyncio.sleep(0)

        pump = LinkPump(link, receive, sleep=no_sleep)
        task = asyncio.create_task(pump.run(stop=stop))
        for _ in range(200):
            if pump.processed == 2:
                break
            await asyncio.sleep(0.005)
        stop.set()
        await asyncio.wait_for(task, 2)
        return pump, calls

    pump, calls = asyncio.run(go())
    assert calls == [b"poison", b"next"] and pump.intake_retries == 0



# --- G2 / G3: SOAP version-matched faults and acks; media type enforced -------------------
def _soap12(ref="v12", prop="HOTEL-A"):
    from app.integrations.simulators.fixtures import TEST_XML_NS

    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope" '
        f'xmlns:t="{TEST_XML_NS}"><env:Body><t:GuestArrival>'
        f"<t:MessageRef>{ref}</t:MessageRef><t:PropertyCode>{prop}</t:PropertyCode>"
        "<t:Room>101</t:Room><t:StayRef>s1</t:StayRef></t:GuestArrival></env:Body></env:Envelope>"
    ).encode()


def _headers(stack, content_type):
    return {"X-Integration-Client": "pms-a", "X-Integration-Secret": stack.secrets["pms-a"],
            "Content-Type": content_type}


def test_soap12_request_gets_soap12_ack(env):
    from app.integrations.transport.soap import SOAP12_NS, SoapVersion, parse_soap

    stack, client, _, _ = env
    r = client.post("/api/v1/integrations/htng/inbound", content=_soap12(),
                    headers=_headers(stack, "application/soap+xml; charset=utf-8"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/soap+xml")
    msg = parse_soap(r.content)
    assert msg.version is SoapVersion.SOAP12 and r.content.count(SOAP12_NS.encode()) >= 1


def test_soap12_request_gets_soap12_fault(env):
    from app.integrations.transport.soap import SoapVersion, parse_soap

    stack, client, _, _ = env
    r = client.post("/api/v1/integrations/htng/inbound", content=_soap12(prop="HOTEL-B"),
                    headers=_headers(stack, "application/soap+xml"))
    assert r.status_code == 403 and r.headers["content-type"].startswith("application/soap+xml")
    msg = parse_soap(r.content)
    assert msg.version is SoapVersion.SOAP12 and msg.fault.code == "env:Sender"


def test_soap11_fault_unchanged(env):
    from app.integrations.transport.soap import SoapVersion, parse_soap

    stack, client, _, _ = env
    bad = {**_headers(stack, "text/xml"), "X-Integration-Secret": "x" * 40}
    r = client.post("/api/v1/integrations/htng/inbound", content=b"<x/>", headers=bad)
    msg = parse_soap(r.content)
    assert r.status_code == 401 and msg.version is SoapVersion.SOAP11 and msg.fault.code == "soap:Client"


@pytest.mark.parametrize("ctype", ["application/json", "text/plain", ""])
def test_non_soap_media_type_rejected_after_authentication(env, ctype):
    stack, client, _, _ = env
    r = client.post("/api/v1/integrations/htng/inbound", content=_soap12(), headers=_headers(stack, ctype))
    assert r.status_code == 415
    assert stack.repo.list_messages(facility_scope=None) == []


def test_transient_intake_failure_is_503_so_clients_retry(env):
    stack, client, _, _ = env

    def down(*a, **k):
        raise ConnectionError("db down")

    stack.repo.accept = down
    r = client.post("/api/v1/integrations/htng/inbound", content=_soap12(),
                    headers=_headers(stack, "application/soap+xml"))
    assert r.status_code == 503


def test_media_type_detection():
    from app.integrations.api.router import soap_version_from_content_type as v
    from app.integrations.transport.soap import SoapVersion

    assert v("text/xml; charset=utf-8") is SoapVersion.SOAP11
    assert v("Application/SOAP+XML;action=x") is SoapVersion.SOAP12
    assert v(None) is None and v("application/xml") is None


# --- G4: grammar encodings must be ASCII-compatible (byte-level framing) ---------------
@pytest.mark.parametrize("encoding", ["utf-16", "utf-32", "utf-16-le", "cp500"])
def test_non_ascii_compatible_encodings_rejected(encoding):
    from app.integrations.adapters.fias.spec import VerificationStatus, WireGrammar

    with pytest.raises(ValueError):
        WireGrammar(encoding, 2, b"|", 2, VerificationStatus.PROVISIONAL_TEST, "x")


@pytest.mark.parametrize("encoding", ["ascii", "latin-1", "cp1252", "utf-8"])
def test_ascii_compatible_encodings_accepted(encoding):
    from app.integrations.adapters.fias.spec import VerificationStatus, WireGrammar

    assert WireGrammar(encoding, 2, b"|", 2, VerificationStatus.PROVISIONAL_TEST, "x").encoding == encoding


def test_separator_must_be_valid_in_encoding():
    from app.integrations.adapters.fias.spec import VerificationStatus, WireGrammar

    with pytest.raises(ValueError):
        WireGrammar("ascii", 2, b"\xff", 2, VerificationStatus.PROVISIONAL_TEST, "x")


# --- G5: same-timestamp arrivals must keep arrival order ------------------------------
def test_same_instant_arrivals_get_strictly_increasing_received_at():
    s = build_stack()  # fixed clock: every intake happens at the same instant
    ids = []
    for i in range(5):
        r = s.gateway.receive(json_msg(f"same-{i}", body={"room": "101", "n": i}), protocol=Protocol.TEST,
                              client=s.auth(), context=CTX)
        ids.append(r.message_id)
    stamps = [s.repo.get(i, facility_scope=None).received_at for i in ids]
    assert stamps == sorted(stamps) and len(set(stamps)) == 5


def test_ordering_follows_arrival_even_when_clock_does_not_advance():
    s = build_stack()
    h = s.handlers["test.guest_arrival"]
    h.ordered_by = "room"
    for i in range(6):
        s.gateway.receive(json_msg(f"o-{i}", body={"room": "101", "n": i}), protocol=Protocol.TEST,
                          client=s.auth(), context=CTX)
    s.clock.advance(1)  # real time passes before the worker runs
    for _ in range(10):
        s.worker.run_once()
    assert [e.body["n"] for e in h.seen] == [0, 1, 2, 3, 4, 5]
