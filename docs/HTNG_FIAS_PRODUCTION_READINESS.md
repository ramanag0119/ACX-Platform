# HTNG / FIAS — Production Readiness Dashboard

Reviewed 2026-11-20 · branch `feature/htng-fias-on-develop` (uncommitted) · overall project
status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. Categories are independent; no
combined percentage is given because readiness in one category does not offset a blocker in
another. "Tested" means automated tests in disposable environments; nothing is verified against
the real HMS database or a real vendor.

| # | Category | Status | Evidence | Blocker | Owner (role) | Next action |
|---|---|---|---|---|---|---|
| 1 | Shared integration foundation | IMPLEMENTED; tested | 406 collected / 405 passed / 1 skipped (round 3); D1–D6 fixed with regression tests | none technical | BE | keep green; commit once git identity exists |
| 2 | FIAS protocol readiness | PENDING VENDOR DOCUMENTATION | spec-driven parser, both TCP roles tested on synthetic grammar; production spec `None` | BLK-F1…F7 (HF-11 content, HF-06 link rules) | VENDOR, PROJECT LEAD | send vendor request (Part B) |
| 3 | HTNG protocol readiness | PENDING VENDOR DOCUMENTATION | safe XML, SOAP 1.1/1.2, registry tested; production registry empty | BLK-H1…H4 (HF-07, HF-08, HF-39 library) | VENDOR, SEC, DBA | send vendor request (Part C); decide XSD library |
| 4 | HMS business integration | PENDING BUSINESS APPROVAL | real `stays_write` check-in/out via worker on seeded disposable MySQL (TEST-ONLY gate); gate closed in code | BLK-B1, B2, B4, B5 (+ B3) | PO, ARCH, SEC | decision owners answer `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` |
| 5 | Database readiness | PENDING DBA APPROVAL | upgrade/downgrade + concurrency on disposable MySQL 8.4; DDL generated from models; 19 pre-existing HMS incompatibilities catalogued | BLK-D1…D5 (HF-39) | DBA | review `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md`, complete §10 |
| 6 | Security readiness | READY FOR REVIEW | auth/isolation/injection/secret-exposure tests; secret scan 0 findings (gitleaks, positive control passed); `.gitignore` coverage OK | HF-08, HF-21 (encryption), HF-22, HF-24; vendor-sample PII handling | SEC, LEGAL | security review of `HTNG_FIAS_SECURITY_DESIGN.md` + scan report |
| 7 | Vendor interoperability | PENDING VENDOR VALIDATION | contract harness + report CLI ready; official run skipped (no samples) | BLK-V1…V7 | VENDOR, QA | identify vendor (BLK-V1); send request |
| 8 | Operational readiness | IMPLEMENTED; tested (not deployed) | health/readiness endpoints, facility health, service process, runbook | HF-25/26 hosting, HF-23 audit retention, monitoring ownership | OPS, ARCH | choose supervision (PM2/systemd) and alert routing |
| 9 | Business approval | PENDING BUSINESS APPROVAL | 7 decisions with questions/options/evidence; none approved | HF-01, 02, 05, 18, 19, 21, 27 | PO, ARCH, SEC, LEGAL, HOTEL-OPS | decision meeting |
| 10 | Deployment readiness | BLOCKED | nothing committed; all switches off; migration outside Alembic path | git identity; categories 2–9 | repository owner, OPS | configure identity, scan staged diff, commit in planned groups |

## Production switches (must stay as they are until the blockers close)

`INTEGRATION_ENABLED=false`, `INTEGRATION_HTNG_INBOUND_ENABLED=false`,
`INTEGRATION_LIVE_DOMAIN_WRITES=false`, `INTEGRATION_STORE_RAW_WIRE_PAYLOAD=false`,
`INTEGRATION_SIMULATOR_ENABLED=false`, FIAS `PRODUCTION_SPECIFICATION=None`, HTNG registry
empty, no decision approved in `approvals.py`, draft migration in `migrations/drafts/`.

Full production integration requires, in order: vendor documents validated (2, 3) → business
decisions approved (4, 9) → DBA approval and migration plan (5) → vendor interoperability
evidence (7) → explicit authorisation of live HMS integration.

## Evidence update (2026-11-20) and go / no-go

The table above is a round-3 snapshot; its test count (406) is historical. Latest evidence, all
synthetic and on disposable environments:

| Evidence | Result | Source |
|---|---|---|
| Integration suite | 517 collected, 516 passed, 1 skipped (vendor samples absent) | `HTNG_FIAS_OBSERVABILITY_IMPLEMENTATION_REPORT.md` |
| Certification harness | 40 PASS, 0 FAIL, 5 BLOCKED (official vendor scenarios) | `HTNG_FIAS_CERTIFICATION_SPRINT_REPORT.md` |
| Frontend | 49/49 tests; build OK; browser visual QA at 4 viewports | `HTNG_FIAS_DASHBOARD_VISUAL_QA_REPORT.md` |
| Full-stack E2E | 90/90 API, 56/56 browser checks; isolation verified; defect BLK-D6 found | `HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` |
| Decisions | 29 pending, 0 approved | `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` |

**Go / no-go for production activation: NO-GO.** Required and missing:
* vendor validation (HF-09, BLK-V5/V6);
* the vendor specifications (HF-06, 07, 08, 11);
* the DBA decision (HF-39, BLK-D6);
* the live-write gate decisions (HF-01, 02, 05, 19) and the actor account (HF-18);
* the security and infrastructure decisions (HF-21, 22, 23, 24, 25, 26);
* a monitoring owner;
* explicit switch authorisation.

The gate list is maintained in `HTNG_FIAS_MASTER_PROJECT_COMPLETION_PLAN.md` §5.
