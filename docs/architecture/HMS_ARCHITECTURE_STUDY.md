# HMS Architecture Study

Architectural study of the HMS platform: FastAPI service structure, BSS MySQL integration,
OSS microservice integration, routing, authentication and data flow — traced through real
execution paths with actual file paths, symbol names and captured request/response pairs.

| | |
|---|---|
| Scope | `backend/` (HMS API), `oss-service/` (OSS microservices), `frontend/` (React/Vite) |
| Backend version | `0.3.0` (`app/core/version.py`) |
| BSS database | MySQL 8.4.13 `inspironics_app`, Alembic `a3f1c8e2d904`, 94 tables |
| OSS database | PostgreSQL `insp_iot` (external, read-only) — **not reachable during this study** |
| Route surface | 142 paths / 186 operations (112 GET, 40 POST, 23 PATCH, 7 DELETE, 4 PUT) |
| Study date | 2026-11-16 |

> **Read-only.** No code, schema, configuration or existing file was modified. Runtime
> evidence came from starting the backend on a scratch port (8097), issuing GET/POST
> requests, and running `SELECT`-only queries through existing service functions. The one
> token used was minted in-process with `create_access_token()` (a signing operation; it
> writes nothing) to exercise the authorised path.

---

## 1. Process topology

Four tiers, deployed as seven PM2 processes (`ecosystem.config.js`):

```
┌─────────────────────────────────────────────────────────────────────────┐
│  hms-frontend   Vite dev server  :8080                                  │
│  React 18 + TypeScript. Proxies /api/v1 -> :8000 (vite.config.ts:23)    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  fetch(), Bearer JWT
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  hms-backend    FastAPI  :8000      backend/app/main.py                 │
│  ─ CORS ─ error envelope ─ JWT auth ─ DB-backed RBAC ─ routing          │
└──────────┬──────────────────────────────────────┬───────────────────────┘
           │ SQLAlchemy 2.0 ORM                   │ httpx (GET only)
           │ mysql+pymysql, TLS                   │
           ▼                                      ▼
┌──────────────────────────┐      ┌──────────────────────────────────────┐
│  BSS MySQL               │      │  hms-oss-device     :8001            │
│  inspironics_app         │      │  hms-oss-telemetry  :8002            │
│  94 tables               │      │  hms-oss-alert      :8003            │
│  TLS_AES_256_GCM_SHA384  │      │  hms-oss-energy     :8004            │
└──────────────────────────┘      └───────────────┬──────────────────────┘
                                                  │ psycopg2, read-only
                                                  ▼
                                  ┌──────────────────────────────────────┐
                                  │  OSS PostgreSQL  insp_iot (external) │
                                  └──────────────────────────────────────┘
```

The four OSS processes run the *same* codebase (`oss-service/`); `OSS_DOMAINS` is set per
process in `ecosystem.config.js` so each mounts only its own routers
(`oss-service/app/api/router.py:43` `build_api_router`). `ecosystem.config.js` derives
`OSS_{DEVICE,TELEMETRY,ALERT,ENERGY}_SERVICE_URL` from the same port list it uses to launch
them, so the backend's routing table cannot drift from the processes actually running.

### Current runtime state

`OSS_ENABLED=false` in `backend/.env`. **Every device/telemetry/alert/energy read is
currently served from BSS MySQL**, and the OSS processes are not in the request path.
Note that `ecosystem.config.js` does not set `OSS_ENABLED` either — so even under PM2 the
stack runs BSS-only until `backend/.env` is changed.

---

## 2. Backend structure

```
backend/app/
├── main.py                   create_app(): CORS, error handlers, router mount, /health
├── core/
│   ├── config.py             Settings (pydantic-settings); vault-backed MYSQL_* properties
│   ├── vault.py              KeePass credential provider (etc/hmsBackend.kdbx)
│   ├── security.py           bcrypt verify + JWT mint/decode
│   ├── platform.py           role_type -> client application boundary
│   ├── oss_routes.py         SINGLE source of truth for which paths are OSS
│   └── version.py            API_VERSION
├── api/
│   ├── deps.py               DbSession, get_current_user, require_permission
│   ├── errors.py             the one error envelope + exception handlers
│   ├── write_errors.py       domain errors (Conflict/NotFound/Invalid) -> HTTP
│   └── v1/
│       ├── router.py         aggregate router; OSS dispatch decided HERE at import
│       └── endpoints/        23 modules (HTTP only: validate, gate, delegate)
├── services/                 28 modules — all business logic and all SQL
├── models/                   16 modules, 95 declared tables (SQLAlchemy 2.0 Mapped[])
├── schemas/                  Pydantic request/response contracts
└── db/
    ├── session.py            engine, SessionLocal, get_db
    └── base.py               declarative Base
```

The layering rule holds throughout: **endpoints never emit SQL, services never raise
`HTTPException`.** Services raise the domain errors in `app/services/writes.py`
(`NotFound`, `Conflict`, `Invalid`), which `app/api/write_errors.py` maps to 404/409/422.

---

## 3. Database integration (BSS MySQL)

### 3.1 Credential path

Credentials are **not** in `.env`. `app/core/config.py:82-100` exposes `MYSQL_USER`,
`MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE` as **properties** backed by
a KeePass vault:

```
etc/shibboleth.zip -> shibboleth.txt   (master password)
        ↓
etc/hmsBackend.kdbx, entry "MYSQL_BSS"
        ↓  app/core/vault.py:152  get_mysql_credentials()
MySQLCredentials(host, port, username, password, database, ssl_ca)
        ↓  app/core/config.py:15  _bss_credentials()   @lru_cache
settings.sqlalchemy_url  ->  URL.create("mysql+pymysql", ...)
```

`_bss_credentials()` is `@lru_cache`d because opening the vault derives a key from the
master password — deliberately slow, so per-property-access would cost every request.
`.env` sets `extra="ignore"`, so a stray `MYSQL_HOST=` there is silently dropped rather
than overriding the vault.

### 3.2 Engine

`app/db/session.py:17-30`:

```python
CONNECT_ARGS: dict = {
    "init_command": "SET time_zone = '+00:00'",
    **settings.mysql_ssl_args,          # ssl_ca, ssl_verify_cert, ssl_verify_identity
}
engine = create_engine(
    settings.sqlalchemy_url,
    connect_args=CONNECT_ARGS,
    isolation_level="READ COMMITTED",   # MySQL default REPEATABLE READ would pin each
                                        # session to its first snapshot
    pool_pre_ping=True,
    echo=settings.DEBUG and settings.APP_ENV == "development",
)
```

`migrations/env.py:65` imports the same `CONNECT_ARGS`, so Alembic connects with identical
transport settings — there is no second place TLS could drift.

Verified in this study: cipher `TLS_AES_256_GCM_SHA384`, both `ssl_verify_cert` and
`ssl_verify_identity` true.

### 3.3 Session lifecycle

`get_db()` (`app/db/session.py:35`) yields a session and closes it in `finally`. It does
**not** commit — commits happen only inside `transaction()`
(`app/services/writes.py:56`), which gives one commit per unit of work and rolls back on
any exception, so a multi-table workflow cannot half-apply.

---

## 4. Authentication and authorisation

### 4.1 Login — `POST /api/v1/auth/login`

```
endpoints/auth.py
  └─> services/auth.py:88  authenticate(db, username, password)
        ├─ SELECT app_user WHERE user_name = :username
        ├─ core/security.py:51  verify_password(plain, user.password_hash)   bcrypt
        ├─ _role_types(): SELECT role.role_type JOIN user_role
        ├─ core/platform.py  is_hms_web_role()  -> admin|manager only
        └─ _build(): roles + facility_ids + permissions from services/access.py
  └─> core/security.py:80  create_access_token(user.id)
```

Two deliberate ordering decisions:

1. **Credentials are checked before the platform boundary** (`services/auth.py:89-95`), so a
   wrong password and an unknown username are indistinguishable. Only a caller who already
   proved they own the account learns it belongs to a different application.
2. **The token carries identity only** — `{"sub", "typ", "iat", "exp"}`. No role, no
   permission, no email. Authorization is re-read from the database on *every* request, so
   a revoked grant takes effect immediately rather than at token expiry.

### 4.2 Per-request authorisation

```
HTTPBearer(auto_error=False)        deps.py:30 — so a missing header gets OUR 401 envelope
  └─> decode_access_token()         signature + exp + typ=="access" + sub is a UUID
  └─> load_hms_web_user(db, id)     re-reads user AND role_types; None if either is gone
  └─> require_permission(module, perm)  -> AuthenticatedUser.may()
          reads role_module_permission.read_access / .write_access
```

`require_permission` (`deps.py:69`) rejects any permission other than `read`/`write` at
*construction* time with a `ValueError`, because `role_module_permission` has no other
access column — a typo fails at import, not at request time.

Module names are not hardcoded: the registry is `role_module.module_name`. Live values
(18 modules, 65 grant rows):

```
bookings, caleido_network, dashboard, default_key, employees, events,
facility_management, firmware_management, holidays, job_order, occupancy,
offers, reports, service_planning, service_setup, service_tracking,
tickets, user_roles
```

### 4.3 Platform boundary

`app/core/platform.py` gates on `role.role_type` (a constrained ENUM), not role display
names, because names are free text an operator can rename. `admin` and `manager` reach HMS
Web; `staff` and `guest` belong to the mobile apps; `system_user` is excluded from
interactive login entirely.

### 4.4 Captured auth behaviour

```http
GET /api/v1/devices                      →  401
{"error":{"code":"unauthorized","message":"Not authenticated."}}

POST /api/v1/auth/login                  →  401
{"username":"admin","password":"admin"}
{"error":{"code":"unauthorized","message":"Invalid username or password."}}

GET /api/v1/devices                      →  401
Authorization: Bearer not.a.token
{"error":{"code":"unauthorized","message":"Not authenticated."}}
```

A malformed token and a missing token are intentionally identical responses.

With a valid token (`arjun.menon`, role_type `admin`):

```http
GET /api/v1/auth/me                      →  200
{"id":"2b46adbb-…","user_name":"arjun.menon","platform":"hms_web",
 "role_types":["admin"],
 "roles":[{"role_name":"Administrator","role_type":"admin","facility_id":"e19799cd-…"}],
 "facility_ids":["e19799cd-…"],
 "permissions":[{"module_id":1,"module_name":"dashboard","read_access":true,
                 "write_access":true,"granted_by_roles":["Administrator"]}, …]}
```

---

## 5. Routing and the OSS dispatch switch

### 5.1 Where "OSS or BSS?" is decided

`app/core/oss_routes.py` is the single source of truth. Nothing else in the codebase
decides domain ownership:

| OSS domain | v1 prefixes | Served by |
|---|---|---|
| `device` | `/device-types`, `/devices` | `hms-oss-device` :8001 |
| `telemetry` | `/device-params`, `/device-stats`, `/device-current-stats`, `/other-device-readings` | `hms-oss-telemetry` :8002 |
| `alert` | `/alert-types`, `/alerts` | `hms-oss-alert` :8003 |
| `energy` | `/energy-stats` | `hms-oss-energy` :8004 |

Deliberately **not** OSS, and documented as such in that module:
`/daily-data-points` (mixed KPIs), `/incidents` and `/value-alerts` (OSS has no incident or
threshold-breach table), and all device **writes**.

### 5.2 Dispatch is a mount-time decision

This is the single most important structural fact about the routing layer.
`app/api/v1/router.py` reads `settings.OSS_ENABLED` **at import**, and mounts one of two
disjoint router sets:

```python
if not settings.OSS_ENABLED:                    # router.py:78
    api_router.include_router(devices.device_types_router)
    api_router.include_router(devices.devices_router)
...
if settings.OSS_ENABLED:                        # router.py:144
    for _oss_router in oss_proxy.oss_proxy_routers:
        api_router.include_router(_oss_router)
```

Consequences worth being explicit about:

- There is **no per-request branch** — zero dispatch cost, and no possibility of a request
  taking a half-OSS path.
- The OpenAPI schema differs between the two modes. The 142 paths measured here are the
  `OSS_ENABLED=false` surface.
- **Flipping `OSS_ENABLED` requires a process restart.** It is a deployment decision, not a
  runtime toggle.
- Rollback is symmetric and total: set it back to `false`, restart, and device reads resume
  from MySQL.

### 5.3 The proxy keeps the security boundary in HMS

`app/api/v1/endpoints/oss_proxy.py:42` `_build()` constructs each proxy router with the
**same path and the same `require_permission` gate** as the local router it replaces:

```python
router = APIRouter(prefix=prefix, tags=["oss-proxy"],
                   dependencies=[Depends(require_permission(module, permission))])
```

So HMS authenticates and authorises **before** forwarding; the OSS service never sees an
unauthenticated caller. OSS's own routers carry no `require_permission`
(`oss-service/app/api/router.py` docstring) — they trust that HMS already gated.

Only GETs are registered (`methods=["GET"]`), so no write can ever be forwarded. Query
strings are relayed with `request.query_params.multi_items()` rather than a dict, so
repeated keys (`?status=1&status=2`) survive instead of silently collapsing to the last
value.

`/energy-stats` is gated on `reports` rather than `caleido_network`, matching the local
energy router it replaces.

### 5.4 Failure policy

`app/services/oss_client.py:40` `forward()` distinguishes two failures that must not be
conflated:

- **Transport error or timeout** → raises `OssUnavailable` → `_relay` returns
  `503 {"code": "oss_unavailable"}`.
- **A 4xx/5xx from OSS itself** → passed through verbatim, status and envelope intact.

The per-domain URL is resolved per request path:
`settings.oss_url_for(oss_domain_for(subpath))`, falling back to `OSS_SERVICE_URL`. A
single unreachable domain therefore degrades only its own routes.

---

## 6. Traced execution paths

### 6.1 BSS read — `GET /api/v1/devices` (current mode, `OSS_ENABLED=false`)

```
Browser  fetch("/api/v1/devices?page_size=2", {Authorization: Bearer …})
  │        frontend/src/lib/api/client.ts:160  request<T>()
  ▼
Vite proxy  /api/v1 -> http://127.0.0.1:8000     vite.config.ts:23
  ▼
CORSMiddleware                                    main.py:47
  ▼
devices_router  (prefix="/devices")               endpoints/devices.py:66
  ├─ Depends(require_permission("caleido_network","read"))
  │     └─ get_current_user -> decode JWT -> load_hms_web_user(db, id)
  │           └─ SELECT app_user / role / user_role / role_module_permission
  ├─ Query validation: page>=1, page_size<=MAX_PAGE_SIZE, enum filters as Literal
  ▼
services/device.py  list_devices(db, …)
  └─ SELECT device
       JOIN device_type
       LEFT JOIN amenity        (room)
       LEFT JOIN property_chain -> Property level_one (building) / level_two (floor)
  ▼
schemas/device.py  DeviceRead  ->  Page[DeviceRead]
  ▼
JSON 200
```

Captured response (truncated):

```json
{"items":[{"id":"a5a1ddba-760a-58de-a07f-451d3e31f254",
           "device_uid":"DEV101AIR","device_name":"101",
           "appliance_name":"Air Quality Sensor","device_type":2,
           "device_type_name":"AirQ","device_short_code":"AIR",
           "facility_id":"e19799cd-…","amenity_id":"732f9bbf-…","amenity_name":"101",
           "building_id":"165b288b-…","building_name":"Tower A",
           "floor_id":"31e838fc-…","floor_name":"Floor 1",
           "health_status":"Active","device_config_status":"commissioned",
           "device_temperature":"34.10","is_power_off":false}],
 "page":1,"page_size":20,"total":…}
```

Note `building_name` / `floor_name`: the BSS path resolves location through
`amenity → property_chain → property`, the same projection `room_devices.py` uses.

### 6.2 OSS composed read — `GET /api/v1/devices?amenity_id=…` (`OSS_ENABLED=true`)

This is the one genuinely composed route. OSS has no room concept, so HMS answers the
location half itself.

```
 Frontend          HMS backend (:8000)              BSS MySQL        OSS device svc (:8001)
    │                     │                             │                      │
    │ GET /devices?amenity_id=X                         │                      │
    ├────────────────────▶│                             │                      │
    │                     │ require_permission(caleido_network, read)          │
    │                     ├────────────────────────────▶│  app_user/role/perm  │
    │                     │◀────────────────────────────┤                      │
    │                     │                             │                      │
    │                     │ room_devices.device_ids_at(db, amenity_id=X)       │
    │                     ├────────────────────────────▶│  room_device_map     │
    │                     │◀──── [oss uuid, …] ─────────┤                      │
    │                     │                             │                      │
    │                     │   if empty -> {"items":[],"total":0}  (OSS not called)
    │                     │                             │                      │
    │                     │ GET /devices?device_ids=uuid,uuid                  │
    │                     ├───────────────────────────────────────────────────▶│
    │                     │                             │        SELECT insp_device
    │                     │◀──────────── 200 {items:[…]} ──────────────────────┤
    │                     │                             │                      │
    │                     │ _with_locations(db, items)  │                      │
    │                     ├────────────────────────────▶│  room_device_map +   │
    │                     │◀──── room/floor/building ───┤  amenity+property    │
    │◀─── 200 merged ─────┤                             │                      │
```

Implementation: `oss_proxy.py:86` `list_devices` strips `LOCATION_FILTERS`
(`amenity_id`, `floor_id`, `building_id`, `facility_id`) from the forwarded query, resolves
them against `room_device_map`, and appends `device_ids=…`. If the room has no mapped
devices it short-circuits and **never calls OSS** (`oss_proxy.py:107`). On the way back,
`_with_locations` (`oss_proxy.py:68`) fills room/floor/building; devices with no mapping
keep the nulls OSS sent, because HMS genuinely does not know their room.

### 6.3 Write path — `POST /api/v1/room-devices` (BSS write + OSS read)

```
endpoints/room_devices.py
  └─ require_permission("caleido_network","write")
  └─ services/room_devices.py:131  assign_device(db, amenity_id, oss_device_id, actor_id)
       ├─ require_exists(db, Amenity, amenity_id, "Room")          -> Invalid  -> 422
       ├─ SELECT room_device_map WHERE oss_device_id = …           -> Conflict -> 409
       ├─ oss_client.forward("GET", f"/devices/{oss_device_id}")
       │     404 -> Invalid("does not exist in OSS")               -> 422
       │     not 200 -> OssUnavailable                             -> 503
       └─ with transaction(db):  db.add(RoomDeviceMap(...))        -> one commit
```

The OSS read before the BSS write is the integrity rule: a mapping is never created to a
device nobody has verified exists. HMS still writes **only** its own table — OSS remains
read-only throughout.

---

## 7. Error handling

One envelope for every failure (`app/api/errors.py:38`):

```json
{"error": {"code": "not_found", "message": "…", "detail": …}}
```

Handlers, in `install_exception_handlers`:

| Exception | Status | Rationale |
|---|---:|---|
| `StarletteHTTPException` | as raised | `detail` string → `message`; non-string → `detail` |
| `RequestValidationError` | 422 | normalised to `[{loc, msg, type}]` |
| `DataError` | 422 | a bad **value** (bad enum label, malformed timestamp) is a bad request — must not read as an outage, or the client retries something that can never work |
| `SQLAlchemyError` | 503 | the request is fine, the dependency is not ready |
| `Exception` | 500 | logged in full server-side, never leaked to the client |

`app/api/write_errors.py` adds the domain mappings: `NotFound`→404, `Conflict`→409,
`Invalid`→422.

The frontend mirrors this exactly: `ApiError` (`client.ts:40`) exposes `isUnauthorized`,
`isForbidden`, `isNotFound`, `isConflict`, `isValidation`, `isServerError`,
`isNetworkError` (status 0), and `fieldErrors` — which walks `detail[].loc` backwards to
find the field name, so a 422 lands next to the right input. A 401 dispatches
`hms:unauthorized`, which `AuthContext` listens for to sign the user out; login passes
`skipAuthRedirect` so a failed sign-in does not trigger it.

---

## 8. Health and observability

| Endpoint | Probe type | Touches DB | Behaviour |
|---|---|---|---|
| `GET /health` | liveness | no | always 200 while the process is up |
| `GET /api/v1/health/db` | readiness | yes | `SELECT 1` + database/version/alembic; 503 if unreachable |
| `GET /api/v1/health/oss` | dependency | no | probes each OSS domain's `/health`; 503 if any is down |
| `GET /api/v1/health/version` | info | no | served under `/api/v1` so the frontend reaches it through its configured base |

The liveness/readiness split is deliberate (`endpoints/health.py` docstring): a database
blip must not make an orchestrator kill a healthy process, while anything that genuinely
gates on the database gates on `/health/db`.

Captured with `OSS_ENABLED=false`:

```json
GET /health                  200  {"status":"ok","app":"HMS Backend","env":"development","version":"0.3.0"}
GET /api/v1/health/db        200  {"status":"ok","database":"inspironics_app",
                                   "server_version":"8.4.13","alembic_revision":"a3f1c8e2d904",
                                   "latency_ms":145.49}
GET /api/v1/health/oss       200  {"enabled":false,"status":"disabled","domains":[]}
```

---

## 9. Findings

Observations from tracing. **All are reported only — nothing was changed.**

### 9.1 No account can authenticate (blocking)

`services/auth.credential_availability()` against the live database:

```json
{"accounts": 18, "with_usable_credential": 0, "usable_usernames": []}
```

Every seeded `app_user.password_hash` holds the literal `!seed-no-login` or NULL.
`core/security.py:51` `verify_password` returns False for those by design, so
`POST /auth/login` returns 401 for every account — confirmed live. **The entire
authenticated API surface — 181 of 186 operations — is unreachable through the front door
with current data.** Exactly five operations answer without a token:

```
GET  /health                     GET  /api/v1/health/db
GET  /api/v1/health/version      GET  /api/v1/health/oss
POST /api/v1/auth/login          (and it rejects every credential)
```

This is documented, intended Phase-2.4 behaviour (the seed deliberately never wrote a
usable credential), but it means no end-to-end frontend flow can be exercised until an
operator provisions a credential with `core/security.hash_password()`.

### 9.2 `GET /api/v1/currencies` returns 503 — missing table

Reproduced live:

```http
GET /api/v1/currencies    →  503
{"error":{"code":"service_unavailable","message":"Database is unavailable."}}
```

Server log:

```
pymysql.err.ProgrammingError: (1146, "Table 'inspironics_app.currency' doesn't exist")
```

`router.py:32` mounts `facilities.currencies_router`, and `models/facility.py:248` declares
`class Currency` with `__tablename__ = "currency"` — but that table is not in the database.
Four models declare a `currency_id` FK to it (`Facility`, `Package`, `ServiceCategoryItem`,
`Stay`); only `facility.currency_id` exists as a column, unconstrained.

Two distinct problems here:

1. The endpoint is permanently broken against this schema.
2. **The error is misleading.** The `SQLAlchemyError` handler maps a missing *table* to
   503 "Database is unavailable" — but the database is perfectly healthy. An operator
   following that message would investigate connectivity and find nothing wrong. A missing
   relation is a deployment/migration defect, not an outage.

`room_status_condition_applicability` (`models/amenity.py:173`) has the same drift, though
no endpoint currently reaches it.

### 9.3 PostgreSQL leftovers in a MySQL-only codebase

The BSS database is MySQL and only MySQL (`config.py` removes the engine switch
explicitly), but Postgres assumptions survive in two places:

- **Functional:** `services/writes.py:77` `_constraint_name()` reads
  `exc.orig.diag.constraint_name` — the psycopg2 diagnostics API. PyMySQL has no `.diag`,
  so this always returns `None` via `getattr` defaults. It degrades safely (the 409 is
  still raised, just without the constraint name), but the enrichment it exists to provide
  never fires on MySQL.
- **Documentary:** `deps.py:47` ("load the user from PostgreSQL"), `services/auth.py:3`
  ("read live from PostgreSQL"), `core/security.py:87` ("re-read from PostgreSQL"),
  `errors.py:75` ("PostgreSQL rejected a VALUE"), `writes.py:58` ("one PostgreSQL
  transaction"), and `main.py:37` (the app description still advertises "the seeded
  PostgreSQL data"). The last one is user-visible — it appears in `/docs` and
  `/openapi.json`.

### 9.4 The OSS bridge is empty

`room_device_map` has **0 rows** — confirmed live via `GET /api/v1/room-devices`
→ `{"items":[],"total":0}`. It is the only mechanism by which a room acquires devices when
`OSS_ENABLED=true`. Turning OSS on today would make `/devices?amenity_id=…` short-circuit
to an empty list for every room (`oss_proxy.py:107`) without ever calling OSS, and
unfiltered `/devices` would return OSS devices with null room/floor/building.

### 9.5 Four OSS-routed surfaces have no OSS source

Per `oss-service/docs/INTEGRATION_MAPPING.md`, with `OSS_ENABLED=true`:
`/other-device-readings` and `/energy-stats` return **503**, and device battery/operation
history return `[]`. Those four surfaces are backed by real BSS rows today
(`other_device` 12, `energy_stat` 72, `battery_life_stat` 12, `sensor_operation_stat` 42 —
138 rows). Enabling OSS dispatch silently stops serving them. See
[OSS_BSS_TABLE_AUDIT.md](../database/OSS_BSS_TABLE_AUDIT.md) for the table-level analysis.

### 9.6 Inter-service auth is off by default

`OSS_SERVICE_TOKEN` is unset, so `X-OSS-Service-Token` is not sent and
`oss-service/app/api/security.py` `require_service_token` is a no-op. The OSS data routes
are readable by anything that can reach :8001–:8004. This is a deliberate trusted-LAN PoC
choice and it **fails closed outside development**: `oss-service/app/main.py:28` refuses to
start when `APP_ENV != "development"` without a token. Worth stating plainly because the
OSS services bind to `127.0.0.1` by default — the protection today is the bind address,
not the token.

### 9.7 Study limitation

The OSS PostgreSQL `insp_iot` was **not reachable** — `oss-service/.env` does not exist
(only `.env.example` with a blank `OSS_DATABASE_URL`). All OSS-side behaviour described
here is traced from source (`oss-service/app/`) and its committed docs, not observed. The
OSS proxy path in §6.2 is read from `oss_proxy.py` and was **not executed**, because
`OSS_ENABLED=false` means those routers are not mounted. To validate it end to end you
would need OSS credentials, `OSS_ENABLED=true`, and a backend restart.

---

## 10. Design decisions worth preserving

Things this codebase does deliberately that are easy to break by accident:

1. **One source of truth for domain ownership** — `core/oss_routes.py`. Dispatch, tests and
   docs all read it; nothing re-derives "is this OSS?" from a path string.
2. **The security boundary does not move with the data.** The OSS proxy re-declares the
   same `require_permission` gate as the local router it replaces, so forwarding never
   widens access.
3. **Tokens carry identity only.** Authorization is re-read per request, so revocation is
   immediate.
4. **Credentials live in one encrypted file**, not scattered across `.env`, shell history
   and screenshots — and `.env` holds nothing that can reach the database.
5. **A missing CA bundle is reported as a missing file**, not as a TLS handshake failure
   (`config.py:177`) — the one case an operator must not confuse for an untrusted server.
6. **`ssl={}` is never used.** PyMySQL treats an empty dict as falsy and silently gives a
   plaintext socket; the unverified branch passes real keys instead (`config.py:200`).
7. **Writes are one commit per request.** `transaction()` rolls back everything on any
   failure, so no workflow half-applies.
8. **Nothing is fabricated across the OSS boundary.** Fields with no OSS source are `null`
   and documented; resources with no source return an explicit 503 rather than invented
   data.
