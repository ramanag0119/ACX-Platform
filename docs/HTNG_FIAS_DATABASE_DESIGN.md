# HTNG / FIAS — Database Design (CANDIDATE — NOT APPROVED, HF-39)

Models: `backend/app/integrations/processing/sql_models.py` (separate `INTEGRATION_METADATA`).
Reviewable DDL: `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql` (generated from the models).
Draft revision: `backend/migrations/drafts/integration_tables_candidate.py` (outside
`versions/`; `down_revision` unset on purpose).

**Round 2 (2026-11-20):** `integration_clients` gained `secondary_secret_hash` /
`secondary_expires_on` (rotation); `integration_inbound_messages` gained `ordering_key` and
the index (`client_id`,`facility_id`,`ordering_key`,`received_on`). Upgrade/downgrade
validation: `HTNG_FIAS_MIGRATION_READINESS.md`.

**No table was created in the configured HMS database.** All tables were created only in a
disposable MySQL 8.4 container (`acx_integration_test`) together with a one-column
`facility` stub matching `facility.id CHAR(36)`.

## 1. Tables

| Table | PK | Scope / FKs | Unique | Indexes | Notes |
|---|---|---|---|---|---|
| `integration_clients` | `id` CHAR(36) | — | `client_code` | — | `secret_hash` only; `enabled` default 0; `protocols` CSV |
| `integration_facility_mappings` | `id` | `client_id`→clients, `facility_id`→facility (RESTRICT) | (`client_id`, `normalized_property_code`) | `facility_id` | `normalized_property_code` `utf8mb4_bin`; `enabled` default 0; `created_by` |
| `integration_inbound_messages` | `id` | `client_id`, `facility_id` (RESTRICT) | — | `next_attempt_at`; (`facility_id`,`status`,`received_on`); `correlation_id` | CHECK on status and `attempt_count ≥ 0`; lease owner/token/expiry |
| `integration_inbound_payloads` | `message_id` (FK, CASCADE) | — | — | — | `body_canonical` LONGTEXT; `wire_payload` MEDIUMBLOB null; `retain_until` (unused, HF-21) |
| `integration_idempotency_keys` | `id` BIGINT AI | `client_id`, `facility_id`, `message_id` (CASCADE) | (`client_id`,`facility_id`,`idempotency_key`) | — | `fingerprint` = sha256(type+body) |
| `integration_outbox_messages` | `id` | `client_id`, `facility_id`, `source_message_id` (SET NULL) | — | `next_attempt_at`; (`facility_id`,`status`,`created_on`); `source_message_id` | CHECK on status; lease fields |
| `integration_audit_events` | `id` BIGINT AI | none (must outlive referenced rows) | — | (`facility_id`,`occurred_on`); `message_id` | `detail` JSON, metadata only |

Timestamps are `DATETIME(6)` in UTC via the existing `UTCDateTime` type; ids use the
existing `GUID` (CHAR(36)).

## 2. Query design

* **Claim:** `WHERE next_attempt_at <= :now AND status IN (…) ORDER BY next_attempt_at, id
  LIMIT n FOR UPDATE SKIP LOCKED`. Terminal rows have `next_attempt_at = NULL`; PROCESSING
  rows carry their lease expiry there, so abandoned leases become claimable without a
  second query. `EXPLAIN` lists the `next_attempt_at` index as a possible key
  (`test_claim_query_uses_next_attempt_index`).
* **Fence:** `SELECT … FOR UPDATE` by id, then token + expiry check in the same transaction.
* **Idempotency race:** duplicate INSERT → MySQL 1062 on `integration_idempotency_keys.uq_…`
  → re-read and compare. Any other integrity error (e.g. 1452 unknown facility) is a
  `permanent` `integrity_violation`, never a duplicate. Note the generated constraint name
  is truncated with a hash suffix (64-char limit); matching uses the table + `uq_` prefix.

## 3. Verified against disposable MySQL 8.4 (tests/integrations)

JSON key re-ordering by MySQL; hash stability through LONGTEXT; FK failure (1452);
unique constraint present; concurrent duplicate intake (8 threads → 1 message); forced
insert race → duplicate/conflict; 6 concurrent workers × 40 messages → no double claim;
claim index; domain write + status + outbox atomic; HMS-style `commit()` inside handler
rolled back on lease loss and on later failure; fenced row invisible to other claimers;
restart recovery with a new repository instance; CHECK constraint enforced; binary
collation; SQL client/mapping stores.

## 4. Retention and audit (not implemented)

Purging of payloads, idempotency keys and terminal messages, payload encryption, and
audit immutability need HF-21 / HF-23 values. Until then nothing is deleted.

## 5. DBA decisions required (HF-39)

1. Approve tables, types, collations and FK actions above.
2. Choose `down_revision` (repo has two heads) and confirm the target DB revision.
3. Confirm the pre-existing chain's MySQL incompatibility (`8f1e3c5a7b92`) is understood.
4. Approve `facility` FKs with RESTRICT (facility deletion blocked while messages exist).
