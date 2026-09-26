# HMS Database Analysis Report

| | |
|---|---|
| **System** | ACX Platform — Hospitality Management System (HMS) |
| **Repository** | `ACX-Platform`, branch `develop` @ `e64ee07` |
| **Database** | PostgreSQL 18.6, database `hms_db`, schema `public`, Alembic head `0e2687233b59` |
| **Date of analysis** | 2026-09-26 |
| **Type** | Analysis and documentation only. No code, schema, data, migration or configuration was changed. |

---

## 0. How to read this report

### 0.1 Method

| Evidence source | How it was used |
|---|---|
| **Live database** | Read-only catalog dump (`information_schema`, `pg_catalog`), row counts and a few reference-data queries, each run inside `SET TRANSACTION READ ONLY` and rolled back. No row was written. |
| **ORM models** | `backend/app/models/*.py`. All 92 HMS tables have a model and every model has a table (no drift). |
| **Migration** | `backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py` (single revision, creates all 92 tables). |
| **Backend code** | `backend/app/services/*.py` (queries and business rules) and `backend/app/api/v1/endpoints/*.py` (HTTP routes). |
| **Frontend code** | `frontend/src/lib/api/*` (API client, react-query hooks, write functions) and `frontend/src/features/**` (pages). |
| **Project docs** | `backend/docs/*.md`, `docs/HMS-Data-Gap-Analysis.md`. |

**Not done:** no authenticated API calls were made. The seeded accounts cannot log in by design (`backend/app/core/security.py:29`, sentinel `!seed-no-login`), and the one real account's credentials were not used. Every API behaviour below is therefore established from code, and every data statement from the live database.

**Pending, unapplied change in the working tree:** an untracked migration `backend/migrations/versions/7c4e2b9a1d53_rename_service_status_in_progress.py` (revises `0e2687233b59`) appeared during the analysis. It renames `service_status` id 3 from "Partially completed" to "In Progress" (label only; the id is kept). When this report was written it had **not** been applied, and the report describes that state, so id 3 appears here as "Partially completed". **Update (later on 2026-09-26):** the migration has since been applied (live Alembic head `7c4e2b9a1d53`, `service_status` id 3 = "In Progress"). Matching uncommitted edits in 14 tracked files, all label-only renames (`STATUS_PARTIAL` → `STATUS_IN_PROGRESS`, seeds, tests, `serviceStatus.ts`, `ServiceTracking.tsx`, `ServiceRequestActionsDialog.tsx`), came from work done in parallel with this analysis. Read "Partially completed" in this report as "In Progress".

### 0.2 Evidence conventions

- `file:line` references were checked against the source when the report was written. Where only a file and function are given, the function name is the locator.
- **Confirmed** = shown directly by code and/or live data. **Needs verification** = plausible from code but not demonstrable without runtime access or business input.
- "Not Found" means a search of the repository found no implementation.

### 0.3 Application layering (verified)

There is **no repository/DAO layer**. `backend/app` contains only `api`, `core`, `db`, `models`, `schemas` and `services`. Services build SQLAlchemy `select()` statements and run them on the request `Session` directly. The layering every flow in this report follows is:

```
PostgreSQL table
  → SQLAlchemy model            backend/app/models/<domain>.py
  → Service function (query)    backend/app/services/<domain>.py        (reads)
                                backend/app/services/<domain>_write.py  (writes, inside writes.transaction())
  → FastAPI route               backend/app/api/v1/endpoints/<domain>.py, mounted under /api/v1 (router.py)
  → Frontend API binding        frontend/src/lib/api/endpoints.ts (reads), writes.ts (writes)
  → React Query hook            frontend/src/lib/api/hooks.ts (reads), mutations.ts (writes + cache invalidation)
  → Page / component            frontend/src/features/<module>/...
```

The only raw SQL in the application is four health-check statements in `backend/app/api/v1/endpoints/health.py:38-44`. Everything else is SQLAlchemy Core/ORM, so **there are no `.sql` files or stored procedures, and the database has 0 views, 0 triggers and 0 CHECK constraints**.

---

## Executive summary

- **93 tables** exist in `public`: 92 HMS tables plus `alembic_version`. There are 922 columns, 93 primary keys, 240 foreign keys, 76 unique constraints and 34 PostgreSQL ENUM types. The live counts match the documented Phase 1.7 baseline (`backend/docs/PHASE1_7_DATABASE_IMPLEMENTATION.md`).
- **Every table has seed data** (no table is empty). One facility is loaded: "Ikanos Grand Chennai", 24 guest rooms plus 3 non-room spaces.
- **72 tables are queried by backend services.** 18 have a model but no service, API or UI code: `organisation`, `sub_package`, `import_job`, `room_service_request`, `room_service_request_item`, `command_type`, `device_command`, `mqtt_broker`, `mqtt_topic`, `user_token`, `user_device`, `user_device_acl`, `access_key`, `key_type`, `lock_activity_log`, `activity_role_association`, `scheduler_job` and `scheduler_job_execution`. 2 more (`attachment`, `country`) are used only as FK targets, and the last is `alembic_version`. A further 17 are exposed by the API but used by no screen (§10.1).
- **Room state has two unreconciled sources of truth.** One is `amenity.status`; the other is the stay/allocation timestamps. Live data shows the gap today: 3 amenities are flagged *Occupied* while 1 guest is in house. Room 201 is *Occupied* and room 108 is *Allotted* with no allocation at all.
- **Holiday Management exists and is backed by the `occasion` table.** However, the list is not filtered to the "Holiday" type, "deleted" holidays stay visible, and the screen's *Lock message* and *Description* fields do not map to what the database stores.
- **Several UI write paths cannot succeed** because the frontend matches hardcoded option values against database names. This affects Package create, Room create, Limit Config create and Offer edit.
- **Reads are not scoped to the user's facility.** Every list endpoint takes an optional `facility_id` that no page sends, and several tables that need facility scoping (`stay`, `job_order`, `promo_code`) have no `facility_id` column.

---

## 1. Database table inventory

All 93 tables, grouped by HMS module. **Rows** are live counts on 2026-09-26. Audit FKs (`created_by`, `updated_by`, `modified_by`, `uploaded_by` → `app_user`) are counted rather than listed, to keep the FK column readable. §2 lists every FK in full.

**Category totals:** Master 20 · Reference 17 · Transaction / Operational 30 · Configuration 13 · Audit / History 12 · Other 1 = **93**

| # | Table | Category | Module | Purpose | Cols | Rows | Primary key | Foreign keys → target | Referenced by |
|---|---|---|---|---|---:|---:|---|---|---|
| 1 | `facility` | Master | Facility & Property | The hotel / premise. Tenant root for almost every other table (29 tables reference it). | 19 | 1 | `id` | `default_key_user`→app_user, `facility_image_id`→attachment, `org_id`→organisation (+1 audit FK→app_user) | 29 tables (see §2) |
| 2 | `organisation` | Master | Facility & Property | Tenant / owning organisation of a facility. | 7 | 1 | `id` |  (+1 audit FK→app_user) | facility |
| 3 | `property` | Master | Facility & Property | One node of the building structure (a building, wing or floor). | 9 | 4 | `id` | `facility_id`→facility, `property_type_id`→property_type (+1 audit FK→app_user) | property_chain |
| 4 | `property_chain` | Master | Facility & Property | Materialised Building → Floor path (level_one/two/three → property). Rooms point to a chain. | 10 | 3 | `id` | `facility_id`→facility, `level_one_id`→property, `level_three_id`→property, `level_two_id`→property (+1 audit FK→app_user) | amenity |
| 5 | `property_type` | Reference | Facility & Property | Kind of structure and the depth (`levels`) of the property chain. | 9 | 1 | `id` | `facility_id`→facility, `property_type_image_id`→attachment | property |
| 6 | `amenity` | Master | Room / Occupancy | A bookable space: guest room, suite, restaurant, gym, conference room. Carries the room's current status (FK amenity_status). 18 tables reference it. | 15 | 27 | `id` | `amenity_type_id`→amenity_type, `facility_id`→facility, `package_id`→package, `parent_amenity_id`→amenity, `property_chain_id`→property_chain, `status`→amenity_status (+1 audit FK→app_user) | 18 tables (see §2) |
| 7 | `amenity_condition` | Reference | Room / Occupancy | Room condition lookup: Dirty, Low battery, Under maintenance, Sanitation. | 4 | 4 | `id` | — | amenity_condition_status |
| 8 | `amenity_condition_status` | Transaction / Operational | Room / Occupancy | Active conditions currently flagged on a room (room × condition). | 5 | 13 | `amenity_id, amenity_condition_id` | `amenity_condition_id`→amenity_condition, `amenity_id`→amenity | — |
| 9 | `amenity_status` | Reference | Room / Occupancy | Room status lookup: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted. | 4 | 4 | `id` | — | amenity |
| 10 | `amenity_type` | Master | Room / Occupancy | Category of space (Guest Room, Suite, Restaurant…) with `amenity_category` enum room/restaurant/others. | 10 | 5 | `id` | `facility_id`→facility, `image_id`→attachment (+1 audit FK→app_user) | amenity, package, user_device_acl |
| 11 | `feature` | Master | Room / Occupancy | Room feature (shown as "Room Amenities" tab). | 10 | 6 | `id` | `device_type`→device_type, `facility_id`→facility (+1 audit FK→app_user) | package_feature |
| 12 | `package` | Master | Room / Occupancy | Room package / rate plan (no price column). Every amenity must have one. | 12 | 8 | `id` | `amenity_type`→amenity_type, `facility_id`→facility, `image_id`→attachment (+1 audit FK→app_user) | amenity, package_feature, room_allocation, stay_package, sub_package |
| 13 | `package_feature` | Configuration | Room / Occupancy | Package ↔ feature link. | 8 | 17 | `id` | `feature_id`→feature, `package_id`→package (+1 audit FK→app_user) | — |
| 14 | `sub_package` | Configuration | Room / Occupancy | Parent package → child package link. | 5 | 7 | `parent_package_id, sub_package_id` | `parent_package_id`→package, `sub_package_id`→package (+1 audit FK→app_user) | — |
| 15 | `import_job` | Transaction / Operational | Booking / Stay | Bulk import job tracking (booking / job order CSV). | 14 | 3 | `id` |  (+1 audit FK→app_user) | — |
| 16 | `invoice` | Transaction / Operational | Booking / Stay | Stay invoice with billing & facility snapshot and amounts. | 19 | 2 | `id` | `billing_user_id`→app_user, `facility_id`→facility, `facility_image_id`→attachment, `stay_id`→stay (+1 audit FK→app_user) | — |
| 17 | `room_allocation` | Transaction / Operational | Booking / Stay | Which room(s) a stay holds (stay ↔ amenity) with package. | 9 | 6 | `id` | `package_id`→package, `room_id`→amenity, `stay_id`→stay (+1 audit FK→app_user) | — |
| 18 | `stay` | Transaction / Operational | Booking / Stay | The reservation/booking and its check-in/check-out lifecycle (`stay_status` enum). No facility_id column. | 21 | 7 | `id` | `booking_user_id`→app_user, `checkout_initiated_by`→app_user (+2 audit FK→app_user) | 12 tables (see §2) |
| 19 | `stay_package` | Transaction / Operational | Booking / Stay | Packages purchased on a stay. | 7 | 6 | `id` | `package_id`→package, `stay_id`→stay | — |
| 20 | `stay_user` | Transaction / Operational | Booking / Stay | Occupants (guests) of a stay, optionally per room. | 10 | 8 | `id` | `app_user_id`→app_user, `room_id`→amenity, `stay_id`→stay (+1 audit FK→app_user) | — |
| 21 | `user_document` | Transaction / Operational | Booking / Stay | Guest ID-proof document pointer with approval status. | 9 | 3 | `id` | `app_user_id`→app_user, `attachment_id`→attachment, `stay_id`→stay | — |
| 22 | `room_service_request` | Transaction / Operational | Service Requests | Guest-app in-room service call with its own 4-value enum (unassigned/assigned/cancelled/completed). | 11 | 3 | `id` | `assigned_to`→app_user, `guest_room_id`→amenity, `stay_id`→stay (+1 audit FK→app_user) | room_service_request_item |
| 23 | `room_service_request_item` | Transaction / Operational | Service Requests | Items of a room service call. | 7 | 4 | `id` | `room_service_request_id`→room_service_request, `service_category_item_id`→service_category_item | — |
| 24 | `service_category` | Master | Service Requests | Category under a service type (e.g. food categories, maintenance categories). | 12 | 13 | `id` | `category_icon`→attachment, `facility_id`→facility, `service_type`→service_type (+1 audit FK→app_user) | maintenance_request, service_category_item, service_request, service_request_item |
| 25 | `service_category_item` | Master | Service Requests | Requestable item with price; JSONB metadata. | 14 | 22 | `id` | `amenity_id`→amenity, `category_id`→service_category, `facility_id`→facility, `item_icon`→attachment (+1 audit FK→app_user) | maintenance_request, room_service_request_item, service_request_item |
| 26 | `service_request` | Transaction / Operational | Service Requests | Service ticket (tracking & tickets), status FK → service_status. | 25 | 7 | `id` | `amenity_id`→amenity, `app_user_id`→app_user, `assigned_to`→app_user, `category_id`→service_category, `department_id`→department, `facility_id`→facility, `promo_code_id`→promo_code, `service_type`→service_type, `status`→service_status, `stay_id`→stay (+2 audit FK→app_user) | service_request_item |
| 27 | `service_request_item` | Transaction / Operational | Service Requests | Line items of a service request. | 11 | 8 | `id` | `assigned_to`→app_user, `category_id`→service_category, `item_id`→service_category_item, `service_request_id`→service_request, `status`→service_status | — |
| 28 | `service_status` | Reference | Service Requests | Request lifecycle lookup: 1 Pending, 2 Assigned, 3 Partially completed, 4 Completed, 5 Canceled. | 4 | 5 | `id` | — | maintenance_request, service_request, service_request_item |
| 29 | `service_type` | Reference | Service Requests | 7 service types (Room Service, Travel Desk, … Sanitation Maintenance). | 4 | 7 | `id` | — | service_category, service_request |
| 30 | `maintenance_request` | Transaction / Operational | Maintenance (Service Planning) | Scheduled / planned / disinfection maintenance work; status FK → service_status; soft delete via status 0. | 25 | 3 | `id` | `category_id`→service_category, `department_id`→department, `facility_id`→facility, `item_id`→service_category_item, `maintenance_request_status`→service_status, `parent_id`→maintenance_request (+2 audit FK→app_user) | access_key, maintenance_request, maintenance_request_amenity, maintenance_request_assignee, maintenance_request_recurrence |
| 31 | `maintenance_request_amenity` | Transaction / Operational | Maintenance (Service Planning) | Rooms covered by a maintenance request. | 8 | 6 | `id` | `amenity_id`→amenity, `maintenance_request_id`→maintenance_request (+1 audit FK→app_user) | — |
| 32 | `maintenance_request_assignee` | Transaction / Operational | Maintenance (Service Planning) | Staff assigned to a maintenance request. | 8 | 4 | `id` | `app_user_id`→app_user, `maintenance_request_id`→maintenance_request (+1 audit FK→app_user) | — |
| 33 | `maintenance_request_recurrence` | Configuration | Maintenance (Service Planning) | 1:1 weekly recurrence rule (days_of_week bitmask). | 6 | 1 | `maintenance_request_id` | `maintenance_request_id`→maintenance_request | — |
| 34 | `job_order` | Transaction / Operational | Job Orders | Field work order (installation/replacement/troubleshoot). No facility_id column. | 15 | 3 | `id` | `assigned_to`→app_user (+1 audit FK→app_user) | job_order_amenity, job_order_device |
| 35 | `job_order_amenity` | Transaction / Operational | Job Orders | Rooms on a job order. | 4 | 4 | `job_order_id, amenity_id` | `amenity_id`→amenity, `job_order_id`→job_order | — |
| 36 | `job_order_device` | Transaction / Operational | Job Orders | Devices on a job order. | 4 | 2 | `job_order_id, device_id` | `device_id`→device, `job_order_id`→job_order | — |
| 37 | `battery_life_stat` | Audit / History | Devices & IoT | Battery charge cycles per device. | 9 | 12 | `id` | `device_id`→device | — |
| 38 | `command_type` | Reference | Devices & IoT | Device command registry (Keys, FirmwareUpdates, Checkout…). | 5 | 10 | `id` | `device_type_id`→device_type | device_command |
| 39 | `device` | Master | Devices & IoT | Physical smart device installed in a room; `parent_device_id` points to its hub. | 28 | 14 | `id` | `amenity_id`→amenity, `current_firmware_version`→firmware, `device_type`→device_type, `expected_firmware_version`→firmware, `facility_id`→facility, `parent_device_id`→device (+1 audit FK→app_user) | 16 tables (see §2) |
| 40 | `device_command` | Transaction / Operational | Devices & IoT | Outbound command queue to devices. | 9 | 7 | `id` | `command_type`→command_type, `device_id`→device (+1 audit FK→app_user) | — |
| 41 | `device_current_stat` | Transaction / Operational | Devices & IoT | Latest JSONB snapshot per device. | 7 | 14 | `id` | `device_id`→device | — |
| 42 | `device_health_stat` | Audit / History | Devices & IoT | Device heartbeat / health & temperature log. | 7 | 168 | `id` | `device_id`→device | — |
| 43 | `device_param` | Reference | Devices & IoT | EAV parameter definitions per device type (name, data type, unit). | 7 | 35 | `id` | `device_type`→device_type | device_stat |
| 44 | `device_stat` | Audit / History | Devices & IoT | Time-series telemetry values (EAV: device × param × timestamp → value as text). | 9 | 504 | `id` | `device_id`→device, `device_param_id`→device_param | — |
| 45 | `device_type` | Reference | Devices & IoT | 4 device families: Intellihub (HUB), AirQ, Mikos, Kleio. | 5 | 4 | `id` | — | 7 tables (see §2) |
| 46 | `firmware` | Master | Devices & IoT | Firmware build per device type; device current/expected version. | 17 | 6 | `id` | `device_type_id`→device_type (+3 audit FK→app_user) | device |
| 47 | `mqtt_broker` | Configuration | Devices & IoT | MQTT broker connection details per facility. | 11 | 1 | `id` | `facility_id`→facility | mqtt_topic |
| 48 | `mqtt_topic` | Configuration | Devices & IoT | MQTT topic per device/broker. | 8 | 12 | `id` | `device_id`→device, `mqtt_broker_id`→mqtt_broker | — |
| 49 | `sensor_operation_stat` | Audit / History | Devices & IoT | Daily sensor uptime percentage. | 6 | 42 | `device_id, stats_date` | `amenity_id`→amenity, `device_id`→device | — |
| 50 | `energy_stat` | Audit / History | Energy | Hourly energy consumption per device name / room. | 7 | 72 | `device_name, facility_id, amenity_id, hour` | `amenity_id`→amenity, `facility_id`→facility | — |
| 51 | `other_device` | Audit / History | Energy | Third-party meter readings (voltage/current/power/energy); no FK, keyed by device_name text. | 17 | 12 | `id` | — | — |
| 52 | `daily_dual_data_point` | Audit / History | Dashboard / Reporting | Daily KPI numerator/denominator per metric type (smart room, service request, checkout, booking, guest room). | 7 | 35 | `metric_date, metric_type` | `facility_id`→facility | — |
| 53 | `alert_type` | Reference | Alerts & Incidents | 16 alert types (BatteryLow, DoorAjar, HubOffline…). | 4 | 16 | `id` | — | device_alert, device_incident |
| 54 | `device_alert` | Transaction / Operational | Alerts & Incidents | Raw device alert stream. | 10 | 9 | `id` | `alert_type`→alert_type, `amenity_id`→amenity, `device_id`→device (+1 audit FK→app_user) | device_incident |
| 55 | `device_incident` | Transaction / Operational | Alerts & Incidents | Assignable incident case raised from alerts. | 14 | 5 | `id` | `alert_type`→alert_type, `amenity_id`→amenity, `assigned_to`→app_user, `current_incident_status`→incident_status, `device_id`→device, `facility_id`→facility, `latest_alert_id`→device_alert (+1 audit FK→app_user) | incident_history |
| 56 | `incident_event` | Reference | Alerts & Incidents | Incident event lookup: Unread, Read, Assigned, Resolved, Reopened. | 4 | 5 | `id` | — | incident_history |
| 57 | `incident_history` | Audit / History | Alerts & Incidents | Audit trail of incident status events. | 8 | 14 | `id` | `incident_event_id`→incident_event, `incident_id`→device_incident (+1 audit FK→app_user) | — |
| 58 | `incident_status` | Reference | Alerts & Incidents | Incident status lookup: Unread, Read, Assigned, Resolved. | 4 | 4 | `id` | — | device_incident |
| 59 | `value_alert` | Transaction / Operational | Alerts & Incidents | Threshold breach raised against a limit config. | 16 | 3 | `id` | `amenity_id`→amenity, `device_id`→device, `device_type_id`→device_type, `facility_id`→facility, `limit_config_id`→value_alert_limit_config | — |
| 60 | `value_alert_limit_config` | Configuration | Alerts & Incidents | Per device-name / parameter threshold configuration. | 16 | 4 | `id` | `device_id`→device, `facility_id`→facility | value_alert |
| 61 | `app_user` | Master | User / Staff / Guest | Single identity table for guests and staff (`is_staff`), including login fields (user_name, password_hash). Referenced by 51 tables. | 29 | 15 | `id` | `country`→country, `department_id`→department, `job_function_id`→job_function, `nationality`→country, `supervisor`→app_user (+1 audit FK→app_user) | 50 tables (see §2) |
| 62 | `country` | Reference | User / Staff / Guest | Country / phone-code lookup (239 rows). | 9 | 239 | `id` | — | app_user |
| 63 | `department` | Master | User / Staff / Guest | Staff department per facility. | 9 | 5 | `id` | `facility_id`→facility (+1 audit FK→app_user) | app_user, maintenance_request, service_request |
| 64 | `facility_user` | Configuration | User / Staff / Guest | Facility membership of a user. | 6 | 13 | `facility_id, app_user_id` | `app_user_id`→app_user, `facility_id`→facility (+1 audit FK→app_user) | — |
| 65 | `job_function` | Master | User / Staff / Guest | Staff job function per facility. | 9 | 5 | `id` | `facility_id`→facility (+1 audit FK→app_user) | app_user |
| 66 | `role` | Master | User / Staff / Guest | Named role per facility; `role_type` (admin/manager/staff/guest/system_user) gates HMS Web login. | 10 | 7 | `id` | `facility_id`→facility (+1 audit FK→app_user) | activity_role_association, role_module_permission, user_role |
| 67 | `role_module` | Reference | User / Staff / Guest | Registry of the 18 permission modules. | 6 | 18 | `id` | — | role_module_permission |
| 68 | `role_module_permission` | Configuration | User / Staff / Guest | Read/write grant per role × module. | 6 | 65 | `role_id, module_id` | `module_id`→role_module, `role_id`→role | — |
| 69 | `user_role` | Configuration | User / Staff / Guest | Role held by a user at a facility. | 6 | 14 | `facility_id, app_user_id, role_id` | `app_user_id`→app_user, `facility_id`→facility, `role_id`→role (+1 audit FK→app_user) | — |
| 70 | `access_key` | Transaction / Operational | Access / Keys | Issued digital door keys (app/keypad). | 13 | 5 | `id` | `device_id`→device, `key_type`→key_type, `maintenance_request_id`→maintenance_request, `stay_id`→stay, `user_device_acl_id`→user_device_acl (+1 audit FK→app_user) | — |
| 71 | `key_type` | Reference | Access / Keys | Key type lookup: Primary, Shared, Staff, Default. | 4 | 4 | `id` | — | access_key, lock_activity_log |
| 72 | `lock_activity_log` | Audit / History | Access / Keys | Door lock/unlock event log. | 13 | 5 | `id` | `amenity_id`→amenity, `app_user_id`→app_user, `facility_id`→facility, `key_type`→key_type, `lock_id`→device, `stay_id`→stay | — |
| 73 | `user_device` | Transaction / Operational | Access / Keys | User mobile device & push token. | 12 | 4 | `id` | `app_user_id`→app_user, `stay_id`→stay, `user_token_id`→user_token | — |
| 74 | `user_device_acl` | Transaction / Operational | Access / Keys | Time-boxed device access grant (user × device × stay). | 14 | 5 | `id` | `amenity_id`→amenity, `amenity_type_id`→amenity_type, `app_user_id`→app_user, `device_id`→device, `device_type_id`→device_type, `stay_id`→stay (+1 audit FK→app_user) | access_key |
| 75 | `user_token` | Transaction / Operational | Access / Keys | API session tokens. | 8 | 3 | `id` | `app_user_id`→app_user | user_device |
| 76 | `activity` | Audit / History | Notifications & Activity | In-app activity feed event (polymorphic entity_id). | 13 | 10 | `id` | `activity_type_id`→activity_type, `actor_id`→app_user, `entity_type_id`→entity_type, `facility_id`→facility, `stay_id`→stay | activity_notifier |
| 77 | `activity_notifier` | Transaction / Operational | Notifications & Activity | Per-user delivery / read state of an activity. | 7 | 15 | `activity_id, app_user_id` | `activity_id`→activity, `app_user_id`→app_user | — |
| 78 | `activity_role_association` | Configuration | Notifications & Activity | Which roles are notified of which activity types. | 4 | 34 | `activity_type_id, role_id` | `activity_type_id`→activity_type, `role_id`→role | — |
| 79 | `activity_type` | Reference | Notifications & Activity | Activity taxonomy (22 types). | 7 | 22 | `id` | `entity_type_id`→entity_type | activity, activity_role_association |
| 80 | `entity_type` | Reference | Notifications & Activity | Entity lookup: Booking, Occupancy, Service Requests, Maintenance Requests, Default Key. | 4 | 5 | `id` | — | activity, activity_type |
| 81 | `notification` | Transaction / Operational | Notifications & Activity | Notification dispatch queue entry. | 9 | 6 | `id` | `template_id`→notification_template | notification_receiver |
| 82 | `notification_receiver` | Transaction / Operational | Notifications & Activity | Recipient of a notification. | 11 | 6 | `id` | `app_user_id`→app_user, `notification_id`→notification | notification_result |
| 83 | `notification_result` | Audit / History | Notifications & Activity | Per-channel delivery outcome. | 9 | 6 | `id` | `receiver_id`→notification_receiver | — |
| 84 | `notification_template` | Configuration | Notifications & Activity | Notification template per channel. | 7 | 16 | `id` | — | notification |
| 85 | `promo_code` | Master | Marketing (Offers) | Offer / discount coupon. | 16 | 3 | `id` | `promo_code_icon`→attachment (+1 audit FK→app_user) | promo_code_amenity, service_request |
| 86 | `promo_code_amenity` | Configuration | Marketing (Offers) | Rooms an offer applies to. | 6 | 8 | `promo_code_id, amenity_id` | `amenity_id`→amenity, `promo_code_id`→promo_code (+1 audit FK→app_user) | — |
| 87 | `facility_event` | Master | Marketing (Events) | Hotel event (venue, dates, attendees, cancellation). | 17 | 3 | `id` | `facility_id`→facility, `image_id`→attachment (+1 audit FK→app_user) | — |
| 88 | `occasion` | Master | Holiday Management | Holidays and other occasions (festival, birthday, anniversary) with dates, repeat flag, hub notification. | 17 | 4 | `id` | `app_user_id`→app_user, `facility_id`→facility, `occasion_type`→occasion_type (+1 audit FK→app_user) | — |
| 89 | `occasion_type` | Reference | Holiday Management | Occasion type lookup: Festival, Birthday, Marriage anniversary, Holiday. | 5 | 4 | `id` | — | occasion |
| 90 | `scheduler_job` | Configuration | Scheduler | Scheduled / cron job definitions. | 9 | 5 | `id` | — | scheduler_job_execution |
| 91 | `scheduler_job_execution` | Audit / History | Scheduler | Scheduler run history. | 9 | 6 | `id` | `scheduler_job_id`→scheduler_job | — |
| 92 | `attachment` | Master | Shared | File registry (file name/path) referenced as image/document by 10 tables. | 8 | 8 | `id` | `facility_id`→facility (+1 audit FK→app_user) | 10 tables (see §2) |
| 93 | `alembic_version` | Other | System | Alembic migration head marker (value `0e2687233b59`). | 1 | 1 | `version_num` | — | — |

---

## 2. Table-by-table analysis

Each card answers the ten questions for one table. **Important columns** lists the business columns (it leaves out ids, FK columns and the timestamp/audit columns every table carries). **All columns** gives the full column list with its PostgreSQL type. **Evidence** links the ORM model class and the migration `create_table` line.

Common technical columns (present on almost every table): `id` (UUID or bigint PK), `created_on` / `updated_on` (timestamptz, NOT NULL), `legacy_id` (bigint, UNIQUE; holds the original IKANOS id) and `created_by` (FK → `app_user`).


### 2.1 Facility & Property

#### `facility`

| | |
|---|---|
| **Purpose** | The hotel / premise. Tenant root for almost every other table (29 tables reference it). |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `default_key_user` → `app_user.id` (on delete restrict); `facility_image_id` → `attachment.id` (on delete cascade); `org_id` → `organisation.id` (on delete cascade) |
| **Unique** | `(facility_uid)`, `(legacy_id)` |
| **Important columns** | `facility_uid`, `name`, `currency_id`, `city`, `state`, `pin_code`, `guest_rooms`, `email` |
| **Depends on** | `app_user`, `attachment`, `organisation` |
| **Depended on by** | `activity`, `amenity`, `amenity_type`, `attachment`, `daily_dual_data_point`, `department`, `device`, `device_incident`, `energy_stat`, `facility_event`, `facility_user`, `feature`, `invoice`, `job_function`, `lock_activity_log`, `maintenance_request`, `mqtt_broker`, `occasion`, `package`, `property`, `property_chain`, `property_type`, `role`, `service_category`, `service_category_item`, `service_request`, `user_role`, `value_alert`, `value_alert_limit_config` |
| **Business process** | Facility & Property |
| **Backend usage** | facility.py `list_facilities`, `get_facility`, `facility_counts`; facility_write.py `update_facility`; access_write.py `default_facility_id` |
| **API** | GET /facilities, GET/PATCH /facilities/{id} |
| **Frontend usage** | FacilityManagement.tsx, KeySettings.tsx (`useFacilities`) |
| **Rows (live)** | 1 |
| **All columns** (19; NN = NOT NULL) | `org_id` uuid NN, `facility_uid` varchar NN, `name` varchar NN, `currency_id` int2, `city` varchar, `state` varchar, `pin_code` varchar, `guest_rooms` int4, `email` varchar NN, `additional_email` varchar, `google_map_link` varchar, `cloud_details` jsonb, `facility_image_id` uuid, `default_key_user` uuid, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:50](../backend/app/models/facility.py#L50) `Facility` · [migration:431](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L431) |

#### `organisation`

| | |
|---|---|
| **Purpose** | Tenant / owning organisation of a facility. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)`, `(org_uid)` |
| **Important columns** | `name`, `org_uid` |
| **Depends on** | `app_user` |
| **Depended on by** | `facility` |
| **Business process** | Facility & Property |
| **Backend usage** | None (only `facility.org_id` echoed in facility responses) |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 1 |
| **All columns** (7; NN = NOT NULL) | `name` varchar NN, `org_uid` varchar NN, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:38](../backend/app/models/facility.py#L38) `Organisation` · [migration:216](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L216) |

#### `property`

| | |
|---|---|
| **Purpose** | One node of the building structure (a building, wing or floor). |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `property_type_id` → `property_type.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `property_name`, `status` |
| **Depends on** | `app_user`, `facility`, `property_type` |
| **Depended on by** | `property_chain` |
| **Business process** | Facility & Property |
| **Backend usage** | facility.py `list_properties`, `get_property`; aliased as Building/Floor in facility.py and occupancy.py |
| **API** | GET /properties[/{id}] (and indirectly /buildings, /floors) |
| **Frontend usage** | `useProperties` has no consumer; used indirectly via buildings/floors |
| **Rows (live)** | 4 |
| **All columns** (9; NN = NOT NULL) | `property_name` varchar NN, `property_type_id` uuid NN, `facility_id` uuid, `status` int2 NN, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:143](../backend/app/models/facility.py#L143) `Property` · [migration:885](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L885) |

#### `property_chain`

| | |
|---|---|
| **Purpose** | Materialised Building → Floor path (level_one/two/three → property). Rooms point to a chain. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `level_one_id` → `property.id` (on delete restrict); `level_three_id` → `property.id` (on delete restrict); `level_two_id` → `property.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `app_user`, `facility`, `property` |
| **Depended on by** | `amenity` |
| **Business process** | Facility & Property |
| **Backend usage** | facility.py `list_buildings`, `list_floors`, room statement; occupancy.py statement |
| **API** | GET /buildings[/{id}], GET /floors[/{id}] |
| **Frontend usage** | Dashboard.tsx, StatusSection.tsx, Occupancy.tsx, RoomView.tsx |
| **Rows (live)** | 3 |
| **All columns** (10; NN = NOT NULL) | `level_one_id` uuid NN, `level_two_id` uuid, `level_three_id` uuid, `facility_id` uuid, `status` int2 NN, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:170](../backend/app/models/facility.py#L170) `PropertyChain` · [migration:943](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L943) |

#### `property_type`

| | |
|---|---|
| **Purpose** | Kind of structure and the depth (`levels`) of the property chain. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | `facility_id` → `facility.id` (on delete cascade); `property_type_image_id` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `property_type_name`, `levels`, `status` |
| **Depends on** | `attachment`, `facility` |
| **Depended on by** | `property` |
| **Business process** | Facility & Property |
| **Backend usage** | facility.py (joined in property/building statements) |
| **API** | Fields inside /properties and /buildings |
| **Frontend usage** | Not directly |
| **Rows (live)** | 1 |
| **All columns** (9; NN = NOT NULL) | `property_type_name` varchar NN, `property_type_image_id` uuid, `levels` int2 NN, `facility_id` uuid, `status` int2 NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:120](../backend/app/models/facility.py#L120) `PropertyType` · [migration:773](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L773) |


### 2.2 Room / Occupancy

#### `amenity`

| | |
|---|---|
| **Purpose** | A bookable space: guest room, suite, restaurant, gym, conference room. Carries the room's current status (FK amenity_status). 18 tables reference it. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_type_id` → `amenity_type.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `package_id` → `package.id` (on delete restrict); `parent_amenity_id` → `amenity.id` (on delete cascade); `property_chain_id` → `property_chain.id` (on delete restrict); `status` → `amenity_status.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `is_dnd`, `power_save_mode`, `metadata` |
| **Depends on** | `amenity_status`, `amenity_type`, `app_user`, `facility`, `package`, `property_chain` |
| **Depended on by** | `amenity`, `amenity_condition_status`, `device`, `device_alert`, `device_incident`, `energy_stat`, `job_order_amenity`, `lock_activity_log`, `maintenance_request_amenity`, `promo_code_amenity`, `room_allocation`, `room_service_request`, `sensor_operation_stat`, `service_category_item`, `service_request`, `stay_user`, `user_device_acl`, `value_alert` |
| **Business process** | Room / Occupancy |
| **Backend usage** | facility.py `list_rooms`, `get_room`; occupancy.py `list_occupancy`, `get_occupancy`; facility_write.py `create_room`, `update_room`; stays_write.py `update_room_state` + status changes on check-in/out/allocate |
| **API** | GET/POST /rooms, GET/PATCH /rooms/{id}, GET /occupancy[/{id}], PATCH /occupancy/{id} |
| **Frontend usage** | Occupancy.tsx, RoomView.tsx, FacilityManagement.tsx, Dashboard KPIs |
| **Rows (live)** | 27 |
| **All columns** (15; NN = NOT NULL) | `name` varchar NN, `parent_amenity_id` uuid, `amenity_type_id` uuid NN, `facility_id` uuid, `property_chain_id` uuid, `package_id` uuid NN, `status` int2, `is_dnd` int2, `power_save_mode` int2, `metadata` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [amenity.py:65](../backend/app/models/amenity.py#L65) `Amenity` · [migration:991](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L991) |

#### `amenity_condition`

| | |
|---|---|
| **Purpose** | Room condition lookup: Dirty, Low battery, Under maintenance, Sanitation. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `amenity_condition_status` |
| **Business process** | Room / Occupancy |
| **Backend usage** | occupancy.py `list_amenity_conditions` |
| **API** | GET /amenity-conditions |
| **Frontend usage** | RoomConditionsDialog.tsx |
| **Rows (live)** | 4 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [amenity.py:53](../backend/app/models/amenity.py#L53) `AmenityCondition` · [migration:78](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L78) |

#### `amenity_condition_status`

| | |
|---|---|
| **Purpose** | Active conditions currently flagged on a room (room × condition). |
| **Category** | Transaction / Operational |
| **Primary key** | `amenity_id, amenity_condition_id` |
| **Foreign keys** | `amenity_condition_id` → `amenity_condition.id` (on delete cascade); `amenity_id` → `amenity.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `status` |
| **Depends on** | `amenity`, `amenity_condition` |
| **Depended on by** | — |
| **Business process** | Room / Occupancy |
| **Backend usage** | facility.py/occupancy.py condition lookups; stays_write.py `set_room_conditions` (delete + insert) |
| **API** | PUT /occupancy/{id}/conditions |
| **Frontend usage** | Occupancy.tsx, RoomConditionsDialog.tsx |
| **Rows (live)** | 13 |
| **All columns** (5; NN = NOT NULL) | `amenity_id` uuid NN, `amenity_condition_id` int2 NN, `status` int2 NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [amenity.py:123](../backend/app/models/amenity.py#L123) `AmenityConditionStatus` · [migration:1021](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1021) |

#### `amenity_status`

| | |
|---|---|
| **Purpose** | Room status lookup: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `amenity_status_name` |
| **Depends on** | — |
| **Depended on by** | `amenity` |
| **Business process** | Room / Occupancy |
| **Backend usage** | occupancy.py `list_amenity_statuses`; stays_write.py status helpers |
| **API** | GET /amenity-statuses |
| **Frontend usage** | OccupancyStatisticsChart.tsx, DashboardKPIs.tsx, ReallocateRoomDialog.tsx |
| **Rows (live)** | 4 |
| **All columns** (4; NN = NOT NULL) | `amenity_status_name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [amenity.py:42](../backend/app/models/amenity.py#L42) `AmenityStatus` · [migration:85](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L85) |

#### `amenity_type`

| | |
|---|---|
| **Purpose** | Category of space (Guest Room, Suite, Restaurant…) with `amenity_category` enum room/restaurant/others. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `image_id` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `status`, `amenity_category` |
| **Depends on** | `app_user`, `attachment`, `facility` |
| **Depended on by** | `amenity`, `package`, `user_device_acl` |
| **Business process** | Room / Occupancy |
| **Backend usage** | catalog.py `list_amenity_types`; facility_write.py create/update |
| **API** | GET/POST /amenity-types, PATCH /amenity-types/{id} |
| **Frontend usage** | FacilityManagement.tsx |
| **Rows (live)** | 5 |
| **All columns** (10; NN = NOT NULL) | `name` varchar NN, `facility_id` uuid, `status` int2 NN, `amenity_category` amenity_category NN, `image_id` uuid, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [amenity.py:18](../backend/app/models/amenity.py#L18) `AmenityType` · [migration:574](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L574) |

#### `feature`

| | |
|---|---|
| **Purpose** | Room feature (shown as "Room Amenities" tab). |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `device_type` → `device_type.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `feature_name`, `is_smart_feature`, `status` |
| **Depends on** | `app_user`, `device_type`, `facility` |
| **Depended on by** | `package_feature` |
| **Business process** | Room / Occupancy |
| **Backend usage** | catalog.py `list_features`; facility_write.py create/update |
| **API** | GET/POST /features, PATCH /features/{id} |
| **Frontend usage** | FacilityManagement.tsx |
| **Rows (live)** | 6 |
| **All columns** (10; NN = NOT NULL) | `facility_id` uuid, `feature_name` varchar NN, `is_smart_feature` bool, `device_type` int2, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [amenity.py:202](../backend/app/models/amenity.py#L202) `Feature` · [migration:652](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L652) |

#### `package`

| | |
|---|---|
| **Purpose** | Room package / rate plan (no price column). Every amenity must have one. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_type` → `amenity_type.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `image_id` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `description`, `status`, `is_sub_package` |
| **Depends on** | `amenity_type`, `app_user`, `attachment`, `facility` |
| **Depended on by** | `amenity`, `package_feature`, `room_allocation`, `stay_package`, `sub_package` |
| **Business process** | Room / Occupancy |
| **Backend usage** | catalog.py `list_packages`, `get_package`; facility_write.py create/update (status 0 = soft delete) |
| **API** | GET/POST /packages, PATCH /packages/{id} |
| **Frontend usage** | FacilityManagement.tsx |
| **Rows (live)** | 8 |
| **All columns** (12; NN = NOT NULL) | `facility_id` uuid, `name` varchar NN, `description` text, `status` int2 NN, `amenity_type` uuid NN, `is_sub_package` bool NN, `image_id` uuid, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [amenity.py:145](../backend/app/models/amenity.py#L145) `Package` · [migration:866](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L866) |

#### `package_feature`

| | |
|---|---|
| **Purpose** | Package ↔ feature link. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `feature_id` → `feature.id` (on delete cascade); `package_id` → `package.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `app_user`, `feature`, `package` |
| **Depended on by** | — |
| **Business process** | Room / Occupancy |
| **Backend usage** | catalog.py (feature names); facility_write.py (replace on package write) |
| **API** | Inside POST/PATCH /packages (`feature_ids`) |
| **Frontend usage** | FacilityManagement.tsx (display only; never sends feature_ids) |
| **Rows (live)** | 17 |
| **All columns** (8; NN = NOT NULL) | `package_id` uuid NN, `feature_id` uuid NN, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [amenity.py:227](../backend/app/models/amenity.py#L227) `PackageFeature` · [migration:927](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L927) |

#### `sub_package`

| | |
|---|---|
| **Purpose** | Parent package → child package link. |
| **Category** | Configuration |
| **Primary key** | `parent_package_id, sub_package_id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `parent_package_id` → `package.id` (on delete restrict); `sub_package_id` → `package.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | — |
| **Depends on** | `app_user`, `package` |
| **Depended on by** | — |
| **Business process** | Room / Occupancy |
| **Backend usage** | None (app uses `package.is_sub_package` instead) |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 7 |
| **All columns** (5; NN = NOT NULL) | `parent_package_id` uuid NN, `sub_package_id` uuid NN, `created_by` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [amenity.py:181](../backend/app/models/amenity.py#L181) `SubPackage` · [migration:980](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L980) |


### 2.3 Booking / Stay

#### `import_job`

| | |
|---|---|
| **Purpose** | Bulk import job tracking (booking / job order CSV). |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `import_job_name`, `entity_type`, `import_status`, `total_records`, `success_count`, `error_count`, `import_file_name`, `error_file_name` |
| **Depends on** | `app_user` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None (Bookings import shows a 'not connected' toast) |
| **Rows (live)** | 3 |
| **All columns** (14; NN = NOT NULL) | `import_job_name` varchar, `entity_type` import_entity_type NN, `import_status` import_status NN, `total_records` int4, `success_count` int4, `error_count` int4, `import_file_name` varchar, `error_file_name` varchar, `completed_on` timestamptz, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:238](../backend/app/models/stay.py#L238) `ImportJob` · [migration:134](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L134) |

#### `invoice`

| | |
|---|---|
| **Purpose** | Stay invoice with billing & facility snapshot and amounts. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `billing_user_id` → `app_user.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `facility_image_id` → `attachment.id` (on delete restrict); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(invoice_number)`, `(legacy_id)` |
| **Important columns** | `invoice_number`, `invoice_date`, `invoice_due_date`, `billing_user_name`, `billing_address`, `facility_name`, `facility_address`, `net_amount` |
| **Depends on** | `app_user`, `attachment`, `facility`, `stay` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `list_invoices`, `get_invoice` (read only; generation not implemented) |
| **API** | GET /invoices[/{id}] |
| **Frontend usage** | None (`useInvoices` unused; Invoice button disabled) |
| **Rows (live)** | 2 |
| **All columns** (19; NN = NOT NULL) | `invoice_number` varchar NN, `invoice_date` timestamptz NN, `invoice_due_date` timestamptz, `billing_user_id` uuid NN, `billing_user_name` varchar, `billing_address` varchar, `facility_id` uuid, `facility_name` varchar, `facility_address` varchar, `facility_image_id` uuid, `stay_id` uuid NN, `net_amount` numeric, `total_tax` numeric, `total_amount` numeric, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:190](../backend/app/models/stay.py#L190) `Invoice` · [migration:669](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L669) |

#### `room_allocation`

| | |
|---|---|
| **Purpose** | Which room(s) a stay holds (stay ↔ amenity) with package. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `package_id` → `package.id` (on delete cascade); `room_id` → `amenity.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `amenity`, `app_user`, `package`, `stay` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `stay_room_allocations`; stays_write.py `create_stay`, `allocate_room`, `reallocate_room`, `release_allocation`; occupancy.py |
| **API** | GET/POST /stays/{id}/room-allocations, PATCH/DELETE /room-allocations/{id} |
| **Frontend usage** | Bookings.tsx (on create), ReallocateRoomDialog.tsx |
| **Rows (live)** | 6 |
| **All columns** (9; NN = NOT NULL) | `stay_id` uuid NN, `room_id` uuid NN, `package_id` uuid, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:130](../backend/app/models/stay.py#L130) `RoomAllocation` · [migration:1113](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1113) |

#### `stay`

| | |
|---|---|
| **Purpose** | The reservation/booking and its check-in/check-out lifecycle (`stay_status` enum). No facility_id column. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `booking_user_id` → `app_user.id` (on delete restrict); `checkout_initiated_by` → `app_user.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `modified_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(internal_stay_ref_number)`, `(legacy_id)` |
| **Important columns** | `internal_stay_ref_number`, `external_stay_ref_number`, `no_of_rooms`, `no_of_guests`, `expected_checkin_time`, `expected_checkout_time`, `actual_checkin_time`, `actual_checkout_time` |
| **Depends on** | `app_user` |
| **Depended on by** | `access_key`, `activity`, `invoice`, `lock_activity_log`, `room_allocation`, `room_service_request`, `service_request`, `stay_package`, `stay_user`, `user_device`, `user_device_acl`, `user_document` |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `list_stays`, `get_stay`; stays_write.py `create_stay`, `update_stay`, `check_in`, `check_out`, `extend_stay`, `set_stay_status`, `set_document_approval`, `cancel_stay`; occupancy.py, reports.py |
| **API** | GET/POST /stays, GET/PATCH /stays/{id}, POST /stays/{id}/check-in\|check-out\|extend\|status\|documents/approval\|cancel |
| **Frontend usage** | Bookings.tsx, RoomView.tsx, Occupancy.tsx (current stay), CheckOutConfirmDialog.tsx |
| **Rows (live)** | 7 |
| **All columns** (21; NN = NOT NULL) | `internal_stay_ref_number` varchar NN, `external_stay_ref_number` varchar, `booking_user_id` uuid NN, `no_of_rooms` int2, `no_of_guests` int2 NN, `expected_checkin_time` timestamptz NN, `expected_checkout_time` timestamptz NN, `actual_checkin_time` timestamptz, `actual_checkout_time` timestamptz, `comments` text, `gst` varchar, `checkout_initiated_by` uuid, `document_approval_status` document_approval_status NN, `status` stay_status, `request_source` request_source, `created_by` uuid NN, `modified_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:21](../backend/app/models/stay.py#L21) `Stay` · [migration:310](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L310) |

#### `stay_package`

| | |
|---|---|
| **Purpose** | Packages purchased on a stay. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `package_id` → `package.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `package`, `stay` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `stay_packages` (read only) |
| **API** | Inside GET /stays/{id} |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (7; NN = NOT NULL) | `stay_id` uuid NN, `package_id` uuid NN, `status` int2 NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:108](../backend/app/models/stay.py#L108) `StayPackage` · [migration:965](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L965) |

#### `stay_user`

| | |
|---|---|
| **Purpose** | Occupants (guests) of a stay, optionally per room. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `room_id` → `amenity.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `is_key_required`, `status` |
| **Depends on** | `amenity`, `app_user`, `stay` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `stay_occupants`; stays_write.py `add_occupant`, `remove_occupant`; occupancy.py `get_occupancy` |
| **API** | GET/POST /stays/{id}/occupants, DELETE /stay-occupants/{id} |
| **Frontend usage** | RoomDetailsModal.tsx via /occupancy/{id} (occupant hooks unused) |
| **Rows (live)** | 8 |
| **All columns** (10; NN = NOT NULL) | `app_user_id` uuid NN, `room_id` uuid, `stay_id` uuid NN, `is_key_required` int2, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:80](../backend/app/models/stay.py#L80) `StayUser` · [migration:1222](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1222) |

#### `user_document`

| | |
|---|---|
| **Purpose** | Guest ID-proof document pointer with approval status. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `attachment_id` → `attachment.id` (on delete cascade); `stay_id` → `stay.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `document_approval_status`, `status` |
| **Depends on** | `app_user`, `attachment`, `stay` |
| **Depended on by** | — |
| **Business process** | Booking / Stay |
| **Backend usage** | stay.py `stay_documents` (read only) |
| **API** | GET /stays/{id}/documents |
| **Frontend usage** | None found |
| **Rows (live)** | 3 |
| **All columns** (9; NN = NOT NULL) | `app_user_id` uuid NN, `attachment_id` uuid NN, `stay_id` uuid, `document_approval_status` user_document_approval_status, `status` int2, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [stay.py:160](../backend/app/models/stay.py#L160) `UserDocument` · [migration:533](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L533) |


### 2.4 Service Requests

#### `room_service_request`

| | |
|---|---|
| **Purpose** | Guest-app in-room service call with its own 4-value enum (unassigned/assigned/cancelled/completed). |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `assigned_to` → `app_user.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `guest_room_id` → `amenity.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `service_request_status`, `comments`, `completed_on` |
| **Depends on** | `amenity`, `app_user`, `stay` |
| **Depended on by** | `room_service_request_item` |
| **Business process** | Service Requests |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 3 |
| **All columns** (11; NN = NOT NULL) | `guest_room_id` uuid NN, `stay_id` uuid, `service_request_status` room_service_request_status, `assigned_to` uuid, `comments` text, `completed_on` timestamptz, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:267](../backend/app/models/service.py#L267) `RoomServiceRequest` · [migration:1132](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1132) |

#### `room_service_request_item`

| | |
|---|---|
| **Purpose** | Items of a room service call. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `room_service_request_id` → `room_service_request.id` (on delete cascade); `service_category_item_id` → `service_category_item.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `is_processed` |
| **Depends on** | `room_service_request`, `service_category_item` |
| **Depended on by** | — |
| **Business process** | Service Requests |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 4 |
| **All columns** (7; NN = NOT NULL) | `room_service_request_id` uuid NN, `service_category_item_id` uuid NN, `is_processed` int2, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:305](../backend/app/models/service.py#L305) `RoomServiceRequestItem` · [migration:1432](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1432) |

#### `service_category`

| | |
|---|---|
| **Purpose** | Category under a service type (e.g. food categories, maintenance categories). |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `category_icon` → `attachment.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete restrict); `service_type` → `service_type.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `category_name`, `description`, `service_category_key`, `status` |
| **Depends on** | `app_user`, `attachment`, `facility`, `service_type` |
| **Depended on by** | `maintenance_request`, `service_category_item`, `service_request`, `service_request_item` |
| **Business process** | Service Requests |
| **Backend usage** | service.py `list_service_categories`; services_write.py create/update |
| **API** | GET/POST /service-categories, GET/PATCH /service-categories/{id} |
| **Frontend usage** | ServicesSetup.tsx, ServicePlanning.tsx |
| **Rows (live)** | 13 |
| **All columns** (12; NN = NOT NULL) | `service_type` int2 NN, `category_name` varchar, `description` text, `category_icon` uuid, `facility_id` uuid, `service_category_key` varchar, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:55](../backend/app/models/service.py#L55) `ServiceCategory` · [migration:804](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L804) |

#### `service_category_item`

| | |
|---|---|
| **Purpose** | Requestable item with price; JSONB metadata. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `category_id` → `service_category.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `item_icon` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `item_name`, `description`, `price_per_unit`, `status`, `metadata` |
| **Depends on** | `amenity`, `app_user`, `attachment`, `facility`, `service_category` |
| **Depended on by** | `maintenance_request`, `room_service_request_item`, `service_request_item` |
| **Business process** | Service Requests |
| **Backend usage** | service.py `list_service_items`; services_write.py create/update |
| **API** | GET/POST /service-items, GET/PATCH /service-items/{id} |
| **Frontend usage** | ServicesSetup.tsx |
| **Rows (live)** | 22 |
| **All columns** (14; NN = NOT NULL) | `item_name` varchar NN, `item_icon` uuid, `category_id` uuid NN, `description` text, `price_per_unit` numeric, `amenity_id` uuid, `facility_id` uuid, `status` int2, `metadata` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:87](../backend/app/models/service.py#L87) `ServiceCategoryItem` · [migration:1151](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1151) |

#### `service_request`

| | |
|---|---|
| **Purpose** | Service ticket (tracking & tickets), status FK → service_status. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `app_user_id` → `app_user.id` (on delete restrict); `assigned_to` → `app_user.id` (on delete restrict); `category_id` → `service_category.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `department_id` → `department.id` (on delete restrict); `facility_id` → `facility.id` (on delete restrict); `promo_code_id` → `promo_code.id` (on delete restrict); `service_type` → `service_type.id` (on delete restrict); `status` → `service_status.id` (on delete restrict); `stay_id` → `stay.id` (on delete restrict); `updated_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)`, `(ref_number)` |
| **Important columns** | `ref_number`, `description`, `request_source`, `net_amount`, `total_tax`, `total_amount`, `expected_date`, `completed_on` |
| **Depends on** | `amenity`, `app_user`, `department`, `facility`, `promo_code`, `service_category`, `service_status`, `service_type`, `stay` |
| **Depended on by** | `service_request_item` |
| **Business process** | Service Requests |
| **Backend usage** | service.py `list_service_requests`, `get_service_request`; services_write.py `create_service_request`, `update_service_request`, `cancel_service_request`; reports.py |
| **API** | GET/POST /service-requests, GET/PATCH /service-requests/{id}, POST /service-requests/{id}/cancel |
| **Frontend usage** | Tickets.tsx, ServiceTracking.tsx, ServiceRequestActionsDialog.tsx, RoomDetailsModal.tsx, AlertsPanel.tsx |
| **Rows (live)** | 7 |
| **All columns** (25; NN = NOT NULL) | `service_type` int2 NN, `ref_number` varchar, `description` text, `assigned_to` uuid, `department_id` uuid, `category_id` uuid, `promo_code_id` uuid, `amenity_id` uuid, `stay_id` uuid, `app_user_id` uuid, `request_source` request_source, `facility_id` uuid, `net_amount` numeric, `total_tax` numeric, `total_amount` numeric, `expected_date` timestamptz, `completed_on` timestamptz, `status` int2, `status_reason` varchar, `created_by` uuid NN, `updated_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:138](../backend/app/models/service.py#L138) `ServiceRequest` · [migration:1176](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1176) |

#### `service_request_item`

| | |
|---|---|
| **Purpose** | Line items of a service request. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `assigned_to` → `app_user.id` (on delete restrict); `category_id` → `service_category.id` (on delete restrict); `item_id` → `service_category_item.id` (on delete restrict); `service_request_id` → `service_request.id` (on delete restrict); `status` → `service_status.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `quantity`, `price_per_unit` |
| **Depends on** | `app_user`, `service_category`, `service_category_item`, `service_request`, `service_status` |
| **Depended on by** | — |
| **Business process** | Service Requests |
| **Backend usage** | service.py `request_items`; services_write.py `replace_service_request_items` (hard delete + insert) |
| **API** | PUT /service-requests/{id}/items; inside GET /service-requests/{id} |
| **Frontend usage** | None found |
| **Rows (live)** | 8 |
| **All columns** (11; NN = NOT NULL) | `service_request_id` uuid NN, `item_id` uuid, `category_id` uuid, `quantity` int2, `price_per_unit` numeric, `assigned_to` uuid, `status` int2, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [service.py:228](../backend/app/models/service.py#L228) `ServiceRequestItem` · [migration:1460](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1460) |

#### `service_status`

| | |
|---|---|
| **Purpose** | Request lifecycle lookup: 1 Pending, 2 Assigned, 3 Partially completed, 4 Completed, 5 Canceled. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `maintenance_request`, `service_request`, `service_request_item` |
| **Business process** | Service Requests |
| **Backend usage** | service.py `list_service_statuses`; services_write.py / maintenance_write.py (hardcoded ids) |
| **API** | GET /service-statuses[/{id}] |
| **Frontend usage** | ServiceRequestActionsDialog.tsx, ServiceTracking.tsx |
| **Rows (live)** | 5 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [service.py:43](../backend/app/models/service.py#L43) `ServiceStatus` · [migration:296](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L296) |

#### `service_type`

| | |
|---|---|
| **Purpose** | 7 service types (Room Service, Travel Desk, … Sanitation Maintenance). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `service_category`, `service_request` |
| **Business process** | Service Requests |
| **Backend usage** | service.py `list_service_types`, `get_service_type`, `service_type_counts` |
| **API** | GET /service-types[/{id}] |
| **Frontend usage** | ServiceTracking.tsx, Tickets.tsx, ServicesSetup.tsx, ServicePlanning.tsx |
| **Rows (live)** | 7 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [service.py:30](../backend/app/models/service.py#L30) `ServiceType` · [migration:303](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L303) |


### 2.5 Maintenance (Service Planning)

#### `maintenance_request`

| | |
|---|---|
| **Purpose** | Scheduled / planned / disinfection maintenance work; status FK → service_status; soft delete via status 0. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `category_id` → `service_category.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `department_id` → `department.id` (on delete restrict); `facility_id` → `facility.id` (on delete restrict); `item_id` → `service_category_item.id` (on delete restrict); `maintenance_request_status` → `service_status.id` (on delete restrict); `parent_id` → `maintenance_request.id` (on delete restrict); `updated_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `maintenance_request_type`, `maintenance_start_date`, `maintenance_end_date`, `maintenance_start_time`, `maintenance_end_time`, `is_recurring`, `completed_on`, `is_room` |
| **Depends on** | `app_user`, `department`, `facility`, `service_category`, `service_category_item`, `service_status` |
| **Depended on by** | `access_key`, `maintenance_request`, `maintenance_request_amenity`, `maintenance_request_assignee`, `maintenance_request_recurrence` |
| **Business process** | Maintenance (Service Planning) |
| **Backend usage** | maintenance.py `list_maintenance_requests`, `get_maintenance_request`; maintenance_write.py create/update/cancel/remove; reports.py |
| **API** | GET/POST /maintenance-requests, GET/PATCH/DELETE /maintenance-requests/{id}, POST …/{id}/cancel |
| **Frontend usage** | ServicePlanning.tsx |
| **Rows (live)** | 3 |
| **All columns** (25; NN = NOT NULL) | `maintenance_request_type` maintenance_request_type NN, `maintenance_start_date` date, `maintenance_end_date` date, `maintenance_start_time` timestamptz, `maintenance_end_time` timestamptz, `is_recurring` int2, `department_id` uuid, `category_id` uuid, `item_id` uuid, `facility_id` uuid, `completed_on` timestamptz, `is_room` int2, `non_room_comments` text, `parent_id` uuid, `maintenance_request_status` int2 NN, `status_reason` varchar, `delete_comments` text, `under_maintenance` bool, `status` int2, `created_by` uuid NN, `updated_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [maintenance.py:29](../backend/app/models/maintenance.py#L29) `MaintenanceRequest` · [migration:1375](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1375) |

#### `maintenance_request_amenity`

| | |
|---|---|
| **Purpose** | Rooms covered by a maintenance request. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `maintenance_request_id` → `maintenance_request.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `amenity`, `app_user`, `maintenance_request` |
| **Depended on by** | — |
| **Business process** | Maintenance (Service Planning) |
| **Backend usage** | maintenance.py; maintenance_write.py (replace via status 0/1) |
| **API** | Inside /maintenance-requests (`amenity_ids`) |
| **Frontend usage** | ServicePlanning.tsx |
| **Rows (live)** | 6 |
| **All columns** (8; NN = NOT NULL) | `maintenance_request_id` uuid NN, `amenity_id` uuid NN, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [maintenance.py:135](../backend/app/models/maintenance.py#L135) `MaintenanceRequestAmenity` · [migration:1595](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1595) |

#### `maintenance_request_assignee`

| | |
|---|---|
| **Purpose** | Staff assigned to a maintenance request. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `maintenance_request_id` → `maintenance_request.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status` |
| **Depends on** | `app_user`, `maintenance_request` |
| **Depended on by** | — |
| **Business process** | Maintenance (Service Planning) |
| **Backend usage** | maintenance.py; maintenance_write.py (replace via status 0/1) |
| **API** | Inside /maintenance-requests (`assignee_ids`) |
| **Frontend usage** | ServicePlanning.tsx |
| **Rows (live)** | 4 |
| **All columns** (8; NN = NOT NULL) | `maintenance_request_id` uuid NN, `app_user_id` uuid NN, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [maintenance.py:164](../backend/app/models/maintenance.py#L164) `MaintenanceRequestAssignee` · [migration:1611](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1611) |

#### `maintenance_request_recurrence`

| | |
|---|---|
| **Purpose** | 1:1 weekly recurrence rule (days_of_week bitmask). |
| **Category** | Configuration |
| **Primary key** | `maintenance_request_id` |
| **Foreign keys** | `maintenance_request_id` → `maintenance_request.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | `recurrence_type`, `days_of_week`, `max_no_of_occurrences` |
| **Depends on** | `maintenance_request` |
| **Depended on by** | — |
| **Business process** | Maintenance (Service Planning) |
| **Backend usage** | maintenance.py; maintenance_write.py (hard delete when rule dropped) |
| **API** | Inside /maintenance-requests (`recurrence`) |
| **Frontend usage** | ServicePlanning.tsx |
| **Rows (live)** | 1 |
| **All columns** (6; NN = NOT NULL) | `maintenance_request_id` uuid NN, `recurrence_type` recurrence_type NN, `days_of_week` int2, `max_no_of_occurrences` int2, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [maintenance.py:114](../backend/app/models/maintenance.py#L114) `MaintenanceRequestRecurrence` · [migration:1626](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1626) |


### 2.6 Job Orders

#### `job_order`

| | |
|---|---|
| **Purpose** | Field work order (installation/replacement/troubleshoot). No facility_id column. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `assigned_to` → `app_user.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)`, `(order_reference)` |
| **Important columns** | `order_reference`, `description`, `type_of_work`, `work_commence`, `estimated_completion_date`, `authentication_code`, `job_order_status`, `completed_on` |
| **Depends on** | `app_user` |
| **Depended on by** | `job_order_amenity`, `job_order_device` |
| **Business process** | Job Orders |
| **Backend usage** | job_order.py `list_job_orders`, `get_job_order`; job_order_write.py `create_job_order`, `update_job_order`, `remove_job_order` (soft) |
| **API** | GET/POST /job-orders, GET/PATCH/DELETE /job-orders/{id} |
| **Frontend usage** | JobOrder.tsx |
| **Rows (live)** | 3 |
| **All columns** (15; NN = NOT NULL) | `order_reference` varchar NN, `description` varchar, `type_of_work` job_order_type_of_work NN, `work_commence` timestamptz NN, `estimated_completion_date` timestamptz NN, `authentication_code` varchar NN, `assigned_to` uuid, `job_order_status` job_order_status NN, `completed_on` timestamptz, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [job_order.py:21](../backend/app/models/job_order.py#L21) `JobOrder` · [migration:167](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L167) |

#### `job_order_amenity`

| | |
|---|---|
| **Purpose** | Rooms on a job order. |
| **Category** | Transaction / Operational |
| **Primary key** | `job_order_id, amenity_id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `job_order_id` → `job_order.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | — |
| **Depends on** | `amenity`, `job_order` |
| **Depended on by** | — |
| **Business process** | Job Orders |
| **Backend usage** | job_order.py; job_order_write.py (hard delete + insert) |
| **API** | Inside /job-orders |
| **Frontend usage** | JobOrder.tsx |
| **Rows (live)** | 4 |
| **All columns** (4; NN = NOT NULL) | `job_order_id` uuid NN, `amenity_id` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [job_order.py:82](../backend/app/models/job_order.py#L82) `JobOrderAmenity` · [migration:1091](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1091) |

#### `job_order_device`

| | |
|---|---|
| **Purpose** | Devices on a job order. |
| **Category** | Transaction / Operational |
| **Primary key** | `job_order_id, device_id` |
| **Foreign keys** | `device_id` → `device.id` (on delete restrict); `job_order_id` → `job_order.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | — |
| **Depends on** | `device`, `job_order` |
| **Depended on by** | — |
| **Business process** | Job Orders |
| **Backend usage** | job_order.py; job_order_write.py (hard delete + insert) |
| **API** | Inside /job-orders |
| **Frontend usage** | JobOrder.tsx |
| **Rows (live)** | 2 |
| **All columns** (4; NN = NOT NULL) | `job_order_id` uuid NN, `device_id` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [job_order.py:61](../backend/app/models/job_order.py#L61) `JobOrderDevice` · [migration:1339](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1339) |


### 2.7 Devices & IoT

#### `battery_life_stat`

| | |
|---|---|
| **Purpose** | Battery charge cycles per device. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `cycle_number`, `initial_battery_percentage`, `latest_battery_percentage`, `battery_life` |
| **Depends on** | `device` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py (health) |
| **API** | GET /devices/{id}/health |
| **Frontend usage** | None found |
| **Rows (live)** | 12 |
| **All columns** (9; NN = NOT NULL) | `device_id` uuid NN, `cycle_number` int2 NN, `initial_battery_percentage` numeric, `latest_battery_percentage` numeric, `battery_life` numeric, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [device.py:393](../backend/app/models/device.py#L393) `BatteryLifeStat` · [migration:1241](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1241) |

#### `command_type`

| | |
|---|---|
| **Purpose** | Device command registry (Keys, FirmwareUpdates, Checkout…). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | `device_type_id` → `device_type.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | `device_type` |
| **Depended on by** | `device_command` |
| **Business process** | Devices & IoT |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 10 |
| **All columns** (5; NN = NOT NULL) | `name` varchar NN, `device_type_id` int2, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [device.py:272](../backend/app/models/device.py#L272) `CommandType` · [migration:409](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L409) |

#### `device`

| | |
|---|---|
| **Purpose** | Physical smart device installed in a room; `parent_device_id` points to its hub. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `current_firmware_version` → `firmware.id` (on delete cascade); `device_type` → `device_type.id` (on delete restrict); `expected_firmware_version` → `firmware.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `parent_device_id` → `device.id` (on delete cascade) |
| **Unique** | `(device_uid)`, `(legacy_id)` |
| **Important columns** | `device_uid`, `part_number`, `model`, `manufacturer_name`, `mfg_date`, `device_name`, `appliance_name`, `authentication_code` |
| **Depends on** | `amenity`, `app_user`, `device_type`, `facility`, `firmware` |
| **Depended on by** | `access_key`, `battery_life_stat`, `device`, `device_alert`, `device_command`, `device_current_stat`, `device_health_stat`, `device_incident`, `device_stat`, `job_order_device`, `lock_activity_log`, `mqtt_topic`, `sensor_operation_stat`, `user_device_acl`, `value_alert`, `value_alert_limit_config` |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py `list_devices`/`get_device`; devices_write.py `create_device`, `update_device`, `set_device_config_status` |
| **API** | GET/POST /devices, GET/PATCH /devices/{id}, POST /devices/{id}/commission\|decommission\|maintenance |
| **Frontend usage** | LimitConfigAlert.tsx, JobOrder.tsx, RoomDetailsModal.tsx, RoomDetailsPanel.tsx, StatusSection.tsx (no UI for device writes) |
| **Rows (live)** | 14 |
| **All columns** (28; NN = NOT NULL) | `device_uid` varchar, `part_number` varchar, `model` varchar, `manufacturer_name` varchar, `mfg_date` timestamptz NN, `parent_device_id` uuid, `device_type` int2 NN, `device_name` varchar, `appliance_name` varchar, `facility_id` uuid NN, `amenity_id` uuid NN, `authentication_code` varchar, `health_status` device_health_status, `device_temperature` numeric, `current_firmware_version` uuid, `expected_firmware_version` uuid, `device_config_status` device_config_status, `is_power_off` bool, `installed_on` timestamptz, `operational_mode` int2, `is_other_device` int4, `status` int2, `metadata` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:97](../backend/app/models/device.py#L97) `Device` · [migration:1032](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1032) |

#### `device_command`

| | |
|---|---|
| **Purpose** | Outbound command queue to devices. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `command_type` → `command_type.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `device_id` → `device.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `command_data`, `processing_status` |
| **Depends on** | `app_user`, `command_type`, `device` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 7 |
| **All columns** (9; NN = NOT NULL) | `device_id` uuid NN, `command_type` int2 NN, `command_data` jsonb NN, `processing_status` command_processing_status, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:287](../backend/app/models/device.py#L287) `DeviceCommand` · [migration:1277](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1277) |

#### `device_current_stat`

| | |
|---|---|
| **Purpose** | Latest JSONB snapshot per device. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `device_stats`, `is_other_device` |
| **Depends on** | `device` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | telemetry.py `list_device_current_stats` |
| **API** | GET /device-current-stats[/{id}] |
| **Frontend usage** | None (`useDeviceCurrentStats` unused) |
| **Rows (live)** | 14 |
| **All columns** (7; NN = NOT NULL) | `device_id` uuid NN, `device_stats` jsonb, `is_other_device` int4, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:230](../backend/app/models/device.py#L230) `DeviceCurrentStat` · [migration:1294](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1294) |

#### `device_health_stat`

| | |
|---|---|
| **Purpose** | Device heartbeat / health & temperature log. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `device_health_status`, `device_temperature` |
| **Depends on** | `device` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py (health) |
| **API** | GET /devices/{id}/health |
| **Frontend usage** | None found |
| **Rows (live)** | 168 |
| **All columns** (7; NN = NOT NULL) | `device_id` uuid NN, `device_health_status` device_health_status NN, `device_temperature` numeric NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [device.py:246](../backend/app/models/device.py#L246) `DeviceHealthStat` · [migration:1307](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1307) |

#### `device_param`

| | |
|---|---|
| **Purpose** | EAV parameter definitions per device type (name, data type, unit). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | `device_type` → `device_type.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | `param_name`, `data_type`, `unit` |
| **Depends on** | `device_type` |
| **Depended on by** | `device_stat` |
| **Business process** | Devices & IoT |
| **Backend usage** | telemetry.py `list_device_params`; energy.py `active_energy_unit` |
| **API** | GET /device-params[/{id}] |
| **Frontend usage** | LimitConfigAlert.tsx |
| **Rows (live)** | 35 |
| **All columns** (7; NN = NOT NULL) | `device_type` int2 NN, `param_name` varchar NN, `data_type` param_data_type, `unit` varchar, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int4 NN |
| **Evidence** | [device.py:181](../backend/app/models/device.py#L181) `DeviceParam` · [migration:419](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L419) |

#### `device_stat`

| | |
|---|---|
| **Purpose** | Time-series telemetry values (EAV: device × param × timestamp → value as text). |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete cascade); `device_param_id` → `device_param.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `timestamp`, `device_param_value`, `is_other_device` |
| **Depends on** | `device`, `device_param` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | telemetry.py `list_device_stats`, `get_device_stat` |
| **API** | GET /device-stats[/{id}] |
| **Frontend usage** | RoomPowerEnergy.tsx, RoomDetailsPanel.tsx |
| **Rows (live)** | 504 |
| **All columns** (9; NN = NOT NULL) | `device_id` uuid NN, `timestamp` timestamptz NN, `device_param_id` int4 NN, `device_param_value` varchar, `is_other_device` int4, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [device.py:201](../backend/app/models/device.py#L201) `DeviceStat` · [migration:1321](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1321) |

#### `device_type`

| | |
|---|---|
| **Purpose** | 4 device families: Intellihub (HUB), AirQ, Mikos, Kleio. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name`, `device_short_code` |
| **Depends on** | — |
| **Depended on by** | `command_type`, `device`, `device_param`, `feature`, `firmware`, `user_device_acl`, `value_alert` |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py list/get; joined in telemetry/alert/job order |
| **API** | GET /device-types[/{id}] |
| **Frontend usage** | JobOrder.tsx |
| **Rows (live)** | 4 |
| **All columns** (5; NN = NOT NULL) | `name` varchar, `device_short_code` device_short_code, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [device.py:42](../backend/app/models/device.py#L42) `DeviceType` · [migration:119](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L119) |

#### `firmware`

| | |
|---|---|
| **Purpose** | Firmware build per device type; device current/expected version. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete cascade); `device_type_id` → `device_type.id` (on delete restrict); `updated_by` → `app_user.id` (on delete cascade); `uploaded_by` → `app_user.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `firmware_version`, `firmware_filename`, `firmware_url`, `firmware_size`, `crc`, `release_date`, `release_notes`, `decommission_reason` |
| **Depends on** | `app_user`, `device_type` |
| **Depended on by** | `device` |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py (joined); devices_write.py (validation) |
| **API** | None of its own (firmware routes removed) |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (17; NN = NOT NULL) | `device_type_id` int2 NN, `firmware_version` varchar NN, `firmware_filename` varchar NN, `firmware_url` varchar NN, `firmware_size` numeric, `crc` text NN, `release_date` timestamptz, `release_notes` text, `decommission_reason` varchar, `status` firmware_status NN, `uploaded_by` uuid NN, `created_by` uuid, `updated_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:58](../backend/app/models/device.py#L58) `Firmware` · [migration:457](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L457) |

#### `mqtt_broker`

| | |
|---|---|
| **Purpose** | MQTT broker connection details per facility. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `broker_name`, `broker_ip`, `broker_vpn_ip`, `broker_port`, `broker_user_name`, `broker_password` |
| **Depends on** | `facility` |
| **Depended on by** | `mqtt_topic` |
| **Business process** | Devices & IoT |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 1 |
| **All columns** (11; NN = NOT NULL) | `facility_id` uuid, `broker_name` varchar NN, `broker_ip` varchar, `broker_vpn_ip` varchar, `broker_port` int4, `broker_user_name` varchar, `broker_password` varchar, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:314](../backend/app/models/device.py#L314) `MqttBroker` · [migration:712](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L712) |

#### `mqtt_topic`

| | |
|---|---|
| **Purpose** | MQTT topic per device/broker. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete cascade); `mqtt_broker_id` → `mqtt_broker.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `topic_name`, `topic_type` |
| **Depends on** | `device`, `mqtt_broker` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 12 |
| **All columns** (8; NN = NOT NULL) | `mqtt_broker_id` uuid NN, `device_id` uuid, `topic_name` varchar NN, `topic_type` mqtt_topic_type NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [device.py:338](../backend/app/models/device.py#L338) `MqttTopic` · [migration:1416](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1416) |

#### `sensor_operation_stat`

| | |
|---|---|
| **Purpose** | Daily sensor uptime percentage. |
| **Category** | Audit / History |
| **Primary key** | `device_id, stats_date` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete cascade); `device_id` → `device.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `stats_date`, `operation_percentage` |
| **Depends on** | `amenity`, `device` |
| **Depended on by** | — |
| **Business process** | Devices & IoT |
| **Backend usage** | device.py (health) |
| **API** | GET /devices/{id}/health |
| **Frontend usage** | None found |
| **Rows (live)** | 42 |
| **All columns** (6; NN = NOT NULL) | `device_id` uuid NN, `stats_date` date NN, `amenity_id` uuid NN, `operation_percentage` numeric NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [device.py:418](../backend/app/models/device.py#L418) `SensorOperationStat` · [migration:1447](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1447) |


### 2.8 Energy

#### `energy_stat`

| | |
|---|---|
| **Purpose** | Hourly energy consumption per device name / room. |
| **Category** | Audit / History |
| **Primary key** | `device_name, facility_id, amenity_id, hour` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `device_name`, `hour`, `energy_consumed` |
| **Depends on** | `amenity`, `facility` |
| **Depended on by** | — |
| **Business process** | Energy |
| **Backend usage** | energy.py `list_energy_stats`, `energy_summary`; reports.py (energy report) |
| **API** | GET /energy-stats, GET /energy-stats/summary |
| **Frontend usage** | EnergyConsumptionChart.tsx, DashboardKPIs.tsx, RoomPowerEnergy.tsx |
| **Rows (live)** | 72 |
| **All columns** (7; NN = NOT NULL) | `device_name` varchar NN, `facility_id` uuid NN, `amenity_id` uuid NN, `hour` int8 NN, `energy_consumed` float8 NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [reporting.py:18](../backend/app/models/reporting.py#L18) `EnergyStat` · [migration:1077](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1077) |

#### `other_device`

| | |
|---|---|
| **Purpose** | Third-party meter readings (voltage/current/power/energy); no FK, keyed by device_name text. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | `(legacy_id)` |
| **Important columns** | `msg_id`, `device_name`, `voltage`, `current`, `power`, `power_factor`, `all_energy`, `thirty_day_energy` |
| **Depends on** | — |
| **Depended on by** | — |
| **Business process** | Energy |
| **Backend usage** | telemetry.py `list_other_device_readings` |
| **API** | GET /other-device-readings[/{id}] |
| **Frontend usage** | None (`useOtherDeviceReadings` unused) |
| **Rows (live)** | 12 |
| **All columns** (17; NN = NOT NULL) | `msg_id` varchar, `device_name` varchar, `voltage` float8, `current` float8, `power` float8, `power_factor` float8, `all_energy` float8, `thirty_day_energy` float8, `today_energy` float8, `current_hour_energy` float8, `ec` float8, `msg_string` jsonb, `timestamp` timestamptz NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [device.py:359](../backend/app/models/device.py#L359) `OtherDevice` · [migration:228](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L228) |


### 2.9 Dashboard / Reporting

#### `daily_dual_data_point`

| | |
|---|---|
| **Purpose** | Daily KPI numerator/denominator per metric type (smart room, service request, checkout, booking, guest room). |
| **Category** | Audit / History |
| **Primary key** | `metric_date, metric_type` |
| **Foreign keys** | `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `metric_date`, `metric_type`, `dp_1`, `dp_2` |
| **Depends on** | `facility` |
| **Depended on by** | — |
| **Business process** | Dashboard / Reporting |
| **Backend usage** | energy.py `list_daily_data_points`, `caleido_at_work`, `get_daily_data_point` |
| **API** | GET /daily-data-points, …/summary, …/{metric_date}/{metric_type} |
| **Frontend usage** | CaleidoAtWork.tsx |
| **Rows (live)** | 35 |
| **All columns** (7; NN = NOT NULL) | `metric_date` date NN, `metric_type` daily_metric_type NN, `dp_1` numeric NN, `dp_2` numeric NN, `facility_id` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [reporting.py:53](../backend/app/models/reporting.py#L53) `DailyDualDataPoint` · [migration:590](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L590) |


### 2.10 Alerts & Incidents

#### `alert_type`

| | |
|---|---|
| **Purpose** | 16 alert types (BatteryLow, DoorAjar, HubOffline…). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `device_alert`, `device_incident` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py list/get/counts |
| **API** | GET /alert-types[/{id}] |
| **Frontend usage** | None directly (Reports filter options) |
| **Rows (live)** | 16 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [alert.py:41](../backend/app/models/alert.py#L41) `AlertType` · [migration:71](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L71) |

#### `device_alert`

| | |
|---|---|
| **Purpose** | Raw device alert stream. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `alert_type` → `alert_type.id` (on delete cascade); `amenity_id` → `amenity.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `device_id` → `device.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `alert_severity`, `alert_data` |
| **Depends on** | `alert_type`, `amenity`, `app_user`, `device` |
| **Depended on by** | `device_incident` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py `list_alerts`, `get_alert`; reports.py |
| **API** | GET /alerts[/{id}], GET /alerts/{id}/incidents |
| **Frontend usage** | AlertsPanel.tsx, DashboardKPIs.tsx |
| **Rows (live)** | 9 |
| **All columns** (10; NN = NOT NULL) | `device_id` uuid NN, `amenity_id` uuid NN, `alert_type` int2 NN, `alert_severity` alert_severity, `alert_data` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [alert.py:84](../backend/app/models/alert.py#L84) `DeviceAlert` · [migration:1256](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1256) |

#### `device_incident`

| | |
|---|---|
| **Purpose** | Assignable incident case raised from alerts. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `alert_type` → `alert_type.id` (on delete cascade); `amenity_id` → `amenity.id` (on delete cascade); `assigned_to` → `app_user.id` (on delete restrict); `current_incident_status` → `incident_status.id` (on delete cascade); `device_id` → `device.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `latest_alert_id` → `device_alert.id` (on delete cascade); `updated_by` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `subject`, `description` |
| **Depends on** | `alert_type`, `amenity`, `app_user`, `device`, `device_alert`, `facility`, `incident_status` |
| **Depended on by** | `incident_history` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py `list_incidents`, `get_incident`; devices_write.py `update_incident` |
| **API** | GET /incidents[/{id}], PATCH /incidents/{id} |
| **Frontend usage** | DashboardKPIs.tsx (counts only; no PATCH caller) |
| **Rows (live)** | 5 |
| **All columns** (14; NN = NOT NULL) | `facility_id` uuid NN, `amenity_id` uuid NN, `device_id` uuid NN, `alert_type` int2 NN, `subject` varchar, `description` text, `assigned_to` uuid, `latest_alert_id` int8, `current_incident_status` int2, `updated_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [alert.py:120](../backend/app/models/alert.py#L120) `DeviceIncident` · [migration:1563](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1563) |

#### `incident_event`

| | |
|---|---|
| **Purpose** | Incident event lookup: Unread, Read, Assigned, Resolved, Reopened. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `incident_history` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py; devices_write.py |
| **API** | None of its own |
| **Frontend usage** | None found |
| **Rows (live)** | 5 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [alert.py:71](../backend/app/models/alert.py#L71) `IncidentEvent` · [migration:153](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L153) |

#### `incident_history`

| | |
|---|---|
| **Purpose** | Audit trail of incident status events. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `incident_event_id` → `incident_event.id` (on delete cascade); `incident_id` → `device_incident.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `incident_event_data` |
| **Depends on** | `app_user`, `device_incident`, `incident_event` |
| **Depended on by** | — |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py `incident_history`; devices_write.py `update_incident` (insert on status change) |
| **API** | Inside GET/PATCH /incidents/{id} |
| **Frontend usage** | None found |
| **Rows (live)** | 14 |
| **All columns** (8; NN = NOT NULL) | `incident_id` uuid NN, `incident_event_id` int2 NN, `incident_event_data` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [alert.py:180](../backend/app/models/alert.py#L180) `IncidentHistory` · [migration:1667](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1667) |

#### `incident_status`

| | |
|---|---|
| **Purpose** | Incident status lookup: Unread, Read, Assigned, Resolved. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `device_incident` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py; devices_write.py |
| **API** | None of its own |
| **Frontend usage** | None found |
| **Rows (live)** | 4 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [alert.py:59](../backend/app/models/alert.py#L59) `IncidentStatus` · [migration:160](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L160) |

#### `value_alert`

| | |
|---|---|
| **Purpose** | Threshold breach raised against a limit config. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `device_id` → `device.id` (on delete restrict); `device_type_id` → `device_type.id` (on delete restrict); `facility_id` → `facility.id` (on delete restrict); `limit_config_id` → `value_alert_limit_config.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `device_name`, `device_status_id`, `timestamp`, `limit_value`, `limit_type`, `description`, `status` |
| **Depends on** | `amenity`, `device`, `device_type`, `facility`, `value_alert_limit_config` |
| **Depended on by** | — |
| **Business process** | Alerts & Incidents |
| **Backend usage** | alert.py `list_value_alerts`, `get_value_alert` |
| **API** | GET /value-alerts[/{id}] |
| **Frontend usage** | DashboardKPIs.tsx |
| **Rows (live)** | 3 |
| **All columns** (16; NN = NOT NULL) | `device_id` uuid NN, `device_type_id` int2 NN, `device_name` varchar NN, `amenity_id` uuid NN, `limit_config_id` uuid NN, `device_status_id` int4 NN, `timestamp` timestamptz NN, `limit_value` varchar NN, `limit_type` varchar NN, `description` text NN, `status` int2 NN, `facility_id` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [alert.py:253](../backend/app/models/alert.py#L253) `ValueAlert` · [migration:1636](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1636) |

#### `value_alert_limit_config`

| | |
|---|---|
| **Purpose** | Per device-name / parameter threshold configuration. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | `device_id` → `device.id` (on delete restrict); `facility_id` → `facility.id` (on delete restrict) |
| **Unique** | `(device_name, parameter, facility_id)`, `(legacy_id)` |
| **Important columns** | `parameter`, `device_name`, `limit_check`, `is_percentage_value`, `nominal`, `limit_low_percentage`, `limit_high_percentage`, `limit_low_value` |
| **Depends on** | `device`, `facility` |
| **Depended on by** | `value_alert` |
| **Business process** | Alerts & Incidents |
| **Backend usage** | limit_config.py; devices_write.py `create_limit_config`, `update_limit_config` |
| **API** | GET/POST /limit-configs, PATCH /limit-configs/{id} |
| **Frontend usage** | LimitConfigAlert.tsx |
| **Rows (live)** | 4 |
| **All columns** (16; NN = NOT NULL) | `parameter` varchar NN, `device_name` varchar NN, `device_id` uuid, `limit_check` bpchar NN, `is_percentage_value` bpchar NN, `nominal` int4, `limit_low_percentage` int4, `limit_high_percentage` int4, `limit_low_value` int4, `limit_high_value` int4, `remarks` text NN, `facility_id` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [alert.py:207](../backend/app/models/alert.py#L207) `ValueAlertLimitConfig` · [migration:1512](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1512) |


### 2.11 User / Staff / Guest

#### `app_user`

| | |
|---|---|
| **Purpose** | Single identity table for guests and staff (`is_staff`), including login fields (user_name, password_hash). Referenced by 51 tables. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `country` → `country.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `department_id` → `department.id` (on delete restrict); `job_function_id` → `job_function.id` (on delete restrict); `nationality` → `country.id` (on delete restrict); `supervisor` → `app_user.id` (on delete restrict) |
| **Unique** | `(legacy_id)`, `(user_name)`, `(user_uid)` |
| **Important columns** | `user_uid`, `first_name`, `last_name`, `email`, `phone_number`, `alternate_phone_number`, `gender`, `dob` |
| **Depends on** | `country`, `department`, `job_function` |
| **Depended on by** | `access_key`, `activity`, `activity_notifier`, `amenity`, `amenity_type`, `app_user`, `attachment`, `department`, `device`, `device_alert`, `device_command`, `device_incident`, `facility`, `facility_event`, `facility_user`, `feature`, `firmware`, `import_job`, `incident_history`, `invoice`, `job_function`, `job_order`, `lock_activity_log`, `maintenance_request`, `maintenance_request_amenity`, `maintenance_request_assignee`, `notification_receiver`, `occasion`, `organisation`, `package`, `package_feature`, `promo_code`, `promo_code_amenity`, `property`, `property_chain`, `role`, `room_allocation`, `room_service_request`, `service_category`, `service_category_item`, `service_request`, `service_request_item`, `stay`, `stay_user`, `sub_package`, `user_device`, `user_device_acl`, `user_document`, `user_role`, `user_token` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | auth.py `authenticate`; access.py list/get; access_write.py `create_user`, `update_user`, `set_user_password`, `deactivate_user`, `reactivate_user` |
| **API** | POST /auth/login, GET /auth/me, GET/POST /users, GET/PATCH /users/{id}, POST /users/{id}/password\|deactivate\|reactivate |
| **Frontend usage** | Login.tsx, Employees.tsx, Bookings.tsx (guest create), Tickets.tsx |
| **Rows (live)** | 15 |
| **All columns** (29; NN = NOT NULL) | `user_uid` varchar NN, `first_name` varchar NN, `last_name` varchar, `email` varchar, `country` int2, `phone_number` varchar NN, `alternate_phone_number` varchar, `gender` gender, `dob` date, `is_child` int2 NN, `age` int2, `is_staff` int2, `date_of_joining` timestamptz, `date_of_termination` timestamptz, `supervisor` uuid, `address` varchar, `nationality` int2, `marital_status` marital_status, `job_function_id` uuid, `department_id` uuid, `emp_id` varchar, `user_name` varchar, `password_hash` varchar, `metadata` jsonb, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:30](../backend/app/models/people.py#L30) `AppUser` · [migration:366](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L366) |

#### `country`

| | |
|---|---|
| **Purpose** | Country / phone-code lookup (239 rows). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name`, `phone_code`, `iso_code`, `nice_name`, `iso3`, `num_code` |
| **Depends on** | — |
| **Depended on by** | `app_user` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | None (only the integer FK on app_user is projected) |
| **API** | None |
| **Frontend usage** | None (Bookings hardcodes country codes) |
| **Rows (live)** | 239 |
| **All columns** (9; NN = NOT NULL) | `name` varchar NN, `phone_code` varchar NN, `iso_code` varchar, `nice_name` varchar NN, `iso3` varchar, `num_code` int2, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [facility.py:226](../backend/app/models/facility.py#L226) `Country` · [migration:106](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L106) |

#### `department`

| | |
|---|---|
| **Purpose** | Staff department per facility. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `department_name`, `status`, `department_key` |
| **Depends on** | `app_user`, `facility` |
| **Depended on by** | `app_user`, `maintenance_request`, `service_request` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; access_write.py create/update; maintenance.py; service.py |
| **API** | GET/POST /departments, PATCH /departments/{id} |
| **Frontend usage** | Employees.tsx, Tickets.tsx |
| **Rows (live)** | 5 |
| **All columns** (9; NN = NOT NULL) | `department_name` varchar NN, `facility_id` uuid NN, `status` int2, `department_key` department_key, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:249](../backend/app/models/people.py#L249) `Department` · [migration:602](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L602) |

#### `facility_user`

| | |
|---|---|
| **Purpose** | Facility membership of a user. |
| **Category** | Configuration |
| **Primary key** | `facility_id, app_user_id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `status` |
| **Depends on** | `app_user`, `facility` |
| **Depended on by** | — |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py `user_facility_ids` (read only; never written by app) |
| **API** | Exposed as facility_ids in /auth/me, /users/{id} |
| **Frontend usage** | AuthContext.tsx |
| **Rows (live)** | 13 |
| **All columns** (6; NN = NOT NULL) | `facility_id` uuid NN, `app_user_id` uuid NN, `status` int2, `created_by` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [facility.py:92](../backend/app/models/facility.py#L92) `FacilityUser` · [migration:641](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L641) |

#### `job_function`

| | |
|---|---|
| **Purpose** | Staff job function per facility. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `function_name`, `status`, `function_key` |
| **Depends on** | `app_user`, `facility` |
| **Depended on by** | `app_user` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; access_write.py create/update |
| **API** | GET/POST /job-functions, PATCH /job-functions/{id} |
| **Frontend usage** | Employees.tsx |
| **Rows (live)** | 5 |
| **All columns** (9; NN = NOT NULL) | `function_name` varchar NN, `facility_id` uuid, `status` int2, `function_key` function_key, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:270](../backend/app/models/people.py#L270) `JobFunction` · [migration:697](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L697) |

#### `role`

| | |
|---|---|
| **Purpose** | Named role per facility; `role_type` (admin/manager/staff/guest/system_user) gates HMS Web login. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `description`, `role_type`, `status` |
| **Depends on** | `app_user`, `facility` |
| **Depended on by** | `activity_role_association`, `role_module_permission`, `user_role` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; access_write.py `create_role`, `update_role`; auth.py |
| **API** | GET/POST /roles, GET/PATCH /roles/{id} |
| **Frontend usage** | UserRoles.tsx |
| **Rows (live)** | 7 |
| **All columns** (10; NN = NOT NULL) | `facility_id` uuid NN, `name` varchar NN, `description` varchar, `role_type` role_type NN, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:149](../backend/app/models/people.py#L149) `Role` · [migration:788](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L788) |

#### `role_module`

| | |
|---|---|
| **Purpose** | Registry of the 18 permission modules. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `module_name`, `read_applicable`, `write_applicable` |
| **Depends on** | — |
| **Depended on by** | `role_module_permission` |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; auth.py `module_names` |
| **API** | GET /modules[/{id}] |
| **Frontend usage** | UserRoles.tsx; mirrored in core/rbac/modules.ts |
| **Rows (live)** | 18 |
| **All columns** (6; NN = NOT NULL) | `module_name` varchar NN, `read_applicable` bool, `write_applicable` bool, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [people.py:209](../backend/app/models/people.py#L209) `RoleModule` · [migration:273](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L273) |

#### `role_module_permission`

| | |
|---|---|
| **Purpose** | Read/write grant per role × module. |
| **Category** | Configuration |
| **Primary key** | `role_id, module_id` |
| **Foreign keys** | `module_id` → `role_module.id` (on delete restrict); `role_id` → `role.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | `read_access`, `write_access` |
| **Depends on** | `role`, `role_module` |
| **Depended on by** | — |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; access_write.py `replace_role_permissions`; deps.py enforcement |
| **API** | GET /permissions, GET/PUT /roles/{id}/permissions |
| **Frontend usage** | UserRoles.tsx, AuthContext.tsx |
| **Rows (live)** | 65 |
| **All columns** (6; NN = NOT NULL) | `role_id` uuid NN, `module_id` int2 NN, `read_access` bool NN, `write_access` bool, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [people.py:226](../backend/app/models/people.py#L226) `RoleModulePermission` · [migration:902](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L902) |

#### `user_role`

| | |
|---|---|
| **Purpose** | Role held by a user at a facility. |
| **Category** | Configuration |
| **Primary key** | `facility_id, app_user_id, role_id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `created_by` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `role_id` → `role.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | — |
| **Depends on** | `app_user`, `facility`, `role` |
| **Depended on by** | — |
| **Business process** | User / Staff / Guest |
| **Backend usage** | access.py; access_write.py (replace on user write); auth.py |
| **API** | Inside POST/PATCH /users (`role_ids`) |
| **Frontend usage** | Employees.tsx |
| **Rows (live)** | 14 |
| **All columns** (6; NN = NOT NULL) | `facility_id` uuid NN, `app_user_id` uuid NN, `role_id` uuid NN, `created_by` uuid, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [people.py:177](../backend/app/models/people.py#L177) `UserRole` · [migration:914](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L914) |


### 2.12 Access / Keys

#### `access_key`

| | |
|---|---|
| **Purpose** | Issued digital door keys (app/keypad). |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `device_id` → `device.id` (on delete cascade); `key_type` → `key_type.id` (on delete restrict); `maintenance_request_id` → `maintenance_request.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade); `user_device_acl_id` → `user_device_acl.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `app_key`, `keypad_key`, `status` |
| **Depends on** | `app_user`, `device`, `key_type`, `maintenance_request`, `stay`, `user_device_acl` |
| **Depended on by** | — |
| **Business process** | Access / Keys |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 5 |
| **All columns** (13; NN = NOT NULL) | `user_device_acl_id` uuid, `app_key` varchar NN, `keypad_key` varchar NN, `key_type` int2 NN, `device_id` uuid, `stay_id` uuid, `maintenance_request_id` uuid, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [access.py:40](../backend/app/models/access.py#L40) `AccessKey` · [migration:1537](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1537) |

#### `key_type`

| | |
|---|---|
| **Purpose** | Key type lookup: Primary, Shared, Staff, Default. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `name` |
| **Depends on** | — |
| **Depended on by** | `access_key`, `lock_activity_log` |
| **Business process** | Access / Keys |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 4 |
| **All columns** (4; NN = NOT NULL) | `name` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [access.py:28](../backend/app/models/access.py#L28) `KeyType` · [migration:189](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L189) |

#### `lock_activity_log`

| | |
|---|---|
| **Purpose** | Door lock/unlock event log. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete cascade); `app_user_id` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `key_type` → `key_type.id` (on delete restrict); `lock_id` → `device.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `timestamp`, `event`, `unlock_mode` |
| **Depends on** | `amenity`, `app_user`, `device`, `facility`, `key_type`, `stay` |
| **Depended on by** | — |
| **Business process** | Access / Keys |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 5 |
| **All columns** (13; NN = NOT NULL) | `timestamp` timestamptz NN, `app_user_id` uuid, `event` lock_event, `unlock_mode` lock_unlock_mode, `lock_id` uuid NN, `amenity_id` uuid NN, `stay_id` uuid, `facility_id` uuid NN, `key_type` int2, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [access.py:138](../backend/app/models/access.py#L138) `LockActivityLog` · [migration:1349](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1349) |

#### `user_device`

| | |
|---|---|
| **Purpose** | User mobile device & push token. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade); `user_token_id` → `user_token.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `mobile_model`, `mobile_os`, `device_token`, `is_mobile_token`, `status` |
| **Depends on** | `app_user`, `stay`, `user_token` |
| **Depended on by** | — |
| **Business process** | Access / Keys |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 4 |
| **All columns** (12; NN = NOT NULL) | `app_user_id` uuid NN, `mobile_model` varchar, `mobile_os` varchar, `device_token` varchar, `is_mobile_token` bool, `user_token_id` uuid, `stay_id` uuid, `status` int2, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:124](../backend/app/models/people.py#L124) `UserDevice` · [migration:513](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L513) |

#### `user_device_acl`

| | |
|---|---|
| **Purpose** | Time-boxed device access grant (user × device × stay). |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete cascade); `amenity_type_id` → `amenity_type.id` (on delete cascade); `app_user_id` → `app_user.id` (on delete cascade); `created_by` → `app_user.id` (on delete cascade); `device_id` → `device.id` (on delete cascade); `device_type_id` → `device_type.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `start_time`, `end_time`, `status_id` |
| **Depends on** | `amenity`, `amenity_type`, `app_user`, `device`, `device_type`, `stay` |
| **Depended on by** | `access_key` |
| **Business process** | Access / Keys |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 5 |
| **All columns** (14; NN = NOT NULL) | `app_user_id` uuid NN, `device_type_id` int2 NN, `device_id` uuid NN, `amenity_type_id` uuid NN, `amenity_id` uuid NN, `stay_id` uuid, `start_time` timestamptz NN, `end_time` timestamptz NN, `status_id` int2 NN, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [access.py:86](../backend/app/models/access.py#L86) `UserDeviceAcl` · [migration:1482](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1482) |

#### `user_token`

| | |
|---|---|
| **Purpose** | API session tokens. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade) |
| **Unique** | `(legacy_id)`, `(token)` |
| **Important columns** | `token`, `is_expired`, `expired_on` |
| **Depends on** | `app_user` |
| **Depended on by** | `user_device` |
| **Business process** | Access / Keys |
| **Backend usage** | None (JWT is stateless) |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 3 |
| **All columns** (8; NN = NOT NULL) | `token` varchar NN, `app_user_id` uuid NN, `is_expired` bool, `expired_on` timestamptz, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [people.py:107](../backend/app/models/people.py#L107) `UserToken` · [migration:340](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L340) |


### 2.13 Notifications & Activity

#### `activity`

| | |
|---|---|
| **Purpose** | In-app activity feed event (polymorphic entity_id). |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `activity_type_id` → `activity_type.id` (on delete cascade); `actor_id` → `app_user.id` (on delete cascade); `entity_type_id` → `entity_type.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `stay_id` → `stay.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `entity_id`, `activity_response_ids`, `data_version`, `data` |
| **Depends on** | `activity_type`, `app_user`, `entity_type`, `facility`, `stay` |
| **Depended on by** | `activity_notifier` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py `list_activities`, `get_activity` (read only; nothing creates rows) |
| **API** | GET /activities[/{id}] |
| **Frontend usage** | RecentActivityPanel.tsx |
| **Rows (live)** | 10 |
| **All columns** (13; NN = NOT NULL) | `activity_type_id` int2 NN, `entity_type_id` int2 NN, `entity_id` int8 NN, `facility_id` uuid NN, `actor_id` uuid NN, `stay_id` uuid, `activity_response_ids` text, `data_version` int2 NN, `data` jsonb NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [activity.py:76](../backend/app/models/activity.py#L76) `Activity` · [migration:549](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L549) |

#### `activity_notifier`

| | |
|---|---|
| **Purpose** | Per-user delivery / read state of an activity. |
| **Category** | Transaction / Operational |
| **Primary key** | `activity_id, app_user_id` |
| **Foreign keys** | `activity_id` → `activity.id` (on delete cascade); `app_user_id` → `app_user.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `status`, `user_type`, `notification_type` |
| **Depends on** | `activity`, `app_user` |
| **Depended on by** | — |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py `activity_notifiers` and filters |
| **API** | Inside /activities |
| **Frontend usage** | RecentActivityPanel.tsx |
| **Rows (live)** | 15 |
| **All columns** (7; NN = NOT NULL) | `activity_id` int8 NN, `app_user_id` uuid NN, `status` activity_notifier_status NN, `user_type` activity_notifier_user_type, `notification_type` int2, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [activity.py:116](../backend/app/models/activity.py#L116) `ActivityNotifier` · [migration:824](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L824) |

#### `activity_role_association`

| | |
|---|---|
| **Purpose** | Which roles are notified of which activity types. |
| **Category** | Configuration |
| **Primary key** | `activity_type_id, role_id` |
| **Foreign keys** | `activity_type_id` → `activity_type.id` (on delete restrict); `role_id` → `role.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | — |
| **Depends on** | `activity_type`, `role` |
| **Depended on by** | — |
| **Business process** | Notifications & Activity |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 34 |
| **All columns** (4; NN = NOT NULL) | `activity_type_id` int2 NN, `role_id` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [activity.py:144](../backend/app/models/activity.py#L144) `ActivityRoleAssociation` · [migration:839](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L839) |

#### `activity_type`

| | |
|---|---|
| **Purpose** | Activity taxonomy (22 types). |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | `entity_type_id` → `entity_type.id` (on delete cascade) |
| **Unique** | None beyond PK |
| **Important columns** | `activity_type`, `notification_type`, `is_subscribable` |
| **Depends on** | `entity_type` |
| **Depended on by** | `activity`, `activity_role_association` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py (joined) |
| **API** | Inside /activities |
| **Frontend usage** | RecentActivityPanel.tsx |
| **Rows (live)** | 22 |
| **All columns** (7; NN = NOT NULL) | `activity_type` varchar NN, `entity_type_id` int2 NN, `notification_type` bpchar NN, `is_subscribable` bool, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [activity.py:58](../backend/app/models/activity.py#L58) `ActivityType` · [migration:354](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L354) |

#### `entity_type`

| | |
|---|---|
| **Purpose** | Entity lookup: Booking, Occupancy, Service Requests, Maintenance Requests, Default Key. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `entity_type` |
| **Depends on** | — |
| **Depended on by** | `activity`, `activity_type` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py (joined) |
| **API** | Inside /activities |
| **Frontend usage** | RecentActivityPanel.tsx |
| **Rows (live)** | 5 |
| **All columns** (4; NN = NOT NULL) | `entity_type` varchar NN, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [activity.py:45](../backend/app/models/activity.py#L45) `EntityType` · [migration:127](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L127) |

#### `notification`

| | |
|---|---|
| **Purpose** | Notification dispatch queue entry. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `template_id` → `notification_template.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `status`, `reference_id`, `params` |
| **Depends on** | `notification_template` |
| **Depended on by** | `notification_receiver` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py `list_notifications`, `get_notification` (read only) |
| **API** | GET /notifications[/{id}] |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (9; NN = NOT NULL) | `created_by` varchar NN, `status` notification_status NN, `reference_id` int8, `template_id` uuid, `params` jsonb, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [activity.py:178](../backend/app/models/activity.py#L178) `Notification` · [migration:480](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L480) |

#### `notification_receiver`

| | |
|---|---|
| **Purpose** | Recipient of a notification. |
| **Category** | Transaction / Operational |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete restrict); `notification_id` → `notification.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `email`, `phone`, `device_token`, `data` |
| **Depends on** | `app_user`, `notification` |
| **Depended on by** | `notification_result` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py `notification_receivers` |
| **API** | Inside GET /notifications/{id} |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (11; NN = NOT NULL) | `app_user_id` uuid, `notification_id` int8 NN, `name` varchar NN, `email` varchar, `phone` varchar, `device_token` varchar, `data` jsonb, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [activity.py:203](../backend/app/models/activity.py#L203) `NotificationReceiver` · [migration:729](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L729) |

#### `notification_result`

| | |
|---|---|
| **Purpose** | Per-channel delivery outcome. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `receiver_id` → `notification_receiver.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `type`, `status`, `log`, `body` |
| **Depends on** | `notification_receiver` |
| **Depended on by** | — |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py |
| **API** | Inside GET /notifications/{id} |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (9; NN = NOT NULL) | `receiver_id` int8 NN, `type` notification_channel NN, `status` varchar NN, `log` jsonb, `body` text, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [activity.py:228](../backend/app/models/activity.py#L228) `NotificationResult` · [migration:849](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L849) |

#### `notification_template`

| | |
|---|---|
| **Purpose** | Notification template per channel. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | `(legacy_id)`, `(name, type)` |
| **Important columns** | `name`, `type`, `path` |
| **Depends on** | — |
| **Depended on by** | `notification` |
| **Business process** | Notifications & Activity |
| **Backend usage** | notification.py `list_templates`, `get_template` |
| **API** | GET /notification-templates[/{id}] |
| **Frontend usage** | UserRoles.tsx (picker; selection never saved) |
| **Rows (live)** | 16 |
| **All columns** (7; NN = NOT NULL) | `name` varchar NN, `type` notification_channel NN, `path` varchar NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [activity.py:163](../backend/app/models/activity.py#L163) `NotificationTemplate` · [migration:196](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L196) |


### 2.14 Marketing (Offers)

#### `promo_code`

| | |
|---|---|
| **Purpose** | Offer / discount coupon. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `promo_code_icon` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)`, `(promo_code)` |
| **Important columns** | `offer_name`, `promo_code`, `start_time`, `expiry_time`, `discount_percentage`, `max_discount_value`, `min_order_value`, `promo_code_description` |
| **Depends on** | `app_user`, `attachment` |
| **Depended on by** | `promo_code_amenity`, `service_request` |
| **Business process** | Marketing (Offers) |
| **Backend usage** | catalog.py `list_promo_codes`, `get_promo_code`; facility_write.py create/update; services_write.py (FK check) |
| **API** | GET/POST /offers, PATCH /offers/{id} |
| **Frontend usage** | Offers.tsx |
| **Rows (live)** | 3 |
| **All columns** (16; NN = NOT NULL) | `offer_name` varchar, `promo_code` varchar NN, `start_time` timestamptz, `expiry_time` timestamptz, `discount_percentage` int2, `max_discount_value` numeric, `min_order_value` numeric, `promo_code_icon` uuid, `promo_code_description` varchar, `offered_by` varchar, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [marketing.py:26](../backend/app/models/marketing.py#L26) `PromoCode` · [migration:250](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L250) |

#### `promo_code_amenity`

| | |
|---|---|
| **Purpose** | Rooms an offer applies to. |
| **Category** | Configuration |
| **Primary key** | `promo_code_id, amenity_id` |
| **Foreign keys** | `amenity_id` → `amenity.id` (on delete restrict); `created_by` → `app_user.id` (on delete restrict); `promo_code_id` → `promo_code.id` (on delete restrict) |
| **Unique** | None beyond PK |
| **Important columns** | `status` |
| **Depends on** | `amenity`, `app_user`, `promo_code` |
| **Depended on by** | — |
| **Business process** | Marketing (Offers) |
| **Backend usage** | catalog.py; facility_write.py (delete + insert) |
| **API** | Inside /offers (`amenity_ids`) |
| **Frontend usage** | Offers.tsx |
| **Rows (live)** | 8 |
| **All columns** (6; NN = NOT NULL) | `promo_code_id` uuid NN, `amenity_id` uuid NN, `status` int2, `created_by` uuid NN, `created_on` timestamptz NN, `updated_on` timestamptz NN |
| **Evidence** | [marketing.py:66](../backend/app/models/marketing.py#L66) `PromoCodeAmenity` · [migration:1101](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L1101) |


### 2.15 Marketing (Events)

#### `facility_event`

| | |
|---|---|
| **Purpose** | Hotel event (venue, dates, attendees, cancellation). |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete restrict); `facility_id` → `facility.id` (on delete cascade); `image_id` → `attachment.id` (on delete restrict) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `name`, `venue`, `chief_guests`, `description`, `expected_attendees`, `interested_attendees`, `start_date_time`, `end_date_time` |
| **Depends on** | `app_user`, `attachment`, `facility` |
| **Depended on by** | — |
| **Business process** | Marketing (Events) |
| **Backend usage** | catalog.py `list_events`; facility_write.py create/update |
| **API** | GET/POST /events, PATCH /events/{id} |
| **Frontend usage** | Events.tsx |
| **Rows (live)** | 3 |
| **All columns** (17; NN = NOT NULL) | `facility_id` uuid NN, `name` varchar NN, `venue` varchar, `chief_guests` varchar, `description` text, `expected_attendees` int2, `interested_attendees` int2, `start_date_time` timestamptz, `end_date_time` timestamptz, `image_id` uuid, `cancellation_reason` text, `status` int2, `created_by` uuid NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [marketing.py:90](../backend/app/models/marketing.py#L90) `FacilityEvent` · [migration:617](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L617) |


### 2.16 Holiday Management

#### `occasion`

| | |
|---|---|
| **Purpose** | Holidays and other occasions (festival, birthday, anniversary) with dates, repeat flag, hub notification. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `app_user_id` → `app_user.id` (on delete cascade); `created_by` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade); `occasion_type` → `occasion_type.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `occasion_name`, `is_repeatable`, `notification_template`, `month`, `day_of_month`, `notify_to_hub`, `occasion_start_date`, `occasion_end_date` |
| **Depends on** | `app_user`, `facility`, `occasion_type` |
| **Depended on by** | — |
| **Business process** | Holiday Management |
| **Backend usage** | catalog.py `list_occasions`, `get_occasion`; facility_write.py `create_occasion`, `update_occasion` |
| **API** | GET/POST /holidays, PATCH /holidays/{occasion_id} |
| **Frontend usage** | Holidays.tsx |
| **Rows (live)** | 4 |
| **All columns** (17; NN = NOT NULL) | `occasion_name` varchar, `occasion_type` int2 NN, `is_repeatable` bool, `notification_template` text, `facility_id` uuid, `month` int2 NN, `day_of_month` int2 NN, `app_user_id` uuid, `notify_to_hub` bool, `occasion_start_date` date NN, `occasion_end_date` date, `status` int2, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [marketing.py:141](../backend/app/models/marketing.py#L141) `Occasion` · [migration:747](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L747) |

#### `occasion_type`

| | |
|---|---|
| **Purpose** | Occasion type lookup: Festival, Birthday, Marriage anniversary, Holiday. |
| **Category** | Reference |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `occasion_type`, `notification_template` |
| **Depends on** | — |
| **Depended on by** | `occasion` |
| **Business process** | Holiday Management |
| **Backend usage** | catalog.py `list_occasion_types`; facility_write.py (validation) |
| **API** | GET /holidays/types |
| **Frontend usage** | Holidays.tsx |
| **Rows (live)** | 4 |
| **All columns** (5; NN = NOT NULL) | `occasion_type` varchar NN, `notification_template` text, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int2 NN |
| **Evidence** | [marketing.py:129](../backend/app/models/marketing.py#L129) `OccasionType` · [migration:208](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L208) |


### 2.17 Scheduler

#### `scheduler_job`

| | |
|---|---|
| **Purpose** | Scheduled / cron job definitions. |
| **Category** | Configuration |
| **Primary key** | `id` |
| **Foreign keys** | None |
| **Unique** | `(job_key)`, `(legacy_id)` |
| **Important columns** | `job_key`, `job_name`, `job_data`, `status`, `is_dynamic_job` |
| **Depends on** | — |
| **Depended on by** | `scheduler_job_execution` |
| **Business process** | Scheduler |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 5 |
| **All columns** (9; NN = NOT NULL) | `job_key` varchar NN, `job_name` varchar NN, `job_data` jsonb, `status` scheduler_job_status NN, `is_dynamic_job` int2 NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [scheduler.py:22](../backend/app/models/scheduler.py#L22) `SchedulerJob` · [migration:282](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L282) |

#### `scheduler_job_execution`

| | |
|---|---|
| **Purpose** | Scheduler run history. |
| **Category** | Audit / History |
| **Primary key** | `id` |
| **Foreign keys** | `scheduler_job_id` → `scheduler_job.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `job_execution_date`, `job_response`, `status`, `job_run_duration` |
| **Depends on** | `scheduler_job` |
| **Depended on by** | — |
| **Business process** | Scheduler |
| **Backend usage** | None |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 6 |
| **All columns** (9; NN = NOT NULL) | `scheduler_job_id` uuid NN, `job_execution_date` timestamptz NN, `job_response` bytea, `status` scheduler_execution_status NN, `job_run_duration` int4 NN, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` int8 NN |
| **Evidence** | [scheduler.py:44](../backend/app/models/scheduler.py#L44) `SchedulerJobExecution` · [migration:497](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L497) |


### 2.18 Shared

#### `attachment`

| | |
|---|---|
| **Purpose** | File registry (file name/path) referenced as image/document by 10 tables. |
| **Category** | Master |
| **Primary key** | `id` |
| **Foreign keys** | `created_by` → `app_user.id` (on delete cascade); `facility_id` → `facility.id` (on delete cascade) |
| **Unique** | `(legacy_id)` |
| **Important columns** | `file_name`, `file_path` |
| **Depends on** | `app_user`, `facility` |
| **Depended on by** | `amenity_type`, `facility`, `facility_event`, `invoice`, `package`, `promo_code`, `property_type`, `service_category`, `service_category_item`, `user_document` |
| **Business process** | Shared |
| **Backend usage** | None directly (only FK ids echoed) |
| **API** | None (no upload endpoint) |
| **Frontend usage** | None (upload inputs in UI have no handler) |
| **Rows (live)** | 8 |
| **All columns** (8; NN = NOT NULL) | `facility_id` uuid, `file_name` varchar NN, `file_path` varchar NN, `created_by` uuid, `legacy_id` int8, `created_on` timestamptz NN, `updated_on` timestamptz NN, `id` uuid NN |
| **Evidence** | [facility.py:208](../backend/app/models/facility.py#L208) `Attachment` · [migration:92](../backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L92) |


### 2.19 System

#### `alembic_version`

| | |
|---|---|
| **Purpose** | Alembic migration head marker (value `0e2687233b59`). |
| **Category** | Other |
| **Primary key** | `version_num` |
| **Foreign keys** | None |
| **Unique** | None beyond PK |
| **Important columns** | `version_num` |
| **Depends on** | — |
| **Depended on by** | — |
| **Business process** | System |
| **Backend usage** | Alembic only |
| **API** | None |
| **Frontend usage** | None found |
| **Rows (live)** | 1 |
| **All columns** (1; NN = NOT NULL) | `version_num` varchar NN |
| **Evidence** |  |


---

## 3. Table relationship analysis

Every relationship below comes from a **declared PostgreSQL foreign key** (all 240 are also declared in the ORM models). There are no relationships inferred from column names. Relationships that exist only in application logic, with no FK, are listed at the end.

**Many-to-many (junction tables whose composite PK is made of FKs):**

| Junction table | Connects | PK |
|---|---|---|
| `activity_notifier` | `activity` ↔ `app_user` | `activity_id, app_user_id` |
| `activity_role_association` | `activity_type` ↔ `role` | `activity_type_id, role_id` |
| `amenity_condition_status` | `amenity_condition` ↔ `amenity` | `amenity_id, amenity_condition_id` |
| `facility_user` | `app_user` ↔ `facility` | `facility_id, app_user_id` |
| `job_order_amenity` | `amenity` ↔ `job_order` | `job_order_id, amenity_id` |
| `job_order_device` | `device` ↔ `job_order` | `job_order_id, device_id` |
| `promo_code_amenity` | `amenity` ↔ `promo_code` | `promo_code_id, amenity_id` |
| `role_module_permission` | `role_module` ↔ `role` | `role_id, module_id` |
| `sub_package` | `package` ↔ `package` | `parent_package_id, sub_package_id` |
| `user_role` | `app_user` ↔ `facility` ↔ `role` | `facility_id, app_user_id, role_id` |

Associative tables with a surrogate `id` PK that behave as many-to-many links (FK pair, no uniqueness on the pair): `room_allocation` (stay ↔ amenity), `stay_user` (stay ↔ app_user), `package_feature` (package ↔ feature), `maintenance_request_amenity` (maintenance_request ↔ amenity), `maintenance_request_assignee` (maintenance_request ↔ app_user), `user_device_acl` (app_user ↔ device). The absence of a unique constraint on the pair is visible in §1/§2 (no UQ listed).

**One-to-one (FK column is also the PK or unique):**

- `maintenance_request` 1 ── 0..1 `maintenance_request_recurrence` (via `maintenance_request_recurrence.maintenance_request_id`)

**Self-references (parent/child hierarchies):**

- `amenity.parent_amenity_id` → `amenity.id`
- `app_user.created_by` → `app_user.id`
- `app_user.supervisor` → `app_user.id`
- `device.parent_device_id` → `device.id`
- `maintenance_request.parent_id` → `maintenance_request.id`

**One-to-many (every other FK). Parent `1 ── *` child, grouped by parent. Audit FKs (`created_by`/`updated_by`/`modified_by`/`uploaded_by` → app_user) are counted separately below.**

| Parent (PK side) | Children (FK column) |
|---|---|
| `facility` | `activity.facility_id`, `amenity.facility_id`, `amenity_type.facility_id`, `attachment.facility_id`, `daily_dual_data_point.facility_id`, `department.facility_id`, `device.facility_id`, `device_incident.facility_id`, `energy_stat.facility_id`, `facility_event.facility_id`, `feature.facility_id`, `invoice.facility_id`, `job_function.facility_id`, `lock_activity_log.facility_id`, `maintenance_request.facility_id`, `mqtt_broker.facility_id`, `occasion.facility_id`, `package.facility_id`, `property.facility_id`, `property_chain.facility_id`, `property_type.facility_id`, `role.facility_id`, `service_category.facility_id`, `service_category_item.facility_id`, `service_request.facility_id`, `value_alert.facility_id`, `value_alert_limit_config.facility_id` |
| `app_user` | `activity.actor_id`, `device_incident.assigned_to`, `facility.default_key_user`, `invoice.billing_user_id`, `job_order.assigned_to`, `lock_activity_log.app_user_id`, `maintenance_request_assignee.app_user_id`, `notification_receiver.app_user_id`, `occasion.app_user_id`, `room_service_request.assigned_to`, `service_request.app_user_id`, `service_request.assigned_to`, `service_request_item.assigned_to`, `stay.booking_user_id`, `stay.checkout_initiated_by`, `stay_user.app_user_id`, `user_device.app_user_id`, `user_device_acl.app_user_id`, `user_document.app_user_id`, `user_token.app_user_id` |
| `device` | `access_key.device_id`, `battery_life_stat.device_id`, `device_alert.device_id`, `device_command.device_id`, `device_current_stat.device_id`, `device_health_stat.device_id`, `device_incident.device_id`, `device_stat.device_id`, `lock_activity_log.lock_id`, `mqtt_topic.device_id`, `sensor_operation_stat.device_id`, `user_device_acl.device_id`, `value_alert.device_id`, `value_alert_limit_config.device_id` |
| `amenity` | `device.amenity_id`, `device_alert.amenity_id`, `device_incident.amenity_id`, `energy_stat.amenity_id`, `lock_activity_log.amenity_id`, `maintenance_request_amenity.amenity_id`, `room_allocation.room_id`, `room_service_request.guest_room_id`, `sensor_operation_stat.amenity_id`, `service_category_item.amenity_id`, `service_request.amenity_id`, `stay_user.room_id`, `user_device_acl.amenity_id`, `value_alert.amenity_id` |
| `stay` | `access_key.stay_id`, `activity.stay_id`, `invoice.stay_id`, `lock_activity_log.stay_id`, `room_allocation.stay_id`, `room_service_request.stay_id`, `service_request.stay_id`, `stay_package.stay_id`, `stay_user.stay_id`, `user_device.stay_id`, `user_device_acl.stay_id`, `user_document.stay_id` |
| `attachment` | `amenity_type.image_id`, `facility.facility_image_id`, `facility_event.image_id`, `invoice.facility_image_id`, `package.image_id`, `promo_code.promo_code_icon`, `property_type.property_type_image_id`, `service_category.category_icon`, `service_category_item.item_icon`, `user_document.attachment_id` |
| `device_type` | `command_type.device_type_id`, `device.device_type`, `device_param.device_type`, `feature.device_type`, `firmware.device_type_id`, `user_device_acl.device_type_id`, `value_alert.device_type_id` |
| `maintenance_request` | `access_key.maintenance_request_id`, `maintenance_request_amenity.maintenance_request_id`, `maintenance_request_assignee.maintenance_request_id`, `maintenance_request_recurrence.maintenance_request_id` |
| `package` | `amenity.package_id`, `package_feature.package_id`, `room_allocation.package_id`, `stay_package.package_id` |
| `service_category` | `maintenance_request.category_id`, `service_category_item.category_id`, `service_request.category_id`, `service_request_item.category_id` |
| `amenity_type` | `amenity.amenity_type_id`, `package.amenity_type`, `user_device_acl.amenity_type_id` |
| `department` | `app_user.department_id`, `maintenance_request.department_id`, `service_request.department_id` |
| `service_category_item` | `maintenance_request.item_id`, `room_service_request_item.service_category_item_id`, `service_request_item.item_id` |
| `service_status` | `maintenance_request.maintenance_request_status`, `service_request.status`, `service_request_item.status` |
| `property` | `property_chain.level_one_id`, `property_chain.level_three_id`, `property_chain.level_two_id` |
| `key_type` | `access_key.key_type`, `lock_activity_log.key_type` |
| `entity_type` | `activity.entity_type_id`, `activity_type.entity_type_id` |
| `country` | `app_user.country`, `app_user.nationality` |
| `firmware` | `device.current_firmware_version`, `device.expected_firmware_version` |
| `alert_type` | `device_alert.alert_type`, `device_incident.alert_type` |
| `service_type` | `service_category.service_type`, `service_request.service_type` |
| `user_device_acl` | `access_key.user_device_acl_id` |
| `activity_type` | `activity.activity_type_id` |
| `property_chain` | `amenity.property_chain_id` |
| `amenity_status` | `amenity.status` |
| `job_function` | `app_user.job_function_id` |
| `command_type` | `device_command.command_type` |
| `incident_status` | `device_incident.current_incident_status` |
| `device_alert` | `device_incident.latest_alert_id` |
| `device_param` | `device_stat.device_param_id` |
| `organisation` | `facility.org_id` |
| `incident_event` | `incident_history.incident_event_id` |
| `device_incident` | `incident_history.incident_id` |
| `mqtt_broker` | `mqtt_topic.mqtt_broker_id` |
| `notification_template` | `notification.template_id` |
| `notification` | `notification_receiver.notification_id` |
| `notification_receiver` | `notification_result.receiver_id` |
| `occasion_type` | `occasion.occasion_type` |
| `feature` | `package_feature.feature_id` |
| `property_type` | `property.property_type_id` |
| `room_service_request` | `room_service_request_item.room_service_request_id` |
| `scheduler_job` | `scheduler_job_execution.scheduler_job_id` |
| `promo_code` | `service_request.promo_code_id` |
| `service_request` | `service_request_item.service_request_id` |
| `user_token` | `user_device.user_token_id` |
| `value_alert_limit_config` | `value_alert.limit_config_id` |

Audit FKs to `app_user` (created_by/updated_by/modified_by/uploaded_by): **47** of the 240 FKs.

### 3.1 Key relationship chains (how the core entities hang together)

```
organisation 1──* facility 1──* property 1──* property_chain (level_one = building, level_two = floor)
                                                  │
property_type 1──* property                       1
                                                  *
amenity_type 1──* amenity *──1 package      amenity (room / restaurant / others)
amenity_status 1──* amenity                       │ 1
                                                  ├──* amenity_condition_status *──1 amenity_condition
                                                  ├──* room_allocation *──1 stay 1──* stay_user *──1 app_user (guest)
                                                  │                          ├──* invoice, stay_package, user_document
                                                  ├──* service_request *──1 service_type / service_status / service_category
                                                  ├──* maintenance_request_amenity *──1 maintenance_request
                                                  ├──* job_order_amenity *──1 job_order 1──* job_order_device *──1 device
                                                  └──* device (parent_device_id = hub) 1──* device_stat *──1 device_param
                                                                   ├──* device_alert 1──* device_incident 1──* incident_history
                                                                   └──* value_alert *──1 value_alert_limit_config
app_user *──* role (user_role, per facility);  role *──* role_module (role_module_permission)
occasion *──1 occasion_type;  promo_code *──* amenity (promo_code_amenity)
```

### 3.2 Relationships that exist only in application logic (no FK)

| Link | How the code joins | Evidence | Consequence |
|---|---|---|---|
| `stay` → `facility` | Through `room_allocation.room_id` → `amenity.facility_id` (EXISTS filter) | `backend/app/services/stay.py`, `list_stays` (:141) | A stay with no allocation belongs to no facility. |
| `job_order` → `facility` | `job_order.id IN (SELECT job_order_id FROM job_order_amenity JOIN amenity …)` | `backend/app/services/job_order.py`, `list_job_orders` (:78) | A job order with no rooms matches no facility filter. |
| `energy_stat.device_name` → `device` | None. Filtered and grouped as text only. | `backend/app/services/energy.py` `energy_summary` (:172); comment at energy.py:45-47 | **Live data:** 0 of 72 `energy_stat` rows match any `device.device_name` or `device_uid` (values look like `101-mik`). |
| `other_device.device_name` → `device` | None | `backend/app/services/telemetry.py` `list_other_device_readings` (:278) | Readings (`MAINS-EB-01`, `MAINS-DG-01`) are not tied to any device, room or facility. |
| `value_alert.device_status_id` | None (int4 with no target table) | `backend/app/models/alert.py` `ValueAlert` | Meaning cannot be verified. |
| `activity.entity_id` | Polymorphic (bigint), typed by `entity_type_id` | `backend/app/models/activity.py` `Activity` | No referential integrity is possible. |
| `notification.reference_id` | Polymorphic | `backend/app/models/activity.py` `Notification` | Same. |
| Status smallints (`property.status`, `feature.status`, `package.status`, `occasion.status`, `facility_event.status`, `promo_code.status`, `job_order.status`, `maintenance_request.status`, …) | 0/1 soft-delete flags validated only in Pydantic (`ge=0, le=1`, `backend/app/schemas/ops_write.py`) | — | No FK or CHECK constraint, so any smallint can be stored by non-API writers. |

---

## 4. HMS business process mapping

Processes are listed only when the repository contains them. "C / R / U / D" = create / read / update / delete.

### 4.1 Property / Hotel (facility)
- **Tables:** `facility` (the hotel), `organisation` (owner; unused), `attachment` (logo pointer; unused).
- **Data flow:** `facility` → `facility.py` `list_facilities` (:59) / `get_facility` (:68) → `GET /api/v1/facilities[/{id}]` (`endpoints/facilities.py:91,109`) → `useFacilities` (`hooks.ts:165`) → `FacilityManagement.tsx`, `KeySettings.tsx`.
- **C:** none (the facility is seeded). **R:** as above. **U:** `PATCH /facilities/{id}` (`endpoints/facility_write.py:109`) → `facility_write.update_facility`. No page calls it (`useUpdateFacility` is unused). **D:** none.

### 4.2 Building and Floor
- **Tables:** `property`, `property_type`, `property_chain`. There is **no building or floor table**. A building is a `property` referenced as `property_chain.level_one_id`, and a floor is one referenced as `level_two_id`. `level_three_id` is never surfaced.
- **Data flow:** `facility.py` `list_buildings` (:162) / `list_floors` (:214) → `GET /buildings`, `GET /floors` (`endpoints/facilities.py:171,215`) → `useBuildings` / `useFloors` (`hooks.ts:169,171`) → `Dashboard.tsx`, `StatusSection.tsx`, `Occupancy.tsx`, `RoomView.tsx`.
- **C/U/D:** none via API. **Observation:** the Facility Structure tree on `FacilityManagement.tsx` is static markup ("CXPL / Building A / Floor 1-5 …") and is not read from these tables.

### 4.3 Room
- **Tables:** `amenity` (the room), `amenity_type` (`amenity_category` = room/restaurant/others), `package`, `feature`, `package_feature`, `amenity_status`.
- **C:** Room Setup (`FacilityManagement.tsx`) → `createRoom` (`writes.ts:345`) → `POST /rooms` (`endpoints/facility_write.py:127`) → `facility_write.create_room` → `amenity`. **R:** `GET /rooms` → `facility.py` `list_rooms` (:301). **U:** `PATCH /rooms/{id}` → `update_room` (no UI caller). **D:** none.
- A "guest room" is only `amenity_type.amenity_category = 'room'`, and only when the caller passes that filter (live: 24 room-category amenities, 3 others).

### 4.4 Guest
- **Tables:** `app_user` with `is_staff = 0`. There is no separate guest table. Occupants are in `stay_user`.
- **C:** the Bookings form first calls `createUser` (`writes.ts:89`) → `POST /users` (`endpoints/access_write.py:88`) → `access_write.create_user` (:64), then creates the stay (see 4.5). **R:** `GET /users` (`access.py` service). **U:** `PATCH /users/{id}`. **D:** none (deactivate sets `date_of_termination`).

### 4.5 Reservation / Booking
- **Tables:** `stay` (the booking; there is no booking table), `room_allocation`, `stay_user`, `stay_package` (read only), `user_document` (read only).
- **C:** `Bookings.tsx` → `createStay` (`writes.ts:218`) → `POST /stays` (`endpoints/stays_write.py:101`) → `stays_write.create_stay` (:169). This writes `stay` (status `pending`, ref `STY-YYYY-NNNN` via `writes.next_yearly_reference`), `room_allocation` (+ `amenity.status = Allotted`) and `stay_user`.
- **R:** `GET /stays` (`endpoints/stays.py:91`) → `stay.list_stays` (:141) → `useStays` (`hooks.ts:264`) → `Bookings.tsx`, `RoomView.tsx`.
- **U:** `PATCH /stays/{id}` → `update_stay` (:210); extend → `extend_stay` (:285); cancel → `cancel_stay` (:342). **D:** none (cancel = status `cancelled`).
- **Double-booking guard:** `stays_write._assert_room_free` (:142-156) rejects a room held by any stay in `LIVE_STAY_STATUSES` (:83-89: pending, active, checkout pending/accepted/rejected). It is not date-based and has no DB constraint or row lock behind it.

### 4.6 Check-in
- `Bookings.tsx` check-in dialog → `checkInStay` (`writes.ts:221`) → `POST /stays/{id}/check-in` (`endpoints/stays_write.py:138`) → `stays_write.check_in` (:228).
- It sets `stay.actual_checkin_time`, sets `stay.status = 'active'`, and sets `amenity.status = Occupied` for each allocated room.
- The Occupancy screen has no check-in action.

### 4.7 Check-out
- `Occupancy.tsx` → `CheckOutConfirmDialog.tsx` (or the Bookings dialog) → `checkOutStay` (`writes.ts:223`) → `POST /stays/{id}/check-out` (`endpoints/stays_write.py:156`) → `stays_write.check_out` (:255).
- Preconditions (:268-271): checked in and not already out. It sets `actual_checkout_time`, `status = 'checked out'` and `checkout_initiated_by`, and sets every allocated room to Available (:277-279).
- It does not require the `checkout accepted` status, does not change `room_allocation.status` (live: still 1 on all checked-out and cancelled stays), and does not touch `amenity_condition_status`.

### 4.8 Occupancy
- **Tables:** `amenity`, `amenity_type`, `package`, `amenity_status`, `property_chain` / `property`, `amenity_condition_status`, `room_allocation`, `stay`, `stay_user`, `device` (detail count).
- **R:** `occupancy.list_occupancy` (:217) / `get_occupancy` (:267) → `GET /occupancy[/{amenity_id}]` (`endpoints/occupancy.py:67,114`) → `useOccupancy` / `useAllOccupancy` / `useOccupancyDetail` (`hooks.ts:228,237,256`) → `Occupancy.tsx`, `OccupancyStatisticsChart.tsx`, `DashboardKPIs.tsx`, `RoomView.tsx`.
- **U:** `PATCH /occupancy/{id}` (`endpoints/stays_write.py:358`) → `update_room_state` (:563; no UI caller); `PUT /occupancy/{id}/conditions` (:379) → `set_room_conditions` (:605) ← `RoomConditionsDialog.tsx`.
- **Two readings of "occupied":** `status_name` comes from `amenity.status`, and `current_stay` / `is_occupied` come from `IN_HOUSE = actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL` (`occupancy.py:39-41`). The endpoint docstring states they are not reconciled (`endpoints/occupancy.py:10-17`). See §8 and §12-A1.

### 4.9 Payment
- **Not Found in the current repository.** There is no payment table, endpoint or service.
- `invoice` exists and is read-only (`stay.list_invoices` :379, `GET /invoices`). No code creates invoices; the module notes generation is not implemented. The E-Wallet selector on Bookings is not submitted.
- `service_request` carries `net_amount` / `total_tax` / `total_amount`. The promo code is validated but does not affect the total.

### 4.10 Inventory
- **Not Found in the current repository.** There is no stock or inventory table.
- `service_category_item` is a priced catalogue of requestable items, not stock.

### 4.11 Service Requests (Service Tracking / Tickets)
- **Tables:** `service_type`, `service_status`, `service_category`, `service_category_item`, `service_request`, `service_request_item`. `room_service_request` and `room_service_request_item` are unused.
- **C:** `Tickets.tsx` → `createServiceRequest` (`writes.ts:155`) → `POST /service-requests` (`endpoints/services_write.py:80`) → `services_write.create_service_request` (:81). Status is Assigned if an assignee is given, otherwise Pending.
- **R:** `service.list_service_requests` (:295) → `GET /service-requests` (`endpoints/services.py:267`) → `useServiceRequests` (`hooks.ts:199`) → `ServiceTracking.tsx`, `Tickets.tsx`.
- **U:** `ServiceRequestActionsDialog.tsx` → `updateServiceRequest` (`writes.ts:157`) → `PATCH /service-requests/{id}` → `update_service_request` (:179).
- **Cancel:** `POST /{id}/cancel` → `cancel_service_request` (:236). **D:** none.

### 4.12 Maintenance
- **Tables:** `maintenance_request`, `maintenance_request_amenity`, `maintenance_request_assignee`, `maintenance_request_recurrence` (Service Planning); `job_order`, `job_order_amenity`, `job_order_device` (Job Orders); `device_incident`, `incident_history` (device incidents).
- **Maintenance requests:**
  - **C:** `ServicePlanning.tsx` → `createMaintenanceRequest` (`writes.ts:646`) → `POST /maintenance-requests` (`endpoints/maintenance.py:182`) → `maintenance_write.create_maintenance_request` (:203). Writes the request, rooms, assignees and recurrence in one transaction.
  - **R:** `maintenance.list_maintenance_requests`.
  - **U:** `PATCH` → `update_maintenance_request` (:249). No UI caller; the edit dialog only closes.
  - **D:** `DELETE` → `remove_maintenance_request` (:331). Soft delete: `status = 0` plus `delete_comments`.
- **Job orders:**
  - **C/U:** `JobOrder.tsx` → `createJobOrder` / `updateJobOrder` (`writes.ts:739,741`) → `POST/PATCH /job-orders` (`endpoints/job_orders.py:176,203`) → `job_order_write.create_job_order` (:121) / `update_job_order` (:165).
  - **D:** `remove_job_order` (:208) is a soft delete. It has no UI caller.

### 4.13 Holiday
See §9 (full analysis). Tables: `occasion`, `occasion_type`. Screen: `frontend/src/features/marketing/pages/Holidays.tsx`.

### 4.14 User / Staff
- **Tables:** `app_user`, `role`, `role_module`, `role_module_permission`, `user_role`, `facility_user`, `department`, `job_function`, `country`.
- **Login:**
  - `Login.tsx` → `POST /auth/login` (`endpoints/auth.py:38`) → `auth.authenticate` (:88).
  - The login query is `select(AppUser).where(AppUser.user_name == username)` (`services/auth.py:97`). Passwords are checked with bcrypt (`core/security.py:48,60`), and the token is an HS256 JWT valid for 60 minutes (`core/config.py:26-27`).
- **Permissions:**
  - `deps.get_current_user` (`api/deps.py:39`) reloads the user and their permissions on every request.
  - `require_permission` (`api/deps.py:69`) enforces the per-module read/write grant.
  - The 18 modules are in `role_module`, and the frontend mirrors them in `frontend/src/core/rbac/modules.ts`.
- **C/U:** `Employees.tsx` → `/users`, `/departments`, `/job-functions`; `UserRoles.tsx` → `/roles`, `PUT /roles/{id}/permissions` (`endpoints/access_write.py:209`) → `access_write.replace_role_permissions` (:234).
- **D:** none (users are deactivated).

### 4.15 Configuration
- **Room catalogue:** `amenity_type`, `package`, `feature`, `package_feature` (`FacilityManagement.tsx`).
- **Service catalogue:** `service_category`, `service_category_item` (`ServicesSetup.tsx`).
- **Alert thresholds:** `value_alert_limit_config` (`LimitConfigAlert.tsx` → `POST /limit-configs`, `endpoints/devices_write.py:230` → `devices_write.create_limit_config` :213).
- **RBAC:** `role_module_permission`.
- **Schema-only (no code):** `mqtt_broker`, `mqtt_topic`, `scheduler_job`, `activity_role_association`, `sub_package`.

### 4.16 Reports
- `GET /reports`, `GET /reports/{key}`, `GET /reports/{key}/export.xlsx` (`endpoints/reports.py:189,202,286`) → `reports.run_report` (:525), which reuses the list services above.
- Report keys and source tables:

| Key | Source tables |
|---|---|
| occupancy | amenity, amenity_status, amenity_condition, stay |
| employee | app_user, department, job_function, user_role |
| room-status | amenity, amenity_status, amenity_condition |
| booking | stay, room_allocation, stay_user |
| ticket | service_request, service_type, service_status, service_category |
| housekeeping | maintenance_request (scheduled/planned) |
| sanitization | maintenance_request (disinfection) |
| alert | device_alert, alert_type, device, amenity |
| energy | energy_stat, amenity |

- The Excel export uses openpyxl (`services/report_export.py`). Screen: `frontend/src/features/reports/pages/Reports.tsx`.

### 4.17 Other processes found
- **Devices & IoT:**
  - Tables: `device`, `device_type`, `firmware`, `device_param`, `device_stat`, `device_current_stat`, `device_health_stat`, `battery_life_stat`, `sensor_operation_stat`.
  - Device writes exist in the API (`endpoints/devices_write.py:78-145`), but no screen calls them.
- **Energy:**
  - Tables: `energy_stat`, `other_device`, `daily_dual_data_point`.
  - Screens: Dashboard energy chart, KPI tile and "Caleido at work"; Room power/energy panel.
- **Alerts & incidents:**
  - Tables: `alert_type`, `device_alert`, `device_incident`, `incident_history`, `incident_status`, `incident_event`, `value_alert`.
  - The read screens are Dashboard panels. `PATCH /incidents/{id}` (`endpoints/devices_write.py:161`) has no UI.
- **Offers:**
  - Tables: `promo_code`, `promo_code_amenity`.
  - Flow: `Offers.tsx` → `/offers` (`endpoints/facility_write.py:355-386`).
- **Events:**
  - Table: `facility_event`.
  - Flow: `Events.tsx` → `/events` (`endpoints/facility_write.py:407-446`).
- **Notifications & activity:**
  - Tables: `activity`, `activity_type`, `entity_type`, `activity_notifier`, `notification*`.
  - These are read-only in the app: `GET /activities`, `/notifications`, `/notification-templates`. **Nothing in the application writes activity or notification rows.**
- **Access keys / locks, push devices, scheduler:** these tables exist in the schema only, with no application code.

---

## 5. Database → backend → API → frontend data flows

Repository/DAO column: **none in this codebase** (see §0.3); the service function is the data-access layer.

| # | Flow | Table(s) | Query (service fn) | API | Frontend API call | UI |
|---|---|---|---|---|---|---|
| 1 | Occupancy grid | amenity ⋈ amenity_type ⋈ package ⟕ amenity_status ⟕ property_chain ⟕ property×2; correlated `count(room_allocation)`; conditions from amenity_condition_status; in-house stay from room_allocation ⋈ stay | `occupancy.list_occupancy` (:217) | `GET /api/v1/occupancy` (`endpoints/occupancy.py:67`) | `useOccupancy` / `useAllOccupancy` (`hooks.ts:228,237`) | `features/occupancy/pages/Occupancy.tsx` |
| 2 | Occupancy KPIs / donut | same as 1, counted with `page_size=1` | `occupancy.list_occupancy` (total) | `GET /occupancy?status=…`, `?is_occupied=true` | `useCount` / `useCounts` (`hooks.ts:111,133`) | `DashboardKPIs.tsx` (OccupancyTile), `OccupancyStatisticsChart.tsx` |
| 3 | Room detail | amenity + stay_user + device count | `occupancy.get_occupancy` (:267) | `GET /occupancy/{amenity_id}` (`endpoints/occupancy.py:114`) | `useOccupancyDetail` (`hooks.ts:256`) | `RoomDetailsModal.tsx`, `RoomDetailsPanel.tsx` |
| 4 | Buildings / floors | property_chain ⋈ property ⋈ property_type ⟕ amenity, `GROUP BY` | `facility.list_buildings` (:162), `list_floors` (:214) | `GET /buildings`, `GET /floors` | `useBuildings`, `useFloors` (`hooks.ts:169,171`) | `Dashboard.tsx`, `StatusSection.tsx`, `RoomView.tsx` |
| 5 | Bookings list | stay (+ EXISTS room_allocation ⋈ amenity for facility/floor) | `stay.list_stays` (:141) | `GET /stays` (`endpoints/stays.py:91`) | `useStays` (`hooks.ts:264`) | `features/bookings/pages/Bookings.tsx` |
| 6 | Service requests | service_request ⋈ service_type ⟕ service_category, service_status, amenity, stay, department, app_user×2 | `service.list_service_requests` (:295) | `GET /service-requests` (`endpoints/services.py:267`) | `useServiceRequests` (`hooks.ts:199`) | `ServiceTracking.tsx`, `Tickets.tsx`, `AlertsPanel.tsx` |
| 7 | Maintenance plan | maintenance_request ⟕ service_category/type/status, department; links batch-loaded | `maintenance.list_maintenance_requests` | `GET /maintenance-requests` (`endpoints/maintenance.py:114`) | `useMaintenanceRequests` (`hooks.ts:328`) | `ServicePlanning.tsx` |
| 8 | Job orders | job_order ⟕ app_user; job_order_amenity / job_order_device | `job_order.list_job_orders` (:78) | `GET /job-orders` (`endpoints/job_orders.py:124`) | `useJobOrders` (`hooks.ts:334`) | `features/config/pages/JobOrder.tsx` |
| 9 | Room power | device_stat ⋈ device ⋈ device_type ⋈ device_param ⟕ amenity ⟕ property_chain, `ORDER BY timestamp DESC` | `telemetry.list_device_stats` (:145) | `GET /device-stats?param_name=…&amenity_id=…` (`endpoints/telemetry.py:142`) | `useDeviceStats` (`hooks.ts:284`) | `features/occupancy/components/RoomPowerEnergy.tsx` |
| 10 | Energy chart / KPI | energy_stat ⋈ amenity, `SUM/COUNT GROUP BY hour, hour/24, amenity or device_name` | `energy.energy_summary` (:172) | `GET /energy-stats/summary` (`endpoints/energy.py:84`) | `useEnergySummary` (`hooks.ts:293`) | `EnergyConsumptionChart.tsx`, `DashboardKPIs.tsx`, `RoomPowerEnergy.tsx` |
| 11 | "Caleido at work" | daily_dual_data_point, `DISTINCT ON (metric_type)` | `energy.caleido_at_work` (:317) | `GET /daily-data-points/summary` (`endpoints/energy.py:187`) | `useCaleidoAtWork` (`hooks.ts:299`) | `CaleidoAtWork.tsx` |
| 12 | Alerts panel | device_alert ⋈ alert_type ⋈ device ⋈ amenity | `alert.list_alerts` (:130) | `GET /alerts` (`endpoints/alerts.py:134`) | `useAlerts` (`hooks.ts:211`) | `AlertsPanel.tsx` |
| 13 | Recent activity | activity ⋈ activity_type ⋈ entity_type; activity_notifier counts | `notification.list_activities` (:269) | `GET /activities` (`endpoints/notifications.py:213`) | `useActivities` (`hooks.ts:223`) | `RecentActivityPanel.tsx` |
| 14 | Login & permissions | app_user, user_role, role, role_module_permission, role_module, facility_user | `auth.authenticate` (:88), `access.user_permissions` (`bool_or` across roles) | `POST /auth/login`, `GET /auth/me` (`endpoints/auth.py:38,76`) | `AuthContext.tsx`, `useCurrentUser` (`hooks.ts:156`) | `Login.tsx`, route guards (`ModuleGuard.tsx`) |
| 15 | Holidays | occasion; occasion_type (second query) | `catalog.list_occasions` (:306) | `GET /holidays` (`endpoints/facility_write.py:466`) | `useHolidays` (`hooks.ts:320`) | `Holidays.tsx` (§9) |
| 16 | Reports | per report key (§4.16) | `reports.run_report` (:525) | `GET /reports/{key}`, `…/export.xlsx` | `useReport` (`hooks.ts:356`) | `Reports.tsx` |

**Client-side caching:** React Query `staleTime` is 30 s for list and count hooks (`hooks.ts:54,144`) and 5 min for the current user and report definitions (`hooks.ts:159,348`). Mutations invalidate query keys listed in `mutations.ts` (`INVALIDATE`). The only `localStorage` use is the JWT (`lib/api/client.ts:25-33`) and the theme.

---

## 6. SQL / query analysis

All queries are SQLAlchemy `select()` statements built in the service layer. There are no hand-written SQL files. Each query is described below by the tables it touches, its joins and filters, and who consumes it.

### 6.1 Important SELECT / JOIN queries

| Query (service fn) | Tables & joins | Filters | Module / API / UI |
|---|---|---|---|
| `occupancy._occupancy_stmt` → `list_occupancy` | amenity JOIN amenity_type JOIN package LEFT JOIN amenity_status, property_chain, property (building), property (floor); scalar subquery `count(room_allocation WHERE room_id = amenity.id)` (all history) | facility_id, building_id, floor_id, amenity_type_id, amenity_category, status (`amenity.status`), condition_id (EXISTS on amenity_condition_status with status 1), is_occupied (EXISTS room_allocation JOIN stay WHERE IN_HOUSE) | Occupancy; `GET /occupancy`; Occupancy page, KPIs, donut, Room View |
| `occupancy._current_stays` | room_allocation JOIN stay (+ booker app_user) | IN_HOUSE, latest per room | Occupancy row enrichment |
| `facility._building_stmt` | property_chain JOIN property (level_one) JOIN property_type LEFT JOIN amenity; `count(distinct level_two_id)`, `count(distinct amenity.id)` GROUP BY building | facility_id | `GET /buildings` |
| `facility._floor_stmt` | property_chain JOIN property (level_two) JOIN property (level_one); GROUP BY property_chain.id | building_id, facility_id | `GET /floors` |
| `facility._room_stmt` | amenity JOIN amenity_type JOIN package LEFT JOIN amenity_status, property_chain, property×2 | facility, building, floor, type, category, status | `GET /rooms` |
| `stay.list_stays` | stay (+ counts of stay_user and room_allocation) | EXISTS room_allocation JOIN amenity for facility / building / floor; status; is_in_house (timestamps); date ranges | `GET /stays`; Bookings, Room View |
| `service.list_service_requests` | service_request JOIN service_type LEFT JOIN service_category, service_status, amenity, stay, department, app_user (requester), app_user (assignee) | facility, type, status, category, assignee, requester, stay, amenity, department, source, unassigned, created_on range; `ORDER BY created_on DESC` | `GET /service-requests` |
| `maintenance.list_maintenance_requests` | maintenance_request LEFT JOIN service_category (→ service_type), service_status, department | default `status = 1`; EXISTS on live assignee / room links | `GET /maintenance-requests` |
| `job_order.list_job_orders` | job_order LEFT JOIN app_user | `status IS DISTINCT FROM 0`; facility via `IN (job_order_amenity JOIN amenity)`; ILIKE search | `GET /job-orders` |
| `telemetry.list_device_stats` | device_stat JOIN device JOIN device_type JOIN device_param LEFT JOIN amenity, property_chain | param_name, amenity_id, device_id, time range; `ORDER BY timestamp DESC` | `GET /device-stats`; Room power |
| `alert.list_alerts` / `list_incidents` / `list_value_alerts` | device_alert / device_incident / value_alert joined to alert_type, device, amenity, incident_status | facility, amenity, type, severity, status, dates | `/alerts`, `/incidents`, `/value-alerts`; Dashboard |
| `catalog.list_occasions` | occasion; then `SELECT id, occasion_type FROM occasion_type` | optional facility_id (never passed); **no type or status filter** | `GET /holidays` |
| `auth.authenticate` | app_user | `user_name = :username` | `POST /auth/login` |

### 6.2 Aggregation queries

| Aggregate | Where | Purpose |
|---|---|---|
| `count(*)` via subquery for `total` | every list service (pagination) | Page totals used by KPI tiles (`useCount`) |
| `count(distinct …)` floors/rooms per building | `facility._building_stmt` | Building cards. Room count includes non-room amenities. |
| `facility_counts` | `facility.py` (:72) | Facility summary counts |
| Correlated `count(room_allocation)` | `occupancy._occupancy_stmt` | `allocation_count` (includes cancelled / checked-out history) |
| `SUM(energy_consumed)`, `COUNT(*)` GROUP BY hour / hour÷24 / amenity / device_name | `energy.energy_summary` (:172) | Energy chart, KPI and room energy. Day buckets are UTC. |
| `DISTINCT ON (metric_type) … ORDER BY metric_date DESC` | `energy.caleido_at_work` (:317) | Latest KPI snapshot per metric |
| `bool_or(read_access)`, `bool_or(write_access)` GROUP BY module | `access.user_permissions` | Effective permissions across a user's roles |
| `service_type_counts`, `alert_type_counts`, `category_item_count`, `template_notification_count` | service.py, alert.py, notification.py | Per-lookup counts |
| `MAX(created_on)` health sample | device.py (health) | `last_reported_on` in `/devices/{id}/health` |

### 6.3 INSERT operations (all inside `writes.transaction()`)

`access_write.create_user` / `create_role` / `create_department` / `create_job_function`; `facility_write.create_room` / `create_amenity_type` / `create_package` / `create_feature` / `create_promo_code` / `create_event` / `create_occasion`; `stays_write.create_stay` / `allocate_room` / `add_occupant`; `services_write.create_service_request` / `create_service_category` / `create_service_item`; `maintenance_write.create_maintenance_request`; `job_order_write.create_job_order`; `devices_write.create_device` / `create_limit_config`; `devices_write.update_incident` (inserts `incident_history`).

Reference numbers such as `STY-2026-0001`, `SR-…` and `JO-…` are computed by `writes.next_reference` / `next_yearly_reference` (`backend/app/services/writes.py:123-156`). These scan all existing values and add 1, with no lock or sequence. A concurrent collision is caught by the UNIQUE constraint and returned as HTTP 409.

### 6.4 UPDATE operations

Every PATCH uses `writes.apply_changes` (`writes.py:108-120`), which assigns only the fields the caller sent. State-changing updates:
- `stays_write.check_in` / `check_out` / `extend_stay` / `set_stay_status` / `cancel_stay` / `reallocate_room` (**rewrites `room_allocation.room_id` in place**, :454-456)
- `_set_room_status` (`amenity.status`)
- `services_write.update_service_request` / `cancel_service_request`
- `maintenance_write.update_…` / `cancel_…` / `remove_…` (soft delete)
- `job_order_write.update_job_order` / `remove_job_order` (soft delete)
- `access_write.deactivate_user` / `reactivate_user`
- `devices_write.set_device_config_status` / `update_incident`

### 6.5 DELETE operations (hard deletes)

| Location | Deletes | Pattern |
|---|---|---|
| `access_write.py:162` | `user_role` for the user (all facilities) | delete-then-reinsert on user save |
| `facility_write.py:229` | `package_feature` for the package | delete-then-reinsert |
| `facility_write.py:312` | `promo_code_amenity` for the offer | delete-then-reinsert |
| `job_order_write.py:110,116` | `job_order_amenity`, `job_order_device` | delete-then-reinsert |
| `services_write.py:223` | `service_request_item` for the request | delete-then-reinsert (`PUT …/items`) |
| `maintenance_write.py:179` | `maintenance_request_recurrence` | when the rule is removed |
| `stays_write.py:479` | `room_allocation` | `release_allocation` |
| `stays_write.py:552` | `stay_user` | `remove_occupant` |
| `stays_write.py:632` | `amenity_condition_status` | `set_room_conditions` (clears a condition) |

Everything else that the UI calls "delete" is a **soft delete** (`status = 0`): package, maintenance request, job order, holiday (occasion), offer, event and feature.

---

## 7. Data creation and update flows

### 7.1 Write path (UI → DB)

| Operational record | UI trigger | Frontend write fn | API | Service | Tables written |
|---|---|---|---|---|---|
| Guest + booking | `Bookings.tsx` "Add booking" | `createUser` (`writes.ts:89`), then `createStay` (:218) | `POST /users`, then `POST /stays` | `access_write.create_user` (:64), `stays_write.create_stay` (:169) | app_user, user_role; stay, room_allocation, stay_user, amenity.status |
| Check-in | Bookings dialog | `checkInStay` (:221) | `POST /stays/{id}/check-in` | `check_in` (:228) | stay, amenity.status |
| Check-out | Occupancy → CheckOutConfirmDialog; Bookings | `checkOutStay` (:223) | `POST /stays/{id}/check-out` | `check_out` (:255) | stay, amenity.status |
| Extend / cancel booking | Bookings | `extendStay` (:225), `cancelStay` (:233) | `POST …/extend`, `…/cancel` | `extend_stay` (:285), `cancel_stay` (:342) | stay (+ amenity.status on cancel) |
| Room reallocation | `ReallocateRoomDialog.tsx` | `reallocateRoom` (:241) | `PATCH /room-allocations/{id}` | `reallocate_room` (:428) | room_allocation (in place), amenity.status ×2 |
| Room conditions | `RoomConditionsDialog.tsx` | `setRoomConditions` (:267) | `PUT /occupancy/{id}/conditions` | `set_room_conditions` (:605) | amenity_condition_status |
| Document approval | Bookings toggle | `setStayDocumentApproval` (:229) | `POST …/documents/approval` | `set_document_approval` (:330) | stay.document_approval_status only |
| Service ticket | `Tickets.tsx` | `createServiceRequest` (:155) | `POST /service-requests` | `create_service_request` (:81) | service_request (+ items if sent; the UI sends none) |
| Ticket status / assign / cancel | `ServiceRequestActionsDialog.tsx` | `updateServiceRequest` (:157), `cancelServiceRequest` (:163) | `PATCH …/{id}`, `POST …/{id}/cancel` | `update_service_request` (:179), `cancel_service_request` (:236) | service_request |
| Maintenance plan | `ServicePlanning.tsx` | `createMaintenanceRequest` (:646), `removeMaintenanceRequest` (:655) | `POST`, `DELETE /maintenance-requests[/{id}]` | `create_…` (:203), `remove_…` (:331) | maintenance_request (+ amenity, assignee, recurrence) |
| Job order | `JobOrder.tsx` | `createJobOrder` (:739), `updateJobOrder` (:741) | `POST`, `PATCH /job-orders` | `create_job_order` (:121), `update_job_order` (:165) | job_order, job_order_amenity, job_order_device |
| Holiday | `Holidays.tsx` | `createHoliday` (:753), `updateHoliday` (:755) | `POST`, `PATCH /holidays` | `create_occasion`, `update_occasion` | occasion |
| Offer / event | `Offers.tsx`, `Events.tsx` | `createOffer` / `updateOffer` (:481-482), `createEvent` / `updateEvent` (:517-518) | `/offers`, `/events` | `create_promo_code`, `update_promo_code`, `create_event`, `update_event` | promo_code, promo_code_amenity; facility_event |
| Room catalogue | `FacilityManagement.tsx` | `createAmenityType` (:361), `createFeature` (:437), `createPackage` (:398), `removePackage` (:422), `createRoom` (:345) | `/amenity-types`, `/features`, `/packages`, `/rooms` | facility_write | amenity_type, feature, package, package_feature, amenity |
| Staff / roles | `Employees.tsx`, `UserRoles.tsx` | `createUser` / `updateUser`, `createRole`, `replaceRolePermissions` (:110) | `/users`, `/roles`, `PUT /roles/{id}/permissions` | access_write | app_user, user_role, role, role_module_permission |
| Alert thresholds | `LimitConfigAlert.tsx` | `createLimitConfig` (:313) | `POST /limit-configs` | `create_limit_config` (:213) | value_alert_limit_config |

### 7.2 Records created outside this application

These tables are populated only by the seed scripts (`backend/seeds/steps/*.py`) or by an external ingester that is not in this repository:
- **Telemetry:** device_stat, device_current_stat, device_health_stat, battery_life_stat, sensor_operation_stat, other_device, energy_stat, daily_dual_data_point
- **Alerts:** device_alert, value_alert, device_incident creation
- **Activity and notifications:** activity, activity_notifier, notification*
- **Stays and devices:** invoice, user_document, stay_package, import_job, device_command
- **Keys and locks:** access_key, lock_activity_log

**The ingestion path for live IoT data cannot be verified from this repository.**

### 7.3 Read path (DB → UI)

See §5. Every read goes model → service `select()` → FastAPI route (Pydantic response schema in `backend/app/schemas/*.py`) → `endpoints.ts` → `hooks.ts` → page.

---

## 8. Database integrity and system ownership

### 8.1 Constraints in place (live catalog)

| Constraint type | Count | Notes |
|---|---:|---|
| Primary keys | 93 | Every table has one. UUID PKs on entity tables; bigint on high-volume logs; composite on junctions. |
| Foreign keys | 240 | 47 of them are audit FKs (`created_by`/`updated_by`/`modified_by`/`uploaded_by`) to `app_user`. 86 FK columns have **no supporting index** (the leading column of an index does not match the FK column). |
| Unique | 76 | Mostly `legacy_id`. Business uniques include `app_user.user_name`, `app_user.user_uid`, `facility.facility_uid`, `organisation.org_uid`, `device.device_uid`, `invoice.invoice_number`, `job_order.order_reference`, `promo_code.promo_code`, `service_request.ref_number`, `stay.internal_stay_ref_number`, `scheduler_job.job_key`, `user_token.token`, `notification_template (name, type)` and `value_alert_limit_config (device_name, parameter, facility_id)`. |
| NOT NULL | 543 | Catalogued as `n` constraints (PostgreSQL 18). |
| CHECK | **0** | Status and flag ranges are enforced only in Pydantic schemas (`backend/app/schemas/ops_write.py`). |
| ENUM types | 34 | E.g. `stay_status`, `room_service_request_status`, `job_order_status`, `device_config_status`, `amenity_category`. |
| Triggers / views | 0 / 0 | — |

### 8.2 Validation, duplicate prevention and transactions

- **Transactions:** every write runs inside `writes.transaction()` (`backend/app/services/writes.py:53-74`). It commits once, rolls back on any exception, and maps `IntegrityError` to HTTP 409 with the constraint name. `get_db` only closes the session (`backend/app/db/session.py:19-24`).
- **Pre-checks:** `require_row` (404), `require_exists` (422 for bad FK references) and `ensure_unique` (409) are used before writes (`writes.py:82-106`).
- **Duplicate prevention:**
  - The DB UNIQUE constraints listed above.
  - `_assert_room_free` for room double-allocation. This is application-only, with no exclusion constraint or `SELECT … FOR UPDATE` anywhere in the codebase.
  - `ensure_unique` on names. For `amenity_type`, `package`, `feature`, `role`, `department`, `job_function` and `service_category` this is **global, not per facility**.
- **Audit/history:**
  - `created_on` / `updated_on` exist on every table; `created_by` on most.
  - The only event-history table written by the app is `incident_history` (on incident status change).
  - `activity` / `notification` are never written by application code.
  - Many updates set no updater column (occasion, promo_code, facility_event and role_module_permission have none).

### 8.3 Data ownership between modules

| Owner module (writes) | Tables | Other modules that read them |
|---|---|---|
| Stays (`stays_write.py`) | stay, room_allocation, stay_user, **amenity.status**, amenity_condition_status | Occupancy, Reports, Services (FK), Dashboard |
| Facility config (`facility_write.py`) | amenity (create/update), amenity_type, package, feature, package_feature, promo_code*, facility_event, occasion | Occupancy, Stays, Services |
| Access (`access_write.py`) | app_user, role, user_role, role_module_permission, department, job_function | All modules (auth), Bookings (guest create) |
| Services / maintenance / job orders | service_*, maintenance_*, job_order* | Reports, Occupancy detail |
| Devices (`devices_write.py`) | device, device_incident, incident_history, value_alert_limit_config | Occupancy detail, Dashboard |
| External / seed only | telemetry, alerts, activity, notification, invoice | Dashboard, Reports |

`amenity.status` has **three writers**: `stays_write._set_room_status` (check-in/out, allocate, cancel, reallocate, release), `stays_write.update_room_state` (`PATCH /occupancy/{id}`) and `facility_write.create_room` / `update_room`. The stay graph is a second, independent source (IN_HOUSE timestamps). **This is the central data-ownership concern of the schema.**

### 8.4 Integrity concerns (evidence-based)

**I-1. Room status diverges from stays (confirmed in live data).**
- **Evidence:**
  - Live DB: 3 amenities have `amenity.status = 1 (Occupied)`, including rooms 201 and 301, but only 1 stay is in house (STY-2026-0007, room 301).
  - Room 201 is *Occupied* and room 108 is *Allotted* with **no `room_allocation` row at all**.
  - The seed sets room statuses independently of stays (`backend/seeds/steps/rooms.py:80-92`, e.g. `("201", "premium", OCCUPIED)`).
  - `update_room_state` blocks only Available/Unavailable while a live stay exists, so *Occupied* can be set with no stay (`stays_write.py:588-598`).
  - The code documents the gap itself (`endpoints/occupancy.py:10-17`). Its example numbers ("5 Occupied vs 3 in house") are out of date; live data shows 3 vs 1.
- **Impact:** "Occupied" counts from `?status=` disagree with "in house" counts from `?is_occupied=true`. The Dashboard tile shows both.
- **Related:** amenity, stay, room_allocation / Occupancy.
- **Recommended investigation:** decide which source is authoritative, then audit every writer of `amenity.status`.

**I-2. `room_allocation.status` never changes.**
- **Evidence:**
  - Always written as `ALLOCATION_ACTIVE = 1` (`stays_write.py:91`).
  - Live: 1 on every allocation of checked-out and cancelled stays.
  - Cancel keeps the rows (`stays_write.py:354-357`).
- **Impact:** the column cannot distinguish current from historical allocations, and `allocation_count` counts history.
- **Recommended investigation:** confirm the intended meaning of `room_allocation.status`.

**I-3. No DB-level protection against double allocation.**
- **Evidence:** `_assert_room_free` (`stays_write.py:142-156`) is a read-then-write check, and no locking is used anywhere (grep for `with_for_update` finds nothing).
- **Impact:** two concurrent bookings of the same room can both pass. This is not observed in live data: 0 rooms have more than one live allocation.
- **Recommended investigation:** concurrency test on `POST /stays`.

**I-4. Multi-facility isolation is not enforced.**
- **Evidence:**
  - `facility_id` is an optional filter on every list endpoint, and no page passes it.
  - `api/deps.py` has no facility logic.
  - `stay`, `job_order`, `promo_code` and `import_job` have no `facility_id` column.
  - `daily_dual_data_point` has PK `(metric_date, metric_type)` with no `facility_id`.
  - `access_write.py:162` deletes a user's roles at **all** facilities before re-inserting them at one.
  - Live: 1 facility, so there is no visible effect today.
- **Impact:** in a second facility, data would be shared or would collide.
- **Recommended investigation:** confirm whether multi-facility is in scope.

**I-5. Schema lengths exceed column lengths.**
- **Evidence** (Pydantic `max_length` vs column size):

  | Field | Schema | Column |
  |---|---|---|
  | `RoomCreate.name` | 255 | `amenity.name` varchar(6) |
  | `OccasionCreate.occasion_name` | 255 (`ops_write.py:452`) | 100 (`models/marketing.py:154`) |
  | `promo_code` | 100 | 20 |
  | GST | 50 | 20 |
  | `status_reason` | 255 | 100 |

- **Impact:** over-long input passes validation, then fails at the database with a generic error instead of a field message.

**I-6. Stale-data window in the UI.**
- **Evidence:** 30 s `staleTime` (`hooks.ts:54`). Room/catalogue mutations do not invalidate `occupancy`, `buildings`, `floors` or `count` keys (`mutations.ts`, `INVALIDATE`).
- **Impact:** KPI tiles can lag writes by up to 30 s. This is a UI concern, not a DB one.

**I-7. Orphan-prone booking creation.**
- **Evidence:** Bookings creates the guest `app_user`, then the stay, in two separate requests (`Bookings.tsx`, `handleSubmit`).
- **Impact:** if the stay is rejected (room taken or bad dates), a guest row is left behind, and retries can create duplicate guests. `app_user` has no unique phone or email.

---

## 9. Holiday Management analysis

### 9.1 Is it implemented?
**Yes.** Holiday Management is implemented on the **`occasion`** table, typed by **`occasion_type`**. There is no table named `holiday`. The model docstring states *"`occasion_type = 'Holiday'` IS the Holidays module"* (`backend/app/models/marketing.py:142`).

### 9.2 Tables and columns

| Table | Column | Type | Meaning / use |
|---|---|---|---|
| `occasion` (17 cols, 4 rows) | `id` | uuid PK | — |
| | `occasion_name` | varchar(100) | Written from the UI "Lock message" field |
| | `occasion_type` | int2 NN → `occasion_type.id` | Written from the UI "Description" field (matched to a type name) |
| | `occasion_start_date` / `occasion_end_date` | date NN / date | Start / end date |
| | `month`, `day_of_month` | int2 NN | Derived from the start date by the service (`facility_write.py:385-386, 406-408`) |
| | `is_repeatable` | bool | Stored; never set by the UI; no reader |
| | `notify_to_hub` | bool | Stored; never set by the UI; no reader |
| | `notification_template` | text | Hub message; **not writable through the API**, not exposed |
| | `app_user_id` | uuid → app_user | For personal occasions; not writable through the API |
| | `facility_id` | uuid → facility | Payload value or the user's default facility |
| | `status` | int2 | 1 active / 0 retired (soft delete) |
| | `created_by`, `created_on`, `updated_on`, `legacy_id` | — | Audit. There is no `updated_by`. |
| `occasion_type` (5 cols, 4 rows) | `id`, `occasion_type`, `notification_template` | int2 PK, varchar, text | Reference: 1 Festival, 2 Birthday, 3 Marriage anniversary, 4 Holiday |

**Year / state / country fields: none exist** in `occasion`, the schemas or the page. The only date parts are the start/end dates and the derived `month` / `day_of_month`. A `lock_message` column also does not exist; the model's comment calls this out (`models/marketing.py:145-149`).

**Live master/reference data:**

| Name | Type | Start | End | Repeatable | Status |
|---|---|---|---|---|---|
| Christmas | Holiday | 2026-12-25 | 2026-12-26 | yes | 1 |
| Diwali | Holiday | 2026-11-08 | 2026-11-10 | yes | 1 |
| New Year | Holiday | 2027-01-01 | 2027-01-01 | yes | 1 |
| Pongal | **Festival** | 2027-01-14 | 2027-01-17 | yes | 1 |

### 9.3 Backend and API

| Endpoint | Route definition | Permission | Service |
|---|---|---|---|
| `GET /api/v1/holidays` | `endpoints/facility_write.py:466` (`list_holidays`) | holidays: read (`:80`) | `catalog.list_occasions` (`services/catalog.py:306`) |
| `GET /api/v1/holidays/types` | `endpoints/facility_write.py:480` | holidays: read | `catalog.list_occasion_types` (`:341`) |
| `POST /api/v1/holidays` | `endpoints/facility_write.py:490` (`create_holiday`) | holidays: write (`:81`) | `facility_write.create_occasion` (`services/facility_write.py:367`) → `catalog.get_occasion` (`:336`) |
| `PATCH /api/v1/holidays/{occasion_id}` | `endpoints/facility_write.py:512` | holidays: write | `facility_write.update_occasion` (`:394`) → `catalog.get_occasion` |

- **Read query** (`catalog.py:306-333`):
  - `select(Occasion).order_by(Occasion.occasion_start_date.desc())`, with an optional `facility_id` filter (`:308-309`) that the endpoint never passes (`facility_write.py:475`). A second query fetches the type names (`:311-313`).
  - **There is no `occasion_type` filter and no `status` filter.**
- **Single-row read:** `get_occasion` re-runs the list with `page_size=1000` and scans in Python (`catalog.py:337`).
- **Create** (`facility_write.py:367-391`): validates that `occasion_type` exists and that end ≥ start (`:375-377`), sets the facility and `created_by`, and derives `month` / `day_of_month`.
- **Update** (`:394-410`): re-validates the type and dates, then `apply_changes`. Month/day are re-derived only when the start date changes.
- **Payload schemas** (`schemas/ops_write.py:448-468`), with unknown keys rejected (`extra="forbid"`, `:43-45`):
  - `OccasionCreate`: occasion_type (required), occasion_name, occasion_start_date (required), occasion_end_date, is_repeatable, notify_to_hub, facility_id, status.
  - `OccasionUpdate`: the same fields without facility_id.
- **Delete:** there is no DELETE route. Retirement is `PATCH {status: 0}`.

### 9.4 Frontend (`frontend/src/features/marketing/pages/Holidays.tsx`)

| Aspect | Implementation | Evidence |
|---|---|---|
| Data load | `useHolidays({page:1, page_size:100})`, `useOccasionTypes()`; paging and search are client-side | `:43-44` |
| Table columns | Start Date, End Date, **Lock message** = `occasion_name ?? occasion_type_name`, **Description** = `occasion_type_name` | `:54-55`, `:227-228` |
| Form | Start Date*, End Date*, Lock message*, Description* (free-text textarea) | `:81-82`, `:163-169` |
| Submit | `occasion_name` = lock message. `occasion_type` = the type whose name equals the Description text, else "Holiday", else the first type. `is_repeatable` / `notify_to_hub` are never sent. | `:99-106` |
| Delete | `updateHoliday.mutate({id, body: {status: 0}})`; the dialog says "You won't be able to revert this!" | `:134`, `:296` |
| Leftovers | Comment "Sample holidays data"; `TableLoading columns={13}` for a 5-column table | `:32`, `:219` |

### 9.5 Complete flow

```
occasion (+ occasion_type)
  → catalog.list_occasions / get_occasion / list_occasion_types      backend/app/services/catalog.py:306-347
  → facility_write.create_occasion / update_occasion                 backend/app/services/facility_write.py:367-410
  → GET/POST /api/v1/holidays, GET /holidays/types, PATCH /holidays/{id}
                                                                      backend/app/api/v1/endpoints/facility_write.py:466-521
  → listHolidays / listOccasionTypes / createHoliday / updateHoliday frontend/src/lib/api/writes.ts:750-755
  → useHolidays / useOccasionTypes                                   frontend/src/lib/api/hooks.ts:320-322
  → Holidays page (route gated by module "holidays")                 frontend/src/features/marketing/pages/Holidays.tsx
```

### 9.6 Relationship with other HMS modules
- **FKs:** `occasion` → `occasion_type`, `facility`, `app_user` (×2).
- **No other table references `occasion`.**
- A grep of `backend/app/api` and `backend/app/services` finds `Occasion` / `OccasionType` only in `catalog.py` and `facility_write.py`. It is not used by bookings, occupancy, pricing, maintenance scheduling, notifications or reports.
- The fields that suggest integration (`notify_to_hub`, `is_repeatable`, `notification_template`) have **no runtime reader**, and the scheduler tables that could drive them are unused.
- The `occasion_type.notification_template` column is also unused.

### 9.7 Holiday findings

- **H-1. Non-holiday occasions appear as holidays.** The list has no `occasion_type` filter (`catalog.py:307`), so live "Pongal" (type Festival) shows on the Holidays screen.
- **H-2. Retired holidays remain visible.** There is no status filter in the service or the page, so "deleted" rows look identical to active ones. The "won't be able to revert" dialog text is also inaccurate, since `status = 1` restores the row.
- **H-3. The UI's fields do not match the DB's meaning.**
  - "Lock message" is stored in `occasion_name`, not in `notification_template` (the hub message).
  - "Description" is used only to pick a type; any other text is **discarded**.
  - The "Description" column displays the type name.
- **H-4. Hub-notification and repeat features are stored but inert.** Nothing reads `is_repeatable`, `notify_to_hub` or `notification_template`.
- **H-5. Truncation.** The page loads at most 100 rows, and `get_occasion` scans at most 1000.

---

## 10. Implementation vs database comparison

### 10.1 Table usage summary

| Usage level | Tables |
|---|---|
| **Read and written by the app (UI reachable)** | facility (PATCH not in UI), amenity, amenity_type, amenity_condition_status, package, feature, package_feature, stay, room_allocation, stay_user (via create), service_request, service_category, service_category_item, maintenance_request (+ amenity, assignee, recurrence), job_order (+ amenity, device), promo_code, promo_code_amenity, facility_event, occasion, app_user, role, user_role, role_module_permission, department, job_function, value_alert_limit_config |
| **Read by API and UI, never written by app** | property, property_type, property_chain, amenity_status, amenity_condition, service_type, service_status, device_type, device, device_param, device_stat, energy_stat, daily_dual_data_point, device_alert, device_incident (writes exist, no UI), value_alert, activity, activity_type, entity_type, activity_notifier, notification_template, role_module, occasion_type, facility_user |
| **Exposed by API but no UI consumer** | invoice, user_document, stay_package, service_request_item, device_current_stat, device_health_stat, battery_life_stat, sensor_operation_stat, other_device, firmware, alert_type, incident_history, incident_status, incident_event, notification, notification_receiver, notification_result |
| **Model only: no service, API or UI** | organisation, sub_package, import_job, room_service_request, room_service_request_item, command_type, device_command, mqtt_broker, mqtt_topic, user_token, user_device, user_device_acl, access_key, key_type, lock_activity_log, activity_role_association, scheduler_job, scheduler_job_execution |
| **FK target only** | attachment, country |
| **Tables referenced by code but missing from the schema** | **None.** Every `__tablename__` in `backend/app/models` exists in the live DB and vice versa. |

### 10.2 Columns that appear unused (no read or write in services or the frontend)

The table-level unused set above implies all of its columns. Beyond those:
- `amenity.metadata`, `is_dnd`, `power_save_mode`, `parent_amenity_id` (returned or writable, but no UI use)
- `facility.cloud_details`, `currency_id`, `additional_email`
- `occasion.notification_template`, `app_user_id`, `is_repeatable`, `notify_to_hub` (§9)
- `occasion_type.notification_template`
- `property_chain.level_three_id`
- `maintenance_request.parent_id`, `under_maintenance` (reports only; no effect on occupancy)
- `maintenance_request_recurrence.max_no_of_occurrences`
- `service_category_item.metadata` (the UI writes food attributes into `description` instead)
- `incident_history.incident_event_data`
- `user_document.document_approval_status` (the UI writes the stay-level flag instead)
- `stay.gst` (accepted, not displayed)

Method: grep across `backend/app/services`, `frontend/src`. A column read only by the generic Pydantic response would still count as "returned".

### 10.3 UI fields and their database source, with label mismatches

| Screen / label | Actual DB source | Mismatch |
|---|---|---|
| Dashboard "Total Rooms" / "of N rooms" (`DashboardKPIs.tsx` OccupancyTile; `OccupancyStatisticsChart.tsx:63`) | `count(amenity)` with **no** `amenity_category` filter | **Live: 27 amenities vs 24 guest rooms** (`facility.guest_rooms = 24`); restaurant, gym and conference room are included |
| Dashboard occupied figure | `?is_occupied=true` (stay timestamps) vs `?status=Occupied` (`amenity.status`) | Two different "occupied" numbers (I-1) |
| Room View tiles (`RoomView.tsx:44,60-70`) | Counts of **one page of 100** occupancy rows (`items.length`), all categories | Wrong above 100 amenities; mixes non-rooms |
| Occupancy "Status" filter/column | `amenity_condition_status` labels, not `amenity.status` | The donut drill-through (`?status=<amenity status name>`) never matches |
| Occupancy "Guest name" / "Primary Guest" | `stay.booking_user_id` (the booker) | Not necessarily an occupant |
| Condition "Need Maintenance" (`occupancy/lib/roomStatus.ts`) | `amenity_condition` "Dirty" | A separate "Under maintenance" condition exists |
| Facility Mgmt "Organization Name" | `facility.name` | Not `organisation.name` |
| Facility Mgmt Amenity Type "Icon" | `amenity_type.amenity_category` | Not an image |
| "Room Amenities" tab | `feature` table | Name differs from the `amenity` table |
| Holidays "Lock message" / "Description" | `occasion_name` / `occasion_type` | §9, H-3 |
| Service Tracking donut "Pending" (`ServiceTracking.tsx:158-165`) | every non-Completed request, including Canceled | Mislabelled; also counts only the first 100 rows (`.length`, :149-161) |
| `service_status` "Canceled" vs frontend "cancelled" | DB value is "Canceled" (id 5); `serviceStatus.ts` accepts both | "cancelled" exists only in the unused `room_service_request_status` enum |
| Energy KPI "no unit" vs chart unit | `device_param.unit` for `active_energy` = **kWh** (live) | Same figure shown with and without a unit |
| UserRoles "Notifications" column | `role.description` | Mislabelled |

### 10.4 Hardcoded or static data where DB data is expected

| Location | Hardcoded content | DB source that exists |
|---|---|---|
| `FacilityManagement.tsx:722-724, 817, 1075-1092` | Amenity Type options `continental`, `guest-room`, `car-parking`; Package options `delux`, … | `amenity_type`, `package`. Submit matches these slugs to DB names and **silently returns** (`:307-310`, `:326-331`), so Package and Room create cannot succeed. |
| `FacilityManagement.tsx` Facility Structure tree | "CXPL / Building A / Floor 1-5 / …" | `property`, `property_chain`. `property_chain_id` is never sent. |
| `LimitConfigAlert.tsx:138-139, 200` | Option value is the device *name*, but lookup is by `id` | `device`; submit silently returns |
| `Offers.tsx` edit (`promo_code` in body) | Sends a field `PromoCodeUpdate` does not define (`schemas/ops_write.py:411-421`, `extra="forbid"`) | Every offer edit → 422 |
| `ServiceTracking.tsx:916-926` | Items modal rows "Wipes / Trimmer / Soap" | `service_request_item` |
| `ServiceTracking.tsx:828, 837` | "Housekeeping Manager", "Alice konyak" options (dead status modal) | `app_user`, `department` |
| `ServicePlanning.tsx` edit dialog | "Sanitation", "Guest Room sanitation", "Admin", fixed times; Submit only closes | `maintenance_request` |
| `Bookings.tsx` | Nationality list and phone country codes (4 codes); mobile / email / room columns `"-"` | `country` (239 rows, incl. `phone_code`), `app_user`, `room_allocation` |
| `JobOrder.tsx:73` | `troubleshoot → "fresh-installation"` radio mapping | `job_order_type_of_work` enum has `troubleshoot`; saving an edit rewrites it to `installation` |
| `Holidays.tsx:32` | Leftover comment "Sample holidays data" | — (the data itself is from the API) |

---

## 11. Complete table → process matrix

All 93 tables. "Related tables" lists business relationships and leaves out audit FKs to `app_user`.

| Table | Category | Purpose | Primary Key | Related Tables | HMS Process | Backend Usage | API | Frontend Usage |
|---|---|---|---|---|---|---|---|---|
| `facility` | Master | The hotel / premise | `id` | activity, amenity, amenity_type, app_user, attachment +26 | Facility & Property | facility.py `list_facilities`, `get_facility`, `facility_counts`; facility_write.py `update_facility`; access_write.py `default_facility_id` | GET /facilities, GET/PATCH /facilities/{id} | FacilityManagement.tsx, KeySettings.tsx (`useFacilities`) |
| `organisation` | Master | Tenant / owning organisation of a facility. | `id` | facility | Facility & Property | None (only `facility.org_id` echoed in facility responses) | None | None found |
| `property` | Master | One node of the building structure (a building, wing or floor). | `id` | facility, property_chain, property_type | Facility & Property | facility.py `list_properties`, `get_property`; aliased as Building/Floor in facility.py and occupancy.py | GET /properties[/{id}] (and indirectly /buildings, /floors) | `useProperties` has no consumer; used indirectly via buildings/floors |
| `property_chain` | Master | Materialised Building → Floor path (level_one/two/three → property) | `id` | amenity, facility, property | Facility & Property | facility.py `list_buildings`, `list_floors`, room statement; occupancy.py statement | GET /buildings[/{id}], GET /floors[/{id}] | Dashboard.tsx, StatusSection.tsx, Occupancy.tsx, RoomView.tsx |
| `property_type` | Reference | Kind of structure and the depth (`levels`) of the property chain. | `id` | attachment, facility, property | Facility & Property | facility.py (joined in property/building statements) | Fields inside /properties and /buildings | Not directly |
| `amenity` | Master | A bookable space: guest room, suite, restaurant, gym, conference room | `id` | amenity_condition_status, amenity_status, amenity_type, device, device_alert +17 | Room / Occupancy | facility.py `list_rooms`, `get_room`; occupancy.py `list_occupancy`, `get_occupancy`; facility_write.py `create_room`, `update_room`; stays_write.py `update_room_state` + status changes on check-in/out/allocate | GET/POST /rooms, GET/PATCH /rooms/{id}, GET /occupancy[/{id}], PATCH /occupancy/{id} | Occupancy.tsx, RoomView.tsx, FacilityManagement.tsx, Dashboard KPIs |
| `amenity_condition` | Reference | Room condition lookup: Dirty, Low battery, Under maintenance, Sanitation. | `id` | amenity_condition_status | Room / Occupancy | occupancy.py `list_amenity_conditions` | GET /amenity-conditions | RoomConditionsDialog.tsx |
| `amenity_condition_status` | Transaction / Operational | Active conditions currently flagged on a room (room × condition). | `amenity_id, amenity_condition_id` | amenity, amenity_condition | Room / Occupancy | facility.py/occupancy.py condition lookups; stays_write.py `set_room_conditions` (delete + insert) | PUT /occupancy/{id}/conditions | Occupancy.tsx, RoomConditionsDialog.tsx |
| `amenity_status` | Reference | Room status lookup: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted. | `id` | amenity | Room / Occupancy | occupancy.py `list_amenity_statuses`; stays_write.py status helpers | GET /amenity-statuses | OccupancyStatisticsChart.tsx, DashboardKPIs.tsx, ReallocateRoomDialog.tsx |
| `amenity_type` | Master | Category of space (Guest Room, Suite, Restaurant…) with `amenity_category` enum room/restaurant/others. | `id` | amenity, attachment, facility, package, user_device_acl | Room / Occupancy | catalog.py `list_amenity_types`; facility_write.py create/update | GET/POST /amenity-types, PATCH /amenity-types/{id} | FacilityManagement.tsx |
| `feature` | Master | Room feature (shown as "Room Amenities" tab). | `id` | device_type, facility, package_feature | Room / Occupancy | catalog.py `list_features`; facility_write.py create/update | GET/POST /features, PATCH /features/{id} | FacilityManagement.tsx |
| `package` | Master | Room package / rate plan (no price column) | `id` | amenity, amenity_type, attachment, facility, package_feature +3 | Room / Occupancy | catalog.py `list_packages`, `get_package`; facility_write.py create/update (status 0 = soft delete) | GET/POST /packages, PATCH /packages/{id} | FacilityManagement.tsx |
| `package_feature` | Configuration | Package ↔ feature link. | `id` | feature, package | Room / Occupancy | catalog.py (feature names); facility_write.py (replace on package write) | Inside POST/PATCH /packages (`feature_ids`) | FacilityManagement.tsx (display only; never sends feature_ids) |
| `sub_package` | Configuration | Parent package → child package link. | `parent_package_id, sub_package_id` | package | Room / Occupancy | None (app uses `package.is_sub_package` instead) | None | None found |
| `import_job` | Transaction / Operational | Bulk import job tracking (booking / job order CSV). | `id` | — | Booking / Stay | None | None | None (Bookings import shows a 'not connected' toast) |
| `invoice` | Transaction / Operational | Stay invoice with billing & facility snapshot and amounts. | `id` | app_user, attachment, facility, stay | Booking / Stay | stay.py `list_invoices`, `get_invoice` (read only; generation not implemented) | GET /invoices[/{id}] | None (`useInvoices` unused; Invoice button disabled) |
| `room_allocation` | Transaction / Operational | Which room(s) a stay holds (stay ↔ amenity) with package. | `id` | amenity, package, stay | Booking / Stay | stay.py `stay_room_allocations`; stays_write.py `create_stay`, `allocate_room`, `reallocate_room`, `release_allocation`; occupancy.py | GET/POST /stays/{id}/room-allocations, PATCH/DELETE /room-allocations/{id} | Bookings.tsx (on create), ReallocateRoomDialog.tsx |
| `stay` | Transaction / Operational | The reservation/booking and its check-in/check-out lifecycle (`stay_status` enum) | `id` | access_key, activity, app_user, invoice, lock_activity_log +8 | Booking / Stay | stay.py `list_stays`, `get_stay`; stays_write.py `create_stay`, `update_stay`, `check_in`, `check_out`, `extend_stay`, `set_stay_status`, `set_document_approval`, `cancel_stay`; occupancy.py, reports.py | GET/POST /stays, GET/PATCH /stays/{id}, POST /stays/{id}/check-in\|check-out\|extend\|status\|documents/approval\|cancel | Bookings.tsx, RoomView.tsx, Occupancy.tsx (current stay), CheckOutConfirmDialog.tsx |
| `stay_package` | Transaction / Operational | Packages purchased on a stay. | `id` | package, stay | Booking / Stay | stay.py `stay_packages` (read only) | Inside GET /stays/{id} | None found |
| `stay_user` | Transaction / Operational | Occupants (guests) of a stay, optionally per room. | `id` | amenity, app_user, stay | Booking / Stay | stay.py `stay_occupants`; stays_write.py `add_occupant`, `remove_occupant`; occupancy.py `get_occupancy` | GET/POST /stays/{id}/occupants, DELETE /stay-occupants/{id} | RoomDetailsModal.tsx via /occupancy/{id} (occupant hooks unused) |
| `user_document` | Transaction / Operational | Guest ID-proof document pointer with approval status. | `id` | app_user, attachment, stay | Booking / Stay | stay.py `stay_documents` (read only) | GET /stays/{id}/documents | None found |
| `room_service_request` | Transaction / Operational | Guest-app in-room service call with its own 4-value enum (unassigned/assigned/cancelled/completed). | `id` | amenity, app_user, room_service_request_item, stay | Service Requests | None | None | None found |
| `room_service_request_item` | Transaction / Operational | Items of a room service call. | `id` | room_service_request, service_category_item | Service Requests | None | None | None found |
| `service_category` | Master | Category under a service type (e.g | `id` | attachment, facility, maintenance_request, service_category_item, service_request +2 | Service Requests | service.py `list_service_categories`; services_write.py create/update | GET/POST /service-categories, GET/PATCH /service-categories/{id} | ServicesSetup.tsx, ServicePlanning.tsx |
| `service_category_item` | Master | Requestable item with price; JSONB metadata. | `id` | amenity, attachment, facility, maintenance_request, room_service_request_item +2 | Service Requests | service.py `list_service_items`; services_write.py create/update | GET/POST /service-items, GET/PATCH /service-items/{id} | ServicesSetup.tsx |
| `service_request` | Transaction / Operational | Service ticket (tracking & tickets), status FK → service_status. | `id` | amenity, app_user, department, facility, promo_code +5 | Service Requests | service.py `list_service_requests`, `get_service_request`; services_write.py `create_service_request`, `update_service_request`, `cancel_service_request`; reports.py | GET/POST /service-requests, GET/PATCH /service-requests/{id}, POST /service-requests/{id}/cancel | Tickets.tsx, ServiceTracking.tsx, ServiceRequestActionsDialog.tsx, RoomDetailsModal.tsx, AlertsPanel.tsx |
| `service_request_item` | Transaction / Operational | Line items of a service request. | `id` | app_user, service_category, service_category_item, service_request, service_status | Service Requests | service.py `request_items`; services_write.py `replace_service_request_items` (hard delete + insert) | PUT /service-requests/{id}/items; inside GET /service-requests/{id} | None found |
| `service_status` | Reference | Request lifecycle lookup: 1 Pending, 2 Assigned, 3 Partially completed, 4 Completed, 5 Canceled. | `id` | maintenance_request, service_request, service_request_item | Service Requests | service.py `list_service_statuses`; services_write.py / maintenance_write.py (hardcoded ids) | GET /service-statuses[/{id}] | ServiceRequestActionsDialog.tsx, ServiceTracking.tsx |
| `service_type` | Reference | 7 service types (Room Service, Travel Desk, … Sanitation Maintenance). | `id` | service_category, service_request | Service Requests | service.py `list_service_types`, `get_service_type`, `service_type_counts` | GET /service-types[/{id}] | ServiceTracking.tsx, Tickets.tsx, ServicesSetup.tsx, ServicePlanning.tsx |
| `maintenance_request` | Transaction / Operational | Scheduled / planned / disinfection maintenance work; status FK → service_status; soft delete via status 0. | `id` | access_key, department, facility, maintenance_request_amenity, maintenance_request_assignee +4 | Maintenance (Service Planning) | maintenance.py `list_maintenance_requests`, `get_maintenance_request`; maintenance_write.py create/update/cancel/remove; reports.py | GET/POST /maintenance-requests, GET/PATCH/DELETE /maintenance-requests/{id}, POST …/{id}/cancel | ServicePlanning.tsx |
| `maintenance_request_amenity` | Transaction / Operational | Rooms covered by a maintenance request. | `id` | amenity, maintenance_request | Maintenance (Service Planning) | maintenance.py; maintenance_write.py (replace via status 0/1) | Inside /maintenance-requests (`amenity_ids`) | ServicePlanning.tsx |
| `maintenance_request_assignee` | Transaction / Operational | Staff assigned to a maintenance request. | `id` | app_user, maintenance_request | Maintenance (Service Planning) | maintenance.py; maintenance_write.py (replace via status 0/1) | Inside /maintenance-requests (`assignee_ids`) | ServicePlanning.tsx |
| `maintenance_request_recurrence` | Configuration | 1:1 weekly recurrence rule (days_of_week bitmask). | `maintenance_request_id` | maintenance_request | Maintenance (Service Planning) | maintenance.py; maintenance_write.py (hard delete when rule dropped) | Inside /maintenance-requests (`recurrence`) | ServicePlanning.tsx |
| `job_order` | Transaction / Operational | Field work order (installation/replacement/troubleshoot) | `id` | app_user, job_order_amenity, job_order_device | Job Orders | job_order.py `list_job_orders`, `get_job_order`; job_order_write.py `create_job_order`, `update_job_order`, `remove_job_order` (soft) | GET/POST /job-orders, GET/PATCH/DELETE /job-orders/{id} | JobOrder.tsx |
| `job_order_amenity` | Transaction / Operational | Rooms on a job order. | `job_order_id, amenity_id` | amenity, job_order | Job Orders | job_order.py; job_order_write.py (hard delete + insert) | Inside /job-orders | JobOrder.tsx |
| `job_order_device` | Transaction / Operational | Devices on a job order. | `job_order_id, device_id` | device, job_order | Job Orders | job_order.py; job_order_write.py (hard delete + insert) | Inside /job-orders | JobOrder.tsx |
| `battery_life_stat` | Audit / History | Battery charge cycles per device. | `id` | device | Devices & IoT | device.py (health) | GET /devices/{id}/health | None found |
| `command_type` | Reference | Device command registry (Keys, FirmwareUpdates, Checkout…). | `id` | device_command, device_type | Devices & IoT | None | None | None found |
| `device` | Master | Physical smart device installed in a room; `parent_device_id` points to its hub. | `id` | access_key, amenity, battery_life_stat, device_alert, device_command +14 | Devices & IoT | device.py `list_devices`/`get_device`; devices_write.py `create_device`, `update_device`, `set_device_config_status` | GET/POST /devices, GET/PATCH /devices/{id}, POST /devices/{id}/commission\|decommission\|maintenance | LimitConfigAlert.tsx, JobOrder.tsx, RoomDetailsModal.tsx, RoomDetailsPanel.tsx, StatusSection.tsx (no UI for device writes) |
| `device_command` | Transaction / Operational | Outbound command queue to devices. | `id` | command_type, device | Devices & IoT | None | None | None found |
| `device_current_stat` | Transaction / Operational | Latest JSONB snapshot per device. | `id` | device | Devices & IoT | telemetry.py `list_device_current_stats` | GET /device-current-stats[/{id}] | None (`useDeviceCurrentStats` unused) |
| `device_health_stat` | Audit / History | Device heartbeat / health & temperature log. | `id` | device | Devices & IoT | device.py (health) | GET /devices/{id}/health | None found |
| `device_param` | Reference | EAV parameter definitions per device type (name, data type, unit). | `id` | device_stat, device_type | Devices & IoT | telemetry.py `list_device_params`; energy.py `active_energy_unit` | GET /device-params[/{id}] | LimitConfigAlert.tsx |
| `device_stat` | Audit / History | Time-series telemetry values (EAV: device × param × timestamp → value as text). | `id` | device, device_param | Devices & IoT | telemetry.py `list_device_stats`, `get_device_stat` | GET /device-stats[/{id}] | RoomPowerEnergy.tsx, RoomDetailsPanel.tsx |
| `device_type` | Reference | 4 device families: Intellihub (HUB), AirQ, Mikos, Kleio. | `id` | command_type, device, device_param, feature, firmware +2 | Devices & IoT | device.py list/get; joined in telemetry/alert/job order | GET /device-types[/{id}] | JobOrder.tsx |
| `firmware` | Master | Firmware build per device type; device current/expected version. | `id` | device, device_type | Devices & IoT | device.py (joined); devices_write.py (validation) | None of its own (firmware routes removed) | None found |
| `mqtt_broker` | Configuration | MQTT broker connection details per facility. | `id` | facility, mqtt_topic | Devices & IoT | None | None | None found |
| `mqtt_topic` | Configuration | MQTT topic per device/broker. | `id` | device, mqtt_broker | Devices & IoT | None | None | None found |
| `sensor_operation_stat` | Audit / History | Daily sensor uptime percentage. | `device_id, stats_date` | amenity, device | Devices & IoT | device.py (health) | GET /devices/{id}/health | None found |
| `energy_stat` | Audit / History | Hourly energy consumption per device name / room. | `device_name, facility_id, amenity_id, hour` | amenity, facility | Energy | energy.py `list_energy_stats`, `energy_summary`; reports.py (energy report) | GET /energy-stats, GET /energy-stats/summary | EnergyConsumptionChart.tsx, DashboardKPIs.tsx, RoomPowerEnergy.tsx |
| `other_device` | Audit / History | Third-party meter readings (voltage/current/power/energy); no FK, keyed by device_name text. | `id` | — | Energy | telemetry.py `list_other_device_readings` | GET /other-device-readings[/{id}] | None (`useOtherDeviceReadings` unused) |
| `daily_dual_data_point` | Audit / History | Daily KPI numerator/denominator per metric type (smart room, service request, checkout, booking, guest room). | `metric_date, metric_type` | facility | Dashboard / Reporting | energy.py `list_daily_data_points`, `caleido_at_work`, `get_daily_data_point` | GET /daily-data-points, …/summary, …/{metric_date}/{metric_type} | CaleidoAtWork.tsx |
| `alert_type` | Reference | 16 alert types (BatteryLow, DoorAjar, HubOffline…). | `id` | device_alert, device_incident | Alerts & Incidents | alert.py list/get/counts | GET /alert-types[/{id}] | None directly (Reports filter options) |
| `device_alert` | Transaction / Operational | Raw device alert stream. | `id` | alert_type, amenity, device, device_incident | Alerts & Incidents | alert.py `list_alerts`, `get_alert`; reports.py | GET /alerts[/{id}], GET /alerts/{id}/incidents | AlertsPanel.tsx, DashboardKPIs.tsx |
| `device_incident` | Transaction / Operational | Assignable incident case raised from alerts. | `id` | alert_type, amenity, app_user, device, device_alert +3 | Alerts & Incidents | alert.py `list_incidents`, `get_incident`; devices_write.py `update_incident` | GET /incidents[/{id}], PATCH /incidents/{id} | DashboardKPIs.tsx (counts only; no PATCH caller) |
| `incident_event` | Reference | Incident event lookup: Unread, Read, Assigned, Resolved, Reopened. | `id` | incident_history | Alerts & Incidents | alert.py; devices_write.py | None of its own | None found |
| `incident_history` | Audit / History | Audit trail of incident status events. | `id` | device_incident, incident_event | Alerts & Incidents | alert.py `incident_history`; devices_write.py `update_incident` (insert on status change) | Inside GET/PATCH /incidents/{id} | None found |
| `incident_status` | Reference | Incident status lookup: Unread, Read, Assigned, Resolved. | `id` | device_incident | Alerts & Incidents | alert.py; devices_write.py | None of its own | None found |
| `value_alert` | Transaction / Operational | Threshold breach raised against a limit config. | `id` | amenity, device, device_type, facility, value_alert_limit_config | Alerts & Incidents | alert.py `list_value_alerts`, `get_value_alert` | GET /value-alerts[/{id}] | DashboardKPIs.tsx |
| `value_alert_limit_config` | Configuration | Per device-name / parameter threshold configuration. | `id` | device, facility, value_alert | Alerts & Incidents | limit_config.py; devices_write.py `create_limit_config`, `update_limit_config` | GET/POST /limit-configs, PATCH /limit-configs/{id} | LimitConfigAlert.tsx |
| `app_user` | Master | Single identity table for guests and staff (`is_staff`), including login fields (user_name, password_hash) | `id` | access_key, activity, activity_notifier, amenity, amenity_type +45 | User / Staff / Guest | auth.py `authenticate`; access.py list/get; access_write.py `create_user`, `update_user`, `set_user_password`, `deactivate_user`, `reactivate_user` | POST /auth/login, GET /auth/me, GET/POST /users, GET/PATCH /users/{id}, POST /users/{id}/password\|deactivate\|reactivate | Login.tsx, Employees.tsx, Bookings.tsx (guest create), Tickets.tsx |
| `country` | Reference | Country / phone-code lookup (239 rows). | `id` | app_user | User / Staff / Guest | None (only the integer FK on app_user is projected) | None | None (Bookings hardcodes country codes) |
| `department` | Master | Staff department per facility. | `id` | app_user, facility, maintenance_request, service_request | User / Staff / Guest | access.py; access_write.py create/update; maintenance.py; service.py | GET/POST /departments, PATCH /departments/{id} | Employees.tsx, Tickets.tsx |
| `facility_user` | Configuration | Facility membership of a user. | `facility_id, app_user_id` | app_user, facility | User / Staff / Guest | access.py `user_facility_ids` (read only; never written by app) | Exposed as facility_ids in /auth/me, /users/{id} | AuthContext.tsx |
| `job_function` | Master | Staff job function per facility. | `id` | app_user, facility | User / Staff / Guest | access.py; access_write.py create/update | GET/POST /job-functions, PATCH /job-functions/{id} | Employees.tsx |
| `role` | Master | Named role per facility; `role_type` (admin/manager/staff/guest/system_user) gates HMS Web login. | `id` | activity_role_association, facility, role_module_permission, user_role | User / Staff / Guest | access.py; access_write.py `create_role`, `update_role`; auth.py | GET/POST /roles, GET/PATCH /roles/{id} | UserRoles.tsx |
| `role_module` | Reference | Registry of the 18 permission modules. | `id` | role_module_permission | User / Staff / Guest | access.py; auth.py `module_names` | GET /modules[/{id}] | UserRoles.tsx; mirrored in core/rbac/modules.ts |
| `role_module_permission` | Configuration | Read/write grant per role × module. | `role_id, module_id` | role, role_module | User / Staff / Guest | access.py; access_write.py `replace_role_permissions`; deps.py enforcement | GET /permissions, GET/PUT /roles/{id}/permissions | UserRoles.tsx, AuthContext.tsx |
| `user_role` | Configuration | Role held by a user at a facility. | `facility_id, app_user_id, role_id` | app_user, facility, role | User / Staff / Guest | access.py; access_write.py (replace on user write); auth.py | Inside POST/PATCH /users (`role_ids`) | Employees.tsx |
| `access_key` | Transaction / Operational | Issued digital door keys (app/keypad). | `id` | device, key_type, maintenance_request, stay, user_device_acl | Access / Keys | None | None | None found |
| `key_type` | Reference | Key type lookup: Primary, Shared, Staff, Default. | `id` | access_key, lock_activity_log | Access / Keys | None | None | None found |
| `lock_activity_log` | Audit / History | Door lock/unlock event log. | `id` | amenity, app_user, device, facility, key_type +1 | Access / Keys | None | None | None found |
| `user_device` | Transaction / Operational | User mobile device & push token. | `id` | app_user, stay, user_token | Access / Keys | None | None | None found |
| `user_device_acl` | Transaction / Operational | Time-boxed device access grant (user × device × stay). | `id` | access_key, amenity, amenity_type, app_user, device +2 | Access / Keys | None | None | None found |
| `user_token` | Transaction / Operational | API session tokens. | `id` | app_user, user_device | Access / Keys | None (JWT is stateless) | None | None found |
| `activity` | Audit / History | In-app activity feed event (polymorphic entity_id). | `id` | activity_notifier, activity_type, app_user, entity_type, facility +1 | Notifications & Activity | notification.py `list_activities`, `get_activity` (read only; nothing creates rows) | GET /activities[/{id}] | RecentActivityPanel.tsx |
| `activity_notifier` | Transaction / Operational | Per-user delivery / read state of an activity. | `activity_id, app_user_id` | activity, app_user | Notifications & Activity | notification.py `activity_notifiers` and filters | Inside /activities | RecentActivityPanel.tsx |
| `activity_role_association` | Configuration | Which roles are notified of which activity types. | `activity_type_id, role_id` | activity_type, role | Notifications & Activity | None | None | None found |
| `activity_type` | Reference | Activity taxonomy (22 types). | `id` | activity, activity_role_association, entity_type | Notifications & Activity | notification.py (joined) | Inside /activities | RecentActivityPanel.tsx |
| `entity_type` | Reference | Entity lookup: Booking, Occupancy, Service Requests, Maintenance Requests, Default Key. | `id` | activity, activity_type | Notifications & Activity | notification.py (joined) | Inside /activities | RecentActivityPanel.tsx |
| `notification` | Transaction / Operational | Notification dispatch queue entry. | `id` | notification_receiver, notification_template | Notifications & Activity | notification.py `list_notifications`, `get_notification` (read only) | GET /notifications[/{id}] | None found |
| `notification_receiver` | Transaction / Operational | Recipient of a notification. | `id` | app_user, notification, notification_result | Notifications & Activity | notification.py `notification_receivers` | Inside GET /notifications/{id} | None found |
| `notification_result` | Audit / History | Per-channel delivery outcome. | `id` | notification_receiver | Notifications & Activity | notification.py | Inside GET /notifications/{id} | None found |
| `notification_template` | Configuration | Notification template per channel. | `id` | notification | Notifications & Activity | notification.py `list_templates`, `get_template` | GET /notification-templates[/{id}] | UserRoles.tsx (picker; selection never saved) |
| `promo_code` | Master | Offer / discount coupon. | `id` | attachment, promo_code_amenity, service_request | Marketing (Offers) | catalog.py `list_promo_codes`, `get_promo_code`; facility_write.py create/update; services_write.py (FK check) | GET/POST /offers, PATCH /offers/{id} | Offers.tsx |
| `promo_code_amenity` | Configuration | Rooms an offer applies to. | `promo_code_id, amenity_id` | amenity, promo_code | Marketing (Offers) | catalog.py; facility_write.py (delete + insert) | Inside /offers (`amenity_ids`) | Offers.tsx |
| `facility_event` | Master | Hotel event (venue, dates, attendees, cancellation). | `id` | attachment, facility | Marketing (Events) | catalog.py `list_events`; facility_write.py create/update | GET/POST /events, PATCH /events/{id} | Events.tsx |
| `occasion` | Master | Holidays and other occasions (festival, birthday, anniversary) with dates, repeat flag, hub notification. | `id` | app_user, facility, occasion_type | Holiday Management | catalog.py `list_occasions`, `get_occasion`; facility_write.py `create_occasion`, `update_occasion` | GET/POST /holidays, PATCH /holidays/{occasion_id} | Holidays.tsx |
| `occasion_type` | Reference | Occasion type lookup: Festival, Birthday, Marriage anniversary, Holiday. | `id` | occasion | Holiday Management | catalog.py `list_occasion_types`; facility_write.py (validation) | GET /holidays/types | Holidays.tsx |
| `scheduler_job` | Configuration | Scheduled / cron job definitions. | `id` | scheduler_job_execution | Scheduler | None | None | None found |
| `scheduler_job_execution` | Audit / History | Scheduler run history. | `id` | scheduler_job | Scheduler | None | None | None found |
| `attachment` | Master | File registry (file name/path) referenced as image/document by 10 tables. | `id` | amenity_type, facility, facility_event, invoice, package +5 | Shared | None directly (only FK ids echoed) | None (no upload endpoint) | None (upload inputs in UI have no handler) |
| `alembic_version` | Other | Alembic migration head marker (value `0e2687233b59`). | `version_num` | — | System | Alembic only | None | None found |

---

## 12. Final actionable findings

Items are **not ranked**; the project defines no priority. Each has evidence in the repository or live database.

### A. Confirmed issues

**Action Item A1 — Room status and stay data disagree**
- **Finding:** `amenity.status` says rooms are Occupied or Allotted that have no stay or allocation.
- **Evidence:** Live: rooms 201 (Occupied) and 108 (Allotted) have no `room_allocation`; 3 amenities are Occupied vs 1 in-house stay. Seed plan `backend/seeds/steps/rooms.py:80-92`. `update_room_state` allows Occupied with no stay (`stays_write.py:588-598`). Documented at `endpoints/occupancy.py:10-17`.
- **Affected:** amenity, stay, room_allocation / Occupancy, Dashboard.
- **Why it needs attention:** occupancy KPIs are internally inconsistent.
- **Recommended next investigation:** confirm which source is authoritative; list all writers of `amenity.status` (§8.3).

**Action Item A2 — "Total Rooms" counts non-room amenities**
- **Finding:** Dashboard / donut denominators include the restaurant, gym and conference room.
- **Evidence:** `useCount("occupancy")` with no category filter (`OccupancyStatisticsChart.tsx:63`, `DashboardKPIs.tsx` OccupancyTile). Live 27 vs 24.
- **Affected:** Occupancy KPIs.
- **Why it needs attention:** occupancy percentages are understated.
- **Recommended next investigation:** confirm the intended denominator (guest rooms only?).

**Action Item A3 — Package and Room creation cannot succeed from the UI**
- **Finding:** Hardcoded select values never match DB names, so submit silently returns.
- **Evidence:** `FacilityManagement.tsx:307-310, 326-331` vs options at `:722-724, 1075-1092`.
- **Affected:** amenity, package / Facility Management.
- **Why it needs attention:** configuration data cannot be added.
- **Recommended next investigation:** reproduce in the running UI; confirm the intended option source.

**Action Item A4 — Limit Config creation cannot succeed from the UI**
- **Finding:** Device option value is the name, but lookup is by id.
- **Evidence:** `LimitConfigAlert.tsx:138-139` vs `:200`.
- **Affected:** value_alert_limit_config.
- **Why it needs attention:** thresholds cannot be configured.
- **Recommended next investigation:** reproduce in the UI.

**Action Item A5 — Offer edit always rejected**
- **Finding:** The UI sends `promo_code`, which `PromoCodeUpdate` does not accept.
- **Evidence:** `Offers.tsx` edit body; `schemas/ops_write.py:411-421`; `extra="forbid"` at `:43-45`.
- **Affected:** promo_code / Offers.
- **Why it needs attention:** offers cannot be edited.
- **Recommended next investigation:** reproduce with an authenticated session.

**Action Item A6 — Holidays list includes non-holidays and retired rows**
- **Finding:** There is no type or status filter.
- **Evidence:** `catalog.py:307`; live Pongal = Festival; `Holidays.tsx:134` soft delete.
- **Affected:** occasion / Holiday Management.
- **Why it needs attention:** the screen misrepresents the holiday calendar.
- **Recommended next investigation:** confirm which occasion types belong on the Holidays screen.

**Action Item A7 — Holiday form data is discarded or mis-stored**
- **Finding:** "Description" text is dropped and "Lock message" goes to `occasion_name`.
- **Evidence:** `Holidays.tsx:99-106`; `models/marketing.py:145-149`.
- **Affected:** occasion.
- **Why it needs attention:** user input is lost.
- **Recommended next investigation:** confirm the field mapping with the product owner.

**Action Item A8 — Energy stats cannot be linked to devices**
- **Finding:** `energy_stat.device_name` matches no device.
- **Evidence:** Live: 0 of 72 rows match `device.device_name` / `device_uid`. No FK (`models/reporting.py`). Comment at `services/energy.py:45-47`.
- **Affected:** energy_stat / Energy.
- **Why it needs attention:** per-device energy is impossible.
- **Recommended next investigation:** identify the naming convention of the external ingester.

**Action Item A9 — `room_allocation.status` is never updated**
- **Finding:** It stays 1 after check-out and cancel.
- **Evidence:** `stays_write.py:91`; live data.
- **Affected:** room_allocation.
- **Why it needs attention:** current and historical allocations are indistinguishable.
- **Recommended next investigation:** confirm the intended lifecycle.

**Action Item A10 — Service request status can move out of terminal states**
- **Finding:** PATCH accepts any status 1–5, including Completed → Canceled or Pending. Only the cancel endpoint blocks it.
- **Evidence:** `services_write.py:189-208` vs `:241-242`.
- **Affected:** service_request.
- **Why it needs attention:** closed tickets can be reopened silently.
- **Recommended next investigation:** confirm allowed transitions. "Partially completed" (id 3) is defined (`STATUS_PARTIAL`, `services_write.py:54`) but never derived from items.

**Action Item A11 — Hardcoded fake data displayed**
- **Finding:** The Service Tracking items modal shows static Wipes / Trimmer / Soap.
- **Evidence:** `ServiceTracking.tsx:916-926`.
- **Affected:** service_request_item.
- **Why it needs attention:** users see fabricated line items.
- **Recommended next investigation:** confirm which data the modal should show.

**Action Item A12 — Counts computed from one page of 100**
- **Finding:** Room View and Service Tracking tally `items.length`.
- **Evidence:** `RoomView.tsx:44,60-70`; `ServiceTracking.tsx:149-161`.
- **Affected:** Occupancy, Services.
- **Why it needs attention:** counts are wrong beyond 100 rows.
- **Recommended next investigation:** confirm expected data volumes.

### B. Missing information / needs verification

**B1 — IoT ingestion path**
- **Finding:** No code writes telemetry, alerts, activity or notifications.
- **Evidence:** §7.2 (grep for constructors in services and api).
- **Why:** the source and freshness of Dashboard data cannot be verified.
- **Next:** locate the external ingester (Porta / IKANOS?).

**B2 — Payment process**
- **Finding:** Not Found; invoice is read-only.
- **Evidence:** §4.9.
- **Why:** billing may be expected in HMS scope.
- **Next:** confirm whether payment is out of scope.

**B3 — Guest-app room service**
- **Finding:** `room_service_request` has seeded data but no code.
- **Evidence:** §4.11; `backend/seeds/steps/services.py`.
- **Why:** there are two models of "Room Service".
- **Next:** confirm whether Porta writes these rows.

**B4 — Double-booking under concurrency**
- **Finding:** There is only an application-level check.
- **Evidence:** I-3.
- **Why:** a race is possible but was not observed.
- **Next:** concurrency test.

**B5 — Runtime behaviour of UI write paths**
- **Finding:** A3–A5 are established from code only.
- **Evidence:** No authenticated session was used (§0.1).
- **Why:** end-to-end confirmation is pending.
- **Next:** reproduce with a real login.

**B6 — Multi-facility scope**
- **Finding:** There is no facility isolation, and several tables lack `facility_id`.
- **Evidence:** I-4.
- **Why:** it matters only if more than one facility is planned.
- **Next:** product decision.

### C. Documentation gaps

**C1 — `NEEDS_REVIEW.md` describes a superseded schema**
- **Finding:** It covers the older 36/39-entity design (`booking`, `employee`, `maintenance_schedule`, `app_user_user_role`, `energy_aggregate`), none of which exist in the live DB. `PHASE1_REPORT.md` and `IKANOS_HMS_SCHEMA_COMPARISON.md` also reference `booking`.
- **Evidence:** `backend/docs/NEEDS_REVIEW.md` §B–E; the README lists it as the current "open schema questions".
- **Affected:** docs.
- **Why:** readers will be misled about the current schema.
- **Next:** mark superseded docs; `PHASE1_7_DATABASE_IMPLEMENTATION.md` matches the live DB (240 FKs, 76 UQ, 34 enums).

**C2 — Stale code comments and docstrings**
- **Finding:** Several comments describe behaviour the code no longer has.
- **Evidence:**
  - `endpoints/occupancy.py:13-15` says "5 Occupied vs 3 in house" (live: 3 vs 1).
  - The occupancy/stay docs say reallocation writes a new row (code updates in place, `stays_write.py:454-456`).
  - `endpoints/devices.py` claims a "READ-ONLY" device API (writes exist in `devices_write.py`).
  - The booking report source says `stay_occupant` (the table is `stay_user`).
  - `ServiceTracking.tsx` / `Tickets.tsx` say "read-only / display-only" (they write).
- **Why:** they mislead maintainers.
- **Next:** doc review.

**C3 — No data dictionary for status values**
- **Finding:** Smallint `status` columns (0/1) have no CHECK constraint or lookup, and their meaning lives only in comments and Pydantic.
- **Evidence:** §3.2, §8.1.
- **Next:** document the allowed values per table.

**C4 — Holiday business rules undocumented**
- **Finding:** Which occasion types are "holidays", and what `notify_to_hub`, `is_repeatable` and lock message should do.
- **Evidence:** §9.
- **Next:** product sign-off.

### D. Implementation mismatches

**D1 — Schema max lengths vs column sizes**
- **Finding:** Pydantic allows longer strings than the columns hold.
- **Evidence:** I-5.
- **Affected:** amenity, occasion, promo_code, stay, service_request, device, event.

**D2 — UI labels vs DB meaning**
- **Finding:** Several screen labels describe a different column than the one shown or written.
- **Evidence:** §10.3.

**D3 — Two document-approval fields**
- **Finding:** `stay.document_approval_status` (2 values) is written; `user_document.document_approval_status` (3 values) never is.
- **Evidence:** `stays_write.set_document_approval` (:330); `models/enums.py`.

**D4 — Two service-request models and status vocabularies**
- **Finding:** `service_status` (5 rows, "Canceled") vs `room_service_request_status` enum (4 values, "cancelled", no "in progress").
- **Evidence:** live reference data; `models/enums.py`.

**D5 — Reads not facility-scoped although writes pick a default facility**
- **Finding:** Writes fill in a default facility; reads never filter by one.
- **Evidence:** `access_write.default_facility_id` (:355) vs optional `facility_id` on all reads.

**D6 — API capabilities without UI**
- **Finding:** Occupants, allocation release, stay status workflow, invoices, documents, device writes, incident updates, maintenance update/cancel and job-order remove all exist in the API with no screen.
- **Evidence:** §10.1; unused hooks in `hooks.ts` / `mutations.ts`.

### E. Further analysis required

**E1 — Index coverage**
- **Finding:** 86 FK columns have no index with that column leading.
- **Evidence:** live catalog query (§8.1).
- **Next:** check query plans once data volume grows.

**E2 — Reference-number generation**
- **Finding:** Max+1 scan of all rows per insert.
- **Evidence:** `writes.py:123-156`.
- **Next:** measure cost at volume; concurrency behaviour.

**E3 — Energy time buckets**
- **Finding:** Day buckets are UTC (`hour // 24`) while the UI window is local time (IST).
- **Evidence:** `energy.energy_summary` (:172).
- **Next:** confirm expected day boundaries.

**E4 — Permission merge across facilities**
- **Finding:** Login computes permissions with no facility filter.
- **Evidence:** `services/auth.py:84`.
- **Next:** review together with B6.

---

## 13. Final summary

| # | Item | Result |
|---|---|---|
| 1 | Total tables identified | **93** (92 HMS + `alembic_version`); 922 columns; 240 FKs; 76 unique; 34 enums; 0 views, triggers or CHECKs |
| 2 | Master + reference tables | **37** (20 master, 17 reference) |
| 3 | Transaction / operational tables | **30** |
| 4 | Configuration tables | **13** |
| 5 | Audit / history tables | **12** (+ 1 other: `alembic_version`) |
| 6 | Main HMS modules | Facility & Property (building/floor via property_chain), Room / Occupancy, Booking / Stay (incl. check-in/out), Service Requests, Maintenance (Service Planning), Job Orders, Devices & IoT, Energy, Alerts & Incidents, User / Staff / RBAC, Offers, Events, Holiday Management, Notifications & Activity (read-only), Reports. Schema-only: Access keys / locks, Scheduler, MQTT, Payment (Not Found). |
| 7 | Major relationships | facility → property → property_chain → amenity; amenity ↔ stay via room_allocation; stay → stay_user → app_user; amenity → device (hub hierarchy) → device_stat / device_alert → device_incident → incident_history; service_request → service_type / service_status / service_category / amenity / stay; app_user ↔ role via user_role; role ↔ role_module via role_module_permission; occasion → occasion_type |
| 8 | Major DB → API → UI flows | Occupancy (`GET /occupancy` → Occupancy / Dashboard), Bookings (`/stays` → Bookings), Services (`/service-requests` → Service Tracking / Tickets), Maintenance (`/maintenance-requests` → Service Planning), Energy (`/energy-stats/summary` → Dashboard / Room power), Alerts (`/alerts` → Dashboard), Auth (`/auth/login`, `/auth/me`), Holidays (`/holidays` → Holidays) — §5 |
| 9 | Holiday Management flow | `occasion` (+ `occasion_type`) → `catalog.list_occasions` / `facility_write.create_occasion` / `update_occasion` → `GET/POST /api/v1/holidays`, `GET /holidays/types`, `PATCH /holidays/{id}` → `useHolidays` / `createHoliday` / `updateHoliday` → `Holidays.tsx`. No year/state/country fields; no type or status filter; inert notify/repeat fields (§9) |
| 10 | Confirmed issues | A1–A12 (§12-A) |
| 11 | Items requiring further verification | B1–B6 and E1–E4 (§12-B, §12-E) |
