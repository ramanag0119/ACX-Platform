"""Adapter and handler registries."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.integrations.adapters.base import AdapterReadiness, AdapterStatus, BaseProtocolAdapter
from app.integrations.core.envelope import CanonicalEnvelope, Direction, Protocol
from app.integrations.core.errors import (
    UnsupportedMessage,
    UnsupportedProtocol,
    VendorSpecificationBlocked,
)
from app.integrations.processing.repository import AuditDraft, OutboxDraft


class AdapterRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._adapters: dict[Protocol, BaseProtocolAdapter] = {}

    def register(self, adapter: BaseProtocolAdapter) -> None:
        with self._lock:
            if adapter.protocol in self._adapters:
                raise ValueError(f"an adapter for {adapter.protocol} is already registered")
            self._adapters[adapter.protocol] = adapter

    def get(self, protocol: Protocol | str, direction: Direction) -> BaseProtocolAdapter:
        try:
            protocol = Protocol(protocol)
        except ValueError:
            raise UnsupportedProtocol("Protocol is not supported.") from None
        with self._lock:
            adapter = self._adapters.get(protocol)
        if adapter is None:
            raise UnsupportedProtocol(
                "No adapter is registered for this protocol.", detail={"protocol": str(protocol)}
            )
        status = adapter.status()
        if status.readiness is AdapterReadiness.BLOCKED:
            decision = status.blocking_decisions[0] if status.blocking_decisions else "unknown"
            raise VendorSpecificationBlocked(
                f"The {protocol} adapter has no verified specification.", decision=decision
            )
        if not adapter.supports(direction):
            raise UnsupportedProtocol(
                f"The {protocol} adapter does not support {direction} messages.",
                detail={"protocol": str(protocol), "direction": str(direction)},
            )
        return adapter

    def statuses(self) -> list[AdapterStatus]:
        with self._lock:
            adapters = list(self._adapters.values())
        return [a.status() for a in adapters]


@dataclass
class HandlerContext:
    """What a handler may use. `session` is the fenced DB session (or None)."""

    session: Any | None
    outbox: list[OutboxDraft] = field(default_factory=list)
    audits: list[AuditDraft] = field(default_factory=list)

    def emit(self, draft: OutboxDraft) -> None:
        self.outbox.append(draft)

    def audit(self, draft: AuditDraft) -> None:
        self.audits.append(draft)


@dataclass(frozen=True)
class HandlerResult:
    summary: dict[str, Any] = field(default_factory=dict)


class MessageHandler(ABC):
    """Handles exactly one canonical message type.

    Handlers raise `IntegrationError` subclasses to signal failure; the
    worker turns the category into retry or dead-letter. Handlers must not
    commit sessions themselves unless they call an HMS service that does
    (see processing/worker.py on transactional coupling).
    """

    message_type: str

    @abstractmethod
    def handle(self, envelope: CanonicalEnvelope, ctx: HandlerContext) -> HandlerResult: ...

    def ordering_key(self, body: dict[str, Any]) -> str | None:
        """Entity key for in-order processing; None means unordered.

        Messages with the same (client, facility, ordering_key) are processed
        strictly in arrival order: a later one is not claimed while an earlier
        one is unfinished (see processing/repository.py)."""
        return None


class HandlerRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, MessageHandler] = {}

    def register(self, handler: MessageHandler) -> None:
        with self._lock:
            if handler.message_type in self._handlers:
                raise ValueError(f"a handler for {handler.message_type} is already registered")
            self._handlers[handler.message_type] = handler

    def has(self, message_type: str) -> bool:
        with self._lock:
            return message_type in self._handlers

    def get(self, message_type: str) -> MessageHandler:
        with self._lock:
            handler = self._handlers.get(message_type)
        if handler is None:
            raise UnsupportedMessage(
                "No handler is registered for this message type.",
                detail={"message_type": message_type},
            )
        return handler

    def message_types(self) -> list[str]:
        with self._lock:
            return sorted(self._handlers)
