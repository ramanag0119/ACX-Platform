"""Read-only integration observability: the dashboard information model.

Served by `/api/v1/integrations/observability/*` (see api/router.py). Nothing
here writes, enqueues, redrives or changes a switch.

Rules this module enforces:

* **No fabricated telemetry.** A figure that cannot be measured is returned as
  `null` with a `status` of `not_available` / `not_observable` and a reason --
  never as 0. A 0 means "the table was queried and holds no such rows".
* **Scope is stated.** Durable counts are over RETAINED rows (retention purge,
  HF-21). In-process figures (heartbeats, intake-rejection counters, link
  probes) say `this_api_process` because the API process cannot see other
  processes (e.g. the integration service that runs the workers).
* **Readiness dimensions are independent.** Synthetic certification never
  implies vendor validation; nothing is `ready` for production unless every
  required decision is APPROVED *with evidence* in `domain/approvals.py`,
  the adapters are driven by a verified specification, persistence is
  provisioned, the switches are on and a certification result is reported.
* **No sensitive data.** Error information is limited to code and category
  identifiers matching a strict pattern; anything else becomes "redacted".
  No payloads, client codes, secrets, peer addresses or worker host names.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.integrations.adapters.base import AdapterReadiness
from app.integrations.core.envelope import Direction, Protocol
from app.integrations.domain.approvals import DECISIONS, Decision, pending
from app.integrations.processing.activity import PENDING_STATUSES, BacklogSnapshot, ProtocolActivity

PROTOCOLS: tuple[str, ...] = (str(Protocol.HTNG), str(Protocol.FIAS))

#: Decisions each readiness dimension depends on. Sources:
#: docs/HTNG_FIAS_CANONICAL_DECISION_REGISTER.md and HTNG_FIAS_BLOCKER_REGISTER.md.
#: A decision missing from the code register counts as pending (never approved).
VENDOR_DECISIONS: dict[str, tuple[str, ...]] = {
    str(Protocol.HTNG): ("HF-07", "HF-08"),
    str(Protocol.FIAS): ("HF-05", "HF-06", "HF-11"),
}
BUSINESS_DECISIONS: tuple[str, ...] = ("HF-01", "HF-02", "HF-18", "HF-19", "HF-21")
DBA_DECISIONS: tuple[str, ...] = ("HF-39",)

#: Default age after which a non-empty backlog is classified as stalled.
DEFAULT_STALL_SECONDS = 900

WORKER_COMPONENTS = ("inbound_worker", "outbox_relay", "integration_service")
NOT_AVAILABLE = "not_available"
NOT_OBSERVABLE = "not_observable"
NOT_REPORTED = "not_reported"

_SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.:-]{0,63}")
_STATUS_VALUE = re.compile(r"[A-Z_]{1,16}")


def safe_identifier(value: Any) -> str | None:
    """Pass through only short lower-case identifiers (error codes/categories)."""
    if value is None:
        return None
    text = str(value)
    return text if _SAFE_IDENTIFIER.fullmatch(text) else "redacted"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _later(a: datetime | None, b: datetime | None) -> datetime | None:
    return b if a is None or (b is not None and b > a) else a


# ------------------------------------------------------------ message items
def sanitized_error(code: str | None, category: str | None) -> dict[str, str | None] | None:
    if code is None and category is None:
        return None
    return {"code": safe_identifier(code), "category": safe_identifier(category)}


def message_item(m) -> dict[str, Any]:
    """Dashboard view of one inbound message. Deliberately omits payload,
    payload hash, idempotency / ordering keys and external ids (they can carry
    reservation or room identifiers), client id and lease owner (host name)."""
    return {
        "message_id": str(m.message_id),
        "protocol": str(m.protocol),
        "facility_id": str(m.facility_id),
        "direction": str(m.direction),
        "message_type": m.message_type,
        "status": str(m.status),
        "received_at": _iso(m.received_at),
        "completed_at": _iso(m.completed_at),
        "attempt_count": m.attempt_count,
        "retry_count": max(m.attempt_count - 1, 0),
        "max_attempts": m.max_attempts,
        "next_attempt_at": _iso(m.next_attempt_at),
        "correlation_id": m.correlation_id,
        "error": sanitized_error(m.last_error_code, m.last_error_category),
    }


def dlq_item(m, *, caller_may_redrive: bool) -> dict[str, Any]:
    """Dead-letter view. `completed_at` of a dead letter is the end of its
    last failed attempt (the repository stamps it when dead-lettering)."""
    item = message_item(m)
    state_eligible = str(m.status) == "DEAD_LETTER"
    return {
        "message_id": item["message_id"],
        "protocol": item["protocol"],
        "facility_id": item["facility_id"],
        "direction": item["direction"],
        "message_type": item["message_type"],
        "status": item["status"],
        "failure_category": item["error"]["category"] if item["error"] else None,
        "failure_code": item["error"]["code"] if item["error"] else None,
        "attempt_count": item["attempt_count"],
        "retry_count": item["retry_count"],
        "received_at": item["received_at"],
        "last_attempt_at": item["completed_at"],
        "correlation_id": item["correlation_id"],
        "redrive": {
            # Both facts are exactly what the existing redrive endpoint checks:
            # status DEAD_LETTER in the caller's scope, and the write grant.
            "state_eligible": state_eligible,
            "caller_has_permission": caller_may_redrive,
            "eligible": state_eligible and caller_may_redrive,
        },
    }


# ---------------------------------------------------------------- overview
def _transport(protocol: str, rt, adapter_states: list[dict]) -> dict[str, Any]:
    s = rt.settings
    if protocol == str(Protocol.HTNG):
        enabled = bool(s.ENABLED and s.HTNG_INBOUND_ENABLED and rt.htng_adapter is not None)
        inbound_blocked = any(a["readiness"] == str(AdapterReadiness.BLOCKED)
                              for a in adapter_states if a["direction"] == str(Direction.INBOUND))
        if not enabled:
            status = "disabled"
        elif inbound_blocked:
            status = "enabled_adapter_blocked"
        else:
            status = "enabled"
        return {
            "kind": "http-soap inbound endpoint",
            "status": status,
            "integration_enabled": bool(s.ENABLED),
            "inbound_endpoint_enabled": bool(s.HTNG_INBOUND_ENABLED),
            # No vendor endpoint exists until HF-07 / HF-24 (same as /readiness).
            "outbound_vendor_endpoint": "not_configured",
        }

    links = [name for name, proto in sorted(rt.transport_protocols.items())
             if proto == protocol and name in rt.transports]
    if not links:
        return {
            "kind": "tcp link",
            "status": NOT_OBSERVABLE,
            "reason": "No FIAS link is registered in this API process; links run in the integration "
                      "service process and their state is not shared with the API.",
            "links": None,
            "active_connections": None,
        }
    out = []
    for name in links:
        try:
            probe = rt.transports[name]() or {}
        except Exception:  # noqa: BLE001 -- a broken probe must not break the dashboard
            probe = {"state": "probe_failed"}
        out.append({
            "name": name,
            "state": safe_identifier(probe.get("state")) or "unknown",
            "connected_since": probe.get("connected_since"),
            "connections": probe.get("connections"),
            "reconnect_attempts": probe.get("reconnect_attempts"),
            "frames_received": probe.get("frames_received"),
            "framing_errors": probe.get("framing_errors"),
            "last_error_code": safe_identifier(probe.get("last_error_code")),
            "last_error_at": probe.get("last_error_at"),
        })
    states = {link["state"] for link in out}
    connected = sum(1 for link in out if link["state"] == "connected")
    status = "connected" if connected == len(out) else ("degraded" if connected else
             ("connecting" if "connecting" in states else "disconnected"))
    return {"kind": "tcp link", "status": status, "scope": "this_api_process",
            "links": out, "active_connections": connected}


def _intake_rejections(protocol: str, rt, transport: dict) -> dict[str, Any]:
    """In-process counters. HTNG intake runs in the API process; FIAS intake
    runs wherever the link runs, so it is observable only with a local link."""
    if protocol == str(Protocol.FIAS) and transport["status"] == NOT_OBSERVABLE:
        return {"status": NOT_OBSERVABLE, "reason": "FIAS intake does not run in this API process.",
                "rejected_by_category": None, "auth_failures_by_reason": None}
    rejected: dict[str, int] = {}
    auth: dict[str, int] = {}
    for key, n in rt.metrics.snapshot()["counters"].items():
        name, *labels = key.split("|")
        lab = dict(item.split("=", 1) for item in labels if "=" in item)
        if lab.get("protocol") != protocol:
            continue
        if name == "intake_rejected":
            k = safe_identifier(lab.get("category")) or "unknown"
            rejected[k] = rejected.get(k, 0) + n
        elif name == "auth_failures":
            k = safe_identifier(lab.get("reason")) or "unknown"
            auth[k] = auth.get(k, 0) + n
    return {"status": "observed", "scope": "this_api_process_since_start",
            "rejected_by_category": dict(sorted(rejected.items())),
            "auth_failures_by_reason": dict(sorted(auth.items()))}


def _authentication(protocol: str, coverage: dict | None, coverage_error: str | None) -> dict[str, Any]:
    if coverage is None:
        return {"status": NOT_AVAILABLE, "reason": coverage_error, "enabled_clients": None,
                "enabled_mappings": None}
    c = coverage.get(protocol, {"enabled_clients": 0, "enabled_mappings": 0})
    status = "configured" if c["enabled_clients"] and c["enabled_mappings"] else "not_configured"
    return {"status": status, "scope": "facilities_in_caller_scope", **c}


def _messages(a: ProtocolActivity | None, available: bool, reason: str | None) -> dict[str, Any]:
    if not available:
        return {"status": NOT_AVAILABLE, "reason": reason, "inbound": None, "outbound": None,
                "retried_messages": None, "extra_attempts": None, "last_received_at": None,
                "last_succeeded_at": None, "last_outbound_sent_at": None}
    a = a or ProtocolActivity("")
    inbound = a.inbound
    outbound = a.outbound
    return {
        "status": "measured",
        "basis": "retained_rows",
        "inbound": {
            "total": sum(inbound.values()),
            "by_status": dict(sorted(inbound.items())),
            "pending": sum(inbound.get(x, 0) for x in PENDING_STATUSES),
            "succeeded": inbound.get("SUCCEEDED", 0),
            "retry_wait": inbound.get("RETRY_WAIT", 0),
            "failed_dead_letter": inbound.get("DEAD_LETTER", 0),
        },
        "outbound": {
            "total": sum(outbound.values()),
            "by_status": dict(sorted(outbound.items())),
            "pending": sum(outbound.get(x, 0) for x in PENDING_STATUSES),
            "sent": outbound.get("SENT", 0),
            "retry_wait": outbound.get("RETRY_WAIT", 0),
            "failed_dead_letter": outbound.get("DEAD_LETTER", 0),
        },
        "retried_messages": a.retried_messages,
        "extra_attempts": a.extra_attempts,
        "last_received_at": _iso(a.last_received_at),
        "last_succeeded_at": _iso(a.last_succeeded_at),
        "last_outbound_sent_at": _iso(a.last_outbound_sent_at),
    }


def _last_error(a: ProtocolActivity | None, available: bool) -> dict[str, Any] | None:
    if not available or a is None or a.latest_failure is None:
        return None
    f = a.latest_failure
    return {
        "message_id": str(f["message_id"]),
        "status": f["status"],
        "error": sanitized_error(f["error_code"], f["error_category"]),
        "received_at": _iso(f["received_at"]),
        "dead_lettered_at": _iso(f["dead_lettered_at"]),
    }


def _heartbeats(rt) -> dict[str, Any]:
    beats = {name: _iso(rt.metrics.last_heartbeat(name)) for name in WORKER_COMPONENTS}
    return {"scope": "this_api_process", "observed": any(beats.values()), "last": beats}


def _age(now: datetime, since: datetime | None) -> float | None:
    return round((now - since).total_seconds(), 3) if since else None


def _processing(a: ProtocolActivity | None, available: bool, reason: str | None, now: datetime,
                stall_seconds: int, heartbeats: dict, backlog: BacklogSnapshot | None = None,
                backlog_available: bool = False) -> dict[str, Any]:
    """Inbound processing state, from durable rows only (never from a guess).

    With the backlog breakdown (normal case) the status says what the
    unfinished work is waiting for:

      idle                      nothing unfinished
      backlog_stalled           work is DUE (PENDING, a retry whose time has
                                come, or an abandoned lease) and the oldest due
                                item has waited longer than the threshold --
                                nothing is processing it
      backlog_within_threshold  work is due, but not for longer than the threshold
      processing                nothing due; a worker holds a live lease
      waiting_for_retry         only FUTURE retries are scheduled -- not a stall

    A message held behind an earlier DEAD-LETTERED message of the same stay is
    due but cannot run until that dead letter is redriven: it is counted in
    `ordering_blocked` and keeps the stall visible on purpose.
    """
    empty = {"due_now": None, "scheduled": None, "in_progress": None, "ordering_blocked": None,
             "oldest_due_age_seconds": None}
    if not available:
        return {"status": NOT_AVAILABLE, "reason": reason, "oldest_pending_age_seconds": None,
                "stall_threshold_seconds": stall_seconds, "worker_heartbeat": heartbeats, **empty}
    a = a or ProtocolActivity("")
    pending_n = sum(a.inbound.get(x, 0) for x in PENDING_STATUSES)
    age = _age(now, a.oldest_pending_at)
    base = {"basis": "durable_backlog", "oldest_pending_age_seconds": age,
            "stall_threshold_seconds": stall_seconds, "worker_heartbeat": heartbeats}
    if not backlog_available:
        # Breakdown not computable: the earlier received-age rule, stated as such.
        if pending_n == 0:
            status = "idle"
        elif age is not None and age > stall_seconds:
            status = "backlog_stalled"
        else:
            status = "backlog_within_threshold"
        return {"status": status, **base, **empty, "classification": "received_age"}
    b = backlog or BacklogSnapshot("")
    overdue = _age(now, b.oldest_due_at)
    if b.unfinished == 0:
        status = "idle"
    elif b.due_now and overdue is not None and overdue > stall_seconds:
        status = "backlog_stalled"
    elif b.due_now:
        status = "backlog_within_threshold"
    elif b.in_progress:
        status = "processing"
    else:
        status = "waiting_for_retry"
    return {"status": status, **base, "classification": "due_work",
            "due_now": b.due_now, "scheduled": b.scheduled, "in_progress": b.in_progress,
            "ordering_blocked": b.ordering_blocked, "oldest_due_age_seconds": overdue}


def outbound_sender(protocol: str, rt) -> tuple[bool, str | None]:
    """Whether the service would register an outbound sender for `protocol`,
    computed from the same settings and adapter state it uses (service.py
    build_outbound_senders). The relay itself runs in another process and is
    not observable from here."""
    statuses = {str(st.protocol): st for st in rt.gateway.adapters.statuses()}
    st = statuses.get(protocol)
    blocked = st is None or st.readiness is AdapterReadiness.BLOCKED
    if protocol == str(Protocol.HTNG):
        if not rt.settings.HTNG_OUTBOUND_ENDPOINT_URL:
            return False, "No outbound vendor endpoint is configured (HF-24)."
        if blocked:
            return False, "The HTNG adapter is blocked: no approved profile (HF-07, HF-08)."
        return True, None
    return False, "FIAS outbound needs a running FIAS link and approved link rules (HF-06, HF-11)."


def _outbound_processing(protocol: str, rt, backlog: BacklogSnapshot | None, available: bool,
                         backlog_available: bool, reason: str | None, now: datetime,
                         stall_seconds: int, heartbeats: dict) -> dict[str, Any]:
    configured, sender_reason = outbound_sender(protocol, rt)
    common = {"sender_configured": configured, "sender_reason": sender_reason,
              "relay_heartbeat_observed": bool(heartbeats["last"].get("outbox_relay")),
              "stall_threshold_seconds": stall_seconds}
    if not available or not backlog_available:
        return {"status": NOT_AVAILABLE, "reason": reason, "unfinished": None, "due_now": None,
                "scheduled": None, "oldest_due_age_seconds": None, **common}
    b = backlog or BacklogSnapshot("")
    overdue = _age(now, b.outbound_oldest_due_at)
    if b.outbound_unfinished == 0:
        status = "idle"
    elif not configured:
        # Queued on purpose: nothing may deliver it yet. Not a stall.
        status = "queued_no_sender"
    elif b.outbound_due_now and overdue is not None and overdue > stall_seconds:
        status = "backlog_stalled"
    elif b.outbound_due_now:
        status = "backlog_within_threshold"
    else:
        status = "waiting_for_retry"
    return {"status": status, "basis": "durable_backlog", "unfinished": b.outbound_unfinished,
            "due_now": b.outbound_due_now, "scheduled": b.outbound_scheduled,
            "oldest_due_age_seconds": overdue, **common}


def _adapters(rt, protocol: str) -> list[dict]:
    return [
        {
            "direction": d,
            "readiness": str(st.readiness),
            "specification": st.specification,
            "blocking_decisions": list(st.blocking_decisions),
        }
        for st in rt.gateway.adapters.statuses()
        if str(st.protocol) == protocol
        for d in _directions(st)
    ]


def _directions(st) -> list[str]:
    dirs = []
    if st.inbound_message_types:
        dirs.append(str(Direction.INBOUND))
    if st.outbound_message_types:
        dirs.append(str(Direction.OUTBOUND))
    return dirs or ["unspecified"]


def _vendor_validation(protocol: str, adapters: list[dict], register) -> dict[str, Any]:
    decisions = pending(VENDOR_DECISIONS[protocol], register)
    readiness = sorted({a["readiness"] for a in adapters}) or ["absent"]
    verified = bool(adapters) and all(a["readiness"] == str(AdapterReadiness.READY) for a in adapters)
    return {
        "status": "validated" if verified and not decisions else "pending",
        "adapter_readiness": readiness,
        "pending_decisions": decisions,
        "blocking_decisions": sorted({d for a in adapters for d in a["blocking_decisions"]}),
        "note": "Synthetic certification results never change this status.",
    }


def _certification(protocol: str, certification: dict[str, str] | None) -> dict[str, Any]:
    if not certification or protocol not in certification:
        return {"status": NOT_REPORTED,
                "reason": "The certification harness runs in CI / CLI "
                          "(backend/tests/integrations/certification); results are not published to the API.",
                "scope": "synthetic_messages_only"}
    return {"status": safe_identifier(certification[protocol]), "scope": "synthetic_messages_only"}


def _persistence(rt) -> dict[str, Any]:
    if rt.persistence_probe is None:
        return {"status": "in_memory", "missing_tables": []}
    try:
        tables = rt.persistence_probe()
    except SQLAlchemyError:
        return {"status": "database_unavailable", "missing_tables": None}
    missing = sorted(t for t, ok in tables.items() if not ok)
    return {"status": "ok" if not missing else "tables_missing", "missing_tables": missing}


def _readiness(protocol: str, rt, *, transport, auth, processing, adapters, persistence,
               register, certification) -> dict[str, Any]:
    vendor = _vendor_validation(protocol, adapters, register)
    business_pending = pending(BUSINESS_DECISIONS, register)
    dba_pending = pending(DBA_DECISIONS, register)
    cert = _certification(protocol, certification)
    gate_blocking = rt.live_write_gate.blocking()

    reasons: list[str] = []
    if vendor["status"] != "validated":
        reasons.append("vendor_validation_pending")
    if business_pending:
        reasons.append("business_approval_pending")
    if dba_pending:
        reasons.append("dba_schema_approval_pending")
    if persistence["status"] != "ok":
        reasons.append(f"persistence_{persistence['status']}")
    if cert["status"] != "passed":
        reasons.append("synthetic_certification_not_passed_or_not_reported")
    if not rt.settings.ENABLED:
        reasons.append("integration_disabled")
    if gate_blocking:
        reasons.append("live_domain_writes_gated")
    if transport["status"] in ("disabled",):
        reasons.append("transport_disabled")

    return {
        "transport": {"status": transport["status"]},
        "authentication": {"status": auth["status"]},
        "processing": {"status": processing["status"]},
        "synthetic_certification": cert,
        "vendor_validation": vendor,
        "business_approval": {
            "status": "approved" if not business_pending else "pending",
            "pending_decisions": business_pending,
            "live_domain_writes": {"open": not gate_blocking, "blocking": gate_blocking},
        },
        "dba_schema_approval": {
            "status": "approved" if not dba_pending else "pending",
            "pending_decisions": dba_pending,
            "persistence": persistence["status"],
        },
        "production_readiness": {
            "status": "ready" if not reasons else "not_ready",
            "reasons": reasons,
            "blocked_by": blocked_by(reasons),
        },
    }


#: Readiness reason -> the kind of blocker an operator must act on. Keeps
#: "Not ready" from collapsing distinct causes into one label.
BLOCKER_CATEGORY: dict[str, str] = {
    "vendor_validation_pending": "vendor_specification",
    "business_approval_pending": "business_approval",
    "live_domain_writes_gated": "business_approval",
    "dba_schema_approval_pending": "dba_approval",
    "persistence_in_memory": "dba_approval",
    "persistence_tables_missing": "dba_approval",
    "persistence_database_unavailable": "infrastructure",
    "synthetic_certification_not_passed_or_not_reported": "certification_not_reported",
    "integration_disabled": "switched_off",
    "transport_disabled": "switched_off",
}
_BLOCKER_ORDER = ("vendor_specification", "business_approval", "dba_approval", "infrastructure",
                  "certification_not_reported", "switched_off")


def blocked_by(reasons: list[str]) -> list[str]:
    found = {BLOCKER_CATEGORY.get(r, "other") for r in reasons}
    return [c for c in (*_BLOCKER_ORDER, "other") if c in found]


def build_overview(
    rt,
    *,
    facility_scope: set[uuid.UUID] | None,
    now: datetime,
    stall_seconds: int = DEFAULT_STALL_SECONDS,
    register: dict[str, Decision] | None = None,
    certification: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The shared overview plus one independent entry per protocol.

    `register` defaults to the code approval register (DECISIONS); tests pass
    their own. `certification` maps protocol -> reported synthetic status and
    is None in production (no runtime source exists -- see `_certification`).
    """
    register = DECISIONS if register is None else register

    activity: dict[str, ProtocolActivity] | None
    activity_reason: str | None = None
    try:
        activity = rt.repository.protocol_activity(facility_scope=facility_scope)
    except SQLAlchemyError:
        activity, activity_reason = None, "database_unavailable_or_tables_missing (HF-39)"

    coverage: dict | None = None
    coverage_reason: str | None = None
    if rt.admin is None:
        coverage_reason = "no SQL client store in this runtime"
    else:
        try:
            coverage = rt.admin.auth_coverage(facility_scope=facility_scope)
        except SQLAlchemyError:
            coverage_reason = "database_unavailable_or_tables_missing (HF-39)"

    backlog: dict[str, BacklogSnapshot] = {}
    backlog_available = False
    if activity is not None:
        try:
            backlog = rt.repository.backlog(facility_scope=facility_scope, now=now)
            backlog_available = True
        except (SQLAlchemyError, NotImplementedError):
            backlog_available = False

    persistence = _persistence(rt)
    heartbeats = _heartbeats(rt)
    available = activity is not None
    entries: dict[str, Any] = {}
    for protocol in PROTOCOLS:
        a = activity.get(protocol) if activity else None
        b = backlog.get(protocol)
        adapters = _adapters(rt, protocol)
        transport = _transport(protocol, rt, adapters)
        auth = _authentication(protocol, coverage, coverage_reason)
        processing = _processing(a, available, activity_reason, now, stall_seconds, heartbeats,
                                 backlog=b, backlog_available=backlog_available)
        entries[protocol] = {
            "protocol": protocol,
            "configuration": {"adapters": adapters},
            "transport": transport,
            "authentication": auth,
            "processing": processing,
            "outbound_processing": _outbound_processing(protocol, rt, b, available, backlog_available,
                                                        activity_reason, now, stall_seconds, heartbeats),
            "messages": _messages(a, available, activity_reason),
            "last_error": _last_error(a, available),
            "intake_rejections": _intake_rejections(protocol, rt, transport),
            "readiness": _readiness(protocol, rt, transport=transport, auth=auth, processing=processing,
                                    adapters=adapters, persistence=persistence, register=register,
                                    certification=certification),
        }

    return {
        "generated_at": now.isoformat(),
        "facility_scope": "caller" if facility_scope is not None else "all",
        "overview": _shared(entries, activity, available, activity_reason),
        "protocols": entries,
        "other_protocols": sorted(p for p in (activity or {}) if p not in PROTOCOLS),
    }


def _shared(entries: dict, activity, available: bool, reason: str | None) -> dict[str, Any]:
    statuses = {p: e["readiness"]["production_readiness"]["status"] for p, e in entries.items()}
    ready = [p for p, s in statuses.items() if s == "ready"]
    vendor_pending = any(e["readiness"]["vendor_validation"]["status"] != "validated" for e in entries.values())
    if len(ready) == len(statuses):
        classification = "production_ready"
    elif ready:
        classification = "partially_ready"
    elif vendor_pending:
        classification = "vendor_validation_pending"
    else:
        classification = "not_ready"

    shared: dict[str, Any] = {
        "htng_status": _summary(entries[str(Protocol.HTNG)]),
        "fias_status": _summary(entries[str(Protocol.FIAS)]),
        "readiness_classification": classification,
    }
    if not available:
        return {**shared, "messages": {"status": NOT_AVAILABLE, "reason": reason, "processed": None,
                                       "pending": None, "failed_dead_letter": None,
                                       "outbound_dead_letter": None, "last_successful_exchange_at": None}}
    totals = {"processed": 0, "pending": 0, "failed_dead_letter": 0, "outbound_dead_letter": 0}
    last: datetime | None = None
    for p in PROTOCOLS:
        a = activity.get(p)
        if a is None:
            continue
        totals["processed"] += a.inbound.get("SUCCEEDED", 0)
        totals["pending"] += sum(a.inbound.get(x, 0) for x in PENDING_STATUSES)
        totals["failed_dead_letter"] += a.inbound.get("DEAD_LETTER", 0)
        totals["outbound_dead_letter"] += a.outbound.get("DEAD_LETTER", 0)
        last = _later(_later(last, a.last_succeeded_at), a.last_outbound_sent_at)
    return {**shared, "messages": {"status": "measured", "basis": "retained_rows",
                                   "protocols_counted": list(PROTOCOLS), **totals,
                                   "last_successful_exchange_at": _iso(last)}}


def _summary(entry: dict) -> dict[str, Any]:
    r = entry["readiness"]
    return {
        "transport": entry["transport"]["status"],
        "processing": entry["processing"]["status"],
        "vendor_validation": r["vendor_validation"]["status"],
        "production_readiness": r["production_readiness"]["status"],
    }


# ------------------------------------------------------------------ metrics
INBOUND_STATUS_ORDER = ("SUCCEEDED", "PENDING", "PROCESSING", "RETRY_WAIT", "DEAD_LETTER")
OUTBOUND_STATUS_ORDER = ("SENT", "PENDING", "PROCESSING", "RETRY_WAIT", "DEAD_LETTER")

#: Metrics the dashboard asks for that the current data cannot support, with the
#: reason. They are returned explicitly so the UI never shows them as zero.
_UNAVAILABLE_COMMON = {
    "retry_attempt_timeline": "Individual retry attempts are not timestamped; only the final attempt count is "
                              "stored. Shown instead: messages that needed a retry, by arrival time.",
    "processing_latency": "The time a worker STARTED processing is not stored (each claim overwrites it). "
                          "Latency is therefore measured from intake to completion (end-to-end).",
    "rejected_intake": "Messages rejected at intake (credentials, parsing, validation, facility mapping) are "
                       "never stored; only temporary counters exist, reset whenever the service restarts.",
    "worker_health": "Worker activity is recorded only inside the background service and is not stored, so it "
                     "cannot be shown here (needs a stored heartbeat record, pending HF-39).",
}
_UNAVAILABLE_BY_PROTOCOL = {
    str(Protocol.HTNG): {
        "endpoint_availability_history": "SOAP endpoint availability is not probed or recorded over time; only "
                                         "the configured switch state is known.",
    },
    str(Protocol.FIAS): {
        "connection_history": "FIAS link connect / disconnect events are not persisted, and no FIAS link runs "
                              "(blocked: HF-11 specification, HF-06 link rules).",
        "ack_statistics": "No ACK / NAK is implemented: the FIAS acknowledgement rules are not specified (HF-06).",
        "timeout_statistics": "Link read timeouts are counted only by a running FIAS link, and none runs.",
        "parse_failures": "Records that fail framing or parsing are rejected before storage, and their counters "
                          "are not visible to this dashboard.",
    },
}


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def build_metrics(rt, *, protocol: str, range_key: str, now: datetime, facility_ids: frozenset | None,
                  facility_scope: set[uuid.UUID] | None, tz_offset_minutes: int = 0) -> dict[str, Any]:
    """Windowed metrics for one protocol (GET /observability/metrics).

    * The window is [from, to): `to` is the end of the bucket holding `now`, so the
      last bucket is still filling. Buckets align to the viewer's local clock.
    * KPIs and the status distribution describe the COHORT of messages RECEIVED in
      the window, in their CURRENT status (processed + queued + failed = received).
    * Trend series are EVENT counts per bucket: received (received_on), processed
      and failed (completed_on of SUCCEEDED / DEAD_LETTER rows), outbound created /
      sent. Counts are over RETAINED rows (retention purge, HF-21).
    * Unmeasurable values are null and listed in `unavailable` with a reason.
    """
    from app.integrations.processing.activity import MetricsQuery, metrics_window

    start, end, bucket = metrics_window(range_key, now, tz_offset_minutes)
    query = MetricsQuery(protocol=protocol, start=start, end=end, bucket_seconds=bucket, facility_ids=facility_ids)
    unavailable = {**_UNAVAILABLE_COMMON, **_UNAVAILABLE_BY_PROTOCOL.get(protocol, {})}
    head = {
        "protocol": protocol, "generated_at": now.isoformat(),
        "facility_scope": "caller" if facility_scope is not None else "all",
        "window": {"range": range_key, "from": start.isoformat(), "to": end.isoformat(),
                   "bucket_seconds": bucket, "tz_offset_minutes": tz_offset_minutes},
        "basis": "retained_rows", "retention_days": rt.settings.RETENTION_DAYS,
        "unavailable": [{"metric": k, "reason": v} for k, v in unavailable.items()],
    }
    try:
        raw = rt.repository.metrics(query, facility_scope=facility_scope)
    except (SQLAlchemyError, NotImplementedError):
        return {**head, "status": NOT_AVAILABLE,
                "reason": "database_unavailable_or_tables_missing (HF-39)",
                "kpis": None, "series": [], "status_distribution": None, "latency": None,
                "errors": None, "message_types": None}

    ins, outs = raw["inbound_status"], raw["outbound_status"]
    processed, failed = ins.get("SUCCEEDED", 0), ins.get("DEAD_LETTER", 0)
    queued = sum(ins.get(x, 0) for x in PENDING_STATUSES)
    kpis = {
        "inbound_total": sum(ins.values()),
        "processed": processed,
        "failed": failed,
        "queued": queued,
        "awaiting_retry": ins.get("RETRY_WAIT", 0),
        "success_rate": _ratio(processed, processed + failed),
        "retried_messages": raw["retried_messages"],
        "extra_attempts": raw["extra_attempts"],
        "outbound_total": sum(outs.values()),
        "outbound_sent": outs.get("SENT", 0),
        "outbound_queued": sum(outs.get(x, 0) for x in PENDING_STATUSES),
        "outbound_failed": outs.get("DEAD_LETTER", 0),
    }
    s = raw["series"]
    series = []
    for i in range(query.buckets):
        n_done = s["processed"].get(i, 0)
        series.append({
            "bucket_start": (start + timedelta(seconds=i * bucket)).isoformat(),
            "received": s["received"].get(i, 0),
            "processed": n_done,
            "failed": s["failed"].get(i, 0),
            "retried_received": s["retried"].get(i, 0),
            "outbound_created": s["outbound_created"].get(i, 0),
            "outbound_sent": s["outbound_sent"].get(i, 0),
            "avg_latency_seconds": round(s["latency_sum"][i] / n_done, 3) if n_done and i in s["latency_sum"] else None,
        })

    def dist(counts, order):
        total = sum(counts.values())
        keys = [k for k in order if k in counts] + sorted(k for k in counts if k not in order)
        return [{"status": k if _STATUS_VALUE.fullmatch(str(k)) else "redacted", "count": counts[k],
                 "share": _ratio(counts[k], total)} for k in keys]

    lat = raw["latency"]
    return {
        **head, "status": "measured",
        "kpis": kpis,
        "series": series,
        "status_distribution": {"inbound": dist(ins, INBOUND_STATUS_ORDER),
                                "outbound": dist(outs, OUTBOUND_STATUS_ORDER)},
        "latency": {"basis": "received_to_completed", "scope": "SUCCEEDED messages completed in the window",
                    "count": lat["count"],
                    **{k: (round(lat[k], 3) if lat[k] is not None else None) for k in ("avg", "p50", "p95", "max")}},
        "errors": [{"category": safe_identifier(c), "code": safe_identifier(k), "count": n} for c, k, n in raw["errors"]],
        "message_types": [{"message_type": safe_identifier(t), "count": n} for t, n in raw["message_types"]],
    }


def scope_check(requested: Iterable[uuid.UUID] | None, scope: set[uuid.UUID]) -> list[uuid.UUID]:
    """Requested facility ids that are outside the caller's scope."""
    return sorted((f for f in (requested or []) if f not in scope), key=str)


__all__: list[str] = [
    "BLOCKER_CATEGORY", "BUSINESS_DECISIONS", "DBA_DECISIONS", "VENDOR_DECISIONS", "PROTOCOLS", "blocked_by",
    "build_metrics", "build_overview", "dlq_item", "message_item", "outbound_sender", "safe_identifier", "sanitized_error",
    "scope_check",
]
