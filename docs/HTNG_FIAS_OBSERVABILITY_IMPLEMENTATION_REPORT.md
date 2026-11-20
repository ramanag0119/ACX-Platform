# HTNG / FIAS — Observability & Dashboard API Sprint Report (2026-11-20)

Branch `feature/htng-fias-on-develop` (uncommitted). Status unchanged:
**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. HTNG/FIAS vendor integration is **not**
complete; nothing in this sprint is vendor evidence.

Working copy: `ACX_PLATFORM\ACX-Platform`. The brief named `HMS-Frontend\ACX-Platform`, but that
copy is on a different branch (`feature/htng&fias-integrate`) with a separate integration
codebase. It was not touched.

## 1. What already existed

Readiness, adapters, messages (status + limit), masked message detail, DLQ (limit only), outbox,
in-process metrics, per-facility health (counts, backlog age, latency), audit, mappings, and
audited redrive. All are RBAC (`facility_management`) and facility scoped. See
`HTNG_FIAS_OBSERVABILITY_API_DESIGN.md` §1 for the full inventory. None of these were changed.

## 2. What was implemented

| Item | File |
|---|---|
| Per-protocol durable activity (counts by status in and out, last received/succeeded/sent, oldest pending, retries, latest failure) and bounded search, both repository backends | `app/integrations/processing/activity.py`; `repository.py`, `sql_repository.py` (2 new read methods each) |
| Dashboard information model: per-protocol entries, shared overview, 8 readiness dimensions, sanitising | `app/integrations/observability.py` |
| Per-protocol authentication coverage (single SQL aggregate, scoped) | `app/integrations/admin.py` `auth_coverage` |
| Explicit transport → protocol tagging (no guessing from names) | `app/integrations/runtime.py` `transport_protocols` |
| `GET /integrations/observability/overview`, `/messages`, `/dlq` | `app/integrations/api/router.py` |
| Tests (22) | `tests/integrations/test_observability.py` |
| OpenAPI path list: appended the 3 new paths and the 3 integration paths that were already served but missing (`facilities/health`, `mappings`, `mappings/{id}`); append-only, backup kept | `tests/test_health_api.py` |

No migration, no schema change, no write or redrive action, no retry/ordering change, no
protocol change, no switch changed, no frontend change.

## 3. Tests and checks (run this sprint, Docker, disposable MySQL 8.4)

| Check | Result |
|---|---|
| `pytest tests/integrations/test_observability.py` with `INTEGRATION_TEST_MYSQL_URL` | 22 passed (MySQL variants ran, 0 skipped) |
| Mutation checks: SQL search without facility scope / missing data reported as 0 / unsanitised error codes | each caught (1, 1, 2 failures); originals restored and checksum-verified |
| Full integration suite (both disposable DBs) | **517 collected: 516 passed, 1 skipped** (vendor sample contract test: no official samples) |
| Certification harness `run --label observability-sprint` (HMS DB set) | PASS 40 · FAIL 0 · BLOCKED 5 · NOT RUN 0 (unchanged) |
| `tests/test_health_api.py` | 24 passed, 5 failed. **The original file fails the same 5** (4 `/health/db` tests need the live HMS DB; the OpenAPI test fails on 14 non-integration routes). Integration paths now match: 0 integration extras, 0 missing |
| ruff E,F,W,B,S (established ignores) on `app/integrations`, `tests/integrations`, `migrations/drafts` | all checks passed |
| ruff with UP added | 11 style findings, all in lines that predate this sprint; new files clean |
| gitleaks v8.21.2 (read-only, redacted) on `app/integrations` (56 files), `tests/integrations` (37), `test_health_api.py` | no leaks found |
| Legacy HMS suite | not re-run this sprint |

What the tests cover: HTNG/FIAS overview responses; null-not-zero on database failure;
FIAS link status only from tagged transports (connected/degraded/probe failure); worker
heartbeat scope; counts; pagination stability, ordering and filters; date-window, page and
offset bounds; facility isolation in overview, search and DLQ; 401 and 403; secret and PII
exclusion (guest name, e-mail, card number, client code, client secret, payload hash, keys);
DLQ fields and redrive eligibility by grant; read-only guarantee (state, audit, outbox and
counters unchanged; POST/DELETE → 405); readiness classification; synthetic PASS never making
a vendor validated; an approval without evidence staying pending; `test_only` adapters never
validated; the real register never being production-ready.

A test-only "approved" register is built inside one test to prove the positive path exists. The
real register in `domain/approvals.py` is unchanged; nothing is approved.

## 4. Process note (corrected during the sprint)

The first gitleaks command had an unexpanded path variable. Docker then created an empty
`backend${d}/` mount directory, and the two "no leaks" results scanned that empty directory.
Those results were discarded. The two empty directories (`backend${d`, `backend${d/}`, no files)
were removed and the scans re-run against the real paths (results above). A temporary script
used to capture the response examples was deleted.

## 5. Missing telemetry

Worker health and FIAS link state are not visible from the API process. Totals are over retained
rows only. Rejected intake is counted per process only. There is no runtime source for synthetic
certification, so production readiness is unreachable by design until one exists. See design §7
for what each gap needs.

## 6. Blockers (unchanged)

* **Vendor:** HF-05, HF-06, HF-11 (FIAS); HF-07, HF-08 (HTNG; HF-08 is also absent from the code
  register); official samples; test environment (HF-09).
* **Business:** HF-01, HF-02, HF-18, HF-19, HF-21; HF-27 (retry/ordering).
* **DBA:** HF-39 (integration tables; also an RBAC module for integrations); two Alembic heads.
* **Ops/infra:** HF-25/26 (service hosting, link ownership) for cross-process health.

## 7. Git state at end of sprint

* Branch `feature/htng-fias-on-develop`; nothing staged, committed or pushed.
* Tracked modifications: `backend/app/api/v1/router.py` (unchanged this sprint, sha256 `f5a865e0…`)
  and `backend/tests/test_health_api.py` (append-only, +8 lines; sha256 now `3f1fa713…`; pre-sprint
  copy in the session scratchpad).
* Untracked (as before): `backend/app/integrations/`, `backend/migrations/drafts/`,
  `backend/tests/integrations/`, `docker-compose.dev.yml` (sha256 `37cb9f3b…`, unchanged), `docs/`.
