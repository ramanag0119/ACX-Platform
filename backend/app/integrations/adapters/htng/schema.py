"""HTNG schema profiles and the schema registry.

A `SchemaProfile` is everything vendor-specific about one HTNG deployment:
profile id + version, the payload namespaces it may use, and one
`OperationSpec` per supported root element (validator + mapper + optional
response builder). The adapter knows nothing beyond what a profile tells it.

No HTNG WSDL, XSD, namespace, operation, SOAPAction or WS-Security profile
exists in the repository (decision HF-07 / HF-08), so the production registry
is EMPTY and the HTNG adapter reports BLOCKED. A profile is registered as
VERIFIED only from approved vendor schemas; a generic test profile
(`simulators/fixtures.py`) is accepted only with `allow_unverified=True`
outside production.

XSD validation: the standard library cannot validate XSD and no XSD library
(lxml / xmlschema) is approved (HF-39). `XsdValidator` therefore refuses to be
constructed until such a library is installed AND an XSD is supplied; the
structural validator below is the only validator available today.
"""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.integrations.adapters.fias.spec import VERIFIED, VerificationStatus
from app.integrations.core.envelope import Direction, is_valid_message_type
from app.integrations.core.errors import (
    ApprovalRequired,
    UnsupportedMessage,
    ValidationFailed,
    VendorSpecificationBlocked,
)
from app.integrations.transport.xml_security import qname

BLOCKING_DECISION = "HF-07"


class XmlValidator(Protocol):
    def validate(self, element: ET.Element) -> None: ...


@dataclass(frozen=True)
class StructuralValidator:
    """Checks required child paths and the namespaces in use.

    `required_paths` use ElementTree path syntax with `{ns}local` names.
    This is NOT schema validation; it is what can be checked without an XSD.
    """

    required_paths: tuple[str, ...] = ()
    allowed_namespaces: frozenset[str] = frozenset()

    def validate(self, element: ET.Element) -> None:
        for el in element.iter():
            ns, _ = qname(el)
            if self.allowed_namespaces and ns not in self.allowed_namespaces:
                raise ValidationFailed("Element uses an unexpected namespace.", code="unexpected_namespace")
        missing = [p for p in self.required_paths if element.find(p) is None]
        if missing:
            raise ValidationFailed(
                "Required elements are missing.", code="missing_required_elements",
                detail={"paths": missing},
            )


class XsdValidator:
    """Placeholder for real XSD validation; refuses until its dependency is approved."""

    def __init__(self, xsd_bytes: bytes) -> None:
        try:
            import xmlschema  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            raise ApprovalRequired(
                "XSD validation needs an XML-schema library that is not approved yet.",
                decisions=["HF-39", "HF-07"],
            ) from None
        raise VendorSpecificationBlocked(  # pragma: no cover - library not installed
            "XSD validation is not wired until an approved HTNG XSD is supplied.",
            decision=BLOCKING_DECISION,
        )

    def validate(self, element: ET.Element) -> None:  # pragma: no cover
        raise NotImplementedError


#: element -> (message_type, body, property_code, idempotency_key, external_message_id)
InboundMapper = Callable[[ET.Element], "MappedInbound"]
OutboundBuilder = Callable[[dict[str, Any]], ET.Element]
ResponseBuilder = Callable[[str, str], ET.Element]  # (outcome, correlation_id) -> element


@dataclass(frozen=True)
class MappedInbound:
    message_type: str
    body: dict[str, Any] = field(repr=False)
    property_code: str | None = None
    idempotency_key: str | None = None
    external_message_id: str | None = None


@dataclass(frozen=True)
class OperationSpec:
    root: tuple[str, str]  # (namespace, local name) of the Body child
    message_type: str
    direction: Direction
    validator: XmlValidator
    inbound_mapper: InboundMapper | None = None
    outbound_builder: OutboundBuilder | None = None
    response_builder: ResponseBuilder | None = None
    soap_action: str | None = None

    def __post_init__(self) -> None:
        if not is_valid_message_type(self.message_type):
            raise ValueError("invalid canonical message type")
        if self.direction is Direction.INBOUND and self.inbound_mapper is None:
            raise ValueError("inbound operations need an inbound_mapper")
        if self.direction is Direction.OUTBOUND and self.outbound_builder is None:
            raise ValueError("outbound operations need an outbound_builder")


@dataclass(frozen=True)
class SchemaProfile:
    profile_id: str
    version: str
    namespaces: frozenset[str]
    operations: tuple[OperationSpec, ...]
    status: VerificationStatus
    source: str

    def __post_init__(self) -> None:
        roots = [(op.root, op.direction) for op in self.operations]
        if len(roots) != len(set(roots)):
            raise ValueError("duplicate operation root for one direction")
        for op in self.operations:
            if op.root[0] not in self.namespaces:
                raise ValueError("operation root namespace is not declared in the profile")

    @property
    def key(self) -> str:
        return f"{self.profile_id}/{self.version}"

    def is_verified(self) -> bool:
        return self.status in VERIFIED

    def inbound(self, root: tuple[str, str]) -> OperationSpec:
        for op in self.operations:
            if op.root == root and op.direction is Direction.INBOUND:
                return op
        raise UnsupportedMessage("Operation is not supported by this profile.", detail={"element": root[1][:64]})

    def outbound(self, message_type: str) -> OperationSpec:
        for op in self.operations:
            if op.message_type == message_type and op.direction is Direction.OUTBOUND:
                return op
        raise UnsupportedMessage("Message type cannot be sent with this profile.",
                                 detail={"message_type": message_type})

    def message_types(self, direction: Direction) -> frozenset[str]:
        return frozenset(op.message_type for op in self.operations if op.direction is direction)


class SchemaRegistry:
    def __init__(self, *, allow_unverified: bool = False, app_env: str = "development") -> None:
        if allow_unverified and app_env == "production":
            raise VendorSpecificationBlocked(
                "Unverified HTNG profiles cannot be enabled in production.", decision=BLOCKING_DECISION
            )
        self._allow_unverified = allow_unverified
        self._lock = threading.Lock()
        self._profiles: dict[str, SchemaProfile] = {}

    def register(self, profile: SchemaProfile) -> None:
        if not profile.is_verified() and not self._allow_unverified:
            raise VendorSpecificationBlocked(
                "HTNG profile is not verified against approved schemas.", decision=BLOCKING_DECISION
            )
        if profile.status in (VerificationStatus.UNSUPPORTED, VerificationStatus.REJECTED):
            raise ValueError("unsupported/rejected profiles cannot be registered")
        with self._lock:
            if profile.key in self._profiles:
                raise ValueError("profile version already registered")
            self._profiles[profile.key] = profile

    def resolve(self, profile_id: str, version: str) -> SchemaProfile:
        with self._lock:
            profile = self._profiles.get(f"{profile_id}/{version}")
        if profile is None:
            raise VendorSpecificationBlocked(
                "No approved HTNG schema profile is registered for this id/version.",
                decision=BLOCKING_DECISION,
            )
        return profile

    def profiles(self) -> list[SchemaProfile]:
        with self._lock:
            return list(self._profiles.values())
