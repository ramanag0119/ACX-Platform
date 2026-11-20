"""`BaseProtocolAdapter` -- the contract every protocol adapter implements.

An adapter converts between wire bytes and canonical messages and nothing
else. It never authenticates, never resolves facilities, never touches the
database and never calls HMS services; those belong to the exchange and the
domain adapters. Keeping the adapter pure is what lets FIAS and HTNG share one
security and processing path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from app.integrations.core.envelope import DecodedMessage, Direction, OutboundRequest, Protocol


class AdapterReadiness(StrEnum):
    #: Driven by a verified vendor specification.
    READY = "ready"
    #: Running on an explicitly provisional test specification. Never production.
    TEST_ONLY = "test_only"
    #: No verified specification supplied; every operation is refused.
    BLOCKED = "blocked"


@dataclass(frozen=True)
class AdapterStatus:
    protocol: Protocol
    readiness: AdapterReadiness
    specification: str | None
    inbound_message_types: tuple[str, ...]
    outbound_message_types: tuple[str, ...]
    blocking_decisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransportContext:
    """What the transport knows about where bytes came from.

    `bound_property_code` is set when a link/endpoint is configured for exactly
    one external property (e.g. one TCP link per property). It is still
    resolved and authorised by the exchange like any other property code.
    """

    transport: str
    peer: str | None = None
    bound_property_code: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)


class BaseProtocolAdapter(ABC):
    protocol: Protocol

    @abstractmethod
    def decode(self, raw: bytes, context: TransportContext) -> DecodedMessage:
        """Wire bytes -> DecodedMessage. Raises ProtocolError / ValidationFailed /
        UnsupportedMessage / VendorSpecificationBlocked."""

    @abstractmethod
    def encode(self, request: OutboundRequest) -> bytes:
        """Canonical outbound request -> wire bytes (unframed)."""

    @abstractmethod
    def message_types(self, direction: Direction) -> frozenset[str]:
        """Canonical message types this adapter can handle in `direction`."""

    @abstractmethod
    def status(self) -> AdapterStatus: ...

    def supports(self, direction: Direction) -> bool:
        return bool(self.message_types(direction))
