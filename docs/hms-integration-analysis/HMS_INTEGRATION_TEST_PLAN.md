# HMS OSS/BSS Integration — Test Plan

**Date:** 2026-10-10 · **Status:** a plan for the target integration. **No test in this plan exists or was run yet.**

## 1. Baseline (current state)

| Item | Fact | Evidence |
|---|---|---|
| Existing suite | 22 modules, 691 test functions, pytest 9.1.1, FastAPI `TestClient` | `backend/tests/` |
| Database | Live PostgreSQL; the tests assert seeded row counts and statuses | `RUN_REPORT.md` §8, `tests/test_seed_data.py` |
| Writes | `*_write_api.py` tests POST/PATCH through the API | `backend/tests/test_*_write_api.py` |
| Run in this audit | **No.** The tests write to `hms_db` and need a fresh re-seed; both are forbidden by this task | — |
| Frontend | `npx tsc -b --noEmit`, `npm run build`, `npm run lint`; no unit-test runner configured | `README.md`, `RUN_REPORT.md` |

**Phase 1 exit action:** re-seed a *disposable* database and record a green baseline before any integration change.

## 2. Test environments and data

| Environment | Composition | Purpose |
|---|---|---|
| Unit | No database; `OssClient` mocked | Orchestration logic, state machines, validation |
| Contract | `OssClient` against the OSS OpenAPI (consumer-driven contract tests or a recorded stub) | Detect OSS API drift (B-01) |
| Integration | MySQL 8.0 (disposable) + OSS stub server seeded with **matching IDs** + the existing PostgreSQL (until D-01 cut-over) | Cross-system flows A–H |
| UAT | Real OSS test instance + BSS test database | Business acceptance |

**Seed rule:** one seed manifest generates both the OSS fixtures and the BSS rows, so every `oss_facility_id`, `oss_asset_id` and `oss_device_id` in BSS resolves. Reconciliation on a fresh seed must report **0** findings.

## 3. Scenario tests

Priority: **P1** = release gate · **P2** = must pass before UAT sign-off · **P3** = nice to have.

### A. Property and room loading
| ID | Test | Pri |
|---|---|---|
| T-A1 | Occupancy grid from BSS equals the seeded rooms (count, floor, status) | P1 |
| T-A2 | Caller with grants on facility X sees no room of property Y (list → absent, detail → 404) | P1 |
| T-A3 | Room with no `oss_asset_id` / no devices renders as "no devices mapped", not as an error | P2 |
| T-A4 | OSS stub down → grid still loads from BSS; device health shows "as of" / unknown | P1 |

### B. Reservation and availability
| ID | Test | Pri |
|---|---|---|
| T-B1 | Create a reservation → reservation, rooms, guest and calendar rows written atomically | P1 |
| T-B2 | Overlapping booking of the last room → 409; calendar unchanged | P1 |
| T-B3 | Two concurrent requests for the last room → exactly one succeeds | P1 |
| T-B4 | Departure ≤ arrival → 422 (parity with the current `stays_write.create_stay`) | P1 |
| T-B5 | Guest PII stored encrypted; `email_hash` lookup finds a returning guest | P1 |
| T-B6 | Cancel within policy → status and calendar restored | P2 |

### C. Check-in / stay / checkout
| ID | Test | Pri |
|---|---|---|
| T-C1 | Check-in without a room → 422; double check-in → 409 (parity with today) | P1 |
| T-C2 | Check-in commits BSS rows + `key.issue` event in one transaction (fault-inject after insert → nothing persisted) | P1 |
| T-C3 | Processor issues the key through the stub, with the idempotency key = `event_id`; a replay does not create a second key | P1 |
| T-C4 | OSS rejects the key → stay remains checked in; event `failed`; UI shows "key pending" | P1 |
| T-C5 | Checkout before check-in → 409; checkout twice → 409 | P1 |
| T-C6 | Checkout emits `key.revoke`; a revoke failure retries and raises an ops alert | P1 |
| T-C7 | Multi-room reservation → one `bss_stays` row per room; OSS context per room (D-05) | P2 |
| T-C8 | Extend stay updates planned checkout and availability | P2 |

### D. Checkout → housekeeping and audit
| ID | Test | Pri |
|---|---|---|
| T-D1 | Checkout creates exactly one housekeeping task per room, with status history `occupied→vacant`, `clean→dirty` | P1 |
| T-D2 | `bss_automation_events` row links source stay → target task | P1 |
| T-D3 | `bss_audit_trail` rows for every changed table, with `user_id` = the caller's OSS id | P1 |
| T-D4 | Retried checkout request (same idempotency key) does not duplicate tasks | P2 |

### E. Room ↔ device, health and alert navigation
| ID | Test | Pri |
|---|---|---|
| T-E1 | Registry sync maps devices to rooms via `oss_asset_id`; an unmapped device is reported, not inserted | P1 |
| T-E2 | Health snapshot updates `last_known_health_status` and `health_synced_at` | P1 |
| T-E3 | Snapshot older than the threshold → reported as unknown, not as healthy | P1 |
| T-E4 | Dashboard alert tile count = OSS stub alert summary; each link = configured FleetExplorer URL + alert id | P2 |
| T-E5 | The dashboard makes **no** per-room OSS call (assert the stub call count) | P2 |

### F. Work order from an OSS alert
| ID | Test | Pri |
|---|---|---|
| T-F1 | Create a work order from alert id (BIGINT) → condition + work order linked | P1 |
| T-F2 | Alert room ≠ work-order room → 422 | P1 |
| T-F3 | Unknown alert id → 422; OSS down → 503 and nothing written | P1 |
| T-F4 | Second open work order for the same alert → 409 | P2 |
| T-F5 | Closing the work order resolves the room condition | P2 |

### G. Identity and authorization
| ID | Test | Pri |
|---|---|---|
| T-G1 | Valid OSS token → `/auth/me` returns the OSS user and HMS grants | P1 |
| T-G2 | Expired or tampered token → 401 (envelope unchanged) | P1 |
| T-G3 | Role with no HMS module (FleetExplorer-only) → 403 on every HMS route (Rule 4) | P1 |
| T-G4 | Staff, guest or system role → refused for HMS Web (parity with `core/platform.py`) | P1 |
| T-G5 | Revoking a grant in OSS takes effect within the cache TTL | P2 |
| T-G6 | **Every router enforces its module**, including `tickets` and `default_key` (route-table test that fails on any unguarded business route) | P1 |
| T-G7 | Permission parity: for every role, old `role_module_permission` grants = new `platform_*` grants (migration check) | P1 |

### H. Dashboard and sustainability
| ID | Test | Pri |
|---|---|---|
| T-H1 | `/dashboard/summary` returns all tiles in one call; values equal the sources | P1 |
| T-H2 | Response carries `generated_at` and `oss_as_of` | P2 |
| T-H3 | Carbon calculation: kWh × factor = `carbon_kg` for a fixed fixture; rerun is idempotent | P2 |
| T-H4 | Energy for a room with no stay in the period is attributed to the property, not to a guest | P2 |
| T-H5 | Reports: each report's totals reconcile with its source (BSS or OSS) | P2 |
| T-H6 | XLSX export masks PII for callers without the PII permission | P1 |

## 4. Cross-cutting suites

| Suite | Tests | Pri |
|---|---|---|
| **Data integrity / reconciliation** | Reconciliation job returns 0 on fresh seed; injects each orphan type (missing asset, facility mismatch, deleted device, stale stay context) and asserts it is reported | P1 |
| **Identifier validation** | Each bridge column in approach §6: valid, unknown, wrong facility, wrong type | P1 |
| **PII** | `/users` no longer returns guest PII; PII endpoint requires a purpose and writes `bss_pii_access_log`; logs contain no PII (log capture) | P1 |
| **Property scope** | For every BSS list endpoint: another property's rows are never returned (parametrised over the route table) | P1 |
| **Resilience** | OSS timeout, 5xx, slow response, circuit open/half-open; MySQL down → 503 with the envelope | P1 |
| **Event processor** | Concurrent processors (`SKIP LOCKED`) never double-process; back-off; max attempts → failed | P1 |
| **Migration** | BSS baseline migration up/down on an empty database; OSS additive changes are backward compatible with the current HMS reads | P1 |
| **Regression** | The existing 691 tests (adapted) stay green for behaviour that does not move | P1 |
| **Frontend** | Typecheck/build/lint; UAT scripts per module (mapping doc acceptance criteria); stale/pending/error states visible | P2 |
| **Performance** | Dashboard p95 with a remote OSS stub (latency injected) under the agreed budget (**budget TBD**) | P2 |

## 5. Entry and exit criteria

- **Entry:** decisions D-01, D-05, D-07, D-14 signed; OSS OpenAPI available; MySQL test instance available.
- **Exit:** all P1 tests pass in CI; no open Critical/High defects; reconciliation = 0 on seed; security review of the PII and scope suites signed by SEC.
