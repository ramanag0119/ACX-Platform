# HMS P1 Actionable Items Analysis

**Room reassignment · sensor ↔ room mapping · DB source tracing**

| | |
|---|---|
| **System** | ACX Platform — Hospitality Management System (HMS) |
| **Repository** | `ACX-Platform`, branch `develop` @ `e64ee07`, plus the uncommitted working tree (see §0.2) |
| **Database** | PostgreSQL 18.6, `hms_db` / `public`, live Alembic head `7c4e2b9a1d53` |
| **Date** | 2026-09-26 |
| **Type** | Analysis only. No code, schema, data, migration or configuration was changed. |

---

## 0. Method and evidence rules

### 0.1 Method
- **Code:** backend models, services, routes, schemas and tests; frontend API client, hooks, mutations and pages. Every `file:line` cited here was read during this analysis.
- **Live database:** read-only queries only (`SET TRANSACTION READ ONLY`, rolled back). No rows were written.
- **Layering:** there is **no repository/DAO layer** in this codebase. Services build SQLAlchemy `select()` statements directly on the request session. In every trace below, the service function *is* the data-access layer. The only raw SQL is the health check (`backend/app/api/v1/endpoints/health.py:38-44`).
- **Not done:** no authenticated API calls (seeded accounts cannot log in by design). API behaviour is established from code and tests; data statements come from the live database.

### 0.2 Working-tree state during this analysis
Parallel work outside this analysis has applied migration `7c4e2b9a1d53` to the live database. It renames `service_status` id 3 from "Partially completed" to **"In Progress"**. The same work left label-only edits, uncommitted, in 14 tracked files (services, schemas, seeds, tests, `serviceStatus.ts`, `ServiceTracking.tsx`, `ServiceRequestActionsDialog.tsx`). **None of these files belong to Item 1 or Item 2.** Item 3 reads the working tree as it stood.

### 0.3 Abbreviations
- **Backend:** `SW` = `backend/app/services/stays_write.py`; `DW` = `backend/app/services/devices_write.py`; `ep/` = `backend/app/api/v1/endpoints/`; `sv/` = `backend/app/services/`.
- **Frontend:** `H` = `frontend/src/lib/api/hooks.ts`; `W` = `frontend/src/lib/api/writes.ts`; `M` = `frontend/src/lib/api/mutations.ts`; `D/` = `frontend/src/features/dashboard/`; `O/` = `frontend/src/features/occupancy/`.

---

## P1 – Item 1: Room reassignment logic

### Finding
**The current implementation does not meet the requirement.** A reassignment **overwrites** the existing `room_allocation` row in place, changing its `room_id` and `package_id`. No assignment is closed, no end date or end state is recorded, and no new record is created. The previous room assignment is lost. The project's own test suite asserts this overwrite behaviour. The model and API documentation still say "re-allocation writes a new row", which contradicts the code.

### Current behaviour
```
Occupancy page "Reassign" → ReallocateRoomDialog → PATCH /api/v1/room-allocations/{allocation_id} {room_id}
  → SW.reallocate_room:
       allocation.room_id    = new room          (same row, same id)
       allocation.package_id = new room's package
       old room amenity.status → Available
       new room amenity.status → Occupied (if checked in) else Allotted
       stay.modified_by      = actor
  → returns the stay's allocation list
```

### Expected behaviour (requirement)
Close the existing assignment (end date / end state) → create a **new** assignment record → the new record becomes the active one, and the old one stays as history.

### Database tables

**`room_allocation`** is the room-assignment table (model `backend/app/models/stay.py:130-157`, class `RoomAllocation`).

| Aspect | Current schema |
|---|---|
| Primary key | `id` uuid |
| Foreign keys | `stay_id` → `stay.id` (on delete CASCADE); `room_id` → `amenity.id` (CASCADE); `package_id` → `package.id` (CASCADE); `created_by` → `app_user.id` (RESTRICT) |
| Room columns | `room_id`, `package_id` |
| Stay / guest columns | `stay_id`. The guest is reached via `stay.booking_user_id` and `stay_user`. |
| **Start date/time** | **None.** Only the technical `created_on` (timestamptz, default now()). |
| **End date/time** | **None.** Only `updated_on`, which is refreshed on any update (`onupdate=func.now()`, `backend/app/db/base.py:104-107`). |
| Status / state | `status` smallint, nullable, no FK or CHECK. It is always written as `ALLOCATION_ACTIVE = 1` (`SW:91`) and never changed. |
| Unique constraints | Only `legacy_id`. **Nothing** prevents two rows for the same (stay, room) or the same room across stays. |

**Related tables whose room reference is *not* moved:**
- `stay_user.room_id`: occupant ↔ room.
- `service_request.amenity_id`: correct to keep as history.
- `user_device_acl.amenity_id`, `access_key`: unused by the app.

**Stay-level dates** (`stay.expected_*` / `actual_*`) are per stay, not per room.

### Backend logic

| Function | Location | Behaviour |
|---|---|---|
| Create assignment | `SW._allocate` (:365-406), called by `create_stay` (:169) and `allocate_room` (:409-424) | Validates the room exists and `_assert_room_free`, rejects the same room twice in one stay (:379-386), inserts a new row with `status=1` (:390-398), and sets the room Allotted or Occupied (:401-404) |
| **Reassign** | `SW.reallocate_room` (:428-466) | Rejects the same room (:444-445) and cancelled or checked-out stays (:446-447), validates the new room (:449-451) and `_assert_room_free` (:452). Then **updates in place**: `allocation.room_id = room_id`, `allocation.package_id = new_room.package_id` (:454-456). Old room → Available (:458), new room → Occupied/Allotted (:459-461) |
| "Close" assignment | **Not implemented.** The nearest is `SW.release_allocation` (:468-485), which **hard-deletes** the row (`db.delete(allocation)`, :479) and sets the room Available. It is refused while the stay is in house (:474-477). |
| Room state change | `SW._set_room_status` (:126-131); `SW.update_room_state` (:563); check-in / check-out / cancel | Writes `amenity.status` |
| Double-hold guard | `SW._assert_room_free` (:142-156) | 409 if any *other* stay in `LIVE_STAY_STATUSES` (:83-89) holds the room. Not date-based; no DB lock or constraint. |
| Transaction | `writes.transaction()` (`sv/writes.py:53-74`) | Commit once, roll back on error, `IntegrityError` → 409 |

### API
- **Route:** `PATCH /api/v1/room-allocations/{allocation_id}`, handler `reallocate_room` (`ep/stays_write.py:276-296`), permission `bookings:write`.
- **Request body:** `ReallocateRoomBody {room_id}` (`backend/app/schemas/ops_write.py:195-196`).
- **Response:** the stay's allocation list via `stay.stay_room_allocations` (`sv/stay.py:286`).
- **Related routes:** `POST /stays/{id}/room-allocations` (allocate, `ep/stays_write.py:249`), `DELETE /room-allocations/{id}` (release, `:299`), `GET /stays/{id}/room-allocations` (`ep/stays.py:194`).

### Frontend
1. `O/pages/Occupancy.tsx`: "Reassign" column (:498), button `onClick={() => setReallocateRoom(room)}` (:626), dialog mounted at :669-671.
2. `O/components/ReallocateRoomDialog.tsx`:
   - Loads allocations with `useStayRoomAllocations(stayId)` (:115).
   - Picks the allocation to move with `rows.find(row => row.room_name === currentRoomName) ?? rows[0]` (:120).
   - Offers Available guest rooms without a current stay (:127-128).
   - Submits with `reallocate.mutate` (:143).
3. `useReallocateRoom` (`M:283-287`) → `W.reallocateRoom` (`W:241`). This invalidates `INVALIDATE.stays` = stays, occupancy, rooms, invoices, daily-data-points (`M:27`).

### Evidence (requirement checks)

| # | Check | Result | Evidence |
|---|---|---|---|
| 6 | Overwrite, or close + new record? | **A. Overwrite** | `SW:454-456`. Test `test_reallocation_moves_the_stay_and_swaps_both_room_states` asserts the *same* allocation id now holds the new room (`backend/tests/test_stay_write_api.py:382-404`, assertion at :399-401) |
| 7 | History preserved? | **No.** The previous `room_id` is overwritten, and no audit or history table records it | `SW:454-456`; no history table for allocations exists (93-table inventory) |
| 8 | Start/end dates maintained? | **No such columns.** `updated_on` changes, so the move time is only recoverable as the row's last update | `models/stay.py:130-157`; `db/base.py:104-107` |
| 9 | Can an old assignment stay active after reassignment? | Not as a row, because there is only one row. But the old room's **other links remain on the old room**: `stay_user.room_id` is not moved | No `StayUser` update in `SW.reallocate_room`. Readers filter on `StayUser.room_id` (`sv/occupancy.py:287`, `sv/stay.py:231-239`) |
| 10 | Multiple active assignments per stay? | **Yes, by design** (multi-room stays). `_allocate` blocks the same room twice (:379-385), but **`reallocate_room` does not**: `_assert_room_free` ignores the same stay (:452). Moving allocation A onto a room the same stay already holds through allocation B would leave two rows for one room. | `SW:379-386` vs `:449-456`. Not covered by a test. |
| 11a | Effect on stay | `stay.modified_by` only. No dates change; `no_of_rooms` unchanged. | `SW:462` |
| 11b | Effect on room allocation | Row overwritten; `status` stays 1 | `SW:91,454-456` |
| 11c | Effect on occupancy | `current_stay` follows the allocation to the new room (`sv/occupancy.py _current_stays`). Occupants shown in room detail are filtered by `StayUser.room_id == amenity_id` (`sv/occupancy.py:287`), so they stay attributed to the old room. | — |
| 11d | Effect on room status | Old room → Available **unconditionally**; new room → Occupied/Allotted | `SW:458-461` |
| 11e | Effect on billing/payment | **None.** No payment process exists, and `invoice` has no room column and no create path. | `models/stay.py Invoice`; `sv/stay.py:379-410` (read only) |
| 11f | Other modules | `service_request.amenity_id` keeps the old room (history). Digital keys and device ACLs (`access_key`, `user_device_acl`) have no app code, so no key re-issue happens. No `activity` row is written. | grep of `backend/app/services` |
| 12 | Validation present | Same room → 422; cancelled or checked-out stay → 409; unknown room → 422; room held by another live stay → 409; bookings write permission | `SW:444-452`; `ep/stays_write.py:276-282` |
| 13 | Tests | `test_reallocation_moves_the_stay_and_swaps_both_room_states` (:382), `test_reallocating_into_an_occupied_room_is_409_and_changes_nothing` (:407), `test_reallocating_to_the_same_room_is_rejected` (:434); also allocate / release tests (:331, :367, :450) | `backend/tests/test_stay_write_api.py` |
| 14 | **Satisfies requirement?** | **No** | — |

### Gap
1. There is no close-then-create: the existing row is mutated.
2. There are no assignment validity columns (start/end) and no usable end state. `status` is fixed at 1.
3. Assignment history is irrecoverable. Only `created_on` / `updated_on` of the surviving row remain.
4. Documentation contradicts the code:
   - `models/stay.py:131-132`: "Re-allocation writes a new row".
   - `ep/stays.py:199-200`: "A re-allocation writes a new row, so this is the assignment history".
5. `stay_user.room_id` is not moved with the stay.
6. There is no same-stay duplicate check on the reallocate path.
7. The UI can choose the wrong allocation on multi-room stays (`rows[0]` fallback).

### Impact
- The room-change trail for a stay cannot be reported or audited (who was in which room, when).
- Any future per-room billing, energy-per-guest or housekeeping attribution has no historical basis.
- Occupant ↔ room links drift after a move.
- Anyone who trusts the docstrings will assume history exists.

### Recommended investigation
- Confirm with the business what "closed" means (end timestamp, end status value, or both) and which record should carry it.
- Review every reader of `room_allocation` that assumes one-row-per-room-per-stay, and every reader that counts rows as history (e.g. `allocation_count`, `sv/occupancy.py`), before changing semantics.
- Decide whether `stay_user.room_id` should follow a reassignment.
- Establish the meaning of `room_allocation.status`: there is no lookup table and the only value written is 1.

---

## P1 – Item 2: Sensor ↔ room mapping

### Finding
The mapping is **stored directly on the device row**: `device.amenity_id` (NOT NULL FK → `amenity.id`). This is option **A**. There is **no separate mapping table**, no validity period and no mapping history. The room's business identity (`amenity.id`, a stable UUID) is independent of the sensor, so a room can receive a new sensor.

However, the architecture does **not** make replacement seamless or traceable:
- Telemetry is attributed to a room through the device's **current** `amenity_id`, so moving a device re-attributes its whole history.
- A decommissioned device keeps its room link and is still counted and summed.
- Some tables key sensors by free-text `device_name`, which follows **different naming conventions** in different tables.

### Current mapping mechanism

| Question | Answer | Evidence |
|---|---|---|
| Sensor table | `device` (28 cols); family in `device_type` (Intellihub = HUB, AirQ, Mikos, Kleio) | `backend/app/models/device.py:97-178` (`Device`), `:42-55` (`DeviceType`) |
| Room table | `amenity` (room/space), typed by `amenity_type.amenity_category` | `backend/app/models/amenity.py` (`Amenity`, `AmenityType`) |
| Mapping column | `device.amenity_id` uuid **NOT NULL**, FK → `amenity.id` ON DELETE CASCADE | `models/device.py` (`amenity_id`, nullable=False); live FK catalog |
| Other link columns | `device.parent_device_id` → `device.id` (hub hierarchy); `device.facility_id` → `facility.id`; `device.device_uid` (varchar(16), **UNIQUE**) = physical identity; `device.device_name` (free text); `device.installed_on` (single timestamp); `device.device_config_status` enum (configured, bad_configuration, commissioned, decommissioned, under_maintenance, missing) | `models/device.py`; enum in the live catalog |
| `sensor_id` / `room_id` on device | **Not Found.** There is no `sensor_id` column anywhere. "Sensor" appears only in `sensor_operation_stat`. | grep of `backend/app`, `frontend/src` |
| Separate mapping table | **Not Found** | 93-table inventory |
| Hardcoded mapping | **Not Found** in backend or frontend | — |

**Tables that copy the room at event time** (history-stable) carry their own `amenity_id` as well as `device_id`: `device_alert`, `value_alert`, `device_incident`, `sensor_operation_stat`, `lock_activity_log`, `user_device_acl`. In live data every copy matches the device's current room (0 mismatches in each of `device_alert`, `value_alert`, `device_incident` and `sensor_operation_stat`).

**Tables that do *not* copy the room:** `device_stat` (time-series), `device_current_stat`, `device_health_stat`, `battery_life_stat`. Their room is always derived through `device.amenity_id` *now*.

**Tables keyed by device name text instead of a FK:**

| Table | Key | Live values | Match to `device`? |
|---|---|---|---|
| `energy_stat` | PK (device_name, facility_id, amenity_id, hour); no device FK | `101-mik`, `106-mik`, `205-mik` | **0 of 72 rows** match `device.device_name` or `device_uid` |
| `value_alert_limit_config` | UNIQUE (device_name, parameter, facility_id); `device_id` nullable | `205-mik`, `101-hub` | device_id is set; name ≠ `device.device_name` |
| `other_device` | device_name only | `MAINS-EB-01`, `MAINS-DG-01` | no link to any device, room or facility |

`device.device_name` itself holds the **room number** (`101`, `101HUB`, `205`), so three naming conventions coexist.

### Live mapping (read-only query)

| Room | Devices (device_uid · type · parent · config status) |
|---|---|
| 101 | DEV101HUB · Intellihub · — · commissioned; DEV101AIR · AirQ · DEV101HUB · commissioned; DEV101KLE · Kleio · DEV101HUB · commissioned; DEV101MIK · Mikos · DEV101HUB · commissioned |
| 104 | DEV104KLE · Kleio · — · under_maintenance |
| 106 | DEV106HUB · Intellihub · — · **missing**; DEV106AIR · AirQ · DEV106HUB · configured; DEV106KLE · Kleio · DEV106HUB · commissioned; DEV106MIK · Mikos · DEV106HUB · configured |
| 205 | DEV205HUB · Intellihub; DEV205AIR / KLE / MIK → DEV205HUB (all commissioned) |
| REST01 | DEVRESTMIK · Mikos · — · bad_configuration |

In the live data, every child device's parent hub is in the same room (0 cross-room parents).

### Relationship
- **Room → devices:** `amenity 1 ── * device`. One room can have **multiple sensors** of **multiple types**, with **parent/child** (hub → sensors) via `parent_device_id`.
- **Device → room:** each device belongs to **exactly one** room (NOT NULL). **A sensor cannot be mapped to multiple rooms.**
- **Parent and child in the same room:** not enforced. `DW.create_device` / `update_device` only check that the parent exists (`DW:76`, `:108`) and that a device is not its own parent (`:106-107`).

### Backend logic

| Function | Location | Mapping behaviour |
|---|---|---|
| Register device | `DW.create_device` (:67-99) | Requires an existing `amenity_id` (:73-75); `device_uid` unique or auto `DEV######` (:78-82); `facility_id` from payload, room or default (:87); config status defaults to `configured` (:89) |
| Change device | `DW.update_device` (:102-116) | `DeviceUpdate` permits `amenity_id` and `parent_device_id` (`schemas/ops_write.py:246-253`). **`apply_changes` overwrites `device.amenity_id` in place** (:114); no history is kept |
| Commission / decommission / maintenance | `DW.set_device_config_status` (:129-139) | Changes only `device_config_status`. **Does not clear `amenity_id`**; writes no end date or history. The decommission `reason` is accepted by the route but not stored. |
| Read devices per room | `sv/device.py list_devices` (filter `amenity_id`, optional `device_config_status` :189-190) | No default exclusion of decommissioned devices |
| Room telemetry | `sv/telemetry.py list_device_stats` (:145), `_stat_stmt` | `device_stat JOIN device … LEFT JOIN amenity ON amenity.id = device.amenity_id`; filter `Device.amenity_id == :amenity_id` (`_stat_stmt` join at :138, filter :174). No config-status filter. |
| Room device count | `sv/occupancy.py get_occupancy` (:299-301) | `COUNT(device) WHERE amenity_id = :room`. Includes decommissioned and missing devices. |
| Job order "replacement" | `sv/job_order_write.py` | `type_of_work = replacement` exists and `job_order_device` links devices, but **no device row is changed** (devices are only validated, :101) |

### API
- `GET /api/v1/devices?amenity_id=…` (`ep/devices.py:125`)
- `GET /devices/{id}` (:177), `GET /devices/{id}/health` (:197)
- `POST /devices` (`ep/devices_write.py:78`), `PATCH /devices/{id}` (:103)
- `POST /devices/{id}/commission` (:116), `/decommission` (:127), `/maintenance` (:145)
- `GET /device-stats?amenity_id=…` (`ep/telemetry.py:142`)
- `GET /occupancy/{amenity_id}` (device_count)
- Limit configs: `GET/POST/PATCH /limit-configs` (`ep/devices_write.py:200-255`)

### Frontend usage
- **Room details** (`O/components/RoomDetailsModal.tsx`): device table from `useDevices({amenity_id})` showing type, room, UID, config status (:406-411), health and installed-on.
- **Room details panel** (`O/components/RoomDetailsPanel.tsx`): `useDevices` plus `useDeviceStats`, keeping the latest reading per device+param from ≤100 rows.
- **Room power/energy** (`O/components/RoomPowerEnergy.tsx`): `useDeviceStats({param_name, amenity_id})` (:181-186), then `latestPerDevice` (:80-96). Power and energy are the **sum of each device's latest reading** (:109-114).
- **Other screens:** `StatusSection.tsx` device health counts; `JobOrder.tsx` device picker; `LimitConfigAlert.tsx`.
- **No screen calls any device write** (create, update, commission, decommission). Replacement can only be done through the API.

### Sensor replacement behaviour
There is no replacement operation. From the code, only two paths are possible:

| Path | What happens | Room identity | Sensor history | Old mapping closed? | Historical mapping identifiable? |
|---|---|---|---|---|---|
| **1. Register new + decommission old** (`POST /devices` with the same `amenity_id`, then `POST /devices/{old}/decommission`) | New device row linked to the room. The old device keeps `amenity_id` and becomes `decommissioned`. | ✔ unchanged (`amenity.id`) | ✔ kept per `device_id` | ✘ Not closed. The old device still "belongs" to the room: it is counted in `device_count` and included in room telemetry queries. Its last readings can still be summed into room power if they are among the latest 100 rows. | Partly. Only by inference from `device_config_status` + `installed_on`. There is no end date and no link "B replaced A". |
| **2. Re-point / edit in place** (`PATCH /devices/{id}` changing `amenity_id`, or reusing the row for a new physical unit) | The device row is overwritten | ✔ unchanged | ✘ Moving a device **re-attributes all of its `device_stat` / health / battery history to the new room**, because those tables have no room column | ✘ No record | ✘ None |

**Other replacement side effects:**
- `value_alert_limit_config` is keyed by `device_name` text plus a nullable `device_id`, so thresholds do not follow the room to a new sensor automatically.
- `energy_stat` rows stay attached to the room (`amenity_id`), which keeps room history stable, but they cannot be tied to either sensor.
- `mqtt_topic.device_id` and `user_device_acl.device_id` point at the physical device. Those tables are unused by the app.
- There is no validation that a room has at most one active device per type. Two active Mikos meters in one room would both be summed.

### Historical mapping
**Not implemented.**
- There is no mapping table with valid-from / valid-to, and no device ↔ room history.
- `device.installed_on` is a single timestamp that is not updated on moves.
- Event tables that copy `amenity_id` (alerts, incidents, sensor operation) preserve *where the event happened*. The time-series tables do not.

### Tests
- `backend/tests/test_device_write_api.py` covers create (:52), commission then decommission (:104-122), maintenance flag (:141), own-parent rejection (:170), unknown room (:182) and limit configs (:300-350).
- `test_update_device_appliance_and_room` (:153-168) **only asserts `appliance_name`**. Moving a device to another room is untested.
- There are no tests for replacement.

### Evidence summary
- `models/device.py` (`amenity_id` NOT NULL FK; `device_uid` UNIQUE; `parent_device_id`)
- `DW:67-139` (update at :114); `schemas/ops_write.py:228-253`
- `sv/telemetry.py` (`_stat_stmt`, `list_device_stats`); `sv/occupancy.py:299-301`
- `O/components/RoomPowerEnergy.tsx:80-114`
- Live queries listed above

### Gap
1. No mapping entity with a validity period, so the current mapping and past mappings cannot be told apart.
2. Decommissioning does not end the room link.
3. Time-series data has no room copy, so moving a device rewrites history.
4. Name-keyed tables (`energy_stat`, `value_alert_limit_config`, `other_device`) do not reference `device`, and use conventions that differ from `device.device_name`.
5. No rule enforces "one active sensor of a type per room" or "parent hub in the same room".
6. No UI for device lifecycle; the room-move path is untested.

### Recommended investigation
- Confirm the business definition of "the room's sensor" (one per type? per metering point?) and whether replacements must be auditable.
- Find out how the external IoT ingester (not in this repository) resolves devices when writing `device_stat` / `energy_stat` (by `device_uid`? by name?). This decides which identity must survive a replacement.
- Establish the `energy_stat.device_name` and `value_alert_limit_config.device_name` naming convention and its relation to `device`.
- Review readers that sum or count devices per room for how they treat `decommissioned` / `missing` devices.

---

## P1 – Item 3: DB source tracing

### Finding
The major values on the Dashboard, Occupancy, Room View, Bookings, Service Tracking, Tickets, Service Planning, Job Orders and Reports screens can be traced **end to end** to a table and column, with the exceptions listed in §3.4–3.7. The chain is always:

`table → sv/<module>.py select() → ep/<module>.py route → frontend endpoints.ts / writes.ts → H hook → component`

There is no DAO layer. Most KPI values are **aggregated in the backend** (`COUNT(*)` of a filtered list, read through `useCount` with `page_size=1`). Several screens **calculate counts and percentages in the browser from a single page of 100 rows**. A number of UI values are **hardcoded** or have **no database source**.

**Caching:** every read hook uses React Query `staleTime: 30_000` (`H:54`); report definitions use 5 min (`H:348`). Count queries (`["count", …]`, `H:111-115`) are **never invalidated by mutations** (`M:66-70` invalidates by prefix only for the `INVALIDATE` lists at `M:20-30`, none of which contain `"count"`). Dashboard KPIs can therefore lag a write until they are refetched.

### 3.1 Source-tracing matrix: Dashboard

| UI data | Frontend component | API | Backend service | Repository/DAO | Query | Table | Column | Nature |
|---|---|---|---|---|---|---|---|---|
| Device alerts (value) | `D/components/DashboardKPIs.tsx:257`, `useCount("alerts")` :237 | `GET /alerts?page_size=1` (`ep/alerts.py:134`) | `sv/alert.py list_alerts` (:130) | none | COUNT device_alert ⋈ alert_type, device, device_type, amenity | device_alert | id | Aggregated (BE) |
| … "N critical · M warning" | :258-262, :238-239 | `…&alert_severity=critical\|warning` | same | none | WHERE alert_severity = ? | device_alert | alert_severity | Aggregated ×2 |
| Active value alerts | :270, :242 | `GET /value-alerts?status=0` (`ep/alerts.py:274`) | `sv/alert.py list_value_alerts` (:391) | none | COUNT value_alert WHERE status = 0 | value_alert | status | Aggregated; "0 = active" is a FE constant (`types.ts:105`) |
| Incidents / "N unassigned" | :279-280, :243-244 | `GET /incidents[?unassigned=true]` (`ep/alerts.py:213`) | `sv/alert.py list_incidents` (:260) | none | COUNT device_incident [WHERE assigned_to IS NULL] | device_incident | id, assigned_to | Aggregated |
| **Rooms in house** | :332, `useCount("occupancy",{is_occupied:true})` :297 | `GET /occupancy?is_occupied=true` (`ep/occupancy.py:67`) | `sv/occupancy.py list_occupancy` (:217) | none | COUNT amenity WHERE EXISTS (room_allocation ⋈ stay WHERE actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL) (`IN_HOUSE`, `sv/occupancy.py:39-41`) | amenity, room_allocation, stay | actual_checkin_time, actual_checkout_time | Multi-table, Aggregated |
| … "of N rooms" | :318-324, :296 | `GET /occupancy` | same | none | COUNT amenity, **no category filter** | amenity | id | Aggregated. **Live 27 = all amenities; guest rooms = 24** |
| … "amenity flag says N Occupied" | :305-312 | `GET /amenity-statuses`, then `GET /occupancy?status=<Occupied id>` | `sv/occupancy.py:69`, `:242-243` | none | COUNT amenity WHERE status = id | amenity_status, amenity | amenity_status_name, status | Aggregated; id resolved in FE. **Second, independent "occupied" source** |
| Stays in house / "of N stays" | :349-350, :341-342 | `GET /stays[?is_in_house=true]` (`ep/stays.py:91`) | `sv/stay.py list_stays` (:141) | none | COUNT stay [IN_HOUSE] | stay | actual_checkin_time, actual_checkout_time | Aggregated |
| Service requests / unassigned | :366-367, :358-359 | `GET /service-requests[?unassigned=true]` (`ep/services.py:267`) | `sv/service.py list_service_requests` (:295) | none | COUNT service_request [WHERE assigned_to IS NULL] | service_request | id, assigned_to | Aggregated |
| Energy consumed "(no unit)" | :384-387, `useEnergySummary({group_by:"day"})` :380 | `GET /energy-stats/summary?group_by=day` (`ep/energy.py:84`) | `sv/energy.py energy_summary` (:172) | none | SUM(energy_consumed), COUNT(*) FROM energy_stat ⋈ amenity GROUP BY hour/24; total summed in Python (:276-279) | energy_stat | energy_consumed, hour | Aggregated, all-time and all facilities; FE `toFixed(3)` |
| Activities | :406, :396 | `GET /activities` (`ep/notifications.py:213`) | `sv/notification.py list_activities` (:269) | none | COUNT activity ⋈ activity_type, entity_type | activity | id | Aggregated |
| Occupancy Statistics slices | `O/components/OccupancyStatisticsChart.tsx:52,61,327,335` | `GET /amenity-statuses`; `GET /occupancy?status=<id>` for each | `sv/occupancy.py:69`, `:217` | none | COUNT amenity per status | amenity_status, amenity | amenity_status_name, status | Aggregated; FE drops zero slices |
| … centre total / % | :63, :125 | `GET /occupancy` | same | none | COUNT all amenities | amenity | id | FE: `Math.round(centreValue / total * 100)`; always 100 % at rest |
| Energy chart bars / "Average per reading" | `D/components/EnergyConsumptionChart.tsx:103`, `D/data/energyConsumption.ts:84-86` | `GET /energy-stats/summary?group_by=hour\|day&date_from&date_to` | `sv/energy.py energy_summary` | none | SUM / COUNT per bucket; day = UTC `hour // 24` | energy_stat | energy_consumed, hour | Aggregated + FE average `round(total / reading_count)`; title "Average …" but the main series is a total |
| Energy unit suffix | `EnergyConsumptionChart.tsx:116-117` | same | `sv/energy.py active_energy_unit` (:41-65) | none | DISTINCT device_param.unit WHERE param_name = 'active_energy' | device_param | unit | Backend (config, not per reading); live `kWh` |
| Caleido rings % and "dp_1 / dp_2" | `D/components/CaleidoAtWork.tsx:50-53,92` | `GET /daily-data-points/summary?metric_date_from=` (`ep/energy.py:187`) | `sv/energy.py caleido_at_work` (:317) | none | DISTINCT ON (metric_type) ORDER BY metric_date DESC; % = `int(dp_1/dp_2*100+0.5)` | daily_dual_data_point | metric_type, dp_1, dp_2 | Backend-calculated; labels hardcoded (:60-65) |
| Alerts panel rows | `D/components/AlertsPanel.tsx:34,47-49` | `GET /alerts?page_size=10&created_from=` | `sv/alert.py list_alerts` | none | ORDER BY created_on DESC | device_alert, alert_type, amenity, device | name, alert_severity, created_on, device_name | Multi-table |
| Recent activity rows | `D/components/RecentActivityPanel.tsx:39,115-132` | `GET /activities?page_size=10[&unread_only]` | `sv/notification.py list_activities` | none | ⋈ activity_type, entity_type, app_user; unread from activity_notifier | activity, activity_type, entity_type, app_user, activity_notifier | activity_type, entity_type, names, status | Multi-table; the actor name is joined in Python; "unread" means any recipient, not the current user |
| Building card: floors / rooms | `D/components/StatusSection.tsx:244-254` | `GET /buildings` (`ep/facilities.py:171`) | `sv/facility.py list_buildings` (:162) | none | COUNT(DISTINCT level_two_id), COUNT(DISTINCT amenity.id) GROUP BY building | property, property_chain, amenity | property_name, level_two_id, id | Aggregated; room count includes non-rooms |
| Devices "N Active \| N Inactive" | `StatusSection.tsx:77-78,91-93` | `GET /devices?health_status=Active\|Inactive` (`ep/devices.py:125`) | `sv/device.py list_devices` | none | COUNT device WHERE health_status = ? | device | health_status | Aggregated |
| Room tiles (number, type, status, conditions) | `StatusSection.tsx:121-133,391-405` | `GET /occupancy?floor_id=&page_size=100` | `sv/occupancy.py list_occupancy` | none | see Occupancy grid | amenity, amenity_type, amenity_status, amenity_condition(_status) | name, amenity_status_name | Multi-table; ≤100 rows per floor |

### 3.2 Source-tracing matrix: Occupancy, Room View, room detail

| UI data | Frontend component | API | Backend service | Query | Table | Column | Nature |
|---|---|---|---|---|---|---|---|
| Occupancy grid rows (Room No, Room Type, Building, Floor) | `O/pages/Occupancy.tsx:516-530`, `useAllOccupancy` (`H:237`) | `GET /occupancy?amenity_category=room&building_id&floor_id` (all pages; Non Guest = restaurant + others) | `sv/occupancy.py list_occupancy` | amenity ⋈ amenity_type ⋈ package ⟕ amenity_status ⟕ property_chain ⟕ property ×2 | amenity, amenity_type, property | name, name, property_name | Multi-table; FE shortens Room Type to its first letter |
| Guest name | :533 | same | `_current_stays` + `_user_ref` (`sv/occupancy.py:54-61`) | room_allocation ⋈ stay ⟕ app_user WHERE IN_HOUSE | app_user | first_name + last_name of **stay.booking_user_id** | Backend-concatenated; this is the booker, not necessarily an occupant |
| Check-In / Check-Out | :536-539 | same | same | — | stay | actual_checkin_time / **expected_checkout_time** | Direct; the "Check-Out" header shows the *expected* time |
| "Overdue" tag | :166, `isOverdueCheckout` :196-199 | — | — | — | — | — | FE: `checkedIn && checkOutTime < now` |
| Status pills | :607-611 | same | `_conditions_for` (:178) | amenity_condition_status (status = 1) ⋈ amenity_condition | amenity_condition | name | Multi-table; **conditions, not `amenity.status`**; FE relabels Dirty → "Need Maintenance" (`O/lib/roomStatus.ts:121-126`) |
| Invoice button | :639-651 | — | — | — | — | — | Hardcoded, disabled |
| Room View: Current in House | `O/pages/RoomView.tsx:89` | `GET /stays?is_in_house=true&page_size=1` | `sv/stay.py list_stays` | COUNT IN_HOUSE | stay | actual_* | Aggregated |
| Room View: Expected Check-In / Check-Out | :90-91, :45-56 | `GET /stays?expected_checkin_from/to` (and checkout) | `sv/stay.py:194-201` | COUNT in today's window, **any status** | stay | expected_checkin_time / expected_checkout_time | Aggregated; includes cancelled and checked-out stays |
| Room View: Current Status % / End of Day | :44, :59-78, :92, :100-103 | `GET /occupancy?page_size=100[&floor_id]` | `sv/occupancy.py list_occupancy` | — | amenity_status | amenity_status_name | **FE-calculated over one page**: `total = items.length`, `Math.round(occupied/total*100)` (:66-76), all categories |
| Room View: Start of Day / Realized Check-In / Check-Out | :97-99 | — | — | — | — | — | Hardcoded "-" |
| Room detail: Category, Building, Floor, Room Allocations | `O/components/RoomDetailsModal.tsx:261-273` | `GET /occupancy/{amenity_id}` (`ep/occupancy.py:114`) | `sv/occupancy.py get_occupancy` (:267) | + correlated COUNT(room_allocation) | amenity_type, property, room_allocation | name, property_name, count | Multi-table; "Room Allocations" counts all history |
| Room detail: Expected/Actual Check-In, Expected Check-Out, Primary Guest, Stay Ref, Stay Status, Guests | :279-353 | same | `_current_stays` | IN_HOUSE | stay, app_user | expected_*/actual_checkin_time, internal_stay_ref_number, status, no_of_guests | Multi-table |
| Room detail: Actual Check-Out | :309 | — | — | — | — | — | Hardcoded "-" |
| Room detail: Additional Guest | `O/components/RoomDetailsPanel.tsx:165` | same | — | — | stay | no_of_guests | FE: `Math.max(no_of_guests - 1, 0)` |
| Room detail: device table | `RoomDetailsModal.tsx:396-422` | `GET /devices?amenity_id=` | `sv/device.py list_devices` | device ⋈ device_type ⋈ amenity | device | device_uid, device_config_status, health_status, installed_on | Direct; includes decommissioned devices |
| Room detail: service request cards | :493-530 | `GET /service-requests?amenity_id=&page_size=100` | `sv/service.py list_service_requests` | see §3.3 | service_request, service_status, service_category, service_type, department, app_user | … | Multi-table |
| Room Temperature / Air Quality | `O/components/RoomPowerEnergy.tsx:183-186,269-280` | `GET /device-stats?param_name=room_temperature\|air_quality&amenity_id=&page_size=100` (`ep/telemetry.py:142`) | `sv/telemetry.py list_device_stats` (:145) | device_stat ⋈ device ⋈ device_param WHERE device.amenity_id = ? ORDER BY timestamp DESC | device_stat, device_param | device_param_value (varchar → Number), unit | FE picks the newest reading from ≤100 rows |
| Power Consumed / Energy Consumed | :181-182, :109-114, :287-292 | `…param_name=active_power\|active_energy` | same | same | device_stat | device_param_value | FE: **sum of each device's latest value**; "KW" re-cased to "kW" |
| Recorded Consumption / Readings Recorded | :187-190, :295-317 | `GET /energy-stats/summary?group_by=amenity&amenity_id=` | `sv/energy.py energy_summary` | SUM / COUNT GROUP BY amenity, **no date bound** | energy_stat | energy_consumed | Aggregated, all time |

### 3.3 Source-tracing matrix: Bookings, Services, Maintenance, Job Orders, Reports

| UI data | Frontend component | API | Backend service | Query | Table | Column | Nature |
|---|---|---|---|---|---|---|---|
| Bookings: Name | `frontend/src/features/bookings/pages/Bookings.tsx:171` | `GET /stays?page=1&page_size=100` (`ep/stays.py:91`) | `sv/stay.py list_stays` (:141) | stay ⟕ app_user (booker) + COUNT subqueries | app_user | first_name + last_name | Backend-concatenated |
| Bookings: Occupants / No. of Rooms / Booking Date / Doc approval | :175, :179, :187-188 | same | same | — | stay | no_of_guests, no_of_rooms, created_on, document_approval_status | Direct |
| Bookings: Mobile / Email / Room No / Room Type | :173-178 | — | — | — | — | — | **Hardcoded `"-"` / `""`** |
| Bookings: "Showing X of Z" | :258-263 | — | — | — | — | — | FE count over ≤100 rows |
| Service Tracking: type card label / count | `frontend/src/features/services/pages/ServiceTracking.tsx:144-151` | `GET /service-types`, `GET /service-requests?page_size=100` | `sv/service.py list_service_types` (:60), `list_service_requests` (:295) | service_request ⋈ service_type ⟕ category, status, amenity, stay, department, app_user ×2 | service_type, service_request | name, service_type | FE: `allRequests.filter(r => r.service_type === type.id).length` over ≤100 rows |
| Service Tracking: donut Completed / "Pending" | :158-165 | same | same | — | service_status | name | FE: `completed/total*100`; **"Pending" = everything not Completed, including Canceled** |
| Service Tracking: Service Item | :180 | — | — | — | — | — | **Hardcoded `"Items"`** |
| Service Tracking: Items modal | :914-928 | — | — | — | — | — | **Mocked** (Wipes / Trimmer / Soap) |
| Service Tracking: Under Maintenance | :195 | — | — | — | — | — | Hardcoded `"-"` |
| Service Tracking: Room / Category / Department / Assigned To / Status / Date / To Date / End Time | :177-198 | same | same | — | amenity, service_category, department, app_user, service_status, service_request | name, category_name, department_name, emp_id + name, name, created_on, expected_date, completed_on | Multi-table; "From Date / Start Time" shows **created_on** |
| Status dialog options | `…/components/ServiceRequestActionsDialog.tsx:51-56,105-125` | `GET /service-statuses`, `GET /users?is_staff=1` | `sv/service.py list_service_statuses` (:91), `sv/access.py list_users` | — | service_status, app_user | id, name (live id 3 = "In Progress") | Direct |
| Tickets: Quantity | `frontend/src/features/tickets/pages/Tickets.tsx:104` | — | — | — | (`service_request_item.quantity` exists but is not fetched) | — | Hardcoded `"-"` |
| Tickets: Department picker | :76-85 | `GET /users?is_staff=1&page_size=100` | `sv/access.py list_users` | — | app_user ⋈ department | department_id, department_name | FE-derived distinct over the first 100 staff; `/departments` is not used |
| Service Planning rows | `frontend/src/features/services/pages/ServicePlanning.tsx:84-93,211-224` | `GET /maintenance-requests?request_type=&page_size=100` (`ep/maintenance.py:114`) | `sv/maintenance.py list_maintenance_requests` (:133) | maintenance_request ⟕ department, service_category → service_type, service_status; WHERE status = 1; links batch-loaded | maintenance_request, _amenity, _assignee, amenity, app_user | dates / times, name, names, under_maintenance | Multi-table; **plan status is never shown** |
| Service Planning edit modal | :1329-1470 | — | — | — | — | — | **Mocked** (Submit only closes) |
| Job Orders rows | `frontend/src/features/config/pages/JobOrder.tsx:690-710` | `GET /job-orders?page_size=100` (`ep/job_orders.py:124`) | `sv/job_order.py list_job_orders` (:78) | job_order ⟕ app_user; WHERE status IS DISTINCT FROM 0; rooms / devices batch-loaded | job_order, job_order_amenity, job_order_device | description, order_reference, type_of_work, work_commence, estimated_completion_date | Multi-table; Job ID = FE `id.slice(0,8)` |
| Reports rows / "N rows" | `frontend/src/features/reports/pages/Reports.tsx:459` | `GET /reports/{key}` (`ep/reports.py:202`) | `sv/reports.py run_report` (:525), reusing the list services | per key | occupancy / employee / room-status / booking / ticket / housekeeping / sanitization / alert / energy | declared columns | Backend; the only screen that uses the API `total` |

### 3.4 Classification summary

| Nature | Examples |
|---|---|
| **Directly from DB** | Room/type/floor names, stay references and times, service request fields, device UID / config / health, job order fields |
| **Calculated in backend** | Booker / assignee / actor names (Python concatenation); Caleido %; energy totals and unit; `is_in_house` / `is_checked_in` |
| **Calculated in frontend** | Room View %, Service Tracking card counts and donut %, Occupancy Statistics centre %, Energy "average per reading", Additional Guest, Overdue, room power sum, Job ID |
| **Aggregated** | All KPI tiles (COUNT via `page_size=1`), building floor/room counts, energy summaries, `allocation_count` |
| **Cached** | All hooks 30 s (`H:54`); report definitions 5 min (`H:348`); count keys not invalidated on writes |
| **Hardcoded** | See §3.6 |
| **Mocked** | Service Tracking items modal; Service Planning edit modal; dead Service Tracking status modal (:803-891, unreachable) |
| **Multi-table derived** | "Rooms in house" (amenity + room_allocation + stay), occupancy grid, service request rows, activity feed |

### 3.5 Frontend calculations to understand from a DB/business perspective
1. **Two meanings of "occupied".** `?status=<Occupied>` reads `amenity.status`; `?is_occupied=true` reads stay timestamps. Live: **3 amenities flagged Occupied vs 1 room with a guest in house**.
2. **Room denominators include non-room spaces.** Live: 27 amenities vs 24 guest rooms. This affects "of N rooms", the Occupancy Statistics total, building room counts and Room View.
3. **One-page counts** (`items.length` of ≤100 rows): Room View %, Service Tracking cards and donut, and the "Showing X of Z" footers on Bookings, Tickets, Service Planning and Job Orders. These become wrong above 100 rows.
4. **Service donut "Pending"** includes Assigned, In Progress and Canceled.
5. **Room power** = sum of each device's latest reading from ≤100 newest rows. Decommissioned devices are included (Item 2).
6. **Energy day buckets are UTC** (`hour // 24`) while the chart window is local midnight; the Caleido "Today" date comes from `toISOString()` (UTC).
7. **Expected check-in/out counts** include every stay status.

### 3.6 Hardcoded values and UI values without an obvious DB source

| Screen | Value | Note |
|---|---|---|
| Bookings | Mobile Number, Email, Room No, Room Type, Room Category (dialog) | `Bookings.tsx:173-178`; data exists in `app_user` / `room_allocation` but is not fetched |
| Service Tracking | "Items", Items modal rows, "Under Maintenance" | :180, :914-928, :195 |
| Tickets | Quantity | :104 |
| Service Planning | Edit modal fields | :1329-1470 |
| Occupancy / Room View / detail | Invoice (disabled), Start of Day, Realized Check-In/Out, Actual Check-Out | `Occupancy.tsx:639-651`; `RoomView.tsx:97-99`; `RoomDetailsModal.tsx:309` |
| Dashboard | Title / tagline; KPI detail sentences; "(no unit)"; Caleido labels; chart title "Average …"; StatusSection legend (constant list, not from `amenity_status`) | `Dashboard.tsx:70,73`; `DashboardKPIs.tsx:271,384,407`; `CaleidoAtWork.tsx:60-65`; `EnergyConsumptionChart.tsx:127`; `StatusSection.tsx:325-329` |
| Constants | `VALUE_ALERT_ACTIVE = 0`; status / condition colours; Dirty → "Need Maintenance" | `types.ts:105`; `O/lib/roomStatus.ts`; `O/lib/serviceStatus.ts` |

### 3.7 API fields whose DB source cannot be traced, or is only indirect
- **Housekeeping report "Type" filter:** `options_from = "maintenance-types"` (`sv/reports.py:428`). **No such route exists** in the backend or frontend, so the source cannot be traced and the dropdown cannot load.
- **Energy unit:** from `device_param` configuration, not from the reading. `energy_stat` cannot be joined to `device` (live: 0 of 72 rows match).
- **Tables written only by seeds:** no application code writes `energy_stat`, `daily_dual_data_point`, `device_alert`, `value_alert`, `device_stat` or `activity`. Their writer (external IoT ingester?) **cannot be verified from the available repository**.
- **Booking report source label** says `stay_occupant`; the table is `stay_user`.
- **`current_stay.booker.emp_id`** on occupancy is always null (`sv/occupancy.py:60`).

### 3.8 Queried or returned but not displayed (main examples)
- **`/occupancy`:** `status` id, `is_dnd`, `power_save_mode`, `facility_id`. The detail endpoint also returns `occupants[]` and `device_count`.
- **`/stays`:** external_stay_ref_number, request_source, gst, comments, checkout_initiated_by, expected_checkin_time, actual_checkout_time (mapped but not rendered).
- **`/service-requests`:** requester, promo_code_id, net_amount, total_tax, total_amount, stay_ref_number. Service Tracking fetches `/service-statuses` without using the items.
- **`/maintenance-requests`:** status_name, is_recurring, recurrence, status_reason, completed_on.
- **`/job-orders`:** assignee, job_order_status, completed_on.
- **`/devices`:** appliance_name, part_number, model, manufacturer, firmware. **`/energy-stats/summary`** buckets are fetched and discarded by the KPI tile.

### 3.9 Both directions (UI → API → backend → DB)

| UI action | API | Service | Written |
|---|---|---|---|
| Occupancy → Check-Out (`CheckOutConfirmDialog.tsx:50`) | `POST /stays/{id}/check-out` (`ep/stays_write.py:156`) | `SW.check_out` (:255) | `stay.actual_checkout_time`, `status='checked out'`, `checkout_initiated_by`, `modified_by` (:273-276); `amenity.status` → Available for each allocation (:277-279). **Not written:** room_allocation.status, amenity_condition_status, activity |
| Room conditions (`RoomConditionsDialog.tsx`) | `PUT /occupancy/{id}/conditions` (`ep/stays_write.py:379`) | `SW.set_room_conditions` (:605) | Deletes unticked `amenity_condition_status` rows (:630-632), inserts new ones with status 1 (:633-638). An existing row with status ≠ 1 is neither reactivated nor re-inserted. |
| Reassign room | `PATCH /room-allocations/{id}` | `SW.reallocate_room` (:428) | Item 1 |
| Create booking (`Bookings.tsx:319-349`) | `POST /users`, then `POST /stays` | `sv/access_write.py create_user` (:64); `SW.create_stay` (:169) | app_user; then stay, room_allocation, amenity.status → Allotted. **Two non-atomic calls** |
| Update service request (`ServiceRequestActionsDialog.tsx`) | `PATCH /service-requests/{id}` / `POST …/cancel` | `sv/services_write.py update_service_request` (:179) / `cancel_service_request` (:236) | status, assigned_to, status_reason, completed_on, updated_by; cancel → status 5 |
| Create maintenance request (`ServicePlanning.tsx:322-380`) | `POST /maintenance-requests` (`ep/maintenance.py:182`) | `sv/maintenance_write.py create_maintenance_request` (:203) | maintenance_request + _amenity + _assignee + _recurrence. `under_maintenance` does **not** change `amenity.status` |
| Create job order (`JobOrder.tsx:238-272`) | `POST /job-orders` (`ep/job_orders.py:176`) | `sv/job_order_write.py create_job_order` (:121) | job_order, job_order_amenity, job_order_device. No device row changes |

### Gap (Item 3)
- Most values are traceable, but several are not backed by the database at all (§3.6).
- Some are computed over a truncated page (§3.5 item 3).
- Some have two competing sources ("occupied").
- A report filter points at a route that does not exist.
- A group of dashboard tables has no writer in this repository.

---

## Final comparison

| P1 item | Current implementation | Expected requirement | Gap | Evidence | Impact | Recommended investigation |
|---|---|---|---|---|---|---|
| **1. Room reassignment** | `PATCH /room-allocations/{id}` overwrites `room_allocation.room_id` / `package_id` in place; old room → Available; no end date or state; `status` always 1 | Close the existing assignment (end date/state), then create a new active assignment record, keeping history | No close, no new row, no history, no validity columns; `stay_user.room_id` not moved; docstrings claim the opposite | `SW:428-466` (:454-456); `models/stay.py:130-157`; `backend/tests/test_stay_write_api.py:382-404`; `ep/stays.py:199-200` | Room history for a stay is lost; no audit or attribution basis | Define "closed" (timestamp and/or status); audit readers of `room_allocation`; decide `stay_user` behaviour |
| **2. Sensor ↔ room mapping** | Direct FK `device.amenity_id` (NOT NULL); room has many devices; hub via `parent_device_id`; no mapping table | Stable room identity with a manageable, replaceable sensor mapping | No mapping validity or history; decommission does not end the link; time-series has no room copy (moving re-attributes history); name-keyed tables not linked to `device` | `models/device.py`; `DW:101-139`; `sv/telemetry.py _stat_stmt`; `sv/occupancy.py:299-301`; `RoomPowerEnergy.tsx:109-114`; live queries | Replaced sensors keep counting toward the room; history attribution unreliable; energy/limits cannot follow a sensor | Confirm the replacement business rule; how the external ingester identifies devices; naming convention of `device_name` keys |
| **3. DB source tracing** | Traceable chain table → service `select()` → route → hook → component for all main values; KPIs are backend COUNTs; several FE calculations and hardcoded values | Every important UI value traceable to its DB source | Hardcoded / mocked values; one-page FE counts; two "occupied" sources; non-room denominators; missing `maintenance-types` route; seed-only tables with no writer | §3.1–3.9 | Some displayed figures are misleading or not data-backed | Confirm intended KPI definitions; locate the ingester; review hardcoded fields with product |

---

## Final actionable findings

### A. Confirmed implementation
- **A1.** Reassignment runs in one transaction with the swap of room states: old → Available, new → Occupied/Allotted (`SW:428-466`, `sv/writes.py:53-74`).
- **A2.** A room held by another live stay cannot be targeted (`SW._assert_room_free:142-156`). Covered by a test (:407).
- **A3.** Sensor → room mapping is a mandatory FK `device.amenity_id` → `amenity.id`. Each device has one room and a room can have many devices and types, with a hub/child hierarchy (`parent_device_id`). The physical identity `device_uid` is UNIQUE.
- **A4.** Event tables (`device_alert`, `value_alert`, `device_incident`, `sensor_operation_stat`) store the room at event time, and live copies are consistent (0 mismatches).
- **A5.** All main UI values follow the model → service → route → hook → component chain; KPIs are backend COUNTs (§3.1–3.3).

### B. Confirmed gaps
- **B1.** Reassignment overwrites the allocation. There is no close or new record, and history is lost (`SW:454-456`; test :399-401).
- **B2.** `room_allocation` has no start/end columns and `status` is never changed from 1 (`SW:91`).
- **B3.** `stay_user.room_id` is not updated on reassignment.
- **B4.** Decommissioning a device does not end its room link. It is still counted (`sv/occupancy.py:299-301`) and included in room telemetry (`sv/telemetry.py` has no config-status filter).
- **B5.** Moving a device (`PATCH /devices/{id}` `amenity_id`) re-attributes its time-series history. `device_stat` has no room column.
- **B6.** Several UI values are hardcoded or mocked, and several counts are computed over a single page of 100 rows (§3.5–3.6).
- **B7.** The Housekeeping report filter `maintenance-types` has no route (`sv/reports.py:428`).
- **B8.** Dashboard count queries are not invalidated after writes (`M:20-30`, `H:111-115`).

### C. Missing business rules
- **C1.** The definition of "closing" a room assignment (end timestamp, end status, reason).
- **C2.** Whether occupants (`stay_user`) move with a reassignment.
- **C3.** The sensor replacement rule: one active device per type per room? must replacements be linked (B replaced A)?
- **C4.** Which "occupied" is authoritative: `amenity.status` or the stay timestamps.
- **C5.** Whether room KPIs count guest rooms only.

### D. Missing database relationships
- **D1.** There is no assignment history or validity for room allocations.
- **D2.** There is no device ↔ room mapping history or validity; the mapping is a single column.
- **D3.** `energy_stat.device_name`, `value_alert_limit_config.device_name` and `other_device.device_name` have no FK to `device`. Live values do not match `device.device_name`.
- **D4.** `device_stat`, `device_health_stat` and `battery_life_stat` carry no room copy.

### E. Missing validation
- **E1.** `reallocate_room` does not check whether the target room is already allocated to the same stay; `_allocate` does (`SW:379-386` vs `:449-456`).
- **E2.** The UI picks the allocation by room name with a `rows[0]` fallback (`ReallocateRoomDialog.tsx:120`).
- **E3.** No rule keeps a child device in the same room as its parent hub (`DW:102-116`). Live data is consistent.
- **E4.** No uniqueness rule for active devices per type per room.
- **E5.** No DB-level guard against concurrent double allocation (no lock or exclusion constraint).

### F. Needs business confirmation
C1–C5 above; plus the intended meanings of `room_allocation.status` and `device.installed_on` on replacement.

### G. Needs backend investigation
- **G1.** Which readers depend on the current one-row-per-allocation semantics (`allocation_count`, `_current_stays`, `stay_room_allocations`, reports).
- **G2.** How room telemetry and device counts should treat `decommissioned` / `missing` devices.
- **G3.** The missing `maintenance-types` options route.
- **G4.** Cache invalidation of `count` keys after writes.

### H. Needs database investigation
- **H1.** The writer of the seed-only telemetry, alert and activity tables (external ingester), and which device identity it uses (`device_uid` vs name).
- **H2.** The `device_name` naming conventions across `device`, `energy_stat` and `value_alert_limit_config`.
- **H3.** Existing `amenity.status` values that disagree with stays. Live: room 201 Occupied and room 108 Allotted, each with no allocation.

---

## Final summary

1. **How does room reassignment currently work?** The Occupancy page "Reassign" button calls `PATCH /api/v1/room-allocations/{id}` → `stays_write.reallocate_room`. It overwrites the existing `room_allocation` row's `room_id` and `package_id`, sets the old room Available and the new room Occupied/Allotted, all in one transaction.
2. **Does it preserve previous assignment history?** **No.** The previous room is overwritten, and there are no start/end columns or history table. The project's test asserts the overwrite, while the docstrings wrongly claim a new row is written.
3. **How is sensor-to-room mapping maintained?** Through a single mandatory column, `device.amenity_id` (FK → `amenity`), plus `parent_device_id` for the hub hierarchy. There is no mapping table.
4. **What happens when a sensor is replaced?** There is no replacement operation, and no UI for device lifecycle. Via the API, the new device is registered to the room and the old one decommissioned. The old device keeps its room link and is still counted and included in room telemetry. Editing a device's room in place instead rewrites its history attribution.
5. **Can sensor history and room history be preserved?** Per-device readings are preserved (keyed by `device_id`), and event tables keep the room at event time. Time-series room attribution and the mapping history are **not** preserved. Room-assignment history is **not** preserved.
6. **Can every important UI value be traced to its DB source?** Most can, end to end (§3.1–3.3). The exceptions are hardcoded or mocked fields, values computed in the browser over a 100-row page, a report filter with no backing route, and dashboard tables whose writer is outside this repository.
7. **Confirmed gaps:** B1–B8.
8. **Requires business clarification:** C1–C5 (closing semantics, occupant movement, sensor replacement rule, authoritative occupancy source, room KPI denominator).
9. **Requires backend/database investigation:** G1–G4 and H1–H3.
