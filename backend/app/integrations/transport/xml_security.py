"""Safe parsing of untrusted XML.

No new dependency (defusedxml/lxml are not approved -- HF-39), so this is a
two-pass design over the standard library:

1. Size check BEFORE any parsing.
2. A raw `pyexpat` pass with handlers that REJECT any DOCTYPE, any entity
   declaration and any external entity reference, and that enforce limits on
   nesting depth, element count and attribute count. Parameter-entity parsing
   is switched off. Namespaces are reported per element, so an allow-list can
   be enforced.
3. Only a document that passed (2) -- and therefore contains no DTD at all,
   so no entity can be defined or expanded -- is handed to
   `xml.etree.ElementTree` to build the tree.

Rejecting every DOCTYPE closes XXE, billion-laughs / quadratic-blowup and DTD
retrieval in one rule. SOAP 1.1 and 1.2 both forbid a DTD in a message, so no
legitimate SOAP traffic is lost.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from xml.parsers import expat

from app.integrations.core.errors import FrameTooLarge, ProtocolError, ValidationFailed


class UnsafeXml(ProtocolError):
    code = "unsafe_xml"


@dataclass(frozen=True)
class XmlLimits:
    max_bytes: int = 1024 * 1024
    max_depth: int = 64
    max_elements: int = 20_000
    max_attributes_per_element: int = 64


DEFAULT_LIMITS = XmlLimits()


class _Abort(Exception):
    def __init__(self, error: Exception) -> None:
        self.error = error


def _prescan(data: bytes, limits: XmlLimits, allowed_namespaces: frozenset[str] | None) -> None:
    parser = expat.ParserCreate(namespace_separator="\x01")
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    depth = 0
    elements = 0

    def reject_doctype(*_args):
        raise _Abort(UnsafeXml("XML documents with a DOCTYPE are not accepted."))

    def reject_entity(*_args):
        raise _Abort(UnsafeXml("XML entity declarations are not accepted."))

    def reject_external(*_args):
        raise _Abort(UnsafeXml("External XML entities are not accepted."))

    def start(name, attrs):
        nonlocal depth, elements
        depth += 1
        elements += 1
        if depth > limits.max_depth:
            raise _Abort(UnsafeXml("XML nesting is too deep."))
        if elements > limits.max_elements:
            raise _Abort(UnsafeXml("XML has too many elements."))
        if len(attrs) > limits.max_attributes_per_element * 2:  # flat list name,value,...
            raise _Abort(UnsafeXml("XML element has too many attributes."))
        if allowed_namespaces is not None:
            ns = name.split("\x01", 1)[0] if "\x01" in name else ""
            if ns not in allowed_namespaces:
                raise _Abort(ValidationFailed("Unexpected XML namespace.", code="unexpected_namespace"))

    def end(_name):
        nonlocal depth
        depth -= 1

    parser.StartDoctypeDeclHandler = reject_doctype
    parser.EntityDeclHandler = reject_entity
    parser.UnparsedEntityDeclHandler = reject_entity
    parser.ExternalEntityRefHandler = reject_external
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.ordered_attributes = True
    try:
        parser.Parse(data, True)
    except _Abort as abort:
        raise abort.error from None
    except expat.ExpatError:
        raise ProtocolError("XML is not well-formed.", code="malformed_xml") from None


def parse_untrusted_xml(
    data: bytes,
    *,
    limits: XmlLimits = DEFAULT_LIMITS,
    allowed_namespaces: frozenset[str] | None = None,
) -> ET.Element:
    if not isinstance(data, (bytes, bytearray)):
        raise ProtocolError("XML must be supplied as bytes.", code="xml_not_bytes")
    if not data:
        raise ValidationFailed("XML document is empty.", code="empty_xml")
    if len(data) > limits.max_bytes:
        raise FrameTooLarge("XML document exceeds the size limit.")
    _prescan(bytes(data), limits, allowed_namespaces)
    try:
        # Safe: _prescan rejected every DOCTYPE/entity declaration above.
        return ET.fromstring(bytes(data))  # noqa: S314
    except ET.ParseError:  # pragma: no cover - prescan already rejected malformed input
        raise ProtocolError("XML is not well-formed.", code="malformed_xml") from None


def qname(element: ET.Element) -> tuple[str, str]:
    """(namespace, local name) of an ElementTree element."""
    tag = element.tag
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


def text_of(element: ET.Element | None, *, max_length: int = 4096) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    if len(text) > max_length:
        raise ValidationFailed("XML text value is too long.", code="xml_text_too_long")
    return text
