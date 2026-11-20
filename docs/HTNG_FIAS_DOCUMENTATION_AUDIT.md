# HTNG / FIAS — Documentation Audit (round 4, 2026-11-20)

Method: each statement checked against source code, git state and the latest executed test
evidence (round 3: integration 406 collected / 405 passed / 1 skipped; legacy on seeded
disposable DB 1,250 / 78 / 1, identical to pristine). Historical sections are kept; only
statements that are wrong *as current statements* were corrected.

## 1. Verified facts (re-checked this round)

| Fact | Check | Result |
|---|---|---|
| Branch / other branches untouched | `git branch`, `rev-parse` | `feature/htng-fias-on-develop` @ `46904fd`; `feature/htng&fias-integration` `45ac98a`; `feature/htng&fias` `46904fd` |
| FIAS production spec empty | `adapters/fias/spec.py:182` | `None` |
| All switches off by default | `config.py:27-31` | `False` |
| No decision approved | `domain/approvals.py` | only the gate's own comparison references APPROVED |
| HTNG registry empty in production | `runtime.py:77` | `SchemaRegistry()` |
| Draft outside Alembic path; heads unchanged | `migrations/versions`, `alembic heads` (round 3) | yes; `a3f1c8e2d904`, `b3c4d5e6f7a8` |
| Every test cited in the DBA / readiness / plan documents exists | grep of 25 names | all present |
| Round-2 schema delta | DDL diff | 3 columns + 1 index |

## 2. Corrections made

| Document | Problem | Correction |
|---|---|---|
| `HTNG_FIAS_FACILITY_MAPPING.md` | said mapping audit "not implemented" | now points to the round-2 audited mapping API |
| `HTNG_FIAS_TEST_STRATEGY.md` | totals stopped at 385 | round-3 section added (406/405/1) |
| `HTNG_FIAS_CANONICAL_MESSAGE_CONTRACT.md` | `ordering_key` missing from the envelope table | added |
| `HTNG_FIAS_NEXT_PHASE_REPORT.md` | secret scan "not executed" | points to this round's scan report |
| `HTNG_FIAS_DBA_APPROVAL_PACKAGE.md` | Appendix A shows logical index names; MySQL stores names >64 chars truncated with a hash (e.g. `…_or_3881`) | note added; checklist and decision record added |
| `HTNG_FIAS_DECISION_REGISTER.md` | HF-27 impact said "no per-entity ordering" | corrected in round 3 |

## 3. Known historical statements left as-is (dated, superseded)

* `HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` §1–21: round-1 figures (308 tests). Superseded
  by §21a and `HTNG_FIAS_NEXT_PHASE_REPORT.md`.
* `HTNG_FIAS_IMPLEMENTATION_AUDIT.md`: round-2 audit; defects D3–D6 found later are recorded in
  the progress record and the round-3 report.
* `docs/HTNG-FIAS/`: reports of an **earlier, different** implementation (not this code).

## 4. Contradictions found that need an owner decision

1. **Resolved 2026-11-20** (`HTNG_FIAS_HF_ID_RECONCILIATION_PROPOSAL.md`, Option A): HF numbering conflict (HF-05, HF-11) between this repository's register and the earlier
   register — canonical IDs now in `HTNG_FIAS_DECISION_REGISTER.md` §1–2.
2. `docs/HTNG-FIAS/` claims (e.g. "103 tests", draft `b74e92a1d044`) do not describe this
   branch; the folder is now labelled historical (`docs/HTNG-FIAS/README.md`, 2026-11-20).
