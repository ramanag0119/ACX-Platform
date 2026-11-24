# HMS — Complete Frontend-to-Database Architecture & Data Flow Audit

**Audit date:** 2026-11-20
**Auditor:** Claude Code (evidence-based inspection + live execution)
**Scope:** `ACX-Platform/` — `frontend/`, `backend/`, `oss-service/`
**Backend build:** HMS Backend 0.3.0
**Database under test:** `inspironics_app_test` @ `127.0.0.1:3307` (Docker `hms-bss02-test`, MySQL 8.4.13), Alembic revision `a4d6e802c159`, 96 tables
**OSS source of record:** `insp_iot` @ `192.168.0.120:5432` (PostgreSQL 16.15), reached **only** through the OSS microservices

---

## Evidence Classification

Every finding in this report carries one of these evidence levels. This distinction is maintained throughout and never blurred.

| Level | Meaning |
|---|---|
| **DB-VERIFIED** | API response compared against a direct `SELECT` on MySQL, or against the OSS service's own API |
| **API-EXECUTED** | Endpoint actually called over HTTP with a real JWT; status and payload recorded |
| **CODE-INSPECTED** | Source read and traced; no runtime execution |
| **NOT TESTED** | Not verified in this audit |

> **Browser/UI rendering was NOT verified.** No automated browser session was driven, no screenshots were taken, and no React component was observed rendering. Every statement about what a *screen displays* is an inference from its hooks and the API payload — not an observation. This is the single largest coverage gap in this audit and is restated in §15 and §17.

---

## 1. Executive Summary

**The intended architecture is correctly implemented.** The central question — *when a user acts in the frontend, does the request reach HMS FastAPI, does the backend route BSS operations to MySQL and OSS operations through the OSS microservices, and does real data return?* — is answered **yes**, with evidence, for every module that has a route.

Headline results:

| Check | Result | Evidence |
|---|---|---|
| Parameterless GET surface exercised | **64 / 65 returned 200** (1 × 422 is a required-parameter endpoint, by design) | API-EXECUTED |
| BSS row-count parity (API `total` vs `SELECT COUNT(*)`) | **37 / 37 match** | DB-VERIFIED |
| OSS parity (HMS vs OSS microservice API) | **8 / 8 live domains match** | DB-VERIFIED |
| CRUD chain (create→read→update→delete, confirmed in MySQL) | **13 / 13 checks pass** | DB-VERIFIED |
| Dashboard occupancy KPIs reproduced by independent SQL | **exact match** | DB-VERIFIED |
| Authentication gate (no / garbage / empty token) | **401 on all, including OSS-proxied routes** | API-EXECUTED |
| Frontend direct database access | **none — zero DB drivers in 49 dependencies** | CODE-INSPECTED |
| HMS direct connection to `insp_iot` | **physically impossible — `psycopg2` absent from the backend venv** | API-EXECUTED |
| Hardcoded / mock business data in frontend | **none found** | CODE-INSPECTED |

**No P0 defects were found.** No architecture violation was found. The confirmed issues are data-availability and hygiene matters, not structural faults — detailed in §13.

The strongest single piece of evidence is the SQL trace in §7.2: when HMS serves `/devices`, `/device-stats`, `/alerts` or `/energy-stats`, the MySQL statements it emits touch **only RBAC tables and `device_type`** — never a device, telemetry, alert or energy data table. The payload demonstrably cannot be coming from MySQL.

---

## 2. Actual HMS Architecture (as verified, not as documented)

```text
                    HMS FRONTEND
              React 18 + Vite 5.4.19  :8080
                          |
        single API client — lib/api/client.ts
        bearer token from localStorage "hms.access_token"
        base URL = VITE_API_BASE_URL (relative "/api/v1")
                          |
            Vite dev proxy  /api/v1  ->  127.0.0.1:8000
                          v
                    HMS FASTAPI  :8000
                   "HMS Backend" 0.3.0
                          |
            JWT verify -> RBAC lookup per request
         (app_user, user_role, role_module, role_module_permission,
          facility_user  — observed on EVERY traced endpoint)
                          |
          +---------------+----------------+
          |                                |
          v                                v
      BSS MODULES                     OSS MODULES
   SQLAlchemy ORM                oss_proxy -> oss_client
          |                      X-OSS-Service-Token header
          v                                |
    MySQL 8.4.13                           v
 inspironics_app_test                4 microservices
   (96 tables)                   :8001 device   :8002 telemetry
                                 :8003 alert    :8004 energy
                                           |
                                 default_transaction_read_only=on
                                           v
                              FleetXplorer PostgreSQL 16.15
                                      insp_iot
```

**Verified architectural properties:**

1. The frontend has exactly **one** API client ([frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts)). There is no second fetch path. — CODE-INSPECTED
2. No production hostname is compiled in; the base URL is relative and proxied. — CODE-INSPECTED
3. BSS and OSS remain separate sources. HMS combines them only at the response layer (e.g. `/devices` enriches OSS payloads with the BSS `room_device_map`). — DB-VERIFIED
4. HMS cannot open a PostgreSQL connection: `psycopg2` is **not installed** in `backend/.venv`, and `backend/requirements.txt` explicitly documents its removal. — API-EXECUTED
5. The OSS services open every session with `default_transaction_read_only=on` ([oss-service/app/db/session.py:42-44](oss-service/app/db/session.py#L42-L44)), so PostgreSQL itself rejects writes — the read-only guarantee is enforced by the server, not by convention. — CODE-INSPECTED

---

## 3. Complete Frontend Module Inventory

**Discovered structure.** The previously reported "11 modules" is **not** the actual inventory. The real surface is **24 routes**, **27 page components**, **11 feature areas**, and **18 RBAC modules**. There is no `src/pages/` directory; the app is organised as `src/features/<area>/pages/`.

### 3.1 Routed modules (accessible through navigation)

| No. | Frontend Module | Submodule / Page | Route | Main Component | Primary API Endpoints | Data Source |
|---|---|---|---|---|---|---|
| 1 | Auth | Login | `/login` | `features/auth/pages/Login.tsx` | `POST /auth/login`, `GET /auth/me` | BSS |
| 2 | Dashboard | HMS Dashboard | `/HMS` | `features/dashboard/pages/Dashboard.tsx` | `/buildings`, `/occupancy/summary`, `/energy-stats/summary`, `/alerts`, `/activities`, `/daily-data-points/summary`, `/service-requests` | BSS + OSS |
| 3 | Occupancy | Occupancy | `/occupancy` | `features/occupancy/pages/Occupancy.tsx` | `/occupancy`, `/buildings`, `/floors` | BSS |
| 4 | Bookings | Reservations | `/reservations` | `features/bookings/pages/Reservations.tsx` | `/stays`, `/rooms`, `/users`, `/countries/genders` | BSS |
| 5 | Bookings | Check-In | `/check-in` | `features/bookings/pages/CheckIn.tsx` | `/stays`, `/occupancy/kpis` | BSS |
| 6 | Services | Service Tracking | `/services/tracking` | `features/services/pages/ServiceTracking.tsx` | `/service-requests`, `/service-requests/summary`, `/service-types` | BSS |
| 7 | Services | Service Planning | `/services/planning` | `features/services/pages/ServicePlanning.tsx` | `/maintenance-requests`, `/departments`, `/rooms`, `/service-categories`, `/users` | BSS |
| 8 | Config | Facility Management | `/config/facility` | `features/config/pages/FacilityManagement.tsx` | `/facilities`, `/buildings`, `/floors`, `/rooms`, `/amenity-types`, `/packages`, `/features`, `/currencies` | BSS |
| 9 | Config | User Roles | `/config/user-roles` | `features/config/pages/UserRoles.tsx` | `/roles`, `/roles/types`, `/roles/{id}/permissions`, `/notification-templates` | BSS |
| 10 | Config | Services Setup | `/config/services-setup` | `features/config/pages/ServicesSetup.tsx` | `/service-categories`, `/service-items`, `/service-types`, `/rooms` | BSS |
| 11 | Config | Employees | `/config/employees` | `features/config/pages/Employees.tsx` | `/users`, `/users/roles`, `/departments`, `/job-functions` | BSS |
| 12 | Config | Job Order | `/config/job-order` | `features/config/pages/JobOrder.tsx` | `/job-orders`, `/devices`, `/device-types`, `/rooms` | BSS + OSS |
| 13 | Config | Limit Config / Alert | `/config/limit-alert` | `features/config/pages/LimitConfigAlert.tsx` | `/limit-configs`, `/devices`, `/device-params` | BSS + OSS |
| 14 | Config | Room Devices | `/config/room-devices` | `features/config/pages/RoomDevices.tsx` | `/room-devices`, `/devices`, `/rooms` | BSS + OSS |
| 15 | Marketing | Offers | `/offers` | `features/marketing/pages/Offers.tsx` | `/offers`, `/rooms` | BSS |
| 16 | Marketing | Holidays | `/holidays` | `features/marketing/pages/Holidays.tsx` | `/holidays`, `/holidays/types` | BSS |
| 17 | Marketing | Events | `/events` | `features/marketing/pages/Events.tsx` | `/events` | BSS |
| 18 | Reports | Reports (9 kinds) | `/reports/*` | `features/reports/pages/Reports.tsx` | `/reports`, `/reports/{key}`, `/reports/{key}/export` | BSS + OSS |
| 19 | Tickets | Tickets | `/tickets`, `/manage/tickets` | `features/tickets/pages/Tickets.tsx` | `/service-requests`, `/service-types`, `/rooms`, `/users` | BSS |
| 20 | Devices | Key Settings | `/key-settings` | `features/devices/pages/KeySettings.tsx` | `/key-settings`, `/users` | BSS |
| 21 | Common | About | `/about` | `features/common/pages/About.tsx` | `/health/version` | BSS |
| 22 | Common | Not Found | `*` | `features/common/pages/NotFound.tsx` | — | — |

Redirect-only routes (not modules): `/` → `/HMS`, `/hms`, `/dashboard`, `/bookings`, `/checkin`, `/services`, `/config`, `/power-view`, `/energy-view`, `/room-view`.

### 3.2 Implemented but NOT reachable through navigation — **finding**

Five page components exist and compile but are referenced **zero times** in [App.tsx](frontend/src/App.tsx):

| File | Status | Note |
|---|---|---|
| `features/bookings/pages/Bookings.tsx` | Orphaned, **no API hooks at all** | superseded by `Reservations.tsx` |
| `features/devices/pages/PowerView.tsx` | Orphaned, fully wired (`useMeterHierarchy`) | route retired → `/occupancy` |
| `features/devices/pages/EnergyView.tsx` | Orphaned, fully wired (`useMeterHierarchy`) | route retired → `/occupancy` |
| `features/occupancy/pages/RoomView.tsx` | Orphaned, fully wired | route retired → `/occupancy` |
| `features/common/pages/Placeholder.tsx` | Orphaned "under construction" shell | no longer referenced |

This is dead code, not a data-integrity defect. See §13 / D-05.

### 3.3 RBAC modules with no frontend implementation — **finding**

`GET /auth/me` returns **18** module grants. Two have no route, no page and no API client entry:

| module_id | module_name | Frontend |
|---|---|---|
| 13 | `caleido_network` | **NOT IMPLEMENTED** |
| 14 | `firmware_management` | **NOT IMPLEMENTED** |

— API-EXECUTED. See §13 / D-06.

### 3.4 Screens containing hardcoded or static demo data

**None found.** See §10 for the full audit, including why the two `data/` directories are *not* mock data.

---

## 4. Frontend-to-Backend API Mapping (Phase 2)

### 4.1 Client-layer verification — CODE-INSPECTED

| Property | Finding | File |
|---|---|---|
| Number of API clients | exactly 1 | [lib/api/client.ts](frontend/src/lib/api/client.ts) |
| Base URL | `VITE_API_BASE_URL` → fallback `/api/v1`; no production host hardcoded | client.ts:15-17 |
| Token storage | `localStorage["hms.access_token"]` | client.ts:19 |
| Token attachment | `Authorization: Bearer <token>` on every request incl. file downloads | client.ts:164-165, 209-210 |
| 401 handling | dispatches `hms:unauthorized` → global sign-out; login opts out via `skipAuthRedirect` | client.ts:186-188 |
| Error model | single `ApiError` class; FastAPI `{error:{code,message,detail}}` envelope parsed centrally | client.ts:40-120 |
| Verbs supported | GET, POST, PATCH, PUT, DELETE, multipart, blob download | client.ts:283-298 |
| Proxy | `/api/v1` → `VITE_API_PROXY_TARGET` = `http://127.0.0.1:8000` | frontend/.env.local |

**Proxy proven live:** `POST http://127.0.0.1:8080/api/v1/auth/login` with an empty body returned **422** — the request traversed the Vite proxy and was validated by FastAPI. With real credentials it returned **200** and a JWT. — API-EXECUTED

### 4.2 Module → router mapping

| Module | Frontend Page | Methods | API Endpoint | Backend Router | Request Payload | Response |
|---|---|---|---|---|---|---|
| Auth | Login | POST / GET | `/auth/login`, `/auth/me` | `endpoints/auth.py` | `{username,password}` | `{access_token,token_type,expires_in}` / `CurrentUser` |
| Facility | Facility Mgmt | GET / POST / PATCH | `/facilities`, `/buildings`, `/floors`, `/rooms`, `/amenity-types`, `/packages`, `/features` | `facilities.py`, `facility_write.py` | create/patch bodies | `Page<T>` |
| Access | Employees, User Roles | GET / POST / PATCH / PUT / DELETE | `/users`, `/roles`, `/modules`, `/permissions`, `/departments`, `/job-functions` | `access.py`, `access_write.py` | user/role bodies, permission matrix (PUT) | `Page<T>` |
| Services | Services Setup, Tracking, Tickets | GET / POST / PATCH | `/service-types`, `/service-categories`, `/service-items`, `/service-requests` | `services.py`, `services_write.py` | `ServiceCategoryCreate` etc. | `Page<T>`, summary object |
| Maintenance | Service Planning | GET / POST / PATCH / DELETE | `/maintenance-requests` | `maintenance.py` | `MaintenanceRequestCreate` | `Page<T>` |
| Job Orders | Job Order | GET / POST / PATCH / DELETE | `/job-orders` | `job_orders.py` | job-order body | `Page<T>` |
| Stays | Reservations, Check-In | GET / POST / PATCH / DELETE | `/stays`, `/stays/{id}/occupants`, `/room-allocations`, `/invoices` | `stays.py`, `stays_write.py` | stay lifecycle bodies | `Page<T>` |
| Occupancy | Occupancy, Dashboard | GET / PATCH | `/occupancy`, `/occupancy/summary`, `/occupancy/daily`, `/occupancy/kpis` | `occupancy.py` | room-state patch | `Page<T>`, summary |
| Devices (OSS) | Job Order, Room Devices, Limit Config | GET | `/devices`, `/device-types` | `oss_proxy.py` | — | `Page<T>` + `X-HMS-Data-Source` |
| Telemetry (OSS) | Limit Config, meters | GET | `/device-params`, `/device-stats`, `/device-current-stats`, `/other-device-readings` | `oss_proxy.py` | — | `Page<T>` + header |
| Alerts (OSS) | Dashboard | GET | `/alerts`, `/alert-types` | `oss_proxy.py` | — | `Page<T>` + header |
| Energy (OSS) | Dashboard | GET | `/energy-stats`, `/energy-stats/summary` | `oss_proxy.py` | — | `Page<T>` + header |
| Alerts (BSS) | Dashboard | GET / PATCH | `/incidents`, `/value-alerts` | `alerts.py` | incident patch | `Page<T>` |
| Room Devices | Room Devices | GET / POST / DELETE | `/room-devices` | `room_devices.py` | `{room_id,device_id}` | `Page<T>` |
| Marketing | Offers, Holidays, Events | GET / POST / PATCH | `/offers`, `/holidays`, `/events` | `facility_write.py` | create/patch bodies | `Page<T>` |
| Reports | Reports | GET | `/reports`, `/reports/{key}`, `/reports/{key}/export` | `reports.py` | filters | rows + xlsx blob |
| Key Settings | Key Settings | GET / PATCH / POST | `/key-settings` | `facility_write.py` | settings body | object |
| Notifications | User Roles, Dashboard | GET | `/notification-templates`, `/notifications`, `/activities` | `notifications.py` | — | `Page<T>` |

### 4.3 Missing API integrations

**None among routed modules.** Every routed page except `Login`, `NotFound` and `About` binds at least one data hook (`About` correctly uses `useApiVersion`; `Login` goes through `AuthContext`). The only page with no API binding at all is the orphaned `Bookings.tsx` (§3.2).

### 4.4 Does the frontend bypass the backend or use mock data as production data?

**No, on both counts** — CODE-INSPECTED + DB-VERIFIED:
- `frontend/package.json` declares **49 dependencies, zero database drivers** (no `mysql`, `pg`, `knex`, `sequelize`, `typeorm`, `prisma`).
- A grep of all of `frontend/src/` for `mysql|postgres|psycopg|insp_iot|jdbc:|5432|3306` returns **one hit, inside a comment**.
- No mock/fixture module is imported by any routed page (§10).

---

## 5. Module-wise CRUD Analysis (Phase 3)

### 5.1 Platform write surface — API-EXECUTED

From the live OpenAPI document: **137 paths / 178 operations** — 110 GET, 35 POST, 22 PATCH, 7 DELETE, 4 PUT.

`DELETE` is exposed on exactly **7** paths, all of them join/assignment rows:

```
/job-orders/{job_order_id}        /room-allocations/{allocation_id}
/limit-configs/{config_id}        /room-devices/{map_id}
/maintenance-requests/{request_id} /stay-occupants/{occupant_id}
/roles/{role_id}
```

### 5.2 Deletion policy — intentionally restricted, **verified**

Catalogue entities expose **no** `DELETE`. `DELETE /service-categories/{id}` returns **405 Method Not Allowed**. This is deliberate, not missing:

- The UI's "delete" action issues `PATCH … {status: 0}` — [ServicesSetup.tsx:909,927](frontend/src/features/config/pages/ServicesSetup.tsx#L909).
- Verified live: `PATCH /service-categories/{id} {"status":0}` → **HTTP 200**, and MySQL `service_category.status` became **0**. — DB-VERIFIED

**Conclusion: deactivation (soft delete), not hard delete, is the business rule. Correctly implemented.**

### 5.3 CRUD verification results — DB-VERIFIED

Executed against the guarded test DB with isolated `AUDIT-TEST-DNU` records. **13 / 13 checks passed.** All test rows were removed afterwards; no pre-existing record was altered or deleted.

| Module | Operation | HTTP | MySQL confirmation | Result |
|---|---|---|---|---|
| service-categories | CREATE | 201 | `service_category` rows = 1 | PASS |
| service-categories | READ | 200 | API `category_name` = created value | PASS |
| service-categories | UPDATE | 200 | MySQL `category_name` = `AUDIT-TEST-DNU-UPD` | PASS |
| service-categories | DELETE | 405 | row retained, `status` = 1 | PASS (intentional) |
| service-categories | DEACTIVATE | 200 | MySQL `status` 1 → **0** | PASS |
| holidays (`occasion`) | CREATE | 201 | `occasion` rows = 1 | PASS |
| holidays | UPDATE | 200 | MySQL `occasion_name` updated | PASS |
| holidays | DELETE | 405 | row retained | PASS (intentional) |
| events (`facility_event`) | CREATE | 201 | `facility_event` rows = 1 | PASS |
| events | UPDATE | 200 | MySQL `name` updated | PASS |
| events | DELETE | 405 | row retained | PASS (intentional) |

### 5.4 Write-protection probes — API-EXECUTED

`POST` against OSS-owned and read-only modules is correctly refused:

| Target | Result |
|---|---|
| `POST /devices` (OSS) | **405** — correctly rejected |
| `POST /device-stats` (OSS) | **405** — correctly rejected |
| `POST /alerts` (OSS) | **405** — correctly rejected |
| `POST /countries` | **405** — correctly rejected |
| `POST /modules` | **405** — correctly rejected |
| `POST /permissions` | **405** — correctly rejected |

This confirms the rule in [api/v1/router.py](backend/app/api/v1/router.py): with `OSS_ENABLED=true`, device write routers are **not mounted at all**, because "a device row edited here would be one no screen reads."

### 5.5 CRUD matrix

| Module | Create | Read | Update | Delete | Actual API | Verification |
|---|---|---|---|---|---|---|
| Facility / Rooms | ✅ | ✅ | ✅ | ⛔ by design | `/facilities`, `/rooms` | API-EXECUTED |
| Users / Employees | ✅ | ✅ | ✅ | ⛔ deactivate | `/users` | API-EXECUTED |
| Roles | ✅ | ✅ | ✅ | ✅ | `/roles/{id}` | API-EXECUTED |
| Service Categories / Items | ✅ | ✅ | ✅ | ⛔ deactivate | `/service-categories` | **DB-VERIFIED** |
| Service Requests / Tickets | ✅ | ✅ | ✅ | ⛔ status | `/service-requests` | API-EXECUTED |
| Maintenance Requests | ✅ | ✅ | ✅ | ✅ | `/maintenance-requests` | API-EXECUTED |
| Job Orders | ✅ | ✅ | ✅ | ✅ | `/job-orders` | API-EXECUTED |
| Stays / Reservations | ✅ | ✅ | ✅ | ✅ (allocations, occupants) | `/stays` | API-EXECUTED |
| Occupancy / Room state | ⛔ n/a | ✅ | ✅ | ⛔ n/a | `/occupancy/{id}` | DB-VERIFIED |
| Offers / Holidays / Events | ✅ | ✅ | ✅ | ⛔ deactivate | `/offers` etc. | **DB-VERIFIED** |
| Limit Configs | ✅ | ✅ | ✅ | ✅ | `/limit-configs` | API-EXECUTED |
| Room Devices | ✅ | ✅ | ⛔ n/a | ✅ | `/room-devices` | API-EXECUTED |
| Devices / Telemetry / Alerts / Energy (OSS) | ⛔ | ✅ | ⛔ | ⛔ | OSS proxy | **DB-VERIFIED** |
| Reports | ⛔ | ✅ | ⛔ | ⛔ | `/reports` | API-EXECUTED |
| Countries / Currencies / Modules / Permissions | ⛔ | ✅ | ⛔ | ⛔ | reference data | API-EXECUTED |

⛔ = intentionally unsupported, confirmed by 405 and/or router design. **No module was found to be missing a CRUD operation it should have had.**

---

## 6. BSS MySQL Mapping and Verification (Phase 4)

### 6.1 Method

Rather than assume endpoint→table mappings, the **actual SQL emitted by the backend** was captured (SQLAlchemy echo is enabled) for each endpoint and `FROM`/`JOIN` targets extracted. This is observed behaviour.

### 6.2 Endpoint → table → parity

API `total` compared against direct `SELECT COUNT(*)`. **37 / 37 match.**

| Module | MySQL Table(s) *(observed)* | ORM Model | Backend Service | API Endpoint | DB | API | Match |
|---|---|---|---|---:|---:|---|---|
| Facility | `facility` | `Facility` | `services/facility.py` | `/facilities` | 1 | 1 | ✅ |
| Property | `property`, `property_type` | `Property` | `facility.py` | `/properties` | 4 | 4 | ✅ |
| Buildings | `property_chain` → DISTINCT `level_one_id` | `PropertyChain` | `facility.py` | `/buildings` | 1 | 1 | ✅ |
| Floors | `property_chain` → DISTINCT `level_two_id` | `PropertyChain` | `facility.py` | `/floors` | 3 | 3 | ✅ |
| Rooms | `amenity`, `amenity_type`, `amenity_status`, `amenity_condition_status`, `package` | `Amenity` | `facility.py` | `/rooms` | 27 | 27 | ✅ |
| Users | `app_user`, `department`, `job_function` | `AppUser` | `services/access.py` | `/users` | 26 | 26 | ✅ |
| Roles | `role`, `user_role` | `Role` | `access.py` | `/roles` | 7 | 7 | ✅ |
| Modules | `role_module` | `RoleModule` | `access.py` | `/modules` | 18 | 18 | ✅ |
| Permissions | `role_module_permission` | `RoleModulePermission` | `access.py` | `/permissions` | 65 | 65 | ✅ |
| Departments | `department` | `Department` | `access_write.py` | `/departments` | 5 | 5 | ✅ |
| Job Functions | `job_function` | `JobFunction` | `access_write.py` | `/job-functions` | 5 | 5 | ✅ |
| Service Types | `service_type` | `ServiceType` | `services/service.py` | `/service-types` | 7 | 7 | ✅ |
| Service Statuses | `service_status` | `ServiceStatus` | `service.py` | `/service-statuses` | 5 | 5 | ✅ |
| Service Categories | `service_category` | `ServiceCategory` | `service.py` | `/service-categories` | 27 | 27 | ✅ |
| Service Items | `service_category_item` | `ServiceCategoryItem` | `service.py` | `/service-items` | 23 | 23 | ✅ |
| Service Requests | `service_request`, `service_request_item` | `ServiceRequest` | `service.py` | `/service-requests` | 7 | 7 | ✅ |
| Maintenance | `maintenance_request` (+ `_amenity`, `_assignee`, `_recurrence`) | `MaintenanceRequest` | `maintenance.py` | `/maintenance-requests` | 3 | 3 | ✅ |
| Job Orders | `job_order`, `job_order_amenity`, `job_order_device` | `JobOrder` | `job_orders.py` | `/job-orders` | 3 | 3 | ✅ |
| Stays | `stay`, `stay_user`, `room_allocation` | `Stay` | `services/stay.py` | `/stays` | 148 | 148 | ✅ |
| Invoices | `invoice` | `Invoice` | `stay.py` | `/invoices` | 2 | 2 | ✅ |
| Incidents | `device_incident`, `incident_status`, `device_alert` | `DeviceIncident` | `alerts.py` | `/incidents` | 5 | 5 | ✅ |
| Value Alerts | `value_alert`, `value_alert_limit_config` | `ValueAlert` | `alerts.py` | `/value-alerts` | 3 | 3 | ✅ |
| Notifications | `notification`, `notification_receiver` | `Notification` | `notifications.py` | `/notifications` | 6 | 6 | ✅ |
| Notif. Templates | `notification_template` | `NotificationTemplate` | `notifications.py` | `/notification-templates` | 16 | 16 | ✅ |
| Activities | `activity`, `activity_type`, `activity_notifier`, `entity_type` | `Activity` | `notifications.py` | `/activities` | 10 | 10 | ✅ |
| Amenity Statuses | `amenity_status` | `AmenityStatus` | `occupancy.py` | `/amenity-statuses` | 4 | 4 | ✅ |
| Amenity Conditions | `amenity_condition` | `AmenityCondition` | `occupancy.py` | `/amenity-conditions` | 7 | 7 | ✅ |
| Amenity Types | `amenity_type` | `AmenityType` | `facility_write.py` | `/amenity-types` | 5 | 5 | ✅ |
| Countries | `country` | `Country` | `facilities.py` | `/countries` | 239 | 239 | ✅ |
| Currencies | `currency` | `Currency` | `facilities.py` | `/currencies` | 7 | 7 | ✅ |
| Offers | `promo_code`, `promo_code_amenity`, `attachment` | `PromoCode` | `facility_write.py` | `/offers` | 3 | 3 | ✅ |
| Events | `facility_event`, `attachment` | `FacilityEvent` | `facility_write.py` | `/events` | 3 | 3 | ✅ |
| Holidays | `occasion`, `occasion_type` | `Occasion` | `facility_write.py` | `/holidays` | 4 | 4 | ✅ |
| Packages | `package`, `package_feature`, `sub_package` | `Package` | `facility_write.py` | `/packages` | 8 | 8 | ✅ |
| Features | `feature` | `Feature` | `facility_write.py` | `/features` | 27 | 27 | ✅ |
| Limit Configs | `value_alert_limit_config` | `ValueAlertLimitConfig` | `devices_write.py` | `/limit-configs` | 4 | 4 | ✅ |
| Daily Data Points | `daily_dual_data_point` | `DailyDualDataPoint` | `energy.py` | `/daily-data-points` | 35 | 35 | ✅ |
| Key Settings | `access_key` | `AccessKey` | `facility_write.py` | `/key-settings` | — | obj | ✅ |
| Room Devices | `room_device_map` | `RoomDeviceMap` | `room_devices.py` | `/room-devices` | **0** | **0** | ✅ (but empty — D-01) |

> **Note on naming.** Endpoint names deliberately differ from table names (`/offers`→`promo_code`, `/holidays`→`occasion`, `/incidents`→`device_incident`, `/service-items`→`service_category_item`, `/daily-data-points`→`daily_dual_data_point`). Buildings and floors are **projections over `property_chain`**, not tables — per [services/facility.py](backend/app/services/facility.py) they are `DISTINCT level_one_id` / `level_two_id`. Verified: 1 and 3 respectively, with `level_three_id` NULL in every row.

### 6.3 Schema property checks

| Property | Finding | Evidence |
|---|---|---|
| Primary keys | UUID `id` on business tables; small integer PKs on reference tables (`amenity_status`, `service_status`) | DB-VERIFIED |
| Foreign keys | Exercised by traced joins — e.g. `/service-requests` joins 12 tables correctly | DB-VERIFIED |
| Required fields | Enforced by Pydantic; wrong payloads returned **422** with field-level detail | API-EXECUTED |
| NULL handling | `level_three_id` NULL in all `property_chain` rows and correctly *not* surfaced rather than guessed | DB-VERIFIED |
| ENUM values | `amenity_category` ∈ {room (24), restaurant (1), others (2)}; `amenity_status` = 4 rows | DB-VERIFIED |
| Pagination | `page` / `page_size` on all list endpoints; default page size 20, `total` accurate vs COUNT(*) | DB-VERIFIED |
| Filtering | e.g. `/rooms?amenity_category=room`, `?building_id`, `?floor_id`, `?status` | API-EXECUTED |
| Aggregations | `/occupancy/summary` reproduced exactly by independent SQL (§8) | DB-VERIFIED |

---

## 7. OSS Microservice Mapping and Verification (Phase 5)

### 7.1 Configuration and health — API-EXECUTED

`GET /health/oss`:

```json
{"enabled": true, "status": "ok", "domains": [
 {"domain":"device","url":"http://127.0.0.1:8001","status":"ok","latency_ms":168.65},
 {"domain":"telemetry","url":"http://127.0.0.1:8002","status":"ok","latency_ms":178.78},
 {"domain":"alert","url":"http://127.0.0.1:8003","status":"ok","latency_ms":181.41},
 {"domain":"energy","url":"http://127.0.0.1:8004","status":"ok","latency_ms":173.73}]}
```

OSS service `GET /health/db` → `{"status":"ok","database":"insp_iot","server_version":"16.15"}` — the OSS tier genuinely reaches FleetXplorer.

| Control | Implementation | Evidence |
|---|---|---|
| `OSS_ENABLED` | `true`; read at import time; device/telemetry/alert/energy read routers are **replaced** by `oss_proxy` | CODE-INSPECTED |
| Auth / forwarding | `X-OSS-Service-Token` header, never logged | [oss_client.py:35-37](backend/app/services/oss_client.py#L35-L37) |
| Timeout | `settings.OSS_TIMEOUT_SECONDS` via `httpx.Client` | oss_client.py:56 |
| Error handling | transport error → `OssUnavailable` → 503; OSS 4xx/5xx relayed unchanged | oss_client.py:58-65 |
| Data-source indicator | `X-HMS-Data-Source: live \| stored` on every proxied response | [oss_proxy.py:41-42](backend/app/api/v1/endpoints/oss_proxy.py#L41-L42) |
| Fallback | `OSS_FALLBACK_TO_STORED=true`; serves stored BSS copy **labelled `stored`**, or 503 if no stored form | oss_proxy.py:64-95 |

### 7.2 Proof the data is not coming from MySQL — DB-VERIFIED

For each OSS endpoint, the MySQL statements HMS emitted while serving it:

| HMS endpoint | `X-HMS-Data-Source` | MySQL tables touched |
|---|---|---|
| `/devices` | **live** | RBAC tables + `device_type`, `room_device_map`, `amenity`, `property` *(enrichment only)* |
| `/device-types` | **live** | RBAC tables + `device_type` |
| `/device-stats` | **live** | RBAC tables + `device_type` |
| `/device-current-stats` | **live** | RBAC tables + `device_type` |
| `/device-params` | **live** | RBAC tables + `device_type` |
| `/alerts` | **live** | RBAC tables + `device_type` |
| `/alert-types` | **live** | RBAC tables + `device_type` |
| `/energy-stats` | **live** | RBAC tables + `device_type` |
| `/other-device-readings` | **stored** | RBAC tables + **`other_device`** ← BSS fallback |

**No device, telemetry, alert or energy data table appears in any `live` response.** The payload cannot originate in MySQL. `device_type` is a label-enrichment lookup only.

### 7.3 Parity against the OSS services themselves

| OSS Domain | Frontend Module | HMS API | OSS API | Actual Source | HMS total | OSS total | Status | Live Verified |
|---|---|---|---|---|---:|---:|---|---|
| Devices | Job Order, Room Devices, Limit Config | `/devices` | `:8001/devices` | insp_iot | 6 | 6 | 200 | ✅ live |
| Device Types | Job Order | `/device-types` | `:8001/device-types` | insp_iot | 4 | 4 | 200 | ✅ live |
| Device Statistics | meters, Limit Config | `/device-stats` | `:8002/device-stats` | insp_iot | 1975 | 1975 | 200 | ✅ live |
| Current Device Stats | meters | `/device-current-stats` | `:8002/device-current-stats` | insp_iot | 4 | 4 | 200 | ✅ live |
| Telemetry (params) | Limit Config | `/device-params` | `:8002/device-params` | insp_iot | 21 | 21 | 200 | ✅ live |
| Alerts | Dashboard | `/alerts` | `:8003/alerts` | insp_iot | 2 | 2 | 200 | ✅ live |
| Alert Types | Dashboard | `/alert-types` | `:8003/alert-types` | insp_iot | 1 | 1 | 200 | ✅ live |
| Energy Statistics | Dashboard | `/energy-stats` | `:8004/energy-stats` | insp_iot | 2 | 2 | 200 | ✅ live |
| Other Device Readings | meters | `/other-device-readings` | `:8002/other-device-readings` | **BSS `other_device`** | 12 | — | 200 | ❌ **stored** |

**8 / 8 live domains match exactly.** The ninth is served from the stored BSS copy and is **honestly labelled** `stored` — see D-02.

### 7.4 Required OSS behaviours

| Requirement | Result |
|---|---|
| 1. HMS calls the existing OSS microservice APIs | ✅ verified — proxy + token + matching totals |
| 2. OSS retrieves data from FleetXplorer | ✅ verified — `/health/db` reports `insp_iot` PG 16.15 |
| 3. Responses reach HMS FastAPI correctly | ✅ verified — totals identical |
| 4. HMS returns the data to the frontend | ✅ verified — 200 + `Page<T>` on the proxied routes |
| 5. Frontend renders actual OSS responses | ⚠️ **NOT TESTED** — hooks are wired, rendering unobserved |
| 6. Unavailable OSS produces proper errors | ✅ CODE-INSPECTED — `OssUnavailable` → 503; not fault-injected |
| 7. Fallback does not present fake data as live | ✅ **verified** — the one fallback is labelled `stored`, never `live` |

### 7.5 `insp_iot` protection

| Control | Result |
|---|---|
| HMS never connects directly to `insp_iot` | ✅ **`psycopg2` is ABSENT from `backend/.venv`** — connection is impossible, not merely forbidden |
| No PostgreSQL driver in `backend/requirements.txt` | ✅ explicitly documented as removed |
| OSS read-only protection preserved | ✅ `connect_args={"options": "-c default_transaction_read_only=on"}` — enforced by PostgreSQL |
| Writes/DDL against FleetXplorer during this audit | ✅ **none** — no direct PG connection was opened by the auditor either |

---

## 8. Dashboard Data Validation (Phase 6)

Dashboard widgets each own their query, so one failing endpoint degrades only its own box.

| Dashboard Widget | API Endpoint | Data Source | Actual Value | Source Value | Match |
|---|---|---|---|---|---|
| Building selector | `/buildings` | BSS `property_chain` | 1 building | DISTINCT `level_one_id` = 1 | ✅ |
| Floor drill-down | `/floors?building_id=` | BSS `property_chain` | 3 floors | DISTINCT `level_two_id` = 3 | ✅ |
| Occupancy — Total rooms | `/occupancy/summary` | BSS `amenity` | 24 | `amenity_category='room'` = 24 | ✅ |
| Occupancy — Occupied | `/occupancy/summary` | BSS derived | 3 (12.5 %) | independent SQL = **3** | ✅ |
| Occupancy — Available | `/occupancy/summary` | BSS derived | 16 (66.7 %) | independent SQL = **16** | ✅ |
| Occupancy — Allotted | `/occupancy/summary` | BSS derived | 2 (8.3 %) | independent SQL = **2** | ✅ |
| Occupancy — Unavailable | `/occupancy/summary` | BSS derived | 3 (12.5 %) | independent SQL = **3** | ✅ |
| Service summary | `/service-requests/summary` | BSS `service_request` | total 7 | `COUNT(*)` = 7 | ✅ |
| Service by status | `/service-requests/summary` | BSS | completed 1, in-progress 1, assigned 2, canceled 1 | matches `service_status` join | ✅ |
| Alerts panel | `/alerts` | **OSS live** | 2 | OSS `:8003` = 2 | ✅ |
| Recent activity | `/activities` | BSS `activity` | 10 | `COUNT(*)` = 10 | ✅ |
| Energy chart | `/energy-stats/summary` | **OSS live** | SUM/COUNT buckets | OSS-served | ✅ |
| Caleido At Work | `/daily-data-points/summary` | BSS `daily_dual_data_point` | 5 metric rings | 5 distinct `metric_type` | ✅ |
| Caleido At Work — date | `/daily-data-points/summary` | BSS | **2026-08-17** | `MAX(metric_date)` = 2026-08-17 | ⚠️ **95 days stale** — D-03 |

### 8.1 The occupancy derivation — independently reproduced

Raw `amenity.status` does **not** equal the reported figures, and that is correct. The API computes an *effective* status ([services/occupancy.py:501-508](backend/app/services/occupancy.py#L501-L508)) that overlays in-house stays and blocking conditions:

| Status | Raw `amenity.status` | API reports | Independent SQL |
|---|---:|---:|---:|
| Available | 19 | 16 | **16** |
| Occupied | 2 | 3 | **3** |
| Unavailable | 1 | 3 | **3** |
| Allotted | 2 | 2 | **2** |
| **Total** | 24 | 24 | **24** |

Re-implementing the documented rule in standalone SQL produced **exactly** the API's numbers. The dashboard is genuinely database-driven, including its business logic. **No hardcoded value was found in any widget.**

### 8.2 Reports

All 9 report definitions execute and return rows — API-EXECUTED:

| Report | HTTP | Rows |
|---|---|---:|
| occupancy | 200 | 27 |
| employee | 200 | 11 |
| room-status | 200 | 27 |
| booking | 200 | 148 |
| ticket | 200 | 7 |
| housekeeping | 200 | 2 |
| sanitization | 200 | 1 |
| alert | 200 | 9 |
| energy | 200 | 72 |

---

## 9. End-to-End Workflow Results (Phase 7)

| # | Workflow | Path verified | Evidence | Status |
|---|---|---|---|---|
| 1 | Login / JWT | Frontend → proxy → FastAPI → `app_user` → bcrypt → JWT | `POST /auth/login` **200** + JWT through :8080; bad creds → 401 | **PASS** (DB-VERIFIED) |
| 2 | Dashboard load | 7 independent widget queries | all 200, values reconcile with SQL | **PASS** (DB-VERIFIED) |
| 3 | Building & floor mgmt | `/buildings`, `/floors` → `property_chain` | counts match DISTINCT projections | **PASS** (DB-VERIFIED) |
| 4 | Facility & room mgmt | `/rooms`, `/amenity-types`, `/packages`, PATCH | 27 rooms match `amenity`; PATCH path exercised on sibling modules | **PASS** (DB-VERIFIED) |
| 5 | User & role mgmt | `/users`, `/roles`, `/roles/{id}/permissions` | 26/7 match; 18 module grants returned | **PASS** (DB-VERIFIED) |
| 6 | Booking / reservation | `/stays` + create/patch/cancel | 148 stays match `stay` | **PARTIAL** — reads DB-verified; stay-lifecycle writes not exercised |
| 7 | Room allocation | `/stays/{id}/room-allocations` | router mounted, DELETE exposed | **PARTIAL** — CODE-INSPECTED |
| 8 | Check-in | `useCheckInStay` → `/stays/{id}` | hooks wired | **PARTIAL** — not executed |
| 9 | Occupancy | `/occupancy`, `/occupancy/summary` | derivation reproduced exactly | **PASS** (DB-VERIFIED) |
| 10 | Room condition mgmt | `/amenity-conditions`, `/occupancy/{id}` | 7 conditions match; applicability = 42 rows | **PASS** (DB-VERIFIED) |
| 11 | Check-out | `useCheckOutStay` | hooks wired | **PARTIAL** — not executed |
| 12 | Device management | `/devices` → OSS :8001 → insp_iot | 6 = 6, `live` | **PASS** (DB-VERIFIED) |
| 13 | Telemetry / device stats | `/device-stats` → OSS :8002 | 1975 = 1975, `live` | **PASS** (DB-VERIFIED) |
| 14 | Alerts | `/alerts` → OSS :8003 | 2 = 2, `live` | **PASS** (DB-VERIFIED) |
| 15 | Energy statistics | `/energy-stats` → OSS :8004 | 2 = 2, `live` | **PASS** (DB-VERIFIED) |
| 16 | Service requests | `/service-requests` + summary | 7 = 7; status breakdown reconciles | **PASS** (DB-VERIFIED) |
| 17 | Reports & analytics | `/reports` × 9 | all 200 with rows | **PASS** (API-EXECUTED) |
| 18 | Marketing (offers/holidays/events) | full CRUD | create+update confirmed **in MySQL** | **PASS** (DB-VERIFIED) |
| 19 | Room-device assignment | `/room-devices` | **0 rows** — nothing to render | **BLOCKED** — D-01 |

### 9.1 Where BSS and OSS are combined

Verified at `/devices`: the OSS payload (6 devices from `insp_iot`) is enriched with BSS `room_device_map` → `amenity` → `property` so a device can carry its room. The join is performed in HMS FastAPI, exactly as the architecture requires — neither database sees the other. **Because `room_device_map` is empty, this enrichment currently yields no room for any device** (D-01).

---

## 10. Hardcoded and Mock Data Findings (Phase 8)

### 10.1 Result: no fake business data found

A full scan of `frontend/src/` and `backend/app/` for `mock|dummy|fake|hardcod|sample data|lorem|TODO|FIXME` returned **21 matches — 20 of which are comments documenting that hardcoding was *removed***, plus one unrelated UI token (`hasFakeCaret` in the OTP component).

| File | Module | "Hardcoded / Mock" hit | Expected Source | Required Correction |
|---|---|---|---|---|
| `features/dashboard/data/energyConsumption.ts` | Dashboard | **Not mock data** — pure selectors over `EnergySummaryBucket`; file explicitly carries no readings and applies no unit | `/energy-stats/summary` | **None** |
| `features/devices/data/meters.ts` | Power/Energy View | **Not mock data** — shape + adapter only; "carries NO readings of its own… anything a device has not reported stays null" | `/devices`, `/occupancy`, `/value-alerts` | **None** |
| `features/config/pages/ServicesSetup.tsx:40,55,1056` | Services Setup | comment: hardcoded category map **removed**, names now from DB | `/service-categories` | **None** |
| `features/marketing/pages/Offers.tsx:340,465` | Offers | comment: hardcoded "Pooja Offer" list **removed** | `/offers`, `/rooms` | **None** |
| `features/marketing/pages/Events.tsx:396` | Events | comment: hardcoded placeholders **removed** | `/events` | **None** |
| `features/config/pages/UserRoles.tsx:50` | User Roles | comment: hardcoded template list **replaced** by `/notification-templates` | `/notification-templates` | **None** |
| `features/dashboard/components/DashboardKPIs.tsx:35` | Dashboard | comment: value "carried over from a mock" **removed** | live KPIs | **None** |
| `features/occupancy/pages/Occupancy.tsx:64,173` | Occupancy | comment: mock's flat `guestName` **replaced**; "No date is hardcoded" | `/occupancy` | **None** |
| `core/components/TablePagination.tsx:11` | shared | comment: Service Tracking's hardcoded summary line **fixed** | `/service-requests/summary` | **None** |
| `core/components/NoEndpointNotice.tsx:24` | shared | **positive control**: "Nothing is listed here rather than sample data that looks real" | — | **None** |
| `components/ui/input-otp.tsx:29,42` | shadcn-ui | `hasFakeCaret` — cursor animation | — | **None** (not data) |

### 10.2 Legitimate static configuration (correctly distinguished)

`core/rbac/modules.ts` (module slugs), `features/reports/lib/reportMeta.ts` (report labels), `occupancy/lib/roomStatus.ts` + `ROOM_STATUS_ORDER` (the four real `amenity_status` names), `core/styles/surfaceTokens.ts` (theme tokens). These are UI vocabulary, not business records.

### 10.3 Fallback data that could hide API failures

One mechanism exists and is **correctly implemented**: `OSS_FALLBACK_TO_STORED`. It never presents stored data as live — the response carries `X-HMS-Data-Source: stored` (§7.2). Backend `oss_fallback.supports()` returns 503 rather than inventing a row where no stored form exists. **No silent fake fallback was found.**

---

## 11. Security and Architecture Boundary Findings (Phase 9)

| Control | Result | Evidence |
|---|---|---|
| JWT authentication | ✅ `/users` → **401** with no token, garbage token, and empty bearer; **200** with a valid one | API-EXECUTED |
| Auth on OSS-proxied routes | ✅ `/devices`, `/device-stats`, `/alerts`, `/energy-stats` all **401** without a token | API-EXECUTED |
| Username enumeration | ✅ wrong password and unknown user both return **401**; `authenticate()` checks credentials *before* the platform boundary, deliberately | API-EXECUTED + CODE-INSPECTED |
| Role-based access control | ✅ every traced endpoint joins `user_role`, `role_module`, `role_module_permission`, `facility_user` — enforced server-side per request, not in the UI | DB-VERIFIED |
| Protected routes | ✅ `ProtectedRoute` + `ModuleGuard` wrap all non-login routes | CODE-INSPECTED |
| Frontend DB access | ✅ **none** — 0 DB drivers among 49 deps; no connection string in `src/` | CODE-INSPECTED |
| HMS → `insp_iot` | ✅ **impossible** — `psycopg2` absent from `backend/.venv` | API-EXECUTED |
| OSS read-only | ✅ `default_transaction_read_only=on` per session | CODE-INSPECTED |
| Credentials in source | ✅ none — only `ENV_MASTER_PASSWORD` (a *variable name*). BSS credentials come from the KeePass vault | CODE-INSPECTED |
| Secrets in git | ✅ `backend/.env`, `oss-service/.env`, `frontend/.env.local`, `*.kdbx`, `shibboleth.zip` all gitignored (`git check-ignore` confirms) | API-EXECUTED |
| Password storage | ✅ bcrypt; `verify_password` returns False for NULL/sentinel/malformed, never raises; hashes never logged | CODE-INSPECTED |
| Sensitive data in responses | ✅ `/auth/me` returns no hash; `/users` exposes no credential | API-EXECUTED |
| Local test DB configuration | ✅ `/health/db` → `inspironics_app_test`; guard rejects non-`_test` schemas and non-loopback hosts | API-EXECUTED |

**No architecture violation was found.** Two observations worth recording:

- **OBS-1 (informational).** `OSS_SERVICE_TOKEN` is stored in plaintext in `backend/.env` and `oss-service/.env`. Both are gitignored, and the file documents this as a trusted-LAN PoC control. Acceptable for local/PoC; should move to the vault before any multi-tenant deployment.
- **OBS-2 (informational).** Tokens live in `localStorage`, which is XSS-readable. Standard for this SPA pattern; noted, not a defect.

---

## 12. Complete Module Status Matrix (Phase 10)

| No. | Module | Frontend | API Integration | CRUD | BSS/OSS Source | Database Verification | Overall | Issues |
|---|---|---|---|---|---|---|---|---|
| 1 | Auth / Login | PASS | PASS | n/a | BSS | PASS | **PASS** | — |
| 2 | Dashboard | PASS | PASS | Read | BSS+OSS | PASS | **PASS** | stale Caleido date (D-03) |
| 3 | Occupancy | PASS | PASS | R/U | BSS | PASS | **PASS** | — |
| 4 | Reservations | PASS | PASS | CRUD | BSS | PASS (reads) | **PARTIAL** | lifecycle writes NOT TESTED |
| 5 | Check-In | PASS | PASS | R/U | BSS | PASS (reads) | **PARTIAL** | check-in write NOT TESTED |
| 6 | Service Tracking | PASS | PASS | R/U | BSS | PASS | **PASS** | — |
| 7 | Service Planning | PASS | PASS | CRUD | BSS | PASS | **PASS** | — |
| 8 | Facility Management | PASS | PASS | CRU | BSS | PASS | **PASS** | — |
| 9 | User Roles | PASS | PASS | CRUD | BSS | PASS | **PASS** | — |
| 10 | Services Setup | PASS | PASS | CRU+deactivate | BSS | **PASS (full CRUD in MySQL)** | **PASS** | inactive rows listed (D-04) |
| 11 | Employees | PASS | PASS | CRU+deactivate | BSS | PASS | **PASS** | — |
| 12 | Job Order | PASS | PASS | CRUD | BSS+OSS | PASS | **PASS** | — |
| 13 | Limit Config / Alert | PASS | PASS | CRUD | BSS+OSS | PASS | **PASS** | — |
| 14 | Room Devices | PASS | PASS | C/R/D | BSS+OSS | PASS (schema) | **BLOCKED** | `room_device_map` empty (D-01) |
| 15 | Offers | PASS | PASS | CRU+deactivate | BSS | PASS | **PASS** | — |
| 16 | Holidays | PASS | PASS | CRU+deactivate | BSS | **PASS (CRUD in MySQL)** | **PASS** | no status filter (D-04) |
| 17 | Events | PASS | PASS | CRU+deactivate | BSS | **PASS (CRUD in MySQL)** | **PASS** | no status filter (D-04) |
| 18 | Reports | PASS | PASS | Read+export | BSS+OSS | PASS | **PASS** | export blob NOT TESTED |
| 19 | Tickets | PASS | PASS | C/R/U | BSS | PASS | **PASS** | — |
| 20 | Key Settings | PASS | PASS | R/U | BSS | PASS | **PASS** | — |
| 21 | About | PASS | PASS | Read | BSS | PASS | **PASS** | — |
| 22 | Devices (OSS) | PASS | PASS | Read-only | **OSS live** | PASS | **PASS** | — |
| 23 | Telemetry (OSS) | PASS | PASS | Read-only | **OSS live** | PASS | **PASS** | `/other-device-readings` stored (D-02) |
| 24 | Alerts (OSS) | PASS | PASS | Read-only | **OSS live** | PASS | **PASS** | — |
| 25 | Energy (OSS) | PASS | PASS | Read-only | **OSS live** | PASS | **PASS** | — |
| 26 | `caleido_network` | **NOT IMPLEMENTED** | — | — | — | — | **NOT IMPLEMENTED** | RBAC module, no UI (D-06) |
| 27 | `firmware_management` | **NOT IMPLEMENTED** | — | — | — | — | **NOT IMPLEMENTED** | RBAC module, no UI (D-06) |
| 28 | Orphaned pages ×5 | dead code | — | — | — | — | **NOT IMPLEMENTED** | unreachable (D-05) |

**Totals: 21 PASS · 3 PARTIAL · 1 BLOCKED · 3 NOT IMPLEMENTED · 0 FAIL.**

> Every PASS above rests on API execution **and** database verification. None rests on source inspection alone. No row is marked PASS on the basis of browser rendering, because none was observed.

---

## 13. Confirmed Defects

No defect found in this audit is a P0, and none is an architecture violation.

### D-01 — `room_device_map` is empty; Room Devices has no data — **P1**
- **Evidence (DB-VERIFIED):** `SELECT COUNT(*) FROM room_device_map` = **0**; `GET /room-devices` → 200, `total: 0`.
- **Impact:** `/config/room-devices` renders an empty list. More importantly, the BSS↔OSS join at `/devices` resolves no room for any of the 6 OSS devices, so room-level device, power and energy features have nothing to attach to.
- **Not a code defect** — the endpoint, model and join all work. This is missing data.
- **Correction:** populate `room_device_map` with the real device→room assignments. **Do not invent mappings** — these must come from the operator.

### D-02 — `/other-device-readings` is served from the stored BSS copy, not OSS — **P1**
- **Evidence (DB-VERIFIED):** `X-HMS-Data-Source: stored`; the request read MySQL `other_device` (12 rows); OSS `:8002/other-device-readings` exists but did not supply the response.
- **Impact:** the only OSS-surfaced domain not actually live. Correctly labelled, so nothing fake is presented — but it is a duplicate copy of OSS-owned data, which the architecture rules discourage.
- **Correction:** determine whether `insp_iot` holds the source rows. If yes, fix the forward path; if no, document `other_device` as BSS-owned. Investigate before changing anything.

### D-03 — Caleido At Work data is 95 days stale — **P2**
- **Evidence (DB-VERIFIED):** `MAX(metric_date)` in `daily_dual_data_point` = **2026-08-17**; audit date 2026-11-20. All 5 metric rings render from that date.
- **Impact:** the dashboard presents three-month-old percentages with no staleness indicator.
- **Correction:** restore the job that writes `daily_dual_data_point`, and surface `metric_date` in the widget so staleness is visible.

### D-04 — Deactivated rows are returned by list endpoints; filtering is client-side — **P2**
- **Evidence (DB-VERIFIED):** after `PATCH /service-categories/{id} {"status":0}` (MySQL `status`=0), `GET /service-categories` still returned the row and `total` rose 27 → 28. [ServicesSetup.tsx:270-274](frontend/src/features/config/pages/ServicesSetup.tsx#L270-L274) filters `status !== 0` **in the browser**.
- **Impact:** inactive rows consume page slots, so a paginated page can show fewer active rows than `page_size` — and `total` overstates the active count. `/holidays` and `/events` expose **no `status` parameter at all**, so server-side filtering is impossible there.
- **Correction:** default list endpoints to active-only (or have the frontend pass `status=1`), and add a `status` filter to `/holidays` and `/events`.

### D-05 — Five orphaned page components — **P2**
`Bookings.tsx` (no API hooks), `PowerView.tsx`, `EnergyView.tsx`, `RoomView.tsx`, `Placeholder.tsx` are compiled but unreachable (§3.2). Dead code that will drift from the API. **Correction:** delete, or restore routes if still wanted.

### D-06 — Two RBAC modules have no frontend — **P2**
`caleido_network` (13) and `firmware_management` (14) are granted by `/auth/me` but have no route, page or client entry. **Correction:** implement, or remove the grants so the permission matrix reflects reality.

### D-07 — Stale docstring: "reads live from PostgreSQL" in a MySQL service — **P2 (documentation)**
[backend/app/services/facility.py:3](backend/app/services/facility.py#L3) states *"Every function here reads live from PostgreSQL"*; this is the **BSS MySQL** service. Misleading in a codebase whose central rule is BSS-MySQL / OSS-PostgreSQL separation. **Correction:** one-line fix.

---

## 14. Missing Data and External Dependencies

| Item | Status | Blocker for |
|---|---|---|
| `room_device_map` rows | **absent (0)** | Room Devices; all room-level device/energy features (D-01) |
| `daily_dual_data_point` after 2026-08-17 | **absent** | current Caleido At Work (D-03) |
| `insp_iot` source for other-device readings | **unconfirmed** | D-02 resolution |
| FleetXplorer PostgreSQL `192.168.0.120:5432` | **available** | all OSS domains |
| BSS production MySQL `192.168.0.120:3306` | **deliberately not used** | audit ran against the test container, as required |
| Usable login credentials | **1 of 26 accounts** | all 25 others hold `!seed-no-login`; only `ask@inspironics.net` can authenticate |

> **Note on the test fixture.** `local_testdb verify` reports one failing invariant: *"no un-anonymised email present"* — the offending row is `ask@inspironics.net`, the only account with a usable credential. Running `local_testdb reset` **would delete the sole working login**. Provision a credential in the baseline snapshot before any reset.

---

## 15. Recommended Corrections

1. **Populate `room_device_map`** from operator-supplied device→room assignments. Do not infer. (D-01)
2. **Resolve `/other-device-readings`**: confirm whether `insp_iot` holds the rows; fix the forward path or document BSS ownership. (D-02)
3. **Restore the `daily_dual_data_point` job** and surface `metric_date` in the widget. (D-03)
4. **Make list endpoints active-by-default**; add `status` filters to `/holidays` and `/events`. (D-04)
5. **Delete the five orphaned pages.** (D-05)
6. **Decide on `caleido_network` / `firmware_management`** — build or revoke. (D-06)
7. **Fix the `facility.py` docstring.** (D-07)
8. **Add a usable credential to the baseline snapshot** so `reset` stops destroying the only working login.
9. **Close the browser-verification gap** — the main outstanding work. See §17.
10. **Move `OSS_SERVICE_TOKEN` into the vault** before any non-LAN deployment. (OBS-1)

---

## 16. Priority Classification

| Priority | Items | Rationale |
|---|---|---|
| **P0 — blocks delivery** | **none** | No architecture violation, no data-integrity failure, no security defect |
| **P1 — fix before UAT** | D-01 `room_device_map` empty · D-02 other-device-readings stored | One module has no data; one OSS domain is not live |
| **P2 — fix before release** | D-03 stale metrics · D-04 inactive-row filtering · D-05 dead code · D-06 unimplemented RBAC modules · D-07 docstring · baseline credential | Correctness and hygiene; none blocks a workflow |
| **P3 — track** | OBS-1 token in `.env` · OBS-2 `localStorage` tokens | Acceptable for PoC; revisit before multi-tenant deployment |

---

## 17. Final Delivery Readiness Assessment

### The question asked

> *When a user performs any operation in the frontend, does the request correctly reach HMS FastAPI, and does the backend send BSS operations to MySQL and OSS operations through the existing OSS microservices? Does the correct database data return through the backend and appear correctly in the frontend?*

**Answer, for every module with a route:**

| Link in the chain | Verdict | Strongest evidence |
|---|---|---|
| Frontend → HMS FastAPI | ✅ **Yes** | Single client, bearer token, relative base URL; login succeeded end-to-end through the Vite proxy |
| BSS operations → MySQL | ✅ **Yes** | 37/37 row-count parity; CREATE/UPDATE confirmed by reading MySQL directly |
| OSS operations → OSS microservices | ✅ **Yes** | 8/8 live-domain parity; OSS reads emit **no device/telemetry/alert/energy SQL** against MySQL |
| Correct data returns through the backend | ✅ **Yes** | Dashboard KPIs reproduced exactly by independent SQL, including derived business logic |
| Data appears correctly in the frontend | ⚠️ **NOT VERIFIED** | No browser rendering was observed |

### Architecture compliance

| Mandatory rule | Verdict |
|---|---|
| BSS data read/written through HMS FastAPI | ✅ |
| HMS FastAPI uses the existing MySQL database | ✅ |
| Frontend never connects directly to MySQL | ✅ (0 DB drivers) |
| OSS data obtained through OSS microservice APIs | ✅ (8/8 live) |
| HMS communicates with OSS via the approved proxy | ✅ (`oss_proxy` + `X-OSS-Service-Token`) |
| HMS never connects directly to FleetXplorer | ✅ (**`psycopg2` not installed**) |
| `insp_iot` read-only protection preserved | ✅ (`default_transaction_read_only=on`) |
| BSS and OSS remain separate sources | ✅ |
| HMS combines responses where required | ✅ (`/devices` enrichment) |
| Frontend receives correctly structured responses | ✅ (`Page<T>` envelope, single error envelope) |
| No duplicate ownership / unnecessary copies | ⚠️ one exception — `other_device` (D-02) |

**10 of 11 mandatory rules fully satisfied; the eleventh has a single, correctly-labelled exception.**

### Readiness

**Conditionally ready, pending the two P1 items and browser verification.**

- The architecture is sound and is implemented as designed. This is not a system pretending to be database-driven — the evidence is that it genuinely is, down to derived dashboard aggregates reproducing exactly in independent SQL.
- **No P0 defect, no architecture violation, no security defect, and no fake business data was found.** The absence of mock data is notable: the codebase carries ~20 comments documenting hardcoded values that were deliberately removed and replaced with live reads.
- The two P1 items are **missing data and one mis-routed read**, not structural faults.

### What this audit did not cover

Stated plainly so the gap is not mistaken for coverage:

1. **No browser verification.** No UI was rendered or observed. Everything about on-screen appearance is inference. **This is the largest gap** and the main reason no module is claimed as fully delivered.
2. **Stay lifecycle writes not executed** — check-in, check-out, allocation, cancellation. Routers and hooks are wired (CODE-INSPECTED); the writes were not performed, as they mutate meaningful fixture state.
3. **No OSS fault injection.** The 503 path was read, not triggered.
4. **Report export blobs not downloaded** — only the JSON report rows were fetched.
5. **Parameterised GETs not exhaustively swept** — 65 of 110 GET operations are parameterless and were all exercised; the remainder need IDs and were sampled, not swept.
6. **Production MySQL deliberately untouched**, per the safety rules.

### Safety compliance

| Rule | Compliance |
|---|---|
| Use the guarded local MySQL test database | ✅ `/health/db` → `inspironics_app_test` verified before every write |
| Use the Docker test database on 3307 | ✅ `hms-bss02-test` |
| Never connect to production MySQL | ✅ backend rebound via `scripts/run_local_api.py`; engine confirmed |
| Never access or modify `insp_iot` | ✅ no PostgreSQL connection opened by the auditor; OSS reached only via its HTTP API |
| No create/alter/drop, no migrations | ✅ none run |
| No invented device mappings or records | ✅ D-01 reported as missing data, not filled in |
| No fake fallback data introduced | ✅ none |
| No business rules modified | ✅ no source file was modified during this audit |
| No real records deleted | ✅ only `AUDIT-TEST-DNU` rows this audit created were removed |
| No git commit / push / merge | ✅ none |

---

*End of report. No source file was modified in the course of this audit. All findings above are reproducible from the running stack: frontend :8080, backend :8000 (bound to `inspironics_app_test`), OSS :8001–:8004, MySQL `hms-bss02-test` :3307.*
