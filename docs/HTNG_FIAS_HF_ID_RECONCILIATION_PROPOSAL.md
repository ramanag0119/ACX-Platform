# HTNG / FIAS — HF Decision ID Reconciliation Proposal

| | |
|---|---|
| Date | 2026-11-20 |
| Branch | `feature/htng-fias-on-develop` (uncommitted working tree) |
| Status | **APPLIED 2026-11-20** by repository-owner decision: canonical register = this repository's; **Option A**; HF-40 = folio/billing; 11 IDs imported; `docs/HTNG-FIAS/` kept with errata README; no HF ID for vendor volumes (BLK-V7); sibling register not copied. Sections below are the proposal as approved; Appendix A is the pre-change snapshot. |
| Audience | repository owner / project lead; decision owners for awareness |

## 1. Executive summary

* **27 unique HF IDs** are referenced in this repository (324 reference lines in 67 files:
  documents, code comments, code constants and test assertions). HF-15 appears only in the
  shorthand `HF-14/15`; `HF-22…HF-27` is a range.
* Two numbering sources exist:
  1. **This repository's register** — `docs/HTNG_FIAS_DECISION_REGISTER.md` and its code mirror
     `backend/app/integrations/domain/approvals.py`. Its meanings for HF-01/02/05/07/11/19/21/39 come
     from the implementation brief of 2026-11-19 (quoted in that register's §1).
  2. **The earlier register** — `../HMS-Frontend/ACX-Platform/docs/HTNG_FIAS_BUSINESS_VENDOR_DECISION_REGISTER.md`
     (2026-11-17, **outside this repository, untracked**), defining HF-01 … HF-39.
* **4 conflicting IDs:** HF-05 and HF-11 (this repository vs earlier register); HF-07 and HF-18
  (earlier implementation's phase reports in `docs/HTNG-FIAS/` vs every register).
* **11 IDs are referenced but not defined in this repository's register** (HF-03, 04, 06, 09,
  14, 15, 20, 30, 31, 37, 38 — 27 references), and **3 references misattribute HF-24**.
* **One silent merge already happened (round 1):** this repository's HF-11 ("FIAS official
  protocol and operational rules") covers what the earlier register split into HF-05 (spec
  and record set) and HF-06 (connection/link rules). This proposal makes that explicit and asks
  the owner to choose between restoring the split and confirming the merge.
* **Recommendation:** keep this repository's IDs as canonical (code and tests depend on them),
  import the missing earlier IDs verbatim, give the displaced earlier meaning of HF-11 (folio
  and billing ownership) a new ID **HF-40**, and record legacy IDs in a cross-reference column.

## 2. HF ID inventory

"Repo" = this repository's register / code mirror. "Earlier" = earlier register (external).
"Phase docs" = `docs/HTNG-FIAS/` reports of the earlier implementation. Owners are roles only.

| ID | Repo meaning | Earlier register meaning | Phase docs usage | Owner (role) | Required decision / evidence | Dependent work | Refs | Finding |
|---|---|---|---|---|---|---|---|---|
| HF-01 | PMS / HMS system of record | Operating model: HMS as PMS host / subsystem / both | Authority of record (consistent) | PO, ARCH | signed per-entity table | live-write gate (`approvals.py`) | 31 | consistent |
| HF-02 | Facility / entity mapping ownership | Entity ownership per entity | — | PO, BA, ARCH | ownership statement | live-write gate; stay resolver | 28 | consistent (repo = subset) |
| HF-03 | (not defined) | Target PMS / vendor, product, version | — | PO | named product | vendor request | 3 | **missing in repo register** |
| HF-04 | (not defined) | Protocol selection per deployment | — | PO, VENDOR | FIAS / HTNG / REST choice | which adapter is built | 2 | **missing** |
| HF-05 | FIAS external property-code **case sensitivity** | FIAS **spec version and licensed record set** | — | Repo: VENDOR, HOTEL-OPS · Earlier: VENDOR | Repo: vendor A3 · Earlier: manual | Repo: live-write gate, mapping collation | 32 | **CONFLICT** |
| HF-06 | (not defined; cited in code comments and docs as link rules) | FIAS connection details: TCP/RS-232, listening side, framing, encoding, sequence/ACK, heartbeat, reconnect, resync | — | VENDOR, OPS | vendor link document | TCP role, framing, ACK, heartbeat | 8 | **missing**; overlaps repo HF-11 |
| HF-07 | HTNG version / profile / schema scope | HTNG specification (release, style, WSDL/XSD, SOAP version, endpoints) | Phase 5: HTNG profile (consistent) · **Phase 6/7: "idempotency key TTL / retention window"** | VENDOR | WSDL/XSD + profile | HTNG adapter `BLOCKING_DECISION` | 44 | **CONFLICT (phase docs only)** |
| HF-08 | HTNG security profile | HTNG security: WS-Security, TLS/mTLS, endpoint side | — | VENDOR, SEC | security spec | HTNG exposure | 20 | consistent |
| HF-09 | (not defined) | Vendor test environment, simulator, credentials, certification | — | VENDOR, QA | environment access | vendor validation | 2 | **missing** |
| HF-11 | **FIAS official protocol and operational rules** | **Folio and billing ownership** | Phase 5: "FIAS Vendor Specification Manual" (agrees with repo, contradicts its own register) | Repo: VENDOR · Earlier: FIN, PO | Repo: FIAS manual · Earlier: E1/E2/E3 | FIAS adapter `BLOCKING_DECISION`, tests | 55 | **CONFLICT** (+ silent merge of earlier HF-05/06) |
| HF-14 | (not defined) | Who executes room-level device actions (keys, HVAC, DND) | — | ARCH, PLAT, PO | ownership | device intents | 1 | **missing** |
| HF-15 | (not defined) | Lock vendor, encoding method, key types, lock-activity sync | — | LOCK-VENDOR, PLAT | lock vendor docs | key issuance | 1 (shorthand) | **missing** |
| HF-18 | Integration principal / HMS actor for writes | Integration identity and authentication (actor stamping) | **Phase 5: "System of Record for Room Cleanliness States"** | SEC, ARCH | named account | `INTEGRATION_ACTOR_USER_ID` | 19 | **CONFLICT (phase docs only)** |
| HF-19 | Facility authorization / isolation | Property isolation + pilot scope | consistent | SEC, PO | sign-off + pilot list | live-write gate | 22 | consistent |
| HF-20 | (not defined) | Guest PII scope; phone/email requirements; consent | — | LEGAL, PO, SEC | policy | guest mapping | 1 | **missing** |
| HF-21 | Raw-payload retention / encryption | Integration-log retention and masking | — | LEGAL, SEC | values | retention purge, raw storage | 30 | consistent |
| HF-22 | Credential storage | Credential storage | — | SEC, OPS | storage decision | secret delivery | 15 | consistent |
| HF-23 | Audit-log retention / immutability | Audit-log retention and immutability | — | SEC, LEGAL | retention value | audit table | 8 | consistent |
| HF-24 | Vendor network access path and TLS | Vendor network access and network security | — | OPS, SEC, VENDOR | network design | connectivity | 18 | consistent, but **3 misattributed refs** (§3.3) |
| HF-25 | Worker / link hosting | Dedicated worker under PM2 / runtime hosting | — | ARCH, OPS | hosting choice | service supervision | 11 | consistent |
| HF-26 | Restart policy | Worker restart and failure handling | — | OPS | restart policy | supervision | 4 | consistent |
| HF-27 | Retry and ordering policy | Message retry policy (per type; ordering) | — | ARCH, BE | per-type policy | `RetryPolicy`, ordering switch | 15 | consistent |
| HF-30 | (not defined) | Property timezone | — | PO, HOTEL-OPS | timezone source | date mapping | 1 | **missing** |
| HF-31 | (not defined) | Vendor code ↔ HMS code mappings | — | HOTEL-OPS, BA, VENDOR | mapping tables | stay reference, vocabularies | 4 | **missing** |
| HF-37 | (not defined) | Room-status vocabulary extension | — | HOTEL-OPS, BA | vocabulary | room-status mapping | 3 | **missing** |
| HF-38 | (not defined) | Reservation data scope in HMS | — | PO, FIN | scope | reservation flows | 1 | **missing** |
| HF-39 | DBA / schema authorization (+ new dependencies) | Approval for Phase 1 schema migration and new dependencies | — | ARCH, DBA, PO | DBA decision record | migration, XSD library | 54 | consistent |

Reference counts are from a repository-wide search on 2026-11-20 (Appendix A lists every line).
The earlier register also defines HF-10, 12, 13, 16, 17, 28, 29, 32–36; none is referenced in
this repository.

## 3. Conflict matrix

### 3.1 Same ID, different decisions

| ID | Meaning A (where) | Meaning B (where) | Same decision? | Evidence |
|---|---|---|---|---|
| HF-05 | Property-code case sensitivity (repo register, `approvals.py`, `facility.py`, `sql_models.py`, `admin.py`, `test_domain.py`, 20 docs) | FIAS spec version + licensed record set (earlier register) | **No** | repo register §1; earlier register row HF-05 |
| HF-11 | FIAS official protocol/operational rules (repo register, `spec.py` `BLOCKING_DECISION`, adapters, transports, contracts, tests, docs; also Phase 5 report) | Folio and billing ownership (earlier register; repo `HTNG_FIAS_FACILITY_MAPPING.md` "HF-11 earlier numbering") | **No** | repo register §1; earlier register row HF-11 |
| HF-07 | HTNG version/profile/schema (all registers, code, tests) | Idempotency key TTL / retention window (`docs/HTNG-FIAS/…PHASE6…:419`, `…PHASE7…:239`) | **No** | phase docs lines cited |
| HF-18 | Integration principal / actor (repo register, earlier register) | System of record for room-cleanliness states (`docs/HTNG-FIAS/…PHASE5…:345`) | **No** | phase doc line cited |

### 3.2 One ID covering several earlier decisions (merge)

| Repo ID | Covers earlier | How it happened | Evidence of merge |
|---|---|---|---|
| HF-11 | earlier HF-05 (spec + record set) **and** earlier HF-06 (link: framing, ACK, heartbeat, listening side) | round-1 brief defined HF-11 as "FIAS official protocol/operational rules"; implementation then used it for both content and link rules | blocker rows BLK-F1…F7 all cite HF-11; BLK-F6 notes "earlier register HF-06"; `tcp.py:15`, `tcp_server.py:4` cite "HF-06 / HF-11" |

### 3.3 Misattributed references (wrong ID for the subject)

| Location | Text | Subject actually meant | HF-24 meaning |
|---|---|---|---|
| `backend/app/integrations/config.py` (`HTNG_RATE_LIMIT_PER_MINUTE` comment) | "vendor volumes unknown, HF-24" | expected vendor message volumes (vendor request A2/A4) | network path / TLS |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` R-23 | approval dep "HF-24", blocker "limit value" | same | same |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` R-13 | approval dep "HF-24", blocker "role decision" | TCP listening side (earlier HF-06 / repo HF-11); HF-24 is relevant only for the allow-list network path | partly correct |

### 3.4 Referenced but undefined in the repo register

HF-03, 04, 06, 09, 14, 15, 20, 30, 31, 37, 38 — used with their earlier-register meanings
(consistently), but only defined in a file outside this repository.

## 4. Proposed canonical mapping

Principle: **this repository's register becomes the single canonical register**; every
earlier ID is either kept (same meaning), imported (missing), or renumbered (collision) — and a
"Legacy ID" column records where each meaning came from. No two decisions share an ID, and no
decision's meaning is changed.

| Canonical ID | Canonical meaning | Legacy reference(s) | Action |
|---|---|---|---|
| HF-01, 02, 07, 08, 18, 19, 21, 22, 23, 24, 25, 26, 27, 39 | as in the repo register | earlier register same ID | **keep** |
| HF-05 | FIAS external property-code case sensitivity | (none in earlier register) | **keep** |
| HF-11 | FIAS official specification content: manual, version, licensed record set, record/field definitions, official samples | earlier **HF-05** (spec version + licensed record set) | keep ID; **narrow** to content if Option A below is chosen |
| HF-06 | FIAS connection / link rules: listening side, framing, encoding, sequence/ACK/NAK, heartbeat, reconnect, resync | earlier **HF-06** (same meaning) | **import** (Option A) — or record as absorbed into HF-11 (Option B) |
| **HF-40** (new) | Folio and billing ownership | earlier **HF-11** | **renumber** (collision); HF-40 is unused in both registers |
| HF-03, 04, 09, 14, 15, 20, 30, 31, 37, 38 | earlier-register meanings verbatim | earlier same ID | **import** with earlier status and owner roles |
| — | Phase-doc HF-07 "idempotency TTL" | `docs/HTNG-FIAS` Phase 6/7 | **annotate only**: subject belongs to canonical HF-21 (retention also defines the duplicate window). Historical docs are not edited |
| — | Phase-doc HF-18 "SoR for room cleanliness" | `docs/HTNG-FIAS` Phase 5 | **annotate only**: subject belongs to canonical HF-01 (per-entity system of record) and HF-37 (room-status vocabulary) |
| — | Rate-limit / volume values | `config.py`, R-23 | **remove HF-24 attribution**; cite vendor request A2/A4 (no decision ID) — or create a new capacity decision if the owner wants one |

### Option A vs Option B for HF-11 / HF-06 (owner decides)

| | Option A — restore the split (recommended) | Option B — confirm the merge |
|---|---|---|
| Canonical | HF-11 = spec content; HF-06 = link rules | HF-11 = content + link rules; HF-06 retired as "absorbed into HF-11" |
| Preserves earlier decision boundaries | yes (different owners: VENDOR vs VENDOR+OPS) | no — documented merge |
| Code/test changes later | comments in `transport/framing.py`, `transport/tcp.py`, `transport/tcp_server.py`, `simulators/fixtures.py` (framing + ACK lines); `contracts.py` ACK message "(HF-11)" → "(HF-06)" and its assertion in `test_vendor_contracts.py`; `FIASAdapter`'s `BLOCKING_DECISION` stays HF-11 | none; only doc wording (remove "HF-06 / HF-11" double citations) |
| Doc changes | blocker rows BLK-F3 (framing), F4 (ACK), F5 (heartbeat), F6 (role) → HF-06; protocol support, vendor dependencies, vendor request B3–B7, validation plan V-03…V-06 | BLK-F6 note; FIAS protocol support; vendor dependencies |
| Risk | small code-comment/test-string edits; must be done in one change to stay consistent | loses the distinction for future decision tracking |

## 5. Evidence and reasoning

* **Verified facts:** all reference counts and locations (Appendix A); repo register §1 records
  the brief's meanings and the conflict for HF-05/HF-11; `approvals.py` defines HF-01, 02, 05, 07,
  11, 18, 19, 21, 39; tests assert `"HF-11"` (`test_fias_adapter.py`, `test_exchange.py`,
  `test_api.py`, `test_vendor_contracts.py`), `"HF-07"` (`test_exchange.py`) and the live-write
  set `{"HF-01","HF-02","HF-05","HF-19"}` (`test_domain.py`); earlier register rows for HF-01…HF-39
  (read from the sibling copy, unchanged); phase-doc lines cited in §3.1.
* **Why repo IDs are canonical:** they are the ones enforced by code and asserted by tests; the
  earlier register is untracked and outside this repository; renumbering repo IDs would change
  the live-write gate and test contracts without changing any decision.
* **Why HF-40 for folio:** HF-01…HF-39 are all taken in the earlier register; HF-40 appears
  nowhere in either source.
* **Assumptions requiring owner confirmation:** (1) the earlier register is the authoritative
  history for HF-03…HF-38 meanings; (2) the round-1 brief was authoritative for the repo's
  HF-05/HF-11 meanings; (3) no other team or document outside these two sources uses HF IDs
  (not verifiable from this repository); (4) the earlier implementation's phase reports in
  `docs/HTNG-FIAS/` are historical and should be annotated, not edited.

## 6. Repository-owner decisions required

1. Approve this repository's register as the **single canonical register** (Y/N).
2. Choose **Option A** (restore HF-06 split) or **Option B** (confirm merge into HF-11).
3. Approve **HF-40** for "Folio and billing ownership" (earlier HF-11).
4. Approve importing HF-03, 04, 09, 14, 15, 20, 30, 31, 37, 38 (and HF-06 under Option A) with
   their earlier meanings, statuses and owner roles.
5. Decide how `docs/HTNG-FIAS/` is treated: annotate with an errata note / archive / leave.
6. Decide whether rate-limit/volume values get their own decision ID or none.
7. Confirm whether the earlier register file should be copied into this repository as a
   read-only historical reference (currently only on one disk, untracked).

## 7. Document update checklist (to execute only after approval)

| # | File | Change | Depends on |
|---|---|---|---|
| 1 | `docs/HTNG_FIAS_DECISION_REGISTER.md` | add Legacy-ID column; add imported IDs; add HF-40; Option A/B outcome | decisions 1–4 |
| 2 | `backend/app/integrations/domain/approvals.py` | add imported IDs to `DECISIONS` only if owner wants them gate-visible (no status change) | 4 |
| 3 | `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | BLK-F3…F6 → HF-06 (Option A); BLK-V1 cite HF-03/04 as canonical | 2, 4 |
| 4 | `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | replace "numbering caution" with canonical note | 1 |
| 5 | `docs/HTNG_FIAS_FACILITY_MAPPING.md` | "HF-11 earlier numbering" → HF-40 | 3 |
| 6 | `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md`, `HTNG_FIAS_VENDOR_DEPENDENCIES.md`, `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` (B3–B7), `HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` (V-03…V-06) | HF-06/HF-11 per option; drop "earlier register" qualifiers for imported IDs | 2, 4 |
| 7 | `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | R-13, R-23 corrections (§3.3) | 6 |
| 8 | `backend/app/integrations/config.py` (comment) | remove HF-24 attribution | 6 |
| 9 | Option A only: `transport/framing.py`, `transport/tcp.py`, `transport/tcp_server.py`, `simulators/fixtures.py`, `contracts.py`, `tests/integrations/test_vendor_contracts.py` | HF-11 → HF-06 in link-rule comments/messages; update assertion; re-run integration suite | 2 |
| 10 | `docs/HTNG_FIAS_DOCUMENTATION_AUDIT.md`, `HTNG_FIAS_REPOSITORY_BASELINE.md`, `HTNG_FIAS_PRODUCTION_READINESS.md`, `HTNG_FIAS_ARCHITECTURE.md`, `HTNG_FIAS_NEXT_PHASE_REPORT.md` | reflect canonical IDs | 1–4 |
| 11 | `docs/HTNG-FIAS/` | errata note only (HF-07, HF-11, HF-18 usages) | 5 |

Unchanged in any option: `approvals.REQUIRED_FOR_LIVE_WRITES` (HF-01, 02, 05, 19) and its tests;
`HTNG` adapter `BLOCKING_DECISION` (HF-07); `FIASAdapter` `BLOCKING_DECISION` (HF-11).

## 8. Approval / sign-off

| Field | Value |
|---|---|
| Decision 1 (canonical register) | ☐ Approved ☐ Rejected |
| Decision 2 | ☐ Option A ☐ Option B |
| Decision 3 (HF-40) | ☐ Approved ☐ Other: ______ |
| Decision 4 (imports) | ☐ Approved ☐ Partial: ______ |
| Decision 5 (`docs/HTNG-FIAS/`) | ☐ Errata ☐ Archive ☐ Leave |
| Decision 6 (volumes ID) | ☐ No ID ☐ New ID: ______ |
| Decision 7 (copy earlier register) | ☐ Yes ☐ No |
| Approved by (role, name), date | |

## Appendix A — Every HF reference in the repository (2026-11-20, before this file)

Tokens are shown as written (shorthand such as `HF-14/15` and `HF-25/26` kept). Paths are
relative to the repository root.

| File | Line | HF token(s) |
|---|---|---|
| `backend/app/integrations/__init__.py` | 17 | HF-07 / HF-11 |
| `backend/app/integrations/adapters/fias/adapter.py` | 4 | HF-11 |
| `backend/app/integrations/adapters/fias/spec.py` | 10 | HF-11 |
| `backend/app/integrations/adapters/fias/spec.py` | 185 | HF-11 |
| `backend/app/integrations/adapters/htng/adapter.py` | 4 | HF-07 |
| `backend/app/integrations/adapters/htng/adapter.py` | 66 | HF-08 |
| `backend/app/integrations/adapters/htng/schema.py` | 9 | HF-07 / HF-08 |
| `backend/app/integrations/adapters/htng/schema.py` | 16 | HF-39 |
| `backend/app/integrations/adapters/htng/schema.py` | 39 | HF-07 |
| `backend/app/integrations/adapters/htng/schema.py` | 79 | HF-39, HF-07 |
| `backend/app/integrations/adapters/htng/sender.py` | 4 | HF-24 |
| `backend/app/integrations/admin.py` | 13 | HF-05 |
| `backend/app/integrations/admin.py` | 18 | HF-22 |
| `backend/app/integrations/api/router.py` | 5 | HF-39 |
| `backend/app/integrations/api/router.py` | 22 | HF-07 / HF-24 |
| `backend/app/integrations/api/router.py` | 72 | HF-39 |
| `backend/app/integrations/api/router.py` | 121 | HF-39 |
| `backend/app/integrations/api/router.py` | 383 | HF-07 |
| `backend/app/integrations/cli.py` | 10 | HF-39 |
| `backend/app/integrations/cli.py` | 12 | HF-22 |
| `backend/app/integrations/config.py` | 7 | HF-01/02/05/19 |
| `backend/app/integrations/config.py` | 9 | HF-21 |
| `backend/app/integrations/config.py` | 45 | HF-18 |
| `backend/app/integrations/config.py` | 50 | HF-21 |
| `backend/app/integrations/config.py` | 55 | HF-24 |
| `backend/app/integrations/config.py` | 66 | HF-18 |
| `backend/app/integrations/contracts.py` | 135 | HF-11 |
| `backend/app/integrations/contracts.py` | 151 | HF-07 / HF-11 |
| `backend/app/integrations/core/retry.py` | 7 | HF-27 |
| `backend/app/integrations/domain/approvals.py` | 40 | HF-01 |
| `backend/app/integrations/domain/approvals.py` | 41 | HF-02 |
| `backend/app/integrations/domain/approvals.py` | 42 | HF-05 |
| `backend/app/integrations/domain/approvals.py` | 43 | HF-07 |
| `backend/app/integrations/domain/approvals.py` | 44 | HF-11 |
| `backend/app/integrations/domain/approvals.py` | 45 | HF-18 |
| `backend/app/integrations/domain/approvals.py` | 46 | HF-19 |
| `backend/app/integrations/domain/approvals.py` | 47 | HF-21 |
| `backend/app/integrations/domain/approvals.py` | 48 | HF-39 |
| `backend/app/integrations/domain/approvals.py` | 52 | HF-01, HF-02, HF-05, HF-19 |
| `backend/app/integrations/domain/stays.py` | 15 | HF-01/02/05/19 |
| `backend/app/integrations/domain/stays.py` | 16 | HF-18 |
| `backend/app/integrations/domain/stays.py` | 19 | HF-02 / HF-31 |
| `backend/app/integrations/domain/stays.py` | 164 | HF-18 |
| `backend/app/integrations/domain/stays.py` | 166 | HF-02 |
| `backend/app/integrations/processing/repository.py` | 370 | HF-27 |
| `backend/app/integrations/processing/sql_models.py` | 3 | HF-39 |
| `backend/app/integrations/processing/sql_models.py` | 95 | HF-05 |
| `backend/app/integrations/processing/sql_models.py` | 97 | HF-05 |
| `backend/app/integrations/processing/sql_models.py` | 162 | HF-21 |
| `backend/app/integrations/processing/sql_models.py` | 234 | HF-23 |
| `backend/app/integrations/runtime.py` | 8 | HF-11 |
| `backend/app/integrations/runtime.py` | 9 | HF-07 |
| `backend/app/integrations/runtime.py` | 11 | HF-01/02/05/19/18 |
| `backend/app/integrations/runtime.py` | 12 | HF-39 |
| `backend/app/integrations/security/clients.py` | 19 | HF-22 |
| `backend/app/integrations/security/facility.py` | 9 | HF-05 |
| `backend/app/integrations/security/sql_stores.py` | 1 | HF-39 |
| `backend/app/integrations/service.py` | 15 | HF-21 |
| `backend/app/integrations/service.py` | 17 | HF-25/HF-26 |
| `backend/app/integrations/simulators/fixtures.py` | 10 | HF-11 |
| `backend/app/integrations/simulators/fixtures.py` | 130 | HF-11 |
| `backend/app/integrations/transport/framing.py` | 7 | HF-11 |
| `backend/app/integrations/transport/soap.py` | 6 | HF-07 / HF-08 |
| `backend/app/integrations/transport/tcp.py` | 15 | HF-06 / HF-11 |
| `backend/app/integrations/transport/tcp.py` | 322 | HF-06 |
| `backend/app/integrations/transport/tcp.py` | 403 | HF-11 |
| `backend/app/integrations/transport/tcp_server.py` | 4 | HF-06 / HF-11 |
| `backend/app/integrations/transport/xml_security.py` | 3 | HF-39 |
| `backend/migrations/drafts/integration_tables_candidate.py` | 3 | HF-39 |
| `backend/migrations/drafts/integration_tables_candidate.py` | 19 | HF-21 |
| `backend/migrations/drafts/integration_tables_candidate.py` | 20 | HF-23 |
| `backend/tests/integrations/test_api.py` | 115 | HF-11 |
| `backend/tests/integrations/test_domain.py` | 82 | HF-01, HF-02, HF-05, HF-19 |
| `backend/tests/integrations/test_domain.py` | 88 | HF-01, HF-02, HF-05, HF-19 |
| `backend/tests/integrations/test_domain.py` | 129 | HF-18 |
| `backend/tests/integrations/test_domain.py` | 134 | HF-02 |
| `backend/tests/integrations/test_exchange.py` | 51 | HF-11, HF-07 |
| `backend/tests/integrations/test_fias_adapter.py` | 46 | HF-11 |
| `backend/tests/integrations/test_fias_adapter.py` | 50 | HF-11 |
| `backend/tests/integrations/test_hms_domain_mysql.py` | 84 | HF-02 / HF-31 |
| `backend/tests/integrations/test_htng_adapter.py` | 150 | HF-07 |
| `backend/tests/integrations/test_htng_adapter.py` | 176 | HF-39 |
| `backend/tests/integrations/test_migration_candidate.py` | 3 | HF-39 |
| `backend/tests/integrations/test_vendor_contracts.py` | 5 | HF-07 / HF-11 |
| `backend/tests/integrations/test_vendor_contracts.py` | 33 | HF-07, HF-11 |
| `backend/tests/integrations/test_vendor_contracts.py` | 81 | HF-11 |
| `backend/tests/integrations/test_vendor_contracts.py` | 92 | HF-11, HF-07 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 88 | HF-19 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 341 | HF-01 to HF-39 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 342 | HF-01 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 343 | HF-07 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 344 | HF-11 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | 345 | HF-18 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE6_PERSISTENCE_READINESS_REPORT.md` | 418 | HF-01 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE6_PERSISTENCE_READINESS_REPORT.md` | 419 | HF-07 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE7_MYSQL_RUNTIME_VERIFICATION_REPORT.md` | 238 | HF-01 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE7_MYSQL_RUNTIME_VERIFICATION_REPORT.md` | 239 | HF-07 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE8_SECURITY_AND_OPERATIONAL_READINESS_REPORT.md` | 21 | HF-19 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE8_SECURITY_AND_OPERATIONAL_READINESS_REPORT.md` | 36 | HF-19 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE8_SECURITY_AND_OPERATIONAL_READINESS_REPORT.md` | 38 | HF-19 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE8_SECURITY_AND_OPERATIONAL_READINESS_REPORT.md` | 125 | HF-07 |
| `docs/HTNG-FIAS/HTNG_FIAS_PHASE9_ADVERSARIAL_SECURITY_VERIFICATION_REPORT.md` | 21 | HF-19 |
| `docs/HTNG_FIAS_ARCHITECTURE.md` | 63 | HF-11, HF-07 |
| `docs/HTNG_FIAS_ARCHITECTURE.md` | 72 | HF-39 |
| `docs/HTNG_FIAS_ARCHITECTURE.md` | 82 | HF-25/26, HF-06 |
| `docs/HTNG_FIAS_ARCHITECTURE.md` | 83 | HF-11 |
| `docs/HTNG_FIAS_ARCHITECTURE.md` | 91 | HF-27 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 11 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 12 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 13 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 14 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 15 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 16 | HF-11, HF-06 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 17 | HF-11 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 23 | HF-07 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 24 | HF-08 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 25 | HF-39, HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 26 | HF-07 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 32 | HF-01 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 33 | HF-02 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 34 | HF-05 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 35 | HF-18 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 36 | HF-19 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 37 | HF-21 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 38 | HF-27 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 44 | HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 45 | HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 46 | HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 47 | HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 48 | HF-39 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 54 | HF-03/HF-04 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 57 | HF-22 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 63 | HF-22, HF-23, HF-24 |
| `docs/HTNG_FIAS_BLOCKER_REGISTER.md` | 64 | HF-25/26 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 10 | HF-05 / HF-11 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 17 | HF-01 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 18 | HF-02 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 19 | HF-05 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 20 | HF-18 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 21 | HF-19 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 22 | HF-21 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 23 | HF-27 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 25 | HF-01 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 36 | HF-02 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 46 | HF-05 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 55 | HF-18 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 64 | HF-19 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 73 | HF-21 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 82 | HF-27 |
| `docs/HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | 94 | HF-01, HF-02, HF-05, HF-19 |
| `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql` | 1 | HF-39 |
| `docs/HTNG_FIAS_DATABASE_DESIGN.md` | 1 | HF-39 |
| `docs/HTNG_FIAS_DATABASE_DESIGN.md` | 24 | HF-21 |
| `docs/HTNG_FIAS_DATABASE_DESIGN.md` | 58 | HF-21 / HF-23 |
| `docs/HTNG_FIAS_DATABASE_DESIGN.md` | 60 | HF-39 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 1 | HF-39 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 74 | HF-05 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 80 | HF-21 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 107 | HF-39 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 114 | HF-21 |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | 147 | HF-39 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 15 | HF-01 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 16 | HF-02 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 17 | HF-05 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 18 | HF-07 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 19 | HF-11 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 20 | HF-19 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 21 | HF-21 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 22 | HF-39 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 30 | HF-01 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 31 | HF-02 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 32 | HF-05 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 33 | HF-07 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 34 | HF-08 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 35 | HF-11 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 36 | HF-18 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 37 | HF-19 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 38 | HF-21 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 39 | HF-22 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 40 | HF-23 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 41 | HF-24 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 42 | HF-25 / HF-26 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 43 | HF-27 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 44 | HF-39 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 46 | HF-08, HF-18, HF-22, HF-27 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 47 | HF-01/02/05/07/11/19/21/39 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 53 | HF-01, HF-02, HF-05, HF-19 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 54 | HF-11 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 55 | HF-07 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 56 | HF-39, HF-07 |
| `docs/HTNG_FIAS_DECISION_REGISTER.md` | 57 | HF-39 |
| `docs/HTNG_FIAS_DOCUMENTATION_AUDIT.md` | 30 | HF-27 |
| `docs/HTNG_FIAS_DOCUMENTATION_AUDIT.md` | 42 | HF-05, HF-11 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 13 | HF-05 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 16 | HF-02 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 19 | HF-02 / HF-31 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 37 | HF-18 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 38 | HF-02 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 43 | HF-01, HF-02, HF-05, HF-19 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 50 | HF-38, HF-20 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 51 | HF-37, HF-11 |
| `docs/HTNG_FIAS_FACILITY_MAPPING.md` | 52 | HF-14/15 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 14 | HF-11 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 30 | HF-11 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 32 | HF-11, HF-05 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 35 | HF-06 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 37 | HF-30, HF-37 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 63 | HF-11, HF-03/04 |
| `docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md` | 67 | HF-27 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 15 | HF-07, HF-08 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 26 | HF-39, HF-07 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 43 | HF-07 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 44 | HF-07 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 45 | HF-07 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 46 | HF-08 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 47 | HF-24 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 48 | HF-07 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 49 | HF-39 |
| `docs/HTNG_FIAS_HTNG_SCHEMA_SUPPORT.md` | 50 | HF-09 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 11 | HF-39/HF-07 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 39 | HF-06 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 41 | HF-21 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 44 | HF-11 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 45 | HF-07/08/39 |
| `docs/HTNG_FIAS_IMPLEMENTATION_AUDIT.md` | 46 | HF-01/02/05/19/18 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 25 | HF-21 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 46 | HF-11 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 47 | HF-07, HF-08, HF-39 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 48 | HF-01, HF-02, HF-05, HF-19, HF-18 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 49 | HF-39 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 50 | HF-21 |
| `docs/HTNG_FIAS_IMPLEMENTATION_PROGRESS.md` | 51 | HF-25 / HF-26 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 64 | HF-11 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 72 | HF-07/HF-08, HF-39 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 98 | HF-01/02/05/19 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 99 | HF-18, HF-02 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 151 | HF-01, HF-02, HF-05, HF-19, HF-18, HF-21/22/23 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 152 | HF-25/26/27 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 157 | HF-39 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 205 | HF-39 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 207 | HF-25/26, HF-27 |
| `docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` | 208 | HF-21 |
| `docs/HTNG_FIAS_MIGRATION_READINESS.md` | 3 | HF-39 |
| `docs/HTNG_FIAS_MIGRATION_READINESS.md` | 64 | HF-21 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 21 | HF-27 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 37 | HF-11 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 82 | HF-11 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 83 | HF-07, HF-08 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 84 | HF-01, HF-02, HF-05, HF-18, HF-19, HF-21, HF-27, HF-22, HF-23 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 85 | HF-24, HF-25/26 |
| `docs/HTNG_FIAS_NEXT_PHASE_REPORT.md` | 86 | HF-39 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 4 | HF-39 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 14 | HF-18 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 15 | HF-21 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 16 | HF-21 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 28 | HF-22 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 46 | HF-39 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 53 | HF-24 |
| `docs/HTNG_FIAS_OPERATIONS_RUNBOOK.md` | 102 | HF-25/HF-26 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 12 | HF-11 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 13 | HF-07, HF-08, HF-39 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 15 | HF-39 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 16 | HF-08, HF-21, HF-22, HF-24 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 18 | HF-25/26, HF-23 |
| `docs/HTNG_FIAS_PRODUCTION_READINESS.md` | 19 | HF-01 |
| `docs/HTNG_FIAS_REPOSITORY_BASELINE.md` | 54 | HF-05 |
| `docs/HTNG_FIAS_REPOSITORY_BASELINE.md` | 55 | HF-11 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 10 | HF-22 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 11 | HF-22 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 12 | HF-02, HF-05 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 13 | HF-19 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 15 | HF-21 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 17 | HF-27 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 18 | HF-27 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 20 | HF-24 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 22 | HF-24 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 23 | HF-11 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 25 | HF-07, HF-08, HF-39 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 26 | HF-01, HF-02, HF-05, HF-18, HF-19 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 27 | HF-01, HF-02 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 28 | HF-39 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 30 | HF-25/26 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 31 | HF-21 |
| `docs/HTNG_FIAS_REQUIREMENTS_TRACEABILITY.md` | 32 | HF-24 |
| `docs/HTNG_FIAS_SECRET_SCAN_REPORT.md` | 37 | HF-21 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 15 | HF-08 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 16 | HF-24, HF-22 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 23 | HF-05 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 36 | HF-39 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 50 | HF-21 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 82 | HF-08 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 83 | HF-21 |
| `docs/HTNG_FIAS_SECURITY_DESIGN.md` | 84 | HF-22, HF-23, HF-24 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 8 | HF-03/HF-04 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 9 | HF-11 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 10 | HF-11, HF-06 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 11 | HF-05 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 12 | HF-07 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 13 | HF-08 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 14 | HF-24 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 15 | HF-09 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 16 | HF-07 / HF-11 |
| `docs/HTNG_FIAS_VENDOR_DEPENDENCIES.md` | 17 | HF-31 / HF-37 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 14 | HF-05 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 16 | HF-01/HF-02 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 37 | HF-24 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 39 | HF-22 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 44 | HF-39 |
| `docs/HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md` | 50 | HF-01/02/05/19 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 39 | HF-05 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 41 | HF-01 / HF-02 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 50 | HF-11 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 61 | HF-24 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 67 | HF-07 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 68 | HF-07 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 71 | HF-08 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 76 | HF-24 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 79 | HF-39 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 106 | HF-39 |
| `docs/HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | 108 | HF-08 |
| `docs/HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` | 15 | HF-11 |
| `docs/HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` | 19 | HF-39 |
| `docs/HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` | 20 | HF-08 |
| `docs/HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` | 53 | HF-05 |
