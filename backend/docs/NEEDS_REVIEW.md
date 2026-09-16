# HMS Phase 1 — NEEDS_REVIEW Register

Every item below is a point where the IKANOS documentation is **silent or
incomplete**. Per the Phase 1 brief, nothing here was invented — the gap is
recorded instead of guessed at.

**Source of truth:** `d:\Inspornics\HMS_ikanos\Ikanos_code\`
  - `CPA` = `COMPLETE_PROJECT_ANALYSIS_REPORT.md`
  - `FM`  = `1_FACILITI_MANAGER_DOCUMENTATION.md`
  - `DM`  = `2_DEVICE_MANAGER_DOCUMENTATION.md`
  - `AM`  = `4_ALARM_MANAGER_DOCUMENTATION.md`
  - `SH`  = `7_SCHEDULE_HANDLER_DOCUMENTATION.md`
  - `LAD` = `8_LAYERS_ARCHITECTURE_DIAGRAMS.md`

> **Standing caveat.** CPA §0 "Evidence Boundary" states the IKANOS snapshot
> contains *no `src/`, no backend source, no ORM schema, no migrations*. Its
> entity tables are documentation-derived. This schema therefore reproduces
> the **documented** model, and is explicitly **not** a reconstruction of the
> original production DDL.

---

## A. Severity legend

| Level | Meaning |
|---|---|
| **A1** | Entity referenced by a documented API but has **no field table at all** |
| **A2** | Documented field whose **type/enum values** are not specified |
| **A3** | Field strongly implied by a documented API/error message but **not listed** |
| **A4** | Relationship implied but **not explicitly documented** |
| **A5** | Structural choice made for relational integrity |

---

## B. Missing entities (A1)

Referenced by documented APIs, but no field definition exists anywhere.
**None of these were created.**

| # | Entity | Evidence it exists | Impact |
|---|---|---|---|
| B1 | `property` | `POST /api/facility/{ID}/properties`, `PUT /properties/{PROP_ID}` (FM §5). Distinct from `propertyType`. | Building/floor hierarchy below `propertyType` cannot be modelled. `amenity.floor` is currently a free-text column. |
| B2 | `serviceType` (maintenance) | `CRUD /api/facility/{ID}/maintenance/service-types` (FM §9); `maintenanceSchedule.serviceTypeId` (SH §10) | `maintenance_schedule.service_type_id` exists as a UUID column **with no FK** because the target table is undefined. |
| B3 | `maintenanceCategory` | `GET/PUT /api/facility/{ID}/maintenance/categories` (FM §9) | Maintenance taxonomy unmodelled. |
| B4 | `country` / country code | "Country Codes — Phone country code list" (FM §2); `EMPLOYEES.INVALID_PHONE` references country code (FM §13) | Phone validation reference data unmodelled. |
| B5 | `restaurant` | `GET /api/facility/{ID}/restaurants` (FM §9) | Restaurant grouping for `foodMenu` unmodelled. |
| B6 | `roomAmenity` | `CRUD /api/facility/{ID}/room-amenities`, `PUT /rooms/{ROOM_ID}/amenities` (FM §6). Distinct from `amenityType` (hotel-wide). | Per-room features (TV/AC/WiFi) unmodelled. |
| B7 | `travelDesk`, `healthFitness`, `businessCenter` | `POST` config endpoints (FM §9) | Service-configuration entities unmodelled. |
| B8 | `module` (RBAC) | `GET /api/facility/{ID}/modules`; `GET/PUT /user-roles/{ROLE_ID}/permissions` (FM §10) | Permission structure unmodelled — see D1. |

---

## C. Entities materially under-specified (A3)

Documented with only a handful of "key fields". The columns created are
**exactly** those documented; the listed gaps were **not** added.

### C1. `booking` — most severe gap
Documented (CPA §8 / FM §12): `id, firstName, checkinDate, packageId`

Implied by documented APIs/errors but **not defined**:
- `lastName` — FM §13 error text implies a full guest name
- depart/checkout date — `BOOKING.DATE_ERROR`: *"Arrive date cannot be greater than depart date"* (FM §13)
- `phoneNumber` — `BOOKING.DUPLICATE`: *"Guest with same phone number exists"* (FM §13)
- booking status — no status field is documented on `booking` at all
- email, nationality, city, gender, number of rooms, occupant count, GST, booking reference, comments, ID-proof documents

> The HMS frontend renders all of the above, but the IKANOS docs do not
> define them on `booking`. Requires product sign-off before adding.

### C2. `employee`
Documented: `id, email, departmentId, userRoleId`

Implied but not defined:
- `firstName` / `lastName`
- `phoneNumber` — `EMPLOYEES.DUPLICATE_PHONE` implies a **unique** phone (FM §13)
- active/inactive status — `PUT /employees/{EMP_ID}/status` exists (FM §8)
- `functionId` — a `function` entity exists and `/functions` CRUD exists (FM §8), but no `employee.functionId` is documented. **See D2.**

### C3. `user` (`app_user`)
Documented: `id, email, password, userRoles, facilityId`

Implied but not defined:
- `username` — login is `POST /api/login { username, password }` (FM §4), yet only `email` is a documented column
- `name` — returned in the login response (FM §4)
- active flag — `LOGIN.USER_INACTIVE`: *"User with the given username is inactive"* (FM §13)

### C4. Other entities

| Entity | Documented | Not defined |
|---|---|---|
| `stay` | id, bookingId, amenityId, status | actual check-in/checkout timestamps, extension target, key-generated flag |
| `occupant` | id, bookingId, firstName, phoneNumber | lastName, age/type, ID proof |
| `event` | id, name, venue, startDate, status | endDate, chiefGuests, attendees, description, image, cancellation reason (`PUT /events/{ID}/cancel` exists) |
| `offer` | id, name, couponCode, validFrom | validTo, description, offerBy, image, applicable rooms, withdrawn flag (`PUT /offers/{ID}/withdraw` exists) |
| `holiday` | id, startDate, lockMessage | endDate, description |
| `invoice` | id, stayId, amount, status | invoice number, issue date, currency, line items |
| `serviceRequest` | id, serviceType/requestType, roomId, assignedTo, status, guestId, subject, createdOn | department, quantity, description, priority, completion timestamp, service category |
| `foodMenu` | id, name, foodCode, categoryId, price | veg/non-veg, spicy flags |
| `facility` | id, name, address, settings | logo (named in FM §2 prose, absent from the field table), timezone, currency, default check-in/out times |

---

## D. Undefined structures (A2)

| # | Item | Documented as | Implementation | Action needed |
|---|---|---|---|---|
| D1 | `userRole.permissions` | "permissions" (CPA §8). FM §10 shows an 8-module × 4-role matrix but no table. | `JSONB` column | Define the permission model. FM §10 names module IDs `CALEIDO_NETWORK` / `device-alerts` / `SERVICE_TRACKING`. |
| D2 | `amenity.status` | "status" — **values never enumerated** | `VARCHAR(50)` | Enumerate. Compare against `stay.status` and the frontend's Available/Unavailable vs Occupied/Vacant vocabularies. |
| D3 | `stay.status` | "status" — values never enumerated | `VARCHAR(50)` | Enumerate. |
| D4 | `serviceRequest.status` | "status" — values never enumerated | `VARCHAR(50)` | Enumerate. Note `deviceIncident.status` **is** enumerated (AM §11) but `serviceRequest.status` is not. |
| D5 | `event.status` / `offer` / `invoice.status` | "status" — values never enumerated | `VARCHAR(50)` | Enumerate. |
| D6 | `deviceIncident.alertSeverity` | "Severity display" (AM §11), alongside the enumerated `severity` | `VARCHAR(50)` | Clarify why two severity fields exist. |
| D7 | `deviceIncident.assignedUser` | "Embedded user info" — an object (AM §11) | `JSONB` | Confirm denormalisation is intended vs relying on `assignedTo`. |
| D8 | `valueAlerts.status` | Integer `0=Active, 1=Resolved` (AM §11) — an integer, unlike every other status | `INTEGER` | Preserved as documented. Confirm it should not be normalised. |
| D9 | `notification.referenceId` | "Related entity ID (alert, booking, etc.)" (NE §8) | `UUID`, **no FK** | Polymorphic by design — no FK possible. Confirm. |
| D10 | `scheduledTask.targetEntity` | "Related entity (room, stay, etc.)" (SH §10) | `UUID`, **no FK** | Polymorphic by design. Confirm. |
| D11 | `maintenanceSchedule.startTime` | "Schedule time", type `String` (SH §10) | `VARCHAR(20)` | Kept as string per the doc; confirm it is not a `TIME`. |
| D12 | `firmware.deviceType` | `String` (DM §10) — **not** the `device.type` enum | `VARCHAR(100)` | Confirm whether it should reference the `DeviceType` enum. |

---

## E. Inferred relationships (A4) — please confirm

These FKs are **not explicitly documented**. They were added because the
column is documented and a target table exists.

| # | Relationship | Basis | Risk if wrong |
|---|---|---|---|
| E1 | `amenity.property_type_id -> property_type.id` | FM §5 documents a building/floor structure and `propertyType`; the link column itself is not documented. | Building hierarchy misattributed. **Nullable** — safe to drop. |
| E2 | `employee.job_function_id -> job_function.id` | `function` exists with `departmentId` (CPA §8); FM §8 exposes `/functions`. The FK direction is assumed. | Staff capability mapping wrong. **Nullable**. |
| E3 | `service_request.assigned_to -> employee.id` | "assignedTo | UUID | Assigned staff". Could target `app_user` instead. | Assignment resolution wrong. |
| E4 | `device_incident.assigned_to -> employee.id` | Same as E3. AM §11 also carries `assignedUser` (a user object), which suggests `app_user` may be correct. | **Most likely of these to be wrong.** |
| E5 | `job_order.assigned_to -> employee.id` | "Assigned technician" (DM §10). | Technician assignment wrong. |
| E6 | `service_request.guest_id -> app_user.id` | LAD shows `serviceRequest.guestId`; GUEST is a documented `roleType`. Could target `occupant`. | Guest attribution wrong. |
| E7 | `service_request.room_id -> amenity.id` | "roomId" + CPA §8 defines `amenity` as "Rooms/locations". | Low risk. |
| E8 | `energy_aggregate.room_id -> amenity.id` | Same basis as E7. | Low risk. |
| E9 | `package.amenity_type_id -> amenity_type.id` | `package.amenityType` (CPA §8) + `amenityType` table (FM §12). | Low risk. |
| E10 | `maintenance_schedule.amenity_id` uses `ON DELETE CASCADE` | Schedules are meaningless without their room. Cascade behaviour is nowhere documented. | Data loss on room deletion. |

> **All `ON DELETE` behaviours are engineering choices** — the IKANOS docs
> specify none. Current policy: `CASCADE` from `facility` (tenant root) and
> for owned children; `SET NULL` for optional references; `RESTRICT` on
> `booking.package_id` (supported by `PACKAGES.HAS_BOOKING`: *"Cannot delete
> a package which has booking"*, FM §13).

---

## F. Structural additions for relational integrity (A5)

Three tables exist beyond the 36 in the brief. None add business fields.

| # | Table | Reason |
|---|---|---|
| F1 | `amenity_type` | **Documented** in FM §12 (`id, name, image`) and required by `package.amenityType` + `/amenity-types` CRUD — but absent from the 36-entity list. |
| F2 | `app_user_user_role` | `user.userRoles` is documented as a **list** (FM §4 login response). A junction is required; a scalar column would lose integrity. |
| F3 | `job_order_device` | `jobOrder.devices` is documented as type **`Array`** (DM §10). Same reasoning. |

### Naming deviations
Two IKANOS entity names collide with SQL reserved/ambiguous words:

| IKANOS | PostgreSQL table | Reason |
|---|---|---|
| `user` | `app_user` | `USER` is a reserved word in PostgreSQL |
| `function` | `job_function` | `FUNCTION` is a SQL keyword |

### Technical columns added
`created_at` / `updated_at` on every table (`TimestampMixin`). These are
operational audit columns and are **not** part of the IKANOS field set.
Documented temporal fields (`createdOn`, `resolvedOn`, `registeredOn`,
`lastSeen`, `timestamp`, ...) are declared **separately and explicitly** on
their entities so documented data is never conflated with audit metadata.

---

## G. Recommended resolution order

1. **B1 `property`** — blocks the building/floor hierarchy the Dashboard needs.
2. **C1 `booking`** — the most-used entity; currently 4 documented fields.
3. **D1 permissions** — blocks all RBAC, which the HMS frontend lacks entirely.
4. **E4 / E3 assignment targets** — decide `employee` vs `app_user` before any data is written.
5. **D2–D5 status vocabularies** — enumerate before seeding.
6. **B2 `serviceType`** — required to add the missing FK on `maintenance_schedule`.
7. Remaining B, C and D items.
