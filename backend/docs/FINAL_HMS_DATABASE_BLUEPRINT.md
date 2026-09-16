# FINAL HMS DATABASE BLUEPRINT

**Phase:** 1.5 (blueprint only)
**Date:** 2026-08-16
**Status:** Design document. **No PostgreSQL change, no migration, no seed, no API was created.**
Alembic revision `8a8456154f0e` and the existing 39 tables are untouched.

---

## 0. Sources of truth and evidence rules

| Rank | Source | Used for |
|---:|---|---|
| 1 | **IKANOS SQL dump** `d:\Inspornics\DB_files\Dump20230928 (1).sql` — 108 `CREATE TABLE` blocks read directly | Every column, type, enum, PK, FK, index in this document |
| 2 | `backend/docs/IKANOS_HMS_SCHEMA_COMPARISON.md` | Table-by-table mapping, lookup-row values, accuracy verdict |
| 3 | IKANOS workflow docs `d:\Inspornics\HMS_ikanos\Ikanos_code\*.md` | Business purpose of each entity |
| 4 | HMS architecture — `role_modules` 18 rows ≡ the 15 sidebar modules; React feature folders in `src/features/` | Module → table dependency |
| 5 | `HMS-Data-Gap-Analysis.md` | Field-level frontend expectations |
| 6 | Current HMS 39-table schema (`app/models/*.py`, revision `8a8456154f0e`) | Disposition of what exists |

**Evidence labels used below**
- **[FACT]** — read from the dump.
- **[INFER]** — reasoned from the dump + workflow; stated as inference.
- **REVIEW** — required by HMS but **not supported by any source**. Recorded as REVIEW, **never invented as a column**.

**Invention rule applied:** the column lists below contain *only* columns that exist in the IKANOS dump, plus three technical columns declared openly in §2.3 (`id`, `legacy_id`, and the retained IKANOS `created_on`/`updated_on`). Every HMS frontend field with no IKANOS backing appears in §11 OPEN DECISIONS as REVIEW, not as a column.

---

## 1. Headline result

| Measure | Value |
|---|---:|
| IKANOS tables examined | **107** (101 `caleido` + 5 `caleido_notification` + 2 `caleido_scheduler`) |
| IKANOS → USE | **57** |
| IKANOS → ADAPT | **35** |
| IKANOS → MERGE (absorbed into another final table) | **7** |
| IKANOS → EXCLUDE | **8** |
| **FINAL HMS TABLE COUNT** | **92** |
| Current HMS tables kept unchanged | **1** |
| Current HMS tables removed outright | **4** |
| Brand-new HMS-invented business tables | **0** |

57 + 35 + 7 + 8 = **107** ✔ — every IKANOS table is classified exactly once.

The 92 final tables are 92 IKANOS tables (57 USE + 35 ADAPT), each of which additionally absorbs the 7 MERGE tables. **No table in the final list is an HMS invention.**

---

## 2. Global design rules

### 2.1 One database, not three
IKANOS runs `caleido`, `caleido_notification` and `caleido_scheduler`. HMS is a single FastAPI service over one PostgreSQL database. All three are folded into `hms_db` / `public`. The two `jobs` tables collide, so they are disambiguated by name:

| IKANOS | Final HMS |
|---|---|
| `caleido.jobs` (job orders, 15 cols) | `job_order` |
| `caleido_scheduler.jobs` (cron jobs, 8 cols) | `scheduler_job` |

### 2.2 Naming
- Singular `snake_case` table names (existing HMS convention, kept).
- IKANOS `created_on` / `updated_on` retained verbatim — **the HMS `created_at`/`updated_at` naming is dropped** (IKANOS uses `created_on`/`updated_on` on 99 tables).
- PostgreSQL reserved/ambiguous words renamed: `users`→`app_user`, `functions`→`job_function`, `keys`→`access_key`, `imports`→`import_job`, `templates`→`notification_template`.

### 2.3 Primary keys — three-tier policy
IKANOS uses `int`/`bigint AUTO_INCREMENT` throughout; **zero UUID columns exist in the dump** [FACT]. HMS Phase 1 used UUID everywhere. The blueprint adopts a tiered policy:

| Tier | PK type | Applies to | Count |
|---|---|---|---:|
| **T1 Lookup** | native `SMALLINT`/`INTEGER`, **seeded with the IKANOS ids** | reference tables whose ids are fixed and referenced by the frontend | 16 |
| **T2 Entity** | `UUID` (`uuid4`) | business/transactional entities | 65 |
| **T3 High-volume log** | `BIGINT GENERATED ALWAYS AS IDENTITY` | append-only telemetry, alert, notification and audit streams | 11 |

T1 is not negotiable: `amenity_statuses` id `0/1/2/3`, `service_statuses`, `alert_types`, `role_modules` ids are the values the HMS frontend already renders. Preserving the integer ids preserves IKANOS business meaning.

**Every table also carries `legacy_id BIGINT NULL UNIQUE`** — the original IKANOS integer key, so a live IKANOS install can be migrated without key collision. This is the only structural addition in the blueprint. → **OPEN DECISION #1.**

### 2.4 Audit columns
`created_on TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_on TIMESTAMPTZ NOT NULL DEFAULT now()` on all 92 tables (IKANOS has them on 99/101).
`created_by` / `updated_by` are carried **only on the 44 tables where IKANOS has them** [FACT] — they are not added anywhere else.

### 2.5 `facility_uid` — dropped
`facility_uid varchar(3)` appears on 91 IKANOS tables and is **not a foreign key anywhere** [FACT]; it is a denormalised copy of `facilities.facility_uid`. Its purpose is undocumented. It is **excluded from all 92 tables**; `facility.facility_uid` itself is retained. → **OPEN DECISION #2.**

### 2.6 Soft delete
IKANOS `status tinyint` (soft-delete flag) is carried as `status SMALLINT` **only where the dump has it**. Where a table has both a soft-delete `status` and a business status, the business status keeps its own name (e.g. `service_request.status` is the FK to `service_status`; `stay.status` is the stay-lifecycle enum). Semantics of the tinyint flag are undocumented → **OPEN DECISION #3.**

### 2.7 Enums
All enums use PostgreSQL native `ENUM` types with the **exact IKANOS value strings, lowercase as stored in the dump**. All 13 current HMS enums are discarded; none matched [FACT].

### 2.8 ON DELETE
Mirrors IKANOS: `CASCADE` on facility-, device- and stay-owned children; `NO ACTION`→`RESTRICT` on lookup/reference links. The HMS-invented `RESTRICT` on `booking.package_id` disappears with `booking`.

---

## 3. IKANOS TABLES → CLASSIFICATION (all 107)

Legend: **USE** = required, IKANOS business meaning and relationships preserved as-is · **ADAPT** = required, minor structural change for HMS/PostgreSQL · **MERGE** = represented inside another final table · **EXCLUDE** = not required by the HMS workflow/architecture, with evidence.

### 3.1 USE — 57 tables

| # | IKANOS table | Final HMS table | Why HMS requires it |
|---:|---|---|---|
| 1 | `organisations` | `organisation` | `facilities.org_id` is a NOT NULL FK — a facility cannot exist without one |
| 2 | `facility_users` | `facility_user` | User ↔ facility scope; the login flow resolves the facility from this |
| 3 | `properties` | `property` | Dashboard building and floor cards |
| 4 | `property_chains` | `property_chain` | The building → wing → floor → room chain (`level_one/two/three_id`) |
| 5 | `attachments` | `attachment` | Facility logo, offer icon, event image, guest ID scan, service-item icon |
| 6 | `countries` | `country` | Booking form country code + nationality (239 rows in the dump) |
| 7 | `amenity_statuses` | `amenity_status` | Occupancy vocabulary: `0` Available · `1` Occupied · `2` Unavailable · `3` Allotted |
| 8 | `amenity_conditions` | `amenity_condition` | Occupancy condition badges: Dirty · Low battery · Under maintenance · Sanitation |
| 9 | `amenity_condition_status` | `amenity_condition_status` | Room ↔ condition junction with per-condition status |
| 10 | `sub_packages` | `sub_package` | Bookings "Sub Packages" selector |
| 11 | `features` | `feature` | Facility Management → Room Amenities |
| 12 | `package_features` | `package_feature` | Package ↔ feature junction |
| 13 | `stay_users` | `stay_user` | Occupants per stay per room, plus `is_key_required` |
| 14 | `stay_packages` | `stay_package` | Package(s) attached to a stay |
| 15 | `room_allocations` | `room_allocation` | Check-in room assignment and the re-allocation workflow |
| 16 | `user_documents` | `user_document` | Bookings "Documents Approval" column |
| 17 | `user_tokens` | `user_token` | Session token, expiry, revocation (Auth gaps A2 / A6) |
| 18 | `user_devices` | `user_device` | Push/FCM token registry (Header gap H7) |
| 19 | `roles` | `role` | User Roles module |
| 20 | `role_modules` | `role_module` | 18 rows that match the HMS sidebar exactly — closes NEEDS_REVIEW D1 |
| 21 | `role_module_permissions` | `role_module_permission` | Read/write access per role per module |
| 22 | `service_types` | `service_type` | The 7 Services Tracking tabs |
| 23 | `service_statuses` | `service_status` | Pending · Assigned · Partially completed · Completed · Canceled |
| 24 | `service_categories` | `service_category` | Services Setup groups (replaces HMS `food_category`) |
| 25 | `service_request_items` | `service_request_item` | Service Tracking "Items" modal, quantities and unit prices |
| 26 | `room_service_requests` | `room_service_request` | Guest-room service queue — flagged REVIEW §11.7 |
| 27 | `maintenance_request_recurrence` | `maintenance_request_recurrence` | Services Planning recurrence (`weekly`, `days_of_week`, `max_no_of_occurrences`) |
| 28 | `service_maintenance_request_amenities` | `maintenance_request_amenity` | Maintenance request ↔ rooms |
| 29 | `service_maintenance_request_assignees` | `maintenance_request_assignee` | Maintenance request ↔ staff |
| 30 | `device_types` | `device_type` | Intellihub(HUB) · AirQ(AIR) · Mikos(MIK) · Kleio(KLE) — the 4 Dashboard device cards |
| 31 | `device_params` | `device_param` | Telemetry parameter registry (name, data type, unit) |
| 32 | `device_stats` | `device_stat` | All telemetry — Power View, Energy View, device detail cards |
| 33 | `device_current_stats` | `device_current_stat` | Latest-value blob per device for room and device tiles |
| 34 | `device_commands` | `device_command` | Key generation, lock/unlock, config push |
| 35 | `command_types` | `command_type` | Command registry per device type |
| 36 | `mqtt_brokers` | `mqtt_broker` | Device-communicator transport layer |
| 37 | `mqtt_topics` | `mqtt_topic` | 8 topic types incl. `DeviceAlert`, `DeviceHealth`, `LastWill` |
| 38 | `battery_life_stats` | `battery_life_stat` | Kleio battery %, drives the "Low battery" amenity condition |
| 39 | `sensor_operation_stats` | `sensor_operation_stat` | "Smart Rooms Online" KPI (replaces HMS `device_uptime`) |
| 40 | `job_devices` | `job_order_device` | Job order ↔ device |
| 41 | `job_amenities` | `job_order_amenity` | Job order ↔ room |
| 42 | `key_types` | `key_type` | Primary · Shared · Staff · Default — Default Key Settings module |
| 43 | `user_device_acl` | `user_device_acl` | Time-boxed device access grant behind every issued key |
| 44 | `lock_activity_log` | `lock_activity_log` | Kleio lock/unlock audit (`event`, `unlock_mode`) |
| 45 | `device_alerts` | `device_alert` | Raw alert stream; carries the real `alert_severity` |
| 46 | `incident_events` | `incident_event` | Unread · Read · Assigned · Resolved · **Reopened** |
| 47 | `incident_history` | `incident_history` | Incident audit trail |
| 48 | `entity_types` | `entity_type` | Booking · Occupancy · Service Requests · Maintenance Requests · Default Key |
| 49 | `activity_types` | `activity_type` | In-app activity taxonomy + `notification_type` + `is_subscribable` |
| 50 | `activity_notifiers` | `activity_notifier` | Per-user unread/read/clear — the Header notification feed |
| 51 | `activity_role_association` | `activity_role_association` | Which roles receive which activity type |
| 52 | `notification_receivers` | `notification_receiver` | Dispatch fan-out per recipient (email, phone, device token) |
| 53 | `notification_results` | `notification_result` | Per-channel delivery result (email / sms / push / silent) |
| 54 | `promo_code_amenities` | `promo_code_amenity` | Offer applicability per room |
| 55 | `occasion_types` | `occasion_type` | Festival · Birthday · Marriage anniversary · **Holiday** |
| 56 | `occasions` | `occasion` | Holidays and occasions module — flagged REVIEW §11.5 |
| 57 | `daily_dual_data_points` | `daily_dual_data_point` | `metric_type` enum is exactly the Caleido At Work KPI set |

### 3.2 ADAPT — 35 tables

| # | IKANOS table | Final HMS table | Structural change and why |
|---:|---|---|---|
| 1 | `facilities` | `facility` | UUID PK + `legacy_id`; `cloud_details text` → `JSONB` |
| 2 | `property_types` | `property_type` | UUID PK; `levels tinyint(1)` → `SMALLINT` (it stores 1–3, not a boolean) |
| 3 | `amenity_types` | `amenity_type` | UUID PK; `amenity_category` enum restored |
| 4 | `amenities` | `amenity` | UUID PK; `property_type_id` **replaced by `property_chain_id`**; `status tinyint` becomes an FK to `amenity_status` [INFER]; absorbs `amenity_metadata` |
| 5 | `packages` | `package` | UUID PK; `price` **removed** — it does not exist in `packages` (§11.3) |
| 6 | `stays` | `stay` | UUID PK; **absorbs the entire HMS `booking` table**; all 21 IKANOS columns restored |
| 7 | `invoices` | `invoice` | UUID PK; money columns → `NUMERIC(10,2)`; 11 columns restored |
| 8 | `imports` | `import_job` | Renamed (`imports` collides with tooling); UUID PK |
| 9 | `users` | `app_user` | UUID PK; absorbs `user_login_details` + `user_metadata`; also absorbs the HMS `employee` table |
| 10 | `user_roles` | `user_role` | Composite PK becomes `(facility_id, app_user_id, role_id)` — **facility scope added** |
| 11 | `departments` | `department` | UUID PK; `status` and `department_key enum('admin')` restored |
| 12 | `functions` | `job_function` | Renamed (SQL keyword). **FK is `facility_id`, not `department_id`** — `functions.department_id` does not exist [FACT] |
| 13 | `service_category_items` | `service_category_item` | UUID PK; absorbs `service_item_metadata`; replaces HMS `food_menu` |
| 14 | `service_requests` | `service_request` | UUID PK; 13 columns restored; `assigned_to` repointed from `employee` to `app_user` |
| 15 | `room_service_request_items` | `room_service_request_item` | `faciliti_service_id` has **no FK target anywhere in the dump**; repointed to `service_category_item` [INFER] — REVIEW §11.7 |
| 16 | `service_maintenance_requests` | `maintenance_request` | Renamed; UUID PK; 17 columns restored; recurrence split out |
| 17 | `devices` | `device` | UUID PK; `ip_address`/`mac_address`/`last_seen` **removed** (absent from the dump); absorbs `device_metadata` |
| 18 | `firmware` | `firmware` | UUID PK; `is_latest` **removed**; `status`, `crc`, `firmware_url`, `release_notes`, `firmware_size`, `decommission_reason` restored |
| 19 | `device_health_stats` | `device_health_stat` | BIGINT identity PK (7.7 M rows in the dump); `response_time`/`error_detail` removed; `device_temperature` added |
| 20 | `other_devices` | `other_device` | BIGINT identity PK; `msgString json` → `JSONB` — REVIEW §11.8 |
| 21 | `jobs` (caleido) | `job_order` | UUID PK; 7 columns restored; `assigned_to → app_user` [FACT: `jobs.assigned_to → users.user_id`] |
| 22 | `keys` | `access_key` | Renamed (`keys`/`key` is ambiguous in PostgreSQL); UUID PK |
| 23 | `alert_types` | `alert_type` | **Reduced to `(id, name)`** — `severity`/`category`/`description`/`is_active` do not exist |
| 24 | `incident_statuses` | `incident_status` | **Reduced to `(id, name)`** — `status_code`/`display_color`/`is_resolved` do not exist |
| 25 | `device_incidents` | `device_incident` | UUID PK; 5 invented columns removed; `amenity_id`, `alert_type`, `latest_alert_id`, `updated_by` added |
| 26 | `value_alerts` | `value_alert` | UUID PK; invented `parameter`/`unit`/`current_value` removed; `limit_config_id` FK added; `timestamp date` → `TIMESTAMPTZ` |
| 27 | `value_alert_limit_config` | `value_alert_limit_config` | UUID PK; keyed by `device_name varchar` in IKANOS — kept, plus a **nullable** `device_id` FK [INFER] |
| 28 | `activities` | `activity` | BIGINT identity PK; absorbs `activity_data` |
| 29 | `notifications` | `notification` | BIGINT identity PK; absorbs `notification_params` |
| 30 | `templates` | `notification_template` | Renamed (`templates` too generic); enum kept verbatim |
| 31 | `facility_events` | `facility_event` | UUID PK; 7 columns restored (`chief_guests`, attendee counts, `cancellation_reason`, `image_id`) |
| 32 | `promo_codes` | `promo_code` | UUID PK; all 8 discount columns restored |
| 33 | `energy_stats` | `energy_stat` | Composite PK `(device_name, facility_id, amenity_id, hour)` preserved verbatim |
| 34 | `jobs` (scheduler) | `scheduler_job` | Renamed to resolve the `jobs` collision; `job_data json` → `JSONB` |
| 35 | `job_executions` | `scheduler_job_execution` | BIGINT identity PK; `job_response blob` → `BYTEA` |

### 3.3 MERGE — 7 IKANOS tables absorbed into another final table

| IKANOS table | Absorbed into | Mapping |
|---|---|---|
| `user_login_details` (`user_id` PK, `user_name`, `password`) | `app_user` | Strict 1:1 on the PK → `app_user.user_name VARCHAR(100)`, `app_user.password_hash VARCHAR(100)`. HMS has one auth entity; a 1:1 side table adds a join to every login for no gain. |
| `user_metadata` (`user_id`, `metadata_key`, `metadata_value`) | `app_user` | Key-value bag → `app_user.metadata JSONB` |
| `amenity_metadata` | `amenity` | → `amenity.metadata JSONB` |
| `device_metadata` | `device` | → `device.metadata JSONB` |
| `service_item_metadata` | `service_category_item` | → `service_category_item.metadata JSONB` |
| `activity_data` (`activity_id` PK, `version`, `data text`) | `activity` | Strict 1:1 on the PK → `activity.data_version SMALLINT` + `activity.data JSONB` |
| `notification_params` (`notification_id`, key, value) | `notification` | Template parameter bag → `notification.params JSONB`. The dispatch worker reads every param for one notification at once; no query filters by param key. |

**Why these four `*_metadata` merges are safe:** all four are the same MySQL-era EAV workaround — composite PK `(parent_id, metadata_key)`, a `text` value, and no other table foreign-keys to them [FACT]. PostgreSQL `JSONB` with a GIN index gives the same key lookup without a join, and the parent relationship is preserved because the data now lives on the parent row. **No relationship is lost and no business meaning is dropped.**

### 3.4 EXCLUDE — 8 tables

| IKANOS table | Evidence for exclusion |
|---|---|
| `migrations` | TypeORM migration ledger. HMS uses Alembic (`alembic_version`). Infrastructure, not business data. |
| `payment_gateway_keys` | Razorpay credentials. There is **no payment module** among the 15 HMS sidebar entries and **no payment row in `role_modules`** [FACT]. Table is empty in the dump. |
| `payment_order_status` | Same evidence. |
| `payment_status` | Same evidence. |
| `feedback_questions` | Guest feedback belongs to the **Porta** guest app (`request_source = 'porta'` [FACT]). No HMS sidebar module, no `role_modules` row, no screen in the 25-page frontend inventory. |
| `feedback_options` | Same evidence. |
| `feedback_responses` | Same evidence. |
| `user_feedback` | Same evidence. |

Excluded on **workflow evidence** (no HMS module consumes them), not on a judgement that the data is worthless. Both groups reappear in §11 OPEN DECISIONS.

**Deliberately NOT excluded:** `other_devices`, `room_service_requests` and `room_service_request_items` are kept with a REVIEW flag, because Power View and the guest service queue are real HMS screens that would otherwise have zero database support.

---

## 4. CURRENT HMS 39 TABLES → ACTION

| # | Current HMS table | Action | Becomes | Reason |
|---:|---|---|---|---|
| 1 | `facility` | **MODIFY** | `facility` | +12 IKANOS columns: `org_id`, `facility_uid`, address block, `currency_id`, `default_key_user`, `facility_image_id` |
| 2 | `app_user` | **MODIFY** | `app_user` | +20 columns from `users`; absorbs `employee`, `user_login_details`, `user_metadata` |
| 3 | `employee` | **MERGE** | → `app_user` | **No `employee` table exists in IKANOS** [FACT]; staff are `users` rows with `is_staff = 1` |
| 4 | `user_role` | **MODIFY** | `role` | Renamed to match `roles`; `permissions JSONB` dropped in favour of `role_module` + `role_module_permission` |
| 5 | `app_user_user_role` | **MODIFY** | `user_role` | PK becomes `(facility_id, app_user_id, role_id)`; today a user cannot hold different roles at different facilities |
| 6 | `department` | **MODIFY** | `department` | +`status`, `department_key`, `created_by` |
| 7 | `job_function` | **MODIFY** | `job_function` | **FK repointed `department_id` → `facility_id`**; `functions.department_id` does not exist |
| 8 | `property_type` | **MODIFY** | `property_type` | +`levels`, `property_type_image_id`, `status` |
| 9 | `amenity_type` | **MODIFY** | `amenity_type` | +`amenity_category` enum, `status`, `image_id` |
| 10 | `amenity` | **MODIFY** | `amenity` | `floor VARCHAR` + `property_type_id` **replaced by `property_chain_id`**; +`parent_amenity_id`, `is_dnd`, `power_save_mode`, `metadata` |
| 11 | `package` | **MODIFY** | `package` | +`description`, `is_sub_package`, `image_id`, `status`; **`price` removed** |
| 12 | `booking` | **MERGE** | → `stay` | **No `booking` table exists in IKANOS** [FACT]; `stays` is the reservation entity. Largest single structural correction. |
| 13 | `occupant` | **REPLACE** | `stay_user` | IKANOS models occupants as `user_id` + `room_id` + `stay_id`; guest identity lives in `users` |
| 14 | `stay` | **REPLACE** | `stay` | Rebuilt with all 21 IKANOS columns and absorbing `booking` |
| 15 | `invoice` | **MODIFY** | `invoice` | +11 columns: `invoice_number`, dates, billing/facility snapshot, tax breakdown |
| 16 | `service_request` | **MODIFY** | `service_request` | +13 columns; `assigned_to → app_user`; +`stay_id`, `category_id`, amounts |
| 17 | `food_category` | **REPLACE** | `service_category` | **No `foodCategory` table exists**; categories are generic, keyed by `service_type` |
| 18 | `food_menu` | **REPLACE** | `service_category_item` | **No `foodMenu` table exists**; items are generic and carry `price_per_unit` |
| 19 | `event` | **MODIFY** | `facility_event` | +7 columns incl. attendee counts and `cancellation_reason` |
| 20 | `offer` | **MODIFY** | `promo_code` | +8 discount columns — all discount logic was missing |
| 21 | `holiday` | **REPLACE** | `occasion` | No `holiday` table; `occasion_types` contains a row named `Holiday` — **REVIEW §11.5** |
| 22 | `device` | **MODIFY** | `device` | +14 columns; `ip_address`/`mac_address`/`last_seen` removed |
| 23 | `firmware` | **MODIFY** | `firmware` | +8 columns; `is_latest` removed |
| 24 | `job_order` | **MODIFY** | `job_order` | +7 columns; `assigned_to → app_user` |
| 25 | `job_order_device` | **KEEP** | `job_order_device` | **The only structurally correct table in the current 39** |
| 26 | `device_incident` | **MODIFY** | `device_incident` | 5 invented columns removed; `amenity_id`, `alert_type`, `latest_alert_id`, `updated_by` added |
| 27 | `value_alerts` | **MODIFY** | `value_alert` | `parameter`/`unit`/`current_value` removed; `limit_config_id`, `device_name`, `device_type_id`, `amenity_id` added |
| 28 | `limit_config` | **MODIFY** | `value_alert_limit_config` | Percentage **and** absolute limits; keyed by `device_name` |
| 29 | `alert_type` | **MODIFY** | `alert_type` | Reduced to `(id, name)`; the 16 real rows to be seeded |
| 30 | `current_incident_status` | **MODIFY** | `incident_status` | Reduced to `(id, name)`; the 4 real rows to be seeded |
| 31 | `notification` | **REPLACE** | `activity`, `activity_notifier`, `notification`, `notification_receiver`, `notification_result` | IKANOS separates the **in-app feed** (`activities`/`activity_notifiers`) from the **dispatch queue** (`notifications`); HMS collapsed both into one table |
| 32 | `fcm_token` | **MODIFY** | `user_device` | +`mobile_model`, `mobile_os`, `user_token_id`, `stay_id`, `is_mobile_token` |
| 33 | `maintenance_schedule` | **REPLACE** | `maintenance_request` + `maintenance_request_recurrence` + 2 junctions | +17 columns; recurrence and assignment split out as IKANOS does |
| 34 | `scheduled_task` | **REPLACE** | `scheduler_job` + `scheduler_job_execution` | No `scheduled_task` exists; the executor is the `caleido_scheduler` pair |
| 35 | `energy_data` | **REMOVE** | → `device_param` + `device_stat` | Table does not exist in IKANOS; telemetry is a generic EAV pair |
| 36 | `sensor_reading` | **REMOVE** | → `device_param` + `device_stat` | Same |
| 37 | `energy_aggregate` | **REPLACE** | `energy_stat` | IKANOS is hourly only, PK `(device_name, facility_id, amenity_id, hour)`; the `aggregate_interval` enum was invented |
| 38 | `device_health_log` | **MODIFY** | `device_health_stat` | `response_time`/`error_detail` removed; `device_temperature` added |
| 39 | `device_uptime` | **REPLACE** | `sensor_operation_stat` | No `device_uptime`; IKANOS stores `operation_percentage` per device per day |

**Totals: KEEP 1 · MODIFY 24 · REPLACE 10 · MERGE 2 · REMOVE 2 = 39** ✔
---

## 5. FINAL HMS TABLE SPECIFICATIONS

### 5.0 Reading these specifications

To avoid repeating 92 identical blocks, three column groups are **implicit on every table** and are not re-listed:

| Implicit column | Type | Note |
|---|---|---|
| `id` | per §2.3 (T1 `SMALLINT`/`INTEGER` · T2 `UUID` · T3 `BIGINT` identity) | omitted only where the table has a composite natural PK |
| `legacy_id` | `BIGINT NULL` **UNIQUE** | the original IKANOS integer key (§2.3) |
| `created_on` / `updated_on` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | IKANOS naming retained (§2.4) |

`created_by` and `updated_by` are listed **explicitly** and only where IKANOS carries them.
Every `facility_id` is `UUID NOT NULL/NULL → facility(id) ON DELETE CASCADE` and is indexed; the nullability shown matches the dump.
`REVIEW` on a row means: HMS needs it, the dump does not support it, and it is **not** being added.

---

### GROUP A — Organisation, facility and property hierarchy (8 tables)

#### 1. `organisation`
- **Purpose:** Top-level tenant that owns facilities.
- **Source:** `organisations` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | `VARCHAR(100)` | NOT NULL | |
| `org_uid` | `VARCHAR(3)` | NOT NULL | unique short code |
| `created_by` | `UUID` | NOT NULL | → `app_user(id)` |

- **PK** `id` (UUID) · **UNIQUE** `org_uid`, `legacy_id` · **FK** `created_by → app_user(id) RESTRICT`
- **Indexes** `ux_organisation_org_uid`
- **Relationships** 1 organisation → many `facility`.

#### 2. `facility`
- **Purpose:** A hotel/premise. Tenant root for 32 downstream tables.
- **Source:** `facilities` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `org_id` | `UUID` | NOT NULL | → `organisation(id)` |
| `facility_uid` | `VARCHAR(3)` | NOT NULL | the canonical copy; the denormalised copies on 91 other tables are dropped (§2.5) |
| `name` | `VARCHAR(100)` | NOT NULL | |
| `currency_id` | `SMALLINT` | NULL | base currency for food ordering and invoicing. **No `currencies` table exists in the dump** → no FK. REVIEW |
| `city` | `VARCHAR(100)` | NULL | |
| `state` | `VARCHAR(100)` | NULL | |
| `pin_code` | `VARCHAR(20)` | NULL | |
| `guest_rooms` | `INTEGER` | NULL | |
| `email` | `VARCHAR(500)` | NOT NULL | comma-separated list |
| `additional_email` | `VARCHAR(500)` | NULL | comma-separated list |
| `google_map_link` | `VARCHAR(256)` | NULL | |
| `cloud_details` | `JSONB` | NULL | `text` in IKANOS |
| `facility_image_id` | `UUID` | NULL | → `attachment(id)` |
| `default_key_user` | `UUID` | NULL | → `app_user(id)` — powers the Default Key Settings module |
| `created_by` | `UUID` | NOT NULL | → `app_user(id)` |

- **PK** `id` · **UNIQUE** `facility_uid`, `legacy_id`
- **FK** `org_id → organisation(id) CASCADE` · `facility_image_id → attachment(id) CASCADE` · `default_key_user → app_user(id) RESTRICT`
- **Indexes** `ix_facility_org_id`, `ux_facility_facility_uid`
- **Not present, not added:** `address` (single-line), `timezone`, `default_checkin_time`, `default_checkout_time`, `logo` as a varchar → **REVIEW** (§11.9)
- **Relationships** facility is the cascade root for amenity, device, role, department, package, service, alert and event trees.

#### 3. `facility_user`
- **Purpose:** Which users belong to which facility.
- **Source:** `facility_users` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NOT NULL | part of PK |
| `app_user_id` | `UUID` | NOT NULL | part of PK |
| `status` | `SMALLINT` | NULL DEFAULT 1 | soft-delete flag |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `(facility_id, app_user_id)` — composite, no surrogate `id`
- **FK** `facility_id → facility(id) CASCADE` · `app_user_id → app_user(id) CASCADE` · `created_by → app_user(id) RESTRICT`
- **Indexes** `ix_facility_user_app_user_id`
- **Relationships** many-to-many `facility` ↔ `app_user`.

#### 4. `property_type`
- **Purpose:** Kind of structure (e.g. Building, Wing, Floor) and how many chain levels it uses.
- **Source:** `property_types` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `property_type_name` | `VARCHAR(200)` | NOT NULL | |
| `property_type_image_id` | `UUID` | NULL | → `attachment(id)` |
| `levels` | `SMALLINT` | NOT NULL | 1–3; drives `property_chain` depth |
| `facility_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NOT NULL DEFAULT 1 | |

- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · `property_type_image_id → attachment(id) RESTRICT`
- **Indexes** `ix_property_type_facility_id`
- **Relationships** 1 property_type → many `property`.

#### 5. `property`
- **Purpose:** A named physical unit — one building, one wing, one floor.
- **Source:** `properties` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `property_name` | `VARCHAR(200)` | NOT NULL | |
| `property_type_id` | `UUID` | NOT NULL | → `property_type(id)` |
| `facility_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NOT NULL DEFAULT 1 | |
| `created_by` | `UUID` | NULL | |

- **PK** `id` · **FK** `property_type_id → property_type(id) RESTRICT` · `facility_id → facility(id) CASCADE` · `created_by → app_user(id) CASCADE`
- **Indexes** `ix_property_property_type_id`, `ix_property_facility_id`
- **Relationships** `property` rows are assembled into paths by `property_chain`. **This is the table the Dashboard building/floor cards were missing.**

#### 6. `property_chain`
- **Purpose:** One materialised building → wing → floor path. An amenity points at a chain, not at a floor string.
- **Source:** `property_chains` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `level_one_id` | `UUID` | NOT NULL | → `property(id)` — building |
| `level_two_id` | `UUID` | NULL | → `property(id)` — wing/floor |
| `level_three_id` | `UUID` | NULL | → `property(id)` — floor/sub-level |
| `facility_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NOT NULL DEFAULT 1 | |
| `created_by` | `UUID` | NULL | |

- **PK** `id` · **UNIQUE** `legacy_id`
- **FK** all three level columns `→ property(id) RESTRICT` · `facility_id → facility(id) CASCADE` · `created_by → app_user(id) CASCADE`
- **Indexes** `ix_property_chain_level_one_id`, `..._level_two_id`, `..._level_three_id`, `ix_property_chain_facility_id`
- **Relationships** `amenity.property_chain_id → property_chain`. Resolves NEEDS_REVIEW **B1** and gap **D36/D38** (floors missing for buildings 3 and 4).

#### 7. `attachment`
- **Purpose:** Uploaded file registry — logos, icons, images, guest ID scans.
- **Source:** `attachments` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NULL | |
| `file_name` | `VARCHAR(100)` | NOT NULL | |
| `file_path` | `VARCHAR(256)` | NOT NULL | |
| `created_by` | `UUID` | NULL | |

- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · `created_by → app_user(id) CASCADE`
- **Indexes** `ix_attachment_facility_id`, `ix_attachment_created_by`
- **Referenced by** `facility.facility_image_id`, `property_type.property_type_image_id`, `amenity_type.image_id`, `package.image_id`, `facility_event.image_id`, `promo_code.promo_code_icon`, `service_category.category_icon`, `service_category_item.item_icon`, `user_document.attachment_id`, `invoice.facility_image_id`.

#### 8. `country`
- **Purpose:** Country reference data — phone codes and nationality.
- **Source:** `countries` — **USE** (239 rows to seed)

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1 lookup** — IKANOS ids preserved |
| `name` | `VARCHAR(50)` | NOT NULL | |
| `phone_code` | `VARCHAR(10)` | NOT NULL | |
| `iso_code` | `VARCHAR(10)` | NULL | |
| `nice_name` | `VARCHAR(50)` | NOT NULL | |
| `iso3` | `VARCHAR(3)` | NULL | |
| `num_code` | `SMALLINT` | NULL | |

- **PK** `id` · **Indexes** `ix_country_phone_code`
- **Relationships** `app_user.country → country`, `app_user.nationality → country`. Resolves NEEDS_REVIEW **B4** and Bookings gaps **B44/B45**.

---

### GROUP B — Rooms, amenities and packages (9 tables)

#### 9. `amenity_type`
- **Purpose:** Category of bookable/non-bookable space.
- **Source:** `amenity_types` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NOT NULL | |
| `facility_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NOT NULL | |
| `amenity_category` | `ENUM amenity_category` | NOT NULL DEFAULT `'others'` | |
| `image_id` | `UUID` | NULL | → `attachment(id)` |
| `created_by` | `UUID` | NOT NULL | |

- **Enum** `amenity_category` = `room` · `restaurant` · `others`
- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · `image_id → attachment(id) RESTRICT`
- **Relationships** `amenity.amenity_type_id`, `package.amenity_type`, `user_device_acl.amenity_type_id`.

#### 10. `amenity`
- **Purpose:** A room or space. The central operational object.
- **Source:** `amenities` + `amenity_metadata` (MERGE) — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | `VARCHAR(6)` | NOT NULL | room number, e.g. `106` |
| `parent_amenity_id` | `UUID` | NULL | self-reference (sub-space) |
| `amenity_type_id` | `UUID` | NOT NULL | → `amenity_type(id)` |
| `facility_id` | `UUID` | NULL | |
| `property_chain_id` | `UUID` | NULL | → `property_chain(id)` — **replaces `floor VARCHAR`** |
| `package_id` | `UUID` | NOT NULL | → `package(id)` |
| `status` | `SMALLINT` | NULL DEFAULT 2 | → `amenity_status(id)` **[INFER]** — see below |
| `is_dnd` | `SMALLINT` | NULL | do-not-disturb |
| `power_save_mode` | `SMALLINT` | NULL | |
| `metadata` | `JSONB` | NULL | absorbed `amenity_metadata` |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **UNIQUE** `legacy_id`
- **FK** `parent_amenity_id → amenity(id) CASCADE` · `amenity_type_id → amenity_type(id) CASCADE` · `facility_id → facility(id) CASCADE` · `property_chain_id → property_chain(id) RESTRICT` · `package_id → package(id) RESTRICT` · **`status → amenity_status(id) RESTRICT` [INFER]**
- **Indexes** `ix_amenity_facility_id`, `ix_amenity_amenity_type_id`, `ix_amenity_property_chain_id`, `ix_amenity_status`, GIN on `metadata`
- **Status values** from `amenity_statuses`: `0` Available · `1` Occupied · `2` Unavailable · `3` Allotted
- **[INFER] note:** IKANOS declares `amenities.status tinyint DEFAULT 2` with **no FK constraint**, while `amenity_statuses` holds exactly ids 0–3 and the default `2` = *Unavailable* is a sensible new-room default. The FK is therefore inferred, not read. Flagged in §11.4.
- **Relationships** amenity ← device, device_alert, device_incident, room_allocation, stay_user, service_request, maintenance_request_amenity, promo_code_amenity, lock_activity_log, energy_stat, sensor_operation_stat, user_device_acl, job_order_amenity, amenity_condition_status.
- Resolves gaps **D40, O13, O5** (single status vocabulary, building/floor columns).

#### 11. `amenity_status`
- **Purpose:** The 4-value room status vocabulary.
- **Source:** `amenity_statuses` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** — seeded 0,1,2,3 |
| `amenity_status_name` | `VARCHAR(100)` | NOT NULL | |

- **PK** `id` · **UNIQUE** `id` (IKANOS declares a redundant unique key; kept as documentation only)
- **Seed** `0` Available · `1` Occupied · `2` Unavailable · `3` Allotted

#### 12. `amenity_condition`
- **Purpose:** Housekeeping/operational condition badges, independent of status.
- **Source:** `amenity_conditions` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(45)` | NOT NULL | |

- **PK** `id` · **Seed** Dirty · Low battery · Under maintenance · Sanitation
- Resolves gap **O17** (condition master, and whether the badge list is exhaustive — it is: 4 rows).

#### 13. `amenity_condition_status`
- **Purpose:** Which conditions are currently set on which room.
- **Source:** `amenity_condition_status` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `amenity_id` | `UUID` | NOT NULL | part of PK |
| `amenity_condition_id` | `SMALLINT` | NOT NULL | part of PK |
| `status` | `SMALLINT` | NOT NULL DEFAULT 1 | condition on/off |

- **PK** `(amenity_id, amenity_condition_id)` · **FK** both `CASCADE`
- **Indexes** `ix_acs_amenity_condition_id`
- **Relationships** many-to-many `amenity` ↔ `amenity_condition`.

#### 14. `package`
- **Purpose:** Room package / rate plan. Also models sub-packages via `is_sub_package`.
- **Source:** `packages` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NULL | |
| `name` | `VARCHAR(100)` | NOT NULL | |
| `description` | `TEXT` | NULL | |
| `status` | `SMALLINT` | NOT NULL | |
| `amenity_type` | `UUID` | NOT NULL | → `amenity_type(id)` **[INFER]** — `smallint` with no FK in IKANOS |
| `is_sub_package` | `BOOLEAN` | NOT NULL DEFAULT false | |
| `image_id` | `UUID` | NULL | → `attachment(id)` |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · `image_id → attachment(id) RESTRICT` · `amenity_type → amenity_type(id) RESTRICT` [INFER]
- **Indexes** `ix_package_facility_id`
- **`price` is NOT a column.** `packages` has no price in the dump [FACT]. The only price in the schema is `service_category_item.price_per_unit`. Room tariff therefore has **no source** → **REVIEW §11.3** (commercially significant; blocks Bookings gaps B36/B8).
- **Relationships** `amenity.package_id`, `room_allocation.package_id`, `stay_package.package_id`, `sub_package`, `package_feature`.

#### 15. `sub_package`
- **Purpose:** Parent package → child package composition.
- **Source:** `sub_packages` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `parent_package_id` | `UUID` | NOT NULL | part of PK |
| `sub_package_id` | `UUID` | NOT NULL | part of PK |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `(parent_package_id, sub_package_id)` · **FK** both `→ package(id) RESTRICT`
- **Indexes** `ix_sub_package_sub_package_id`
- Resolves Bookings gap **B42** (Sub Packages dropdown driven by a master).

#### 16. `feature`
- **Purpose:** Room feature (TV, AC, WiFi …), optionally tied to a smart device type.
- **Source:** `features` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NULL | |
| `feature_name` | `VARCHAR(100)` | NOT NULL | |
| `is_smart_feature` | `BOOLEAN` | NULL | |
| `device_type` | `SMALLINT` | NULL | → `device_type(id)` |
| `status` | `SMALLINT` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · `device_type → device_type(id) RESTRICT`
- Resolves NEEDS_REVIEW **B6** (`roomAmenity` — per-room features).

#### 17. `package_feature`
- **Purpose:** Which features a package includes.
- **Source:** `package_features` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `package_id` | `UUID` | NOT NULL | |
| `feature_id` | `UUID` | NOT NULL | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` (IKANOS uses a surrogate here, not a composite) · **FK** both `CASCADE`
- **Indexes** `ix_package_feature_package_id`, `ix_package_feature_feature_id`

---

### GROUP C — Guests, stays and billing (7 tables)

#### 18. `stay`
- **Purpose:** **The reservation.** Booking, check-in, check-out and cancellation are all states of one `stay` row.
- **Source:** `stays` — **ADAPT** (absorbs the HMS `booking` table)

| Column | Type | Null | Notes |
|---|---|---|---|
| `internal_stay_ref_number` | `VARCHAR(100)` | NOT NULL | the booking reference the UI shows |
| `external_stay_ref_number` | `VARCHAR(100)` | NULL | PMS/OTA reference |
| `booking_user_id` | `UUID` | NOT NULL | → `app_user(id)` — who the booking is for |
| `no_of_rooms` | `SMALLINT` | NULL DEFAULT 0 | |
| `no_of_guests` | `SMALLINT` | NOT NULL DEFAULT 0 | |
| `expected_checkin_time` | `TIMESTAMPTZ` | NOT NULL | |
| `expected_checkout_time` | `TIMESTAMPTZ` | NOT NULL | |
| `actual_checkin_time` | `TIMESTAMPTZ` | NULL | set at check-in |
| `actual_checkout_time` | `TIMESTAMPTZ` | NULL | set at check-out |
| `comments` | `TEXT` | NULL | |
| `gst` | `VARCHAR(20)` | NULL | |
| `checkout_initiated_by` | `UUID` | NULL | → `app_user(id)` |
| `document_approval_status` | `ENUM document_approval_status` | NOT NULL DEFAULT `'pending'` | |
| `status` | `ENUM stay_status` | NULL DEFAULT `'pending'` | |
| `request_source` | `ENUM request_source` | NULL | |
| `created_by` | `UUID` | NOT NULL | |
| `modified_by` | `UUID` | NOT NULL | IKANOS name kept |

- **Enums**
  - `stay_status` = `pending` · `active` · `checkout accepted` · `checkout pending` · `checkout rejected` · `checked out` · `cancelled`
  - `document_approval_status` = `pending` · `approved`
  - `request_source` = `ikanos` · `porta`
- **PK** `id` · **UNIQUE** `internal_stay_ref_number`, `legacy_id`
- **FK** `booking_user_id → app_user(id) RESTRICT` · `checkout_initiated_by → app_user(id) RESTRICT` · `created_by`/`modified_by → app_user(id) RESTRICT`
- **Indexes** `ux_stay_internal_ref`, `ix_stay_status`, `ix_stay_expected_checkin_time`, `ix_stay_expected_checkout_time`, `ix_stay_booking_user_id`
- **`stays` has no `facility_id` column in the dump** [FACT]. Facility scope is reached through `room_allocation → amenity → facility`. → **REVIEW §11.6.**
- **Relationships** stay → `room_allocation`, `stay_user`, `stay_package`, `user_document`, `invoice`, `access_key`, `user_device_acl`, `service_request`, `room_service_request`, `activity`, `user_device`.
- Resolves gaps **B3, B5, B11, B12, B19–B21, B25, D14, D15, D45, D47, D48, O6, O20, O21**.

#### 19. `stay_user`
- **Purpose:** Occupants of a stay, and which room each occupies.
- **Source:** `stay_users` — **USE** (replaces HMS `occupant`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `app_user_id` | `UUID` | NOT NULL | → `app_user(id)` — guest identity lives in `app_user` |
| `room_id` | `UUID` | NULL | → `amenity(id)` |
| `stay_id` | `UUID` | NOT NULL | → `stay(id)` |
| `is_key_required` | `SMALLINT` | NULL | drives key generation |
| `status` | `SMALLINT` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** all three `CASCADE` · **Indexes** `ix_stay_user_stay_id`, `ix_stay_user_room_id`, `ix_stay_user_app_user_id`
- Resolves gaps **O8, O26, O27, D46** (occupant count and list per room).

#### 20. `stay_package`
- **Purpose:** Package(s) purchased on a stay.
- **Source:** `stay_packages` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `stay_id` | `UUID` | NOT NULL | |
| `package_id` | `UUID` | NOT NULL | |
| `status` | `SMALLINT` | NOT NULL DEFAULT 1 | |

- **PK** `id` · **FK** both `CASCADE` · **Indexes** on both FKs

#### 21. `room_allocation`
- **Purpose:** Which room(s) a stay is allocated, at which package. Re-allocation writes a new row.
- **Source:** `room_allocations` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `stay_id` | `UUID` | NOT NULL | |
| `room_id` | `UUID` | NOT NULL | → `amenity(id)` |
| `package_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** all three `CASCADE` · **Indexes** `ix_room_allocation_stay_id`, `ix_room_allocation_room_id`, `ix_room_allocation_package_id`
- Resolves gaps **B9, B21, D50, O12** (room allocation and re-allocation).

#### 22. `user_document`
- **Purpose:** Guest ID proof and its approval state.
- **Source:** `user_documents` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `app_user_id` | `UUID` | NOT NULL | |
| `attachment_id` | `UUID` | NOT NULL | → `attachment(id)` |
| `stay_id` | `UUID` | NULL | |
| `document_approval_status` | `ENUM user_document_approval_status` | NULL | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |

- **Enum** `user_document_approval_status` = `approved` · `rejected` · `pending` *(note: 3 values here vs 2 on `stay.document_approval_status` — both kept verbatim [FACT])*
- **PK** `id` · **FK** `app_user_id`/`attachment_id` `CASCADE`, `stay_id RESTRICT`
- **Document type and document number are NOT columns** in IKANOS → **REVIEW** (gaps O24, B40).
- Resolves gaps **B13, B23**.

#### 23. `invoice`
- **Purpose:** Stay invoice with a point-in-time billing and facility snapshot.
- **Source:** `invoices` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `invoice_number` | `VARCHAR(20)` | NOT NULL | |
| `invoice_date` | `TIMESTAMPTZ` | NOT NULL | |
| `invoice_due_date` | `TIMESTAMPTZ` | NULL | |
| `billing_user_id` | `UUID` | NOT NULL | → `app_user(id)` |
| `billing_user_name` | `VARCHAR(100)` | NULL | snapshot |
| `billing_address` | `VARCHAR(500)` | NULL | snapshot |
| `facility_id` | `UUID` | NULL | |
| `facility_name` | `VARCHAR(100)` | NULL | snapshot |
| `facility_address` | `VARCHAR(500)` | NULL | snapshot |
| `facility_image_id` | `UUID` | NULL | → `attachment(id)` |
| `stay_id` | `UUID` | NOT NULL | |
| `net_amount` | `NUMERIC(10,2)` | NULL | |
| `total_tax` | `NUMERIC(10,2)` | NULL | |
| `total_amount` | `NUMERIC(10,2)` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **UNIQUE** `invoice_number` · **FK** `stay_id`/`facility_id` `CASCADE`
- **Indexes** `ux_invoice_invoice_number`, `ix_invoice_stay_id`, `ix_invoice_facility_id`
- **There is no `invoice.status` column** in IKANOS [FACT]; the HMS `invoice.status` was documentation-derived. Payment state has no source → **REVIEW §11.10** (gaps B8, B37).
- Resolves gaps **O11, D49**.

#### 24. `import_job`
- **Purpose:** Bulk CSV upload tracking for bookings and job orders.
- **Source:** `imports` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `import_job_name` | `VARCHAR(100)` | NULL | |
| `entity_type` | `ENUM import_entity_type` | NOT NULL | |
| `import_status` | `ENUM import_status` | NOT NULL DEFAULT `'queued'` | |
| `total_records` | `INTEGER` | NULL | |
| `success_count` | `INTEGER` | NULL | |
| `error_count` | `INTEGER` | NULL | |
| `import_file_name` | `VARCHAR(100)` | NULL | |
| `error_file_name` | `VARCHAR(100)` | NULL | the "last upload report" link |
| `completed_on` | `TIMESTAMPTZ` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **Enums** `import_entity_type` = `booking` · `job order` · `import_status` = `queued` · `success` · `error` · `processing`
- **PK** `id` · **Indexes** `ix_import_job_import_status`, `ix_import_job_created_on`
- Resolves Bookings gaps **B30, B31, B32**.

---

### GROUP D — People, authentication and RBAC (9 tables)

#### 25. `app_user`
- **Purpose:** **One identity table for guests and staff.** `is_staff` distinguishes them.
- **Source:** `users` + `user_login_details` (MERGE) + `user_metadata` (MERGE) — **ADAPT**; also absorbs the HMS `employee` table

| Column | Type | Null | Notes |
|---|---|---|---|
| `user_uid` | `VARCHAR(72)` | NOT NULL | hash of the phone number; stable across facilities |
| `first_name` | `VARCHAR(100)` | NOT NULL | |
| `last_name` | `VARCHAR(100)` | NULL | |
| `email` | `VARCHAR(256)` | NULL | |
| `country` | `SMALLINT` | NULL | → `country(id)` |
| `phone_number` | `VARCHAR(15)` | NOT NULL | |
| `alternate_phone_number` | `VARCHAR(15)` | NULL | |
| `gender` | `ENUM gender` | NULL | |
| `dob` | `DATE` | NULL | |
| `is_child` | `SMALLINT` | NOT NULL DEFAULT 0 | |
| `age` | `SMALLINT` | NULL | |
| `is_staff` | `SMALLINT` | NULL DEFAULT 1 | **replaces the `employee` table** |
| `date_of_joining` | `TIMESTAMPTZ` | NULL | staff |
| `date_of_termination` | `TIMESTAMPTZ` | NULL | staff |
| `supervisor` | `UUID` | NULL | self-reference |
| `address` | `VARCHAR(1000)` | NULL | |
| `nationality` | `SMALLINT` | NULL | → `country(id)` |
| `marital_status` | `ENUM marital_status` | NULL | |
| `job_function_id` | `UUID` | NULL | → `job_function(id)` (IKANOS `function_id`) |
| `department_id` | `UUID` | NULL | → `department(id)` |
| `emp_id` | `VARCHAR(20)` | NULL | staff employee number |
| `user_name` | `VARCHAR(100)` | NULL | **merged from `user_login_details`** |
| `password_hash` | `VARCHAR(100)` | NULL | **merged from `user_login_details`** |
| `metadata` | `JSONB` | NULL | **merged from `user_metadata`** |
| `created_by` | `UUID` | NOT NULL | |

- **Enums** `gender` = `male` · `female` · `other` · `marital_status` = `married` · `unmarried` · `divorced` · `other`
- **PK** `id` · **UNIQUE** `user_uid`, `user_name`, `legacy_id`
- **FK** `country`/`nationality → country(id) RESTRICT` · `department_id → department(id) RESTRICT` · `job_function_id → job_function(id) RESTRICT` · `supervisor → app_user(id) RESTRICT`
- **Indexes** `ux_app_user_user_uid`, `ux_app_user_user_name`, `ix_app_user_phone_number`, `ix_app_user_email`, `ix_app_user_department_id`, `ix_app_user_job_function_id`, `ix_app_user_is_staff`, GIN on `metadata`
- **`users` has no `facility_id`** [FACT] — facility scope comes from `facility_user` and `user_role`. **There is no `is_active` column** → the documented `LOGIN.USER_INACTIVE` error has no backing column → **REVIEW §11.11.**
- **Relationships** referenced by 30+ tables. Resolves NEEDS_REVIEW **C2, C3** and gaps **A3, A4, A5, H9, H10, O22, O23**.

#### 26. `user_token`
- **Purpose:** API session tokens with explicit expiry — the missing session model.
- **Source:** `user_tokens` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `token` | `VARCHAR(36)` | NOT NULL | |
| `app_user_id` | `UUID` | NOT NULL | |
| `is_expired` | `BOOLEAN` | NULL DEFAULT false | |
| `expired_on` | `TIMESTAMPTZ` | NULL | |

- **PK** `id` · **UNIQUE** `token` · **FK** `app_user_id → app_user(id) CASCADE`
- **Indexes** `ux_user_token_token`, `ix_user_token_app_user_id`
- Resolves gaps **A2, A6** (bearer token, expiry → 401 → login redirect).

#### 27. `user_device`
- **Purpose:** Registered mobile/browser device and its push token.
- **Source:** `user_devices` — **USE** (replaces HMS `fcm_token`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `app_user_id` | `UUID` | NOT NULL | |
| `mobile_model` | `VARCHAR(100)` | NULL | |
| `mobile_os` | `VARCHAR(50)` | NULL | |
| `device_token` | `VARCHAR(200)` | NULL | FCM token |
| `is_mobile_token` | `BOOLEAN` | NULL | |
| `user_token_id` | `UUID` | NULL | → `user_token(id)` — ties push token to session |
| `stay_id` | `UUID` | NULL | → `stay(id)` |
| `status` | `SMALLINT` | NULL | |

- **PK** `id` · **FK** all three `CASCADE` · **Indexes** `ix_user_device_app_user_id`, `ix_user_device_user_token_id`
- Resolves gaps **H7, A7** (register FCM token at login, delete at logout).

#### 28. `role`
- **Purpose:** Named role within a facility.
- **Source:** `roles` — **USE** (HMS `user_role` renamed)

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NOT NULL | |
| `name` | `VARCHAR(50)` | NOT NULL | |
| `description` | `VARCHAR(200)` | NULL | |
| `role_type` | `ENUM role_type` | NOT NULL DEFAULT `'staff'` | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **Enum** `role_type` = `admin` · `system_user` · `manager` · `guest` · `staff` — **5 values, lowercase.** The HMS 4-value uppercase enum is discarded; `system_user` exists in the DB but is hidden in the UI.
- **PK** `id` · **FK** `facility_id → facility(id) CASCADE`
- **The `permissions JSONB` column is deleted.** Permissions live in `role_module_permission`.
- Resolves gap **A9**.

#### 29. `user_role`
- **Purpose:** Which role a user holds **at which facility**.
- **Source:** `user_roles` — **ADAPT** (HMS `app_user_user_role`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NOT NULL | part of PK |
| `app_user_id` | `UUID` | NOT NULL | part of PK |
| `role_id` | `UUID` | NOT NULL | part of PK |
| `created_by` | `UUID` | NULL | |

- **PK** `(facility_id, app_user_id, role_id)` — **the facility column the current HMS junction is missing**
- **FK** all `CASCADE` · **Indexes** `ix_user_role_role_id`, `ix_user_role_app_user_id`
- **Relationship** a user may hold different roles at different facilities — impossible in the current schema.

#### 30. `role_module`
- **Purpose:** The module registry. **18 rows that match the HMS sidebar exactly.**
- **Source:** `role_modules` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `module_name` | `VARCHAR(100)` | NOT NULL | |
| `read_applicable` | `BOOLEAN` | NULL | whether read access is meaningful |
| `write_applicable` | `BOOLEAN` | NULL | |

- **PK** `id`
- **Seed (18):** `dashboard` · `occupancy` · `bookings` · `service_tracking` · `service_planning` · `facility_management` · `user_roles` · `service_setup` · `employees` · `job_order` · `offers` · `events` · `caleido_network` · `firmware_management` · `reports` · `tickets` · `holidays` · `default_key`
- Resolves NEEDS_REVIEW **B8** and **D1**, and gaps **A8, A10, X11** (role-driven sidebar).

#### 31. `role_module_permission`
- **Purpose:** Read/write access per role per module.
- **Source:** `role_module_permissions` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `role_id` | `UUID` | NOT NULL | part of PK |
| `module_id` | `SMALLINT` | NOT NULL | part of PK → `role_module(id)` |
| `read_access` | `BOOLEAN` | NOT NULL DEFAULT false | |
| `write_access` | `BOOLEAN` | NULL | |

- **PK** `(role_id, module_id)` · **FK** `role_id → role(id) RESTRICT` · `module_id → role_module(id) RESTRICT`
- **Indexes** `ix_rmp_module_id`
- **This replaces `user_role.permissions JSONB` entirely.**

#### 32. `department`
- **Purpose:** Staff department (e.g. Kitchen, Housekeeping).
- **Source:** `departments` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `department_name` | `VARCHAR(255)` | NOT NULL | |
| `facility_id` | `UUID` | NOT NULL | |
| `status` | `SMALLINT` | NULL | |
| `department_key` | `ENUM department_key` | NULL | |
| `created_by` | `UUID` | NULL | |

- **Enum** `department_key` = `admin` (single-valued in IKANOS [FACT]; kept verbatim)
- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · **Indexes** `ix_department_facility_id`
- **Referenced by** `app_user.department_id`, `service_request.department_id`, `maintenance_request.department_id`.

#### 33. `job_function`
- **Purpose:** Staff function (e.g. Service Staff). **Scoped to facility, not department.**
- **Source:** `functions` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `function_name` | `VARCHAR(100)` | NOT NULL | |
| `facility_id` | `UUID` | NULL | **→ `facility(id)`, NOT `department`** |
| `status` | `SMALLINT` | NULL | |
| `function_key` | `ENUM function_key` | NULL | |
| `created_by` | `UUID` | NULL | |

- **Enum** `function_key` = `admin`
- **PK** `id` · **FK** `facility_id → facility(id) CASCADE` · **Indexes** `ix_job_function_facility_id`
- **Corrects NEEDS_REVIEW E2 / comparison §8.1:** the current HMS FK `job_function.department_id → department.id` is **wrong** — `functions` has no `department_id` column [FACT]. A user links to `department_id` and `function_id` **independently**.
---

### GROUP E — Services, tickets and the service catalogue (8 tables)

#### 34. `service_type`
- **Purpose:** Top-level service taxonomy. **These 7 rows are the 7 Services Tracking tabs.**
- **Source:** `service_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(100)` | NOT NULL | |

- **PK** `id`
- **Seed (7):** Room Service · Travel Desk · Business Center · Food Order · Facility Maintenance Service · Health & Fitness · Sanitation Maintenance Service
- **Referenced by** `service_category.service_type`, `service_request.service_type`. Resolves NEEDS_REVIEW **B2**.

#### 35. `service_status`
- **Purpose:** Service request and maintenance request lifecycle vocabulary.
- **Source:** `service_statuses` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(100)` | NOT NULL | |

- **PK** `id`
- **Seed (5):** Pending · Assigned · Partially completed · Completed · Canceled
- Resolves NEEDS_REVIEW **D4** and gaps **X8, O34, D13**.

#### 36. `service_category`
- **Purpose:** Category within a service type (Services Setup groups). **Generic — not food-specific.**
- **Source:** `service_categories` — **USE** (replaces HMS `food_category`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `service_type` | `SMALLINT` | NOT NULL | → `service_type(id)` |
| `category_name` | `VARCHAR(100)` | NULL | |
| `description` | `TEXT` | NULL | |
| `category_icon` | `UUID` | NULL | → `attachment(id)` |
| `facility_id` | `UUID` | NULL | |
| `service_category_key` | `VARCHAR(100)` | NULL | stable programmatic key |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** `service_type → service_type(id) RESTRICT` · `facility_id → facility(id) RESTRICT` · `category_icon → attachment(id) RESTRICT`
- **Indexes** `ix_service_category_service_type`, `ix_service_category_facility_id`

#### 37. `service_category_item`
- **Purpose:** A purchasable/requestable item. **Carries the only price in the schema.**
- **Source:** `service_category_items` + `service_item_metadata` (MERGE) — **ADAPT** (replaces HMS `food_menu`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `item_name` | `VARCHAR(100)` | NOT NULL | |
| `item_icon` | `UUID` | NULL | → `attachment(id)` |
| `category_id` | `UUID` | NOT NULL | → `service_category(id)` |
| `description` | `TEXT` | NULL | |
| `price_per_unit` | `NUMERIC(10,2)` | NULL | **the only price column in IKANOS** |
| `amenity_id` | `UUID` | NULL | restaurant/venue the item belongs to |
| `facility_id` | `UUID` | NULL | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `metadata` | `JSONB` | NULL | **merged from `service_item_metadata`** — veg/non-veg, spicy etc. live here |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** `category_id`/`item_icon`/`amenity_id` `RESTRICT`, `facility_id CASCADE`
- **Indexes** `ix_scitem_category_id`, `ix_scitem_amenity_id`, `ix_scitem_facility_id`, GIN on `metadata`
- **`food_code`, `is_veg`, `is_spicy` are not columns** — they belong in `metadata` (NEEDS_REVIEW C4). `amenity_id` + `amenity_category = 'restaurant'` answers NEEDS_REVIEW **B5** (`restaurant`).

#### 38. `service_request`
- **Purpose:** A service ticket. Drives both Services Tracking and the Tickets module.
- **Source:** `service_requests` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `service_type` | `SMALLINT` | NOT NULL | → `service_type(id)` |
| `ref_number` | `VARCHAR(20)` | NULL | ticket reference |
| `description` | `TEXT` | NULL | |
| `assigned_to` | `UUID` | NULL | **→ `app_user(id)`**, not `employee` |
| `department_id` | `UUID` | NULL | → `department(id)` |
| `category_id` | `UUID` | NULL | → `service_category(id)` |
| `promo_code_id` | `UUID` | NULL | → `promo_code(id)` |
| `amenity_id` | `UUID` | NULL | → `amenity(id)` — the room |
| `stay_id` | `UUID` | NULL | → `stay(id)` |
| `app_user_id` | `UUID` | NULL | the requesting guest (IKANOS `user_id`) |
| `request_source` | `ENUM request_source` | NULL | `ikanos` · `porta` |
| `facility_id` | `UUID` | NULL | |
| `net_amount` | `NUMERIC(10,2)` | NULL | |
| `total_tax` | `NUMERIC(10,2)` | NULL | |
| `total_amount` | `NUMERIC(10,2)` | NULL | |
| `expected_date` | `TIMESTAMPTZ` | NULL | |
| `completed_on` | `TIMESTAMPTZ` | NULL | |
| `status` | `SMALLINT` | NULL | → `service_status(id)` |
| `status_reason` | `VARCHAR(100)` | NULL | |
| `created_by` | `UUID` | NOT NULL | |
| `updated_by` | `UUID` | NOT NULL | |

- **PK** `id` · **UNIQUE** `ref_number` (nullable unique)
- **FK** `service_type`, `category_id`, `status` `RESTRICT`; `amenity_id`, `stay_id`, `facility_id`, `promo_code_id`, `department_id`, `assigned_to` per IKANOS (no FK on `assigned_to`/`user_id` in the dump — **added here as `RESTRICT` [INFER]**, correcting the current wrong target `employee`)
- **Indexes** `ix_sr_service_type`, `ix_sr_category_id`, `ix_sr_amenity_id`, `ix_sr_stay_id`, `ix_sr_facility_id`, `ix_sr_status`, `ix_sr_assigned_to`, `ix_sr_created_on`
- **No `priority` column exists** [FACT] → **REVIEW** (NEEDS_REVIEW C4).
- Resolves gaps **D13, A11, A12, O33, O34**.

#### 39. `service_request_item`
- **Purpose:** Line items on a ticket, with quantity, unit price and per-item assignment.
- **Source:** `service_request_items` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `service_request_id` | `UUID` | NOT NULL | |
| `item_id` | `UUID` | NULL | → `service_category_item(id)` |
| `category_id` | `UUID` | NULL | → `service_category(id)` |
| `quantity` | `SMALLINT` | NULL | |
| `price_per_unit` | `NUMERIC(10,2)` | NULL | |
| `assigned_to` | `UUID` | NULL | |
| `status` | `SMALLINT` | NULL | → `service_status(id)` |

- **PK** `id` · **FK** all `RESTRICT` · **Indexes** on `service_request_id`, `item_id`, `category_id`
- **Explains "Partially completed"** — a ticket is partial when its items differ in status.

#### 40. `room_service_request`
- **Purpose:** Lightweight in-room service call raised from the guest app.
- **Source:** `room_service_requests` — **USE** — **REVIEW §11.7**

| Column | Type | Null | Notes |
|---|---|---|---|
| `guest_room_id` | `UUID` | NOT NULL | → `amenity(id)` |
| `stay_id` | `UUID` | NULL | |
| `service_request_status` | `ENUM room_service_request_status` | NULL DEFAULT `'unassigned'` | |
| `assigned_to` | `UUID` | NULL | |
| `comments` | `TEXT` | NULL | |
| `completed_on` | `TIMESTAMPTZ` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **Enum** `room_service_request_status` = `unassigned` · `assigned` · `cancelled` · `completed` (**a separate vocabulary from `service_status`** [FACT])
- **PK** `id` · **FK** `guest_room_id`, `stay_id` `CASCADE` · **Indexes** on both

#### 41. `room_service_request_item`
- **Purpose:** Items on a room service call.
- **Source:** `room_service_request_items` — **ADAPT** — **REVIEW §11.7**

| Column | Type | Null | Notes |
|---|---|---|---|
| `room_service_request_id` | `UUID` | NOT NULL | |
| `service_category_item_id` | `UUID` | NOT NULL | IKANOS `faciliti_service_id` — **its FK target table does not exist in the dump**; repointed here [INFER] |
| `is_processed` | `SMALLINT` | NULL DEFAULT 0 | |

- **PK** `id` · **FK** `room_service_request_id CASCADE`, `service_category_item_id RESTRICT` [INFER]

---

### GROUP F — Maintenance and Services Planning (4 tables)

#### 42. `maintenance_request`
- **Purpose:** Scheduled, planned and disinfection maintenance. Drives Services Planning.
- **Source:** `service_maintenance_requests` — **ADAPT** (replaces HMS `maintenance_schedule`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `maintenance_request_type` | `ENUM maintenance_request_type` | NOT NULL | **the 3 Services Planning tabs** |
| `maintenance_start_date` | `DATE` | NULL | |
| `maintenance_end_date` | `DATE` | NULL | |
| `maintenance_start_time` | `TIMESTAMPTZ` | NULL | |
| `maintenance_end_time` | `TIMESTAMPTZ` | NULL | |
| `is_recurring` | `SMALLINT` | NULL DEFAULT 0 | |
| `department_id` | `UUID` | NULL | → `department(id)` |
| `category_id` | `UUID` | NULL | → `service_category(id)` |
| `item_id` | `UUID` | NULL | → `service_category_item(id)` |
| `facility_id` | `UUID` | NULL | |
| `completed_on` | `TIMESTAMPTZ` | NULL | |
| `is_room` | `SMALLINT` | NULL | room vs non-room work |
| `non_room_comments` | `TEXT` | NULL | |
| `parent_id` | `UUID` | NULL | self-reference — a recurrence instance points at its template |
| `maintenance_request_status` | `SMALLINT` | NOT NULL | → `service_status(id)` |
| `status_reason` | `VARCHAR(100)` | NULL | |
| `delete_comments` | `TEXT` | NULL | |
| `under_maintenance` | `BOOLEAN` | NULL | takes the room out of service |
| `status` | `SMALLINT` | NULL DEFAULT 1 | soft delete |
| `created_by` | `UUID` | NOT NULL | |
| `updated_by` | `UUID` | NOT NULL | |

- **Enum** `maintenance_request_type` = `scheduled` · `planned` · `disinfection` — **replaces the invented `scheduled_task_type` enum**
- **PK** `id` · **FK** `department_id`, `category_id`, `item_id`, `maintenance_request_status`, `facility_id` all `RESTRICT`; `parent_id → maintenance_request(id) RESTRICT`
- **Indexes** `ix_mr_department_id`, `ix_mr_category_id`, `ix_mr_item_id`, `ix_mr_facility_id`, `ix_mr_status` (business status), `ix_mr_maintenance_start_date`
- **There is no `service_type_id` column** — the current HMS `maintenance_schedule.service_type_id` (a UUID with no FK) has no IKANOS counterpart; the real link is `category_id`/`item_id`. Closes NEEDS_REVIEW **B2/B3**.
- **`startTime` is a real timestamp**, not `VARCHAR(20)` — closes NEEDS_REVIEW **D11**.

#### 43. `maintenance_request_recurrence`
- **Purpose:** Recurrence rule for a maintenance request. 1:1, present only when recurring.
- **Source:** `maintenance_request_recurrence` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NOT NULL | **is the PK** |
| `recurrence_type` | `ENUM recurrence_type` | NOT NULL | |
| `days_of_week` | `SMALLINT` | NULL | bitmask |
| `max_no_of_occurrences` | `SMALLINT` | NULL | |

- **Enum** `recurrence_type` = `weekly` (single-valued in IKANOS [FACT])
- **PK** `maintenance_request_id` · **FK** `→ maintenance_request(id) RESTRICT`
- **Replaces** the HMS `maintenance_schedule.days[]` array column.

#### 44. `maintenance_request_amenity`
- **Purpose:** Rooms covered by a maintenance request.
- **Source:** `service_maintenance_request_amenities` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` (IKANOS uses a surrogate, not a composite) · **FK** both `RESTRICT` · **Indexes** on both

#### 45. `maintenance_request_assignee`
- **Purpose:** Staff assigned to a maintenance request (many per request).
- **Source:** `service_maintenance_request_assignees` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NOT NULL | |
| `app_user_id` | `UUID` | NOT NULL | → `app_user(id)` |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** both `RESTRICT` · **Indexes** on both
- **This is why `maintenance_schedule.assigned_to` (single UUID) is wrong** — assignment is many-to-many.

---

### GROUP G — Devices, telemetry and IoT (14 tables)

#### 46. `device_type`
- **Purpose:** The 4 Caleido device families.
- **Source:** `device_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NULL | |
| `device_short_code` | `ENUM device_short_code` | NULL | |

- **Enum** `device_short_code` = `HUB` · `KLE` · `MIK` · `AIR`
- **Seed (4):** Intellihub (HUB) · Kleio (KLE) · Mikos (MIK) · AirQ (AIR)
- **The HMS `device_type` enum values `LOCK, SENSOR, SWITCH, CONTROLLER` do not exist** — Kleio *is* the lock. Enum → lookup table.

#### 47. `device`
- **Purpose:** A physical device installed in a room.
- **Source:** `devices` + `device_metadata` (MERGE) — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_uid` | `VARCHAR(16)` | NULL | the real device identity |
| `part_number` | `VARCHAR(50)` | NULL | |
| `model` | `VARCHAR(20)` | NULL | |
| `manufacturer_name` | `VARCHAR(50)` | NULL | |
| `mfg_date` | `TIMESTAMPTZ` | NOT NULL | |
| `parent_device_id` | `UUID` | NULL | self-reference — sensors carry their hub id |
| `device_type` | `SMALLINT` | NOT NULL | → `device_type(id)` |
| `device_name` | `VARCHAR(100)` | NULL | |
| `appliance_name` | `VARCHAR(50)` | NULL | |
| `facility_id` | `UUID` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | → `amenity(id)` |
| `authentication_code` | `VARCHAR(20)` | NULL | |
| `health_status` | `ENUM device_health_status` | NULL | |
| `device_temperature` | `NUMERIC(10,2)` | NULL | latest internal temp |
| `current_firmware_version` | `UUID` | NULL | → `firmware(id)` |
| `expected_firmware_version` | `UUID` | NULL | → `firmware(id)` — **this is how "is latest" is computed** |
| `device_config_status` | `ENUM device_config_status` | NULL | |
| `is_power_off` | `BOOLEAN` | NULL | |
| `installed_on` | `TIMESTAMPTZ` | NULL | |
| `operational_mode` | `SMALLINT` | NULL | hubless architecture flag |
| `is_other_device` | `INTEGER` | NULL | 1 = third-party device |
| `status` | `SMALLINT` | NULL DEFAULT 1 | soft delete |
| `metadata` | `JSONB` | NULL | **merged from `device_metadata`** |
| `created_by` | `UUID` | NOT NULL | |

- **Enums**
  - `device_health_status` = `Active` · `Inactive` *(replaces the invented Online/Offline/Error)*
  - `device_config_status` = `configured` · `bad_configuration` · `commissioned` · `decommissioned` · `under_maintenance` · `missing`
- **PK** `id` · **UNIQUE** `device_uid`, `legacy_id`
- **FK** `device_type RESTRICT` · `parent_device_id`, `amenity_id`, `facility_id`, both firmware columns `CASCADE`
- **Indexes** `ix_device_amenity_id`, `ix_device_facility_id`, `ix_device_device_type`, `ix_device_parent_device_id`, `ix_device_health_status`, `ux_device_device_uid`, GIN on `metadata`
- **`ip_address`, `mac_address`, `last_seen` are NOT columns** [FACT] — documented in CPA §8 but absent from the DB. `last_seen` is derivable from `device_health_stat.created_on`. → **REVIEW §11.12** (gaps O31, D55, D56, D61).

#### 48. `firmware`
- **Purpose:** Firmware binaries per device type.
- **Source:** `firmware` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_type_id` | `SMALLINT` | NOT NULL | → `device_type(id)` |
| `firmware_version` | `VARCHAR(20)` | NOT NULL | |
| `firmware_filename` | `VARCHAR(500)` | NOT NULL | |
| `firmware_url` | `VARCHAR(500)` | NOT NULL | |
| `firmware_size` | `NUMERIC(10,2)` | NULL | |
| `crc` | `TEXT` | NOT NULL | |
| `release_date` | `TIMESTAMPTZ` | NULL | |
| `release_notes` | `TEXT` | NULL | |
| `decommission_reason` | `VARCHAR(200)` | NULL | |
| `status` | `ENUM firmware_status` | NOT NULL DEFAULT `'active'` | |
| `uploaded_by` | `UUID` | NOT NULL | |
| `created_by` | `UUID` | NULL | |
| `updated_by` | `UUID` | NULL | |

- **Enum** `firmware_status` = `active` · `decommissioned`
- **PK** `id` · **FK** `device_type_id RESTRICT`; `uploaded_by`/`created_by`/`updated_by → app_user(id) CASCADE`
- **`is_latest` is removed** — currency is `device.current_firmware_version` vs `device.expected_firmware_version`.

#### 49. `device_param`
- **Purpose:** Telemetry parameter registry — **the schema half of the EAV telemetry model.**
- **Source:** `device_params` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `INTEGER` | NOT NULL | **T1** — referenced by a 1.3 M-row table |
| `device_type` | `SMALLINT` | NOT NULL | → `device_type(id)` |
| `param_name` | `VARCHAR(50)` | NOT NULL | voltage, current, humidity, IAQ … |
| `data_type` | `ENUM param_data_type` | NULL | |
| `unit` | `VARCHAR(20)` | NULL | **the missing Y-axis unit (gap D4)** |

- **Enum** `param_data_type` = `Integer` · `Double` · `String` · `Date Time`
- **PK** `id` · **FK** `device_type → device_type(id) RESTRICT` · **Indexes** `ix_device_param_device_type`
- **35 rows in the dump.** This plus `device_stat` **replaces the invented `energy_data` and `sensor_reading` tables**.

#### 50. `device_stat`
- **Purpose:** Every telemetry reading. Powers Power View, Energy View and the device cards.
- **Source:** `device_stats` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `device_id` | `UUID` | NOT NULL | |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL | reading time |
| `device_param_id` | `INTEGER` | NOT NULL | → `device_param(id)` |
| `device_param_value` | `VARCHAR(500)` | NULL | value as text; `device_param.data_type` says how to read it |
| `is_other_device` | `INTEGER` | NULL | |

- **PK** `id` · **FK** both `CASCADE`
- **Indexes** `ix_device_stat_device_id_timestamp` (composite, descending on timestamp) · `ix_device_stat_device_param_id` · **BRIN on `timestamp`** recommended for a table of this size
- **Relationship** one row per parameter per reading. All of D51–D54 (IntelliHub, AirQ, Mikos, Kleio telemetry) come from here.

#### 51. `device_current_stat`
- **Purpose:** Latest snapshot per device, as a single blob — avoids a top-N-per-group query on 1.3 M rows.
- **Source:** `device_current_stats` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_id` | `UUID` | NOT NULL | |
| `device_stats` | `JSONB` | NULL | `blob` in IKANOS; JSON payload |
| `is_other_device` | `INTEGER` | NULL | |

- **PK** `id` · **FK** `device_id → device(id) CASCADE` · **Indexes** `ix_dcs_device_id`
- **Powers** the Room View / Dashboard device tiles without touching `device_stat`.

#### 52. `device_health_stat`
- **Purpose:** Heartbeat/health log per device. 7.7 M rows in the dump.
- **Source:** `device_health_stats` — **ADAPT** (replaces HMS `device_health_log`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `device_id` | `UUID` | NOT NULL | |
| `device_health_status` | `ENUM device_health_status` | NOT NULL | `Active` · `Inactive` |
| `device_temperature` | `NUMERIC(10,2)` | NOT NULL | |

- **PK** `id` · **FK** `device_id → device(id) CASCADE`
- **Indexes** `ix_dhs_device_id_created_on` (composite), BRIN on `created_on`
- **`response_time` and `error_detail` are removed** — neither exists [FACT].
- Resolves gaps **D29, D34, D37, D57** (health counts per building/floor/room).

#### 53. `device_command`
- **Purpose:** Outbound command queue to devices — key issuance, lock/unlock, config push.
- **Source:** `device_commands` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_id` | `UUID` | NOT NULL | |
| `command_type` | `SMALLINT` | NOT NULL | → `command_type(id)` |
| `command_data` | `JSONB` | NOT NULL | `text` (JSON) in IKANOS |
| `processing_status` | `ENUM command_processing_status` | NULL DEFAULT `'Queued'` | |
| `created_by` | `UUID` | NOT NULL | |

- **Enum** `command_processing_status` = `Queued` · `Processing` · `Processed` · `Error`
- **PK** `id` · **FK** both `CASCADE` · **Indexes** `ix_device_command_device_id`, `ix_device_command_processing_status`
- Resolves gaps **O10, B22, D60** (Generate Key, key issuance, device configuration).

#### 54. `command_type`
- **Purpose:** Command registry, optionally scoped to a device type.
- **Source:** `command_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NOT NULL | |
| `device_type_id` | `SMALLINT` | NULL | → `device_type(id)` |

- **PK** `id` · **FK** `device_type_id CASCADE` · **Indexes** `ix_command_type_device_type_id`
- **Backs** the Default Key Settings module.

#### 55. `mqtt_broker`
- **Purpose:** MQTT broker connection per facility.
- **Source:** `mqtt_brokers` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NULL | |
| `broker_name` | `VARCHAR(50)` | NOT NULL | |
| `broker_ip` | `VARCHAR(40)` | NULL | |
| `broker_vpn_ip` | `VARCHAR(40)` | NULL | |
| `broker_port` | `INTEGER` | NULL | |
| `broker_user_name` | `VARCHAR(50)` | NULL | |
| `broker_password` | `VARCHAR(50)` | NULL | **stored in clear in IKANOS** → must be encrypted at rest in HMS. REVIEW §11.13 |

- **PK** `id` · **FK** `facility_id CASCADE` · **Indexes** `ix_mqtt_broker_facility_id`

#### 56. `mqtt_topic`
- **Purpose:** Topic per device per purpose.
- **Source:** `mqtt_topics` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `mqtt_broker_id` | `UUID` | NOT NULL | |
| `device_id` | `UUID` | NULL | |
| `topic_name` | `VARCHAR(50)` | NOT NULL | |
| `topic_type` | `ENUM mqtt_topic_type` | NOT NULL | |

- **Enum** `mqtt_topic_type` = `DeviceData` · `DeviceAlert` · `DeviceHealth` · `LastWill` · `ServerBroadCast` · `ServerToHub` · `DeviceToIkanos` · `IkanosToDevice`
- **PK** `id` · **FK** both `CASCADE` · **Indexes** on both

#### 57. `other_device`
- **Purpose:** Third-party (non-Caleido) energy meter readings. **REVIEW §11.8**
- **Source:** `other_devices` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `msg_id` | `VARCHAR(255)` | NULL | |
| `device_name` | `VARCHAR(225)` | NULL | **no FK to `device`** in IKANOS |
| `voltage` | `DOUBLE PRECISION` | NULL | |
| `current` | `DOUBLE PRECISION` | NULL | |
| `power` | `DOUBLE PRECISION` | NULL | |
| `power_factor` | `DOUBLE PRECISION` | NULL | |
| `all_energy` | `DOUBLE PRECISION` | NULL | |
| `thirty_day_energy` | `DOUBLE PRECISION` | NULL | |
| `today_energy` | `DOUBLE PRECISION` | NULL | |
| `current_hour_energy` | `DOUBLE PRECISION` | NULL | |
| `ec` | `DOUBLE PRECISION` | NULL | IKANOS `EC`; purpose undocumented — REVIEW |
| `msg_string` | `JSONB` | NULL | raw payload |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL | |

- **PK** `id` · **no foreign keys at all** (as in IKANOS) · **Indexes** `ix_other_device_device_name_timestamp`
- **Note:** this table has **no `created_on`/`updated_on`** in IKANOS — only `timestamp`. The implicit audit columns of §5.0 are still added.

#### 58. `battery_life_stat`
- **Purpose:** Battery charge-cycle history per device.
- **Source:** `battery_life_stats` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `device_id` | `UUID` | NOT NULL | **no FK in IKANOS**; added here as `CASCADE` [INFER] |
| `cycle_number` | `SMALLINT` | NOT NULL | |
| `initial_battery_percentage` | `NUMERIC(5,2)` | NULL | |
| `latest_battery_percentage` | `NUMERIC(5,2)` | NULL | |
| `battery_life` | `NUMERIC(6,2)` | NULL | |

- **PK** `id` · **Indexes** `ix_battery_life_stat_device_id`
- **Feeds** the Kleio battery reading (D54) and the "Low battery" amenity condition.

#### 59. `sensor_operation_stat`
- **Purpose:** Daily per-device operational percentage. **The real "Smart Rooms Online" source.**
- **Source:** `sensor_operation_stats` — **USE** (replaces HMS `device_uptime`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_id` | `UUID` | NOT NULL | part of PK |
| `stats_date` | `DATE` | NOT NULL | part of PK |
| `amenity_id` | `UUID` | NOT NULL | |
| `operation_percentage` | `NUMERIC(10,2)` | NOT NULL | |

- **PK** `(device_id, stats_date)` — composite, no surrogate
- **FK** both `CASCADE` · **Indexes** `ix_sos_amenity_id`, `ix_sos_stats_date`
- **`online_minutes`, `offline_minutes`, `uptime_percent` do not exist** — IKANOS stores a single `operation_percentage`. Resolves gap **D12**.

---

### GROUP H — Job orders (3 tables)

#### 60. `job_order`
- **Purpose:** Field work order — installation, replacement, troubleshooting.
- **Source:** `jobs` (caleido) — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `order_reference` | `VARCHAR(20)` | NOT NULL | |
| `description` | `VARCHAR(200)` | NULL | |
| `type_of_work` | `ENUM job_order_type_of_work` | NOT NULL | |
| `work_commence` | `TIMESTAMPTZ` | NOT NULL | |
| `estimated_completion_date` | `TIMESTAMPTZ` | NOT NULL | |
| `authentication_code` | `VARCHAR(20)` | NOT NULL | technician on-site code |
| `assigned_to` | `UUID` | NULL | **→ `app_user(id)`** [FACT: `jobs.assigned_to → users.user_id`] |
| `job_order_status` | `ENUM job_order_status` | NOT NULL DEFAULT `'pending'` | |
| `completed_on` | `TIMESTAMPTZ` | NULL | |
| `status` | `SMALLINT` | NULL | soft delete |
| `created_by` | `UUID` | NOT NULL | |

- **Enums**
  - `job_order_type_of_work` = `installation` · `replacement` · `troubleshoot` *(replaces the invented Commission/Decommission/Maintenance)*
  - `job_order_status` = `pending` · `completed` *(replaces the invented Created/InProgress/Completed)*
- **PK** `id` · **UNIQUE** `order_reference`
- **FK** `assigned_to`, `created_by → app_user(id) RESTRICT`
- **`jobs` has no `facility_id`** [FACT] — scope is reached via `job_order_amenity → amenity`. REVIEW §11.6.
- **Indexes** `ux_job_order_order_reference`, `ix_job_order_assigned_to`, `ix_job_order_job_order_status`

#### 61. `job_order_device`
- **Purpose:** Devices covered by a job order.
- **Source:** `job_devices` — **USE** — **the one current HMS table kept unchanged in shape**

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_order_id` | `UUID` | NOT NULL | part of PK |
| `device_id` | `UUID` | NOT NULL | part of PK |

- **PK** `(job_order_id, device_id)` · **FK** both `RESTRICT` · **Indexes** `ix_job_order_device_device_id`

#### 62. `job_order_amenity`
- **Purpose:** Rooms covered by a job order.
- **Source:** `job_amenities` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_order_id` | `UUID` | NOT NULL | part of PK |
| `amenity_id` | `UUID` | NOT NULL | part of PK |

- **PK** `(job_order_id, amenity_id)` · **FK** both `RESTRICT` · **Indexes** `ix_job_order_amenity_amenity_id`

---

### GROUP I — Access control and digital keys (4 tables)

#### 63. `key_type`
- **Purpose:** Key classification.
- **Source:** `key_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NOT NULL | |

- **PK** `id` · **Seed (4):** Primary · Shared · Staff · Default
- **`Default` is the row behind the Default Key Settings module** and `facility.default_key_user`.

#### 64. `access_key`
- **Purpose:** An issued digital key — app key and keypad key.
- **Source:** `keys` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `user_device_acl_id` | `UUID` | NULL | → `user_device_acl(id)` |
| `app_key` | `VARCHAR(10)` | NOT NULL | mobile unlock code |
| `keypad_key` | `VARCHAR(10)` | NOT NULL | keypad unlock code |
| `key_type` | `SMALLINT` | NOT NULL | → `key_type(id)` |
| `device_id` | `UUID` | NULL | the lock |
| `stay_id` | `UUID` | NULL | |
| `maintenance_request_id` | `UUID` | NULL | staff key for maintenance access |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** all `CASCADE` except `key_type RESTRICT`
- **Indexes** `ix_access_key_stay_id`, `ix_access_key_device_id`, `ix_access_key_user_device_acl_id`, `ix_access_key_key_type`
- Resolves gaps **O10, B22** and gives the Default Key Settings module its first table.

#### 65. `user_device_acl`
- **Purpose:** Time-boxed grant of a user's access to a device in a room.
- **Source:** `user_device_acl` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `app_user_id` | `UUID` | NOT NULL | |
| `device_type_id` | `SMALLINT` | NOT NULL | |
| `device_id` | `UUID` | NOT NULL | |
| `amenity_type_id` | `UUID` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | |
| `stay_id` | `UUID` | NULL | |
| `start_time` | `TIMESTAMPTZ` | NOT NULL | |
| `end_time` | `TIMESTAMPTZ` | NOT NULL | **access expires with the stay** |
| `status_id` | `SMALLINT` | NOT NULL | |
| `created_by` | `UUID` | NULL | |

- **PK** `id` · **FK** all six `CASCADE`
- **Indexes** on all six FK columns, plus `ix_udacl_end_time`
- **This is the mechanism behind automatic key expiry at checkout.**

#### 66. `lock_activity_log`
- **Purpose:** Every lock and unlock event.
- **Source:** `lock_activity_log` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL | |
| `app_user_id` | `UUID` | NULL | |
| `event` | `ENUM lock_event` | NULL | |
| `unlock_mode` | `ENUM lock_unlock_mode` | NULL | |
| `lock_id` | `UUID` | NOT NULL | → `device(id)` |
| `amenity_id` | `UUID` | NOT NULL | |
| `stay_id` | `UUID` | NULL | |
| `facility_id` | `UUID` | NOT NULL | |
| `key_type` | `SMALLINT` | NULL | → `key_type(id)` |

- **Enums** `lock_event` = `locked` · `unlocked` · `lock_unlock_mode` = `app` · `keypad`
- **PK** `id` · **FK** all `CASCADE` except `key_type RESTRICT`
- **Indexes** `ix_lal_lock_id_timestamp`, `ix_lal_amenity_id`, `ix_lal_facility_id`, `ix_lal_app_user_id`
- **Feeds** the Kleio "Lock Status" reading (gap D54).
---

### GROUP J — Alerts, incidents and value limits (8 tables)

#### 67. `alert_type`
- **Purpose:** The alert catalogue. **16 real rows.**
- **Source:** `alert_types` — **ADAPT** (reduced to `(id, name)`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NOT NULL | |

- **PK** `id`
- **Seed (16):** BatteryLow · DeviceDisconnection · LoginAttemptsFailure · ImproperShaftMovement · DeviceOverheating · PreventiveMaintenance · MikosOvercurrentTrip · RoomAirQualityPoor · RoomInternalHot · AirConditioningFail · TamperingAttempt · DoorAjar · HubOffline · MikosOffline · LockOffline · AirqOffline
- **`severity`, `category`, `description`, `is_active` are REMOVED** — they do not exist [FACT]. Severity lives on `device_alert.alert_severity`. These rows are exactly the Network Alert Tracking table contents.

#### 68. `device_alert`
- **Purpose:** Raw alert stream from devices. 46 k rows in the dump.
- **Source:** `device_alerts` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `device_id` | `UUID` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | **the affected room (gap D23)** |
| `alert_type` | `SMALLINT` | NOT NULL | → `alert_type(id)` |
| `alert_severity` | `ENUM alert_severity` | NULL | |
| `alert_data` | `JSONB` | NULL | `text` (JSON) in IKANOS |
| `created_by` | `UUID` | NOT NULL | |

- **Enum** `alert_severity` = `warning` · `critical` — **only two values; `Info` does not exist**
- **PK** `id` · **FK** all `CASCADE` · **Indexes** `ix_device_alert_device_id`, `ix_device_alert_amenity_id`, `ix_device_alert_alert_type`, `ix_device_alert_created_on`
- **Relationship** `device_incident.latest_alert_id → device_alert.id`. **Alerts are the event stream; incidents are the deduplicated, assignable case.** This linkage is entirely missing from the current HMS schema.

#### 69. `device_incident`
- **Purpose:** The assignable, resolvable case raised from one or more alerts.
- **Source:** `device_incidents` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | **added** |
| `device_id` | `UUID` | NOT NULL | |
| `alert_type` | `SMALLINT` | NOT NULL | **added** → `alert_type(id)` |
| `subject` | `VARCHAR(200)` | NULL | |
| `description` | `TEXT` | NULL | |
| `assigned_to` | `UUID` | NULL | **→ `app_user(id)`**, not `employee` |
| `latest_alert_id` | `BIGINT` | NULL | **added** → `device_alert(id)` |
| `current_incident_status` | `SMALLINT` | NULL | → `incident_status(id)` |
| `updated_by` | `UUID` | NULL | |

- **PK** `id` · **FK** `facility_id`, `amenity_id`, `device_id`, `alert_type`, `latest_alert_id`, `current_incident_status` `CASCADE`; `updated_by`, `assigned_to → app_user(id) RESTRICT`
- **Indexes** `ix_di_facility_id`, `ix_di_amenity_id`, `ix_di_device_id`, `ix_di_alert_type`, `ix_di_latest_alert_id`, `ix_di_current_incident_status`, `ix_di_assigned_to`, `ix_di_created_on`
- **REMOVED (do not exist [FACT]):** `severity`, `alert_severity`, `notes`, `resolved_on`, `assigned_user JSONB`. Severity comes from `device_alert`; resolution time and notes come from `incident_history`. This closes NEEDS_REVIEW **D6** and **D7**.
- Resolves gaps **D19–D28, D31, O38**.

#### 70. `incident_status`
- **Purpose:** Current incident state.
- **Source:** `incident_statuses` — **ADAPT** (reduced to `(id, name)`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NOT NULL | |

- **PK** `id` · **Seed (4):** Unread · Read · Assigned · Resolved
- **`Open` was invented and is removed.** `status_code`, `display_color`, `is_resolved` do not exist.

#### 71. `incident_event`
- **Purpose:** Vocabulary of transitions written to the incident audit trail.
- **Source:** `incident_events` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `name` | `VARCHAR(50)` | NOT NULL | |

- **PK** `id` · **Seed (5):** Unread · Read · Assigned · Resolved · **Reopened**
- **`Reopened` exists only as an event, never as a status** [FACT] — a reopened incident returns to an earlier `incident_status`.

#### 72. `incident_history`
- **Purpose:** Audit trail of every incident transition. 46 k rows.
- **Source:** `incident_history` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `incident_id` | `UUID` | NOT NULL | |
| `incident_event_id` | `SMALLINT` | NOT NULL | |
| `incident_event_data` | `JSONB` | NULL | `text` in IKANOS — carries the note and the assignee |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** both `CASCADE` · **Indexes** `ix_ih_incident_id`, `ix_ih_incident_event_id`
- **This is where `resolved_on` and `notes` actually live** — as the `Resolved` event row and its `incident_event_data`.

#### 73. `value_alert`
- **Purpose:** Threshold-breach alert on a telemetry parameter.
- **Source:** `value_alerts` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_id` | `UUID` | NOT NULL | |
| `device_type_id` | `SMALLINT` | NOT NULL | |
| `device_name` | `VARCHAR(50)` | NOT NULL | |
| `amenity_id` | `UUID` | NOT NULL | |
| `limit_config_id` | `UUID` | NOT NULL | → `value_alert_limit_config(id)` — **`parameter` lives there, not here** |
| `device_status_id` | `INTEGER` | NOT NULL | purpose undocumented → REVIEW |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL | `date` in IKANOS; widened |
| `limit_value` | `VARCHAR(50)` | NOT NULL | |
| `limit_type` | `VARCHAR(50)` | NOT NULL | "low" or "high" — **a varchar in IKANOS, not an enum** |
| `description` | `TEXT` | NOT NULL | |
| `status` | `SMALLINT` | NOT NULL DEFAULT 0 | `0` = Active, `1` = Resolved (NEEDS_REVIEW D8 — kept as an integer, as documented) |
| `facility_id` | `UUID` | NOT NULL | |

- **PK** `id` · **IKANOS declares no FKs on this table**; `device_id`, `amenity_id`, `facility_id`, `limit_config_id` are added here as `RESTRICT` [INFER]
- **Indexes** `ix_value_alert_device_id`, `ix_value_alert_amenity_id`, `ix_value_alert_limit_config_id`, `ix_value_alert_timestamp`, `ix_value_alert_status`
- **REMOVED:** `parameter`, `unit`, `current_value` — none exists [FACT]. `parameter` is on the config row; `unit` is on `device_param`.
- Resolves gap **D58** (threshold-breach highlighting).

#### 74. `value_alert_limit_config`
- **Purpose:** Per-device-name, per-parameter limits. Backs the Limit Config Alert screen.
- **Source:** `value_alert_limit_config` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `parameter` | `VARCHAR(50)` | NOT NULL | voltage, current, power … |
| `device_name` | `VARCHAR(50)` | NOT NULL | **IKANOS keys by name, not id** |
| `device_id` | `UUID` | NULL | **added, nullable** [INFER] — lets HMS resolve to a real device without losing the name key |
| `limit_check` | `CHAR(1)` | NOT NULL | enabled/disabled |
| `is_percentage_value` | `CHAR(3)` | NOT NULL | percentage vs absolute mode |
| `nominal` | `INTEGER` | NULL | |
| `limit_low_percentage` | `INTEGER` | NULL | |
| `limit_high_percentage` | `INTEGER` | NULL | |
| `limit_low_value` | `INTEGER` | NULL | |
| `limit_high_value` | `INTEGER` | NULL | |
| `remarks` | `TEXT` | NOT NULL | |
| `facility_id` | `UUID` | NOT NULL | |

- **PK** `id` · **UNIQUE** `(device_name, parameter, facility_id)` [INFER — no unique key in IKANOS]
- **Indexes** `ix_valc_device_name`, `ix_valc_facility_id`
- **The HMS `limit_type` enum (`high`/`low`) is not an enum in IKANOS** — a config row carries **both** a low and a high limit, in **both** percentage and absolute form. `highLimit`/`lowLimit`/`unit` from the documentation map onto these five columns.
- Resolves gap **D59** (AirQ banded scale thresholds).

---

### GROUP K — Activity feed and notification dispatch (9 tables)

> **Why nine tables and not one.** IKANOS separates two concerns that the current HMS `notification` table conflates:
> **(a) the in-app feed** — `activity` → `activity_notifier`, per-user read state, driven by `activity_type` / `entity_type` / `activity_role_association`;
> **(b) the dispatch queue** — `notification` → `notification_receiver` → `notification_result`, one row per channel per recipient, rendered from `notification_template`.
> The Header bell reads (a). Email/SMS/push delivery is (b). `activity.activity_response_ids` links a feed item to the dispatch rows it produced. This closes comparison Deferred Item 7.

#### 75. `entity_type`
- **Source:** `entity_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `entity_type` | `VARCHAR(50)` | NOT NULL | |

- **PK** `id` · **Seed (5):** Booking · Occupancy · Service Requests · Maintenance Requests · Default Key
- **This is the real `notification_type` axis** — the invented HMS enum (`alert`/`service`/`booking`/`system`/`event`) is discarded.

#### 76. `activity_type`
- **Source:** `activity_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `activity_type` | `VARCHAR(50)` | NOT NULL | |
| `entity_type_id` | `SMALLINT` | NOT NULL | → `entity_type(id)` |
| `notification_type` | `CHAR(3)` | NOT NULL | |
| `is_subscribable` | `BOOLEAN` | NULL DEFAULT true | |

- **PK** `id` · **FK** `entity_type_id CASCADE` · **Indexes** `ix_activity_type_entity_type_id`

#### 77. `activity`
- **Purpose:** One business event worth telling someone about.
- **Source:** `activities` + `activity_data` (MERGE) — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `activity_type_id` | `SMALLINT` | NOT NULL | |
| `entity_type_id` | `SMALLINT` | NOT NULL | |
| `entity_id` | `BIGINT` | NOT NULL | polymorphic — **no FK possible**, by design (NEEDS_REVIEW D9 confirmed) |
| `facility_id` | `UUID` | NOT NULL | |
| `actor_id` | `UUID` | NOT NULL | → `app_user(id)` — who caused it |
| `stay_id` | `UUID` | NULL | |
| `activity_response_ids` | `TEXT` | NULL | comma-separated dispatch notification ids |
| `data_version` | `SMALLINT` | NOT NULL | **merged from `activity_data.version`** — selects the template |
| `data` | `JSONB` | NOT NULL | **merged from `activity_data.data`** |

- **PK** `id` · **FK** `activity_type_id`, `entity_type_id`, `actor_id`, `facility_id` `CASCADE`
- **Indexes** `ix_activity_facility_id`, `ix_activity_entity_type_id_entity_id` (composite), `ix_activity_actor_id`, `ix_activity_created_on`
- **`entity_id` stays polymorphic** — it points at a booking, a room, a ticket. Confirms NEEDS_REVIEW D9: no FK is possible.

#### 78. `activity_notifier`
- **Purpose:** Per-user delivery of a feed item, with read state. **This is the Header notification list.**
- **Source:** `activity_notifiers` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `activity_id` | `BIGINT` | NOT NULL | part of PK |
| `app_user_id` | `UUID` | NOT NULL | part of PK |
| `status` | `ENUM activity_notifier_status` | NOT NULL | |
| `user_type` | `ENUM activity_notifier_user_type` | NULL | selects the message template |
| `notification_type` | `SMALLINT` | NULL | |

- **Enums** `activity_notifier_status` = `0` unread · `1` read · `2` clear · `activity_notifier_user_type` = `0` · `1` · `2` *(IKANOS stores these as `enum('0','1','2')` — string enums of digits. Preserved verbatim; the label meanings for `user_type` are undocumented → REVIEW)*
- **PK** `(activity_id, app_user_id)` · **FK** both `CASCADE`
- **Indexes** `ix_an_app_user_id`, `ix_an_status`, `ix_an_user_type`, `ix_an_notification_type`
- Resolves gaps **H1, H2, H3, H5, H6** (real feed, unread count, type, timestamp, persisted read state).

#### 79. `activity_role_association`
- **Purpose:** Which roles are notified of which activity type.
- **Source:** `activity_role_association` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `activity_type_id` | `SMALLINT` | NOT NULL | part of PK |
| `role_id` | `UUID` | NOT NULL | part of PK |

- **PK** `(activity_type_id, role_id)` · **FK** both `RESTRICT` · **Indexes** `ix_ara_role_id`

#### 80. `notification`
- **Purpose:** Dispatch queue entry — one outbound message to render and send.
- **Source:** `notifications` + `notification_params` (MERGE) — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `created_by` | `VARCHAR(100)` | NOT NULL | **a service name string in IKANOS, not a user FK** [FACT] |
| `status` | `ENUM notification_status` | NOT NULL | |
| `reference_id` | `BIGINT` | NULL | the originating `activity.id` |
| `template_id` | `UUID` | NULL | → `notification_template(id)` |
| `params` | `JSONB` | NULL | **merged from `notification_params`** |

- **Enum** `notification_status` = `pending` · `processing` · `processed` · `error`
- **PK** `id` · **FK** `template_id RESTRICT` · **Indexes** `ix_notification_status`, `ix_notification_template_id`, `ix_notification_reference_id`

#### 81. `notification_template`
- **Purpose:** Message template per channel.
- **Source:** `templates` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NOT NULL | |
| `type` | `ENUM notification_channel` | NOT NULL | |
| `path` | `VARCHAR(100)` | NOT NULL | template file path |

- **Enum** `notification_channel` = `email` · `sms` · `push notification` · `silent notification`
- **PK** `id` · **UNIQUE** `(name, type)` [INFER] · 16 rows in the dump
- Resolves gap **H8** (SMS/email channels absent from HMS).

#### 82. `notification_receiver`
- **Purpose:** One recipient of one notification, with contact snapshot.
- **Source:** `notification_receivers` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** — 46 k rows |
| `app_user_id` | `UUID` | NULL | |
| `notification_id` | `BIGINT` | NOT NULL | |
| `name` | `VARCHAR(100)` | NOT NULL | |
| `email` | `VARCHAR(256)` | NULL | |
| `phone` | `VARCHAR(20)` | NULL | |
| `device_token` | `VARCHAR(200)` | NULL | |
| `data` | `JSONB` | NULL | per-recipient merge data |

- **PK** `id` · **FK** `notification_id RESTRICT`, `app_user_id RESTRICT` [INFER — IKANOS stores a bare `bigint`]
- **Indexes** `ix_nr_notification_id`, `ix_nr_app_user_id`
- **This table has no `created_on`/`updated_on` in IKANOS**; the implicit audit columns of §5.0 are still added.

#### 83. `notification_result`
- **Purpose:** Delivery outcome per recipient per channel.
- **Source:** `notification_results` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `receiver_id` | `BIGINT` | NOT NULL | → `notification_receiver(id)` [INFER — no FK in IKANOS] |
| `type` | `ENUM notification_channel` | NOT NULL | same enum as the template |
| `status` | `VARCHAR(15)` | NOT NULL | provider status string |
| `log` | `JSONB` | NULL | provider response |
| `body` | `TEXT` | NULL | rendered message |

- **PK** `id` · **Indexes** `ix_nres_receiver_id`, `ix_nres_type`, `ix_nres_created_on`
- **`updated_on` does not exist in IKANOS** on this table (append-only); added per §5.0.

---

### GROUP L — Scheduler (2 tables)

#### 84. `scheduler_job`
- **Purpose:** Cron job definition — housekeeping, sanitation, checkout, expiry.
- **Source:** `caleido_scheduler.jobs` — **ADAPT** (replaces HMS `scheduled_task`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_key` | `VARCHAR(100)` | NOT NULL | IKANOS `job_id` — the cron key |
| `job_name` | `VARCHAR(50)` | NOT NULL | |
| `job_data` | `JSONB` | NULL | schedule + parameters |
| `status` | `ENUM scheduler_job_status` | NOT NULL | |
| `is_dynamic_job` | `SMALLINT` | NOT NULL DEFAULT 0 | |

- **Enum** `scheduler_job_status` = `active` · `inactive`
- **PK** `id` · **UNIQUE** `job_key`
- **Renamed** because `caleido.jobs` (→ `job_order`) and `caleido_scheduler.jobs` are unrelated entities sharing a name.
- **The HMS `scheduled_task` columns `type`, `target_entity`, `scheduled_at`, `last_executed`, `recur_pattern` have no IKANOS counterpart** — the schedule lives inside `job_data`, and execution history lives in `scheduler_job_execution`. Closes NEEDS_REVIEW **D10**.

#### 85. `scheduler_job_execution`
- **Purpose:** One run of a scheduled job. 3.5 k rows.
- **Source:** `job_executions` — **ADAPT**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BIGINT` identity | NOT NULL | **T3** |
| `scheduler_job_id` | `UUID` | NOT NULL | → `scheduler_job(id)` |
| `job_execution_date` | `TIMESTAMPTZ` | NOT NULL | |
| `job_response` | `BYTEA` | NULL | `blob` in IKANOS |
| `status` | `ENUM scheduler_execution_status` | NOT NULL | |
| `job_run_duration` | `INTEGER` | NOT NULL | milliseconds |

- **Enum** `scheduler_execution_status` = `passed` · `failed` — **replaces the invented `Pending/Executed/Cancelled/Failed`**
- **PK** `id` · **FK** `scheduler_job_id CASCADE` · **Indexes** `ix_sje_scheduler_job_id`, `ix_sje_job_execution_date`
- **This table has no `created_on`/`updated_on` in IKANOS**; added per §5.0.

---

### GROUP M — Marketing, events and occasions (5 tables)

#### 86. `promo_code`
- **Purpose:** Discount offer. Backs the Offers module.
- **Source:** `promo_codes` — **ADAPT** (replaces HMS `offer`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `offer_name` | `VARCHAR(100)` | NULL | |
| `promo_code` | `VARCHAR(20)` | NOT NULL | the coupon code |
| `start_time` | `TIMESTAMPTZ` | NULL | |
| `expiry_time` | `TIMESTAMPTZ` | NULL | |
| `discount_percentage` | `SMALLINT` | NULL | |
| `max_discount_value` | `NUMERIC(10,2)` | NULL | |
| `min_order_value` | `NUMERIC(10,2)` | NULL | |
| `promo_code_icon` | `UUID` | NULL | → `attachment(id)` |
| `promo_code_description` | `VARCHAR(250)` | NULL | |
| `offered_by` | `VARCHAR(100)` | NULL | |
| `status` | `SMALLINT` | NULL DEFAULT 1 | **the "withdrawn" state** |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **UNIQUE** `promo_code` · **FK** `promo_code_icon → attachment(id) RESTRICT`
- **`promo_codes` has no `facility_id`** [FACT] — scope is via `promo_code_amenity`. REVIEW §11.6.
- **Indexes** `ux_promo_code_promo_code`, `ix_promo_code_expiry_time`, `ix_promo_code_status`
- **All 8 discount columns the current `offer` table lacks are here.** `PUT /offers/{ID}/withdraw` maps to `status`.

#### 87. `promo_code_amenity`
- **Purpose:** Which rooms an offer applies to.
- **Source:** `promo_code_amenities` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `promo_code_id` | `UUID` | NOT NULL | part of PK |
| `amenity_id` | `UUID` | NOT NULL | part of PK |
| `status` | `SMALLINT` | NULL DEFAULT 1 | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `(promo_code_id, amenity_id)` · **FK** both `RESTRICT` · **Indexes** `ix_pca_amenity_id`

#### 88. `facility_event`
- **Purpose:** A hotel event. Backs the Events module.
- **Source:** `facility_events` — **ADAPT** (replaces HMS `event`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `facility_id` | `UUID` | NOT NULL | |
| `name` | `VARCHAR(100)` | NOT NULL | |
| `venue` | `VARCHAR(200)` | NULL | **a free-text string, not an `amenity` FK** [FACT] |
| `chief_guests` | `VARCHAR(500)` | NULL | |
| `description` | `TEXT` | NULL | |
| `expected_attendees` | `SMALLINT` | NULL | |
| `interested_attendees` | `SMALLINT` | NULL DEFAULT 0 | |
| `start_date_time` | `TIMESTAMPTZ` | NULL | |
| `end_date_time` | `TIMESTAMPTZ` | NULL | |
| `image_id` | `UUID` | NULL | → `attachment(id)` |
| `cancellation_reason` | `TEXT` | NULL | backs `PUT /events/{ID}/cancel` |
| `status` | `SMALLINT` | NULL | |
| `created_by` | `UUID` | NOT NULL | |

- **PK** `id` · **FK** `facility_id CASCADE`, `image_id RESTRICT` · **Indexes** `ix_facility_event_facility_id`, `ix_facility_event_start_date_time`
- Closes NEEDS_REVIEW **C4** for `event` — every "not defined" field turns out to exist in the DB.

#### 89. `occasion_type`
- **Source:** `occasion_types` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `SMALLINT` | NOT NULL | **T1** |
| `occasion_type` | `VARCHAR(50)` | NOT NULL | |
| `notification_template` | `TEXT` | NULL | |

- **PK** `id` · **Seed (4):** Festival · Birthday · Marriage anniversary · **Holiday**

#### 90. `occasion`
- **Purpose:** A dated occasion. **`occasion_type = 'Holiday'` is the Holidays module.**
- **Source:** `occasions` — **USE** — **REVIEW §11.5**

| Column | Type | Null | Notes |
|---|---|---|---|
| `occasion_name` | `VARCHAR(100)` | NULL | |
| `occasion_type` | `SMALLINT` | NOT NULL | → `occasion_type(id)` |
| `is_repeatable` | `BOOLEAN` | NULL DEFAULT false | |
| `notification_template` | `TEXT` | NULL | |
| `facility_id` | `UUID` | NULL | |
| `month` | `SMALLINT` | NOT NULL | |
| `day_of_month` | `SMALLINT` | NOT NULL | |
| `app_user_id` | `UUID` | NULL | for personal occasions (birthday, anniversary) |
| `notify_to_hub` | `BOOLEAN` | NULL DEFAULT true | pushes the occasion to in-room hubs |
| `occasion_start_date` | `DATE` | NOT NULL | |
| `occasion_end_date` | `DATE` | NULL | |
| `status` | `SMALLINT` | NULL | |
| `created_by` | `UUID` | NULL | |

- **PK** `id` · **FK** `occasion_type CASCADE`, `facility_id CASCADE`, `app_user_id CASCADE`, `created_by CASCADE`
- **Indexes** `ix_occasion_occasion_type`, `ix_occasion_facility_id`, `ix_occasion_occasion_start_date`
- **There is no `lock_message` column** [FACT], yet the HMS Holidays screen is built entirely around "Lock message". `notification_template` is the nearest field — it is the message pushed to hubs when `notify_to_hub` is set. **Mapping asserted as [INFER], not resolved → §11.5.**

---

### GROUP N — Energy and reporting (2 tables)

#### 91. `energy_stat`
- **Purpose:** Hourly energy rollup per device per room. Backs Energy View and the Dashboard energy chart.
- **Source:** `energy_stats` — **ADAPT** (replaces HMS `energy_aggregate`)

| Column | Type | Null | Notes |
|---|---|---|---|
| `device_name` | `VARCHAR(11)` | NOT NULL | part of PK — a room can hold several standalone devices |
| `facility_id` | `UUID` | NOT NULL | part of PK |
| `amenity_id` | `UUID` | NOT NULL | part of PK |
| `hour` | `BIGINT` | NOT NULL | part of PK — **hours elapsed since 2000**, not a timestamp |
| `energy_consumed` | `DOUBLE PRECISION` | NOT NULL | |

- **PK** `(device_name, facility_id, amenity_id, hour)` — composite, no surrogate id
- **Indexes** `ix_energy_stat_amenity_id_hour`, `ix_energy_stat_facility_id_hour`
- **`avg_power`, `max_power`, `total_energy`, `interval`, `room_id` do not exist** [FACT]. IKANOS stores **one metric, hourly only**. The invented `aggregate_interval` enum (`5min`/`hourly`/`daily`) is discarded — daily and weekly rollups are aggregated at query time.
- Resolves gaps **D3, D5, D7, O37** — with the caveat that avg/max power are derived, not stored.

#### 92. `daily_dual_data_point`
- **Purpose:** Pre-aggregated daily KPI pairs. **`metric_type` is exactly the Caleido At Work KPI set.**
- **Source:** `daily_dual_data_points` — **USE**

| Column | Type | Null | Notes |
|---|---|---|---|
| `metric_date` | `DATE` | NOT NULL | part of PK |
| `metric_type` | `ENUM daily_metric_type` | NOT NULL | part of PK |
| `dp_1` | `NUMERIC(10,2)` | NOT NULL | numerator (e.g. rooms online) |
| `dp_2` | `NUMERIC(10,2)` | NOT NULL | denominator (e.g. rooms total) |
| `facility_id` | `UUID` | NOT NULL | |

- **Enum** `daily_metric_type` = `smart room` · `service request` · `checkout` · `booking` · `guest room`
- **PK** `(metric_date, metric_type)` — composite. **Note: `facility_id` is NOT in the IKANOS PK** [FACT], so the table is single-facility as built → **REVIEW §11.6.**
- **Indexes** `ix_dddp_facility_id_metric_date`
- **The `dp_1`/`dp_2` pair is why the Dashboard rings show "n of m".** Resolves gaps **D12, D13, D14, D15, D16** — the four "Caleido At Work" cards that currently render `0%` and `-` map one-to-one onto `smart room`, `service request`, `checkout`, `booking`.
---

## 6. TABLES DIRECTLY COPIED FROM IKANOS (57)

Structure, columns, keys and relationships preserved. The only changes are PK type per §2.3, the `legacy_id` column, dropping `facility_uid`, and MySQL→PostgreSQL type mapping (`tinyint(1)`→`BOOLEAN`, `text`(JSON)→`JSONB`, `datetime`→`TIMESTAMPTZ`, `double`→`DOUBLE PRECISION`, `decimal`→`NUMERIC`).

`organisation` · `facility_user` · `property` · `property_chain` · `attachment` · `country` · `amenity_status` · `amenity_condition` · `amenity_condition_status` · `sub_package` · `feature` · `package_feature` · `stay_user` · `stay_package` · `room_allocation` · `user_document` · `user_token` · `user_device` · `role` · `role_module` · `role_module_permission` · `service_type` · `service_status` · `service_category` · `service_request_item` · `room_service_request` · `maintenance_request_recurrence` · `maintenance_request_amenity` · `maintenance_request_assignee` · `device_type` · `device_param` · `device_stat` · `device_current_stat` · `device_command` · `command_type` · `mqtt_broker` · `mqtt_topic` · `battery_life_stat` · `sensor_operation_stat` · `job_order_device` · `job_order_amenity` · `key_type` · `user_device_acl` · `lock_activity_log` · `device_alert` · `incident_event` · `incident_history` · `entity_type` · `activity_type` · `activity_notifier` · `activity_role_association` · `notification_receiver` · `notification_result` · `promo_code_amenity` · `occasion_type` · `occasion` · `daily_dual_data_point`

**14 of these 57 carry seeded reference data read from the dump** and must be loaded before anything else works: `country` (239) · `amenity_status` (4) · `amenity_condition` (4) · `service_type` (7) · `service_status` (5) · `role_module` (18) · `device_type` (4) · `device_param` (35) · `command_type` · `key_type` (4) · `incident_event` (5) · `entity_type` (5) · `activity_type` · `occasion_type` (4). Add the two ADAPT lookups `alert_type` (16) and `incident_status` (4) → **16 seed tables**.

---

## 7. TABLES ADAPTED FROM IKANOS (35)

| Final table | IKANOS source | Nature of the adaptation |
|---|---|---|
| `facility` | `facilities` | `cloud_details` → `JSONB` |
| `property_type` | `property_types` | `levels tinyint(1)` → `SMALLINT` (holds 1–3) |
| `amenity_type` | `amenity_types` | enum restored |
| `amenity` | `amenities` + `amenity_metadata` | `property_chain_id` replaces `floor`/`property_type_id`; `status` gains an inferred FK; metadata → JSONB |
| `package` | `packages` | `price` not carried (does not exist); `amenity_type` gains an inferred FK |
| `stay` | `stays` | absorbs the HMS `booking` entity; 14 columns restored |
| `invoice` | `invoices` | money → `NUMERIC(10,2)`; no `status` column |
| `import_job` | `imports` | renamed |
| `app_user` | `users` + `user_login_details` + `user_metadata` | absorbs credentials and metadata; absorbs the HMS `employee` entity |
| `user_role` | `user_roles` | PK is the 3-column IKANOS composite |
| `department` | `departments` | UUID PK |
| `job_function` | `functions` | renamed; **FK repointed to facility** |
| `service_category_item` | `service_category_items` + `service_item_metadata` | metadata → JSONB |
| `service_request` | `service_requests` | `assigned_to` repointed to `app_user`; FKs added where IKANOS had bare integers |
| `room_service_request_item` | `room_service_request_items` | orphaned FK repointed [INFER] |
| `maintenance_request` | `service_maintenance_requests` | renamed; recurrence split out |
| `device` | `devices` + `device_metadata` | invented network columns removed; metadata → JSONB |
| `firmware` | `firmware` | `is_latest` removed; real status enum added |
| `device_health_stat` | `device_health_stats` | BIGINT identity; invented columns removed |
| `other_device` | `other_devices` | `json` → `JSONB`; `EC` → `ec` |
| `job_order` | `caleido.jobs` | renamed to resolve the `jobs` collision |
| `access_key` | `keys` | renamed (`keys` ambiguous in PostgreSQL) |
| `alert_type` | `alert_types` | reduced to `(id, name)` |
| `incident_status` | `incident_statuses` | reduced to `(id, name)` |
| `device_incident` | `device_incidents` | 5 invented columns removed; 4 real columns added |
| `value_alert` | `value_alerts` | 3 invented columns removed; FKs added [INFER] |
| `value_alert_limit_config` | `value_alert_limit_config` | nullable `device_id` added [INFER]; unique key added [INFER] |
| `activity` | `activities` + `activity_data` | 1:1 absorbed |
| `notification` | `notifications` + `notification_params` | param bag absorbed |
| `notification_template` | `templates` | renamed |
| `facility_event` | `facility_events` | UUID PK only |
| `promo_code` | `promo_codes` | UUID PK only |
| `energy_stat` | `energy_stats` | composite PK preserved verbatim |
| `scheduler_job` | `caleido_scheduler.jobs` | renamed; `job_id` → `job_key` |
| `scheduler_job_execution` | `job_executions` | `blob` → `BYTEA` |

---

## 8. NEW HMS-SPECIFIC TABLES

**None. Zero.**

Every one of the 92 final tables maps to a table that exists in the IKANOS dump. The three technical additions are *columns*, not tables, and each is declared openly:

| Addition | Scope | Declared in |
|---|---|---|
| `id` as `UUID` / `BIGINT` identity instead of `AUTO_INCREMENT` | all tables | §2.3 |
| `legacy_id BIGINT UNIQUE` | all tables | §2.3 |
| `created_on` / `updated_on` on the 6 IKANOS tables that lack them | `other_device`, `notification_receiver`, `notification_result`, `scheduler_job_execution`, `notification_params`(merged), `notification` | §5.0 |

The one piece of infrastructure outside the count is Alembic's own `alembic_version` table.

---

## 9. TABLES REMOVED FROM THE CURRENT 39-TABLE FOUNDATION

### 9.1 Removed outright — no replacement table (4)

| Removed | Why |
|---|---|
| `employee` | No such table in IKANOS. Staff are `users` rows with `is_staff = 1`. → `app_user` |
| `booking` | No such table in IKANOS. The reservation **is** the stay. → `stay` |
| `energy_data` | Invented. Telemetry is `device_param` + `device_stat` |
| `sensor_reading` | Invented. Same EAV path |

### 9.2 Removed and replaced by a differently-shaped IKANOS table (10)

| Removed | Replaced by |
|---|---|
| `occupant` | `stay_user` |
| `stay` (Phase 1 shape) | `stay` (21-column IKANOS shape) |
| `food_category` | `service_category` |
| `food_menu` | `service_category_item` |
| `holiday` | `occasion` (REVIEW §11.5) |
| `notification` | `activity` + `activity_notifier` + `notification` + `notification_receiver` + `notification_result` |
| `maintenance_schedule` | `maintenance_request` + `maintenance_request_recurrence` + 2 junctions |
| `scheduled_task` | `scheduler_job` + `scheduler_job_execution` |
| `energy_aggregate` | `energy_stat` |
| `device_uptime` | `sensor_operation_stat` |

### 9.3 Columns removed from surviving tables

| Table | Columns removed | Evidence |
|---|---|---|
| `device` | `ip_address`, `mac_address`, `last_seen` | Absent from `devices` [FACT] |
| `firmware` | `is_latest` | Absent; currency is current vs expected firmware version |
| `alert_type` | `severity`, `category`, `description`, `is_active` | `alert_types` is `(id, name)` [FACT] |
| `incident_status` | `status_code`, `display_color`, `is_resolved` | `incident_statuses` is `(id, name)` [FACT] |
| `device_incident` | `severity`, `alert_severity`, `notes`, `resolved_on`, `assigned_user` | Severity is on `device_alerts`; history is `incident_history` |
| `value_alert` | `parameter`, `unit`, `current_value` | `parameter` is on the limit config; `unit` is on `device_param` |
| `package` | `price` | Absent from `packages` [FACT] — **§11.3** |
| `invoice` | `status` | Absent from `invoices` [FACT] — **§11.10** |
| `role` | `permissions JSONB` | Replaced by `role_module_permission` |
| `amenity` | `floor VARCHAR`, `property_type_id` | Replaced by `property_chain_id` |
| `maintenance_request` | `service_type_id`, `days[]`, `start_time VARCHAR` | Replaced by `category_id`/`item_id`, the recurrence table, and real timestamps |
| all tables | `created_at` / `updated_at` | Renamed to `created_on` / `updated_on` |

### 9.4 Enum types removed — all 13

Every current HMS enum is dropped. **Zero of 13 matched IKANOS** [FACT]. Replacements:

| Dropped HMS enum | Replaced by |
|---|---|
| `role_type` | `role_type` with 5 lowercase values incl. `system_user` |
| `device_status` | `device_health_status` (`Active`/`Inactive`) |
| `device_config_status` | 6-value IKANOS enum |
| `device_type` | the `device_type` **lookup table** (4 rows) |
| `job_order_status` | `pending`/`completed` |
| `job_order_type` | `installation`/`replacement`/`troubleshoot` |
| `alert_severity` | `warning`/`critical` (no `Info`) |
| `incident_status` | the `incident_status` **lookup table** (no `Open`) |
| `scheduled_task_type` | `maintenance_request_type` (`scheduled`/`planned`/`disinfection`) |
| `scheduled_task_status` | `scheduler_execution_status` (`passed`/`failed`) |
| `aggregate_interval` | removed — `energy_stat` is hourly only |
| `limit_type` | removed — not an enum; both limits are columns |
| `notification_type` | `entity_type` lookup + `notification_channel` enum (two different axes) |

---

## 10. TABLES THAT REMAIN UNCERTAIN (9)

Included in the 92, but carrying an unresolved question. Each is safe to build; none blocks the others.

| # | Table | Uncertainty | Consequence if the assumption is wrong |
|---:|---|---|---|
| 1 | `occasion` | Is a Holiday really an `occasion` row? There is **no `lock_message` column**, and the HMS Holidays screen is built around one. | A dedicated `holiday` table is needed, or `notification_template` must carry the lock message |
| 2 | `room_service_request` | Is this an HMS entity or a Porta-only entity? It has its own 4-value status vocabulary, separate from `service_status`. | Table is unused; Services Tracking is served entirely by `service_request` |
| 3 | `room_service_request_item` | `faciliti_service_id` has **no FK target table anywhere in the dump**. Repointed to `service_category_item` [INFER]. | Wrong join target; items resolve to nothing |
| 4 | `other_device` | Third-party meter landing table with no FKs and an undocumented `EC` column. Does Power View read this or `device_stat`? | Dead table, or Power View has no source |
| 5 | `amenity.status` FK | IKANOS declares no FK from `amenities.status` to `amenity_statuses`, but the id ranges align exactly. | The FK must be dropped; status becomes a bare integer |
| 6 | `value_alert` FKs | IKANOS declares **no foreign keys at all** on `value_alerts`. Six are added here as [INFER]. | Inserts fail against legacy data that violates them |
| 7 | `package.amenity_type` FK | `packages.amenity_type smallint` has no FK in IKANOS. | Drop the constraint |
| 8 | `battery_life_stat.device_id` FK | No FK in IKANOS. | Drop the constraint |
| 9 | `daily_dual_data_point` PK | PK is `(metric_date, metric_type)` — **`facility_id` is not in it**, so the table cannot hold two facilities. | PK must be widened to include `facility_id`; a deliberate deviation from IKANOS |

**Rule applied:** every one of these is recorded as an inference with its evidence, not silently resolved.

---

## 11. OPEN DECISIONS

| # | Decision | What is at stake | Recommendation |
|---:|---|---|---|
| 1 | **Primary key strategy** (§2.3) | Blocks model generation for all 92 tables. IKANOS is integer AUTO_INCREMENT everywhere; HMS Phase 1 is UUID everywhere. | Adopt the three-tier policy in §2.3 with `legacy_id` on every table. Lookup ids **must** stay integer — the frontend depends on them. |
| 2 | **`facility_uid`** | Present on 91 IKANOS tables, never a foreign key, purpose undocumented. Likely a per-premise routing tag. | Drop it everywhere except `facility.facility_uid`. Reversible. |
| 3 | **`status tinyint` semantics** | ~30 tables carry a soft-delete `status` whose value meanings are undocumented. | Confirm `1 = active`, `0 = deleted` against a live install before seeding. |
| 4 | **`amenity.status` → `amenity_status` FK** | The Occupancy status vocabulary. Inferred, not declared. | Add the FK; the id ranges match exactly (0–3). |
| 5 | **Holidays** [CONFLICT] | `role_modules` has a `holidays` module; `occasion_types` has a `Holiday` row; **no `holiday` table and no `lock_message` column exist**. | Confirm against a live install. Do **not** create a `holiday` table on documentation alone. |
| 6 | **Facility scoping of `stay`, `job_order`, `promo_code`, `daily_dual_data_point`** | None of the four carries a usable `facility_id`; scope is reached through a junction, or not at all. | Decide whether HMS is single-facility. If multi-facility, `daily_dual_data_point`'s PK must be widened. |
| 7 | **`room_service_request*`** | Whether the guest room-service queue is in HMS scope at all (it may be Porta-only). | Keep the tables; leave the module unbuilt until confirmed. |
| 8 | **`other_devices`** | Power View's only candidate source besides `device_stat`. | Confirm which one Power View reads before building the module. |
| 9 | **Facility operating settings** | `timezone`, `default_checkin_time`, `default_checkout_time`, single-line `address`, `logo` — **none exists in `facilities`** [FACT], yet checkout scheduling and the "no timezone / no last-updated" gap (X10) need them. | REVIEW. Do not add without product sign-off. |
| 10 | **Room tariff and payment state** | `packages` has **no price**; `invoices` has **no status**. Bookings gaps B8/B36/B37 (rate, taxes, payment method, advance, balance) have **no source at all**. | **Commercially significant.** Resolve before the Bookings module is built. |
| 11 | **Guest ID document type and number** | `user_documents` stores an attachment and an approval status only. Gaps O24 and B40 need a type and number. | REVIEW — not added. |
| 12 | **`app_user` active flag** | The documented `LOGIN.USER_INACTIVE` error has no backing column; `users` has no `is_active`. `facility_user.status` is the nearest. | Confirm whether `facility_user.status` is the login gate. |
| 13 | **`service_request.priority`** | Documented in the gap analysis, absent from `service_requests`. | REVIEW — not added. |
| 14 | **`mqtt_broker.broker_password`** | Stored in clear text in IKANOS. | Encrypt at rest in HMS regardless of the IKANOS behaviour. |
| 15 | **Feedback module (4 tables)** | Excluded on the evidence that no HMS screen or `role_modules` row exists. Tables are real and populated. | Confirm the module is genuinely out of scope. |
| 16 | **Payments (3 tables)** | Excluded on the same evidence. All three are empty in the dump. | Confirm. If payment lands in scope, §11.10 becomes urgent. |
| 17 | **Porta** | `request_source = 'porta'` proves a second client application writes to this schema. | Out of scope for HMS, but it constrains what HMS may assume about data it did not create. |

---

## 12. SUMMARY

### 12.1 FINAL HMS DATABASE TABLE COUNT

# **92**

| Group | Tables |
|---|---:|
| A — Organisation, facility, property hierarchy | 8 |
| B — Rooms, amenities, packages | 9 |
| C — Guests, stays, billing | 7 |
| D — People, authentication, RBAC | 9 |
| E — Services, tickets, catalogue | 8 |
| F — Maintenance / Services Planning | 4 |
| G — Devices, telemetry, IoT | 14 |
| H — Job orders | 3 |
| I — Access control and digital keys | 4 |
| J — Alerts, incidents, value limits | 8 |
| K — Activity feed and notification dispatch | 9 |
| L — Scheduler | 2 |
| M — Marketing, events, occasions | 5 |
| N — Energy and reporting | 2 |
| **Total** | **92** |

Plus `alembic_version` (infrastructure, not counted).

### 12.2 FINAL HMS TABLE LIST

| # | Table | # | Table | # | Table | # | Table |
|---:|---|---:|---|---:|---|---:|---|
| 1 | `organisation` | 24 | `import_job` | 47 | `device` | 70 | `incident_status` |
| 2 | `facility` | 25 | `app_user` | 48 | `firmware` | 71 | `incident_event` |
| 3 | `facility_user` | 26 | `user_token` | 49 | `device_param` | 72 | `incident_history` |
| 4 | `property_type` | 27 | `user_device` | 50 | `device_stat` | 73 | `value_alert` |
| 5 | `property` | 28 | `role` | 51 | `device_current_stat` | 74 | `value_alert_limit_config` |
| 6 | `property_chain` | 29 | `user_role` | 52 | `device_health_stat` | 75 | `entity_type` |
| 7 | `attachment` | 30 | `role_module` | 53 | `device_command` | 76 | `activity_type` |
| 8 | `country` | 31 | `role_module_permission` | 54 | `command_type` | 77 | `activity` |
| 9 | `amenity_type` | 32 | `department` | 55 | `mqtt_broker` | 78 | `activity_notifier` |
| 10 | `amenity` | 33 | `job_function` | 56 | `mqtt_topic` | 79 | `activity_role_association` |
| 11 | `amenity_status` | 34 | `service_type` | 57 | `other_device` | 80 | `notification` |
| 12 | `amenity_condition` | 35 | `service_status` | 58 | `battery_life_stat` | 81 | `notification_template` |
| 13 | `amenity_condition_status` | 36 | `service_category` | 59 | `sensor_operation_stat` | 82 | `notification_receiver` |
| 14 | `package` | 37 | `service_category_item` | 60 | `job_order` | 83 | `notification_result` |
| 15 | `sub_package` | 38 | `service_request` | 61 | `job_order_device` | 84 | `scheduler_job` |
| 16 | `feature` | 39 | `service_request_item` | 62 | `job_order_amenity` | 85 | `scheduler_job_execution` |
| 17 | `package_feature` | 40 | `room_service_request` | 63 | `key_type` | 86 | `promo_code` |
| 18 | `stay` | 41 | `room_service_request_item` | 64 | `access_key` | 87 | `promo_code_amenity` |
| 19 | `stay_user` | 42 | `maintenance_request` | 65 | `user_device_acl` | 88 | `facility_event` |
| 20 | `stay_package` | 43 | `maintenance_request_recurrence` | 66 | `lock_activity_log` | 89 | `occasion_type` |
| 21 | `room_allocation` | 44 | `maintenance_request_amenity` | 67 | `alert_type` | 90 | `occasion` |
| 22 | `user_document` | 45 | `maintenance_request_assignee` | 68 | `device_alert` | 91 | `energy_stat` |
| 23 | `invoice` | 46 | `device_type` | 69 | `device_incident` | 92 | `daily_dual_data_point` |

### 12.3 CURRENT 39 TABLES → FINAL ACTION

| Action | Count | Tables |
|---|---:|---|
| **KEEP** | 1 | `job_order_device` |
| **MODIFY** | 24 | `facility` · `app_user` · `user_role`→`role` · `app_user_user_role`→`user_role` · `department` · `job_function` · `property_type` · `amenity_type` · `amenity` · `package` · `invoice` · `service_request` · `event`→`facility_event` · `offer`→`promo_code` · `device` · `firmware` · `job_order` · `device_incident` · `value_alerts`→`value_alert` · `limit_config`→`value_alert_limit_config` · `alert_type` · `current_incident_status`→`incident_status` · `fcm_token`→`user_device` · `device_health_log`→`device_health_stat` |
| **REPLACE** | 10 | `occupant`→`stay_user` · `stay` · `food_category`→`service_category` · `food_menu`→`service_category_item` · `holiday`→`occasion` · `notification`→5 tables · `maintenance_schedule`→4 tables · `scheduled_task`→2 tables · `energy_aggregate`→`energy_stat` · `device_uptime`→`sensor_operation_stat` |
| **MERGE** | 2 | `employee`→`app_user` · `booking`→`stay` |
| **REMOVE** | 2 | `energy_data` · `sensor_reading` |
| **Total** | **39** | ✔ |

### 12.4 IKANOS TABLES → FINAL ACTION

| Action | Count |
|---|---:|
| **USE** | 57 |
| **ADAPT** | 35 |
| **MERGE** (absorbed into another final table) | 7 |
| **EXCLUDE** | 8 |
| **Total** | **107** ✔ |

Full lists: USE §3.1 · ADAPT §3.2 · MERGE §3.3 · EXCLUDE §3.4.

### 12.5 Coverage change

| Module | DB coverage before | After |
|---|---|---|
| Bookings / Occupancy | ~30% | full — `stay`, `stay_user`, `room_allocation`, `stay_package`, `user_document`, `import_job`, `invoice`, `amenity_status`, `amenity_condition` |
| Device Management | ~30% | full — 14 tables incl. telemetry, commands, MQTT, battery |
| Services / Tickets | ~35% | full — 8 tables incl. the type/status/category/item taxonomy |
| Config & Setup | ~50% | full — property hierarchy, RBAC (`role_module` + `role_module_permission`), features |
| Dashboard | ~25% | full — `daily_dual_data_point`, `device_health_stat`, `energy_stat`, `property_chain` |
| Reports | **0%** | `daily_dual_data_point`, `energy_stat`, `sensor_operation_stat` + cross-domain |
| Power View | **0%** | `device_stat`, `device_param`, `device_current_stat`, `other_device` (REVIEW) |
| Energy View | **0%** | `energy_stat`, `device_stat`, `device_param` |
| Default Key Settings | **0%** | `access_key`, `key_type`, `user_device_acl`, `lock_activity_log`, `facility.default_key_user` |

**The three modules that had zero database support now have it.**

### 12.6 Blocking order

Nothing is implemented. When implementation is authorised, the dependency order is:

| Step | Scope | Blocked by |
|---:|---|---|
| 0 | Resolve **OPEN DECISION #1** (PK strategy) | — |
| 1 | 16 lookup tables + their seed data (§6) | 0 |
| 2 | `organisation` → `facility` → `property_type` → `property` → `property_chain` | 1 |
| 3 | `app_user` → `role` → `user_role` → `role_module_permission` → `facility_user` (self-referencing `created_by` needs a bootstrap row) | 2 |
| 4 | `amenity_type` → `package` → `amenity` and their junctions | 2, 3 |
| 5 | `stay` → `room_allocation` / `stay_user` / `stay_package` / `user_document` / `invoice` | 4 |
| 6 | `device_type` → `firmware` → `device` → telemetry (`device_param`, `device_stat`, …) | 4 |
| 7 | Alerts: `alert_type` → `device_alert` → `device_incident` → `incident_history` | 6 |
| 8 | Services and maintenance | 4, 5 |
| 9 | Keys, activity/notification, scheduler, marketing, reporting | 5, 6 |

**Circular dependency to plan for:** `facility.created_by → app_user` and `app_user.created_by → app_user`, while `role.facility_id → facility`. IKANOS resolves this with a bootstrap `users` row created before any facility. HMS must do the same or make `created_by` deferrable.

---

## 13. Statement of scope

This document is a **blueprint only**.

- No PostgreSQL object was created, altered or dropped.
- No Alembic migration was generated. Revision `8a8456154f0e` is unchanged.
- No seed data was written.
- No API, model, schema or service module was created or modified.
- The only files produced are this document and a scratch extract of the IKANOS DDL.

**Nothing further should be implemented until OPEN DECISION #1 (§11) is resolved.**
