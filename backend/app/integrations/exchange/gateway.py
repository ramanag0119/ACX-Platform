"""ExchangeAdapter / ExchangeGateway -- the protocol-independent boundary.

Inbound order of operations (each step can only narrow what is trusted):

    1. size / emptiness guard                    (before any parsing)
    2. client authorised for this protocol       (authentication happened at
                                                  the transport: TCP link or
                                                  HTTP request)
    3. adapter lookup (protocol + direction)     UnsupportedProtocol /
                                                  VendorSpecificationBlocked
    4. adapter.decode(raw)                       ProtocolError / ValidationFailed
    5. property code -> facility (client scoped) FacilityAuthorizationError
    6. payload scope-smuggling check             FacilityAuthorizationError
    7. handler exists for the message type       UnsupportedMessage
    8. idempotency key present                   ValidationFailed
    9. canonical envelope built + persisted with idempotency in ONE
       transaction                               DUPLICATE / IdempotencyConflict

Business processing happens later, in the worker. Nothing here calls an HMS
service, so a burst of vendor traffic can never hold HMS write locks.
"""

from __future__ import annotations

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta

from pydantic import ValidationError

from app.integrations.adapters.base import TransportContext
from app.integrations.core.correlation import accept_correlation_id
from app.integrations.core.envelope import (
    CanonicalEnvelope,
    Direction,
    IntakeOutcome,
    IntakeResult,
    MessageStatus,
    OutboundRequest,
    Protocol,
    utcnow,
)
from app.integrations.core.errors import (
    PermanentFailure,
    AuthenticationFailed,
    ErrorCategory,
    FacilityAuthorizationError,
    FrameTooLarge,
    IntegrationError,
    ProtocolError,
    UnsupportedMessage,
    ValidationFailed,
    classify,
)
from app.integrations.core.hashing import payload_hash
from app.integrations.core.lifecycle import assert_transition
from app.integrations.exchange.registry import AdapterRegistry, HandlerRegistry
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.repository import (
    AuditEvent,
    IntegrationRepository,
    OutboxDraft,
)
from app.integrations.security.clients import CLIENT_CODE_PATTERN, AuthenticatedClient, ClientAuthenticator
from app.integrations.security.facility import FacilityResolver

logger = logging.getLogger("hms.integrations.exchange")


class ExchangeAdapter(ABC):
    """What transports and HMS code depend on. Transports never see handlers,
    repositories or resolvers -- only this interface."""

    @abstractmethod
    def authenticate(self, code: str | None, secret: str | None, *, protocol: Protocol) -> AuthenticatedClient: ...

    @abstractmethod
    def receive(
        self,
        raw: bytes,
        *,
        protocol: Protocol,
        client: AuthenticatedClient,
        context: TransportContext,
        correlation_id: str | None = None,
    ) -> IntakeResult: ...

    @abstractmethod
    def request_outbound(self, request: OutboundRequest) -> uuid.UUID: ...


class ExchangeGateway(ExchangeAdapter):
    def __init__(
        self,
        *,
        adapters: AdapterRegistry,
        handlers: HandlerRegistry,
        authenticator: ClientAuthenticator,
        resolver: FacilityResolver,
        repository: IntegrationRepository,
        metrics: IntegrationMetrics | None = None,
        max_message_bytes: int = 256 * 1024,
        max_attempts: int = 5,
        store_wire_payload: bool = False,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.adapters = adapters
        self.handlers = handlers
        self._authenticator = authenticator
        self._resolver = resolver
        self._repo = repository
        self.metrics = metrics or IntegrationMetrics()
        self._max_bytes = max_message_bytes
        self._max_attempts = max_attempts
        self._store_wire = store_wire_payload
        self._clock = clock
        self._intake_lock = threading.Lock()
        self._last_received_at: datetime | None = None

    # ------------------------------------------------------------------ auth
    def authenticate(self, code, secret, *, protocol):
        try:
            return self._authenticator.authenticate(code, secret, protocol=protocol)
        except AuthenticationFailed as exc:
            self.metrics.inc("auth_failures", protocol=str(protocol), reason=exc.reason)
            self._audit_security(
                "client.authentication_failed",
                # Only a well-formed code is stored: the raw value is attacker-controlled.
                actor_id=code if isinstance(code, str) and CLIENT_CODE_PATTERN.fullmatch(code) else None,
                detail={"reason": exc.reason, "protocol": str(protocol)},
            )
            raise

    # --------------------------------------------------------------- inbound
    def receive(self, raw, *, protocol, client, context, correlation_id=None):
        cid = accept_correlation_id(correlation_id)
        try:
            try:
                envelope = self._validate(raw, protocol=protocol, client=client, context=context, cid=cid)
            except IntegrationError:
                raise
            except Exception as exc:
                # The same bytes will fail the same way every time (adapter or
                # mapper defect, malformed structure): PERMANENT, never retried.
                # Only persistence failures below are transient (G1, sprint 5).
                raise PermanentFailure(
                    "Message could not be validated.",
                    code="intake_unexpected_error",
                    detail={"exception_type": type(exc).__name__},
                ) from None
            outcome = self._repo.accept(
                envelope,
                wire_bytes=raw if self._store_wire else None,
                max_attempts=self._max_attempts,
            )
        except Exception as exc:  # noqa: BLE001 - every failure becomes a result
            error = classify(exc)
            self.metrics.inc("intake_rejected", protocol=str(protocol), category=str(error.category))
            if error.category is ErrorCategory.SECURITY:
                self._audit_security(
                    "message.rejected_security",
                    actor_id=str(client.client_id),
                    detail={"code": error.code, "protocol": str(protocol)},
                )
            logger.info(
                "intake rejected correlation_id=%s client=%s code=%s category=%s",
                cid, client.code, error.code, error.category,
            )
            return IntakeResult(outcome=IntakeOutcome.REJECTED, correlation_id=cid, error=error.as_dict())

        self.metrics.inc(
            "intake_" + str(outcome.outcome), protocol=str(protocol), message_type=envelope.message_type
        )
        logger.info(
            "intake %s message_id=%s correlation_id=%s type=%s",
            outcome.outcome, outcome.message_id, cid, envelope.message_type,
        )
        return IntakeResult(
            outcome=outcome.outcome,
            correlation_id=cid,
            message_id=outcome.message_id,
            message_type=envelope.message_type,
        )

    def _validate(self, raw, *, protocol, client, context, cid) -> CanonicalEnvelope:
        if not isinstance(raw, (bytes, bytearray)):
            raise ProtocolError("Message must be bytes.")
        if len(raw) > self._max_bytes:
            raise FrameTooLarge("Message exceeds the configured size limit.")
        if not raw:
            raise ValidationFailed("Message is empty.", code="empty_message")
        if protocol not in client.protocols:
            raise AuthenticationFailed("protocol_not_permitted")

        adapter = self.adapters.get(protocol, Direction.INBOUND)
        try:
            decoded = adapter.decode(bytes(raw), context)
        except ValidationError:
            raise ValidationFailed("Decoded message failed validation.", code="decoded_invalid") from None
        if decoded.protocol != protocol:
            raise ProtocolError("Adapter returned a message for a different protocol.")

        if (
            context.bound_property_code
            and decoded.property_code
            and decoded.property_code != context.bound_property_code
        ):
            raise FacilityAuthorizationError(
                "Message property code differs from the property bound to this link.",
                code="link_property_mismatch",
            )
        property_code = decoded.property_code or context.bound_property_code
        facility_id = self._resolver.resolve(client, property_code)
        self._resolver.assert_no_scope_smuggling(
            decoded.body, facility_id=facility_id, property_code=property_code
        )

        if not self.handlers.has(decoded.message_type):
            raise UnsupportedMessage(
                "No handler is registered for this message type.",
                detail={"message_type": decoded.message_type},
            )
        if not decoded.idempotency_key:
            raise ValidationFailed("Message carries no idempotency key.", code="idempotency_key_missing")

        assert_transition(MessageStatus.RECEIVED, MessageStatus.VALIDATED)
        try:
            envelope = CanonicalEnvelope(
                external_message_id=decoded.external_message_id,
                ordering_key=self.handlers.get(decoded.message_type).ordering_key(decoded.body),
                idempotency_key=decoded.idempotency_key,
                correlation_id=cid,
                facility_id=facility_id,
                client_id=client.client_id,
                protocol=protocol,
                message_type=decoded.message_type,
                direction=Direction.INBOUND,
                schema_version=decoded.schema_version,
                received_at=self._next_received_at(),
                payload_hash=payload_hash(decoded.body),
                status=MessageStatus.VALIDATED,
                trace={"transport": context.transport},
                body=decoded.body,
            )
        except (ValidationError, ValueError):
            raise ValidationFailed("Canonical envelope failed validation.", code="envelope_invalid") from None
        assert_transition(MessageStatus.VALIDATED, MessageStatus.PENDING)
        return envelope

    def _next_received_at(self) -> datetime:
        """Strictly increasing intake timestamps (sprint gap G5).

        Per-entity ordering sorts by `received_on`; when two messages arrive at
        the same clock reading (coarse OS timers, fixed clocks) the tie used to
        fall back to the random message id and could reorder a stay's events.
        Within one gateway -- one process owns a link -- arrival order is now
        preserved by nudging ties forward by one microsecond. During a burst the
        stamp can run ahead of the wall clock by at most one microsecond per
        tied message (the message becomes claimable that much later).
        """
        with self._intake_lock:
            now = self._clock()
            last = self._last_received_at
            if last is not None and now <= last:
                now = last + timedelta(microseconds=1)
            self._last_received_at = now
            return now

    # -------------------------------------------------------------- outbound
    def request_outbound(self, request: OutboundRequest) -> uuid.UUID:
        adapter = self.adapters.get(request.protocol, Direction.OUTBOUND)
        if request.message_type not in adapter.message_types(Direction.OUTBOUND):
            raise UnsupportedMessage(
                "The adapter cannot send this message type.",
                detail={"message_type": request.message_type},
            )
        self._resolver.assert_authorized(request.client_id, request.facility_id)
        # Encode now so an unencodable request fails at the caller, not later
        # in the relay. The bytes are re-produced by the relay at send time.
        adapter.encode(request)
        outbox_id = self._repo.enqueue_outbox(
            OutboxDraft(
                protocol=request.protocol,
                message_type=request.message_type,
                body=request.body,
                correlation_id=accept_correlation_id(request.correlation_id),
            ),
            client_id=request.client_id,
            facility_id=request.facility_id,
            source_message_id=request.source_message_id,
            max_attempts=self._max_attempts,
            now=self._clock(),
        )
        self.metrics.inc("outbound_enqueued", protocol=str(request.protocol), message_type=request.message_type)
        return outbox_id

    # ---------------------------------------------------------------- audit
    def _audit_security(self, action: str, *, actor_id: str | None, detail: dict) -> None:
        try:
            self._repo.record_audit(
                AuditEvent(
                    action=action,
                    actor_type="client",
                    actor_id=actor_id,
                    facility_id=None,
                    message_id=None,
                    reason=None,
                    detail=detail,
                    occurred_at=self._clock(),
                )
            )
        except Exception:  # noqa: BLE001 - auditing must not mask the rejection
            logger.exception("failed to record security audit event action=%s", action)


def is_security_rejection(result: IntakeResult) -> bool:
    return bool(result.error) and result.error.get("category") == str(ErrorCategory.SECURITY)


__all__ = ["ExchangeAdapter", "ExchangeGateway", "IntegrationError", "is_security_rejection"]
