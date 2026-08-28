# PHASE 1.8 — HMS SEED DATA

**Date:** 2026-08-17
**Source of truth:** [`FINAL_HMS_DATABASE_BLUEPRINT.md`](FINAL_HMS_DATABASE_BLUEPRINT.md) + the IKANOS SQL dump
**Migration:** `0e2687233b59` — unchanged, no new revision
**Scope:** demo data only. No schema change, no API, no frontend change.

---

## 1. Architecture

```
seeds/run_seed.py  ->  SQLAlchemy  ->  PostgreSQL hms_db  ->  (Phase 2 FastAPI)
```

Seed *scripts* live in the backend repo; seed *records* live only in `hms_db`.
No business data is embedded in the frontend, and none is hardcoded in an API
layer — there is no API layer yet.

## 2. Layout

```
backend/seeds/
├── __init__.py
├── helpers.py              deterministic ids, idempotent upsert, demo clock
├── run_seed.py             orchestrator: one transaction + row-count report
├── data/
│   ├── reference.py        lookup rows transcribed from the IKANOS dump
│   └── countries.json      all 239 real country rows, extracted from the dump
└── steps/                  11 steps, strict dependency order
    ├── reference_data.py   1  lookup / reference data
    ├── facility.py         2  organisation, facility, property hierarchy
    ├── people.py           3  departments, users, roles, permissions
    ├── rooms.py            4  amenity types, packages, rooms
    ├── stays.py            5  stays, occupants, allocations, invoices
    ├── services.py         6  service catalogue, requests, maintenance
    ├── devices.py          7  firmware, devices, MQTT, commands
    ├── telemetry.py        8  telemetry, health, energy, dashboard KPIs
    ├── alerts.py           9  alerts, incidents, value alerts
    ├── activity.py        10  activity feed + notification dispatch
    └── operations.py      11  job orders, keys, scheduler, marketing
```

## 3. Commands

```bash
cd backend
python -m seeds.run_seed              # seed, then print the report
python -m seeds.run_seed --report     # report only, writes nothing
python -m pytest tests -q             # 189 tests
```

Credentials come from `app.core.config` (`.env`). Nothing is hardcoded and
nothing is printed.

## 4. The demo scenario

One organisation, **Inspornics Hospitality**, operating one facility,
**Ikanos Grand Chennai** (`facility_uid = ikg`).

| | |
|---|---|
| Property hierarchy | Tower A → Floor 1/2/3 via `property_chain` |
| Rooms | 24 guest rooms + 3 non-room amenities (restaurant, gym, conference) |
| Room states | all 4 IKANOS statuses: Available, Occupied, Unavailable, Allotted |
| Room conditions | all 4: Dirty, Low battery, Under maintenance, Sanitation |
| Users | 13 — 1 bootstrap + 6 staff + 6 guests |
| Roles | 7, covering all 5 `role_type` values incl. the UI-hidden `system_user` |
| Stays | 6, covering pending / active / checkout pending / checked out / cancelled |
| Devices | 14 across 3 instrumented rooms + 2 standalone |
| Alerts → incidents | 9 alerts → 5 incidents → 14 history events |
| Energy | 24 hourly readings × 3 meters |
| Dashboard KPIs | 5 metric types × 7 days |

**Only one facility.** `daily_dual_data_point`'s primary key is
`(metric_date, metric_type)` and excludes `facility_id`, so a second facility
could not hold its own dashboard KPIs — blueprint OPEN DECISION #6.

## 5. Reference data is real, not invented

Every lookup row was extracted from `Dump20230928 (1).sql`, with the IKANOS
integer ids preserved because the T1 primary-key tier depends on them:

| Table | Rows | Table | Rows |
|---|---:|---|---:|
| `country` | 239 | `alert_type` | 16 |
| `device_param` | 35 | `notification_template` | 16 |
| `activity_type` | 22 | `command_type` | 10 |
| `role_module` | 18 | `service_type` | 7 |
| `service_status` | 5 | `incident_event` | 5 |
| `entity_type` | 5 | `amenity_status` | 4 |
| `amenity_condition` | 4 | `incident_status` | 4 |
| `key_type` | 4 | `occasion_type` | 4 |
| `device_type` | 4 | | |

A test asserts these match the dump exactly, in order.

## 6. Idempotency

Two mechanisms, no random UUIDs anywhere:

- **Deterministic ids** — `uuid5(DEMO_NAMESPACE, "table:natural_key")` for every
  UUID-keyed row.
- **Natural keys** — for BIGINT-identity tables that have no stable surrogate:
  `device_stat(device_id, device_param_id, timestamp)`,
  `device_health_stat(device_id, created_on)`,
  `device_alert(device_id, alert_type, created_on)`,
  `activity(activity_type_id, entity_type_id, entity_id)`, and so on.

`legacy_id` was deliberately **not** used as the idempotency key: it belongs to
IKANOS migration traceability (blueprint §2.3), not to demo bookkeeping. It
stays NULL on every seeded row.

The demo clock is pinned to `DEMO_NOW = 2026-08-17 12:00 UTC` so repeated runs
write identical timestamps. Anchoring to "now" would defeat idempotency.

Verified: runs 1, 2 and 3 produce byte-identical row-count reports.

## 7. Safety properties

| Property | How it is achieved | Verified |
|---|---|---|
| Transaction safety | all 11 steps in one transaction; rollback + exact failing step on error | injected a failure at step 9 → 0 tables changed |
| FK safety | dependency-ordered steps, constraints fully enabled | `VALIDATE CONSTRAINT` re-run on all 240 FKs |
| No FK bypass | `session_replication_role` never touched | grep-clean |
| No schema change | DML only; fingerprint compared before/after | tables 92, enums 34, FKs 240, indexes 352 |
| No secrets | config read from `.env` via `app.core.config` | no credential in any seed file |

The circular-FK bootstrap the blueprint predicted (§12.6) is handled by
`facility._bootstrap_user`: a first `app_user` whose `created_by` points at
itself, exactly as IKANOS does.

## 8. Intentionally empty tables

**None.** All 92 approved tables carry meaningful, connected demo rows.

## 9. Fields deliberately left unpopulated

Recorded here so a later phase does not mistake absence for oversight.

| Field | Why nothing was seeded |
|---|---|
| `package.price` | Column does not exist. Room tariff has no source — **OPEN DECISION #10**, still unresolved. No price was smuggled into `metadata` either; a test enforces this. |
| `invoice.status` | Column does not exist. Payment state has no source — OPEN DECISION #10. Invoice amounts are seeded and internally consistent (`total = net + tax`), sourced from `service_category_item.price_per_unit`, the only price in the schema. |
| `service_request.priority` | Column does not exist in IKANOS. |
| `occasion.lock_message` | Column does not exist. Holidays are `occasion` rows with `occasion_type = 'Holiday'`; the hub message lives in `notification_template` — **OPEN DECISION #5**, unresolved. |
| `device.ip_address` / `mac_address` / `last_seen` | Columns do not exist. Connectivity is `health_status`; "last seen" derives from `device_health_stat.created_on`. |
| `alert_type.severity` | Column does not exist. Severity is on `device_alert.alert_severity`, whose only values are `warning` and `critical`. |
| `facility.currency_id` | Left NULL — there is no `currencies` table to point at. |
| `value_alert.device_status_id` | Set to `1` only to satisfy NOT NULL; the column has no documented meaning and no FK target in IKANOS. **REVIEW.** |

## 10. Synthetic identity policy

- Every email uses the reserved `.invalid` TLD (RFC 2606) — none can resolve.
- Every phone number is in a reserved `+9100000…` demo range.
- Every `password_hash` is the literal `!seed-no-login`, which no hashing
  scheme can produce, so **no seeded account can be authenticated against**.
- `mqtt_broker.broker_password` is `!seed-placeholder`. IKANOS stores this in
  clear text; HMS must encrypt it before any real credential is written
  (OPEN DECISION #14).

Tests enforce all four.

## 11. Validation

189 tests pass: 151 schema (Phase 1.7) + 38 seed (this phase).

One Phase 1.7 test was superseded: `test_no_business_data_was_seeded` asserted
every table was empty, which was correct then and is wrong now. It is replaced
by `test_schema_suite_is_independent_of_seeded_data`, and the data-level
assertions moved to `tests/test_seed_data.py`. That file skips itself entirely
when the database is unseeded, so the schema suite still passes on a bare
foundation.

Workflow chains asserted end to end:

```
facility -> property -> property_chain -> amenity
app_user -> user_role -> role -> role_module_permission -> role_module
guest -> stay -> room_allocation -> amenity
stay -> stay_user
service_type -> service_category -> service_category_item -> service_request_item
service_request -> stay / amenity / app_user
device -> device_stat -> device_param
device -> device_health_stat
device -> device_alert -> device_incident -> incident_history
app_user -> notification_receiver -> notification_result
activity -> activity_notifier
stay -> access_key -> user_device_acl
device -> energy_stat -> amenity
```
