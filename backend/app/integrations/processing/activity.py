"""Per-protocol activity and bounded message search, computed from durable state.

Read-only. Used by the observability API (`/integrations/observability/*`).

What these figures are -- and are not:

* Counts are over the rows currently RETAINED in the integration tables. When
  INTEGRATION_RETENTION_DAYS is set (HF-21) SUCCEEDED / SENT rows older than the
  retention window are purged, so counts are not lifetime totals.
* Intake that was rejected before persistence (bad credentials, malformed XML,
  unknown property) never becomes a row; it is not counted here.
* `latest_failure` is the most recently RECEIVED message that is currently in
  RETRY_WAIT or DEAD_LETTER. The repository keeps only an error code and
  category -- never free text -- so nothing from the payload can leak through.

Every query is facility-scoped and row-bounded (aggregates group by indexed
columns; the search has a bounded date window, page size and offset).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.integrations.core.envelope import MessageStatus

PENDING_STATUSES = ("PENDING", "PROCESSING", "RETRY_WAIT")
FAILURE_STATUSES = ("RETRY_WAIT", "DEAD_LETTER")
#: Hard ceilings for the message search (HMS `Page` convention: max 100).
MAX_PAGE_SIZE = 100
MAX_OFFSET = 10_000


# ---------------------------------------------------------------- activity
@dataclass
class ProtocolActivity:
    protocol: str
    inbound: dict[str, int] = field(default_factory=dict)
    outbound: dict[str, int] = field(default_factory=dict)
    last_received_at: datetime | None = None
    last_succeeded_at: datetime | None = None
    oldest_pending_at: datetime | None = None
    last_outbound_sent_at: datetime | None = None
    #: retained inbound messages that needed more than one attempt
    retried_messages: int = 0
    #: retained inbound attempts beyond the first, summed
    extra_attempts: int = 0
    latest_failure: dict[str, Any] | None = None


def _later(a, b):
    return b if a is None or (b is not None and b > a) else a


def _earlier(a, b):
    return b if a is None or (b is not None and b < a) else a


def _failure(message_id, status, code, category, received_at, completed_at) -> dict[str, Any]:
    return {
        "message_id": message_id,
        "status": status,
        "error_code": code,
        "error_category": category,
        "received_at": received_at,
        "dead_lettered_at": completed_at if status == "DEAD_LETTER" else None,
    }


def activity_from_memory(messages, outbox, *, scope) -> dict[str, ProtocolActivity]:
    out: dict[str, ProtocolActivity] = {}

    def bucket(protocol) -> ProtocolActivity:
        key = str(protocol)
        if key not in out:
            out[key] = ProtocolActivity(key)
        return out[key]

    latest_fail_rx: dict[str, datetime] = {}
    for m in messages:
        if scope is not None and m.facility_id not in scope:
            continue
        a = bucket(m.protocol)
        status = str(m.status)
        a.inbound[status] = a.inbound.get(status, 0) + 1
        a.last_received_at = _later(a.last_received_at, m.received_at)
        if status in PENDING_STATUSES:
            a.oldest_pending_at = _earlier(a.oldest_pending_at, m.received_at)
        if m.status is MessageStatus.SUCCEEDED:
            a.last_succeeded_at = _later(a.last_succeeded_at, m.completed_at)
        if m.attempt_count > 1:
            a.retried_messages += 1
            a.extra_attempts += m.attempt_count - 1
        if status in FAILURE_STATUSES and m.last_error_code:
            key = (m.received_at, str(m.message_id))
            prev = latest_fail_rx.get(a.protocol)
            if prev is None or key > prev:
                latest_fail_rx[a.protocol] = key
                a.latest_failure = _failure(m.message_id, status, m.last_error_code, m.last_error_category,
                                            m.received_at, m.completed_at)
    for r in outbox:
        if scope is not None and r.facility_id not in scope:
            continue
        a = bucket(r.protocol)
        a.outbound[r.status] = a.outbound.get(r.status, 0) + 1
        if r.status == "SENT":
            a.last_outbound_sent_at = _later(a.last_outbound_sent_at, r.sent_at)
    return out


def activity_from_sql(engine: Engine, *, scope) -> dict[str, ProtocolActivity]:
    from app.integrations.processing.sql_models import InboundMessageRow as M
    from app.integrations.processing.sql_models import OutboxMessageRow as O

    if scope is not None and not scope:
        return {}

    def scoped(stmt, col):
        return stmt if scope is None else stmt.where(col.in_(list(scope)))

    out: dict[str, ProtocolActivity] = {}

    def bucket(protocol) -> ProtocolActivity:
        if protocol not in out:
            out[protocol] = ProtocolActivity(protocol)
        return out[protocol]

    def aware(value):
        if value is None or getattr(value, "tzinfo", None) is not None:
            return value
        return M.received_on.type.process_result_value(value, engine.dialect)

    with Session(engine) as s:
        for protocol, status, n in s.execute(scoped(
            select(M.protocol, M.status, func.count()).group_by(M.protocol, M.status), M.facility_id
        )):
            bucket(protocol).inbound[status] = int(n)
        for protocol, status, n in s.execute(scoped(
            select(O.protocol, O.status, func.count()).group_by(O.protocol, O.status), O.facility_id
        )):
            bucket(protocol).outbound[status] = int(n)
        for protocol, last_rx, last_ok, oldest, retried, extra in s.execute(scoped(
            select(
                M.protocol,
                func.max(M.received_on),
                func.max(case((M.status == "SUCCEEDED", M.completed_on))),
                func.min(case((M.status.in_(PENDING_STATUSES), M.received_on))),
                func.sum(case((M.attempt_count > 1, 1), else_=0)),
                func.sum(case((M.attempt_count > 1, M.attempt_count - 1), else_=0)),
            ).group_by(M.protocol),
            M.facility_id,
        )):
            a = bucket(protocol)
            a.last_received_at = aware(last_rx)
            a.last_succeeded_at = aware(last_ok)
            a.oldest_pending_at = aware(oldest)
            a.retried_messages = int(retried or 0)
            a.extra_attempts = int(extra or 0)
        for protocol, last_sent in s.execute(scoped(
            select(O.protocol, func.max(O.sent_on)).where(O.status == "SENT").group_by(O.protocol),
            O.facility_id,
        )):
            bucket(protocol).last_outbound_sent_at = aware(last_sent)
        for protocol in list(out):
            row = s.execute(scoped(
                select(M.id, M.status, M.last_error_code, M.last_error_category, M.received_on, M.completed_on)
                .where(M.protocol == protocol, M.status.in_(FAILURE_STATUSES), M.last_error_code.is_not(None))
                .order_by(M.received_on.desc(), M.id.desc())
                .limit(1),
                M.facility_id,
            )).first()
            if row is not None:
                out[protocol].latest_failure = _failure(row[0], row[1], row[2], row[3], row[4], row[5])
    return out


# ----------------------------------------------------------------- backlog
@dataclass
class BacklogSnapshot:
    """What the unfinished work of one protocol is actually waiting for.

    `next_attempt_at` already encodes when a row may be claimed: PENDING rows
    get the intake time, RETRY_WAIT rows the retry time and PROCESSING rows
    their lease expiry (sql_repository / InMemoryIntegrationRepository). So:

    * due_now      unfinished rows whose `next_attempt_at` has passed -- work a
                   worker should be doing right now (incl. abandoned leases);
    * scheduled    rows waiting for a FUTURE retry time (not a stall);
    * in_progress  PROCESSING rows whose lease is still valid;
    * oldest_due_at the earliest `next_attempt_at` among due rows -- the
                   start of the longest wait that nobody is serving;
    * ordering_blocked unfinished rows held back by an EARLIER dead-lettered
                   message with the same ordering key: only a redrive frees them.
    """

    protocol: str
    unfinished: int = 0
    due_now: int = 0
    scheduled: int = 0
    in_progress: int = 0
    oldest_due_at: datetime | None = None
    ordering_blocked: int = 0
    outbound_unfinished: int = 0
    outbound_due_now: int = 0
    outbound_scheduled: int = 0
    outbound_oldest_due_at: datetime | None = None


def backlog_from_memory(messages, outbox, *, scope, now) -> dict[str, BacklogSnapshot]:
    out: dict[str, BacklogSnapshot] = {}

    def bucket(protocol) -> BacklogSnapshot:
        key = str(protocol)
        if key not in out:
            out[key] = BacklogSnapshot(key)
        return out[key]

    rows = [m for m in messages if scope is None or m.facility_id in scope]
    dead = {}
    for m in rows:
        if str(m.status) == "DEAD_LETTER" and m.ordering_key:
            dead.setdefault((m.client_id, m.facility_id, m.ordering_key), []).append(
                (m.received_at, str(m.message_id)))
    for m in rows:
        status = str(m.status)
        if status not in PENDING_STATUSES:
            continue
        b = bucket(m.protocol)
        b.unfinished += 1
        due_at = m.next_attempt_at or m.received_at
        if due_at <= now:
            b.due_now += 1
            b.oldest_due_at = _earlier(b.oldest_due_at, due_at)
        elif status == "PROCESSING":
            b.in_progress += 1
        else:
            b.scheduled += 1
        if m.ordering_key:
            mine = (m.received_at, str(m.message_id))
            if any(d < mine for d in dead.get((m.client_id, m.facility_id, m.ordering_key), ())):
                b.ordering_blocked += 1
    for r in outbox:
        if scope is not None and r.facility_id not in scope:
            continue
        if r.status not in PENDING_STATUSES:
            continue
        b = bucket(r.protocol)
        b.outbound_unfinished += 1
        due_at = r.next_attempt_at or r.created_at
        if due_at <= now:
            b.outbound_due_now += 1
            b.outbound_oldest_due_at = _earlier(b.outbound_oldest_due_at, due_at)
        else:
            b.outbound_scheduled += 1
    return out


def backlog_from_sql(engine: Engine, *, scope, now) -> dict[str, BacklogSnapshot]:
    from sqlalchemy import and_, exists, or_
    from sqlalchemy.orm import aliased

    from app.integrations.processing.sql_models import InboundMessageRow as M
    from app.integrations.processing.sql_models import OutboxMessageRow as O

    if scope is not None and not scope:
        return {}

    def scoped(stmt, col):
        return stmt if scope is None else stmt.where(col.in_(list(scope)))

    def aware(value):
        if value is None or getattr(value, "tzinfo", None) is not None:
            return value
        return M.received_on.type.process_result_value(value, engine.dialect)

    out: dict[str, BacklogSnapshot] = {}

    def bucket(protocol) -> BacklogSnapshot:
        if protocol not in out:
            out[protocol] = BacklogSnapshot(protocol)
        return out[protocol]

    due_at = func.coalesce(M.next_attempt_at, M.received_on)
    is_due = due_at <= now
    o_due_at = func.coalesce(O.next_attempt_at, O.created_on)
    o_is_due = o_due_at <= now
    p = aliased(M)
    blocked_by_dead_letter = exists().where(
        p.client_id == M.client_id, p.facility_id == M.facility_id, p.ordering_key == M.ordering_key,
        p.status == "DEAD_LETTER",
        or_(p.received_on < M.received_on, and_(p.received_on == M.received_on, p.id < M.id)),
    )
    with Session(engine) as s:
        for protocol, n, due, processing_live, oldest in s.execute(scoped(
            select(
                M.protocol,
                func.count(),
                func.sum(case((is_due, 1), else_=0)),
                func.sum(case((and_(~is_due, M.status == "PROCESSING"), 1), else_=0)),
                func.min(case((is_due, due_at))),
            ).where(M.status.in_(PENDING_STATUSES)).group_by(M.protocol),
            M.facility_id,
        )):
            b = bucket(protocol)
            b.unfinished = int(n)
            b.due_now = int(due or 0)
            b.in_progress = int(processing_live or 0)
            b.scheduled = b.unfinished - b.due_now - b.in_progress
            b.oldest_due_at = aware(oldest)
        for protocol, n in s.execute(scoped(
            select(M.protocol, func.count())
            .where(M.status.in_(PENDING_STATUSES), M.ordering_key.is_not(None), blocked_by_dead_letter)
            .group_by(M.protocol),
            M.facility_id,
        )):
            bucket(protocol).ordering_blocked = int(n)
        for protocol, n, due, oldest in s.execute(scoped(
            select(O.protocol, func.count(), func.sum(case((o_is_due, 1), else_=0)),
                   func.min(case((o_is_due, o_due_at))))
            .where(O.status.in_(PENDING_STATUSES)).group_by(O.protocol),
            O.facility_id,
        )):
            b = bucket(protocol)
            b.outbound_unfinished = int(n)
            b.outbound_due_now = int(due or 0)
            b.outbound_scheduled = b.outbound_unfinished - b.outbound_due_now
            b.outbound_oldest_due_at = aware(oldest)
    return out


# ----------------------------------------------------------------- metrics
#: Supported windows: (span seconds, bucket seconds). Short ranges use short
#: buckets, long ranges daily buckets. Bounded so every series has <= 30 points.
METRIC_RANGES: dict[str, tuple[int, int]] = {
    "1h": (3600, 300),
    "24h": (86400, 3600),
    "7d": (7 * 86400, 86400),
    "30d": (30 * 86400, 86400),
}


@dataclass(frozen=True)
class MetricsQuery:
    """One protocol, one window. `facility_ids` is the EFFECTIVE set (caller
    scope intersected with any requested facility); None = unrestricted."""

    protocol: str
    start: datetime
    end: datetime
    bucket_seconds: int
    facility_ids: frozenset | None = None

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("metrics window must be timezone-aware")
        if self.end <= self.start or self.bucket_seconds <= 0:
            raise ValueError("invalid metrics window")

    @property
    def buckets(self) -> int:
        return int((self.end - self.start).total_seconds() // self.bucket_seconds)

    def index(self, at: datetime) -> int | None:
        if at is None or at < self.start or at >= self.end:
            return None
        return int((at - self.start).total_seconds() // self.bucket_seconds)


def metrics_window(range_key: str, now: datetime, tz_offset_minutes: int = 0) -> tuple[datetime, datetime, int]:
    """[start, end) for `range_key`, with bucket boundaries aligned to the
    viewer's local clock (`tz_offset_minutes` east of UTC) so a daily bucket is
    a local day. `end` is the end of the bucket containing `now`."""
    import math
    from datetime import UTC, timedelta

    span, bucket = METRIC_RANGES[range_key]
    offset = timedelta(minutes=tz_offset_minutes)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    local_seconds = (now + offset - epoch).total_seconds()
    end = epoch + timedelta(seconds=math.floor(local_seconds / bucket + 1) * bucket) - offset
    return end - timedelta(seconds=span), end, bucket


def _nearest_rank(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    import math

    k = max(1, math.ceil(p * len(sorted_values)))
    return sorted_values[k - 1]


def _empty_metrics() -> dict[str, Any]:
    return {
        "inbound_status": {}, "outbound_status": {}, "retried_messages": 0, "extra_attempts": 0,
        "series": {k: {} for k in ("received", "retried", "processed", "failed", "latency_sum",
                                   "outbound_created", "outbound_sent")},
        "latency": {"count": 0, "avg": None, "p50": None, "p95": None, "max": None},
        "errors": [], "message_types": [],
    }


def metrics_from_memory(messages, outbox, query: MetricsQuery, *, scope) -> dict[str, Any]:
    facilities = query.facility_ids if query.facility_ids is not None else (None if scope is None else set(scope))
    out = _empty_metrics()
    s = out["series"]

    def bump(series, i, n=1):
        if i is not None:
            series[i] = series.get(i, 0) + n

    latencies: list[float] = []
    errors: dict[tuple, int] = {}
    types: dict[str, int] = {}
    for m in messages:
        if str(m.protocol) != query.protocol or (facilities is not None and m.facility_id not in facilities):
            continue
        status = str(m.status)
        i_rx = query.index(m.received_at)
        if i_rx is not None:
            out["inbound_status"][status] = out["inbound_status"].get(status, 0) + 1
            bump(s["received"], i_rx)
            types[m.message_type] = types.get(m.message_type, 0) + 1
            if m.attempt_count > 1:
                out["retried_messages"] += 1
                out["extra_attempts"] += m.attempt_count - 1
                bump(s["retried"], i_rx)
            if status in FAILURE_STATUSES and m.last_error_code:
                key = (m.last_error_category, m.last_error_code)
                errors[key] = errors.get(key, 0) + 1
        i_done = query.index(m.completed_at)
        if status == "SUCCEEDED" and i_done is not None:
            bump(s["processed"], i_done)
            secs = (m.completed_at - m.received_at).total_seconds()
            latencies.append(secs)
            s["latency_sum"][i_done] = s["latency_sum"].get(i_done, 0.0) + secs
        elif status == "DEAD_LETTER" and i_done is not None:
            bump(s["failed"], i_done)
    for r in outbox:
        if str(r.protocol) != query.protocol or (facilities is not None and r.facility_id not in facilities):
            continue
        i_c = query.index(r.created_at)
        if i_c is not None:
            out["outbound_status"][r.status] = out["outbound_status"].get(r.status, 0) + 1
            bump(s["outbound_created"], i_c)
        if r.status == "SENT":
            bump(s["outbound_sent"], query.index(r.sent_at))
    latencies.sort()
    if latencies:
        out["latency"] = {"count": len(latencies), "avg": sum(latencies) / len(latencies),
                          "p50": _nearest_rank(latencies, 0.5), "p95": _nearest_rank(latencies, 0.95),
                          "max": latencies[-1]}
    out["errors"] = sorted(((c, k, n) for (c, k), n in errors.items()), key=lambda t: (-t[2], str(t[1])))[:10]
    out["message_types"] = sorted(types.items(), key=lambda t: (-t[1], t[0]))[:10]
    return out


def metrics_from_sql(engine: Engine, query: MetricsQuery, *, scope) -> dict[str, Any]:
    """Server-side aggregation only: every statement is a GROUP BY / COUNT /
    AVG over an indexed, bounded window, plus two single-row percentile
    lookups. No message rows are returned."""
    from datetime import UTC

    from sqlalchemy import literal_column

    from app.integrations.processing.sql_models import InboundMessageRow as M
    from app.integrations.processing.sql_models import OutboxMessageRow as O

    facilities = query.facility_ids if query.facility_ids is not None else (None if scope is None else set(scope))
    out = _empty_metrics()
    if facilities is not None and not facilities:
        return out
    s = out["series"]
    start_naive = query.start.astimezone(UTC).replace(tzinfo=None)

    def idx(col):
        return func.floor(func.timestampdiff(literal_column("SECOND"), start_naive, col) / query.bucket_seconds)

    def where_in(col, model):
        conds = [col >= query.start, col < query.end, model.protocol == query.protocol]
        if facilities is not None:
            conds.append(model.facility_id.in_(list(facilities)))
        return conds

    duration = func.timestampdiff(literal_column("MICROSECOND"), M.received_on, M.completed_on) / 1_000_000
    rx = where_in(M.received_on, M)
    done = where_in(M.completed_on, M)
    with Session(engine) as ses:
        for status, n, retried, extra in ses.execute(
            select(M.status, func.count(), func.sum(case((M.attempt_count > 1, 1), else_=0)),
                   func.sum(case((M.attempt_count > 1, M.attempt_count - 1), else_=0)))
            .where(*rx).group_by(M.status)
        ):
            out["inbound_status"][status] = int(n)
            out["retried_messages"] += int(retried or 0)
            out["extra_attempts"] += int(extra or 0)
        for i, n, retried in ses.execute(
            select(idx(M.received_on).label("i"), func.count(), func.sum(case((M.attempt_count > 1, 1), else_=0)))
            .where(*rx).group_by(literal_column("i"))
        ):
            s["received"][int(i)] = int(n)
            if retried:
                s["retried"][int(i)] = int(retried)
        for i, n, total in ses.execute(
            select(idx(M.completed_on).label("i"), func.count(), func.sum(duration))
            .where(*done, M.status == "SUCCEEDED").group_by(literal_column("i"))
        ):
            s["processed"][int(i)] = int(n)
            s["latency_sum"][int(i)] = float(total or 0)
        for i, n in ses.execute(
            select(idx(M.completed_on).label("i"), func.count())
            .where(*done, M.status == "DEAD_LETTER").group_by(literal_column("i"))
        ):
            s["failed"][int(i)] = int(n)
        n_lat, avg_lat, max_lat = ses.execute(
            select(func.count(), func.avg(duration), func.max(duration)).where(*done, M.status == "SUCCEEDED")
        ).one()
        if n_lat:
            def at_rank(p):
                import math

                k = max(1, math.ceil(p * n_lat)) - 1
                return float(ses.execute(
                    select(duration).where(*done, M.status == "SUCCEEDED").order_by(duration).offset(k).limit(1)
                ).scalar_one())
            out["latency"] = {"count": int(n_lat), "avg": float(avg_lat), "p50": at_rank(0.5),
                              "p95": at_rank(0.95), "max": float(max_lat)}
        out["errors"] = [
            (c, k, int(n)) for c, k, n in ses.execute(
                select(M.last_error_category, M.last_error_code, func.count().label("n"))
                .where(*rx, M.status.in_(FAILURE_STATUSES), M.last_error_code.is_not(None))
                .group_by(M.last_error_category, M.last_error_code)
                .order_by(literal_column("n").desc(), M.last_error_code).limit(10)
            )
        ]
        out["message_types"] = [
            (t, int(n)) for t, n in ses.execute(
                select(M.message_type, func.count().label("n")).where(*rx)
                .group_by(M.message_type).order_by(literal_column("n").desc(), M.message_type).limit(10)
            )
        ]
        ocreated = where_in(O.created_on, O)
        for status, n in ses.execute(select(O.status, func.count()).where(*ocreated).group_by(O.status)):
            out["outbound_status"][status] = int(n)
        for i, n in ses.execute(
            select(idx(O.created_on).label("i"), func.count()).where(*ocreated).group_by(literal_column("i"))
        ):
            s["outbound_created"][int(i)] = int(n)
        for i, n in ses.execute(
            select(idx(O.sent_on).label("i"), func.count()).where(*where_in(O.sent_on, O), O.status == "SENT")
            .group_by(literal_column("i"))
        ):
            s["outbound_sent"][int(i)] = int(n)
    return out


# ------------------------------------------------------------------ search
@dataclass(frozen=True)
class MessageQuery:
    """Bounded inbound message search in the HMS `Page` convention.

    Ordering is (received_at DESC, message_id DESC): total and deterministic,
    so the same query over unchanged data always returns the same pages.
    Bounds: a date window (enforced by the API), `page_size <= MAX_PAGE_SIZE`
    and `(page - 1) * page_size <= MAX_OFFSET`.
    """

    received_from: datetime
    received_to: datetime
    protocols: frozenset[str] | None = None
    statuses: frozenset[str] | None = None
    facility_ids: frozenset[uuid.UUID] | None = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be 1..{MAX_PAGE_SIZE}")
        if self.page < 1 or self.offset > MAX_OFFSET:
            raise ValueError(f"page out of range (offset must be <= {MAX_OFFSET})")
        if self.received_from.tzinfo is None or self.received_to.tzinfo is None:
            raise ValueError("received_from / received_to must be timezone-aware")
        if self.received_to < self.received_from:
            raise ValueError("received_to must not be before received_from")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def _effective_facilities(query: MessageQuery, scope) -> set | None:
    """Intersection of the caller's scope and the requested facilities.
    None = unrestricted (no scope restriction and no filter)."""
    if query.facility_ids is None:
        return None if scope is None else set(scope)
    return set(query.facility_ids) if scope is None else set(query.facility_ids) & set(scope)


def search_memory(messages, query: MessageQuery, *, scope) -> tuple[list, int]:
    facilities = _effective_facilities(query, scope)
    rows = [
        m for m in messages
        if (facilities is None or m.facility_id in facilities)
        and (query.protocols is None or str(m.protocol) in query.protocols)
        and (query.statuses is None or str(m.status) in query.statuses)
        and query.received_from <= m.received_at <= query.received_to
    ]
    rows.sort(key=lambda m: (m.received_at, str(m.message_id)), reverse=True)
    return rows[query.offset: query.offset + query.page_size], len(rows)


def search_sql(engine: Engine, query: MessageQuery, *, scope, to_stored) -> tuple[list, int]:
    from app.integrations.processing.sql_models import InboundMessageRow as M

    facilities = _effective_facilities(query, scope)
    if facilities is not None and not facilities:
        return [], 0
    conditions = [M.received_on >= query.received_from, M.received_on <= query.received_to]
    if facilities is not None:
        conditions.append(M.facility_id.in_(list(facilities)))
    if query.protocols is not None:
        conditions.append(M.protocol.in_(sorted(query.protocols)))
    if query.statuses is not None:
        conditions.append(M.status.in_(sorted(query.statuses)))
    with Session(engine) as s:
        total = int(s.execute(select(func.count()).select_from(M).where(*conditions)).scalar_one())
        rows = s.execute(
            select(M).where(*conditions)
            .order_by(M.received_on.desc(), M.id.desc())
            .offset(query.offset).limit(query.page_size)
        ).scalars().all()
        return [to_stored(r) for r in rows], total
