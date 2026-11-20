# HTNG / FIAS — External Blocker Closure Readiness Report (2026-11-20)

Project status (unchanged): **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING**. No vendor
certification and no production readiness is claimed. No decision is approved.

## 1. Repository and Git state

| Item | Value |
|---|---|
| Repository / branch | `ACX_PLATFORM\ACX-Platform`, `feature/htng-fias-on-develop` (verified; not switched) |
| HEAD | `46904fd` (unchanged) |
| Working tree at start | 53 status entries: 2 tracked modifications (`backend/app/api/v1/router.py`, `backend/tests/test_health_api.py`) plus untracked integration work and docs. Nothing staged |
| Working tree at end | The same entries, plus 3 new untracked documents (§11). The modified `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` was already untracked, so its line in the status is unchanged. Nothing staged, committed or pushed |
| Not touched | `HMS-Frontend\ACX-Platform`; `docker-compose.dev.yml` (checksum unchanged); application code, schema, migrations, configuration |

## 2. Documents reviewed

| Document | Used for |
|---|---|
| `HTNG_FIAS_DECISION_REGISTER.md` (canonical) | all 28 decision IDs, status, owners |
| `HTNG_FIAS_BLOCKER_REGISTER.md` | BLK-F/H/B/D/V rows, BLK-V7 |
| `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` | questions and documented options |
| `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` | items A1–A8, B1–B12, C1–C10; tracker (status NOT SENT) |
| `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | HF-39 Q1–Q7, §10 decision record |
| `HTNG_FIAS_PRODUCTION_READINESS.md` | category blockers, switch list |
| `HTNG_FIAS_SECURITY_DESIGN.md` | security gaps (HF-08, 21, 22, 23, 24) |
| `HTNG_FIAS_OPERATIONS_RUNBOOK.md` | hosting and supervision (HF-25/26) |
| `HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` | invalid-`direction` defect |
| Code, read-only, to verify facts | `core/envelope.py`, `processing/sql_models.py`, `sql_repository.py`, `exchange/gateway.py`, `domain/approvals.py`, `config.py`, `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql` |

**Missing** (reported, not fabricated):
* a dedicated infrastructure/deployment design document;
* any named-person ownership (RACI);
* the legacy register, which exists only in the sibling copy with provenance unconfirmed. It is
  the only record of the HF-40 options E1–E3 and the HF-30 dependency.

## 3. Decisions audited

**28 HF decision IDs** (HF-25 and HF-26 share one canonical row) **plus BLK-V7** (not an HF
decision) = **29 pending items. None is approved.**

| Canonical status | Count | IDs |
|---|---|---|
| Awaiting Business Approval | 7 | HF-01, 02, 19, 20, 30, 31, 40 |
| Awaiting Vendor Confirmation | 9 | HF-04, 05, 06, 07, 08, 09, 11, 15, 24 |
| Open | 11 | HF-03, 14, 18, 21, 22, 23, 25, 26, 27, 37, 38 |
| Awaiting DBA Approval | 1 | HF-39 |
| Pending vendor documentation (blocker register) | 1 | BLK-V7 |

| Primary category (this audit) | Count | IDs |
|---|---|---|
| Vendor | 9 | HF-04, 05, 06, 07, 08, 09, 11, 15, BLK-V7 |
| Business | 14 | HF-01, 02, 03, 14, 18, 19, 20, 21, 27, 30, 31, 37, 38, 40 |
| DBA | 1 (+ new sub-item BLK-D6) | HF-39 |
| Infrastructure | 3 | HF-24, 25, 26 |
| Security | 2 | HF-22, 23 (SEC is also co-owner of HF-08, 18, 19, 20, 21, 24) |

**Ownership**
* **Owner roles recorded:** all 29 items. **Named persons:** none (unassigned everywhere).
* **Owners from this repository's own decisions:** 16 (HF-01, 02, 05, 07, 08, 11, 18, 19, 21,
  22, 23, 24, 25, 26, 27, 39), plus BLK-V7.
* **Owners pending provenance confirmation:** 12 legacy-imported rows (HF-03, 04, 06, 09, 14,
  15, 20, 30, 31, 37, 38, 40).
* **Undefined roles:** PLAT, LOCK-VENDOR, FIN.
* **No owner recorded:** monitoring and alert routing.

## 4. Blocker register summary

`HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` gives every item its category, status (verbatim),
responsible role, exact decision, evidence, dependency, impact, next action and closure evidence.
It also provides:
* priority classes (P0: HF-03, HF-04, HF-39);
* the dependency chain;
* items that can be closed independently;
* items needing joint approval;
* items that must remain blocked;
* six documented inconsistencies (§5 there), which are preserved rather than corrected.

## 5. Owner-specific action packages

In the action register §6:

| Package | Contents |
|---|---|
| **A. Vendor** | Vendor package items A–C mapped to HF-04/05/06/07/08/09/11 and BLK-V7; samples with manifest and PII status; response format per Part E |
| **B. DBA** | Q1–Q7 plus the new Q8 / §11 |
| **C. Business** | The seven decisions of the business register, plus HF-03 and the confirm/defer list |
| **D. Infrastructure / security** | HF-25/26/24, HF-22, HF-08, HF-21/23/20, recovery and monitoring ownership, database TLS CA |

## 6. Communication drafts prepared (not sent)

`HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md`:
1. vendor specification request (send only after HF-03);
2. DBA approval request (HF-39, Q1–Q8);
3. business decision confirmation;
4. infrastructure and security request.

Each has its purpose, decisions, attachments, response format, dependencies, and the
completed-versus-pending status paragraph. **Nothing was sent or submitted.**

## 7. HF-39 invalid-`direction` defect review

Added to `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` as **§11 (BLK-D6, proposed)**. Appended only; the
original 267 lines are byte-identical.

| Topic | Summary |
|---|---|
| Observed | The invalid row is counted in the overview (16 → 17) but message search and DLQ return 500 (E2E checks R6, R7) |
| Reproduction | A direct insert into the disposable E2E database (`direction='sideways'`), deleted afterwards |
| Root cause (verified in code) | No CHECK on `direction` (model and candidate DDL); `_to_stored` raises on unknown values; aggregates do not parse `direction` |
| Allowed values (not assumed) | Enum `inbound` / `outbound`; the only writer path stores `inbound`. **Option A or B is a DBA/ARCH choice** |
| Related | `protocol` on the inbound and outbox tables is also unconstrained; the enum includes `test` |
| Validation | Read-only queries before any CHECK. The target database has no such tables yet |
| Remediation | Export first; correct, quarantine or purge with sign-off; check FK effects |
| Application | Tolerant mapping recommended. **Possible worker stall** from a bad claimable row: this comes from reading the code and was **not reproduced** |
| Approvals | ARCH/DBA (values), DBA (DDL, §10), DBA/OPS (validation), BE/ARCH (code), DBA/PO (migration) |

**Not implemented:** no constraint, no code change, no migration.

## 8. Critical dependency chain (summary)

1. **HF-03** (PO names the vendor) → vendor request sent → **HF-04** protocol.
2. If FIAS: **HF-11** → **HF-06**. If HTNG: **HF-07** → **HF-08** (+ HF-39 XSD library).
3. **HF-22** + **HF-24** → **HF-09** test environment → vendor validation.
4. In parallel:
   * **HF-39** (+ BLK-D6) → persistence;
   * **HF-01** → **HF-02**, together with **HF-05** and **HF-19**, then **HF-18** → live writes;
   * **HF-25** → **HF-26** → supervised service.

## 9. Missing information and unassigned ownership

* **No named owner for any item.**
* **VENDOR has no counterpart** until HF-03 is answered.
* **Undefined roles:** PLAT, LOCK-VENDOR, FIN.
* **Monitoring ownership** unrecorded.
* **12 owner assignments pending provenance confirmation.**
* **Status conflicts to clarify:** HF-18, 21, 27 (Open vs pending business approval); HF-05
  category; HF-08 absent from `approvals.py`.
* **Vendor-sample location conflict:** vendor package Part F vs the certification runbook.
* **Missing infrastructure design document.**

## 10. Exact next actions (all by humans; none performed here)

| # | Action | Owner |
|---|---|---|
| 1 | Answer **HF-03** (vendor, product, version, properties) | PO |
| 2 | Review draft 1; fill the placeholders; send with the vendor package; record "sent" in Part E | PROJECT LEAD |
| 3 | Review the DBA package incl. §11; complete §10 and Q1–Q8 | DBA, ARCH, PO |
| 4 | Hold a decision meeting for HF-01, 02, 18, 19 (and HF-21, 27); confirm or defer HF-14, 20, 30, 31, 37, 38, 40; clarify the status conflicts | PO, ARCH, SEC, LEGAL, HOTEL-OPS, FIN |
| 5 | Decide HF-22 and HF-25/26; draft the internal side of HF-24; assign monitoring ownership | SEC, OPS, ARCH |
| 6 | Name a person per role (RACI); confirm the legacy-row provenance; define PLAT, LOCK-VENDOR, FIN | PO / repository owner |
| 7 | Resolve the vendor-sample location conflict before any sample arrives | PROJECT LEAD, SEC |
| 8 | After approvals: record each decision in `approvals.py` with its evidence (reviewed commit); BE implements the BLK-D6 defensive mapping if approved | BE, reviewers |

### What evidence is required before vendor validation

* HF-03 and HF-04 answered.
* Official documents filed with references:
  * FIAS: B1–B11 (HF-11, HF-06);
  * HTNG: C1–C9 (HF-07, HF-08).
* Vendor samples with manifest and PII status; the contract report passing.
* HF-05 statement.
* HF-22 channel, HF-24 network design, HF-09 environment and credentials.
* HF-21 rules for samples.
* An approved XSD library if HTNG.

### What evidence is required before production readiness

* All of the above, plus vendor validation executed and signed (BLK-V5/V6; plan items V-21,
  V-22).
* HF-39 decision record signed and the migration applied by the DBA.
* HF-01, 02, 05, 19 Approved with evidence in `approvals.py`; HF-18 account configured.
* HF-21, 23, 25, 26, 27 decided and configured.
* Monitoring ownership assigned.
* Git identity configured and the work committed through review.
* Explicit authorisation to enable the production switches.

### Status by stage

| Stage | Items |
|---|---|
| Implemented | Shared foundation, FIAS/HTNG adapter frameworks (blocked on specs), observability API, dashboard, certification harness |
| Internally verified | 517-test integration suite; 45 certification scenarios (40 PASS, 5 official-vendor scenarios BLOCKED); 49 frontend tests; browser visual QA; isolated full-stack E2E (90 API + 56 browser checks) — all synthetic and disposable |
| Awaiting approval | HF-01, 02, 18, 19, 20, 21, 22, 23, 25, 26, 27, 30, 31, 37, 38, 39, 40, 14, 03 (+ BLK-D6) |
| Awaiting vendor documentation | HF-04, 05, 06, 07, 08, 11, 15, 24 (vendor part), BLK-V7 |
| Awaiting vendor testing | HF-09; BLK-V5, BLK-V6 |
| Not production-ready | the whole integration |

## 11. Files created or modified

| File | Change |
|---|---|
| `docs/HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` | **created** |
| `docs/HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md` | **created** |
| `docs/HTNG_FIAS_EXTERNAL_BLOCKER_CLOSURE_READINESS_REPORT.md` | **created** (this file) |
| `docs/HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | **appended** §11 (BLK-D6); lines 1–267 unchanged; pre-change copy in the session scratchpad |
| `docs/HTNG_FIAS_DECISION_REGISTER.md`, `HTNG_FIAS_BLOCKER_REGISTER.md`, all others | **not modified** |

## 12. Confirmation

* **Not changed:** application code, tests, database schema, migrations, configuration,
  `approvals.py` and approval statuses.
* **Not done:** no migration was run, no database was accessed (live or disposable), no vendor
  was contacted and no traffic was sent, no switch was enabled, nothing was sent or submitted.
* **Git:** nothing staged, committed or pushed; no branch switched; Git history unchanged.
* **Credentials and PII:** no credentials or guest data appear in any created document.
