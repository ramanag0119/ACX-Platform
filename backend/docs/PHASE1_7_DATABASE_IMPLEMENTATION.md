# PHASE 1.7 — HMS DATABASE FOUNDATION IMPLEMENTATION

**Date:** 2026-08-16
**Source of truth:** [`FINAL_HMS_DATABASE_BLUEPRINT.md`](FINAL_HMS_DATABASE_BLUEPRINT.md)
**Migration revision:** `0e2687233b59` (single head, `down_revision = None`)
**Database:** `hms_db` / schema `public` · PostgreSQL 16.12 · SQLAlchemy 2.x · Alembic

---

## 1. Implementation summary

The approved 92-table blueprint is implemented and live. The superseded Phase 1
39-table foundation and its Alembic revision `8a8456154f0e` are gone.

| | |
|---|---:|
| Tables created | **92** |
| PostgreSQL ENUM types | **34** |
| Foreign keys | **240** |
| Unique constraints | **76** |
| Indexes | **352** |
| Schema tests | **151 passing** |
| Seed rows written | **0** |
| API routes created | **0** |
| Frontend files touched | **0** |

Not done, by instruction: no seed data, no FastAPI routes, no frontend change.

---

## 2. Final 92-table count

| Group | Tables |
|---|---:|
| A — organisation, facility, property hierarchy | 8 |
| B — rooms, amenities, packages | 9 |
| C — guests, stays, billing | 7 |
| D — people, authentication, RBAC | 9 |
| E — services, tickets, catalogue | 8 |
| F — maintenance / Services Planning | 4 |
| G — devices, telemetry, IoT | 14 |
| H — job orders | 3 |
| I — access control and digital keys | 4 |
| J — alerts, incidents, value limits | 8 |
| K — activity feed and notification dispatch | 9 |
| L — scheduler | 2 |
| M — marketing, events, occasions | 5 |
| N — energy and reporting | 2 |
| **Total** | **92** |

Plus `alembic_version` (infrastructure, excluded from every count).

`app.models.APPROVED_TABLES` holds the list verbatim from blueprint §12.2. The
test suite asserts the live database equals that set exactly, so neither a
missing table nor an unapproved one can pass unnoticed.

---

## 3. Model structure

```
backend/
├── app/
│   ├── core/config.py            unchanged — settings from .env
│   ├── db/
│   │   ├── base.py               Base, 4 PK tiers, LegacyIdMixin, TimestampMixin
│   │   ├── session.py            unchanged — engine + sessionmaker
│   │   └── verify_schema.py      rewritten — Phase 1.7 inventory report
│   └── models/
│       ├── __init__.py           imports all 92; APPROVED_TABLES + PK tier sets
│       ├── enums.py              34 PG ENUM types, IKANOS literals verbatim
│       ├── facility.py      A    8   + the two cycle-breaking FK helpers
│       ├── amenity.py       B    9
│       ├── stay.py          C    7
│       ├── people.py        D    9
│       ├── service.py       E    8
│       ├── maintenance.py   F    4
│       ├── device.py        G   14
│       ├── job_order.py     H    3
│       ├── access.py        I    4
│       ├── alert.py         J    8
│       ├── activity.py      K    9
│       ├── scheduler.py     L    2
│       ├── marketing.py     M    5
│       └── reporting.py     N    2
├── migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py
├── tests/test_schema_foundation.py
└── docs/
    ├── FINAL_HMS_DATABASE_BLUEPRINT.md
    ├── PHASE1_7_DATABASE_IMPLEMENTATION.md   (this file)
    └── archive/                              Phase 1 backups
```

Module boundaries follow the blueprint's own §12.1 grouping, so a table is
found where the blueprint puts it.

Every model class carries a docstring naming its IKANOS source table and its
USE / ADAPT / MERGE classification, plus the specific columns the blueprint
refuses to invent.

---

## 4. Migration strategy

### 4.1 Why rebuild rather than patch

The previous `hms_db` held the Phase 1 39-table foundation at revision
`8a8456154f0e`. Before touching anything:

1. All 39 tables were row-counted — **total business rows: 0**. Nothing to migrate.
2. Backups were taken regardless (§4.2).
3. The blueprint supersedes the 39-table design: 24 MODIFY, 10 REPLACE,
   2 MERGE, 2 REMOVE, only 1 KEEP. An incremental patch chain would have been
   a longer, riskier path to the same empty schema, and would have left
   `upgrade` on a clean database creating 39 tables only to drop them again.

**Strategy chosen: single baseline revision.** `0e2687233b59` has
`down_revision = None` and creates the 92-table schema in one deterministic
step. The Phase 1 revision file was removed from `migrations/versions/` after
being archived.

### 4.2 Backups taken (all under `backend/docs/archive/`)

| Artefact | Contents |
|---|---|
| `hms_db_phase1_schema_backup.sql` | `pg_dump --schema-only` of the 39-table database (2,078 lines) |
| `phase1_models_backup/` | the 8 Phase 1 model modules |
| `8a8456154f0e_phase1_ikanos_entity_foundation.py.bak` | the superseded revision, `.bak` so Alembic cannot load it |

`docs/archive/*.sql` is gitignored (see §10).

### 4.3 Rebuild sequence executed

```
row-count all 39 tables            -> 0 rows, safe to proceed
pg_dump --schema-only              -> docs/archive/
cp app/models, cp old revision     -> docs/archive/
DROP SCHEMA public CASCADE; CREATE SCHEMA public
rm migrations/versions/8a8456154f0e_*.py
alembic revision --autogenerate
post-process the revision          -> §6, §7
alembic upgrade head
```

### 4.4 The migration is not raw autogenerate output

Two things Alembic autogenerate cannot express for this schema were applied
deterministically after generation, by script rather than by hand:

1. **ENUM lifecycle** — §6.
2. **Cyclic foreign keys** — §7.

The resulting migration is 2,729 lines: 34 `CREATE TYPE`, 92 `create_table`,
the index set, then 84 deferred `create_foreign_key` calls; `downgrade` runs
the exact inverse.

---

## 5. Primary key strategy

Blueprint §2.3 is implemented literally, table by table. No tier was applied
globally.

| Tier | Type | Tables | Rationale |
|---|---|---:|---|
| **T1** lookup | `SMALLINT` / `INTEGER`, `autoincrement=False` | **16** | The IKANOS ids ARE the values the frontend renders (`amenity_status` 0–3, `role_module` 1–18, `service_type` 1–7). They are seeded, never generated. |
| **T2** entity | `UUID` (uuid4) | **50** | Business/transactional entities. |
| **T3** high-volume | `BIGINT GENERATED ALWAYS AS IDENTITY` | **12** | Append-only telemetry, alert, notification and audit streams (`device_health_stat` is 7.7 M rows in the IKANOS dump). |
| **Composite** | IKANOS natural key | **14** | `user_role(facility_id, app_user_id, role_id)`, `energy_stat(device_name, facility_id, amenity_id, hour)`, etc. — no surrogate added. |

16 + 50 + 12 + 14 = 92. The three tier sets are exported as
`LOOKUP_TABLES`, `HIGH_VOLUME_TABLES` and `COMPOSITE_PK_TABLES`, and a test
asserts they are disjoint and name only approved tables.

**`legacy_id BIGINT UNIQUE`** is present on the 62 T2 + T3 tables — those whose
IKANOS integer surrogate key is replaced by a UUID or an identity value, so the
original key is what needs preserving. See **Deviation D1 (§11)** for the 30
tables that do not carry it and why.

Corrections to Phase 1 that the PK work forced:

- `user_role` PK is now `(facility_id, app_user_id, role_id)`. Previously
  `(app_user_id, user_role_id)`, so a user could not hold different roles at
  different facilities.
- `energy_stat` keeps the IKANOS 4-column PK instead of a UUID surrogate.
- `daily_dual_data_point` keeps `(metric_date, metric_type)` verbatim —
  including the consequence that `facility_id` is *not* in the key. Preserved
  rather than silently widened; raised as OPEN DECISION #6.

---

## 6. ENUM strategy

**34 native PostgreSQL ENUM types**, values byte-for-byte from the IKANOS dump.
All 13 Phase 1 enums are dropped — zero of them matched.

### 6.1 Fidelity

Literals are never normalised. The test suite pins the ones easiest to
"tidy up" by accident:

| Type | Literal preserved |
|---|---|
| `stay_status` | `checkout accepted`, `checkout pending`, `checkout rejected`, `checked out` (spaces) |
| `notification_channel` | `push notification`, `silent notification` (spaces) |
| `param_data_type` | `Date Time` (space + capitals) |
| `import_entity_type` | `job order` (space) |
| `daily_metric_type` | `smart room`, `service request`, `guest room` (spaces) |
| `device_health_status` | `Active`, `Inactive` (capitals) |
| `command_processing_status` | `Queued`, `Processing`, `Processed`, `Error` (capitals) |
| `device_short_code` | `HUB`, `KLE`, `MIK`, `AIR` (upper) |
| `mqtt_topic_type` | `DeviceData`, `LastWill`, `ServerBroadCast` (camel) |
| `activity_notifier_status` | `'0'`, `'1'`, `'2'` — string enums of digits |
| `role_type` | includes `system_user`, which the UI hides |
| `alert_severity` | `warning`, `critical` only — `Info` was invented and is gone |

### 6.2 Lifecycle

Three types are used by two tables each — `request_source` (`stay`,
`service_request`), `device_health_status` (`device`, `device_health_stat`) and
`notification_channel` (`notification_template`, `notification_result`).
Rendering `postgresql.ENUM(values…, name=…)` inline in `create_table` would
emit `CREATE TYPE` once per occurrence and fail on the second.

Implementation:

- `app/models/enums.py` declares every type with **`create_type=False`**, so no
  `create_table` ever emits `CREATE TYPE`.
- The migration owns the lifecycle. It carries a frozen `ENUM_TYPES` list —
  names and values copied in at generation time, so the migration never drifts
  with the models — and runs:

```python
def upgrade():
    for enum_type in ENUM_TYPES:
        enum_type.create(bind, checkfirst=False)     # 34 types, once each
    ...                                              # 92 tables
def downgrade():
    ...                                              # tables first
    for enum_type in reversed(ENUM_TYPES):
        enum_type.drop(bind, checkfirst=False)
```

`checkfirst=False` is deliberate: a duplicate or orphan type should fail loudly,
not be silently skipped. Verified — after `downgrade base`, zero enum types
remain.

---

## 7. Circular dependency handling

### 7.1 The cycles

`verify_schema` reports **9** foreign-key cycles. They are legitimate, not
defects:

```
facility  -> attachment -> facility                     (facility.facility_image_id)
app_user  -> department -> facility -> app_user         (facility.created_by)
app_user  -> job_function -> facility -> app_user
app_user  -> department -> facility -> organisation -> app_user
app_user  -> department -> app_user                     (department.created_by)
```

plus the self-references `app_user.supervisor`, `amenity.parent_amenity_id`,
`device.parent_device_id`, `maintenance_request.parent_id` — those are fine
inside a single `CREATE TABLE` and need no special handling.

### 7.2 Approach chosen: staged FK creation

Options considered: nullable bootstrap references (rejected — `created_by` is
`NOT NULL` in IKANOS on `organisation`, `facility` and `app_user`; weakening it
would change the approved schema), deferrable constraints (rejected — it
changes transaction semantics application-wide to solve a DDL-ordering
problem), and staged creation (**chosen**).

Implementation:

1. Every FK pointing at `app_user` or `attachment`, plus
   `app_user.department_id` and `app_user.job_function_id`, is declared with
   `use_alter=True`.
2. `use_alter` is honoured by SQLAlchemy's `create_all` sorter but **not** by
   `op.create_table`, which emits every constraint inline. The migration
   post-processor therefore strips those constraints out of the
   `create_table` calls and re-emits them as **84 `op.create_foreign_key`
   statements** after all 92 tables exist.
3. `downgrade` drops those 84 constraints first, then the tables in reverse —
   so the tables can be dropped in any order.

**No foreign key was weakened, made nullable, or omitted.** All 240 FKs exist in
the database; the cyclic 84 are simply added by `ALTER TABLE` instead of inline.
A test asserts each of the 9 bootstrap edges still has its constraint.

### 7.3 Consequence for seeding (Phase 2, not done here)

`organisation.created_by`, `facility.created_by` and `app_user.created_by` are
all `NOT NULL` and all resolve to `app_user`. IKANOS bootstraps this with a
first `users` row created before any facility, whose `created_by` points at
itself. Any future seed script must do the same — insert the bootstrap
`app_user` first, self-referencing. Recorded here so it is not rediscovered.

---

## 8. Validation results

All commands run against `hms_db` @ localhost:5432.

| # | Check | Result |
|---:|---|---|
| 1 | Exactly 92 approved tables exist | **PASS** — 92 |
| 2 | Every approved table exists | **PASS** — 0 missing |
| 3 | No unapproved business table exists | **PASS** — 0 extra; 0 of the 20 retired Phase 1 tables survive |
| 4 | Primary keys match the blueprint | **PASS** — per-table comparison + all four tiers asserted individually |
| 5 | Foreign keys match | **PASS** — 240, set-equal to the models in both directions |
| 6 | Unique constraints match | **PASS** — 76, set-equal per table |
| 7 | Indexes match | **PASS** — 352, including 4 GIN on merged JSONB and 2 BRIN on high-volume timestamps |
| 8 | ENUM types and values match | **PASS** — 34 types, value lists compared in order |
| 9 | Nullable / non-nullable match | **PASS** — every column |
| 10 | Data types match | **PASS** — model and reflected type both compiled with the PG dialect |
| 11 | Circular relationships valid | **PASS** — 9 cycles present, all 84 deferred FKs created |
| 12 | `alembic upgrade head` | **PASS** |
| 13 | `alembic downgrade base` | **PASS** — 0 tables, 0 enum types, 0 FKs left |
| 14 | `alembic upgrade head` again | **PASS** — 92 tables, 34 types |
| 15 | `alembic check` | **PASS** — "No new upgrade operations detected" |

Automated suite: **151 tests, 151 passing**, in `tests/test_schema_foundation.py`.
Beyond the 15 required checks it also asserts:

- audit columns are `created_on`/`updated_on`, never Phase 1's `created_at`/`updated_at`;
- every TIMESTAMP is TIMESTAMPTZ;
- `facility_uid` exists only on `facility` (blueprint §2.5);
- the `legacy_id` policy holds on both sides (present where required, absent where not);
- **22 columns the blueprint refuses to invent are absent** — `package.price`,
  `invoice.status`, `device.ip_address`/`mac_address`/`last_seen`,
  `firmware.is_latest`, `alert_type.severity`, `incident_status.status_code`,
  `device_incident.resolved_on`, `value_alert.parameter`,
  `service_request.priority`, `occasion.lock_message`, `role.permissions`,
  `app_user.is_active`, and others;
- 18 named critical relationships resolve to the corrected target
  (`job_function → facility`, `*.assigned_to → app_user`,
  `amenity → property_chain`, `device_incident.latest_alert_id → device_alert`, …);
- no rows exist in any table (Phase 1.7 is schema only).

---

## 9. Migration revision ID

```
0e2687233b59   phase1_7 hms 92 table foundation
down_revision = None          (single head, clean baseline)
```

Superseded and removed: `8a8456154f0e` (Phase 1, 39 tables) — archived at
`docs/archive/8a8456154f0e_phase1_ikanos_entity_foundation.py.bak`.

---

## 10. Known REVIEW / TODO items

Carried forward from the blueprint. **None was resolved by inventing anything.**

### 10.1 Implemented as an explicit `[INFER]` the blueprint approved

| Item | Implementation |
|---|---|
| `amenity.status → amenity_status.id` | FK added. IKANOS declares none, but the id ranges align exactly (0–3). |
| `package.amenity_type → amenity_type.id` | FK added. IKANOS has a bare `smallint`. |
| `value_alert` — 6 FKs | Added. IKANOS declares **no** FKs at all on this table. |
| `value_alert_limit_config.device_id` | Nullable column + FK added alongside the IKANOS `device_name` key. |
| `battery_life_stat.device_id` | FK added; IKANOS has none. |
| `room_service_request_item.service_category_item_id` | IKANOS `faciliti_service_id` has no FK target table anywhere in the dump; repointed. |
| `notification_result.receiver_id`, `notification_receiver.app_user_id` | FKs added; IKANOS stores bare integers. |
| `value_alert_limit_config` unique key, `notification_template` unique key | Added; IKANOS declares none. |

Each is flagged in the model docstring. If any turns out to be wrong, dropping
the constraint is a one-line migration.

### 10.2 Unresolved — blocking or commercially significant

| # | Item | Status |
|---:|---|---|
| **10** | **Room tariff and payment state.** `packages` has no `price`; `invoices` has no `status`. Bookings needs rate, taxes, payment method, advance, balance — **no source exists**. | Columns NOT created. Blocks the Bookings module. |
| **5** | **Holidays** [CONFLICT]. `role_modules` has a `holidays` module and `occasion_types` has a `Holiday` row, but there is no `holiday` table and no `lock_message` column — and the HMS screen is built around a lock message. | Mapped to `occasion`; `notification_template` is the nearest field. No `lock_message` invented. |
| **6** | **Facility scoping.** `stay`, `job_order` and `promo_code` carry no `facility_id`; `daily_dual_data_point`'s PK excludes it, so that table is single-facility as built. | Preserved verbatim. Needs a single-vs-multi-facility decision. |
| **9** | Facility operating settings — `timezone`, default check-in/out times, single-line `address`, `logo`. | Not created. |
| **11** | Guest ID document **type** and **number**. `user_documents` stores an attachment and an approval status only. | Not created. |
| **12** | `app_user.is_active`. The documented `LOGIN.USER_INACTIVE` error has no backing column; `facility_user.status` is the nearest. | Not created. |
| **13** | `service_request.priority`. | Not created. |
| **7** | `room_service_request` / `room_service_request_item` — possibly Porta-only. | Tables created, module unbuilt. |
| **8** | `other_device` — Power View's only candidate source besides `device_stat`; the `EC` column's purpose is undocumented. | Table created with no FKs, as in IKANOS. |
| **3** | `status SMALLINT` soft-delete semantics on ~30 tables are undocumented. | Column preserved; meaning unconfirmed. |
| **14** | `mqtt_broker.broker_password` is clear text in IKANOS. | Column type unchanged (it is an application-layer concern); **must be encrypted at rest before any credential is written**. |
| **15/16** | Feedback (4 tables) and payments (3 tables) excluded on the evidence that no HMS module consumes them. | Not created. |
| **1** | `facility.currency_id` has no `currencies` table in the dump. | Column kept, no FK. |
| **—** | `value_alert.device_status_id` — purpose undocumented, no FK target identified. | Column kept as a plain integer. |

---

## 11. Deviations from the approved blueprint

Two, both reported rather than silently chosen.

### D1 — `legacy_id` is on 62 tables, not all 92

**Blueprint §2.3 / §5.0** state `legacy_id` is implicit on every table.
**Implemented:** on the 62 T2 (UUID) and T3 (BIGINT identity) tables only.

Omitted from:

- the **16 T1 lookup tables** — their primary key *is* the IKANOS integer id,
  seeded verbatim, so `legacy_id` would be an exact duplicate of the PK;
- the **14 composite-natural-PK tables** — IKANOS has no single surrogate
  integer key for those rows, so there is nothing to preserve.

The blueprint's own §12.6 also calls `legacy_id` "the original IKANOS integer
key", which those 30 tables either already hold or never had. The prompt's
wording — "only on tables where the blueprint specifies it" — was read the same
way. **If you want the literal reading instead, it is a one-line change to
`HMSBase` plus a regenerated migration.**

### D2 — Constraint name prefixes

The blueprint's illustrative index names use a `ux_` prefix (`ux_stay_internal_ref`).
The implementation uses the project's existing SQLAlchemy naming convention —
`uq_` for unique constraints, `ix_` for indexes, `fk_`, `pk_`, `ck_`. Cosmetic;
the columns and uniqueness are exactly as specified. Keeping the established
convention is what makes `alembic check` stable.

### Not a deviation, but worth stating

`app/models/enums.py`, `app/db/base.py`, `app/db/verify_schema.py`,
`tests/test_schema_foundation.py` and `app/models/__init__.py` were **rewritten**,
not edited — all five were Phase 1 artefacts describing the 39-table design.
`app/core/config.py`, `app/db/session.py`, `migrations/env.py`, `alembic.ini`
and `app/main.py` are **unchanged**.

---

## 12. Git safety

- `backend/` is untracked in git (`?? backend/`); no tracked file was
  overwritten or deleted. Only `package-lock.json` and `HMS-Data-Gap-Analysis.md`
  are modified/untracked at the repo root, both pre-existing and untouched.
- **`backend/.gitignore` was created** to ignore `.env`, `__pycache__/`,
  `.pytest_cache/`, virtualenvs and `docs/archive/*.sql`. `.env.example` is
  explicitly kept.
- No credential appears in any file created by this phase. `.env` was read only
  through `app.core.config`.
- Nothing was committed. Nothing was pushed.

---

## 13. Commands used for validation

```bash
cd backend

# full cycle
alembic upgrade head
alembic downgrade base
alembic upgrade head
alembic check                      # -> "No new upgrade operations detected."

# schema inventory report (exit 0 = PASS)
python -m app.db.verify_schema

# automated schema tests
python -m pytest tests -q          # -> 151 passed

# raw counts
psql -d hms_db -c "SELECT count(*) FROM information_schema.tables
                   WHERE table_schema='public' AND table_name<>'alembic_version';"   -- 92
psql -d hms_db -c "SELECT count(*) FROM pg_type t JOIN pg_namespace n
                   ON n.oid=t.typnamespace WHERE n.nspname='public' AND t.typtype='e';" -- 34
psql -d hms_db -c "SELECT count(*) FROM information_schema.table_constraints
                   WHERE table_schema='public' AND constraint_type='FOREIGN KEY';"      -- 240
```

`verify_schema` echoes SQL when `DEBUG=true` in `.env`; run it with `DEBUG=false`
for a clean report.

---

## 14. Scope statement

Delivered: the database foundation only.

- **No seed data.** No business record, user, device, dashboard or demo row was
  inserted. A test asserts every one of the 92 tables is empty.
- **No API.** No FastAPI route, CRUD, auth or endpoint was created.
- **No frontend change.** No file under `src/` was read for modification or
  written.

**STOP.** Seed data, APIs and frontend integration are Phase 2.
