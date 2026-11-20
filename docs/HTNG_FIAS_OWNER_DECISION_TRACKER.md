# HTNG / FIAS — Owner and Decision Tracker

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** As of 2026-11-20 **no decision
is approved and no owner is named.** This tracker records ownership confirmation and, later,
approval evidence. Decision meanings and statuses come from `HTNG_FIAS_DECISION_REGISTER.md`
(canonical); actions and dependencies are in `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md`.

Rules:
* A field stays blank until the evidence exists.
* No approver, name or date is ever inferred.
* A technical recommendation is not an approval.

## 1. Ownership confirmation (29 items)

Provenance: **Repo** = set by this repository's implementation brief. **Legacy †** = imported
from the older register in the other working copy (`../HMS-Frontend/ACX-Platform`, kept
read-only and not copied); its provenance is unconfirmed (canonical register §1).

| ID | Current role(s) | Provenance | All roles defined? | Named individual | Confirmation required from | Ownership status |
|---|---|---|---|---|---|---|
| HF-01 | PO, ARCH | Repo | yes | | Project sponsor / PO | Role assigned; person unassigned |
| HF-02 | PO, BA, ARCH | Repo | yes | | PO | Role assigned; person unassigned |
| HF-03 | PO | Legacy † | yes | | Project sponsor | **Provenance unconfirmed**; person unassigned |
| HF-04 | PO, VENDOR | Legacy † | yes | | PO (VENDOR side: none until HF-03) | **Provenance unconfirmed**; vendor contact missing |
| HF-05 | VENDOR, HOTEL-OPS | Repo | yes | | PO; vendor contact after HF-03 | Role assigned; vendor contact missing |
| HF-06 | VENDOR, OPS | Legacy † | yes | | PO | **Provenance unconfirmed**; vendor contact missing |
| HF-07 | VENDOR | Repo | yes | | PO | Vendor contact missing |
| HF-08 | VENDOR, SEC | Repo | yes | | PO, SEC lead | Vendor contact missing |
| HF-09 | VENDOR, QA | Legacy † | yes | | PO | **Provenance unconfirmed**; vendor contact missing |
| HF-11 | VENDOR | Repo | yes | | PO | Vendor contact missing |
| HF-14 | ARCH, **PLAT**, PO | Legacy † | **no (PLAT)** | | PO | **Provenance unconfirmed; role undefined** |
| HF-15 | **LOCK-VENDOR**, **PLAT** | Legacy † | **no (both)** | | PO | **Provenance unconfirmed; roles undefined** |
| HF-18 | SEC, ARCH | Repo | yes | | SEC lead | Role assigned; person unassigned |
| HF-19 | SEC, PO | Repo | yes | | SEC lead, PO | Role assigned; person unassigned |
| HF-20 | LEGAL, PO, SEC | Legacy † | yes | | PO | **Provenance unconfirmed** |
| HF-21 | LEGAL, SEC | Repo | yes | | LEGAL, SEC lead | Role assigned; person unassigned |
| HF-22 | SEC, OPS | Repo | yes | | SEC lead | Role assigned; person unassigned |
| HF-23 | SEC, LEGAL | Repo | yes | | SEC lead | Role assigned; person unassigned |
| HF-24 | OPS, SEC, VENDOR | Repo | yes | | OPS lead | Vendor contact missing |
| HF-25 | ARCH, OPS | Repo | yes | | OPS lead | Role assigned; person unassigned |
| HF-26 | ARCH, OPS | Repo | yes | | OPS lead | Role assigned; person unassigned |
| HF-27 | ARCH, BE | Repo | yes | | ARCH lead | Role assigned; person unassigned |
| HF-30 | PO, HOTEL-OPS | Legacy † | yes | | PO | **Provenance unconfirmed** (dependency not captured) |
| HF-31 | HOTEL-OPS, BA, VENDOR | Legacy † | yes | | PO | **Provenance unconfirmed**; vendor contact missing |
| HF-37 | HOTEL-OPS, BA | Legacy † | yes | | PO | **Provenance unconfirmed** |
| HF-38 | PO, **FIN** | Legacy † | **no (FIN)** | | PO | **Provenance unconfirmed; role undefined** |
| HF-39 | ARCH, DBA, PO | Repo | yes | | DBA lead | Role assigned; person unassigned |
| HF-40 | **FIN**, PO | Legacy † (legacy HF-11) | **no (FIN)** | | PO | **Provenance unconfirmed; role undefined**; options E1–E3 not in this repo |
| BLK-V7 | VENDOR, OPS | Repo (blocker register) | yes | | PO | Vendor contact missing |
| Monitoring and alert routing (not an HF ID) | — | none recorded | — | | OPS lead / PO | **No owner recorded** |

| Summary | Count |
|---|---|
| Items with a named individual | 0 / 29 |
| Owner roles pending provenance confirmation (legacy †) | 12 |
| Items using an undefined role | 4 (HF-14, HF-15, HF-38, HF-40) |
| Items whose PMS-vendor counterpart cannot exist until HF-03 | 10 (HF-04, 05, 06, 07, 08, 09, 11, 24, 31, BLK-V7); HF-15 needs the separate lock vendor |

**Undefined roles.** Proposed descriptions, for the PO to confirm or replace (not adopted):

| Role | Proposed description |
|---|---|
| PLAT | Platform / device-integration lead (room devices, OSS command paths) |
| LOCK-VENDOR | The door-lock system vendor's technical contact |
| FIN | Finance / revenue owner for folio, billing and rates |

## 2. HF-03 decision package (first critical decision)

| Field | Content |
|---|---|
| Decision | Target PMS vendor, product, version and hosting (on-premise / cloud) for the pilot, **per property** |
| Owner | PO (legacy †; provenance to be confirmed in the same answer) |
| Status | **Open** (canonical) |
| Why first | It gates every vendor request (HF-04 … HF-09), gives every VENDOR-owned item a counterpart, and determines whether FIAS, HTNG or both are pursued |
| What the project knows | Nothing about the vendor: no vendor, product or property list appears in any project document. **None is assumed** |
| Answer format | Per property: property name / HMS `facility_uid` · PMS vendor · product · version · hosting · interface the vendor offers (if known) · vendor technical contact (role or name) |
| Evidence | Signed or minuted PO decision with date and reference |
| Unblocks | Vendor request dispatch (`HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md` draft 1); HF-04; HF-19 / HF-30 property list |
| Request draft | `HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md` draft 0 |

## 3. Decision papers not covered by the business register

`HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` already holds papers for HF-01, 02, 05, 18, 19, 21
and 27. The remaining business items are below. Only options already documented are listed.

| ID | Question | Documented options | Impact while open | Can it be deferred? |
|---|---|---|---|---|
| HF-14 | Who executes room-level device actions? Is an OSS command path built? | none recorded in this repo | Phase-4 scope; the outbox emits no device intents | Register: "Phase 4 scope". The PO may confirm deferral |
| HF-20 | Guest PII scope; phone/email; consent | none recorded | Guest canonical model; possible schema change | Only if the pilot carries no guest PII beyond the stay reference (LEGAL to confirm) |
| HF-30 | Source and value of each property's timezone | none; dependency **not captured** | Date/time mapping (no timezone column on `facility`) | No, if any vendor timestamp is local time (vendor B8) |
| HF-31 | Vendor code ↔ HMS code mappings | none (needs the vendor's code lists) | Mapping tables | No, for any status/room-type mapping in scope |
| HF-37 | Room-status vocabulary extension | none recorded | Possible schema/seed change | Yes, if the pilot does not exchange room status |
| HF-38 | Reservation data scope (rates, guarantee, no-show, confirmation numbers) | none recorded | Canonical model / schema | **Register: deferrable for a FIAS guest-event-first pilot** |
| HF-40 | Folio and billing ownership | legacy E1 · E2 · E3. **The texts are not in this repository**: the PO/FIN must supply or confirm them | Posting direction; folio scope | Yes, if the pilot excludes postings |

## 4. Candidates for internal closure: verification result

Each candidate from the blocker-closure report was checked against the canonical register. The
decision authority is always a named role outside engineering, and **no approval evidence
exists**. Engineering can supply recommendations and evidence but cannot close any of these.

| Candidate | Decision authority | Evidence available | Still needed |
|---|---|---|---|
| HF-03 | PO | none (no vendor named anywhere) | PO decision (§2) |
| HF-39 (except the XSD library) | DBA (+ARCH, PO) | DBA package §1–§11, DDL, tests, disposable-DB validation (§11.8) | DBA §10 decision record |
| BLK-D6 allowed values | ARCH, DBA | code evidence and data validation (DBA package §11) | Q8 answer |
| HF-01 | PO, ARCH | options A/B/C (business register) | signed per-entity table |
| HF-21 | LEGAL, SEC | settings exist; values unset | policy with values |
| HF-22 | SEC, OPS | secret is hash-only and shown once (security design) | storage/channel decision |
| HF-23 | SEC, LEGAL | append-only by convention | retention value |
| HF-18 account naming | SEC, ARCH | settings validation requires a UUID | named account approved |
| HF-25 hosting pattern | ARCH, OPS | infrastructure draft (`HTNG_FIAS_INFRASTRUCTURE_SECURITY_READINESS.md`) | OPS/ARCH decision |
| HF-14 / HF-38 deferral | PO (+ARCH/FIN) | register text (HF-38 deferrable) | PO confirmation |

**Result: 0 decisions closed. 0 decisions can be closed without the owner.**

## 5. Approval record format (Phase 5: fill only from supplied evidence)

| ID | Decision text (as approved) | Approver role | Approver name | Evidence reference | Date | Approved scope | Conditions | Implementation impact | Recorded in code? |
|---|---|---|---|---|---|---|---|---|---|
| *(no approvals received as of 2026-11-20)* | | | | | | | | | |

Implementation follows only after a row is complete: map the row to code, write tests, then
make a reviewed change to `domain/approvals.py` that cites the evidence reference.
