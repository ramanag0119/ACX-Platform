# HTNG / FIAS — Master Implementation Report

| | |
|---|---|
| Date | 2026-11-19 |
| Branch | `feature/htng-fias-on-develop` (created from `origin/develop` @ `46904fd`); changes **uncommitted**, nothing pushed |
| Readiness status | **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING** |

## 1. Repository baseline

See `HTNG_FIAS_REPOSITORY_BASELINE.md`. Key facts: MySQL `inspironics_app` backend
exists only on `develop`; no integration code or vendor document in the repository;
two Alembic heads; the repo cannot build its schema on a fresh MySQL; the earlier
HTNG/FIAS work exists only untracked in `../HMS-Frontend/ACX-Platform` and was not adopted.

## 2. Architecture implemented

`HTNG_FIAS_ARCHITECTURE.md`. Transport → protocol adapter → ExchangeGateway (auth,
facility, smuggling check, idempotent persist) → durable worker (lease + fencing) →
dispatcher → approval-gated domain adapter → existing HMS services; outbox → relay →
sender. Vendor semantics are data with verification status; production specs are empty.

## 3. Files created

`backend/app/integrations/` (48 Python files including package `__init__.py`; ~6,300 lines incl. docstrings):

| Package | Files |
|---|---|
| root | `__init__.py`, `config.py`, `metrics.py`, `runtime.py` |
| `core/` | `errors.py`, `envelope.py`, `hashing.py`, `lifecycle.py`, `retry.py`, `masking.py`, `correlation.py` |
| `security/` | `clients.py`, `facility.py`, `sql_stores.py` |
| `exchange/` | `registry.py`, `dispatcher.py`, `gateway.py` |
| `processing/` | `repository.py`, `sql_models.py`, `sql_repository.py`, `worker.py` |
| `transport/` | `framing.py`, `tcp.py`, `xml_security.py`, `soap.py` |
| `adapters/` | `base.py`; `fias/spec.py`, `fias/codec.py`, `fias/adapter.py`; `htng/schema.py`, `htng/adapter.py`, `htng/sender.py` |
| `domain/` | `approvals.py`, `stays.py` |
| `simulators/` | `fixtures.py`, `fias_simulator.py` (TEST ONLY) |
| `api/` | `router.py` |

* `backend/tests/integrations/` — `conftest.py` + 11 test modules (3,080 lines, 308 tests)
* `backend/migrations/drafts/integration_tables_candidate.py` (not scanned by Alembic)
* `docs/HTNG_FIAS_*.md` (14 documents) and `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`

## 4. Files modified

| File | Change |
|---|---|
| `backend/app/api/v1/router.py` | import + `include_router(integrations_router)` |
| `backend/tests/test_health_api.py` | added the 11 integration paths to the `DELIVERED_PATHS` inventory (the project's per-phase convention). The 14 paths missing before this work were **not** touched |

No other existing file, configuration, `.env`, migration or database was changed.

## 5. Exchange Adapter

Implemented: adapter registry (unique per protocol, direction and BLOCKED checks),
handler registry, ExchangeGateway intake (9 ordered checks), idempotent persistence,
outbound requests with facility authorisation and early encodability check, structured
`IntakeResult`, security audit events, metrics. Tests: `test_exchange.py` (28),
`test_security.py` (46).

## 6. FIAS adapter

Spec-driven parser/serializer and adapter implemented and tested on a synthetic spec.
**Production BLOCKED (HF-11)** — no manual, record set or example exists. Earlier
GI/GO/GC/WR and STX/ETX assumptions classified as provisional test assumptions and not
encoded. Matrix: `HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md`.

## 7. HTNG adapter

Safe XML, SOAP 1.1/1.2, SOAP HTTP client, versioned schema registry, structural
validation, adapter, outbound sender, inbound endpoint (disabled). **Production BLOCKED
(HF-07/HF-08)**; XSD validation blocked on an approved library (HF-39).
`HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md`.

## 8. Security

Fail-closed client auth (hashed generated secrets, constant-time compare, uniform
errors, audit), client-scoped facility mapping, recursive scope-smuggling rejection,
facility-scoped operator APIs with 404-on-out-of-scope, masked bodies, no payload in
logs. `HTNG_FIAS_SECURITY_DESIGN.md`.

## 9. Database

Seven candidate tables on a separate metadata; DDL generated for review; verified on
disposable MySQL 8.4 only. **Not applied to the HMS database; Alembic heads unchanged
(`a3f1c8e2d904`, `b3c4d5e6f7a8`).** `HTNG_FIAS_DATABASE_DESIGN.md`.

## 10. Worker / idempotency / retry / DLQ / outbox

Implemented for both repositories: scoped idempotency with canonical fingerprints,
`SKIP LOCKED` claiming, lease tokens with fencing on entry and exit, savepoint-joined
completion (domain + status + outbox atomic), bounded retry for transient errors only,
DLQ, reason-required audited redrive, outbox with its own leases, restart recovery.

## 11. HMS domain integration

`StayDomainAdapter` wraps `stays_write.check_in/check_out`, verifies facility ownership
via room allocations. **Live writes disabled**: env flag off, HF-01/02/05/19 not
approved, no actor (HF-18), no resolver (HF-02). Tested with mocked services only.

## 12. Test commands executed

All in Docker (`python:3.12-slim`, `requirements.txt`; `mysql:8.4` disposable):

```sh
python -m pytest --co -q                                   # baseline collection
python -m pytest -q --tb=no -rfE                           # pristine tree (git archive HEAD)
python -m pytest -q --tb=no -rfE --ignore=tests/integrations   # modified tree
INTEGRATION_TEST_MYSQL_URL=…/acx_integration_test python -m pytest tests/integrations -q
python -m pytest tests/test_health_api.py -q              # both trees
ruff check --select E,F,W,B,S … app/integrations tests/integrations migrations/drafts
alembic heads
```

## 13. Actual results

| Run | Collected | Passed | Failed | Errors | Skipped |
|---|---|---|---|---|---|
| Integration suites (memory + disposable MySQL) | 308 | **308** | 0 | 0 | 0 |
| Legacy suite, pristine `HEAD` | 1,329 | 63 | 150 | 1,115 | 1 |
| Legacy suite, with changes | 1,329 | 63 | 150 | 1,115 | 1 |
| `test_health_api.py`, pristine / with changes | 29 / 29 | 24 / 24 | 5 / 5 | 0 | 0 |

The pristine and modified failure sets were compared ID by ID (`comm`): **identical
(1,265 IDs), no new failure**. `ruff`: all checks passed (intentional S-rule exceptions
annotated). `alembic heads`: unchanged.

## 14. Baseline failures (pre-existing)

1,265 legacy tests fail or error because the suite needs a seeded HMS database and the
repository cannot build the schema on MySQL (`8f1e3c5a7b92` / `create_all` → MySQL 1067).
`test_openapi_exposes_only_the_phases_delivered_so_far` was already failing on 14
undeclared paths from earlier phases.

## 15. New defects found and fixed during this work

| Defect | Fix | Test |
|---|---|---|
| Duplicate-key matcher used the full constraint name; MySQL's 64-char limit truncates it with a hash, so a real insert race would surface as an integrity failure | match `integration_idempotency_keys.uq_` | `test_lost_insert_race_resolves_via_duplicate_key_error` |
| Framer raised mid-chunk, dropping valid frames already decoded | errors queued, `take_errors()` | `test_oversized_unterminated_input_is_dropped_without_losing_good_frames` |
| Completion fence re-checked with a fixed timestamp, missing handler overrun | clock callable, re-fence on exit | `test_handler_overrunning_lease_is_fenced_at_commit_and_outbox_discarded` |
| Invalid field regex raised `re.error` instead of `ValueError` | wrapped | `test_specification_is_validated` |

## 16. Pending vendor documentation

`HTNG_FIAS_VENDOR_DEPENDENCIES.md` V-1 … V-10 (FIAS manual and link rules, HTNG
WSDL/XSD and security profile, endpoints, test environment, vocabularies).

## 17. Pending business decisions

HF-01, HF-02, HF-05, HF-19 (live writes); HF-18 (actor); HF-21/22/23 (data
retention, secrets, audit); HF-25/26/27 (hosting, restart, ordering). Note the HF
numbering conflict with the earlier register (resolved 2026-11-20, `HTNG_FIAS_DECISION_REGISTER.md` §1).

## 18. Pending DBA approvals

HF-39: the seven tables, collation, FK actions; choose `down_revision` given two heads;
confirm the target database revision; approve an XSD library if HTNG proceeds.

## 19. Intentionally disabled

FIAS and HTNG production adapters (BLOCKED); HTNG inbound endpoint; live domain writes;
raw wire-payload storage; simulators (opt-in, loopback only, never started by the API);
XSD validator.

## 20. Readiness status

**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** Not "ready for controlled vendor
testing": no specification, schema, credentials or test environment exists. Passing
unit and simulator tests is not interoperability evidence.

## 21a. Round 2 (2026-11-20)

Audit: `HTNG_FIAS_IMPLEMENTATION_AUDIT.md`. Defects fixed: D1 (audit injection via client
code), D2 (repeated check-in/out dead-lettered instead of no-op), D3 (`$` anchors accepted
a trailing newline — correlation-id header/log injection). Added: credential rotation +
CLI, audited mapping management API, per-entity ordering, in-transaction domain audit,
facility health view, integration service process, retention purge (disabled), HTNG rate
limit, TCP listener, migration upgrade/downgrade validation, vendor contract harness.
New modules: `admin.py`, `cli.py`, `service.py`, `processing/health.py`,
`transport/tcp_server.py`; new tests: `test_admin.py`, `test_ordering.py`,
`test_health_view.py`, `test_service.py`, `test_transport_server.py`,
`test_migration_candidate.py`, `test_vendor_contracts.py`. New docs:
`HTNG_FIAS_IMPLEMENTATION_AUDIT.md`, `HTNG_FIAS_MIGRATION_READINESS.md`,
`HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md`.

Results executed 2026-11-20 (Docker, disposable MySQL 8.4):

| Run | Result |
|---|---|
| Integration suites | **385 collected: 384 passed, 1 skipped** (vendor harness: no official samples) |
| Legacy suite with changes | 150 failed, 63 passed, 1 skipped, 1,115 errors — **identical ID set** to the pristine baseline (1,265 IDs) |
| `ruff` (E,F,W,B,S) on integrations, tests, drafts | all checks passed |
| Alembic heads | unchanged (`a3f1c8e2d904`, `b3c4d5e6f7a8`) |

Status unchanged: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** Acceptance
criteria 2, 3, 5 (DBA approval), 8 are not met; see `HTNG_FIAS_IMPLEMENTATION_PROGRESS.md`.

## 21. Remaining blockers and next actions

1. Commit this branch (configure a git identity) and decide its relationship to
   `feature/htng&fias-integration` (still at `main`).
2. Decide what happens to the earlier untracked work and to `docs/HTNG-FIAS/`, which
   describes that earlier implementation, not this one.
3. Reconcile HF numbering; take HF-39 to the DBA with `HTNG_FIAS_DATABASE_DESIGN.md`.
4. Obtain vendor documents (V-2, V-5) and encode them as verified specs.
5. Build the supervised worker/link process (HF-25/26), per-entity ordering (HF-27),
   mapping management API, payload encryption/retention (HF-21).
6. Fix the pre-existing MySQL bootstrap so the legacy suite can run on a seeded DB.
