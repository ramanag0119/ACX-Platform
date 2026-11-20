# HTNG / FIAS — Business Decision Package (approval-ready)

Audience: the decision owners (product owner, architecture, security, legal, hotel
operations). Reviewed 2026-11-20. **No decision is made here and none is approved.**

Definitions and statuses are taken verbatim in meaning from `HTNG_FIAS_DECISION_REGISTER.md`
(this repository). Owner roles and the listed options come from the earlier register
(`../HMS-Frontend/ACX-Platform/docs/HTNG_FIAS_BUSINESS_VENDOR_DECISION_REGISTER.md`, roles only —
no individuals are named in any project document) or from switches that already exist in code.
**Numbering:** IDs follow the canonical register (`HTNG_FIAS_DECISION_REGISTER.md`, reconciled
2026-11-20). The earlier register's HF-05 subject is now canonical HF-11 and its HF-11 subject is
canonical HF-40; FIAS link rules are canonical HF-06.

## Summary

| ID | Subject | Status | Owner (role) | Blocks |
|---|---|---|---|---|
| HF-01 | PMS / HMS system of record | PENDING BUSINESS APPROVAL | PO, ARCH | live HMS writes |
| HF-02 | Mapping / entity ownership (incl. external stay reference) | PENDING BUSINESS APPROVAL | PO, BA, ARCH | production mappings, stay resolver, live writes |
| HF-05 | FIAS property-code case sensitivity | PENDING VENDOR DOCUMENTATION | VENDOR, HOTEL-OPS | verified mapping behaviour, live writes |
| HF-18 | Integration principal / HMS actor | PENDING BUSINESS APPROVAL (Open) | SEC, ARCH | live writes |
| HF-19 | Facility authorization / isolation; pilot scope | PENDING BUSINESS APPROVAL | SEC, PO | production access, live writes |
| HF-21 | Raw-payload retention, encryption, access | PENDING BUSINESS APPROVAL (Open) | LEGAL, SEC | payload retention, purge, vendor-sample handling |
| HF-27 | Retry and ordering policy | PENDING BUSINESS APPROVAL (Open) | ARCH, BE | final production policy |

## HF-01 — System of record

* **Question:** For reservations, guests, check-in/out and room status, is the PMS or HMS the
  system of record — per entity and per property?
* **Technical impact:** decides message direction for every entity and whether HMS accepts PMS
  stay changes as authoritative.
* **Operational consequence while open:** integration can only be tested; no PMS event changes HMS data.
* **Evidence required:** signed decision per entity (table), by PO and ARCH.
* **Options (earlier register):** A HMS acts as the PMS-side host · B HMS is a subsystem receiving PMS events · C both, per property.
* **Dependent work:** enabling `stay.check_in/check_out` live; any reservation/guest/room-status flow (R-17, R-18).

## HF-02 — Mapping and entity ownership

* **Question:** Who maintains PMS-property → HMS-facility mappings, and is
  `stay.external_stay_ref_number` the PMS reservation/confirmation number, unique per facility?
* **Technical impact:** production stay resolver; mapping data stewardship.
* **Consequence while open:** no production resolver is registered; mappings exist only through the audited API in test.
* **Evidence:** ownership statement per entity; confirmation of the reference field.
* **Options (earlier register):** per entity owner: HMS · PMS · OSS · vendor.
* **Dependent work:** production `ExternalReferenceResolver`; mapping onboarding procedure.

## HF-05 — Property-code case sensitivity

* **Question:** Are the vendor's property codes case-sensitive? If not, which canonical case is stored?
* **Technical impact:** normalisation of codes and the unique key in `integration_facility_mappings`.
* **Consequence while open:** codes are compared exactly (binary collation) — safe, may reject a differently-cased code.
* **Evidence:** vendor documentation (A3) confirmed by HOTEL-OPS.
* **Options (implemented switch):** `CaseSensitivity.EXACT` (current) · `CaseSensitivity.INSENSITIVE` (requires re-normalising stored mappings).
* **Dependent work:** none beyond configuration.

## HF-18 — Integration principal / HMS actor

* **Question:** Which HMS user or dedicated service account is recorded as `created_by` / `modified_by` for PMS-originated changes?
* **Technical impact:** `INTEGRATION_ACTOR_USER_ID`; settings validation refuses live writes without it.
* **Consequence while open:** live writes impossible.
* **Evidence:** SEC approval naming the account and its permissions.
* **Options (earlier register):** one principal per interface and per property · one per vendor · shared system user (earlier register: not recommended).
* **Dependent work:** account provisioning; audit review.

## HF-19 — Facility authorization and pilot scope

* **Question:** Is every integration client bound to a fixed set of properties, and is the pilot single- or multi-property?
* **Technical impact:** already enforced in code (client-scoped mappings, scope-smuggling rejection, operator scoping).
* **Consequence while open:** behaviour is the strict default; activation not allowed.
* **Evidence:** SEC/PO sign-off of the isolation rules and the pilot property list.
* **Options (earlier register):** mandatory facility scope on all integration paths now · single-property pilot first.
* **Dependent work:** none in code; pilot configuration.

## HF-21 — Payload retention, encryption, access

* **Question:** How many days are processed messages kept (this is also the duplicate-protection window)? Must payloads be encrypted at rest? Who may view them? May vendor samples containing guest data be committed?
* **Technical impact:** `INTEGRATION_RETENTION_DAYS`; `INTEGRATION_STORE_RAW_WIRE_PAYLOAD`; encryption not implemented.
* **Consequence while open:** no purge; raw bytes not stored; payloads unencrypted in the candidate table.
* **Evidence:** LEGAL/SEC policy with values.
* **Options (earlier register, values for LEGAL to set):** raw payload N days, metadata M months.
* **Dependent work:** set retention; implement encryption at rest if required; vendor-sample handling (`HTNG_FIAS_SECRET_SCAN_REPORT.md` §3).

## HF-27 — Retry and ordering

* **Question:** Per message type: retry count and back-off; should a dead-lettered event block later events for the same stay?
* **Technical impact:** `RetryPolicy` settings; `dead_letter_blocks_ordering` switch.
* **Current defaults (implemented, not approved):** 5 attempts, 5 s → 900 s; per-stay ordering; dead-lettered predecessor blocks until redrive.
* **Evidence:** ARCH/BE decision, informed by vendor re-delivery rules (B4/C6).
* **Options (earlier register):** per-message-type policy; strict per-room/per-stay ordering.
* **Dependent work:** configuration only.

## Gate in code (unchanged)

Live HMS writes need `INTEGRATION_LIVE_DOMAIN_WRITES=true`, `INTEGRATION_ACTOR_USER_ID`, and
HF-01, HF-02, HF-05, HF-19 recorded as Approved **with evidence** in
`backend/app/integrations/domain/approvals.py` — a reviewed code change after sign-off.
