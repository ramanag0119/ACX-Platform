"""PROVISIONAL TEST FIXTURES -- NOT FIAS, NOT HTNG.

TEST ASSUMPTION, NOT A VENDOR SPECIFICATION. These definitions exist only so
the transport, framing, parsing, exchange and processing layers can be
exercised end to end without vendor documents. They are deliberately
synthetic so they cannot be mistaken for real protocol definitions:

* Framing: start byte 0x02, end byte 0x03. This is a common convention for
  ASCII serial/TCP links and is used here ONLY as a test assumption. It is
  NOT a verified FIAS framing rule (HF-06).
* Records use synthetic two-letter ids starting with "Z" ("ZA", "ZD", "ZS",
  "ZK") and synthetic field ids ("MI", "PC", ...). None of them is a FIAS
  record or field id. Canonical message types are prefixed "test.".
* The XML profile uses the namespace "urn:acx:test:generic-xml:v1", which is
  not an HTNG namespace. Operations are invented for testing only.

Historical assumptions from earlier work (FIAS records GI/GO/GC/WR, STX/ETX
framing) are NOT encoded here; they are listed as unverified in
docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.integrations.adapters.fias.spec import (
    FieldSpec,
    FiasSpecification,
    RecordSpec,
    VerificationStatus,
    WireGrammar,
)
from app.integrations.adapters.htng.schema import (
    MappedInbound,
    OperationSpec,
    SchemaProfile,
    StructuralValidator,
)
from app.integrations.core.envelope import Direction, IntakeOutcome, IntakeResult
from app.integrations.transport.framing import DelimitedFramer
from app.integrations.transport.xml_security import text_of

PROVISIONAL = VerificationStatus.PROVISIONAL_TEST
SOURCE = "TEST ASSUMPTION - app/integrations/simulators/fixtures.py (no vendor document)"

TEST_START_MARKER = b"\x02"
TEST_END_MARKER = b"\x03"


def provisional_test_framer(max_frame_bytes: int = 8192) -> DelimitedFramer:
    """TEST ASSUMPTION framing (see module docstring)."""
    return DelimitedFramer(start=TEST_START_MARKER, end=TEST_END_MARKER, max_frame_bytes=max_frame_bytes)


IN = frozenset({Direction.INBOUND})
OUT = frozenset({Direction.OUTBOUND})

PROVISIONAL_TEST_FIAS_SPEC = FiasSpecification(
    name="ACX-SYNTHETIC-TEST",
    version="0",
    grammar=WireGrammar(
        encoding="ascii",
        record_id_length=2,
        field_separator=b"|",
        field_id_length=2,
        status=PROVISIONAL,
        source=SOURCE,
    ),
    records=(
        RecordSpec(
            record_id="ZA",
            message_type="test.guest_arrival",
            directions=IN,
            fields=(
                FieldSpec("MI", "message_ref", mandatory=True, max_length=32, pattern=r"[A-Za-z0-9\-]+"),
                FieldSpec("PC", "property_code", mandatory=True, max_length=32),
                FieldSpec("RN", "room", mandatory=True, max_length=10, pattern=r"[A-Za-z0-9]+"),
                FieldSpec("GN", "guest_name", max_length=80),
                FieldSpec("SR", "external_stay_ref", mandatory=True, max_length=40),
            ),
            status=PROVISIONAL,
            source=SOURCE,
            idempotency_fields=("MI",),
            property_field="PC",
        ),
        RecordSpec(
            record_id="ZD",
            message_type="test.guest_departure",
            directions=IN,
            fields=(
                FieldSpec("MI", "message_ref", mandatory=True, max_length=32, pattern=r"[A-Za-z0-9\-]+"),
                FieldSpec("PC", "property_code", mandatory=True, max_length=32),
                FieldSpec("RN", "room", mandatory=True, max_length=10, pattern=r"[A-Za-z0-9]+"),
                FieldSpec("SR", "external_stay_ref", mandatory=True, max_length=40),
            ),
            status=PROVISIONAL,
            source=SOURCE,
            idempotency_fields=("MI",),
            property_field="PC",
        ),
        RecordSpec(
            record_id="ZS",
            message_type="test.room_state",
            directions=OUT,
            fields=(
                FieldSpec("RN", "room", mandatory=True, max_length=10, pattern=r"[A-Za-z0-9]+"),
                FieldSpec("ST", "state", mandatory=True, max_length=16, pattern=r"[a-z_]+"),
            ),
            status=PROVISIONAL,
            source=SOURCE,
        ),
        RecordSpec(
            record_id="ZK",
            message_type="test.receipt",
            directions=OUT,
            fields=(
                FieldSpec("MI", "message_ref", mandatory=True, max_length=32),
                FieldSpec("OK", "outcome", mandatory=True, max_length=12),
            ),
            status=PROVISIONAL,
            source=SOURCE,
        ),
    ),
)


def synthetic_receipt_record(result: IntakeResult, message_ref: str | None) -> bytes | None:
    """TEST ASSUMPTION responder: answers each frame with a synthetic ZK record.

    Real FIAS acknowledgement behaviour is unverified (HF-06); the production
    link has no responder.
    """
    if not message_ref:
        return None
    outcome = "ok" if result.outcome in (IntakeOutcome.ACCEPTED, IntakeOutcome.DUPLICATE) else "rejected"
    return f"ZK|MI{message_ref}|OK{outcome}|".encode("ascii")


# ---------------------------------------------------------------------------
# Generic XML profile (NOT HTNG)
# ---------------------------------------------------------------------------

TEST_XML_NS = "urn:acx:test:generic-xml:v1"


def _t(local: str) -> str:
    return f"{{{TEST_XML_NS}}}{local}"


def _map_arrival(el: ET.Element) -> MappedInbound:
    ref = text_of(el.find(_t("MessageRef")), max_length=64)
    return MappedInbound(
        message_type="test.guest_arrival",
        property_code=text_of(el.find(_t("PropertyCode")), max_length=32),
        idempotency_key=ref,
        external_message_id=ref,
        body={
            "message_ref": ref,
            "room": text_of(el.find(_t("Room")), max_length=10),
            "external_stay_ref": text_of(el.find(_t("StayRef")), max_length=40),
            "guest_name": text_of(el.find(_t("GuestName")), max_length=80),
        },
    )


def _build_room_state(body: dict) -> ET.Element:
    root = ET.Element(_t("RoomStateNotice"))
    ET.SubElement(root, _t("Room")).text = str(body["room"])
    ET.SubElement(root, _t("State")).text = str(body["state"])
    return root


def _ack(outcome: str, correlation_id: str) -> ET.Element:
    root = ET.Element(_t("Receipt"))
    ET.SubElement(root, _t("Outcome")).text = outcome
    ET.SubElement(root, _t("CorrelationId")).text = correlation_id
    return root


PROVISIONAL_TEST_XML_PROFILE = SchemaProfile(
    profile_id="acx-generic-xml-test",
    version="0",
    namespaces=frozenset({TEST_XML_NS}),
    status=PROVISIONAL,
    source=SOURCE,
    operations=(
        OperationSpec(
            root=(TEST_XML_NS, "GuestArrival"),
            message_type="test.guest_arrival",
            direction=Direction.INBOUND,
            validator=StructuralValidator(
                required_paths=(_t("MessageRef"), _t("PropertyCode"), _t("Room"), _t("StayRef")),
                allowed_namespaces=frozenset({TEST_XML_NS}),
            ),
            inbound_mapper=_map_arrival,
            response_builder=_ack,
        ),
        OperationSpec(
            root=(TEST_XML_NS, "RoomStateNotice"),
            message_type="test.room_state",
            direction=Direction.OUTBOUND,
            validator=StructuralValidator(
                required_paths=(_t("Room"), _t("State")),
                allowed_namespaces=frozenset({TEST_XML_NS}),
            ),
            outbound_builder=_build_room_state,
            soap_action="urn:acx:test:generic-xml:v1#RoomStateNotice",
        ),
    ),
)


def generic_arrival_soap(
    *, message_ref: str, property_code: str, room: str, stay_ref: str, guest_name: str | None = None,
    extra: str = "",
) -> bytes:
    """A SOAP 1.1 request carrying the TEST GuestArrival element."""
    guest = f"<t:GuestName>{guest_name}</t:GuestName>" if guest_name else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:t="{TEST_XML_NS}"><soap:Body><t:GuestArrival>'
        f"<t:MessageRef>{message_ref}</t:MessageRef><t:PropertyCode>{property_code}</t:PropertyCode>"
        f"<t:Room>{room}</t:Room><t:StayRef>{stay_ref}</t:StayRef>{guest}{extra}"
        "</t:GuestArrival></soap:Body></soap:Envelope>"
    ).encode()
