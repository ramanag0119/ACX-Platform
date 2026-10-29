# HMS OSS & Device Dependency Audit Report

**Audit Type:** Architectural Coupling & Dependency Analysis (HMS vs. OSS/Device Operations)  
**Date:** 2026-10-26  
**Target:** Identifying Direct, Indirect, and Foreign-Key Dependencies of HMS on OSS  
**Status:** Read-Only Verification

---

## 1. Executive Summary

This audit assesses the feasibility of decoupling the core Hotel Management System (HMS) from the Operations Support System (OSS / IoT / Device Platform).

### Headline Findings:
1. **Low Structural Coupling from HMS to OSS:** Across the entire schema, **only TWO foreign keys** point from HMS Core/Supporting tables outward to OSS tables:
   - `feature.device_type -> device_type.id`
   - `job_order_device.device_id -> device.id`
2. **High Structural Coupling from OSS to HMS:** Conversely, OSS/device tables depend heavily on HMS foundational entities. OSS tables contain **37 foreign keys** pointing into `amenity` (rooms), `facility`, `stay`, and `app_user`.
3. **Selective Code Dependencies:** Core HMS booking, check-in, guest services, housekeeping condition workflows, and user RBAC can function independently of OSS tables with minimal code adjustments. The only functional dependencies on OSS exist in:
   - Room detail card in Occupancy (`device_count` calculation).
   - Facility Management Default Key Settings (`/key-settings` queries `access_key` and `key_type`).
   - Dashboard KPI widgets ("Smart Rooms Online", "Energy Consumption", "Caleido At Work", "Device Cards").
   - Reports module (Energy Consumption Report).

---

## 2. Foreign Key Dependency Analysis

### 2.1 Direct FKs: HMS Core / Supporting Tables -> OSS Tables (Total: 2)

| HMS Source Table | Constraint Column | Target OSS Table | Target Column | On Delete | Impact if OSS Table Removed |
|---|---|---|---|---|---|
| `feature` | `device_type` | `device_type` | `id` | `RESTRICT` | Room amenity features tagged with an IoT hardware type (e.g. Smart AC) will fail FK validation. **Remediation:** Make column nullable or replace with loose string/ID. |
| `job_order_device` | `device_id` | `device` | `id` | `CASCADE` | Work orders cannot attach specific hardware controller IDs. **Remediation:** Job orders attach to `amenity_id` (room) instead of device ID. |

### 2.2 Reverse FKs: OSS Tables -> HMS Core / Supporting Tables (Total: 37)

OSS tables treat HMS as the authoritative source for spatial hierarchy, reservations, and actors:

- **Point to `amenity` (Room Asset):**
  - `device.amenity_id -> amenity.id`
  - `device_alert.amenity_id -> amenity.id`
  - `device_incident.amenity_id -> amenity.id`
  - `energy_stat.amenity_id -> amenity.id`
  - `sensor_operation_stat.amenity_id -> amenity.id`
  - `value_alert.amenity_id -> amenity.id`
  - `lock_activity_log.amenity_id -> amenity.id`
  - `user_device_acl.amenity_id -> amenity.id`
- **Point to `stay` (Guest Reservation):**
  - `access_key.stay_id -> stay.id`
  - `lock_activity_log.stay_id -> stay.id`
  - `user_device.stay_id -> stay.id`
  - `user_device_acl.stay_id -> stay.id`
- **Point to `app_user` (Staff / Actor):**
  - `device.created_by`, `device_alert.created_by`, `device_command.created_by`
  - `device_incident.assigned_to`, `device_incident.updated_by`
  - `firmware.created_by`, `firmware.updated_by`, `firmware.uploaded_by`
  - `lock_activity_log.app_user_id`, `user_device.app_user_id`, `user_device_acl.app_user_id`
- **Point to `facility` (Tenant Root):**
  - `device.facility_id`, `device_incident.facility_id`, `energy_stat.facility_id`, `mqtt_broker.facility_id`, `value_alert.facility_id`, `value_alert_limit_config.facility_id`

**Architectural Takeaway:** The OSS platform cannot exist without the HMS spatial and user foundation. However, the HMS commercial PMS can operate autonomously if OSS tables are segregated.

---

## 3. Backend Code Dependency Trace

### 3.1 Occupancy Service ([services/occupancy.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/occupancy.py))
- **Execution Path:** `GET /api/v1/occupancy/{amenity_id}` -> `occupancy.get_occupancy()`
- **Reference (lines 603-605):**
  ```python
  enriched["device_count"] = db.execute(
      select(func.count()).select_from(Device).where(Device.amenity_id == amenity_id)
  ).scalar_one()
  ```
- **Type:** Direct code dependency on `device`.
- **Can HMS operate without it?** **YES.** If device telemetry is isolated, `device_count` can default to `0` or be fetched via asynchronous API.

### 3.2 Facility Management & Key Settings ([services/facility.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/facility.py))
- **Execution Path:** `GET /api/v1/key-settings`, `POST /api/v1/key-settings/reset`
- **Reference:** Queries `access_key` and `key_type` to configure facility default digital keys.
- **Type:** Direct code dependency on `access_key` and `key_type`.
- **Can HMS operate without it?** **YES.** Traditional physical key management does not require digital key tables.

### 3.3 Dashboard KPI Visualizations
- **Endpoints:**
  - `GET /api/v1/energy-stats` (reads `energy_stat`)
  - `GET /api/v1/daily-data-points` (reads `daily_dual_data_point`)
  - `GET /api/v1/devices` (reads `device`, `device_type`)
  - `GET /api/v1/alerts` (reads `device_alert`, `alert_type`)
- **Type:** Frontend dashboard dependency on IoT summaries.
- **Can HMS operate without it?** **YES.** Traditional PMS dashboards focus on RevPAR, ADR, Occupancy %, and Housekeeping status rather than sensor telemetry.

### 3.4 Reports Service ([services/reports.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/reports.py))
- **Execution Path:** `GET /api/v1/reports/energy-consumption`
- **Reference:** `energy.list_energy_stats()` querying `energy_stat`.
- **Type:** Direct code dependency in report catalog.
- **Can HMS operate without it?** **YES.** Energy report can be migrated to an OSS/sustainability reporting suite.

---

## 4. Standalone HMS Decoupling Assessment

| Category | Table Count | Tables | Decoupling Strategy |
|---|---:|---|---|
| **Retain in HMS Core** | 61 | All 36 HMS Core + 25 HMS Supporting tables | Kept in standalone HMS database (`hms_db`). Fully self-sufficient for PMS operations. |
| **Move to OSS / IoT Platform** | 15 | `device_param`, `device_stat`, `device_health_stat`, `battery_life_stat`, `sensor_operation_stat`, `other_device`, `firmware`, `device_command`, `command_type`, `mqtt_broker`, `mqtt_topic`, `lock_activity_log`, `user_device`, `scheduler_job`, `scheduler_job_execution` | Relocate to dedicated IoT Timescale/PostgreSQL service. Zero negative impact on HMS reservations, check-in, or billing. |
| **Shared Boundary Candidates** | 17 | `device`, `device_type`, `device_current_stat`, `access_key`, `key_type`, `user_device_acl`, `job_order_device`, `alert_type`, `device_alert`, `incident_status`, `incident_event`, `device_incident`, `incident_history`, `value_alert`, `value_alert_limit_config`, `energy_stat`, `daily_dual_data_point` | Keep as read-only integration contracts or link via REST/gRPC API between HMS and OSS. |
