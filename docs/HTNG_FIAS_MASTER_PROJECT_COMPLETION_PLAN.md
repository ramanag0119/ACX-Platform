# HTNG / FIAS — Master Project Completion Plan

**Overall status: FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING** (updated 2026-11-20).
This is the single execution view. Details live in the documents in §8. This plan does not
duplicate them.

## 1. Definition-of-done stages

| Stage | State | Evidence |
|---|---|---|
| Foundation complete | **Achieved** (synthetic, disposable environments) | integration suite 517/516/1-skip; certification 40 PASS / 5 BLOCKED; frontend 49/49; visual QA; full-stack E2E 90 + 56 checks |
| Decision closure | **Not started externally**: 29 pending, 0 approved, 0 owners named | `HTNG_FIAS_OWNER_DECISION_TRACKER.md` |
| Approved implementation | **Waiting**: nothing approved to implement | tracker §5 (empty) |
| Vendor validation | **Blocked**: no vendor identified (HF-03) | `HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` |
| Production readiness | **NO-GO** | `HTNG_FIAS_PRODUCTION_READINESS.md` (evidence update) |

## 2. Workstreams

| WS | Scope | Status | Next action | Owner (role) | Gate to proceed |
|---|---|---|---|---|---|
| A Decisions and ownership | 29 items; ownership; reconciliation | Packages ready; reconciliation done (§3) | PO answers HF-03, names people per role, confirms the 12 legacy owners and the PLAT/LOCK-VENDOR/FIN/monitoring roles | PO | tracker §1 confirmed |
| B Vendor readiness | Request package A–C, tracker E | Ready; **not sent** | Send draft 1 after HF-03 | PROJECT LEAD | HF-03 answered |
| C DBA / schema | HF-39, BLK-D1–D6 | Package ready incl. §11 + §11.8 data validation | DBA completes §10 and Q1–Q8 | DBA, ARCH, PO | §10 signed |
| D Business | HF-01, 02, 05, 14, 18, 19, 20, 21, 27, 30, 31, 37, 38, 40 | Papers ready (business register + tracker §3) | Decision meeting (draft 3) | PO, ARCH, SEC, LEGAL, HOTEL-OPS, FIN | approval records in tracker §5 |
| E Infrastructure / security | HF-20–26, monitoring | Draft design created | OPS/ARCH/SEC decide (draft 4) | OPS, ARCH, SEC, LEGAL | decisions recorded |
| F Approved implementation | Only approved scope | **Idle**: nothing approved | — | BE | a complete tracker §5 row |
| G Vendor validation | Spec-compliant FIAS/HTNG, vendor tests | **Blocked** | — | BE, QA, VENDOR | official documents + test environment + HF-09 |
| H Production readiness | Go/no-go | **NO-GO** | — | PO, OPS, SEC, DBA | §5 gates |

## 3. Reconciliation performed in this execution (documentation only)

| Discrepancy | Outcome |
|---|---|
| HF-18 / 21 / 27 "Open" vs "pending business approval" | Canonical status governs; recorded in the blocker register. **No status changed** |
| HF-05 vendor status in the business section | Explained in the blocker register (vendor states the rule, HOTEL-OPS confirms; it is one of the live-write gate decisions) |
| HF-08 absent from the code register | Analysed; correction proposed in §4, **not implemented** |
| Vendor samples in the repository vs outside | **Stricter rule applied** in vendor package Part F |
| No infrastructure design | `HTNG_FIAS_INFRASTRUCTURE_SECURITY_READINESS.md` (draft; decides nothing) |
| HF-40 options / HF-30 dependency only in the other copy | Not copied (that copy is read-only); requested from PO/FIN (tracker §3) |
| Stale test counts in production readiness | Evidence update appended |

## 4. HF-08 code-register discrepancy (proposed correction; needs approval)

* **Fact.** `backend/app/integrations/domain/approvals.py` `DECISIONS` contains HF-01, 02, 05,
  06, 07, 11, 18, 19, 21, 39. `observability.py` `VENDOR_DECISIONS["htng"]` requires
  **HF-07 and HF-08**. `pending()` treats a missing ID as pending.
* **Impact today: none harmful.** HTNG vendor validation is reported "pending", which is
  correct now. The dashboard can only *under*-report readiness.
* **Impact later.** Once HF-08 is genuinely approved, HTNG would stay "pending" until HF-08 is
  added in code. No other gate references an ID missing from the code register.
* **Proposed change**, for BE/ARCH approval, as a separate reviewed change with a test:

  ```python
  Decision("HF-08", "HTNG security profile", DecisionStatus.AWAITING_VENDOR)
  ```

  This adds the row with its canonical status and no approval. Optional: a consistency test that
  every ID used by `observability.py` exists in `DECISIONS`.
* **Not implemented:** the code change has no approval yet.

## 5. Approval gates (in order) and conditions for final completion

| # | Gate | Requires |
|---|---|---|
| G1 | Vendor engagement | HF-03 answered → draft 1 sent → Part E tracker started |
| G2 | Protocol specification | HF-04; FIAS: HF-11 + HF-06 documents; HTNG: HF-07 + HF-08 (+ XSD library under HF-39) |
| G3 | Persistence | HF-39 §10 signed incl. BLK-D6 (Q8); migration applied by the DBA in the target environment |
| G4 | Live HMS writes | HF-01, 02, 05, 19 Approved with evidence in `approvals.py`; HF-18 account configured |
| G5 | Security / infrastructure | HF-20, 21, 22, 23, 24, 25, 26 decided; monitoring owner named; security review signed |
| G6 | Vendor validation | HF-09 environment + credentials (via the HF-22 channel); V-21/V-22 executed; vendor acceptance evidence |
| G7 | Production activation | G1–G6 + deployment and rollback approved + explicit switch authorisation |

**Final completion** = G1–G7 satisfied. Only then may the status change from FOUNDATION
IMPLEMENTED — VENDOR VALIDATION PENDING.

## 6. Milestones

| Done | Pending |
|---|---|
| Foundation, certification harness, observability API, dashboard, visual QA, full-stack E2E, blocker register, communications, DBA §11, ownership tracker, infrastructure draft, document reconciliation | HF-03 → vendor request → vendor documents → spec-compliant implementation → vendor validation; DBA approval; business, security and infrastructure decisions; named owners; production go/no-go |

## 7. Next actionable task

**The PO answers HF-03** using `HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md` draft 0:
* the PMS vendor, product, version, hosting and vendor contact role for each pilot property;
* confirmation of PO ownership of HF-03;
* who owns monitoring.

Nothing vendor-related can move until this is answered.

In parallel, without waiting for HF-03:
* the DBA can complete HF-39 §10;
* LEGAL/SEC can set the HF-21 values.

## 8. Document map (one owner per kind of information)

| Information | Maintained in |
|---|---|
| Decision meanings and status | `HTNG_FIAS_DECISION_REGISTER.md` (canonical) |
| Actions, dependencies, priorities | `HTNG_FIAS_EXTERNAL_BLOCKER_ACTION_REGISTER.md` |
| Ownership confirmation, HF-03 package, approval records | `HTNG_FIAS_OWNER_DECISION_TRACKER.md` |
| Business decision papers | `HTNG_FIAS_BUSINESS_DECISION_REGISTER.md` + tracker §3 |
| Vendor request and tracker | `HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` |
| Vendor validation tests | `HTNG_FIAS_VENDOR_VALIDATION_TEST_PLAN.md` (existing; no new plan created) |
| DBA / BLK-D6 | `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` |
| Infrastructure / security | `HTNG_FIAS_INFRASTRUCTURE_SECURITY_READINESS.md`, `HTNG_FIAS_SECURITY_DESIGN.md`, `HTNG_FIAS_OPERATIONS_RUNBOOK.md` |
| Communications (not sent) | `HTNG_FIAS_EXTERNAL_APPROVAL_COMMUNICATIONS.md` |
| Production go/no-go | `HTNG_FIAS_PRODUCTION_READINESS.md` (evidence update) |
