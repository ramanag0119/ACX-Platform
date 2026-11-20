# HTNG / FIAS — Round 3 Report: Hardening, Vendor Readiness, Approval Packages

Date 2026-11-20 · branch `feature/htng-fias-on-develop` (from `origin/develop` @ `46904fd`),
uncommitted · status **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**.

## 1. The "384/385" result

There was **no failing test**. The previous run was 384 passed + 1 skipped: the vendor-sample
harness skips with an explicit reason because no official samples exist. Re-run today: the
skip and its reason are unchanged and correct.

## 2. Defects found and fixed in round 3

| ID | Defect | Fix | Regression tests |
|---|---|---|---|
| D4 | **Message loss**: a DB outage during TCP intake turned a valid frame into a "rejected" result that was dropped; an exception in intake killed the pump | `IntakeResult.retryable`; `LinkPump` retries the same frame with bounded back-off, keeps order, stops reading meanwhile; no reply until accepted; on stop the frame stays unacknowledged | `test_hardening.py` (4) |
| D5 | DB failure while recording a failure aborted the rest of the worker batch | caught, counted (`failure_unrecorded`); message recovers by lease expiry | `test_worker_continues_batch_when_failure_cannot_be_recorded` |
| D6 | Inconsistent settings accepted (retry max < base, HTNG inbound without master switch, live writes without actor, non-UUID actor) | `model_validator` on `IntegrationSettings` | `test_inconsistent_settings_rejected` |

Also corrected: the candidate-migration delta is **3 columns + 1 index**, not "eight" (an
earlier summary error); the stale HF-27 row in the decision register.

## 3. New capability

* **Real HMS business integration test** (`test_hms_domain_mysql.py`): the HMS schema is built
  on a disposable MySQL with a test-only shim and seeded with the repository's own seed; the
  worker drives the **real** `stays_write.check_in/check_out` through the fenced savepoint
  transaction. Proven: in-order processing, HMS-rule rejection of check-out-before-check-in,
  repeated check-in = no-op with audit, unknown stay = retry, **lost lease rolls back the real
  HMS commit**, production approval register still blocks.
* **HMS schema MySQL incompatibility inventory**: 19 objects (14 × 1067, 4 × 3152, 1 × 1101)
  — `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` §4.
* **Legacy HMS suite now runs on a seeded disposable copy** (previously 1,265 environment
  failures): 1,250 passed / 78 failed / 1 skipped, identical ID set with and without this work.
* **Contract harness as a library + CLI** (`app/integrations/contracts.py`): manifest
  validation, production-adapter runs, pass/fail/blocked/invalid per case, JSON/Markdown report,
  FIAS ACK expectations reported as blocked (HF-06).

## 4. Test results (executed 2026-11-20, Docker, disposable MySQL 8.4)

| Suite | Collected | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|---|
| Integration (memory + `acx_integration_test` + seeded `acx_hms_domain_e2e`) | 406 | **405** | 0 | 1 | skip = no official vendor samples |
| Legacy HMS, seeded disposable DB, pristine `HEAD` | 1,329 | 1,250 | 78 | 1 | pre-existing |
| Legacy HMS, seeded disposable DB, with changes | 1,329 | 1,250 | 78 | 1 | identical 78 IDs |
| ruff (E,F,W,B,S) | — | clean | — | — | |
| Type checks | — | — | — | — | **not executed**: no mypy/pyright configuration in the repository |
| Secret scan (gitleaks) | — | — | — | — | not executed in round 3; **executed in round 4** — see `HTNG_FIAS_SECRET_SCAN_REPORT.md` |
| Alembic heads | — | unchanged (`a3f1c8e2d904`, `b3c4d5e6f7a8`) | | | |

Per-file integration counts: admin 12, api 16, core 35, domain 25, end_to_end 8, exchange 28,
fias_adapter 40, hardening 13, health_view 7, hms_domain_mysql 4, htng_adapter 39,
migration_candidate 3, mysql_persistence 18, ordering 19, repository_contract 40,
security 52, service 11, transport_server 6, transport_tcp 25, vendor_contracts 5.

## 5. Deliverables

`HTNG_FIAS_DBA_APPROVAL_PACKAGE.md`, `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` (incl. FIAS/HTNG
traceability), `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md`,
`HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md`, `HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md`, this report.

## 6. Git change management (nothing done; proposal only)

* Branch `feature/htng-fias-on-develop`; other branches unchanged
  (`feature/htng&fias-integration` = `45ac98a`, `feature/htng&fias` = `46904fd`).
* Working tree: 2 modified tracked files (+20 lines), integration package, tests, drafts, docs.
* **Git identity required** (not configured, local or global):
  `git config user.name "<name>"` and `git config user.email "<email>"` — by the user.
* Exclude from commits: `docker-compose.dev.yml` (pre-existing, not ours, contains a dev
  password) and `docs/HTNG-FIAS/` (earlier implementation's reports) unless the owner decides.
* Run a secret scan on the staged diff before the first commit.
* Proposed commit groups:
  1. `feat(integrations): core contracts, security, exchange gateway` — `core/`, `security/`, `exchange/`, `metrics.py`, `config.py`
  2. `feat(integrations): durable processing, MySQL candidate schema, worker, service` — `processing/`, `service.py`, `admin.py`, `cli.py`, `runtime.py`, `migrations/drafts/`
  3. `feat(integrations): transports and protocol adapters (spec-driven, production blocked)` — `transport/`, `adapters/`, `simulators/`, `contracts.py`
  4. `feat(integrations): stay domain adapter (approval-gated) and operator API` — `domain/`, `api/`, `app/api/v1/router.py`, `tests/test_health_api.py`
  5. `test(integrations): integration suites` — `tests/integrations/`
  6. `docs(integrations): design, approval packages, runbooks` — `docs/HTNG_FIAS_*`

## 7. Pending dependencies

* **Vendor documentation:** FIAS manual + record set (HF-11), framing/ACK/heartbeat/link role (HF-06);
  HTNG WSDL/XSD + profile (HF-07), security profile (HF-08); samples; test environment.
* **Business decisions:** HF-01, HF-02, HF-05, HF-18, HF-19, HF-21, HF-27 (+ HF-22, HF-23,
  HF-24, HF-25/26).
* **DBA:** HF-39 — tables, `down_revision` with two heads, live DB revision, 19 pre-existing
  incompatibilities, XSD library.

## 8. Recommended next action

Send `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` to the vendor, `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md`
to the DBA, and `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` to the decision owners; configure a
git identity and commit in the groups above. Further protocol implementation waits for the
official documents.
