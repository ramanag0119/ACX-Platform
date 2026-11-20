# HTNG / FIAS — Vendor Validation Test Plan

Audience: QA and integration engineers running validation once vendor material arrives.
Readiness labels: **LOCAL** = ready for local testing (automated today) · **SAMPLE** = waiting
for official sample/spec · **VENDOR-ENV** = waiting for vendor test environment · **BIZ** =
waiting for business approval · **DBA** = waiting for DBA approval.

Simulator / synthetic-fixture results are plumbing evidence only, never vendor evidence.

| ID | Area | Test | Method / tool | Ready | Existing automated evidence |
|---|---|---|---|---|---|
| V-01 | FIAS parsing | Every official sample record parses to the documented fields | contract harness, production adapter | SAMPLE | harness self-tests (`test_vendor_contracts.py`) |
| V-02 | FIAS parsing | Malformed / unknown / oversize records rejected with documented error | contract harness negative cases | SAMPLE | `test_fias_adapter.py` (synthetic grammar) |
| V-03 | FIAS framing | Official framing: partial, multiple, oversize frames | transport + official markers | SAMPLE | `test_transport_tcp.py` (TEST markers) |
| V-04 | FIAS ACK/NAK | ACK on accepted, NAK/behaviour on rejected, per manual | responder + vendor link | SAMPLE → VENDOR-ENV | none (not implemented, HF-06) |
| V-05 | FIAS heartbeat / link | Start-up, heartbeat, resync, reconnect per manual | vendor test link | SAMPLE → VENDOR-ENV | reconnect/backpressure/idle generic: `test_transport_tcp.py`, `test_transport_server.py` |
| V-06 | FIAS connection role | Client or listener mode against vendor; allow-list | vendor test link | VENDOR-ENV | `test_transport_server.py` |
| V-07 | HTNG operations | Each in-scope operation decodes / encodes per profile | contract harness, verified profile | SAMPLE | `test_htng_adapter.py` (generic profile) |
| V-08 | WSDL/XSD | Inbound and outbound messages validate against official XSD | XsdValidator + approved library | SAMPLE + DBA (library, HF-39) | `test_xsd_validation_requires_approved_dependency` |
| V-09 | HTNG security | WS-Security / mTLS per profile; replay window | vendor test env | SAMPLE (HF-08) → VENDOR-ENV | none |
| V-10 | Client auth | Missing / wrong / disabled / foreign-protocol credentials rejected; uniform errors | automated | LOCAL | `test_security.py` (52), `test_api.py` |
| V-11 | Duplicates | Vendor re-sends same event → `duplicate`, processed once; same key different content → conflict | automated + vendor resend | LOCAL → VENDOR-ENV | `test_exchange.py`, `test_mysql_persistence.py` (race) |
| V-12 | Ordering | Same-stay events processed in arrival order; check-out before check-in rejected by HMS rule | automated (real stay services, disposable MySQL) | LOCAL | `test_ordering.py`, `test_hms_domain_mysql.py` |
| V-13 | Retry / DLQ | Transient failures retried with back-off; exhaustion → DLQ; redrive audited | automated | LOCAL | `test_exchange.py`, `test_repository_contract.py` |
| V-14 | Outage | DB outage during TCP intake → frame retried, not dropped; worker survives | automated | LOCAL | `test_hardening.py` |
| V-15 | Credential rotation | Overlap, expiry, early revoke, audit without secrets | automated (MySQL) | LOCAL | `test_admin.py` |
| V-16 | Property mapping | Client-scoped, disabled mapping unusable, scoped API, audited | automated | LOCAL | `test_security.py`, `test_admin.py` |
| V-17 | Audit trail | Domain change + audit atomic; lost lease discards both | automated (real stay services) | LOCAL | `test_repository_contract.py`, `test_hms_domain_mysql.py` |
| V-18 | Facility health | Counts, backlog age, latency, per-client activity, scoping | automated | LOCAL | `test_health_view.py` |
| V-19 | HMS business mapping | Check-in / check-out through real `stays_write` incl. no-op repeat and HMS conflict | automated (disposable MySQL, TEST-ONLY gate) | LOCAL; production activation BIZ | `test_hms_domain_mysql.py` |
| V-20 | Persistence | Candidate schema upgrade/downgrade, constraints, concurrency | automated (disposable MySQL) | LOCAL; deployment DBA | `test_migration_candidate.py`, `test_mysql_persistence.py` |
| V-21 | End-to-end vendor run | Vendor sends real traffic to test HMS; HMS sends outbound; reconciliation | vendor test env | VENDOR-ENV + DBA + BIZ | none |
| V-22 | Certification | Vendor acceptance criteria | vendor | VENDOR-ENV | none |

## Traceability: vendor requirement → document → implementation → test → expected → evidence

Document references point to the vendor request package items (no official section numbers
exist yet). Evidence column: "local" = automated, synthetic/disposable; "—" = none yet.

| Area | Vendor requirement | Official doc ref | Implementation | Test case | Expected result | Evidence | State |
|---|---|---|---|---|---|---|---|
| FIAS transport | connect/listen, timeouts, reconnect, backpressure | B7, B12 | `transport/tcp.py`, `tcp_server.py` | V-06, `test_transport_tcp.py`, `test_transport_server.py` | stable link, no frame loss | local | BLOCKED for vendor run (BLK-F6) |
| FIAS framing | markers, escaping, max length | B3 | `transport/framing.py` | V-03 | official frames split exactly | local (TEST markers) | BLOCKED (BLK-F3) |
| FIAS parsing / serialisation | records, fields, formats | B2, B8, B10 | `adapters/fias/spec.py`, `codec.py`, `adapter.py` | V-01, V-02, contract harness | every sample → documented canonical fields; negatives rejected | — | BLOCKED (BLK-F2, BLK-F7) |
| FIAS acknowledgements | ACK/NAK | B4 | `LinkPump.responder` (none) | V-04 | ACK/NAK per manual | — | BLOCKED (BLK-F4) |
| HTNG SOAP | SOAP version, actions, faults | C4, C6 | `transport/soap.py`, `adapters/htng/adapter.py` | V-07 | operations decode/encode per profile | local (generic profile) | BLOCKED (BLK-H1) |
| HTNG schema validation | WSDL/XSD | C2, C9 | `XsdValidator` | V-08 | every sample validates | — | BLOCKED (BLK-H1, BLK-H3) |
| Security | message security / mTLS | C5, B12 | not implemented | V-09 | per profile | — | BLOCKED (BLK-H2) |
| Authentication | client credentials, rotation | A6 | `security/clients.py`, `admin.py` | V-10, V-15 | uniform rejection; overlap honoured | local (`test_security.py`, `test_admin.py`) | LOCAL ready; vendor creds BLK-V4 |
| Business mapping | events per direction | A4, B2/C3 | `domain/stays.py` (+ future mappers) | V-19 | correct `stay.*` operations | local (real `stays_write`, TEST-ONLY gate) | BLOCKED for activation (BLK-B1/B2/B4/B5) |
| HMS stay operations | check-in/out idempotent, ordered, facility-checked | A4, A5 | `domain/stays.py`, repositories | V-12, V-17, V-19 | no duplicate effect; HMS rules enforced | local (`test_hms_domain_mysql.py`) | LOCAL ready |
| Retry / DLQ | re-delivery and fault rules | B4, C6 | `processing/worker.py` | V-13, V-14 | transient retried, permanent → DLQ, redrive audited | local | policy BLK-B7 |
| Facility isolation | property codes | A3 | `security/facility.py`, API scoping | V-16, V-18 | foreign/disabled mappings rejected | local | LOCAL ready; HF-05 BLK-B3 |
| End-to-end acceptance | certification | A6, A7 | whole stack | V-21, V-22 | vendor sign-off | — | BLOCKED (BLK-V5, BLK-V6, BLK-D1) |

No vendor sample has been fabricated; synthetic fixtures are used only for LOCAL rows.

## Execution order once material arrives

1. Encode verified spec/profile (`VERIFIED_OFFICIAL`, with section references).
2. Load samples into `tests/integrations/vendor_contracts/<vendor>/`; run
   `python -m app.integrations.contracts tests/integrations/vendor_contracts --report contract.md`
   until all cases pass (V-01, V-02, V-07, V-08).
3. Re-run the full integration suite (LOCAL rows must stay green).
4. With DBA approval, provision a test HMS environment; with vendor environment, run V-03…V-06,
   V-09, V-11, V-21.
5. With business approval, enable live writes in the test environment only; run V-19 against
   vendor traffic, then V-22.
