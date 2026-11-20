# HTNG / FIAS — Visual Monitoring Dashboard Report (2026-11-20)

Official status (unchanged): **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.**
Every number on the two dashboards is a server-side aggregate of stored integration rows. Nothing
is sampled, randomised, hard-coded or invented; anything the data cannot support is listed as
unavailable with its reason. No vendor is connected; all verification used synthetic data.

| Repository | Branch | HEAD | Staged / committed / pushed |
|---|---|---|---|
| `ACX_PLATFORM\ACX-Platform` | `feature/htng-fias-on-develop` | `46904fd` (unchanged) | nothing |

## A. Implementation summary

The HTNG Monitoring and FIAS Monitoring pages are now visual dashboards (same layout for both):

1. **Header + filters** — title, protocol (HTNG SOAP / FIAS TCP), current endpoint / link status
   badge, "Updated <time>" (server `generated_at` of the metrics), Refresh (refetches every query),
   existing 60 s auto-refresh. Filters: time range 1h · 24h · 7d · 30d, facility (only facilities in
   the user's scope). Both are kept in the URL (`?range=7d&facility=<uuid>`).
2. **KPI cards** (windowed) — 4 primary + 4 secondary.
3. **Charts** — traffic trend (line), processing-status distribution (donut), failures and retries
   (bars + failure-reason list), processing time (stats + trend line), message / record types
   (horizontal bars), and a "Not measured" panel.
4. **Transport and integration health** (current state, from the existing overview query) —
   status summary, connection, authentication and processing panels (kept from before; the FIAS
   connection panel now states "Connection history: Not recorded" and "ACK / heartbeat: Not
   implemented (HF-06)"; HTNG states "Availability history: Not recorded").
5. **Recent activity** — recent messages and failed messages tables, now restricted to the same
   window and facility, with links to Message Logs / Failed Messages.
6. Vendor validation and readiness panels (unchanged).

The old "Message statistics" block (retained-row totals) was replaced by the windowed KPIs; the
retained totals remain on the Integrations Overview page.

## B. Visual components

| Component | File | Data |
|---|---|---|
| Filter toolbar (range buttons with `aria-pressed`, facility select) | `pages/ProtocolMonitoring.tsx` | URL → query params |
| `KpiTile` ×8 (gained `format`, `emptyText`) | `components/KpiTile.tsx` | `kpis`, `latency` |
| `TrafficTrendChart` (Recharts LineChart) | `components/MonitoringCharts.tsx` | `series[].received / processed / outbound_created` |
| `StatusDonut` (PieChart + legend with count and %) | same | `status_distribution.inbound` |
| `ErrorRetryChart` (BarChart + reason list) | same | `series[].failed / retried_received`, `errors` |
| `LatencyPanel` (stats + LineChart) | same | `latency`, `series[].avg_latency_seconds` |
| `MessageTypeChart` (vertical BarChart) | same | `message_types` |
| `UnavailableMetrics` | same | `unavailable` |
| `MonitoringDashboard` (KPIs + chart grid; loading / error / not-available) | `views/MonitoringDashboard.tsx` | one metrics response |
| Existing tables | `components/MessageTables.tsx` | `/observability/messages`, `/observability/dlq` |

Charts use the already-installed **Recharts 2.15** (as the HMS dashboard does) and the HMS surface
tokens for axis, grid and tooltip colours in light and dark mode. Every chart has a visually hidden
data table with the exact plotted values (screen readers). Colours are semantic and consistent:
received blue, processed green, failed red, retry amber, outbound violet, queued grey.

## C. Backend changes

**One new read-only endpoint** (existing JWT, `facility_management` read, caller facility scope):

`GET /api/v1/integrations/observability/metrics?protocol=htng|fias&range=1h|24h|7d|30d&facility_id=<uuid>…&tz_offset_minutes=-840..840`

| Range | Window | Bucket | Points |
|---|---|---|---|
| 1h | 1 hour | 5 min | 12 |
| 24h | 24 hours | 1 hour | 24 |
| 7d | 7 days | 1 day (viewer-local) | 7 |
| 30d | 30 days | 1 day (viewer-local) | 30 |

The window is `[from, to)`; `to` is the end of the bucket containing "now" (the last bucket is
still filling). Bucket boundaries align to the viewer's local clock (`tz_offset_minutes`), so a
daily bar is a local day. Errors: 401 / 403 (no grant, or a facility outside the scope) / 422
(unknown protocol, range, malformed facility id, offset out of range); 405 for any write method.
If the integration tables cannot be read the response is 200 with `status: "not_available"` and
all figures `null` (never 0).

**Aggregation** (`processing/activity.py` `metrics_from_sql`; in-memory twin `metrics_from_memory`
for tests): GROUP BY / COUNT / SUM / AVG over the window, filtered by protocol and the effective
facility set; bucket index `FLOOR(TIMESTAMPDIFF(SECOND, :from, ts) / :bucket)`; two single-row
`ORDER BY duration LIMIT 1 OFFSET k` lookups for the percentiles. No message rows are returned.
Statements (inbound table `integration_inbound_messages`, outbox `integration_outbox_messages`):

1. cohort status counts and retry counts — `WHERE received_on IN window GROUP BY status`;
2. received / retried per bucket — `GROUP BY bucket(received_on)`;
3. processed per bucket + latency sum — `WHERE status='SUCCEEDED' AND completed_on IN window`;
4. failed per bucket — `WHERE status='DEAD_LETTER' AND completed_on IN window`;
5. latency count / avg / max, then p50 and p95 (nearest rank);
6. failure reasons — current `RETRY_WAIT` / `DEAD_LETTER` rows received in the window,
   `GROUP BY last_error_category, last_error_code` (top 10);
7. message types — `GROUP BY message_type` (top 10);
8. outbound status (by `created_on`), created and sent per bucket (`sent_on`).

The existing indexes `(facility_id, status, received_on)` (inbound) and
`(facility_id, status, created_on)` (outbox) serve the window filters. No new table, column, index
or migration.

Model: `observability.build_metrics` (KPIs, series, distribution, latency, errors, types,
`unavailable`). Route: `api/router.py` `observability_metrics`. Repository: `metrics()` on the
interface (non-abstract), in-memory and SQL implementations.

## D. Metric accuracy (every displayed value)

**Cohort** = messages (FIAS: records) **received in the window**, in their **current** status.
Identity: total = processed + failed + queued. One FIAS record that passes intake is stored as
exactly one message, so "records" = stored messages; TCP packets / frames are not counted (frames
that fail framing or parsing are never stored).

| Display | Source | Calculation |
|---|---|---|
| Total messages / records | cohort | count of rows |
| Successfully processed | cohort | status `SUCCEEDED` |
| Failed | cohort | status `DEAD_LETTER` |
| Queued (detail: awaiting retry) | cohort | `PENDING + PROCESSING + RETRY_WAIT` (detail: `RETRY_WAIT`) |
| Success rate | cohort | processed ÷ (processed + failed); **"No completed messages"** when the denominator is 0 (never 0 %) |
| Average processing time | `SUCCEEDED` rows **completed** in the window | mean of `completed_on − received_on` — intake to completion, **including queue wait**; "No completions" when none |
| Needed a retry (detail: extra attempts) | cohort | rows with `attempt_count > 1` (detail: Σ `attempt_count − 1`) |
| Outbound (detail: sent · queued · failed) | outbox rows **created** in the window | count; `SENT`; `PENDING + PROCESSING + RETRY_WAIT`; `DEAD_LETTER` |
| Traffic: Received | event | rows by `received_on` bucket |
| Traffic: Processed | event | `SUCCEEDED` rows by `completed_on` bucket |
| Traffic: Outbound queued | event | outbox rows by `created_on` bucket |
| Status donut | cohort | count and share per stored status; only statuses present are shown, labelled Processed / Pending / Processing / Awaiting retry / Failed |
| Failures bar | event | `DEAD_LETTER` rows by `completed_on` (= time of the last failed attempt) |
| Retried bar | cohort by arrival | rows with `attempt_count > 1` by `received_on` bucket |
| Failure reasons | cohort | current `RETRY_WAIT` / `DEAD_LETTER` rows grouped by error code / category (successful messages' errors are cleared on success) |
| Processing time stats | as average | avg, median (p50), 95th percentile (p95, nearest rank), slowest |
| Processing time trend | event | per completion bucket, mean duration; empty bucket = no point (not 0) |
| Message / record types | cohort | `GROUP BY message_type`, top 10, business labels |
| Updated | response | server `generated_at` |
| Health panels | `/observability/overview` | current state (unchanged; see earlier reports) |

Counts are over **retained rows**: if `INTEGRATION_RETENTION_DAYS` is set, purged `SUCCEEDED` /
`SENT` rows are no longer counted (the response carries `basis: retained_rows` and
`retention_days`). They are never lifetime totals.

## E. Testing results

| Suite | Result |
|---|---|
| Backend `tests/integrations` (disposable MySQL 8.4 + in-memory) | **579 passed, 3 skipped, 0 failed** (previous run 563 + 16 new). Skips: 2 SQL-only corruption tests on the memory variant, 1 vendor-sample test (no official samples) |
| New `tests/integrations/test_monitoring_metrics.py` | 16 passed (both stores): window alignment and local-day buckets; HTNG KPIs, distribution, success rate, errors, types; FIAS / HTNG isolation; facility scope and requested facility; empty scope; series buckets by event time; latency avg / p50 / p95 / max; date-range filtering (24h vs 7d); empty dataset (null rate and latency); store unavailable → null; unavailable-metric list per protocol; API 200 / 401 / 403 (no grant, foreign facility) / 422 ×5 / 405; protocol isolation and no sensitive fields over the API |
| `tests/test_health_api.py` | 24 passed, 5 failed — **identical to baseline** (4 need the live HMS DB; the OpenAPI test fails only on 14 pre-existing non-integration routes). The new path was added to its integration route list |
| Frontend `node --test` | **68 / 68** (59 before + 9 new): KPI values and labels, charts and hidden value tables, real statuses only, FIAS records + unavailable ACK / connection / timeout / parse metrics, empty state, not-available state (8 tiles unavailable, none 0), loading and error (503 → Retry), filters → exact server params (range, facility, window start), invalid range / out-of-scope facility, responsive grid classes, dark theme, plus the updated protocol-page structure tests |
| `tsc -p tsconfig.app.json --noEmit` | 6 errors — the same pre-existing 6, none in Integrations |
| `eslint .` | 3 errors, 7 warnings — identical to baseline, none in Integrations |
| `vite build` | success (only the pre-existing chunk-size warning) |
| `ruff` (integration code) | not re-run after the final edits — see §H |

Fixtures for the frontend tests (`metrics_htng`, `metrics_fias`, `metrics_empty`,
`metrics_unavailable`) were **generated by the real backend code** from the synthetic
`seed_world` data, not hand-written.

Defects found by tests / browser checks and fixed during the work:
* "Not measured" reasons first contained internal wording ("service process", "in-memory"); the
  no-internals test caught it; reworded.
* the time-zone offset was sent as `-0` in UTC; normalised.
* the hidden chart tables (class `sr-only` on a `<table>`) kept their content width and widened
  the page on phones (layout viewport 767 px at a 390 px screen); the class now sits on a wrapper
  `<div>`; a regression test was added.

## F. Responsive verification (headless Edge 157, real backend, demo data, `range=7d`)

| Width | HTNG | FIAS | Notes |
|---|---|---|---|
| 1440 | no overflow; 5 charts rendered (traffic / errors / latency / types 528 px, donut 220 px) | same | KPIs one row of 4 (×2), charts two columns |
| 1280 | no overflow; charts 448 px | same | |
| 768 | no overflow; charts 448 px | same | KPIs two columns, charts one column |
| 390 | no overflow; with the HMS sidebar collapsed (existing toggle): charts 254 px, single-column KPIs | same | with the sidebar expanded the existing HMS shell leaves ~150 px for content on every page (pre-existing shell behaviour) |
| Dark theme | 1440 and 390 checked | same | dark surface tokens, readable axes / tooltips |
| Filter click | clicking "24h" changed the URL and every KPI (22 → 21 messages) | — | |

Demo values cross-checked against the database: HTNG 7d = 22 messages (24 stored minus the two
synthetic messages that are 12 days old), 11 processed, 3 failed, 8 queued, success 78.6 %,
average 2.1 s. Screenshots: session scratchpad `op\shots\dash-*.png` (not committed).

## G. Git safety report

* Path `ACX_PLATFORM\ACX-Platform`, branch `feature/htng-fias-on-develop`, HEAD `46904fd`.
* Modified (inside the pre-existing untracked feature folders unless noted):
  backend `app/integrations/{observability.py, api/router.py, processing/activity.py,
  processing/repository.py, processing/sql_repository.py}`; `tests/test_health_api.py`
  (pre-existing modified file: one route added to the expected list);
  frontend `lib/api/integrations.ts`, `lib/api/hooks.ts` (pre-existing modified file: one hook
  appended), `features/integrations/{lib/presentation.ts, components/KpiTile.tsx,
  views/ProtocolView.tsx, pages/ProtocolMonitoring.tsx, __tests__/harness.tsx,
  __tests__/integrations.test.cjs, __tests__/observability-fixtures.json}`.
* Added: `backend/tests/integrations/test_monitoring_metrics.py`,
  `frontend/src/features/integrations/components/MonitoringCharts.tsx`,
  `frontend/src/features/integrations/views/MonitoringDashboard.tsx`, this report.
* Unchanged: `docker-compose.dev.yml`, `backend/app/api/v1/router.py`, the decision register,
  every other HMS module, the separate `HMS-Frontend\ACX-Platform` copy.
* No database, schema, migration or switch change; no DLQ redrive, no live HMS write, no protocol
  behaviour change. Nothing staged, committed or pushed.

## H. Remaining limitations (unavailable metrics and their dependency)

| Metric | Why unavailable | Needs |
|---|---|---|
| Retry attempts over time | individual attempts are not timestamped (only the final `attempt_count`) | an attempt history table (DBA, HF-39) |
| Worker processing time (start → finish) | the claim time is overwritten by each claim | a stored processing-start time (HF-39) |
| Rejected messages (auth / parse / validation / mapping) | rejected before storage; counters are per process and reset on restart | durable intake-rejection counts (HF-39) |
| Worker health | heartbeats live inside the background service | stored heartbeats (HF-39, HF-25/26) |
| HTNG endpoint availability history | not probed or recorded | an availability probe and store |
| FIAS connection history (connected / disconnected / reconnecting) | events not persisted; no FIAS link runs | HF-11, HF-06, HF-25/26 and a stored event log |
| FIAS ACK / NAK statistics, heartbeat | not implemented — rules unspecified | HF-06 |
| FIAS timeout statistics | counted only by a running link; none runs | HF-11, HF-06 |
| FIAS parse / framing failures | rejected before storage | as "rejected messages" |
| Direction / status filters on the dashboard | not added: the status donut already breaks the window down by status, and the dashboard search is inbound-only (outbound has its own series); Message Logs keeps the status filter | — |

Also: `ruff` was run on the integration code in the previous sprint; it was not re-run after this
sprint's final edits. Remaining vendor blockers are unchanged: HF-03, HF-04, HF-07, HF-08, HF-11,
HF-06, HF-05, HF-09, HF-24, BLK-V7; business HF-01, HF-02, HF-18, HF-19, HF-21, HF-27; DBA HF-39.

## I. Official project status

**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** No vendor certification or production
readiness is claimed. The demo figures above are synthetic.
