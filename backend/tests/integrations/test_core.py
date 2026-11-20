"""Core contracts: hashing, correlation, masking, lifecycle, retry, envelope, errors."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.integrations.core import correlation, masking
from app.integrations.core.envelope import CanonicalEnvelope, Direction, MessageStatus, Protocol
from app.integrations.core.errors import (
    AuthenticationFailed,
    ErrorCategory,
    InvalidTransition,
    TransientFailure,
    ValidationFailed,
    classify,
)
from app.integrations.core.hashing import (
    CanonicalizationError,
    canonical_json,
    idempotency_fingerprint,
    payload_hash,
)
from app.integrations.core.lifecycle import ALLOWED, TERMINAL, assert_transition, can_transition
from app.integrations.core.retry import RetryPolicy, full_jitter

from .conftest import T0, make_envelope


# --- hashing ---------------------------------------------------------------
def test_canonical_json_is_key_order_independent():
    a = {"b": 1, "a": {"y": [1, 2], "x": "é"}}
    b = {"a": {"x": "é", "y": [1, 2]}, "b": 1}
    assert canonical_json(a) == canonical_json(b)
    assert payload_hash(a) == payload_hash(b)
    assert canonical_json(a) == '{"a":{"x":"é","y":[1,2]},"b":1}'.encode()


def test_hash_distinguishes_values_and_types():
    assert payload_hash({"a": 1}) != payload_hash({"a": "1"})
    assert payload_hash({"a": [1, 2]}) != payload_hash({"a": [2, 1]})
    assert payload_hash({"a": Decimal("1.10")}) != payload_hash({"a": Decimal("1.1")})


def test_hash_normalizes_uuid_and_aware_datetimes():
    u = uuid.uuid4()
    ist = timezone(timedelta(hours=5, minutes=30))
    assert payload_hash({"u": u, "t": datetime(2026, 1, 1, 5, 30, tzinfo=ist)}) == payload_hash(
        {"u": str(u), "t": "2026-01-01T00:00:00+00:00"}
    )


@pytest.mark.parametrize("bad", [{"x": float("nan")}, {"x": float("inf")}, {"x": datetime(2026, 1, 1)},
                                 {1: "non-string key"}, {"x": {1, 2}}])
def test_hash_rejects_non_deterministic_values(bad):
    with pytest.raises(CanonicalizationError):
        canonical_json(bad)


def test_idempotency_fingerprint_includes_message_type():
    assert idempotency_fingerprint("a.b", {"x": 1}) != idempotency_fingerprint("a.c", {"x": 1})


# --- correlation ---------------------------------------------------------------
def test_correlation_id_accepts_safe_and_replaces_unsafe():
    assert correlation.accept_correlation_id("abc-123:x.y") == "abc-123:x.y"
    replaced = correlation.accept_correlation_id("bad\nvalue<script>")
    assert "\n" not in replaced and len(replaced) == 32
    assert correlation.accept_correlation_id(None)
    assert correlation.accept_correlation_id("x" * 65) != "x" * 65


def test_correlation_scope_binds_and_resets():
    assert correlation.current_correlation_id() is None
    with correlation.correlation_scope("cid-1"):
        assert correlation.current_correlation_id() == "cid-1"
    assert correlation.current_correlation_id() is None


# --- masking ---------------------------------------------------------------
def test_masking_masks_sensitive_keys_recursively():
    data = {
        "guest_name": "Jane Roe", "room": "101", "contact": {"email": "j@x.io", "Phone-Number": "99999"},
        "items": [{"card_number": "4111111111111111"}], "cards": ["x"], "note": "VIP", "message_type": "x",
        "capacity": 2,
    }
    out = masking.mask_mapping(data)
    assert out["guest_name"] == "***" and out["room"] == "101"
    assert out["contact"] == {"email": "***", "Phone-Number": "***"}
    assert out["items"][0]["card_number"] == "***" and out["cards"] == "***"
    assert out["note"] == "***" and out["message_type"] == "x" and out["capacity"] == 2
    assert data["guest_name"] == "Jane Roe"  # input untouched


def test_masking_scrubs_free_text():
    text = "contact jane@example.com card 4111 1111 1111 1111 room 101"
    out = masking.mask_text(text)
    assert "jane@example.com" not in out and "4111" not in out and "room 101" in out


# --- lifecycle ---------------------------------------------------------------
def test_lifecycle_happy_path_and_retry_and_redrive():
    S = MessageStatus
    for a, b in [(S.RECEIVED, S.VALIDATED), (S.VALIDATED, S.PENDING), (S.PENDING, S.PROCESSING),
                 (S.PROCESSING, S.SUCCEEDED), (S.PROCESSING, S.RETRY_WAIT), (S.RETRY_WAIT, S.PROCESSING),
                 (S.PROCESSING, S.DEAD_LETTER), (S.DEAD_LETTER, S.PENDING), (S.PROCESSING, S.PROCESSING)]:
        assert can_transition(a, b)


@pytest.mark.parametrize("a,b", [
    ("SUCCEEDED", "PENDING"), ("REJECTED", "PENDING"), ("PENDING", "SUCCEEDED"),
    ("DEAD_LETTER", "PROCESSING"), ("RECEIVED", "PENDING"), ("RETRY_WAIT", "SUCCEEDED"),
])
def test_lifecycle_rejects_illegal_transitions(a, b):
    with pytest.raises(InvalidTransition):
        assert_transition(a, b)


def test_terminal_states_have_no_exits():
    assert all(not ALLOWED[s] for s in TERMINAL)


# --- retry ---------------------------------------------------------------
def test_retry_backoff_is_bounded_exponential():
    p = RetryPolicy(max_attempts=10, base_delay_seconds=5, max_delay_seconds=60)
    assert [p.delay_for(n) for n in range(1, 6)] == [5, 10, 20, 40, 60]


def test_retry_only_transient_and_within_budget():
    p = RetryPolicy(max_attempts=3, base_delay_seconds=5, max_delay_seconds=60)
    d = p.decide(TransientFailure("x"), attempts_made=1, now=T0)
    assert d.retry and d.next_attempt_at == T0 + timedelta(seconds=5)
    assert not p.decide(TransientFailure("x"), attempts_made=3, now=T0).retry
    assert not p.decide(ValidationFailed("x"), attempts_made=1, now=T0).retry
    assert not p.decide(AuthenticationFailed(), attempts_made=1, now=T0).retry


def test_retry_jitter_stays_in_bounds():
    p = RetryPolicy(max_attempts=5, base_delay_seconds=5, max_delay_seconds=60, jitter=full_jitter)
    for _ in range(50):
        assert 0 <= p.delay_for(4) <= 40


@pytest.mark.parametrize("kwargs", [{"max_attempts": 0}, {"base_delay_seconds": 0},
                                    {"base_delay_seconds": 10, "max_delay_seconds": 5}, {"multiplier": 0.5}])
def test_retry_policy_validates(kwargs):
    with pytest.raises(ValueError):
        RetryPolicy(**kwargs)


# --- errors ---------------------------------------------------------------
def test_unknown_exceptions_classify_as_transient_without_leaking_text():
    err = classify(RuntimeError("guest Jane Roe card 4111111111111111"))
    assert err.category is ErrorCategory.TRANSIENT and err.retryable
    assert "Jane" not in err.message and "4111" not in str(err.as_dict())


def test_authentication_failure_hides_reason_from_clients():
    err = AuthenticationFailed("client_disabled")
    assert "disabled" not in str(err.as_dict())
    assert err.reason == "client_disabled"


# --- envelope ---------------------------------------------------------------
def test_envelope_repr_never_contains_body():
    env = make_envelope(body={"guest_name": "Jane Roe"})
    assert "Jane" not in repr(env)
    assert "body" not in env.metadata()


def test_envelope_validates_fields():
    base = dict(idempotency_key="k", correlation_id="c", facility_id=uuid.uuid4(), client_id=uuid.uuid4(),
                protocol=Protocol.TEST, direction=Direction.INBOUND, schema_version="1", body={})
    with pytest.raises(ValidationError):
        CanonicalEnvelope(message_type="Bad Type", payload_hash="0" * 64, **base)
    with pytest.raises(ValidationError):
        CanonicalEnvelope(message_type="a.b", payload_hash="xyz", **base)
    with pytest.raises(ValidationError):
        CanonicalEnvelope(message_type="a.b", payload_hash="0" * 64, received_at=datetime(2026, 1, 1), **base)
    env = CanonicalEnvelope(message_type="a.b", payload_hash="0" * 64,
                            received_at=datetime(2026, 1, 1, tzinfo=UTC), **base)
    assert env.received_at.tzinfo is not None


# --- regression: `$` must not accept a trailing newline -----------------------------
@pytest.mark.parametrize("value", ["abc\n", "abc\r\n"])
def test_correlation_id_with_trailing_newline_is_replaced(value):
    assert correlation.accept_correlation_id(value) != value


def test_validators_reject_trailing_newline_everywhere():
    from app.integrations.core.envelope import is_valid_message_type
    from app.integrations.security.clients import CLIENT_CODE_PATTERN
    from app.integrations.security.facility import PROPERTY_CODE_PATTERN

    assert not is_valid_message_type("stay.check_in\n")
    assert CLIENT_CODE_PATTERN.fullmatch("pms-a\n") is None
    assert PROPERTY_CODE_PATTERN.fullmatch("HOTEL-A\n") is None
    base = dict(idempotency_key="k", correlation_id="c", facility_id=uuid.uuid4(), client_id=uuid.uuid4(),
                protocol=Protocol.TEST, direction=Direction.INBOUND, schema_version="1", body={})
    with pytest.raises(ValidationError):  # pydantic pattern fields too
        CanonicalEnvelope(message_type="stay.check_in\n", payload_hash="0" * 64, **base)
    with pytest.raises(ValidationError):
        CanonicalEnvelope(message_type="a.b", payload_hash="0" * 64 + "\n", **base)
