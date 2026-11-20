HTNG &amp; FIAS Integration DashboardCode-Level Functional, Data Lineage and Backend ExplanationFOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDINGRepository: ACX_PLATFORM\ACX-Platform · Branch: feature/htng-fias-on-develop · HEAD 46904fdPrepared: 20 November 2026 · Audience: project owner, technical team, NDTM / managementMethod: read-only inspection of the source code, tests and verification reports in the repositoryEvery figure in the dashboard is traced to its source file, function, table and query. Anything that could not be confirmed from source is marked NOT VERIFIED. Synthetic and demo data are never presented as live vendor traffic.

# How to Read This Document

This document answers one question for every value on the HTNG / FIAS Integrations dashboard:
**where did this value come from, how was it calculated, how does it reach the screen, and what
does it actually mean?**

It was written by reading the code in this repository. Nothing was changed, no migration was
run, and the real HMS database was not contacted. Values quoted as "current" come from one of
three clearly named environments, and never from a vendor:

| Environment | What it is | Where its numbers come from |
|---|---|---|
| **Unit / API test fixture** | `frontend/src/features/integrations/__tests__/observability-fixtures.json`, produced by the backend observability code in its synthetic test environment | synthetic rows created by tests |
| **Isolated demo stack** | Docker containers `acx-demo-web`, `acx-demo-api`, `acx-demo-mysql` on an internal-only network, seeded by a scratchpad script through the real `SqlIntegrationRepository` (42 synthetic inbound messages, 3 outbox rows, 2 facilities) | read on 20 Nov 2026 05:37 UTC through the real API as the synthetic user `e2e.operator` |
| **Real development database** | the HMS database used by the dev backend | **not contacted.** The integration tables do not exist there (HF-39, `sql_models.py` docstring), so the dashboard would show "Unavailable" for every count. This is derived from code, NOT VERIFIED by observation |

Conventions used throughout:

- File paths are relative to the repository root (`ACX-Platform/`).
- `backend/app/integrations/...` is abbreviated to `integrations/...` where it is unambiguous.
- **NOT VERIFIED** marks a statement that could not be confirmed from source code or evidence.
- **PROPOSED** marks a design that is not implemented.
- Line numbers are deliberately not quoted; functions and classes are named instead, because
  line numbers change with every edit.
- Internal names (tables, columns, functions) are documented here because this is a
  code-level document. They are **never shown in the end-user dashboard**: the dashboard
  translates them into business wording (`lib/presentation.ts`).

## Table of Contents

- Chapter 1 – Project and Integration Overview
- Chapter 2 – Complete Dashboard Navigation
- Chapter 3 – Integrations Overview: Complete KPI Explanation
- Chapter 4 – Timestamp and Timezone Explanation
- Chapter 5 – HTNG Monitoring Page
- Chapter 6 – FIAS Monitoring Page
- Chapter 7 – Message Logs Page
- Chapter 8 – Failed Messages and DLQ
- Chapter 9 – Complete Backend Code-Level Architecture
- Chapter 10 – Database Tables and Data Lineage
- Chapter 11 – Frontend Implementation
- Chapter 12 – API-by-API Explanation
- Chapter 13 – Testing and Evidence
- Chapter 14 – Current Issues and Inconsistencies
- Chapter 15 – Pending Vendor and Production Readiness
- Chapter 16 – Complete End-to-End Workflow
- Chapter 17 – How to Explain This to Management
- Appendix A – Unverified Items and Evidence Gaps
- Appendix B – Source Index

# Chapter 1 – Project and Integration Overview

## 1.1 What HMS is

HMS is the hotel management system in this repository: a FastAPI backend (`backend/app`) on
MySQL and a React / TypeScript frontend (`frontend/src`) branded "Inspironics Ikanos". It holds
facilities (hotels), rooms, stays, check-in / check-out, room conditions and related operations.
Users sign in with a JWT (`POST /api/v1/auth/login`) and every screen is guarded by
module-level role permissions (`require_permission` in `backend/app/api/deps.py`, mirrored in
`frontend/src/core/rbac/modules.ts`).

## 1.2 Why external hotel-system integration is required

Hotels already run a Property Management System (PMS) from a vendor. Reservations, check-ins,
check-outs and room moves start there. If HMS is to react to those events (room readiness,
device actions, housekeeping) without staff re-typing them, HMS must receive the PMS's
messages, map the PMS's property codes to HMS facilities, and apply them through HMS's own
business rules. The integration layer under `backend/app/integrations/` was built for that.

## 1.3 What HTNG and FIAS are

| | HTNG | FIAS |
|---|---|---|
| Full name | Hospitality Technology Next Generation messaging | Fidelio Interface Application Specification |
| Wire format | XML documents inside a SOAP 1.1 or 1.2 envelope | delimited text records |
| Transport | HTTP request / response (web service) | long-lived TCP socket (one link per property) |
| Who connects | the PMS calls an HTTP endpoint | either side may listen — **not decided (HF-06)** |
| Message identity | vendor schema / profile (WSDL, XSD) | vendor record set (record ids and field ids) |
| What we have from the vendor | **nothing** (HF-07 schema, HF-08 security) | **nothing** (HF-11 specification, HF-06 link rules) |

## 1.4 Why both protocols are supported

The target PMS vendor and product are not yet named (decision **HF-03**) and the protocol per
deployment is not yet chosen (**HF-04**: FIAS, HTNG, a vendor REST API or a combination). The
code therefore implements a shared pipeline with two pluggable protocol adapters
(`integrations/adapters/base.py` `BaseProtocolAdapter`), so either answer can be served without
rebuilding authentication, facility mapping, persistence, retry or monitoring.

## 1.5 HTNG SOAP/XML versus FIAS TCP in this code

- **HTNG** arrives at `POST /api/v1/integrations/htng/inbound` (`api/router.py` `htng_inbound`).
  The SOAP version is taken from the HTTP media type (`text/xml` = 1.1,
  `application/soap+xml` = 1.2, `soap_version_from_content_type`). XML is parsed by
  `transport/xml_security.py`, which rejects every DOCTYPE and entity declaration. Faults are
  answered in the request's SOAP version (`soap_fault`).
- **FIAS** would arrive over a TCP stream: `transport/tcp.py` (`TcpLink`, client side) or
  `transport/tcp_server.py` (`TcpListenerLink`, server side with a mandatory IP allow-list),
  `transport/framing.py` (`DelimitedFramer`, no default markers) and `adapters/fias/codec.py`
  (a parser driven entirely by a `FiasSpecification` data object).

## 1.6 Overall architecture

> **Figure: Overall architecture (verified components; dashed = not wired / blocked)** (diagram rendered in the PDF)

Both protocols converge on `ExchangeGateway.receive()` (`exchange/gateway.py`): authenticate
the client, decode through the protocol adapter, resolve the facility, validate, and store the
message durably as `PENDING`. A separate long-running process (`integrations/service.py`)
claims stored messages and dispatches them to a domain handler. The dashboard reads the same
tables through a read-only observability API.

## 1.7 What is implemented, and what still needs the vendor

These are different engineering states and the document keeps them apart:

| Capability | Implemented in code | Exercised by synthetic tests | Wired into a running process | Verified with a vendor |
|---|---|---|---|---|
| Shared intake pipeline (auth, facility, idempotency, persistence) | Yes | Yes | Yes (API process, but switched off) | No |
| HTNG SOAP endpoint, SOAP 1.1 / 1.2, safe XML | Yes | Yes | Yes, behind `INTEGRATION_ENABLED` + `INTEGRATION_HTNG_INBOUND_ENABLED` (both default **false**) | No |
| HTNG schema profile (operations, namespaces) | Registry only; production registry **empty** | Yes (generic test profile, `allow_unverified=True`) | Adapter reports **BLOCKED** | No (HF-07, HF-08) |
| FIAS record parser / serializer | Yes (specification-driven) | Yes (provisional test specification) | Adapter reports **BLOCKED** (`PRODUCTION_SPECIFICATION is None`) | No (HF-11) |
| FIAS TCP client / server, framing, reconnect | Yes | Yes (`test_transport_tcp.py`, `test_transport_server.py`, simulator) | **No** — no link is created by `app/main.py`, `runtime.py` or `service.py` | No (HF-06) |
| FIAS ACK, heartbeat, handshake | **Not implemented** on purpose ("nothing here sends anything on its own", `tcp.py`) | — | — | No (HF-06) |
| Durable processing (claim, lease, retry, DLQ, redrive, ordering) | Yes | Yes (MySQL 8.4 disposable DB) | Inbound worker in `service.py` (requires `INTEGRATION_ENABLED=true`) | — |
| Outbound relay (send to vendor) | Yes (`OutboxRelay`) | Yes | **No** — `service.main()` passes `relay=None`; no sender exists | No (HF-24) |
| HMS check-in / check-out writes | Yes (`domain/stays.py`) | Yes | Gated: `LiveWriteGate` closed; no production stay resolver | — |
| Integration tables in the HMS database | Candidate DDL only | Yes (disposable MySQL) | **No** (HF-39) | — |
| Observability API and dashboard | Yes | Yes (API, browser, full-stack E2E) | Yes | — |

# Chapter 2 – Complete Dashboard Navigation

## 2.1 Routes, navigation and access

> **Figure: Dashboard navigation, routes and the API each page calls** (diagram rendered in the PDF)

| Page | Route (`frontend/src/App.tsx`) | Component | Sidebar label (`AppSidebar.tsx`) |
|---|---|---|---|
| Integrations Overview | `/integrations` | `features/integrations/pages/IntegrationOverview.tsx` → `views/OverviewView.tsx` | Overview |
| HTNG Monitoring | `/integrations/htng` | `pages/ProtocolMonitoring.tsx` `HtngMonitoring` → `views/ProtocolView.tsx` | HTNG Monitoring |
| FIAS Monitoring | `/integrations/fias` | `pages/ProtocolMonitoring.tsx` `FiasMonitoring` → `views/ProtocolView.tsx` | FIAS Monitoring |
| Message Logs | `/integrations/messages` | `pages/MessageLogs.tsx` | Message Logs |
| Failed Messages / DLQ | `/integrations/dlq` | `pages/DeadLetters.tsx` | Failed Messages / DLQ |

**Permissions.** There is no integration module in the HMS `role_module` table yet (adding one
is a seed / schema change under HF-39), so the existing `facility_management` grant is reused:

- Frontend: `core/rbac/modules.ts` maps the prefix `/integrations` to `facility_management`;
  the shared `ModuleGuard` renders "Access denied" and issues **no** integration request
  without `read`. The sidebar hides the whole group (verified by the test "sidebar hides the
  group without facility_management read").
- Backend: every observability endpoint depends on
  `require_permission("facility_management", "read")` (`api/router.py`, `Reader`). Redrive and
  mapping changes need `write`.
- **Facility scope.** Every query is restricted to the signed-in user's `facility_ids` (from
  `app/services/auth.py` `AuthenticatedUser`). Records outside the scope are invisible; an
  explicit filter for an out-of-scope facility answers 403.

## 2.2 Page-by-page summary

| Page | Business purpose | Typical user | APIs called (hook) | Backend function |
|---|---|---|---|---|
| Overview | One-screen health of both protocols, message volumes, latest activity | operations lead, project owner | `useIntegrationOverview` → `GET /observability/overview`; `useIntegrationMessages({page 1, size 5})`; `useIntegrationDeadLetters({page 1, size 5})` | `build_overview()`; `search_messages()` |
| HTNG / FIAS Monitoring | Everything about one protocol: connection, authentication, processing, statistics, recent and failed messages, vendor status, readiness | integration engineer, support | the overview query (shared cache) + `messages {protocol, size 10}` + `dlq {protocol, size 5}` | same |
| Message Logs | Search inbound messages with server-side filters and paging | support, operations | `useIntegrationMessages(toQueryParams(filters))` | `observability_messages` → `search_sql()` |
| Failed Messages / DLQ | Investigate dead-lettered messages, read-only | support, operations | `useIntegrationDeadLetters(...)` + the overview query for the summary tiles | `observability_dlq` → `search_sql()` |

## 2.3 Loading, empty and error states (all pages)

| State | Implementation | What the user sees |
|---|---|---|
| Loading overview | `InlineLoading` in the page | "Loading integration status..." / "Loading HTNG status..." |
| Loading a table | `DataState` + `TableLoading` skeleton | skeleton rows |
| Empty result | `DataState isEmpty` | e.g. "No messages match these filters", "No failed messages", "No HTNG messages in the last 7 days" |
| Unmeasured figure (backend returned `null`) | `KpiTile` / `CountValue` → `formatMetric` | "Unavailable" or "Not currently observable" plus a one-line reason; **never 0** |
| 401 | API client dispatches `hms:unauthorized` → sign-out | login page |
| 403 | `QueryErrorState` → shared `ErrorState` | "Access denied", no Retry button |
| 5xx / network | `QueryErrorState` | error message with a **Retry** button |
| Partial failure | each query renders its own error | e.g. HTNG page shows statistics while the recent-messages panel shows the error |
| Invalid date range | `validateDateRange` | inline alert; **no request is sent** |

# Chapter 3 – Integrations Overview: Complete KPI Explanation

## 3.1 One request feeds the whole page (except the two activity lists)

Everything in the "Integration status" panel, the six KPI tiles and the two protocol health
panels comes from **one** response:

```text
Frontend  pages/IntegrationOverview.tsx  → useIntegrationOverview()  (lib/api/hooks.ts)
          → getIntegrationOverview()  (lib/api/integrations.ts)
          → GET /api/v1/integrations/observability/overview
Backend   api/router.py  observability_overview(rt, user, stall_threshold_seconds=900)
          → observability.py  build_overview(rt, facility_scope=user.facility_ids, now=utcnow())
          → rt.repository.protocol_activity()  → processing/activity.py  activity_from_sql()
          → rt.admin.auth_coverage()           → integrations/admin.py
Database  integration_inbound_messages, integration_outbox_messages,
          integration_clients, integration_facility_mappings
```

The response has this shape (fields abbreviated; real field names):

```json
{ "generated_at": "...+00:00", "facility_scope": "caller",
  "overview": { "htng_status": {"transport","processing","vendor_validation","production_readiness"},
                "fias_status": {...}, "readiness_classification": "vendor_validation_pending",
                "messages": {"status":"measured","basis":"retained_rows","processed","pending",
                             "failed_dead_letter","outbound_dead_letter","last_successful_exchange_at"} },
  "protocols": { "htng": {"transport","authentication","processing","messages","last_error",
                          "intake_rejections","configuration","readiness"}, "fias": {...} },
  "other_protocols": [] }
```

**The null rule.** If the integration tables cannot be read (`SQLAlchemyError`, e.g. tables
missing under HF-39), `build_overview` does not fail: it sets every count to `null` with
`status: "not_available"`. The frontend shows "Unavailable" plus "Message storage is not
available." — never 0 (`lib/presentation.ts` `formatMetric`, `unavailableExplanation`).

## 3.2 Section A – HTNG · production readiness panel

The panel (`OverviewView.tsx`, first `StatusItem`) shows three badges taken from
`overview.htng_status` (built by `_summary()` in `observability.py`).

### A1. Production readiness badge ("Not ready")

| Question | Answer from source |
|---|---|
| Backend field | `overview.htng_status.production_readiness` = `protocols.htng.readiness.production_readiness.status` |
| Calculated by | `_readiness()` in `observability.py` |
| Possible values | `ready` (UI "Ready") or `not_ready` (UI "Not ready") |
| Rule | `ready` only if the `reasons` list is empty. Each of these adds a reason: vendor validation not `validated`; any business decision HF-01/02/18/19/21 not Approved-with-evidence; DBA decision HF-39 not approved; persistence status not `ok`; synthetic certification not `passed`; `INTEGRATION_ENABLED` false; live-write gate blocking; transport `disabled` |
| Why it shows "Not ready" now | In the demo stack the reasons are: `vendor_validation_pending`, `business_approval_pending`, `dba_schema_approval_pending`, `synthetic_certification_not_passed_or_not_reported`, `integration_disabled`, `live_domain_writes_gated`, `transport_disabled` |
| What must change | every reason above must clear — in practice, vendor documents, approvals recorded **in code** (`domain/approvals.py`) with evidence, DBA approval, switches on, and a certification result published (no runtime channel exists for that today) |
| What it represents | a **governance and readiness** verdict, not connectivity |

### A2. Connection badge ("Disabled")

| Question | Answer from source |
|---|---|
| Backend field | `overview.htng_status.transport` = `protocols.htng.transport.status` |
| Calculated by | `_transport("htng", ...)` |
| Values and conditions | `disabled` if NOT (`INTEGRATION_ENABLED` and `INTEGRATION_HTNG_INBOUND_ENABLED` and an HTNG adapter exists); otherwise `enabled_adapter_blocked` if the inbound adapter readiness is `blocked`; otherwise `enabled` |
| Why "Disabled" now | both switches default to `false` (`integrations/config.py`) and the demo / dev environments do not set them |
| What it represents | **configuration switches only.** It does not test a network path. HTNG is an inbound HTTP endpoint; there is no persistent connection to observe. `outbound_vendor_endpoint` is the constant `"not_configured"` (no vendor endpoint exists until HF-07 / HF-24) |
| Note | The unit-test fixture shows "Enabled" because that test runtime switched HTNG on; the label therefore depends on the environment, not on vendor traffic |

### A3. Processing badge ("Backlog stalled")

| Question | Answer from source |
|---|---|
| Backend field | `overview.htng_status.processing` = `protocols.htng.processing.status` |
| Calculated by | `_processing()` in `observability.py` |
| Inputs | `pending_n` = number of **inbound** rows with status in `PENDING_STATUSES` = (`PENDING`, `PROCESSING`, `RETRY_WAIT`); `age` = `now − MIN(received_on)` over those rows (`activity_from_sql`, `func.min(case((M.status.in_(PENDING_STATUSES), M.received_on)))`) |
| Values | `idle` if `pending_n == 0`; `backlog_stalled` if `age > stall_seconds` (default **900 s = 15 min**, `DEFAULT_STALL_SECONDS`, overridable per request with `?stall_threshold_seconds=60..86400`); otherwise `backlog_within_threshold`; `not_available` if the tables cannot be read |
| Why "Backlog stalled" now | the demo stack has unfinished rows (8 for HTNG) and **no worker is running** (the integration service is not started; `INTEGRATION_ENABLED` is false). The oldest is about 17.7 h old (63 819 s at 05:37 UTC), far above 900 s |
| What it represents | **only the age of the oldest unfinished inbound message.** It does not read worker heartbeats or worker progress |

> **Label caution.** "Backlog stalled" can be produced by a message in `RETRY_WAIT` whose next
> attempt is legitimately scheduled in the future, because `RETRY_WAIT` counts as unfinished.
> It also appears whenever no worker runs at all (as in every test and demo environment). The
> label is accurate as "the oldest unfinished message is older than the threshold", and should
> not be read as "a worker has crashed". Worker liveness is a separate field
> (`processing.worker_heartbeat`) that the API process cannot observe (see 3.4).

## 3.3 Section B – FIAS · production readiness panel

Same three badges from `overview.fias_status`. The FIAS-specific differences:

| Badge | Field / function | Current value and reason |
|---|---|---|
| Production readiness | `_readiness("fias")` | **Not ready** (same reasons as HTNG except `transport_disabled`, because the FIAS transport is `not_observable`, not `disabled`) |
| Connection | `_transport("fias")` | **Not observable**. The function looks for transports registered in the API process and tagged `fias` (`rt.transport_protocols`). None exist, so it returns `status: "not_observable"`, `links: null`, `active_connections: null` |
| Processing | `_processing()` | **Backlog stalled** in the demo (5 unfinished FIAS rows, oldest about 28 h) |

**What "Not observable" means, precisely.** No FIAS link object exists in the API process, and
in fact **no FIAS link exists in any process**: `runtime.build_default_runtime()` registers no
transport and `service.main()` starts only the inbound worker. The UI explanation ("Live link
state is not reported to this dashboard...") is deliberately neutral: it must not be read as
"connected" nor as "disconnected". The engineering states are:

| State | FIAS today |
|---|---|
| Parser implemented | Yes (`adapters/fias/codec.py`, spec-driven) |
| TCP transport implemented | Yes (`transport/tcp.py`, `transport/tcp_server.py`) |
| TCP connection established | Only in tests against the local `FiasTestSimulator` |
| Wired into a production process | **No** |
| Vendor connectivity verified | **No** |

**Authentication (FIAS).** A FIAS link is authenticated once, when the link is set up: the
pump's `receive` callable is bound to an `AuthenticatedClient` (see
`tests/integrations/test_end_to_end.py`, `stack.auth(...)`), and `TcpListenerLink` admits only
allow-listed peer IPs. There is no per-record credential. How a production link obtains its
client binding is not wired — **NOT VERIFIED** beyond tests.

## 3.4 Section C – Vendor validation panel

| Question | Answer from source |
|---|---|
| Badge | `overview.readiness_classification` → "Vendor validation pending" |
| Calculated by | `_shared()`: `production_ready` if both protocols are ready; `partially_ready` if one is; else `vendor_validation_pending` if any protocol's vendor validation is not `validated`; else `not_ready` |
| Per protocol | `_vendor_validation()`: `validated` only if every adapter readiness is `ready` **and** every vendor decision is Approved with evidence. HTNG decisions: HF-07, HF-08. FIAS: HF-05, HF-06, HF-11 (`VENDOR_DECISIONS`) |
| Live or static? | **Static, configuration-derived.** It reads the in-code register `domain/approvals.py` `DECISIONS` and the adapters' declared readiness. No network call, no vendor feedback, no test result changes it ("Synthetic certification results never change this status.") |
| Note | HF-08 is not present in the code register; `pending()` treats a missing decision as pending, which is the safe default |
| Evidence expected | WSDL / XSD and profile (HF-07), security specification (HF-08), FIAS manual and record set (HF-11), link rules (HF-06), property-code case rule (HF-05), vendor test environment (HF-09) |

## 3.5 Section D – Message activity: every KPI

The six tiles are rendered by `OverviewView.tsx` with `KpiTile` (`components/KpiTile.tsx`).
Derived values use `sumMeasured()` (`lib/presentation.ts`): **the sum is `null` as soon as any
input is `null`**, so a partially measurable total is shown as "Unavailable", not as a smaller
number.

Source query for all six (from `activity_from_sql`, faithful SQL equivalent):

```sql
-- inbound: one row per (protocol, status), restricted to the caller's facilities
SELECT protocol, status, COUNT(*) FROM integration_inbound_messages
 WHERE facility_id IN (:caller_facility_ids)
 GROUP BY protocol, status;
-- outbound: same over the outbox
SELECT protocol, status, COUNT(*) FROM integration_outbox_messages
 WHERE facility_id IN (:caller_facility_ids)
 GROUP BY protocol, status;
```

There is **no date filter, no direction filter and no join** in these queries. Only the
protocols `htng` and `fias` are summed into the shared figures (`PROTOCOLS`,
`protocols_counted`); any other protocol value is listed in `other_protocols` and excluded.

> **Figure: Overview KPI data lineage: table → query → response field → tile** (diagram rendered in the PDF)

### D1. INBOUND

1. **Business meaning.** How many inbound HTNG + FIAS messages for your facilities are
   currently held in the integration store, in any status.
2. **Data source.** `GET /observability/overview` → `build_overview` → `_messages()` →
   `protocols.<p>.messages.inbound.total`; table `integration_inbound_messages`, columns
   `protocol`, `status`, `facility_id`.
3. **Counting logic.** `inbound.total = Σ COUNT(*)` over all statuses for the protocol. The
   tile adds HTNG and FIAS in the browser:
   `sumMeasured([htng.messages.inbound.total, fias.messages.inbound.total])`.
4. **Example (hypothetical).** HTNG has 12 SUCCEEDED, 3 PENDING, 2 DEAD_LETTER; FIAS has 5
   SUCCEEDED, 1 RETRY_WAIT → Inbound = 17 + 6 = **23**.
5. **Current value.** Demo stack: HTNG 24 + FIAS 18 = **42** (synthetic). Test fixture: 4 + 3 = 7.
6. **Lifecycle.** A row enters at intake (`repository.accept()`, status `PENDING`) and leaves
   only if deleted by the retention purge (SUCCEEDED rows older than
   `INTEGRATION_RETENTION_DAYS`; off by default) — so the number only grows today.
7. **Frontend.** `OverviewView.tsx` → `KpiTile label="Inbound"`, detail "Received from
   vendors"; `null` → "Unavailable".
8. **Refresh.** See 3.8.

### D2. OUTBOUND

1. **Business meaning.** How many messages HMS has queued to send back to vendors, in any
   status.
2. **Data source.** `protocols.<p>.messages.outbound.total`; table
   `integration_outbox_messages` (`protocol`, `status`, `facility_id`).
3. **Counting logic.** `Σ COUNT(*)` of outbox rows over all statuses, HTNG + FIAS
   (`sumMeasured`). Includes `PENDING`, `SENT`, `RETRY_WAIT`, `DEAD_LETTER`.
4. **Example (hypothetical).** 4 PENDING + 2 SENT outbox rows → Outbound = **6**.
5. **Current value.** Demo: 2 + 1 = **3**, all `PENDING`. They were produced by the seed's
   handler completions; they stay `PENDING` because **no outbox relay runs anywhere**
   (`service.main()` passes `relay=None`). The detail text "Queued or sent to vendors" is
   therefore, today, "queued".
6. **Lifecycle.** Created in the same transaction that marks an inbound message SUCCEEDED
   (`completion().add_outbox`), or by `ExchangeGateway.request_outbound()`; would move to
   `SENT` / `RETRY_WAIT` / `DEAD_LETTER` only through `OutboxRelay`.
7. **Frontend.** `KpiTile label="Outbound"`.

### D3. PENDING

1. **Business meaning.** Inbound messages that are not finished yet.
2. **Data source.** `overview.messages.pending` (`_shared()`), table
   `integration_inbound_messages`.
3. **Counting logic.** `Σ over HTNG and FIAS of COUNT(status IN ('PENDING','PROCESSING','RETRY_WAIT'))`.
   **Inbound only**: outbound `PENDING` rows are **not** included.
4. **Example (hypothetical).** 3 PENDING + 1 PROCESSING + 2 RETRY_WAIT → Pending = **6**.
5. **Current value.** Demo: HTNG 8 + FIAS 5 = **13** (of which 5 are RETRY_WAIT and 3
   PROCESSING). Fixture: 3.
6. **Lifecycle.** PENDING → PROCESSING (claim) → SUCCEEDED (leaves Pending) or RETRY_WAIT
   (stays in Pending) or DEAD_LETTER (leaves Pending, enters Failed).
7. **Frontend.** `KpiTile label="Pending"`, detail "Waiting to be processed".
   **Caution:** the detail text undersells the scope — the figure also includes messages being
   processed right now and messages waiting for a retry.

### D4. FAILED

1. **Business meaning.** Inbound messages that have given up: they failed permanently or ran
   out of attempts and now sit in the dead-letter queue.
2. **Data source.** `overview.messages.failed_dead_letter` (`_shared()`).
3. **Counting logic.** `Σ COUNT(status = 'DEAD_LETTER')` over inbound rows, HTNG + FIAS. A
   message that failed once and is waiting to retry is **not** counted here.
4. **Example (hypothetical).** 2 DEAD_LETTER + 4 RETRY_WAIT → Failed = **2**.
5. **Current value.** Demo: 3 + 2 = **5**. Fixture: 1.
6. **Lifecycle.** Enters when `record_failure()` sets `DEAD_LETTER`; leaves only through the
   audited redrive (`POST /integrations/messages/{id}/redrive`), which sets it back to
   `PENDING` with `attempt_count = 0`.
7. **Frontend.** `KpiTile label="Failed"`, detail "Inbound, moved to the DLQ".

### D5. AWAITING RETRY

1. **Business meaning.** Inbound messages that failed with a temporary error and are scheduled
   for another attempt.
2. **Data source.** `protocols.<p>.messages.inbound.retry_wait`.
3. **Counting logic.** `COUNT(status = 'RETRY_WAIT')`, HTNG + FIAS, summed in the browser
   (`sumMeasured([htng.inbound.retry_wait, fias.inbound.retry_wait])`). Inbound only.
4. **Example (hypothetical).** 2 HTNG + 1 FIAS rows in RETRY_WAIT → **3**.
5. **Current value.** Demo: 3 + 2 = **5**. Fixture: 0 + 1 = 1.
6. **Lifecycle.** PROCESSING → RETRY_WAIT (transient error, attempts left;
   `next_attempt_at = now + delay`) → PROCESSING when due (claimed again).
7. **Frontend.** `KpiTile label="Awaiting retry"`, detail "Scheduled for another attempt".

### D6. DLQ

1. **Business meaning.** Everything in the dead-letter queue, both directions.
2. **Data source.** `overview.messages.failed_dead_letter + overview.messages.outbound_dead_letter`.
3. **Counting logic.** inbound `DEAD_LETTER` rows + outbox `DEAD_LETTER` rows (HTNG + FIAS),
   summed in the browser with `sumMeasured`.
4. **Example (hypothetical).** 2 inbound + 1 outbound dead letters → DLQ = **3** while Failed = 2.
5. **Current value.** Demo: 5 + 0 = **5**. Fixture: 1 + 0 = 1.
6. **Lifecycle.** Inbound part as D4. Outbound dead letters would come from `OutboxRelay`,
   which is not running.
7. **Frontend.** `KpiTile label="DLQ"`, detail "Inbound and outbound".

### D7. Protocol health panels and recent activity

| Panel item | Source field | Function |
|---|---|---|
| HTNG / FIAS health – Connection, Authentication, Processing, Vendor validation badges | `protocols.<p>.transport.status`, `.authentication.status`, `.processing.status`, `.readiness.vendor_validation.status` | `_transport`, `_authentication`, `_processing`, `_vendor_validation` |
| Inbound, Outbound, Pending, Awaiting retry | `messages.inbound.total`, `messages.outbound.total`, `messages.inbound.pending`, `messages.inbound.retry_wait` | `_messages` |
| Failed (DLQ) | `inbound.failed_dead_letter + outbound.failed_dead_letter` (`sumMeasured`) | `_messages` |
| Last successful processing (per protocol) | `messages.last_succeeded_at` = `MAX(completed_on) WHERE status='SUCCEEDED'` | `activity_from_sql` |
| Latest failure | `last_error`: newest-received row in `RETRY_WAIT` or `DEAD_LETTER` with an error code | `activity_from_sql` (`ORDER BY received_on DESC, id DESC LIMIT 1`) |
| Recent messages list | `GET /observability/messages?page=1&page_size=5` (all protocols, **last 7 days**) | `search_sql` |
| Latest failures list | `GET /observability/dlq?page=1&page_size=5` (inbound DEAD_LETTER, no window) | `search_sql` |
| "Last successful processing" above Recent messages | `overview.messages.last_successful_exchange_at` = the later of the last inbound SUCCEEDED `completed_on` and the last outbox `sent_on` | `_shared` |

Note the two "last successful processing" values differ by design: the per-protocol one is
inbound only; the one above the recent-messages list also counts outbound sends.

## 3.6 Section E – KPI overlap investigation

A row has exactly one `status` at a time, and inbound and outbound are separate tables.
Overlaps therefore come only from how the tiles **group** statuses:

| KPI A | KPI B | Same record in both? | Evidence |
|---|---|---|---|
| Pending | Awaiting retry | **Yes** — every RETRY_WAIT row is in both | `PENDING_STATUSES = ("PENDING","PROCESSING","RETRY_WAIT")` in `activity.py` |
| Pending | Failed | No | DEAD_LETTER is not in `PENDING_STATUSES` |
| Pending | DLQ | No | as above |
| Failed | DLQ | **Yes** — every inbound dead letter is in both | DLQ = `failed_dead_letter + outbound_dead_letter` |
| Awaiting retry | Failed / DLQ | No | different status values |
| Inbound | Pending, Failed, Awaiting retry | **Yes** (subsets) | Inbound total counts every status |
| Outbound | DLQ | **Yes** for outbound dead letters | DLQ includes `outbound_dead_letter` |
| Inbound | Outbound | No (different tables); an outbox row may *originate* from an inbound message (`source_message_id`) | `sql_models.py` |
| Duplicates | any | Not counted twice: a duplicate delivery returns `DUPLICATE` and inserts no row | `_accept_once` / idempotency unique key |
| Rejected intake | any | Never counted: rejected messages are not stored (only an in-memory counter) | `ExchangeGateway.receive` |
| Purged rows | any | Excluded once deleted (retention purge, off by default) | `purge_completed` |

**Failed means terminal.** "Failed" is `DEAD_LETTER` only, not "any failed attempt". A message
that failed once and succeeded on retry is counted as Processed, and appears only in
`retried_messages` (protocol pages, "N retried in total").

**Why adding tiles gives a wrong total.** The correct identity, verified on the demo data, is:

```text
Inbound = Processed (SUCCEEDED) + Pending (PENDING+PROCESSING+RETRY_WAIT) + Failed (DEAD_LETTER)
Demo:   42 =        24          +                 13                      +        5
```

Adding "Awaiting retry" (5) as well would count those 5 messages twice (47). Adding "DLQ" and
"Failed" together double-counts every inbound dead letter. Processed is not an Overview tile; it
is `overview.messages.processed` and appears on the protocol pages.

## 3.7 Section F – KPI time window

**There is no time filter on any Overview KPI.** The queries in `activity_from_sql` have no
`WHERE received_on ...` clause. Each KPI is the count of **rows currently retained** in the
integration tables for the caller's facilities, which the API states explicitly
(`"basis": "retained_rows"`) and the UI repeats ("messages currently retained, not lifetime
totals"). It is not a daily, 24-hour or 7-day figure.

Consequences:

- Rows stay forever unless `INTEGRATION_RETENTION_DAYS` is set **and** the integration service
  runs its purge (only SUCCEEDED inbound and SENT outbound rows are purged).
- The Message Logs page **does** use a window (default last 7 days). Its total can therefore be
  lower than the Inbound tile: in the demo stack, 38 messages in the last 7 days versus 42
  retained (four synthetic messages are 12 days old).

## 3.8 Refresh behaviour (Overview)

| Aspect | Behaviour | Source |
|---|---|---|
| Initial fetch | on first mount of any page that uses the overview query | `useIntegrationOverview` |
| Query key | `["integrations","overview"]` — shared by Overview, HTNG, FIAS and the DLQ summary | `lib/api/hooks.ts` |
| Automatic refresh | `refetchInterval: 60_000` (every 60 s) while the page is mounted. React Query v5 pauses interval refetching while the browser tab is hidden (default `refetchIntervalInBackground: false`) | `useIntegrationOverview` |
| Freshness | `staleTime: 30_000`; navigating to another integration page within 30 s reuses the cached data, after that the page refetches on mount | `useApiQuery` |
| Window focus | React Query default `refetchOnWindowFocus: true` (refetch if stale) — no override found | `App.tsx` `new QueryClient()` (defaults) |
| Manual refresh | **Refresh** button refetches the overview and the two activity lists | `IntegrationOverview.tsx` `refresh()` |
| Retries | up to 2 retries for network / 5xx; none for 4xx | `retry()` in `lib/api/hooks.ts` |
| Activity lists | `staleTime` 30 s, **no interval**; refreshed by the Refresh button or remount | `useIntegrationMessages`, `useIntegrationDeadLetters` |
| Server-side caching | none found; every request runs the queries | `observability.py` |

The "updated ..." time under "Integration status" is `generated_at` — the server time at which
this response was built. It is the closest thing to a "last refreshed" stamp and changes on
every refetch, even when no message changed.

# Chapter 4 – Timestamp and Timezone Explanation

## 4.1 Which timestamp is which

| What the UI shows | Response field | Database column | Set by | Meaning |
|---|---|---|---|---|
| Message "Received" | `received_at` | `integration_inbound_messages.received_on` | `ExchangeGateway._next_received_at()` at intake | the moment **our gateway accepted** the message (gateway clock), not a time supplied by the vendor |
| Message "Processed" | `completed_at` | `completed_on` | `completion()` on SUCCEEDED; `record_failure()` on DEAD_LETTER | when processing finished (success, or the final failed attempt) |
| DLQ "Last attempt" | `last_attempt_at` (= `completed_at`) | `completed_on` | `record_failure()` when dead-lettering | end of the last failed attempt |
| "Last successful processing" (protocol) | `messages.last_succeeded_at` | `MAX(completed_on) WHERE status='SUCCEEDED'` | worker | latest successful inbound completion |
| "Last successful processing" (Overview list header) | `overview.messages.last_successful_exchange_at` | later of the above and `MAX(outbox.sent_on)` | worker / relay | latest success in either direction |
| "Latest failure" time | `last_error.dead_lettered_at` or `received_at` | `completed_on` / `received_on` | worker | when that failure was recorded |
| "updated ..." (Integration status) | `generated_at` | — (server clock) | `build_overview(now=utcnow())` | when the API built this response — the page's effective "last refreshed" time |
| Worker heartbeat | `processing.worker_heartbeat.last.*` | — (in-memory) | `IntegrationMetrics.heartbeat()` in the **worker's** process | never observable from the API process; shown as "Not currently observable" |
| FIAS "Connected since" | `transport.links[].connected_since` | — (in-memory probe) | `TcpLink` health | only if a link existed in the API process (never today) |

There is **no** separate "page last refreshed in the browser" label; `generated_at` plays that
role on the Overview. Message Logs and DLQ show no refresh time.

## 4.2 Storage and transport format

1. **Clock.** `utcnow()` = `datetime.now(UTC)` (`core/envelope.py`).
2. **Storage.** Columns use `UTCDateTime` (`backend/app/db/types.py`): on MySQL it is
   `DATETIME(6)`; aware values are converted to UTC and stored without an offset
   (`process_bind_param`), and read back as aware UTC (`process_result_value`). Microseconds
   are kept.
3. **API.** `_iso()` returns `datetime.isoformat()`, e.g. `2026-11-20T00:13:46.648952+00:00`
   — always UTC with an explicit offset.
4. **Browser.** `new Date(iso)` then `toLocaleString(undefined, options)` — the user's
   **browser locale and browser time zone** decide the text (`lib/presentation.ts`).

## 4.3 Display formats

| Function (`lib/presentation.ts`) | Used for | Options | Example for `2026-11-20T00:13:46+00:00` in India (UTC+05:30) |
|---|---|---|---|
| `formatShortTimestamp` | table cells, activity lists, panel times | month short, day 2-digit, hour 2-digit, minute 2-digit; **year only if not the current year**; no seconds | en-IN: "20 Nov, 05:43 am"; en-US: "Nov 20, 05:43 AM" |
| `formatTimestamp` | tooltips (`title`) and "updated ..." | adds the year | "20 Nov 2026, 05:43 am" |
| `formatAge` | backlog age, stall threshold | compact duration | 63 819 s → "17h 43m"; 900 s → "15m" |

- Absolute, not relative ("5 minutes ago" is never shown).
- Same format on mobile (no separate mobile format; wide tables scroll horizontally).
- Missing value: tables "—"; panels "None recorded" (measured, nothing found) or
  "Unavailable" (could not be measured); invalid date strings fall back to "—" / "Unavailable".
- Hover any table time to see the full date with year.

> **About the example "25, 4:43 AM".** With `hour: "2-digit"` the hour is normally printed
> with a leading zero ("04:43"), and the month is always present. The exact string
> "25, 4:43 AM" could not be reproduced from the current source — **NOT VERIFIED**. It may be a
> clipped table cell or a screenshot of an earlier build. Whatever the rendering, the value is
> the gateway's UTC intake time converted to the viewer's time zone.

## 4.4 What happens over time after a message arrives

> **Figure: Timestamp and refresh lifecycle (what changes and what does not)** (diagram rendered in the PDF)

The answer depends on whether a worker runs. **In every environment that exists today, none
does**: the integration service refuses to start while `INTEGRATION_ENABLED` is false.

| Time | Event | Received time | KPI effect | Shown after the next refresh |
|---|---|---|---|---|
| 04:43:00 | message accepted (`PENDING`) | 04:43 (fixed forever) | Inbound +1, Pending +1 | within 60 s (interval) or on Refresh |
| 04:43:01 | *if a worker runs*: claimed (`PROCESSING`, `attempt_count` 1) | unchanged | Pending unchanged | — |
| 04:43:01 | *if the handler succeeds*: `SUCCEEDED`, `completed_on` set | unchanged | Pending −1, Processed +1, "Last successful processing" = 04:43 | next refetch |
| — | *today, with no worker* | unchanged | stays Pending | "Backlog stalled" after 15 min; backlog age grows on every refresh |

Two facts that follow from the code:

- If a message were accepted in production today and a worker ran, the stay handler would
  raise `ApprovalRequired` (live-write gate closed). That category is not retryable, so the
  message would go straight to `DEAD_LETTER` on its first attempt (`core/retry.py`
  `RetryPolicy.decide`). In practice intake is refused even earlier: both production adapters
  are BLOCKED.
- The worker polls every 1 s when idle (`ServiceSettings.poll_interval_seconds = 1.0`), so the
  dashboard's 60-second interval dominates how quickly a change becomes visible.

# Chapter 5 – HTNG Monitoring Page

The HTNG page (`ProtocolMonitoring protocol="htng"`) renders `views/ProtocolView.tsx` from
`protocols.htng` of the shared overview response, plus two small requests:
`GET /observability/messages?protocol=htng&page=1&page_size=10` and
`GET /observability/dlq?protocol=htng&page=1&page_size=5`. Refresh: the overview part polls
every 60 s; the Refresh button refetches all three.

## 5.1 Sections and data paths

| # | Section (UI) | Item | Response field | Backend calculation |
|---|---|---|---|---|
| 1 | Status summary | Connection / Authentication / Processing / Vendor validation | `transport.status`, `authentication.status`, `processing.status`, `readiness.vendor_validation.status` | `_transport`, `_authentication`, `_processing`, `_vendor_validation` |
| 2 | Connection | Status; Integration (switched on/off); Inbound endpoint; Vendor endpoint (outbound) | `transport.status`, `integration_enabled`, `inbound_endpoint_enabled`, `outbound_vendor_endpoint` | `_transport("htng")` from `IntegrationSettings`; vendor endpoint is the constant `"not_configured"` |
| 3 | Authentication | Status | `authentication.status` | `configured` if ≥1 enabled client **and** ≥1 enabled mapping for this protocol in your facilities, else `not_configured`; `not_available` when the admin store cannot be read |
| 3 | | Active senders / Facility mappings | `enabled_clients`, `enabled_mappings` | `IntegrationAdmin.auth_coverage()`: `COUNT(DISTINCT client.id)`, `COUNT(mapping.id)` over enabled clients JOIN enabled mappings, `WHERE mapping.facility_id IN (scope)`, grouped by the client's `protocols` value |
| 3 | | Rejected messages / Sign-in failures | `intake_rejections.rejected_by_category`, `auth_failures_by_reason` | in-memory counters `intake_rejected` / `auth_failures` of **this API process since it started** (`IntegrationMetrics`); reset on restart; not durable |
| 4 | Processing | Status, oldest pending message, stall threshold | `processing.status`, `oldest_pending_age_seconds`, `stall_threshold_seconds` | `_processing` (see 3.2 A3) |
| 4 | | Worker activity | `processing.worker_heartbeat.observed` | `_heartbeats()`: heartbeats recorded in this API process — workers run elsewhere, so always "Not currently observable" today |
| 5 | Message statistics | Inbound / Processed / Pending / Awaiting retry / Failed / Outbound | `messages.inbound.total`, `.succeeded`, `.pending`, `.retry_wait`, `.failed_dead_letter`, `messages.outbound.total` | `_messages` over `activity_from_sql` counts (no time window) |
| 5 | | detail lines | `last_received_at`, `last_succeeded_at`, `retried_messages` ("N retried in total" = retained inbound rows with `attempt_count > 1`), `outbound.sent` | `activity_from_sql` |
| 6 | Recent messages | table | `/observability/messages` page items | `search_sql`, last 7 days, newest first |
| 7 | Failed messages | Latest failure + table | `last_error`; `/observability/dlq` items | see 3.5 D7; `search_sql` with `status = DEAD_LETTER` |
| 8 | Vendor validation | adapter rows, status, pending decisions | `configuration.adapters[]`, `readiness.vendor_validation` | `_adapters` from `AdapterRegistry.statuses()`; production HTNG adapter: readiness `blocked`, specification `null`, blocking HF-07, HF-08 → UI "Specification: Not received" |
| 9 | HTNG readiness | 8 dimensions | `readiness.*` | `_readiness` (`readinessRows` in the UI keeps them separate) |

Demo-stack values (synthetic, 05:37 UTC): Connection **Disabled**, Authentication
**Configured** (1 sender, 2 mappings), Processing **Backlog stalled**, Inbound 24, Processed 13,
Pending 8, Awaiting retry 3, Failed 3, Outbound 2 (0 sent), 3 retried messages.

## 5.2 HTNG implementation details

| Topic | What the code does | Where |
|---|---|---|
| SOAP transport | endpoint `POST /api/v1/integrations/htng/inbound`; disabled → SOAP fault 503 | `api/router.py` `htng_inbound` |
| SOAP 1.1 / 1.2 | version from media type; 415 for any other media type; faults in the request's version (1.2 uses Sender/Receiver) | `soap_version_from_content_type`, `soap_fault`, `transport/soap.py` |
| Size limit | `Content-Length` and streamed body checked against `INTEGRATION_MAX_MESSAGE_BYTES` (default 256 KiB) → 413 | `htng_inbound` |
| XML security | rejects any DOCTYPE / entity (XXE, billion-laughs), limits depth, element and attribute counts and reports namespaces per element (so a profile can enforce an allow-list), all before ElementTree builds a tree | `transport/xml_security.py` |
| Schema registry | `SchemaProfile` per vendor deployment; production `SchemaRegistry()` is **empty** → adapter BLOCKED | `adapters/htng/schema.py`, `runtime.py` |
| WSDL / XSD | none in the repository; `XsdValidator` refuses to be constructed until an approved XSD library and an XSD exist | `schema.py` (HF-07, HF-39) |
| WS-Security | not implemented (HF-08) | — |
| Authentication | headers `X-Integration-Client` + `X-Integration-Secret`; stored as `sha256$<hex>`, constant-time compare, dummy digest for unknown clients, same error for every failure → SOAP fault 401 | `security/clients.py` |
| Rate limit | optional per-client per-minute limit per API process → 429; off by default (needs BLK-V7 volumes) | `_MinuteRateLimiter`, `HTNG_RATE_LIMIT_PER_MINUTE` |
| Inbound processing | gateway pipeline, then the asynchronous worker | `ExchangeGateway`, `InboundWorker` |
| Response | profile acknowledgement (200) if the profile defines one, else 202; `X-Correlation-ID` header | `htng_inbound` |
| Outbound | `HtngSoapSender` → `SoapTransport.call()`; endpoints must be HTTPS (`insecure_endpoint` otherwise); **no endpoint configured** and no relay running | `adapters/htng/sender.py`, `transport/soap.py` |

> **Figure: HTNG SOAP inbound sequence (code path; production is switched off and the adapter is BLOCKED)** (diagram rendered in the PDF)

**Synthetic tests versus vendor validation.** Tests (e.g. `test_htng_adapter.py`,
`test_api.py`, the certification harness under `tests/integrations/certification/`) drive the
same code with a generic test profile accepted only with `allow_unverified=True` outside
production. They prove the pipeline behaves correctly for *our* test messages. They cannot
prove that a real vendor's messages, namespaces, SOAP actions or security headers are handled
correctly — that needs HF-07, HF-08 and a vendor test environment (HF-09).

# Chapter 6 – FIAS Monitoring Page

The FIAS page uses exactly the same nine sections and data paths as Chapter 5, with
`protocols.fias` and `protocol=fias`. Only the differences are listed here.

## 6.1 Displayed differences

| Section | FIAS behaviour | Source |
|---|---|---|
| Connection – Status | **Not observable**: no FIAS transport is registered in the API process | `_transport("fias")` |
| Active connections, Links | `null` → "Not currently observable"; would come from per-link health probes (`TcpLink` health: state, connections, reconnect attempts, frames, framing errors, last error code) | `_transport`, `transport/tcp.py` `TransportHealth` |
| Link table | shown only when links exist (verified only with the test fixture `overview_fias_links`) | `ProtocolView.tsx` |
| Rejected messages / Sign-in failures | **Not currently observable**: "FIAS intake does not run in this API process" | `_intake_rejections` |
| Vendor validation | readiness `blocked`, blocking HF-11; pending decisions HF-05, HF-06, HF-11 | `FIASAdapter.status()`, `VENDOR_DECISIONS` |

Demo-stack values (synthetic): Authentication **Configured** (1 sender, 1 enabled mapping; the
second FIAS mapping is deliberately disabled), Inbound 18, Processed 11, Pending 5, Awaiting
retry 2, Failed 2, Outbound 1.

## 6.2 FIAS implementation details

| Topic | Implemented in code | Exercised by tests | Wired into production | Vendor-verified |
|---|---|---|---|---|
| TCP client link (`TcpLink`): connect timeout, read/write timeouts, bounded inbound queue (100), graceful stop | Yes | Yes | No | No |
| TCP server link (`TcpListenerLink`): mandatory `allowed_peers` IP/CIDR allow-list, one active connection, refuses to start with an empty list | Yes | Yes (`test_transport_server.py`) | No | No |
| Reconnection: exponential back-off 1 s → 60 s (`ReconnectPolicy`) | Yes | Yes | No | No |
| Framing: `DelimitedFramer`, explicit start/end markers, max frame size | Yes; **no default markers** | Yes, with **test** markers 0x02 / 0x03 (`simulators/fixtures.py`, labelled a test assumption) | No | No (HF-06) |
| Record parser / serializer: encoding, record id, separator, field ids all from `FiasSpecification` data | Yes | Yes (provisional spec) | Adapter BLOCKED (`PRODUCTION_SPECIFICATION = None`) | No (HF-11) |
| ACK, heartbeat, handshake / session start | **No** (deliberately; rules unknown) | — | — | No (HF-06) |
| Intake from a link: `LinkPump` hands frames to the gateway in a worker thread; a transient intake failure retries the **same** frame with back-off (0.5 s → 30 s) and never drops it | Yes | Yes | No | No |
| Property-code matching: EXACT (case-sensitive) until HF-05; MySQL column uses binary collation so the DB cannot silently decide | Yes | Yes | n/a | No (HF-05) |
| Persistence, retry, DLQ | shared with HTNG | Yes | worker only | — |

> **Figure: FIAS TCP sequence as exercised by tests and the simulator (NOT wired into any running process)** (diagram rendered in the PDF)

# Chapter 7 – Message Logs Page

## 7.1 How records are stored and retrieved

Each accepted inbound message is one row in `integration_inbound_messages` (metadata), one row
in `integration_inbound_payloads` (the body, never sent to the dashboard) and one row in
`integration_idempotency_keys`. The page reads only the first table, through
`GET /api/v1/integrations/observability/messages` → `observability_messages` →
`MessageQuery` → `repository.search_messages` → `activity.search_sql`.

```sql
-- faithful equivalent of search_sql()
SELECT COUNT(*) FROM integration_inbound_messages
 WHERE received_on >= :from AND received_on <= :to
   AND facility_id IN (:effective_facilities)   -- your scope ∩ requested facilities
   AND protocol IN (:protocols)                 -- only if filtered
   AND status IN (:statuses);                   -- only if filtered
SELECT * FROM integration_inbound_messages WHERE <same conditions>
 ORDER BY received_on DESC, id DESC
 LIMIT :page_size OFFSET (:page - 1) * :page_size;
```

## 7.2 Parameters and limits

| Parameter | Rule | Source |
|---|---|---|
| `protocol` | `htng` / `fias`, repeatable | `ProtocolFilter` |
| `status` | `PENDING`, `PROCESSING`, `SUCCEEDED`, `RETRY_WAIT`, `DEAD_LETTER` (repeatable; the UI sends one) | `StatusFilter` |
| `facility_id` | up to 50 UUIDs; any outside your scope → **403** | `_facility_filter` |
| `received_from`, `received_to` | must carry a timezone offset (else 422); default window = **last 7 days** ending now; window over **31 days** → 422 | `SEARCH_DEFAULT_WINDOW`, `SEARCH_MAX_WINDOW` |
| `page`, `page_size` | `page ≥ 1`; `page_size` 1–100 (default 20); offset ≤ 10 000 | `MAX_PAGE_SIZE`, `MAX_OFFSET` |
| Sorting | fixed: newest received first, then message id — stable across pages | `search_sql` |
| Response | HMS `Page` envelope `{items, page, page_size, total}` plus `window {received_from, received_to}` | `_page` |
| Item fields | `message_id, protocol, facility_id, direction, message_type, status, received_at, completed_at, attempt_count, retry_count (= attempt_count − 1, min 0), max_attempts, next_attempt_at, correlation_id, error {code, category}` | `message_item` |

## 7.3 What the user does and what happens

| User action | Frontend | Request |
|---|---|---|
| Opens the page | `parseFilters` reads the URL; defaults page 1, size 20 | `?page=1&page_size=20` (backend window: last 7 days) |
| Picks Protocol = FIAS | `MessageFilterBar` → `onChange({..., page: 1})` → `useUrlFilters` writes `?protocol=fias` | `&protocol=fias` |
| Picks Status = Processed | URL `status=SUCCEEDED` | `&status=SUCCEEDED` |
| Picks a facility | choices limited to your scope (`facilityOptions`); an out-of-scope id typed into the URL is dropped (`restrictToScope`) | `&facility_id=<uuid>` |
| Sets From / To dates | local calendar days → `toQueryParams` converts to start/end of day in the browser's time zone, sent as UTC ISO | `&received_from=…Z&received_to=…Z` |
| Invalid range (To before From, or > 31 days) | `validateDateRange` shows an alert; the query is disabled | **none** |
| Next page / rows per page | `TablePagination`; rows 10/20/50/100 | `&page=2` / `&page_size=50` |
| Reset | clears every filter, keeps the page size | default request |

A link such as "HTNG message logs" on the Overview simply opens
`/integrations/messages?protocol=htng`, because filters live in the URL.

**Table columns** (`components/MessageTables.tsx`): Message (business type, short message id,
reference id = `correlation_id`), Protocol, Facility (name from `GET /facilities`), Status,
Received, Processed, Retries, Failure reason (business wording of `error.code` + category).

**Limitations, stated plainly.**

- Inbound only: the endpoint never returns outbox rows, so outbound messages cannot be
  browsed in the UI (an operator API `GET /integrations/outbox` exists but no page uses it).
- **No message-id or reference-id search** (the API has no such parameter).
- Only retained rows can be shown; rejected intake is never stored.
- No payload or body is ever returned; `GET /integrations/messages/{id}` (masked body) exists
  but is not used by the dashboard.

> **Figure: Message Logs filtering flow (URL → request → SQL → table)** (diagram rendered in the PDF)

# Chapter 8 – Failed Messages and DLQ

## 8.1 Definitions as implemented

| Term | Implementation |
|---|---|
| Transient failure | an error whose category is `TRANSIENT` (e.g. `hms_unavailable`, timeouts). `IntegrationError.retryable` is true **only** for this category |
| Permanent failure | every other category: permanent, validation, protocol, security, conflict, unsupported, vendor_blocked, approval_blocked — dead-lettered on the **first** failure |
| Retryable message | a message whose last error was transient and whose `attempt_count < max_attempts` (default 5) |
| Retry | automatic: `RETRY_WAIT` with `next_attempt_at = now + delay`; delay = `5 s × 2^(attempt−1)` capped at 900 s (`RetryPolicy`); the service adds full jitter |
| Retry exhaustion | `attempt_count >= max_attempts` → `DEAD_LETTER` (`max_attempts_exhausted`) |
| Dead-lettered message | status `DEAD_LETTER`, `completed_on` = time of the last attempt, `last_error_code` / `last_error_category` kept |
| Retry count (UI "Retries") | `attempt_count − 1` (never negative) |
| Retry attempts (DLQ column) | `attempt_count` (total attempts made) |
| Failed vs Awaiting retry | Failed = `DEAD_LETTER` (stopped); Awaiting retry = `RETRY_WAIT` (will try again) |
| Retry vs Redrive | retry is automatic and bounded; **redrive** is a manual, audited operator action that moves a dead letter back to `PENDING` with `attempt_count = 0` |

> **Figure: Failure, retry and dead-letter decision (worker.py, core/retry.py, sql_repository.py)** (diagram rendered in the PDF)

## 8.2 Storage, investigation and redrive

- DLQ storage is the same inbound table filtered by `status = 'DEAD_LETTER'` — there is no
  separate DLQ table. Outbox dead letters live in `integration_outbox_messages`.
- `GET /observability/dlq` has **no default date window** (dead letters stay until redriven);
  it returns `failure_category`, `failure_code`, `attempt_count`, `retry_count`, `received_at`,
  `last_attempt_at`, `correlation_id`, and `redrive {state_eligible, caller_has_permission,
  eligible}`.
- Redrive: `POST /api/v1/integrations/messages/{id}/redrive` with a reason of 10–500
  characters, `facility_management` **write**, scoped to the caller. It locks the row, checks
  it is `DEAD_LETTER`, resets it to `PENDING` and writes an `integration_audit_events` row
  (`action = message.redrive`, reason, previous error code) in the **same transaction**
  (`sql_repository.redrive`).

## 8.3 The DLQ page today (read-only)

| Element | Source |
|---|---|
| Failure summary tiles: Total in DLQ, HTNG inbound, FIAS inbound, Outbound | the cached **overview** query: `failed_dead_letter + outbound_dead_letter`, `protocols.htng/fias.messages.inbound.failed_dead_letter`, `outbound_dead_letter` |
| Filters (protocol, facility, dates; no status) | URL filters → `GET /observability/dlq` |
| Table: Message, Facility, Failure category, Failure reason, Retry attempts, Last attempt (with Received underneath), Reprocessing | `dlq_item` fields; `components/MessageTables.tsx` `DeadLetterTable` |
| "Reprocessing" column | Eligible / Not eligible / Requires write access — **information only** |

**There is no redrive button.** The page states "Reprocessing is not available from this
screen". The audited endpoint exists in the backend but is deliberately not exposed in this UI
(verified by the frontend test "no redrive action is exposed").

Two consistency notes:

1. The summary tiles count **all** your facilities and both directions; the table lists only
   **inbound** dead letters matching the filters. If outbox dead letters existed, "Total in
   DLQ" would exceed the table total.
2. The summary refreshes every 60 s with the overview; the table does not poll.

# Chapter 9 – Complete Backend Code-Level Architecture

All paths below are under `backend/app/integrations/` unless stated. Tests are under
`backend/tests/integrations/`.

> **Figure: Common backend processing used by both protocols** (diagram rendered in the PDF)

## 9.1 Components

| Component | Why it exists | How it works | Implemented by | Data | Calls | Verified by | Does NOT guarantee |
|---|---|---|---|---|---|---|---|
| Integration authentication | a vendor link is a machine, not a user | client code + 256-bit generated secret; `sha256$<hex>` stored; `hmac.compare_digest`; dummy digest for unknown codes; one generic failure | `security/clients.py` `ClientAuthenticator`, `security/sql_stores.py` `SqlClientStore` | `integration_clients` | — | `test_security.py`, `test_admin.py` | secret storage on the vendor side (HF-22); mutual TLS |
| Facility mapping | external property codes must map to exactly one HMS facility per client | lookup by (client, normalized code); missing / ambiguous / disabled → reject; payload facility identifiers must agree ("scope smuggling" check) | `security/facility.py` `FacilityResolver` | `integration_facility_mappings` | — | `test_security.py`, `test_exchange.py` | the final case rule (HF-05, EXACT until then) |
| Exchange layer | one pipeline for both protocols | `receive()`: size → protocol permitted → adapter decode → facility → handler exists → idempotency key → envelope → `repository.accept()`; every failure becomes a REJECTED result | `exchange/gateway.py` `ExchangeGateway` | inbound tables | adapters, resolver, repository | `test_exchange.py`, `test_end_to_end.py` | that a vendor's real messages decode (adapters BLOCKED) |
| Protocol adapters | isolate everything vendor-specific | pure bytes ↔ canonical message; `status()` reports READY / TEST_ONLY / BLOCKED | `adapters/htng/adapter.py`, `adapters/fias/adapter.py` | — | schema / spec data | `test_htng_adapter.py`, `test_fias_adapter.py` | correctness against vendor specs (none supplied) |
| Durable persistence | nothing accepted may be lost | message + payload + idempotency key in one transaction, status `PENDING`, `next_attempt_at = received_on` | `processing/sql_repository.py` `SqlIntegrationRepository.accept` | 3 inbound tables | — | `test_mysql_persistence.py`, `test_repository_contract.py` | encryption at rest / retention values (HF-21) |
| Idempotency | vendors resend | unique (client, facility, idempotency_key); same fingerprint → `DUPLICATE` (no new row); different content → conflict; MySQL 1062 on that key handled as a race | `_accept_once`, `_compare`, `is_idempotency_duplicate` | `integration_idempotency_keys` | — | `test_mysql_persistence.py` | duplicate protection after the key is purged (lasts `RETENTION_DAYS`) |
| Worker leases | safe concurrency and crash recovery | `SELECT … FOR UPDATE SKIP LOCKED` ordered by `next_attempt_at`; fresh random lease token; completion re-checks token and expiry ("fencing") else `LeaseLost` | `sql_repository.claim`, `_fenced_row`, `completion` | inbound table | — | `test_mysql_persistence.py`, `test_hardening.py` | exactly-once side effects outside the HMS transaction |
| Retry / back-off | temporary faults should heal | `RetryPolicy`: only TRANSIENT retried; delay 5 s × 2ⁿ⁻¹ ≤ 900 s; max 5 attempts (settings) | `core/retry.py`, `processing/worker.py` | inbound table | — | `test_core.py`, `test_service.py` | per-message-type policy (HF-27) |
| DLQ | bad messages must stop, visibly | `record_failure` sets `DEAD_LETTER`, `completed_on`, error code/category | `sql_repository.record_failure` | inbound table | — | `test_repository_contract.py` | automatic recovery |
| Redrive | operator-controlled recovery | locks row, checks DEAD_LETTER, → PENDING, attempts 0, audit row same transaction; reason 10–500 chars; write permission | `sql_repository.redrive`, `api/router.py` `redrive` | inbound + audit tables | — | `test_api.py`, `test_repository_contract.py` | that reprocessing will now succeed |
| Per-stay ordering | a check-out must not overtake its check-in | handler's `ordering_key` = `stay:<external_stay_ref>`; a message is claimable only if no EARLIER same-key message is unfinished; a dead-lettered predecessor also blocks (until redrive) | `domain/stays.py` `ordering_key`, `sql_repository._not_blocked`, `repository.blocking_statuses` | inbound table | — | `test_ordering.py` | ordering across different clients |
| Audit transactions | the trail cannot disagree with the data | audit rows written in the same transaction as the change (redrive, mappings, clients, completion audits, retention purge) | `admin.py`, `sql_repository.py` | `integration_audit_events` | — | `test_admin.py` | immutability / retention (HF-23) |
| Credential rotation | change secrets without an outage | `rotate_secret(overlap ≤ 7 days)` keeps the previous hash until `secondary_expires_on`; `revoke_previous_secret` ends it early; CLI only (`python -m app.integrations.cli`) | `admin.py` `IntegrationAdmin` | `integration_clients` | — | `test_admin.py` | secure delivery of the new secret (HF-22) |
| Background worker / service | process stored messages | loop: `InboundWorker.run_once()` (batch 10), sleep 1 s when idle, bounded error back-off, graceful SIGTERM, optional retention purge hourly; refuses to start unless `INTEGRATION_ENABLED` | `service.py`, `processing/worker.py` | inbound / outbox | dispatcher, repository | `test_service.py` | hosting / restart policy (HF-25/26); **no outbox relay is started** |
| Domain handler | apply check-in / check-out through HMS rules | `StayEventHandler` → `StayDomainAdapter` → existing `app/services/stays_write` | `domain/stays.py` | HMS stay tables | LiveWriteGate | `test_domain.py`, `test_hms_domain_mysql.py` | anything while the gate is closed and no resolver is registered |
| Feature switches | nothing changes production by default | `IntegrationSettings` (`INTEGRATION_` prefix), all OFF; validation (e.g. live writes require an actor id) | `config.py` | — | — | `test_core.py` / `test_hardening.py` | — |
| Live-write gate | approvals are code, not a flag | open only if `LIVE_DOMAIN_WRITES` and HF-01/02/05/19 Approved **with evidence** in `DECISIONS` | `domain/approvals.py` `LiveWriteGate` | — | — | `test_domain.py` | — |
| Health checks | operations | `GET /integrations/health` (public, no data); `/readiness` (persistence, adapters, worker heartbeats, transports; 503 when not ready); `/facilities/health` (per-facility durable figures) | `api/router.py`, `processing/health.py` | integration tables | — | `test_api.py`, `test_health_view.py` | cross-process worker visibility |
| Observability | dashboard model | read-only aggregation; null for unmeasurable; sanitized error identifiers only | `observability.py`, `processing/activity.py` | inbound, outbox, clients, mappings | — | `test_observability.py` | live vendor status |
| In-process metrics | counters for diagnostics | dictionary counters with low-cardinality labels; heartbeats per component | `metrics.py` `IntegrationMetrics` | memory | — | `test_api.py` | persistence across restarts or processes |

## 9.2 Runtime wiring

`runtime.build_default_runtime()` (called lazily on the first integration request; importing
`app.main` opens no socket and starts no worker) builds:

- `SqlIntegrationRepository(engine)` on the **HMS database engine** (`app.db.session.engine`);
- `FIASAdapter()` and `HTNGAdapter(SchemaRegistry())` — both BLOCKED;
- handlers for `stay.check_in` and `stay.check_out` with a closed `LiveWriteGate` and
  `resolver=None`;
- `ClientAuthenticator(SqlClientStore)`, `FacilityResolver(SqlFacilityMappingStore)`;
- `persistence_probe = table_presence(engine)`, `admin = IntegrationAdmin(engine)`;
- **no transports** (`transports = {}`), hence FIAS "Not observable".

The integration router is mounted in `backend/app/api/v1/router.py`
(`api_router.include_router(integrations_router)`), so all routes are under `/api/v1/integrations`.

# Chapter 10 – Database Tables and Data Lineage

## 10.1 Status of the schema

| Layer | Status | Location |
|---|---|---|
| SQLAlchemy models | **Candidate schema, not approved (HF-39)**; declared on a separate `INTEGRATION_METADATA` so Alembic never sees them | `processing/sql_models.py` |
| Draft migration | **not applied**; in `migrations/drafts/`, which Alembic does not scan; down-revision deliberately unset (two existing Alembic heads) | `backend/migrations/drafts/integration_tables_candidate.py` |
| Reviewable DDL | generated from the models | `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`, `docs/HTNG_FIAS_DATABASE_DESIGN.md` |
| Where the tables exist | **only** in disposable test / demo MySQL databases, created by `create_integration_tables()` | test suite, demo stack |
| HMS dev / production database | **absent** — every count on the dashboard would be "Unavailable" | DBA approval pending |

> **Figure: Integration tables (sql_models.py; CANDIDATE SCHEMA, not approved — HF-39)** (diagram rendered in the PDF)

## 10.2 Entities

| Table | Purpose | Important columns | Inserted by | Updated by | Read by (API → KPI) | Retention |
|---|---|---|---|---|---|---|
| `integration_clients` | one vendor link identity | `client_code` (unique), `secret_hash`, `secondary_secret_hash`, `secondary_expires_on`, `enabled` (default 0), `protocols` | `IntegrationAdmin.create_client` (CLI) | enable, rotate, revoke | overview → Authentication "Active senders" | none |
| `integration_facility_mappings` | external property code → facility, per client | `client_id`, `external_property_code`, `normalized_property_code` (binary collation), `facility_id`, `enabled` (default 0), `created_by`; unique (client, normalized code) | `create_mapping` (API write / CLI) | `set_mapping_enabled` (audited) | overview → "Facility mappings"; `GET /integrations/mappings` | none |
| `integration_inbound_messages` | one accepted inbound message (metadata) | `id`, `client_id`, `facility_id`, `protocol`, `direction`, `message_type`, `external_message_id`, `idempotency_key`, `ordering_key`, `correlation_id`, `schema_version`, `payload_hash`, `status` (CHECK in 8 values), `attempt_count`, `max_attempts`, `next_attempt_at`, `lease_owner/token/expires_at`, `last_error_code`, `last_error_category`, `received_on`, `completed_on` | `accept()` | `claim`, `completion`, `record_failure`, `redrive` | overview (all inbound KPIs), `/observability/messages`, `/observability/dlq` | SUCCEEDED rows older than `RETENTION_DAYS` purged (off by default) |
| `integration_inbound_payloads` | the message body, kept apart from metadata | `message_id` (PK, FK, cascade), `body_canonical`, `wire_payload` (only if `STORE_RAW_WIRE_PAYLOAD`), `retain_until` | `accept()` | — | worker only; **never** the dashboard | deleted with the message; encryption pending HF-21 |
| `integration_idempotency_keys` | duplicate detection | `client_id`, `facility_id`, `idempotency_key`, `fingerprint`, `message_id`; unique (client, facility, key) | `accept()` | — | intake only | deleted with the message |
| `integration_outbox_messages` | messages to send to vendors | `source_message_id`, `client_id`, `facility_id`, `protocol`, `message_type`, `correlation_id`, `body_canonical`, `payload_hash`, `status` (5 values), `attempt_count`, `next_attempt_at`, lease columns, `last_error_code`, `created_on`, `sent_on` | `completion().add_outbox`, `enqueue_outbox` | relay (not running) | overview → Outbound, DLQ, "last successful exchange" | SENT rows older than `RETENTION_DAYS` purged |
| `integration_audit_events` | append-only trail | `occurred_on`, `actor_type`, `actor_id`, `action`, `facility_id`, `message_id` (no FKs), `reason`, `detail` (metadata only) | admin, redrive, completion audits, purge, security rejections | never | `GET /integrations/audit` (not used by the dashboard) | pending HF-23 |

**Indexes that the dashboard relies on:** `(facility_id, status, received_on)` and
`next_attempt_at` on the inbound table; `(facility_id, status, created_on)` on the outbox.

**Known data-quality gap.** `protocol` and `direction` have **no CHECK constraint**. A row with
an invalid `direction` is counted by the overview aggregates but makes `/observability/messages`
and `/observability/dlq` fail with HTTP 500 (found in the full-stack E2E sprint; see Chapter 14).

# Chapter 11 – Frontend Implementation

## 11.1 Files

| Area | Files (`frontend/src/...`) |
|---|---|
| Routes | `App.tsx` (inside the authenticated layout) |
| Navigation | `components/layout/AppSidebar.tsx` (Integrations group) |
| RBAC | `core/rbac/modules.ts` (`/integrations` → `facility_management`), `core/components/ModuleGuard` |
| API client | `lib/api/client.ts` (base URL `VITE_API_BASE_URL`, default `/api/v1`; `Authorization: Bearer <token>`; 401 → `hms:unauthorized` event) |
| API types and calls | `lib/api/integrations.ts` (`getIntegrationOverview`, `searchIntegrationMessages`, `listIntegrationDeadLetters`) |
| Hooks | `lib/api/hooks.ts` (`useIntegrationOverview`, `useIntegrationMessages`, `useIntegrationDeadLetters`, `useFacilities`) |
| Pages | `features/integrations/pages/*.tsx` |
| Views | `features/integrations/views/OverviewView.tsx`, `ProtocolView.tsx` |
| Components | `components/Panel.tsx`, `KpiTile.tsx`, `ProtocolCard.tsx` (`ProtocolHealthPanel`, `LastErrorText`), `StatusBadge.tsx` (`StatusBadge`, `StatusItem`), `Metric.tsx` (`DetailRow`, `CountValue`), `ReadinessPanel.tsx`, `MessageFilterBar.tsx`, `MessageTables.tsx`, `QueryErrorState.tsx` |
| Business wording | `lib/presentation.ts` (status labels and tones, failure / category / message-type labels, explanations, null rule, filters, date validation, facility scope) |
| Facility scope | `lib/hooks.ts` `useFacilityScope` (user's `facility_ids` from `AuthContext`; names from `GET /facilities`) and `useUrlFilters` |
| Shared HMS styling reused | `core/styles/surfaceTokens.ts` (card surface tokens), `PageHeader`, `DataState`, `TablePagination`, `Table` |

## 11.2 Complete data path

```text
MySQL integration tables
  → activity_from_sql / search_sql / auth_coverage          (backend/app/integrations/processing, admin.py)
  → build_overview / message_item / dlq_item                (observability.py)
  → FastAPI route, facility_management read, caller scope   (api/router.py)
  → JSON (UTC ISO timestamps, null for unmeasurable)
  → apiClient.get + Bearer JWT                              (lib/api/client.ts)
  → React Query cache, key ["integrations", ...]            (lib/api/hooks.ts)
  → page → view → KpiTile / Panel / tables                  (features/integrations)
  → business wording + browser-local time                   (lib/presentation.ts)
```

## 11.3 Page → component → API mapping

| Page | Components | Queries (key) | Polling |
|---|---|---|---|
| Overview | `OverviewView`, `StatusItem`, `KpiTile` ×6, `ProtocolHealthPanel` ×2, `MessageActivityList`, `FailureActivityList` | `["integrations","overview"]`; `["integrations","messages",{page:1,page_size:5}]`; `["integrations","dlq",{page:1,page_size:5}]` | overview 60 s |
| HTNG / FIAS | `ProtocolView`, `StatusItem` ×4, `Panel` ×3, `KpiTile` ×6, `MessageTable`, `DeadLetterTable`, `ReadinessPanel` | overview; `messages {protocol, page 1, size 10}`; `dlq {protocol, page 1, size 5}` | overview 60 s |
| Message Logs | `MessageFilterBar`, `MessageTable`, `TablePagination` | `["integrations","messages", toQueryParams(filters)]` (previous page kept as placeholder while loading) | none |
| DLQ | `KpiTile` ×4, `MessageFilterBar` (no status), `DeadLetterTable`, `TablePagination` | overview; `["integrations","dlq", params]` | overview 60 s |

## 11.4 Behaviour shared by every page

- **Null rule:** `formatMetric(null)` → "Unavailable" / "Not currently observable"; derived
  totals use `sumMeasured` (null if any input is null).
- **Status badges:** text label + tone; "unknown" tone (dashed, muted) for not observable /
  unavailable / not reported, so "we cannot see it" never looks like "it is down".
- **No internals on screen:** error codes, categories and message types are translated
  (`failureLabel`, `failureCategoryLabel`, `messageTypeLabel`); raw identifiers survive only in
  `data-*` attributes for support and tests.
- **Responsive:** grids `grid-cols-2 md:grid-cols-3 xl:grid-cols-6` for KPIs; panels stack on
  small screens; tables scroll inside their own container. Browser-verified at 1440×900,
  1366×768, 768×1024 and 390×844 (20 Nov 2026, headless Edge, mock data).

# Chapter 12 – API-by-API Explanation

All routes are mounted under `/api/v1/integrations` (`api/router.py`). Authentication is the HMS
JWT (`Authorization: Bearer`). "Scope" means the user's `facility_ids`.

## 12.1 Endpoints used by the dashboard

### GET /observability/overview

| Item | Value |
|---|---|
| Handler | `observability_overview` → `build_overview` |
| Permission | `facility_management` read (401 without token, 403 without the grant) |
| Query parameters | `stall_threshold_seconds` (int, 60–86400, default 900) |
| Database | grouped counts on inbound and outbox tables; MIN / MAX timestamps; latest failure (LIMIT 1); auth coverage join; table presence probe |
| Response | see 3.1; `facility_scope: "caller"` |
| Errors | does **not** return 503 when tables are missing: figures become `null` with `status: "not_available"` |
| Consumers | Overview, HTNG, FIAS, DLQ summary |

### GET /observability/messages

| Item | Value |
|---|---|
| Handler | `observability_messages` → `MessageQuery` → `search_messages` → `search_sql` |
| Permission / scope | read; facility filter outside scope → 403 |
| Parameters | `protocol[]`, `status[]`, `facility_id[]` (≤ 50), `received_from`, `received_to` (offset required), `page` (≥ 1), `page_size` (1–100, default 20) |
| Rules | default window 7 days; maximum 31 days; offset ≤ 10 000 |
| Response | `{items[message_item], page, page_size, total, window}` |
| Errors | 422 (bad parameter, naive datetime, window > 31 days, unknown value, offset too large); 503 if persistence is unavailable (`PERSISTENCE_UNAVAILABLE`); 500 on an invalid stored `direction` (Chapter 14) |
| Consumers | Message Logs, HTNG / FIAS recent messages, Overview recent messages |

### GET /observability/dlq

| Item | Value |
|---|---|
| Handler | `observability_dlq` → `search_sql` with `statuses = {"DEAD_LETTER"}` |
| Parameters | `protocol[]`, `facility_id[]`, `received_from`, `received_to`, `page`, `page_size` (no status) |
| Rules | default window from 1970-01-01 to now (no default limit on age) |
| Response | Page envelope of `dlq_item` with `redrive {state_eligible, caller_has_permission, eligible}` (`caller_has_permission` = `facility_management` write) |
| Consumers | DLQ page, protocol pages, Overview latest failures |

## 12.2 Other integration endpoints (not used by the dashboard)

| Method and route | Permission | Purpose |
|---|---|---|
| `GET /health` | public | liveness, returns `{"status":"ok"}` only |
| `GET /readiness` | read | persistence, adapters, worker heartbeats, transports, live-write gate; HTTP 503 when not ready |
| `GET /adapters` | read | adapter readiness, specification, message types, blocking decisions |
| `GET /messages` | read | inbound metadata list (`status`, `limit` ≤ 200) |
| `GET /messages/{id}` | read | one message with **masked** body |
| `GET /dlq` | read | dead letters (list, `limit`) |
| `POST /messages/{id}/redrive` | **write** | audited redrive, reason 10–500 chars |
| `GET /outbox` | read | outbound queue |
| `GET /metrics` | read | in-process counters + counts by status |
| `GET /facilities/health` | read | per-facility durable health, `window_minutes` 1–10 080 |
| `GET /audit` | read | audit trail |
| `GET /mappings`, `POST /mappings`, `PATCH /mappings/{id}` | read / write / write | facility mappings (created disabled; changes audited) |
| `POST /htng/inbound` | client credentials (not JWT) | vendor SOAP endpoint; disabled by default |

> **Figure: Dashboard API architecture (request path for one observability call)** (diagram rendered in the PDF)

# Chapter 13 – Testing and Evidence

Results are quoted **per run, with their source**. They are not added together: different
runs collected different test sets on different days, and a sum would be meaningless.

| Category | What was tested | How | Latest reported result (source) | Proves | Does not prove |
|---|---|---|---|---|---|
| Backend integration suite | all integration code: security, exchange, adapters, transport, persistence, ordering, service, domain, observability, API | `pytest tests/integrations/` (24 files, 341 test functions before parameterisation) against disposable MySQL 8.4 databases | **517 collected: 516 passed, 1 skipped** — the skip is the vendor-sample contract test (no official samples) (`docs/HTNG_FIAS_OBSERVABILITY_IMPLEMENTATION_REPORT.md`, 20 Nov 2026) | the code behaves as designed on MySQL, including concurrency and failure paths | behaviour against any real vendor |
| Observability tests | overview figures, null rule, scope, sanitisation, search bounds | `test_observability.py` with MySQL variants | 22 passed; mutation checks (scope removed, 0 instead of null, unsanitised codes) were each caught (same report) | the KPIs are computed as documented and are facility-scoped | anything about live traffic |
| HTNG synthetic scenarios | inbound endpoint, SOAP 1.1/1.2, faults, auth, size limits, duplicates | certification harness, generic test XML profile | part of **PASS 40 · FAIL 0 · BLOCKED 5** (45 scenarios: 15 HTNG + 2 official BLOCKED, 15 FIAS + 3 official BLOCKED, 10 HMS) (`docs/HTNG_FIAS_CERTIFICATION_SPRINT_REPORT.md`; rerun in the observability sprint) | our pipeline handles our test messages | HTNG certification; the 2 official scenarios are BLOCKED for lack of vendor material |
| FIAS synthetic scenarios | TCP link, framing, reconnect, intake retry, parser with provisional spec | `FiasTestSimulator` on loopback, `TcpLink`, `LinkPump` | as above (3 official scenarios BLOCKED) | transport and parser mechanics | real FIAS framing, ACK, heartbeat or records (HF-06, HF-11) |
| HMS workflow tests | check-in / check-out through the real `stays_write` service | `test_e2e_hms_simulation.py`, `test_hms_domain_mysql.py`, HMS scenarios | 10 HMS scenarios PASS (harness) | domain adapter applies HMS rules and gates | production enablement (gate closed) |
| Frontend unit / render tests | presentation rules, RBAC, routing, every page's structure and requests, null rule, no internals, read-only DLQ, API client | `node --test` + esbuild + server-side rendering | **54 / 54 pass** (40 integration + 14 occupancy), run 20 Nov 2026 in the frontend container | the UI renders the real API contract correctly | visual layout (see next row) |
| Browser visual QA | 5 pages × 4 viewports, error and empty states, filters, keyboard, navigation | headless Edge 157 over DevTools against a local mock server with real fixtures; all other hosts blocked | 44 records, no page overflow, no internal terms on screen, null scenario 16 "Unavailable" and 0 zeros, no redrive buttons (20 Nov 2026 UI refactor run; `docs/HTNG_FIAS_DASHBOARD_VISUAL_QA_REPORT.md` for the earlier pass) | the UI is usable at the four sizes | real data volumes |
| Full-stack E2E | real build ↔ real FastAPI ↔ disposable MySQL with synthetic data | isolated Docker network with no route out; independent SQL oracle | **API 90 / 90; browser 56 / 56**; 45 backend tests passed (`docs/HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md`) | the dashboard shows exactly what the database holds, per facility | vendor traffic (data written through the repository) |
| Isolation checks | the E2E backend could not reach the real HMS DB or the internet | `isolation_check.py` inside the container | no default route, DNS for real hosts unresolvable, engine bound to the disposable DB (same report) | the tests did not touch production data | — |
| Baseline failures (not hidden) | — | — | frontend `tsc`: 6 pre-existing errors in 4 non-integration files; `eslint`: 3 errors, 7 warnings, all pre-existing; `tests/test_health_api.py`: 5 pre-existing failures (4 need the live HMS DB, 1 OpenAPI test on 14 non-integration routes); legacy HMS suite not re-run | — | — |

**Synthetic success is not vendor certification.** Every pass above uses messages we wrote
ourselves. Vendor validation remains PENDING until the vendor supplies specifications and a
test environment and the results are recorded with evidence.

# Chapter 14 – Current Issues and Inconsistencies

| # | Issue | Root cause | Impact | Evidence | Fixed? | Why open / owner |
|---|---|---|---|---|---|---|
| 1 | Invalid `direction` value breaks search | no CHECK constraint on `direction` / `protocol`; `_to_stored` raises on unknown enum values | one bad row is counted by the overview but makes `/observability/messages` and `/dlq` return 500 | E2E report, finding 1 | No | backend change not approved; belongs in the HF-39 DDL review (DBA, backend) |
| 2 | KPI overlap | Pending includes RETRY_WAIT; DLQ includes Failed | adding tiles double-counts | Chapter 3.6 | No (by design) | document / consider relabelling (product owner) |
| 3 | "Pending" detail wording | tile says "Waiting to be processed" but includes PROCESSING and RETRY_WAIT | understatement of scope | `OverviewView.tsx`, `PENDING_STATUSES` | No | UI wording decision (product owner) |
| 4 | "Backlog stalled" meaning | based only on the age of the oldest unfinished message; RETRY_WAIT and messages blocked behind a dead-lettered predecessor count; appears whenever no worker runs | can look like a crash when nothing is broken (every demo / test environment) | `_processing`, `blocking_statuses` | No | needs cross-process worker visibility (HF-25/26) |
| 5 | Worker heartbeat never visible | heartbeats are in-memory in the worker's process | "Worker activity: Not currently observable" always | `_heartbeats`, `service.py` | No | HF-25/26 hosting design |
| 6 | FIAS production wiring gap | no process creates a `TcpLink` / `TcpListenerLink`; transport registry empty | FIAS cannot receive anything; transport "Not observable" | `runtime.py`, `service.py` | No | needs HF-06 link rules, HF-11 spec, HF-24 network, HF-25/26 hosting |
| 7 | Outbound relay not started | `service.main()` passes `relay=None`; no sender / endpoint | outbox rows stay PENDING; "Outbound" is "queued", never "sent" | `service.py` | No | HF-24 vendor endpoint, HF-07 / HF-11 |
| 8 | Outbound detail limitation | dashboard search reads only the inbound table | outbound messages cannot be browsed; DLQ summary "Total in DLQ" may exceed the DLQ table total | Chapters 7, 8.3 | No | product decision |
| 9 | Missing message-id search | API has no id / reference parameter | support must filter by time and protocol | `observability_messages` | No | future enhancement |
| 10 | Unavailable metrics on the real HMS DB | integration tables absent (HF-39) | every count shows "Unavailable" against the dev / prod DB | `sql_models.py` docstring, `build_overview` | No | DBA approval HF-39 |
| 11 | In-process counters | intake rejections / auth failures reset on restart and are per process; FIAS not observable | partial, non-durable figures | `_intake_rejections` | No | metrics backend not approved |
| 12 | Synthetic certification not published | harness runs in CI / CLI only | readiness always "Not reported" | `_certification` | No | needs a reporting channel |
| 13 | HF-08 absent from the code register | `DECISIONS` mirrors part of the canonical register | none (missing = pending) but the mirror is incomplete | `domain/approvals.py` | No | update with the next approval change |
| 14 | Two "last successful processing" values | per-protocol = inbound only; Overview list header = inbound or outbound | values can differ | Chapter 3.5 D7 | No | wording decision |
| 15 | Timestamp example "25, 4:43 AM" | not reproducible from current source | — | Chapter 4.3 | — | NOT VERIFIED |
| 16 | Message Logs total vs Inbound KPI | logs default to 7 days; KPI has no window | numbers differ (demo 38 vs 42) | Chapter 3.7 | No (by design) | explain to users |
| 17 | Frontend / backend baselines | pre-existing TypeScript and lint errors outside Integrations; health-API test failures | none on Integrations | Chapter 13 | No | owning HMS teams |
| 18 | Vendor specification gaps | no HTNG WSDL / XSD / profile / security; no FIAS manual / records / link rules | adapters BLOCKED | Chapter 15 | No | vendor (after HF-03) |

# Chapter 15 – Pending Vendor and Production Readiness

**Register state (canonical `docs/HTNG_FIAS_DECISION_REGISTER.md`, 20 Nov 2026):** 27 rows
covering 28 decision IDs (HF-25 and HF-26 share a row) — **10 Open, 9 Awaiting Vendor
Confirmation, 7 Awaiting Business Approval, 1 Awaiting DBA Approval, 0 Approved**. External
prerequisites such as BLK-V7 are tracked separately in `docs/HTNG_FIAS_BLOCKER_REGISTER.md`.
The owner tracker lists 29 items (28 decisions + BLK-V7); no named owner is recorded yet.

| ID | Subject | Status | Why it is required | What depends on it |
|---|---|---|---|---|
| HF-03 | PMS vendor, product, version, hosting | Open | every vendor request needs a named counterpart | HF-04 … HF-09, HF-11, HF-24, BLK-V7 |
| HF-04 | Protocol per deployment | Awaiting Vendor Confirmation | decides FIAS, HTNG, REST or a combination | which adapter is completed; SOAP stack need |
| HF-05 | FIAS property-code case sensitivity | Awaiting Vendor Confirmation | mapping correctness | `FacilityResolver` policy (EXACT meanwhile); live-write gate |
| HF-06 | FIAS link rules: listening side, framing, encoding, ACK, heartbeat, reconnect, resync | Awaiting Vendor Confirmation | link layer cannot be finished without it | production framer, responder, heartbeat, `TcpLink` vs `TcpListenerLink` |
| HF-07 | HTNG version / profile / schema | Awaiting Vendor Confirmation | HTNG adapter is BLOCKED without a profile | every HTNG operation; XSD validation |
| HF-08 | HTNG security profile | Awaiting Vendor Confirmation | WS-Security / headers unknown | HTNG exposure |
| HF-09 | Vendor test environment and certification | Awaiting Vendor Confirmation | vendor validation needs a counterpart system | vendor-validation exit criteria |
| HF-11 | FIAS official specification and records | Awaiting Vendor Confirmation | parser is data-driven; `PRODUCTION_SPECIFICATION` is None | every FIAS record |
| HF-21 | Payload retention and encryption | Open | guest data in payloads | raw-wire storage (off), purge values, encryption |
| HF-24 | Network path and TLS | Awaiting Vendor Confirmation | connectivity and certificates | any vendor connection; outbound endpoints |
| HF-25 / HF-26 | Worker / link hosting and restart policy | Open | where the service and FIAS link run, and who owns the link | production wiring; cross-process monitoring |
| HF-39 | DBA / schema authorization | Awaiting DBA Approval | integration tables are not in the HMS DB | persistence, every dashboard count, XSD library approval |
| BLK-V7 | Vendor message volumes | Pending vendor documentation | rate-limit value | `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE` (stays unset) |

Also gating production in code: HF-01, HF-02, HF-19 (business) and HF-18 (integration actor)
for live HMS writes; HF-27 for the final retry / ordering policy.

> **Figure: Vendor validation roadmap (all steps PENDING; dependencies from the canonical register)** (diagram rendered in the PDF)

# Chapter 16 – Complete End-to-End Workflow

> **Figure: Inbound and outbound status lifecycle (core/lifecycle.py, sql_repository.py)** (diagram rendered in the PDF)

| Step | Component | Success path | Failure branch |
|---|---|---|---|
| 1 External vendor | PMS (not named) | sends a message | — (no vendor connected today) |
| 2 HTNG SOAP / FIAS TCP | `htng_inbound` / `TcpLink` + `LinkPump` | bytes received | switch off → 503; too large → 413; wrong media type → 415; FIAS: framing error counted |
| 3 Transport checks | router / framer | size, media type, rate limit | 413 / 415 / 429 |
| 4 Authentication | `ClientAuthenticator` | client resolved | 401 fault; counter `auth_failures` |
| 5 Protocol parser | `HTNGAdapter` / `FIASAdapter` `decode` | canonical message | **BLOCKED today** → rejected (`vendor_specification_missing`) |
| 6 Facility mapping | `FacilityResolver` | facility id | missing / disabled / ambiguous / scope smuggling → rejected (security) |
| 7 Validation | gateway | handler exists, idempotency key, envelope | rejected (`unsupported_message`, `idempotency_key_missing`, `envelope_invalid`) |
| 8 Idempotency | `accept` | new row | `DUPLICATE` (no row) or conflict (same key, different content) |
| 9 Persistence | `accept` | `PENDING` + payload + key | database error → transient rejection (FIAS pump retries the same frame) |
| 10 Worker processing | `InboundWorker.claim` | `PROCESSING`, lease | lease lost → result dropped, re-claimed later |
| 11 HMS workflow | `StayEventHandler` → `stays_write` | `SUCCEEDED` + outbox + audit in one commit | gate closed → `approval_required` → DEAD_LETTER; transient → RETRY_WAIT; exhausted → DEAD_LETTER |
| 12 Audit and observability | audit table, metrics, observability API | visible on the dashboard within one refresh | — |
| 13 Dashboard monitoring | React pages | counts, statuses, lists | null → "Unavailable"; API error → error state with Retry |

**Implemented framework versus vendor-connected execution.** Steps 2–13 exist as code and are
exercised by tests with synthetic messages. In a running environment today, step 5 rejects
every message for both protocols, the FIAS side of step 2 is not instantiated, and step 11 is
gated. No message from a vendor has ever passed through this pipeline.

# Chapter 17 – How to Explain This to Management

## 17.1 Executive summary

- **Problem.** Hotels run their own PMS. HMS must receive check-ins, check-outs and room events
  from it automatically, safely and per hotel.
- **Why two protocols.** The PMS vendor is not chosen yet. The two industry options are HTNG
  (web service) and FIAS (socket link); the platform supports either through one shared core.
- **Done.** Secure intake, per-hotel isolation, duplicate protection, guaranteed storage,
  automatic retry, a dead-letter queue with audited recovery, ordering per stay, gated HMS
  updates, and a five-page monitoring dashboard. All of it is tested with synthetic data.
- **Dashboard.** Overview (health and volumes), HTNG and FIAS pages (deep dive per
  protocol), Message Logs (search) and Failed Messages (investigation, read-only).
- **Not operational yet.** No vendor is connected; both protocol adapters are blocked until
  vendor specifications arrive; the integration tables await DBA approval; live HMS updates
  are switched off pending business approvals.
- **Status.** FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.

## 17.2 What each KPI tells management

| KPI | Plain meaning | Watch for |
|---|---|---|
| Inbound | messages received and stored | growth = traffic; flat = no traffic |
| Outbound | replies queued for vendors | stays "queued" until a vendor endpoint exists |
| Pending | not finished yet (includes being processed and waiting to retry) | a rising number means processing is not keeping up |
| Awaiting retry | temporary problems that will be retried | a high number suggests an HMS or network issue |
| Failed | gave up, needs a person | any non-zero value needs investigation |
| DLQ | all failed messages, both directions | same as Failed plus outbound |

Do not add the tiles together: Awaiting retry is part of Pending, and Failed is part of DLQ.

## 17.3 Required inputs and next milestones

1. **Name the PMS vendor and product (HF-03)** and choose the protocol (HF-04).
2. **Vendor documents:** HTNG schema, profile and security (HF-07, HF-08) or the FIAS manual,
   records and link rules (HF-11, HF-06, HF-05); a vendor test environment (HF-09) and message
   volumes (BLK-V7).
3. **DBA approval** of the integration tables (HF-39).
4. **Business approvals:** system of record, mapping ownership, facility isolation, integration
   user, retention (HF-01, HF-02, HF-19, HF-18, HF-21).
5. **Infrastructure:** network path and TLS (HF-24), hosting of the worker and FIAS link
   (HF-25/26).
6. Then: register the verified specification, run vendor validation with evidence, record the
   approvals in code, and switch on per environment.

## 17.4 Five-minute presentation script

> **Minute 1 — Why.** "Every hotel already runs a PMS. Today, check-ins and check-outs entered
> there do not reach HMS automatically. This project builds the bridge so HMS can react to them
> without double entry."
>
> **Minute 2 — How.** "The industry uses two kinds of connection: HTNG, a web service, and
> FIAS, a socket link. We do not yet know which our vendor will use, so we built one secure core
> with two plug-in adapters. Messages are authenticated, mapped to the right hotel, stored
> safely, processed in order, retried automatically if something is temporarily down, and
> parked for a person if they cannot be processed."
>
> **Minute 3 — The dashboard.** "Five pages. The Overview shows whether each protocol is ready
> and how many messages are received, pending, awaiting retry and failed. The HTNG and FIAS pages
> explain each protocol in detail. Message Logs lets support search messages. Failed Messages
> lists what needs attention. Every number comes straight from the stored messages for the
> user's own hotels, and anything we cannot measure is shown as unavailable, never as zero."
>
> **Minute 4 — Where we are.** "The foundation is implemented and tested end to end with
> synthetic messages, including an isolated full-stack test. What the dashboard shows today is
> honest: connections disabled or not observable, readiness not ready, vendor validation
> pending. No vendor is connected, and we have not claimed certification."
>
> **Minute 5 — What we need.** "Three things unblock the next phase: the vendor and protocol
> decision with the vendor's specifications and test environment; DBA approval for the
> integration tables; and the business approvals for live updates. With those, we complete the
> adapter for the chosen protocol, validate with the vendor, and go live hotel by hotel."

# Appendix A – Unverified Items and Evidence Gaps

| Item | Why not verified |
|---|---|
| The timestamp string "25, 4:43 AM" | not reproducible from the current formatting code |
| Dashboard figures against the real development HMS database | deliberately not contacted; inferred from code that every count would be "Unavailable" |
| How a production FIAS link would be bound to an integration client | not wired; only test code binds a link to a client |
| Any vendor behaviour (formats, ACK, heartbeat, security, volumes) | no vendor material in the repository |
| React Query behaviour beyond the configured options (window-focus refetch, background interval pause) | library defaults (TanStack Query v5), not overridden in `App.tsx`; not separately measured |
| Backend test results | quoted from the sprint reports listed in Chapter 13; the backend suite was not re-run for this document |

# Appendix B – Source Index

| Concern | Primary source |
|---|---|
| KPI and status calculation | `backend/app/integrations/observability.py` (`build_overview`, `_messages`, `_shared`, `_processing`, `_transport`, `_authentication`, `_vendor_validation`, `_readiness`) |
| SQL aggregates and search | `backend/app/integrations/processing/activity.py` (`activity_from_sql`, `search_sql`, `PENDING_STATUSES`, `MAX_PAGE_SIZE`, `MAX_OFFSET`) |
| Routes, windows, permissions | `backend/app/integrations/api/router.py` |
| Tables | `backend/app/integrations/processing/sql_models.py` |
| Status transitions | `backend/app/integrations/core/lifecycle.py`, `processing/sql_repository.py` |
| Retry | `backend/app/integrations/core/retry.py`, `processing/worker.py` |
| Switches | `backend/app/integrations/config.py` |
| Approvals | `backend/app/integrations/domain/approvals.py`, `docs/HTNG_FIAS_DECISION_REGISTER.md` |
| Frontend wording, null rule, time formats | `frontend/src/features/integrations/lib/presentation.ts` |
| Frontend queries and refresh | `frontend/src/lib/api/hooks.ts`, `frontend/src/App.tsx` |
| Pages and views | `frontend/src/features/integrations/pages/*`, `views/*` |
| Frontend tests | `frontend/src/features/integrations/__tests__/integrations.test.cjs` |
| Backend tests | `backend/tests/integrations/` |
