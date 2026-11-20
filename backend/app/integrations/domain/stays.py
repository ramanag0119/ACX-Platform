"""Stay domain adapter around the EXISTING `app.services.stays_write` service.

Canonical message types handled (HMS-internal names, not vendor records):

    stay.check_in   body: external_stay_ref (str, required), occurred_at (ISO-8601, optional)
    stay.check_out  body: external_stay_ref (str, required), occurred_at (ISO-8601, optional)

What this adapter does NOT do: it never writes HMS tables itself. It resolves
the HMS stay, verifies the stay belongs to the message's facility, and calls
`stays_write.check_in` / `check_out`, so every HMS business rule (allocation
required, blocking room conditions, status checks, room-status sync) still
applies.

Gates, in order:
  1. LiveWriteGate (INTEGRATION_LIVE_DOMAIN_WRITES + HF-01/02/05/19 approved)
  2. an HMS actor id (HF-18) to stamp modified_by
  3. the stay is resolved through an ExternalReferenceResolver. `stay` has an
     `external_stay_ref_number` column, but whether a PMS confirmation number
     belongs there, and whether it is unique per facility, is HF-02 / HF-31 --
     so the resolver is injected and no production resolver is registered.
  4. facility ownership: every room the stay holds must be in the message's
     facility (stay has no facility_id; scope is via room_allocation -> amenity).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select

from app.integrations.core.envelope import CanonicalEnvelope
from app.integrations.core.errors import (
    ApprovalRequired,
    FacilityAuthorizationError,
    PermanentFailure,
    TransientFailure,
    ValidationFailed,
)
from app.integrations.domain.approvals import LiveWriteGate
from app.integrations.exchange.registry import HandlerContext, HandlerResult, MessageHandler
from app.integrations.processing.repository import AuditDraft

CHECK_IN = "stay.check_in"
CHECK_OUT = "stay.check_out"


class ExternalReferenceResolver(Protocol):
    def resolve_stay(
        self, session: Any, *, client_id: uuid.UUID, facility_id: uuid.UUID, external_ref: str
    ) -> uuid.UUID | None: ...


@dataclass(frozen=True)
class StayCommand:
    action: str  # "check_in" | "check_out"
    external_ref: str
    occurred_at: datetime | None


def plan(envelope: CanonicalEnvelope) -> StayCommand:
    body = envelope.body
    ref = body.get("external_stay_ref")
    if not isinstance(ref, str) or not ref.strip() or len(ref) > 100:
        raise ValidationFailed("external_stay_ref is required.", code="external_stay_ref_missing")
    occurred = body.get("occurred_at")
    when = None
    if occurred is not None:
        if not isinstance(occurred, str):
            raise ValidationFailed("occurred_at must be an ISO-8601 string.", code="occurred_at_invalid")
        try:
            when = datetime.fromisoformat(occurred)
        except ValueError:
            raise ValidationFailed("occurred_at must be an ISO-8601 string.", code="occurred_at_invalid") from None
        if when.tzinfo is None:
            raise ValidationFailed("occurred_at must carry a UTC offset.", code="occurred_at_naive")
        when = when.astimezone(UTC)
    if envelope.message_type == CHECK_IN:
        action = "check_in"
    elif envelope.message_type == CHECK_OUT:
        action = "check_out"
    else:
        raise ValidationFailed("Not a stay message.", code="not_a_stay_message")
    return StayCommand(action=action, external_ref=ref.strip(), occurred_at=when)


@dataclass(frozen=True)
class StayState:
    actual_checkin_time: datetime | None
    actual_checkout_time: datetime | None
    status: str | None


def load_stay_state(session: Any, stay_id: uuid.UUID) -> StayState | None:
    """Read-only snapshot used for business-level idempotency."""
    from app.models import Stay

    stay = session.get(Stay, stay_id)
    if stay is None:
        return None
    return StayState(stay.actual_checkin_time, stay.actual_checkout_time, stay.status)


def already_applied(action: str, state: StayState) -> bool:
    """True when the stay is ALREADY in the state the message asks for.

    A PMS re-sends events under new message ids (link restarts, resyncs), so a
    second check-in for a stay that is checked in -- and not yet checked out --
    is a no-op, not a failure. Anything else that HMS rejects (e.g. check-in of
    a checked-out stay) is still a genuine conflict and is dead-lettered.
    """
    if action == "check_in":
        return state.actual_checkin_time is not None and state.actual_checkout_time is None
    return state.actual_checkout_time is not None


def stay_facility_ids(session: Any, stay_id: uuid.UUID) -> set[uuid.UUID]:
    from app.models import Amenity, RoomAllocation

    rows = session.execute(
        select(Amenity.facility_id)
        .join(RoomAllocation, RoomAllocation.room_id == Amenity.id)
        .where(RoomAllocation.stay_id == stay_id)
    ).scalars().all()
    return set(rows)


class StayDomainAdapter:
    def __init__(
        self,
        *,
        gate: LiveWriteGate,
        resolver: ExternalReferenceResolver | None,
        actor_id: uuid.UUID | None,
        services: Any | None = None,
        facility_lookup: Callable[[Any, uuid.UUID], set[uuid.UUID]] = stay_facility_ids,
        state_lookup: Callable[[Any, uuid.UUID], StayState | None] = load_stay_state,
    ) -> None:
        self._gate = gate
        self._resolver = resolver
        self._actor_id = actor_id
        self._services = services
        self._facility_lookup = facility_lookup
        self._state_lookup = state_lookup

    @property
    def actor_id(self) -> uuid.UUID | None:
        return self._actor_id

    def _stays_write(self):
        if self._services is not None:
            return self._services
        from app.services import stays_write

        return stays_write

    def apply(self, envelope: CanonicalEnvelope, session: Any) -> dict[str, Any]:
        command = plan(envelope)  # validate first: a bad message is rejected even while gated
        self._gate.assert_open()
        if self._actor_id is None:
            raise ApprovalRequired("No HMS actor is configured for integration writes.", decisions=["HF-18"])
        if self._resolver is None:
            raise ApprovalRequired("No external stay reference resolver is approved.", decisions=["HF-02"])
        if session is None:
            raise PermanentFailure("Domain writes need a database session.", code="no_session")

        stay_id = self._resolver.resolve_stay(
            session, client_id=envelope.client_id, facility_id=envelope.facility_id,
            external_ref=command.external_ref,
        )
        if stay_id is None:
            # The PMS may send the event before HMS knows the stay: retry later.
            raise TransientFailure("Stay is not known to HMS yet.", code="stay_not_found")

        facilities = self._facility_lookup(session, stay_id)
        if not facilities:
            raise PermanentFailure("Stay holds no room, so its facility is unknown.", code="stay_without_room")
        if facilities != {envelope.facility_id}:
            raise FacilityAuthorizationError(
                "Stay does not belong to the message's facility.", code="stay_facility_mismatch"
            )

        state = self._state_lookup(session, stay_id)
        if state is not None and already_applied(command.action, state):
            return {"stay_id": str(stay_id), "action": command.action, "already_applied": True}

        service = self._stays_write()
        from app.services.writes import WriteError

        try:
            fn = service.check_in if command.action == "check_in" else service.check_out
            fn(session, stay_id, actor_id=self._actor_id, when=command.occurred_at)
        except WriteError as exc:
            # HMS business rule rejected the change (already checked in, ...).
            raise PermanentFailure(
                "HMS rejected the stay change.", code="hms_business_rule",
                detail={"rule": type(exc).__name__},
            ) from None
        return {"stay_id": str(stay_id), "action": command.action, "already_applied": False}


class StayEventHandler(MessageHandler):
    def __init__(self, message_type: str, adapter: StayDomainAdapter) -> None:
        if message_type not in (CHECK_IN, CHECK_OUT):
            raise ValueError("unsupported stay message type")
        self.message_type = message_type
        self._adapter = adapter

    def ordering_key(self, body: dict[str, Any]) -> str | None:
        """Check-in and check-out of one stay must not be reordered."""
        ref = body.get("external_stay_ref")
        return f"stay:{ref.strip()}"[:200] if isinstance(ref, str) and ref.strip() else None

    def handle(self, envelope: CanonicalEnvelope, ctx: HandlerContext) -> HandlerResult:
        summary = self._adapter.apply(envelope, ctx.session)
        # Written in the same transaction as the HMS change (see AuditDraft).
        ctx.audit(AuditDraft(
            action=f"domain.{envelope.message_type}",
            actor_type="system",
            actor_id=str(self._adapter.actor_id) if self._adapter.actor_id else None,
            detail=summary,
        ))
        return HandlerResult(summary=summary)
