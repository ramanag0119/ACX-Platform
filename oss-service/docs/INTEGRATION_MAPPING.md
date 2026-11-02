# OSS Integration — Endpoint Mapping, Status & Decisions

Every OSS-served endpoint, its real source in `insp_iot`, and its status. All
reads are read-only, parameterised SQLAlchemy Core over explicit tables
(`app/db/tables.py`). No value is fabricated: fields without an OSS source are
served as `null` (documented) and resources without a source return an explicit
**503** (`oss_adapter_not_mapped`), never fake data.

## Endpoint → source mapping

| Endpoint | OSS source | Status | Notes |
|---|---|---|---|
| `GET /device-types` | `DISTINCT insp_device.device_type` | **Implemented** | derived registry; stable ordinal id; `short_code`/timestamps = null (no source) |
| `GET /device-types/{id}` | ″ + counts over `insp_device` | **Implemented** | `device_count` real; `firmware_count` = distinct `firmware_version` |
| `GET /devices` | `insp_device` (+ latest `insp_device_health` by `device_uid`, latest `insp_device_state`→`insp_device_state_type`) | **Implemented** | `facility_id`←`site_id` (null in data), `amenity_id`=null, `health_status` as-stored |
| `GET /devices/{id}` | ″ + parent/child via `parent_device_id` | **Implemented** | parent ref + children list + count |
| `GET /devices/{id}/health` | `insp_device_health` (by `device_uid`) | **Implemented** | real samples/temperature/last_reported_on; battery/operation history = [] (no source) |
| `GET /devices?amenity_id=…` | — | **Unsupported (503)** | OSS has no room/amenity linkage |
| `GET /device-current-stats` | latest `insp_device_performance.param_data` per `device_uid` | **Implemented** | JSON snapshot returned as-is |
| `GET /device-current-stats/{id}` | `insp_device_performance.record_id` | **Implemented** | real uuid id |
| `GET /device-params` | `DISTINCT` keys of `param_data` | **Implemented** | derived registry; `data_type` inferred from value; `unit`=null (no source) |
| `GET /device-params/{id}` | ″ + occurrence count | **Implemented** | `reading_count` real |
| `GET /device-stats` | `param_data` exploded to per-parameter rows | **Implemented** | values as-stored (strings); `device_param_id` = registry ordinal; filter by `device_uid`/`param_name` |
| `GET /device-stats/{id}` | — | **Unsupported (503)** | OSS has no stable per-parameter-reading id |
| `GET /other-device-readings` | — | **Unsupported (503)** | no third-party-meter table in OSS |
| `GET /alert-types` | `DISTINCT insp_device_alert.alert_type` | **Implemented** | name = stored code (no name lookup); empty now (0 rows) |
| `GET /alert-types/{id}` | ″ + `alert_count` | **Implemented** | `incident_count`=null (unknown; no incident table) |
| `GET /alerts` | `insp_device_alert` | **Implemented** | real mapping; empty now (0 rows); derived ordinal id |
| `GET /alerts/{id}` | — | **Unsupported (503)** | no stable integer id (PK is uuid+time) |
| `GET /alerts/{id}/incidents` | — | **Unsupported (503)** | no device_incident / alert linkage |
| `GET /incidents`, `/incidents/{id}` | — | **HMS (not served here)** | no `device_incident` in OSS (`insp_service_request` is a distinct ticket concept); HMS owns incidents with their `PATCH` |
| `GET /value-alerts`, `/value-alerts/{id}` | — | **HMS (not served here)** | no breach table in OSS; value alerts are breaches of HMS `/limit-configs` |
| `GET /energy-stats`, `/energy-stats/summary` | `param_data.active_energy` (cumulative) | **Unsupported (503)** | hourly consumption needs a business-confirmed delta/bucketing rule — **needs confirmation** |

## Implemented / partial / unsupported

- **Implemented (real data):** device-types, devices, device detail, device health, device-current-stats, device-params, device-stats, alert-types, alerts.
- **Partial / empty-but-correct:** alert-types & alerts are implemented but currently return 0 rows (tables empty).
- **Unsupported (explicit 503, documented):** device-stats detail-by-id, other-device-readings, alert detail-by-id, alert incidents, energy-stats + summary.
- **Moved to HMS (BSS):** incidents and value-alerts -- OSS has no source for either, so HMS serves them whether or not OSS dispatch is on.

## Compatibility decisions applied (approved)

1. OSS is site/customer-scoped with no room/amenity → `facility_id` (←`site_id`) and `amenity_id` widened to nullable; room-filtered device queries unsupported; occupancy `device_count` from OSS = **null (unknown), never 0**.
2. No device-type table → derived registry (stable ordinal id); `device_short_code` = null (no OSS source — not fabricated).
3. `health_status` returned **as stored** (no OSS label lookup — no invented "Active"/"Inactive").
4. Health/telemetry link by `device_uid` (OSS `device_id` is NULL on those tables).
5. Fields with no OSS source (`mfg_date`, firmware target, power/op flags, units, per-type timestamps) → null, documented.

## Business decisions requiring confirmation

| # | Topic | Question | Options |
|---|---|---|---|
| 1 | **Incidents** | Is HMS "incident" equivalent to OSS `insp_service_request` (support ticket)? They differ (SR has no alert linkage). | (a) map incident←service_request with alert-linkage null; (b) keep unsupported |
| 2 | **Energy** | How is hourly `energy_consumed` derived from the cumulative `active_energy` counter? | (a) expose raw cumulative readings; (b) delta-between-readings bucketed to hour with a confirmed reset/rollover policy |
| 3 | **short_code / health labels** | Should name→short_code and health-code→label mappings be configured (business-owned), or stay null/as-stored? | config-driven mapping vs null/as-stored (current) |
| 4 | **site = facility?** | Confirm OSS `site` maps to HMS `facility` (and that `site_id` will be populated). | confirm / provide linkage |

## Run instructions (local)

```bash
# 1) OSS service
cd oss-service
cp .env.example .env            # set OSS_DATABASE_URL (never commit)
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
#   docs: http://127.0.0.1:8001/docs   health: /health /health/db

# 2) HMS backend (enable dispatch)
#   backend/.env:  OSS_ENABLED=true  OSS_SERVICE_URL=http://127.0.0.1:8001
cd backend
PYTHONPATH=. python -m uvicorn app.main:app --port 8000

# 3) Frontend (unchanged)
cd frontend && npm run dev      # :8080
```

Rollback: set `OSS_ENABLED=false` on HMS → device reads resume from `hms_db`.

## Example (sanitized)

```
GET /api/v1/devices           (HMS, with JWT)  →  HMS RBAC (caleido_network:read) → OSS :8001
→ {"items":[{"device_uid":"0202110000000001","device_type_name":"AirQ",
             "device_short_code":null,"facility_id":null,"amenity_id":null,
             "health_status":"1","parent_device_id":"…"}],
   "page":1,"page_size":20,"total":6}
```
