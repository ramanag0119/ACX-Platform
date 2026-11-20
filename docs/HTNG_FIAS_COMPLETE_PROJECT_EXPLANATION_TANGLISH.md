<div class="cover"><div class="cover-band"></div><div class="cover-title">HTNG &amp; FIAS Integration</div><div class="cover-sub">Complete Project Explanation — Tanglish Edition</div><div class="cover-status">Official status: FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING</div><div class="cover-meta">Repository: ACX_PLATFORM\ACX-Platform · Branch: feature/htng-fias-on-develop · HEAD 46904fd<br/>Prepared: 2026-11-20 · Source: actual code + project reports (verified in this repository)</div><div class="cover-note">Indha document project owner-ku full-ah purinjukka ezhudhappattadhu. Synthetic testing-ah vendor certification-nu sollala. Production-ready-nu claim pannala.</div></div>

<div class="pagebreak"></div>

# Indha Document-ah Eppadi Padikkanum

Indha document-la namma repository-la actual-ah enna build pannirukkom, yen build pannom, eppadi work aagudhu, enna test pannom, innum enna pending — ellathayum Tanglish-la explain pannirukkom.

Moonu rules follow pannirukkom:

1. **Code dhaan first evidence.** Report-la "implemented"-nu irundha, adhoda source file-ah open panni verify pannirukkom. Verify panna mudiyaadhadhu "not verified"-nu clear-ah mark pannirukkom.
2. **Synthetic test ≠ vendor certification.** Namma tests ellam disposable database, synthetic messages vechu panninadhu. Real HTNG/FIAS vendor-oda oru message kooda innum exchange aagala.
3. **Status maaraadhu.** Official status eppovum: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**.

Ovvoru technical concept-kum indha format use pannirukkom:

| Label | Artham |
|---|---|
| **Enna** | Adhu enna |
| **Yen venum** | Edhukku thevai |
| **Eppadi work aagudhu** | Mechanism |
| **Namma project-la** | Indha repository-la eppadi implement pannirukkom |
| **Example** | Simple real-world example |
| **Enga irukku** | Repository-relative file path (class/function name) |

> **Evidence note:** File path ellam `ACX-Platform` folder-oda relative path. Backend integration code ellam `backend/app/integrations/` ulla irukku; frontend dashboard `frontend/src/features/integrations/` ulla irukku. Test counts latest reports-la irundhu eduthadhu; indha document ezhudhumbodhu `pytest --collect-only` vechu backend count-ah (517) re-check pannom.

## Table of Contents

- Chapter 1 – Project Introduction
- Chapter 2 – Basic Technical Concepts
- Chapter 3 – Complete System Architecture
- Chapter 4 – Common Backend Implementation
- Chapter 5 – HTNG Complete Explanation
- Chapter 6 – FIAS Complete Explanation
- Chapter 7 – Complete Message Processing Flow
- Chapter 8 – Database and Data Flow
- Chapter 9 – Security Architecture
- Chapter 10 – Observability Dashboard
- Chapter 11 – API Documentation
- Chapter 12 – Testing and Verification
- Chapter 13 – Known Issues and Limitations
- Chapter 14 – Pending Vendor and Business Decisions
- Chapter 15 – Actual Work Completed vs Pending
- Chapter 16 – Future Execution Roadmap
- Chapter 17 – Glossary and Learning Reference
- Chapter 18 – Final Project Status

# Chapter 1 – Project Introduction

## 1.1 HMS-um PMS-um — enna relationship?

**HMS (Hotel Management System)** — idhu namma product. Rooms, stays (guest thangura period), service requests, devices, energy, occupancy — ellathayum namma HMS manage pannudhu.

**PMS (Property Management System)** — hotel-oda main front-office software. Reservations, guest check-in/check-out, folio (bill) ellam PMS-la dhaan nadakkum. Hotels Opera, Protel maadhiri vendor PMS-ah use pannuvaanga.

Problem enna-na: guest PMS-la check-in aanaa, adhu namma HMS-kum theriyanum — room "Occupied"-ah maaranum, devices welcome mode-ku pogalaam, housekeeping-ku update varanum. Manual-ah update panna mistakes varum, delay varum. Adhunaala **PMS-um HMS-um automatic-ah pesanum**. Andha pesura bridge dhaan indha project.

> **Important:** Indha project-la *endha* PMS vendor-oda connect pannanum-nu innum decide aagala. Adhu decision **HF-03** (Open). Endha vendor peraiyum naanga assume pannala.

## 1.2 Yen external integration venum?

- **Automation:** check-in/check-out manual entry illama HMS-la reflect aaganum.
- **Accuracy:** rendu system-la vera vera data irundha guest experience kettu pogum.
- **Speed:** guest room-ku pogumbodhe room ready-ah irukkanum.
- **Audit:** yaar, eppo, enna maathunaanga-nu track pannanum.

## 1.3 HTNG enna?

**HTNG (Hospitality Technology Next Generation)** oru hospitality industry standards family. Idhula messages **XML** format-la irukkum, **SOAP** envelope-la wrap aagi **HTTP** mela anuppuvaanga. Ovvoru vendor-um HTNG-oda oru "subset"-ai implement pannuvaanga — adha **implementation profile** nu solluvaanga. Adhunaala vendor-oda **WSDL**, **XSD** files illama exact message structure theriyaadhu (decision **HF-07**).

## 1.4 FIAS enna?

**FIAS (Fidelio Interface Application Specification)** — PMS-um interface systems-um (telephone, minibar, door lock maadhiri) pesura oru record-based protocol. Idhu **TCP** connection mela chinna chinna text **records**-ah anuppum. Record format, framing characters, ACK rules, heartbeat ellam **official FIAS manual**-la dhaan irukkum (decisions **HF-11**, **HF-06**). Andha manual namma kitta illa.

## 1.5 Yen rendu protocol-um?

Endha PMS vendor-nu theriyaadhadhunaala (HF-03), andha vendor endha interface offer pannuvaanga-nu theriyaadhu (HF-04). Sila vendors FIAS, sila HTNG, sila rendum. Adhunaala:

- Rendu protocol-kum common-aana **shared foundation** (authentication, facility mapping, durable processing, retry, DLQ, audit, monitoring) build pannom.
- Protocol-specific parts (FIAS records, HTNG schemas) **specification-driven framework**-ah build pannom — official spec vandha udane configure pannalaam, guess panni code ezhudhala.

## 1.6 Project objective

PMS-la irundhu vara stay events (check-in, check-out) safe-ah, duplicate illama, correct facility-ku, correct order-la, audit-oda HMS-ku kondu varanum; operators-ku full visibility kudukkanum; vendor validation mudinja appuram dhaan production-ku pogum.

## 1.7 Current implementation scope

| Scope | Status |
|---|---|
| Shared integration foundation (backend) | Implemented, internally tested |
| HTNG SOAP endpoint + generic framework | Implemented; production profile illa → **BLOCKED** (HF-07) |
| FIAS TCP + record framework | Implemented; production spec illa → **BLOCKED** (HF-11); production process-la wire aagala |
| HMS stay check-in/check-out handler | Implemented; live writes **gate closed** (HF-01/02/05/19) |
| Operator APIs + observability APIs | Implemented |
| Integrations dashboard (5 pages) | Implemented |
| Vendor validation | **Pending** — vendor-e innum identify aagala |

## 1.8 System overview diagram

<figure class="diagram" id="fig-overview"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 300" width="100%" role="img" style="max-width:700px"><defs><marker id="a1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="10" y="20" width="190" height="96" rx="8" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.6"/><text x="105.0" y="41.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">PMS (vendor system)</text><text x="105.0" y="56.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">reservations,</text><text x="105.0" y="72.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">check-in/out</text><text x="105.0" y="88.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">vendor not named yet</text><text x="105.0" y="103.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HF-03)</text><rect x="230" y="20" width="190" height="46" rx="8" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.6"/><text x="325.0" y="39.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HTNG</text><text x="325.0" y="55.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">SOAP/XML over HTTP</text><rect x="230" y="80" width="190" height="46" rx="8" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.6"/><text x="325.0" y="99.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">FIAS</text><text x="325.0" y="115.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">records over TCP</text><rect x="460" y="30" width="220" height="70" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="570.0" y="53.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Integration layer (this</text><text x="570.0" y="69.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">project)</text><text x="570.0" y="85.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">backend/app/integrations</text><rect x="460" y="160" width="220" height="60" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="570.0" y="186.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HMS (our system)</text><text x="570.0" y="202.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">stays, rooms, facilities</text><rect x="20" y="160" width="250" height="60" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="145.0" y="186.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Operators</text><text x="145.0" y="202.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">Integrations dashboard (5 pages)</text><line x1="200.0" y1="68.0" x2="230.0" y2="43.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a1)"/><line x1="200.0" y1="68.0" x2="230.0" y2="103.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a1)"/><line x1="420.0" y1="43.0" x2="460.0" y2="65.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a1)"/><line x1="420.0" y1="103.0" x2="460.0" y2="65.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a1)"/><line x1="570.0" y1="100.0" x2="570.0" y2="160.0" stroke="#374151" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a1)"/><rect x="491.4" y="113.0" width="157.2" height="34" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="570.0" y="127.0" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">check-in/out</text><text x="570.0" y="140.7" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">(gated: HF-01/02/05/19)</text><path d="M270,190.0 L365.0,190.0 L365.0,105.0 L460,105.0" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a1)"/><rect x="296.0" y="137.5" width="138.0" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="365.0" y="151.3" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">read-only monitoring</text><rect x="10" y="275" width="16" height="12" rx="2" fill="#F3F4F6" stroke="#4B5563"/><text x="32.0" y="284.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">External</text><rect x="84.8" y="275" width="16" height="12" rx="2" fill="#E0F2FE" stroke="#0369A1"/><text x="106.8" y="284.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Protocol</text><rect x="159.6" y="275" width="16" height="12" rx="2" fill="#DCFCE7" stroke="#15803D"/><text x="181.6" y="284.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Integration</text><rect x="252.7" y="275" width="16" height="12" rx="2" fill="#FCE7F3" stroke="#BE185D"/><text x="274.7" y="284.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">HMS</text><rect x="297.0" y="275" width="16" height="12" rx="2" fill="#EDE9FE" stroke="#6D28D9"/><text x="319.0" y="284.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Dashboard</text></svg><figcaption>Figure 1: System overview</figcaption></figure>

Diagram-la dashed line na "gated/pending" — andha path code-la irukku, aana approval illama open aagaadhu.

## 1.9 Indha integration achieve panna vendiyadhu

- PMS check-in → HMS stay active, room Occupied (real HMS business rules use panni).
- PMS check-out → HMS stay closed.
- Duplicate message vandhaalum oru thadava dhaan apply aaganum.
- Oru facility-oda data vera facility user-ku theriyakoodadhu.
- Fail aana messages lose aagakoodadhu — DLQ-la irundhu operator controlled-ah redrive pannalaam.
- Ellathukkum audit trail irukkanum.

**Chapter 1 summary:** HMS-um PMS-um pesura bridge build pannirukkom. Foundation ready. Endha vendor-nu decide aagala; vendor documents illa; adhunaala protocol adapters BLOCKED state-la irukku.

# Chapter 2 – Basic Technical Concepts

Indha chapter-la project purinjukka thevaiyaana basic terms. Ovvondhukkum "Namma project-la" & "Enga irukku" kuduthirukkom.

## 2.1 PMS

- **Enna:** Hotel-oda front-office software (reservations, check-in/out, billing).
- **Yen venum:** Guest data-voda "source" adhu dhaan; adhu kooda pesaama automation illa.
- **Eppadi work aagudhu:** PMS events (check-in maadhiri) external systems-ku interface vazhiya anuppum.
- **Namma project-la:** PMS-ah "client"-ah treat pannrom — ovvoru vendor link-kum oru integration client record.
- **Example:** Front desk-la Ravi check-in aanaar → PMS "check-in" event anuppudhu.
- **Enga irukku:** Client concept: `backend/app/integrations/security/clients.py` (`IntegrationClient`).

## 2.2 Protocol

- **Enna:** Rendu systems pesura rules — message format, order, response.
- **Yen venum:** Rendu pakkamum same rules follow pannaa dhaan purinjukka mudiyum.
- **Eppadi work aagudhu:** Format (XML/records), transport (HTTP/TCP), acknowledgement rules.
- **Namma project-la:** `Protocol` enum-la `fias`, `htng`, `test` (test & simulator-ku mattum) irukku.
- **Example:** Phone call-la "Hello" sonnaa "Hello" thirumba solradhu oru simple protocol.
- **Enga irukku:** `backend/app/integrations/core/envelope.py` (`Protocol`).

## 2.3 API

- **Enna:** Oru software innoru software-ku kudukkura defined entry point (URL + method).
- **Yen venum:** Dashboard, vendor, tools ellam backend kooda pesa.
- **Eppadi work aagudhu:** HTTP request (GET/POST) → server process → JSON/XML response.
- **Namma project-la:** FastAPI router-la 18 integration endpoints (Chapter 11).
- **Example:** `GET /api/v1/integrations/observability/overview` → dashboard numbers.
- **Enga irukku:** `backend/app/integrations/api/router.py`.

## 2.4 SOAP

- **Enna:** XML message-ah oru standard "envelope"-la wrap panni anuppura protocol. Versions: **SOAP 1.1** (`text/xml`) and **SOAP 1.2** (`application/soap+xml`).
- **Yen venum:** HTNG messages SOAP mela dhaan varum.
- **Eppadi work aagudhu:** `Envelope` → optional `Header` → `Body` (actual message). Error-na `Fault`.
- **Namma project-la:** Rendu version-um support; error vandha request vandha *same version*-la fault return pannrom; wrong content-type-ku 415.
- **Example:** Courier cover (envelope) ulla letter (body) — cover mela address (header).
- **Enga irukku:** `backend/app/integrations/transport/soap.py` (`parse_soap`, `SoapVersion`, `build_soap_envelope`); fault: `api/router.py` (`soap_fault`).

## 2.5 XML

- **Enna:** Tags vechu structured data ezhudhura text format (`<Stay><Room>101</Room></Stay>`).
- **Yen venum:** HTNG messages XML.
- **Eppadi work aagudhu:** Elements, attributes, namespaces.
- **Namma project-la:** Untrusted XML-ah safe-ah parse panna special parser (Chapter 9).
- **Example:** `<Guest><Name>…</Name></Guest>`.
- **Enga irukku:** `backend/app/integrations/transport/xml_security.py` (`parse_untrusted_xml`).

## 2.6 WSDL

- **Enna:** SOAP service-oda "menu card" — endha operations irukku, endha message structure, endha endpoint.
- **Yen venum:** HTNG vendor endha operations support pannuvaanga-nu exact-ah theriya.
- **Eppadi work aagudhu:** XML document; operations, input/output messages, bindings define pannum.
- **Namma project-la:** Innum receive pannala (HF-07). Adhunaala production `SchemaRegistry` empty.
- **Example:** Hotel restaurant menu — enna order pannalaam, enna varum.
- **Enga irukku:** Vendor request item C2 — `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md`.

## 2.7 XSD

- **Enna:** XML message-oda "rules book" — endha element mandatory, data type enna, length enna.
- **Yen venum:** Varra message valid-aa-nu check panna.
- **Eppadi work aagudhu:** Validator XML-ah XSD kooda compare pannum.
- **Namma project-la:** `XsdValidator` class irukku, aana **refuse** pannum — approved validation library (`xmlschema` or `lxml`) illa (HF-39) and official XSD illa (HF-07). Meanwhile synthetic profile-ku `StructuralValidator` use pannrom.
- **Example:** Form-la "Phone number 10 digits mattum" maadhiri rule.
- **Enga irukku:** `backend/app/integrations/adapters/htng/schema.py` (`XsdValidator`, `StructuralValidator`).

## 2.8 TCP

- **Enna:** Rendu computers-kulla reliable byte stream connection.
- **Yen venum:** FIAS TCP mela dhaan pesum.
- **Eppadi work aagudhu:** Connect → bytes send/receive → close. Message boundaries TCP-ku theriyaadhu — adhukku dhaan "framing".
- **Namma project-la:** Client mode (`TcpLink`) and listener mode (`TcpListenerLink`) rendum.
- **Example:** Phone call line — line open-ah irukku, pesuradhu continuous.
- **Enga irukku:** `backend/app/integrations/transport/tcp.py`, `transport/tcp_server.py`.

## 2.9 Parser

- **Enna:** Raw text/bytes-ah structured data-va maathura code.
- **Yen venum:** Vendor anuppura bytes-ah namma system purinjukkanum.
- **Eppadi work aagudhu:** Grammar/spec padi split panni, validate panni, fields-ah extract pannum.
- **Namma project-la:** FIAS-ku `parse_record` (spec-driven); HTNG-ku SOAP + XML parser + profile mapper.
- **Example:** "RN101|GNRavi" → `{room: 101, guest: Ravi}`.
- **Enga irukku:** `backend/app/integrations/adapters/fias/codec.py` (`parse_record`, `serialize_record`).

## 2.10 Payload

- **Enna:** Message-oda actual content (body).
- **Yen venum:** Business data adhula dhaan irukku.
- **Eppadi work aagudhu:** Metadata (who, when, type) separate; payload separate.
- **Namma project-la:** Canonical JSON body `integration_inbound_payloads.body_canonical`-la; raw wire bytes store pannuradhu **default off** (`INTEGRATION_STORE_RAW_WIRE_PAYLOAD=false`, HF-21 pending).
- **Example:** Letter-oda content = payload; cover details = metadata.
- **Enga irukku:** `backend/app/integrations/processing/sql_models.py` (`InboundPayloadRow`).

## 2.11 Inbound message

- **Enna:** Vendor → namma pakkam varra message.
- **Yen venum:** Check-in/check-out events inbound-ah dhaan varum.
- **Eppadi work aagudhu:** Transport → adapter → gateway → database → worker.
- **Namma project-la:** `integration_inbound_messages` table-la store; direction eppovum `inbound`.
- **Example:** PMS "Guest checked in, room 101".
- **Enga irukku:** `backend/app/integrations/exchange/gateway.py` (`ExchangeGateway.receive`).

## 2.12 Outbound message

- **Enna:** Namma pakkam irundhu vendor-ku pogura message.
- **Yen venum:** Acknowledgements / receipts / future updates.
- **Eppadi work aagudhu:** "Outbox pattern" — first database-la queue pannuvom, appuram relay anuppum.
- **Namma project-la:** `integration_outbox_messages` + `OutboxRelay`. Aana **production sender configure aagala** — outbox rows PENDING-la wait pannum. `HtngSoapSender` class define aagirukku, aana app-la endha idathulayum instantiate aagala.
- **Example:** Post office box-la letter podradhu; postman edukkum vara adhu safe.
- **Enga irukku:** `backend/app/integrations/processing/worker.py` (`OutboxRelay`), `adapters/htng/sender.py` (`HtngSoapSender`).

## 2.13 Facility mapping

- **Enna:** Vendor side property code-ai (e.g. "HOTEL-A") namma HMS-la irukkura correct facility ID-oda connect pannradhu.
- **Yen venum:** Message endha hotel-ku-nu theriyanum; wrong hotel-ku pona serious data leak.
- **Eppadi work aagudhu:** (client, normalized code) → facility_id lookup. Mapping client-scoped — rendu clients same code use pannaalum vera vera facility-ku pogalaam.
- **Namma project-la:** `FacilityResolver.resolve()`; mappings DISABLED-ah create aagum, explicit-ah enable pannanum; case rule EXACT (HF-05 pending).
- **Example:** Courier "Chennai Branch" code → namma office address.
- **Enga irukku:** `backend/app/integrations/security/facility.py` (`FacilityResolver`, `CaseSensitivity`, `normalize_code`); SQL: `security/sql_stores.py` (`SqlFacilityMappingStore`).

## 2.14 Idempotency

- **Enna:** Idempotency na same message rendu thadava vandhaalum, same business operation duplicate-ah execute aagama prevent panra mechanism.
- **Yen venum:** Network retry-la vendor same message-ah thirumba anuppalaam; check-in rendu thadava apply aagakoodadhu.
- **Eppadi work aagudhu:** (client, facility, idempotency key) unique. Same key + same content fingerprint → "duplicate"; same key + different content → conflict (reject).
- **Namma project-la:** `integration_idempotency_keys` table-la UNIQUE constraint; fingerprint = canonical JSON SHA-256.
- **Example:** Bank-la same cheque number rendu thadava clear aagaadhu.
- **Enga irukku:** `backend/app/integrations/core/hashing.py` (`idempotency_fingerprint`, `payload_hash`); `processing/sql_repository.py` (`SqlIntegrationRepository.accept`).

## 2.15 Retry

- **Enna:** Temporary failure aana thirumba try pannradhu.
- **Yen venum:** Database busy, HMS temporarily down maadhiri transient problems-ku.
- **Eppadi work aagudhu:** Error "transient"-aa "permanent"-aa-nu classify; transient-ku mattum retry.
- **Namma project-la:** `RetryPolicy` — max 5 attempts (default).
- **Example:** Phone busy-na konja neram kazhichu thirumba call pannradhu.
- **Enga irukku:** `backend/app/integrations/core/retry.py` (`RetryPolicy`, `RetryDecision`).

## 2.16 Backoff

- **Enna:** Ovvoru retry-kum wait time increase pannradhu.
- **Yen venum:** Udane udane retry panna system-ku load adhigamaagum.
- **Eppadi work aagudhu:** delay = base × multiplier^(attempt-1), max cap.
- **Namma project-la:** 5 s → 10 s → 20 s … max 900 s (multiplier 2.0). Optional jitter (`full_jitter`).
- **Example:** Traffic jam-la ovvoru thadavaiyum konjam adhigam wait pannradhu.
- **Enga irukku:** `backend/app/integrations/core/retry.py` (`RetryPolicy.delay_for`).

## 2.17 Worker

- **Enna:** Background-la queue-la irundhu messages edukkura process.
- **Yen venum:** Vendor-ku udane response kudukkalaam; heavy HMS work appuram nadakkalaam.
- **Eppadi work aagudhu:** Poll → claim → process → result record.
- **Namma project-la:** `InboundWorker` (inbound), `OutboxRelay` (outbound), `IntegrationService` process — default-ah start aagaadhu (`INTEGRATION_ENABLED=false` → exit code 3).
- **Example:** Restaurant-la waiter order edukkiraar; kitchen staff (worker) cook pannuvaanga.
- **Enga irukku:** `backend/app/integrations/processing/worker.py`, `backend/app/integrations/service.py`.

## 2.18 Lease

- **Enna:** Oru worker oru message-ah "konja neram naan dhaan handle pannuren"-nu lock pannradhu.
- **Yen venum:** Rendu workers same message-ah process panna koodadhu; worker crash aana message stuck aagakoodadhu.
- **Eppadi work aagudhu:** Lease owner + token + expiry. Expire aana vera worker re-claim pannalaam. Old worker late-ah commit panna try pannaa token match aagaadhu (**fencing**) → reject.
- **Namma project-la:** `WORKER_LEASE_SECONDS` default 60; `SKIP LOCKED` claim; completion-la lease entry-lum exit-lum check.
- **Example:** Library book borrow — due date mudinja vera aal edukkalaam.
- **Enga irukku:** `backend/app/integrations/processing/sql_repository.py` (`claim`, `completion`); `core/errors.py` (`LeaseLost`).

## 2.19 DLQ (Dead Letter Queue)

- **Enna:** DLQ na repeated-ah fail aagura messages-ai separate-ah store panni, operator investigate pannitu controlled-ah retry panna use panra mechanism.
- **Yen venum:** Fail aana messages lose aagakoodadhu; infinite retry-um aagakoodadhu.
- **Eppadi work aagudhu:** Permanent error or attempts exhausted → status `DEAD_LETTER`.
- **Namma project-la:** Separate table illa — same messages table-la status `DEAD_LETTER`; dashboard-la "Failed Messages / DLQ" page.
- **Example:** Post office-la address illaadha letters "returned" section.
- **Enga irukku:** `backend/app/integrations/core/lifecycle.py`; `processing/worker.py` (`InboundWorker._fail`).

## 2.20 Redrive

- **Enna:** DLQ-la irukkura message-ah thirumba processing-ku anuppradhu.
- **Yen venum:** Root cause fix aana appuram message-ah replay panna.
- **Eppadi work aagudhu:** DEAD_LETTER → PENDING, attempt count 0; reason mandatory; audit record.
- **Namma project-la:** `POST /api/v1/integrations/messages/{id}/redrive` — `facility_management` **write** permission, reason 10–500 characters. Dashboard-la redrive button **illa** (read-only).
- **Example:** Returned letter-ku correct address pottu thirumba post pannradhu.
- **Enga irukku:** `backend/app/integrations/processing/sql_repository.py` (`redrive`), `api/router.py` (`redrive`).

## 2.21 Audit

- **Enna:** Yaar, eppo, enna action panninaanga-nu permanent record.
- **Yen venum:** Security, troubleshooting, compliance.
- **Eppadi work aagudhu:** Action nadakkura *same transaction*-la audit row ezhudhradhu — data-vum audit-um mismatch aagaadhu.
- **Namma project-la:** `integration_audit_events` table; redrive, mapping changes, client changes, HMS stay changes (`domain.stay.check_in` maadhiri) ellam audit.
- **Example:** Bank passbook entry.
- **Enga irukku:** `backend/app/integrations/processing/repository.py` (`AuditDraft`, `AuditEvent`); `admin.py` (`IntegrationAdmin._audit`).

## 2.22 Observability

- **Enna:** System ulla enna nadakkudhu-nu veliya irundhu paakka mudiyura capability (counts, health, errors).
- **Yen venum:** Problem vandha operator udane kandupidikkanum.
- **Eppadi work aagudhu:** Durable database counts + in-process counters + health probes.
- **Namma project-la:** Overview/messages/DLQ APIs + 5-page dashboard. Measure panna mudiyaadha value-va **0-nu kaatta maattom** — "Data unavailable" / "Not observable".
- **Example:** Car dashboard — speed, fuel, warning lights.
- **Enga irukku:** `backend/app/integrations/observability.py` (`build_overview`), `processing/activity.py`.

## 2.23 RBAC (Role-Based Access Control)

- **Enna:** User-oda role-ku kudutha permission padi dhaan access.
- **Yen venum:** Ellarum ellathayum paakka / maathakoodadhu.
- **Eppadi work aagudhu:** Role → module → read/write grant.
- **Namma project-la:** Integration APIs existing HMS module `facility_management` use pannudhu (read = view, write = redrive/mapping). Separate integration module illa — adhu add panna schema/seed change (HF-39).
- **Example:** Office-la staff ID card — sila doors mattum open.
- **Enga irukku:** `backend/app/api/deps.py` (`require_permission`); `backend/app/integrations/api/router.py` (`RBAC_MODULE`, `Reader`, `Writer`); frontend `frontend/src/core/rbac/modules.ts`.

**Chapter 2 summary:** Indha terms purinjaa, remaining chapters easy-ah follow pannalaam. Mukkiyamaana moonu: idempotency (duplicate prevent), lease (safe parallel processing), DLQ (failures lose aagaama).

# Chapter 3 – Complete System Architecture

## 3.1 Architecture diagram

<figure class="diagram" id="fig-architecture"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 690" width="100%" role="img" style="max-width:700px"><defs><marker id="a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="10" width="300" height="44" rx="8" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.6"/><text x="170.0" y="36.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Vendor PMS — HTNG client</text><rect x="380" y="10" width="300" height="44" rx="8" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.6"/><text x="530.0" y="36.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Vendor PMS — FIAS link</text><rect x="20" y="74" width="300" height="86" rx="8" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.6"/><text x="170.0" y="105.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HTNG endpoint (FastAPI)</text><text x="170.0" y="121.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">POST /api/v1/integrations/htng/inbound</text><text x="170.0" y="137.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">api/router.py · transport/soap.py</text><rect x="380" y="74" width="300" height="86" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="97.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">FIAS TCP transport</text><text x="530.0" y="113.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">TcpLink · TcpListenerLink</text><text x="530.0" y="129.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">DelimitedFramer · LinkPump</text><text x="530.0" y="144.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">not wired in a production process</text><rect x="20" y="176" width="300" height="56" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="170.0" y="192.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HTNGAdapter + SchemaRegistry</text><text x="170.0" y="208.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">adapters/htng/ (prod registry empty →</text><text x="170.0" y="224.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">BLOCKED)</text><rect x="380" y="176" width="300" height="56" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="530.0" y="192.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">FIASAdapter + FiasSpecification</text><text x="530.0" y="208.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">adapters/fias/ (prod spec None →</text><text x="530.0" y="224.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">BLOCKED)</text><rect x="20" y="262" width="660" height="70" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="350.0" y="293.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">ExchangeGateway  (exchange/gateway.py)</text><text x="350.0" y="309.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">ClientAuthenticator · FacilityResolver · validation · CanonicalEnvelope · metrics</text><rect x="20" y="362" width="660" height="70" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="393.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">SqlIntegrationRepository  (processing/sql_repository.py)</text><text x="350.0" y="409.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">messages · payloads · idempotency keys · outbox · audit  (7 candidate tables, HF-39)</text><rect x="20" y="462" width="200" height="70" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="120.0" y="477.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">InboundWorker</text><text x="120.0" y="493.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(IntegrationService)</text><text x="120.0" y="509.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">claim · lease · retry ·</text><text x="120.0" y="524.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">DLQ</text><rect x="245" y="462" width="200" height="70" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="345.0" y="485.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">MessageDispatcher →</text><text x="345.0" y="501.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">StayEventHandler →</text><text x="345.0" y="517.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">StayDomainAdapter</text><rect x="470" y="462" width="210" height="70" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="575.0" y="485.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HMS stays_write</text><text x="575.0" y="501.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">check_in / check_out</text><text x="575.0" y="517.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(LiveWriteGate CLOSED)</text><rect x="20" y="562" width="200" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="120.0" y="578.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">OutboxRelay (reads</text><text x="120.0" y="594.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">outbox)</text><text x="120.0" y="610.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">sender: none configured</text><rect x="245" y="562" width="435" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="462.5" y="578.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Observability + operator APIs → Integrations dashboard</text><text x="462.5" y="594.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">api/router.py · observability.py ·</text><text x="462.5" y="610.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">frontend/src/features/integrations</text><line x1="170.0" y1="54.0" x2="170.0" y2="74.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><rect x="126.6" y="54.0" width="86.8" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="170.0" y="67.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">SOAP 1.1/1.2</text><line x1="530.0" y1="54.0" x2="530.0" y2="74.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><rect x="493.0" y="54.0" width="74.0" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="530.0" y="67.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">TCP frames</text><line x1="170.0" y1="160.0" x2="170.0" y2="176.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><line x1="530.0" y1="160.0" x2="530.0" y2="176.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><line x1="170.0" y1="232.0" x2="170.0" y2="262.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><line x1="530.0" y1="232.0" x2="530.0" y2="262.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><line x1="350.0" y1="332.0" x2="350.0" y2="362.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><rect x="319.4" y="337.0" width="61.2" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="350.0" y="350.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">accept()</text><line x1="120.0" y1="432.0" x2="120.0" y2="462.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><rect x="92.6" y="437.0" width="54.8" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="120.0" y="450.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">claim()</text><line x1="220.0" y1="497.0" x2="245.0" y2="497.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><line x1="445.0" y1="497.0" x2="470.0" y2="497.0" stroke="#374151" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a2)"/><path d="M457,432 L457,562" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a2)"/><rect x="10" y="665" width="16" height="12" rx="2" fill="#F3F4F6" stroke="#4B5563"/><text x="32.0" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">External</text><rect x="84.8" y="665" width="16" height="12" rx="2" fill="#E0F2FE" stroke="#0369A1"/><text x="106.8" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Transport</text><rect x="165.7" y="665" width="16" height="12" rx="2" fill="#DCFCE7" stroke="#15803D"/><text x="187.7" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Integration core</text><rect x="289.29999999999995" y="665" width="16" height="12" rx="2" fill="#FEF3C7" stroke="#B45309"/><text x="311.3" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Database</text><rect x="364.09999999999997" y="665" width="16" height="12" rx="2" fill="#FCE7F3" stroke="#BE185D"/><text x="386.1" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">HMS</text><rect x="408.4" y="665" width="16" height="12" rx="2" fill="#EDE9FE" stroke="#6D28D9"/><text x="430.4" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Dashboard/API</text><rect x="513.6999999999999" y="665" width="16" height="12" rx="2" fill="#FFFFFF" stroke="#6B7280" stroke-dasharray="4 3"/><text x="535.7" y="674.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Pending / not wired</text></svg><figcaption>Figure 2: Complete system architecture</figcaption></figure>

Colour artham: green = integration core, blue = transport, amber = database, pink = HMS, purple = dashboard/API. **Dashed box** = code irukku aana production-la wire aagala / approval illa.

## 3.2 Ovvoru block-um enna pannudhu

| Block | Velai | Real file | Current state |
|---|---|---|---|
| Vendor PMS | Messages anuppura external system | — | **Vendor innum decide aagala (HF-03)** |
| HTNG endpoint | SOAP HTTP request receive pannum | `api/router.py` (`htng_inbound`), `transport/soap.py` | Code ready; default **disabled** (503) |
| FIAS TCP transport | TCP bytes receive, frames-ah pirikkum | `transport/tcp.py` (`TcpLink`, `LinkPump`), `transport/tcp_server.py` (`TcpListenerLink`), `transport/framing.py` (`DelimitedFramer`) | Code + tests ready; **production process-la wire aagala** |
| HTNGAdapter | SOAP body-ah canonical message-ah maathum | `adapters/htng/adapter.py`, `adapters/htng/schema.py` | Production registry empty → **BLOCKED** (HF-07) |
| FIASAdapter | FIAS record-ah canonical message-ah maathum | `adapters/fias/adapter.py`, `spec.py`, `codec.py` | `PRODUCTION_SPECIFICATION = None` → **BLOCKED** (HF-11) |
| ExchangeGateway | Common entry: auth, facility, validation, envelope | `exchange/gateway.py` | Implemented, tested |
| Repository | Durable storage + claim + completion | `processing/sql_repository.py`, `processing/repository.py` | Implemented; tables only in disposable DBs (HF-39) |
| InboundWorker | Background processing, retry, DLQ | `processing/worker.py`, `service.py` | Implemented; service default off |
| Dispatcher + Stay handler | Message type → HMS action | `exchange/dispatcher.py`, `domain/stays.py` | Implemented; **LiveWriteGate closed** |
| HMS stays_write | Existing HMS check-in/out service | `app/services/stays_write` (existing HMS code) | Reused, not modified |
| OutboxRelay | Outbound messages anuppum | `processing/worker.py` (`OutboxRelay`) | No production sender configured |
| Observability + dashboard | Monitoring | `observability.py`, `api/router.py`, `frontend/src/features/integrations/` | Implemented |

(Paths `backend/app/integrations/` ulla irukkura relative paths, except HMS and frontend.)

## 3.3 Blocks-ukku naduvula relationship

1. **Transport protocol-specific, gateway common.** HTNG HTTP-la varudhu, FIAS TCP-la varudhu — rendum adapter vazhiya oru `DecodedMessage`-ah maari, `ExchangeGateway.receive()` kitta pogum. Idhukku appuram protocol difference illa.
2. **Gateway → Repository synchronous.** Message accept aana *udane* database-la save; adhukku appuram dhaan vendor-ku "accepted" sollrom. Save aagala-na "accepted" solla maattom.
3. **Repository → Worker asynchronous.** Worker konjam neram kazhichu claim pannum. Vendor wait panna thevai illa.
4. **Worker → HMS gated.** HMS data maathura handler `LiveWriteGate` open-ah irundha dhaan run aagum. Ippo closed.
5. **Observability read-only.** Dashboard data padikkum; maathaadhu.

## 3.4 Process boundaries (yaar endha process-la run aagudhu)

| Process | Enna run aagudhu | Start condition |
|---|---|---|
| FastAPI app (existing HMS backend) | HTNG endpoint, operator APIs, observability APIs | HMS backend start aagumbodhu; HTNG endpoint switch off-na 503 |
| Integration service | `python -m app.integrations.service` → InboundWorker, OutboxRelay, retention purge | `INTEGRATION_ENABLED=true` illa-na exit code 3 |
| FIAS link | `TcpLink` / `TcpListenerLink` + `LinkPump` | **Endha production process-um idha start pannala** (HF-25/HF-06 decide pannanum) |
| Simulator | `FiasTestSimulator` | Test-ku mattum; `INTEGRATION_SIMULATOR_ENABLED=true` + loopback address mattum |
| CLI | `python -m app.integrations.cli` (create-client, rotate-secret …) | Operator manual-ah run pannanum |

**Chapter 3 summary:** Protocol-specific edge (transport + adapter), common middle (gateway + repository + worker), gated HMS boundary, read-only monitoring. Production-la ippo endha vendor path-um open illa.

# Chapter 4 – Common Backend Implementation

Rendu protocol-kum share aagura components. Ovvondhukkum: purpose, implementation, files, data flow, example, tests.

## 4.1 Authentication (integration clients)

- **Purpose:** Message anuppuradhu yaar-nu confirm pannradhu. Ovvoru vendor link = oru "integration client" (`client_code` + secret).
- **Implementation:**
  - Secret generate: `secrets.token_urlsafe(32)` (`generate_secret`); store pannradhu hash mattum (`sha256$<hex>`, `hash_secret`). Plain secret oru thadava mattum print aagum.
  - Compare: `hmac.compare_digest` (constant-time — timing attack illa).
  - Disabled client, unknown client, wrong secret, protocol permitted illa → `AuthenticationFailed` (reason metric-la mattum; secret log aagaadhu).
  - HTNG headers: `X-Integration-Client`, `X-Integration-Secret`.
- **Files:** `security/clients.py` (`ClientAuthenticator`, `IntegrationClient`, `hash_secret`), `security/sql_stores.py` (`SqlClientStore`), `exchange/gateway.py` (`ExchangeGateway.authenticate`).
- **Data flow:** request → `authenticate(code, secret, protocol)` → `AuthenticatedClient` or 401.
- **Example:** "pms-a" client correct secret anuppina accept; old secret anuppina overlap window mudinja reject.
- **Tests:** `tests/integrations/test_security.py` (52 tests), `test_admin.py` (12).

## 4.2 Facility mapping

- **Purpose:** Vendor property code → HMS facility. Wrong facility-ku message pogakoodadhu.
- **Implementation:**
  - `FacilityResolver.resolve(client, property_code)`: client-oda **enabled** mapping mattum use.
  - `normalize_code` + `CaseSensitivity` (`EXACT` default; `INSENSITIVE` option) — HF-05 decide pannra vara EXACT.
  - Database column `normalized_property_code` `utf8mb4_bin` collation — default case-insensitive collation use panna HF-05-ah silent-ah decide panna maadhiri aagidum.
  - **Scope smuggling check** (`assert_no_scope_smuggling`): message body-kulla vera facility/property refer pannaa reject.
  - **Bound property:** FIAS link oru property-ku bind aagirundha, message vera property sonnaa `FacilityAuthorizationError`.
  - Mapping create aagumbodhu **DISABLED**; enable panna reason + audit.
- **Files:** `security/facility.py`, `security/sql_stores.py` (`SqlFacilityMappingStore`), `admin.py` (`create_mapping`, `set_mapping_enabled`), API `/integrations/mappings`.
- **Example:** pms-a "HOTEL-A" → Facility A; pms-b "HOTEL-A" → Facility B (rendum allowed, client-scoped).
- **Tests:** `test_security.py`, `test_admin.py`, `test_api.py`.

<figure class="diagram" id="fig-facility"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="100%" role="img" style="max-width:700px"><defs><marker id="a5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="20" width="170" height="50" rx="8" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.6"/><text x="105.0" y="33.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Client pms-a</text><text x="105.0" y="49.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">sends property</text><text x="105.0" y="65.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">HOTEL-A</text><rect x="20" y="100" width="170" height="50" rx="8" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.6"/><text x="105.0" y="113.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Client pms-b</text><text x="105.0" y="129.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">sends property</text><text x="105.0" y="145.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">HOTEL-A</text><rect x="225" y="30" width="250" height="116" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="61.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_facility_mappings</text><text x="350.0" y="76.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(client_id, normalized code)</text><text x="350.0" y="92.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">UNIQUE per client</text><text x="350.0" y="108.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">utf8mb4_bin = EXACT case</text><text x="350.0" y="123.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HF-05 pending)</text><rect x="560" y="20" width="130" height="50" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="625.0" y="49.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Facility A</text><rect x="560" y="100" width="130" height="50" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="625.0" y="129.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Facility B</text><rect x="20" y="220" width="190" height="70" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="115.0" y="243.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Operator user</text><text x="115.0" y="259.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">facility_ids = [A]</text><text x="115.0" y="275.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(facility_user rows)</text><rect x="250" y="220" width="220" height="70" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="360.0" y="243.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Integration APIs</text><text x="360.0" y="259.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">require_permission +</text><text x="360.0" y="275.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">scope = user.facility_ids</text><rect x="510" y="200" width="170" height="46" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="595.0" y="227.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Rows of facility A ✓</text><rect x="500" y="266" width="190" height="60" rx="8" fill="#FEE2E2" stroke="#B91C1C" stroke-width="1.6"/><text x="595.0" y="292.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Facility B filter → 403</text><text x="595.0" y="308.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">B rows never counted</text><line x1="190.0" y1="45.0" x2="225.0" y2="88.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><line x1="190.0" y1="125.0" x2="225.0" y2="88.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><line x1="475.0" y1="88.0" x2="560.0" y2="45.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><rect x="496.5" y="56.5" width="42.0" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="517.5" y="70.3" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">pms-a</text><line x1="475.0" y1="88.0" x2="560.0" y2="125.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><rect x="496.5" y="96.5" width="42.0" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="517.5" y="110.3" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">pms-b</text><line x1="210.0" y1="255.0" x2="250.0" y2="255.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><rect x="215.4" y="245.0" width="29.2" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="230.0" y="258.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">JWT</text><line x1="470.0" y1="255.0" x2="510.0" y2="223.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/><line x1="470.0" y1="255.0" x2="500.0" y2="296.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a5)"/></svg><figcaption>Figure 3: Facility mapping and isolation</figcaption></figure>

## 4.3 Message exchange (ExchangeGateway)

- **Purpose:** Ella protocol-kum oru common, strict intake pipeline.
- **Implementation (`ExchangeGateway.receive` → `_validate`), order:**
  1. Bytes-aa, size ≤ `MAX_MESSAGE_BYTES` (default 256 KiB), empty illaiyaa.
  2. Client-ku indha protocol permitted-aa.
  3. `adapter.decode()` — adapter protocol-specific parsing.
  4. Bound property check, `FacilityResolver.resolve`, scope smuggling check.
  5. Message type-ku handler registered-aa (`UnsupportedMessage` illa-na).
  6. Idempotency key irukkaa.
  7. `CanonicalEnvelope` build: `ordering_key` (handler kudukkum), `payload_hash`, strictly increasing `received_at` (`_next_received_at` — same microsecond-la rendu message vandhaalum order maaraadhu).
  8. `repository.accept()`.
  - Validation-la unexpected exception → **permanent** reject (retry panna use illa). Persistence failure mattum transient.
  - Result: `IntakeResult` (ACCEPTED / DUPLICATE / REJECTED + correlation id).
- **Files:** `exchange/gateway.py`, `core/envelope.py` (`CanonicalEnvelope`, `IntakeResult`), `core/correlation.py`.
- **Tests:** `test_exchange.py` (28), `test_end_to_end.py` (8), `test_sprint_hardening.py` (22).

<figure class="diagram" id="fig-pipeline"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 470" width="100%" role="img" style="max-width:700px"><defs><marker id="a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="10" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="31.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">1. Raw bytes from transport</text><text x="235.0" y="47.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(size ≤ MAX_MESSAGE_BYTES, not empty)</text><rect x="20" y="76" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="97.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">2. Protocol permitted for this client?</text><text x="235.0" y="113.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(ClientAuthenticator result)</text><rect x="20" y="142" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="163.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">3. adapter.decode(bytes)</text><text x="235.0" y="179.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HTNG / FIAS adapter)</text><rect x="20" y="208" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="229.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">4. Bound property check + FacilityResolver.resolve</text><text x="235.0" y="245.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">+ assert_no_scope_smuggling</text><rect x="20" y="274" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="303.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">5. Handler registered? Idempotency key present?</text><rect x="20" y="340" width="430" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="235.0" y="361.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">6. CanonicalEnvelope (ordering_key, payload_hash,</text><text x="235.0" y="377.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">strictly increasing received_at)</text><rect x="20" y="406" width="430" height="50" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="235.0" y="435.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">7. repository.accept() → ACCEPTED or DUPLICATE</text><rect x="490" y="150" width="190" height="120" rx="8" fill="#FEE2E2" stroke="#B91C1C" stroke-width="1.6"/><text x="585.0" y="190.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">IntakeResult REJECTED</text><text x="585.0" y="206.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">nothing stored</text><text x="585.0" y="222.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">error category + code</text><text x="585.0" y="237.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">metric intake_rejected</text><line x1="235.0" y1="60.0" x2="235.0" y2="76.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="235.0" y1="126.0" x2="235.0" y2="142.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="235.0" y1="192.0" x2="235.0" y2="208.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="235.0" y1="258.0" x2="235.0" y2="274.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="235.0" y1="324.0" x2="235.0" y2="340.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="235.0" y1="390.0" x2="235.0" y2="406.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a3)"/><line x1="450.0" y1="101.0" x2="490.0" y2="210.0" stroke="#B91C1C" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a3)"/><line x1="450.0" y1="167.0" x2="490.0" y2="210.0" stroke="#B91C1C" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a3)"/><line x1="450.0" y1="233.0" x2="490.0" y2="210.0" stroke="#B91C1C" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a3)"/><line x1="450.0" y1="299.0" x2="490.0" y2="210.0" stroke="#B91C1C" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#a3)"/></svg><figcaption>Figure 4: Shared backend intake pipeline</figcaption></figure>

## 4.4 Durable persistence

- **Purpose:** Accept panna message system crash aanaalum lose aagakoodadhu.
- **Implementation:** 7 candidate tables (Chapter 8). `SqlIntegrationRepository` SQLAlchemy 2 vechu MySQL-la ezhudhum. Same interface-oda `InMemoryIntegrationRepository` tests-ku.
  - Body canonical JSON-ah LONGTEXT-la (MySQL JSON type key order maathidum, hash break aagum).
  - Tables **separate metadata**-la declare (`INTEGRATION_METADATA`) — HMS Alembic autogenerate-la varaadhu.
  - Migration draft `backend/migrations/drafts/integration_tables_candidate.py` — Alembic `versions/` folder-la **illa**, adhunaala yaarum accidental-ah apply panna mudiyaadhu.
- **Files:** `processing/sql_models.py`, `processing/sql_repository.py`, `processing/repository.py`.
- **Tests:** `test_repository_contract.py` (40 — same tests in-memory-kum disposable MySQL-kum), `test_mysql_persistence.py` (18), `test_migration_candidate.py` (3).

## 4.5 Idempotency

- **Implementation:** `integration_idempotency_keys` UNIQUE (client_id, facility_id, idempotency_key) + `fingerprint`. Accept-la insert; unique violation vandha existing fingerprint compare:
  - same fingerprint → **DUPLICATE** (vendor-ku "duplicate" response; oru row mattum);
  - different fingerprint → `IdempotencyConflict` (reject).
  - Idempotency key adapter dhaan kudukkum — FIAS-la endha field event-ai unique-ah identify pannum-nu official spec sollanum (vendor item B9). Naanga key fabricate pannala.
  - Retention purge enable aana, duplicate protection window = retention days (HF-21).
- **Files:** `core/hashing.py`, `processing/sql_repository.py` (`accept`, `is_idempotency_duplicate`).
- **Example:** Vendor network timeout-naala check-in message-ah rendu thadava anuppudhu → rendaavadhu "duplicate", HMS-la oru check-in mattum.
- **Tests:** `test_repository_contract.py`, `test_mysql_persistence.py` (concurrent duplicate intake → 1 message), `test_core.py`.

## 4.6 Worker leases

- **Implementation:**
  - `claim()`: `SELECT … FOR UPDATE SKIP LOCKED` — rendu workers same row edukka maattaanga.
  - Claim panna row → PROCESSING, `attempt_count + 1`, `lease_owner`, random `lease_token`, `lease_expires_at`.
  - `completion()` context: lease-ah **entry-lum exit-lum** check (fresh clock). Lease poyirundha `LeaseLost` → handler-oda HMS change **rollback**.
  - HMS service `commit()` call pannaalum adhu **savepoint**-ku join aagum (`join_transaction_mode="create_savepoint"`) — SUCCEEDED status, outbox, audit, HMS change ellam oru transaction.
  - Lease expire aana message vera worker re-claim pannum (PROCESSING → PROCESSING allowed).
- **Files:** `processing/sql_repository.py` (`claim`, `completion`), `processing/worker.py`, `core/lifecycle.py` (`CLAIMABLE`).
- **Example:** Worker 1 crash aachu → 60 s kazhichu Worker 2 edukkum; Worker 1 late-ah save panna try pannaa reject.
- **Tests:** `test_mysql_persistence.py` (6 workers × 40 messages, double claim illa), `test_hardening.py`, `test_hms_domain_mysql.py`.

## 4.7 Retry and backoff

- **Implementation:** Worker error vandha `RetryPolicy.decide(error, attempts_made, now)`:
  - **TransientFailure** & attempts < max → RETRY_WAIT, `next_attempt_at = now + delay`.
  - **PermanentFailure** or attempts exhausted → DEAD_LETTER.
  - Delay: `base_delay_seconds 5.0 × multiplier 2.0^(attempt-1)`, max 900 s. Defaults implemented; final policy **HF-27** (Open).
  - Settings: `INTEGRATION_RETRY_MAX_ATTEMPTS` (5), `INTEGRATION_RETRY_BASE_SECONDS` (5), `INTEGRATION_RETRY_MAX_SECONDS` (900).
- **Files:** `core/retry.py`, `processing/worker.py` (`InboundWorker._fail`), `config.py`.
- **Tests:** `test_core.py`, `test_exchange.py`.

<figure class="diagram" id="fig-lifecycle"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 420" width="100%" role="img" style="max-width:700px"><defs><marker id="a4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="10" y="30" width="150" height="60" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="85.0" y="56.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">PENDING</text><text x="85.0" y="72.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(stored by accept)</text><rect x="250" y="30" width="190" height="60" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="345.0" y="48.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">PROCESSING</text><text x="345.0" y="64.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">lease + token; expired</text><text x="345.0" y="80.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">lease → re-claimed</text><rect x="540" y="30" width="150" height="60" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="615.0" y="56.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">SUCCEEDED</text><text x="615.0" y="72.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(terminal)</text><rect x="250" y="200" width="190" height="66" rx="8" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.6"/><text x="345.0" y="221.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">RETRY_WAIT</text><text x="345.0" y="237.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">next_attempt_at =</text><text x="345.0" y="253.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">5s × 2^(n-1), max 900s</text><rect x="540" y="200" width="150" height="66" rx="8" fill="#FEE2E2" stroke="#B91C1C" stroke-width="1.6"/><text x="615.0" y="221.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">DEAD_LETTER</text><text x="615.0" y="237.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">permanent error or</text><text x="615.0" y="253.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">attempts exhausted</text><rect x="460" y="330" width="230" height="66" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="575.0" y="351.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Audited redrive</text><text x="575.0" y="367.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">POST …/redrive (write grant,</text><text x="575.0" y="383.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">reason 10–500 chars)</text><line x1="160.0" y1="60.0" x2="250.0" y2="60.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="177.6" y="43.0" width="54.8" height="34" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="205.0" y="57.0" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">worker</text><text x="205.0" y="70.7" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">claim()</text><line x1="440.0" y1="48.0" x2="540.0" y2="48.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="453.0" y="38.0" width="74.0" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="490.0" y="51.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">handler OK</text><path d="M300,90 L300,200" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="165.8" y="128.0" width="112.4" height="34" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="222.0" y="142.0" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">transient error,</text><text x="222.0" y="155.7" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">attempts &lt; 5</text><path d="M390,200 L390,90" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="311.2" y="118.0" width="67.6" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="345.0" y="131.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">due again</text><path d="M440,75 L500,75 L500,233 L540,233" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="459.8" y="143.0" width="80.4" height="34" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="500.0" y="157.0" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">permanent /</text><text x="500.0" y="170.7" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">exhausted</text><path d="M615,266 L615,330" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="619.4" y="288.0" width="61.2" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="650.0" y="301.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">operator</text><path d="M460,363 L85,363 L85,90" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a4)"/><rect x="136.2" y="370.0" width="227.6" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="250.0" y="383.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">back to PENDING, attempt_count = 0</text></svg><figcaption>Figure 5: Message lifecycle: retry, DLQ and redrive</figcaption></figure>

## 4.8 DLQ (Dead Letter Queue)

- **Implementation:** Separate queue table illa — status `DEAD_LETTER` + `last_error_code`, `last_error_category`, `completed_on` (dead-letter aana time). DEAD_LETTER-la irundhu velila vara oru vazhi dhaan: audited redrive (`core/lifecycle.py` `ALLOWED`).
- **Visibility:** `GET /integrations/dlq`, `GET /integrations/observability/dlq`, dashboard page.
- **Tests:** `test_api.py`, `test_observability.py`, `test_repository_contract.py`.

## 4.9 Audited redrive

- **Implementation:** `redrive(message_id, facility_scope, actor_id, reason, now)`: message caller-oda facility-la irukkanum (illa-na 404 — "not found" maadhiri, existence leak aagaadhu), status DEAD_LETTER-ah irukkanum (illa-na 409), reason 10–500 chars (`validate_redrive_reason`). Status PENDING, attempts 0, lease clear; same transaction-la audit `message.redrive` + previous error code.
- **Files:** `processing/sql_repository.py` (`redrive`), `processing/repository.py` (`validate_redrive_reason`), `api/router.py` (`redrive`, `RedriveRequest`).
- **Tests:** `test_api.py`, `test_repository_contract.py`, `test_ordering.py`.

## 4.10 Per-stay ordering

- **Purpose:** Same stay-ku check-out, check-in-ku munnaadi process aagakoodadhu.
- **Implementation:** Handler `ordering_key(body)` kudukkum (stay reference). `claim()` `_not_blocked()` condition: same (client, facility, ordering_key)-la *earlier* message PENDING/PROCESSING/RETRY_WAIT-la irundha later message claim aagaadhu. Earlier message **DEAD_LETTER**-la irundhaalum block (`dead_letter_blocks_ordering=True` default; final policy HF-27) — operator redrive pannra vara chain hold.
- **Files:** `processing/sql_repository.py` (`_not_blocked`), `processing/repository.py` (`blocking_statuses`), `domain/stays.py`.
- **Example:** Check-in fail aagi DLQ-la irukku → check-out wait pannum; check-in redrive aana appuram check-out process aagum.
- **Tests:** `test_ordering.py` (19), `test_hms_domain_mysql.py`, `test_e2e_hms_simulation.py`.

## 4.11 Audit transaction handling

- **Implementation:** Handler `AuditDraft` raise pannum; repository adha HMS change + SUCCEEDED status kooda **same transaction**-la `integration_audit_events`-la ezhudhum. Admin actions (`client.created`, `mapping.enabled`, …) `IntegrationAdmin._audit` vazhiya same transaction. Audit detail-la ids, codes mattum — guest data illa.
- **Files:** `processing/repository.py` (`AuditDraft`, `CompletionContext`), `admin.py`, `domain/stays.py`.
- **Tests:** `test_domain.py` (25), `test_hms_domain_mysql.py`, `test_admin.py`.
- **Limitation:** Audit table append-only *convention* mattum; database-level immutability illa (HF-23).

## 4.12 Credential rotation

- **Implementation:** `rotate_secret(code, overlap, actor)` — new secret; old secret `secondary_secret_hash`-la `secondary_expires_on` vara valid; overlap 0 to 7 days (`MAX_OVERLAP`); `revoke_previous_secret` early cut; disabled client-ku rendum reject; CLI-only; audited.
- **Files:** `admin.py`, `security/clients.py`, `cli.py`.
- **Tests:** `test_admin.py` (`test_rotation_overlap_expiry_and_revoke`, `test_rotation_without_overlap_invalidates_immediately`, `test_overlap_bounds_and_duplicate_client`), `test_security.py` (`test_previous_secret_accepted_during_overlap_only`).
- **Pending:** Secret enga store pannanum, vendor-ku eppadi deliver pannanum — HF-22.

## 4.13 Feature switches

| Switch (env) | Default | Artham |
|---|---|---|
| `INTEGRATION_ENABLED` | false | Integration overall on/off; service start aaga venum |
| `INTEGRATION_HTNG_INBOUND_ENABLED` | false | HTNG endpoint (ENABLED-um venum) |
| `INTEGRATION_LIVE_DOMAIN_WRITES` | false | HMS data maathalaam-aa (approval gate-um venum) |
| `INTEGRATION_STORE_RAW_WIRE_PAYLOAD` | false | Raw bytes store (HF-21) |
| `INTEGRATION_SIMULATOR_ENABLED` | false | Test simulator |
| `INTEGRATION_RETENTION_DAYS` | unset | Purge window (HF-21) |
| `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE` | unset | Rate limit (BLK-V7 volumes venum) |
| `INTEGRATION_ACTOR_USER_ID` | unset | HMS writes-ku actor (HF-18) |

Cross-validation: HTNG_INBOUND without ENABLED → error; LIVE_DOMAIN_WRITES without ACTOR_USER_ID → error; ACTOR_USER_ID UUID-ah irukkanum. **Live writes-ku env flag mattum podhaadhu** — `domain/approvals.py`-la HF-01, HF-02, HF-05, HF-19 **Approved + evidence**-oda irukkanum (reviewed code change).

- **Files:** `config.py` (`IntegrationSettings`), `domain/approvals.py` (`LiveWriteGate`, `DECISIONS`).
- **Tests:** `test_hardening.py`, `test_domain.py`, `test_admin.py`.

## 4.14 Background worker (Integration service)

- **Implementation:** `IntegrationService.run_iteration()`: `InboundWorker.run_once()` + `OutboxRelay.run_once()`; work illa-na `poll_interval`; unexpected error → type mattum log + bounded exponential back-off (loop saagaadhu); SIGTERM/SIGINT → current batch mudichu stop; retention purge `INTEGRATION_RETENTION_DAYS` set aana mattum (1,000-row batches). Multiple instances safe (SKIP LOCKED + fencing).
- **Files:** `service.py`, `processing/worker.py`.
- **Tests:** `test_service.py` (11).
- **Pending:** Hosting & supervision (PM2/systemd) HF-25, restart policy HF-26.

## 4.15 Health monitoring

| Endpoint / source | Enna kaattum |
|---|---|
| `GET /integrations/health` | Public liveness — data illa (`{"status":"ok"}`) |
| `GET /integrations/readiness` | Persistence (tables present?), adapters, worker heartbeats, transports, live-write gate; not ready-na 503 |
| `GET /integrations/facilities/health` | Per-facility counts, oldest pending age, latency p50/p95/max, per-client last received/succeeded |
| `GET /integrations/metrics` | In-process counters + status counts |
| `IntegrationMetrics` | Counters/heartbeats — **process-local** (API process worker heartbeat paakka mudiyaadhu) |

- **Files:** `api/router.py`, `processing/health.py`, `metrics.py`.
- **Tests:** `test_health_view.py` (7), `test_api.py` (16).

**Chapter 4 summary:** Common layer-la ella safety mechanisms-um irukku: auth, isolation, idempotency, leases, retry, DLQ, redrive, ordering, transactional audit. Ellam disposable MySQL-la test aagirukku; production database-la tables innum create aagala (HF-39).

# Chapter 5 – HTNG Complete Explanation

## 5.1 Moonu category-ah pirichu paakanum

| Category | Enna |
|---|---|
| **Implemented generic framework** | SOAP 1.1/1.2 handling, safe XML parser, schema/profile registry, endpoint, faults, auth, facility mapping, persistence, retry/DLQ, monitoring |
| **Official vendor contracts — pending** | WSDL/XSD bundle, implementation profile, operation list, security profile (HF-07, HF-08) |
| **Not vendor validated** | Oru real HTNG vendor message kooda test pannala; synthetic profile (`acx-generic-xml-test`) vechu dhaan test |

## 5.2 HTNG sequence diagram

<figure class="diagram" id="fig-htng_seq"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 592" width="100%" role="img" style="max-width:700px"><defs><marker id="a6" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><line x1="75.0" y1="54" x2="75.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="25.5" y="8" width="99.0" height="46" rx="6" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.5"/><text x="75.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Vendor PMS</text><text x="75.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">(HTNG client)</text><line x1="185.0" y1="54" x2="185.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="135.5" y="8" width="99.0" height="46" rx="6" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.5"/><text x="185.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">htng_inbound</text><text x="185.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">(api/router.py)</text><line x1="295.0" y1="54" x2="295.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="245.5" y="8" width="99.0" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="295.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">ExchangeGateway</text><line x1="405.0" y1="54" x2="405.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="355.5" y="8" width="99.0" height="46" rx="6" fill="#FEF3C7" stroke="#B45309" stroke-width="1.5"/><text x="405.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Repository</text><text x="405.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">(MySQL)</text><line x1="515.0" y1="54" x2="515.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="465.5" y="8" width="99.0" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="515.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">InboundWorker</text><line x1="625.0" y1="54" x2="625.0" y2="586" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="575.5" y="8" width="99.0" height="46" rx="6" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.5" stroke-dasharray="6 4"/><text x="625.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">HMS</text><text x="625.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">stays_write</text><rect x="28.8" y="64" width="642.4" height="38" rx="4" fill="#FFFBEB" stroke="#D97706"/><text x="350.0" y="79" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">Production today: INTEGRATION_ENABLED / HTNG_INBOUND_ENABLED = false → 503;</text><text x="350.0" y="93" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">production SchemaRegistry empty → HTNGAdapter BLOCKED (HF-07)</text><text x="130.0" y="116.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">POST SOAP envelope</text><text x="130.0" y="129.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">X-Integration-Client / -Secret</text><line x1="75.0" y1="136" x2="179.0" y2="136" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><path d="M185.0,160 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a6)"/><text x="219.0" y="170" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">enabled? size ≤ limit?</text><text x="240.0" y="189.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">authenticate(code, secret, HTNG)</text><line x1="185.0" y1="196" x2="289.0" y2="196" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><text x="240.0" y="219.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">client (or 401 fault)</text><line x1="295.0" y1="226" x2="191.0" y2="226" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a6)"/><path d="M185.0,250 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a6)"/><text x="219.0" y="260" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">rate limit (429) · media type (415)</text><text x="240.0" y="279.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">receive(raw bytes)</text><line x1="185.0" y1="286" x2="289.0" y2="286" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><path d="M295.0,310 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a6)"/><text x="329.0" y="320" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">decode · facility · validate</text><text x="350.0" y="339.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">accept(envelope)</text><line x1="295.0" y1="346" x2="399.0" y2="346" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><text x="350.0" y="369.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">ACCEPTED / DUPLICATE</text><line x1="405.0" y1="376" x2="301.0" y2="376" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a6)"/><text x="240.0" y="399.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">IntakeResult</text><line x1="295.0" y1="406" x2="191.0" y2="406" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a6)"/><text x="130.0" y="416.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">profile ack (SOAP 1.1/1.2), 202,</text><text x="130.0" y="429.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">or SOAP fault in the request&#x27;s version</text><line x1="185.0" y1="436" x2="81.0" y2="436" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a6)"/><line x1="20" y1="462" x2="680" y2="462" stroke="#9CA3AF" stroke-dasharray="2 3"/><rect x="263.8" y="451" width="172.4" height="20" rx="4" fill="#F3F4F6" stroke="#9CA3AF"/><text x="350.0" y="464.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="bold" text-anchor="middle" fill="#374151">asynchronous processing</text><text x="460.0" y="485.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">claim() with lease</text><line x1="515.0" y1="492" x2="411.0" y2="492" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><text x="570.0" y="515.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">dispatch (only if LiveWriteGate open)</text><line x1="515.0" y1="522" x2="619.0" y2="522" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/><text x="460.0" y="545.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">completion: SUCCEEDED + outbox + audit</text><line x1="515.0" y1="552" x2="411.0" y2="552" stroke="#374151" stroke-width="1.4" marker-end="url(#a6)"/></svg><figcaption>Figure 6: HTNG message flow (sequence)</figcaption></figure>

## 5.3 SOAP 1.1 and SOAP 1.2

- **Version detect:** HTTP `Content-Type` vechu — `text/xml` = SOAP 1.1, `application/soap+xml` = SOAP 1.2 (`soap_version_from_content_type`). Vera media type → **415**.
- **Response same version-la:** SOAP 1.2 request-ku SOAP 1.2 response/fault (`env:Sender` / `env:Receiver`, `application/soap+xml`); SOAP 1.1-ku `soap:Client` / `soap:Server`, `text/xml`.
- **Enga irukku:** `backend/app/integrations/transport/soap.py` (`SoapVersion`, `parse_soap`, `build_soap_envelope`), `api/router.py` (`soap_fault`, `soap_version_from_content_type`).
- **Tests:** `test_htng_adapter.py` (39), `test_api.py`, certification HTNG-SYN-001…004.

## 5.4 Request and response handling (`htng_inbound`)

Order (actual code `api/router.py`):

1. Switch check: `INTEGRATION_ENABLED` and `INTEGRATION_HTNG_INBOUND_ENABLED` and adapter irukkaa — illa-na **503** fault.
2. Size: `Content-Length` and streaming body ≤ `MAX_MESSAGE_BYTES` — illa-na **413**.
3. Authenticate (`X-Integration-Client`, `X-Integration-Secret`) — fail-na **401**; DB down-na **503**.
4. Rate limit (per client, per minute, per API process) — set pannirundha mattum; exceed-na **429**. Default unset (BLK-V7).
5. Media type — SOAP illa-na **415**.
6. `gateway.receive(...)` — rejected-na error category padi HTTP status: SECURITY 403, VALIDATION/PROTOCOL 400, CONFLICT 409, TRANSIENT/VENDOR_BLOCKED/APPROVAL_BLOCKED 503.
7. Accepted/duplicate-na profile-la `response_builder` irundha SOAP ack (200); illa-na **202** empty.
8. `X-Correlation-ID` header response-la echo (unsafe value-na new id).

## 5.5 XML parsing and XML security

- **Enna problem:** XML-la DOCTYPE/ENTITY vechu attacks pannalaam — XXE (server files read), "billion laughs" (memory explode).
- **Namma solution:** `parse_untrusted_xml` — first `pyexpat` prescan: **any DOCTYPE, any entity declaration → reject**. SOAP spec-um DTD allow pannaadhu, adhunaala idhu legit messages-ah block pannaadhu. Limits (`XmlLimits`): max 1 MiB, depth 64, 20,000 elements, 64 attributes/element.
- **Enga irukku:** `backend/app/integrations/transport/xml_security.py`.
- **Tests:** `test_htng_adapter.py` (`test_dtds_and_entities_are_refused`, `test_malformed_xml`, `test_xxe_inside_soap_rejected_by_adapter`, `test_soap_response_xxe_rejected`).

## 5.6 Schema registry, version and profile

- **SchemaProfile:** `profile_id`, `version`, allowed `namespaces`, `operations`, `status` (`VerificationStatus`), `source`.
- **OperationSpec:** Body-oda root element (namespace + name), canonical `message_type`, `direction`, `validator`, `inbound_mapper` / `outbound_builder`, `response_builder`, `soap_action`.
- **SchemaRegistry:** Production-la `VERIFIED_OFFICIAL` profile mattum register aagum; unverified profile test environment-la `allow_unverified` kudutha mattum.
- **Ippo:** Production `HTNGAdapter(SchemaRegistry())` — **empty** → adapter **BLOCKED**, blocking decision HF-07 (`adapters/htng/schema.py` `BLOCKING_DECISION = "HF-07"`).
- **Decode steps (`HTNGAdapter.decode`):** `parse_soap` (profile namespaces mattum allow) → Fault-aa? empty body-aa? → operation lookup by root → `op.validator.validate` → `op.inbound_mapper` → `DecodedMessage`.

### WSDL and XSD — practical example

Oru vendor "guest check-in" operation-ku indha maadhiri files kudupaanga (illustration mattum — real vendor file illa):

- **WSDL** sollum: "`CheckInNotification` operation irukku; input message `CheckInRQ`; endpoint URL; SOAPAction value."
- **XSD** sollum: "`CheckInRQ`-la `HotelCode` mandatory, string, max 10; `ReservationID` mandatory; `ArrivalDate` date format."

Andha files vandha appuram naanga panna vendiyadhu: XSD-ah approved library vechu validator-ah load pannradhu (HF-39 library approval), ovvoru operation-kum `OperationSpec` ezhudhradhu (root, mapper, response), profile-ah `VERIFIED_OFFICIAL`-ah register pannradhu, vendor samples vechu contract tests run pannradhu.

## 5.7 Common exchange integration, auth, mapping, persistence

HTNG decode aana appuram ellam Chapter 4-la sonna common path: `ExchangeGateway` → facility (property code message-la irundhu) → idempotency → repository → worker. HTNG-ku special-aana edhuvum illa — adhu dhaan design-oda nalla vishayam.

## 5.8 Retry and failure handling (HTNG specific)

- Intake-la DB down → 503 fault (vendor retry pannalaam; namma kitta onnum save aagala).
- Worker-la transient → RETRY_WAIT; permanent → DLQ.
- Vendor-oda fault semantics (endha fault retryable) vendor item C6 — pending.

## 5.9 Monitoring

`htng` protocol entry overview API-la: transport status (Disabled / Enabled / Enabled · adapter blocked), auth readiness, processing, message counts, last error, intake rejections (this API process), readiness dimensions. Dashboard "HTNG Monitoring" page.

## 5.10 HTNG outbound

`HtngSoapSender` (`adapters/htng/sender.py`) class irukku, aana app-la **endha idathulayum instantiate aagala**; `OutboxRelay`-ku production sender illa. Vendor endpoint URL & security (C3, C5, C10) vandha appuram dhaan wire pannalaam.

**Chapter 5 summary:** HTNG framework ready & tested with synthetic profile. Real vendor profile/WSDL/XSD illaama production-la oru operation kooda run aagaadhu — adhu correct, safe behaviour.

# Chapter 6 – FIAS Complete Explanation

> **Accurate status:** FIAS TCP transport, framing, record parser framework ellam code-la irukku, loopback-la test aagirukku. Aana **endha production process-um FIAS link-ah start pannala**, `PRODUCTION_SPECIFICATION = None`, real FIAS vendor kooda oru connection kooda establish aagala.

## 6.1 FIAS sequence diagram

<figure class="diagram" id="fig-fias_seq"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 532" width="100%" role="img" style="max-width:700px"><defs><marker id="a7" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><line x1="75.0" y1="54" x2="75.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="25.5" y="8" width="99.0" height="46" rx="6" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.5"/><text x="75.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Vendor PMS</text><text x="75.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">(FIAS)</text><line x1="185.0" y1="54" x2="185.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="135.5" y="8" width="99.0" height="46" rx="6" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.5" stroke-dasharray="6 4"/><text x="185.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">TcpLink /</text><text x="185.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">TcpListenerLink</text><line x1="295.0" y1="54" x2="295.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="245.5" y="8" width="99.0" height="46" rx="6" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.5"/><text x="295.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">DelimitedFramer</text><line x1="405.0" y1="54" x2="405.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="355.5" y="8" width="99.0" height="46" rx="6" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.5"/><text x="405.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">LinkPump</text><line x1="515.0" y1="54" x2="515.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="465.5" y="8" width="99.0" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="515.0" y="28.1" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">ExchangeGateway</text><text x="515.0" y="41.2" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="middle" fill="#111827">+ FIASAdapter</text><line x1="625.0" y1="54" x2="625.0" y2="526" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="575.5" y="8" width="99.0" height="46" rx="6" fill="#FEF3C7" stroke="#B45309" stroke-width="1.5"/><text x="625.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Repository</text><rect x="28.8" y="64" width="642.4" height="38" rx="4" fill="#FFFBEB" stroke="#D97706"/><text x="350.0" y="79" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">Not wired into any production process; PRODUCTION_SPECIFICATION = None → FIASAdapter</text><text x="350.0" y="93" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">BLOCKED (HF-11). Framing, ACK, heartbeat and link role await the official manual (HF-06).</text><text x="130.0" y="116.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">TCP connect (listener: IP allow-list,</text><text x="130.0" y="129.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">one active connection)</text><line x1="75.0" y1="136" x2="179.0" y2="136" stroke="#374151" stroke-width="1.4" marker-end="url(#a7)"/><text x="130.0" y="159.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">bytes</text><line x1="75.0" y1="166" x2="179.0" y2="166" stroke="#374151" stroke-width="1.4" marker-end="url(#a7)"/><text x="240.0" y="189.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">feed(bytes)</text><line x1="185.0" y1="196" x2="289.0" y2="196" stroke="#374151" stroke-width="1.4" marker-end="url(#a7)"/><path d="M295.0,220 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a7)"/><text x="329.0" y="230" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">start/end markers,</text><text x="329.0" y="243" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">max 64 KiB per frame</text><text x="350.0" y="262.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">complete frame</text><line x1="295.0" y1="269" x2="399.0" y2="269" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a7)"/><text x="460.0" y="292.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">receive(frame, bound property)</text><line x1="405.0" y1="299" x2="509.0" y2="299" stroke="#374151" stroke-width="1.4" marker-end="url(#a7)"/><path d="M515.0,323 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a7)"/><text x="549.0" y="333" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">WireGrammar + RecordSpec</text><text x="549.0" y="346" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">→ canonical message</text><text x="570.0" y="365.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">accept()</text><line x1="515.0" y1="372" x2="619.0" y2="372" stroke="#374151" stroke-width="1.4" marker-end="url(#a7)"/><text x="460.0" y="395.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">ACCEPTED / DUPLICATE / REJECTED</text><line x1="515.0" y1="402" x2="411.0" y2="402" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a7)"/><rect x="358.8" y="420" width="202.4" height="38" rx="4" fill="#FFFBEB" stroke="#D97706"/><text x="460.0" y="435" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">DB unavailable → LinkPump retries the same frame</text><text x="460.0" y="449" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">with back-off (0.5 s … 30 s); frame is not lost</text><text x="240.0" y="472.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">ACK/NAK only if a responder is configured</text><text x="240.0" y="485.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">(none in production: HF-06)</text><line x1="405.0" y1="492" x2="81.0" y2="492" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a7)"/></svg><figcaption>Figure 7: FIAS message flow (sequence)</figcaption></figure>

## 6.2 TCP transport and connection lifecycle

- **Client mode — `TcpLink`:** vendor host:port-ku connect; `LinkState` = disconnected → connecting → connected → closed; disconnect aana **bounded reconnect back-off** (`ReconnectPolicy`); budget mudinja stop. Bounded outbound queue (backpressure).
- **Server mode — `TcpListenerLink`:** namma port-la listen; **`allowed_peers` mandatory** (IP or CIDR) — empty list-ku object create aagaadhu (ValueError); allow-list-la illaadha IP → reject (`rejected_peers` counter); **oru time-la oru active connection** (`_active`); extra connection → `rejected_busy`.
- **Health:** `TransportHealth.as_dict()` — state, connected_since, last_error_code, reconnect_attempts, connections, frames/bytes in-out, framing_errors, read_timeouts.
- **Endha mode use pannanum (who listens), host/port** — vendor item B7, decision HF-06.
- **Enga irukku:** `transport/tcp.py`, `transport/tcp_server.py`. **Tests:** `test_transport_tcp.py` (25), `test_transport_server.py` (6).

## 6.3 Message framing

- **Enna:** TCP continuous byte stream; "oru message enga start, enga end"-nu pirikkanum.
- **`DelimitedFramer`:** optional **start marker**, mandatory **end marker**, `max_frame_bytes` (default 64 KiB). Start marker-ku munnaadi irukkura bytes discard (count mattum, log illa); end illaama rendaavadhu start vandha previous frame drop; oversize frame drop & counted; link continue.
- **Production markers ENNA?** — theriyaadhu. Official manual (B3, HF-06) vara default illa. Tests-la `provisional_test_framer` (synthetic STX/ETX test markers) mattum.
- **Enga irukku:** `transport/framing.py`, `simulators/fixtures.py`.

## 6.4 Record parser framework and encoding

- **WireGrammar:** `encoding`, `record_id_length`, `field_separator`, `field_id_length`, separator rules, status/source. Encoding ASCII-compatible-ah irukkanum; separator andha encoding-la round-trip aaganum (validation in `spec.py`).
- **RecordSpec:** `record_id`, canonical `message_type`, `directions`, `fields` (`FieldSpec`: id, name, mandatory, max_length, pattern), `idempotency_fields`, `property_field`, `unknown_fields` (default "reject").
- **FiasSpecification:** name, version, grammar, records.
- **Codec:** `parse_record` / `serialize_record` (`adapters/fias/codec.py`) — spec padi dhaan parse; field validate; unknown field reject.
- **Production:** `adapters/fias/spec.py` `PRODUCTION_SPECIFICATION: FiasSpecification | None = None`, `BLOCKING_DECISION = "HF-11"` → `FIASAdapter` BLOCKED. Test-la `PROVISIONAL_TEST_FIAS_SPEC` (synthetic "Z*" records, `VerificationStatus.PROVISIONAL_TEST`).
- **Tests:** `test_fias_adapter.py` (40).

## 6.5 ACK, heartbeat, reconnect, resynchronization

| Item | Code-la | Status |
|---|---|---|
| ACK/NAK | `LinkPump` optional `responder` — configure pannaa mattum reply | **Production responder illa**; rules B4 / HF-06 pending — guess panni ACK anuppala |
| Heartbeat | Implement pannala (idle error-ah treat pannala) | B6 / HF-06 pending |
| Reconnect | `TcpLink` bounded back-off reconnect | Implemented, tested |
| Link start-up / resync / sequence numbers | Implement pannala | B5 / HF-06 pending |

## 6.6 LinkPump — TCP-la irundhu exchange-ku

`LinkPump` frames-ah `ExchangeGateway.receive` kitta kudukkum (bound property code context-oda). **Database unavailable-na same frame-ah back-off (0.5 s … 30 s) vechu retry pannum — frame lose aagaadhu** (certification FIAS-SYN-011 idha verify pannudhu). Responder configure aagirundha mattum vendor-ku reply.

## 6.7 Persistence, retry, DLQ, monitoring

Decode aana appuram common path (Chapter 4). Monitoring: overview-la FIAS transport — API process-la tagged link illa-na **"Not observable"** (unknown — "down" illa). Link FIAS-ku `runtime.transport_protocols`-la explicit-ah tag panna mattum state kaattum.

## 6.8 Simulator restrictions

`FiasTestSimulator` (`simulators/fias_simulator.py`): `INTEGRATION_SIMULATOR_ENABLED=true` venum; **loopback address-la mattum bind** (`_assert_loopback`); development/test-ku mattum.

**Chapter 6 summary:** FIAS-ku TCP + framing + spec-driven parser framework ready. Production link process, official spec, ACK/heartbeat rules — moonum missing; adhunaala FIAS production-la BLOCKED.

# Chapter 7 – Complete Message Processing Flow

Ippo oru message vendor-kitta irundhu kelambi, HMS-la apply aagi, dashboard-la theriyura vara muzhu payanatha paakkalaam. HTNG-um FIAS-um edge-la mattum vera — middle-la irundhu ellame same path. Failure aanaalum message oru "known state"-ku dhaan pogum (rejected, retry wait, dead letter) — edhuvum kaanaama pogaadhu.

## 7.1 End-to-end sequence

<figure class="diagram" id="fig-e2e_seq"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 488" width="100%" role="img" style="max-width:700px"><defs><marker id="a8" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><line x1="67.1" y1="54" x2="67.1" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="24.7" y="8" width="84.9" height="46" rx="6" fill="#F3F4F6" stroke="#4B5563" stroke-width="1.5"/><text x="67.1" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Vendor</text><line x1="161.4" y1="54" x2="161.4" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="119.0" y="8" width="84.9" height="46" rx="6" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.5"/><text x="161.4" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Transport</text><line x1="255.7" y1="54" x2="255.7" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="213.3" y="8" width="84.9" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="255.7" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Adapter</text><line x1="350.0" y1="54" x2="350.0" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="307.6" y="8" width="84.9" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="350.0" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Gateway</text><line x1="444.3" y1="54" x2="444.3" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="401.9" y="8" width="84.9" height="46" rx="6" fill="#FEF3C7" stroke="#B45309" stroke-width="1.5"/><text x="444.3" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Repository</text><line x1="538.6" y1="54" x2="538.6" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="496.1" y="8" width="84.9" height="46" rx="6" fill="#DCFCE7" stroke="#15803D" stroke-width="1.5"/><text x="538.6" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Worker</text><line x1="632.9" y1="54" x2="632.9" y2="482" stroke="#9CA3AF" stroke-dasharray="4 4"/><rect x="590.4" y="8" width="84.9" height="46" rx="6" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.5"/><text x="632.9" y="34.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="#111827">Dashboard</text><text x="114.3" y="69.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">1. message</text><line x1="67.1" y1="76" x2="155.4" y2="76" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><text x="208.6" y="99.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">2–3. bytes → decode</text><line x1="161.4" y1="106" x2="249.7" y2="106" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><text x="302.9" y="129.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">decoded message</text><line x1="255.7" y1="136" x2="344.0" y2="136" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><path d="M350.00000000000006,160 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a8)"/><text x="384.00000000000006" y="170" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">4. auth · 5. facility</text><text x="384.00000000000006" y="183" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">6. validate · 7. idempotency key</text><text x="397.1" y="202.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">8. persist (PENDING)</text><line x1="350.0" y1="209" x2="438.3" y2="209" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><text x="255.7" y="232.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">intake result</text><line x1="350.0" y1="239" x2="167.4" y2="239" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a8)"/><text x="114.3" y="262.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">12. protocol response / ACK*</text><line x1="161.4" y1="269" x2="73.1" y2="269" stroke="#374151" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#a8)"/><text x="491.4" y="292.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">9. claim (lease)</text><line x1="538.6" y1="299" x2="450.3" y2="299" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><path d="M538.5714285714286,323 h28 v16 h-22" fill="none" stroke="#374151" stroke-width="1.3" marker-end="url(#a8)"/><text x="572.5714285714286" y="333" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">10. HMS boundary</text><text x="572.5714285714286" y="346" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="#111827">(gated handler)</text><text x="491.4" y="352.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">SUCCEEDED / RETRY_WAIT /</text><text x="491.4" y="365.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">DEAD_LETTER + audit</text><line x1="538.6" y1="372" x2="450.3" y2="372" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><text x="538.6" y="395.0" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#111827">11. observability reads</text><line x1="632.9" y1="402" x2="450.3" y2="402" stroke="#374151" stroke-width="1.4" marker-end="url(#a8)"/><rect x="27.5" y="420" width="644.9" height="24" rx="4" fill="#FFFBEB" stroke="#D97706"/><text x="350.0" y="435" font-family="Arial, Helvetica, sans-serif" font-size="11" text-anchor="middle" fill="#78350F">* HTNG: profile ack / fault. FIAS: no ACK until the official rules (HF-06) exist.</text></svg><figcaption>Figure 8: End-to-end system sequence</figcaption></figure>

## 7.2 Step by step (12 steps)

| # | Step | Enna nadakkudhu | Code |
|---|---|---|---|
| 1 | Vendor sends | HTNG: HTTP POST; FIAS: TCP bytes | — |
| 2 | Transport receives | HTNG endpoint size/switch checks; FIAS framer frames | `api/router.py`, `transport/framing.py` |
| 3 | Protocol parser | `HTNGAdapter.decode` / `FIASAdapter.decode` | `adapters/` |
| 4 | Authentication | `ClientAuthenticator` (HTNG headers-la; FIAS link client-ku bind) | `security/clients.py` |
| 5 | Facility mapping | `FacilityResolver.resolve` + smuggling check | `security/facility.py` |
| 6 | Validation | handler registered, idempotency key, envelope validation | `exchange/gateway.py` |
| 7 | Idempotency | unique key + fingerprint | `processing/sql_repository.py` (`accept`) |
| 8 | Persist | PENDING row + payload + idempotency key (one transaction) | `processing/sql_repository.py` |
| 9 | Worker | claim with lease → dispatch | `processing/worker.py` |
| 10 | HMS boundary | `StayDomainAdapter` → `stays_write` (gate open-na mattum) | `domain/stays.py` |
| 11 | Audit + observability | audit row same transaction; counters; dashboard reads | `processing/repository.py`, `observability.py` |
| 12 | Response/ACK | HTNG: ack / 202 / fault; FIAS: responder configure aana mattum | `api/router.py`, `transport/tcp.py` |

> **Note:** Intake-la status RECEIVED → VALIDATED → PENDING memory-la nadakkum; database-la first row **PENDING**-ah dhaan save aagum. Reject aana message database-la save aagaadhu (REJECTED terminal, in-memory).

## 7.3 Failure paths

| Failure | Behaviour | Evidence |
|---|---|---|
| Invalid message (bad XML, schema fail, unknown type) | Intake **REJECTED**, nothing stored; HTNG 400 fault; metric `intake_rejected` | certification HTNG-SYN-005/013/014/015, FIAS-SYN-004 |
| Duplicate | Same fingerprint → DUPLICATE (one row); different content same key → conflict 409 | HTNG-SYN-009, FIAS-SYN-007, HMS-SYN-003 |
| Database unavailable at intake | HTNG: 503 (retryable, nothing stored); FIAS: LinkPump retries frame | HTNG-SYN-011, FIAS-SYN-011 |
| Worker unavailable / crash | Messages PENDING-la safe; lease expire → vera worker | FIAS-SYN-012, HMS-SYN-009 |
| Lease lost mid-handler | HMS change rollback (savepoint) | HMS-SYN-008 |
| Retry exhaustion | max attempts → DEAD_LETTER | `test_exchange.py`, HTNG-SYN-012 (recovery path) |
| DLQ | operator dashboard-la paakkalaam (read-only) | `test_observability.py`, E2E F1–F5 |
| Audited redrive | write grant + reason → PENDING → reprocess | FIAS-SYN-015, HMS-SYN-010 |

## 7.4 Shared processing — retry & DLQ (recap diagram)

Chapter 4.7 lifecycle diagram (PENDING → PROCESSING → SUCCEEDED / RETRY_WAIT / DEAD_LETTER → redrive) idhukkum apply aagum.

**Chapter 7 summary:** Message lose aagaama, duplicate aagaama, correct facility-ku, correct order-la process aaganum-ngradhukku ovvoru step-um design pannirukkom. Failure-um "known state"-ku dhaan pogum.

# Chapter 8 – Database and Data Flow

Database dhaan indha integration-oda "memory". Vendor-ku "accepted"-nu sonna message enna aanaalum lose aagakoodadhu — adhukku message munnaadiye database-la save aaganum. Indha chapter-la endha tables, endha columns, avanga relationship, data eppadi flow aagudhu — ellame actual SQLAlchemy models (`backend/app/integrations/processing/sql_models.py`) padichu dhaan ezhudhirukkom. Model-la illaadha column-ai inga sollala.

Mukkiyamaa nyabagam vechukka vendiyadhu: **indha tables HMS production database-la innum create aagala.** Disposable test databases-la mattum create panni test pannirukkom.

## 8.1 Schema status — naalu category

| Category | Enna | Enga |
|---|---|---|
| **Existing active HMS schema** | Integration tables **illa**. Integration code existing `facility` table-ah FK-ku mattum refer pannum | HMS models (`app/models`) |
| **Draft migration (candidate)** | 7 integration tables. Alembic `versions/`-la illa; HMS database-la apply aagala; disposable MySQL-la mattum create panni test | `backend/migrations/drafts/integration_tables_candidate.py`, `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`, `processing/sql_models.py` |
| **Proposed schema changes** | `direction`, `protocol` CHECK constraints (BLK-D6) — **proposal mattum**, model-la add pannala | `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` §11 |
| **Pending DBA approval** | Ellame — tables, `down_revision` (two Alembic heads), live DB revision, 19 pre-existing MySQL incompatibilities, backup/rollback, XSD library (HF-39) | DBA package §7, §10 |

## 8.2 ER-style diagram (verified models only)

<figure class="diagram" id="fig-er"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 560" width="100%" role="img" style="max-width:700px"><defs><marker id="a9" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="260" y="10" width="180" height="46" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="350.0" y="21.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">facility (existing</text><text x="350.0" y="37.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">HMS)</text><text x="350.0" y="53.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">id CHAR(36)</text><rect x="10" y="90" width="220" height="96" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="120.0" y="111.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_clients</text><text x="120.0" y="126.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">id · client_code (UNIQUE)</text><text x="120.0" y="142.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">secret_hash ·</text><text x="120.0" y="158.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">secondary_secret_hash</text><text x="120.0" y="173.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">enabled · protocols</text><rect x="470" y="90" width="220" height="96" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="580.0" y="111.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_facility_mappings</text><text x="580.0" y="126.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">id · client_id · facility_id</text><text x="580.0" y="142.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">external_property_code</text><text x="580.0" y="158.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">normalized_property_code ·</text><text x="580.0" y="173.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">enabled</text><rect x="210" y="220" width="280" height="140" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="224.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_inbound_messages</text><text x="350.0" y="239.7" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">id · client_id · facility_id</text><text x="350.0" y="255.3" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">protocol · direction · message_type</text><text x="350.0" y="270.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">idempotency_key · ordering_key</text><text x="350.0" y="286.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">status · attempt_count ·</text><text x="350.0" y="302.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">max_attempts</text><text x="350.0" y="317.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">next_attempt_at ·</text><text x="350.0" y="333.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">lease_owner/token/expires_at</text><text x="350.0" y="349.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">last_error_code/category ·</text><text x="350.0" y="364.7" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">received_on</text><rect x="10" y="400" width="210" height="90" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="115.0" y="425.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_inbound_payloads</text><text x="115.0" y="441.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">message_id (PK, FK)</text><text x="115.0" y="457.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">body_canonical</text><text x="115.0" y="472.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">wire_payload (off)</text><rect x="245" y="400" width="210" height="90" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="418.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_idempotency_keys</text><text x="350.0" y="433.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">UNIQUE(client, facility,</text><text x="350.0" y="449.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">key)</text><text x="350.0" y="465.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">fingerprint</text><text x="350.0" y="480.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">message_id</text><rect x="480" y="400" width="210" height="90" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="585.0" y="425.9" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_outbox_messages</text><text x="585.0" y="441.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">source_message_id</text><text x="585.0" y="457.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">client_id · facility_id</text><text x="585.0" y="472.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">status · attempt_count</text><rect x="10" y="250" width="170" height="80" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="95.0" y="263.1" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">integration_audit_events</text><text x="95.0" y="278.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">actor_type · action</text><text x="95.0" y="294.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">facility_id ·</text><text x="95.0" y="310.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">message_id</text><text x="95.0" y="325.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(no FKs)</text><line x1="470.0" y1="138.0" x2="230.0" y2="138.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="316.2" y="128.0" width="67.6" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="350.0" y="141.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">client_id</text><line x1="580.0" y1="90.0" x2="350.0" y2="56.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="424.8" y="63.0" width="80.4" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="465.0" y="76.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">facility_id</text><line x1="250.0" y1="220.0" x2="120.0" y2="186.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="151.2" y="193.0" width="67.6" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="185.0" y="206.8" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">client_id</text><line x1="350.0" y1="220.0" x2="350.0" y2="56.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="309.8" y="121.0" width="80.4" height="34" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="350.0" y="135.0" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">facility_id</text><text x="350.0" y="148.7" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">(RESTRICT)</text><line x1="115.0" y1="400.0" x2="240.0" y2="360.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="150.1" y="370.0" width="54.8" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="177.5" y="383.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">CASCADE</text><line x1="350.0" y1="400.0" x2="350.0" y2="360.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="322.6" y="370.0" width="54.8" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="350.0" y="383.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">CASCADE</text><line x1="585.0" y1="400.0" x2="460.0" y2="360.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a9)"/><rect x="491.9" y="370.0" width="61.2" height="20" rx="3" fill="#FFFFFF" fill-opacity="0.95"/><text x="522.5" y="383.9" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="normal" text-anchor="middle" fill="#1F2937">SET NULL</text><rect x="10" y="535" width="16" height="12" rx="2" fill="#FEF3C7" stroke="#B45309"/><text x="32.0" y="544.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Candidate table (HF-39, disposable DBs only)</text><rect x="304.4" y="535" width="16" height="12" rx="2" fill="#FCE7F3" stroke="#BE185D"/><text x="326.4" y="544.7" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="normal" text-anchor="start" fill="#374151">Existing HMS table</text></svg><figcaption>Figure 9: Integration tables (ER-style, verified models)</figcaption></figure>

Columns diagram-la mukkiyamaanadhu mattum; full list DBA package Appendix A (models-la irundhu generate aanadhu).

## 8.3 Tables explained

| Table | Enna store pannudhu | Key points |
|---|---|---|
| `integration_clients` | Vendor link client | `client_code` UNIQUE; `secret_hash` + `secondary_secret_hash`/`secondary_expires_on` (rotation); `enabled` default 0; `protocols` (comma list) |
| `integration_facility_mappings` | Client + property code → facility | UNIQUE (client_id, normalized_property_code); `utf8mb4_bin`; `enabled` default 0; FK facility RESTRICT |
| `integration_inbound_messages` | Message metadata + processing state | protocol, direction, message_type, idempotency_key, ordering_key, correlation_id, payload_hash, status (CHECK), attempt_count (CHECK ≥ 0), max_attempts, next_attempt_at, lease_owner/token/expires_at, last_error_code/category, received_on, completed_on |
| `integration_inbound_payloads` | Canonical body (LONGTEXT), optional raw bytes (MEDIUMBLOB, off), retain_until | PK = message_id, FK CASCADE |
| `integration_idempotency_keys` | Duplicate detection | UNIQUE (client, facility, key); fingerprint; FK message CASCADE |
| `integration_outbox_messages` | Outbound queue | status (CHECK), attempts, lease, `source_message_id` FK SET NULL |
| `integration_audit_events` | Append-only audit | actor_type, actor_id, action, facility_id, message_id, reason, detail JSON — **FK illa** |

## 8.4 Mukkiya columns — artham

- **Status:** inbound CHECK values `RECEIVED, VALIDATED, PENDING, PROCESSING, SUCCEEDED, RETRY_WAIT, DEAD_LETTER, REJECTED`; outbox `PENDING, PROCESSING, SENT, RETRY_WAIT, DEAD_LETTER`.
- **Protocol:** `VARCHAR(16)`, **CHECK illa**. Code enum: `fias`, `htng`, `test`.
- **Direction:** `VARCHAR(16)`, **CHECK illa**. Code enum: `inbound`, `outbound`; gateway eppovum `inbound` dhaan ezhudhum (Chapter 13 defect).
- **Facility relationship:** `facility_id` FK → HMS `facility.id`, `ON DELETE RESTRICT` (integration rows irukkura facility delete aagaadhu — intended).
- **Retry info:** `attempt_count`, `max_attempts`, `next_attempt_at`, `last_error_*`.
- **DLQ info:** status `DEAD_LETTER` + `last_error_*` + `completed_on`.
- **Worker lease:** `lease_owner`, `lease_token`, `lease_expires_at`.
- **Indexes:** (facility_id, status, received_on), (client_id, facility_id, ordering_key, received_on), next_attempt_at, correlation_id.

## 8.5 Data flow (write path)

1. `accept()` one transaction: message row (PENDING) + payload row + idempotency row.
2. `claim()`: PROCESSING + lease.
3. `completion()`: SUCCEEDED + `completed_on` + outbox rows + audit rows + HMS change — one transaction (savepoint join).
4. `record_failure()`: RETRY_WAIT (next_attempt_at) or DEAD_LETTER (completed_on).
5. `redrive()`: DEAD_LETTER → PENDING + audit.
6. `purge_completed()`: SUCCEEDED/SENT rows older than retention — **retention set aana mattum** (HF-21); PENDING/RETRY/DLQ rows purge aagaadhu.

## 8.6 Database conventions & limits

MySQL ≥ 8.0.16 (CHECK enforce, SKIP LOCKED); ids CHAR(36); DATETIME(6) UTC; body cap 256 KiB. HMS schema-vai repository-la irundhu MySQL-la bootstrap panna **19 pre-existing incompatibilities** (BOOL default, JSON index, JSON default) irukku — tests-ku `tests/integrations/hms_schema_shim.py` workaround; HMS models-ah maathala.

**Chapter 8 summary:** 7 candidate tables design & test aagirukku; production DB-la onnum create aagala. DBA approval (HF-39) & BLK-D6 constraint decision pending.

# Chapter 9 – Security Architecture

Security-la namma principle simple: **default-ah ellam moodi irukkum; open panna explicit switch-um approval-um venum.** Vendor message, operator request, test tool — yaaraa irundhaalum identity check, facility check, permission check — moonum nadakkum. Kezha irukkura table-la ovvoru control-um enna, yen, enga irukku-nu paakkalaam. "Yen" column dhaan mukkiyam — ovvoru control-um oru specific risk-ai thadukka dhaan irukku.

| Control | Enna | Yen | Enga |
|---|---|---|---|
| Integration authentication | client code + secret; hash-only; constant-time compare | Fake vendor message block | `security/clients.py` |
| Facility isolation (intake) | client-scoped mapping, bound property, scope-smuggling check | Oru vendor vera hotel data inject panna koodadhu | `security/facility.py`, `exchange/gateway.py` |
| Facility isolation (operators) | Every API query `user.facility_ids`-ku scope; out-of-scope record → 404; out-of-scope filter → 403 | Hotel A staff Hotel B data paakka koodadhu | `api/router.py` (`_scope`, `_facility_filter`) |
| RBAC | `facility_management` read/write | Least privilege | `app/api/deps.py` (`require_permission`) |
| IP allow-list | FIAS listener `allowed_peers` mandatory; one connection | Unknown IP connect panna koodadhu | `transport/tcp_server.py` |
| Credential rotation | 0–7 day overlap, early revoke, audited | Secret leak aana zero-downtime change | `admin.py` |
| Secret protection | secret oru thadava print; log/report-la illa; masking | Leak prevent | `core/masking.py`, `security/clients.py` |
| XML parser security | DOCTYPE/entity reject; size/depth/element limits | XXE, billion laughs | `transport/xml_security.py` |
| Raw payload retention | raw wire bytes default **off**; retention unset | Guest data minimise (HF-21 pending) | `config.py` |
| Live HMS write restriction | env flag **and** HF-01/02/05/19 Approved with evidence **and** actor UUID | Approval illaama HMS data maaradhu | `domain/approvals.py`, `config.py` |
| Feature switches | ellam default off | Accidental activation prevent | `config.py` |
| Simulator restriction | opt-in + loopback only | Test tool production-la expose aagakoodadhu | `simulators/fias_simulator.py` |
| Database isolation (testing) | tests disposable DB-la mattum; configured HMS DB name-ah refuse; E2E internal network-la | Real HMS data touch aagakoodadhu | `tests/integrations/conftest.py`, E2E report |
| Error sanitisation | API-la error code/category mattum; identifier pattern match aagaadhadhu "redacted" | Free-text-la PII leak aagakoodadhu | `observability.py` (`safe_identifier`) |

**Pending security decisions:** HF-08 (HTNG WS-Security/mTLS), HF-21 (retention/encryption), HF-22 (secret storage), HF-23 (audit immutability), HF-24 (network/TLS). Evidence: `docs/HTNG_FIAS_SECURITY_DESIGN.md`, `docs/HTNG_FIAS_SECRET_SCAN_REPORT.md`.

**Chapter 9 summary:** Default-ah ellam closed; open panna explicit switch + approval venum. Isolation intake-lum operator pakkamum rendu idathulayum enforce.

# Chapter 10 – Observability Dashboard

Dashboard-oda velai: operator-ku "ippo integration-la enna nadakkudhu"-nu oru paarvaiyila kaattradhu — evvalavu messages vandhuchu, evvalavu pending, edhu fail aachu, edhu DLQ-la irukku, vendor validation enga irukku. Idhu **read-only** — dashboard-la irundhu endha data-vum maathaadhu, redrive button-um illa. Existing HMS login, existing permissions, existing page layout — ellame reuse pannirukkom; pudhusa oru login system build pannala.

## 10.1 Navigation and API data flow

<figure class="diagram" id="fig-dashboard"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 470" width="100%" role="img" style="max-width:700px"><defs><marker id="a10" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="10" width="660" height="50" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="350.0" y="31.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Sidebar group &#x27;Integrations&#x27; (AppSidebar.tsx) + ModuleGuard →</text><text x="350.0" y="47.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">moduleForPath(&#x27;/integrations&#x27;) = facility_management</text><rect x="20" y="90" width="120" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="80.0" y="114.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Overview</text><text x="80.0" y="130.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">/integrations</text><rect x="150" y="90" width="120" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="210.0" y="114.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HTNG</text><text x="210.0" y="130.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">/integrations/htng</text><rect x="280" y="90" width="120" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="340.0" y="114.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">FIAS</text><text x="340.0" y="130.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">/integrations/fias</text><rect x="410" y="90" width="130" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="475.0" y="114.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Message Logs</text><text x="475.0" y="130.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">/integrations/messages</text><rect x="550" y="90" width="130" height="56" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="615.0" y="114.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Failed / DLQ</text><text x="615.0" y="130.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">/integrations/dlq</text><rect x="20" y="180" width="660" height="50" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="350.0" y="201.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">React Query hooks (lib/api/hooks.ts): useIntegrationOverview · useIntegrationMessages ·</text><text x="350.0" y="217.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">useIntegrationDeadLetters</text><rect x="20" y="260" width="660" height="44" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="350.0" y="286.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">apiClient (lib/api/client.ts): Bearer JWT · ApiError · 401 → sign-out event</text><rect x="20" y="334" width="660" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="350.0" y="355.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">GET /api/v1/integrations/observability/overview · /messages · /dlq</text><text x="350.0" y="371.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">require_permission(&#x27;facility_management&#x27;,&#x27;read&#x27;) + scope = user.facility_ids</text><rect x="20" y="414" width="660" height="44" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="440.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">build_overview() · repository.search_messages() → integration tables (read-only)</text><line x1="80.0" y1="146.0" x2="80.0" y2="180.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="210.0" y1="146.0" x2="210.0" y2="180.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="340.0" y1="146.0" x2="340.0" y2="180.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="475.0" y1="146.0" x2="475.0" y2="180.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="615.0" y1="146.0" x2="615.0" y2="180.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="350.0" y1="230.0" x2="350.0" y2="260.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="350.0" y1="304.0" x2="350.0" y2="334.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/><line x1="350.0" y1="384.0" x2="350.0" y2="414.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a10)"/></svg><figcaption>Figure 10: Dashboard / API architecture</figcaption></figure>

- **Frontend files:** `frontend/src/features/integrations/` (pages, views, components, lib), `frontend/src/lib/api/integrations.ts` (types + endpoint functions), hooks `frontend/src/lib/api/hooks.ts`, routes `frontend/src/App.tsx`, sidebar `frontend/src/components/layout/AppSidebar.tsx`, RBAC map `frontend/src/core/rbac/modules.ts`.
- **Permission:** route guard & sidebar rendum `facility_management` read; illa-na "Access denied", API call-um pogaadhu.
- **Facility isolation:** backend already scope pannum; frontend facility filter options = user-oda `facility_ids` mattum; URL-la vera facility id pottaalum request-la anuppaadhu (`restrictToScope`).
- **Null rule:** measure panna mudiyaadha value "Data unavailable" / "Not observable" (grey dashed) — **0 illa**; "unknown" red colour illa.

## 10.2 Ovvoru page-um

| Page | Purpose | Data / API | Filters | States | Limitations |
|---|---|---|---|---|---|
| **Integrations Overview** `/integrations` | Shared summary + HTNG & FIAS cards | `GET …/observability/overview` (60 s refetch + Refresh) | — | loading text; error + Retry (5xx/network); 403 "Access denied"; 401 → login | Counts = retained rows (lifetime illa) |
| **HTNG Monitoring** `/integrations/htng` | HTNG transport, auth, processing, stats, recent, failed, vendor requirements, 8 readiness dimensions | overview + `…/messages?protocol=htng` (10) + `…/dlq?protocol=htng` (5) | — | per-section error/empty | Recent list inbound mattum |
| **FIAS Monitoring** `/integrations/fias` | Same for FIAS + link table (tagged links mattum) | same with `fias` | — | "Not observable" link state | FIAS link API process-la illa → not observable |
| **Message Logs** `/integrations/messages` | Server-side search | `GET …/observability/messages` | protocol, status, facility, date (≤31 days), rows per page; URL-la sync | skeleton, empty, invalid-date alert, error + Retry | Message-ID search API-la illa; single-select filters |
| **Failed Messages / DLQ** `/integrations/dlq` | Dead letters read-only | `GET …/observability/dlq` | protocol, facility, date | empty, error | **Redrive button illa** (eligibility mattum) |

**Chapter 10 summary:** Real APIs, existing auth/RBAC, facility scope, honest "unknown" states. Read-only.

# Chapter 11 – API Documentation

Indha chapter-la integration API endpoints ellathayum actual router code (`backend/app/integrations/api/router.py`) padichu list pannirukkom — code-la illaadha endpoint-o field-o inga illa. Moonu type endpoints irukku: (1) **public** — `/health` mattum, data edhuvum kudukkaadhu; (2) **operator** — HMS login (JWT) + `facility_management` permission venum, data ellam user-oda facilities-ku mattum; (3) **vendor** — `/htng/inbound`, idhu HMS user login use pannaadhu, integration client code + secret headers use pannum.

Ellam `/api/v1/integrations` prefix kooda (`backend/app/api/v1/router.py` mount pannudhu). Operator endpoints: HMS JWT Bearer + `require_permission("facility_management", …)` + facility scope. Errors: `{"error": {"code", "message", "detail"}}` HMS envelope.

## 11.1 Endpoint table (actual code: `backend/app/integrations/api/router.py`)

| Method | Path | Purpose | Permission | Query / body | Facility scope |
|---|---|---|---|---|---|
| GET | `/health` | Liveness, data illa | **public** | — | — |
| GET | `/readiness` | Components readiness (503 if not ready) | read | — | — |
| GET | `/adapters` | Adapter readiness + blocking decisions | read | — | — |
| GET | `/messages` | Inbound messages metadata | read | `status`, `limit` 1–200 | yes |
| GET | `/messages/{message_id}` | One message, **body masked** | read | — | yes (out of scope → 404) |
| GET | `/dlq` | Dead letters | read | `limit` 1–200 | yes |
| POST | `/messages/{message_id}/redrive` | Audited redrive | **write** | body `{"reason": 10–500 chars}` | yes |
| GET | `/outbox` | Outbound queue | read | `status`, `limit` | yes |
| GET | `/metrics` | Counters + status counts | read | — | counts scoped |
| GET | `/facilities/health` | Per-facility health | read | `window_minutes` 1–10080 | yes |
| GET | `/observability/overview` | Dashboard model | read | `stall_threshold_seconds` 60–86400 (default 900) | yes |
| GET | `/observability/messages` | Search (Page) | read | `protocol`, `status`, `facility_id` (≤50), `received_from`, `received_to`, `page`, `page_size` ≤100 | yes; foreign facility → 403 |
| GET | `/observability/dlq` | Dead letters (Page) | read | `protocol`, `facility_id`, dates, `page`, `page_size` | yes |
| GET | `/audit` | Audit trail | read | `limit` 1–200 | yes |
| GET | `/mappings` | Mappings in my facilities | read | — | yes |
| POST | `/mappings` | Create mapping (DISABLED, audited) | **write** | `{client_code, external_property_code, facility_id}` → 201 | facility must be in scope |
| PATCH | `/mappings/{mapping_id}` | Enable/disable (audited) | **write** | `{enabled, reason}` | yes |
| POST | `/htng/inbound` | Vendor SOAP endpoint | integration client headers (not HMS JWT) | SOAP body; `X-Integration-Client`, `X-Integration-Secret`, `X-Correlation-ID` | via mapping |

## 11.2 Observability response structures (verified)

**`GET /observability/overview`** → `generated_at`, `facility_scope`, `overview` {`htng_status`, `fias_status` (transport, processing, vendor_validation, production_readiness), `readiness_classification`, `messages` {status, basis, processed, pending, failed_dead_letter, outbound_dead_letter, last_successful_exchange_at}}, `protocols` {`htng`, `fias`: configuration.adapters, transport, authentication, processing, messages, last_error, intake_rejections, readiness (8 dimensions)}, `other_protocols`.

**`GET /observability/messages`** → HMS Page: `items`, `page`, `page_size`, `total`, plus `window` {received_from, received_to}. Item: `message_id, protocol, facility_id, direction, message_type, status, received_at, completed_at, attempt_count, retry_count, max_attempts, next_attempt_at, correlation_id, error {code, category}`. Errors: 422 (naive datetime, window > 31 days, page_size > 100, offset > 10,000, unknown enum), 403 (facility outside scope), 503 (persistence unavailable).

**`GET /observability/dlq`** → same Page; item: `message_id, protocol, facility_id, direction, message_type, status, failure_category, failure_code, attempt_count, retry_count, received_at, last_attempt_at, correlation_id, redrive {state_eligible, caller_has_permission, eligible}`. Default date window illa (DEAD_LETTER index use).

**Never returned:** payload, payload_hash, idempotency/ordering keys, external ids, client codes/secrets, lease owner.

## 11.3 Other responses (summary)

- `/messages` item (`StoredMessage.as_public_dict`): message & client ids, protocol, direction, type, external id, correlation, ordering key, schema version, payload hash, status, attempts, lease, last error, received/completed times. (Observability search-ai vida adhigam fields — operator detail use.)
- `/messages/{id}`: above + `body_masked` (`mask_mapping` — guest fields, e-mails, long digit runs masked).
- `/readiness`: `status`, `reasons[]`, `components` {persistence, adapters, workers, transports, vendor_endpoints: "not_configured", live_domain_writes}.
- `/facilities/health`: `generated_at`, `window_minutes`, `facilities[]`, `transports`, `auth_failures`.

**Chapter 11 summary:** 18 endpoints; 17 operator/public + 1 vendor endpoint. Write endpoints moonu mattum (redrive, create mapping, update mapping) — ellam write permission + audit.

# Chapter 12 – Testing and Verification

Testing-ai layers-ah panni irukkom — chinna unit tests-la irundhu full stack browser test vara. Ovvoru layer-um vera vera kelvikku badhil sollum: "logic sariyaa?", "database-la-um same-ah work aagudhaa?", "real browser-la sariyaa theriyudhaa?", "ellam serndhu work aagudhaa?".

Rendu vishayam theliva purinjukkanum:

- **Ellame synthetic/disposable.** Fake-aana aana realistic data, throwaway databases. Real HMS database-ah thodala.
- **Idhu vendor certification illa.** Vendor-oda official documents-um test environment-um illaama certification nadakkave mudiyaadhu. Adhunaala dhaan official vendor scenarios 5-um "BLOCKED"-nu honest-ah report aagudhu.

## 12.1 Testing architecture

<figure class="diagram" id="fig-testing"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 520" width="100%" role="img" style="max-width:700px"><defs><marker id="a11" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="10" width="660" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="350.0" y="31.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Unit / component tests — in-memory repository, synthetic adapters (test_core,</text><text x="350.0" y="47.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">test_exchange, test_security, …)</text><rect x="20" y="74" width="660" height="50" rx="8" fill="#FEF3C7" stroke="#B45309" stroke-width="1.6"/><text x="350.0" y="95.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Repository contract — same tests on in-memory AND disposable MySQL 8.4</text><text x="350.0" y="111.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(test_repository_contract, test_mysql_persistence)</text><rect x="20" y="138" width="660" height="50" rx="8" fill="#E0F2FE" stroke="#0369A1" stroke-width="1.6"/><text x="350.0" y="159.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Transport — loopback TCP + FiasTestSimulator; SOAP 1.1/1.2 (test_transport_*,</text><text x="350.0" y="175.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">test_fias_adapter, test_htng_adapter)</text><rect x="20" y="202" width="660" height="50" rx="8" fill="#FCE7F3" stroke="#BE185D" stroke-width="1.6"/><text x="350.0" y="223.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">HMS workflow — real stays_write on seeded disposable MySQL (test_hms_domain_mysql,</text><text x="350.0" y="239.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">test_e2e_hms_simulation)</text><rect x="20" y="266" width="660" height="50" rx="8" fill="#DCFCE7" stroke="#15803D" stroke-width="1.6"/><text x="350.0" y="295.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Certification harness — 45 scenarios: 40 PASS · 5 BLOCKED (official vendor scenarios)</text><rect x="20" y="330" width="660" height="50" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="350.0" y="359.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Frontend — node:test + esbuild + server render: 49 tests (14 existing + 35 integrations)</text><rect x="20" y="394" width="660" height="50" rx="8" fill="#EDE9FE" stroke="#6D28D9" stroke-width="1.6"/><text x="350.0" y="423.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Browser visual QA — real build in headless Edge, mocked API, 5 pages × 4 viewports</text><rect x="20" y="458" width="660" height="50" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="350.0" y="479.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">Full-stack E2E — Edge → proxy → real FastAPI → disposable MySQL on an internal network:</text><text x="350.0" y="495.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">90 API + 56 browser checks</text></svg><figcaption>Figure 11: Testing architecture</figcaption></figure>

## 12.2 Verification layers

Ovvoru result-um **avangalukku sondhamaana report-la irundhu**; historical counts-ah oru single number-ah combine pannala.

| Layer | Enna test | Eppadi | Result (source) | Enna prove pannudhu | Enna prove pannala |
|---|---|---|---|---|---|
| Backend integration suite | Core, security, exchange, transport, adapters, repository, ordering, domain, API, observability, certification | pytest; in-memory + disposable MySQL 8.4 | **517 collected · 516 passed · 1 skipped** (skip = official vendor samples illa) — latest full run, `docs/HTNG_FIAS_OBSERVABILITY_IMPLEMENTATION_REPORT.md`; 517 count indha document-kaga re-collect panni confirm | Framework logic correct with synthetic inputs | Real vendor compatibility |
| Repository contract | Same behaviour in memory & MySQL | `repo` fixture rendu backend-la | `test_repository_contract.py` 40 tests (part of above) | SQL implementation = reference behaviour | Production DB behaviour (HF-39) |
| HTNG synthetic | SOAP 1.1/1.2, faults, 415, XML safety, duplicates, outage | certification HTNG-SYN-001…015 | 15/15 PASS (`HTNG_FIAS_CERTIFICATION_SPRINT_REPORT.md`) | Generic SOAP/HTNG pipeline | Vendor WSDL/XSD/profile |
| FIAS synthetic | framing, split frames, malformed, encoding, oversize, reconnect, DB outage, worker crash, wrong property, DLQ redrive | FiasTestSimulator + TcpLink + LinkPump, synthetic "Z*" records | 15/15 PASS (same report) | TCP + framing + pipeline mechanics | Official FIAS records/ACK/heartbeat |
| Official vendor scenarios | HTNG-OFF-001/002, FIAS-OFF-001/002/003 | runner forces BLOCKED | **5 BLOCKED** (HF-06/07/08/11/39) | Honest "blocked" reporting | — |
| HMS workflow | Real `stays_write` check-in/out, ordering, lease loss, audit | Seeded disposable HMS MySQL | HMS-SYN-001…010: 10/10 PASS | Real HMS rules work through the pipeline | Live HMS DB; approvals |
| Observability (backend) | overview, search, DLQ, RBAC, isolation, null-not-zero | pytest | 45 passed (test_observability + test_api + test_health_view), `HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` | API contracts correct | — |
| Frontend | presentation rules, RBAC, pages, filters, pagination, states, API client | node:test + esbuild + server render | **49/49** (14 existing + 35 integrations), `HTNG_FIAS_DASHBOARD_VISUAL_QA_REPORT.md` | UI logic + contract rendering | Visual layout (next layer) |
| Browser visual QA | 5 pages × 4 viewports, failure states, real clicks | Headless Edge 157, real production build, mocked API | Defects D1–D7 found & fixed; pass 2 clean (`…VISUAL_QA_REPORT.md`) | Real browser rendering | Firefox/Safari; real backend |
| Full-stack E2E | Real build ↔ real FastAPI ↔ disposable MySQL; login, filters, isolation, failures | Internal Docker network, isolation proven inside backend | **90/90 API checks, 56/56 browser checks** (`…FULLSTACK_E2E_VERIFICATION_REPORT.md`) | Whole stack works together; facility isolation; RBAC | Vendor traffic; production DB |
| Isolation verification | No route, unresolvable real hosts, engine hostname = disposable DB | `isolation_check.py` inside container | All checks passed (E2E report §3) | Tests never touched real HMS DB | — |

## 12.3 Failure scenario testing (E2E, real stack)

Backend stopped → error + Retry → recovery; database stopped → "Service unavailable" → recovery; permission revoked mid-session → real 403 "Access denied"; corrupt row → genuine 500 (partial failure, Chapter 13); integration tables missing → "Data unavailable", **zero zeros**; empty data → real zeros + empty states; expired JWT → login.

## 12.4 Baseline (pre-existing) results — namma code-ala illa

- Frontend type check: **6 errors in 4 non-integration files**; lint **3 errors, 7 warnings** — same before & after (`HTNG_FIAS_DASHBOARD_IMPLEMENTATION_REPORT.md`).
- `backend/tests/test_health_api.py`: **5 pre-existing failures** (4 need live HMS DB; OpenAPI test non-integration routes-naala).
- Legacy HMS suite **latest sprints-la re-run pannala**. Earlier round historical run (seeded disposable DB): 1,250 passed, 78 failed, 1 skipped — pristine copy-um same result (earlier sprint record; indha document-kaga re-run pannala).

**Chapter 12 summary:** Layered testing — unit to full stack. Ellam synthetic/disposable. **Idhu vendor certification illa.**

# Chapter 13 – Known Issues and Limitations

## 13.1 Invalid `direction` value (BLK-D6, HF-39 package §11)

- **Reproduction (E2E sprint, disposable DB):** oru row `protocol='htng', direction='sideways'` direct-ah insert.
- **Impact observed:** overview count-la serndhadhu (HTNG inbound 16 → 17, pending 5 → 6); message search **HTTP 500**; DLQ list **500** (HTNG page recent list error, mattha sections normal).
- **Root cause (code verify pannadhu):** `direction` column-ku CHECK illa (`sql_models.py`, candidate SQL); `_to_stored()` `Direction(row.direction)` unknown value-ku `ValueError` raise; router `IntegrationError`/`SQLAlchemyError` mattum handle pannudhu → 500; overview aggregates `direction` parse pannaadhadhaala count aagudhu.
- **Investigated:** disposable test DBs-la read-only validation — `direction` ellam `inbound`, invalid rows 0; `protocol` values `test` & `fias` (test suite `test` ezhudhum — protocol CHECK-la idha consider pannanum).
- **Suspected (verify aagala):** worker `claim()` `_to_stored` call pannradhaala bad claimable row batch-ah rollback panni queue-ah stall pannalaam — **code reading mattum, reproduce pannala**.
- **Yen unfixed:** schema/model change & backend code change-ku DBA/architecture approval venum.
- **Decision required:** Option A `direction IN ('inbound','outbound')` vs Option B `direction = 'inbound'`; protocol allowed values (ARCH + DBA, Q8).
- **Safe remediation:** validate first (read-only queries); bad rows silent delete pannaadhey — export, correct (proof irundha), quarantine, or purge with sign-off; tolerant mapping in code (BE/ARCH approval); regression test.

## 13.2 Other verified gaps

| Issue | Detail | Where |
|---|---|---|
| HF-08 code register-la illa | `approvals.py` `DECISIONS`-la HF-08 illa; observability HTNG-ku HF-08 require pannudhu → eppovum "pending" (safe). Future-la approve aana code change venum. Proposed, not implemented | `domain/approvals.py`, `observability.py` |
| FIAS link not wired | No production process starts `TcpLink`/`TcpListenerLink` | `service.py` |
| HTNG outbound sender not wired | `HtngSoapSender` defined, never instantiated | `adapters/htng/sender.py` |
| Worker visibility | API process worker heartbeat paakka mudiyaadhu → "Not observable" | `metrics.py` |
| Counts lifetime illa | retention purge aana rows count-la varaadhu | `processing/activity.py` |
| Alembic two heads | `a3f1c8e2d904`, `b3c4d5e6f7a8` — DBA decide | DBA package §4 |
| 19 MySQL incompatibilities | HMS schema MySQL-la bootstrap aagaadhu (test shim mattum) | DBA package §4 |
| Dev backend environment | Running dev backend container `MYSQL_SSL_CA` illaama startup crash (environment config; integration code illa) | observed during "run" |

## 13.3 Dashboard limitations

Message-ID search illa (API support illa); outbound message list illa (counts mattum); single-select filters; 390 px-la HMS shell sidebar 150 px content-ku kurachidum (existing shell; collapse pannaa OK); shared pagination row mobile-la wrap aagaadhu; global CSS badge text black (tone background/border-la); header `/notifications` 403 & fixed "INSP Admin" label (existing `AppHeader.tsx`); Edge mattum test; dark mode check pannala.

## 13.4 Documentation discrepancies (recorded, not hidden)

- HF-18/21/27: canonical "Open" vs other registers "pending business approval" — canonical governs (blocker register reconciliation note).
- HF-05 vendor status but business section-la.
- Vendor sample location conflict — stricter rule (repository-ku veliya) apply pannom.
- Production readiness doc-la round-3 count (406) historical — dated evidence update append pannom.
- HF-40 options (E1–E3) & HF-30 dependency matha repository copy-la mattum — indha repo-la verify panna mudiyala.

**Chapter 13 summary:** Known issues ellam documented; edhuvum maraikkala; fix panna approval venum.

# Chapter 14 – Pending Vendor and Business Decisions

Code ezhudhi mudikka mudiyaadha vishayangal ivai — business, vendor, DBA, security, infrastructure owners dhaan decide pannanum. Engineering team oru recommendation kudukkalaam, aana approval kudukka mudiyaadhu. Indha decisions edhuvum approve aagaama, live HMS writes-um vendor connection-um production switches-um on aagaadhu — code-laye gate pottirukkom (`backend/app/integrations/domain/approvals.py`).

Owner-na oru **role** (PO, DBA, SEC …). Project documents-la endha individual peyarum illa — adhunaala "yaar" decide pannanum-nu role level-la dhaan solla mudiyum.

## 14.1 Official count (canonical register `docs/HTNG_FIAS_DECISION_REGISTER.md`)

**29 pending items = 28 HF decisions + BLK-V7. Approved: 0.**

| Status | Count | IDs |
|---|---|---|
| Awaiting Business Approval | 7 | HF-01, 02, 19, 20, 30, 31, 40 |
| Awaiting Vendor Confirmation | 9 | HF-04, 05, 06, 07, 08, 09, 11, 15, 24 |
| Open | 11 | HF-03, 14, 18, 21, 22, 23, 25, 26, 27, 37, 38 |
| Awaiting DBA Approval | 1 | HF-39 |
| Pending vendor documents | 1 | BLK-V7 |

Owner-group view (`HTNG_FIAS_EXTERNAL_BLOCKER_CLOSURE_READINESS_REPORT.md`): Vendor 9 · Business 14 · DBA 1 · Infrastructure 3 · Security 2. Named individual: **0/29**.

## 14.2 Mukkiya decisions

| ID | Artham | Yen venum | Owner (role) | Block aagura work |
|---|---|---|---|---|
| **HF-03** | Endha PMS vendor/product/version/hosting | Ellaa vendor requests-um idhai poruthadhu | PO | Vendor request dispatch, HF-04…09 |
| **HF-05** | FIAS property code case-sensitive-aa | Mapping normalisation | VENDOR, HOTEL-OPS | Verified mapping; live-write gate |
| **HF-06** | FIAS link rules: TCP role, host/port, framing, encoding, ACK, heartbeat, reconnect, resync | Production framer/responder/heartbeat | VENDOR, OPS | FIAS link layer |
| **HF-07** | HTNG version/profile/WSDL/XSD | Operations define panna | VENDOR | Every HTNG operation |
| **HF-08** | HTNG security profile (WS-Security, mTLS) | Endpoint expose panna | VENDOR, SEC | HTNG exposure |
| **HF-09** | Vendor test environment, credentials, certification process | Real validation | VENDOR, QA | Vendor validation |
| **HF-11** | FIAS official manual, record set, fields, samples | Parser configure panna | VENDOR | Every FIAS record |
| **HF-21** | Payload retention days, encryption, access, guest-data samples | Privacy/compliance | LEGAL, SEC | Purge, encryption, sample handling |
| **HF-25** | Worker/link hosting & supervision | Service deploy panna | ARCH, OPS | Supervised process |
| **HF-39** | DBA schema authorization (+ BLK-D6, XSD library) | Tables HMS DB-la create panna | ARCH, DBA, PO | Production persistence |
| **BLK-V7** | Vendor message volumes (HF decision illa) | Rate limit value | VENDOR, OPS | Rate limiting, load sizing |

Live HMS writes-ku extra: **HF-01** (system of record), **HF-02** (mapping ownership), **HF-19** (facility isolation rules), **HF-18** (integration actor account). Full list & actions: `docs/HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md`, ownership: `docs/HTNG_FIAS_OWNER_DECISION_TRACKER.md`.

**Chapter 14 summary:** Engineering-ala close panna mudiyaadha decisions idhu; owners (roles) decide pannanum. First: HF-03.

# Chapter 15 – Actual Work Completed vs Pending

Indha table-la ovvoru component-um ippo endha nilaiyila irukku-nu oru paarvaiyila paakkalaam. "Production readiness" column-la endha component-um "ready"-nu illa — adhu dhaan unmai.

| Component | Implementation status | Evidence | Remaining work | Dependency | Production readiness |
|---|---|---|---|---|---|
| Shared exchange (auth, mapping, idempotency, leases, retry, DLQ, redrive, ordering, audit) | Mudinjirukku; test aagirukku | 517-test suite; certification | Final retry/ordering policy decide pannanum | HF-27 | Innum illa |
| Persistence (7 tables) | Candidate design; disposable MySQL-la mattum test | DBA package, migration tests | DBA approval, migration, BLK-D6 constraint | HF-39 | Innum illa |
| HTNG endpoint + framework | Generic framework mudinjirukku | HTNG-SYN 15/15 | Official profile, XSD, security, outbound sender wire pannanum | HF-07, HF-08, HF-39 | **BLOCKED** |
| FIAS transport + parser framework | Generic framework mudinjirukku; production process-la wire aagala | FIAS-SYN 15/15 | Official spec, link rules, ACK/heartbeat, link process | HF-11, HF-06, HF-25 | **BLOCKED** |
| HMS stay handler | Mudinjirukku; seeded disposable DB-la test | HMS-SYN 10/10 | Approvals + actor account | HF-01, 02, 05, 18, 19 | Gate closed |
| Background service | Mudinjirukku | test_service | Hosting, restart policy | HF-25, HF-26 | Deploy aagala |
| Observability APIs | Mudinjirukku | 45 tests; E2E 90 checks | — | — | Data irundha use pannalaam |
| Dashboard (5 pages) | Mudinjirukku | 49 tests; visual QA; E2E 56 checks | Chinna limitations (Chapter 13) | — | Read-only-ah use pannalaam |
| Security controls | Mudinjirukku | test_security; secret scans | Decisions venum | HF-08, 21, 22, 23, 24 | Review pending |
| Vendor validation | **Start-e aagala** | — | Vendor pakkam ellame | HF-03 → HF-09 | **Illa** |

**Simple-ah sonna:** engineering foundation ready; vendor illaama, approvals illaama production-ku poga mudiyaadhu.

# Chapter 16 – Future Execution Roadmap

<figure class="diagram" id="fig-roadmap"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 460" width="100%" role="img" style="max-width:700px"><defs><marker id="a12" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker></defs><rect x="20" y="10" width="320" height="56" rx="8" fill="#FEE2E2" stroke="#B91C1C" stroke-width="1.6"/><text x="180.0" y="34.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">1. PO confirms PMS vendor / product /</text><text x="180.0" y="50.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">version / hosting (HF-03)</text><rect x="20" y="84" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="180.0" y="116.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">2. Identify vendor technical contact</text><rect x="20" y="158" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="180.0" y="182.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">3. Obtain official HTNG / FIAS documents</text><text x="180.0" y="198.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HF-07/08, HF-11/06)</text><rect x="20" y="232" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="180.0" y="256.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">4. Obtain sandbox + test credentials</text><text x="180.0" y="272.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HF-09, HF-22 channel)</text><rect x="20" y="306" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="180.0" y="330.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">5. Business / security / DBA / infra</text><text x="180.0" y="346.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">approvals (HF-01…, HF-39, HF-25/26)</text><rect x="20" y="380" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="180.0" y="396.8" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">6. Confirm protocol-specific contracts</text><text x="180.0" y="412.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(encode spec / profile as</text><text x="180.0" y="428.0" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">VERIFIED_OFFICIAL)</text><rect x="370" y="10" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="34.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">7. Isolated vendor test connectivity</text><text x="530.0" y="50.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">(HF-24)</text><rect x="370" y="84" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="116.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">8. Execute real message exchange</text><rect x="370" y="158" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="190.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">9. Fix issues + regression tests</text><rect x="370" y="232" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="256.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">10. Complete vendor validation (V-21,</text><text x="530.0" y="272.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">V-22)</text><rect x="370" y="306" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="338.4" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">11. Formal acceptance evidence</text><rect x="370" y="380" width="320" height="56" rx="8" fill="#FFFFFF" stroke="#6B7280" stroke-width="1.6" stroke-dasharray="6 4"/><text x="530.0" y="404.6" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#111827">12. Production readiness approvals +</text><text x="530.0" y="420.2" font-family="Arial, Helvetica, sans-serif" font-size="12.5" font-weight="normal" text-anchor="middle" fill="#111827">switch authorisation</text><line x1="180.0" y1="66.0" x2="180.0" y2="84.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="180.0" y1="140.0" x2="180.0" y2="158.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="180.0" y1="214.0" x2="180.0" y2="232.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="180.0" y1="288.0" x2="180.0" y2="306.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="180.0" y1="362.0" x2="180.0" y2="380.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="530.0" y1="66.0" x2="530.0" y2="84.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="530.0" y1="140.0" x2="530.0" y2="158.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="530.0" y1="214.0" x2="530.0" y2="232.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="530.0" y1="288.0" x2="530.0" y2="306.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><line x1="530.0" y1="362.0" x2="530.0" y2="380.0" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/><path d="M340,408.0 L355.0,408.0 L355.0,38.0 L370,38.0" fill="none" stroke="#374151" stroke-width="1.5" marker-end="url(#a12)"/></svg><figcaption>Figure 12: Vendor validation roadmap</figcaption></figure>

Idhu dependency order. Munnaadi step mudiyaama adutha step-ku pona, guess panni build panna vendi varum — adhai naanga panna maattom.

**Step 1 — PO vendor confirm pannanum (HF-03).** Endha PMS vendor, product, version, hosting (on-premise / cloud), ovvoru property-kum. Idhu illaama vendor-ku request anuppave mudiyaadhu. *Prerequisite:* onnum illa — request draft ready (`docs/HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md`, draft 0).

**Step 2 — Vendor technical contact.** Vendor pakkam technical-ah pesa oru aal (role pothum). Ippo VENDOR-owned 10 items-ku pesa yaarum illa. *Prerequisite:* Step 1.

**Step 3 — Official documents vaanganum.** Vendor request package Part A (ellarukkum), Part B (FIAS: manual, records, framing, ACK, heartbeat…), Part C (HTNG: profile, WSDL/XSD, security…). Protocol choice (HF-04) inga confirm aagum. *Prerequisite:* Step 2.

**Step 4 — Sandbox + test credentials.** Vendor test environment, test property, credentials. Credentials email-la anuppa koodadhu — HF-22 channel decide aaganum. *Prerequisite:* Step 3 + HF-22.

**Step 5 — Approvals (parallel-ah).** Business (HF-01, 02, 05, 18, 19 …), security (HF-21–24), DBA (HF-39 + BLK-D6), infrastructure (HF-25/26). HF-39, HF-21 maadhiri sila decisions vendor-ku wait pannaama ippave start pannalaam. *Prerequisite:* owners named.

**Step 6 — Protocol contracts confirm.** Official documents-la irundhu FIAS `FiasSpecification` / HTNG `SchemaProfile` ezhudhi `VERIFIED_OFFICIAL`-ah mark pannradhu; vendor samples vechu contract tests. *Prerequisite:* Step 3; XSD library (HF-39) for HTNG.

**Step 7 — Isolated vendor test connectivity.** VPN/IP allow-list, TLS, endha side listen pannum (HF-24, HF-06); integration service-ah non-production-la host pannradhu (HF-25). *Prerequisite:* Steps 4–6.

**Step 8 — Real message exchange.** Vendor test environment kooda inbound/outbound, ACK/fault, duplicates, reconnect ellam try pannradhu. *Prerequisite:* Step 7.

**Step 9 — Fix + regression.** Kandupidicha issues fix panni, ella existing suites-um (backend, certification, frontend, E2E) thirumba run pannradhu. *Prerequisite:* Step 8.

**Step 10 — Vendor validation.** Test plan V-21 (interoperability), V-22 (acceptance) execute (`docs/HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md`). *Prerequisite:* Step 9.

**Step 11 — Formal acceptance evidence.** Vendor sign-off, reports file pannradhu. *Prerequisite:* Step 10.

**Step 12 — Production readiness approvals.** DBA migration apply, deployment & rollback plan approve, monitoring owner, live-write gate decisions code-la record (reviewed commit), production switches-ku explicit authorisation. Appo dhaan status maarum. *Prerequisite:* ellame.

# Chapter 17 – Glossary and Learning Reference

| Term | Tanglish explanation |
|---|---|
| Adapter | Protocol-specific translator — vendor format-ah namma canonical format-ku maathum |
| BLOCKED (adapter) | Verified spec illaama ella operation-um refuse pannura safe state |
| Canonical envelope | Ella protocol-kum common message shape (`CanonicalEnvelope`) |
| Correlation ID | Oru message-ah ella logs/systems-la trace panna kudukkura id |
| DLQ | Repeated-ah fail aana messages separate-ah vechu operator investigate panra mechanism |
| Fencing token | Old worker late-ah commit panna mudiyaama tadukkura lease token |
| Framing | TCP byte stream-la message boundaries kandupidikkiradhu |
| Idempotency | Same message rendu thadava vandhaalum oru thadava dhaan apply |
| Lease | Worker-oda temporary ownership of a message |
| LiveWriteGate | HMS data maathura munnaadi env flag + approvals check pannura gate |
| Outbox | Outbound messages-ah first DB-la queue panni appuram anuppura pattern |
| Profile (HTNG) | Vendor HTNG-la endha subset implement pannirukkaanga-nu define pannradhu |
| Redrive | DLQ message-ah audit-oda thirumba processing-ku anuppradhu |
| Scope smuggling | Message body-la vera facility-ah refer panni isolation-ah bypass panna try pannradhu |
| SKIP LOCKED | Lock aana rows-ah skip panni rendu workers clash aagaama irukka MySQL feature |
| Synthetic test | Namma create panna fake (but realistic) data vechu test — vendor certification illa |
| VERIFIED_OFFICIAL | Official vendor document-la irundhu verify aana spec status |
| HF-01 | PMS/HMS system of record |
| HF-02 | Facility/entity mapping ownership |
| HF-03 | PMS vendor/product/version/hosting |
| HF-04 | Protocol selection per deployment |
| HF-05 | FIAS property-code case sensitivity |
| HF-06 | FIAS connection/framing/ACK/heartbeat/resync rules |
| HF-07 | HTNG version/profile/schema |
| HF-08 | HTNG security profile |
| HF-09 | Vendor test environment & certification |
| HF-11 | FIAS official specification & samples |
| HF-14 | Room device actions ownership |
| HF-15 | Lock vendor & key types |
| HF-18 | Integration principal / HMS actor |
| HF-19 | Facility isolation rules & pilot scope |
| HF-20 | Guest PII scope |
| HF-21 | Payload retention & encryption |
| HF-22 | Credential storage |
| HF-23 | Audit retention |
| HF-24 | Network path & TLS |
| HF-25 / HF-26 | Hosting / restart policy |
| HF-27 | Retry & ordering policy |
| HF-30 | Property timezone |
| HF-31 | Vendor-to-HMS code mappings |
| HF-37 | Room-status vocabulary |
| HF-38 | Reservation data scope |
| HF-39 | DBA/schema authorization |
| HF-40 | Folio & billing ownership |
| BLK-V7 | Vendor message volumes (prerequisite, HF illa) |
| BLK-D6 | Invalid direction/protocol constraint item (HF-39 kulla, proposed) |

# Chapter 18 – Final Project Status

<div class="status-box">FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING</div>

**Engineering complete pannadhu:** shared integration foundation (auth, facility isolation, idempotency, leases, retry, DLQ, audited redrive, per-stay ordering, transactional audit), HTNG & FIAS generic frameworks, background service, operator & observability APIs, 5-page dashboard, certification harness — synthetic & disposable environments-la layered testing (517-test backend suite, 45 certification scenarios, 49 frontend tests, browser visual QA, full-stack E2E 90 + 56 checks).

**Vendor validation complete aagala:** vendor-e identify aagala (HF-03); official FIAS/HTNG documents, samples, test environment illa; oru real vendor message kooda exchange aagala; official scenarios 5-um BLOCKED.

**Production readiness-ku venum:** vendor validation evidence + acceptance; business approvals (HF-01, 02, 05, 18, 19 …); DBA approval & migration (HF-39 incl. BLK-D6); security/infra decisions (HF-21–26); monitoring owner; deployment & rollback approval; explicit production switch authorisation.

**Next single action:** Product Owner HF-03-ku answer pannanum (communications doc draft 0).
