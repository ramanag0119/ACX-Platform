"""SOAP 1.1 / 1.2 envelope handling and an HTTP transport.

Only the W3C SOAP envelope standards are implemented here (their namespace
URIs are fixed by the SOAP 1.1 note and the SOAP 1.2 recommendation). Nothing
HTNG-specific lives in this module: no operations, no SOAPAction values, no
WS-Security. Those come from an approved HTNG schema profile (HF-07 / HF-08).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlsplit

import httpx

from app.integrations.core.correlation import accept_correlation_id
from app.integrations.core.errors import (
    PermanentFailure,
    ProtocolError,
    TransientFailure,
    TransportError,
    ValidationFailed,
)
from app.integrations.core.masking import mask_text
from app.integrations.transport.xml_security import (
    DEFAULT_LIMITS,
    XmlLimits,
    parse_untrusted_xml,
    qname,
    text_of,
)

SOAP11_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP12_NS = "http://www.w3.org/2003/05/soap-envelope"
SOAP_NAMESPACES = frozenset({SOAP11_NS, SOAP12_NS})

CONTENT_TYPES = {
    SOAP11_NS: "text/xml; charset=utf-8",
    SOAP12_NS: "application/soap+xml; charset=utf-8",
}

FAULT_TEXT_LIMIT = 256


class SoapVersion(StrEnum):
    SOAP11 = "1.1"
    SOAP12 = "1.2"

    @property
    def namespace(self) -> str:
        return SOAP11_NS if self is SoapVersion.SOAP11 else SOAP12_NS


@dataclass(frozen=True)
class SoapFault:
    """Fault fields, truncated and masked: a vendor fault can echo payload."""

    code: str
    reason: str


@dataclass(frozen=True)
class SoapMessage:
    version: SoapVersion
    headers: tuple[ET.Element, ...]
    body: ET.Element | None
    fault: SoapFault | None = None
    raw_size: int = 0


def _safe_fault_text(value: str | None) -> str:
    if not value:
        return ""
    return mask_text(value[:FAULT_TEXT_LIMIT])


def _parse_fault(fault: ET.Element, version: SoapVersion) -> SoapFault:
    if version is SoapVersion.SOAP11:
        code = text_of(fault.find("faultcode"), max_length=FAULT_TEXT_LIMIT * 4)
        reason = text_of(fault.find("faultstring"), max_length=FAULT_TEXT_LIMIT * 16)
    else:
        ns = SOAP12_NS
        code = text_of(fault.find(f"{{{ns}}}Code/{{{ns}}}Value"), max_length=FAULT_TEXT_LIMIT * 4)
        reason = text_of(fault.find(f"{{{ns}}}Reason/{{{ns}}}Text"), max_length=FAULT_TEXT_LIMIT * 16)
    return SoapFault(code=_safe_fault_text(code), reason=_safe_fault_text(reason))


def parse_soap(
    data: bytes,
    *,
    limits: XmlLimits = DEFAULT_LIMITS,
    allowed_payload_namespaces: frozenset[str] | None = None,
) -> SoapMessage:
    allowed = None
    if allowed_payload_namespaces is not None:
        # Empty namespace is allowed for SOAP 1.1 fault children (faultcode...).
        allowed = SOAP_NAMESPACES | allowed_payload_namespaces | {""}
    root = parse_untrusted_xml(data, limits=limits, allowed_namespaces=allowed)
    ns, local = qname(root)
    if local != "Envelope" or ns not in SOAP_NAMESPACES:
        raise ProtocolError("Document is not a SOAP envelope.", code="not_soap_envelope")
    version = SoapVersion.SOAP11 if ns == SOAP11_NS else SoapVersion.SOAP12

    header = root.find(f"{{{ns}}}Header")
    body = root.find(f"{{{ns}}}Body")
    if body is None:
        raise ProtocolError("SOAP envelope has no Body.", code="soap_body_missing")
    for child in root:
        cns, clocal = qname(child)
        if cns != ns or clocal not in ("Header", "Body"):
            raise ProtocolError("Unexpected element in SOAP envelope.", code="soap_envelope_invalid")

    children = list(body)
    if len(children) > 1:
        raise ProtocolError("SOAP Body must contain one element.", code="soap_body_multiple")
    payload = children[0] if children else None
    fault = None
    if payload is not None and qname(payload) == (ns, "Fault"):
        fault = _parse_fault(payload, version)
        payload = None
    return SoapMessage(
        version=version,
        headers=tuple(header) if header is not None else (),
        body=payload,
        fault=fault,
        raw_size=len(data),
    )


def build_soap_envelope(
    body: ET.Element, *, version: SoapVersion = SoapVersion.SOAP11, headers: list[ET.Element] | None = None
) -> bytes:
    ns = version.namespace
    env = ET.Element(f"{{{ns}}}Envelope")
    if headers:
        header = ET.SubElement(env, f"{{{ns}}}Header")
        header.extend(headers)
    body_el = ET.SubElement(env, f"{{{ns}}}Body")
    body_el.append(body)
    return ET.tostring(env, encoding="utf-8", xml_declaration=True)


@dataclass(frozen=True)
class SoapEndpoint:
    url: str
    version: SoapVersion = SoapVersion.SOAP11
    timeout_seconds: float = 10.0
    #: Plain HTTP only for loopback test endpoints.
    allow_insecure_loopback: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        parts = urlsplit(self.url)
        if parts.scheme == "https":
            return
        if parts.scheme == "http" and self.allow_insecure_loopback and parts.hostname in (
            "127.0.0.1", "localhost", "::1"
        ):
            return
        raise ValidationFailed("SOAP endpoints must use HTTPS.", code="insecure_endpoint")


class SoapTransport:
    """Sends a SOAP envelope over HTTP(S) and classifies the outcome.

    * timeouts / connection errors / HTTP 5xx without a fault -> TRANSIENT
    * a SOAP Fault -> PERMANENT for Client/Sender faults, TRANSIENT otherwise
      (both SOAP versions define these generic fault codes)
    * HTTP 4xx -> PERMANENT
    """

    def __init__(self, client: httpx.Client | None = None, *, limits: XmlLimits = DEFAULT_LIMITS) -> None:
        self._client = client or httpx.Client(follow_redirects=False)
        self._limits = limits

    def call(
        self,
        endpoint: SoapEndpoint,
        envelope: bytes,
        *,
        soap_action: str | None = None,
        correlation_id: str | None = None,
    ) -> SoapMessage:
        headers = {"Content-Type": CONTENT_TYPES[endpoint.version.namespace]}
        if endpoint.version is SoapVersion.SOAP11:
            headers["SOAPAction"] = f'"{soap_action or ""}"'
        elif soap_action:
            headers["Content-Type"] += f'; action="{soap_action}"'
        headers["X-Correlation-ID"] = accept_correlation_id(correlation_id)
        headers.update(endpoint.extra_headers)
        try:
            response = self._client.post(
                endpoint.url, content=envelope, headers=headers, timeout=endpoint.timeout_seconds
            )
        except httpx.TimeoutException:
            raise TransportError("SOAP call timed out.", code="soap_timeout") from None
        except httpx.HTTPError:
            raise TransportError("SOAP call failed to connect.", code="soap_connect_failed") from None

        content = response.content
        if len(content) > self._limits.max_bytes:
            raise ProtocolError("SOAP response exceeds the size limit.", code="soap_response_too_large")

        message: SoapMessage | None = None
        if content:
            try:
                message = parse_soap(content, limits=self._limits)
            except ProtocolError:
                if response.status_code >= 500:
                    raise TransientFailure(
                        "SOAP endpoint returned a server error.", code="soap_http_5xx"
                    ) from None
                raise

        if message is not None and message.fault is not None:
            local = message.fault.code.rsplit(":", 1)[-1]
            if local in ("Client", "Sender"):
                raise PermanentFailure("SOAP endpoint rejected the request.", code="soap_fault_client",
                                       detail={"fault_code": message.fault.code})
            raise TransientFailure("SOAP endpoint reported a server fault.", code="soap_fault_server",
                                   detail={"fault_code": message.fault.code})
        if response.status_code >= 500:
            raise TransientFailure("SOAP endpoint returned a server error.", code="soap_http_5xx")
        if response.status_code >= 400:
            raise PermanentFailure("SOAP endpoint rejected the request.", code="soap_http_4xx",
                                   detail={"status": response.status_code})
        if message is None:
            raise ProtocolError("SOAP response was empty.", code="soap_response_empty")
        return message
