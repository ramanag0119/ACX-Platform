# HTNG / FIAS — Certification Harness Sprint Report (2026-11-20)

Branch `feature/htng-fias-on-develop` (uncommitted) · status unchanged:
**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. This sprint adds engineering
certification tooling; it is **not** vendor certification.

## 1. Delivered

| Component | File(s) | Reuses |
|---|---|---|
| Scenario registry, execution engine, evidence collector | `backend/tests/integrations/certification/core.py` | `core/masking.py` |
| HTNG scenarios (15 synthetic + 2 official BLOCKED) | `certification/scenarios_htng.py` | `test_api.env_impl`, real inbound endpoint, generic XML profile |
| FIAS scenarios (15 synthetic + 3 official BLOCKED) | `certification/scenarios_fias.py` | `FiasTestSimulator`, `TcpLink`, `LinkPump`, `FIASAdapter`, `build_stack` |
| HMS workflow scenarios (10) | `certification/scenarios_hms.py` | `test_e2e_hms_simulation.build`, `hms_engine_impl`, real `stays_write` |
| Reports (JSON, Markdown) and run comparison | `certification/report.py` | — |
| Vendor sample replay with provenance / PII / size / immutability controls | `certification/replay.py` | `app.integrations.contracts.run_contracts` |
| CLI (`list`, `run`, `replay-vendor`, `compare`) | `certification/__main__.py` | — |
| Tests | `tests/integrations/test_certification_harness.py` (65 tests: 45 scenarios + 20 harness tests) | — |

No application code changed. No new transport, adapter, gateway, worker, HMS integration,
operator API or UI. Certification controls are CLI/pytest only.

## 2. Defect found in the harness during the sprint

Evidence field `notes` was masked wholesale by key name ("note" is a sensitive fragment) and the
secret check ran after masking, so it could never trigger. Renamed to `observations` (still
text-scrubbed) and the secret check now runs on raw evidence before masking; regression test
`test_evidence_masks_pii_and_refuses_secrets` failed first, passes now.

## 3. Results (executed this sprint, Docker, disposable MySQL 8.4)

| Command | Result |
|---|---|
| `python -m tests.integrations.certification list` | 45 scenarios |
| `… run` (no HMS DB) | PASS 30 · FAIL 0 · BLOCKED 5 · NOT RUN 10 |
| `INTEGRATION_TEST_HMS_DB_URL=… … run --label sprint-full --json --md` | **PASS 40 · FAIL 0 · BLOCKED 5 · NOT RUN 0** |
| `pytest tests/integrations/test_certification_harness.py` (no HMS DB) | 55 passed, 10 skipped |
| **Full integration suite** (`INTEGRATION_TEST_MYSQL_URL` + `INTEGRATION_TEST_HMS_DB_URL`) | **495 collected: 494 passed, 1 skipped** (vendor sample contract test). The 5 official-vendor scenario tests pass by asserting BLOCKED |
| ruff (E,F,W,B,S) `app/integrations`, `tests/integrations` | all checks passed |
| gitleaks `backend/tests/integrations` | no leaks found |
| Protected files (`router.py`, `test_health_api.py`, `docker-compose.dev.yml`) | sha256 unchanged |

By group (sprint-full run): HTNG 15/15 synthetic PASS, 2 BLOCKED · FIAS 15/15 synthetic PASS,
3 BLOCKED · HMS 10/10 PASS with real state and audit verified (e.g. HMS-SYN-001 pending/Allotted
→ active/Occupied; HMS-SYN-008 lost lease leaves pending/Allotted, recovery → active).

Note: HTNG-SYN-011 asserts the 503; "stores nothing" holds by construction (the injected outage
is in the persistence call).

The legacy HMS suite was not re-run this sprint.

## 4. Still blocked

| Scenario | Blocked by |
|---|---|
| HTNG-OFF-001 official operations | HF-07, HF-08 |
| HTNG-OFF-002 official XSD validation | HF-07, HF-39 |
| FIAS-OFF-001 official records | HF-11 |
| FIAS-OFF-002 framing + ACK/NAK | HF-06 |
| FIAS-OFF-003 heartbeat / link start-up | HF-06 |
| Real vendor sample replay | no samples; guest-data samples need HF-21 |
| Live HMS writes in any real environment | HF-01, HF-02, HF-05, HF-18, HF-19 |
| Integration tables in HMS DB | HF-39 |

No production switch, approval status, decision meaning, migration or database was changed;
the real HMS database was not contacted; no vendor traffic was sent.
