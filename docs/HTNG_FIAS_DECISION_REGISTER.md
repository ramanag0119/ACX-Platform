# HTNG / FIAS — Decision and Approval Register (CANONICAL)

**This is the canonical HF register for this repository** (repository-owner decision,
2026-11-20, applying `HTNG_FIAS_HF_ID_RECONCILIATION_PROPOSAL.md`, Option A).
**No decision below is Approved.** No approval evidence exists in this repository.
`backend/app/integrations/domain/approvals.py` mirrors part of this table in code; changing a
status to Approved there requires the evidence reference and a reviewed commit.

## 1. Provenance and numbering

* **Repo** = meaning set by the implementation brief of 2026-11-19 and used by this
  repository's code and tests since round 1.
* **Legacy** = earlier register `HTNG_FIAS_BUSINESS_VENDOR_DECISION_REGISTER.md` (2026-11-17),
  found only in the untracked sibling working copy `../HMS-Frontend/ACX-Platform/docs/`. It has
  **not** been copied here; its provenance and exact source are **pending project-owner
  confirmation**. Imported rows reproduce its meaning, status, owner roles and stated
  dependency as read on 2026-11-19; nothing was added to them.
* Reconciliation applied 2026-11-20:

| Change | Detail |
|---|---|
| HF-11 narrowed | FIAS official **specification content** (legacy HF-05's subject) — no longer covers link rules |
| HF-06 restored | FIAS **communication / link rules** (legacy HF-06) — the round-1 merge into HF-11 is reversed |
| HF-40 new | Folio and billing ownership (legacy **HF-11**), renumbered because of the collision |
| Imported | HF-03, 04, 06, 09, 14, 15, 20, 30, 31, 37, 38 |
| Not an HF decision | Vendor message volumes for rate-limit configuration — tracked as external prerequisite `BLK-V7` in `HTNG_FIAS_BLOCKER_REGISTER.md` |
| Historical | `docs/HTNG-FIAS/` keeps its original wording; see its `README.md` errata |

Legacy ↔ canonical: legacy HF-05 → **HF-11**; legacy HF-06 → **HF-06**; legacy HF-11 → **HF-40**;
all other shared numbers have the same meaning in both sources (verified for HF-01, 02, 07, 08,
18, 19, 21–27, 39 in the reconciliation proposal §2).

## 2. Register

| ID | Decision | Status | Impact / blocks | Owner (role) | Required evidence | Source |
|---|---|---|---|---|---|---|
| HF-01 | PMS / HMS system of record | Awaiting Business Approval | Blocks live domain writes | PO, ARCH | signed per-entity table | Repo |
| HF-02 | Facility / entity mapping ownership | Awaiting Business Approval | Blocks production mapping, stay resolver, live writes | PO, BA, ARCH | ownership statement | Repo |
| HF-03 | Target PMS / vendor, product, version and hosting for the pilot | Open | Gates all vendor requests (HF-04 … HF-09) | PO | named product per property | Legacy (pending confirmation) |
| HF-04 | Protocol selection per deployment (FIAS · HTNG · vendor REST · combination) | Awaiting Vendor Confirmation | Which adapter is built; whether a SOAP stack is needed | PO, VENDOR | protocol statement | Legacy (pending confirmation) |
| HF-05 | FIAS external property-code case sensitivity | Awaiting Vendor Confirmation | Blocks verified mapping behaviour; EXACT used meanwhile; blocks live writes | VENDOR, HOTEL-OPS | vendor statement (request A3) | Repo |
| HF-06 | FIAS connection / link rules: TCP/RS-232, listening side, host/port, framing, encoding, sequence/ACK, heartbeat, reconnect, resync | Awaiting Vendor Confirmation | Link layer design; firewall rules; production framer, responder, heartbeat, link role | VENDOR, OPS | vendor link document (request B3–B7) | Legacy HF-06 (pending confirmation) |
| HF-07 | HTNG version / profile / schema scope | Awaiting Vendor Confirmation | Blocks every HTNG operation; adapter BLOCKED | VENDOR | WSDL/XSD + profile | Repo |
| HF-08 | HTNG security profile | Awaiting Vendor Confirmation | Blocks HTNG exposure | VENDOR, SEC | security specification | Repo (= legacy HF-08) |
| HF-09 | Vendor test environment, simulator, test credentials, certification process | Awaiting Vendor Confirmation | Phase 2/5 exit criteria (vendor validation) | VENDOR, QA | environment access, process document | Legacy (pending confirmation) |
| HF-11 | FIAS official specification content: manual and version, licensed record set, record/field definitions, official samples | Awaiting Vendor Confirmation | Blocks every FIAS record; adapter BLOCKED | VENDOR | manual + record set (request B1, B2, B8–B11) | Repo; subject = legacy HF-05 |
| HF-14 | Who executes room-level device actions (keys, HVAC, DND); is an OSS command path built? | Open | Phase 4 scope; whether the outbox emits device intents | ARCH, PLAT, PO | ownership decision | Legacy (pending confirmation) |
| HF-15 | Lock vendor, encoding method, key types (card, mobile, keypad) and lock-activity sync | Awaiting Vendor Confirmation | Key-issuance service; key-secret storage | LOCK-VENDOR, PLAT | lock-vendor documentation | Legacy (pending confirmation) |
| HF-18 | Integration principal / HMS actor for writes | Open | Blocks live writes (`INTEGRATION_ACTOR_USER_ID` unset) | SEC, ARCH | named account | Repo (= legacy HF-18) |
| HF-19 | Facility authorization / isolation rules | Awaiting Business Approval | Blocks production access; enforced in code meanwhile; blocks live writes | SEC, PO | sign-off + pilot list | Repo |
| HF-20 | Guest PII scope; phone/email requirements; consent | Awaiting Business Approval | Guest canonical model; possible schema change | LEGAL, PO, SEC | policy | Legacy (pending confirmation) |
| HF-21 | Raw-payload retention / encryption | Open | Blocks production payload retention; raw wire storage off; no purge | LEGAL, SEC | values | Repo |
| HF-22 | Credential storage | Open | Blocks issuing real client secrets | SEC, OPS | storage decision | Repo (= legacy HF-22) |
| HF-23 | Audit-log retention / immutability | Open | Audit table append-only by convention only | SEC, LEGAL | retention value | Repo (= legacy HF-23) |
| HF-24 | Vendor network access path and TLS | Awaiting Vendor Confirmation | Blocks connectivity | OPS, SEC, VENDOR | network design | Repo (= legacy HF-24) |
| HF-25 / HF-26 | Worker / link hosting and restart policy | Open | No supervised process wired | ARCH, OPS | hosting + restart policy | Repo (= legacy HF-25/26) |
| HF-27 | Retry policy and ordering | Open | Bounded retry and per-entity (per-stay) ordering implemented with defaults; final policy pending | ARCH, BE | per-type policy | Repo (= legacy HF-27) |
| HF-30 | Property timezone (source and value of each property's timezone) | Awaiting Business Approval | Date/time mapping (no timezone column on `facility`) | PO, HOTEL-OPS | timezone source per property | Legacy (pending confirmation); dependency column not recorded in the captured legacy row |
| HF-31 | Vendor code ↔ HMS code mappings (hotel code ↔ `facility_uid`, room types, room status, reservation status, work-order status) | Awaiting Business Approval | Mapping tables / vocabularies | HOTEL-OPS, BA, VENDOR | mapping tables | Legacy (pending confirmation) |
| HF-37 | Room-status vocabulary extension (e.g. inspected, out-of-order, out-of-service) | Open | Possible schema/seed change; housekeeping screens | HOTEL-OPS, BA | vocabulary decision | Legacy (pending confirmation) |
| HF-38 | Reservation data scope in HMS (rates, amounts, guarantee, no-show, confirmation numbers) | Open | Canonical model and possible schema change; deferrable for a FIAS guest-event-first pilot | PO, FIN | scope decision | Legacy (pending confirmation) |
| HF-39 | DBA / schema authorization (and new dependencies) | Awaiting DBA Approval | Blocks target-database migration; tables exist only in disposable DB | ARCH, DBA, PO | DBA decision record | Repo (= legacy HF-39) |
| HF-40 | Folio and billing ownership | Awaiting Business Approval | Posting direction; folio model scope | FIN, PO | decision among legacy options E1 · E2 · E3 | Legacy **HF-11**, renumbered (pending confirmation) |

## 3. Gates in code

| Gate | Where | Requires |
|---|---|---|
| Live domain writes | `domain/approvals.py` `LiveWriteGate` | env flag + HF-01, HF-02, HF-05, HF-19 Approved with evidence |
| FIAS production | `adapters/fias/spec.py` | verified `PRODUCTION_SPECIFICATION` (HF-11) and verified link rules (HF-06) |
| HTNG production | `adapters/htng/schema.py` | verified profile registered (HF-07) |
| XSD validation | `XsdValidator` | approved library (HF-39) + XSD (HF-07) |
| Integration tables | `migrations/drafts/` | DBA sign-off (HF-39) |
