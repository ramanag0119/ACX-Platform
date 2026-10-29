# HMS Database Complete Table Inventory

**Audit Type:** Read-Only Complete Schema & Metadata Inventory  
**Date:** 2026-10-26  
**Target Database:** PostgreSQL 18.6 (`hms_db` @ `localhost:5432`)  
**Schema:** `public`  
**Total Verified Tables:** **94 tables** (93 Application Tables + 1 Migration Ledger)  
**Total Database Views:** **0 views** (Verified via PostgreSQL `information_schema.views`)

---

## 1. Inventory Summary by Functional Group

| Group ID | Functional Group | Table Count | Sample Tables |
|---|---|---:|---|
| **Group A** | Organisation & Facility Hierarchy | 8 | `organisation`, `facility`, `facility_user`, `property`, `property_chain` |
| **Group B** | Rooms, Amenities & Packages | 10 | `amenity`, `amenity_type`, `amenity_status`, `amenity_condition`, `package` |
| **Group C** | Stays, Reservations & Billing | 7 | `stay`, `stay_user`, `room_allocation`, `invoice`, `user_document` |
| **Group D** | People, Staff & RBAC | 9 | `app_user`, `role`, `user_role`, `department`, `job_function`, `role_module` |
| **Group E** | Services, Dining & Requests | 8 | `service_request`, `service_category`, `service_category_item`, `service_type` |
| **Group F** | Maintenance Planning | 4 | `maintenance_request`, `maintenance_request_recurrence`, `assignee`, `amenity` |
| **Group G** | IoT Devices & Telemetry | 14 | `device`, `device_type`, `device_stat`, `device_current_stat`, `energy_stat` |
| **Group H** | Job Orders | 3 | `job_order`, `job_order_amenity`, `job_order_device` |
| **Group I** | Access Control & Digital Keys | 4 | `access_key`, `key_type`, `lock_activity_log`, `user_device_acl` |
| **Group J** | Alerts & Incidents | 8 | `device_alert`, `alert_type`, `device_incident`, `incident_history`, `value_alert` |
| **Group K** | Activity Feed & Notifications | 9 | `activity`, `activity_notifier`, `notification`, `notification_template` |
| **Group L** | Schedulers | 2 | `scheduler_job`, `scheduler_job_execution` |
| **Group M** | Marketing, Events & Holidays | 5 | `promo_code`, `facility_event`, `occasion`, `occasion_type` |
| **Group N** | Reporting & Operational KPIs | 2 | `daily_dual_data_point`, `energy_stat` |
| **Group O** | Infrastructure | 1 | `alembic_version` |

---

## 2. Detailed Table Specifications (All 94 Tables)

### access_key

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Digital room access keys and PINs issued to guests or staff for room door locks.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `AccessKey` in [AccessKey](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/access.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `device_id` -> `device(id)`
- `key_type` -> `key_type(id)`
- `maintenance_request_id` -> `maintenance_request(id)`
- `stay_id` -> `stay(id)`
- `user_device_acl_id` -> `user_device_acl(id)`

**Key Columns Sample (13 of 13 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `user_device_acl_id` | `UUID` | YES |  |
| `app_key` | `VARCHAR(10)` | NO |  |
| `keypad_key` | `VARCHAR(10)` | NO |  |
| `key_type` | `SMALLINT` | NO |  |
| `device_id` | `UUID` | YES |  |
| `stay_id` | `UUID` | YES |  |
| `maintenance_request_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### activity

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** System-wide activity audit trail and event log.
- **Primary Key:** `id`
- **Row Count (Live DB):** `10`
- **ORM Model:** `Activity` in [Activity](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `activity_type_id` -> `activity_type(id)`
- `actor_id` -> `app_user(id)`
- `entity_type_id` -> `entity_type(id)`
- `facility_id` -> `facility(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (13 of 13 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `activity_type_id` | `SMALLINT` | NO |  |
| `entity_type_id` | `SMALLINT` | NO |  |
| `entity_id` | `BIGINT` | NO |  |
| `facility_id` | `UUID` | NO |  |
| `actor_id` | `UUID` | NO |  |
| `stay_id` | `UUID` | YES |  |
| `activity_response_ids` | `TEXT` | YES |  |
| `data_version` | `SMALLINT` | NO |  |
| `data` | `JSONB` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### activity_notifier

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Per-user read/unread indicators for in-app header notification feed.
- **Primary Key:** `activity_id, app_user_id`
- **Row Count (Live DB):** `15`
- **ORM Model:** `ActivityNotifier` in [ActivityNotifier](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `activity_id` -> `activity(id)`
- `app_user_id` -> `app_user(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `activity_id` | `BIGINT` | NO |  |
| `app_user_id` | `UUID` | NO |  |
| `status` | `VARCHAR(1)` | NO |  |
| `user_type` | `VARCHAR(1)` | YES |  |
| `notification_type` | `SMALLINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### activity_role_association

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Role-based subscription matrix for activity notifications.
- **Primary Key:** `activity_type_id, role_id`
- **Row Count (Live DB):** `34`
- **ORM Model:** `ActivityRoleAssociation` in [ActivityRoleAssociation](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `activity_type_id` -> `activity_type(id)`
- `role_id` -> `role(id)`

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `activity_type_id` | `SMALLINT` | NO |  |
| `role_id` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### activity_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Taxonomy of audit events and in-app activity types.
- **Primary Key:** `id`
- **Row Count (Live DB):** `22`
- **ORM Model:** `ActivityType` in [ActivityType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `entity_type_id` -> `entity_type(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `activity_type` | `VARCHAR(50)` | NO |  |
| `entity_type_id` | `SMALLINT` | NO |  |
| `notification_type` | `CHAR(3)` | NO |  |
| `is_subscribable` | `BOOLEAN` | YES | true |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### alembic_version

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Infrastructure**
- **Business Purpose:** Database schema migration version ledger for Alembic.
- **Primary Key:** `version_num`
- **Row Count (Live DB):** `1`
- **ORM Model:** None (Migration / Internal)
- **Existence Status:** Live DB (YES) · Source Code (NO) · Migrations (YES)
- **Verification Status:** Verified (Alembic Migration Tracker)

**Foreign Key Relationships:**
None

**Key Columns Sample (1 of 1 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `version_num` | `VARCHAR(32)` | NO |  |

---

### alert_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Taxonomy of system and sensor alert types (smoke, door ajar, offline, threshold).
- **Primary Key:** `id`
- **Row Count (Live DB):** `16`
- **ORM Model:** `AlertType` in [AlertType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### amenity

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Physical room units and hotel facilities inventory.
- **Primary Key:** `id`
- **Row Count (Live DB):** `27`
- **ORM Model:** `Amenity` in [Amenity](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_type_id` -> `amenity_type(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `package_id` -> `package(id)`
- `parent_amenity_id` -> `amenity(id)`
- `property_chain_id` -> `property_chain(id)`
- `status` -> `amenity_status(id)`

**Key Columns Sample (15 of 15 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(6)` | NO |  |
| `parent_amenity_id` | `UUID` | YES |  |
| `amenity_type_id` | `UUID` | NO |  |
| `facility_id` | `UUID` | YES |  |
| `property_chain_id` | `UUID` | YES |  |
| `package_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '2'::smallint |
| `is_dnd` | `SMALLINT` | YES |  |
| `power_save_mode` | `SMALLINT` | YES |  |
| `metadata` | `JSONB` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### amenity_condition

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Housekeeping condition labels (Clean, Dirty, Under Maintenance, etc.).
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `AmenityCondition` in [AmenityCondition](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(45)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |
| `display_name` | `VARCHAR(100)` | YES |  |
| `applicable_to_occupied` | `BOOLEAN` | NO | true |
| `applicable_to_vacant` | `BOOLEAN` | NO | true |
| `is_active` | `BOOLEAN` | NO | true |

---

### amenity_condition_status

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Active condition state for each physical room.
- **Primary Key:** `amenity_id, amenity_condition_id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `AmenityConditionStatus` in [AmenityConditionStatus](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_condition_id` -> `amenity_condition(id)`
- `amenity_id` -> `amenity(id)`

**Key Columns Sample (5 of 5 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `amenity_id` | `UUID` | NO |  |
| `amenity_condition_id` | `SMALLINT` | NO |  |
| `status` | `SMALLINT` | NO | '1'::smallint |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### amenity_status

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Occupancy status vocabulary (Available, Occupied, Unavailable, Allotted).
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `AmenityStatus` in [AmenityStatus](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `amenity_status_name` | `VARCHAR(100)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### amenity_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Room categories and classification (Deluxe Room, Suite, Banquet).
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `AmenityType` in [AmenityType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `image_id` -> `attachment(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | NO |  |
| `amenity_category` | `VARCHAR(10)` | NO | 'others'::amenity_category |
| `image_id` | `UUID` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### app_user

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Authoritative user account directory for staff and guests; stores bcrypt password hashes.
- **Primary Key:** `id`
- **Row Count (Live DB):** `15`
- **ORM Model:** `AppUser` in [AppUser](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `country` -> `country(id)`
- `created_by` -> `app_user(id)`
- `department_id` -> `department(id)`
- `job_function_id` -> `job_function(id)`
- `nationality` -> `country(id)`
- `supervisor` -> `app_user(id)`

**Key Columns Sample (15 of 29 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `user_uid` | `VARCHAR(72)` | NO |  |
| `first_name` | `VARCHAR(100)` | NO |  |
| `last_name` | `VARCHAR(100)` | YES |  |
| `email` | `VARCHAR(256)` | YES |  |
| `country` | `SMALLINT` | YES |  |
| `phone_number` | `VARCHAR(15)` | NO |  |
| `alternate_phone_number` | `VARCHAR(15)` | YES |  |
| `gender` | `VARCHAR(6)` | YES |  |
| `dob` | `DATE` | YES |  |
| `is_child` | `SMALLINT` | NO | '0'::smallint |
| `age` | `SMALLINT` | YES |  |
| `is_staff` | `SMALLINT` | YES | '1'::smallint |
| `date_of_joining` | `TIMESTAMP` | YES |  |
| `date_of_termination` | `TIMESTAMP` | YES |  |
| `supervisor` | `UUID` | YES |  |
*... and 14 more columns*

---

### attachment

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** File attachment registry for images, logos, guest documents.
- **Primary Key:** `id`
- **Row Count (Live DB):** `8`
- **ORM Model:** `Attachment` in [Attachment](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | YES |  |
| `file_name` | `VARCHAR(100)` | NO |  |
| `file_path` | `VARCHAR(256)` | NO |  |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### battery_life_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Battery life monitoring for wireless locks and battery-powered sensors.
- **Primary Key:** `id`
- **Row Count (Live DB):** `12`
- **ORM Model:** `BatteryLifeStat` in [BatteryLifeStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `cycle_number` | `SMALLINT` | NO |  |
| `initial_battery_percentage` | `NUMERIC(5, 2)` | YES |  |
| `latest_battery_percentage` | `NUMERIC(5, 2)` | YES |  |
| `battery_life` | `NUMERIC(6, 2)` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### command_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Registry of valid command types per device class.
- **Primary Key:** `id`
- **Row Count (Live DB):** `10`
- **ORM Model:** `CommandType` in [CommandType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `device_type_id` -> `device_type(id)`

**Key Columns Sample (5 of 5 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `device_type_id` | `SMALLINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### country

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** ISO country and phone code reference data (239 countries).
- **Primary Key:** `id`
- **Row Count (Live DB):** `239`
- **ORM Model:** `Country` in [Country](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `phone_code` | `VARCHAR(10)` | NO |  |
| `iso_code` | `VARCHAR(10)` | YES |  |
| `nice_name` | `VARCHAR(50)` | NO |  |
| `iso3` | `VARCHAR(3)` | YES |  |
| `num_code` | `SMALLINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### daily_dual_data_point

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Aggregated daily operational and energy KPI metrics ('Caleido At Work').
- **Primary Key:** `metric_date, metric_type`
- **Row Count (Live DB):** `35`
- **ORM Model:** `DailyDualDataPoint` in [DailyDualDataPoint](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/reporting.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `facility_id` -> `facility(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `metric_date` | `DATE` | NO |  |
| `metric_type` | `VARCHAR(15)` | NO |  |
| `dp_1` | `NUMERIC(10, 2)` | NO |  |
| `dp_2` | `NUMERIC(10, 2)` | NO |  |
| `facility_id` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### department

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Hotel organizational departments (Front Office, Housekeeping, etc.).
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `Department` in [Department](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `department_name` | `VARCHAR(255)` | NO |  |
| `facility_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES |  |
| `department_key` | `VARCHAR(5)` | YES |  |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### device

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Physical IoT hardware registry (Intellihub, Mikos, AirQ, Kleio) located in rooms.
- **Primary Key:** `id`
- **Row Count (Live DB):** `14`
- **ORM Model:** `Device` in [Device](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `created_by` -> `app_user(id)`
- `current_firmware_version` -> `firmware(id)`
- `device_type` -> `device_type(id)`
- `expected_firmware_version` -> `firmware(id)`
- `facility_id` -> `facility(id)`
- `parent_device_id` -> `device(id)`

**Key Columns Sample (15 of 28 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_uid` | `VARCHAR(16)` | YES |  |
| `part_number` | `VARCHAR(50)` | YES |  |
| `model` | `VARCHAR(20)` | YES |  |
| `manufacturer_name` | `VARCHAR(50)` | YES |  |
| `mfg_date` | `TIMESTAMP` | NO |  |
| `parent_device_id` | `UUID` | YES |  |
| `device_type` | `SMALLINT` | NO |  |
| `device_name` | `VARCHAR(100)` | YES |  |
| `appliance_name` | `VARCHAR(50)` | YES |  |
| `facility_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `authentication_code` | `VARCHAR(20)` | YES |  |
| `health_status` | `VARCHAR(8)` | YES |  |
| `device_temperature` | `NUMERIC(10, 2)` | YES |  |
| `current_firmware_version` | `UUID` | YES |  |
*... and 13 more columns*

---

### device_alert

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Hardware and sensor alert stream surfaced in Dashboard and Reports.
- **Primary Key:** `id`
- **Row Count (Live DB):** `9`
- **ORM Model:** `DeviceAlert` in [DeviceAlert](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `alert_type` -> `alert_type(id)`
- `amenity_id` -> `amenity(id)`
- `created_by` -> `app_user(id)`
- `device_id` -> `device(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `alert_type` | `SMALLINT` | NO |  |
| `alert_severity` | `VARCHAR(8)` | YES |  |
| `alert_data` | `JSONB` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### device_command

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Hardware actuation command queue (lock/unlock, set temperature).
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `DeviceCommand` in [DeviceCommand](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `command_type` -> `command_type(id)`
- `created_by` -> `app_user(id)`
- `device_id` -> `device(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `command_type` | `SMALLINT` | NO |  |
| `command_data` | `JSONB` | NO |  |
| `processing_status` | `VARCHAR(10)` | YES | 'Queued'::command_processing_status |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### device_current_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Latest telemetry snapshot per device used in room detail and device tiles.
- **Primary Key:** `id`
- **Row Count (Live DB):** `14`
- **ORM Model:** `DeviceCurrentStat` in [DeviceCurrentStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `device_stats` | `JSONB` | YES |  |
| `is_other_device` | `INTEGER` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### device_health_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Technical health logs, ping times, uptime, and operating temperatures.
- **Primary Key:** `id`
- **Row Count (Live DB):** `168`
- **ORM Model:** `DeviceHealthStat` in [DeviceHealthStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `device_health_status` | `VARCHAR(8)` | NO |  |
| `device_temperature` | `NUMERIC(10, 2)` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### device_incident

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Tracked technical incidents and hardware failures created from alerts.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `DeviceIncident` in [DeviceIncident](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `alert_type` -> `alert_type(id)`
- `amenity_id` -> `amenity(id)`
- `assigned_to` -> `app_user(id)`
- `current_incident_status` -> `incident_status(id)`
- `device_id` -> `device(id)`
- `facility_id` -> `facility(id)`
- `latest_alert_id` -> `device_alert(id)`
- `updated_by` -> `app_user(id)`

**Key Columns Sample (14 of 14 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `device_id` | `UUID` | NO |  |
| `alert_type` | `SMALLINT` | NO |  |
| `subject` | `VARCHAR(200)` | YES |  |
| `description` | `TEXT` | YES |  |
| `assigned_to` | `UUID` | YES |  |
| `latest_alert_id` | `BIGINT` | YES |  |
| `current_incident_status` | `SMALLINT` | YES |  |
| `updated_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### device_param

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Telemetry parameter definitions (temperature, humidity, voltage, power).
- **Primary Key:** `id`
- **Row Count (Live DB):** `35`
- **ORM Model:** `DeviceParam` in [DeviceParam](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_type` -> `device_type(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_type` | `SMALLINT` | NO |  |
| `param_name` | `VARCHAR(50)` | NO |  |
| `data_type` | `VARCHAR(9)` | YES |  |
| `unit` | `VARCHAR(20)` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `INTEGER` | NO |  |

---

### device_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** High-volume time-series raw telemetry data from room sensors.
- **Primary Key:** `id`
- **Row Count (Live DB):** `504`
- **ORM Model:** `DeviceStat` in [DeviceStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`
- `device_param_id` -> `device_param(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `timestamp` | `TIMESTAMP` | NO |  |
| `device_param_id` | `INTEGER` | NO |  |
| `device_param_value` | `VARCHAR(500)` | YES |  |
| `is_other_device` | `INTEGER` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### device_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Catalog of supported hardware models and capabilities.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `DeviceType` in [DeviceType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (5 of 5 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | YES |  |
| `device_short_code` | `VARCHAR(3)` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### energy_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Hourly energy consumption (kWh) rollup per room/device used in Reports and Dashboard.
- **Primary Key:** `device_name, facility_id, amenity_id, hour`
- **Row Count (Live DB):** `72`
- **ORM Model:** `EnergyStat` in [EnergyStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/reporting.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_name` | `VARCHAR(11)` | NO |  |
| `facility_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `hour` | `BIGINT` | NO |  |
| `energy_consumed` | `DOUBLE PRECISION` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### entity_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** System entity catalog for activity and notification correlation.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `EntityType` in [EntityType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `entity_type` | `VARCHAR(50)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### facility

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Core tenant root representing hotel property/premise.
- **Primary Key:** `id`
- **Row Count (Live DB):** `1`
- **ORM Model:** `Facility` in [Facility](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `default_key_user` -> `app_user(id)`
- `facility_image_id` -> `attachment(id)`
- `org_id` -> `organisation(id)`

**Key Columns Sample (15 of 19 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `org_id` | `UUID` | NO |  |
| `facility_uid` | `VARCHAR(3)` | NO |  |
| `name` | `VARCHAR(100)` | NO |  |
| `currency_id` | `SMALLINT` | YES |  |
| `city` | `VARCHAR(100)` | YES |  |
| `state` | `VARCHAR(100)` | YES |  |
| `pin_code` | `VARCHAR(20)` | YES |  |
| `guest_rooms` | `INTEGER` | YES |  |
| `email` | `VARCHAR(500)` | NO |  |
| `additional_email` | `VARCHAR(500)` | YES |  |
| `google_map_link` | `VARCHAR(256)` | YES |  |
| `cloud_details` | `JSONB` | YES |  |
| `facility_image_id` | `UUID` | YES |  |
| `default_key_user` | `UUID` | YES |  |
| `created_by` | `UUID` | NO |  |
*... and 4 more columns*

---

### facility_event

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Hotel events, banquet bookings, and conferences.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `FacilityEvent` in [FacilityEvent](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/marketing.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `image_id` -> `attachment(id)`

**Key Columns Sample (15 of 17 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | NO |  |
| `name` | `VARCHAR(100)` | NO |  |
| `venue` | `VARCHAR(200)` | YES |  |
| `chief_guests` | `VARCHAR(500)` | YES |  |
| `description` | `TEXT` | YES |  |
| `expected_attendees` | `SMALLINT` | YES |  |
| `interested_attendees` | `SMALLINT` | YES | '0'::smallint |
| `start_date_time` | `TIMESTAMP` | YES |  |
| `end_date_time` | `TIMESTAMP` | YES |  |
| `image_id` | `UUID` | YES |  |
| `cancellation_reason` | `TEXT` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
*... and 2 more columns*

---

### facility_user

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Many-to-many scoping of users to facilities.
- **Primary Key:** `facility_id, app_user_id`
- **Row Count (Live DB):** `14`
- **ORM Model:** `FacilityUser` in [FacilityUser](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | NO |  |
| `app_user_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### feature

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Catalog of room amenities and features (AC, TV, Minibar).
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `Feature` in [Feature](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `device_type` -> `device_type(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | YES |  |
| `feature_name` | `VARCHAR(100)` | NO |  |
| `is_smart_feature` | `BOOLEAN` | YES |  |
| `device_type` | `SMALLINT` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### firmware

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Firmware binary repository, versions, CRC checks, and release notes.
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `Firmware` in [Firmware](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `device_type_id` -> `device_type(id)`
- `updated_by` -> `app_user(id)`
- `uploaded_by` -> `app_user(id)`

**Key Columns Sample (15 of 17 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_type_id` | `SMALLINT` | NO |  |
| `firmware_version` | `VARCHAR(20)` | NO |  |
| `firmware_filename` | `VARCHAR(500)` | NO |  |
| `firmware_url` | `VARCHAR(500)` | NO |  |
| `firmware_size` | `NUMERIC(10, 2)` | YES |  |
| `crc` | `TEXT` | NO |  |
| `release_date` | `TIMESTAMP` | YES |  |
| `release_notes` | `TEXT` | YES |  |
| `decommission_reason` | `VARCHAR(200)` | YES |  |
| `status` | `VARCHAR(14)` | NO | 'active'::firmware_status |
| `uploaded_by` | `UUID` | NO |  |
| `created_by` | `UUID` | YES |  |
| `updated_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
*... and 2 more columns*

---

### import_job

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Batch reservation CSV import tracking.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `ImportJob` in [ImportJob](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`

**Key Columns Sample (14 of 14 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `import_job_name` | `VARCHAR(100)` | YES |  |
| `entity_type` | `VARCHAR(9)` | NO |  |
| `import_status` | `VARCHAR(10)` | NO | 'queued'::import_status |
| `total_records` | `INTEGER` | YES |  |
| `success_count` | `INTEGER` | YES |  |
| `error_count` | `INTEGER` | YES |  |
| `import_file_name` | `VARCHAR(100)` | YES |  |
| `error_file_name` | `VARCHAR(100)` | YES |  |
| `completed_on` | `TIMESTAMP` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### incident_event

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Workflow transitions and events on device incidents.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `IncidentEvent` in [IncidentEvent](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### incident_history

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Full audit log of updates and staff comments on incidents.
- **Primary Key:** `id`
- **Row Count (Live DB):** `14`
- **ORM Model:** `IncidentHistory` in [IncidentHistory](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `incident_event_id` -> `incident_event(id)`
- `incident_id` -> `device_incident(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `incident_id` | `UUID` | NO |  |
| `incident_event_id` | `SMALLINT` | NO |  |
| `incident_event_data` | `JSONB` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### incident_status

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Incident lifecycle states (New, Assigned, In Progress, Resolved, Closed).
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `IncidentStatus` in [IncidentStatus](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### invoice

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Guest billing invoice, line items, and tax breakdown.
- **Primary Key:** `id`
- **Row Count (Live DB):** `2`
- **ORM Model:** `Invoice` in [Invoice](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `billing_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `facility_image_id` -> `attachment(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (15 of 19 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `invoice_number` | `VARCHAR(20)` | NO |  |
| `invoice_date` | `TIMESTAMP` | NO |  |
| `invoice_due_date` | `TIMESTAMP` | YES |  |
| `billing_user_id` | `UUID` | NO |  |
| `billing_user_name` | `VARCHAR(100)` | YES |  |
| `billing_address` | `VARCHAR(500)` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `facility_name` | `VARCHAR(100)` | YES |  |
| `facility_address` | `VARCHAR(500)` | YES |  |
| `facility_image_id` | `UUID` | YES |  |
| `stay_id` | `UUID` | NO |  |
| `net_amount` | `NUMERIC(10, 2)` | YES |  |
| `total_tax` | `NUMERIC(10, 2)` | YES |  |
| `total_amount` | `NUMERIC(10, 2)` | YES |  |
| `created_by` | `UUID` | NO |  |
*... and 4 more columns*

---

### job_function

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Staff job roles within departments.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `JobFunction` in [JobFunction](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `function_name` | `VARCHAR(100)` | NO |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `function_key` | `VARCHAR(5)` | YES |  |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### job_order

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Technical work orders and facility repair jobs.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `JobOrder` in [JobOrder](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/job_order.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `assigned_to` -> `app_user(id)`
- `created_by` -> `app_user(id)`

**Key Columns Sample (15 of 15 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `order_reference` | `VARCHAR(20)` | NO |  |
| `description` | `VARCHAR(200)` | YES |  |
| `type_of_work` | `VARCHAR(12)` | NO |  |
| `work_commence` | `TIMESTAMP` | NO |  |
| `estimated_completion_date` | `TIMESTAMP` | NO |  |
| `authentication_code` | `VARCHAR(20)` | NO |  |
| `assigned_to` | `UUID` | YES |  |
| `job_order_status` | `VARCHAR(9)` | NO | 'pending'::job_order_status |
| `completed_on` | `TIMESTAMP` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### job_order_amenity

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Rooms/locations linked to a job order.
- **Primary Key:** `job_order_id, amenity_id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `JobOrderAmenity` in [JobOrderAmenity](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/job_order.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `job_order_id` -> `job_order(id)`

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `job_order_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### job_order_device

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Junction linking job orders to physical IoT devices undergoing maintenance.
- **Primary Key:** `job_order_id, device_id`
- **Row Count (Live DB):** `2`
- **ORM Model:** `JobOrderDevice` in [JobOrderDevice](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/job_order.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`
- `job_order_id` -> `job_order(id)`

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `job_order_id` | `UUID` | NO |  |
| `device_id` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### key_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Key category registry (Primary, Shared, Staff, Default Key).
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `KeyType` in [KeyType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/access.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### lock_activity_log

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Audit log of physical lock/unlock events from smart door locks.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `LockActivityLog` in [LockActivityLog](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/access.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `app_user_id` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `key_type` -> `key_type(id)`
- `lock_id` -> `device(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (13 of 13 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `timestamp` | `TIMESTAMP` | NO |  |
| `app_user_id` | `UUID` | YES |  |
| `event` | `VARCHAR(8)` | YES |  |
| `unlock_mode` | `VARCHAR(6)` | YES |  |
| `lock_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `stay_id` | `UUID` | YES |  |
| `facility_id` | `UUID` | NO |  |
| `key_type` | `SMALLINT` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### maintenance_request

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Preventive and corrective maintenance work orders.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `MaintenanceRequest` in [MaintenanceRequest](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/maintenance.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `category_id` -> `service_category(id)`
- `created_by` -> `app_user(id)`
- `department_id` -> `department(id)`
- `facility_id` -> `facility(id)`
- `item_id` -> `service_category_item(id)`
- `maintenance_request_status` -> `service_status(id)`
- `parent_id` -> `maintenance_request(id)`
- `updated_by` -> `app_user(id)`

**Key Columns Sample (15 of 25 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `maintenance_request_type` | `VARCHAR(12)` | NO |  |
| `maintenance_start_date` | `DATE` | YES |  |
| `maintenance_end_date` | `DATE` | YES |  |
| `maintenance_start_time` | `TIMESTAMP` | YES |  |
| `maintenance_end_time` | `TIMESTAMP` | YES |  |
| `is_recurring` | `SMALLINT` | YES | '0'::smallint |
| `department_id` | `UUID` | YES |  |
| `category_id` | `UUID` | YES |  |
| `item_id` | `UUID` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `completed_on` | `TIMESTAMP` | YES |  |
| `is_room` | `SMALLINT` | YES |  |
| `non_room_comments` | `TEXT` | YES |  |
| `parent_id` | `UUID` | YES |  |
| `maintenance_request_status` | `SMALLINT` | NO |  |
*... and 10 more columns*

---

### maintenance_request_amenity

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Rooms/amenities attached to a maintenance work order.
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `MaintenanceRequestAmenity` in [MaintenanceRequestAmenity](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/maintenance.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `created_by` -> `app_user(id)`
- `maintenance_request_id` -> `maintenance_request(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### maintenance_request_assignee

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Staff members assigned to a maintenance work order.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `MaintenanceRequestAssignee` in [MaintenanceRequestAssignee](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/maintenance.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `maintenance_request_id` -> `maintenance_request(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NO |  |
| `app_user_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### maintenance_request_recurrence

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Recurrence rules for scheduled maintenance tasks.
- **Primary Key:** `maintenance_request_id`
- **Row Count (Live DB):** `1`
- **ORM Model:** `MaintenanceRequestRecurrence` in [MaintenanceRequestRecurrence](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/maintenance.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `maintenance_request_id` -> `maintenance_request(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `maintenance_request_id` | `UUID` | NO |  |
| `recurrence_type` | `VARCHAR(6)` | NO |  |
| `days_of_week` | `SMALLINT` | YES |  |
| `max_no_of_occurrences` | `SMALLINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### mqtt_broker

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** MQTT broker connection configuration per facility.
- **Primary Key:** `id`
- **Row Count (Live DB):** `1`
- **ORM Model:** `MqttBroker` in [MqttBroker](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `facility_id` -> `facility(id)`

**Key Columns Sample (11 of 11 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | YES |  |
| `broker_name` | `VARCHAR(50)` | NO |  |
| `broker_ip` | `VARCHAR(40)` | YES |  |
| `broker_vpn_ip` | `VARCHAR(40)` | YES |  |
| `broker_port` | `INTEGER` | YES |  |
| `broker_user_name` | `VARCHAR(50)` | YES |  |
| `broker_password` | `VARCHAR(50)` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### mqtt_topic

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** MQTT publish/subscribe topic structure definitions.
- **Primary Key:** `id`
- **Row Count (Live DB):** `12`
- **ORM Model:** `MqttTopic` in [MqttTopic](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`
- `mqtt_broker_id` -> `mqtt_broker(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `mqtt_broker_id` | `UUID` | NO |  |
| `device_id` | `UUID` | YES |  |
| `topic_name` | `VARCHAR(50)` | NO |  |
| `topic_type` | `VARCHAR(15)` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### notification

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Outbound dispatch message queue (Email, SMS, Push).
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `Notification` in [Notification](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `template_id` -> `notification_template(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `created_by` | `VARCHAR(100)` | NO |  |
| `status` | `VARCHAR(10)` | NO |  |
| `reference_id` | `BIGINT` | YES |  |
| `template_id` | `UUID` | YES |  |
| `params` | `JSONB` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### notification_receiver

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Recipients of dispatched notifications.
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `NotificationReceiver` in [NotificationReceiver](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `notification_id` -> `notification(id)`

**Key Columns Sample (11 of 11 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `app_user_id` | `UUID` | YES |  |
| `notification_id` | `BIGINT` | NO |  |
| `name` | `VARCHAR(100)` | NO |  |
| `email` | `VARCHAR(256)` | YES |  |
| `phone` | `VARCHAR(20)` | YES |  |
| `device_token` | `VARCHAR(200)` | YES |  |
| `data` | `JSONB` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### notification_result

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Delivery status per dispatch channel (sent, failed, delivered).
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `NotificationResult` in [NotificationResult](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `receiver_id` -> `notification_receiver(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `receiver_id` | `BIGINT` | NO |  |
| `type` | `VARCHAR(19)` | NO |  |
| `status` | `VARCHAR(15)` | NO |  |
| `log` | `JSONB` | YES |  |
| `body` | `TEXT` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### notification_template

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Message templates for alerts, check-in, bookings, and operations.
- **Primary Key:** `id`
- **Row Count (Live DB):** `16`
- **ORM Model:** `NotificationTemplate` in [NotificationTemplate](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/activity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(50)` | NO |  |
| `type` | `VARCHAR(19)` | NO |  |
| `path` | `VARCHAR(100)` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### occasion

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Hotel holiday calendar and special occasion events.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `Occasion` in [Occasion](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/marketing.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `occasion_type` -> `occasion_type(id)`

**Key Columns Sample (15 of 17 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `occasion_name` | `VARCHAR(100)` | YES |  |
| `occasion_type` | `SMALLINT` | NO |  |
| `is_repeatable` | `BOOLEAN` | YES | false |
| `notification_template` | `TEXT` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `month` | `SMALLINT` | NO |  |
| `day_of_month` | `SMALLINT` | NO |  |
| `app_user_id` | `UUID` | YES |  |
| `notify_to_hub` | `BOOLEAN` | YES | true |
| `occasion_start_date` | `DATE` | NO |  |
| `occasion_end_date` | `DATE` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
*... and 2 more columns*

---

### occasion_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Classification of occasions (Festival, Holiday, Birthday).
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `OccasionType` in [OccasionType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/marketing.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (5 of 5 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `occasion_type` | `VARCHAR(50)` | NO |  |
| `notification_template` | `TEXT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### organisation

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Top-level enterprise tenant entity; parent of facility.
- **Primary Key:** `id`
- **Row Count (Live DB):** `1`
- **ORM Model:** `Organisation` in [Organisation](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(100)` | NO |  |
| `org_uid` | `VARCHAR(3)` | NO |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### other_device

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Third-party and peripheral device telemetry readings (Power View).
- **Primary Key:** `id`
- **Row Count (Live DB):** `12`
- **ORM Model:** `OtherDevice` in [OtherDevice](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (15 of 17 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `msg_id` | `VARCHAR(255)` | YES |  |
| `device_name` | `VARCHAR(225)` | YES |  |
| `voltage` | `DOUBLE PRECISION` | YES |  |
| `current` | `DOUBLE PRECISION` | YES |  |
| `power` | `DOUBLE PRECISION` | YES |  |
| `power_factor` | `DOUBLE PRECISION` | YES |  |
| `all_energy` | `DOUBLE PRECISION` | YES |  |
| `thirty_day_energy` | `DOUBLE PRECISION` | YES |  |
| `today_energy` | `DOUBLE PRECISION` | YES |  |
| `current_hour_energy` | `DOUBLE PRECISION` | YES |  |
| `ec` | `DOUBLE PRECISION` | YES |  |
| `msg_string` | `JSONB` | YES |  |
| `timestamp` | `TIMESTAMP` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
*... and 2 more columns*

---

### package

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Room booking packages and rate plans.
- **Primary Key:** `id`
- **Row Count (Live DB):** `8`
- **ORM Model:** `Package` in [Package](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_type` -> `amenity_type(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `image_id` -> `attachment(id)`

**Key Columns Sample (12 of 12 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | YES |  |
| `name` | `VARCHAR(100)` | NO |  |
| `description` | `TEXT` | YES |  |
| `status` | `SMALLINT` | NO |  |
| `amenity_type` | `UUID` | NO |  |
| `is_sub_package` | `BOOLEAN` | NO | false |
| `image_id` | `UUID` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### package_feature

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Junction linking packages to room features.
- **Primary Key:** `id`
- **Row Count (Live DB):** `17`
- **ORM Model:** `PackageFeature` in [PackageFeature](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `feature_id` -> `feature(id)`
- `package_id` -> `package(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `package_id` | `UUID` | NO |  |
| `feature_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### promo_code

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Promotional discount codes and marketing offers.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `PromoCode` in [PromoCode](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/marketing.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `promo_code_icon` -> `attachment(id)`

**Key Columns Sample (15 of 16 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `offer_name` | `VARCHAR(100)` | YES |  |
| `promo_code` | `VARCHAR(20)` | NO |  |
| `start_time` | `TIMESTAMP` | YES |  |
| `expiry_time` | `TIMESTAMP` | YES |  |
| `discount_percentage` | `SMALLINT` | YES |  |
| `max_discount_value` | `NUMERIC(10, 2)` | YES |  |
| `min_order_value` | `NUMERIC(10, 2)` | YES |  |
| `promo_code_icon` | `UUID` | YES |  |
| `promo_code_description` | `VARCHAR(250)` | YES |  |
| `offered_by` | `VARCHAR(100)` | YES |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
*... and 1 more columns*

---

### promo_code_amenity

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Room applicability restrictions for promo codes.
- **Primary Key:** `promo_code_id, amenity_id`
- **Row Count (Live DB):** `8`
- **ORM Model:** `PromoCodeAmenity` in [PromoCodeAmenity](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/marketing.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `created_by` -> `app_user(id)`
- `promo_code_id` -> `promo_code(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `promo_code_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### property

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Physical building/floor assets within a facility.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `Property` in [Property](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `property_type_id` -> `property_type(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `property_name` | `VARCHAR(200)` | NO |  |
| `property_type_id` | `UUID` | NO |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | NO | '1'::smallint |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### property_chain

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Materialized Building->Wing->Floor paths linking amenities.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `PropertyChain` in [PropertyChain](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `level_one_id` -> `property(id)`
- `level_three_id` -> `property(id)`
- `level_two_id` -> `property(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `level_one_id` | `UUID` | NO |  |
| `level_two_id` | `UUID` | YES |  |
| `level_three_id` | `UUID` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | NO | '1'::smallint |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### property_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Physical hierarchy classification (Building, Wing, Floor).
- **Primary Key:** `id`
- **Row Count (Live DB):** `1`
- **ORM Model:** `PropertyType` in [PropertyType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/facility.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `facility_id` -> `facility(id)`
- `property_type_image_id` -> `attachment(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `property_type_name` | `VARCHAR(200)` | NO |  |
| `property_type_image_id` | `UUID` | YES |  |
| `levels` | `SMALLINT` | NO |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | NO | '1'::smallint |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### role

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** RBAC roles defining system permission levels (admin, manager, staff, etc.).
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `Role` in [Role](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (11 of 11 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | NO |  |
| `name` | `VARCHAR(50)` | NO |  |
| `description` | `VARCHAR(200)` | YES |  |
| `role_type` | `VARCHAR(11)` | NO | 'staff'::role_type |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |
| `notification_preferences` | `JSONB` | YES | '[]'::jsonb |

---

### role_module

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Catalog of 18 system modules matching the HMS navigation sidebar.
- **Primary Key:** `id`
- **Row Count (Live DB):** `18`
- **ORM Model:** `RoleModule` in [RoleModule](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `module_name` | `VARCHAR(100)` | NO |  |
| `read_applicable` | `BOOLEAN` | YES |  |
| `write_applicable` | `BOOLEAN` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### role_module_permission

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Matrix of read/write grants per role per module.
- **Primary Key:** `role_id, module_id`
- **Row Count (Live DB):** `65`
- **ORM Model:** `RoleModulePermission` in [RoleModulePermission](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `module_id` -> `role_module(id)`
- `role_id` -> `role(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `role_id` | `UUID` | NO |  |
| `module_id` | `SMALLINT` | NO |  |
| `read_access` | `BOOLEAN` | NO | false |
| `write_access` | `BOOLEAN` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### room_allocation

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Room assignment and allocation history for a reservation.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `RoomAllocation` in [RoomAllocation](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `package_id` -> `package(id)`
- `room_id` -> `amenity(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `stay_id` | `UUID` | NO |  |
| `room_id` | `UUID` | NO |  |
| `package_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### room_service_request

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** IKANOS legacy room service queue; dormant in current HMS routes.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `RoomServiceRequest` in [RoomServiceRequest](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `assigned_to` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `guest_room_id` -> `amenity(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (11 of 11 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `guest_room_id` | `UUID` | NO |  |
| `stay_id` | `UUID` | YES |  |
| `service_request_status` | `VARCHAR(10)` | YES | 'unassigned'::room_service_request_status |
| `assigned_to` | `UUID` | YES |  |
| `comments` | `TEXT` | YES |  |
| `completed_on` | `TIMESTAMP` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### room_service_request_item

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Child items for legacy room service queue; dormant.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `RoomServiceRequestItem` in [RoomServiceRequestItem](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `room_service_request_id` -> `room_service_request(id)`
- `service_category_item_id` -> `service_category_item(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `room_service_request_id` | `UUID` | NO |  |
| `service_category_item_id` | `UUID` | NO |  |
| `is_processed` | `SMALLINT` | YES | '0'::smallint |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### room_status_condition_applicability

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Business rules governing which conditions apply to which room status.
- **Primary Key:** `id`
- **Row Count (Live DB):** `42`
- **ORM Model:** `RoomStatusConditionApplicability` in [RoomStatusConditionApplicability](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_status_id` -> `amenity_status(id)`
- `condition_id` -> `amenity_condition(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `id` | `INTEGER` | NO | nextval('room_status_condition_applicability_id_seq'::regclass) |
| `room_status` | `VARCHAR(50)` | NO |  |
| `amenity_status_id` | `SMALLINT` | YES |  |
| `condition_id` | `SMALLINT` | NO |  |
| `is_applicable` | `BOOLEAN` | NO | true |
| `is_active` | `BOOLEAN` | NO | true |
| `blocks_checkin` | `BOOLEAN` | NO | false |
| `blocks_readiness` | `BOOLEAN` | NO | false |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### scheduler_job

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Cron job definitions from legacy caleido_scheduler service.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `SchedulerJob` in [SchedulerJob](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/scheduler.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `job_key` | `VARCHAR(100)` | NO |  |
| `job_name` | `VARCHAR(50)` | NO |  |
| `job_data` | `JSONB` | YES |  |
| `status` | `VARCHAR(8)` | NO |  |
| `is_dynamic_job` | `SMALLINT` | NO | '0'::smallint |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### scheduler_job_execution

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Execution log and run results for scheduled cron jobs.
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `SchedulerJobExecution` in [SchedulerJobExecution](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/scheduler.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `scheduler_job_id` -> `scheduler_job(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `scheduler_job_id` | `UUID` | NO |  |
| `job_execution_date` | `TIMESTAMP` | NO |  |
| `job_response` | `BYTEA` | YES |  |
| `status` | `VARCHAR(6)` | NO |  |
| `job_run_duration` | `INTEGER` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `BIGINT` | NO |  |

---

### sensor_operation_stat

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Daily sensor operational percentage and uptime tracking.
- **Primary Key:** `device_id, stats_date`
- **Row Count (Live DB):** `42`
- **ORM Model:** `SensorOperationStat` in [SensorOperationStat](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/device.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `device_id` -> `device(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `stats_date` | `DATE` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `operation_percentage` | `NUMERIC(10, 2)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### service_category

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Service menu categories (Food, Spa, Housekeeping Items).
- **Primary Key:** `id`
- **Row Count (Live DB):** `13`
- **ORM Model:** `ServiceCategory` in [ServiceCategory](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `category_icon` -> `attachment(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `service_type` -> `service_type(id)`

**Key Columns Sample (12 of 12 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `service_type` | `SMALLINT` | NO |  |
| `category_name` | `VARCHAR(100)` | YES |  |
| `description` | `TEXT` | YES |  |
| `category_icon` | `UUID` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `service_category_key` | `VARCHAR(100)` | YES |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### service_category_item

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Specific menu items and services available to order with pricing.
- **Primary Key:** `id`
- **Row Count (Live DB):** `22`
- **ORM Model:** `ServiceCategoryItem` in [ServiceCategoryItem](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `category_id` -> `service_category(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `item_icon` -> `attachment(id)`

**Key Columns Sample (14 of 14 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `item_name` | `VARCHAR(100)` | NO |  |
| `item_icon` | `UUID` | YES |  |
| `category_id` | `UUID` | NO |  |
| `description` | `TEXT` | YES |  |
| `price_per_unit` | `NUMERIC(10, 2)` | YES |  |
| `amenity_id` | `UUID` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `metadata` | `JSONB` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### service_request

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Service tickets and orders raised by or on behalf of guests.
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `ServiceRequest` in [ServiceRequest](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `app_user_id` -> `app_user(id)`
- `assigned_to` -> `app_user(id)`
- `category_id` -> `service_category(id)`
- `created_by` -> `app_user(id)`
- `department_id` -> `department(id)`
- `facility_id` -> `facility(id)`
- `promo_code_id` -> `promo_code(id)`
- `service_type` -> `service_type(id)`
- `status` -> `service_status(id)`
- `stay_id` -> `stay(id)`
- `updated_by` -> `app_user(id)`

**Key Columns Sample (15 of 25 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `service_type` | `SMALLINT` | NO |  |
| `ref_number` | `VARCHAR(20)` | YES |  |
| `description` | `TEXT` | YES |  |
| `assigned_to` | `UUID` | YES |  |
| `department_id` | `UUID` | YES |  |
| `category_id` | `UUID` | YES |  |
| `promo_code_id` | `UUID` | YES |  |
| `amenity_id` | `UUID` | YES |  |
| `stay_id` | `UUID` | YES |  |
| `app_user_id` | `UUID` | YES |  |
| `request_source` | `VARCHAR(6)` | YES |  |
| `facility_id` | `UUID` | YES |  |
| `net_amount` | `NUMERIC(10, 2)` | YES |  |
| `total_tax` | `NUMERIC(10, 2)` | YES |  |
| `total_amount` | `NUMERIC(10, 2)` | YES |  |
*... and 10 more columns*

---

### service_request_item

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Ordered item lines and quantities within a service request.
- **Primary Key:** `id`
- **Row Count (Live DB):** `8`
- **ORM Model:** `ServiceRequestItem` in [ServiceRequestItem](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `assigned_to` -> `app_user(id)`
- `category_id` -> `service_category(id)`
- `item_id` -> `service_category_item(id)`
- `service_request_id` -> `service_request(id)`
- `status` -> `service_status(id)`

**Key Columns Sample (11 of 11 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `service_request_id` | `UUID` | NO |  |
| `item_id` | `UUID` | YES |  |
| `category_id` | `UUID` | YES |  |
| `quantity` | `SMALLINT` | YES |  |
| `price_per_unit` | `NUMERIC(10, 2)` | YES |  |
| `assigned_to` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### service_status

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Service request status workflow (Pending, Assigned, In Progress, Completed, Canceled).
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `ServiceStatus` in [ServiceStatus](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(100)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### service_type

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Service request categories (Housekeeping, Room Service, Laundry, etc.).
- **Primary Key:** `id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `ServiceType` in [ServiceType](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/service.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
None

**Key Columns Sample (4 of 4 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `name` | `VARCHAR(100)` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `SMALLINT` | NO |  |

---

### stay

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Central guest reservation and stay lifecycle record (Bookings/Check-in).
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `Stay` in [Stay](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `booking_user_id` -> `app_user(id)`
- `checkout_initiated_by` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `modified_by` -> `app_user(id)`

**Key Columns Sample (15 of 21 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `internal_stay_ref_number` | `VARCHAR(100)` | NO |  |
| `external_stay_ref_number` | `VARCHAR(100)` | YES |  |
| `booking_user_id` | `UUID` | NO |  |
| `no_of_rooms` | `SMALLINT` | YES | '0'::smallint |
| `no_of_guests` | `SMALLINT` | NO | '0'::smallint |
| `expected_checkin_time` | `TIMESTAMP` | NO |  |
| `expected_checkout_time` | `TIMESTAMP` | NO |  |
| `actual_checkin_time` | `TIMESTAMP` | YES |  |
| `actual_checkout_time` | `TIMESTAMP` | YES |  |
| `comments` | `TEXT` | YES |  |
| `gst` | `VARCHAR(20)` | YES |  |
| `checkout_initiated_by` | `UUID` | YES |  |
| `document_approval_status` | `VARCHAR(8)` | NO | 'pending'::document_approval_status |
| `status` | `VARCHAR(17)` | YES | 'pending'::stay_status |
| `request_source` | `VARCHAR(6)` | YES |  |
*... and 6 more columns*

---

### stay_package

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Rate package applied to a guest stay.
- **Primary Key:** `id`
- **Row Count (Live DB):** `6`
- **ORM Model:** `StayPackage` in [StayPackage](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `package_id` -> `package(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (7 of 7 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `stay_id` | `UUID` | NO |  |
| `package_id` | `UUID` | NO |  |
| `status` | `SMALLINT` | NO | '1'::smallint |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### stay_user

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Occupants and guests linked to each stay/room.
- **Primary Key:** `id`
- **Row Count (Live DB):** `8`
- **ORM Model:** `StayUser` in [StayUser](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `room_id` -> `amenity(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (10 of 10 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `app_user_id` | `UUID` | NO |  |
| `room_id` | `UUID` | YES |  |
| `stay_id` | `UUID` | NO |  |
| `is_key_required` | `SMALLINT` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `created_by` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### sub_package

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Package child options and rate modifiers.
- **Primary Key:** `parent_package_id, sub_package_id`
- **Row Count (Live DB):** `7`
- **ORM Model:** `SubPackage` in [SubPackage](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/amenity.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `created_by` -> `app_user(id)`
- `parent_package_id` -> `package(id)`
- `sub_package_id` -> `package(id)`

**Key Columns Sample (5 of 5 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `parent_package_id` | `UUID` | NO |  |
| `sub_package_id` | `UUID` | NO |  |
| `created_by` | `UUID` | NO |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### user_device

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **OSS / Device Operations**
- **Business Purpose:** Mobile device registry (FCM tokens, OS, device model).
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `UserDevice` in [UserDevice](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `stay_id` -> `stay(id)`
- `user_token_id` -> `user_token(id)`

**Key Columns Sample (12 of 12 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `app_user_id` | `UUID` | NO |  |
| `mobile_model` | `VARCHAR(100)` | YES |  |
| `mobile_os` | `VARCHAR(50)` | YES |  |
| `device_token` | `VARCHAR(200)` | YES |  |
| `is_mobile_token` | `BOOLEAN` | YES |  |
| `user_token_id` | `UUID` | YES |  |
| `stay_id` | `UUID` | YES |  |
| `status` | `SMALLINT` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### user_device_acl

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Time-boxed access control permissions linking users to smart locks/devices.
- **Primary Key:** `id`
- **Row Count (Live DB):** `5`
- **ORM Model:** `UserDeviceAcl` in [UserDeviceAcl](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/access.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `amenity_type_id` -> `amenity_type(id)`
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `device_id` -> `device(id)`
- `device_type_id` -> `device_type(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (14 of 14 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `app_user_id` | `UUID` | NO |  |
| `device_type_id` | `SMALLINT` | NO |  |
| `device_id` | `UUID` | NO |  |
| `amenity_type_id` | `UUID` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `stay_id` | `UUID` | YES |  |
| `start_time` | `TIMESTAMP` | NO |  |
| `end_time` | `TIMESTAMP` | NO |  |
| `status_id` | `SMALLINT` | NO |  |
| `created_by` | `UUID` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### user_document

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Core**
- **Business Purpose:** Guest identity and verification document scans.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `UserDocument` in [UserDocument](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/stay.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `attachment_id` -> `attachment(id)`
- `stay_id` -> `stay(id)`

**Key Columns Sample (9 of 9 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `app_user_id` | `UUID` | NO |  |
| `attachment_id` | `UUID` | NO |  |
| `stay_id` | `UUID` | YES |  |
| `document_approval_status` | `VARCHAR(8)` | YES |  |
| `status` | `SMALLINT` | YES | '1'::smallint |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### user_role

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Junction assigning roles to users with facility scoping.
- **Primary Key:** `facility_id, app_user_id, role_id`
- **Row Count (Live DB):** `14`
- **ORM Model:** `UserRole` in [UserRole](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`
- `created_by` -> `app_user(id)`
- `facility_id` -> `facility(id)`
- `role_id` -> `role(id)`

**Key Columns Sample (6 of 6 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `facility_id` | `UUID` | NO |  |
| `app_user_id` | `UUID` | NO |  |
| `role_id` | `UUID` | NO |  |
| `created_by` | `UUID` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |

---

### user_token

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **HMS Supporting**
- **Business Purpose:** Legacy IKANOS session tokens; dormant in HMS stateless JWT auth.
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `UserToken` in [UserToken](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/people.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Dormant in Code / Seeded in DB)

**Foreign Key Relationships:**
- `app_user_id` -> `app_user(id)`

**Key Columns Sample (8 of 8 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `token` | `VARCHAR(36)` | NO |  |
| `app_user_id` | `UUID` | NO |  |
| `is_expired` | `BOOLEAN` | YES | false |
| `expired_on` | `TIMESTAMP` | YES |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
| `id` | `UUID` | NO |  |

---

### value_alert

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Telemetry threshold violation records (e.g. temperature out of bounds).
- **Primary Key:** `id`
- **Row Count (Live DB):** `3`
- **ORM Model:** `ValueAlert` in [ValueAlert](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `amenity_id` -> `amenity(id)`
- `device_id` -> `device(id)`
- `device_type_id` -> `device_type(id)`
- `facility_id` -> `facility(id)`
- `limit_config_id` -> `value_alert_limit_config(id)`

**Key Columns Sample (15 of 16 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `device_id` | `UUID` | NO |  |
| `device_type_id` | `SMALLINT` | NO |  |
| `device_name` | `VARCHAR(50)` | NO |  |
| `amenity_id` | `UUID` | NO |  |
| `limit_config_id` | `UUID` | NO |  |
| `device_status_id` | `INTEGER` | NO |  |
| `timestamp` | `TIMESTAMP` | NO |  |
| `limit_value` | `VARCHAR(50)` | NO |  |
| `limit_type` | `VARCHAR(50)` | NO |  |
| `description` | `TEXT` | NO |  |
| `status` | `SMALLINT` | NO | '0'::smallint |
| `facility_id` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
*... and 1 more columns*

---

### value_alert_limit_config

- **Database / Schema:** `hms_db` / `public`
- **Classification:** **Shared / Integration**
- **Business Purpose:** Configured parameter min/max thresholds per room/device type.
- **Primary Key:** `id`
- **Row Count (Live DB):** `4`
- **ORM Model:** `ValueAlertLimitConfig` in [ValueAlertLimitConfig](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/alert.py)
- **Existence Status:** Live DB (YES) · Source Code (YES) · Migrations (YES)
- **Verification Status:** Verified (Active in Code & DB)

**Foreign Key Relationships:**
- `device_id` -> `device(id)`
- `facility_id` -> `facility(id)`

**Key Columns Sample (15 of 16 columns):**

| Column Name | Data Type | Nullable | Default |
|---|---|---|---|
| `parameter` | `VARCHAR(50)` | NO |  |
| `device_name` | `VARCHAR(50)` | NO |  |
| `device_id` | `UUID` | YES |  |
| `limit_check` | `CHAR(1)` | NO |  |
| `is_percentage_value` | `CHAR(3)` | NO |  |
| `nominal` | `INTEGER` | YES |  |
| `limit_low_percentage` | `INTEGER` | YES |  |
| `limit_high_percentage` | `INTEGER` | YES |  |
| `limit_low_value` | `INTEGER` | YES |  |
| `limit_high_value` | `INTEGER` | YES |  |
| `remarks` | `TEXT` | NO |  |
| `facility_id` | `UUID` | NO |  |
| `legacy_id` | `BIGINT` | YES |  |
| `created_on` | `TIMESTAMP` | NO | now() |
| `updated_on` | `TIMESTAMP` | NO | now() |
*... and 1 more columns*

