# HTNG / FIAS — Accelerated Sprint Report (2026-11-20)

Branch `feature/htng-fias-on-develop` (uncommitted) · status unchanged:
**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. Gap matrix:
`HTNG_FIAS_IMPLEMENTATION_GAP_MATRIX.md`.

## 1. Gaps found and fixed (each with regression tests in `tests/integrations/test_sprint_hardening.py`)

| ID | Area | Defect (verified before fixing) | Fix | Reproduced first? |
|---|---|---|---|---|
| G1 | Shared / FIAS | An unexpected exception while **validating** a message (adapter/mapper defect, malformed structure) was classified TRANSIENT; with the round-3 no-loss pump, a poison frame was retried **forever** and blocked the link | `ExchangeGateway.receive`: validation failures → PERMANENT `intake_unexpected_error`; only persistence failures stay transient | yes (pump looped on the poison frame) |
| G2 | HTNG | Inbound endpoint always answered **SOAP 1.1** faults and acknowledgements, even to SOAP 1.2 requests | `soap_fault(version, …)` (1.2: `Code/Value` Sender/Receiver, `Reason/Text`, `application/soap+xml`); ack built in the request's version (`HTNGAdapter.build_response(version=…)`) | confirmed by code reading; tests written with the fix |
| G3 | HTNG | Any Content-Type accepted | SOAP media types per W3C bindings only; 415 after authentication; transient intake → 503 | confirmed by code reading |
| G4 | FIAS | Grammar accepted non-ASCII-compatible encodings (UTF-16/32, EBCDIC) although framing and field splitting are byte-level | `WireGrammar` requires ASCII-compatible encoding and a separator that round-trips | yes (UTF-16 grammar accepted) |
| G5 | Shared / FIAS | Per-stay ordering sorted by `received_on`; messages with **equal timestamps** fell back to random UUID order — a check-out could run before its check-in | gateway issues strictly increasing intake timestamps (+1 µs on ties) | yes (found by the new E2E simulation; isolated tests failed first) |

Side effect of G5 handled in tests: under a frozen test clock, tied messages are stamped
microseconds ahead and become claimable when time advances; three tests now advance their
fake clock before running the worker (`test_end_to_end.py`, `test_e2e_hms_simulation.py`,
`test_sprint_hardening.py`). No assertion was weakened.

## 2. New end-to-end simulation (real HMS stay services, disposable MySQL)

`tests/integrations/test_e2e_hms_simulation.py` — FIAS-style TCP and HTNG-style SOAP 1.2 flows
through the shared engine into the real `stays_write`, covering valid, duplicate, malformed,
cross-property, unauthorized, connection interruption, DB outage during intake, worker crash
with lease-expiry recovery, ordering and audit. Synthetic record/profile definitions only;
live-write gate opened only with a TEST-ONLY register.

## 3. Results (all executed in this sprint, Docker, disposable MySQL 8.4)

| Command | Result |
|---|---|
| G1 reproduction before fix | 2 failed, 1 passed (as expected) |
| G4 reproduction before fix | UTF-16 grammar accepted |
| G5 reproduction before fix | 2 failed |
| `pytest tests/integrations/test_sprint_hardening.py` (after fixes) | 22 passed |
| `pytest tests/integrations/test_e2e_hms_simulation.py` (with `INTEGRATION_TEST_HMS_DB_URL`) | 2 passed |
| Full suite, first run (both disposable DBs) | 427 passed, 2 failed, 1 skipped — the 2 failures were the G5 frozen-clock side effect in `test_end_to_end.py` |
| `pytest tests/integrations/test_end_to_end.py` after clock adjustment | 8 passed |
| **Full suite, final run** (`INTEGRATION_TEST_MYSQL_URL` + `INTEGRATION_TEST_HMS_DB_URL`) | **430 collected: 429 passed, 1 skipped** (vendor samples absent) |
| ruff (E,F,W,B,S) on `app/integrations`, `tests/integrations` | all checks passed |
| gitleaks on `backend/app/integrations`, `backend/tests/integrations` | no leaks found |
| Protected files (`router.py`, `test_health_api.py`, `docker-compose.dev.yml`) | sha256 unchanged |

The legacy HMS suite was **not** re-run in this sprint.

## 4. Files changed in this sprint

Code: `app/integrations/exchange/gateway.py` (G1, G5), `app/integrations/api/router.py` (G2, G3),
`app/integrations/adapters/htng/adapter.py` (G2), `app/integrations/adapters/fias/spec.py` (G4).
Tests: new `test_sprint_hardening.py`, `test_e2e_hms_simulation.py`; `conftest.py` (shared
`hms_engine` fixture), `test_hms_domain_mysql.py` (fixture moved to conftest),
`test_end_to_end.py` (clock advance). Docs: this report, `HTNG_FIAS_IMPLEMENTATION_GAP_MATRIX.md`,
`HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md`.

## 5. Blocked (unchanged)

* Vendor: FIAS content (HF-11) and link rules (HF-06); HTNG profile/WSDL/XSD (HF-07) and
  security (HF-08); official samples; test environment (HF-09).
* Approval: live HMS writes (HF-01, 02, 05, 18, 19), retention (HF-21), retry/ordering policy
  (HF-27), DBA schema + XSD library (HF-39).

No production switch, approval status, decision meaning, migration or database was changed.
