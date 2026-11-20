# HTNG / FIAS — External Blocker Action Register (2026-11-20)

Project status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. **No decision is
approved.** This register makes every pending item actionable. It does **not** change any
status.

| Source of truth | Used for |
|---|---|
| `HTNG_FIAS_DECISION_REGISTER.md` (canonical) | IDs, decision text, status, owner roles |
| `HTNG_FIAS_BLOCKER_REGISTER.md` | BLK-* evidence and resolution criteria |
| `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | business questions and documented options |
| `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | vendor items A1–A8, B1–B12, C1–C10 |
| `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` (incl. new §11) | HF-39 |
| `HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` | defect evidence |

**Role codes** (no individuals are named in any project document): PO product owner, ARCH
architecture, BA business analyst, SEC security, OPS operations, DBA, BE backend, QA, LEGAL,
HOTEL-OPS hotel operations, VENDOR PMS/interface vendor, PROJECT LEAD. The canonical register
also uses **PLAT, LOCK-VENDOR and FIN**, which are not defined in any project glossary (§4).

**Source of the "Status" column:** the canonical register, quoted verbatim. Where another
document states a different status, both are shown and the difference is flagged (§5). Rows
marked † were imported from the legacy register; their meaning and owner roles are *pending
project-owner confirmation of provenance* (canonical register §1).

## 1. Register

### 1.1 Vendor

| ID | Category | Current status | Responsible role | Exact decision required | Evidence required | Dependency | Implementation impact | Recommended next action | Closure evidence |
|---|---|---|---|---|---|---|---|---|---|
| HF-04 † | Vendor (joint PO) | Awaiting Vendor Confirmation | PO, VENDOR | Which protocol(s) per deployment: FIAS, HTNG, vendor REST or a combination? | Vendor protocol statement (A2) confirmed by PO | HF-03 | Which adapter is completed; whether a SOAP stack and XSD library (HF-39) are needed | Ask in vendor request A2 once HF-03 names the vendor | A2 answer filed in the vendor package Part E; PO confirmation |
| HF-05 | Vendor (+HOTEL-OPS) | Awaiting Vendor Confirmation (blocker register lists it under Business, BLK-B3) | VENDOR, HOTEL-OPS | Are property codes case-sensitive? If not, which canonical case is stored? | Vendor document (A3) confirmed by HOTEL-OPS | HF-03 | Mapping normalisation; EXACT matching in force; one of the 4 live-write gate decisions | Vendor request A3 | `approvals.py` HF-05 Approved with evidence (reviewed commit); `CaseSensitivity` configured |
| HF-06 † | Vendor | Awaiting Vendor Confirmation | VENDOR, OPS | FIAS link rules: physical link, listening side, host/port, framing, encoding, sequence/ACK, heartbeat, reconnect, resync | Vendor link document (B3–B7) | HF-03, HF-04 (FIAS chosen); BLK-F1 | Production framer, ACK responder, heartbeat and link role; firewall rules | Vendor request B3–B7 | Sections cited in `spec.py`; framer/responder implemented; contract tests pass (BLK-F3–F6) |
| HF-07 | Vendor | Awaiting Vendor Confirmation | VENDOR | HTNG version, implementation profile and schema scope | WSDL/XSD bundle and profile statement (C1, C2) | HF-03, HF-04 (HTNG chosen) | Every HTNG operation; adapter BLOCKED | Vendor request C1–C4, C6–C9 | Verified `SchemaProfile` registered; contract report passes (BLK-H1, H4) |
| HF-08 | Vendor (+SEC) | Awaiting Vendor Confirmation | VENDOR, SEC | HTNG message security: WS-Security token type, signing/encryption, timestamps/nonce, mTLS | Security specification (C5) and SEC review | HF-07 | HTNG endpoint cannot be exposed | Vendor request C5, then SEC review | Implemented with security tests (BLK-H2); **HF-08 also has to be added to the code register `approvals.py`** (§5) |
| HF-09 † | Vendor (+QA) | Awaiting Vendor Confirmation | VENDOR, QA | Test environment, simulator, test credentials and certification process | Environment access, process document (A6, A7) | HF-03; HF-22 (credential channel); HF-24 (network) | Vendor validation and certification (BLK-V4–V6) | Vendor request A6/A7 | V-21 and V-22 executed and signed (vendor validation test plan) |
| HF-11 | Vendor | Awaiting Vendor Confirmation | VENDOR | FIAS official specification: manual and version, licensed record set, record/field definitions, official samples | Manual and record set (B1, B2, B8–B11) | HF-03, HF-04 (FIAS chosen) | Every FIAS record; adapter BLOCKED | Vendor request B1, B2, B8–B11 | `PRODUCTION_SPECIFICATION` marked `VERIFIED_OFFICIAL`; contract report passes (BLK-F1, F2, F7) |
| HF-15 † | Vendor (lock) | Awaiting Vendor Confirmation | LOCK-VENDOR, PLAT | Lock vendor, encoding method, key types, lock-activity sync | Lock-vendor documentation | HF-14 | Key-issuance service; key-secret storage | Confirm whether the pilot needs it (HF-14) before requesting | Lock documentation filed and accepted |
| BLK-V7 | Vendor (not an HF decision) | PENDING VENDOR DOCUMENTATION (blocker register) | VENDOR, OPS | Peak and average message volume per property and protocol | Volume figures (vendor request A2/A4) | HF-03 | `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE` stays unset; load test not sized | Ask with A2/A4 | Volumes received; limit value configured |

### 1.2 Business

| ID | Category | Current status | Responsible role | Exact decision required | Evidence required | Dependency | Implementation impact | Recommended next action | Closure evidence |
|---|---|---|---|---|---|---|---|---|---|
| HF-01 | Business | Awaiting Business Approval | PO, ARCH | Per entity (reservation, guest, check-in/out, room status) and per property: is the PMS or the HMS the system of record? | Signed per-entity table | — (informed by vendor A5) | Live domain writes; message direction per entity | Decision meeting with the documented options (A / B / C) | Signed table; `approvals.py` HF-01 Approved with evidence |
| HF-02 | Business | Awaiting Business Approval | PO, BA, ARCH | Who owns PMS-property→HMS-facility mappings? Is `stay.external_stay_ref_number` the PMS reservation number, unique per facility? | Ownership statement; field confirmation | HF-01 | Production stay resolver; mapping onboarding; live writes | Decision meeting | Statement filed; `approvals.py` HF-02 Approved with evidence |
| HF-03 † | Business (vendor selection) | **Open** | PO | Which PMS vendor, product, version and hosting for the pilot, per property? | Named product per property | — | **Gates every vendor request (HF-04 … HF-09)** | PO names the vendor/product (BLK-V1) | Named product recorded; vendor request sent (Part E "sent" field filled) |
| HF-14 † | Business / architecture | Open | ARCH, PLAT, PO | Who executes room-level device actions (keys, HVAC, DND)? Is an OSS command path built? | Ownership decision | — | Phase 4 scope; whether the outbox emits device intents | Confirm whether Phase 4 is in pilot scope | Decision recorded |
| HF-18 | Business (security-owned) | **Open** (blocker/business registers: PENDING BUSINESS APPROVAL) | SEC, ARCH | Which HMS user or service account is recorded for PMS-originated writes? | SEC approval naming the account and its permissions | HF-01 | `INTEGRATION_ACTOR_USER_ID` unset, so live writes are impossible | SEC selects among the documented options | Account approved; value configured |
| HF-19 | Business | Awaiting Business Approval | SEC, PO | Is every client bound to a fixed set of properties? Is the pilot single- or multi-property? | SEC/PO sign-off and pilot property list | HF-03 (property list) | Activation; one of the 4 live-write gate decisions (behaviour already enforced in code) | Sign-off meeting | `approvals.py` HF-19 Approved with evidence; pilot list filed |
| HF-20 † | Business (legal) | Awaiting Business Approval | LEGAL, PO, SEC | Guest PII scope; phone/email requirements; consent | Policy | — | Guest canonical model; possible schema change | LEGAL policy | Policy filed |
| HF-21 | Business (security/legal) | **Open** (business register: PENDING BUSINESS APPROVAL) | LEGAL, SEC | Processed-message retention in days (= duplicate-protection window); encryption at rest; who may view payloads; may vendor samples containing guest data be stored? | LEGAL/SEC policy with values | — | No purge; raw wire bytes off; payloads unencrypted in the candidate table; guest-data samples refused by replay | LEGAL/SEC set the values | `INTEGRATION_RETENTION_DAYS` configured; encryption decision implemented if required |
| HF-27 | Business (technical) | **Open** (business register: PENDING BUSINESS APPROVAL) | ARCH, BE | Per message type: retry count and back-off; should a dead letter block later events for the same stay? | ARCH/BE policy informed by vendor re-delivery rules (B4/C6) | HF-06 or HF-07 (vendor re-delivery rules) | Defaults in force (5 attempts, 5 s → 900 s, per-stay ordering, dead letter blocks) | Decide after vendor B4/C6 answers | Configuration approved |
| HF-30 † | Business | Awaiting Business Approval | PO, HOTEL-OPS | Source and value of each property's timezone | Timezone source per property | HF-03, HF-19 (property list); vendor B8 | Date/time mapping (no timezone column on `facility`) | HOTEL-OPS supplies values | Values recorded; dependency column **not recorded** in the legacy row |
| HF-31 † | Business | Awaiting Business Approval | HOTEL-OPS, BA, VENDOR | Vendor code ↔ HMS code mappings (hotel code ↔ `facility_uid`, room types, room/reservation/work-order status) | Mapping tables | HF-03, HF-04 (vendor vocabularies) | Mapping tables and vocabularies | After the vendor supplies its code lists | Mapping tables filed |
| HF-37 † | Business | Open | HOTEL-OPS, BA | Room-status vocabulary extension (inspected, out-of-order, out-of-service) | Vocabulary decision | HF-31 | Possible schema/seed change | HOTEL-OPS decision | Decision recorded |
| HF-38 † | Business | Open | PO, FIN | Reservation data scope in HMS (rates, amounts, guarantee, no-show, confirmation numbers) | Scope decision | HF-01 | Canonical model; possible schema change. **The register states it is deferrable for a FIAS guest-event-first pilot** | Confirm deferral for the pilot | Scope recorded |
| HF-40 † | Business | Awaiting Business Approval | FIN, PO | Folio and billing ownership | Choice among the legacy options E1 · E2 · E3 | HF-01 | Posting direction; folio model scope | FIN/PO decision (option texts are in the legacy register only, §4) | Decision recorded |

### 1.3 DBA

| ID | Category | Current status | Responsible role | Exact decision required | Evidence required | Dependency | Implementation impact | Recommended next action | Closure evidence |
|---|---|---|---|---|---|---|---|---|---|
| HF-39 | DBA | Awaiting DBA Approval | ARCH, DBA, PO | Approve the 7 integration tables (BLK-D1); choose the `down_revision` for the two Alembic heads (D2); confirm the live DB revision/DDL (D3); fix plan for 19 MySQL incompatibilities (D4); backup/window/rollback (D5); XSD library if HTNG (BLK-H3) | DBA package §10 decision record signed | none for the table approval; the XSD library depends on HF-04 | No persistence in the HMS DB; tables exist only in disposable DBs | DBA review of the package §1–§11 | §10 completed and signed; `approvals.py` HF-39 updated by a reviewed commit |
| BLK-D6 (proposed, under HF-39) | DBA / schema integrity | New — PENDING DBA APPROVAL (§11 of the DBA package) | DBA, ARCH, BE | Allowed `direction` values (Option A `inbound`/`outbound` or Option B `inbound`) and `protocol` values; tolerant application mapping | E2E finding 1; code references in DBA package §11 | HF-39 | One invalid row returns 500 on message search and DLQ, and is still counted in the overview; possible worker stall (from code reading, not reproduced) | DBA/ARCH answer Q8; BE plans the defensive fix | CHECK added to the model and DDL; regression tests; validation queries clean |

### 1.4 Infrastructure

| ID | Category | Current status | Responsible role | Exact decision required | Evidence required | Dependency | Implementation impact | Recommended next action | Closure evidence |
|---|---|---|---|---|---|---|---|---|---|
| HF-24 | Infrastructure (+SEC, VENDOR) | Awaiting Vendor Confirmation | OPS, SEC, VENDOR | Vendor network path (VPN, IP ranges, listener exposure) and TLS termination | Network design | HF-03; vendor B12/C10; HF-06 (listening side) | Connectivity blocked | OPS/SEC draft the internal side; request B12/C10 | Network design approved; firewall rules recorded |
| HF-25 | Infrastructure | Open | ARCH, OPS | Where the integration service process (workers, outbox relay, FIAS link) runs and how it is supervised (e.g. PM2 or systemd, both named in the docs) | Hosting decision | HF-06 (which side listens affects placement) | No supervised process is wired | OPS/ARCH decision | Hosting documented; service deployed in a non-production environment |
| HF-26 | Infrastructure | Open (one row with HF-25 in the canonical register) | ARCH, OPS | Restart policy, and the single-owner rule for a FIAS link | Restart and operational policy | HF-25 | Restart behaviour undefined | OPS/ARCH decision | Policy documented and tested (kill/restart drill) |

### 1.5 Security

| ID | Category | Current status | Responsible role | Exact decision required | Evidence required | Dependency | Implementation impact | Recommended next action | Closure evidence |
|---|---|---|---|---|---|---|---|---|---|
| HF-22 | Security | Open | SEC, OPS | Where client secrets are stored and through which channel they are delivered to the vendor | Storage decision | — | Real client secrets cannot be issued; blocks vendor test credentials (BLK-V4) | SEC/OPS decision | Channel documented; first secret delivered through it |
| HF-23 | Security (+LEGAL) | Open | SEC, LEGAL | Audit-log retention period and immutability | Retention value | — | The audit table is append-only by convention only | SEC/LEGAL decision | Value recorded; enforcement decided |

## 2. Priority classification (proposed by this audit; for the owners to confirm)

| Priority | Items | Reason |
|---|---|---|
| **P0 — root of the critical path** | HF-03, HF-04, HF-39 | Nothing reaches a vendor until HF-03 and HF-04 are answered; nothing persists in the HMS DB without HF-39 |
| **P1 — needed for vendor validation** | HF-11 + HF-06 (FIAS) or HF-07 + HF-08 (HTNG), HF-05, HF-09, HF-22, HF-24, HF-21 (sample handling), BLK-D6 | Protocol material, credentials channel, network, and safe handling of vendor samples |
| **P1 — needed for any live HMS write** | HF-01, HF-02, HF-05, HF-19 (the code gate) and HF-18 (actor) | `LiveWriteGate` and settings validation |
| **P2 — needed for production operation** | HF-25, HF-26, HF-23, HF-27, HF-30, HF-31, BLK-V7, HF-20 | Operability, retention, policy, mappings |
| **P3 — deferrable per the register / pilot scope** | HF-14, HF-15, HF-37, HF-38, HF-40 | Phase-4 or billing scope; HF-38 is explicitly "deferrable for a FIAS guest-event-first pilot" |

## 3. Critical dependency chain

```text
HF-03 vendor/product named (PO)
  └─► vendor request sent (BLK-V1/V2) ─► HF-04 protocol chosen
        ├─ FIAS ─► HF-11 spec + samples ─► HF-06 link rules ─► HF-27 final retry policy
        └─ HTNG ─► HF-07 profile/XSD ─► HF-08 security ─► HF-39 XSD library ─► HF-27
        ├─► HF-05 case rule (A3) · HF-31 code mappings · BLK-V7 volumes · HF-30 (B8)
        └─► HF-24 network/TLS ─┐
HF-22 credential channel ──────┴─► HF-09 test environment + credentials ─► vendor validation
                                                                            (BLK-V5/V6)
HF-39 DBA approval (+ BLK-D6) ─► migration in target DB ─► persistence: ok
HF-01 ─► HF-02 ─┐
HF-19 ──────────┼─► LiveWriteGate (HF-01, 02, 05, 19) + HF-18 actor ─► live HMS writes
HF-05 ──────────┘
HF-25 ─► HF-26 ─► supervised service
Production readiness = vendor validation + all of the above + explicit authorisation
```

| Grouping | Items |
|---|---|
| **Can be closed independently now** (no unresolved upstream decision) | HF-03 · HF-39 (tables, heads, live revision, backup: everything except the XSD library) · BLK-D6 value choice · HF-01 · HF-21 · HF-22 · HF-23 · HF-18 (account naming) · HF-25 (hosting pattern) · HF-14 / HF-38 deferral confirmations |
| **Require joint approval** (several roles in the canonical register) | HF-01 (PO+ARCH) · HF-02 (PO+BA+ARCH) · HF-04 (PO+VENDOR) · HF-05 (VENDOR+HOTEL-OPS) · HF-08 (VENDOR+SEC) · HF-09 (VENDOR+QA) · HF-14 (ARCH+PLAT+PO) · HF-18 (SEC+ARCH) · HF-19 (SEC+PO) · HF-20 (LEGAL+PO+SEC) · HF-21 (LEGAL+SEC) · HF-22 (SEC+OPS) · HF-23 (SEC+LEGAL) · HF-24 (OPS+SEC+VENDOR) · HF-25/26 (ARCH+OPS) · HF-27 (ARCH+BE) · HF-31 (HOTEL-OPS+BA+VENDOR) · HF-39 (ARCH+DBA+PO) · HF-40 (FIN+PO) |
| **Must remain blocked** (closable only with vendor material) | HF-04, HF-05 (vendor statement), HF-06, HF-07, HF-08 (vendor part), HF-09, HF-11, HF-15, HF-24 (vendor part), BLK-V7, and therefore vendor validation and certification; live writes until the gate decisions are Approved with evidence |

## 4. Ownership gaps and missing information

| Gap | Detail |
|---|---|
| No individual owner anywhere | All owners are roles. A named person per role is **unassigned** for every row |
| Owner roles pending provenance confirmation | 12 legacy-imported rows: HF-03, 04, 06, 09, 14, 15, 20, 30, 31, 37, 38, 40 |
| Roles not defined in the stakeholder glossary | PLAT (HF-14, HF-15), LOCK-VENDOR (HF-15), FIN (HF-38, HF-40) |
| VENDOR has no counterpart | Until HF-03 names the vendor, every VENDOR-owned item has nobody to answer it |
| Monitoring ownership | Production readiness category 8 names "monitoring ownership" as a blocker; **no role is recorded** |
| Repository-owner items | git identity for committing; decision on `docs/HTNG-FIAS/` and `docker-compose.dev.yml` (blocker register "Other open items") |
| Missing documents | No dedicated infrastructure/deployment design (only `OPERATIONS_RUNBOOK.md` §8 and readiness category 8). The legacy register lives only in the sibling copy and its provenance is unconfirmed; HF-40 options E1–E3 and the HF-30 dependency are recorded only there |

## 5. Inconsistencies found (preserved, not corrected; owners please clarify)

| # | Inconsistency | Documents |
|---|---|---|
| 1 | HF-18, HF-21 and HF-27 are **Open** in the canonical register but "PENDING BUSINESS APPROVAL" in the blocker and business registers | canonical vs `BLOCKER_REGISTER`, `BUSINESS_DECISION_REGISTER` |
| 2 | HF-05 has vendor status (canonical) but sits in the business section (BLK-B3); the "seven business decisions" include it | same |
| 3 | HF-08 is required for HTNG vendor validation but is **absent from the code register** in `domain/approvals.py`; the observability API therefore always reports it pending | `approvals.py`, `observability.py` |
| 4 | Vendor samples: vendor package Part F places them in `backend/tests/integrations/vendor_contracts/<vendor>/`; the certification runbook says outside the repository unless HF-21 approves | `VENDOR_REQUEST_PACKAGE.md` Part F vs `CERTIFICATION_RUNBOOK.md` |
| 5 | Production readiness quotes round-3 test counts (406 collected); the latest are 517 / 516 / 1 | historical snapshot |
| 6 | HF-25 and HF-26 share one row and status in the canonical register | kept as one row there; split here for actionability only |

## 6. Owner action packages

### A. Vendor team (sent by PROJECT LEAD after HF-03)

* **Documents:** the vendor request package, Parts A–C. Part A is required for everyone (A1–A5
  before development, A6–A8 before certification); Part B applies to FIAS (B1–B11 before
  development, B12 before certification); Part C applies to HTNG (C1–C9, C10 before
  certification).
* **FIAS decisions:**
  * HF-11 — B1, B2, B8–B11.
  * HF-06 — B3 framing, B4 ACK/NAK, B5 start-up/resync, B6 heartbeat, B7 direction and
    host/port.
  * HF-05 — A3.
* **HTNG decisions:** HF-07 (C1–C4, C7, C9) and HF-08 (C5).
* **Samples (both directions, including acknowledgements and errors):** B10 / C8, with a
  `manifest.json` (vendor, product, protocol, protocol_version, source, received_on,
  pii_status). `contains-guest-data` samples are refused until HF-21 is approved.
* **Security and connectivity:** B12 / C10 / HF-24 (VPN, IP ranges, TLS); HF-08 for HTNG.
* **Test environment and certification:** A6 (environment, test property, credentials process,
  with credentials delivered via the HF-22 channel) and A7 (acceptance criteria). Volumes
  (BLK-V7) come with A2/A4.
* **Response format:** one row per item in Part E: received date, document title / version /
  section, reviewer, accepted (Y/N), follow-up. "Not applicable" must be stated explicitly.
  Synthetic material never counts.

### B. DBA team

* HF-39 package §1–§10 (7 tables, Appendix A).
* BLK-D2 `down_revision` for heads `a3f1c8e2d904` / `b3c4d5e6f7a8`.
* BLK-D3 live revision and DDL.
* BLK-D4 the 19 incompatibilities.
* BLK-D5 backup, window and executor.
* BLK-H3 XSD library, if HTNG.
* **New §11 / BLK-D6:** `direction` and `protocol` CHECK values, the validation queries, the
  remediation procedure, and the defensive-mapping requirement.
* Close by completing the §10 decision record and answering Q1–Q8.

### C. Business owners

The seven decisions listed in `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md`: HF-01, HF-02, HF-05,
HF-18, HF-19, HF-21 and HF-27. Each has its question, impact, documented options and evidence
there. Also requested:

* **HF-03** (PO): the root of the vendor path.
* **Confirm or defer:** HF-14, HF-20, HF-30, HF-31, HF-37, HF-38, HF-40.

Options are only those already documented. **Explicit owner confirmation** is required for
each item, recorded with an evidence reference.

### D. Infrastructure and security teams

| Area | Decisions |
|---|---|
| Hosting, restart and network | HF-25 hosting and supervision (PM2 or systemd); HF-26 restart and single-link-owner policy; HF-24 network path and TLS; monitoring and alert-routing ownership (no owner recorded) |
| TLS and credentials | HF-22 secret storage and delivery channel; HF-08 HTNG message security (with the vendor). The backend already requires TLS to MySQL (`MYSQL_SSL_CA`, verify on by default): confirm the CA distribution for the target database |
| Payload and audit | HF-21 retention days, encryption at rest, payload access, vendor-sample PII; HF-23 audit retention and immutability; HF-20 guest PII scope (with LEGAL) |
| Recovery | Owners for the runbook procedures: DLQ redrive (write grant), credential rotation, link troubleshooting, retention purge |

## 7. Reconciliation status of §5 (updated 2026-11-20)

| §5 # | Resolution |
|---|---|
| 1, 2 | Recorded: canonical status governs (`HTNG_FIAS_BLOCKER_REGISTER.md`, reconciliation section). No status changed |
| 3 | HF-08 code-register gap analysed; correction **proposed, not implemented** (`HTNG_FIAS_MASTER_PROJECT_COMPLETION_PLAN.md` §4) |
| 4 | **Resolved:** the stricter rule (outside the repository until HF-21) applied in vendor package Part F |
| 5 | **Resolved:** dated evidence update appended to `HTNG_FIAS_PRODUCTION_READINESS.md` |
| 6 | Unchanged (canonical row kept; split only in this register) |
| Missing infrastructure design | **Draft created:** `HTNG_FIAS_INFRASTRUCTURE_SECURITY_READINESS.md` (decides nothing) |
| HF-40 options / HF-30 dependency | Still only in the other working copy (read-only, not copied); requested from PO/FIN (`HTNG_FIAS_OWNER_DECISION_TRACKER.md` §3) |
