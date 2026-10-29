# HMS Forensic Database Audit & Current State Analysis
**Document Version:** 1.0.0  
**Audit Date:** 2026-10-26  
**Auditor:** Senior Backend Architect & Database Migration Specialist  
**System Under Audit:** Hotel Management System (HMS) / ACX-Platform  
**Workspace:** `c:\Users\user\OneDrive - Inspironics India\Insp Total Work\HMS-Frontend\ACX-Platform`  

---

## 1. Executive Summary & Forensic Audit Methodology

This forensic audit evaluates the live implementation of the Hotel Management System (HMS), hosted within the `ACX-Platform` repository, against the proposed **HMS OSS/BSS v3 Architecture**. 

The audit was conducted strictly against live database instances, running processes, codebase configurations, ORM entities, Alembic migrations, and automated test suites. In accordance with architectural safety rules, no destructive operations were executed, no production credentials were leaked, and no speculative counts were recorded.

### Summary of Forensic Findings:
1. **Current System Architecture Classification:**  
   **Option B — Modular Monolith with a Single PostgreSQL Database.**  
   All 94 active database tables reside within a single PostgreSQL database (`hms_db`) under the `public` schema. The backend service is a unified FastAPI application serving both physical infrastructure management (FleetExplorer/OSS concerns) and hotel business workflows (BSS concerns).
2. **PostgreSQL Environment:**  
   - Engine: PostgreSQL 18.4 (msvc-19.44.35227, 64-bit).
   - Port: `5432` (Note: PostgreSQL 17 also runs locally on port `5433`).
   - Active Database: `hms_db`.
   - Table Count: **94 tables** in `public` (93 application tables + 1 `alembic_version`).
   - Data Population: **94/94 tables contain verified rows** (from 1 row in `facility` and `organisation` to 504 rows in `device_stat`, 239 in `country`, and 168 in `device_health_stat`).
3. **MySQL Environment:**  
   - Engine: MySQL Server 8.0.45 Community Edition.
   - Port: `3307` (Windows service `MySQL80`, PID 8408).
   - Status: Running, accessible, but currently hosts only legacy/unrelated schemas (`motor_insurance_db`, `student_management`, `sakila`, `world`, etc.).  
   - **Crucial Fact:** No `hms_bss` or BSS tables have been created in MySQL yet.
4. **Backend Stack:**  
   - Runtime: Python 3.13.9 in `.venv`.
   - Framework: FastAPI 0.135.3, Uvicorn 0.34.0, SQLAlchemy 2.0.52, Pydantic 2.12.5, Alembic 1.19.1.
   - Migration Revision: `0e2687233b59` (Single revision chain: `0e2687233b59_phase1_7_hms_92_table_foundation.py`).

---

## 2. Infrastructure & Runtime Configuration

### 2.1 Backend Configuration Management
Configuration is loaded via Pydantic Settings in `backend/app/core/config.py`.
- **Primary Source:** `backend/.env` (active, ignored by Git).
- **Fallback Template:** `backend/.env.example`.
- **Database Resolution Logic:**
  ```python
  @property
  def sqlalchemy_url(self) -> str:
      if self.DATABASE_URL:
          return self.DATABASE_URL
      return (
          f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
          f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
      )
  ```
  `DATABASE_URL` is commented out in `.env`. The URL is constructed from components: `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `POSTGRES_USER=postgres`, `POSTGRES_DB=hms_db`.
- **Connection Engine:** Configured in `backend/app/db/session.py` with `pool_pre_ping=True`, `echo=True` (active in development).

### 2.2 Frontend Client & Proxy Integration
- **Runtime:** Node.js v24.9.0 / npm 11.6.0.
- **Framework:** Vite 5.4.19, React 18.3.1, TypeScript 5.8.3, TanStack React Query 5.83.0, TailwindCSS 3.4.17.
- **Proxy Configuration:** `frontend/vite.config.ts` proxies all `/api/v1` traffic to `http://127.0.0.1:8000` (`VITE_API_PROXY_TARGET`), ensuring zero CORS friction during local development.

---

## 3. Forensic Inventory of Existing PostgreSQL Database (`hms_db`)

The live database contains 94 physical tables in `public`. Below is the verified physical inventory including row counts, primary keys, and functional role:

| # | Table Name | Physical Rows | Columns | Primary Key | Existing Domain / Role |
|---|---|---|---|---|---|
| 1 | `access_key` | 5 | 13 | `id` (uuid) | Smart locks / physical access keys |
| 2 | `activity` | 10 | 13 | `id` (uuid) | Operational activity stream |
| 3 | `activity_notifier` | 15 | 7 | `(activity_id, app_user_id)` | Activity notification dispatch |
| 4 | `activity_role_association` | 34 | 4 | `(activity_type_id, role_id)` | Role-to-activity mapping |
| 5 | `activity_type` | 22 | 7 | `id` (uuid) | Activity taxonomy registry |
| 6 | `alembic_version` | 1 | 1 | `version_num` | Migration tracker (`0e2687233b59`) |
| 7 | `alert_type` | 16 | 4 | `id` (uuid) | IoT & system alert taxonomy |
| 8 | `amenity` | 27 | 15 | `id` (uuid) | Rooms, halls, facilities & physical assets |
| 9 | `amenity_condition` | 7 | 8 | `id` (uuid) | Physical condition states (AC, temp, humidity) |
| 10 | `amenity_condition_status` | 6 | 5 | `(amenity_id, amenity_condition_id)` | Live room sensor/condition values |
| 11 | `amenity_status` | 4 | 4 | `id` (uuid) | Operational status (Available, Occupied, Maintenance) |
| 12 | `amenity_type` | 5 | 10 | `id` (uuid) | Asset categories (Room, Suite, Hall, Amenity) |
| 13 | `app_user` | 13 | 29 | `id` (uuid) | Staff & guest identity (login by `user_name`) |
| 14 | `attachment` | 8 | 8 | `id` (uuid) | Document/image binary metadata |
| 15 | `battery_life_stat` | 12 | 9 | `id` (uuid) | IoT device battery health telemetry |
| 16 | `command_type` | 10 | 5 | `id` (uuid) | Actuator command registry (Lock, Unlock, AC Set) |
| 17 | `country` | 239 | 9 | `id` (smallint) | ISO country reference lookup |
| 18 | `daily_dual_data_point` | 35 | 7 | `(metric_date, metric_type)` | Aggregated metric reporting cache |
| 19 | `department` | 5 | 9 | `id` (uuid) | Organisational departments (Front Desk, Housekeeping) |
| 20 | `device` | 14 | 28 | `id` (uuid) | IoT hardware units, controllers, sensors |
| 21 | `device_alert` | 9 | 10 | `id` (uuid) | Active hardware anomalies & thresholds |
| 22 | `device_command` | 7 | 9 | `id` (uuid) | Outbound device control audit trail |
| 23 | `device_current_stat` | 14 | 7 | `id` (uuid) | Latest snapshot of device electrical/sensor values |
| 24 | `device_health_stat` | 168 | 7 | `id` (uuid) | Hourly health checks & uptime |
| 25 | `device_incident` | 5 | 14 | `id` (uuid) | Hardware failure tracking tickets |
| 26 | `device_param` | 35 | 7 | `id` (uuid) | Device config parameter definitions |
| 27 | `device_stat` | 504 | 9 | `id` (uuid) | Timescale-ready raw telemetry stream |
| 28 | `device_type` | 4 | 5 | `id` (uuid) | Hardware hardware types (Thermostat, Lock, Gateway) |
| 29 | `energy_stat` | 72 | 7 | `(device_name, facility_id, amenity_id, hour)` | Hourly kWh consumption statistics |
| 30 | `entity_type` | 5 | 4 | `id` (uuid) | Polymorphic entity registry |
| 31 | `facility` | 1 | 19 | `id` (uuid) | Hotel facility ("Ikanos Grand Chennai") |
| 32 | `facility_event` | 3 | 17 | `id` (uuid) | Banquets, meetings & scheduled events |
| 33 | `facility_user` | 13 | 6 | `(facility_id, app_user_id)` | Facility staff scoping assignment |
| 34 | `feature` | 6 | 10 | `id` (uuid) | Room & package feature definitions |
| 35 | `firmware` | 6 | 17 | `id` (uuid) | IoT device firmware build repository |
| 36 | `import_job` | 3 | 14 | `id` (uuid) | Batch data import executions |
| 37 | `incident_event` | 5 | 4 | `id` (uuid) | Hardware incident lifecycle event types |
| 38 | `incident_history` | 14 | 8 | `id` (uuid) | Transition audit log for hardware incidents |
| 39 | `incident_status` | 4 | 4 | `id` (uuid) | Incident statuses (Open, Investigating, Resolved) |
| 40 | `invoice` | 2 | 19 | `id` (uuid) | Guest folios / invoices |
| 41 | `job_function` | 5 | 9 | `id` (uuid) | Staff job roles (Manager, Technician, Housekeeper) |
| 42 | `job_order` | 3 | 15 | `id` (uuid) | Operational task tickets |
| 43 | `job_order_amenity` | 4 | 4 | `(job_order_id, amenity_id)` | Job order room scoping |
| 44 | `job_order_device` | 2 | 4 | `(job_order_id, device_id)` | Job order hardware scoping |
| 45 | `key_type` | 4 | 4 | `id` (smallint) | Key types (NFC, Mobile App, Keypad PIN) |
| 46 | `lock_activity_log` | 5 | 13 | `id` (uuid) | Access control door unlock events |
| 47 | `maintenance_request` | 4 | 25 | `id` (uuid) | Facility maintenance work requests |
| 48 | `maintenance_request_amenity` | 7 | 8 | `id` (uuid) | Maintenance room associations |
| 49 | `maintenance_request_assignee` | 5 | 8 | `id` (uuid) | Staff assigned to maintenance work |
| 50 | `maintenance_request_recurrence` | 1 | 6 | `maintenance_request_id` | Recurring preventative maintenance schedule |
| 51 | `mqtt_broker` | 1 | 11 | `id` (uuid) | IoT message broker connection details |
| 52 | `mqtt_topic` | 12 | 8 | `id` (uuid) | Inbound/outbound MQTT topic mappings |
| 53 | `notification` | 6 | 9 | `id` (uuid) | Outbound notification instances |
| 54 | `notification_receiver` | 6 | 11 | `id` (uuid) | User recipients for notifications |
| 55 | `notification_result` | 6 | 9 | `id` (uuid) | SMS/Email delivery status logs |
| 56 | `notification_template` | 16 | 7 | `id` (uuid) | Standard messaging templates |
| 57 | `occasion` | 4 | 17 | `id` (uuid) | Holidays, festivals & seasonal events |
| 58 | `occasion_type` | 4 | 5 | `id` (uuid) | Occasion categories (National Holiday, Festival) |
| 59 | `organisation` | 1 | 7 | `id` (uuid) | Parent enterprise organisation |
| 60 | `other_device` | 12 | 17 | `id` (uuid) | Non-IoT auxiliary hardware assets |
| 61 | `package` | 8 | 12 | `id` (uuid) | Rate bundles / room packages |
| 62 | `package_feature` | 17 | 8 | `id` (uuid) | Features bundled into packages |
| 63 | `promo_code` | 3 | 16 | `id` (uuid) | Commercial discounts & promo vouchers |
| 64 | `promo_code_amenity` | 8 | 6 | `(promo_code_id, amenity_id)` | Room eligibility for promo codes |
| 65 | `property` | 4 | 9 | `id` (uuid) | Physical property blocks/buildings |
| 66 | `property_chain` | 3 | 10 | `id` (uuid) | Multi-property chain management |
| 67 | `property_type` | 1 | 9 | `id` (uuid) | Property classifications (Hotel, Resort) |
| 68 | `role` | 7 | 11 | `id` (uuid) | User role definitions |
| 69 | `role_module` | 18 | 6 | `id` (smallint) | 18 frontend module permissions registry |
| 70 | `role_module_permission` | 65 | 6 | `(role_id, module_id)` | Granular read/write permissions per module |
| 71 | `room_allocation` | 5 | 9 | `id` (uuid) | Stay-to-room physical binding |
| 72 | `room_service_request` | 3 | 11 | `id` (uuid) | In-room dining/amenity service orders |
| 73 | `room_service_request_item` | 4 | 7 | `id` (uuid) | Specific line items in room service order |
| 74 | `room_status_condition_applicability` | 42 | 10 | `id` (uuid) | Threshold rules for room readiness |
| 75 | `scheduler_job` | 5 | 9 | `id` (uuid) | Cron / background job registry |
| 76 | `scheduler_job_execution` | 6 | 9 | `id` (uuid) | Background job run history |
| 77 | `sensor_operation_stat` | 42 | 6 | `(device_id, stats_date)` | Daily sensor uptime & packet counts |
| 78 | `service_category` | 13 | 12 | `id` (uuid) | Hotel service catalog categories |
| 79 | `service_category_item` | 22 | 14 | `id` (uuid) | Specific orderable hotel services |
| 80 | `service_request` | 7 | 25 | `id` (uuid) | General guest requests (Housekeeping, Valet) |
| 81 | `service_request_item` | 8 | 11 | `id` (uuid) | Line items for service requests |
| 82 | `service_status` | 5 | 4 | `id` (uuid) | Service lifecycle states (Pending, Done) |
| 83 | `service_type` | 7 | 4 | `id` (uuid) | Service types (Food, Cleaning, Laundry) |
| 84 | `stay` | 6 | 21 | `id` (uuid) | Guest stay and check-in records |
| 85 | `stay_package` | 6 | 7 | `id` (uuid) | Packages linked to guest stays |
| 86 | `stay_user` | 8 | 10 | `id` (uuid) | Primary and accompanying guests on stay |
| 87 | `sub_package` | 7 | 5 | `(parent_package_id, sub_package_id)` | Sub-package bundle hierarchy |
| 88 | `user_device` | 4 | 12 | `id` (uuid) | Devices assigned to specific users |
| 89 | `user_device_acl` | 5 | 14 | `id` (uuid) | Fine-grained access control for devices |
| 90 | `user_document` | 3 | 9 | `id` (uuid) | Identification documents (Passport, ID) |
| 91 | `user_role` | 13 | 6 | `(facility_id, app_user_id, role_id)` | Facility-scoped user role assignments |
| 92 | `user_token` | 3 | 8 | `id` (uuid) | Session tokens and mobile app refresh tokens |
| 93 | `value_alert` | 3 | 16 | `id` (uuid) | Telemetry threshold trigger events |
| 94 | `value_alert_limit_config` | 4 | 16 | `id` (uuid) | Sensor limit threshold configurations |

---

## 4. Key Architectural Insights & System Gaps

1. **Dual Representation of Rooms (Asset vs Sellable Room):**  
   In the current HMS schema, `amenity` represents both physical rooms, physical conference halls, and generic assets. Business room concepts (sellable room inventory, room types, seasonal rates, channel distribution) do not exist as independent tables; they are conflated with the physical asset `amenity`.
2. **Missing Reservation Lifecycle:**  
   Currently, the system has no `reservation` table. The frontend "Bookings" page reads directly from the `stay` table. This means a reservation cannot exist without creating a `stay` record. In standard hotel PMS architectures (and v3 BSS), a reservation precedes a stay, and multiple rooms/guests can belong to a single reservation.
3. **Guest PII Isolation Gap:**  
   Guests and staff are currently stored in the same table (`app_user`), differentiated only by `is_staff = 0` or `1`. Unencrypted guest PII (phone number, email, date of birth, address) is stored in the same table as staff system logins.
4. **RBAC Scope:**  
   The current system uses `role_module` and `role_module_permission` covering 18 modules. The v3 proposal introduces `platform_modules`, `platform_permissions`, and `platform_role_permissions`, with a required `module_id` scoping to prevent HMS users from accessing FleetExplorer infrastructure screens.
5. **Backend Surface:**  
   FastAPI exposes 21 endpoints files under `backend/app/api/v1/endpoints/`. All operations execute against PostgreSQL `hms_db`.
