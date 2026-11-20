# HTNG / FIAS — External Approval Communications (drafts)

**Status of every draft: NOT SENT.** Nothing in this file has been emailed, submitted or shared
by the project tooling. Bracketed fields are placeholders for the sender: no names, addresses or
vendor identities are known to the project documents. IDs follow
`HTNG_FIAS_DECISION_REGISTER.md`; the action details are in
`HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md`.

Use this paragraph in every message:

> **Status:** the HTNG and FIAS integration foundation is implemented and internally verified
> on disposable environments with synthetic data: automated tests, a certification harness, an
> observability dashboard and an isolated full-stack end-to-end run. It has **not** been
> validated with any vendor, is **not** connected to the production HMS database, and is
> **not** production-ready. Official status: FOUNDATION IMPLEMENTED — VENDOR VALIDATION
> PENDING.

---

## 1. Vendor technical specification request

**Prerequisite before sending:** HF-03 answered (vendor, product, version and properties named
by PO). Sender: PROJECT LEAD.

> **Subject:** Interface documentation request — [PMS product, version] ↔ HMS ([property list])
>
> Hello [vendor contact],
>
> **Purpose.** We are preparing the interface between [PMS product, version] and our Hotel
> Management System for [property list]. We implement only behaviour stated in your official
> documents, so we need the material below before development continues and before joint
> testing.
>
> [Status paragraph]
>
> **What we need from you** (the attached request package lists every item):
> 1. Product, version and hosting (A1); interfaces offered — FIAS, HTNG, other — and the
>    versions (A2); events and operations per direction (A4); system-of-record expectations (A5).
> 2. Property codes in scope and whether they are case-sensitive (A3).
> 3. *If FIAS:* the official interface manual and version, and the licensed record set (B1);
>    record and field definitions (B2); framing (B3); ACK/NAK behaviour (B4); start-up,
>    sequence and resynchronisation (B5); heartbeat (B6); connection direction and host/port
>    (B7); character set and date/time formats (B8); the event-identity field (B9); extensions
>    (B11).
> 4. *If HTNG:* the specification release and your implementation profile (C1); WSDL and the
>    complete XSD bundle (C2); operations per direction (C3); SOAP version and SOAPAction (C4);
>    message security — WS-Security, mTLS, certificates (C5); fault semantics (C6);
>    acknowledgement semantics (C7); versioning policy (C9).
> 5. Official sample messages for every record or operation in scope, **in both directions**,
>    including acknowledgements and error/fault cases (B10 / C8). Please state for each sample
>    whether it is vendor-synthetic, anonymised or contains real guest data. We cannot accept
>    real guest data until our retention policy is approved.
> 6. Network path, IP ranges and TLS (B12 / C10).
> 7. Expected message volumes: peak and average per property.
> 8. Test environment, test property and credentials process (A6); certification and
>    acceptance criteria (A7); support and escalation contacts (A8).
>
> **Response format.** For each item: document title, version and section reference, or
> "not applicable". Please send documents and samples to [project lead contact]. Do **not**
> send credentials by email; we will propose a channel.
>
> **Dependencies on our side.** Our network design and credential channel are being finalised
> in parallel. Joint testing starts after both are agreed.
>
> Kind regards, [name, role]

**Attachments:** `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` (Parts A–C), with Part E pre-filled with
the vendor name and the date sent. Internal parts D and F are **not** attached.

---

## 2. DBA schema and migration approval request (HF-39)

> **Subject:** HF-39 — approval request: 7 integration tables, Alembic attachment, schema-integrity constraint
>
> Hello [DBA team],
>
> **Purpose.** We request a DBA decision on the HTNG/FIAS integration persistence. Nothing has
> been applied to `inspironics_app`: all evidence comes from disposable MySQL 8.4 environments.
>
> [Status paragraph]
>
> **Decisions requested** (DBA package §7, Q1–Q8):
> 1. Q1 Approve the seven tables, types, collations and FK actions (Appendix A)?
> 2. Q2 `down_revision`: merge `a3f1c8e2d904` + `b3c4d5e6f7a8` first, or make this revision
>    the merge?
> 3. Q3 The live database's actual revision and DDL.
> 4. Q4 A fix plan for the 19 pre-existing HMS/MySQL incompatibilities (a separate change).
> 5. Q5 `create_all(checkfirst)` or explicit `op.create_table` / `op.create_index`.
> 6. Q6 Backup method, maintenance window and executor; the rollback is a downgrade that drops
>    only the seven tables.
> 7. Q7 XSD-validation library (`xmlschema` / `lxml` / none), only if HTNG proceeds.
> 8. **Q8 (new).** The full-stack test found that one inbound row with an invalid `direction`
>    is still counted in the overview but makes message search and DLQ return HTTP 500,
>    because the column has no CHECK. Please choose:
>    * Option A: `direction IN ('inbound','outbound')`;
>    * Option B: `direction = 'inbound'`.
>
>    Also choose the allowed `protocol` values for the inbound and outbox tables (the enum
>    contains `fias`, `htng`, `test`), and whether the validation queries in §11.4 must run in
>    any existing environment.
>
> **Response format.** Complete the decision record (package §10): approved / approved with
> changes / rejected; required changes; `down_revision`; live revision confirmed; backup,
> window and executor; XSD library; Q8 choices; name, date, reference.
>
> **Dependencies.** The XSD library depends on the protocol decision (HF-04). An application
> change for tolerant mapping (§11.6) would follow separately and needs BE/ARCH approval.
>
> Kind regards, [name, role]

**Attachments:**
* `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` (incl. §11);
* `HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`;
* `HTNG_FIAS_DATABASE_DESIGN.md`;
* `HTNG_FIAS_MIGRATION_READINESS.md`;
* `HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` §5–§6 (defect evidence).

---

## 3. Business decision confirmation request

> **Subject:** HTNG/FIAS — business decisions needed before any live HMS update
>
> Hello [PO, ARCH, SEC, LEGAL, HOTEL-OPS, FIN — per item],
>
> **Purpose.** The integration cannot change HMS data until the decisions below are confirmed.
> Each item in the attached package has its question, impact, the options already documented,
> and the evidence required. No option has been pre-selected.
>
> [Status paragraph]
>
> **Decisions requested**
>
> | ID | Question | Owner |
> |---|---|---|
> | HF-03 | Which PMS vendor, product, version and properties for the pilot? *(gates every vendor request)* | PO |
> | HF-01 | System of record per entity and property (options A / B / C) | PO, ARCH |
> | HF-02 | Mapping and entity ownership; is `external_stay_ref_number` the PMS reservation number? | PO, BA, ARCH |
> | HF-05 | Property-code case rule (confirmation of the vendor answer) | HOTEL-OPS (with VENDOR) |
> | HF-18 | Which account is recorded for PMS-originated writes | SEC, ARCH |
> | HF-19 | Facility isolation rules; single- or multi-property pilot; pilot list | SEC, PO |
> | HF-21 | Retention days, encryption at rest, payload access, guest data in vendor samples | LEGAL, SEC |
> | HF-27 | Retry and ordering policy per message type (after the vendor's re-delivery rules) | ARCH, BE |
> | HF-14, 20, 30, 31, 37, 38, 40 | Confirm, or confirm deferral for the pilot (HF-38 is recorded as deferrable for a FIAS guest-event-first pilot) | as listed in the register |
>
> **Response format.** Per item: decision (or "deferred"), approver role, date, evidence
> reference (a signed table, policy document or meeting minute). Approved items are recorded
> in code only by a reviewed change that cites that reference.
>
> **Dependencies.** HF-02 follows HF-01. HF-27 needs the vendor's re-delivery rules. HF-19 and
> HF-30 need the HF-03 property list.
>
> **Please also clarify:** the registers disagree on the status of HF-18, HF-21 and HF-27
> ("Open" vs "Pending business approval"). Which applies?
>
> Kind regards, [name, role]

**Attachments:**
* `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md`;
* `HTNG_FIAS_DECISION_REGISTER.md`;
* `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` §1.2 and §3.

---

## 4. Infrastructure and security decision request

> **Subject:** HTNG/FIAS — hosting, network, credential and data-protection decisions
>
> Hello [OPS, ARCH, SEC, LEGAL],
>
> **Purpose.** Before any vendor connectivity or non-production deployment, we need these
> decisions. Each is open in the canonical register.
>
> [Status paragraph]
>
> **Decisions requested**
> 1. **HF-25:** where the integration service process (workers, outbox relay, FIAS link) runs,
>    and its supervision (the runbook names PM2 or systemd as candidates).
> 2. **HF-26:** restart policy, and the rule that a FIAS link has a single owner process.
> 3. **HF-24:** network path for the vendor (VPN, IP ranges, which side listens) and TLS
>    termination; completed with the vendor's B12 / C10 answers.
> 4. **HF-22:** where integration client secrets are stored, and the channel for delivering
>    them to the vendor (secrets are shown once and stored hashed).
> 5. **HF-08** (with the vendor): HTNG message security and certificate handling.
> 6. **HF-21:** payload retention, encryption at rest, and payload access (with LEGAL).
> 7. **HF-23:** audit-log retention and immutability (with LEGAL).
> 8. **HF-20:** guest PII scope (LEGAL-owned; for awareness).
> 9. **Ownership:** who owns monitoring and alert routing, and the runbook procedures (DLQ
>    redrive, credential rotation, link troubleshooting, retention purge). The project
>    documents record **no** owner for these.
> 10. **Database TLS:** the backend requires TLS to MySQL with certificate verification by
>     default. Confirm how the CA is provided for the target database.
>
> **Response format.** Per item: decision, approver role, date, reference. Network and hosting
> as a short design note.
>
> **Dependencies.** HF-24 and the HF-25 placement depend on the vendor's link rules (HF-06,
> which side listens). HF-22 must be decided before vendor test credentials are issued.
>
> Kind regards, [name, role]

**Attachments:**
* `HTNG_FIAS_SECURITY_DESIGN.md`;
* `HTNG_FIAS_OPERATIONS_RUNBOOK.md`;
* `HTNG_FIAS_SECRET_SCAN_REPORT.md`;
* `HTNG_FIAS_PRODUCTION_READINESS.md`;
* `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` §1.4, §1.5, §6.D.

---

## 0. HF-03 decision request (send first — added 2026-11-20)

> **Subject:** HF-03 — please confirm the target PMS for the HTNG/FIAS pilot
>
> Hello [Product Owner],
>
> **Purpose.** Every vendor request and vendor-owned decision (HF-04 … HF-09, HF-24, HF-31,
> BLK-V7) is waiting for one answer: which PMS the pilot integrates with. The project documents
> do not name a vendor, product or property, and we will not assume one.
>
> [Status paragraph]
>
> **Decision requested (HF-03, currently Open).** Per pilot property:
> * property name / HMS `facility_uid`;
> * PMS vendor, product and version;
> * hosting (on-premise or cloud);
> * the interface the vendor offers, if known (FIAS / HTNG / other);
> * the vendor's technical contact (a role is enough).
>
> **Please also confirm:**
> * that HF-03 is owned by PO (this ownership was imported from the older register and its
>   provenance is unconfirmed);
> * who owns monitoring and alert routing (currently unrecorded).
>
> **Response format.** A short decision note with your name or role, the date and a reference,
> so it can be recorded in `HTNG_FIAS_OWNER_DECISION_TRACKER.md` §5.
>
> **What it unblocks.** Dispatch of the vendor request (draft 1) and the property list needed
> for HF-19 and HF-30.
>
> Kind regards, [name, role]

**Attachments:**
* `HTNG_FIAS_OWNER_DECISION_TRACKER.md` §2;
* `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` §3.
