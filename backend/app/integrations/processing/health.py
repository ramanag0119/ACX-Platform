"""Facility-level integration health, computed from durable state.

Derived from the message tables rather than in-process counters, so the
figures are the same whichever API process answers and survive restarts.
Latency is `completed_on - received_on` of SUCCEEDED inbound messages inside
the window (end-to-end: intake -> business commit).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.integrations.core.envelope import MessageStatus

#: Upper bound on rows read for latency statistics per call.
LATENCY_SAMPLE_LIMIT = 5000


@dataclass
class ClientActivity:
    client_id: uuid.UUID
    last_received_at: datetime | None = None
    last_succeeded_at: datetime | None = None


@dataclass
class FacilityHealth:
    facility_id: uuid.UUID
    inbound: dict[str, int] = field(default_factory=dict)
    outbound: dict[str, int] = field(default_factory=dict)
    oldest_pending_at: datetime | None = None
    latencies_ms: list[float] = field(default_factory=list)
    clients: dict[uuid.UUID, ClientActivity] = field(default_factory=dict)

    def as_dict(self, now: datetime) -> dict[str, Any]:
        lat = sorted(self.latencies_ms)

        def pct(p: float) -> float | None:
            if not lat:
                return None
            return round(lat[min(len(lat) - 1, int(round(p * (len(lat) - 1))))], 1)

        pending = sum(self.inbound.get(s, 0) for s in ("PENDING", "PROCESSING", "RETRY_WAIT"))
        return {
            "facility_id": str(self.facility_id),
            "inbound_by_status": dict(sorted(self.inbound.items())),
            "outbound_by_status": dict(sorted(self.outbound.items())),
            "inbound_total": sum(self.inbound.values()),
            "outbound_total": sum(self.outbound.values()),
            "pending": pending,
            "retrying": self.inbound.get("RETRY_WAIT", 0),
            "failed_dead_letter": self.inbound.get("DEAD_LETTER", 0),
            "outbound_dead_letter": self.outbound.get("DEAD_LETTER", 0),
            "oldest_pending_age_seconds": (
                round((now - self.oldest_pending_at).total_seconds(), 3) if self.oldest_pending_at else None
            ),
            "latency_ms": {"samples": len(lat), "p50": pct(0.5), "p95": pct(0.95), "max": pct(1.0)},
            "clients": [
                {
                    "client_id": str(c.client_id),
                    "last_received_at": c.last_received_at.isoformat() if c.last_received_at else None,
                    "last_succeeded_at": c.last_succeeded_at.isoformat() if c.last_succeeded_at else None,
                }
                for c in sorted(self.clients.values(), key=lambda c: str(c.client_id))
            ],
        }


def _bucket(out: dict, facility_id: uuid.UUID) -> FacilityHealth:
    if facility_id not in out:
        out[facility_id] = FacilityHealth(facility_id)
    return out[facility_id]


def _client(h: FacilityHealth, client_id: uuid.UUID) -> ClientActivity:
    if client_id not in h.clients:
        h.clients[client_id] = ClientActivity(client_id)
    return h.clients[client_id]


def _later(a, b):
    return b if a is None or (b is not None and b > a) else a


def from_memory(messages, outbox, *, scope, now: datetime, window: timedelta) -> list[FacilityHealth]:
    out: dict[uuid.UUID, FacilityHealth] = {}
    since = now - window
    for m in messages:
        if scope is not None and m.facility_id not in scope:
            continue
        h = _bucket(out, m.facility_id)
        h.inbound[str(m.status)] = h.inbound.get(str(m.status), 0) + 1
        c = _client(h, m.client_id)
        c.last_received_at = _later(c.last_received_at, m.received_at)
        if m.status in (MessageStatus.PENDING, MessageStatus.PROCESSING, MessageStatus.RETRY_WAIT):
            h.oldest_pending_at = m.received_at if h.oldest_pending_at is None else min(h.oldest_pending_at, m.received_at)
        if m.status is MessageStatus.SUCCEEDED and m.completed_at:
            c.last_succeeded_at = _later(c.last_succeeded_at, m.completed_at)
            if m.completed_at >= since:
                h.latencies_ms.append((m.completed_at - m.received_at).total_seconds() * 1000)
    for r in outbox:
        if scope is not None and r.facility_id not in scope:
            continue
        h = _bucket(out, r.facility_id)
        h.outbound[r.status] = h.outbound.get(r.status, 0) + 1
    return sorted(out.values(), key=lambda h: str(h.facility_id))


def from_sql(engine: Engine, *, scope, now: datetime, window: timedelta) -> list[FacilityHealth]:
    from app.integrations.processing.sql_models import InboundMessageRow as M
    from app.integrations.processing.sql_models import OutboxMessageRow as O

    if scope is not None and not scope:
        return []

    def scoped(stmt, col):
        return stmt if scope is None else stmt.where(col.in_(list(scope)))

    out: dict[uuid.UUID, FacilityHealth] = {}
    with Session(engine) as s:
        for fid, status, n in s.execute(scoped(
            select(M.facility_id, M.status, func.count()).group_by(M.facility_id, M.status), M.facility_id
        )):
            _bucket(out, fid).inbound[status] = int(n)
        for fid, status, n in s.execute(scoped(
            select(O.facility_id, O.status, func.count()).group_by(O.facility_id, O.status), O.facility_id
        )):
            _bucket(out, fid).outbound[status] = int(n)
        for fid, oldest in s.execute(scoped(
            select(M.facility_id, func.min(M.received_on))
            .where(M.status.in_(("PENDING", "PROCESSING", "RETRY_WAIT"))).group_by(M.facility_id),
            M.facility_id,
        )):
            _bucket(out, fid).oldest_pending_at = _aware(oldest, M, engine)
        succeeded = func.max(case((M.status == "SUCCEEDED", M.completed_on)))
        for fid, cid, last_rx, last_ok in s.execute(scoped(
            select(M.facility_id, M.client_id, func.max(M.received_on), succeeded)
            .group_by(M.facility_id, M.client_id),
            M.facility_id,
        )):
            c = _client(_bucket(out, fid), cid)
            c.last_received_at = _aware(last_rx, M, engine)
            c.last_succeeded_at = _aware(last_ok, M, engine)
        rows = s.execute(scoped(
            select(M.facility_id, M.received_on, M.completed_on)
            .where(M.status == "SUCCEEDED", M.completed_on >= now - window)
            .order_by(M.completed_on.desc()).limit(LATENCY_SAMPLE_LIMIT),
            M.facility_id,
        )).all()
        for fid, rx, done in rows:
            _bucket(out, fid).latencies_ms.append((done - rx).total_seconds() * 1000)
    return sorted(out.values(), key=lambda h: str(h.facility_id))


def _aware(value, model, engine):
    """Aggregates bypass the UTCDateTime type decorator; re-apply it."""
    if value is None or getattr(value, "tzinfo", None) is not None:
        return value
    return model.received_on.type.process_result_value(value, engine.dialect)
