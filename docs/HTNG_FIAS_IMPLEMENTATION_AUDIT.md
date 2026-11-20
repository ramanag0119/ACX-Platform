# HTNG / FIAS — Implementation Audit (Phase 1, round 2)

Date 2026-11-19 · branch `feature/htng-fias-on-develop` · uncommitted working tree.
Method: source inspection of `backend/app/integrations/` (48 files), `app/services/stays_write.py`,
`app/api/`, migrations, tests, docs; grep for placeholders; re-reading every gate.

## 1. Placeholders found

| Location | Finding | Verdict |
|---|---|---|
| `adapters/htng/schema.py` `XsdValidator` | raises until an XSD library + XSD are approved | intentional, BLOCKED (HF-39/HF-07) |
| `processing/worker.py` `OutboundSender.send` | `NotImplementedError` on an interface base | interface only, acceptable |
| no `TODO`/`FIXME` | — | — |

No fake success paths found: blocked adapters raise, gates raise `ApprovalRequired`.

## 2. Defects found

| ID | Defect | Severity |
|---|---|---|
| D1 | `ExchangeGateway.authenticate` stores the **unvalidated, attacker-supplied** client code (≤64 chars, may contain control characters) in the audit table → audit/log injection | Medium |
| D2 | A second, distinct `stay.check_in` for a stay already checked in hits `stays_write.Conflict` and is **dead-lettered**; the same for `check_out`. Not idempotent at business level | Medium |

## 3. Implementation matrix

| Capability | Existing implementation | Missing work | Evidence | Priority |
|---|---|---|---|---|
| Client authentication | fail-closed, hashed secrets, uniform errors | — | `security/clients.py`, 46 security tests | — |
| Credential lifecycle / rotation | single `secret_hash` per client | rotation with overlap window, revoke, CLI | no rotation code | **P1** |
| Facility mapping | client-scoped resolver, SQL store | management service + audited API | no write path for mappings | **P1** |
| Facility isolation | intake + operator scoping | — | tests | — |
| Envelope / idempotency | canonical hash, scoped keys, race handling | — | 308 tests | — |
| Per-entity ordering | none; claim is FIFO by due time only | ordering key, claim skips keys with an earlier unfinished message | `sql_repository.claim` | **P1** (check-in/out may run out of order) |
| Leases / fencing / retry / DLQ / redrive | implemented both backends | — | contract tests ×2 | — |
| Audit of domain writes | none | audit row in the same transaction as the domain write | `domain/stays.py` | P2 |
| Business idempotency | relies on HMS `Conflict` → DLQ | already-applied detection (D2) | `stays_write.py:349,401` | **P1** |
| Long-running worker process | `run_once()` only | runner loop, graceful shutdown, heartbeats, CLI; disabled by default | no entry point | **P1** |
| TCP client link | implemented | — | 25 transport tests | — |
| TCP server (HMS listens) | none | protocol-neutral listener, peer allow-list, single active connection | — | P2 (HF-06 decides if used) |
| HTNG endpoint abuse control | size limit only | per-client rate limit (configurable, off by default) | `api/router.py` | P2 |
| Payload retention | `retain_until` column unused | purge mechanism, disabled until HF-21 sets values | `sql_models.py` | P2 |
| Observability | counters, status counts, heartbeats | per-client last success, processing latency, inbound/outbound/pending/DLQ per facility, client status API | `metrics.py`, `api/router.py` | **P1** |
| Candidate migration | DDL + draft revision | upgrade/downgrade executed on disposable DB | never executed via Alembic ops | **P1** |
| FIAS protocol | spec-driven, production empty | everything protocol-specific | no manual | BLOCKED HF-11 |
| HTNG protocol | SOAP + registry, production empty | operations, XSD validation, WS-Security | no WSDL/XSD | BLOCKED HF-07/08/39 |
| Live HMS writes | gated | approvals | register | BLOCKED HF-01/02/05/19/18 |
| Vendor onboarding | dependency list | per-vendor checklist + contract-test template | — | P2 |

## 4. Not changed (by rule)

Protocol framing/records/HTNG operations (no documents); live-write gate; HF statuses;
migration application; branch/git state.

## 5. Increments planned

1. D1 + D2 fixes; domain audit in-transaction.
2. Credential rotation.
3. Per-entity ordering.
4. Mapping management + audited API.
5. Observability: client/facility status, latency.
6. Worker runner process.
7. TCP listener.
8. Rate limit + retention purge.
9. Migration upgrade/downgrade validation; readiness report; vendor checklist.
