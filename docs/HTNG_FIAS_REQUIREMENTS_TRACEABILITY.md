# HTNG / FIAS — Requirements Traceability (round 3, 2026-11-20)

Status meanings: IMPLEMENTED = code exists · TESTED = automated tests pass (disposable
environments) · VERIFIED = confirmed against the real target (none yet) · BLOCKED ·
PENDING VENDOR DOCUMENTATION · PENDING VENDOR VALIDATION · PENDING BUSINESS APPROVAL ·
PENDING DBA APPROVAL. Paths are under `backend/app/integrations/` and `backend/tests/integrations/`.

| Req | Description | Status | Source | Test evidence | External dep. | Approval dep. | Remaining blocker |
|---|---|---|---|---|---|---|---|
| R-01 | Client authentication, fail-closed, uniform errors | IMPLEMENTED, TESTED | `security/clients.py` | `test_security.py` | — | HF-22 (secret storage) | secret delivery channel |
| R-02 | Credential rotation (overlap 0–7 d, revoke, audit) | IMPLEMENTED, TESTED | `admin.py`, `cli.py` | `test_admin.py`, `test_security.py` | — | HF-22 | — |
| R-03 | Facility mapping, client-scoped, disabled unusable, audited API | IMPLEMENTED, TESTED | `security/facility.py`, `admin.py`, `api/router.py` | `test_admin.py`, `test_security.py` | property codes (A3) | HF-02, HF-05 | production mapping data |
| R-04 | Facility isolation (intake, payload smuggling, operator scope) | IMPLEMENTED, TESTED | `exchange/gateway.py`, `api/router.py` | `test_security.py`, `test_api.py`, `test_health_view.py` | — | HF-19 | approval |
| R-05 | Canonical envelope, hashing, lifecycle | IMPLEMENTED, TESTED | `core/` | `test_core.py` | — | — | — |
| R-06 | Idempotency incl. concurrent race (MySQL) | IMPLEMENTED, TESTED | `processing/*repository.py` | `test_repository_contract.py`, `test_mysql_persistence.py` | event identity per vendor (B9) | HF-21 (window) | vendor key definition |
| R-07 | Leases, fencing, takeover, restart recovery | IMPLEMENTED, TESTED | `processing/` | contract ×2 backends, `test_hms_domain_mysql.py` (real rollback) | — | — | — |
| R-08 | Retry, DLQ, audited redrive | IMPLEMENTED, TESTED | `processing/worker.py`, repositories | `test_exchange.py`, contract | fault semantics (C6) | HF-27 | final policy |
| R-09 | Per-stay ordering | IMPLEMENTED, TESTED | repositories, `domain/stays.py` | `test_ordering.py`, `test_hms_domain_mysql.py` | — | HF-27 | dead-letter blocking policy |
| R-10 | No loss on DB outage (TCP intake retry; worker batch survives) | IMPLEMENTED, TESTED | `transport/tcp.py` `LinkPump`, `processing/worker.py` | `test_hardening.py` | ACK semantics (B4) | — | vendor re-delivery rules |
| R-11 | Outbox + relay | IMPLEMENTED, TESTED | `processing/worker.py` | `test_exchange.py`, `test_end_to_end.py` | endpoints/links | HF-24 | no vendor endpoint |
| R-12 | TCP client link (timeouts, reconnect, backpressure) | IMPLEMENTED, TESTED | `transport/tcp.py` | `test_transport_tcp.py` | — | — | — |
| R-13 | TCP listener (allow-list, single owner) | IMPLEMENTED, TESTED | `transport/tcp_server.py` | `test_transport_server.py` | link role (B7) | HF-06 (role); HF-24 (allow-listed network path) | role decision |
| R-14 | FIAS framing / records / ACK / heartbeat | BLOCKED, PENDING VENDOR DOCUMENTATION | `adapters/fias/` (spec-driven, empty) | synthetic only | B1–B11 | HF-11 (content), HF-06 (framing, ACK, heartbeat) | official manual |
| R-15 | Safe XML, SOAP 1.1/1.2, fault parsing | IMPLEMENTED, TESTED | `transport/xml_security.py`, `soap.py` | `test_htng_adapter.py` | — | — | — |
| R-16 | HTNG operations, XSD validation, WS-Security | BLOCKED, PENDING VENDOR DOCUMENTATION | `adapters/htng/` (registry empty) | synthetic only | C1–C10 | HF-07, HF-08, HF-39 (library) | WSDL/XSD |
| R-17 | Stay check-in/out via real HMS services, idempotent, facility-checked, atomic audit | IMPLEMENTED, TESTED (disposable seeded MySQL, TEST-ONLY gate) | `domain/stays.py` | `test_domain.py`, `test_hms_domain_mysql.py` | vendor mapping (A4) | HF-01, HF-02, HF-05, HF-18, HF-19 | PENDING BUSINESS APPROVAL |
| R-18 | Reservation create/modify/cancel, guest update, room status, availability | not implemented | — | — | vendor support (A4/B2/C3) | HF-01, HF-02 | need protocol + business scope |
| R-19 | Candidate schema, upgrade/downgrade | IMPLEMENTED, TESTED | `processing/sql_models.py`, `migrations/drafts/` | `test_migration_candidate.py` | — | HF-39 | PENDING DBA APPROVAL |
| R-20 | Facility health, metrics, readiness | IMPLEMENTED, TESTED | `processing/health.py`, `api/router.py`, `metrics.py` | `test_health_view.py`, `test_api.py` | — | — | — |
| R-21 | Service process (disabled by default, back-off, graceful stop) | IMPLEMENTED, TESTED | `service.py` | `test_service.py` | — | HF-25/26 (supervision) | hosting decision |
| R-22 | Retention purge | IMPLEMENTED, TESTED (disabled) | repositories, `service.py` | `test_service.py` | — | HF-21 | retention value |
| R-23 | HTNG rate limit | IMPLEMENTED, TESTED (off) | `api/router.py` | `test_service.py` | vendor volumes (external prerequisite BLK-V7, no HF ID) | — | limit value |
| R-24 | Settings consistency validation | IMPLEMENTED, TESTED | `config.py` | `test_hardening.py` | — | — | — |
| R-25 | Header/log injection, secret exposure | IMPLEMENTED, TESTED | `core/correlation.py`, gateway, API | `test_core.py`, `test_security.py`, `test_hardening.py` | — | — | — |
| R-26 | Vendor contract harness + report | IMPLEMENTED, TESTED (self-tests); official run SKIPPED | `contracts.py` | `test_vendor_contracts.py` | samples | — | PENDING VENDOR VALIDATION |
| R-27 | Interoperability with a real PMS | not started | — | — | vendor env (A6/A7) | all above | PENDING VENDOR VALIDATION |

No requirement is VERIFIED: nothing has run against the real HMS database or a real vendor.

## Sprint update (2026-11-20, accelerated sprint)

| Req | Change in evidence |
|---|---|
| R-08 | intake classification: validation failures permanent, persistence failures transient (G1) — `test_sprint_hardening.py` |
| R-09 | ordering robust to equal timestamps (G5) — `test_sprint_hardening.py`, `test_e2e_hms_simulation.py` |
| R-10 | poison frames no longer block the TCP pump (G1) — `test_pump_moves_past_a_poison_frame` |
| R-14 | grammar requires ASCII-compatible encodings for byte-level framing (G4); FIAS content/link rules still BLOCKED (HF-11, HF-06) |
| R-15 | SOAP 1.2 faults/acks in the request's version, media-type enforcement, transient → 503 (G2, G3) |
| R-17 | end-to-end through FIAS-style TCP and HTNG-style SOAP into real `stays_write` — `test_e2e_hms_simulation.py` (disposable MySQL, TEST-ONLY gate); activation still PENDING BUSINESS APPROVAL |

Full integration suite this sprint: 430 collected / 429 passed / 1 skipped.

## Certification harness sprint (2026-11-20)

| Req | Change in evidence |
|---|---|
| R-26 | Contract harness extended into a certification harness (`tests/integrations/certification/`): 45 deterministic scenarios, JSON/Markdown evidence, run comparison, vendor-sample replay with provenance/PII/size/immutability controls. Sprint run: PASS 40 · BLOCKED 5 (official) · FAIL 0. Official contracts remain PENDING VENDOR VALIDATION |
| R-12, R-13 | FIAS-SYN-001…006, 009, 010 (transport via real simulator/TcpLink/LinkPump) — PASS |
| R-15 | HTNG-SYN-001…006, 013…015 (SOAP 1.1/1.2, faults, media type, XML safety) — PASS |
| R-04, R-06, R-08, R-09, R-10 | HTNG-SYN-007…012, FIAS-SYN-007, 008, 011…015 — PASS |
| R-17 | HMS-SYN-001…010 against real `stays_write` on a disposable seeded MySQL — PASS; activation still PENDING BUSINESS APPROVAL |
| R-14, R-16 | FIAS-OFF-001…003, HTNG-OFF-001…002 — BLOCKED (HF-06, HF-07, HF-08, HF-11, HF-39) |

Full integration suite this sprint: 495 collected / 494 passed / 1 skipped.

## Observability & dashboard API sprint (2026-11-20)

| Req | Change in evidence |
|---|---|
| R-20 | Read-only `GET /integrations/observability/{overview,messages,dlq}` (`observability.py`, `processing/activity.py`): per-protocol HTNG/FIAS entries, shared overview, eight separate readiness dimensions; unmeasurable telemetry is `null` + `not_available`/`not_observable`, never 0 — `test_observability.py` (22 tests, both backends) |
| R-04 | Same RBAC grant + facility scope; out-of-scope facility filter → 403; scoped counts — `test_observability.py` |
| R-08 | DLQ visibility with failure category/code, last attempt, redrive eligibility (read-only; no new redrive action) — `test_observability.py` |
| R-14, R-16 | Vendor validation shown as PENDING (HF-05/06/11, HF-07/08); synthetic certification can never set it — tested |

Full integration suite this sprint: 517 collected / 516 passed / 1 skipped. See `HTNG_FIAS_OBSERVABILITY_API_DESIGN.md`.
