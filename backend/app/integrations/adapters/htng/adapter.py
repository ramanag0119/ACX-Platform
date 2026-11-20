"""HTNGAdapter -- SOAP/XML <-> canonical messages, driven by a SchemaProfile.

One adapter instance serves one (profile_id, version). With no profile
registered (today) it is BLOCKED (HF-07) and every operation is refused.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.integrations.adapters.base import (
    AdapterReadiness,
    AdapterStatus,
    BaseProtocolAdapter,
    TransportContext,
)
from app.integrations.adapters.htng.schema import BLOCKING_DECISION, SchemaProfile, SchemaRegistry
from app.integrations.core.envelope import DecodedMessage, Direction, OutboundRequest, Protocol
from app.integrations.core.errors import (
    ProtocolError,
    ValidationFailed,
    VendorSpecificationBlocked,
)
from app.integrations.transport.soap import SoapVersion, build_soap_envelope, parse_soap
from app.integrations.transport.xml_security import DEFAULT_LIMITS, XmlLimits, qname


class HTNGAdapter(BaseProtocolAdapter):
    protocol = Protocol.HTNG

    def __init__(
        self,
        registry: SchemaRegistry,
        *,
        profile_id: str | None = None,
        version: str | None = None,
        soap_version: SoapVersion = SoapVersion.SOAP11,
        limits: XmlLimits = DEFAULT_LIMITS,
    ) -> None:
        self._registry = registry
        self._profile_id = profile_id
        self._version = version
        self._soap_version = soap_version
        self._limits = limits

    def _profile(self) -> SchemaProfile:
        if not self._profile_id or not self._version:
            raise VendorSpecificationBlocked(
                "No HTNG schema profile is configured.", decision=BLOCKING_DECISION
            )
        return self._registry.resolve(self._profile_id, self._version)

    def _profile_or_none(self) -> SchemaProfile | None:
        try:
            return self._profile()
        except VendorSpecificationBlocked:
            return None

    # ---------------------------------------------------------------- status
    def status(self) -> AdapterStatus:
        profile = self._profile_or_none()
        if profile is None:
            return AdapterStatus(
                protocol=self.protocol, readiness=AdapterReadiness.BLOCKED, specification=None,
                inbound_message_types=(), outbound_message_types=(),
                blocking_decisions=(BLOCKING_DECISION, "HF-08"),
            )
        return AdapterStatus(
            protocol=self.protocol,
            readiness=AdapterReadiness.READY if profile.is_verified() else AdapterReadiness.TEST_ONLY,
            specification=profile.key,
            inbound_message_types=tuple(sorted(profile.message_types(Direction.INBOUND))),
            outbound_message_types=tuple(sorted(profile.message_types(Direction.OUTBOUND))),
            blocking_decisions=() if profile.is_verified() else (BLOCKING_DECISION,),
        )

    def message_types(self, direction: Direction) -> frozenset[str]:
        profile = self._profile_or_none()
        return profile.message_types(direction) if profile else frozenset()

    # ---------------------------------------------------------------- decode
    def decode(self, raw: bytes, context: TransportContext) -> DecodedMessage:
        profile = self._profile()
        message = parse_soap(raw, limits=self._limits, allowed_payload_namespaces=profile.namespaces)
        if message.fault is not None:
            raise ProtocolError("Inbound SOAP message is a Fault.", code="inbound_soap_fault")
        if message.body is None:
            raise ValidationFailed("SOAP Body is empty.", code="soap_body_empty")
        op = profile.inbound(qname(message.body))
        op.validator.validate(message.body)
        mapped = op.inbound_mapper(message.body)
        if mapped.message_type != op.message_type:
            raise ProtocolError("Mapper produced a different message type.", code="mapper_mismatch")
        try:
            return DecodedMessage(
                protocol=self.protocol,
                message_type=mapped.message_type,
                schema_version=profile.key,
                property_code=mapped.property_code,
                idempotency_key=mapped.idempotency_key,
                external_message_id=mapped.external_message_id,
                body=mapped.body,
            )
        except ValidationError:
            raise ValidationFailed("Mapped HTNG message is invalid.", code="mapped_invalid") from None

    # ---------------------------------------------------------------- encode
    def encode(self, request: OutboundRequest) -> bytes:
        profile = self._profile()
        op = profile.outbound(request.message_type)
        element = op.outbound_builder(request.body)
        if qname(element) != op.root:
            raise ProtocolError("Builder produced an unexpected root element.", code="builder_mismatch")
        op.validator.validate(element)
        return build_soap_envelope(element, version=self._soap_version)

    def soap_action_for(self, message_type: str) -> str | None:
        return self._profile().outbound(message_type).soap_action

    def build_response(
        self, root: tuple[str, str], outcome: str, correlation_id: str, *, version: SoapVersion | None = None
    ) -> bytes | None:
        """Profile-defined acknowledgement, or None when the profile defines none.

        `version` lets the acknowledgement answer in the SOAP version of the
        request; it defaults to the adapter's configured version."""
        op = self._profile().inbound(root)
        if op.response_builder is None:
            return None
        return build_soap_envelope(op.response_builder(outcome, correlation_id), version=version or self._soap_version)
