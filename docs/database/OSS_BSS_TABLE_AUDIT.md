# OSS / BSS Table Audit - MySQL `inspironics_app`

Read-only classification of all **94** tables in the HMS BSS MySQL database against the FleetXplorer OSS PostgreSQL database (`insp_iot`) as reference.

| | |
|---|---|
| Database | `inspironics_app` on MySQL 8.4.13 |
| Connection | TLS `TLS_AES_256_GCM_SHA384`, session `READ ONLY` |
| Alembic revision | `a3f1c8e2d904` |
| Tables / views | 94 / 0 |
| FK columns | 37 enum columns, 242 FK columns |
| Routines / triggers | 0 / 0 |
| Generated | 2026-11-16 |

> **Read-only.** Every statement was a `SELECT` against `information_schema`, `SHOW GRANTS` or `COUNT(*)`, run in a `SET SESSION TRANSACTION READ ONLY` session via `scripts/audit_bss_mysql.py`, which rejects any statement whose first keyword could mutate. No table or row was created, altered, renamed, migrated or deleted, and no application code was changed.

## Summary

| Class | Tables | Meaning |
|---|---:|---|
| **OSS** | 11 | Device-derived. The HMS read path sits on an OSS route prefix, so with `OSS_ENABLED=true` these MySQL copies are bypassed in favour of `insp_iot`. |
| **Shared** | 3 | Live on both sides of the boundary. Cannot be assigned to one domain without breaking the other. |
| **Uncertain** | 5 | Device-plane by nature, but no OSS counterpart, no OSS route, and (mostly) no code reading them. Needs an owner decision. |
| **BSS** | 75 | Hospitality business data. HMS is the system of record. |
| **Total** | **94** | |

### Method and evidence sources

A table was classified on four independent signals, not on its name:

1. **OSS schema correspondence** - `oss-service/app/db/tables.py`, the transcribed `insp_iot` definitions: `insp_device`, `insp_device_health`, `insp_device_state`, `insp_device_state_type`, `insp_device_performance`, `insp_device_alert`, `insp_site`.
2. **Route ownership** - `app/core/oss_routes.py`, the single source of truth for which API paths are OSS. Only these prefixes are forwarded, and GETs only:

   | OSS domain | v1 prefixes |
   |---|---|
   | `device` | `/device-types`, `/devices` |
   | `telemetry` | `/device-params`, `/device-stats`, `/device-current-stats`, `/other-device-readings` |
   | `alert` | `/alert-types`, `/alerts` |
   | `energy` | `/energy-stats` |

3. **Endpoint -> source mapping** - `oss-service/docs/INTEGRATION_MAPPING.md`, which records for every OSS endpoint its real `insp_iot` source, or an explicit **503** where none exists.
4. **Code reachability** - every `__tablename__` in `app/models/` resolved to its model class, then matched against all 28 service modules and 23 endpoint modules to find which tables are actually read.

Column-level comparison was done against the transcribed OSS definitions. A **live `insp_iot` connection was not available** - `oss-service/.env` does not exist, only `.env.example` - so OSS-side evidence is documentary (the committed table definitions and integration mapping), not queried. This is called out per table below where it matters.

---

## OSS - 11 tables

Device-derived data whose read path is an OSS route prefix. With `OSS_ENABLED=true` the request is forwarded to the OSS microservice and **the MySQL table below is not read**. Note that four of these have no OSS source at all: OSS answers them with an empty list or an explicit 503, so turning dispatch on *loses* data that exists here today.

| Table | Rows | Cols | HMS route (OSS-surfaced) | OSS source in `insp_iot` | Read by |
|---|---:|---:|---|---|---|
| `alert_type` | 16 | 4 | `/alert-types` | `DISTINCT insp_device_alert.alert_type` | `services/alert` |
| `battery_life_stat` | 12 | 9 | `/devices/{id}/health` | none - OSS returns `[]` | `services/device` |
| `device_alert` | 9 | 10 | `/alerts` | `insp_device_alert` | `services/alert` |
| `device_current_stat` | 14 | 7 | `/device-current-stats` | latest `insp_device_performance.param_data` per `device_uid` | `services/telemetry` |
| `device_health_stat` | 168 | 7 | `/devices/{id}/health` | `insp_device_health` | `services/device` |
| `device_param` | 35 | 7 | `/device-params` | `DISTINCT` keys of `insp_device_performance.param_data` | `services/energy`, `services/telemetry` |
| `device_stat` | 504 | 9 | `/device-stats` | `insp_device_performance.param_data` exploded per parameter | `services/telemetry` |
| `device_type` | 4 | 5 | `/device-types` | `DISTINCT insp_device.device_type` | `services/alert`, `services/device`, `services/devices_write`, `services/job_order`, `services/telemetry` |
| `energy_stat` | 72 | 7 | `/energy-stats` | `insp_device_performance.param_data.active_energy` (cumulative) | `services/energy` |
| `other_device` | 12 | 17 | `/other-device-readings` | none - OSS returns **503** | `services/telemetry` |
| `sensor_operation_stat` | 42 | 6 | `/devices/{id}/health` | none - OSS returns `[]` | `services/device` |

**Evidence per table**

- **`alert_type`** - OSS derives the registry; name is the stored code (no OSS name lookup).
  - FK -> _none_ &nbsp;|&nbsp; referenced by `device_alert`, `device_incident`
- **`battery_life_stat`** - Device-derived and on an OSS prefix, but insp_iot has no battery table; OSS serves an empty history.
  - FK -> `device` &nbsp;|&nbsp; referenced by _nothing_
- **`device_alert`** - `alert_type`, `alert_severity`, `alert_data` (JSON) all match the OSS table.
  - FK -> `alert_type`, `amenity`, `app_user`, `device` &nbsp;|&nbsp; referenced by `device_incident`
- **`device_current_stat`** - `device_stats` column is the JSON snapshot OSS stores as `param_data`.
  - FK -> `device` &nbsp;|&nbsp; referenced by _nothing_
- **`device_health_stat`** - Column-for-column: `device_health_status`<-`health_status`, `device_temperature`<-`temperature`.
  - FK -> `device` &nbsp;|&nbsp; referenced by _nothing_
- **`device_param`** - Registry of telemetry parameter names; OSS derives it from JSONB keys.
  - FK -> `device_type` &nbsp;|&nbsp; referenced by `device_stat`
- **`device_stat`** - Largest table in the database (504 rows). Columns `device_param_id`/`device_param_value` are the exploded form of OSS's JSONB.
  - FK -> `device`, `device_param` &nbsp;|&nbsp; referenced by _nothing_
- **`device_type`** - Derived registry in OSS, real table here. 4 rows vs OSS's distinct-value set.
  - FK -> _none_ &nbsp;|&nbsp; referenced by `command_type`, `device`, `device_param`, `feature`, `firmware`, `user_device_acl`, `value_alert`
- **`energy_stat`** - On an OSS prefix but **503**: hourly `energy_consumed` needs a business-confirmed delta/bucketing rule (open question #2).
  - FK -> `amenity`, `facility` &nbsp;|&nbsp; referenced by _nothing_
- **`other_device`** - Third-party meter readings. On an OSS prefix but explicitly unsupported (`oss_adapter_not_mapped`).
  - FK -> _none_ &nbsp;|&nbsp; referenced by _nothing_
- **`sensor_operation_stat`** - Device-derived and on an OSS prefix; no OSS counterpart, so operation history is empty under OSS.
  - FK -> `amenity`, `device` &nbsp;|&nbsp; referenced by _nothing_

> **Caveat on the four unsupported ones.** `battery_life_stat` (12 rows), `sensor_operation_stat` (42 rows), `other_device` (12 rows) and `energy_stat` (72 rows) are classified OSS because they sit on OSS prefixes - but `insp_iot` has nothing behind them. They hold **138 rows of real data today** that an OSS cutover would stop serving. They are the strongest argument for treating the OSS prefix list as a routing decision rather than an ownership decision.

---

## Shared - 3 tables

Referenced from both sides of the boundary. Each is a genuine two-owner table, not an unresolved question.

### `device`

- **Rows / columns:** 14 / 28
- **OSS correspondence:** `insp_device`
- **Used by:** `/devices` (OSS) **and** 15 other tables' foreign keys
- **Code paths:** `services/alert`, `services/device`, `services/devices_write`, `services/energy`, `services/job_order`, `services/job_order_write`, `services/limit_config`, `services/occupancy`, `services/reports`, `services/room_devices`, `services/stays_write`, `services/telemetry`, `endpoints/devices`, `endpoints/room_devices`, `endpoints/telemetry`
- **FK ->** `amenity`, `app_user`, `device`, `device_type`, `facility`, `firmware`
- **Referenced by:** 16 table(s) - `access_key`, `battery_life_stat`, `device`, `device_alert`, `device_command`, `device_current_stat`, `device_health_stat`, `device_incident`, `device_stat`, `job_order_device`, `lock_activity_log`, `mqtt_topic`, `sensor_operation_stat`, `user_device_acl`, `value_alert`, `value_alert_limit_config`
- **Reason:** Strongest OSS correspondence of any table (`device_uid`, `model`, `manufacturer_name`<-`manufacturer`, `mfg_date`, `parent_device_id`, `device_type`, `device_name`, `appliance_name`<-`appliance`, `facility_id`<-`site_id`, `current_firmware_version`<-`firmware_version`, `health_status`, `status`). But it is also the FK target of `access_key`, `battery_life_stat`, `device_alert`, `device_command`, `device_current_stat`, `device_health_stat`, `device_incident`, `device_stat`, `job_order_device`, `lock_activity_log`, `mqtt_topic`, `sensor_operation_stat`, `user_device_acl`, `value_alert`, `value_alert_limit_config` - several of which are BSS by decision. Cannot be retired with the OSS cutover.

### `facility`

- **Rows / columns:** 1 / 19
- **OSS correspondence:** `insp_site` - **mapping unconfirmed**
- **Used by:** every BSS domain (12 services/endpoints)
- **Code paths:** `services/access`, `services/access_write`, `services/catalog`, `services/devices_write`, `services/facility`, `services/facility_write`, `services/maintenance`, `services/occupancy`, `services/reports`, `services/stays_write`, `endpoints/facilities`, `endpoints/facility_write`
- **FK ->** `app_user`, `attachment`, `organisation`
- **Referenced by:** 29 table(s) - `activity`, `amenity`, `amenity_type`, `attachment`, `daily_dual_data_point`, `department`, `device`, `device_incident`, `energy_stat`, `facility_event`, `facility_user`, `feature`, `invoice`, `job_function`, `lock_activity_log`, `maintenance_request`, `mqtt_broker`, `occasion`, `package`, `property`, `property_chain`, `property_type`, `role`, `service_category`, `service_category_item`, `service_request`, `user_role`, `value_alert`, `value_alert_limit_config`
- **Reason:** `insp_device.site_id` is mapped to `facility_id` by the device adapter, so OSS reads reach into this table's key space. HMS owns the row itself (`organisation` -> `facility` -> `property`), and 29 tables FK to it - second only to `app_user` (51). Open question #4 in INTEGRATION_MAPPING.md asks the business to confirm site==facility; until then the OSS half of this relationship is asserted, not proven (`site_id` is null in current OSS data).

### `room_device_map`

- **Rows / columns:** 0 / 7
- **OSS correspondence:** joins to `insp_device.device_id`
- **Used by:** `/room-devices` (BSS-served)
- **Code paths:** `services/room_devices`
- **FK ->** `amenity`, `app_user`
- **Referenced by:** 0 table(s)
- **Reason:** The explicit HMS<->OSS bridge. `oss_device_id char(36)` is an OSS UUID, not a local `device.id`, and there is deliberately no FK on it because the referent lives in another database. OSS is site/customer-scoped and has no room concept (decision #1), so this table is how a room acquires devices when `OSS_ENABLED=true`. Currently **0 rows** - the bridge exists but is unpopulated.

---

## Uncertain - 5 tables

All five are device-plane by nature but have **no table in `insp_iot`, no OSS route**, and four of the five are read by no service or endpoint. They cannot be called OSS (OSS cannot serve them) and calling them BSS asserts an ownership nobody has stated. They need an explicit owner decision.

| Table | Rows | Cols | Read by | FK -> |
|---|---:|---:|---|---|
| `command_type` | 10 | 5 | _none_ | `device_type` |
| `device_command` | 7 | 9 | _none_ | `app_user`, `command_type`, `device` |
| `firmware` | 6 | 17 | `services/device`, `services/devices_write`, `endpoints/devices`, `endpoints/devices_write` | `app_user`, `device_type` |
| `mqtt_broker` | 1 | 11 | _none_ | `facility` |
| `mqtt_topic` | 12 | 8 | _none_ | `device`, `mqtt_broker` |

- **`command_type`** - Lookup for `device_command`, keyed by `device_type_id`. Inherits that table's ambiguity; unreferenced in code.
- **`device_command`** - Device actuation requests (`command_data`, `processing_status`). Device-plane by nature, but OSS exposes no command surface and device WRITES are deliberately retained in HMS (`oss_routes.py`). Unreferenced by any service or endpoint.
- **`firmware`** - Firmware catalogue (version, URL, CRC, release notes) per device type. OSS has no firmware table, yet `insp_device.firmware_version` is surfaced through `/devices` and `/device-types/{id}` counts distinct firmware versions - so the *values* are OSS-derived while the *catalogue* is HMS-owned. Read by `services/device` and `services/devices_write`.
- **`mqtt_broker`** - IoT transport configuration (broker host, port, credentials) scoped to a facility. No OSS counterpart in `insp_iot`, no OSS route, and **no service or endpoint reads it**. It describes device ingestion, which is OSS's concern, but HMS currently owns the row.
- **`mqtt_topic`** - Per-device MQTT topic mapping (`device_id` -> `topic_name`). Same position as `mqtt_broker`: device-plane data with no OSS table, no OSS route and no code reading it.

Suggested resolution: `mqtt_broker` / `mqtt_topic` / `device_command` / `command_type` move to OSS if and when device ingestion and actuation move there; `firmware` stays BSS as a catalogue whose *observed* values come from OSS. **Nothing in this report acts on that** - it is a recommendation for the owners.

---

## BSS - 75 tables

Hospitality business data. HMS is the system of record; `insp_iot` has no counterpart for any of these.

### Identity, roles and access control (11)

User accounts, RBAC and session state. No device semantics; no counterpart anywhere in `insp_iot`.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `activity_role_association` | 34 | 4 | _none_ |
| `app_user` | 18 | 29 | `services/access`, `services/access_write`, `services/alert`, `services/auth`, `services/devices_write`, `services/facility`, `services/facility_write`, `services/job_order`, `services/job_order_write`, `services/maintenance`, `services/maintenance_write`, `services/notification`, `services/occupancy`, `services/service`, `services/services_write`, `services/stay`, `services/stays_write` |
| `department` | 5 | 9 | `services/access`, `services/access_write`, `services/maintenance`, `services/maintenance_write`, `services/reports`, `services/service`, `services/services_write` |
| `facility_user` | 14 | 6 | `services/access`, `services/stays_write` |
| `job_function` | 5 | 9 | `services/access`, `services/access_write` |
| `role` | 7 | 10 | `services/access`, `services/access_write`, `services/auth`, `services/reports`, `endpoints/access`, `endpoints/access_write`, `endpoints/alerts`, `endpoints/auth`, `endpoints/devices`, `endpoints/devices_write`, `endpoints/energy`, `endpoints/facilities`, `endpoints/facility_write`, `endpoints/job_orders`, `endpoints/maintenance`, `endpoints/notifications`, `endpoints/occupancy`, `endpoints/reports`, `endpoints/room_devices`, `endpoints/services`, `endpoints/services_write`, `endpoints/stays`, `endpoints/stays_write`, `endpoints/telemetry` |
| `role_module` | 18 | 6 | `services/access`, `services/access_write`, `services/auth` |
| `role_module_permission` | 65 | 6 | `services/access`, `services/access_write`, `services/auth` |
| `user_device` | 4 | 12 | _none_ |
| `user_role` | 16 | 6 | `services/access`, `services/access_write`, `services/auth`, `services/reports` |
| `user_token` | 3 | 8 | _none_ |

### Stay / guest lifecycle (7)

The core hospitality record: reservations, occupants, documents and billing. OSS has no guest concept.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `import_job` | 3 | 14 | `services/stays_write`, `endpoints/stays_write` |
| `invoice` | 2 | 19 | `services/stay`, `services/stays_write`, `endpoints/stays` |
| `room_allocation` | 18 | 9 | `services/occupancy`, `services/stay`, `services/stays_write` |
| `stay` | 69 | 21 | `services/occupancy`, `services/reports`, `services/service`, `services/services_write`, `services/stay`, `services/stays_write`, `endpoints/stays`, `endpoints/stays_write` |
| `stay_package` | 6 | 7 | `services/stay` |
| `stay_user` | 8 | 10 | `services/occupancy`, `services/stay`, `services/stays_write` |
| `user_document` | 3 | 9 | `services/stay` |

### Organisation, property and files (7)

The ownership hierarchy above a facility plus shared attachments. Purely commercial structure.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `attachment` | 8 | 8 | `services/catalog` |
| `country` | 239 | 9 | `services/access_write`, `services/facility`, `endpoints/facilities` |
| `facility_event` | 3 | 17 | `services/catalog`, `services/facility_write` |
| `organisation` | 1 | 7 | _none_ |
| `property` | 4 | 9 | `services/alert`, `services/device`, `services/energy`, `services/facility`, `services/facility_write`, `services/occupancy`, `services/room_devices`, `services/stay`, `services/telemetry`, `endpoints/facilities` |
| `property_chain` | 3 | 10 | `services/alert`, `services/device`, `services/energy`, `services/facility`, `services/facility_write`, `services/occupancy`, `services/room_devices`, `services/stay`, `services/telemetry` |
| `property_type` | 1 | 9 | `services/facility` |

### Amenity / room inventory (5)

Rooms and their saleable attributes. Decision #1 records that **OSS is site/customer-scoped with no room or amenity concept**, which is precisely why `room_device_map` has to exist.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `amenity` | 27 | 15 | `services/alert`, `services/catalog`, `services/device`, `services/devices_write`, `services/energy`, `services/facility`, `services/facility_write`, `services/job_order`, `services/job_order_write`, `services/limit_config`, `services/maintenance`, `services/maintenance_write`, `services/occupancy`, `services/room_devices`, `services/service`, `services/services_write`, `services/stay`, `services/stays_write`, `services/telemetry`, `endpoints/facility_write` |
| `amenity_condition` | 5 | 4 | `services/facility`, `services/occupancy`, `services/stays_write` |
| `amenity_condition_status` | 4 | 5 | `services/facility`, `services/occupancy`, `services/stays_write` |
| `amenity_status` | 4 | 4 | `services/facility`, `services/facility_write`, `services/occupancy`, `services/stays_write` |
| `amenity_type` | 5 | 10 | `services/catalog`, `services/facility`, `services/facility_write`, `services/occupancy`, `services/stay` |

### Packages, features and marketing (8)

Rate plans, bundled features and promotions. Revenue-side only.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `feature` | 9 | 10 | `services/catalog`, `services/facility_write` |
| `occasion` | 4 | 17 | `services/catalog`, `services/facility_write`, `endpoints/facility_write` |
| `occasion_type` | 4 | 5 | `services/catalog`, `services/facility_write` |
| `package` | 8 | 12 | `services/catalog`, `services/facility`, `services/facility_write`, `services/occupancy`, `services/reports`, `services/stay`, `services/stays_write`, `endpoints/facility_write` |
| `package_feature` | 17 | 8 | `services/catalog`, `services/facility_write` |
| `promo_code` | 3 | 16 | `services/catalog`, `services/facility_write`, `services/services_write` |
| `promo_code_amenity` | 8 | 6 | `services/catalog`, `services/facility_write` |
| `sub_package` | 7 | 5 | `services/catalog`, `services/facility_write` |

### Service requests and catalogue (8)

Guest-facing service ordering and its catalogue.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `room_service_request` | 3 | 11 | _none_ |
| `room_service_request_item` | 4 | 7 | _none_ |
| `service_category` | 15 | 12 | `services/maintenance`, `services/maintenance_write`, `services/service`, `services/services_write` |
| `service_category_item` | 22 | 14 | `services/maintenance`, `services/maintenance_write`, `services/service`, `services/services_write` |
| `service_request` | 7 | 25 | `services/service`, `services/services_write` |
| `service_request_item` | 8 | 11 | `services/service`, `services/services_write` |
| `service_status` | 5 | 4 | `services/maintenance`, `services/maintenance_write`, `services/service`, `services/services_write` |
| `service_type` | 7 | 4 | `services/maintenance`, `services/service`, `services/services_write` |

### Maintenance (4)

Staff maintenance workflow, including recurrence rules.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `maintenance_request` | 3 | 25 | `services/maintenance`, `services/maintenance_write` |
| `maintenance_request_amenity` | 6 | 8 | `services/maintenance`, `services/maintenance_write` |
| `maintenance_request_assignee` | 4 | 8 | `services/maintenance`, `services/maintenance_write` |
| `maintenance_request_recurrence` | 1 | 6 | `services/maintenance`, `services/maintenance_write` |

### Job orders (3)

Work dispatch. `job_order_device` FKs to `device`, but the order itself is a staff workflow artifact.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `job_order` | 3 | 15 | `services/job_order`, `services/job_order_write` |
| `job_order_amenity` | 4 | 4 | `services/job_order`, `services/job_order_write` |
| `job_order_device` | 2 | 4 | `services/job_order`, `services/job_order_write` |

### Incidents and value alerts (BSS **by explicit decision**) (6)

Device-adjacent but deliberately BSS. `app/core/oss_routes.py` states it directly: OSS has no incident table and no threshold-breach table, so it could never answer these. Incidents are acknowledged, assigned and resolved by HMS staff (`PATCH /incidents`); value alerts are breaches of the HMS-owned `/limit-configs`. INTEGRATION_MAPPING.md repeats this as **'Moved to HMS (BSS)'**.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `device_incident` | 5 | 14 | `services/alert`, `services/devices_write` |
| `incident_event` | 5 | 4 | `services/alert`, `services/devices_write` |
| `incident_history` | 14 | 8 | `services/alert`, `services/devices_write` |
| `incident_status` | 4 | 4 | `services/alert`, `services/devices_write` |
| `value_alert` | 3 | 16 | `services/alert`, `services/devices_write` |
| `value_alert_limit_config` | 4 | 16 | `services/alert`, `services/devices_write`, `services/limit_config` |

### Notifications and activity (8)

Staff notification fan-out and the activity feed that drives it.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `activity` | 10 | 13 | `services/notification`, `endpoints/notifications` |
| `activity_notifier` | 15 | 7 | `services/notification` |
| `activity_type` | 22 | 7 | `services/notification` |
| `entity_type` | 5 | 4 | `services/notification` |
| `notification` | 6 | 9 | `services/notification`, `endpoints/notifications` |
| `notification_receiver` | 6 | 11 | `services/notification` |
| `notification_result` | 6 | 9 | `services/notification` |
| `notification_template` | 16 | 7 | `services/notification` |

### Guest access and smart locks (4)

Key issuance and lock audit. These FK to `device`, so they are device-*adjacent*, but the semantics are business rules - which guest, for which stay, may open which room. `insp_iot` has no lock or key table.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `access_key` | 5 | 13 | `services/facility` |
| `key_type` | 4 | 4 | _none_ |
| `lock_activity_log` | 5 | 13 | _none_ |
| `user_device_acl` | 5 | 14 | _none_ |

### Energy KPIs (1)

`oss_routes.py` singles this out: '`/daily-data-points` is deliberately BSS (mixed KPIs)'. It blends device-derived and commercial figures, so it is not an OSS read even though `services/energy` uses it.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `daily_dual_data_point` | 35 | 7 | `services/energy` |

### Platform / infrastructure (3)

Migration state and the job scheduler. Not business data at all.

| Table | Rows | Cols | Read by |
|---|---:|---:|---|
| `alembic_version` | 1 | 1 | _none_ |
| `scheduler_job` | 5 | 9 | _none_ |
| `scheduler_job_execution` | 6 | 9 | _none_ |

---

## Incidental findings

Found while cross-checking models against the live schema. **All are reported only - nothing was changed.**

### 1. Schema drift: the `currency` table does not exist

`app/models/facility.py:248` declares `class Currency` with `__tablename__ = "currency"`, described as the "authoritative ISO 4217 currency master table". **There is no `currency` table in `inspironics_app`.**

Four models declare a `currency_id` FK to it:

| Model | File | Target |
|---|---|---|
| `Facility` | `app/models/facility.py:66` | `currency.id` |
| `Package` (rate plan) | `app/models/amenity.py:236` | `currency.id` |
| `ServiceCategoryItem` | `app/models/service.py:109` | `currency.id` |
| `Stay` | `app/models/stay.py:231` | `currency.id` |

Of those four, only `facility.currency_id` (`smallint`) exists as a column in MySQL - and it has no FK constraint, because its referent is absent. The other three `currency_id` columns are **not in the database at all**. Any query that loads the `currency` relationship, or that selects `Package.currency_id`, `ServiceCategoryItem.currency_id` or `Stay.currency_id`, will fail against this database.

### 2. Schema drift: `room_status_condition_applicability` does not exist

`app/models/amenity.py:173` declares `__tablename__ = "room_status_condition_applicability"`. That table is not in the database. The related `amenity_condition` (5 rows) and `amenity_condition_status` (4 rows) tables *do* exist and are read by `services/facility`, `services/occupancy` and `services/stays_write`.

Taken together, 1 and 2 mean **2 of the 95 declared models have no table**, while 93 of the 94 tables have a model (`alembic_version` is Alembic's own and correctly has none).

### 3. The OSS bridge is empty

`room_device_map` has **0 rows** - the only empty table in the database. It is the sole mechanism by which a room acquires devices when `OSS_ENABLED=true` (decision #1: OSS has no room concept). Until it is populated, enabling OSS dispatch yields rooms with no devices. `OSS_ENABLED` is currently `false`.

### 4. 15 tables are unreachable from any service or endpoint

`activity_role_association`, `command_type`, `device_command`, `key_type`, `lock_activity_log`, `mqtt_broker`, `mqtt_topic`, `organisation`, `room_service_request`, `room_service_request_item`, `scheduler_job`, `scheduler_job_execution`, `user_device`, `user_device_acl`, `user_token`.

These have models but no reader. Three clusters stand out: the MQTT/command group (in **Uncertain** above), the smart-lock group (`key_type`, `lock_activity_log`, `user_device_acl`), and room service (`room_service_request`, `room_service_request_item`) - the last of which holds live data (3 and 4 rows) and has an endpoint-shaped model but no endpoint.

### 5. OSS-side evidence is documentary, not queried

`oss-service/.env` does not exist (only `.env.example`, with `OSS_DATABASE_URL=` blank), so `insp_iot` could not be connected to. Every OSS-side claim here rests on `oss-service/app/db/tables.py` (transcribed from `tools/discover_schema.py` output) and `oss-service/docs/INTEGRATION_MAPPING.md`. **Column-level OSS facts in this report are therefore as current as those files, not as the live OSS database.** Re-run against a live `insp_iot` before acting on any migration decision.

---

## Open questions carried forward

From `oss-service/docs/INTEGRATION_MAPPING.md`, still unanswered and each one changes a classification above:

| # | Question | Affects |
|---|---|---|
| 1 | Is an HMS incident equivalent to OSS `insp_service_request`? | `device_incident` + 3 incident tables (currently BSS by decision) |
| 2 | How is hourly `energy_consumed` derived from the cumulative `active_energy` counter? | `energy_stat` (currently OSS, served 503) |
| 4 | Does OSS `site` map to HMS `facility`, and will `site_id` be populated? | `facility` (**Shared**) and every device's `facility_id` |

Plus, from this audit: **who owns `mqtt_*`, `device_command` / `command_type`, and `firmware`?** (the **Uncertain** five), and **what populates `room_device_map`?**

