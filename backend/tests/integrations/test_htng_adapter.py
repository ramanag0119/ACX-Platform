"""HTNG: XML security, SOAP handling, schema registry, adapter, SOAP transport."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET

import httpx
import pytest

from app.integrations.adapters.base import AdapterReadiness
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry, StructuralValidator, XsdValidator
from app.integrations.core.envelope import Direction, OutboundRequest, Protocol
from app.integrations.core.errors import (
    ApprovalRequired,
    FrameTooLarge,
    PermanentFailure,
    ProtocolError,
    TransientFailure,
    TransportError,
    UnsupportedMessage,
    ValidationFailed,
    VendorSpecificationBlocked,
)
from app.integrations.simulators.fixtures import (
    PROVISIONAL_TEST_XML_PROFILE as PROFILE,
)
from app.integrations.simulators.fixtures import (
    TEST_XML_NS,
    generic_arrival_soap,
)
from app.integrations.transport.soap import (
    SOAP11_NS,
    SOAP12_NS,
    SoapEndpoint,
    SoapTransport,
    SoapVersion,
    build_soap_envelope,
    parse_soap,
)
from app.integrations.transport.xml_security import UnsafeXml, XmlLimits, parse_untrusted_xml

from .conftest import CTX


def make_adapter():
    reg = SchemaRegistry(allow_unverified=True, app_env="test")
    reg.register(PROFILE)
    return HTNGAdapter(reg, profile_id="acx-generic-xml-test", version="0")


# --- XML security ---------------------------------------------------------------
XXE = b"""<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>"""
LAUGHS = (b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">'
          b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;">]><l>&c;</l>')
PARAM = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % p SYSTEM "http://evil/x.dtd"> %p;]><r/>'
EXTERNAL_DTD = b'<?xml version="1.0"?><!DOCTYPE r SYSTEM "http://evil/x.dtd"><r/>'


@pytest.mark.parametrize("doc", [XXE, LAUGHS, PARAM, EXTERNAL_DTD])
def test_dtds_and_entities_are_refused(doc):
    with pytest.raises(UnsafeXml):
        parse_untrusted_xml(doc)


def test_size_limit_checked_before_parsing():
    with pytest.raises(FrameTooLarge):
        parse_untrusted_xml(b"<a>" + b"x" * 2000 + b"</a>", limits=XmlLimits(max_bytes=1000))


def test_depth_and_element_limits():
    deep = b"<a>" * 100 + b"</a>" * 100
    with pytest.raises(UnsafeXml):
        parse_untrusted_xml(deep, limits=XmlLimits(max_depth=50))
    wide = b"<a>" + b"<b/>" * 500 + b"</a>"
    with pytest.raises(UnsafeXml):
        parse_untrusted_xml(wide, limits=XmlLimits(max_elements=100))
    attrs = b"<a " + b" ".join(f'x{i}="1"'.encode() for i in range(80)) + b"/>"
    with pytest.raises(UnsafeXml):
        parse_untrusted_xml(attrs)


@pytest.mark.parametrize("doc", [b"<a>", b"<a></b>", b"not xml", b"<a>&undefined;</a>"])
def test_malformed_xml(doc):
    with pytest.raises(ProtocolError):
        parse_untrusted_xml(doc)


def test_empty_and_non_bytes():
    with pytest.raises(ValidationFailed):
        parse_untrusted_xml(b"")
    with pytest.raises(ProtocolError):
        parse_untrusted_xml("<a/>")  # type: ignore[arg-type]


def test_namespace_allow_list():
    doc = b'<a xmlns="urn:ok"><b xmlns="urn:evil"/></a>'
    with pytest.raises(ValidationFailed):
        parse_untrusted_xml(doc, allowed_namespaces=frozenset({"urn:ok"}))
    assert parse_untrusted_xml(b'<a xmlns="urn:ok"/>', allowed_namespaces=frozenset({"urn:ok"})) is not None


# --- SOAP ---------------------------------------------------------------
def test_parse_soap11_and_soap12_envelopes():
    for ns, ver in ((SOAP11_NS, SoapVersion.SOAP11), (SOAP12_NS, SoapVersion.SOAP12)):
        doc = f'<e:Envelope xmlns:e="{ns}"><e:Header><h/></e:Header><e:Body><x xmlns="urn:t"/></e:Body></e:Envelope>'
        msg = parse_soap(doc.encode())
        assert msg.version is ver and msg.body.tag == "{urn:t}x" and len(msg.headers) == 1


@pytest.mark.parametrize("doc,code", [
    (b"<Envelope/>", "not_soap_envelope"),
    (f'<e:Envelope xmlns:e="{SOAP11_NS}"/>'.encode(), "soap_body_missing"),
    (f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><a/><b/></e:Body></e:Envelope>'.encode(), "soap_body_multiple"),
    (f'<e:Envelope xmlns:e="{SOAP11_NS}"><x/><e:Body/></e:Envelope>'.encode(), "soap_envelope_invalid"),
])
def test_invalid_soap_structures(doc, code):
    with pytest.raises(ProtocolError) as exc:
        parse_soap(doc)
    assert exc.value.code == code


def test_soap_fault_parsing_is_truncated_and_masked():
    long_reason = "guest jane@example.com card 4111111111111111 " + "x" * 1000
    doc = (f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><e:Fault><faultcode>e:Client</faultcode>'
           f"<faultstring>{long_reason}</faultstring></e:Fault></e:Body></e:Envelope>").encode()
    msg = parse_soap(doc)
    assert msg.body is None and msg.fault.code == "e:Client"
    assert len(msg.fault.reason) <= 256 and "jane@" not in msg.fault.reason and "4111" not in msg.fault.reason


def test_soap12_fault():
    doc = (f'<e:Envelope xmlns:e="{SOAP12_NS}"><e:Body><e:Fault><e:Code><e:Value>e:Receiver</e:Value></e:Code>'
           f'<e:Reason><e:Text xml:lang="en">down</e:Text></e:Reason></e:Fault></e:Body></e:Envelope>').encode()
    fault = parse_soap(doc).fault
    assert fault.code == "e:Receiver" and fault.reason == "down"


def test_build_soap_envelope_roundtrip():
    body = ET.Element("{urn:t}x")
    data = build_soap_envelope(body, version=SoapVersion.SOAP12)
    assert parse_soap(data).body.tag == "{urn:t}x"


# --- registry / adapter gate ---------------------------------------------------------
def test_production_htng_adapter_blocked_on_hf07():
    a = HTNGAdapter(SchemaRegistry())
    assert a.status().readiness is AdapterReadiness.BLOCKED
    assert "HF-07" in a.status().blocking_decisions
    with pytest.raises(VendorSpecificationBlocked):
        a.decode(b"<x/>", CTX)


def test_registry_refuses_unverified_profiles_and_production_opt_in():
    with pytest.raises(VendorSpecificationBlocked):
        SchemaRegistry().register(PROFILE)
    with pytest.raises(VendorSpecificationBlocked):
        SchemaRegistry(allow_unverified=True, app_env="production")
    reg = SchemaRegistry(allow_unverified=True, app_env="test")
    reg.register(PROFILE)
    with pytest.raises(ValueError):
        reg.register(PROFILE)
    with pytest.raises(VendorSpecificationBlocked):
        reg.resolve("acx-generic-xml-test", "9")


def test_generic_profile_is_not_htng():
    assert PROFILE.status == "provisional_test" and TEST_XML_NS.startswith("urn:acx:test:")
    assert make_adapter().status().readiness is AdapterReadiness.TEST_ONLY


def test_xsd_validation_requires_approved_dependency():
    with pytest.raises(ApprovalRequired) as exc:
        XsdValidator(b"<xs:schema/>")
    assert "HF-39" in exc.value.decisions


# --- decode / encode ---------------------------------------------------------------
def test_decode_generic_fixture_to_canonical():
    d = make_adapter().decode(
        generic_arrival_soap(message_ref="r1", property_code="HOTEL-A", room="101", stay_ref="s9", guest_name="Jane"),
        CTX,
    )
    assert d.protocol is Protocol.HTNG and d.message_type == "test.guest_arrival"
    assert d.property_code == "HOTEL-A" and d.idempotency_key == "r1"
    assert d.body["external_stay_ref"] == "s9" and d.schema_version == "acx-generic-xml-test/0"


def test_decode_rejects_missing_elements_unknown_ops_and_foreign_namespaces():
    a = make_adapter()
    missing = generic_arrival_soap(message_ref="r1", property_code="H", room="1", stay_ref="s").replace(
        b"<t:StayRef>s</t:StayRef>", b"")
    with pytest.raises(ValidationFailed) as exc:
        a.decode(missing, CTX)
    assert exc.value.code == "missing_required_elements"

    unknown = (f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><t:Other xmlns:t="{TEST_XML_NS}"/></e:Body>'
               "</e:Envelope>").encode()
    with pytest.raises(UnsupportedMessage):
        a.decode(unknown, CTX)

    foreign = generic_arrival_soap(message_ref="r1", property_code="H", room="1", stay_ref="s",
                                   extra='<z:Smuggle xmlns:z="urn:evil">x</z:Smuggle>')
    with pytest.raises(ValidationFailed) as exc:
        a.decode(foreign, CTX)
    assert exc.value.code == "unexpected_namespace"


def test_inbound_fault_and_empty_body_rejected():
    a = make_adapter()
    fault = (f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><e:Fault><faultcode>e:Server</faultcode>'
             "<faultstring>x</faultstring></e:Fault></e:Body></e:Envelope>").encode()
    with pytest.raises(ProtocolError):
        a.decode(fault, CTX)
    with pytest.raises(ValidationFailed):
        a.decode(f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body/></e:Envelope>'.encode(), CTX)


def test_xxe_inside_soap_rejected_by_adapter():
    with pytest.raises(UnsafeXml):
        make_adapter().decode(XXE, CTX)


def test_encode_outbound_and_validate():
    a = make_adapter()
    req = OutboundRequest(protocol=Protocol.HTNG, message_type="test.room_state",
                          facility_id=uuid.uuid4(), client_id=uuid.uuid4(), body={"room": "101", "state": "clean"})
    msg = parse_soap(a.encode(req))
    assert msg.body.tag == f"{{{TEST_XML_NS}}}RoomStateNotice"
    assert a.soap_action_for("test.room_state").endswith("#RoomStateNotice")
    with pytest.raises(UnsupportedMessage):
        a.encode(req.model_copy(update={"message_type": "test.guest_arrival"}))


def test_profile_ack_response():
    a = make_adapter()
    ack = a.build_response((TEST_XML_NS, "GuestArrival"), "accepted", "cid-1")
    body = parse_soap(ack).body
    assert body.find(f"{{{TEST_XML_NS}}}Outcome").text == "accepted"


def test_structural_validator_namespaces():
    v = StructuralValidator(allowed_namespaces=frozenset({"urn:a"}))
    with pytest.raises(ValidationFailed):
        v.validate(ET.fromstring('<a xmlns="urn:a"><b xmlns="urn:b"/></a>'))  # noqa: S314 - trusted literal


def test_adapter_message_types_by_direction():
    a = make_adapter()
    assert a.message_types(Direction.INBOUND) == {"test.guest_arrival"}
    assert a.message_types(Direction.OUTBOUND) == {"test.room_state"}


# --- SOAP transport ---------------------------------------------------------------
def _transport(handler):
    return SoapTransport(httpx.Client(transport=httpx.MockTransport(handler)))


ENDPOINT = SoapEndpoint(url="https://vendor.invalid/soap", timeout_seconds=2)
ENVELOPE = build_soap_envelope(ET.Element("{urn:t}x"))


def _ok_response(request):
    assert request.headers["SOAPAction"] == '"urn:act"'
    assert request.headers["Content-Type"].startswith("text/xml")
    assert request.headers["X-Correlation-ID"] == "cid-7"
    return httpx.Response(200, content=build_soap_envelope(ET.Element("{urn:t}ok")))


def test_soap_call_success():
    msg = _transport(_ok_response).call(ENDPOINT, ENVELOPE, soap_action="urn:act", correlation_id="cid-7")
    assert msg.body.tag == "{urn:t}ok"


def test_soap_call_timeout_is_transient():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(TransportError) as exc:
        _transport(handler).call(ENDPOINT, ENVELOPE)
    assert exc.value.retryable and exc.value.code == "soap_timeout"


def test_soap_connect_error_is_transient():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(TransportError):
        _transport(handler).call(ENDPOINT, ENVELOPE)


def test_soap_server_errors_and_faults():
    def server_fault(request):
        return httpx.Response(500, content=(
            f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><e:Fault><faultcode>e:Server</faultcode>'
            "<faultstring>busy</faultstring></e:Fault></e:Body></e:Envelope>").encode())

    def client_fault(request):
        return httpx.Response(500, content=(
            f'<e:Envelope xmlns:e="{SOAP11_NS}"><e:Body><e:Fault><faultcode>e:Client</faultcode>'
            "<faultstring>bad</faultstring></e:Fault></e:Body></e:Envelope>").encode())

    with pytest.raises(TransientFailure):
        _transport(server_fault).call(ENDPOINT, ENVELOPE)
    with pytest.raises(PermanentFailure):
        _transport(client_fault).call(ENDPOINT, ENVELOPE)
    with pytest.raises(TransientFailure):
        _transport(lambda r: httpx.Response(503, content=b"<html>down</html>")).call(ENDPOINT, ENVELOPE)
    with pytest.raises(PermanentFailure):
        _transport(lambda r: httpx.Response(403, content=b"")).call(ENDPOINT, ENVELOPE)
    with pytest.raises(ProtocolError):
        _transport(lambda r: httpx.Response(200, content=b"")).call(ENDPOINT, ENVELOPE)


def test_soap_response_xxe_rejected():
    def handler(request):
        return httpx.Response(200, content=XXE)

    with pytest.raises(ProtocolError):
        _transport(handler).call(ENDPOINT, ENVELOPE)


def test_soap12_action_in_content_type():
    seen = {}

    def handler(request):
        seen["ct"] = request.headers["Content-Type"]
        return httpx.Response(200, content=build_soap_envelope(ET.Element("{urn:t}ok"), version=SoapVersion.SOAP12))

    ep = SoapEndpoint(url="https://v.invalid/s", version=SoapVersion.SOAP12)
    _transport(handler).call(ep, ENVELOPE, soap_action="urn:a")
    assert seen["ct"].startswith("application/soap+xml") and 'action="urn:a"' in seen["ct"]


def test_endpoint_requires_https_except_loopback_opt_in():
    with pytest.raises(ValidationFailed):
        SoapEndpoint(url="http://vendor.example/soap")
    with pytest.raises(ValidationFailed):
        SoapEndpoint(url="http://10.0.0.5/soap", allow_insecure_loopback=True)
    assert SoapEndpoint(url="http://127.0.0.1:8080/s", allow_insecure_loopback=True)
    with pytest.raises(ValueError):
        SoapEndpoint(url="https://v/s", timeout_seconds=0)
