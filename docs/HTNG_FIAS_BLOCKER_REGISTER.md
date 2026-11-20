# HTNG / FIAS — Central Blocker Register

Last reviewed for all rows: **2026-11-20**. Stakeholders are roles (no individuals are named in
any project document): PO, ARCH, BA, SEC, OPS, DBA, BE, QA, LEGAL, HOTEL-OPS, VENDOR, PROJECT LEAD.
Nothing here is resolved; "Resolution criteria" defines what evidence closes a row.

## FIAS

| ID | Decision | Description | Status | Stakeholder | Required evidence | Depends on | Impact | Resolution criteria |
|---|---|---|---|---|---|---|---|---|
| BLK-F1 | HF-11 | Official FIAS manual + licensed record set | PENDING VENDOR DOCUMENTATION | VENDOR, PROJECT LEAD | manual (title, version) | BLK-V1 | all FIAS processing blocked | manual received and filed (vendor request B1) |
| BLK-F2 | HF-11 | Record and field definitions | PENDING VENDOR DOCUMENTATION | VENDOR | manual sections | BLK-F1 | parser/serializer cannot be configured | sections referenced in `spec.py` as `VERIFIED_OFFICIAL` |
| BLK-F3 | HF-06 | Framing (markers, escaping, max length) | PENDING VENDOR DOCUMENTATION | VENDOR | manual section | BLK-F1 | no production framer | framing configured + contract tests pass |
| BLK-F4 | HF-06 | Acknowledgement (ACK/NAK) behaviour | PENDING VENDOR DOCUMENTATION | VENDOR | manual section + samples | BLK-F1 | no responder; re-delivery rules unknown | responder implemented + tests |
| BLK-F5 | HF-06 | Heartbeat / link start-up / resync | PENDING VENDOR DOCUMENTATION | VENDOR | manual section | BLK-F1 | idle vs dead links indistinguishable | implemented + tests |
| BLK-F6 | HF-06 | Connection direction, host/port | PENDING VENDOR DOCUMENTATION | VENDOR, OPS | vendor statement | BLK-V1 | client vs listener mode unchosen | role chosen; link config approved |
| BLK-F7 | HF-11 | Official FIAS sample messages (both directions, incl. errors) | PENDING VENDOR DOCUMENTATION | VENDOR | sample files + manifest | BLK-F1 | contract tests cannot run | contract report all passed |

## HTNG

| ID | Decision | Description | Status | Stakeholder | Required evidence | Depends on | Impact | Resolution criteria |
|---|---|---|---|---|---|---|---|---|
| BLK-H1 | HF-07 | WSDL/XSD bundle + supported profile + version | PENDING VENDOR DOCUMENTATION | VENDOR | files + profile statement | BLK-V1 | all HTNG operations blocked | verified `SchemaProfile` registered |
| BLK-H2 | HF-08 | Message security profile (WS-Security, mTLS) | PENDING VENDOR DOCUMENTATION | VENDOR, SEC | security spec | BLK-H1 | endpoint cannot be exposed | implemented + security tests |
| BLK-H3 | HF-39 | Approved XSD-validation library (`xmlschema` or `lxml`) | PENDING DBA APPROVAL | DBA/ARCH (HF-39 covers new dependencies) | approval record | — | `XsdValidator` refuses | library approved + pinned |
| BLK-H4 | HF-07 | Official HTNG samples (both directions, incl. faults) | PENDING VENDOR DOCUMENTATION | VENDOR | sample files | BLK-H1 | contract tests cannot run | contract report all passed |

## Business decisions (definitions verified in `HTNG_FIAS_DECISION_REGISTER.md`)

| ID | Decision | Description | Status | Stakeholder | Required evidence | Impact | Resolution criteria |
|---|---|---|---|---|---|---|---|
| BLK-B1 | HF-01 | PMS/HMS system of record | PENDING BUSINESS APPROVAL | PO, ARCH | signed per-entity table | live writes blocked | approval recorded with evidence in `approvals.py` |
| BLK-B2 | HF-02 | Mapping / entity ownership; external stay reference | PENDING BUSINESS APPROVAL | PO, BA, ARCH | ownership statement | no production resolver | same |
| BLK-B3 | HF-05 | Property-code case sensitivity | PENDING VENDOR DOCUMENTATION | VENDOR, HOTEL-OPS | vendor doc A3 | EXACT matching only | same |
| BLK-B4 | HF-18 | Integration principal / HMS actor | PENDING BUSINESS APPROVAL | SEC, ARCH | account named | live writes impossible | `INTEGRATION_ACTOR_USER_ID` approved |
| BLK-B5 | HF-19 | Facility isolation rules; pilot scope | PENDING BUSINESS APPROVAL | SEC, PO | sign-off + pilot list | activation blocked | approval recorded |
| BLK-B6 | HF-21 | Payload retention, encryption, access; vendor-sample PII handling | PENDING BUSINESS APPROVAL | LEGAL, SEC | policy with values | no purge, no encryption | values configured; encryption decided |
| BLK-B7 | HF-27 | Retry and ordering policy | PENDING BUSINESS APPROVAL | ARCH, BE | per-type policy | defaults in force | configuration approved |

## DBA

| ID | Decision | Description | Status | Stakeholder | Required evidence | Impact | Resolution criteria |
|---|---|---|---|---|---|---|---|
| BLK-D1 | HF-39 | Approve the seven candidate tables | PENDING DBA APPROVAL | DBA, ARCH, PO | `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` §10 signed | no persistence in HMS DB | decision record signed |
| BLK-D2 | HF-39 | Two Alembic heads (`a3f1c8e2d904`, `b3c4d5e6f7a8`) | PENDING DBA APPROVAL | DBA | chosen `down_revision` | migration cannot be attached | merge strategy decided |
| BLK-D3 | HF-39 | Actual live DB revision / DDL of `inspironics_app` | PENDING DBA APPROVAL | DBA | revision + DDL export | unknown starting point | confirmed |
| BLK-D4 | HF-39 | 19 pre-existing HMS MySQL incompatibilities | PENDING DBA APPROVAL | DBA, BE | fix plan | HMS schema not reproducible on MySQL | plan agreed (separate change) |
| BLK-D5 | HF-39 | Upgrade, backup and rollback approval | PENDING DBA APPROVAL | DBA, OPS | window, backup, executor | cannot deploy | §6/§7 answered |

## Vendor

| ID | Description | Status | Stakeholder | Required evidence | Impact | Resolution criteria |
|---|---|---|---|---|---|---|
| BLK-V1 | PMS vendor and product identified (HF-03, HF-04) | PENDING VENDOR DOCUMENTATION | PO | named vendor/product/version | request cannot be sent | vendor named |
| BLK-V2 | Official protocol documents received | PENDING VENDOR DOCUMENTATION | PROJECT LEAD | tracker (vendor package Part E) | BLK-F*, BLK-H* | all Required items received |
| BLK-V3 | Vendor sample messages | PENDING VENDOR DOCUMENTATION | VENDOR | sample files | no contract evidence | contract report passed |
| BLK-V4 | Test credentials | PENDING VENDOR DOCUMENTATION | VENDOR, SEC | credentials via approved channel (HF-22) | no joint testing | received |
| BLK-V5 | Vendor test environment | PENDING VENDOR VALIDATION | VENDOR, OPS | environment access | no interoperability evidence | V-21 executed |
| BLK-V7 | Vendor message volumes (peak / average per property) — external prerequisite for `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE`; **not an HF decision** | PENDING VENDOR DOCUMENTATION | VENDOR, OPS | volume figures (vendor request A2/A4) | rate limit stays off (unset) | volumes received; limit value configured |
| BLK-V6 | Acceptance / certification criteria | PENDING VENDOR DOCUMENTATION | VENDOR, QA | criteria document | no definition of done | V-22 executed and signed |

## Other open items (tracked, outside this list's scope)

HF-22 credential storage (SEC, OPS) · HF-23 audit retention (SEC, LEGAL) · HF-24 network path
and TLS (OPS, SEC, VENDOR) · HF-25/26 process hosting and restart policy (ARCH, OPS) · git
identity for committing (repository owner) · decision on `docs/HTNG-FIAS/` and
`docker-compose.dev.yml` (repository owner).

## Reconciliation with the canonical register (2026-11-20)

`HTNG_FIAS_DECISION_REGISTER.md` is authoritative for decision status. Where this register's
status vocabulary differs, the canonical status governs. **No decision status was changed.**

| Item | This register | Canonical | Reading |
|---|---|---|---|
| BLK-B4 / HF-18 | PENDING BUSINESS APPROVAL | **Open** | No owner decision has been proposed yet; the business decision is still to be made |
| BLK-B6 / HF-21 | PENDING BUSINESS APPROVAL | **Open** | same |
| BLK-B7 / HF-27 | PENDING BUSINESS APPROVAL | **Open** | same |
| BLK-B3 / HF-05 | listed under Business | **Awaiting Vendor Confirmation** | The vendor states the rule (A3) and HOTEL-OPS confirms it. It is grouped with the business decisions only because it is one of the four live-write gate decisions |

Related reconciliations recorded elsewhere:
* vendor sample location (`HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` Part F, stricter rule
  applied);
* HF-08 missing from the code register (`HTNG_FIAS_MASTER_PROJECT_COMPLETION_PLAN.md` §4);
* the infrastructure design (`HTNG_FIAS_INFRASTRUCTURE_SECURITY_READINESS.md`).
