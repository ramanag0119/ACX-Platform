# HISTORICAL — earlier HTNG / FIAS implementation (errata notice, 2026-11-20)

The files in this folder are **historical**. They describe an **earlier, different**
HTNG / FIAS implementation (branch `feature/htng&fias-integrate` in a separate working copy),
not the code on `feature/htng-fias-on-develop`. Several files are short "mirror" stubs that
link to that other working copy. They are kept unchanged as a record; their figures (for example
test counts, draft revision `b74e92a1d044`, module paths) do **not** describe the current code.

**Current implementation:** `backend/app/integrations/`.
**Canonical documents:** `docs/HTNG_FIAS_DECISION_REGISTER.md` (canonical HF register),
`docs/HTNG_FIAS_BLOCKER_REGISTER.md`, `docs/HTNG_FIAS_PRODUCTION_READINESS.md`,
`docs/HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md`.

## Errata — HF IDs used here with a different meaning

The original wording below is **not** rewritten. Read these references through the canonical
register (`docs/HTNG_FIAS_HF_ID_RECONCILIATION_PROPOSAL.md`, applied 2026-11-20):

| File (this folder) | Text as written | Canonical reading |
|---|---|---|
| `HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` (§ business ownership decisions) | "`HF-11`: FIAS Vendor Specification Manual (record codes, status digits, link-alive interval)" | HF-11 = FIAS specification content; the link-alive interval is **HF-06** |
| `HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | "`HF-18`: System of Record for Room Cleanliness States" | not HF-18 (integration principal). Subject maps to **HF-01** (system of record per entity) and **HF-37** (room-status vocabulary) |
| `HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md` | "Business Ownership Decisions (HF-01 to HF-39)" | range statement only; see canonical register for each ID |
| `HTNG_FIAS_PHASE6_PERSISTENCE_READINESS_REPORT.md`, `HTNG_FIAS_PHASE7_MYSQL_RUNTIME_VERIFICATION_REPORT.md` | "Business Decision HF-07: idempotency retention window / key TTL" | not HF-07 (HTNG specification). Retention is **HF-21** (which also defines the duplicate-protection window) |

Uses of HF-01, HF-07 (as HTNG profile), HF-19 in these files match the canonical meanings.
The earlier register itself (`HTNG_FIAS_BUSINESS_VENDOR_DECISION_REGISTER.md`) is **not** in
this folder; it exists only in the other working copy and has not been copied (its
provenance is pending project-owner confirmation).
