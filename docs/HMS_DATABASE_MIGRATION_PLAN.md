# HMS Database Migration Plan: Safe OSS/BSS Alignment
**Document Version:** 1.0.0  
**Date:** 2026-10-26  
**Auditor:** Senior Database Migration Engineer & Backend Architect  
**Methodology:** Expand-and-Contract (Zero-Downtime, Additive Only)  

---

## 1. Migration Strategy & Core Guardrails

The migration from the single PostgreSQL monolithic schema to the dual OSS/BSS architecture must execute safely without interrupting existing front-desk operations, corrupting active stays, or breaking frontend API contracts.

### Golden Rules of this Migration:
1. **Never Drop Existing Tables or Columns in Phase 1:** All existing 94 tables in PostgreSQL `hms_db` remain operational.
2. **Additive Schema Modifications Only:** Any changes to PostgreSQL are strictly additive (adding nullable bridge columns: `bss_stay_id`, `bss_service_request_id`, `bss_digital_key_id`, etc.).
3. **Dedicated MySQL BSS Database:** BSS tables are created cleanly in MySQL 8.0 (`hms_bss`) using native InnoDB, UTF8MB4, and explicit indexing.
4. **Data Backfills with Validation Gates:** Backfilling data (e.g. creating `bss_rooms` from `amenity`, creating `bss_reservations` from `stay`) executes via audited Python migration scripts verifying row counts and key mappings before committing transactions.
5. **Reversible Rollbacks:** Every migration step has an explicit, tested rollback operation.

---

## 2. Phased Migration Sequence

The migration is partitioned into six sequential, gate-controlled phases:

```
[Phase 1: Dual Database Plumbing]
       |
       v
[Phase 2: Additive PostgreSQL Bridge Columns]
       |
       v
[Phase 3: MySQL BSS Baseline Schema Creation]
       |
       v
[Phase 4: Foundation Data Synchronization (Facilities, Rooms, Users)]
       |
       v
[Phase 5: Operational Data Bridge (Stays -> Reservations, Services)]
       |
       v
[Phase 6: Frontend / Backend API Transition & Validation]
```

---

### Phase 1: Dual Database Plumbing & Connection Management
**Objective:** Enable backend to talk to both PostgreSQL (`hms_db`) and MySQL (`hms_bss`) simultaneously.
- **Actions:**
  1. Install `pymysql` or `cryptography` in `backend/.venv` and pin to `requirements.txt`.
  2. Create database `hms_bss` in MySQL 8.0:
     ```sql
     CREATE DATABASE IF NOT EXISTS hms_bss 
     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```
  3. Add MySQL configuration to `backend/app/core/config.py`.
  4. Implement `app/db/bss_session.py` and dual database health check in `app/api/v1/endpoints/health.py`.
- **Downtime:** 0 minutes.
- **Rollback:** Disable MySQL settings in `.env`; backend falls back to single PostgreSQL engine.

---

### Phase 2: Additive PostgreSQL Bridge Columns (Alembic)
**Objective:** Add cross-system reference columns to PostgreSQL without touching existing columns.
- **Alembic Revision:** `1a2b3c4d5e6f_add_bss_bridge_columns.py` (down_revision: `0e2687233b59`).
- **Table Alterations (All NULLABLE, Non-Breaking):**
  ```sql
  -- Identity Bridge
  ALTER TABLE app_user ADD COLUMN IF NOT EXISTS user_type VARCHAR(20) DEFAULT 'staff';
  ALTER TABLE app_user ADD COLUMN IF NOT EXISTS is_hms_staff SMALLINT DEFAULT 1;
  ALTER TABLE app_user ADD COLUMN IF NOT EXISTS bss_legacy_user_id BIGINT NULL;
  
  -- Role Bridge
  ALTER TABLE role ADD COLUMN IF NOT EXISTS module_id SMALLINT NULL;
  
  -- Stay & Reservation Bridge
  ALTER TABLE stay ADD COLUMN IF NOT EXISTS bss_stay_id BIGINT NULL;
  ALTER TABLE room_allocation ADD COLUMN IF NOT EXISTS bss_reservation_room_id VARCHAR(36) NULL;
  ALTER TABLE stay_user ADD COLUMN IF NOT EXISTS bss_stay_id BIGINT NULL;
  
  -- Smart Lock Bridge
  ALTER TABLE access_key ADD COLUMN IF NOT EXISTS bss_digital_key_id BIGINT NULL;
  
  -- Services & Maintenance Bridge
  ALTER TABLE service_request ADD COLUMN IF NOT EXISTS bss_service_request_id VARCHAR(36) NULL;
  ALTER TABLE maintenance_request ADD COLUMN IF NOT EXISTS bss_work_order_id VARCHAR(36) NULL;
  ALTER TABLE invoice ADD COLUMN IF NOT EXISTS bss_invoice_id VARCHAR(36) NULL;
  
  -- Indexes for cross-reference lookups
  CREATE INDEX IF NOT EXISTS ix_stay_bss_stay_id ON stay (bss_stay_id);
  CREATE INDEX IF NOT EXISTS ix_app_user_is_hms_staff ON app_user (is_hms_staff);
  ```
- **Downtime:** 0 minutes (instant metadata lock in PostgreSQL).
- **Rollback:** `alembic downgrade 0e2687233b59` drops the added columns.

---

### Phase 3: MySQL BSS Baseline Schema Creation
**Objective:** Instantiate the 54 BSS tables in MySQL `hms_bss`.
- **Script:** `scripts/migrations/001_create_bss_schema.sql` (or SQLAlchemy metadata creation).
- **Core Table Groups:**
  1. **Properties & Inventory:** `bss_brands`, `bss_properties`, `bss_floors`, `bss_room_types`, `bss_rooms`, `bss_room_status_history`, `bss_room_device_registry`.
  2. **Guests & PII:** `bss_guests`, `bss_guest_pii`, `bss_corporate_accounts`, `bss_pii_access_log`.
  3. **Rates & Channels:** `bss_rate_plans`, `bss_rate_plan_room_types`, `bss_seasonal_rates`, `bss_cancellation_policies`, `bss_booking_channels`, `bss_ota_channels`, `bss_property_channel_configs`, `bss_channel_inbound_reservations`, `bss_availability_calendar`, `bss_group_blocks`.
  4. **Bookings & Stays:** `bss_reservations`, `bss_reservation_rooms`, `bss_reservation_guests`, `bss_stays`, `bss_automation_events`.
  5. **Folios & Billing:** `bss_folios`, `bss_folio_charges`, `bss_payments`, `bss_invoices`, `bss_orders`, `bss_revenue_categories`, `bss_payment_methods_config`.
  6. **Operations & Maintenance:** `bss_housekeeping_tasks`, `bss_service_requests`, `bss_maintenance_work_orders`, `bss_room_conditions`, `bss_digital_keys`, `bss_smart_access_log`, `bss_iot_control_events`.
  7. **Events, Loyalty & Marketing:** `bss_events`, `bss_public_holidays`, `bss_loyalty_programs`, `bss_loyalty_tiers`, `bss_loyalty_accounts`, `bss_loyalty_transactions`, `bss_promotions`, `bss_promo_redemptions`, `bss_campaigns`, `bss_campaign_enrollments`.
  8. **Sustainability:** `measurement_units`, `emission_factors`, `carbon_calculations`, `cm_points_ledger`.
- **Downtime:** 0 minutes.
- **Rollback:** `DROP DATABASE hms_bss`.

---

### Phase 4: Foundation Data Synchronization
**Objective:** Populate BSS reference data from existing PostgreSQL entities.
- **Data Transformations:**
  1. `facility` ("Ikanos Grand Chennai") → `bss_brands` ("Ikanos") + `bss_properties` (`property_id = 1`, `oss_facility_id = facility.id`).
  2. `amenity` (where `amenity_type` indicates Room/Suite) → `bss_room_types` + `bss_rooms` (`oss_asset_id = amenity.id`).
  3. `device` (bound to room amenities) → `bss_room_device_registry` (`oss_device_id = device.id`, initial `last_known_health_status = 'online'`).
- **Validation Script:** Asserts that every physical room amenity has exactly one corresponding `bss_rooms` record with a valid `oss_asset_id`.

---

### Phase 5: Operational Data Bridge (Stays & Services)
**Objective:** Backfill existing PostgreSQL `stay` records into BSS `bss_reservations` and `bss_stays`.
- **Data Transformations:**
  ```python
  # Pseudo-logic for backfill script
  for pg_stay in postgres_stays:
      # 1. Create BSS Guest profile
      guest_id = insert_bss_guest(user_id=pg_stay.app_user_id)
      # 2. Create BSS Reservation record
      res_id = insert_bss_reservation(
          guest_id=guest_id,
          check_in=pg_stay.check_in_date,
          check_out=pg_stay.check_out_date,
          status="Completed" if pg_stay.is_checked_out else "Active"
      )
      # 3. Create BSS Stay record
      bss_stay_id = insert_bss_stay(
          reservation_id=res_id,
          room_id=mapped_room_id,
          actual_check_in=pg_stay.actual_check_in,
          actual_check_out=pg_stay.actual_check_out
      )
      # 4. Bridge link back to PostgreSQL stay
      update_postgres_stay(id=pg_stay.id, bss_stay_id=bss_stay_id)
  ```
- **Validation Script:** Ensures `SELECT count(*) FROM stay WHERE bss_stay_id IS NULL` returns 0.

---

### Phase 6: Frontend & Backend API Transition
**Objective:** Transition frontend API consumption gracefully.
- The existing `/api/v1/stays`, `/api/v1/facilities`, `/api/v1/services` endpoints continue returning identical response envelopes, internally querying or coordinating with BSS.
- Introduce versioned `/api/v1/bss/reservations` for modern booking workflows.

---

## 3. Backup, Verification & Rollback Procedures

### 3.1 Pre-Migration Backup (Mandatory)
```powershell
# 1. PostgreSQL Full Database Dump
pg_dump -U postgres -h localhost -p 5432 -F c -b -v -f "C:\backups\hms_db_pre_v3_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump" hms_db

# 2. MySQL Schema State Backup
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe" -u root -p -P 3307 -h 127.0.0.1 --routines --triggers hms_bss > "C:\backups\hms_bss_pre_v3.sql"
```

### 3.2 Automated Reconciliation Queries
```sql
-- 1. Check all physical rooms have sellable BSS counterparts
SELECT a.id, a.name 
FROM amenity a 
JOIN amenity_type t ON a.amenity_type_id = t.id 
WHERE t.name IN ('Room', 'Suite')
  AND a.id NOT IN (SELECT oss_asset_id FROM bss_rooms);

-- 2. Verify stay bidirectional bridging
SELECT s.id, s.bss_stay_id 
FROM stay s 
WHERE s.bss_stay_id IS NULL;
```

### 3.3 Rollback Execution Strategy
If a catastrophic validation error occurs at any point during Phase 2–5:
1. Revert backend code git branch (`git checkout develop`).
2. Rollback Alembic migration: `alembic downgrade 0e2687233b59`.
3. Drop MySQL BSS staging database: `DROP DATABASE hms_bss;`.
4. Restore PostgreSQL backup if any data corruption is detected:
   ```powershell
   pg_restore -U postgres -h localhost -p 5432 -d hms_db --clean "C:\backups\hms_db_pre_v3.dump"
   ```
5. Restart Uvicorn: application is immediately restored to its exact pre-migration state.
