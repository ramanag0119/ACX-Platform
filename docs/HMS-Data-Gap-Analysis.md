# HMS Complete Application — A-to-Z Frontend Data Gap Analysis

**Target application:** ACX-Platform (HMS Frontend, IKANOS portal)
**Branch:** `feature/Dashbord-CSS`
**Audit date:** 2026-08-15
**Auditor scope:** Frontend only. No code was modified. No mock data was created. No values were invented.

---

## 0. Status of this document

| Part | Content | Status |
|---|---|---|
| A | Complete HMS frontend inventory + every observed data gap, hardcoded value, placeholder, dead control and inconsistency | ✅ Complete |
| B | `Expected Data/Value` and `IKANOS Reference` columns, sourced from `HMS_ikanos\Ikanos_code\` | 🔄 In progress — Dashboard, Header, Auth, Occupancy, Bookings done |
| C | Section 6 — IKANOS functionality missing completely from HMS | 🔄 In progress |

**Rules honoured:** no code modified · no mock data created · no values invented · every `Expected Data/Value` cites a specific IKANOS document and section.

### 0.1 IKANOS source of truth — located and adopted

**Location:** `d:\Inspornics\HMS_ikanos\Ikanos_code\` — 12 documents, 5,742 lines.

| Document | Lines | Role in this audit |
|---|---:|---|
| `COMPLETE_PROJECT_ANALYSIS_REPORT.md` | 1,385 | **Master reference.** Entity/field tables (§8), sidebar-to-domain map (§10), user journeys (§6), permission model (§7), business logic deep dive (§20) |
| `1_FACILITI_MANAGER_DOCUMENTATION.md` | 500 | Facility, rooms, packages, bookings, stays, occupants, employees, service requests, events, offers, holidays, invoices |
| `2_DEVICE_MANAGER_DOCUMENTATION.md` | 458 | Device lifecycle, commissioning, firmware, job orders, inventory |
| `3_DEVICE_COMMUNICATOR_DOCUMENTATION.md` | 356 | HUB/device command bridge, key commands, telemetry ingress |
| `4_ALARM_MANAGER_DOCUMENTATION.md` | 459 | Alert creation, assignment, resolution, `deviceIncident` / `valueAlerts` |
| `5_NOTIFICATION_ENGINE_DOCUMENTATION.md` | 394 | FCM, in-app, SMS, email, token registry |
| `6_REPORTS_HANDLER_DOCUMENTATION.md` | 510 | Report aggregation and export |
| `7_SCHEDULE_HANDLER_DOCUMENTATION.md` | 420 | Cron/recurring maintenance, housekeeping, sanitation, checkout, expiry |
| `8_SENSOR_DATA_PROCESSOR_DOCUMENTATION.md` | 439 | Telemetry normalization, thresholds, energy aggregation |
| `9_HEALTH_MONITOR_DOCUMENTATION.md` | 471 | Heartbeat, offline detection, uptime |
| `8_LAYERS_ARCHITECTURE_DIAGRAMS.md` | 232 | Layer diagrams |
| `README.md` | 118 | Repo overview |
| `ALERT_SYSTEM_DOCUMENTATION.md` | 0 | **Empty file — no content** |

**What IKANOS is** (§1): a hotel/facility control and operations platform in the Caleido suite — Angular 9 frontend against a `faciliti-manager` REST gateway (`http://localhost:3006/api/`) coordinating 8 specialist services: `device-manager`, `device-communicator`, `alarm-manager`, `notification-engine`, `reports-handler`, `schedule-handler`, `sensor-data-processor`, `health-monitor`.

**Roles** (§6, §7): ADMIN · MANAGER · STAFF · GUEST, with a documented capability matrix.

**Evidence caveat carried forward from the source itself** (§0 of that report): the IKANOS repository snapshot contains documentation, frontend package metadata and build artefacts — **no `src/`, no backend source, no ORM schema, no migrations**. Its entity tables are therefore documentation-derived, not DDL-derived. Where this audit cites a field, it cites the IKANOS documentation as written; it does not assert the production database matches.

### 0.2 IKANOS entity model used for the `Expected Data/Value` column

Taken verbatim from `COMPLETE_PROJECT_ANALYSIS_REPORT.md` §8.

**Core tables** (§8 "Core Tables"): `user` · `userRole` · `facility` · `amenity` · `package` · `booking` · `stay` · `occupant` · `employee` · `department` · `function` · `serviceRequest` · `foodCategory` · `foodMenu` · `event` · `offer` · `holiday` · `propertyType` · `invoice`

**Device tables:** `device` (id, name, type, deviceConfigStatus, amenityId, hubId, firmwareVersion, status, lastSeen, ipAddress, macAddress, facilityId) · `firmware` (id, version, deviceType, filePath, isLatest, facilityId) · `jobOrder` (id, amenityId, devices, jobType, assignedTo, status, facilityId)

**Alert tables:** `deviceIncident` (id, deviceId, subject, description, status, severity, createdOn, assignedTo, resolvedOn, notes, facilityId) · `valueAlerts` (id, deviceId, parameter, limitType, limitValue, currentValue, status, timestamp, unit, facilityId) · `limitConfig` (id, deviceId, parameter, highLimit, lowLimit, unit, facilityId) · `alertType` (id, name, description, severity, category, isActive) · `currentIncidentStatus` (id, name, statusCode, displayColor, isResolved)

**Notification tables:** `notification` (id, userId, title, message, type, referenceId, isRead, createdOn, facilityId) · `fcmToken` (id, userId, token, deviceType, registeredOn, facilityId)

**Schedule tables:** `maintenanceSchedule` (id, amenityId, serviceTypeId, departmentId, assignedTo, days, startTime, fromDate, toDate, isActive, facilityId) · `scheduledTask` (id, type, targetEntity, scheduledAt, status, lastExecuted, recurPattern, facilityId)

**Sensor & health tables:** `energyData` (id, deviceId, timestamp, energy, power, current, voltage, facilityId) · `sensorReading` (id, deviceId, timestamp, temperature, humidity, motion, lightLevel, facilityId) · `energyAggregate` (id, deviceId, roomId, interval, avgPower, maxPower, totalEnergy, timestamp, facilityId) · `deviceHealthLog` (id, deviceId, status, timestamp, responseTime, errorDetail, facilityId) · `deviceUptime` (id, deviceId, date, onlineMinutes, offlineMinutes, uptimePercent, facilityId)

### 0.3 A note on `WORKFLOW.md`

`ACX codes\ikanos-flow-main\…\WORKFLOW.md` was examined first and set aside — correctly, per your instruction. It documents the **React frontend architecture** (tech stack, folder layout, router config, theme/auth mechanics) and contains no business entities, fields, statuses or workflows. Verified by file comparison: `ikanos-flow-main` is this same React application before the features-based refactor — every hardcoded data array is byte-for-byte identical to ACX-Platform; only import paths, line endings and dark-mode styling differ. It is **not** the legacy IKANOS system. It is retained in this report only as independent corroboration of Section 1 (its own lines 170–179 state that no data fetching exists and that a backend/data layer still needs to be added).

---

## 1. Critical global finding — the application has zero data integration

This is the single most important finding, and it changes how every other row in this report should be read.

| Check | Result | Evidence |
|---|---|---|
| HTTP calls (`fetch` / `axios`) | **None anywhere in `src/`** | Repo-wide grep returns 0 matches |
| `useQuery` / `useMutation` | **None** | 0 matches |
| API base URL / env config | **None** | Only `import.meta.env.DEV` in [main.tsx:6](src/main.tsx#L6) |
| React Query | Installed, `QueryClientProvider` mounted, **never used** | [App.tsx:35-38](src/App.tsx#L35-L38) |
| Authentication | Hardcoded `ikanospro` / `ikanospro` | [AuthContext.tsx](src/core/contexts/AuthContext.tsx) |
| Data source for every page | Module-scoped hardcoded arrays | All 25 pages |
| Write operations (Submit/Update/Delete) | `console.log` or no-op, on **every** form in the app | All forms |

**Consequence:** every value displayed in the HMS frontend today is static. Where this report says "Current Display: 0%" or "Current Display: Alice konyak", both are equally hardcoded — one just looks more plausible than the other. Per audit rule §9, zero/empty values are *not* automatically errors; they are flagged for verification against IKANOS.

---

## 2. Route & page inventory

Every route registered in [App.tsx](src/App.tsx), plus every tab, sub-view and modal reachable from it.

| # | Module | Route | Page file | Tabs / sub-views | Modals |
|---|---|---|---|---|---|
| 1 | Login | `/login` | `auth/pages/Login.tsx` | — | — |
| 2 | Dashboard | `/dashboard` | `dashboard/pages/Dashboard.tsx` | — | — |
| 3 | Occupancy | `/occupancy` | `occupancy/pages/Occupancy.tsx` | Guest, Non Guest | Room Details |
| 4 | Bookings | `/bookings` | `bookings/pages/Bookings.tsx` | List, Add, Edit *(state, not routes)* | Bulk Upload, Check In, Extend Checkout |
| 5 | Services Tracking | `/services/tracking` | `services/pages/ServiceTracking.tsx` | 7 service-type views | Status Update (3 variants), Items |
| 6 | Services Planning | `/services/planning` | `services/pages/ServicePlanning.tsx` | Scheduled Services, Plan Maintenance, Disinfection Schedule | Edit Service Planning |
| 7 | Facility Management | `/config/facility` | `config/pages/FacilityManagement.tsx` | Facility Setup, Room Setup, Room Amenities, Packages | 4 edit modals |
| 8 | User Roles | `/config/user-roles` | `config/pages/UserRoles.tsx` | User Role, Web Modules | Edit User Role |
| 9 | Services Setup | `/config/services-setup` | `config/pages/ServicesSetup.tsx` | 7 service groups, ~30 service types | Edit Food Category / Food Menu / Service Menu |
| 10 | Employees | `/config/employees` | `config/pages/Employees.tsx` | Employee, Department, Function | 3 edit modals |
| 11 | Job Order | `/config/job-order` | `config/pages/JobOrder.tsx` | Create Job, Job Orders | — |
| 12 | Limit Config Alert | `/config/limit-alert` | `config/pages/LimitConfigAlert.tsx` | — | — |
| 13 | Offers | `/offers` | `marketing/pages/Offers.tsx` | — | Add Offer, Withdraw, Edit |
| 14 | Holidays | `/holidays` | `marketing/pages/Holidays.tsx` | — | Edit Holiday, Delete Confirm |
| 15 | Events | `/events` | `marketing/pages/Events.tsx` | — | Add Event, Edit Event, Cancel Event |
| 16 | Device Mgmt — Caleido Network | `/devices/caleido-network` | `devices/pages/DeviceManagement.tsx` | Add device, View Caleido Inventory, Network Alert Tracking, Maintenance Predictor (×4 device types) | Edit Device, Decommission, Edit Alert |
| 17 | Device Mgmt — Firmware | `/devices/firmware-management` | `devices/pages/FirmwareManagement.tsx` | Add Firmware, Firmware Update | Firmware Update, Firmware Delete |
| 18 | Reports | `/reports/*` | `reports/pages/Reports.tsx` | 9 report tabs; Energy has 3 main + 3 sub tabs | — |
| 19 | Tickets | `/tickets` | `tickets/pages/Tickets.tsx` | — | — |
| 20 | Power View | `/power-view` | `devices/pages/PowerView.tsx` | — | — |
| 21 | Energy View | `/energy-view` | `devices/pages/EnergyView.tsx` | — | — |
| 22 | Room View | `/room-view` | `occupancy/pages/RoomView.tsx` | — | — |
| 23 | Default Key Settings | `/key-settings` | `devices/pages/KeySettings.tsx` | — | — |
| 24 | Not Found | `*` | `common/pages/NotFound.tsx` | — | — |
| 25 | Placeholder | *(unrouted)* | `common/pages/Placeholder.tsx` | — | — |

**Totals audited:** 15 sidebar modules · 23 functional pages · 25 page files · 40 tabs/sub-views · 22 modals.

### 2.1 Routing observations

| Finding | Detail | Gap Type |
|---|---|---|
| `Placeholder.tsx` is imported but never routed | [App.tsx:23](src/App.tsx#L23) imports it; no `<Route>` uses it — dead code | Missing Workflow Representation |
| Bookings Add/Edit are not routes | `viewMode` state only — no deep link, no browser back, no bookmarkable edit URL | Missing Detail |
| `/reports/*` wildcard, tab state is local | Sidebar links to `/reports/occupancy`; navigating to `/reports/booking` still shows Occupancy tab | Missing Detail |
| No route for a single booking / room / ticket / device detail page | All detail views are modals with no URL | Missing Sub-module |

---

## 3. Cross-cutting defects (apply to many modules)

| # | Finding | Affected pages | Gap Type | Priority |
|---|---|---|---|---|
| X1 | No loading state anywhere | All 23 pages | Missing Workflow Representation | High |
| X2 | No error state anywhere | All 23 pages | Missing Workflow Representation | High |
| X3 | Real-empty vs not-loaded indistinguishable | All tables/panels | Placeholder | High |
| X4 | Every Submit/Update/Delete is `console.log` or no-op | All forms | Missing Workflow Representation | High |
| X5 | Pagination totals hardcoded, decoupled from data | Occupancy (40), Bookings (13), Svc Tracking (136), Svc Planning (136), Tickets (52), Network Alerts (1,908,789) | Static / Hardcoded Value | High |
| X6 | `entriesPerPage` select has no effect on rendered rows | Most tables | Missing Filter | Medium |
| X7 | Search box non-functional | Services Tracking, Services Planning | Missing Filter | Medium |
| X8 | Status vocabularies inconsistent across modules | Available/Unavailable · Occupied/Vacant/Maintenance · Perfect/Dirty/Maintenance · Commissioned/Decommissioned · Assigned/Pending/Completed/Cancelled/Partially Completed | Missing Status | High |
| X9 | Date formats inconsistent | `DD-MM-YYYY` in tables, `YYYY-MM-DD` in inputs, `2024-01-15` in Firmware table | Missing Detail | Low |
| X10 | No timezone, no "last updated", no live refresh | All pages | Missing Metric | Medium |
| X11 | Role permissions defined but never enforced | `UserRoles` Web Modules never read by `ProtectedRoute` or `AppSidebar` — all 15 modules visible to everyone | Missing Workflow Representation | High |
| X12 | Refresh buttons non-functional | Dashboard ×3 (Energy, Occupancy, Caleido At Work) | Missing Workflow Representation | Medium |
| X13 | Period selectors (Today/Week/Month) non-functional | Dashboard ×3 panels + Alerts panel | Missing Filter | High |
| X14 | Dark mode only implemented on 4 pages | Dark-aware: Dashboard, Room View, Occupancy, Energy View. Hardcoded light: Bookings, Tickets, both Services, Offers, Holidays, Events, Device Mgmt, Firmware, Power View, all 6 Config pages | Missing Detail | Low |
| X15 | Edit modals hardcoded to one record, ignore the clicked row | Offers, Holidays, Events, Device Mgmt, Firmware, Services Planning, User Roles | Static / Hardcoded Value | High |
| X16 | No global search, no notifications deep-link, no breadcrumbs | `AppHeader` left region is an empty div | Missing Detail | Low |

---

## 4. Module-by-module analysis

Each module follows the required A–F structure.

---

### 4.1 DASHBOARD — `/dashboard`

**A. Pages available:** Dashboard (single page).

**B. Sections available:**
1. Page header
2. Average Energy Consumption (chart)
3. Occupancy Statistics (donut)
4. Caleido At Work (4 circular KPIs)
5. Alerts panel
6. Status header (health legend + Affected Rooms + Select All)
7. Building cards
8. Floor cards *(conditional)*
9. Occupancy / Room cards *(conditional)*
10. Room Details panel *(conditional)* — Occupancy Details, Booking Details
11. Device Details — IntelliHub, AirQ, Mikos, Kleio cards

**C. Current data:** All hardcoded in [Dashboard.tsx:11-31](src/features/dashboard/pages/Dashboard.tsx#L11-L31) and each component file. 4 buildings, 6 floors (only for buildings 1 and 2), 3 rooms total.

**D/E/F — Gap table**

| # | Section | Component | Current Display | Missing Data/Value | Expected | IKANOS Ref | Gap Type | Pri |
|---|---|---|---|---|---|---|---|---|
| D1 | Page header | Title | "Dashboard" + static welcome text | Facility context | `facility.name` + business date | §8 Core Tables `facility` | Missing Detail | Low |
| D2 | Page header | Date range | *absent* | Global date-range filter | `createdOn.gte` / `createdOn.lte` date-range params | §9 "Date range: `createdOn.gte`, `createdOn.lte`, `startDate`, `endDate`" | Missing Filter | High |
| D3 | Energy chart | Bar data | Mon 0.2/0.3 … Sun 0.3/0.4 | Real per-day energy | `energyAggregate.totalEnergy` / `avgPower` per interval | §8 Sensor Tables `energyAggregate`; §10 Dashboard row | Static/Hardcoded | High |
| D4 | Energy chart | Y-axis unit | Bare numbers 0–1.0 | Unit label | Unit from `valueAlerts.unit` / energy schema (kWh, kW) | §8 `energyData` (energy, power); §8 `valueAlerts.unit` | Missing Field | Medium |
| D5 | Energy chart | Period select | Today/Week/Month, no `onChange` | Working period filter | `energyAggregate.interval` selection | §8 `energyAggregate` (interval) | Missing Filter | High |
| D6 | Energy chart | Refresh | No handler | Refresh action | Re-query energy stats APIs | §10 "Open Dashboard → energy stats APIs" | Missing Workflow | Medium |
| D7 | Energy chart | Summary | *absent* | Aggregate metrics | `avgPower`, `maxPower`, `totalEnergy` | §8 `energyAggregate` | Missing Metric | Medium |
| D8 | Occupancy donut | Values | 94% / 6% hardcoded | Real occupancy split | Derived from `stay.status` over `amenity` inventory | §8 `stay`, `amenity`; §10 Dashboard data tables `booking`, `stay` | Static/Hardcoded | High |
| D9 | Occupancy donut | Counts | Percent only | Occupied / vacant room counts | Count of `amenity` by `amenity.status` | §8 `amenity` (id, name, type, floor, packageId, status) | Missing Count | High |
| D10 | Occupancy donut | Contradiction | Dashboard 94/6 vs Room View 17/83 vs Room View cards 2-of-10 | Single reconciled source | One `amenity.status` / `stay.status` query serving all views | §8 `amenity`, `stay` | Missing Value | High |
| D11 | Occupancy donut | Period select / refresh | No handlers | Working controls | Date-range params on occupancy query | §9 Common query patterns | Missing Filter | Medium |
| D12 | Caleido At Work | Smart Rooms Online | **`0%`** | Smart-room online count + total + % | `deviceUptime.uptimePercent` / online vs offline device count per room | §8 `deviceUptime` (onlineMinutes, offlineMinutes, uptimePercent); §10 System Health row | Static/Hardcoded | High |
| D13 | Caleido At Work | Service Request Status | **`-`** | Service request counts by status | `serviceRequest.status` grouped counts | §8 `serviceRequest` (id, serviceType/requestType, roomId, assignedTo, status) | Missing Value | High |
| D14 | Caleido At Work | Rooms For Check-Out | **`-`** | Rooms scheduled for checkout | `stay` records with checkout due; `scheduledTask` type=checkout | §6 Booking and Stay Flow step 7; §7-doc `scheduledTask`; §20 Booking Workflow | Missing Value | High |
| D15 | Caleido At Work | Pending Bookings | **`-`** | Pending booking count | Count of `booking` not yet converted to `stay` | §8 `booking`, `stay`; §20 Booking Workflow | Missing Value | High |
| D16 | Caleido At Work | All 4 rings | `value={0}` → ring never fills | Real percentage driving the arc | Computed ratio per KPI | §10 "Dashboard cards, charts, alerts" | Static/Hardcoded | High |
| D17 | Caleido At Work | Drill-down | Cards not clickable | Navigate to filtered list | Link to Bookings / Service Requests filtered by status | §10 Sidebar item→API flow table | Missing Workflow | Medium |
| D18 | Caleido At Work | Period select / refresh | No handlers | Working controls | Date-range params | §9 Common query patterns | Missing Filter | High |
| D19 | Alerts | Body | **"No alerts found"** — always, unconditionally | Alert records | `GET /incidents` + `GET /getvalueAlerts` result set | §10 "Open Dashboard → `GET /system-health`, `GET /incidents`, `GET /getvalueAlerts`" | Placeholder | High |
| D20 | Alerts | Alert count | *absent* | Total / unread alert count | Count of `deviceIncident` + `valueAlerts` by status | §8 Alert Tables; §20 Alert Lifecycle | Missing Count | High |
| D21 | Alerts | Severity | *absent* | Severity per alert | `deviceIncident.severity`; `alertType.severity` (Critical/Warning) | §8 `deviceIncident`, `alertType` (id, name, description, severity, category, isActive) | Missing Field | High |
| D22 | Alerts | Message | *absent* | Alert text | `deviceIncident.subject` + `deviceIncident.description` | §8 `deviceIncident` | Missing Field | High |
| D23 | Alerts | Affected room | *absent* | Room number | `device.amenityId` → `amenity.name` | §8 `device` (amenityId), `amenity` | Missing Field | High |
| D24 | Alerts | Timestamp | *absent* | Date & time raised | `deviceIncident.createdOn`; `valueAlerts.timestamp` | §8 `deviceIncident`, `valueAlerts` | Missing Field | High |
| D25 | Alerts | Device | *absent* | Device that raised it | `deviceIncident.deviceId` → `device.name` | §8 `deviceIncident`, `device` | Missing Field | High |
| D26 | Alerts | Status / assignee | *absent* | Lifecycle state + owner | `deviceIncident.status`, `.assignedTo`, `.resolvedOn`, `.notes`; `currentIncidentStatus` (statusCode, displayColor, isResolved) | §8 Alert Tables; §6 Alert Resolution Flow | Missing Status | High |
| D27 | Alerts | Service \| Caleido tabs | Static text, no handler | Working alert-source filter | Filter by alert source: `serviceRequest` vs `deviceIncident`/`valueAlerts`; module permission IDs `SERVICE_TRACKING` and `CALEIDO_NETWORK`/`device-alerts` | §10 "Important module permission IDs documented" | Missing Filter | High |
| D28 | Alerts | List icon | No handler | View-all alert list | Full Alerts module | §10 Sidebar "Alerts" row | Missing Workflow | Medium |
| D29 | Status header | Good Health \| Warnings \| Error | Coloured labels, **no counts** | Count per health state | `deviceHealthLog.status` grouped counts | §8 `deviceHealthLog`; §20 Health Monitoring Workflow | Missing Count | High |
| D30 | Status header | Same legend | Not clickable | Filter grid by health state | `status` filter param | §9 "Status filtering: `status`, `status.nte`" | Missing Filter | High |
| D31 | Status header | Affected Rooms checkbox | No handler | Filter to affected rooms | Rooms having open `deviceIncident` / `valueAlerts` | §8 Alert Tables; §20 Alert Lifecycle | Missing Filter | High |
| D32 | Status header | "Select All" dropdown | Single option, no handler | Scope selector | Facility → building → floor → room hierarchy | §10 "Facility Setup: facility, buildings, floors, room/amenity types" | Missing Filter | Medium |
| D33 | Buildings | Card data | Building A 5/36, Demo Box 4/5, Dev & Testing 3/28, Building D PILOT 2/5 | Real building master | `propertyType` (id, name, facilityId) + `amenity` counts | §8 Core Tables `propertyType`, `amenity`; §10 Facility Setup row | Static/Hardcoded | High |
| D34 | Buildings | Health status | Legend shown, **no per-building health value** | Health state per building | Aggregated `deviceHealthLog.status` by building | §8 `deviceHealthLog`; §10 System Health row | Missing Status | High |
| D35 | Buildings | Occupancy | *absent* | Occupied/vacant per building | `amenity.status` counts scoped to building | §8 `amenity` | Missing Count | Medium |
| D36 | Floors | Data coverage | Only buildings 1 & 2 have floors; buildings 3 & 4 click → nothing renders | Floors for every building | `amenity.floor` across full facility structure | §8 `amenity` (floor); §10 "Facility Setup defines the hotel/premise structure" | Missing Data | High |
| D37 | Floors | Health status | Legend shown, no data | Health per floor | Aggregated `deviceHealthLog.status` by floor | §8 `deviceHealthLog` | Missing Status | High |
| D38 | Floors | Room count | *absent* | Rooms per floor | Count of `amenity` per `amenity.floor` | §8 `amenity` | Missing Count | Medium |
| D39 | Rooms | Data coverage | 3 rooms total (2 on floor f2, 1 on f1); all other floors click → nothing | Full room list per floor | Complete `amenity` inventory | §8 `amenity`; §10 Rooms/Amenities row | Missing Data | High |
| D40 | Rooms | Status derivation | `isError` inferred from `room.type` string containing "Error"/"Maintenance" — **no status field exists** | Explicit status field | `amenity.status` | §8 `amenity` (id, name, type, floor, packageId, **status**) | Missing Status | High |
| D41 | Rooms | Card fields | Number + type only | Room operational summary | `amenity.status`, occupancy from `stay`, device health from `deviceHealthLog` | §8 `amenity`, `stay`, `deviceHealthLog`; §10 Rooms/Amenities row | Missing Field | High |
| D42 | Room Details | Occupancy Type | **"Golden Package"** hardcoded for every room | Actual package | `package.name` via `amenity.packageId` | §8 `package` (id, name, price, amenityType), `amenity` (packageId) | Static/Hardcoded | High |
| D43 | Room Details | Status | **"Occupied"** hardcoded | Actual room status | `amenity.status` / `stay.status` | §8 `amenity`, `stay` (id, bookingId, amenityId, status) | Static/Hardcoded | High |
| D44 | Room Details | Guest Name | **"Siva Subramanian N"** hardcoded | Actual guest | `occupant.firstName` via `booking` → `stay` | §8 `occupant` (id, bookingId, firstName, phoneNumber) | Static/Hardcoded | High |
| D45 | Room Details | Booking Date | **"27-12-2025 16:10"** hardcoded | Actual booking date | `booking.checkinDate` | §8 `booking` (id, firstName, checkinDate, packageId) | Static/Hardcoded | High |
| D46 | Room Details | Additional Guest | **"0"** hardcoded | Actual additional occupants | Count of `occupant` rows for the booking | §8 `occupant`; §6 "Occupants are added to booking" | Static/Hardcoded | Medium |
| D47 | Room Details | Actual Check In | **"27-12-2025 16:22"** hardcoded | Actual check-in | `stay` activation timestamp | §6 Booking and Stay Flow step 4; §20 "check-in creates stay" | Static/Hardcoded | High |
| D48 | Room Details | Expected Check Out | **"27-12-2026 13:00"** hardcoded | Actual expected checkout | `stay` checkout schedule; `scheduledTask` checkout job | §6 step 7; §7-doc `scheduledTask` (checkout, stay expiry) | Static/Hardcoded | High |
| D49 | Room Details | Missing booking fields | — | Full booking/occupant detail | `occupant.phoneNumber`, `booking.packageId`, `invoice` (id, stayId, amount, status) | §8 `occupant`, `booking`, `invoice` | Missing Field | High |
| D50 | Room Details | Re-Allocate button | No handler | Re-allocation workflow | Room reallocation on active `stay` | §6 Booking and Stay Flow step 6 "Stay can be extended or room can be reallocated"; §1 Core Features "room reallocation" | Missing Workflow | High |
| D51 | Device Details | IntelliHub telemetry | Room Power ON, Temp 66.0 °C, V 260.0, I 0.35 A, F 50.1 Hz, PF 1.00, P 0.370 KW, E 37.140 kWh, Relay Ops 434 — all hardcoded | Live telemetry | `energyData` (energy, power, current, voltage) + `sensorReading` (temperature) | §8 `energyData`, `sensorReading`; §20 Sensor Data Workflow | Static/Hardcoded | High |
| D52 | Device Details | AirQ telemetry | Room Temp **0.0 °C**, Humidity 29.8 %RH, Pressure 999.6 hPa, IAQ 104, Temp 34.5 °C — Room Temp 0.0 contradicts Temp 34.5 | Live telemetry | `sensorReading` (temperature, humidity, motion, lightLevel) | §8 `sensorReading`; §20 Sensor Data Workflow inputs | Static/Hardcoded | High |
| D53 | Device Details | Mikos telemetry | V 258.0, I 0.00 A, F **47.2 Hz**, PF 1.00, P 0.070 KW, E 4.960 kWh, T 59.5 °C — 47.2 Hz out of nominal with no warning | Live telemetry + threshold check | `energyData` + `limitConfig` (highLimit, lowLimit, unit) → `valueAlerts` | §8 `energyData`, `limitConfig`, `valueAlerts`; §20 Sensor Data Workflow | Static/Hardcoded | High |
| D54 | Device Details | Kleio telemetry | Battery 100 %, Temp 31.5 °C, Lock Status CLOSE | Live telemetry + lock state | `sensorReading` + lock command state via `device-communicator` | §8 `sensorReading`; §3-doc Device Communicator (lock commands) | Static/Hardcoded | High |
| D55 | Device Details | Device online/offline | *absent* | Connectivity state | `device.status` + `device.lastSeen` | §8 `device` (status, lastSeen) | Missing Status | High |
| D56 | Device Details | Last communication | *absent* | Last-seen timestamp | `device.lastSeen`; `deviceHealthLog.timestamp` | §8 `device`, `deviceHealthLog` | Missing Field | High |
| D57 | Device Details | Device health | *absent* | Health indicator | `deviceHealthLog.status`, `.responseTime`, `.errorDetail` | §8 `deviceHealthLog`; §20 Health Monitoring Workflow | Missing Status | High |
| D58 | Device Details | Threshold breach | 66.0 °C, 47.2 Hz shown as plain values | Limit-breach highlighting | `valueAlerts` (parameter, limitType, limitValue, currentValue, unit) driven by `limitConfig` | §8 `valueAlerts`, `limitConfig`; §20 Sensor Data Workflow "check thresholds" | Missing Status | High |
| D59 | Device Details | AirQ IAQ legend | GOOD / MODERATE / VERY UNHEALTHY / HAZARDOUS — **"UNHEALTHY" band missing**, no numeric ranges | Complete banded scale | Thresholds from `limitConfig` (highLimit, lowLimit) | §8 `limitConfig` | Missing Field | Medium |
| D60 | Device Details | Settings gear (AirQ, Mikos) | No handler | Device configuration | Device config via `device-manager`; `device.deviceConfigStatus` | §8 `device` (deviceConfigStatus); §2-doc Device Manager | Missing Workflow | Medium |
| D61 | Device Details | Device naming | Derived as `{roomNumber}HUB01` etc. — always `01`, never a real tag | Actual device identity | `device.name`, `device.macAddress`, `device.ipAddress`, `device.hubId`, `device.firmwareVersion` | §8 `device` | Missing Field | High |

**Dashboard total: 61 gaps** (High 45 · Medium 14 · Low 2)

---

### 4.2 GLOBAL HEADER — `AppHeader` (appears on every page)

| # | Section | Component | Current Display | Missing Data/Value | Expected | IKANOS Ref | Gap Type | Pri |
|---|---|---|---|---|---|---|---|---|
| H1 | Notifications | List | 5 hardcoded items (Room 301 check-in, MIKOS firmware, Zone B energy, ticket #1234, Conference Room A) | Real notification feed | `notification` records (title, message, type, referenceId, createdOn) | §8 Notification Tables `notification`; §10 Sidebar "Notifications" row | Static/Hardcoded | High |
| H2 | Notifications | Badge count | Derived from the 5 mocks | Real unread count | Count where `notification.isRead = false` | §8 `notification` (isRead) | Missing Count | High |
| H3 | Notifications | `type` field | Stored (`info/warning/success/error`) but **never rendered** | Type/severity indicator | `notification.type` | §8 `notification` (type) | Missing Field | Medium |
| H4 | Notifications | Click action | Item click does nothing | Deep-link to related record | Navigate via `notification.referenceId` | §8 `notification` (referenceId); §20 Notification Workflow inputs | Missing Workflow | Medium |
| H5 | Notifications | Timestamp | Pre-baked strings ("2 minutes ago") | Real timestamp | `notification.createdOn` | §8 `notification` (createdOn) | Static/Hardcoded | Medium |
| H6 | Notifications | Mark read/unread/clear | Local state only, lost on reload | Persisted state | `PUT /api/facility/{ID}/notifications/{NOTIF_ID}/status` updating `notification.isRead` | §10 Sidebar item→API flow "Mark Notification Read" | Missing Workflow | Medium |
| H7 | Notifications | **Push notifications** | *absent entirely* | Browser push via FCM | FCM token registered on login, deleted on logout; `fcmToken` (token, deviceType, registeredOn) | §6 Login Flow step 5; §6 Logout Flow step 2; §8 `fcmToken`; §20 Notification Workflow | Missing Sub-module | High |
| H8 | Notifications | SMS / email channels | *absent entirely* | Multi-channel delivery | SMS and email dispatch alongside push/in-app | §1 Core Features "FCM push notifications, in-app notifications, SMS, and email"; §20 Notification Workflow outputs | Missing Sub-module | Medium |
| H9 | User menu | Profile | Menu item with no handler | Profile page | `user` (id, email, userRoles, facilityId) | §8 Core Tables `user` | Missing Sub-module | Medium |
| H10 | User menu | Identity | Generic person icon | Logged-in user identity | `LOGGED_IN_USER` — user ID, userRoles, facility | §6 Login Flow steps 3–4; §7 Authorization Flow | Missing Field | Medium |
| H11 | User menu | Logout | Clears `localStorage` only | Full logout sequence | `POST /api/logout` → delete FCM token → clear `localStorage` → redirect | §6 Logout Flow steps 1–4 | Missing Workflow | High |
| H12 | Header | Left region | Empty `<div>` with comment "Search could go here" | Global search | Not specified in IKANOS docs | — (no IKANOS requirement found) | Missing Detail | Low |
| H13 | Header | Facility context | *absent* | Current facility | `facility` scope from `LOGGED_IN_USER`; all APIs are `/api/facility/{ID}/...` | §9 "APIs ... use `/api/facility/{ID}/...` paths"; §6 Login Flow step 3 | Missing Field | High |

**Header total: 13 gaps** (High 5 · Medium 7 · Low 1)

---

### 4.3 AUTH & AUTHORIZATION — `/login`, `ProtectedRoute`, `AppSidebar`

| # | Component | Current Display | Missing Data/Value | Expected | IKANOS Ref | Gap Type | Pri |
|---|---|---|---|---|---|---|---|
| A1 | Credentials | Hardcoded `ikanospro`/`ikanospro` in client source | Server-side authentication | `POST /api/login` with `{ username, password }`, validated server-side | §6 Login Flow steps 1–2; §7 Authentication Flow | Missing Workflow | High |
| A2 | Session token | `localStorage` stores `{username}` only | Bearer token | Token returned by login, sent as `Authorization: Bearer {token}` on every request | §6 Login Flow steps 3, 6; §7 Authentication Flow | Missing Field | High |
| A3 | Session shape | `{ username }` | Full session payload | `LOGGED_IN_USER` = user ID + userRoles + facility + token | §6 Login Flow steps 3–4 | Missing Field | High |
| A4 | Role | Not captured at login | User role | `user.userRoles` → `userRole` (id, name, roleType, permissions) | §8 Core Tables `user`, `userRole`; §7 Authorization Flow | Missing Field | High |
| A5 | Facility scope | *absent* | Facility the user is scoped to | `user.facilityId`; all APIs are `/api/facility/{ID}/...` | §8 `user` (facilityId); §9 API path pattern | Missing Field | High |
| A6 | Session expiry | None — `localStorage` persists indefinitely | Expiry handling | HTTP 401 on invalid/expired token → redirect to login | §7 "Invalid/expired token leads to HTTP 401 and login redirect"; §7 Security Controls "Session expiration handling" | Missing Workflow | High |
| A7 | FCM registration | *absent* | Push token registration at login | Register FCM token if browser notification permission granted | §6 Login Flow step 5 | Missing Workflow | Medium |
| A8 | **Role-based sidebar** | All 15 modules shown to every user | Permission-driven navigation | Sidebar modules shown/hidden per `userRoles` and module permissions | §10 "Sidebar modules are shown or hidden according to `userRoles` and module permissions"; §10 Sidebar Permissions Behavior | Missing Workflow | High |
| A9 | Role model | No roles exist in the app at all | 4 documented roles | ADMIN · MANAGER · STAFF · GUEST, with capability matrix (Facility setup, Rooms/packages, Bookings/stays, Alerts, Reports, Roles/permissions, Device management) | §6 Roles and Access Levels; §7 Permission Model table | Missing Module | High |
| A10 | Module permission IDs | *absent* | Named permission gates | `CALEIDO_NETWORK` / `device-alerts` (device alert visibility + assignment), `SERVICE_TRACKING` (service request visibility) | §10 "Important module permission IDs documented" | Missing Field | High |
| A11 | Staff scoping | *absent* | Assigned-only filtering | Staff alert APIs add `assignedTo={STAFF_ID}` | §7 Authorization Flow; §9 "Staff filtering: `assignedTo={STAFF_ID}`" | Missing Filter | High |
| A12 | Guest scoping | *absent* | Room-scoped filtering | Guest service request APIs filter by `roomId={GUEST_ROOM}` | §7 Authorization Flow; §9 "Guest filtering: `roomId={GUEST_ROOM}`" | Missing Filter | Medium |
| A13 | GUEST portal | *absent entirely* | Guest-facing flows | Guest service request and room/stay interactions | §6 Roles "GUEST: room/service request interactions"; §10 Sidebar Permissions "GUEST sees only guest-scoped service request and room/stay interactions if a guest portal is enabled" | Missing Module | Medium |

**Auth & Authorization total: 13 gaps** (High 10 · Medium 3)

---

### 4.4 OCCUPANCY — `/occupancy`

**A. Pages available:** Occupancy Management (single page, 2 tabs) + Room Details modal.

**B. Sections available:** Page header · Guest/Non-Guest tabs · Table controls (Show entries, Filter By, Search) · Data table (9 columns) · Pagination · Room Details modal (Room Details, Occupants Details, Device Details, Maintenance Details).

**C. Current data:** 10 guest rooms + 10 non-guest rooms hardcoded at [Occupancy.tsx:32-56](src/features/occupancy/pages/Occupancy.tsx#L32-L56). Modal data hardcoded at [RoomDetailsModal.tsx:29-155](src/features/occupancy/components/RoomDetailsModal.tsx#L29-L155).

| # | Section | Component | Current Display | Missing Data/Value | Expected | IKANOS Ref | Gap Type | Pri |
|---|---|---|---|---|---|---|---|---|
| O1 | Page | Occupancy KPIs | *absent* | Occupancy %, occupied/vacant/available counts on the page itself | Occupancy KPIs from amenity/stay counts | §8 `amenity`, `stay`; §10 Rooms/Amenities row | Missing Count | High |
| O2 | Table | Row data | 10+10 hardcoded rows | Real room inventory | `amenity` inventory for the facility | §8 Core Tables `amenity` | Static/Hardcoded | High |
| O3 | Pagination | Total | "of **40** entries" but only 10 rows exist | Real total | Real total from paginated query | §9 "Pagination: `limit`, likely offset/page" | Static/Hardcoded | High |
| O4 | Pagination | Page buttons | Fixed `[1,2,3,4]` | Derived page count | Derived page count | §9 Pagination | Static/Hardcoded | Medium |
| O5 | Table | Building / Floor columns | *absent* | Building and floor per room | `amenity.floor` + `propertyType` (building) | §8 `amenity` (floor), `propertyType` | Missing Field | High |
| O6 | Table | Check-in / Check-out dates | *absent* | Arrival and departure per occupied room | `booking.checkinDate`; `stay` checkout schedule | §8 `booking`, `stay`; §6 Booking and Stay Flow | Missing Field | High |
| O7 | Table | Booking reference | *absent* | Booking ID linking room ↔ booking | `stay.bookingId` → `booking.id` | §8 `stay` (id, bookingId, amenityId, status) | Missing Field | High |
| O8 | Table | Occupant count | *absent* | Pax per room | Count of `occupant` rows for the booking | §8 `occupant` | Missing Count | Medium |
| O9 | Table | Guest name (non-guest tab) | `-` for all 10 rows | N/A or purpose-specific label | N/A for non-bookable amenities | §8 `amenity` (type) | Placeholder | Low |
| O10 | Table | "Generate" column | Button, **no handler**, no label meaning | Purpose (key generation?) + generated artefact | Room key generation on stay | §10 "Generate Key → `POST /api/facility/{ID}/stays/{STAY_ID}/generate-key" → `device-communicator` lock command; §6 Booking and Stay Flow step 5 | Missing Workflow | High |
| O11 | Table | "Invoice" column | Button, **no handler** | Invoice number, amount, status, document | `invoice` (id, stayId, amount, status) + download | §8 Core Tables `invoice`; §6 Booking and Stay Flow step 8; §9 "File downloads for invoice" | Missing Workflow | High |
| O12 | Table | "Reallocate" column | Button, **no handler** | Re-allocation flow + target-room picker + reason | Room reallocation on active `stay` | §6 Booking and Stay Flow step 6; §1 Core Features "room reallocation" | Missing Workflow | High |
| O13 | Table | Status vocabulary | Only `Available` / `Unavailable` | Reconcile with Occupied/Vacant (Dashboard) and Perfect/Dirty/Maintenance (Room View) | `amenity.status` as the single status vocabulary | §8 `amenity` (status), `stay` (status) | Missing Status | High |
| O14 | Controls | Filter By | Only Show All / Available / Unavailable | Filter by room type, floor, building, condition, VIP, package | Filter by status, room type, floor, package | §9 "Status filtering: `status`, `status.nte`"; §8 `amenity` (type, floor, packageId) | Missing Filter | High |
| O15 | Controls | Date filter | *absent* | As-of-date / date-range | Date-range params | §9 "Date range: `createdOn.gte`, `createdOn.lte`" | Missing Filter | Medium |
| O16 | Controls | Show entries | Select present, **no effect** on rows rendered | Working page size | `limit` query param | §9 Pagination | Missing Filter | Medium |
| O17 | Conditions | Badge set | Occupied, VIP, Late checkout, Under maintenance, Sanitation, Low Battery | Full condition master + whether list is exhaustive | Amenity condition/status master | §8 `amenity` (status); §10 Rooms/Amenities row | Missing Field | Medium |
| O18 | Conditions | Empty state | `-` badge when no conditions | Confirm `-` is correct vs "Clean/Ready" | Explicit no-condition state | §8 `amenity` (status) | Placeholder | Low |
| O19 | Modal | Floor | **"Building A - Floor 1"** hardcoded for every room | Actual building/floor | `amenity.floor` + `propertyType.name` | §8 `amenity`, `propertyType` | Static/Hardcoded | High |
| O20 | Modal | Checkin Date | **"12-Oct-2023"** hardcoded (only when status = Unavailable) | Actual check-in | `booking.checkinDate` / `stay` activation | §8 `booking`, `stay`; §20 Booking Workflow | Static/Hardcoded | High |
| O21 | Modal | Checkout Date | **"15-Oct-2023"** hardcoded | Actual check-out | `stay` checkout date | §6 Booking and Stay Flow step 7 | Static/Hardcoded | High |
| O22 | Modal | Contact | **"+1 (555) 123-4567"** hardcoded | Actual guest phone | `occupant.phoneNumber` | §8 `occupant` (id, bookingId, firstName, phoneNumber) | Static/Hardcoded | High |
| O23 | Modal | Email | Derived from guest name → `john.smith@example.com` | Actual email | `user.email` / occupant contact | §8 `user` (email), `occupant` | Static/Hardcoded | High |
| O24 | Modal | ID Proof | **"Passport (Active)"** hardcoded | Actual document type, number, verification status, scan | Guest ID document per booking | §20 Booking Workflow inputs "guest data" | Static/Hardcoded | High |
| O25 | Modal | Nationality | **"United States"** hardcoded | Actual nationality | Guest nationality | §20 Booking Workflow inputs "guest data" | Static/Hardcoded | Medium |
| O26 | Modal | Pax | **"2 Adults, 1 Child"** hardcoded | Actual occupant breakdown | Count and detail of `occupant` rows | §8 `occupant`; §6 "Occupants are added to booking" | Static/Hardcoded | Medium |
| O27 | Modal | Additional occupants | Single guest block only | List of all occupants | All `occupant` rows for the booking | §8 `occupant`; §10 Guests/Occupants row | Missing Detail | Medium |
| O28 | Modal | Booking fields | *absent* | Booking ref, package/sub-package, rate, payment status, source | `booking.packageId` → `package`; `invoice` | §8 `booking`, `package`, `invoice` | Missing Field | High |
| O29 | Modal | Device Details rows | 7 rows, **all room 106 devices**, shown regardless of selected room | Devices for the selected room | `device` rows where `device.amenityId` = selected room | §8 `device` (amenityId) | Static/Hardcoded | High |
| O30 | Modal | Device status | 5 of 7 `Decommissioned` + error health; 2 `Commissioned` | Real status/health | `device.status`, `device.deviceConfigStatus`, `deviceHealthLog.status` | §8 `device`, `deviceHealthLog` | Static/Hardcoded | High |
| O31 | Modal | Device MAC | Blank for the 2 Commissioned rows → `-` | MAC for every device | `device.macAddress` | §8 `device` (macAddress) | Missing Field | Medium |
| O32 | Modal | Device fields | Type, Name/Tag, MAC, Status, Health, Added On | Firmware version, last communication, battery, connectivity | `device.firmwareVersion`, `.lastSeen`, `.ipAddress`, `.hubId` | §8 `device` | Missing Field | High |
| O33 | Modal | Maintenance rows | 6 hardcoded 2023 rows regardless of room | Maintenance history for the selected room | `maintenanceSchedule` + `serviceRequest` for the amenity | §8 `maintenanceSchedule` (amenityId), `serviceRequest` (roomId) | Static/Hardcoded | High |
| O34 | Modal | Maintenance status | All `Completed` | Full status range incl. scheduled/in-progress | `serviceRequest.status` full range | §8 `serviceRequest` (status); §10 Maintenance row | Missing Status | Medium |
| O35 | Modal | Emp name truncation | `"Queen Evang..."` stored truncated **in the data** | Full employee name | `employee` full name | §8 Core Tables `employee` | Missing Value | Low |
| O36 | Modal | Tables | No pagination, sort or filter in either modal table | Paging/filtering for long histories | `limit` + date-range params | §9 Common query patterns | Missing Filter | Low |
| O37 | Modal | Room energy | *absent* | Current/period energy for the room | `energyAggregate` (roomId, totalEnergy, avgPower, maxPower) | §8 `energyAggregate` (deviceId, roomId, interval, avgPower, maxPower, totalEnergy) | Missing Metric | Medium |
| O38 | Modal | Room alerts | *absent* | Active alerts for the room | Open `deviceIncident` / `valueAlerts` for the room | §8 Alert Tables; §20 Alert Lifecycle Workflow | Missing Data | High |

**Occupancy total: 38 gaps** (High 22 · Medium 11 · Low 5)

---

### 4.5 BOOKINGS — `/bookings`

**A. Pages available:** Booking Management list · Add New Booking · Edit Booking (all three are `viewMode` states, not routes).

**B. Sections available:** Header + Add/Bulk-Upload actions · Table controls · Data table (12 columns) · Pagination · Bulk Upload modal · Check In modal · Extend Checkout modal · Booking form (11 rows / 17 fields).

**C. Current data:** 10 bookings hardcoded at [Bookings.tsx:61-202](src/features/bookings/pages/Bookings.tsx#L61-L202).

| # | Section | Component | Current Display | Missing Data/Value | Expected | IKANOS Ref | Gap Type | Pri |
|---|---|---|---|---|---|---|---|---|
| B1 | Table | Row data | 10 hardcoded bookings | Real bookings | `booking` records for the facility | §8 Core Tables `booking` | Static/Hardcoded | High |
| B2 | Pagination | Total | "of **13** entries" vs 10 rows | Real total | Real total from paginated query | §9 "Pagination: `limit`" | Static/Hardcoded | High |
| B3 | Table | **Booking status** | *absent — no status column at all* | Pending / Confirmed / Cancelled / Checked-in / Checked-out / No-show | `stay.status` + booking lifecycle state | §8 `stay` (status); §6 Booking and Stay Flow; §20 Booking Workflow | Missing Status | High |
| B4 | Table | Booking ID / reference | *absent* (form has "Booking Reference" but table does not show it) | Booking ID column | `booking.id` | §8 `booking` (id) | Missing Field | High |
| B5 | Table | Check-out date | *absent* — only Check In (a button) and Booking Date | Expected/actual check-out | `stay` checkout date | §6 Booking and Stay Flow step 7 | Missing Field | High |
| B6 | Table | Duration / nights | *absent* | Nights or stay length | Derived from `booking.checkinDate` → checkout | §8 `booking`, `stay` | Missing Metric | Medium |
| B7 | Table | Booking source / channel | *absent* | Direct / OTA / corporate / walk-in | Booking origin (manual create vs bulk CSV upload) | §20 Booking Workflow trigger "admin/manager creates booking or uploads bulk CSV" | Missing Field | High |
| B8 | Table | Payment status & amount | *absent* | Amount, paid/pending, method | `invoice` (amount, status) | §8 Core Tables `invoice` (id, stayId, amount, status) | Missing Field | High |
| B9 | Table | Room No | Empty for 9 of 10 rows → `-` | Allocated room, or explicit "Unallocated" state | `stay.amenityId` → `amenity.name`, or explicit unallocated state | §8 `stay` (amenityId), `amenity`; §6 step 4 "Check-in creates/activates a stay and assigns room/amenity" | Placeholder | High |
| B10 | Table | Email | Empty for 2 of 10 rows → `-` | Confirm optional vs missing | `user.email` / occupant contact | §8 `user` (email) | Placeholder | Low |
| B11 | Table | Check In column | Icon button only — **no check-in state shown** | Checked-in yes/no + timestamp | `stay` existence/activation state | §6 step 4; §20 "check-in creates stay" | Missing Status | High |
| B12 | Table | Extend Checkout column | Icon button only; `extendCheckOut` is `false` for all 10 rows and **never rendered** | Extension status + new date | Stay extension state | §6 step 6 "Stay can be extended" | Missing Status | Medium |
| B13 | Table | Documents Approval | Renders a green check for **every** row; `false` branch exists but no row uses it | Real approval state + document list/preview | Guest ID document approval state | §20 Booking Workflow inputs "guest data" | Static/Hardcoded | High |
| B14 | Table | Sort | Headers not sortable | Sort by date, name, status | Sort on booking fields | §9 Common query patterns | Missing Filter | Low |
| B15 | Controls | Filters | Free-text search only | Status filter, date-range filter, room-type filter, source filter | Status, date-range and package filters | §9 "Status filtering: `status`, `status.nte`"; "Date range: `startDate`, `endDate`" | Missing Filter | High |
| B16 | Controls | Show entries | No effect on rendered rows | Working page size | `limit` query param | §9 Pagination | Missing Filter | Medium |
| B17 | Actions | Edit | Opens form; **Update only `console.log`** | Persisted update | Persisted update via booking API | §10 "Create Booking → `POST /api/facility/{ID}/bookings`" | Missing Workflow | High |
| B18 | Actions | Delete | **`console.log` only** — row is not removed, no confirmation | Delete with confirmation + reason | Delete with confirmation | §5.2 faciliti-manager booking endpoints | Missing Workflow | High |
| B19 | Check In modal | Checkout Date | **"31-10-2025 13:00"** hardcoded | Actual checkout | `stay` checkout date | §6 step 7 | Static/Hardcoded | High |
| B20 | Check In modal | Checkin Date fallback | Falls back to **"16-10-2025 11:00"** when blank | Actual value or explicit blank | `booking.checkinDate` | §8 `booking` (checkinDate) | Static/Hardcoded | High |
| B21 | Check In modal | Room allocation | *absent* | Room assignment step | Room/amenity assignment at check-in | §10 "Check In → `POST /api/facility/{ID}/bookings/{BK_ID}/check-in` → Stay is created/activated; room becomes occupied"; §6 step 4 | Missing Workflow | High |
| B22 | Check In modal | Key issue | *absent* | Key/card issuance (ties to Kleio + Default Key Settings) | Room key generation | §10 "Generate Key → `POST /api/facility/{ID}/stays/{STAY_ID}/generate-key` → `device-communicator` lock command"; §6 step 5 | Missing Workflow | High |
| B23 | Check In modal | ID verification | *absent* | Document check step | Guest ID verification | §20 Booking Workflow inputs | Missing Workflow | High |
| B24 | Check In modal | Confirm action | "Check In" button just closes the dialog | Persisted check-in | Persisted check-in creating/activating `stay` | §10 Check In flow; §6 step 4 | Missing Workflow | High |
| B25 | Extend modal | Current checkout | **"31-10-2025 13:00"** hardcoded, `readOnly` | Actual current checkout | `stay` current checkout date | §6 step 7 | Static/Hardcoded | High |
| B26 | Extend modal | HH/MM steppers | Buttons with **no state and no handlers** — value can never change | Working time picker | Working date/time entry for extension | §6 step 6 "Stay can be extended" | Missing Workflow | High |
| B27 | Extend modal | AM/PM toggle | Static button, no handler | Working toggle | Working time entry | §6 step 6 | Missing Workflow | Medium |
| B28 | Extend modal | Availability check | *absent* | Conflict/availability validation | Availability validation | §6 step 2 "Availability is checked through `/check-availability`"; §20 "Processing: availability check" | Missing Workflow | High |
| B29 | Extend modal | Rate recalculation | *absent* | New charge for extension | Recalculated charge on `invoice` | §8 `invoice` (amount); §20 Booking Workflow outputs | Missing Metric | Medium |
| B30 | Bulk Upload | Sample Template | Button with **no href/handler** | Downloadable template | Bulk upload template | §20 Booking Workflow trigger "uploads bulk CSV" | Missing Workflow | Medium |
| B31 | Bulk Upload | Last-upload report | `href="#"` | Real report link | Upload result report | §20 Booking Workflow failure scenarios | Missing Workflow | Medium |
| B32 | Bulk Upload | Submit | **`console.log` only** | Upload + row-level validation result | Bulk CSV upload with validation | §20 Booking Workflow trigger + failure scenarios "unavailable room, invalid dates" | Missing Workflow | High |
| B33 | Form | Submit | **`console.log` only** | Persisted create | Persisted create | §10 "Create Booking → `POST /api/facility/{ID}/bookings`" | Missing Workflow | High |
| B34 | Form | Booking status field | *absent* | Status on create/edit | Booking/stay status | §8 `stay` (status) | Missing Field | High |
| B35 | Form | Room allocation field | *absent* (only "Room Preference") | Specific room assignment | Room/amenity assignment | §8 `stay` (amenityId); §6 step 4 | Missing Field | High |
| B36 | Form | Rate / tariff | *absent* | Room rate, taxes, total | `package.price` | §8 `package` (id, name, price, amenityType) | Missing Field | High |
| B37 | Form | Payment | *absent* | Payment method, advance, balance | `invoice` (amount, status) | §8 `invoice` | Missing Field | High |
| B38 | Form | Arrival/Depart granularity | `type="date"` — **time cannot be entered**, yet the table shows `27-12-2025 16:22` | Date **and** time | Date **and** time for arrival/departure | §8 `booking` (checkinDate); §20 failure scenario "invalid dates, checkout time exceeded" | Missing Field | High |
| B39 | Form | Company / corporate | *absent* | Corporate account, GST is present but unlinked | Not specified in IKANOS docs | — (no IKANOS requirement found) | Missing Field | Medium |
| B40 | Form | ID document type | File upload only, no type/number fields | Document type + number | Guest ID document type/number | §20 Booking Workflow inputs "guest data" | Missing Field | Medium |
| B41 | Form | Uploaded file feedback | Always shows "No file chosen" — input has **no `onChange`** | Selected file names | Selected file feedback | §20 Booking Workflow inputs | Missing Workflow | Medium |
| B42 | Form | Sub Packages options | Breakfast/Full Board/Half Board/Room Only — hardcoded, unrelated to Config → Packages | Driven by Facility Management → Packages master | Driven by `package` master | §8 `package`; §10 Packages row | Static/Hardcoded | High |
| B43 | Form | Room Preference options | Golden/Delux/Premium/Standard — hardcoded | Driven by room-type master | Driven by `package` / `amenityType` master | §8 `package` (amenityType); §10 Rooms/Amenities row | Static/Hardcoded | High |
| B44 | Form | Country code options | 4 hardcoded (+91/+1/+44/+971) | Full country master (dump has a `countries` table) | Country master | §8 — `countries` reference data (see also production dump table `countries`) | Static/Hardcoded | Medium |
| B45 | Form | Nationality options | 4 hardcoded | Full nationality master | Nationality master | §20 Booking Workflow inputs "guest data" | Static/Hardcoded | Medium |
| B46 | Form | Validation | Required markers shown but **no validation runs** on submit | Field validation + error messages | Validation with documented failure messages | §20 Booking Workflow failure scenarios; §9 "Error messages are mostly user-facing strings documented in each module" | Missing Workflow | High |
| B47 | Page | Booking KPIs | *absent* | Today's arrivals/departures, pending, confirmed, cancelled counts | Booking KPIs on Dashboard | §10 Dashboard row "bookings" data tables `booking`, `stay` | Missing Count | High |

**Bookings total: 47 gaps** (High 30 · Medium 13 · Low 4)

---

*Sections 4.6 – 4.15 (Services Tracking → Default Key Settings), Section 5 (consolidated Master Table), Section 6 (Missing-module analysis), Section 7 (Module-wise summary), Section 8 (Manual verification checklist), Section 9 (Final summary) and Section 10 (Recommended implementation order) continue below.*
