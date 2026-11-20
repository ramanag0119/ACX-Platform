# HTNG / FIAS — DBA Approval Package (HF-39)

Audience: the DBA responsible for MySQL `inspironics_app`. Status: **PENDING DBA APPROVAL.**
Nothing in this package has been applied to the HMS database; every result below comes from
disposable MySQL 8.4 containers.

## 1. Purpose

Durable storage for PMS integration traffic (FIAS / HTNG): client credentials (hashes only),
external-property → facility mappings, inbound messages with idempotency, outbound queue,
and an audit trail. Without these tables the integration stays disabled.

## 2. What is requested

Seven new tables, no change to any existing HMS table:

| Table | Purpose | Growth |
|---|---|---|
| `integration_clients` | one row per vendor link; secret **hashes** only | tiny |
| `integration_facility_mappings` | client-scoped external property code → `facility.id` | tiny |
| `integration_inbound_messages` | message metadata, status, leases, retry, ordering | per inbound message |
| `integration_inbound_payloads` | canonical body (LONGTEXT), optional raw bytes | per inbound message (largest) |
| `integration_idempotency_keys` | unique (client, facility, key) | per inbound message |
| `integration_outbox_messages` | outbound queue | per outbound message |
| `integration_audit_events` | append-only audit (metadata only) | per privileged action |

Reviewable DDL (generated from the models, not hand-written):
`docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql`. Draft revision:
`backend/migrations/drafts/integration_tables_candidate.py` (outside `versions/`).
Full column / index / FK inventory: Appendix A.

### 2.1 Correction: size of the round-2 change

An earlier summary said "eight additional columns and indexes". That was wrong. The
round-2 delta, verified by diffing the generated DDL, is **3 columns + 1 index**:

| Table | Added |
|---|---|
| `integration_clients` | `secondary_secret_hash VARCHAR(80) NULL`, `secondary_expires_on DATETIME(6) NULL` |
| `integration_inbound_messages` | `ordering_key VARCHAR(200) NULL` + index `(client_id, facility_id, ordering_key, received_on)` |

## 3. Upgrade / downgrade behaviour (tested)

| Step | Behaviour | Evidence |
|---|---|---|
| upgrade | creates exactly the seven tables, columns, indexes, FKs, CHECKs in the model | `test_migration_candidate.py` |
| re-run upgrade | no-op (checkfirst); does **not** reshape a differing existing table | same |
| downgrade | drops the seven tables only; `facility` untouched | same |
| Alembic history | draft not discovered; heads unchanged | `test_draft_is_not_part_of_active_alembic_history` |

## 4. Existing migration state the DBA must resolve first

1. **Two Alembic heads**: `a3f1c8e2d904` (room_device_map) and `b3c4d5e6f7a8`
   (priority4 energy/telemetry/billing), both from `7c4e2b9a1d53`. A new revision needs a
   decided `down_revision` (after a merge revision, or as the merge). Not guessed.
2. **The HMS schema cannot be bootstrapped on MySQL from this repository.** Both
   `alembic upgrade heads` and `Base.metadata.create_all` fail. A test-only shim
   (`tests/integrations/hms_schema_shim.py`) catalogued every incompatibility while building
   the schema in a disposable database — **19 objects, 3 error classes**:

| MySQL error | Count | Objects |
|---|---|---|
| 1067 BOOL default `'true'`/`'false'` | 14 | `amenity_condition.applicable_to_occupied/applicable_to_vacant/is_active`, `currency.is_active`, `user_token.is_expired`, `activity_type.is_subscribable`, `room_status_condition_applicability.is_applicable/is_active/blocks_checkin/blocks_readiness`, `occasion.is_repeatable/notify_to_hub`, `package.is_sub_package`, `role_module_permission.read_access` |
| 3152 index directly on JSON | 4 | `ix_app_user_metadata_gin`, `ix_amenity_metadata_gin`, `ix_device_metadata_gin`, `ix_service_category_item_metadata_gin` |
| 1101 literal default on JSON | 1 | `role.notification_preferences` |

   The shared `inspironics_app` therefore was not built from this code path. **Confirm the
   live database's real revision and DDL** before attaching any new revision.

## 5. Compatibility, integrity, storage

* MySQL ≥ 8.0.16 required (CHECK constraints enforced; `SKIP LOCKED`, `FOR UPDATE OF`).
  Tested on 8.4. Charset utf8mb4; `normalized_property_code` is `utf8mb4_bin` on purpose
  (the default collation is case-insensitive and would silently decide HF-05).
* Ids CHAR(36) and DATETIME(6) UTC, matching existing HMS conventions.
* FKs to `facility.id` are `ON DELETE RESTRICT`: a facility with integration rows cannot be
  deleted. Payloads and idempotency keys cascade with their message.
* Bodies stored as LONGTEXT canonical JSON (MySQL JSON would reorder keys and break hashes).
  Application cap 256 KiB per message. Raw wire bytes (MEDIUMBLOB) only if enabled (off).
* Retention: `INTEGRATION_RETENTION_DAYS` (unset until HF-21) deletes SUCCEEDED/SENT rows in
  1,000-row batches; that window is also the duplicate-protection window.
* Concurrency verified: concurrent duplicate intake (1 message), 6 workers × 40 messages
  (no double claim), same-stay ordering under 4 workers, savepoint-joined completion
  (HMS-service `commit()` rolled back on lease loss) — including against the **real**
  `stays_write.check_in` on a seeded copy of the HMS schema (`test_hms_domain_mysql.py`).

## 6. Backup and rollback requirements (proposed, for DBA decision)

1. Full backup / snapshot of `inspironics_app` immediately before applying.
2. Apply in a maintenance window; the change only creates tables (no rewrite of existing
   data), so lock impact is limited to metadata locks on `facility` for the FK creation.
3. Rollback = downgrade (drop the seven tables). No HMS data is lost by rollback; integration
   message history is.
4. Re-run the readiness endpoint afterwards: `GET /api/v1/integrations/readiness` must show
   `persistence: ok`.

## 7. Approval questions (please answer each)

1. Approve the seven tables, types, collations and FK actions as in Appendix A? (Y/N + changes)
2. Which `down_revision`: a separate merge of `a3f1c8e2d904` + `b3c4d5e6f7a8` first, or this
   revision as the merge?
3. What is the actual Alembic revision / DDL of the live `inspironics_app`, given §4.2?
4. Should the 19 pre-existing incompatibilities be fixed in the HMS models (separate change)?
5. Is `create_all(checkfirst)` acceptable in the revision, or do you require explicit
   `op.create_table` / `op.create_index` (recommended)?
6. Backup method, maintenance window and who executes.
7. Approval of an XSD-validation library (`xmlschema` or `lxml`) if HTNG proceeds (HF-39 also
   covers new dependencies).

## 8. Operational risks

| Risk | Mitigation |
|---|---|
| Payload table growth | 256 KiB cap; retention purge once HF-21 sets a value; monitor table size |
| Long-running claim scans when many same-stay messages wait | ordering index; load test once vendor volumes are known |
| Facility delete blocked by RESTRICT FKs | intended; purge/archive integration rows first |
| Attaching to the wrong `down_revision` | DBA decides (§7 Q2) after confirming the live revision (Q3) |

## 9. DBA review checklist

| # | Item | Evidence location | Reviewed |
|---|---|---|---|
| 1 | Seven tables, columns, types match the generated DDL | Appendix A, `HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql` | ☐ |
| 2 | Round-2 delta = 3 columns + 1 index | §2.1 | ☐ |
| 3 | FKs and ON DELETE actions acceptable | Appendix A (FK table) | ☐ |
| 4 | Unique constraints (client code; client+property; client+facility+key) | Appendix A | ☐ |
| 5 | Physical index names: SQLAlchemy truncates names > 64 chars with a hash suffix (e.g. `ix_integration_inbound_messages_client_id_facility_id_or_3881`); Appendix A lists logical names | DDL file | ☐ |
| 6 | Upgrade / downgrade evidence | §3, `test_migration_candidate.py` | ☐ |
| 7 | Two Alembic heads → `down_revision` decision | §4.1 | ☐ |
| 8 | Live DB revision confirmed | §4.2, Q3 | ☐ |
| 9 | 19 pre-existing MySQL incompatibilities acknowledged; fix plan decided | §4.2, Q4 | ☐ |
| 10 | Backup, window, executor, rollback | §6, Q6 | ☐ |
| 11 | XSD library decision (if HTNG) | Q7 | ☐ |

## 10. Decision record (to be completed by the DBA — blank until signed)

| Field | Value |
|---|---|
| Decision | ☐ Approved ☐ Approved with changes ☐ Rejected |
| Required changes | |
| `down_revision` chosen | |
| Live DB revision confirmed | |
| Backup / window / executor | |
| XSD library | ☐ xmlschema ☐ lxml ☐ none / not now |
| DBA name, date, reference | |

Until this record is completed, HF-39 stays **PENDING DBA APPROVAL** and
`domain/approvals.py` is not changed.

## Appendix A — Schema inventory (generated from `sql_models.py`)

| Table | Column | MySQL type | Null | Default | Key |
|---|---|---|---|---|---|
| integration_clients | id | CHAR(36) | N |  | PK |
| integration_clients | client_code | VARCHAR(64) | N |  |  |
| integration_clients | secret_hash | VARCHAR(80) | N |  |  |
| integration_clients | secondary_secret_hash | VARCHAR(80) | Y |  |  |
| integration_clients | secondary_expires_on | DATETIME(6) | Y |  |  |
| integration_clients | enabled | BOOL | N | 0 |  |
| integration_clients | protocols | VARCHAR(64) | N |  |  |
| integration_clients | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_clients | updated_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_facility_mappings | id | CHAR(36) | N |  | PK |
| integration_facility_mappings | client_id | CHAR(36) | N |  | FK→integration_clients |
| integration_facility_mappings | external_property_code | VARCHAR(32) | N |  |  |
| integration_facility_mappings | normalized_property_code | VARCHAR(32) COLLATE utf8mb4_bin | N |  |  |
| integration_facility_mappings | facility_id | CHAR(36) | N |  | FK→facility |
| integration_facility_mappings | enabled | BOOL | N | 0 |  |
| integration_facility_mappings | created_by | VARCHAR(64) | Y |  |  |
| integration_facility_mappings | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_facility_mappings | updated_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_inbound_messages | id | CHAR(36) | N |  | PK |
| integration_inbound_messages | client_id | CHAR(36) | N |  | FK→integration_clients |
| integration_inbound_messages | facility_id | CHAR(36) | N |  | FK→facility |
| integration_inbound_messages | protocol | VARCHAR(16) | N |  |  |
| integration_inbound_messages | direction | VARCHAR(16) | N |  |  |
| integration_inbound_messages | message_type | VARCHAR(128) | N |  |  |
| integration_inbound_messages | external_message_id | VARCHAR(128) | Y |  |  |
| integration_inbound_messages | idempotency_key | VARCHAR(200) | N |  |  |
| integration_inbound_messages | ordering_key | VARCHAR(200) | Y |  |  |
| integration_inbound_messages | correlation_id | VARCHAR(64) | N |  |  |
| integration_inbound_messages | schema_version | VARCHAR(64) | N |  |  |
| integration_inbound_messages | payload_hash | VARCHAR(64) | N |  |  |
| integration_inbound_messages | status | VARCHAR(16) | N |  |  |
| integration_inbound_messages | attempt_count | INTEGER | N | 0 |  |
| integration_inbound_messages | max_attempts | INTEGER | N |  |  |
| integration_inbound_messages | next_attempt_at | DATETIME(6) | Y |  |  |
| integration_inbound_messages | lease_owner | VARCHAR(96) | Y |  |  |
| integration_inbound_messages | lease_token | VARCHAR(32) | Y |  |  |
| integration_inbound_messages | lease_expires_at | DATETIME(6) | Y |  |  |
| integration_inbound_messages | last_error_code | VARCHAR(64) | Y |  |  |
| integration_inbound_messages | last_error_category | VARCHAR(32) | Y |  |  |
| integration_inbound_messages | received_on | DATETIME(6) | N |  |  |
| integration_inbound_messages | completed_on | DATETIME(6) | Y |  |  |
| integration_inbound_messages | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_inbound_messages | updated_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_inbound_payloads | message_id | CHAR(36) | N |  | PK |
| integration_inbound_payloads | body_canonical | LONGTEXT | N |  |  |
| integration_inbound_payloads | wire_payload | MEDIUMBLOB | Y |  |  |
| integration_inbound_payloads | retain_until | DATETIME(6) | Y |  |  |
| integration_inbound_payloads | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_idempotency_keys | id | BIGINT | N |  | PK |
| integration_idempotency_keys | client_id | CHAR(36) | N |  | FK→integration_clients |
| integration_idempotency_keys | facility_id | CHAR(36) | N |  | FK→facility |
| integration_idempotency_keys | idempotency_key | VARCHAR(200) | N |  |  |
| integration_idempotency_keys | fingerprint | VARCHAR(64) | N |  |  |
| integration_idempotency_keys | message_id | CHAR(36) | N |  | FK→integration_inbound_messages |
| integration_idempotency_keys | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_outbox_messages | id | CHAR(36) | N |  | PK |
| integration_outbox_messages | source_message_id | CHAR(36) | Y |  | FK→integration_inbound_messages |
| integration_outbox_messages | client_id | CHAR(36) | N |  | FK→integration_clients |
| integration_outbox_messages | facility_id | CHAR(36) | N |  | FK→facility |
| integration_outbox_messages | protocol | VARCHAR(16) | N |  |  |
| integration_outbox_messages | message_type | VARCHAR(128) | N |  |  |
| integration_outbox_messages | correlation_id | VARCHAR(64) | N |  |  |
| integration_outbox_messages | body_canonical | LONGTEXT | N |  |  |
| integration_outbox_messages | payload_hash | VARCHAR(64) | N |  |  |
| integration_outbox_messages | status | VARCHAR(16) | N |  |  |
| integration_outbox_messages | attempt_count | INTEGER | N | 0 |  |
| integration_outbox_messages | max_attempts | INTEGER | N |  |  |
| integration_outbox_messages | next_attempt_at | DATETIME(6) | Y |  |  |
| integration_outbox_messages | lease_owner | VARCHAR(96) | Y |  |  |
| integration_outbox_messages | lease_token | VARCHAR(32) | Y |  |  |
| integration_outbox_messages | lease_expires_at | DATETIME(6) | Y |  |  |
| integration_outbox_messages | last_error_code | VARCHAR(64) | Y |  |  |
| integration_outbox_messages | created_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_outbox_messages | sent_on | DATETIME(6) | Y |  |  |
| integration_outbox_messages | updated_on | DATETIME(6) | N | CURRENT_TIMESTAMP(6) |  |
| integration_audit_events | id | BIGINT | N |  | PK |
| integration_audit_events | occurred_on | DATETIME(6) | N |  |  |
| integration_audit_events | actor_type | VARCHAR(16) | N |  |  |
| integration_audit_events | actor_id | VARCHAR(64) | Y |  |  |
| integration_audit_events | action | VARCHAR(64) | N |  |  |
| integration_audit_events | facility_id | CHAR(36) | Y |  |  |
| integration_audit_events | message_id | CHAR(36) | Y |  |  |
| integration_audit_events | reason | VARCHAR(500) | Y |  |  |
| integration_audit_events | detail | JSON | Y |  |  |

| Table | Index / unique | Columns |
|---|---|---|
| integration_clients | UNIQUE uq_integration_clients_client_code | client_code |
| integration_facility_mappings | ix_integration_facility_mappings_facility_id | facility_id |
| integration_facility_mappings | UNIQUE uq_integration_facility_mappings_client_id_normalized_property_code | client_id, normalized_property_code |
| integration_inbound_messages | ix_integration_inbound_messages_client_id_facility_id_ordering_key_received_on | client_id, facility_id, ordering_key, received_on |
| integration_inbound_messages | ix_integration_inbound_messages_correlation_id | correlation_id |
| integration_inbound_messages | ix_integration_inbound_messages_facility_id_status_received_on | facility_id, status, received_on |
| integration_inbound_messages | ix_integration_inbound_messages_next_attempt_at | next_attempt_at |
| integration_idempotency_keys | UNIQUE uq_integration_idempotency_keys_client_id_facility_id_idempotency_key | client_id, facility_id, idempotency_key |
| integration_outbox_messages | ix_integration_outbox_messages_facility_id_status_created_on | facility_id, status, created_on |
| integration_outbox_messages | ix_integration_outbox_messages_next_attempt_at | next_attempt_at |
| integration_outbox_messages | ix_integration_outbox_messages_source_message_id | source_message_id |
| integration_audit_events | ix_integration_audit_events_facility_id_occurred_on | facility_id, occurred_on |
| integration_audit_events | ix_integration_audit_events_message_id | message_id |

| Table | Column | References | ON DELETE |
|---|---|---|---|
| integration_facility_mappings | facility_id | facility.id | RESTRICT |
| integration_facility_mappings | client_id | integration_clients.id | RESTRICT |
| integration_inbound_messages | facility_id | facility.id | RESTRICT |
| integration_inbound_messages | client_id | integration_clients.id | RESTRICT |
| integration_inbound_payloads | message_id | integration_inbound_messages.id | CASCADE |
| integration_idempotency_keys | message_id | integration_inbound_messages.id | CASCADE |
| integration_idempotency_keys | facility_id | facility.id | RESTRICT |
| integration_idempotency_keys | client_id | integration_clients.id | RESTRICT |
| integration_outbox_messages | source_message_id | integration_inbound_messages.id | SET NULL |
| integration_outbox_messages | client_id | integration_clients.id | RESTRICT |
| integration_outbox_messages | facility_id | facility.id | RESTRICT |

## 11. Addendum (2026-11-20) — Schema-integrity defect: unconstrained `direction` (BLK-D6, proposed)

Status: **PENDING DBA APPROVAL** — part of the HF-39 decision. **Nothing has been changed:** no
code fix, no constraint, no migration. This section supplies evidence and options only.

### 11.1 Observed behaviour

In the isolated full-stack E2E run (`HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md` §5 and §6,
finding 1), **one** inbound row with an invalid `direction` value had three effects:

| Effect | Observed |
|---|---|
| Overview aggregates | the row **is counted**: HTNG inbound total went from 16 to 17 for the facility, and pending from 5 to 6 |
| `GET /api/v1/integrations/observability/messages` | **HTTP 500** (check R6) |
| Message lists that include the row (HTNG page "recent messages", DLQ page) | the same 500 (check R7: the page renders, and the list shows "Could not load this data") |

### 11.2 Reproduction (disposable database only)

The row was inserted directly into the disposable `acx_fullstack_e2e` database. It copied
`client_id` and `facility_id` from an existing row and set
`protocol='htng', direction='sideways', status='PENDING'`. After the checks it was deleted.

Root cause, from the code (`backend/app/integrations/processing/`):

* `sql_models.py`: `InboundMessageRow.direction` is `String(16)`, NOT NULL, with **no CHECK**.
  The only CHECKs on the table are `status_valid` and `attempt_count_non_negative`. The same is
  true in `docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql` (line 43 and lines 65–66).
* `sql_repository._to_stored()` maps each row with `Direction(row.direction)`, which raises
  `ValueError` on an unknown value. The router converts only `IntegrationError` and
  `SQLAlchemyError` into HTTP errors, so the `ValueError` becomes a 500.
* `processing/activity.py` aggregates group by `protocol` and `status` only, so the overview
  never parses `direction` and counts the row.

### 11.3 Allowed values: what the code shows (decision required, not assumed)

| Evidence | Value(s) |
|---|---|
| `core/envelope.py` `Direction` enum | `inbound`, `outbound` |
| The only writer of this table, `exchange/gateway.py:240` → `sql_repository.accept()` (`direction=str(envelope.direction)`) | always `inbound` |
| Outbound messages | stored in `integration_outbox_messages`, which has **no** `direction` column |

Two candidate constraints. **ARCH and DBA must choose one:**

```sql
-- Option A: every value the application can parse (matches the enum)
CONSTRAINT ck_integration_inbound_messages_direction_valid CHECK (direction IN ('inbound', 'outbound'))
-- Option B: only the value the inbound table is written with today
CONSTRAINT ck_integration_inbound_messages_direction_valid CHECK (direction = 'inbound')
```

**Related columns (the same pattern, also unconstrained — please decide together):**

| Column | Parsed by | Enum values |
|---|---|---|
| `integration_inbound_messages.protocol` | `Protocol(row.protocol)` | `fias`, `htng`, `test` |
| `integration_outbox_messages.protocol` | `_to_outbox` | `fias`, `htng`, `test` |

`test` is documented as "used only by tests and simulators". Whether a production CHECK should
admit it is an ARCH/DBA decision.

### 11.4 Existing-data validation (before any constraint)

The tables do **not** exist in `inspironics_app` today. If the CHECK is added to the candidate
DDL before HF-39 approval, the target database needs no data validation. Any environment where
the candidate tables already exist must run these checks first. They are read-only. MySQL
8.0.16+ also refuses `ADD CONSTRAINT … CHECK` while violating rows exist.

```sql
SELECT direction, COUNT(*) FROM integration_inbound_messages GROUP BY direction;
SELECT protocol,  COUNT(*) FROM integration_inbound_messages GROUP BY protocol;
SELECT protocol,  COUNT(*) FROM integration_outbox_messages  GROUP BY protocol;
SELECT id, facility_id, status, received_on FROM integration_inbound_messages
 WHERE direction NOT IN ('inbound', 'outbound');   -- adjust to the chosen option
```

### 11.5 Remediation considerations for invalid historical rows (for DBA/ARCH decision)

* Never delete silently. Export the offending rows (metadata; payload only under the HF-21
  rules) for investigation, and record an audit event.
* Choose per row:
  * **correct** the value, only when its true origin is provable;
  * **quarantine** it to a side table;
  * **purge** it, with ARCH/DBA sign-off.

  Changing `status` alone does not help: any search that includes the row still returns 500.
* Rows referenced by `integration_outbox_messages.source_message_id` (`SET NULL`) and by
  payload and idempotency rows (`CASCADE`) are affected by a delete. Check them first.
* Run in the HF-39 maintenance window, after the backup in §6.

### 11.6 Application-level defensive recommendation (not implemented; needs BE/ARCH approval)

* Map unknown enum values tolerantly in `_to_stored` / `_to_outbox`. Expose the row as
  `invalid` with a sanitised error code instead of raising, so one bad row cannot take down a
  list endpoint.
* Keep aggregates and lists consistent: either both include such rows, flagged, or both exclude
  them.
* **Worker risk (from reading the code, not reproduced).** `claim()` calls `_to_stored(row)`
  inside the claim transaction. An invalid claimable row would raise, roll back the whole batch
  and remain at the head of the queue, so it could repeatedly stall inbound processing. Isolate
  such rows (e.g. move them to `DEAD_LETTER` with code `invalid_row`) without failing the batch.
  This needs a regression test before any production use.

### 11.7 Approval required

| Item | Approver |
|---|---|
| Allowed values: Option A or B for `direction`, and the `protocol` value sets | ARCH, DBA |
| Add the CHECK(s) to the model and the candidate DDL before first deployment | DBA (record in §10) |
| Validation and remediation procedure for any pre-existing environment | DBA, OPS |
| Application defensive mapping and the worker fix (code change and tests) | BE, ARCH |
| Migration authorisation (same HF-39 decision record; DDL regenerated after the change) | DBA, PO |

Review checklist addition: **12. Direction and protocol CHECK constraints decided; validation
queries run where tables exist (§11).** Approval question addition: **Q8. Option A or B for
`direction`; allowed `protocol` values; tolerant mapping required before go-live?**

### 11.8 Existing-data validation results (2026-11-20, read-only, disposable databases only)

The §11.4 queries were run read-only on every environment where the candidate tables exist:
the two disposable test databases on the `acx-int-mysql` test container. The HMS database
`inspironics_app` was **not** accessed; per §2 it has no integration tables.

| Database | `direction` values | Invalid `direction` rows | Inbound `protocol` values | Outbox `protocol` values |
|---|---|---|---|---|
| `acx_integration_test` | `inbound` (6) | 0 | `test` (6) | `test` (1) |
| `acx_hms_domain_e2e` | `inbound` (2) | 0 | `fias` (2) | none |

Implications for Q8:

* **Direction.** No existing row would violate either Option A or Option B. The data is test
  residue, so it does **not** show which option is right; that remains an ARCH/DBA decision.
* **Protocol.** The integration test suite writes `protocol='test'` into these MySQL tables. A
  CHECK that excludes `test` would make those tests fail unless they change too. Decide the
  `protocol` value set with that in mind: for example, include `test`, or keep the constraint
  production-only with the tests adjusted. Neither option is assumed here.

No constraint was added, no row was changed and no migration was run.
