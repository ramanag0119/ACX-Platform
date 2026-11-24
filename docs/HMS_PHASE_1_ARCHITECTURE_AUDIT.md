# HMS Phase 1 — Architecture & Existing Code Audit

Analysis-only audit of the existing HMS platform: what is implemented, what is verified,
what is blocked, and what Phase 2 must deliver. Every finding carries a file path, an API
endpoint, a database result or a test run as evidence.

| | |
|---|---|
| Audit date | 2026-11-16 |
| Backend version | `0.3.0` (`backend/app/core/version.py`) |
| BSS database | MySQL 8.4.13 `inspironics_app` — 94 tables, 1,882 rows, Alembic `a3f1c8e2d904` |
| OSS database | PostgreSQL `insp_iot` — **not configured, not reachable** |
| API surface | 142 paths / 186 operations (`OSS_ENABLED=false` mode) |
| Backend tests | 1,028 passed / 273 failed / 27 errors / 1 skipped |
| OSS tests | 15 passed / **20 skipped — all "OSS database not configured"** |

> **No modification was made.** No code, schema, record, configuration, branch or commit was
> changed. Database access was `SELECT`-only under `SET SESSION TRANSACTION READ ONLY`.
> Runtime checks ran the backend on scratch port 8097 and issued GET/POST requests.
> The test suites were executed; the backend suite writes to the BSS database **by its own
> design** (see [§7.2](#72-the-backend-test-suite-runs-against-the-live-bss-database)) — that
> is pre-existing behaviour of the suite, not an action taken by this audit.

---

## 1. Current Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ FRONTEND   React 18 + Vite + TypeScript        frontend/   :8080         │
│ 11 feature modules · 48 API paths · single client lib/api/client.ts      │
│ vite.config.ts:23  proxy /api/v1 -> VITE_API_PROXY_TARGET (:8000)        │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ fetch() + Bearer JWT
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ BACKEND    FastAPI  backend/app/main.py   :8000                          │
│  CORS → error envelope → JWT auth → DB-backed RBAC → router              │
│  app/api/v1/router.py  decides OSS-vs-BSS AT IMPORT (OSS_ENABLED)        │
│                                                                          │
│  ┌── OSS_ENABLED=false  (CURRENT) ──────────────────────────────────┐    │
│  │  device / telemetry / alert / energy reads served FROM MySQL     │    │
│  │  endpoints/devices.py, telemetry.py, alerts.py, energy.py        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│  ┌── OSS_ENABLED=true   (NOT ACTIVE) ───────────────────────────────┐    │
│  │  endpoints/oss_proxy.py → services/oss_client.py → httpx GET     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└───────────────┬──────────────────────────────────┬───────────────────────┘
                │ SQLAlchemy 2.0 / PyMySQL / TLS   │ httpx (GET only)
                ▼                                  ▼
┌──────────────────────────────┐   ┌──────────────────────────────────────┐
│ BSS MySQL  inspironics_app   │   │ OSS microservices :8001-8004         │
│ 94 tables · TLS verified     │   │ ✖ oss-service/.venv MISSING          │
│ ✔ OPERATIONAL                │   │ ✖ oss-service/.env MISSING           │
└──────────────────────────────┘   │ ✖ CANNOT START                       │
                                   └──────────────┬───────────────────────┘
                                                  ▼
                                   ┌──────────────────────────────────────┐
                                   │ FleetXplorer PostgreSQL  insp_iot    │
                                   │ ✖ NO HOST CONFIGURED ANYWHERE        │
                                   └──────────────────────────────────────┘
```

**The OSS tier is entirely non-operational today.** All device, telemetry, alert and energy
data is served from duplicated copies in BSS MySQL.

## 2. Target Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ FRONTEND   React + Vite                                      :8080       │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ Bearer JWT
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ BACKEND    FastAPI  —  OSS_ENABLED=true                      :8000       │
│   BSS reads/writes ──────────────┐    OSS reads ──────────────┐          │
│   /stays /rooms /services …      │    /devices /device-stats  │          │
│                                  │    /alerts /energy-stats   │          │
│   HMS NEVER opens a PostgreSQL connection  ◄── hard rule       │          │
└──────────────────────────────────┼────────────────────────────┼──────────┘
                                   ▼                            ▼
                  ┌────────────────────────┐   ┌────────────────────────────┐
                  │ BSS MySQL              │   │ OSS microservices          │
                  │ inspironics_app        │   │ device    :8001            │
                  │ Hospitality data ONLY  │   │ telemetry :8002            │
                  │ NO OSS-owned copies    │   │ alert     :8003            │
                  └────────────────────────┘   │ energy    :8004            │
                              ▲                └─────────────┬──────────────┘
                              │                              ▼
                  ┌───────────┴────────────┐   ┌────────────────────────────┐
                  │ room_device_map        │   │ FleetXplorer PostgreSQL    │
                  │ amenity_id ↔ oss uuid  │   │ insp_iot  (read-only)      │
                  │ THE ONLY BRIDGE        │   └────────────────────────────┘
                  └────────────────────────┘
```

### Conformance of the existing design to the target rules

| Target rule | Status | Evidence |
|---|---|---|
| Frontend React + Vite | ✔ Met | `frontend/package.json` — vite build; React 18 |
| Backend Python FastAPI | ✔ Met | `backend/app/main.py:33` |
| BSS = MySQL `inspironics_app` | ✔ Met | `config.py:63-80` — engine switch deliberately removed |
| OSS = FleetXplorer PostgreSQL `insp_iot` | ⚠ Designed, not connected | `oss-service/app/db/tables.py` |
| OSS data only via OSS APIs | ✔ Designed correctly | `oss_proxy.py` → `oss_client.py` is the only route |
| HMS never connects to PostgreSQL directly | ✔ Met and enforced | `backend/requirements.txt` declares **no** PostgreSQL driver |
| Do not duplicate OSS data in MySQL | ✖ **Violated today** | 11 OSS-owned tables hold 889 rows in MySQL ([§4](#4-bss-and-oss-data-ownership)) |

> **One caveat on "HMS never connects to PostgreSQL".** The rule is met in *declaration*:
> `backend/requirements.txt` ships no PostgreSQL driver. But `psycopg2` **is importable from
> `backend/.venv`** (verified this audit) because `oss-service` has no venv of its own and
> its dependencies were installed into the backend's. `requirements.txt:9-13` documents this
> exact situation and the fix. So the architectural guarantee is currently procedural, not
> enforced by the environment.

---

## 3. Frontend-to-Backend API Mapping

11 feature modules under `frontend/src/features/`, one API client
(`frontend/src/lib/api/client.ts`), RBAC route map in `frontend/src/core/rbac/modules.ts`.

| Feature module | Key screens | Backend routes | RBAC module |
|---|---|---|---|
| `auth` | Login, session | `/auth/login`, `/auth/me` | — |
| `dashboard` | KPIs, Alerts, Energy, Caleido At Work | `/occupancy/kpis`, `/alerts`, `/service-requests`, `/energy-stats/summary`, `/amenity-statuses`, `/stays`, `/incidents` | `dashboard` |
| `occupancy` | Room grid, daily occupancy | `/occupancy`, `/occupancy/daily`, `/occupancy/summary`, `/rooms`, `/amenity-conditions` | `occupancy` |
| `bookings` | Stays, invoices, allocation | `/stays`, `/invoices`, `/room-allocations`, `/stay-occupants` | `bookings` |
| `devices` | Device list/detail, telemetry | `/devices`, `/device-types`, `/device-stats`, `/device-current-stats`, `/device-params`, `/other-device-readings` | `caleido_network` |
| `services` | Requests, catalogue, planning | `/service-requests`, `/service-categories`, `/service-items`, `/maintenance-requests` | `service_*` |
| `tickets` | Incidents, value alerts | `/incidents`, `/value-alerts`, `/limit-configs` | `tickets` |
| `marketing` | Offers, events, holidays | `/offers`, `/events`, `/holidays` | `offers`, `events`, `holidays` |
| `reports` | Report views + export | `/reports`, `/reports/{key}/export.xlsx` | `reports` |
| `config` | Users, roles, **Room Devices**, job orders | `/users`, `/roles`, `/permissions`, `/modules`, **`/room-devices`**, `/job-orders` | `user_roles`, `caleido_network`, `job_order` |
| `common` | Shared tables, filters | — | — |

### Mapping completeness (verified by diffing `frontend/src/**` against `/openapi.json`)

- **Every frontend path resolves to a real backend route.** No orphaned frontend calls.
- **52 of 54 backend route groups are referenced** from the frontend.
- Only `/room-allocations` and `/stay-occupants` are never referenced — both are write
  sub-resources of the bookings flow; they may be intentionally backend-only.

### Room Devices UI — already built

`frontend/src/features/config/pages/RoomDevices.tsx:44-46` documents its own contract:

```
Table   -> GET    /room-devices     (the mapping, HMS data)
Install -> POST   /room-devices     (HMS confirms the device exists in OSS first)
Remove  -> DELETE /room-devices/{id}
```

Routed at `App.tsx:74` (`/config/room-devices`), in the sidebar at `AppSidebar.tsx:361`,
RBAC-gated to `caleido_network` (`modules.ts:72`), with hooks `useRoomDevices`,
`useAssignRoomDevice`, `useUnassignRoomDevice`. **The bridge UI is complete** — it is only
unpopulated.

### Dashboard data sources

`features/dashboard/components/DashboardKPIs.tsx` composes ~15 independent queries via a
`useCount` helper plus `useOccupancyKpis` and `useEnergySummary`. Material consequence:
**with `OSS_ENABLED=true` the Energy tile and the device KPIs would break**, because
`/energy-stats` returns 503 from OSS and device counts route to OSS
([§5](#5-oss-microservice-api-mapping)).

---

## 4. BSS and OSS Data Ownership

Full table-level analysis: [docs/database/OSS_BSS_TABLE_AUDIT.md](database/OSS_BSS_TABLE_AUDIT.md).

| Class | Tables | Rows | Meaning |
|---|---:|---:|---|
| **BSS** | 75 | — | Hospitality data. HMS is system of record. Correct. |
| **OSS** | 11 | 889 | Device-derived. **Duplicated in MySQL — violates the target rule.** |
| **Shared** | 3 | — | `device`, `facility`, `room_device_map` |
| **Uncertain** | 5 | 36 | `mqtt_broker`, `mqtt_topic`, `device_command`, `command_type`, `firmware` |

### The 11 OSS-owned tables currently duplicated in MySQL

| MySQL table | Rows | OSS source in `insp_iot` | Phase 2 action |
|---|---:|---|---|
| `device_stat` | 504 | `insp_device_performance.param_data` exploded | Stop reading; serve via OSS |
| `device_health_stat` | 168 | `insp_device_health` | Stop reading; serve via OSS |
| `energy_stat` | 72 | `param_data.active_energy` (cumulative) | **Blocked** — no agreed derivation rule |
| `sensor_operation_stat` | 42 | *none* | **Blocked** — no OSS source |
| `device_param` | 35 | `DISTINCT` keys of `param_data` | Derived registry in OSS |
| `alert_type` | 16 | `DISTINCT insp_device_alert.alert_type` | Derived registry in OSS |
| `device_current_stat` | 14 | latest `param_data` per `device_uid` | Stop reading; serve via OSS |
| `other_device` | 12 | *none* | **Blocked** — no OSS source |
| `battery_life_stat` | 12 | *none* | **Blocked** — no OSS source |
| `device_alert` | 9 | `insp_device_alert` | Stop reading; serve via OSS |
| `device_type` | 4 | `DISTINCT insp_device.device_type` | Derived registry in OSS |

**138 of those 889 rows have no OSS source at all** (`sensor_operation_stat`, `other_device`,
`battery_life_stat`, `energy_stat`). Switching to OSS does not migrate them — it stops
serving them. This needs a decision, not an implementation.

### Correctly BSS despite being device-adjacent

`app/core/oss_routes.py:11-15` states it explicitly: `device_incident`, `incident_history`,
`incident_status`, `incident_event`, `value_alert`, `value_alert_limit_config`,
`daily_dual_data_point`. OSS has no incident table and no threshold-breach table. **Do not
move these in Phase 2.**

---

## 5. OSS Microservice API Mapping

Source: `oss-service/docs/INTEGRATION_MAPPING.md` + `oss-service/app/adapters/`.
`app/core/oss_routes.py` is the single source of truth for which HMS paths are OSS.

| OSS domain | Port | HMS prefixes | Adapter | Source table |
|---|---:|---|---|---|
| `device` | 8001 | `/device-types`, `/devices` | `device_adapter.py` | `insp_device`, `insp_device_health`, `insp_device_state(_type)` |
| `telemetry` | 8002 | `/device-params`, `/device-stats`, `/device-current-stats`, `/other-device-readings` | `telemetry_adapter.py` | `insp_device_performance` |
| `alert` | 8003 | `/alert-types`, `/alerts` | `alert_adapter.py` | `insp_device_alert` |
| `energy` | 8004 | `/energy-stats` | `energy_adapter.py` | `insp_device_performance.param_data.active_energy` |

### Endpoint readiness

| Status | Endpoints |
|---|---|
| **Implemented (real data)** | `/device-types`, `/device-types/{id}`, `/devices`, `/devices/{id}`, `/devices/{id}/health`, `/device-current-stats`(+`/{id}`), `/device-params`(+`/{id}`), `/device-stats`, `/alert-types`(+`/{id}`), `/alerts` |
| **Implemented but empty** | `/alert-types`, `/alerts` — `insp_device_alert` has 0 rows |
| **Unsupported → explicit 503** | `/device-stats/{id}`, `/other-device-readings`, `/alerts/{id}`, `/alerts/{id}/incidents`, `/energy-stats`, `/energy-stats/summary` |
| **Unsupported → empty list** | device battery history, device operation history |
| **Stays in HMS** | `/incidents`, `/value-alerts`, `/daily-data-points` |

### HMS→OSS integration layer (implemented, unit-verified)

`backend/app/services/oss_client.py:40` `forward()`:
- Per-domain URL: `settings.oss_url_for(oss_domain_for(subpath))`
- Transport error/timeout → `OssUnavailable` → HMS returns `503 {"code":"oss_unavailable"}`
- A 4xx/5xx **from** OSS is passed through verbatim
- Optional `X-OSS-Service-Token`, never logged

`backend/app/api/v1/endpoints/oss_proxy.py` re-declares the **same `require_permission` gate**
as the local router it replaces, so HMS stays the security boundary. Only GETs are
registered — no write can ever be forwarded.

**`/devices` is the one composed route** (`oss_proxy.py:86`): HMS resolves location filters
against `room_device_map`, forwards `device_ids=…` to OSS, then re-attaches room/floor/
building on the way back. If a room has no mapped devices it short-circuits and never calls
OSS (`oss_proxy.py:107`).

---

## 6. Current Implementation Status

| # | Module | Status | Evidence |
|---|---|---|---|
| 1 | Frontend modules & API wiring | **Implemented, verified** | 11 features; every FE path resolves; 52/54 backend groups referenced |
| 2 | FastAPI endpoints / services / models | **Implemented, verified** | 186 operations; 28 services; 95 models; 1,028 tests pass |
| 3 | MySQL BSS tables | **Implemented, verified** | 94 tables, 242 FKs, TLS verified, Alembic `a3f1c8e2d904` |
| 4 | OSS Device microservice | **Implemented, NOT verified** | `device_adapter.py` complete; all DB tests **skipped** |
| 5 | OSS Telemetry microservice | **Implemented, NOT verified** | `telemetry_adapter.py` complete; 6 tests skipped |
| 6 | OSS Alert microservice | **Implemented, NOT verified** | `alert_adapter.py` complete; source table empty |
| 7 | OSS Energy microservice | **Blocked** | Returns 503 by design — derivation rule unconfirmed |
| 8 | HMS→OSS integration | **Implemented, unit-verified** | `tests/test_oss_dispatch.py` — **20/20 pass** |
| 9 | Dashboard data sources | **Implemented, verified (BSS mode)** | `DashboardKPIs.tsx`; would degrade under OSS |
| 10 | Room-to-device mapping | **Implemented end-to-end, 0 records** | Table + service + 3 API routes + UI page; `GET /room-devices` → `total: 0` |
| 11 | Authentication & permissions | **Implemented; BLOCKED at runtime** | JWT + DB-backed RBAC work; **0/18 accounts can log in** |
| 12 | Deployment / on-prem | **Partially implemented** | `ecosystem.config.js` complete; **OSS venv missing** |

### Status key applied strictly

- *Verified* = exercised this audit against real data or passing tests.
- *Not verified* = code reviewed and complete, but **no execution evidence exists**. All four
  OSS adapters are in this category — their 20 data tests are **skipped**, not passing.

---

## 7. Missing Integrations and Issues

### 7.1 CRITICAL — The migration tree has two heads; one branch was never applied

This is the **root cause of every schema inconsistency** in this codebase.

```
                    ┌─> a3f1c8e2d904  room_device_map          ◄── DATABASE IS HERE (head)
0e2687233b59 → 7c4e2b9a1d53 (branchpoint)
                    └─> 8f1e3c5a7b92  room_status_condition_applicability
                          → 9a2b3c4d5e6f  role.notification_preferences
                            → b3c4d5e6f7a8  currency + energy/billing   ◄── NEVER APPLIED (head)
```

`alembic heads` returns **two** heads; `alembic current` returns `a3f1c8e2d904`.
Alembic cannot auto-upgrade past a branchpoint with two heads — it needs an explicit merge.

Everything the unapplied branch would have created is missing, and each omission is already
breaking something:

| Missing object | From revision | Observed failure |
|---|---|---|
| `currency` table | `b3c4d5e6f7a8` | **`GET /api/v1/currencies` → 503** (reproduced live) |
| `package.price`, `package.currency_id` | `b3c4d5e6f7a8` | `Package` model selects a non-existent column |
| `service_category_item.currency_id` | `b3c4d5e6f7a8` | same |
| `invoice.currency_id` | `b3c4d5e6f7a8` | same |
| `energy_stat.device_id` + FK + indexes | `b3c4d5e6f7a8` | `1054 Unknown column 'device_id'` — 12 test failures |
| `other_device.device_id` + FK | `b3c4d5e6f7a8` | same |
| `room_status_condition_applicability` table | `8f1e3c5a7b92` | 13 test failures |
| `amenity_condition.display_name`, `applicable_to_*`, `is_active` | `8f1e3c5a7b92` | 12 test failures |
| `role.notification_preferences` | `9a2b3c4d5e6f` | confirmed absent from `role` |

Live reproduction:

```http
GET /api/v1/currencies    →  503
{"error":{"code":"service_unavailable","message":"Database is unavailable."}}
```
```
pymysql.err.ProgrammingError: (1146, "Table 'inspironics_app.currency' doesn't exist")
```

> **The 503 is itself misleading.** `app/api/errors.py:91` maps every `SQLAlchemyError` to
> 503 "Database is unavailable" — but the database is healthy; a table is missing. An
> operator would investigate connectivity and find nothing wrong.

> **⚠ The unapplied branch appears to be PostgreSQL-authored and may not run on MySQL as
> written.** `b3c4d5e6f7a8` imports `from sqlalchemy.dialects.postgresql import UUID as
> PGUUID` (line 25) and uses `server_default=sa.text("now()")` and
> `server_default="true"` for Boolean columns. MySQL 8 requires `DEFAULT (now())` for
> expression defaults and `1`/`0` for TINYINT booleans. **This is a code-level reading — I
> did not execute the migration** (that would modify the schema). Phase 2 must dry-run it
> against a scratch database before touching anything real.

### 7.2 CRITICAL — The OSS tier cannot start

| Requirement | State | Evidence |
|---|---|---|
| `oss-service/.venv` | **MISSING** | `ecosystem.config.js` `venvPython("oss-service")` cannot resolve |
| `oss-service/.env` | **MISSING** | only `.env.example` exists |
| `OSS_DATABASE_URL` | **UNSET** | placeholder is redacted: `192.168.x.120` |
| FleetXplorer host/credentials | **NOT SUPPLIED ANYWHERE** | repo-wide grep found only the placeholder |

`backend/requirements.txt:9-13` already documents this gap. Consequence: **all four OSS PM2
processes would fail to launch**, and `/api/v1/health/oss` would report every domain
unreachable the moment `OSS_ENABLED=true`.

### 7.3 CRITICAL — No account can authenticate

```json
{"accounts": 18, "with_usable_credential": 0, "usable_usernames": []}
```

Every `app_user.password_hash` holds the Phase-1.8 sentinel `!seed-no-login` or NULL.
`app/core/security.py:51` returns False for those by design. Live:

```http
POST /api/v1/auth/login  {"username":"admin","password":"admin"}  →  401
{"error":{"code":"unauthorized","message":"Invalid username or password."}}
```

**181 of 186 operations are unreachable through the front door.** Only these five answer
without a token: `GET /health`, `GET /api/v1/health/{db,oss,version}`, and
`POST /api/v1/auth/login` (which rejects everyone).

The auth *mechanism* is sound and verified — `tests/conftest.py` mints real tokens through
the genuine issuing path, and `/auth/me` returns correct roles, facilities and 18 module
grants. Only the **credential data** is absent.

### 7.4 `OSS_ENABLED` configuration

| Location | Value | Effect |
|---|---|---|
| `backend/.env:37` | `false` | all OSS reads served from MySQL |
| `backend/app/core/config.py:136` | default `False` | — |
| `ecosystem.config.js` | **not set** | PM2 does not override; stays `false` |
| `tests/conftest.py:26` | `setdefault("OSS_ENABLED","false")` | suites test the BSS path |

**Dispatch is decided at import** (`router.py:78` / `:144`), not per request. Flipping it
requires a **process restart**, changes the OpenAPI surface, and is a deployment decision.
Rollback is symmetric: set `false`, restart.

### 7.5 `room_device_map` — implemented, empty

`GET /api/v1/room-devices` → `{"items":[],"page":1,"page_size":20,"total":0}` (live).
The only empty table in the database. Full stack exists: table, `services/room_devices.py`,
3 API routes, UI page. `assign_device()` verifies the device in OSS before writing — so
**it cannot be populated until the OSS service runs**. Chicken-and-egg with §7.2.

With 0 rows and `OSS_ENABLED=true`, `/devices?amenity_id=…` short-circuits to an empty list
for every room without ever calling OSS.

### 7.6 OSS service authentication token

`OSS_SERVICE_TOKEN` unset → `oss-service/app/api/security.py` `require_service_token` is a
no-op, and `oss_client._headers()` sends nothing. Data routes on :8001–:8004 would be
readable by anything that can reach the port. **This fails closed outside development**:
`oss-service/app/main.py:28` refuses to start when `APP_ENV != "development"` without a
token. Today's protection is the `127.0.0.1` bind, not the token.

### 7.7 PostgreSQL leftovers in a MySQL-only backend

- **Functional:** `app/services/writes.py:77` `_constraint_name()` reads
  `exc.orig.diag.constraint_name` — the psycopg2 diagnostics API. PyMySQL has no `.diag`,
  so it always returns `None`. Degrades safely (409 still raised, unnamed).
- **User-visible:** `app/main.py:38` advertises "the seeded PostgreSQL data" in the OpenAPI
  description, shown at `/docs`.
- **Docstrings:** `deps.py:47`, `services/auth.py:3`, `core/security.py:87`,
  `api/errors.py:75`, `services/writes.py:58` all still say PostgreSQL.

---

## 8. Database Dependency Findings

### 8.1 Connection and credential path — verified working

```
etc/shibboleth.zip → shibboleth.txt (master password)
  → etc/hmsBackend.kdbx, entry "MYSQL_BSS"   (app/core/vault.py:152)
  → MySQLCredentials(host, port, user, password, database, ssl_ca)
  → app/core/config.py:15 _bss_credentials()  @lru_cache
  → settings.sqlalchemy_url  →  mysql+pymysql://…
```

`.env` holds **no** database credentials (`extra="ignore"` drops stray keys). TLS verified
this audit: cipher `TLS_AES_256_GCM_SHA384`, `ssl_verify_cert` and `ssl_verify_identity`
both true, server cert SAN covers the LAN IP `192.168.0.120`.

`migrations/env.py:65` imports the same `CONNECT_ARGS` as `app/db/session.py:17`, so Alembic
and the app cannot drift on transport settings.

### 8.2 Schema statistics

94 tables · 242 FK columns · 37 enum columns · 0 views · 0 routines · 0 triggers ·
1,882 rows across 93 non-empty tables. Most-referenced: `app_user` (51), `facility` (29),
`amenity` (19), `device` (16), `stay` (12).

### 8.3 Model/table drift — 2 of 95 models have no table

`currency` and `room_status_condition_applicability` — both explained by §7.1.
93 of 94 tables have a model; `alembic_version` correctly has none.

### 8.4 Row-count drift

`tests/conftest_writes.py:4` states the suite expects **1,792 seeded records**. The database
holds **1,882** — **+90 rows**. `stay` holds 69 rows of which **63 are `pending`**, a
distribution consistent with accumulated write-test residue that was never cleaned up.

### 8.5 The backend test suite runs against the live BSS database

`tests/conftest_writes.py:21-27` opens a real `SessionLocal()` against
`inspironics_app`; there is **no separate test database and no transactional rollback
isolation**. The suite's contract is self-cleanup ("creates its own rows and removes them
again"), which fails whenever a run is interrupted.

**Consequence — results are not reproducible.** Three runs this audit, identical code:

| Run | Passed | Failed | Errors |
|---|---:|---:|---:|
| 1 | 1,029 | 285 | 14 |
| 2 | 1,028 | 273 | 27 |
| 3 | 1,028 | 273 | 27 |

Same 1,329 total, different distribution. Two distinct root causes, both confirmed:

1. **Unapplied migration branch** (§7.1) — `test_priority4_database_architecture.py` (12),
   `test_room_condition_applicability.py` (13), `test_room_condition_default.py` (12),
   `test_schema_foundation.py` (13). Confirmed:
   `AssertionError: device_id column missing on energy_stat table`.
2. **Fixture precondition starvation** — `test_occupancy_api.py` (56),
   `test_stay_write_api.py` (15 failed + 24 errors), `test_report_api.py` (25). The
   `free_room` fixture (`conftest_writes.py:169`) needs a room with `status=0` held by no
   live stay. Verified live: **0 rooms qualify** — 24 room amenities, 14 with `status=0`,
   all held by one of 63 pending stays or blocked by a condition.

**Neither failure mode indicates a defect in application code.** Both are environment/data
problems.

---

## 9. On-Premise Deployment Requirements

### Current configuration — `ecosystem.config.js`

7 PM2 processes: 4 OSS (`hms-oss-{device,telemetry,alert,energy}` on 8001–8004), 1 backend
(`hms-backend` :8000), 1 frontend (`hms-frontend` Vite :8080). OSS URLs are derived from the
same port list used to launch the services, so the backend's routing table cannot drift from
the running processes. All bind `127.0.0.1`.

### Readiness

| Requirement | State | Gap |
|---|---|---|
| `backend/.venv` | ✔ Present | — |
| `backend/.env` | ✔ Present | — |
| `backend/etc/` vault + `shibboleth.zip` | ✔ Present, verified | gitignored; must be provisioned per host |
| MySQL `inspironics_app` + TLS CA | ✔ Reachable, TLS verified | CA at `D:\…\HMS-Security\Certificates\ca.pem` — **outside the repo**, must exist per host |
| `oss-service/.venv` | ✖ **MISSING** | blocks all 4 OSS processes |
| `oss-service/.env` | ✖ **MISSING** | blocks all 4 OSS processes |
| FleetXplorer host/credentials | ✖ **NOT SUPPLIED** | blocks everything OSS |
| `OSS_SERVICE_TOKEN` | ✖ Unset | required outside development |
| Frontend production build | ⚠ Untested here | `vite build`; set `VITE_API_BASE_URL` |
| Frontend served by PM2 | ⚠ **Dev server** | `hms-frontend` runs `vite`, not a static build behind a web server |

### Dependencies that must exist on the host

- Python venvs for **both** `backend/` and `oss-service/` (the latter deliberately separate
  so `psycopg2` is not importable from the backend — `requirements.txt:9-13`)
- Node.js for Vite; PM2 as process manager
- Network reach: backend → MySQL `192.168.0.120:3306` (TLS); OSS services → FleetXplorer
  PostgreSQL `:5432`; backend → `127.0.0.1:8001-8004`
- The CA bundle file, kept outside the repository

---

## 10. Phase 2 Implementation Plan

Ordered by dependency. **Nothing below has been done** — this is a proposal for review.

### Stage 0 — Decisions and access required *before* any code (BLOCKING)

| # | Item | Needed from | Blocks |
|---|---|---|---|
| D1 | FleetXplorer host, port, database, read-only user, password | DBA / FleetXplorer owner | All OSS work |
| D2 | Energy derivation rule: how is hourly `energy_consumed` derived from cumulative `active_energy` (reset/rollover policy)? | Business | `/energy-stats`, dashboard Energy tile |
| D3 | The 138 rows with no OSS source (`sensor_operation_stat`, `other_device`, `battery_life_stat`): retain in BSS, or accept loss? | Business | OSS cutover scope |
| D4 | Confirm OSS `site` == HMS `facility`, and that `site_id` will be populated | Business | `/devices.facility_id` |
| D5 | Owner for `mqtt_*`, `device_command`/`command_type`, `firmware` (the 5 Uncertain tables) | Architecture | Final ownership map |
| D6 | Credential provisioning policy for the 18 accounts | Security | Any end-to-end testing |
| D7 | Is `insp_service_request` equivalent to an HMS incident? | Business | `/incidents` ownership |

### Stage 1 — Unblock the environment (no application code)

1. Create `oss-service/.venv`; install `oss-service/requirements.txt`.
2. Create `oss-service/.env` with `OSS_DATABASE_URL` from **D1**. Never commit.
3. `pip uninstall psycopg2-binary` from `backend/.venv` so a stray PostgreSQL URL becomes
   unconnectable from HMS — enforcing the target rule in the environment, as
   `requirements.txt:11-13` already prescribes.
4. Generate `OSS_SERVICE_TOKEN`; set the same value in both `.env` files.
5. Verify: start the 4 OSS services, check `/health` and `/health/db` on each.
6. Re-run the OSS suite — **the 20 skipped tests must become passes.** This is the first
   real evidence the adapters work.

### Stage 2 — Resolve the migration branch (highest-risk item)

1. Dry-run `b3c4d5e6f7a8`, `9a2b3c4d5e6f`, `8f1e3c5a7b92` against a **scratch copy** of
   `inspironics_app`. Expect MySQL incompatibilities (§7.1).
2. Port the PostgreSQL-isms: `PGUUID` → `CHAR(36)`, `sa.text("now()")` →
   `CURRENT_TIMESTAMP`, Boolean `"true"` → `1`.
3. Create an Alembic **merge revision** joining the two heads.
4. Apply to the scratch DB; confirm `currency`, `room_status_condition_applicability`,
   `energy_stat.device_id`, `role.notification_preferences` and the `currency_id` columns.
5. Re-run the backend suite on the scratch DB — the ~50 schema-dependent failures should
   clear.
6. Only then schedule the production migration, with a backup and a tested rollback.

> **Note the ordering tension:** `b3c4d5e6f7a8` adds `energy_stat.device_id` and
> `other_device.device_id` — new columns on two tables the target architecture says should
> stop living in MySQL. Resolve **D3** before applying, or you build on a table you intend
> to retire.

### Stage 3 — Fix the test environment

1. Stand up a dedicated test database (restore from seed) — the suite must stop running
   against the live BSS.
2. Or wrap each test in an outer transaction rolled back at teardown.
3. Re-seed to the documented 1,792-row baseline; investigate the +90 residue.
4. Establish a green baseline **before** any Phase 2 feature work. Without it there is no
   signal to regress against.

### Stage 4 — Provision credentials

Use `app/core/security.hash_password()` to set a real bcrypt hash for at least one admin.
Verify `POST /auth/login` returns a token, then exercise one end-to-end frontend flow.
**Nothing in the UI can be validated until this is done.**

### Stage 5 — Populate `room_device_map`

Requires Stage 1 (assignment verifies the device against OSS first). Use the existing
`/config/room-devices` screen — **no new code**. Map each of the 14 BSS devices to its room.

### Stage 6 — Enable OSS dispatch

1. Set `OSS_ENABLED=true` in `backend/.env`; add it to `ecosystem.config.js` so PM2 is
   explicit.
2. Restart `hms-backend` (import-time decision).
3. Verify `/api/v1/health/oss` reports all four domains `ok`.
4. Regression-test device/telemetry/alert screens.
5. Confirm expected degradations: `/other-device-readings` → 503, `/energy-stats` → 503
   until **D2**, battery/operation history → `[]`.
6. Rollback: `OSS_ENABLED=false` + restart.

### Stage 7 — Remove duplicated OSS data (only after Stage 6 is stable)

Retire the 11 OSS-owned tables per **D3**. Keep `device` (16 tables FK to it),
`facility` and `room_device_map`. **Do not** touch the incident/value-alert tables.

### Stage 8 — Cleanup (low risk, do anytime)

Fix `writes.py:77` for PyMySQL; correct the PostgreSQL docstrings; fix the user-visible
OpenAPI description in `main.py:38`; consider distinguishing "missing relation" from
"database unavailable" in `errors.py:91`.

---

## 11. Phase 1 Completion Report

### What has been verified

- **BSS MySQL is fully operational** — 94 tables, 1,882 rows, TLS `TLS_AES_256_GCM_SHA384`
  with certificate **and** identity verification active, vault-backed credentials.
- **The backend application is sound** — 186 operations across 23 endpoint modules,
  28 services, 95 models; 1,028 tests pass.
- **The HMS→OSS dispatch layer is correctly designed and unit-verified** — 20/20 in
  `tests/test_oss_dispatch.py`. The security boundary stays in HMS; only GETs forward;
  per-domain routing and the 503 failure policy work as documented.
- **The frontend is complete and correctly wired** — 11 modules, every path resolves,
  52/54 backend route groups referenced, including a finished Room Devices screen.
- **`room_device_map` is implemented end-to-end** — table, service, 3 routes, UI, RBAC.
- **The architecture already honours the "no direct PostgreSQL" rule** in declaration.

### What is already working

BSS reads and writes · JWT issuing/validation · DB-backed RBAC (18 modules, 65 grants) ·
the single error envelope · health/liveness/readiness · TLS · the vault · OSS dispatch
routing logic · the frontend API client and its error handling.

### What is pending

OSS venv and `.env` · FleetXplorer connectivity · OSS service token · the migration merge ·
credential provisioning · `room_device_map` population · a clean test environment ·
removal of duplicated OSS data · a production frontend build strategy.

### Critical blockers

| # | Blocker | Impact | Unblocked by |
|---|---|---|---|
| **B1** | FleetXplorer credentials not supplied | Entire OSS tier dead; 20 adapter tests skipped | **D1** |
| **B2** | `oss-service/.venv` and `.env` missing | All 4 OSS processes cannot start | Stage 1 |
| **B3** | Migration branch unapplied + likely MySQL-incompatible | `/currencies` 503; ~50 test failures; 9 missing objects | Stage 2 |
| **B4** | 0 of 18 accounts can authenticate | 181/186 operations unreachable; no UI flow testable | **D6** → Stage 4 |
| **B5** | Test suite non-deterministic on live DB | No reliable regression signal | Stage 3 |
| **B6** | `room_device_map` empty | Rooms would show no devices under OSS | B1+B2 → Stage 5 |

**B1 is the master blocker.** B2, B6 and all OSS verification depend on it. B3 and B4 are
independent and can proceed in parallel.

### What needs to be implemented in Phase 2

Little new application code is required. The OSS integration, dispatch layer, room-device
bridge and frontend are **already built**. Phase 2 is predominantly **environment
provisioning, a migration repair, and verification**:

1. Provision the OSS runtime (Stage 1) — configuration, not code.
2. Repair and merge the migration branch (Stage 2) — the only substantive code work, and the
   highest-risk item.
3. Rebuild the test environment (Stage 3).
4. Provision credentials (Stage 4).
5. Populate the mapping through the existing UI (Stage 5) — no code.
6. Enable dispatch and verify (Stage 6) — configuration.
7. Retire duplicated OSS tables (Stage 7) — pending **D3**.

### Decisions and access required before implementation

**Access:** FleetXplorer PostgreSQL connection details and a read-only user (**D1**);
authority to create a scratch database for migration testing; authority to provision an
application credential (**D6**).

**Decisions:** **D2** energy derivation · **D3** the 138 sourceless rows · **D4** site↔facility ·
**D5** ownership of the 5 Uncertain tables · **D7** incident↔service-request.

**No work should begin on Stage 6 or 7 until D2, D3 and D4 are answered** — each one changes
what the cutover is allowed to drop.

---

### Audit limitations — stated plainly

1. **FleetXplorer `insp_iot` was never reached.** No credentials exist in the repository.
   Every OSS-side statement here derives from `oss-service/app/db/tables.py` (transcribed
   from an earlier discovery run) and `INTEGRATION_MAPPING.md` — **not from the live OSS
   database.** Re-verify before acting.
2. **The OSS proxy path was never executed.** `OSS_ENABLED=false` means those routers are not
   mounted. `tests/test_oss_dispatch.py` covers the logic without a real OSS service.
3. **The unapplied migrations were not run.** The MySQL-incompatibility assessment in §7.1 is
   a code reading, not an observed failure. Running it would have modified the schema.
4. **The backend test suite writes to the live BSS database** by its own design. That is
   pre-existing behaviour, not an action chosen by this audit, but it is the reason the
   numbers move between runs — and it is why Stage 3 should precede Phase 2 feature work.
