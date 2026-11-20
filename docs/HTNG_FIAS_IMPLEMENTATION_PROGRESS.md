# HTNG / FIAS — Implementation Progress

Branch `feature/htng-fias-on-develop` (from `origin/develop` @ `46904fd`), uncommitted.
Updated 2026-11-20. Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**.

Note: `docs/HTNG-FIAS/` (untracked, added during round 1) describes an **earlier,
different** implementation; this file is the progress record for the code on this branch.

## Round 1 (2026-11-19)

Core contracts, security, exchange gateway, TCP client transport, spec-driven FIAS
adapter, HTNG SOAP/XML foundation, durable processing, MySQL candidate schema, stay
domain adapter (gated), operator API, simulators, 308 tests. See master report §1–21.

## Round 2 (2026-11-20) — audit-driven increments

| # | Increment | Labels | Evidence |
|---|---|---|---|
| 0 | Audit + implementation matrix | — | `HTNG_FIAS_IMPLEMENTATION_AUDIT.md` |
| 1 | D1 audit injection fix; D2 business idempotency (already-applied check-in/out = no-op); domain audit in the same transaction | IMPLEMENTED, TESTED | `test_domain.py`, `test_security.py`, `test_repository_contract.py` |
| 1b | D3: `$` anchors accepted trailing newline (correlation-id header/log injection) → `fullmatch` everywhere | IMPLEMENTED, TESTED | `test_core.py` |
| 2 | Credential rotation (overlap, revoke), client lifecycle CLI, audited mapping management + API | IMPLEMENTED, TESTED | `admin.py`, `cli.py`, `test_admin.py` |
| 3 | Per-entity ordering (stays ordered by external stay ref) | IMPLEMENTED, TESTED | `test_ordering.py` (both backends, 4-thread concurrency) |
| 4 | Facility health: counts, backlog age, DLQ, latency p50/p95/max, per-client last received/succeeded, link states, auth failures | IMPLEMENTED, TESTED | `processing/health.py`, `test_health_view.py` |
| 5 | Integration service process; retention purge (disabled until HF-21); HTNG per-client rate limit | IMPLEMENTED, TESTED | `service.py`, `test_service.py` |
| 6 | TCP listener (HMS listens) with allow-list and single owner | IMPLEMENTED, TESTED | `transport/tcp_server.py`, `test_transport_server.py` |
| 7 | Candidate migration upgrade/downgrade on disposable MySQL; readiness report | TESTED; PENDING DBA APPROVAL | `test_migration_candidate.py`, `HTNG_FIAS_MIGRATION_READINESS.md` |
| 8 | Vendor contract-test harness (production adapters only) + onboarding checklist | IMPLEMENTED; PENDING VENDOR VALIDATION (no samples) | `test_vendor_contracts.py`, `HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` |

## Round 3 (2026-11-20) — hardening and readiness

| Increment | Labels | Evidence |
|---|---|---|
| D4 no frame loss on DB outage (TCP intake retry); D5 worker batch survives DB failure; D6 settings validation | IMPLEMENTED, TESTED | `test_hardening.py` |
| Real `stays_write` check-in/out via worker on seeded disposable MySQL (TEST-ONLY gate) | IMPLEMENTED, TESTED | `test_hms_domain_mysql.py`, `hms_schema_shim.py` |
| Contract harness library + report CLI | IMPLEMENTED, TESTED (self-tests); PENDING VENDOR VALIDATION | `contracts.py`, `test_vendor_contracts.py` |
| Approval / request packages, traceability, validation plan | done | `HTNG_FIAS_NEXT_PHASE_REPORT.md` §5 |

Results: integration 406 collected / 405 passed / 1 skipped; legacy on seeded disposable DB
1,250 passed / 78 failed (identical to pristine). Full detail: `HTNG_FIAS_NEXT_PHASE_REPORT.md`.

## Still blocked

| Item | Label | Blocker |
|---|---|---|
| FIAS records, framing, ACK, heartbeat, link role | BLOCKED | HF-11 (specification content), HF-06 (link rules) |
| HTNG operations, XSD validation, WS-Security | BLOCKED | HF-07, HF-08, HF-39 (XSD library) |
| Live HMS writes | PENDING BUSINESS APPROVAL | HF-01, HF-02, HF-05, HF-19, HF-18 |
| Integration tables in HMS DB | PENDING DBA APPROVAL | HF-39 (+ two Alembic heads) |
| Retention values, payload encryption | PENDING BUSINESS APPROVAL | HF-21 |
| Process supervision / link ownership | BLOCKED | HF-25 / HF-26 |
| Interoperability | PENDING VENDOR VALIDATION | V-1 … V-10 |
| Commit of this work | BLOCKED | no git identity on this machine |
