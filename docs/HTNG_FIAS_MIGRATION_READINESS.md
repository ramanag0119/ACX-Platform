# HTNG / FIAS — Migration Readiness Report

Status: **PENDING DBA APPROVAL (HF-39)**. Nothing has been applied to the HMS database.

## 1. What is proposed

Seven tables (`docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`, regenerated 2026-11-20 from
`backend/app/integrations/processing/sql_models.py`):

`integration_clients`, `integration_facility_mappings`, `integration_inbound_messages`,
`integration_inbound_payloads`, `integration_idempotency_keys`,
`integration_outbox_messages`, `integration_audit_events`.

Changes since the first candidate (round 2):

| Table | Change | Reason |
|---|---|---|
| `integration_clients` | `secondary_secret_hash`, `secondary_expires_on` | credential rotation with overlap |
| `integration_inbound_messages` | `ordering_key` VARCHAR(200) NULL + index (`client_id`,`facility_id`,`ordering_key`,`received_on`) | per-entity in-order processing |

## 2. Verification on disposable MySQL 8.4 (`acx_integration_test`)

| Check | Result | Evidence |
|---|---|---|
| `upgrade()` creates exactly the modelled tables, columns, indexes, FKs | pass | `test_migration_candidate.py::test_upgrade_creates_exactly_the_modelled_schema_and_downgrade_removes_it` |
| `downgrade()` removes all seven, leaves HMS `facility` untouched | pass | same |
| CHECK constraints present and enforced (MySQL ≥ 8.0.16) | pass | same; `test_status_check_constraint_enforced` |
| Upgrade is a no-op when re-run (checkfirst) | pass | `test_upgrade_is_idempotent_via_checkfirst` |
| Draft not in the Alembic history; heads unchanged (`a3f1c8e2d904`, `b3c4d5e6f7a8`) | pass | `test_draft_is_not_part_of_active_alembic_history` |
| FK failure (1452) surfaces as integrity error, not duplicate | pass | `test_unknown_facility_fk_is_an_integrity_error_not_a_duplicate` |
| Unique idempotency key, insert race (1062 with truncated constraint name) | pass | `test_lost_insert_race_resolves_via_duplicate_key_error` |
| Concurrent claim (SKIP LOCKED), ordering predicate under 4 threads | pass | `test_concurrent_workers_never_claim_the_same_message`, `test_concurrent_workers_never_run_same_key_together` |
| Transaction rollback incl. HMS-style `commit()` inside handler | pass | `test_hms_service_style_commit_inside_handler_is_still_rolled_back_on_lease_loss` |
| Hash stability (LONGTEXT, not JSON) | pass | `test_body_hash_is_stable_through_mysql_storage` |
| Binary collation for property codes | pass | `test_mapping_store_uses_binary_collation_for_exact_policy` |
| Retention purge in batches, cascade of payloads/keys | pass | `test_service.py::test_purge_removes_only_old_completed_rows[mysql]` |

## 3. Types, sizes, timestamps

* Ids CHAR(36) (existing `GUID`), timestamps DATETIME(6) UTC (existing `UTCDateTime`).
* Bodies LONGTEXT (canonical JSON); wire bytes MEDIUMBLOB (≤16 MB, off by default);
  the application caps a message at `INTEGRATION_MAX_MESSAGE_BYTES` (256 KiB).
* Audit `detail` JSON (metadata only).

## 4. Query performance notes

* Claim: range on `next_attempt_at` (indexed) + NOT EXISTS predecessor probe on the
  4-column ordering index; `FOR UPDATE OF … SKIP LOCKED` locks only claimed rows.
* Scans grow with blocked (waiting) same-key messages; volumes are unknown until a
  vendor is chosen — load testing is a pre-production item.
* Health view: GROUP BY facility/status; latency samples capped at 5,000 rows.

## 5. Findings the DBA must decide

1. **`down_revision`.** The repository has two Alembic heads. This migration must either
   follow a merge revision or itself merge. Not guessed.
2. **Pre-existing chain on MySQL.** `8f1e3c5a7b92` fails on a fresh MySQL (1067); confirm
   the target database's actual revision before attaching anything.
3. **Explicit DDL.** The draft calls `create_all(checkfirst)`, which will not reshape an
   existing table. For the real revision, prefer explicit `op.create_table` /
   `op.create_index` generated from the reviewed SQL.
4. **FK actions.** `facility` FKs are RESTRICT (facility deletion blocked while integration
   rows exist).
5. **Retention.** `INTEGRATION_RETENTION_DAYS` (HF-21) also defines how long duplicate
   protection lasts; purge runs in 1,000-row batches.
