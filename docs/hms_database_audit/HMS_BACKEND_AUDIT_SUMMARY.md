# HMS Backend Database Table Usage Audit — Executive Summary

**Audit Date:** 2026-10-26  
**Auditor:** Antigravity AI Senior Backend Architect & Database Specialist  
**Methodology:** 100% Read-Only Codebase & Database Introspection  
**Target Environment:** PostgreSQL 18.6 (`hms_db` @ port 5432)  
**Deliverables Directory:** [docs/hms_database_audit/](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit)

---

## 1. Verified Core Metrics

| Metric | Verified Count | Verification Source / Evidence |
|---|---:|---|
| **Total Database Tables** | **94** | Live PostgreSQL query against `information_schema.tables` (schema: `public`) |
| **Total Database Views** | **0** | Live PostgreSQL query against `information_schema.views` (schema: `public`) |
| **Tables Mapped to ORM Models** | **93** | Registered in SQLAlchemy `Base.metadata.tables` ([app/models/__init__.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/models/__init__.py)) |
| **Migration Tracking Tables** | **1** | `alembic_version` (holding active revision `9a2b3c4d5e6f`) |
| **Tables with Active Code Usage** | **83** | Directly queried by backend services, routers, or health checks |
| **Tables with Zero Code Usage (Dormant/Seeded)**| **11** | Seeded in live database; unreferenced by active service/router functions |
| **FastAPI Registered Endpoints** | **182** | Introspected from FastAPI application routes ([app/main.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/main.py)) |
| **Alembic Migration History Chain** | **4** | Tracked in [migrations/versions/](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/migrations/versions) |

---

## 2. Table Classification Census

All 94 tables have been verified and classified according to their architectural function:

```
+-----------------------------------------------------------------------------------+
|                        TOTAL VERIFIED DATABASE TABLES (94)                        |
+-----------------------------------------------------------------------------------+
        |                       |                       |                   |
        v                       v                       v                   v
+---------------+       +---------------+       +---------------+   +---------------+
|   HMS CORE    |       | HMS SUPPORTING|       |    SHARED     |   |  OSS / DEVICE |
|   36 Tables   |       |   25 Tables   |       |   17 Tables   |   |   15 Tables   |
|    (38.3%)    |       |    (26.6%)    |       |    (18.1%)    |   |    (16.0%)    |
+---------------+       +---------------+       +---------------+   +---------------+
                                                        |                   |
                                                        v                   v
                                                [2 FKs point out]   [Infrastructure:
                                                to OSS device_type  1 alembic_version]
                                                and device tables
```

### Classification Breakdown:
- **HMS Core (36 Tables):** Core commercial PMS operations. Includes `stay`, `stay_user`, `room_allocation`, `invoice`, `amenity` (rooms), `amenity_status`, `amenity_condition`, `amenity_condition_status`, `room_status_condition_applicability`, `package`, `sub_package`, `feature`, `service_request`, `service_category`, `service_category_item`, `maintenance_request`, `job_order`, `promo_code`, `facility_event`, `occasion`.
- **HMS Supporting (25 Tables):** Supporting hotel administration and security. Includes `app_user` (staff/guest identities, bcrypt hashes), `role`, `user_role`, `role_module` (18 sidebar modules), `role_module_permission`, `department`, `job_function`, `facility`, `facility_user`, `organisation`, `property`, `property_chain`, `attachment`, `country`, `notification`, `activity`.
- **Shared / Integration (17 Tables):** Cross-boundary entities linking hotel spaces to hardware. Includes `device` (room hardware registry), `device_type`, `device_current_stat`, `access_key` (digital door keys), `key_type`, `user_device_acl`, `job_order_device`, `alert_type`, `device_alert`, `device_incident`, `incident_history`, `value_alert`, `value_alert_limit_config`, `energy_stat`, `daily_dual_data_point`.
- **OSS / Device Operations (15 Tables):** Pure IoT telemetry, hardware control, and protocols. Includes `device_param`, `device_stat` (raw sensor readings), `device_health_stat`, `battery_life_stat`, `sensor_operation_stat`, `other_device`, `firmware`, `device_command`, `command_type`, `mqtt_broker`, `mqtt_topic`, `lock_activity_log`, `user_device`, `scheduler_job`, `scheduler_job_execution`.
- **Infrastructure (1 Table):** `alembic_version`.

---

## 3. Key Architectural & Operational Discoveries

1. **Clean Separation Potential:** The HMS domain is remarkably uncoupled from OSS hardware tables. Only **two foreign keys** point from HMS tables outward to OSS tables:
   - `feature.device_type -> device_type.id`
   - `job_order_device.device_id -> device.id`
2. **Reverse Dependencies:** The OSS platform is the heavily dependent party: **37 foreign keys** in OSS tables reference `amenity` (rooms), `stay`, `app_user`, and `facility`.
3. **Stateless JWT Security:** Authentication in HMS Web is completely stateless. The legacy `user_token` table from IKANOS is dormant. All sessions use HS256 JWTs with real-time database permission re-validation on every request.
4. **No In-Process Background Jobs:** Scheduled jobs (`scheduler_job`, `scheduler_job_execution`) are dormant schema legacy; the FastAPI backend runs zero background threads or queues.
5. **Dormant Tables Identified:** Exactly 11 tables have zero code references in active endpoints/services, despite carrying seeded rows in the live database.

---

## 4. Master Deliverables Directory Index

All detailed audit reports have been generated and saved to the audit directory:

1. [A. HMS_BACKEND_ARCHITECTURE_AUDIT.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_BACKEND_ARCHITECTURE_AUDIT.md): Framework, routers, services, ORM, auth, and session architecture.
2. [B. HMS_DATABASE_TABLE_INVENTORY.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_DATABASE_TABLE_INVENTORY.md): Complete 94-table inventory with columns, PKs, FKs, models, and row counts.
3. [C. HMS_BACKEND_MODULE_TABLE_MAPPING.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_BACKEND_MODULE_TABLE_MAPPING.md): Endpoints, routes, and services mapped to tables.
4. [D. HMS_TABLE_USAGE_MATRIX.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_TABLE_USAGE_MATRIX.md): Full 94-row usage, direct/indirect references, and CRUD matrix.
5. [E. HMS_OSS_DEPENDENCY_AUDIT.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_OSS_DEPENDENCY_AUDIT.md): Detailed audit of HMS-to-OSS dependencies and decoupling feasibility.
6. [F. HMS_ORIGINAL_SCHEMA_HISTORY_AUDIT.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_ORIGINAL_SCHEMA_HISTORY_AUDIT.md): Historical schema evolution from IKANOS MySQL to PostgreSQL.
7. [G. HMS_BACKEND_AUDIT_SUMMARY.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_BACKEND_AUDIT_SUMMARY.md): Executive summary and decision guide.

---

## 5. Recommended Next Investigation Steps (Non-Modifying)

1. **Resolve the Two HMS-to-OSS Foreign Keys:**
   - Investigate relaxing `feature.device_type` (nullable/loose identifier) so room features can exist without `device_type`.
   - Investigate modifying `job_order_device` to allow work orders to attach directly to `amenity_id` (rooms) when no IoT device is present.
2. **Review the 11 Dormant Tables:**
   - Confirm with product management whether legacy room service queue (`room_service_request`, `room_service_request_item`) and scheduler tables (`scheduler_job`, `scheduler_job_execution`) should be deprecated in a future migration.
3. **Inspect Frontend API Contract:**
   - Cross-verify frontend components with [HMS_BACKEND_MODULE_TABLE_MAPPING.md](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/docs/hms_database_audit/HMS_BACKEND_MODULE_TABLE_MAPPING.md) to ensure all frontend queries match active backend routes.
