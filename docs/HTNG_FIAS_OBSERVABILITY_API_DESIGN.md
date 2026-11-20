# HTNG / FIAS — Observability API Design

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. These endpoints describe the
integration; they do not certify it. Nothing here is vendor evidence.

Code: `backend/app/integrations/observability.py` (information model),
`backend/app/integrations/processing/activity.py` (durable queries),
`backend/app/integrations/api/router.py` (endpoints). Tests:
`backend/tests/integrations/test_observability.py`.

## 1. Architecture discovered (Phase 1 inventory)

### 1.1 Existing observability capabilities

| Capability | Where | Scope / limit |
|---|---|---|
| In-process counters, gauges, heartbeats | `metrics.py` (`IntegrationMetrics`) | **One process only**, reset on restart |
| Worker heartbeats `inbound_worker`, `outbox_relay`, `integration_service` | `processing/worker.py`, `service.py` | Written in the **integration service process**; the API process does not see them |
| Facility health (status counts, oldest pending, latency p50/p95/max, per-client last received/succeeded) | `processing/health.py` | Durable, per facility, **not per protocol** |
| Transport health dict (state, connections, frames, framing errors, last error code) | `transport/tcp.py` `TransportHealth` | Per link object, in the process that runs the link |
| Adapter readiness (`ready` / `test_only` / `blocked`) + blocking decisions | `adapters/base.py` | Static per process |
| Approval register + live-write gate | `domain/approvals.py` | Code register; nothing approved |
| Audit trail | `integration_audit_events` | Durable |

### 1.2 Existing APIs (unchanged by this sprint)

`/integrations/health`, `/readiness`, `/adapters`, `/messages` (status + limit only),
`/messages/{id}` (masked body), `/messages/{id}/redrive`, `/dlq` (limit only), `/outbox`,
`/metrics`, `/facilities/health`, `/audit`, `/mappings`, `/mappings/{id}`, `/htng/inbound`.

### 1.3 Persistence used (no schema change)

`integration_inbound_messages` (protocol, direction, status, attempt_count, max_attempts,
next_attempt_at, last_error_code, last_error_category, received_on, completed_on, correlation_id,
facility_id; indexes `(facility_id, status, received_on)`, `correlation_id`, `next_attempt_at`),
`integration_outbox_messages` (protocol, status, sent_on, facility_id; index
`(facility_id, status, created_on)`), `integration_clients` (enabled, protocols),
`integration_facility_mappings` (enabled, facility_id). The tables are still a **candidate schema
(HF-39)**; they exist only in disposable test databases.

### 1.4 What was missing for a dashboard

* Per-**protocol** counts, last success, last error, retries (existing views were per facility or global).
* A paginated, date/protocol/facility-filtered message search (existing `/messages` has only
  status + limit).
* DLQ fields: failure category, last attempt time, redrive eligibility.
* Authentication readiness per protocol.
* A readiness model that keeps transport, processing, certification, vendor, business, DBA and
  production readiness separate.
* An explicit "unknown" representation: existing endpoints returned `null` heartbeats with no
  explanation of *why*.

### 1.5 RBAC and facility isolation (existing, reused)

HMS JWT + `require_permission("facility_management", "read")` (no integration module exists in
`role_module`; adding one is a seed/schema change under HF-39). Every query is restricted to
`AuthenticatedUser.facility_ids`. Redrive needs the `write` grant. The new endpoints use exactly
the same `Reader` dependency and scope helper as the existing operator endpoints.

## 2. API contracts

All under `/api/v1/integrations/observability`, `GET` only (other methods → 405). 401 without a
token, 403 without `facility_management:read`.

### 2.1 `GET /overview`

Query: `stall_threshold_seconds` (60–86400, default 900).

```text
{
  generated_at, facility_scope: "caller",
  overview: {
    htng_status / fias_status: {transport, processing, vendor_validation, production_readiness},
    readiness_classification: production_ready | partially_ready | vendor_validation_pending | not_ready,
    messages: {status: measured|not_available, basis: "retained_rows", protocols_counted,
               processed, pending, failed_dead_letter, outbound_dead_letter, last_successful_exchange_at}
  },
  protocols: {
    htng | fias: {
      protocol, configuration: {adapters: [{direction, readiness, specification, blocking_decisions}]},
      transport, authentication, processing, messages, last_error, intake_rejections, readiness
    }
  },
  other_protocols: [...]      # protocols present in data but not HTNG/FIAS (never summed in)
}
```

Per-protocol blocks:

| Block | Values | Source |
|---|---|---|
| `transport` (HTNG) | `disabled` / `enabled_adapter_blocked` / `enabled`; `outbound_vendor_endpoint: not_configured` | settings + adapter readiness |
| `transport` (FIAS) | `not_observable` (no link in this process) or `connected` / `degraded` / `connecting` / `disconnected`, `links[]`, `active_connections` | `runtime.transports` **only when tagged** in `runtime.transport_protocols` |
| `authentication` | `configured` / `not_configured` / `not_available`; `enabled_clients`, `enabled_mappings` (caller's facilities only) | `IntegrationAdmin.auth_coverage` (SQL aggregate) |
| `processing` | `idle` / `backlog_within_threshold` / `backlog_stalled` / `not_available`; `oldest_pending_age_seconds`; `worker_heartbeat {scope: this_api_process, observed, last}` | durable backlog + in-process heartbeats |
| `messages` | inbound `{total, by_status, pending, succeeded, retry_wait, failed_dead_letter}`, outbound `{total, by_status, pending, sent, retry_wait, failed_dead_letter}`, `retried_messages`, `extra_attempts`, `last_received_at`, `last_succeeded_at`, `last_outbound_sent_at` | durable, `basis: retained_rows` |
| `last_error` | `{message_id, status, error: {code, category}, received_at, dead_lettered_at}` or `null` | most recently received message currently in RETRY_WAIT / DEAD_LETTER |
| `intake_rejections` | HTNG: `{scope: this_api_process_since_start, rejected_by_category, auth_failures_by_reason}`; FIAS: `not_observable` unless a FIAS link runs in this process | in-process counters |

Example (synthetic test environment, captured this sprint, abridged):

```json
"fias": {
  "transport": {"kind": "tcp link", "status": "not_observable",
                "reason": "No FIAS link is registered in this API process; ...",
                "links": null, "active_connections": null},
  "authentication": {"status": "not_available", "reason": "no SQL client store in this runtime",
                     "enabled_clients": null, "enabled_mappings": null},
  "processing": {"status": "backlog_stalled", "basis": "durable_backlog",
                 "oldest_pending_age_seconds": 827883.952, "stall_threshold_seconds": 900,
                 "worker_heartbeat": {"scope": "this_api_process", "observed": false, "last": {...}}},
  "messages": {"status": "measured", "basis": "retained_rows",
               "inbound": {"total": 3, "by_status": {"PENDING": 1, "RETRY_WAIT": 1, "SUCCEEDED": 1},
                           "pending": 2, "succeeded": 1, "retry_wait": 1, "failed_dead_letter": 0}, ...},
  "last_error": {"status": "RETRY_WAIT", "error": {"code": "hms_unavailable", "category": "transient"}, ...},
  "intake_rejections": {"status": "not_observable", "rejected_by_category": null, ...},
  "readiness": {
    "synthetic_certification": {"status": "not_reported", "scope": "synthetic_messages_only", ...},
    "vendor_validation": {"status": "pending", "adapter_readiness": ["test_only"],
                          "pending_decisions": ["HF-05", "HF-06", "HF-11"], "blocking_decisions": ["HF-11"]},
    "business_approval": {"status": "pending", "pending_decisions": ["HF-01","HF-02","HF-18","HF-19","HF-21"], ...},
    "dba_schema_approval": {"status": "pending", "pending_decisions": ["HF-39"], "persistence": "in_memory"},
    "production_readiness": {"status": "not_ready", "reasons": ["vendor_validation_pending", ...]}
  }
}
```

### 2.2 `GET /messages`

Query: `protocol` (repeatable; `htng`, `fias`), `status` (repeatable; PENDING, PROCESSING,
SUCCEEDED, RETRY_WAIT, DEAD_LETTER), `facility_id` (repeatable UUID, ≤ 50), `received_from`,
`received_to` (ISO 8601 **with offset**; default last 7 days; window ≤ 31 days), `page` (≥ 1),
`page_size` (1–100, default 20; offset ≤ 10 000).

Response: the HMS `Page` envelope (`app/schemas/common.py`) plus the applied window:

```json
{"items": [{"message_id": "d6715183-…", "protocol": "fias", "facility_id": "aaaaaaaa-…",
            "direction": "inbound", "message_type": "test.guest_arrival", "status": "RETRY_WAIT",
            "received_at": "2026-11-10T08:04:00+00:00", "completed_at": null,
            "attempt_count": 1, "retry_count": 0, "max_attempts": 10,
            "next_attempt_at": "2027-11-10T08:04:01+00:00", "correlation_id": "corr-f2",
            "error": {"code": "hms_unavailable", "category": "transient"}}],
 "page": 1, "page_size": 2, "total": 3,
 "window": {"received_from": "2026-11-10T07:00:00+00:00", "received_to": "2026-11-10T09:00:00+00:00"}}
```

Ordering `received_at DESC, message_id DESC` (total, deterministic). Errors: 403 when a requested
`facility_id` is outside the caller's scope; 422 for unknown enum values, naive datetimes, a window
over 31 days, `page_size > 100`, or an offset over 10 000.

`completed_at` is when the message reached SUCCEEDED or DEAD_LETTER. `retry_count` =
`max(attempt_count − 1, 0)`; it resets on redrive (the repository resets `attempt_count`).

### 2.3 `GET /dlq`

Same filters except `status` (fixed to DEAD_LETTER) and **no default date window**: dead letters
stay until redriven, the status predicate uses the `(facility_id, status, received_on)` index and
the page is limited.

```json
{"items": [{"message_id": "235c5eb4-…", "protocol": "htng", "facility_id": "aaaaaaaa-…",
            "direction": "inbound", "message_type": "test.guest_arrival", "status": "DEAD_LETTER",
            "failure_category": "permanent", "failure_code": "hms_business_rule",
            "attempt_count": 1, "retry_count": 0, "received_at": "2026-11-10T08:02:00+00:00",
            "last_attempt_at": "2026-11-10T08:02:01+00:00", "correlation_id": "corr-h3",
            "redrive": {"state_eligible": true, "caller_has_permission": false, "eligible": false}}],
 "page": 1, "page_size": 5, "total": 1, "window": {...}}
```

`redrive` reports exactly the two checks the existing redrive endpoint performs (status
DEAD_LETTER in scope; `facility_management:write`). It does not predict whether processing will
succeed after a redrive. **No redrive action was added.** The existing audited
`POST /messages/{id}/redrive` is unchanged.

## 3. Data sources, metrics and limitations

| Metric | Source | Limitation |
|---|---|---|
| Inbound / outbound counts by status | durable tables | Retained rows only: with `INTEGRATION_RETENTION_DAYS` set (HF-21), purged SUCCEEDED/SENT rows disappear. **Not lifetime totals.** |
| Pending | PENDING + PROCESSING + RETRY_WAIT | — |
| Failed | DEAD_LETTER (terminal) | RETRY_WAIT shown separately |
| Retries | `retried_messages`, `extra_attempts` | Reset by redrive; retained rows only |
| Last success / last outbound sent | `max(completed_on)` of SUCCEEDED, `max(sent_on)` of SENT | — |
| Last error | latest-received RETRY_WAIT / DEAD_LETTER row | The repository stores no error time for RETRY_WAIT and no free-text message |
| Intake rejections, auth failures | in-process counters | Only this API process since start; rejected intake is never persisted |
| Worker health | heartbeats | Workers run in the service process; in production the API shows `observed: false`. **That means "not visible", not "down"** |
| FIAS link | transport probes | Not visible from the API process unless a link is registered there and tagged |
| Latency | `/facilities/health` (existing) | Not duplicated in the overview |

## 4. Readiness definitions

| Dimension | `approved` / `validated` / `ready` only when |
|---|---|
| Transport | HTNG: integration + inbound switches on and no inbound adapter BLOCKED. FIAS: a tagged link reports `connected` |
| Authentication | ≥ 1 enabled client for the protocol **and** ≥ 1 enabled mapping in the caller's facilities |
| Processing | no backlog older than the stall threshold |
| Synthetic certification | a result is reported. **There is no runtime source today**, so it is always `not_reported` |
| Vendor validation | every adapter for the protocol is `ready` (verified specification) **and** HTNG: HF-07, HF-08 / FIAS: HF-05, HF-06, HF-11 are APPROVED **with evidence**. A synthetic PASS never changes this |
| Business approval | HF-01, HF-02, HF-18, HF-19, HF-21 APPROVED with evidence |
| DBA / schema | HF-39 APPROVED with evidence; persistence probe `ok` |
| Production readiness | all of: vendor validated, business approved, DBA approved, persistence ok, synthetic certification `passed`, integration enabled, live-write gate open |

A decision absent from the code register counts as pending. HF-08 is not in the code register,
so HTNG vendor validation cannot pass until it is added by a reviewed change. With the current
register **no protocol can be production-ready**. Shared classification:
`production_ready` (all), `partially_ready` (some), `vendor_validation_pending` (none ready and a
vendor validation pending), otherwise `not_ready`.

## 5. Security

* Same JWT, RBAC grant and facility scope as existing operator endpoints. Requested facilities
  outside scope → 403. Out-of-scope rows are never counted.
* Never returned: payloads, payload hashes, idempotency / ordering keys, external message ids
  (they can carry reservation or room numbers), client ids and codes, secrets, lease owners
  (host names), peer addresses.
* Error codes, categories and link error codes pass only if they match `[a-z][a-z0-9_.:-]{0,63}`;
  otherwise `"redacted"`.
* Bounded: grouped aggregates over indexed columns; the search has a date window, page size and
  offset ceilings; authentication coverage is a single `GROUP BY` aggregate.

## 6. Frontend integration recommendations

* The frontend has no integration pages yet. A future page fits the existing pattern: a route
  gated through `core/rbac/modules.moduleForPath` → `facility_management`, and API calls typed
  with the existing `Page<T>` in `lib/api/endpoints.ts`.
* Render `not_available` / `not_observable` / `not_reported` as "unknown" (grey), **never as 0 or
  green**. Show `basis: retained_rows` next to totals.
* Keep "Synthetic tests" and "Vendor certification" as separate tiles. Show `pending_decisions`
  IDs verbatim.
* Poll `/overview` no faster than every 30 s. Use `/messages` and `/dlq` for drill-down. Link the
  DLQ redrive button only when `redrive.eligible` and keep using the existing audited endpoint.

## 7. Telemetry not available (and what would provide it)

| Missing | Needed |
|---|---|
| Worker health in the API | Heartbeats persisted by the service (table or shared cache): a schema change (HF-39) or infra decision (HF-25/26) |
| FIAS link state in the API | The link owner process publishing state, or the link running in-process: HF-06, HF-25/26 |
| Lifetime / per-period totals | Counters persisted before purge (HF-21 retention defines the need) |
| Rejected-intake totals across processes | A persisted rejection log or shared metrics backend (no Prometheus client approved) |
| Synthetic certification in the API | An approved publication path for CI reports |
| Error time for RETRY_WAIT | An `updated_on`-based or dedicated column in the views (the column exists; not exposed by the repository model today) |
