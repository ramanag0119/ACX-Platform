# HTNG / FIAS — Implementation Gap Matrix (accelerated sprint, 2026-11-20)

Classification: **COMPLETE** (implemented and tested, protocol-independent) · **PARTIAL** ·
**MISSING** · **BLOCKED BY VENDOR** · **BLOCKED BY APPROVAL**. "Fixed this sprint" items
carry a G-number (see `HTNG_FIAS_ACCELERATED_SPRINT_REPORT.md`). Decision IDs per the
canonical register `HTNG_FIAS_DECISION_REGISTER.md`.

## HTNG

| Capability | Existing implementation | Gap | Evidence | Class | Next action |
|---|---|---|---|---|---|
| SOAP 1.1 / 1.2 envelope parse/build | `transport/soap.py` | inbound endpoint answered **only SOAP 1.1** faults/acks (G2) — fixed | `test_sprint_hardening.py` G2 tests, `test_htng_adapter.py` | COMPLETE | — |
| HTTP media type | endpoint accepted any Content-Type (G3) — fixed: `text/xml` / `application/soap+xml` only, 415 otherwise (after authentication) | — | G3 tests | COMPLETE | — |
| XML parser security | DTD/entity rejection, limits, namespace allow-list | none found | `test_htng_adapter.py` | COMPLETE | — |
| Namespace handling | profile namespaces + allow-list | none found | same | COMPLETE | — |
| Schema registry / version selection | `SchemaRegistry` (`profile_id/version`), production empty | real profiles | `test_htng_adapter.py` | BLOCKED BY VENDOR (HF-07) | vendor WSDL/XSD |
| XSD validation | `XsdValidator` refuses | library + XSD | `test_xsd_validation_requires_approved_dependency` | BLOCKED BY APPROVAL (HF-39) + VENDOR (HF-07) | DBA/ARCH library decision |
| Request/response correlation | `X-Correlation-ID` validated, echoed, propagated | none found | `test_hardening.py` | COMPLETE | — |
| Client authentication / authorization | client auth, facility scoping, rate limit | none found | `test_security.py`, `test_api.py` | COMPLETE | — |
| Message security (WS-Security / mTLS) | not implemented | profile | — | BLOCKED BY VENDOR (HF-08) | vendor security profile |
| Timeouts | `SoapTransport` per-endpoint timeout | none found | `test_soap_call_timeout_is_transient` | COMPLETE | — |
| Retry classification / fault mapping | generic Client/Server classification; transient intake now **503** | vendor-specific faults | G2/G3 tests, `test_htng_adapter.py` | PARTIAL (generic complete) | vendor fault semantics (HF-07) |
| Idempotency / duplicates | shared engine | none found | `test_api.py`, E2E HTNG test | COMPLETE | — |
| Observability | metrics, facility health, audit | none found | `test_health_view.py` | COMPLETE | — |
| Simulator / contract infrastructure | synthetic profiles, contract harness | official samples | `test_vendor_contracts.py` | BLOCKED BY VENDOR | official samples |
| HTNG operations | none in production | everything vendor-specific | — | BLOCKED BY VENDOR (HF-07) | — |

## FIAS

| Capability | Existing implementation | Gap | Evidence | Class | Next action |
|---|---|---|---|---|---|
| TCP lifecycle, reconnect, timeouts | `TcpLink`, `TcpListenerLink` | none found | `test_transport_tcp.py`, `test_transport_server.py` | COMPLETE | — |
| Partial / multiple frames, buffer limits, malformed frames | `DelimitedFramer` | none found | `test_transport_tcp.py` | COMPLETE | — |
| Poison frame on the TCP pump | intake errors classified transient → pump retried a poison frame **forever** (G1) — fixed | — | G1 tests | COMPLETE | — |
| Character-encoding boundaries | grammar accepted non-ASCII-compatible encodings (e.g. UTF-16) with byte-level framing (G4) — fixed | — | G4 tests | COMPLETE | — |
| Parser extensibility | spec-as-data, `RecordSpec`, `unknown_fields` | none found | `test_fias_adapter.py` | COMPLETE | — |
| Message ordering | per-entity ordering; **ties on equal timestamps fell back to random ids** (G5) — fixed with strictly increasing intake stamps | — | G5 tests, E2E FIAS test | COMPLETE | — |
| Durable processing / recovery / leases | shared engine | none found | contract ×2, E2E | COMPLETE | — |
| Connection health | `TransportHealth`, listener rejections | none found | transport tests | COMPLETE | — |
| Records, framing markers, ACK/NAK, heartbeat, link role | not configured | everything protocol-specific | — | BLOCKED BY VENDOR (HF-11 content, HF-06 link rules) | vendor manual |

## Shared engine

| Capability | Existing implementation | Gap | Evidence | Class | Next action |
|---|---|---|---|---|---|
| Facility isolation, auth, rotation, mapping | yes | none found | `test_security.py`, `test_admin.py` | COMPLETE | — |
| Idempotency, retry/backoff, DLQ, audited redrive | yes | none found | `test_repository_contract.py`, `test_exchange.py` | COMPLETE | — |
| Intake error classification | validation vs persistence separated (G1) | — | G1 tests | COMPLETE | — |
| Per-stay ordering | yes + G5 | — | `test_ordering.py`, G5 | COMPLETE | final policy HF-27 |
| Atomic HMS operation + audit | yes | none found | `test_hms_domain_mysql.py`, E2E | COMPLETE | — |
| Worker lease, shutdown, recovery | yes | none found | `test_service.py`, `test_hardening.py`, E2E | COMPLETE | — |
| Health / metrics | yes | none found | `test_health_view.py` | COMPLETE | — |
| Live HMS writes | gated | approvals | `test_domain.py` | BLOCKED BY APPROVAL (HF-01, 02, 05, 18, 19) | decision owners |
| Persistence in HMS DB | candidate schema | DBA | `test_migration_candidate.py` | BLOCKED BY APPROVAL (HF-39) | DBA package |

## End-to-end simulation (disposable MySQL, real `stays_write`)

| Scenario | Evidence |
|---|---|
| FIAS-style TCP: valid, duplicate, malformed, wrong property on bound link, connection drop + reconnect, DB outage during intake, worker crash + lease expiry, ordering, audit | `test_e2e_hms_simulation.py::test_fias_style_tcp_into_real_stay_services` |
| HTNG-style SOAP 1.2 over HTTP: unauthorized client, cross-facility, accepted + ack, duplicate, worker → real check-in, audit | `test_e2e_hms_simulation.py::test_htng_style_soap12_into_real_stay_services` |
| Out-of-order events rejected by real HMS rule; retry → DLQ; redrive | `test_hms_domain_mysql.py`, `test_repository_contract.py` |

Record ids, field ids and XML namespaces used in these simulations are synthetic test
assumptions; they are not FIAS or HTNG definitions.
