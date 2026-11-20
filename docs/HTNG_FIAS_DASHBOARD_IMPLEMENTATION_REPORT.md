# HTNG / FIAS — Integration Management Dashboard: Implementation Report (2026-11-20)

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. The dashboard monitors the
integration; it does not certify it. HTNG and FIAS are **not** vendor-certified and **not**
production-ready.

## 1. Repository

| Item | Value |
|---|---|
| Path | `ACX_PLATFORM\ACX-Platform` (git root verified) |
| Branch | `feature/htng-fias-on-develop` (verified; not switched) |
| HEAD | `46904fd1` (unchanged; nothing committed) |
| Initial state | 2 tracked modifications (`backend/app/api/v1/router.py`, `backend/tests/test_health_api.py`), untracked backend integration work, `docker-compose.dev.yml`, `docs/`; **no frontend changes**; nothing staged |
| Not touched | `HMS-Frontend\ACX-Platform` (branch `feature/htng&fias-integrate`) |

## 2. Frontend architecture discovered

| Area | Finding | Reused as |
|---|---|---|
| Stack | React 18.3, Vite 5, TypeScript 5.8, Tailwind 3 + shadcn/Radix, TanStack Query 5.83, react-router-dom 6 | — |
| Root | `frontend/src`; routes in `App.tsx` under `<ProtectedRoute><AppLayout/>` | 5 routes added inside the protected layout |
| Navigation | `components/layout/AppSidebar.tsx` grouped items filtered through `moduleForPath` + `canRead` | "Integrations" group, 5 sub-items |
| RBAC | `core/rbac/modules.ts` `ROUTE_MODULE` (longest prefix) + `ModuleGuard` in `AppLayout` | `"/integrations": "facility_management"` |
| Auth / token | `AuthContext` (`/auth/me`, `canRead`/`canWrite`, `user.facility_ids`); `lib/api/client.ts` bearer token, single `ApiError`, 401 → global sign-out event | unchanged, used as-is |
| API layer | `lib/api/client.ts` (one client), feature modules (`reports.ts`), hooks in `lib/api/hooks.ts` via `useApiQuery` (retry off for 4xx, 30 s stale) | new `lib/api/integrations.ts`; 3 hooks appended |
| Facility context | No global facility selector; scope = `user.facility_ids`; names from `GET /facilities` (same `facility_management` grant) | `useFacilityScope` |
| States | `core/components/DataState.tsx` (loading skeleton, empty, `ErrorState` for 401/403/503/network) | used everywhere, plus a Retry wrapper |
| Pagination | HMS `Page{items,page,page_size,total}`; `core/components/TablePagination.tsx` | used for logs and DLQ |
| Layout | `PageHeader`, `Card`, `Table`, `Badge` tokens (`success`/`warning`/`destructive`/`muted`) | used; no new design tokens |
| Tests | No Vitest/Jest/RTL. One test: `node:test` + esbuild (`occupancy/__tests__/roomConditions.test.cjs`) | same convention; **no new dependency** |

## 3. Navigation and routes

Sidebar group **Integrations** (shown only with `facility_management` read):

| Route | Page |
|---|---|
| `/integrations` | Integration Overview |
| `/integrations/htng` | HTNG Monitoring |
| `/integrations/fias` | FIAS Monitoring |
| `/integrations/messages` | Message Logs (filters in the URL, e.g. `?protocol=htng`) |
| `/integrations/dlq` | Failed Messages / DLQ |

No new permission model: the route map entry uses the grant the backend enforces.

## 4. Files

New:
* `src/lib/api/integrations.ts` (contract types + 3 endpoint functions)
* `src/features/integrations/lib/presentation.ts` (pure rules) and `lib/hooks.ts`
* `src/features/integrations/components/`: `StatusBadge`, `Metric`, `ProtocolCard`,
  `ReadinessPanel`, `MessageTables`, `MessageFilterBar`, `QueryErrorState`
* `src/features/integrations/views/`: `OverviewView`, `ProtocolView`
* `src/features/integrations/pages/`: `IntegrationOverview`, `ProtocolMonitoring` (HTNG/FIAS),
  `MessageLogs`, `DeadLetters`
* `src/features/integrations/__tests__/`: `integrations.test.cjs`, `harness.tsx` (test-only),
  `observability-fixtures.json`

Changed (additions only, 66 lines, 0 removed): `App.tsx` (+11), `AppSidebar.tsx` (+21),
`core/rbac/modules.ts` (+5), `lib/api/hooks.ts` (+29).

## 5. API integration and contracts used

| Endpoint | Hook | Use |
|---|---|---|
| `GET /api/v1/integrations/observability/overview` | `useIntegrationOverview` (one cached query for Overview/HTNG/FIAS; refetch 60 s; manual Refresh) | cards, summary, readiness |
| `GET /api/v1/integrations/observability/messages` | `useIntegrationMessages(params)` | logs; HTNG/FIAS recent (10 rows) |
| `GET /api/v1/integrations/observability/dlq` | `useIntegrationDeadLetters(params)` | DLQ page; HTNG/FIAS failed (5 rows) |

The types in `lib/api/integrations.ts` were transcribed from `backend/app/integrations/observability.py`
and `api/router.py`. The test fixtures are **real backend output** from the synthetic test
environment: the measured overview, the database-unavailable overview, tagged FIAS links, and a
messages page and a DLQ page. No response is hardcoded in production code. No backend contract
was changed.

Query parameters sent: `protocol`, `status` (logs only), `facility_id`, `received_from`,
`received_to` (ISO instants), `page`, `page_size` (≤ 100). Pagination is server-side only; one
page is in the browser at a time. The backend's order (newest received first) is stable.

### Contract gaps (documented, backend not modified)

| Gap | Effect in the UI |
|---|---|
| No message-ID search parameter | Not offered |
| Message search covers inbound messages only (no outbound list in the observability API) | "Recent inbound messages"; outbound shown as counts only |
| No per-protocol "retry count" field; available: `retry_wait`, `retried_messages`, `extra_attempts` | Shown as "Awaiting retry / retried" |
| No total-messages field in the shared summary | "Total inbound (retained)" = HTNG + FIAS inbound totals; unavailable if either is unavailable |
| No live certification-results source | Synthetic certification shows **Not available** |
| Message detail (`GET /messages/{id}`) returns a masked body | Not used (no payload display) |
| Worker heartbeat and FIAS link state are not visible to the API process | Shown as **Not observable** (unknown, not down) |

## 6. RBAC and facility scope

* The route guard (`ModuleGuard`) and the sidebar both use `facility_management` read. A denied
  user sees the standard "Access denied" page, and **no integration request is issued**
  (tested). The backend still enforces 401/403 on every call.
* Facility filter options are only the user's `facility_ids`. A facility in the URL that is
  outside that scope is dropped before the request. All figures arrive already scoped by the
  backend.
* 401 → the existing global sign-out. 403 → "Access denied" with no retry. 503 / network →
  "Service unavailable" with **Retry**.
* DLQ is read-only: redrive eligibility is displayed as reported. The existing audited
  `POST /integrations/messages/{id}/redrive` is **not exposed** (it exists and needs
  `facility_management` write, but was not approved for this screen).

## 7. Status accuracy

* `null` metrics show **Data unavailable** / **Not observable**, with the backend reason as a
  tooltip, never 0. `not_observable` uses a neutral dashed "unknown" style, never the failure
  colour.
* Eight readiness dimensions are shown separately: transport, authentication, processing,
  synthetic certification, official vendor validation, business approval, DBA/schema approval
  and production readiness. Decision IDs are shown verbatim. Nothing on screen can change an
  approval.
* Counts are labelled as retained rows, not lifetime totals.

## 8. Verification (run this sprint, in the existing frontend container, Node 20)

| Check | Baseline (before) | After |
|---|---|---|
| Tests `node --test` (existing + new) | 14/14 pass | **48/48 pass** (14 existing + 34 new) |
| Mutation checks (null shown as 0 / RBAC map removed / unobservable shown as failure / scope bypass) | — | each caught (2, 3, 2, 1 failures); originals restored and checksum-verified |
| Type check `tsc -p tsconfig.app.json --noEmit` | 6 errors in 4 files | **same 6 errors, same 4 files** (FacilityManagement, JobOrder, ReportFilters, ReportSummaryCards); 0 in new or changed files |
| Lint `eslint .` | 3 errors, 7 warnings | **identical list** (all in Reservations, CheckIn, ServicesSetup, Events, Holidays, ServiceTracking); 0 in new or changed files |
| Production build `vite build` (to `/tmp`, not the repo) | success | **success** (2618 modules); bundle contains the pages, not the test harness |
| gitleaks (read-only) on `features/integrations` (18 files) and `lib/api/integrations.ts` | — | no leaks found |

The 34 new tests cover:
* Presentation rules, and navigation and route registration.
* Sidebar visibility with and without the grant, and route denial with no requests issued.
* The overview contract, with both protocol cards rendered independently.
* Status accuracy (not observable, vendor pending, never production-ready) and null-not-zero
  over the real "database unavailable" response.
* The HTNG and FIAS pages, including unobservable and tagged-link FIAS.
* Message filters and page sent to the server, facility-scope restriction, server totals, and
  empty and date-error states.
* DLQ rendering, redrive wording, and no redrive action.
* Loading, empty, 401, 403, 503 and network states.
* API client URLs, bearer token, 401 sign-out and 403.
* Responsive class checks, and no payload, secret or guest-data strings in rendered output.

**Page evidence:** pages are rendered by the tests with React's server renderer (real
components, real backend fixtures). No screenshots were taken. The running dev stack's backend
uses the real HMS database, which this sprint must not contact, and no browser automation is
installed. Rendered layout in a browser has therefore not been visually verified. Responsive
behaviour is verified at the class level only (`grid-cols-1 … xl:grid-cols-2`, horizontally
scrollable tables).

## 9. Known limitations

* No visual / browser-level verification (see above).
* Facility names depend on `GET /facilities`; if it fails, facilities show as "Facility <id prefix>".
* Filters are single-select per field (the shared API client sends one value per parameter;
  the backend accepts repeats).
* Overview polling is 60 s; there is no push channel.

## 10. Remaining blockers (unchanged)

* **Vendor:** FIAS HF-05, HF-06, HF-11; HTNG HF-07, HF-08 (HF-08 is also absent from the code
  register); official samples; vendor test environment (HF-09).
* **Business:** HF-01, HF-02, HF-18, HF-19, HF-21; HF-27.
* **DBA:** HF-39 (integration tables; an integration RBAC module).
* **Ops:** HF-25/26 (cross-process worker and link health).
* **Certification:** an approved channel for publishing harness results.

## 11. Git state at end of sprint

Branch `feature/htng-fias-on-develop`; HEAD unchanged; **nothing staged, committed or pushed**.
New this sprint:
* Tracked modifications: `frontend/src/App.tsx`, `components/layout/AppSidebar.tsx`,
  `core/rbac/modules.ts`, `lib/api/hooks.ts`.
* Untracked: `frontend/src/features/integrations/`, `frontend/src/lib/api/integrations.ts`, and
  this report.

All pre-existing changes are unchanged. Checksums verified for `backend/app/api/v1/router.py`,
`backend/tests/test_health_api.py` and `docker-compose.dev.yml`.
