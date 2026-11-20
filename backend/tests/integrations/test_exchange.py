"""ExchangeAdapter: registration, routing, rejection paths, duplicates, outbound."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry
from app.integrations.core.envelope import Direction, IntakeOutcome, MessageStatus, OutboundRequest, Protocol
from app.integrations.core.errors import (
    FacilityAuthorizationError,
    PermanentFailure,
    TransientFailure,
    UnsupportedMessage,
    UnsupportedProtocol,
    VendorSpecificationBlocked,
)
from app.integrations.exchange.registry import AdapterRegistry, HandlerRegistry

from .conftest import CLIENT_A, CTX, FACILITY_A, FACILITY_B, JsonTestAdapter, RecordingHandler, json_msg


# --- registries ---------------------------------------------------------------
def test_adapter_registration_is_unique():
    reg = AdapterRegistry()
    reg.register(JsonTestAdapter())
    with pytest.raises(ValueError):
        reg.register(JsonTestAdapter())


def test_unregistered_and_unknown_protocols_are_explicit():
    reg = AdapterRegistry()
    with pytest.raises(UnsupportedProtocol):
        reg.get(Protocol.FIAS, Direction.INBOUND)
    with pytest.raises(UnsupportedProtocol):
        reg.get("smtp", Direction.INBOUND)


def test_blocked_adapters_report_their_decision():
    reg = AdapterRegistry()
    reg.register(FIASAdapter())
    reg.register(HTNGAdapter(SchemaRegistry()))
    with pytest.raises(VendorSpecificationBlocked) as fias:
        reg.get(Protocol.FIAS, Direction.INBOUND)
    with pytest.raises(VendorSpecificationBlocked) as htng:
        reg.get(Protocol.HTNG, Direction.OUTBOUND)
    assert fias.value.decision == "HF-11" and htng.value.decision == "HF-07"


def test_direction_not_supported():
    reg = AdapterRegistry()
    reg.register(JsonTestAdapter(outbound=()))
    with pytest.raises(UnsupportedProtocol):
        reg.get(Protocol.TEST, Direction.OUTBOUND)


def test_handler_registry_unique_and_unknown():
    reg = HandlerRegistry()
    reg.register(RecordingHandler("a.b"))
    with pytest.raises(ValueError):
        reg.register(RecordingHandler("a.b"))
    with pytest.raises(UnsupportedMessage):
        reg.get("a.c")
    assert reg.message_types() == ["a.b"]


# --- inbound ---------------------------------------------------------------
def test_accepts_and_routes_to_handler(stack):
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX,
                              correlation_id="corr-42")
    assert r.outcome is IntakeOutcome.ACCEPTED and r.correlation_id == "corr-42"
    msg = stack.repo.get(r.message_id, facility_scope=None)
    assert msg.status is MessageStatus.PENDING and msg.facility_id == FACILITY_A and msg.client_id == CLIENT_A
    summary = stack.worker.run_once()
    assert summary.succeeded == 1
    seen = stack.handlers["test.guest_arrival"].seen[0]
    assert seen.correlation_id == "corr-42" and seen.body["room"] == "101"
    assert stack.repo.get(r.message_id, facility_scope=None).status is MessageStatus.SUCCEEDED


def test_unsafe_correlation_id_replaced(stack):
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX,
                              correlation_id="evil\r\nheader")
    assert "\n" not in r.correlation_id


@pytest.mark.parametrize("raw,code", [
    (b"", "empty_message"),
    (b"{not json", "malformed_json"),
    (json.dumps({"type": "nope", "id": "1"}).encode(), "unknown_type"),
    (b"x" * (64 * 1024 + 1), "frame_too_large"),
])
def test_malformed_inputs_rejected_not_persisted(stack, raw, code):
    r = stack.gateway.receive(raw, protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.error["code"] == code
    assert stack.repo.list_messages(facility_scope=None) == []


def test_unsupported_message_type_without_handler():
    from .conftest import build_stack

    s = build_stack()
    s.gateway.adapters  # noqa: B018
    raw = json.dumps({"type": "test.guest_departure", "id": "1", "property": "HOTEL-A"}).encode()
    # Replace handler registry with one lacking the departure handler.
    from app.integrations.exchange.registry import HandlerRegistry

    hr = HandlerRegistry()
    hr.register(s.handlers["test.guest_arrival"])
    s.gateway.handlers = hr
    r = s.gateway.receive(raw, protocol=Protocol.TEST, client=s.auth(), context=CTX)
    assert r.error["code"] == "unsupported_message"


def test_missing_idempotency_key_rejected(stack):
    raw = json.dumps({"type": "test.guest_arrival", "property": "HOTEL-A", "body": {}}).encode()
    r = stack.gateway.receive(raw, protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.error["code"] == "idempotency_key_missing"


def test_unregistered_protocol_rejected_cleanly(stack):
    from app.integrations.exchange.registry import AdapterRegistry

    stack.gateway.adapters = AdapterRegistry()
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.error["code"] == "unsupported_protocol"


def test_client_not_permitted_for_protocol_at_receive(stack):
    from app.integrations.security.clients import AuthenticatedClient

    limited = AuthenticatedClient(CLIENT_A, "pms-a", frozenset({Protocol.FIAS}))
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=limited, context=CTX)
    assert r.error["category"] == "security"


# --- duplicates ---------------------------------------------------------------
def test_genuine_duplicate_returns_original_id_and_is_processed_once(stack):
    a = stack.gateway.receive(json_msg("dup"), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    b = stack.gateway.receive(json_msg("dup"), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert a.outcome is IntakeOutcome.ACCEPTED and b.outcome is IntakeOutcome.DUPLICATE
    assert a.message_id == b.message_id
    stack.worker.run_once()
    stack.worker.run_once()
    assert len(stack.handlers["test.guest_arrival"].seen) == 1


def test_duplicate_with_reordered_json_keys_is_still_duplicate(stack):
    raw1 = json.dumps({"type": "test.guest_arrival", "id": "k", "property": "HOTEL-A",
                       "body": {"a": 1, "b": {"x": 1, "y": 2}}}).encode()
    raw2 = json.dumps({"property": "HOTEL-A", "body": {"b": {"y": 2, "x": 1}, "a": 1},
                       "id": "k", "type": "test.guest_arrival"}).encode()
    stack.gateway.receive(raw1, protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    r = stack.gateway.receive(raw2, protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.DUPLICATE


def test_same_key_different_content_is_conflict(stack):
    stack.gateway.receive(json_msg("k", body={"room": "101"}), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    r = stack.gateway.receive(json_msg("k", body={"room": "102"}), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.error["code"] == "idempotency_conflict"
    assert len(stack.repo.list_messages(facility_scope=None)) == 1


def test_same_key_different_type_is_conflict(stack):
    stack.gateway.receive(json_msg("k"), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    r = stack.gateway.receive(json_msg("k", type_="test.guest_departure"), protocol=Protocol.TEST,
                              client=stack.auth(), context=CTX)
    assert r.error["code"] == "idempotency_conflict"


# --- handler failures ---------------------------------------------------------
def test_handler_failure_retries_then_dead_letters(stack):
    h = stack.handlers["test.guest_arrival"]
    h.failures.extend([TransientFailure("t1"), TransientFailure("t2"), TransientFailure("t3")])
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert stack.worker.run_once().retried == 1
    msg = stack.repo.get(r.message_id, facility_scope=None)
    assert msg.status is MessageStatus.RETRY_WAIT and msg.next_attempt_at == stack.clock.now + timedelta(seconds=10)
    assert stack.worker.run_once().claimed == 0  # not due yet
    stack.clock.advance(10)
    assert stack.worker.run_once().retried == 1
    stack.clock.advance(20)
    assert stack.worker.run_once().dead_lettered == 1
    msg = stack.repo.get(r.message_id, facility_scope=None)
    assert msg.status is MessageStatus.DEAD_LETTER and msg.attempt_count == 3
    assert msg.last_error_code == "transient_failure"


def test_permanent_failure_dead_letters_immediately(stack):
    stack.handlers["test.guest_arrival"].failures.append(PermanentFailure("no"))
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert stack.worker.run_once().dead_lettered == 1
    assert stack.repo.get(r.message_id, facility_scope=None).attempt_count == 1


def test_unexpected_exception_is_bounded(stack):
    stack.handlers["test.guest_arrival"].failures.extend([KeyError("x")] * 5)
    stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    for _ in range(5):
        stack.worker.run_once()
        stack.clock.advance(120)
    msgs = stack.repo.list_messages(facility_scope=None)
    assert msgs[0].status is MessageStatus.DEAD_LETTER and msgs[0].last_error_code == "unexpected_error"


# --- outbound ---------------------------------------------------------------
def test_successful_processing_emits_outbox_and_relay_sends(stack):
    stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    stack.worker.run_once()
    out = stack.repo.list_outbox(facility_scope=None)
    assert len(out) == 1 and out[0].status == "PENDING" and out[0].facility_id == FACILITY_A
    assert stack.relay.run_once().succeeded == 1
    assert json.loads(stack.sent[0]) == {"type": "test.receipt", "body": {"outcome": "ok"}}
    assert stack.repo.list_outbox(facility_scope=None)[0].status == "SENT"


def test_request_outbound_enqueues_after_authorization(stack):
    req = OutboundRequest(protocol=Protocol.TEST, message_type="test.receipt", facility_id=FACILITY_A,
                          client_id=CLIENT_A, body={"outcome": "ok"})
    outbox_id = stack.gateway.request_outbound(req)
    assert stack.repo.list_outbox(facility_scope={FACILITY_A})[0].outbox_id == outbox_id


def test_request_outbound_rejects_unmapped_facility(stack):
    req = OutboundRequest(protocol=Protocol.TEST, message_type="test.receipt", facility_id=FACILITY_B,
                          client_id=CLIENT_A, body={})
    with pytest.raises(FacilityAuthorizationError):
        stack.gateway.request_outbound(req)


def test_request_outbound_rejects_unsupported_type(stack):
    req = OutboundRequest(protocol=Protocol.TEST, message_type="test.unknown", facility_id=FACILITY_A,
                          client_id=CLIENT_A, body={})
    with pytest.raises(UnsupportedMessage):
        stack.gateway.request_outbound(req)


def test_relay_retries_and_dead_letters_outbound(stack):
    stack.relay._senders[Protocol.TEST].failures.extend([TransientFailure("down"), PermanentFailure("bad")])
    stack.gateway.request_outbound(OutboundRequest(protocol=Protocol.TEST, message_type="test.receipt",
                                                   facility_id=FACILITY_A, client_id=CLIENT_A, body={}))
    assert stack.relay.run_once().retried == 1
    stack.clock.advance(10)
    assert stack.relay.run_once().dead_lettered == 1
    assert stack.repo.list_outbox(facility_scope=None)[0].status == "DEAD_LETTER"


def test_relay_without_sender_leaves_rows_pending(stack):
    """Changed contract (operational-completion sprint): a relay claims only the
    protocols it has a sender for. A row nobody can deliver stays PENDING (and
    the dashboard reports it as queued without a sender) instead of being
    dead-lettered with sender_not_configured -- which needed a redrive later
    for a message that never failed."""
    stack.relay._senders.clear()
    stack.gateway.request_outbound(OutboundRequest(protocol=Protocol.TEST, message_type="test.receipt",
                                                   facility_id=FACILITY_A, client_id=CLIENT_A, body={}))
    summary = stack.relay.run_once()
    assert (summary.claimed, summary.dead_lettered) == (0, 0)
    (row,) = stack.repo.list_outbox(facility_scope=None)
    assert row.status == "PENDING" and row.attempt_count == 0
