"""FIAS adapter: production is blocked; codec behaviour on the PROVISIONAL TEST spec."""

from __future__ import annotations

import uuid

import pytest

from app.integrations.adapters.base import AdapterReadiness
from app.integrations.adapters.fias import spec as fias_spec
from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.fias.codec import parse_record, serialize_record
from app.integrations.adapters.fias.spec import (
    FieldSpec,
    FiasSpecification,
    RecordSpec,
    VerificationStatus,
    WireGrammar,
)
from app.integrations.core.envelope import Direction, OutboundRequest, Protocol
from app.integrations.core.errors import (
    ProtocolError,
    UnsupportedMessage,
    ValidationFailed,
    VendorSpecificationBlocked,
)
from app.integrations.simulators.fixtures import PROVISIONAL_TEST_FIAS_SPEC as SPEC

from .conftest import CTX

IN = frozenset({Direction.INBOUND})


def adapter():
    return FIASAdapter(SPEC, allow_unverified=True, app_env="test")


# --- documentation gate ---------------------------------------------------------
def test_no_verified_fias_specification_ships():
    assert fias_spec.PRODUCTION_SPECIFICATION is None


def test_production_adapter_is_blocked_on_hf11():
    a = FIASAdapter()
    st = a.status()
    assert st.readiness is AdapterReadiness.BLOCKED and st.blocking_decisions == ("HF-11",)
    assert a.message_types(Direction.INBOUND) == frozenset()
    with pytest.raises(VendorSpecificationBlocked) as exc:
        a.decode(b"anything", CTX)
    assert exc.value.decision == "HF-11"
    with pytest.raises(VendorSpecificationBlocked):
        a.encode(OutboundRequest(protocol=Protocol.FIAS, message_type="test.room_state",
                                 facility_id=uuid.uuid4(), client_id=uuid.uuid4(), body={}))


def test_unverified_spec_refused_without_opt_in_and_in_production():
    with pytest.raises(VendorSpecificationBlocked):
        FIASAdapter(SPEC)
    with pytest.raises(VendorSpecificationBlocked):
        FIASAdapter(SPEC, allow_unverified=True, app_env="production")
    assert adapter().status().readiness is AdapterReadiness.TEST_ONLY


def test_provisional_fixture_is_marked_and_synthetic():
    assert SPEC.unverified_elements()  # never verified
    assert all(r.record_id.startswith("Z") for r in SPEC.records)
    assert all(r.message_type.startswith("test.") for r in SPEC.records)
    assert not {"GI", "GO", "GC", "WR"} & {r.record_id for r in SPEC.records}


def test_verified_spec_reports_ready():
    verified = FiasSpecification(
        name="X", version="1",
        grammar=WireGrammar("ascii", 2, b"|", 2, VerificationStatus.VERIFIED_OFFICIAL, "doc §1"),
        records=(RecordSpec("AA", "a.b", IN, (FieldSpec("F1", "f"),), VerificationStatus.VERIFIED_OFFICIAL, "doc §2"),),
    )
    assert FIASAdapter(verified).status().readiness is AdapterReadiness.READY


# --- parsing ---------------------------------------------------------------
def test_parse_valid_record_to_canonical():
    d = adapter().decode(b"ZA|MIm-1|PCHOTEL-A|RN101|GNJane Roe|SRres-9|", CTX)
    assert d.message_type == "test.guest_arrival"
    assert d.property_code == "HOTEL-A" and d.idempotency_key == "ZA:m-1"
    assert d.body == {"message_ref": "m-1", "property_code": "HOTEL-A", "room": "101",
                      "guest_name": "Jane Roe", "external_stay_ref": "res-9"}
    assert "Jane" not in repr(d)


def test_missing_mandatory_fields_never_fabricated():
    with pytest.raises(ValidationFailed) as exc:
        adapter().decode(b"ZA|MIm-1|PCHOTEL-A|", CTX)
    assert set(exc.value.detail["field_ids"]) == {"RN", "SR"}


def test_empty_mandatory_value_is_missing():
    with pytest.raises(ValidationFailed):
        adapter().decode(b"ZA|MIm-1|PCHOTEL-A|RN|SRx|", CTX)


@pytest.mark.parametrize("raw,exc_type,code", [
    (b"", ValidationFailed, "empty_record"),
    (b"Q", ProtocolError, "record_too_short"),
    (b"XX|MI1|", UnsupportedMessage, "unsupported_message"),
    (b"ZS|RN1|STx|", UnsupportedMessage, "unsupported_message"),  # outbound-only record
    (b"ZAMI1|", ProtocolError, "missing_separator"),
    (b"ZA|M|", ProtocolError, "bad_field_token"),
    (b"ZA|MI1|MI2|PCH|RN1|SR1|", ProtocolError, "duplicate_field"),
    (b"ZA|MI1|PCH|RN1|SR1|QQx|", ValidationFailed, "unknown_field"),
    (b"ZA|MI1|PCH|RN1-1|SR1|", ValidationFailed, "field_invalid_format"),
    (b"ZA|MI1|PCH|RN12345678901|SR1|", ValidationFailed, "field_too_long"),
    (b"ZA|MI1|PC\xff|RN1|SR1|", ProtocolError, "bad_encoding"),
    (b"ZA|MI1|PCH\x07|RN1|SR1|", ProtocolError, "control_characters"),
])
def test_malformed_records_rejected(raw, exc_type, code):
    with pytest.raises(exc_type) as exc:
        adapter().decode(raw, CTX)
    assert exc.value.code == code


def test_error_details_never_echo_values():
    with pytest.raises(ValidationFailed) as exc:
        adapter().decode(b"ZA|MI1|PCH|RN1|SR1|GN" + b"Z" * 200 + b"|", CTX)
    assert "ZZZZ" not in str(exc.value.as_dict())


def test_unknown_record_id_echo_is_sanitized():
    with pytest.raises(UnsupportedMessage) as exc:
        parse_record(b"\x7fq|", SPEC)
    assert exc.value.detail["record_id"] == "?q"


def test_unsupported_status_records_are_not_parsed():
    spec = FiasSpecification(
        name="X", version="1", grammar=SPEC.grammar,
        records=(RecordSpec("ZQ", "a.b", IN, (FieldSpec("F1", "f"),), VerificationStatus.UNSUPPORTED, "doc"),),
    )
    with pytest.raises(UnsupportedMessage):
        parse_record(b"ZQ|F1x|", spec)
    assert FIASAdapter(spec, allow_unverified=True, app_env="test").message_types(Direction.INBOUND) == frozenset()


# --- serialisation ---------------------------------------------------------------
def test_serialize_outbound_record_and_roundtrip_grammar():
    a = adapter()
    req = OutboundRequest(protocol=Protocol.FIAS, message_type="test.room_state",
                          facility_id=uuid.uuid4(), client_id=uuid.uuid4(), body={"room": "101", "state": "clean"})
    assert a.encode(req) == b"ZS|RN101|STclean|"


@pytest.mark.parametrize("body,code", [
    ({"room": "1|01", "state": "clean"}, "field_contains_separator"),
    ({"room": "101\n", "state": "clean"}, "field_contains_separator"),
    ({"room": "101"}, "missing_mandatory_fields"),
    ({"room": "101", "state": "clean", "extra": "x"}, "unknown_body_field"),
    ({"room": 101, "state": "clean"}, "field_not_text"),
    ({"room": "101", "state": "CLEAN"}, "field_invalid_format"),
])
def test_serialize_rejects_bad_bodies(body, code):
    req = OutboundRequest(protocol=Protocol.FIAS, message_type="test.room_state",
                          facility_id=uuid.uuid4(), client_id=uuid.uuid4(), body=body)
    with pytest.raises(ValidationFailed) as exc:
        adapter().encode(req)
    assert exc.value.code == code


def test_serialize_inbound_only_record_refused():
    with pytest.raises(UnsupportedMessage):
        serialize_record(SPEC.record("ZA"), {"MI": "1"}, SPEC)
    req = OutboundRequest(protocol=Protocol.FIAS, message_type="test.guest_arrival",
                          facility_id=uuid.uuid4(), client_id=uuid.uuid4(), body={})
    with pytest.raises(UnsupportedMessage):
        adapter().encode(req)


# --- spec validation ---------------------------------------------------------------
@pytest.mark.parametrize("build", [
    lambda: RecordSpec("ZZ", "Bad Type", IN, (), VerificationStatus.PROVISIONAL_TEST, "x"),
    lambda: RecordSpec("ZZ", "a.b", IN, (FieldSpec("F1", "a"), FieldSpec("F1", "b")), VerificationStatus.PROVISIONAL_TEST, "x"),
    lambda: RecordSpec("ZZ", "a.b", IN, (FieldSpec("F1", "a"),), VerificationStatus.PROVISIONAL_TEST, "x", idempotency_fields=("F9",)),
    lambda: RecordSpec("ZZ", "a.b", frozenset(), (), VerificationStatus.PROVISIONAL_TEST, "x"),
    lambda: FiasSpecification("X", "1", SPEC.grammar, (RecordSpec("ZZZ", "a.b", IN, (), VerificationStatus.PROVISIONAL_TEST, "x"),)),
    lambda: WireGrammar("no-such-codec", 2, b"|", 2, VerificationStatus.PROVISIONAL_TEST, "x"),
    lambda: WireGrammar("ascii", 2, b"", 2, VerificationStatus.PROVISIONAL_TEST, "x"),
    lambda: FieldSpec("F1", "a", pattern="("),
])
def test_specification_is_validated(build):
    with pytest.raises((ValueError, LookupError)):
        build()


def test_records_without_idempotency_fields_yield_no_key():
    spec = FiasSpecification(
        name="X", version="1", grammar=SPEC.grammar,
        records=(RecordSpec("ZN", "a.b", IN, (FieldSpec("F1", "f"),), VerificationStatus.PROVISIONAL_TEST, "x"),),
    )
    d = FIASAdapter(spec, allow_unverified=True, app_env="test").decode(b"ZN|F1v|", CTX)
    assert d.idempotency_key is None  # the exchange then rejects it: no fabricated key
