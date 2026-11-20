# HTNG / FIAS — Isolated Full-Stack End-to-End Verification Report (2026-11-20)

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. This sprint checks that the
dashboard works against the real backend code. It does not certify the integration with any
vendor.

## 1. Repository

| Item | Value |
|---|---|
| Path / branch | `ACX_PLATFORM\ACX-Platform`, `feature/htng-fias-on-develop` (verified, not switched); HEAD `46904fd` |
| Start / end | 52 status entries at start; at end the same 52 plus this report. **No repository file was changed** (all scripts lived in the session scratchpad). Nothing staged, committed or pushed. Checksums of `router.py`, `test_health_api.py` and `docker-compose.dev.yml` unchanged |
| Not used | The running dev backend (`acx-platform-backend-1`, real HMS database), the dev frontend (`:8080`), `HMS-Frontend\ACX-Platform` |

## 2. Isolated environment (created for this sprint, removed at the end)

```text
Edge (host, headless) --127.0.0.1:4318--> acx-e2e-web (Node, no deps)
                                             | serves the production build
                                             | forwards /api/v1 ONLY to acx-e2e-api:8000
          ================ acx-e2e-internal (Docker network, --internal: no gateway) ================
                                acx-e2e-api  (real FastAPI app, uvicorn, backend mounted read-only)
                                acx-e2e-mysql (MySQL 8.4, database acx_fullstack_e2e)
```

| Component | Identity / configuration |
|---|---|
| Disposable database | Container `acx-e2e-mysql`, server `@@hostname` = `af2f557a08dc`, MySQL 8.4.13, database `acx_fullstack_e2e`, user `e2e_app`, attached only to `acx-e2e-internal`, no published port |
| Backend | Container `acx-e2e-api`: the real app (`uvicorn app.main:app`), source mounted read-only. Runs from a snapshot image of the existing disposable test Python environment (used for its virtualenv only). The `MYSQL_*` variables point at `acx-e2e-mysql`. `OSS_ENABLED=false`. All `INTEGRATION_*` switches left at their defaults (off). A random JWT secret was used, and there is no `.env` file in `backend/` |
| Schema / seed | Repository tooling only: `tests/integrations/hms_schema_shim.create_hms_schema`, `seeds.run_seed`, `create_integration_tables` |
| Synthetic data | 2 facilities: the seeded "Ikanos Grand Chennai" (B) and a clone renamed "E2E Synthetic Facility" (A). 4 users: `e2e.viewer.a`, `e2e.viewer.b`, `e2e.operator` (A+B, write), `e2e.noaccess` (no `facility_management`), with bcrypt passwords. 2 integration clients (HTNG, FIAS) with mappings; the FIAS→B mapping is disabled. 42 inbound messages (all statuses, 4 of them 12 days old) and 3 outbox rows, created through the real `SqlIntegrationRepository`. Bodies contain only a marker string, no guest data |
| Frontend | The production build (`vite build`, `VITE_API_BASE_URL=/api/v1`, unchanged dashboard code) served by `acx-e2e-web` |
| Browser | Microsoft Edge 157.0.4341.60 headless, driven over DevTools from PowerShell (no packages). All traffic except `127.0.0.1:4318`, loopback included, went to a dead proxy |

Secrets were random and kept only in the scratchpad. They were deleted with the environment
and appear nowhere in this report.

## 3. Isolation verification (explicit)

Checked from **inside the backend container**, using the app's own settings and engine
(`isolation_check.py`):

| Check | Result |
|---|---|
| Routing table | only `172.20.0.0/16`; **no default route** |
| DNS: `acx-platform-backend-1`, `acx-platform-db-1`, `acx-int-mysql`, `host.docker.internal`, `example.com` | all **unresolvable** |
| TCP to Docker host `:8000`, `:5432`, `:3306`, `:8080`, host gateway `:8000`, internet `:443` | all **"Network is unreachable"** |
| `settings.MYSQL_HOST` / `MYSQL_DATABASE` | `acx-e2e-mysql` / `acx_fullstack_e2e` |
| Engine URL (password masked) | `mysql+pymysql://e2e_app:***@acx-e2e-mysql:3306/acx_fullstack_e2e` |
| `SELECT @@hostname, DATABASE()` through the **app's engine** | `af2f557a08dc` / `acx_fullstack_e2e`, which matches `docker inspect acx-e2e-mysql` |
| Integration switches | `ENABLED`, `LIVE_DOMAIN_WRITES`, `HTNG_INBOUND_ENABLED` and `SIMULATOR_ENABLED` are all false |

* **Seed guard.** The seed script refused to run unless the configured host and database were
  exactly the disposable ones, **and** the connected server's `@@hostname` matched the
  container. It passed.
* **Browser.** The network log shows hosts `127.0.0.1:4318` and `fonts.googleapis.com` only,
  and the fonts request was blocked.
* **Real backend.** Its log shows **0** HTTP requests and **0** reloads during the sprint.
* Because the backend has no route outside the internal subnet, the real HMS database host
  (wherever it is) cannot be reached from it.

## 4. Backend API results (real endpoints, independent SQL oracle)

`api_checks.py`: **90 checks, 90 passed.** Expected values were computed with raw SQL written
for the check, not with the repository code under test.

| Area | Verified |
|---|---|
| Authentication | 401 without a token on all 3 endpoints; wrong password → 401; **expired JWT → 401** |
| Authorization | user without `facility_management` → 403 on all 3; POST → 405 (read-only) |
| Overview | per facility × protocol, counts by status equal SQL (e.g. A/HTNG: SUCCEEDED 9, DEAD_LETTER 2, RETRY_WAIT 2, PENDING 2, PROCESSING 1); outbound totals; shared processed (A 15, B 9) |
| Overview readiness | vendor `pending`, production `not_ready`, synthetic `not_reported` |
| Overview, unobservable parts | FIAS transport `not_observable` with `null` connections; worker heartbeat not observed |
| Overview, persistence and auth | persistence `ok`; auth coverage equals SQL (A FIAS configured 1/1; B FIAS `not_configured`, because its mapping is disabled) |
| Messages | `Page` schema; item fields exactly as the contract; default 7-day total equals SQL (24 for A); newest-first ordering |
| Messages, filtering and paging | 4 pages × 7 rows = 28 distinct rows; each protocol × status filter (10 combinations) equals SQL with matching rows; facility filter; date window returns exactly the 4 twelve-day-old rows |
| Messages, validation | 422 for `page_size` 101, a naive datetime, a window over 31 days, an unknown status, an unknown protocol, offset over 10 000, and a bad UUID |
| Facility isolation | A→B filter 403; B→A filter 403; B sees only B rows; A's DLQ excludes B |
| DLQ | total equals SQL (A: 3); category and code present; viewer eligibility `{true,false,false}`; operator (write) `eligible=true`; protocol filter |
| No leakage | no payload marker, client secret, bcrypt hash, client code, `payload_hash`, idempotency key or lease owner in any response |
| Read-only | fingerprint of messages, outbox and audit rows identical before and after every GET |

## 5. Browser E2E results (real build ↔ real backend)

`browser.ps1`: **56 checks, 56 passed** (final run). On-screen values were compared with the
live API for the same session.

| Flow | Result |
|---|---|
| A. Login and navigation | Login through the real form (`/auth/login`); Integrations group with its 5 screens |
| B. Overview | HTNG and FIAS cards separate. Inbound, pending, failed and outbound figures equal the API (HTNG 16, FIAS 10 for A). FIAS transport "Not observable" in the neutral tone. No ready/validated badge; vendor pending. Authentication "Configured" from real client data. **Refresh** issues a new backend request |
| C/D. HTNG / FIAS | Recent messages equal the backend's first page (10 rows). 8 readiness dimensions. "All HTNG/FIAS messages" opens `?protocol=…`; every row is that protocol and the total equals the backend (14 / 10) |
| E. Message Logs (operator) | Facility options are exactly the operator's two facilities. Real clicks on Protocol FIAS, Status Succeeded and the Facility B name put all three in the URL. Every row matches all three filters, and the total equals the backend (3) |
| E. Message Logs, dates and paging | Date range returns exactly the 4 old rows. Rows per page 10, then Next: `page=2`, rows equal the backend's page 2, no overlap |
| E. Message Logs, invalid input | Invalid URL filters are dropped, not sent |
| F. DLQ | Operator: 5 rows, all "Eligible". Viewer A: 3 rows, facility A only, "Needs write access". Category and code from the backend. **No redrive action** |
| Isolation (UI) | Viewer B opening `?facility=<A>`: **0** requests with facility A were sent; all rows are B. B's overview figures; B's FIAS readiness "Not configured" |
| Isolation (no leakage) | No marker, secret or hash anywhere in the rendered app |
| RBAC (UI) | No-access user: no Integrations nav; direct `/integrations/dlq` shows "Access denied"; **no** observability request |
| Expired session | Expired token → real 401 → login page |

### Failure and recovery (real stack)

| Scenario | How it was produced | UI result |
|---|---|---|
| Backend unavailable | `docker stop acx-e2e-api`, then Refresh | During React Query's retries the last data stays visible with Refresh disabled. Then "Could not load this data" with Retry. After restart, **Retry recovers** |
| Database unavailable | `docker stop acx-e2e-mysql`, then Refresh | "Service unavailable — The HMS database is unavailable" with Retry; no metrics shown. After restart, recovers |
| Permission revoked mid-session | Viewer A's grant set to read=0 in the DB, then Refresh | Real 403: "Access denied", no Retry |
| Genuine 500 / partial failure | One corrupt row (invalid `direction`) inserted | Real 500 on search. The HTNG page shows its statistics and readiness, while the recent list shows "Could not load this data" with Retry |
| Missing metrics | Integration tables renamed (the pre-HF-39 state) | Overview: 19 "Data unavailable" markers and **zero zeros**. Logs: "Service unavailable" (real 503) |
| Empty database | Integration rows removed | Measured zeros, "None recorded", processing "Idle"; logs and DLQ empty states. Data restored and verified afterwards |
| Invalid filters / unauthorized facility / expired auth | See above | Correct |

Console: **no JavaScript exceptions.** Every error-level entry is the HTTP status of a deliberate
scenario, the blocked Google Fonts request, or the header's pre-existing `/notifications` 403.

## 6. Findings

| # | Finding | Where | Action |
|---|---|---|---|
| 1 | A row with an invalid `direction` is **counted** by the overview aggregates but makes `/messages` and `/dlq` return **500**. The `direction` and `protocol` columns have no CHECK constraint, and `_to_stored` raises on unknown enum values | backend `processing/sql_models.py`, `sql_repository._to_stored` | **Reported, not changed** (backend changes not approved). Suggest a CHECK constraint in the candidate DDL (HF-39) or tolerant mapping |
| 2 | For the production (BLOCKED) HTNG/FIAS adapters the requirements table shows direction "Unspecified": the blocked adapters declare no message types | real contract value; dashboard `_directions` | Accurate; cosmetic only |
| 3 | While the backend is unreachable, a refresh keeps the last data visible until React Query's retries finish (up to about 45 s through the proxy), then shows the error | React Query default behaviour | Acceptable; noted |
| 4 | The header requests `/notifications` without the `dashboard` grant (403) | `AppHeader.tsx` (pre-existing) | Not changed |

Test-script defects found and fixed during the sprint, all in scratchpad scripts and not in the
application:
* a `facility_uid` longer than the 3-character column;
* use of a detached ORM object;
* the JWT library (the app uses `python-jose`);
* a PowerShell case-insensitive variable clash;
* a native stderr warning aborting the run;
* two over-strict checks (sidebar sub-links are only rendered when the group is expanded, and a
  refresh wait that was too short);
* one meaningless always-pass check, removed.

No application defect required a code change in this sprint.

## 7. Tests, lint and build (compared with the baseline)

| Check | Result |
|---|---|
| Backend `tests/integrations/test_observability.py`, `test_api.py`, `test_health_view.py` (existing disposable test MySQL) | **45 passed** |
| Full-stack API checks | **90/90** |
| Full-stack browser checks | **56/56** |
| Frontend `node --test` | **49/49** (baseline 49) |
| `tsc -p tsconfig.app.json --noEmit` | **6 errors**, the same pre-existing 6 in 4 non-integration files |
| `eslint .` | **identical** to the baseline (3 errors, 7 warnings, all pre-existing) |
| `vite build` | **success** |

Existing baseline failures (unchanged, not hidden):
* the frontend's 6 type errors and 3 lint errors noted above;
* `tests/test_health_api.py` has 5 pre-existing failures (4 need a live HMS database; 1 OpenAPI
  test fails on 14 non-integration routes);
* the legacy HMS suite was not re-run.

## 8. Evidence

Kept in the session scratchpad and **not committed**
(`C:\Users\Bhuvii\AppData\Local\Temp\claude\d8827ef51840337f\aa708178-8736-4f51-8711-c4cd8145e15f\scratchpad\e2e\`):
* Scripts: `seed_e2e.py`, `isolation_check.py`, `api_checks.py`, `webserver.cjs`, `cdp.ps1`,
  `browser.ps1`.
* Results: `out\isolation.json`, `out\api_results.json`, `out\browser_results.json`,
  `out\seed.json`, `out\web-requests.jsonl`.
* `shots\` — 17 screenshots: overview (viewer A and B), HTNG, FIAS, filtered logs, DLQ
  (operator and viewer), no-access, expired session, backend down, database down, permission
  revoked, partial 500, tables missing (overview and logs), empty overview and DLQ.

## 9. Teardown

`acx-e2e-web`, `acx-e2e-api` and `acx-e2e-mysql` (with their volume), the network
`acx-e2e-internal` and the image `acx-e2e-py:snapshot` were removed. The secret files were
deleted. Pre-existing containers (`acx-int-*`, `acx-platform-*`) were left untouched.

## 10. Remaining blockers (unchanged)

* **Vendor:** FIAS HF-05, HF-06, HF-11; HTNG HF-07, HF-08 (HF-08 is not in the code register);
  official samples; vendor test environment (HF-09).
* **Business:** HF-01, HF-02, HF-18, HF-19, HF-21, HF-27.
* **DBA:** HF-39 (integration tables, RBAC module); finding 1 above belongs in that review.
* **Ops:** HF-25/26 (cross-process worker and link visibility).
* **Certification:** no runtime channel for publishing harness results.

## 11. Limitations

* Only Edge (Chromium) at 1440×900; responsive behaviour was covered by the previous visual QA
  sprint (mocked data).
* The synthetic data was written through the repository, not through live HTNG/FIAS traffic:
  the production adapters are correctly BLOCKED and no protocol switch was enabled.
* The "empty database" scenario deleted payload and idempotency rows, which were not restored.
  The environment was then destroyed, so this had no lasting effect.
