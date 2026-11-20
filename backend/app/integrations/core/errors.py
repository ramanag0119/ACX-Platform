"""Error taxonomy.

Every failure inside the integration framework is an `IntegrationError` with a
`category`. The category -- not the exception class name -- drives behaviour:

    TRANSIENT         retried with bounded back-off
    PERMANENT         never retried; dead-lettered
    VALIDATION        message is well-formed but unacceptable; rejected
    PROTOCOL          bytes do not follow the protocol grammar; rejected
    SECURITY          authentication / facility authorization; rejected,
                      never retried, never echoes the offending value
    CONFLICT          idempotency key reused with different content
    UNSUPPORTED       protocol / message type has no adapter or handler
    VENDOR_BLOCKED    needs a vendor document that has not been supplied
    APPROVAL_BLOCKED  needs a business / DBA approval that is not recorded
    LEASE_LOST        a worker's lease expired; its result is discarded

Messages are written for logs and API responses, so they must never contain
payload values, credentials or guest data. Pass identifiers in `detail` only
when they are not sensitive (field ids, decision ids, message ids).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCategory(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    VALIDATION = "validation"
    PROTOCOL = "protocol"
    SECURITY = "security"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"
    VENDOR_BLOCKED = "vendor_blocked"
    APPROVAL_BLOCKED = "approval_blocked"
    LEASE_LOST = "lease_lost"


class IntegrationError(Exception):
    category: ErrorCategory = ErrorCategory.PERMANENT
    code: str = "integration_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.detail = detail or {}

    @property
    def retryable(self) -> bool:
        return self.category is ErrorCategory.TRANSIENT

    def as_dict(self) -> dict[str, Any]:
        """Safe, client-facing representation (no payload values)."""
        out: dict[str, Any] = {
            "code": self.code,
            "category": str(self.category),
            "message": self.message,
        }
        if self.detail:
            out["detail"] = self.detail
        return out


class TransientFailure(IntegrationError):
    category = ErrorCategory.TRANSIENT
    code = "transient_failure"


class PermanentFailure(IntegrationError):
    category = ErrorCategory.PERMANENT
    code = "permanent_failure"


class ValidationFailed(IntegrationError):
    category = ErrorCategory.VALIDATION
    code = "validation_failed"


class ProtocolError(IntegrationError):
    category = ErrorCategory.PROTOCOL
    code = "protocol_error"


class FrameTooLarge(ProtocolError):
    code = "frame_too_large"


class AuthenticationFailed(IntegrationError):
    """Deliberately generic: callers never learn WHY (unknown vs disabled)."""

    category = ErrorCategory.SECURITY
    code = "authentication_failed"

    def __init__(self, reason: str = "unspecified") -> None:
        super().__init__("Integration client authentication failed.")
        #: Internal reason for audit/metrics. Never returned to the caller.
        self.reason = reason

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "category": str(self.category), "message": self.message}


class FacilityAuthorizationError(IntegrationError):
    category = ErrorCategory.SECURITY
    code = "facility_not_authorized"


class IdempotencyConflict(IntegrationError):
    category = ErrorCategory.CONFLICT
    code = "idempotency_conflict"


class UnsupportedMessage(IntegrationError):
    category = ErrorCategory.UNSUPPORTED
    code = "unsupported_message"


class UnsupportedProtocol(IntegrationError):
    category = ErrorCategory.UNSUPPORTED
    code = "unsupported_protocol"


class VendorSpecificationBlocked(IntegrationError):
    category = ErrorCategory.VENDOR_BLOCKED
    code = "vendor_specification_missing"

    def __init__(self, message: str, *, decision: str) -> None:
        super().__init__(message, detail={"decision": decision})
        self.decision = decision


class ApprovalRequired(IntegrationError):
    category = ErrorCategory.APPROVAL_BLOCKED
    code = "approval_required"

    def __init__(self, message: str, *, decisions: list[str]) -> None:
        super().__init__(message, detail={"decisions": list(decisions)})
        self.decisions = list(decisions)


class LeaseLost(IntegrationError):
    category = ErrorCategory.LEASE_LOST
    code = "lease_lost"


class InvalidTransition(IntegrationError):
    category = ErrorCategory.PERMANENT
    code = "invalid_status_transition"


class NotFoundInScope(IntegrationError):
    """The record does not exist OR is outside the caller's facility scope.

    The two cases are intentionally indistinguishable so scope cannot be probed.
    """

    category = ErrorCategory.SECURITY
    code = "not_found"


# --- transport -------------------------------------------------------------


class TransportError(TransientFailure):
    code = "transport_error"


class ConnectTimeout(TransportError):
    code = "connect_timeout"


class ReadTimeout(TransportError):
    code = "read_timeout"


class WriteTimeout(TransportError):
    code = "write_timeout"


class ConnectionClosed(TransportError):
    code = "connection_closed"


class TransportNotConnected(TransportError):
    code = "not_connected"


def classify(exc: BaseException) -> IntegrationError:
    """Map any exception onto the taxonomy.

    Unknown exceptions are TRANSIENT: the retry budget is bounded, so a
    programming error ends in the dead-letter queue after N attempts instead of
    being silently dropped on the first one. The original exception text is NOT
    copied, because it may contain payload values.
    """
    if isinstance(exc, IntegrationError):
        return exc
    return TransientFailure(
        "Unexpected handler failure.",
        code="unexpected_error",
        detail={"exception_type": type(exc).__name__},
    )
