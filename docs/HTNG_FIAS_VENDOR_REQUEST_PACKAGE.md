# HTNG / FIAS — Vendor Technical Information Request

Audience: the PMS / interface vendor (and our project lead who sends it). Purpose: obtain
the official material needed to implement and certify the interface. We implement **only**
behaviour stated in your official documents; we do not infer protocol rules.

Please return items marked **Required** before integration development starts; items marked
**Before certification** before joint testing.

## Cover note (ready to send — fill the bracketed fields; not sent by the project tooling)

> Subject: Interface documentation request — [PMS product] ↔ HMS ([property / group])
>
> Hello [vendor contact],
>
> We are preparing the interface between [PMS product, version] and our Hotel Management
> System for [property list]. To build and certify it strictly to your specification, please
> provide the items listed below — official documents, your implementation profile, and
> sample inbound and outbound messages including acknowledgements and error cases — together
> with access to a test environment and your certification criteria.
>
> Items in Part A apply to every interface; Part B applies if you offer FIAS, Part C if you
> offer HTNG. Please indicate which items do not apply to your product.
>
> Kind regards, [name, role, contact]

Items 1–13 of the onboarding requirement map as follows: product/version A1; protocol and
version A2/B1/C1; FIAS manual B1; WSDL/XSD C2; vendor profile C1; security B12/C5; connection
architecture B7/C3/C10; inbound samples B10/C8; outbound samples B10/C8 (both directions);
acknowledgements and errors B4/C6/C7; business operations A4; test environment A6;
certification A7.

## Part A — For every vendor

| # | Item | Required | Why we need it |
|---|---|---|---|
| A1 | Vendor, PMS product name and version; hosting model | Required | Selects protocol, profile and deployment |
| A2 | Interface(s) offered for this product: FIAS, HTNG, other | Required | We build only what is supported |
| A3 | Properties in scope and their exact property / hotel codes, incl. case rules | Required | Our routing maps your codes to our facilities; case handling is decision HF-05 |
| A4 | Which business events/operations you send and accept, per direction | Required | Scope of mapping and testing |
| A5 | System-of-record expectations (who owns reservations, guest data, room status) | Required | Business decisions HF-01 / HF-02 |
| A6 | Test environment access, credentials process, test property | Before certification | Interoperability evidence |
| A7 | Certification / acceptance procedure and criteria | Before certification | Defines "done" |
| A8 | Support contacts and escalation for interface faults | Before certification | Operations |

## Part B — FIAS (if offered)

| # | Item | Required | Why we need it |
|---|---|---|---|
| B1 | Official FIAS interface manual / specification, exact version, and the licensed record set for this property | Required | All record parsing is blocked on it (HF-11) |
| B2 | Record definitions: record ids, field ids, mandatory/optional, lengths, formats, encodings | Required | Our parser/serializer is driven by these tables |
| B3 | Message framing: start/end markers, escaping, max message length | Required | Transport framing is configurable but has no default |
| B4 | Acknowledgement behaviour: ACK/NAK records or bytes, timing, what happens on NAK / timeout | Required | We send nothing back until this is defined |
| B5 | Link start-up / shutdown sequence, sequence numbers, resynchronisation | Required | Recovery after outages |
| B6 | Heartbeat / keep-alive rules and timeouts | Required | Distinguishing idle from dead links |
| B7 | Connection direction: who listens, host/port, one link per property or shared | Required | We support both client and listener modes; choose one |
| B8 | Character set, date/time formats and time zone of timestamps | Required | Correct mapping without guessing |
| B9 | Which field uniquely identifies an event (for duplicate detection) | Required | Idempotency; we will not fabricate keys |
| B10 | Official sample messages for every record in scope, **inbound and outbound**, incl. ACK/NAK and error cases | Required | Contract tests (`app.integrations.contracts`) |
| B11 | Vendor-specific extensions, if any | Required | Explicitly supported or rejected |
| B12 | Network path and security (VPN, IP ranges, TLS if any) | Before certification | HF-24 |

## Part C — HTNG (if offered)

| # | Item | Required | Why we need it |
|---|---|---|---|
| C1 | HTNG specification family and release, and your **implementation profile** | Required | Vendors implement different subsets (HF-07) |
| C2 | WSDL(s) and complete XSD bundle, with versions and namespaces | Required | Schema validation and operation set (HF-07) |
| C3 | Supported operations per direction; sync vs async; who hosts which endpoint | Required | Endpoint design |
| C4 | SOAP version (1.1 / 1.2), SOAPAction values | Required | Envelope handling |
| C5 | Message security: WS-Security token type, signing/encryption, timestamps/nonce, mTLS, certificates | Required | Authentication and replay protection (HF-08) |
| C6 | Fault semantics: fault codes, which are retryable | Required | Retry vs dead-letter decisions |
| C7 | Acknowledgement / response semantics per operation | Required | We return only profile-defined acknowledgements |
| C8 | Official sample requests and responses for every operation, **both directions**, incl. faults | Required | Contract tests |
| C9 | Schema-version compatibility policy (how versions change, deprecation) | Required | Versioned schema registry |
| C10 | Endpoint URLs per environment, IP ranges, TLS details | Before certification | HF-24 |

Internal note (not for the vendor): XSD validation also needs approval of a validation
library (`xmlschema` or `lxml`) under HF-39.

## Part D — How we will use the material

Each item is traced to code and tests below. Rows stay **PENDING VENDOR DOCUMENTATION**
until the cited section exists; nothing is implemented from assumption.

### D.1 FIAS requirement traceability

| Req | Requirement | Source (vendor doc §) | Module | Test | Status |
|---|---|---|---|---|---|
| F-01 | Framing markers / escaping / max length | B3 — pending | `transport/framing.py` (`DelimitedFramer`, configurable) | `test_transport_tcp.py` (generic) + contract | PENDING VENDOR DOCUMENTATION |
| F-02 | Record grammar (separator, id lengths, encoding) | B2/B8 — pending | `adapters/fias/spec.py` `WireGrammar` | `test_fias_adapter.py` (synthetic) + contract | PENDING VENDOR DOCUMENTATION |
| F-03 | Record definitions per record id | B2 — pending | `spec.py` `RecordSpec` | contract | PENDING VENDOR DOCUMENTATION |
| F-04 | Event identity / duplicate key | B9 — pending | `RecordSpec.idempotency_fields` | contract | PENDING VENDOR DOCUMENTATION |
| F-05 | ACK / NAK | B4 — pending | `LinkPump.responder` (none in production) | contract | PENDING VENDOR DOCUMENTATION |
| F-06 | Link start-up, sequence, resync | B5 — pending | not implemented | — | BLOCKED |
| F-07 | Heartbeat | B6 — pending | not implemented (idle is not an error) | — | BLOCKED |
| F-08 | Connection direction | B7 — pending | `TcpLink` / `TcpListenerLink` | `test_transport_tcp.py`, `test_transport_server.py` | IMPLEMENTED, TESTED (choice pending) |
| F-09 | Record → canonical `stay.*` mapping | B2 + A4 — pending | `adapters/fias/adapter.py` | contract + `test_hms_domain_mysql.py` | PENDING VENDOR DOCUMENTATION |
| F-10 | Vendor extensions | B11 — pending | `RecordSpec.unknown_fields` | contract | PENDING VENDOR DOCUMENTATION |

### D.2 HTNG requirement traceability

| Req | Requirement | Source | Module | Test | Status |
|---|---|---|---|---|---|
| H-01 | Operation set and profile | C1/C3 — pending | `adapters/htng/schema.py` `SchemaProfile` | contract | PENDING VENDOR DOCUMENTATION |
| H-02 | XSD validation | C2 — pending; library HF-39 | `XsdValidator` (refuses) | `test_xsd_validation_requires_approved_dependency` | BLOCKED |
| H-03 | SOAP version / SOAPAction | C4 — pending | `transport/soap.py` (1.1 + 1.2 generic) | `test_htng_adapter.py` | IMPLEMENTED, TESTED (generic) |
| H-04 | WS-Security / mTLS | C5 — pending | not implemented | — | BLOCKED (HF-08) |
| H-05 | Fault semantics | C6 — pending | `SoapTransport` generic Client/Server classification | `test_soap_server_errors_and_faults` | IMPLEMENTED (generic), PENDING VENDOR DOCUMENTATION |
| H-06 | Acknowledgements | C7 — pending | `OperationSpec.response_builder` | `test_profile_ack_response` (synthetic) | PENDING VENDOR DOCUMENTATION |
| H-07 | Schema versioning | C9 — pending | `SchemaRegistry` (`profile_id/version`) | `test_registry_refuses_unverified_profiles_and_production_opt_in` | IMPLEMENTED, TESTED (registry) |
| H-08 | Element → canonical mapping | C2/C8 — pending | `OperationSpec.inbound_mapper` | contract | PENDING VENDOR DOCUMENTATION |

## Part E — Vendor response tracker (one copy per vendor)

Vendor: ______ · Product/version: ______ · Request sent (date, by): ______ · Status: NOT SENT

| Item | Requested | Received (date) | Document / version / reference | Reviewed by | Accepted? | Follow-up |
|---|---|---|---|---|---|---|
| A1 Product, version, hosting | ☐ | | | | | |
| A2 Interfaces + versions | ☐ | | | | | |
| A3 Property codes + case rules | ☐ | | | | | |
| A4 Business operations per direction | ☐ | | | | | |
| A5 System-of-record expectations | ☐ | | | | | |
| A6 Test environment + credentials process | ☐ | | | | | |
| A7 Certification criteria | ☐ | | | | | |
| B1–B11 FIAS manual, records, framing, ACK, link, heartbeat, direction, formats, event identity, samples, extensions | ☐ | | | | | |
| B12 FIAS network/security | ☐ | | | | | |
| C1–C9 HTNG profile, WSDL/XSD, operations, SOAP, security, faults, acks, samples, versioning | ☐ | | | | | |
| C10 HTNG endpoints/TLS | ☐ | | | | | |

Rule: an item counts as received only with a document reference; a sample counts only if it
is from the vendor (synthetic fixtures never count).

## Part F — Delivery

Send documents and samples to the project lead. **Samples are kept outside the repository**
(an access-controlled location chosen by the project lead) with a `manifest.json` (format in
`backend/app/integrations/contracts.py`). The contract report is produced from that location,
e.g. `python -m tests.integrations.certification replay-vendor <dir>`, or
`python -m app.integrations.contracts`.

> **Reconciled 2026-11-20 (stricter rule applied).** This section previously said samples go
> into `backend/tests/integrations/vendor_contracts/<vendor>/`. That conflicted with
> `HTNG_FIAS_CERTIFICATION_RUNBOOK.md`, which keeps samples outside the repository until HF-21
> (retention, encryption and guest-data handling) is approved. The stricter rule applies: no
> vendor sample, guest data, credential or sensitive payload is placed in the repository until
> HF-21 is approved and a data-handling approach is formally recorded. Samples marked
> `contains-guest-data` are refused by the replay tool until then.
