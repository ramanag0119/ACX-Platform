# HMS Phase 1 — Database Foundation Report

**Status:** ✅ Complete and verified against live PostgreSQL
**Date:** 2026-08-16

---

## 1. Summary

| Item | Value |
|---|---|
| Database name | `hms_db` |
| Schema name | `public` |
| PostgreSQL version | 16.12 |
| Total tables created | **39** |
| Documented entities covered | **36 / 36** |
| Supporting tables | 3 |
| Primary keys | 39 / 39 |
| Foreign keys | 71 |
| Indexes | 33 |
| Unique constraints | 13 |
| ENUM types | 13 |
| Circular dependencies | **None** |
| Alembic revision | `8a8456154f0e` |
| Migration status | Applied · reversible · drift-free |
| Tests | 8 / 8 passing |

**Source of truth:** `d:\Inspornics\HMS_ikanos\Ikanos_code\` (12 documents).

> ⚠️ **This is not the original production schema.** CPA §0 "Evidence
> Boundary" states the IKANOS snapshot contains no `src/`, no backend source,
> no ORM schema and no migrations. This design is derived strictly from the
> documented entity field tables, workflows and API definitions.

---

## 2. Table-by-table inventory

### 2.1 CORE (19 documented entities)

| # | IKANOS entity | PostgreSQL table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 1 | `facility` | `facility` | `id` | 0 | name, address, settings |
| 2 | `userRole` | `user_role` | `id` | 1 | name, roleType, permissions |
| 3 | `user` | `app_user` ¹ | `id` | 1 | email, password, userRoles, facilityId |
| 4 | `propertyType` | `property_type` | `id` | 1 | name, facilityId |
| 5 | `package` | `package` | `id` | 2 | name, price, amenityType |
| 6 | `amenity` | `amenity` | `id` | 3 | name, type, floor, packageId, status |
| 7 | `department` | `department` | `id` | 1 | name, facilityId |
| 8 | `function` | `job_function` ¹ | `id` | 1 | name, departmentId |
| 9 | `employee` | `employee` | `id` | 4 | email, departmentId, userRoleId |
| 10 | `booking` | `booking` | `id` | 2 | firstName, checkinDate, packageId |
| 11 | `occupant` | `occupant` | `id` | 1 | bookingId, firstName, phoneNumber |
| 12 | `stay` | `stay` | `id` | 3 | bookingId, amenityId, status |
| 13 | `invoice` | `invoice` | `id` | 2 | stayId, amount, status |
| 14 | `serviceRequest` | `service_request` | `id` | 4 | serviceType, roomId, guestId, subject, assignedTo, status, createdOn |
| 15 | `foodCategory` | `food_category` | `id` | 1 | name |
| 16 | `foodMenu` | `food_menu` | `id` | 2 | name, foodCode, categoryId, price |
| 17 | `event` | `event` | `id` | 1 | name, venue, startDate, status |
| 18 | `offer` | `offer` | `id` | 1 | name, couponCode, validFrom |
| 19 | `holiday` | `holiday` | `id` | 1 | startDate, lockMessage |

¹ Renamed — see §5.

### 2.2 DEVICE (3)

| # | Entity | Table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 20 | `device` | `device` | `id` | 3 | name, type, deviceConfigStatus, amenityId, hubId, firmwareVersion, status, lastSeen, ipAddress, macAddress |
| 21 | `firmware` | `firmware` | `id` | 1 | version, deviceType, filePath, isLatest |
| 22 | `jobOrder` | `job_order` | `id` | 3 | amenityId, devices, jobType, assignedTo, status |

### 2.3 ALERT (5)

| # | Entity | Table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 23 | `deviceIncident` | `device_incident` | `id` | 3 | deviceId, subject, description, status, severity, alertSeverity, createdOn, assignedTo, assignedUser, resolvedOn, notes |
| 24 | `valueAlerts` | `value_alerts` | `id` | 2 | deviceId, parameter, limitType, limitValue, currentValue, status, timestamp, unit |
| 25 | `limitConfig` | `limit_config` | `id` | 2 | deviceId, parameter, highLimit, lowLimit, unit |
| 26 | `alertType` | `alert_type` | `id` | 0 | name, description, severity, category, isActive |
| 27 | `currentIncidentStatus` | `current_incident_status` | `id` | 0 | name, statusCode, displayColor, isResolved |

### 2.4 NOTIFICATION (2)

| # | Entity | Table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 28 | `notification` | `notification` | `id` | 2 | userId, title, message, type, referenceId, isRead, createdOn |
| 29 | `fcmToken` | `fcm_token` | `id` | 2 | userId, token, deviceType, registeredOn |

### 2.5 SCHEDULE (2)

| # | Entity | Table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 30 | `maintenanceSchedule` | `maintenance_schedule` | `id` | 4 | amenityId, serviceTypeId, departmentId, assignedTo, days, startTime, fromDate, toDate, isActive |
| 31 | `scheduledTask` | `scheduled_task` | `id` | 1 | type, targetEntity, scheduledAt, status, lastExecuted, recurPattern |

### 2.6 SENSOR / HEALTH (5)

| # | Entity | Table | PK | FKs | Documented fields |
|---|---|---|---:|---:|---|
| 32 | `energyData` | `energy_data` | `id` | 2 | deviceId, timestamp, energy, power, current, voltage |
| 33 | `sensorReading` | `sensor_reading` | `id` | 2 | deviceId, timestamp, temperature, humidity, motion, lightLevel |
| 34 | `energyAggregate` | `energy_aggregate` | `id` | 3 | deviceId, roomId, interval, avgPower, maxPower, totalEnergy, timestamp |
| 35 | `deviceHealthLog` | `device_health_log` | `id` | 2 | deviceId, status, timestamp, responseTime, errorDetail |
| 36 | `deviceUptime` | `device_uptime` | `id` | 2 | deviceId, date, onlineMinutes, offlineMinutes, uptimePercent |

### 2.7 Supporting tables (3, beyond the 36)

| # | Table | FKs | Justification |
|---|---|---:|---|
| 37 | `amenity_type` | 1 | **Documented** in FM §12 (`id, name, image`); required by `package.amenityType` and `/amenity-types`. Absent from the 36-entity brief. |
| 38 | `app_user_user_role` | 2 | Junction — `user.userRoles` is documented as a list (FM §4). |
| 39 | `job_order_device` | 2 | Junction — `jobOrder.devices` is documented as type `Array` (DM §10). |

---

## 3. Relationships

### 3.1 Dependency order (migration creation order)

```
1. facility                                    (root, 0 FKs)
2. user_role, property_type, amenity_type, department, alert_type,
   current_incident_status
3. app_user, app_user_user_role, job_function, package
4. amenity, employee
5. booking, occupant, stay, invoice
6. service_request, food_category, food_menu, event, offer, holiday
7. device, firmware, job_order, job_order_device
8. energy_data, sensor_reading, energy_aggregate,
   device_health_log, device_uptime
9. device_incident, value_alerts, limit_config
10. notification, fcm_token
11. maintenance_schedule, scheduled_task
```

### 3.2 Principal relationships

- `facility` **1—N** everything (multi-tenant root; 33 of 39 tables carry `facility_id`)
- `booking` **1—N** `occupant`, **1—N** `stay`
- `stay` **N—1** `amenity`, **1—N** `invoice`
- `amenity` **N—1** `package` **N—1** `amenity_type`
- `amenity` **N—1** `property_type` *(inferred — see NEEDS_REVIEW E1)*
- `device` **N—1** `amenity`, **N—1** `device` (self-referential `hub_id`)
- `device` **1—N** `energy_data`, `sensor_reading`, `energy_aggregate`, `device_health_log`, `device_uptime`, `device_incident`, `value_alerts`, `limit_config`
- `employee` **N—1** `department`, **N—1** `job_function`, **N—1** `user_role`
- `app_user` **N—M** `user_role` via `app_user_user_role`
- `job_order` **N—M** `device` via `job_order_device`

### 3.3 Self-reference

`device.hub_id -> device.id` — a device may hang off a parent HUB (DM §10).
Verified as a self-reference, **not** a circular dependency.

---

## 4. Enums

All 13 store the **documented IKANOS literals**, not Python member names.

| Type | Values | Source |
|---|---|---|
| `role_type` | ADMIN, MANAGER, STAFF, GUEST | FM §4 |
| `device_type` | HUB, LOCK, SENSOR, SWITCH, CONTROLLER, MIKOS | DM §10 |
| `device_config_status` | active, inactive, decommissioned | DM §10 |
| `device_status` | Online, Offline, Error | DM §10 / HM §10 |
| `job_order_type` | Commission, Decommission, Maintenance | DM §10 |
| `job_order_status` | Created, InProgress, Completed | DM §10 |
| `incident_status` | Open, Unread, Read, Assigned, Resolved | AM §11 |
| `alert_severity` | Critical, Warning, Info | AM §11 |
| `limit_type` | high, low | AM §11 |
| `notification_type` | alert, service, booking, system, event | NE §8 |
| `scheduled_task_type` | maintenance, housekeeping, sanitation, checkout, system | SH §10 |
| `scheduled_task_status` | Pending, Executed, Cancelled, Failed | SH §10 |
| `aggregate_interval` | 5min, hourly, daily | SDP §9 |

Statuses the docs mention but never enumerate (`amenity.status`, `stay.status`,
`serviceRequest.status`, `event.status`, `invoice.status`) are `VARCHAR` — see
NEEDS_REVIEW D2–D5. `valueAlerts.status` is `INTEGER` exactly as documented.

---

## 5. Naming deviations

| IKANOS | PostgreSQL | Reason |
|---|---|---|
| `user` | `app_user` | `USER` is a PostgreSQL reserved word |
| `function` | `job_function` | `FUNCTION` is a SQL keyword |

All other names are the camelCase → snake_case mapping (`deviceIncident` →
`device_incident`).

---

## 6. Indexes

13 unique constraints (business keys — e.g. unique device name per facility,
unique firmware version per device type per facility) and 33 indexes, added
only where the documentation clearly implies the access pattern:

- `(facility_id, status)` on `amenity`, `stay`, `service_request`, `device`, `job_order`, `value_alerts`
- `(device_id, timestamp)` on `energy_data`, `sensor_reading`, `device_health_log`, `value_alerts`
- `(device_id, interval, timestamp)` on `energy_aggregate`
- `(assigned_to, status)` on `device_incident`, `service_request` — supports the documented staff filter `assignedTo={STAFF_ID}` (CPA §9)
- `(facility_id, created_on)` on `device_incident`, `notification` — supports `createdOn.gte/.lte` (CPA §9)
- `(facility_id, scheduled_at, status)` on `scheduled_task`

These follow CPA §8 "Index Recommendations" directly.

---

## 7. NEEDS_REVIEW summary

Full detail in [`NEEDS_REVIEW.md`](NEEDS_REVIEW.md).

| Category | Count | Highlights |
|---|---:|---|
| Missing entities (A1) | 8 | `property`, `serviceType`, `maintenanceCategory`, `country`, `restaurant`, `roomAmenity`, service configs, RBAC `module` |
| Under-specified entities (A3) | 9 | **`booking` has only 4 documented fields**; `employee` and `user` lack names/phone/status |
| Undefined structures (A2) | 12 | `userRole.permissions` shape; 5 un-enumerated status vocabularies |
| Inferred relationships (A4) | 10 | Assignment targets (`employee` vs `app_user`) are the highest-risk |
| Structural additions (A5) | 3 | `amenity_type` + 2 junctions |

**Nothing was invented.** Where documentation was silent, the gap is recorded.

### Top blockers before seeding
1. **`property` entity missing** — building/floor hierarchy cannot be modelled
2. **`booking` under-specified** — no status, no depart date, no phone
3. **Permission model undefined** — blocks all RBAC
4. **Assignment FK targets ambiguous** — `employee` vs `app_user`, decide before writing data
5. **Status vocabularies un-enumerated**

---

## 8. Verification results

```
Database          : hms_db
Schema            : public
PostgreSQL        : 16.12
Alembic revision  : 8a8456154f0e
Tables created    : 39

Documented entities present : 36/36
Tables with a primary key   : 39/39
Total foreign keys          : 71
Total indexes               : 33 | unique constraints: 13
Circular dependencies       : none
Self-referential            : device (intentional)
Models vs DB                : 39 = 39, no drift either way

RESULT: PASS
```

**Migration reversibility** (verified end-to-end):

| Step | Tables | Enum types |
|---|---:|---:|
| `alembic upgrade head` | 39 | 13 |
| `alembic downgrade base` | 0 | 0 |
| `alembic upgrade head` | 39 | 13 |

`alembic check` → *"No new upgrade operations detected."*

**Tests:** `python -m pytest tests -q` → **8 passed**

**Application smoke test:**
```
GET /health    -> {"status":"ok","app":"HMS Backend","env":"development"}
GET /health/db -> {"status":"ok","database":"hms_db","schema":"public",
                   "alembic_revision":"8a8456154f0e","tables":39}
```

---

## 9. Project structure

```
backend/
├── app/
│   ├── main.py                    FastAPI app — health endpoints only
│   ├── core/config.py             Settings from .env
│   ├── db/
│   │   ├── base.py                Declarative Base, mixins, naming convention
│   │   ├── session.py             Engine + session factory
│   │   └── verify_schema.py       Phase 1D verification report
│   ├── models/
│   │   ├── enums.py               13 documented enums + pg_enum helper
│   │   ├── core.py                19 core entities + amenity_type + junction
│   │   ├── device.py              device, firmware, job_order + junction
│   │   ├── alert.py               5 alert entities
│   │   ├── notification.py        notification, fcm_token
│   │   ├── schedule.py            maintenance_schedule, scheduled_task
│   │   └── sensor.py              5 sensor/health entities
│   ├── schemas/                   (empty — Phase 2)
│   ├── api/                       (empty — Phase 2)
│   └── services/                  (empty — Phase 2)
├── migrations/
│   ├── env.py                     URL from app settings
│   └── versions/8a8456154f0e_*.py 39 tables, reversible
├── scripts/patch_downgrade_enums.py
├── seeds/                         (empty — Phase 2)
├── tests/test_schema_foundation.py
├── docs/{PHASE1_REPORT,NEEDS_REVIEW}.md
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## 10. Scope boundary

Per the brief, **not** done in Phase 1:

- ❌ No seed data
- ❌ No business APIs (only `/health`, `/health/db`)
- ❌ No frontend changes
- ❌ No Pydantic schemas
- ❌ No service layer

**Phase 1 stops here, as instructed.**

---

## 11. Reproducing

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env          # set POSTGRES_PASSWORD

createdb -U postgres hms_db
alembic upgrade head

python -m app.db.verify_schema
python -m pytest tests -q
uvicorn app.main:app --reload
```
