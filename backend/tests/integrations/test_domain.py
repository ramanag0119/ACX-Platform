"""Approval-gated stay domain adapter. No live HMS writes: services are mocked."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.integrations.core.envelope import Direction, Protocol
from app.integrations.core.errors import (
    ApprovalRequired,
    ErrorCategory,
    FacilityAuthorizationError,
    PermanentFailure,
    TransientFailure,
    ValidationFailed,
)
from app.integrations.domain import approvals
from app.integrations.domain.approvals import Decision, DecisionStatus, LiveWriteGate
from app.integrations.domain.stays import CHECK_IN, CHECK_OUT, StayDomainAdapter, StayEventHandler, plan
from app.integrations.exchange.registry import HandlerContext
from app.services.writes import Conflict

from .conftest import FACILITY_A, FACILITY_B, make_envelope

STAY = uuid.UUID("dddddddd-0000-4000-8000-000000000001")
ACTOR = uuid.UUID("eeeeeeee-0000-4000-8000-000000000001")


def approved_register():
    return {
        did: Decision(did, d.subject, DecisionStatus.APPROVED, evidence="TEST ONLY - not real approval")
        for did, d in approvals.DECISIONS.items()
    }


class FakeServices:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def check_in(self, db, stay_id, *, actor_id, when=None):
        self.calls.append(("check_in", db, stay_id, actor_id, when))
        if self.fail:
            raise self.fail

    def check_out(self, db, stay_id, *, actor_id, when=None):
        self.calls.append(("check_out", db, stay_id, actor_id, when))


class Resolver:
    def __init__(self, stay=STAY):
        self.stay = stay
        self.calls = []

    def resolve_stay(self, session, *, client_id, facility_id, external_ref):
        self.calls.append((client_id, facility_id, external_ref))
        return self.stay


def env(mtype=CHECK_IN, body=None, facility=FACILITY_A):
    return make_envelope(mtype=mtype, facility=facility,
                         body=body if body is not None else {"external_stay_ref": "PMS-123",
                                                             "occurred_at": "2026-11-19T10:00:00+05:30"})


def open_adapter(services=None, resolver=None, facilities=frozenset({FACILITY_A}), actor=ACTOR, state=None):
    return StayDomainAdapter(
        gate=LiveWriteGate(enabled_flag=True, register=approved_register()),
        resolver=resolver or Resolver(),
        actor_id=actor,
        services=services or FakeServices(),
        facility_lookup=lambda session, stay_id: set(facilities),
        state_lookup=lambda session, stay_id: state,
    )


# --- the real register ---------------------------------------------------------------
def test_no_decision_is_approved_in_the_repository():
    assert all(d.status is not DecisionStatus.APPROVED for d in approvals.DECISIONS.values())
    assert set(approvals.REQUIRED_FOR_LIVE_WRITES) == {"HF-01", "HF-02", "HF-05", "HF-19"}


def test_gate_is_closed_by_default_even_with_flag():
    gate = LiveWriteGate(enabled_flag=True)
    assert not gate.is_open()
    assert gate.blocking() == ["HF-01", "HF-02", "HF-05", "HF-19"]
    closed = LiveWriteGate(enabled_flag=False)
    assert closed.blocking()[0] == "INTEGRATION_LIVE_DOMAIN_WRITES"


def test_approval_without_evidence_does_not_count():
    reg = {k: Decision(k, "x", DecisionStatus.APPROVED, evidence=None) for k in approvals.DECISIONS}
    assert not LiveWriteGate(enabled_flag=True, register=reg).is_open()


def test_default_wiring_blocks_live_writes_and_calls_no_service():
    services = FakeServices()
    adapter = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=False), resolver=Resolver(), actor_id=ACTOR,
                                services=services)
    with pytest.raises(ApprovalRequired) as exc:
        adapter.apply(env(), session=object())
    assert exc.value.category is ErrorCategory.APPROVAL_BLOCKED and not exc.value.retryable
    assert services.calls == []


# --- with a TEST-ONLY open gate ---------------------------------------------------------
def test_check_in_calls_existing_hms_service_with_actor_and_utc_time():
    services, resolver = FakeServices(), Resolver()
    session = object()
    out = open_adapter(services, resolver).apply(env(), session)
    assert out == {"stay_id": str(STAY), "action": "check_in", "already_applied": False}
    action, db, stay_id, actor, when = services.calls[0]
    assert (action, db, stay_id, actor) == ("check_in", session, STAY, ACTOR)
    assert when == datetime(2026, 11, 19, 4, 30, tzinfo=UTC)
    assert resolver.calls[0][1] == FACILITY_A and resolver.calls[0][2] == "PMS-123"


def test_check_out_routes_to_check_out():
    services = FakeServices()
    open_adapter(services).apply(env(CHECK_OUT, {"external_stay_ref": "PMS-1"}), object())
    assert services.calls[0][0] == "check_out" and services.calls[0][4] is None


def test_missing_actor_or_resolver_blocks():
    with pytest.raises(ApprovalRequired) as exc:
        open_adapter(actor=None).apply(env(), object())
    assert exc.value.decisions == ["HF-18"]
    adapter = open_adapter()
    adapter._resolver = None  # noqa: SLF001
    with pytest.raises(ApprovalRequired) as exc:
        adapter.apply(env(), object())
    assert exc.value.decisions == ["HF-02"]


def test_stay_in_another_facility_is_rejected():
    services = FakeServices()
    with pytest.raises(FacilityAuthorizationError):
        open_adapter(services, facilities={FACILITY_B}).apply(env(), object())
    with pytest.raises(FacilityAuthorizationError):
        open_adapter(services, facilities={FACILITY_A, FACILITY_B}).apply(env(), object())
    assert services.calls == []


def test_unknown_stay_is_transient_and_roomless_stay_permanent():
    with pytest.raises(TransientFailure):
        open_adapter(resolver=Resolver(stay=None)).apply(env(), object())
    with pytest.raises(PermanentFailure):
        open_adapter(facilities=set()).apply(env(), object())


def test_hms_business_rule_rejection_is_permanent_and_not_echoed():
    services = FakeServices(fail=Conflict("This stay is already checked in."))
    with pytest.raises(PermanentFailure) as exc:
        open_adapter(services).apply(env(), object())
    assert exc.value.code == "hms_business_rule" and exc.value.detail == {"rule": "Conflict"}


def test_no_session_is_refused():
    with pytest.raises(PermanentFailure):
        open_adapter().apply(env(), None)


@pytest.mark.parametrize("body,code", [
    ({}, "external_stay_ref_missing"),
    ({"external_stay_ref": "  "}, "external_stay_ref_missing"),
    ({"external_stay_ref": "x" * 101}, "external_stay_ref_missing"),
    ({"external_stay_ref": "a", "occurred_at": "yesterday"}, "occurred_at_invalid"),
    ({"external_stay_ref": "a", "occurred_at": "2026-11-19T10:00:00"}, "occurred_at_naive"),
    ({"external_stay_ref": "a", "occurred_at": 5}, "occurred_at_invalid"),
])
def test_plan_validates_without_fabricating(body, code):
    with pytest.raises(ValidationFailed) as exc:
        plan(env(body=body))
    assert exc.value.code == code


def test_invalid_message_rejected_before_gate():
    adapter = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=False), resolver=None, actor_id=None)
    with pytest.raises(ValidationFailed):
        adapter.apply(env(body={}), None)


def test_handler_wraps_adapter_and_validates_type():
    services = FakeServices()
    handler = StayEventHandler(CHECK_IN, open_adapter(services))
    result = handler.handle(env(), HandlerContext(session=object()))
    assert result.summary["action"] == "check_in"
    with pytest.raises(ValueError):
        StayEventHandler("stay.teleport", open_adapter())


def test_envelope_types_used_are_canonical_not_vendor():
    e = env()
    assert e.protocol is Protocol.TEST and e.direction is Direction.INBOUND
    assert CHECK_IN == "stay.check_in" and CHECK_OUT == "stay.check_out"


# --- business-level idempotency (D2) and in-transaction audit -------------------------
from app.integrations.domain.stays import StayState  # noqa: E402

IN_HOUSE = StayState(datetime(2026, 11, 19, tzinfo=UTC), None, "active")
DEPARTED = StayState(datetime(2026, 11, 18, tzinfo=UTC), datetime(2026, 11, 19, tzinfo=UTC), "checked out")


def test_repeated_check_in_is_a_noop_not_a_dead_letter():
    services = FakeServices()
    out = open_adapter(services, state=IN_HOUSE).apply(env(), object())
    assert out["already_applied"] is True and services.calls == []


def test_repeated_check_out_is_a_noop():
    services = FakeServices()
    out = open_adapter(services, state=DEPARTED).apply(env(CHECK_OUT, {"external_stay_ref": "x"}), object())
    assert out["already_applied"] is True and services.calls == []


def test_check_in_of_departed_stay_still_reaches_hms_rules():
    services = FakeServices(fail=Conflict("A stay with status 'checked out' cannot be checked in."))
    with pytest.raises(PermanentFailure):
        open_adapter(services, state=DEPARTED).apply(env(), object())
    assert services.calls and services.calls[0][0] == "check_in"


def test_handler_emits_audit_draft_with_actor_and_summary():
    ctx = HandlerContext(session=object())
    StayEventHandler(CHECK_IN, open_adapter(state=IN_HOUSE)).handle(env(), ctx)
    (draft,) = ctx.audits
    assert draft.action == "domain.stay.check_in" and draft.actor_type == "system"
    assert draft.actor_id == str(ACTOR) and draft.detail["already_applied"] is True


def test_gate_still_blocks_before_state_is_read():
    seen = []
    adapter = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=False), resolver=Resolver(), actor_id=ACTOR,
                                services=FakeServices(), state_lookup=lambda s, i: seen.append(i))
    with pytest.raises(ApprovalRequired):
        adapter.apply(env(), object())
    assert seen == []
