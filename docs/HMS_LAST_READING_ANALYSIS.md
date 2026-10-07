# HMS Analysis Report: "Last Reading"

| | |
|---|---|
| **System** | ACX Platform — Hospitality Management System (HMS) |
| **Repository** | `ACX-Platform`, branch `develop` @ `f97f582` |
| **Database** | PostgreSQL 18.6, `hms_db` / `public`, Alembic head `7c4e2b9a1d53`, session TimeZone `Asia/Calcutta` |
| **Date** | 2026-09-26 |
| **Type** | Analysis only. No code, schema, data or UI was changed. Database access was read-only (`SET TRANSACTION READ ONLY`). |

---

## 1. Scope

**Analysed:** the **"Last Reading"** column in the per-device table of **Occupancy → Room details → "Environment & Utilities" tab**. It is rendered by `frontend/src/features/occupancy/components/RoomPowerEnergy.tsx:349-351` (header) and `:367-369` (cell).

**Included because they share the name or the data:**
- **"Readings Recorded"** (`RoomPowerEnergy.tsx:307-317`). This field was itself labelled **"Last Reading"** between 16 and 25 September 2026 (§8.5).
- The room totals rendered beside the table (Room Temperature, Air Quality, Power Consumed, Energy Consumed, Recorded Consumption). They come from the same rows and carry no time information.
- The other "latest reading" display, on the Dashboard room panel (`frontend/src/features/occupancy/components/RoomDetailsPanel.tsx`, rendered by `frontend/src/features/dashboard/pages/Dashboard.tsx`).
- The backend's other "last" concepts that exist but are not used by this UI: `last_reported_on`, `device_current_stat.captured_at` and `device_stat.created_on`.

**Out of scope:** redesign, alternative wording and fixes. None are proposed as approved.

---

## 2. Current architecture

```
device_stat (EAV time-series, one row per device × parameter × timestamp)
  ⋈ device ⋈ device_type ⋈ device_param ⟕ amenity ⟕ property_chain ⟕ property×2
  → sv/telemetry.py list_device_stats (_stat_stmt, ORDER BY timestamp DESC, id DESC)
  → GET /api/v1/device-stats?param_name=active_power|active_energy&amenity_id=<room>&page=1&page_size=100
  → frontend useDeviceStats (hooks.ts:284)                      [React Query, 30 s staleTime]
  → RoomPowerEnergy.tsx: latestPerDevice() → meteredDevices → "Last Reading" = newest of two timestamps
  → new Date(value).toLocaleString()
```

There is no repository/DAO layer: the service builds the SQLAlchemy `select()` directly. There is no dedicated "last reading" column, view or endpoint. **The value is assembled in the browser.**

---

## 3. Database tables

| Table | Purpose | PK | Important FKs | Used by "Last Reading"? | Role |
|---|---|---|---|---|---|
| `device_stat` | Time-series telemetry, entity-attribute-value (EAV) style: one value per device, parameter and time | `id` bigint | `device_id` → device; `device_param_id` → device_param | **Yes: source of the timestamp** (`timestamp`) and of the displayed values (`device_param_value`) | Primary source |
| `device_param` | Parameter definitions per device type (name, data type, unit) | `id` int | `device_type` → device_type | Yes: filter `param_name IN ('active_power','active_energy')` and `unit` | Reference |
| `device` | Physical device installed in a room | `id` uuid | `amenity_id` → amenity (NOT NULL); `device_type` → device_type; `parent_device_id` → device | Yes: scopes rows to the room (`device.amenity_id`) and supplies the row label (`device_name` / `device_uid`) | Master |
| `device_type` | Device family (Intellihub, AirQ, Mikos, Kleio) | `id` int2 | — | Joined (`device_type_name` returned, not displayed in this table) | Reference |
| `amenity` | The room | `id` uuid | `property_chain_id` → property_chain | Room filter via `device.amenity_id` | Master |
| `energy_stat` | Hourly energy per room / device-name | (device_name, facility_id, amenity_id, hour) | `amenity_id` → amenity; `facility_id` → facility | **No.** Feeds "Readings Recorded" and "Recorded Consumption", not the column | Aggregation source (adjacent fields) |
| `device_current_stat` | Latest JSONB snapshot per device (`health`, `params`, `captured_at`) | `id` uuid | `device_id` → device | **No.** Not read by any page (`useDeviceCurrentStats`, `hooks.ts:286`, has no caller) | Unused alternative |
| `device_health_stat` | Heartbeat / health log | `id` bigint | `device_id` → device | **No.** Backs `last_reported_on` in `GET /devices/{id}/health`, which the UI does not call | Unused alternative |

**Column facts (live catalog):**
- `device_stat.timestamp` is `timestamp with time zone`, NOT NULL.
- `device_stat.device_param_value` is `varchar`.
- `device_stat.created_on` is a timestamptz audit column.

The response schema describes `timestamp` as **"When the device took the reading"** (`backend/app/schemas/telemetry.py:117`).

---

## 4. Table relationships

Confirmed by declared foreign keys:

```
amenity (room)
  ↑ device.amenity_id (NOT NULL)
device ──→ device_type
  ↑ device_stat.device_id
device_stat ──→ device_param ──→ device_type

amenity ← energy_stat.amenity_id        (energy_stat has NO FK to device; keyed by device_name text)
device  ← device_current_stat.device_id
device  ← device_health_stat.device_id
```

- `device_stat` has **no room column**. The room of a reading is always the device's **current** `amenity_id` (`backend/app/services/telemetry.py:_stat_stmt`: `outerjoin(Amenity, Amenity.id == Device.amenity_id)`, filter `Device.amenity_id == amenity_id`, :138 / :174).
- In live data, 0 of 72 `energy_stat.device_name` values (e.g. `101-mik`) match any `device.device_name` / `device_uid`. The "Readings Recorded" count therefore cannot be linked to the devices listed in the table.

---

## 5. Backend flow

| Step | Location | Detail |
|---|---|---|
| Route | `GET /api/v1/device-stats`: `backend/app/api/v1/endpoints/telemetry.py:142` | Gated on module `caleido_network` (read) |
| Service | `backend/app/services/telemetry.py` `list_device_stats` (:145) | `_stat_stmt()` (:109) selects `DeviceStat.id, device_id, Device.device_uid, Device.device_name, DeviceType.name, Device.amenity_id, …, DeviceParam.param_name, data_type, unit, DeviceStat.device_param_value, DeviceStat.timestamp, is_other_device, DeviceStat.created_on` |
| Ordering | `list_device_stats` | `ORDER BY device_stat.timestamp DESC, device_stat.id DESC` |
| Filters used by this screen | same | `DeviceParam.param_name == :param_name`; `Device.amenity_id == :amenity_id` (:174). **No `device_config_status` filter**, so decommissioned or misconfigured devices are included. |
| Paging | route | `page=1`, `page_size=100` (the cap is `MAX_PAGE_SIZE`) |
| Response | `DeviceStatRead` (`backend/app/schemas/telemetry.py:86-119`) | `timestamp` (datetime, serialised ISO-8601 with offset), `created_on`, `device_param_value` (string as stored), `unit` |

**Adjacent field ("Readings Recorded"):**
- **Chain:** `GET /api/v1/energy-stats/summary?group_by=amenity&amenity_id=<room>` (`ep/energy.py:84`) → `sv/energy.py energy_summary` (:172).
- **Query:** `SUM(energy_consumed)` and `COUNT(*) AS reading_count` over `energy_stat ⋈ amenity`, grouped by amenity (:214, :230-253). No date bound is sent, so this is all time.

---

## 6. Frontend flow

| Step | Location | Detail |
|---|---|---|
| Page | `frontend/src/features/occupancy/pages/Occupancy.tsx` → `RoomDetailsModal.tsx` | Tab "Environment & Utilities" (`RoomDetailsModal.tsx:230-232`, panel :363) mounts `RoomPowerEnergy` |
| Queries | `RoomPowerEnergy.tsx:176-186` | Four `useDeviceStats` calls with `{page:1, page_size:100, param_name, amenity_id}` for `active_power`, `active_energy`, `room_temperature`, `air_quality`. Enabled only with the `caleido_network` read grant (:167, :173) |
| Latest per device | `latestPerDevice` (:80-96) | Walks the rows in API order and keeps the **first** row per `device_id`, which is the newest because of `timestamp DESC`. Skips null or non-numeric values. Stores `{value, unit, timestamp}` |
| Row assembly | `meteredDevices` (:204-223) | One row per device that has a power **or** energy reading. `lastSeen = [load?.timestamp, consumption?.timestamp].filter(Boolean).sort().pop()`, i.e. the **later of the two timestamps**, chosen by string sort |
| Render | :349-351, :367-369 | Header **"Last Reading"**; cell `formatDateTime(row.lastSeen)` = `new Date(value).toLocaleString()` (:153-154), or `-` if absent |
| Sibling columns | :346-348, :358-366 | "Device", "Power Consumed" (latest `active_power` value + unit), "Energy Consumed" (latest `active_energy` value + unit) |
| Room totals (no time shown) | :267-302 | Temperature / Air Quality = newest single reading (`latest`, :124-130); Power / Energy Consumed = **sum of each device's latest value** (`total`, :109-114) |
| "Readings Recorded" | :307-317 | `"${reading_count} hourly readings"` from the energy summary; tooltip "Number of hourly energy_stat readings summed into Recorded Consumption." |

---

## 7. End-to-end process

1. A user opens a room on the Occupancy page and selects **Environment & Utilities**.
2. The browser requests the newest ≤100 `device_stat` rows for `active_power` and for `active_energy`, restricted to devices whose **current** `amenity_id` is this room.
3. The backend returns rows ordered newest first. Each row carries the stored value (string), the parameter's unit and the reading's `timestamp`.
4. For each device, the browser keeps its newest power row and its newest energy row.
5. Each device becomes one table row. **"Last Reading" is the later of those two rows' timestamps**, formatted in the viewer's browser locale and time zone.
6. Nothing is written. The data is cached for 30 s (`hooks.ts:54`).

**What "Last Reading" currently represents:** a **timestamp**, the time the device took its most recent power or energy reading, taken from `device_stat.timestamp`. It is **not** a reading value, not a status, not an age, not the ingestion time (`created_on`), not the heartbeat (`last_reported_on`) and not the snapshot time (`captured_at`).

**Live example** (read-only query, 2026-09-26 19:04 IST):

| Room | Device | Config status | Power (latest) | Energy (latest) | power `timestamp` | energy `timestamp` | "Last Reading" would show |
|---|---|---|---|---|---|---|---|
| 101 | DEV101HUB | commissioned | 0.436 | 41.760 | 2026-08-17 16:30 +05:30 | 2026-08-17 16:30 +05:30 | 17/08/2026 16:30 (browser-formatted) |
| 101 | DEV101MIK | commissioned | 0.114 | 7.270 | same | same | same |
| 205 | DEV205HUB / DEV205MIK | commissioned | 0.436 / 0.114 | 41.760 / 7.270 | same | same | same |
| REST01 | DEVRESTMIK | bad_configuration | 0.114 | 7.270 | same | same | same |
| 104, 106 | — | — | no power/energy rows | — | — | — | table empty ("No metered readings recorded for this room") |

- **Overall:** `device_stat` holds 504 rows across only 12 distinct timestamps (2026-08-17 05:30 → 16:30 IST); the newest reading is **40 days old**.
- **Lag:** `created_on − timestamp` is 0 for every row, so ingestion time and reading time are identical in the seeded data.

---

## 8. Findings

### 8.1 Confirmed behaviour
- **C1.** "Last Reading" is a timestamp derived in the browser as `max(timestamp of the device's newest active_power row, timestamp of its newest active_energy row)` (`RoomPowerEnergy.tsx:216-219`).
- **C2.** The source column is `device_stat.timestamp`, documented as the time the device took the reading (`schemas/telemetry.py:117`).
- **C3.** It is formatted with `toLocaleString()` in the viewer's locale and time zone, with no zone label (`RoomPowerEnergy.tsx:153-154`).
- **C4.** Only devices whose **current** `amenity_id` is the room are included, and decommissioned or misconfigured devices are **not** excluded (`sv/telemetry.py:174`; live: REST01's `bad_configuration` device appears).
- **C5.** The candidate rows are the newest **100 per parameter per room** (`RoomPowerEnergy.tsx:49,178`).

### 8.2 Data / model observations
- **D1.** No stored "last reading" field exists. Three other "latest" sources exist and are not used by this screen:
  - `device_current_stat.device_stats.captured_at` (JSONB; live keys `health`, `params`, `captured_at`).
  - `last_reported_on` in `GET /devices/{id}/health`, derived as `MAX(device_health_stat.created_on)` (`sv/device.py:295`, `ep/devices.py:204-205`).
  - `device_stat.created_on` (returned by the API, not displayed).
- **D2.** `device_stat` has no room column. After a device is moved, its whole history is attributed to its new room.
- **D3.** `device_param` defines `active_power` and `active_energy` **twice** each, for device types 1 (Intellihub) and 3 (Mikos). In room 101 both the hub and the Mikos meter report both parameters. Whether the hub's figure is an aggregate of its children is **not confirmed from the available source** (relevant to the room totals, not to the timestamp itself).
- **D4.** The "Readings Recorded" count comes from `energy_stat`, which cannot be joined to `device`. Room 106 has 24 `energy_stat` rows and zero `device_stat` power/energy rows. REST01 is the reverse.

### 8.3 UI observations
- **U1.** The column sits beside two **value** columns ("Power Consumed", "Energy Consumed"). The header does not say it is a time. The cell content (a date/time) makes it recognisable once seen, but the header alone reads like "the value of the last reading".
- **U2.** The row shows **two values but one timestamp**. If a device's newest power and newest energy readings were taken at different times, the older value's time is not shown. In live data both timestamps are identical, so the case is not visible today.
- **U3.** There is **no age or staleness context**: an absolute date/time only, and no "x days ago". The room totals above the table (Power Consumed, Energy Consumed, Temperature, Air Quality) show **no time at all**. Live, they present 40-day-old readings with nothing on screen saying so except this column.
- **U4.** Temperature and Air Quality readings have no per-reading time anywhere on this tab, because the per-device table lists only metered (power/energy) devices.
- **U5.** The Dashboard room panel (`RoomDetailsPanel.tsx:84-101`, rendered :195-218) shows each device's latest value per parameter with **no timestamp**. It fetches all parameters in one 100-row page (`useDeviceStats`, :35).
- **U6.** The "Recorded Consumption" tooltip and comments say the API returns `energy_unit: null` (`RoomPowerEnergy.tsx:13-16, 238, 297-300`). The backend now resolves it from `device_param` (`sv/energy.py active_energy_unit`, :41-65), and it is live `kWh`.

### 8.4 Integration observations
- **I1.** The column depends on `caleido_network` read access. Without it, the table is empty and a note is shown (`RoomPowerEnergy.tsx:321-326`). "Readings Recorded" depends separately on `reports` read access (:327-332).
- **I2.** Nothing in this repository writes `device_stat` (only `backend/seeds/steps/telemetry.py`). How live readings are ingested, and so how current "Last Reading" can ever be, is **not confirmed from the available source**.
- **I3.** Results are cached 30 s, and no mutation invalidates `device-stats`. That's appropriate for read-only telemetry, but reopening the dialog within 30 s shows cached times.

### 8.5 Ambiguities
- **A1. Two meanings of the same label over time** (git history):

  | Commit | Date | Change |
  |---|---|---|
  | `cbd1f12` | 2026-09-11 | Introduced the table column **"Last Reading"** (timestamp) |
  | `a2d587b` | 2026-09-16 | Renamed the count field "Hourly Readings" → **"Last Reading"**, displaying `reading_count` (e.g. "24") |
  | `4e15fa6` | 2026-09-25 | Renamed that field to **"Readings Recorded"**. The code comment says the old label "made a bare '24' read like a timestamp or an age" (`RoomPowerEnergy.tsx:303-306`) |

  Any ticket, screenshot or feedback about "Last Reading" dated 16–25 Sep may refer to the **count**, not the timestamp.
- **A2.** "Last" is relative to the newest ≤100 rows fetched per parameter, not to all stored data. With more than 100 rows per parameter in a room, a device whose newest reading falls outside that page shows an older time or no row at all. Live maximum is 24 rows per room and parameter, so there is no effect today.
- **A3.** The later of the two timestamps is chosen by **string sort** (`.sort().pop()`), and `latest()` compares strings (:127). This is correct while every timestamp in a response has the same offset (the session zone is `Asia/Calcutta`, a fixed +05:30). It would not be correct for mixed offsets. Whether a different server zone could ever be configured is not confirmed.
- **A4.** Whether "Last Reading" is intended to mean *reading time* (current behaviour), *time data arrived* (`created_on`), or *time the device was last heard from* (`last_reported_on` / `captured_at`) is **not confirmed from the available source**. The code implements the first; no requirement document in the repository defines it.

### 8.6 Potential issues
- **P1.** Stale readings are shown without warning (U3). Live readings are 40 days old.
- **P2.** Decommissioned or misconfigured devices contribute rows and totals (C4).
- **P3.** The row timestamp can understate the age of one of its two values (U2).
- **P4.** "Readings Recorded" (energy_stat) and the device table (device_stat) describe different data sets for the same room, with no stated time range, and can contradict each other (D4).
- **P5.** Tooltip and comment text about `energy_unit` is outdated (U6).

---

## 9. Evidence

| Finding | Evidence |
|---|---|
| Header / cell | `frontend/src/features/occupancy/components/RoomPowerEnergy.tsx:349-351`, `:367-369` |
| Derivation of `lastSeen` | `RoomPowerEnergy.tsx:204-223` (esp. :216-219) |
| Latest-per-device rule | `RoomPowerEnergy.tsx:80-96` |
| Formatting | `RoomPowerEnergy.tsx:153-154` |
| Query parameters | `RoomPowerEnergy.tsx:49, 176-186` |
| Former "Last Reading" = count | `git show a2d587b` (label change); `RoomPowerEnergy.tsx:303-317` (current label and comment); commit `4e15fa6` |
| Route | `backend/app/api/v1/endpoints/telemetry.py:142` |
| Service / ordering / filters | `backend/app/services/telemetry.py` `_stat_stmt` (:109, join :138), `list_device_stats` (:145, filter :174) |
| Field meaning | `backend/app/schemas/telemetry.py:117` `timestamp: "When the device took the reading"` |
| Column types | live `information_schema.columns`: `device_stat.timestamp` = timestamptz |
| Live values | read-only queries on `device_stat`, `device_param`, `device`, `energy_stat`, `device_current_stat`, `device_health_stat` (2026-09-26) |
| `last_reported_on` | `backend/app/services/device.py:295, 343`; `backend/app/api/v1/endpoints/devices.py:204-205`; `backend/app/schemas/device.py:19-20, 211-215` |
| Unused current-stat hook | `frontend/src/lib/api/hooks.ts:286` (no caller) |
| Energy summary count | `backend/app/services/energy.py:214, 230-253`; unit `:41-65` |
| Dashboard panel without time | `frontend/src/features/occupancy/components/RoomDetailsPanel.tsx:84-101, 195-218` |
| Tab mounting | `frontend/src/features/occupancy/components/RoomDetailsModal.tsx:26, 230-232, 363` |

---

## 10. Gaps / questions requiring clarification

1. **Intended meaning of "Last Reading":** device reading time (current), data arrival time, or last contact with the device (heartbeat)? Not defined in the repository.
2. **Per-parameter vs per-device time:** should one row carry one time for two values, or should each value carry its own? Not confirmed.
3. **Staleness expectations:** is there a threshold after which a reading should be treated as outdated? No such rule exists in the code or docs.
4. **Device lifecycle:** should decommissioned or misconfigured devices appear in room readings? Not confirmed.
5. **Hub vs meter:** does the Intellihub's `active_power` / `active_energy` already include its child meters' values? Not confirmed (it affects the room totals next to the column).
6. **Ingestion:** who writes `device_stat` in production, and at what frequency? Not confirmed from the available source.
7. **Historic feedback:** do any open tickets or feedback referring to "Last Reading" date from 16–25 Sep, when the label meant the reading count?

---

## 11. Recommended next investigation

Investigation steps only. None of these are implementation.

1. Confirm the intended definition (Q1–Q3) with the product owner, using the three available time sources: `device_stat.timestamp`, `device_stat.created_on`, and `device_current_stat.captured_at` / `last_reported_on`.
2. Locate the external telemetry ingester and document its write frequency and whether `timestamp` is device time or server time.
3. Review tickets and screenshots from 16–25 Sep for "Last Reading" to separate count-related from timestamp-related feedback.
4. With production-like volume, check whether >100 `device_stat` rows per parameter per room occur (A2).
5. Confirm hub-vs-meter semantics with the hardware team (Q5).
6. Inventory every other screen that shows device values without a time (e.g. the Dashboard room panel) for consistency with whatever definition is agreed.

---

## 12. Executive summary

"Last Reading" on the room's Environment & Utilities tab is a **timestamp**: the time the device took its most recent power or energy reading, from `device_stat.timestamp`. It is worked out in the browser for each device as the later of the two readings' times, and shown in the viewer's local time. It is not a value, age or status.

The implementation is consistent with its source, but the display leaves room for misreading:
- The column sits between two value columns.
- Each row gives a single time for two values that may have been read at different times.
- Nothing shows how old the readings are. Live data is currently 40 days old, and the room totals above the table show no time at all.
- Decommissioned devices are included.
- The same label was used for a reading **count** from 16 to 25 September. Earlier feedback about "Last Reading" may refer to that count.

What "Last Reading" should mean (reading time, arrival time or last device contact) is not defined anywhere in the repository and should be agreed before any change.
