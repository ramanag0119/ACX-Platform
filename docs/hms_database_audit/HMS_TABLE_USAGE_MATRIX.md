# HMS Table Usage Matrix

**Audit Type:** 94-Table Comprehensive Code, Query & CRUD Usage Matrix  
**Date:** 2026-10-26  
**Scope:** Complete Census of all 94 database tables in `hms_db` / `public`

---

## 1. Table Usage & CRUD Matrix

| Table Name | Classification | Rows (Live DB) | Direct Code Usage | Indirect Dependencies | CRUD Operations | Foreign Keys (In / Out) | Confidence |
|---|---|---:|---|---|---|---|---|
| `access_key` | Shared / Integration | `5` | facility.py | FK Cascade / Seed | `UPDATE` | In: 0 / Out: 6 | Verified |
| `activity` | HMS Supporting | `10` | notification.py, notifications.py | FK Cascade / Seed | `None` | In: 1 / Out: 5 | Verified |
| `activity_notifier` | HMS Supporting | `15` | notification.py, notifications.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `activity_role_association` | HMS Supporting | `34` | None (Dormant) | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `activity_type` | HMS Supporting | `22` | notification.py | FK Cascade / Seed | `None` | In: 2 / Out: 1 | Verified |
| `alembic_version` | Infrastructure | `1` | health.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 0 | Verified |
| `alert_type` | Shared / Integration | `16` | alert.py, alerts.py, reports.py | FK Cascade / Seed | `SELECT` | In: 2 / Out: 0 | Verified |
| `amenity` | HMS Core | `27` | alert.py, catalog.py, device.py (+20) | FK Cascade / Seed | `SELECT` | In: 18 / Out: 7 | Verified |
| `amenity_condition` | HMS Core | `7` | facility.py, occupancy.py, reports.py (+1) | FK Cascade / Seed | `SELECT` | In: 2 / Out: 0 | Verified |
| `amenity_condition_status` | HMS Core | `7` | facility.py, occupancy.py, stays_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 2 | Verified |
| `amenity_status` | HMS Core | `4` | facilities.py, facility.py, occupancy.py (+2) | Occupancy Hierarchy | `SELECT` | In: 2 / Out: 0 | Verified |
| `amenity_type` | HMS Core | `5` | catalog.py, facility.py, facility_write.py (+2) | Occupancy Hierarchy | `SELECT` | In: 3 / Out: 3 | Verified |
| `app_user` | HMS Supporting | `15` | access.py, access_write.py, alert.py (+17) | Auth/RBAC | `SELECT` | In: 71 / Out: 6 | Verified |
| `attachment` | HMS Supporting | `8` | catalog.py, reports.py, stays.py (+1) | FK Cascade / Seed | `SELECT` | In: 10 / Out: 2 | Verified |
| `battery_life_stat` | OSS / Device Operations | `12` | device.py, devices.py | FK Cascade / Seed | `None` | In: 0 / Out: 1 | Verified |
| `command_type` | OSS / Device Operations | `10` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 1 | Verified |
| `country` | HMS Supporting | `239` | access.py, access_write.py, facilities.py (+2) | FK Cascade / Seed | `SELECT` | In: 2 / Out: 0 | Verified |
| `daily_dual_data_point` | Shared / Integration | `35` | energy.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 1 | Verified |
| `department` | HMS Supporting | `5` | access.py, access_write.py, maintenance.py (+4) | FK Cascade / Seed | `SELECT` | In: 3 / Out: 2 | Verified |
| `device` | Shared / Integration | `14` | alert.py, alerts.py, device.py (+11) | FK Cascade / Seed | `SELECT` | In: 16 / Out: 7 | Verified |
| `device_alert` | Shared / Integration | `9` | alert.py, alerts.py, devices_write.py (+1) | FK Cascade / Seed | `None` | In: 1 / Out: 4 | Verified |
| `device_command` | OSS / Device Operations | `7` | devices.py | FK Cascade / Seed | `None` | In: 0 / Out: 3 | Verified |
| `device_current_stat` | Shared / Integration | `14` | device.py, devices.py, telemetry.py | FK Cascade / Seed | `None` | In: 0 / Out: 1 | Verified |
| `device_health_stat` | OSS / Device Operations | `168` | device.py, devices.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 1 | Verified |
| `device_incident` | Shared / Integration | `5` | alert.py, alerts.py, devices_write.py | FK Cascade / Seed | `None` | In: 1 / Out: 8 | Verified |
| `device_param` | OSS / Device Operations | `35` | energy.py, telemetry.py | Telemetry Aggregation | `SELECT` | In: 1 / Out: 1 | Verified |
| `device_stat` | OSS / Device Operations | `504` | device.py, devices.py, devices_write.py (+1) | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `device_type` | Shared / Integration | `4` | alert.py, alerts.py, catalog.py (+6) | Telemetry Aggregation | `SELECT` | In: 7 / Out: 0 | Verified |
| `energy_stat` | Shared / Integration | `72` | energy.py, reports.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `entity_type` | HMS Supporting | `5` | notification.py, stays_write.py | FK Cascade / Seed | `None` | In: 2 / Out: 0 | Verified |
| `facility` | HMS Supporting | `1` | access.py, access_write.py, catalog.py (+14) | Auth/RBAC | `SELECT` | In: 29 / Out: 4 | Verified |
| `facility_event` | HMS Core | `3` | catalog.py, facility_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 3 | Verified |
| `facility_user` | HMS Supporting | `14` | access.py, stays_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 3 | Verified |
| `feature` | HMS Core | `6` | catalog.py, facility_write.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 3 | Verified |
| `firmware` | OSS / Device Operations | `6` | device.py, devices.py, devices_write.py (+1) | FK Cascade / Seed | `SELECT` | In: 2 / Out: 4 | Verified |
| `import_job` | HMS Core | `3` | stays_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 1 | Verified |
| `incident_event` | Shared / Integration | `5` | alert.py, devices_write.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 0 | Verified |
| `incident_history` | Shared / Integration | `14` | alert.py, alerts.py, devices_write.py | FK Cascade / Seed | `None` | In: 0 / Out: 3 | Verified |
| `incident_status` | Shared / Integration | `4` | alert.py, alerts.py, devices_write.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 0 | Verified |
| `invoice` | HMS Core | `2` | services.py, stay.py, stays.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 5 | Verified |
| `job_function` | HMS Supporting | `5` | access.py, access_write.py, reports.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 2 | Verified |
| `job_order` | HMS Core | `3` | job_order.py, job_order_write.py, job_orders.py | FK Cascade / Seed | `None` | In: 2 / Out: 2 | Verified |
| `job_order_amenity` | HMS Core | `4` | job_order.py, job_order_write.py, job_orders.py | FK Cascade / Seed | `DELETE/INSERT/SELECT` | In: 0 / Out: 2 | Verified |
| `job_order_device` | Shared / Integration | `2` | devices_write.py, job_order.py, job_order_write.py (+1) | FK Cascade / Seed | `DELETE/INSERT/SELECT` | In: 0 / Out: 2 | Verified |
| `key_type` | Shared / Integration | `4` | facility.py | FK Cascade / Seed | `None` | In: 2 / Out: 0 | Verified |
| `lock_activity_log` | OSS / Device Operations | `5` | None (Dormant) | FK Cascade / Seed | `None` | In: 0 / Out: 6 | Verified |
| `maintenance_request` | HMS Core | `4` | job_order.py, job_order_write.py, maintenance.py (+2) | FK Cascade / Seed | `None` | In: 5 / Out: 8 | Verified |
| `maintenance_request_amenity` | HMS Core | `7` | job_order.py, maintenance.py, maintenance_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 3 | Verified |
| `maintenance_request_assignee` | HMS Core | `5` | maintenance.py, maintenance_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 3 | Verified |
| `maintenance_request_recurrence` | HMS Core | `1` | maintenance.py, maintenance_write.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 1 | Verified |
| `mqtt_broker` | OSS / Device Operations | `1` | devices.py | FK Cascade / Seed | `None` | In: 1 / Out: 1 | Verified |
| `mqtt_topic` | OSS / Device Operations | `12` | devices.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `notification` | HMS Supporting | `6` | notification.py, notifications.py | FK Cascade / Seed | `None` | In: 1 / Out: 1 | Verified |
| `notification_receiver` | HMS Supporting | `6` | notification.py, notifications.py | FK Cascade / Seed | `None` | In: 1 / Out: 2 | Verified |
| `notification_result` | HMS Supporting | `6` | notification.py, notifications.py | FK Cascade / Seed | `None` | In: 0 / Out: 1 | Verified |
| `notification_template` | HMS Supporting | `16` | notification.py, notifications.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 0 | Verified |
| `occasion` | HMS Core | `4` | catalog.py, facility_write.py, notifications.py | FK Cascade / Seed | `SELECT` | In: 0 / Out: 4 | Verified |
| `occasion_type` | HMS Core | `4` | catalog.py, facility_write.py | FK Cascade / Seed | `SELECT` | In: 1 / Out: 0 | Verified |
| `organisation` | HMS Supporting | `1` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 1 | Verified |
| `other_device` | OSS / Device Operations | `12` | telemetry.py | FK Cascade / Seed | `None` | In: 0 / Out: 0 | Verified |
| `package` | HMS Core | `8` | catalog.py, facility.py, facility_write.py (+5) | FK Cascade / Seed | `SELECT` | In: 6 / Out: 4 | Verified |
| `package_feature` | HMS Core | `17` | catalog.py, facility_write.py | FK Cascade / Seed | `DELETE/SELECT` | In: 0 / Out: 3 | Verified |
| `promo_code` | HMS Core | `3` | catalog.py, facility_write.py, services_write.py | FK Cascade / Seed | `SELECT` | In: 2 / Out: 2 | Verified |
| `promo_code_amenity` | HMS Core | `8` | catalog.py, facility_write.py | FK Cascade / Seed | `DELETE/SELECT` | In: 0 / Out: 3 | Verified |
| `property` | HMS Supporting | `4` | alert.py, device.py, energy.py (+6) | FK Cascade / Seed | `SELECT` | In: 3 / Out: 3 | Verified |
| `property_chain` | HMS Supporting | `3` | alert.py, alerts.py, device.py (+9) | Occupancy Hierarchy | `SELECT` | In: 1 / Out: 5 | Verified |
| `property_type` | HMS Supporting | `1` | facility.py | FK Cascade / Seed | `None` | In: 1 / Out: 2 | Verified |
| `role` | HMS Supporting | `7` | access.py, access_write.py, alerts.py (+16) | Auth/RBAC | `SELECT` | In: 3 / Out: 2 | Verified |
| `role_module` | HMS Supporting | `18` | access.py, access_write.py, auth.py (+6) | FK Cascade / Seed | `SELECT` | In: 1 / Out: 0 | Verified |
| `role_module_permission` | HMS Supporting | `65` | access.py, access_write.py, auth.py | Auth/RBAC | `SELECT` | In: 0 / Out: 2 | Verified |
| `room_allocation` | HMS Core | `5` | occupancy.py, reports.py, stay.py (+2) | FK Cascade / Seed | `SELECT` | In: 0 / Out: 4 | Verified |
| `room_service_request` | HMS Core | `3` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 4 | Verified |
| `room_service_request_item` | HMS Core | `4` | None (Dormant) | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `room_status_condition_applicability` | HMS Core | `42` | occupancy.py, stays_write.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `scheduler_job` | OSS / Device Operations | `5` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 0 | Verified |
| `scheduler_job_execution` | OSS / Device Operations | `6` | None (Dormant) | FK Cascade / Seed | `None` | In: 0 / Out: 1 | Verified |
| `sensor_operation_stat` | OSS / Device Operations | `42` | device.py, devices.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `service_category` | HMS Core | `13` | maintenance.py, maintenance_write.py, reports.py (+3) | FK Cascade / Seed | `SELECT` | In: 4 / Out: 4 | Verified |
| `service_category_item` | HMS Core | `22` | maintenance.py, maintenance_write.py, service.py (+2) | FK Cascade / Seed | `SELECT` | In: 3 / Out: 5 | Verified |
| `service_request` | HMS Core | `7` | maintenance_write.py, reports.py, service.py (+2) | FK Cascade / Seed | `None` | In: 1 / Out: 12 | Verified |
| `service_request_item` | HMS Core | `8` | service.py, services_write.py | FK Cascade / Seed | `DELETE/SELECT` | In: 0 / Out: 5 | Verified |
| `service_status` | HMS Core | `5` | maintenance.py, maintenance_write.py, reports.py (+3) | FK Cascade / Seed | `SELECT` | In: 3 / Out: 0 | Verified |
| `service_type` | HMS Core | `7` | maintenance.py, reports.py, service.py (+2) | FK Cascade / Seed | `SELECT` | In: 2 / Out: 0 | Verified |
| `stay` | HMS Core | `6` | device.py, facility_write.py, job_order.py (+8) | FK Cascade / Seed | `SELECT` | In: 12 / Out: 4 | Verified |
| `stay_package` | HMS Core | `6` | stay.py | FK Cascade / Seed | `None` | In: 0 / Out: 2 | Verified |
| `stay_user` | HMS Core | `8` | occupancy.py, stay.py, stays.py (+1) | FK Cascade / Seed | `SELECT` | In: 0 / Out: 4 | Verified |
| `sub_package` | HMS Core | `7` | catalog.py, facility_write.py | FK Cascade / Seed | `DELETE/INSERT/SELECT` | In: 0 / Out: 3 | Verified |
| `user_device` | OSS / Device Operations | `4` | None (Dormant) | FK Cascade / Seed | `None` | In: 0 / Out: 3 | Verified |
| `user_device_acl` | Shared / Integration | `5` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 7 | Verified |
| `user_document` | HMS Core | `3` | stay.py, stays.py | FK Cascade / Seed | `None` | In: 0 / Out: 3 | Verified |
| `user_role` | HMS Supporting | `14` | access.py, access_write.py, auth.py (+1) | FK Cascade / Seed | `DELETE/SELECT` | In: 0 / Out: 4 | Verified |
| `user_token` | HMS Supporting | `3` | None (Dormant) | FK Cascade / Seed | `None` | In: 1 / Out: 1 | Verified |
| `value_alert` | Shared / Integration | `3` | alert.py, alerts.py, devices_write.py (+1) | FK Cascade / Seed | `SELECT` | In: 0 / Out: 5 | Verified |
| `value_alert_limit_config` | Shared / Integration | `4` | alert.py, alerts.py, devices_write.py (+1) | FK Cascade / Seed | `SELECT` | In: 1 / Out: 2 | Verified |

---

## 2. Classification Distribution Summary

- **HMS Core:** **36 tables** (38.3%) — Direct commercial hotel operations (bookings, stays, rooms, housekeeping, services, maintenance, packages).
- **HMS Supporting:** **25 tables** (26.6%) — Foundational operational support (auth, RBAC, departments, facility hierarchy, attachments, notifications, audit).
- **Shared / Integration:** **17 tables** (18.1%) — Boundary entities shared between hotel staff operations and IoT hardware (digital keys, alerts, room devices, energy rollups).
- **OSS / Device Operations:** **15 tables** (16.0%) — Technical IoT, gateway, telemetry, firmware, and MQTT platform operations.
- **Infrastructure:** **1 table** (1.1%) — Alembic migration version tracker (`alembic_version`).
- **Total:** **94 tables** (100.0%).
