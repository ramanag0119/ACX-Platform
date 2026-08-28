# IKANOS Database vs HMS Database — Complete Schema Comparison

**Phase:** 1.5
**Date:** 2026-08-16
**Status:** Analysis only. No database, migration, seed or API changes were made.

Evidence labelling used throughout:
**[FACT]** = read directly from the IKANOS SQL dump or the live HMS database ·
**[INFER]** = reasoned conclusion, flagged as such ·
**[CONFLICT]** = sources disagree; both sides reported.

---

## 1. Executive Summary

The Phase 1 HMS schema was built from the IKANOS **documentation**. We now have the
actual IKANOS **database**. They differ substantially.

### Headline numbers **[FACT]**

| | IKANOS (actual) | HMS (current) |
|---|---:|---:|
| Databases | **3** (`caleido`, `caleido_notification`, `caleido_scheduler`) | 1 (`hms_db`) |
| Tables | **107** (101 + 5 + 2; `jobs` defined twice) | 39 |
| Columns | 1,032 (989 in `caleido`) | 313 |
| Foreign keys | 177 (173 in `caleido`) | 71 |
| Enum columns / types | 32 | 13 |
| Composite primary keys | 17 | 2 |
| Auto-increment PKs | 68 | 0 |
| UUID PKs | 0 | 39 |
| Indexes | 166 | 33 |

### The five findings that matter most

1. **Primary key strategy is wrong.** IKANOS uses `int`/`bigint AUTO_INCREMENT`
   throughout — **zero UUID columns exist in the entire dump**. HMS uses UUID on all
   39 tables. This came from `KT-IKANOS.pdf` §08 and `COMPLETE_PROJECT_ANALYSIS_REPORT.md`
   §8, both of which state "UUID primary keys". **[CONFLICT]** — the documentation is
   wrong; the database is the authority.

2. **There is no `booking` table.** IKANOS models the reservation as `stays`
   (21 columns: internal/external ref numbers, expected vs actual check-in/out,
   `no_of_rooms`, `no_of_guests`, `gst`, `document_approval_status`, `status`,
   `request_source`). HMS created **both** a `booking` (4 documented columns) and a
   `stay` (4 columns), splitting one entity into two and losing 14 columns. This is
   the single largest structural error.

3. **There is no `employee` table.** IKANOS has one `users` table (26 columns) with
   `is_staff`, `emp_id`, `department_id`, `function_id`, `supervisor`,
   `date_of_joining`/`date_of_termination`, plus `user_login_details` for credentials
   and `facility_users` for facility scope. HMS split this into `app_user` (6 cols)
   and `employee` (6 cols) and lost 20 columns.

4. **The RBAC model already exists, fully.** `role_modules` contains **18 rows that
   match the HMS sidebar exactly** (`dashboard`, `occupancy`, `bookings`,
   `service_tracking`, `service_planning`, `facility_management`, `user_roles`,
   `service_setup`, `employees`, `job_order`, `offers`, `events`, `caleido_network`,
   `firmware_management`, `reports`, `tickets`, `holidays`, `default_key`), with
   `role_module_permissions(role_id, module_id, read_access, write_access)`. HMS
   modelled this as an unstructured `JSONB` column. This closes NEEDS_REVIEW **D1**.

5. **The telemetry model is entirely different.** HMS invented `energy_data`,
   `sensor_reading`, `energy_aggregate` and `device_uptime`. **None of these exist.**
   IKANOS uses a generic EAV pair — `device_params` (param name, data type, unit) and
   `device_stats` (device_id, device_param_id, device_param_value, timestamp) — plus
   `device_current_stats` (latest blob), `energy_stats` (hourly rollup),
   `battery_life_stats` and `sensor_operation_stats`.

### Accuracy verdict

| Measure | Result |
|---|---:|
| HMS tables with a true IKANOS counterpart | 33 / 39 (85%) |
| HMS tables that are structurally correct as built | **1 / 39** (`job_order_device`) |
| IKANOS `caleido` tables absent from HMS | **66 / 101** (65%) |
| Columns missing from mapped HMS tables | **190** |
| HMS columns with no IKANOS counterpart | 62 |
| Enum vocabularies that match IKANOS | **0 / 13** |

**Overall: the current HMS schema is a reasonable skeleton of the documented model,
but it is not an accurate representation of the actual IKANOS database.** It is
roughly one third of the real schema, with the wrong key strategy and no correct
enum vocabulary.

---

## 2. Source Files Used

| Priority | Source | Path | Used for |
|---:|---|---|---|
| 1 | **IKANOS SQL dump** | `d:\Inspornics\DB_files\Dump20230928 (1).sql` (770 MB) | **Primary authority.** 108 `CREATE TABLE` blocks, all FKs, enums, indexes, and lookup-table `INSERT` data |
| 2 | IKANOS DB structure CSVs | `dbfile.csv` … `dbfile6csv.csv` (attached) | Cross-check. Cover only the `caleido` DB (104 tables) — **missing the 5 notification and 2 scheduler tables** |
| 3 | IKANOS workflow / architecture | `d:\Inspornics\HMS_ikanos\Ikanos_code\*.md` (12 docs) | Business purpose; the Phase 1 basis |
| 4 | HMS Data Gap Analysis | `HMS-Data-Gap-Analysis.md` | Frontend field expectations |
| 5 | HMS Phase 1 report | `backend/docs/PHASE1_REPORT.md` | Current HMS state |
| 6 | HMS NEEDS_REVIEW | `backend/docs/NEEDS_REVIEW.md` | Open questions now answerable |
| 7 | KT handbook | `KT-IKANOS.pdf` (24 pp) | Runtime, roles, flows, verified-vs-documented split |
| — | Live HMS database | `hms_db` @ localhost:5432 | Read-only introspection |

**A second, truncated dump** exists at `ACX codes\Dump20230928.sql` (446 MB, only 22
tables, `activities`→`device_health_stats`). It was **not** used — superseded by the
770 MB copy. **[FACT]**

### Note on the CSV exports
The CSVs describe only `caleido`. They omit `notifications`, `notification_params`,
`notification_receivers`, `notification_results`, `templates`, `job_executions` and
the scheduler `jobs`. Anyone working from the CSVs alone would conclude IKANOS has no
notification persistence — it does, in a separate database. **[FACT]**

---

## 3. IKANOS Database Inventory **[FACT]**

### 3.1 Three databases, not one

| Database | Tables | Columns | FKs | Owning service (KT §04) |
|---|---:|---:|---:|---|
| `caleido` | 101 | 989 | 173 | `faciliti-manager` + 6 others |
| `caleido_notification` | 5 | 29 | 3 | `notification-engine` |
| `caleido_scheduler` | 2 | 14 | 1 | `schedule-handler` |

`jobs` exists in **both** `caleido` (job orders, 15 cols) and `caleido_scheduler`
(cron jobs, 8 cols). They are unrelated entities sharing a name.

### 3.2 Structural conventions

| Convention | Evidence |
|---|---|
| PKs are `int`/`bigint unsigned AUTO_INCREMENT` | 68 tables; **0 UUID columns in the dump** |
| Natural/composite PKs on junctions and rollups | 17 tables |
| `facility_id` (numeric FK) | 32 tables |
| **`facility_uid varchar(3)`** — denormalised tenant tag | **91 tables** |
| Audit columns are `created_on` / `updated_on` | 99 / 99 tables |
| `created_by` / `updated_by` (user FK) | 44 tables |
| Engine / collation | InnoDB, `latin1_swedish_ci` (some `utf8mb3`) |
| Soft delete | `status tinyint` on ~30 tables |

`facility_uid` appears on 91 tables but is **not** a foreign key anywhere — it is a
denormalised copy of `facilities.facility_uid`. **[FACT]** Its purpose is
undocumented. **[INFER]** Likely a sharding/routing tag for the per-premise install
model described in KT §05.

### 3.3 Functional grouping

| Group | Tables |
|---|---|
| Facility & property | `organisations`, `facilities`, `facility_users`, `property_types`, `properties`, `property_chains`, `attachments`, `countries` |
| Rooms & packages | `amenities`, `amenity_types`, `amenity_statuses`, `amenity_conditions`, `amenity_condition_status`, `amenity_metadata`, `packages`, `sub_packages`, `package_features`, `features` |
| Guests & stays | `stays`, `stay_users`, `stay_packages`, `room_allocations`, `invoices`, `user_documents`, `imports` |
| People & RBAC | `users`, `user_login_details`, `user_metadata`, `user_tokens`, `user_devices`, `roles`, `user_roles`, `role_modules`, `role_module_permissions`, `departments`, `functions` |
| Services & tickets | `service_requests`, `service_request_items`, `service_types`, `service_statuses`, `service_categories`, `service_category_items`, `service_item_metadata`, `room_service_requests`, `room_service_request_items`, `order_items` |
| Maintenance | `service_maintenance_requests`, `maintenance_request_recurrence`, `service_maintenance_request_amenities`, `service_maintenance_request_assignees` |
| Devices & IoT | `devices`, `device_types`, `device_metadata`, `device_params`, `device_stats`, `device_current_stats`, `device_health_stats`, `device_commands`, `command_types`, `firmware`, `jobs`, `job_devices`, `job_amenities`, `mqtt_brokers`, `mqtt_topics`, `other_devices`, `battery_life_stats`, `sensor_operation_stats` |
| Access control (locks) | `keys`, `key_types`, `user_device_acl`, `lock_activity_log` |
| Alerts | `device_alerts`, `alert_types`, `device_incidents`, `incident_statuses`, `incident_events`, `incident_history`, `value_alerts`, `value_alert_limit_config` |
| Activity / notification | `activities`, `activity_types`, `activity_data`, `activity_notifiers`, `activity_role_association`, `entity_types` + (`caleido_notification`: `notifications`, `templates`, `notification_params`, `notification_receivers`, `notification_results`) |
| Marketing | `promo_codes`, `promo_code_amenities`, `facility_events`, `occasions`, `occasion_types` |
| Energy | `energy_stats` |
| Reporting | `daily_dual_data_points` |
| Feedback | `feedback_questions`, `feedback_options`, `feedback_responses`, `user_feedback` |
| Payments | `payment_gateway_keys`, `payment_order_status`, `payment_status` |
| Infrastructure | `migrations` + (`caleido_scheduler`: `jobs`, `job_executions`) |

---

## 4. HMS Database Inventory **[FACT]**

`hms_db` / `public`, Alembic revision `8a8456154f0e`, 39 tables, 313 columns,
71 FKs, 13 enum types, 33 indexes, 13 unique constraints, 2 composite PKs.
All PKs are `uuid`. All tables carry `created_at`/`updated_at`; none carry
`created_by`. 32 tables carry `facility_id`.

---

## 5. Table-by-Table Mapping (Task 1)

### 5.1 HMS tables → IKANOS

| # | HMS Table | IKANOS Table(s) | Match Status | Notes |
|---|---|---|---|---|
| 1 | `facility` | `facilities` | PARTIAL | 12 cols missing; IKANOS has `org_id`, `facility_uid`, contact + address block |
| 2 | `app_user` | `users` + `user_login_details` + `facility_users` | PARTIAL | IKANOS splits identity / credentials / facility scope across 3 tables |
| 3 | `user_role` | `roles` | PARTIAL | `permissions` JSONB replaces `role_modules` + `role_module_permissions` |
| 4 | `app_user_user_role` | `user_roles` | PARTIAL | IKANOS PK is **(facility_id, user_id, role_id)** — facility-scoped |
| 5 | `employee` | `users` | **MERGE** | No `employee` table exists; `users.is_staff = 1` |
| 6 | `department` | `departments` | PARTIAL | missing `status`, `department_key`, `created_by` |
| 7 | `job_function` | `functions` | PARTIAL | IKANOS scopes by `facility_id`, **not** `department_id` — HMS FK direction is wrong |
| 8 | `property_type` | `property_types` | PARTIAL | missing `levels`, image, `status` |
| 9 | `amenity_type` | `amenity_types` | PARTIAL | missing `amenity_category` enum, `status`, `image_id` |
| 10 | `amenity` | `amenities` | PARTIAL | missing `parent_amenity_id`, `property_chain_id`, `is_dnd`, `power_save_mode` |
| 11 | `package` | `packages` | PARTIAL | missing `description`, `is_sub_package`, `image_id`, `status`; **`price` does not exist in IKANOS** |
| 12 | `booking` | — | **HMS-ONLY** | No booking table. `stays` is the reservation entity |
| 13 | `occupant` | `stay_users` | CONCEPTUAL | IKANOS links `user_id` + `room_id` + `stay_id`; guest identity lives in `users` |
| 14 | `stay` | `stays` | PARTIAL | **14 columns missing** — the core operational entity |
| 15 | `invoice` | `invoices` | PARTIAL | 11 cols missing incl. `invoice_number`, tax breakdown, billing snapshot |
| 16 | `service_request` | `service_requests` | PARTIAL | 13 cols missing incl. `ref_number`, `stay_id`, amounts, `completed_on` |
| 17 | `food_category` | `service_categories` | CONCEPTUAL | **No `foodCategory` table**; categories are generic per `service_type` |
| 18 | `food_menu` | `service_category_items` | CONCEPTUAL | **No `foodMenu` table**; items are generic |
| 19 | `event` | `facility_events` | PARTIAL | 7 cols missing incl. attendees, `cancellation_reason` |
| 20 | `offer` | `promo_codes` | PARTIAL | 8 cols missing — **all discount logic** |
| 21 | `holiday` | `occasions` (`occasion_type` = 'Holiday') | **HMS-ONLY / CONFLICT** | No `holiday` table; but `role_modules` has a `holidays` module |
| 22 | `device` | `devices` | PARTIAL | 14 cols missing; HMS `ip_address`/`mac_address`/`last_seen` **do not exist** |
| 23 | `firmware` | `firmware` | PARTIAL | missing `crc`, `firmware_url`, `release_notes`, `status`; **`is_latest` does not exist** |
| 24 | `job_order` | `jobs` (caleido) | PARTIAL | missing `order_reference`, `work_commence`, `estimated_completion_date` |
| 25 | `job_order_device` | `job_devices` | **EXACT (shape)** | Only structurally correct table in HMS |
| 26 | `device_incident` | `device_incidents` | PARTIAL | missing `amenity_id`, `alert_type`, `latest_alert_id`; HMS `severity`/`notes`/`resolved_on` **do not exist** |
| 27 | `value_alerts` | `value_alerts` | PARTIAL | 6 cols missing; HMS `parameter`/`unit`/`current_value` **do not exist** |
| 28 | `limit_config` | `value_alert_limit_config` | PARTIAL | IKANOS keys by `device_name`; has percentage **and** absolute limits |
| 29 | `alert_type` | `alert_types` | PARTIAL | IKANOS is `(id, name)` only — HMS `severity`/`category`/`description`/`is_active` are invented |
| 30 | `current_incident_status` | `incident_statuses` | PARTIAL | IKANOS is `(id, name)` only — HMS `status_code`/`display_color`/`is_resolved` invented |
| 31 | `notification` | `notifications` + `notification_receivers` + `activity_notifiers` | CONCEPTUAL | IKANOS separates dispatch queue from in-app feed |
| 32 | `fcm_token` | `user_devices` | CONCEPTUAL | IKANOS also stores `mobile_model`, `mobile_os`, `user_token_id`, `stay_id` |
| 33 | `maintenance_schedule` | `service_maintenance_requests` + `maintenance_request_recurrence` | PARTIAL | **17 cols missing**; IKANOS splits request from recurrence |
| 34 | `scheduled_task` | — | **HMS-ONLY** | No such table; `caleido_scheduler.jobs` + `job_executions` is the executor |
| 35 | `energy_data` | — | **HMS-ONLY** | EAV via `device_params` + `device_stats` |
| 36 | `sensor_reading` | — | **HMS-ONLY** | Same EAV path |
| 37 | `energy_aggregate` | `energy_stats` | CONCEPTUAL | IKANOS is hourly only, PK `(device_name, facility_id, amenity_id, hour)` |
| 38 | `device_health_log` | `device_health_stats` | PARTIAL | IKANOS logs `device_temperature`; no `response_time`/`error_detail` |
| 39 | `device_uptime` | — | **HMS-ONLY** | `sensor_operation_stats` is the nearest concept |

**Tally:** PARTIAL 25 · CONCEPTUAL 6 · HMS-ONLY 6 · MERGE 1 · EXACT 1.

---

## 6. Column-Level Differences (Task 2)

Full diff in the analysis output. **190 IKANOS columns are missing** from mapped HMS
tables; **62 HMS columns have no IKANOS counterpart**. Audit columns excluded.

### 6.1 The worst offenders

| HMS Table | IKANOS cols | HMS cols | Missing | Key omissions |
|---|---:|---:|---:|---|
| `app_user` ← `users` | 26 | 6 | **20** | `first_name`, `last_name`, `phone_number`, `emp_id`, `is_staff`, `department_id`, `function_id`, `supervisor`, `gender`, `dob`, `nationality`, `country`, `address`, `date_of_joining`, `date_of_termination`, `marital_status`, `is_child`, `age`, `alternate_phone_number`, `user_uid` |
| `maintenance_schedule` ← `service_maintenance_requests` | 25 | 13 | **17** | `maintenance_request_type` (scheduled/planned/disinfection), start/end date+time, `is_recurring`, `is_room`, `under_maintenance`, `maintenance_request_status`, `category_id`, `item_id`, `parent_id`, `status_reason` |
| `stay` ← `stays` | 21 | 7 | **14** | `internal_stay_ref_number`, `external_stay_ref_number`, `booking_user_id`, `no_of_rooms`, `no_of_guests`, expected/actual check-in+out, `gst`, `comments`, `document_approval_status`, `request_source`, `checkout_initiated_by` |
| `device` ← `devices` | 27 | 14 | **14** | `part_number`, `model`, `mfg_date`, `appliance_name`, `manufacturer_name`, `authentication_code`, `health_status`, `device_temperature`, `installed_on`, `expected_firmware_version`, `operational_mode`, `device_uid`, `is_power_off` |
| `service_request` ← `service_requests` | 25 | 11 | **13** | `ref_number`, `category_id`, `department_id`, `stay_id`, `promo_code_id`, `description`, `expected_date`, `completed_on`, `status_reason`, `request_source`, `net_amount`, `total_tax`, `total_amount` |
| `facility` ← `facilities` | 18 | 6 | **12** | `org_id`, `facility_uid`, `city`, `state`, `pin_code`, `email`, `additional_email`, `google_map_link`, `guest_rooms`, `currency_id`, `facility_image_id`, `default_key_user` |
| `invoice` ← `invoices` | 19 | 7 | **11** | `invoice_number`, `invoice_date`, `invoice_due_date`, billing + facility snapshot, `net_amount`, `total_tax` |
| `offer` ← `promo_codes` | 16 | 7 | **8** | `discount_percentage`, `max_discount_value`, `min_order_value`, `expiry_time`, `offered_by`, `promo_code_description`, `promo_code_icon`, `status` |
| `firmware` | 17 | 8 | **8** | `crc`, `firmware_url`, `release_notes`, `release_date`, `status`, `firmware_size`, `decommission_reason`, `uploaded_by` |
| `job_order` ← `jobs` | 15 | 8 | **7** | `order_reference`, `type_of_work`, `work_commence`, `estimated_completion_date`, `authentication_code`, `completed_on`, `description` |

### 6.2 HMS columns that do not exist in IKANOS

These were added from documentation or frontend inference. **Do not keep without evidence.**

| HMS Table | Column | Verdict |
|---|---|---|
| `device` | `ip_address`, `mac_address`, `last_seen` | Documented in CPA §8 but **absent from the DB**. IKANOS uses `device_uid`, `authentication_code`, `health_status`. **REVIEW** |
| `firmware` | `is_latest` | Absent. IKANOS tracks currency via `devices.current_firmware_version` / `expected_firmware_version`. **REMOVE** |
| `alert_type` | `severity`, `category`, `description`, `is_active` | Absent — `alert_types` is `(id, name)`. Severity lives on `device_alerts.alert_severity`. **REMOVE** |
| `current_incident_status` | `status_code`, `display_color`, `is_resolved` | Absent — `incident_statuses` is `(id, name)`. **REMOVE** |
| `device_incident` | `severity`, `alert_severity`, `notes`, `resolved_on`, `assigned_user` | Absent. Severity is on `device_alerts`; history is `incident_history`. **REMOVE / RELOCATE** |
| `value_alerts` | `parameter`, `unit`, `current_value` | Absent. IKANOS references `limit_config_id`; `parameter` lives on the config row. **MODIFY** |
| `package` | `price` | **Absent from `packages`.** Pricing is on `service_category_items.price_per_unit`. **REVIEW — commercially significant** |
| `booking` | entire table | No counterpart. **MERGE into `stay`** |
| `holiday` | entire table | No counterpart. **REVIEW — see §10.3** |
| `scheduled_task`, `energy_data`, `sensor_reading`, `device_uptime` | entire tables | No counterpart. **REPLACE with the IKANOS structures** |
| all tables | `created_at` / `updated_at` | IKANOS uses `created_on` / `updated_on`. **RENAME** |

---

## 7. Primary Key Comparison (Task 3)

### 7.1 Strategy **[CONFLICT]**

| | IKANOS **[FACT]** | HMS | Documentation claim |
|---|---|---|---|
| Type | `int` / `bigint unsigned` | `uuid` | "UUID primary keys" — CPA §8, KT §08 |
| Generation | `AUTO_INCREMENT` (68 tables) | `uuid4()` in Python | — |
| Composite | 17 tables | 2 tables | not mentioned |

**Zero UUID columns exist anywhere in the 770 MB dump.** The documentation is
contradicted by the database. Per the stated source-of-truth priority, the dump wins.

> This is a **decision point, not an automatic defect.** UUIDs are defensible for a
> new build (no sequence coordination, safe to expose). But they are not what IKANOS
> does, and any data migration from a live IKANOS install must map integer keys.
> **Recommendation: keep UUID surrogate keys, and add the IKANOS integer key as a
> nullable `legacy_id` on every migrated table.** Flagged for your decision.

### 7.2 Composite PKs missing from HMS **[FACT]**

IKANOS uses composite natural keys on 17 tables. HMS has 2. Missing:

| IKANOS table | Composite PK |
|---|---|
| `user_roles` | `(facility_id, user_id, role_id)` |
| `role_module_permissions` | `(role_id, module_id)` |
| `amenity_condition_status` | `(amenity_id, amenity_condition_id)` |
| `amenity_metadata` | `(amenity_id, metadata_key)` |
| `device_metadata` | `(device_id, metadata_key)` |
| `user_metadata` | `(user_id, metadata_key)` |
| `service_item_metadata` | `(item_id, metadata_key)` |
| `energy_stats` | `(device_name, facility_id, amenity_id, hour)` |
| `sensor_operation_stats` | `(device_id, stats_date)` |
| `daily_dual_data_points` | `(metric_date, metric_type)` |
| `job_amenities` | `(job_id, amenity_id)` |
| `job_devices` | `(job_id, device_id)` |
| `sub_packages` | `(parent_package_id, sub_package_id)` |
| `promo_code_amenities` | `(promo_code_id, amenity_id)` |
| `facility_users` | `(facility_id, user_id)` |
| `activity_notifiers` | `(activity_id, user_id)` |
| `activity_role_association` | `(activity_type_id, role_id)` |

HMS's `app_user_user_role` is `(app_user_id, user_role_id)` — **missing `facility_id`**,
so the same user cannot hold different roles at different facilities. **[FACT]**

### 7.3 Table

| Table | IKANOS PK | HMS PK | Status | Action |
|---|---|---|---|---|
| `facilities` / `facility` | `facility_id` int AI | `id` uuid | Type differs | REVIEW (§7.1) |
| `users` / `app_user` | `user_id` bigint AI | `id` uuid | Type differs | REVIEW |
| `stays` / `stay` | `stay_id` bigint AI | `id` uuid | Type differs | REVIEW |
| `user_roles` / `app_user_user_role` | `(facility_id,user_id,role_id)` | `(app_user_id,user_role_id)` | **Wrong** | MODIFY — add facility |
| `job_devices` / `job_order_device` | `(job_id,device_id)` | `(job_order_id,device_id)` | Correct | KEEP |
| `energy_stats` / `energy_aggregate` | 4-col composite | `id` uuid | **Wrong** | REPLACE |
| all others | int/bigint AI | uuid | Type differs | REVIEW |

---

## 8. Foreign Key Comparison (Task 4)

IKANOS `caleido`: **173 FKs**. HMS: **71**. All HMS FKs are single-column.

### 8.1 HMS FKs that are wrong or unsupported **[FACT]**

| HMS FK | IKANOS evidence | Verdict |
|---|---|---|
| `job_function.department_id → department.id` | `functions.facility_id → facilities.facility_id`. **No `functions.department_id` column exists.** | **WRONG — direction invented.** Users link to both `department_id` and `function_id` independently |
| `service_request.assigned_to → employee.id` | `service_requests.assigned_to` is a plain `bigint` with **no FK constraint** | Unsupported; target should be `users` |
| `device_incident.assigned_to → employee.id` | `device_incidents.assigned_to` — **no FK**; but `updated_by → users.user_id` exists | Unsupported; **`users`**, not `employee` |
| `job_order.assigned_to → employee.id` | `jobs.assigned_to → users.user_id` **[FACT]** | Right idea, **wrong target** — `users` |
| `service_request.guest_id → app_user.id` | `service_requests.user_id` — no FK; `stay_id → stays` exists | Partially right; add `stay_id` |
| `amenity.property_type_id → property_type.id` | `amenities.property_chain_id → property_chains` **[FACT]**. No direct link to `property_types` | **WRONG — replace with `property_chain_id`** |
| `package.amenity_type_id → amenity_type.id` | `packages.amenity_type` is `smallint` with **no FK** | Unsupported (reasonable, but not IKANOS) |
| `limit_config.device_id → device.id` | `value_alert_limit_config.device_name varchar(50)` — **no FK, keyed by name** | Differs; HMS is arguably better but not IKANOS |
| `booking.package_id → package.id` | No `booking` table | N/A — merge into `stay` |

**Resolves NEEDS_REVIEW E1–E6.** E2 (`employee.job_function_id`) and E4
(`device_incident.assigned_to`) were both wrong; E1 (`amenity.property_type_id`) was
wrong in a different way than suspected.

### 8.2 Major IKANOS FK chains absent from HMS

| Chain | Purpose |
|---|---|
| `amenities.property_chain_id → property_chains.{level_one,level_two,level_three}_id → properties.property_id → property_types` | **Building → wing → floor → room hierarchy.** Closes NEEDS_REVIEW B1 |
| `room_allocations.{stay_id, room_id, package_id}` | Room assignment per stay |
| `stay_users.{user_id, room_id, stay_id}` | Occupant ↔ room ↔ stay |
| `keys.{user_device_acl_id, device_id, stay_id, key_type, maintenance_request_id}` | Digital key issuance |
| `user_device_acl.{user_id, device_id, amenity_id, stay_id, device_type_id, amenity_type_id}` | Time-boxed device access (6 FKs) |
| `device_incidents.{latest_alert_id → device_alerts, alert_type → alert_types, amenity_id, current_incident_status}` | Incident ↔ alert linkage |
| `incident_history.{incident_id, incident_event_id}` | Incident audit trail |
| `device_stats.{device_id, device_param_id → device_params}` | Telemetry EAV |
| `role_module_permissions.{role_id, module_id → role_modules}` | RBAC |
| `service_requests.{category_id, service_type, status, stay_id, amenity_id, promo_code_id, facility_id}` | Ticket context (7 FKs) |

### 8.3 ON DELETE behaviour **[FACT]**

IKANOS overwhelmingly uses `CASCADE` (both delete and update) on facility- and
device-owned children, and `NO ACTION` on lookup/reference links. HMS invented its own
policy (`CASCADE` from facility, `SET NULL` on optional, `RESTRICT` on
`booking.package_id`). Broadly aligned in spirit; **`RESTRICT` on package has no
IKANOS equivalent** (the documented error message was the only basis).

---

## 9. Relationship Comparison (Task 5)

### 9.1 Property hierarchy — **missing entirely from HMS**

```
organisations
  └── facilities
        ├── property_types            (levels: 1-3)
        │     └── properties
        │           └── property_chains  (level_one_id, level_two_id, level_three_id)
        │                 └── amenities   [amenities.property_chain_id]
        └── amenity_types
```
HMS collapses this to `amenity.floor VARCHAR` + `amenity.property_type_id`. The
3-level chain is how IKANOS models **building → wing/floor → room**. **[FACT]**

### 9.2 Guest lifecycle — HMS splits one entity into two

```
IKANOS:  users ──booking_user_id──> stays ──> room_allocations ──> amenities
                                      ├──> stay_users (occupants + room + key flag)
                                      ├──> stay_packages
                                      ├──> user_documents (ID proof, approval)
                                      ├──> keys ──> user_device_acl ──> devices
                                      └──> invoices

HMS:     booking ──> stay ──> amenity
              └──> occupant
                    stay ──> invoice
```
Missing: `room_allocations`, `stay_packages`, `user_documents`, `keys`,
`user_device_acl`. **[FACT]**

### 9.3 Device → alert → incident

```
device_types ──> devices ──> device_alerts ──alert_type──> alert_types
                    │              └──latest_alert_id──> device_incidents
                    │                                       ├──current_incident_status──> incident_statuses
                    │                                       └──> incident_history ──> incident_events
                    ├──> device_health_stats
                    ├──> device_stats ──device_param_id──> device_params
                    ├──> device_current_stats
                    ├──> device_commands ──> command_types
                    ├──> device_metadata
                    └──> mqtt_topics ──> mqtt_brokers
```
HMS has `device → device_incident` only. Missing the entire alert→incident linkage,
history, telemetry EAV, command queue and MQTT layer. **[FACT]**

### 9.4 RBAC

```
facilities ──> roles ──> role_module_permissions ──> role_modules (18 rows)
                 └──> user_roles (facility_id, user_id, role_id) ──> users
users ──> user_login_details / user_tokens / user_devices / user_metadata
```
HMS: `user_role.permissions JSONB` + 2-column junction. **[FACT]**

### 9.5 Service & maintenance

```
service_types ──> service_categories ──> service_category_items ──> service_item_metadata
                                                   │
service_requests ──> service_request_items ────────┘
   ├──status──> service_statuses
   ├──> stays, amenities, promo_codes, facilities

service_maintenance_requests
   ├──> maintenance_request_recurrence
   ├──> service_maintenance_request_amenities
   ├──> service_maintenance_request_assignees
   └──maintenance_request_status──> service_statuses
```
HMS has flat `service_request` + `maintenance_schedule`. **[FACT]**

---

## 10. Enum / Status Comparison (Task 6)

**Zero of the 13 HMS enums match IKANOS.** **[FACT]**

### 10.1 Direct enum conflicts

| HMS enum | HMS values | IKANOS source | IKANOS values | Verdict |
|---|---|---|---|---|
| `role_type` | ADMIN, MANAGER, STAFF, GUEST | `roles.role_type` | admin, system_user, manager, guest, staff | **Missing `system_user`**; case differs |
| `device_status` | Online, Offline, Error | `devices.health_status` | **Active, Inactive** | Completely different |
| `device_config_status` | active, inactive, decommissioned | `devices.device_config_status` | configured, bad_configuration, **commissioned**, decommissioned, under_maintenance, missing | Only 1 of 6 correct |
| `device_type` | HUB, LOCK, SENSOR, SWITCH, CONTROLLER, MIKOS | `device_types` rows | **Intellihub(HUB), AirQ(AIR), Mikos(MIK), Kleio(KLE)** | 4 real types; LOCK/SENSOR/SWITCH/CONTROLLER **do not exist** — Kleio *is* the lock |
| `job_order_status` | Created, InProgress, Completed | `jobs.job_order_status` | **pending, completed** | Wrong |
| `job_order_type` | Commission, Decommission, Maintenance | `jobs.type_of_work` | **installation, replacement, troubleshoot** | Wrong |
| `alert_severity` | Critical, Warning, Info | `device_alerts.alert_severity` | **warning, critical** | `Info` does not exist |
| `incident_status` | Open, Unread, Read, Assigned, Resolved | `incident_statuses` rows | **Unread, Read, Assigned, Resolved** | `Open` invented |
| `scheduled_task_type` | maintenance, housekeeping, sanitation, checkout, system | `service_maintenance_requests.maintenance_request_type` | **scheduled, planned, disinfection** | Wrong |
| `scheduled_task_status` | Pending, Executed, Cancelled, Failed | — | no equivalent | Invented |
| `aggregate_interval` | 5min, hourly, daily | — | `energy_stats` is hourly only | Invented |
| `limit_type` | high, low | — | `value_alert_limit_config` has both low+high columns | Not an enum in IKANOS |
| `notification_type` | alert, service, booking, system, event | `templates.type` | **email, sms, push notification, silent notification** | Different axis. Nearest: `entity_types` = Booking, Occupancy, Service Requests, Maintenance Requests, Default Key |

### 10.2 Status vocabularies — **NEEDS_REVIEW D2–D5 now resolved** **[FACT]**

Real reference data from the dump:

| Lookup table | Values |
|---|---|
| **`amenity_statuses`** | `0` Available · `1` Occupied · `2` Unavailable · `3` Allotted |
| **`amenity_conditions`** | Dirty · Low battery · Under maintenance · Sanitation |
| **`service_statuses`** | Pending · Assigned · Partially completed · Completed · Canceled |
| **`service_types`** | Room Service · Travel Desk · Business Center · Food Order · Facility Maintenance Service · Health & Fitness · Sanitation Maintenance Service |
| **`incident_statuses`** | Unread · Read · Assigned · Resolved |
| **`incident_events`** | Unread · Read · Assigned · Resolved · **Reopened** |
| **`key_types`** | Primary · Shared · Staff · Default |
| **`entity_types`** | Booking · Occupancy · Service Requests · Maintenance Requests · Default Key |
| **`occasion_types`** | Festival · Birthday · Marriage anniversary · **Holiday** |
| **`device_types`** | Intellihub(HUB) · AirQ(AIR) · Mikos(MIK) · Kleio(KLE) |
| **`role_modules`** | dashboard · occupancy · bookings · service_tracking · service_planning · facility_management · user_roles · service_setup · employees · job_order · offers · events · caleido_network · firmware_management · reports · tickets · holidays · default_key |
| **`alert_types`** | BatteryLow · DeviceDisconnection · LoginAttemptsFailure · ImproperShaftMovement · DeviceOverheating · PreventiveMaintenance · MikosOvercurrentTrip · RoomAirQualityPoor · RoomInternalHot · AirConditioningFail · TamperingAttempt · DoorAjar · HubOffline · MikosOffline · LockOffline · AirqOffline |

These match the HMS frontend exactly — the 7 Services Tracking tabs are
`service_types`; the Occupancy condition badges are `amenity_conditions`; the Network
Alert rows ("Hub Offline", "Room Air Quality Poor") are `alert_types`.

### 10.3 Other IKANOS enums with no HMS representation

`stays.status` (pending, active, checkout accepted, checkout pending, checkout
rejected, checked out, cancelled) · `stays.document_approval_status` (pending,
approved) · `stays.request_source` (**ikanos, porta**) · `service_requests.request_source` ·
`room_service_requests.service_request_status` (unassigned, assigned, cancelled,
completed) · `device_commands.processing_status` (Queued, Processing, Processed,
Error) · `mqtt_topics.topic_type` (8 values) · `lock_activity_log.event`
(locked, unlocked) / `.unlock_mode` (app, keypad) · `imports.entity_type` (booking,
job order) / `.import_status` · `firmware.status` (active, decommissioned) ·
`amenity_types.amenity_category` (room, restaurant, others) ·
`device_params.data_type` · `daily_dual_data_points.metric_type` ·
`maintenance_request_recurrence.recurrence_type` (weekly) ·
`user_documents.document_approval_status`.

`request_source = 'porta'` **[FACT]** corroborates KT §01: guests use a separate
**Porta** app; IKANOS is a staff console.

---

## 11. Supporting / Junction Table Comparison (Task 7)

| Purpose | IKANOS table | In HMS? |
|---|---|---|
| User ↔ role | `user_roles` (facility, user, role) | Partial — missing facility |
| Role ↔ module permission | `role_module_permissions` | **NO** |
| Module registry | `role_modules` | **NO** |
| User ↔ facility | `facility_users` | NO (uses `app_user.facility_id`) |
| Job ↔ device | `job_devices` | **YES** |
| Job ↔ amenity | `job_amenities` | **NO** |
| Stay ↔ package | `stay_packages` | **NO** |
| Stay ↔ room | `room_allocations` | **NO** |
| Stay ↔ occupant ↔ room | `stay_users` | Partial (`occupant`) |
| Package ↔ sub-package | `sub_packages` | **NO** |
| Package ↔ feature | `package_features` | **NO** |
| Promo ↔ amenity | `promo_code_amenities` | **NO** |
| Amenity ↔ condition | `amenity_condition_status` | **NO** |
| Maintenance ↔ amenity | `service_maintenance_request_amenities` | **NO** |
| Maintenance ↔ assignee | `service_maintenance_request_assignees` | **NO** |
| Service request ↔ item | `service_request_items` | **NO** |
| Activity ↔ notifier | `activity_notifiers` | **NO** |
| Activity type ↔ role | `activity_role_association` | **NO** |
| User ↔ device ACL | `user_device_acl` | **NO** |
| Key-value metadata (×4) | `amenity_metadata`, `device_metadata`, `user_metadata`, `service_item_metadata` | **NO** |

**19 of 21 supporting tables are missing.** **[FACT]**

---

## 12. HMS Module → DB Dependency Mapping (Task 8)

| HMS Module | Required IKANOS tables | Present in HMS | Missing DB support |
|---|---|---|---|
| **Dashboard** | `daily_dual_data_points`, `device_health_stats`, `device_incidents`, `value_alerts`, `energy_stats`, `stays`, `amenities` | partial | **`daily_dual_data_points`** — its `metric_type` enum (smart room, service request, checkout, booking, guest room) **is exactly the Caleido At Work KPI set** |
| **Occupancy** | `amenities`, `amenity_statuses`, `amenity_conditions`, `amenity_condition_status`, `stays`, `stay_users`, `room_allocations`, `invoices` | partial | conditions, statuses, allocations, key generation |
| **Bookings** | `stays`, `stay_users`, `stay_packages`, `room_allocations`, `user_documents`, `imports`, `invoices` | partial | 5 of 7 tables |
| **Services Tracking** | `service_requests`, `service_request_items`, `service_types`, `service_statuses`, `service_categories`, `service_category_items`, `room_service_requests`, `order_items` | 3 of 8 | items, types, statuses, room-service |
| **Services Planning** | `service_maintenance_requests`, `maintenance_request_recurrence`, `+_amenities`, `+_assignees` | 1 (partial) | recurrence + both junctions |
| **Config & Setup** | `facilities`, `properties`, `property_chains`, `property_types`, `packages`, `sub_packages`, `features`, `package_features`, `users`, `departments`, `functions`, `roles`, `role_modules`, `role_module_permissions`, `jobs`, `value_alert_limit_config` | ~half | property hierarchy, RBAC tables, features |
| **Offers** | `promo_codes`, `promo_code_amenities` | 1 (partial) | applicability junction + all discount fields |
| **Holidays** | `occasions`, `occasion_types` | HMS-only table | **[CONFLICT]** see §14 |
| **Events** | `facility_events`, `attachments` | 1 (partial) | attendees, images, cancellation |
| **Device Management** | `devices`, `device_types`, `device_metadata`, `device_params`, `device_stats`, `device_current_stats`, `device_health_stats`, `device_commands`, `command_types`, `firmware`, `jobs`, `job_devices`, `job_amenities`, `mqtt_*`, `battery_life_stats` | 5 of 16 | telemetry, commands, MQTT, battery |
| **Reports** | `daily_dual_data_points`, `energy_stats`, `sensor_operation_stats` + cross-domain | none of the 3 | **all reporting tables** |
| **Tickets** | `service_requests`, `service_request_items`, `service_statuses`, `service_types` | 1 (partial) | items + both lookups |
| **Power View** | `device_stats`, `device_params`, `device_current_stats`, `other_devices` | none | **all** |
| **Energy View** | `energy_stats`, `device_stats`, `device_params` | none | **all** |
| **Room View** | `amenities`, `amenity_statuses`, `amenity_conditions`, `devices`, `device_current_stats` | partial | statuses, conditions, live stats |
| **Default Key Settings** | `keys`, `key_types`, `user_device_acl`, `lock_activity_log`, `facilities.default_key_user` | **none** | **entire module — 4 tables + 1 column** |

**Three modules have zero database support: Power View, Energy View, Default Key Settings.**

---

## 13. Current 39 HMS Table Validation (Task 9)

| HMS Table | IKANOS Equivalent | Correct? | Required? | Action |
|---|---|---|---|---|
| `facility` | `facilities` | No | Yes | **MODIFY** +12 cols |
| `app_user` | `users`+`user_login_details`+`facility_users` | No | Yes | **MODIFY** +20 cols, split creds |
| `employee` | `users` (`is_staff`) | No | No | **MERGE** into `app_user` |
| `user_role` | `roles` | No | Yes | **MODIFY** — drop JSONB |
| `app_user_user_role` | `user_roles` | No | Yes | **MODIFY** — add `facility_id` to PK |
| `department` | `departments` | Partial | Yes | MODIFY |
| `job_function` | `functions` | **No** | Yes | **MODIFY** — FK to facility not department |
| `property_type` | `property_types` | Partial | Yes | MODIFY +`levels` |
| `amenity_type` | `amenity_types` | Partial | Yes | MODIFY +`amenity_category` |
| `package` | `packages` | Partial | Yes | MODIFY; review `price` |
| `amenity` | `amenities` | Partial | Yes | **MODIFY** — replace `floor`/`property_type_id` with `property_chain_id` |
| `booking` | — | **No** | No | **MERGE** into `stay` |
| `occupant` | `stay_users` | Partial | Yes | **MODIFY** → `user_id`+`room_id` |
| `stay` | `stays` | **No** | Yes | **REPLACE** — +14 cols, absorb `booking` |
| `invoice` | `invoices` | Partial | Yes | MODIFY +11 cols |
| `service_request` | `service_requests` | Partial | Yes | MODIFY +13 cols |
| `food_category` | `service_categories` | **No** | No | **REPLACE** with `service_categories` |
| `food_menu` | `service_category_items` | **No** | No | **REPLACE** with `service_category_items` |
| `event` | `facility_events` | Partial | Yes | MODIFY +7 cols |
| `offer` | `promo_codes` | Partial | Yes | **MODIFY** +8 discount cols |
| `holiday` | `occasions`? | Unclear | Yes | **REVIEW** — see §14 |
| `device` | `devices` | Partial | Yes | MODIFY +14 cols; review ip/mac |
| `firmware` | `firmware` | Partial | Yes | MODIFY; **remove `is_latest`** |
| `job_order` | `jobs` | Partial | Yes | MODIFY +7 cols |
| `job_order_device` | `job_devices` | **Yes** | Yes | **KEEP** |
| `device_incident` | `device_incidents` | Partial | Yes | **MODIFY** — remove invented cols, add `alert_type`/`latest_alert_id`/`amenity_id` |
| `value_alerts` | `value_alerts` | Partial | Yes | MODIFY |
| `limit_config` | `value_alert_limit_config` | Partial | Yes | MODIFY |
| `alert_type` | `alert_types` | **No** | Yes | **MODIFY** — reduce to `(id, name)`; seed 16 rows |
| `current_incident_status` | `incident_statuses` | **No** | Yes | **MODIFY** — reduce to `(id, name)`; seed 4 rows |
| `notification` | `notifications`/`activity_notifiers` | **No** | Yes | **REVIEW** — pick dispatch vs feed |
| `fcm_token` | `user_devices` | Partial | Yes | **RENAME** → `user_device` |
| `maintenance_schedule` | `service_maintenance_requests` | **No** | Yes | **REPLACE** — +17 cols, split recurrence |
| `scheduled_task` | — | **No** | Review | **REVIEW** — scheduler is a separate DB |
| `energy_data` | — | **No** | No | **REPLACE** with `device_params`+`device_stats` |
| `sensor_reading` | — | **No** | No | **REPLACE** with same EAV |
| `energy_aggregate` | `energy_stats` | **No** | Yes | **REPLACE** |
| `device_health_log` | `device_health_stats` | Partial | Yes | MODIFY |
| `device_uptime` | — | **No** | Review | **REVIEW** vs `sensor_operation_stats` |

**KEEP 1 · MODIFY 20 · REPLACE 7 · MERGE 3 · RENAME 1 · REVIEW 7**

---

## 14. IKANOS Tables Missing from HMS (Task 10)

66 of 101 `caleido` tables, plus all 7 in the other two databases.

| Classification | Count | Tables |
|---|---:|---|
| **REQUIRED — Device/IoT** | 13 | `device_types`, `device_metadata`, `device_params`, `device_stats`, `device_current_stats`, `device_commands`, `command_types`, `mqtt_brokers`, `mqtt_topics`, `other_devices`, `battery_life_stats`, `sensor_operation_stats`, `device_alerts` |
| **REQUIRED — Booking/Ops** | 13 | `properties`, `property_chains`, `room_allocations`, `stay_packages`, `sub_packages`, `package_features`, `features`, `amenity_conditions`, `amenity_condition_status`, `amenity_statuses`, `amenity_metadata`, `user_documents`, `imports` |
| **REQUIRED — Services** | 9 | `service_types`, `service_statuses`, `service_request_items`, `service_item_metadata`, `room_service_requests`, `room_service_request_items`, `order_items`, `service_maintenance_request_amenities`, `service_maintenance_request_assignees` |
| **REQUIRED — Notifications** | 8 | `activities`, `activity_types`, `activity_data`, `activity_role_association`, `entity_types` + `notification_params`, `notification_results`, `templates` |
| **REQUIRED — Key management** | 4 | `keys`, `key_types`, `user_device_acl`, `lock_activity_log` |
| **REQUIRED — RBAC** | 4 | `role_modules`, `role_module_permissions`, `user_tokens`, `user_metadata` |
| **REQUIRED — Alerts** | 2 | `incident_history`, `incident_events` |
| **REQUIRED — Reporting** | 1 | `daily_dual_data_points` |
| **SUPPORTING** | 7 | `attachments`, `countries`, `organisations`, `promo_code_amenities`, `job_amenities`, `occasions`, `occasion_types` |
| **REVIEW — Feedback** | 4 | `feedback_questions`, `feedback_options`, `feedback_responses`, `user_feedback` |
| **LEGACY / NOT REQUIRED** | 5 | `migrations`, `payment_gateway_keys`, `payment_order_status`, `payment_status`, `job_executions` |

### Highest-value missing tables

1. **`role_modules` + `role_module_permissions`** — complete RBAC, 18 modules matching the sidebar.
2. **`properties` + `property_chains`** — the building/floor hierarchy the Dashboard needs.
3. **`daily_dual_data_points`** — pre-aggregated dashboard KPIs.
4. **`keys` + `key_types` + `user_device_acl` + `lock_activity_log`** — the whole Default Key module.
5. **`device_params` + `device_stats`** — all telemetry for Power/Energy View.
6. **`amenity_statuses` + `amenity_conditions`** — the Occupancy vocabularies.
7. **`service_types` + `service_statuses`** — the Services/Tickets vocabularies.

### The Holidays conflict **[CONFLICT]**

- CPA §8 and FM §12 document a `holiday` table (`id, startDate, lockMessage`).
- `role_modules` row 17 is `holidays` — the module exists. **[FACT]**
- **No `holiday` table exists in the dump.** **[FACT]**
- `occasion_types` includes a row literally named **`Holiday`**, and `occasions` has
  `occasion_start_date`, `occasion_end_date`, `is_repeatable`, `notification_template`,
  `notify_to_hub`. **[FACT]**

**[INFER]** Holidays are stored as `occasions` rows with `occasion_type` = Holiday.
But `occasions` has no `lock_message` column, and the HMS frontend's Holidays screen
is built entirely around "Lock message". Reported, not resolved — needs confirmation
against a live install.

---

## 15. HMS Tables Not Present in IKANOS

| HMS table | Verdict | Action |
|---|---|---|
| `booking` | `stays` is the reservation | MERGE into `stay` |
| `holiday` | see §14 | REVIEW |
| `scheduled_task` | separate `caleido_scheduler` DB | REVIEW |
| `energy_data` | EAV instead | REPLACE |
| `sensor_reading` | EAV instead | REPLACE |
| `device_uptime` | `sensor_operation_stats` nearest | REVIEW |
| `amenity_type` | **does exist** (`amenity_types`) — Phase 1 flagged it as unlisted | KEEP |
| `app_user_user_role` | **does exist** (`user_roles`) | KEEP + fix PK |
| `job_order_device` | **does exist** (`job_devices`) | KEEP |

The three "supporting tables beyond the 36" flagged in Phase 1 all turn out to be
**real IKANOS tables**. That judgement was correct.

---

## 16. Required Schema Changes (Task 12)

| # | Issue | Current HMS | IKANOS Evidence | Recommended Change | Priority |
|---|---|---|---|---|---|
| 1 | `booking`/`stay` split | 2 tables, 11 cols | `stays` — 21 cols, no `booking` table | Merge into `stay`; add 14 cols | **HIGH** |
| 2 | `employee`/`app_user` split | 2 tables, 12 cols | `users` — 26 cols, `is_staff` | Merge into one; add 20 cols | **HIGH** |
| 3 | RBAC as JSONB | `user_role.permissions` | `role_modules` (18 rows) + `role_module_permissions` | Add both tables; drop JSONB | **HIGH** |
| 4 | Enum vocabularies | 13 invented enums | 12 lookup tables + 32 enum cols | Replace all with IKANOS values | **HIGH** |
| 5 | Property hierarchy | `amenity.floor` varchar | `properties`+`property_chains` | Add both; repoint `amenity` | **HIGH** |
| 6 | Telemetry model | 3 invented tables | `device_params`+`device_stats`+`device_current_stats` | Replace | **HIGH** |
| 7 | Key management absent | — | `keys`,`key_types`,`user_device_acl`,`lock_activity_log` | Add 4 tables | **HIGH** |
| 8 | Room allocation absent | — | `room_allocations` | Add | **HIGH** |
| 9 | Amenity status/condition | `VARCHAR(50)` | `amenity_statuses`(4)+`amenity_conditions`(4)+junction | Add 3 tables | **HIGH** |
| 10 | Service taxonomy | flat `service_request` | `service_types`,`service_statuses`,`service_request_items` | Add 3 tables | **HIGH** |
| 11 | Wrong FK targets | `assigned_to → employee` | `jobs.assigned_to → users` | Repoint to `app_user` | **HIGH** |
| 12 | `job_function` FK | → `department` | `functions.facility_id` | Repoint to facility | **HIGH** |
| 13 | `amenity.property_type_id` | → `property_type` | `amenities.property_chain_id` | Replace | **HIGH** |
| 14 | Composite PK on `user_roles` | 2-col | 3-col with `facility_id` | Add facility | **HIGH** |
| 15 | Invented columns | `alert_type`, `current_incident_status`, `device_incident`, `firmware.is_latest` | lookup tables are `(id,name)` | Remove | **HIGH** |
| 16 | Alert→incident linkage | none | `latest_alert_id`, `alert_type`, `amenity_id` | Add `device_alerts` + FKs | **HIGH** |
| 17 | Dashboard KPI source | none | `daily_dual_data_points` | Add | **HIGH** |
| 18 | Audit column naming | `created_at`/`updated_at` | `created_on`/`updated_on` (99 tables) | Rename | MEDIUM |
| 19 | `created_by` missing | 0 tables | 44 tables | Add where IKANOS has it | MEDIUM |
| 20 | `attachments` absent | image cols are varchar | `attachments` + FKs from 6 tables | Add | MEDIUM |
| 21 | `countries` absent | — | `countries` (239 rows), 2 FKs from `users` | Add | MEDIUM |
| 22 | `organisations` absent | — | `facilities.org_id → organisations` | Add | MEDIUM |
| 23 | Offer discount fields | 3 cols | 8 more incl. `discount_percentage` | Add | MEDIUM |
| 24 | Invoice tax breakdown | `amount` only | `net_amount`,`total_tax`,`total_amount`,`invoice_number` | Add | MEDIUM |
| 25 | Maintenance recurrence | `days[]` array | `maintenance_request_recurrence` | Split out | MEDIUM |
| 26 | Sub-packages / features | — | `sub_packages`,`package_features`,`features` | Add | MEDIUM |
| 27 | `imports` absent | — | `imports` (bulk upload tracking) | Add | MEDIUM |
| 28 | `user_documents` absent | — | `user_documents` + approval status | Add | MEDIUM |
| 29 | Incident history | — | `incident_history`+`incident_events` | Add | MEDIUM |
| 30 | MQTT / commands | — | `mqtt_brokers`,`mqtt_topics`,`device_commands`,`command_types` | Add | MEDIUM |
| 31 | Metadata tables | — | 4 `*_metadata` tables | Add | LOW |
| 32 | Feedback | — | 4 feedback tables | REVIEW | LOW |
| 33 | Payments | — | 3 payment tables | Defer | LOW |
| 34 | `facility_uid` | — | 91 tables | REVIEW — likely not needed single-tenant | LOW |
| 35 | PK type | uuid | int/bigint AI | **Decision required** (§7.1) | **HIGH** |

---

## 17. Deferred / Review Items

1. **PK strategy** — UUID vs integer. Recommend keeping UUID + nullable `legacy_id`.
2. **Holidays** — `occasions` has no `lock_message`. **[CONFLICT]**
3. **`package.price`** — not in `packages`. Where is room pricing held?
4. **`device.ip_address`/`mac_address`** — documented, absent from DB.
5. **`facility_uid`** — on 91 tables, purpose undocumented.
6. **Scheduler DB** — keep `caleido_scheduler` separate or fold in?
7. **Notification split** — dispatch queue (`notifications`) vs in-app feed (`activities`)?
8. **Feedback module** — 4 tables exist; no HMS screen.
9. **Payments** — 3 tables exist, all empty; no HMS screen.
10. **`other_devices`** — non-Caleido meters; JSON payloads, no FKs.
11. **`system_user` role** — exists in DB, hidden in UI (KT §10).
12. **Porta** — `request_source='porta'` proves a second client. Out of scope, affects data.

---

## 18. Final HMS Schema Recommendation

**Do not patch the current 39 tables incrementally.** Rebuild Phase 1 from the dump.

**Recommended target: ~70 tables** — the 66 missing minus legacy/payments/feedback
(~12), plus the 33 corrected existing tables.

Suggested sequence (no work performed):

| Step | Scope |
|---|---|
| 1 | Decide PK strategy (§7.1) — blocks everything |
| 2 | Regenerate models from the dump for: facility/org/property chain, users/RBAC, stays/allocations |
| 3 | Add the 12 lookup tables and seed them with real values (§10.2) |
| 4 | Rebuild device/telemetry on the EAV model |
| 5 | Rebuild alerts with `device_alerts` + `incident_history` |
| 6 | Add key management (4 tables) |
| 7 | Add services taxonomy + maintenance junctions |
| 8 | Add `daily_dual_data_points`, `energy_stats`, `attachments`, `countries`, `imports` |
| 9 | Re-verify; then seed development data |

Phase 1 deliverables that remain valid: project structure, Alembic setup, naming
convention, verification script, test suite, `pg_enum` value-fidelity helper.

---

## 19. Statistics / Summary

### Task 11 summary

| Metric | Value |
|---|---:|
| Total IKANOS tables | **107** (101 + 5 + 2) |
| Total HMS tables | **39** |
| Exact matches | **1** |
| Conceptual matches | **6** |
| Partial matches | **25** |
| Merge candidates | **3** |
| Missing in HMS (`caleido`) | **66** |
| Missing in HMS (other DBs) | 7 |
| HMS-only | **6** |
| Legacy / not required | 5 |
| Needs review | 12 |

| Column / constraint metric | Value |
|---|---:|
| IKANOS columns | 1,032 |
| HMS columns | 313 |
| Missing columns (mapped tables) | **190** |
| HMS columns without IKANOS counterpart | 62 |
| IKANOS FKs | 177 |
| HMS FKs | 71 |
| Missing FKs | **~106** |
| Incorrect HMS FKs | **6** |
| Missing supporting/junction tables | **19 of 21** |
| Enum/status mismatches | **13 of 13** |
| Missing composite PKs | **15** |
| Missing lookup/reference tables | 12 |

### Coverage by module

| Module | DB coverage |
|---|---|
| Bookings / Occupancy | ~30% |
| Device Management | ~30% |
| Services / Tickets | ~35% |
| Config & Setup | ~50% |
| Dashboard | ~25% |
| Reports | 0% |
| Power View | 0% |
| Energy View | 0% |
| Default Key Settings | 0% |

---

**No database, migration, seed or API changes were made. The existing 39 HMS tables
and Alembic revision `8a8456154f0e` are untouched.**
