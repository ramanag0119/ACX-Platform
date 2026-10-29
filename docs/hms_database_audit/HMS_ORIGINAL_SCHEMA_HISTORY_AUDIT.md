# HMS Schema History & Evolution Audit

**Audit Type:** Git History, Schema Evolution & Migration Lineage Audit  
**Date:** 2026-10-26  
**Scope:** Historical transitions from legacy MySQL dumps to current PostgreSQL schema

---

## 1. Evolution Timeline Overview

The database schema in this repository has evolved across four distinct architectural phases:

```
+-------------------------------------------------------------------------------+
| ERA 1: LEGACY IKANOS PLATFORM (MySQL 5.7 / 8.0)                                |
| 3 Separate Databases: caleido (101 tables), caleido_notification (5 tables),  |
|                       caleido_scheduler (2 tables). Total = 108 tables.       |
| Primary Keys: Integer/BigInt Auto-Increment. No UUIDs.                        |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| ERA 2: PHASE 1 HMS PROTOTYPE (PostgreSQL)                                     |
| Alembic revision 8a8456154f0e. Built from documentation, not dump.            |
| Total = 39 tables. UUID PKs everywhere. Invented 'booking' & 'employee'.      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| ERA 3: PHASE 1.5 - 1.7 BLUEPRINT & FOUNDATION REALIGNMENT                     |
| Documented in FINAL_HMS_DATABASE_BLUEPRINT.md. Unified into single DB.        |
| Alembic revision 0e2687233b59_phase1_7_hms_92_table_foundation.py.           |
| Total = 92 tables. Restored 'stays', absorbed 'booking' & 'employee'.         |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| ERA 4: INCREMENTAL EVOLUTION (Current Live State)                             |
| Migration 7c4e2b9a1d53: renamed service status to 'in_progress'.              |
| Migration 8f1e3c5a7b92: added 'room_status_condition_applicability' (Table 93)|
| Migration 9a2b3c4d5e6f: added role notification preferences. (Head)           |
| Total = 94 tables in live PostgreSQL database (93 app + alembic_version).     |
+-------------------------------------------------------------------------------+
```

---

## 2. Detailed Era Analysis

### Era 1 — Legacy IKANOS Architecture (Authority: MySQL SQL Dump 2023-09-28)
- **Structure:** 3 isolated MySQL databases:
  1. `caleido` (101 tables): Core asset, user, telemetry, and operational tables.
  2. `caleido_notification` (5 tables): In-app feed and outbound message queues.
  3. `caleido_scheduler` (2 tables): Scheduled cron jobs and execution histories.
- **Key Strategy:** Native MySQL `AUTO_INCREMENT` integers (`int(11)` / `bigint(20)`). **Zero UUID columns existed.**
- **Entities:**
  - Reservations were stored exclusively in `stays` (21 columns). No `booking` table existed.
  - Staff and guests were stored in `users` (26 columns) with `is_staff=1`. No `employee` table existed.

### Era 2 — Early HMS Prototype (39 Tables, Revision `8a8456154f0e`)
- Built from secondary documentation (`KT-IKANOS.pdf`, `COMPLETE_PROJECT_ANALYSIS_REPORT.md`).
- Adopted UUID primary keys on all 39 tables.
- **Structural Inaccuracies:**
  - Split `stays` into `booking` and `stay`, dropping 14 critical columns.
  - Split `users` into `app_user` and `employee`.
  - Discarded RBAC tables in favor of unstructured JSONB blobs.
  - Invented telemetry tables (`energy_data`, `sensor_reading`, `device_uptime`) that had no backing in the physical IoT hardware.

### Era 3 — The 92-Table Realignment (Revision `0e2687233b59`)
- Authoritative design executed in [FINAL_HMS_DATABASE_BLUEPRINT.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/docs/FINAL_HMS_DATABASE_BLUEPRINT.md).
- Re-analyzed all 108 tables from the IKANOS MySQL dump:
  - **57 tables:** USED as-is.
  - **35 tables:** ADAPTED for PostgreSQL (UUID PKs + `legacy_id BIGINT UNIQUE` to prevent collision with legacy records).
  - **7 tables:** MERGED into parent tables (`user_login_details` -> `app_user.password_hash`, `user_metadata` -> `app_user.metadata JSONB`, `activity_data` -> `activity.data JSONB`).
  - **8 tables:** EXCLUDED (TypeORM migrations, Razorpay payment gateway, Porta guest app feedback).
- Migration file created: [0e2687233b59_phase1_7_hms_92_table_foundation.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py).

### Era 4 — Incremental Migrations & Current Live Database
Subsequent migrations executed on the database:
1. `7c4e2b9a1d53_rename_service_status_in_progress.py`: Renamed service status `partially_completed` to `in_progress`.
2. `8f1e3c5a7b92_room_status_condition_applicability.py`:
   - Added table #93: `room_status_condition_applicability`.
   - Seeded 12 rule rows driving housekeeping condition options based on room status.
3. `9a2b3c4d5e6f_add_role_notification_preferences.py`:
   - Current Alembic HEAD verified live in database (`SELECT version_num FROM alembic_version`).

---

## 3. Git Commit History Evidence

Inspection of Git history confirms major recent architectural refinements:

- `288d552`: `fix: resolve occupancy status and room condition mapping`
- `e92218f`: `fix: update dashboard status section`
- `828f08d`: `fix: update service planning page`
- `2353334`: `fix: update services setup and API mutations`
- `25c9fd0`: `fix: update occupancy conditions and room status logic`
- `9f4853d`: `fix: synchronize room conditions and occupancy statistics`
- `4e4a927`: `feat: update app navigation and RBAC modules`

**Conclusion:** The current database schema is completely consistent with the Alembic migration history and represents the latest stabilized state of the unified HMS/OSS platform.
