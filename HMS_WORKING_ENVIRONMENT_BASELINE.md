# HMS WORKING ENVIRONMENT BASELINE

**Authoritative reference environment for the ACX Platform / HMS project.**

| | |
|---|---|
| Machine role | KNOWN-WORKING HMS reference environment |
| Captured | 2026-09-18 |
| Repository root | `C:\inspironics total work\ACX Platform\ACX-Platform` |
| Method | Read-only inspection. No code, file, database row, environment variable, Git ref or configuration was modified. No migration, seed or password command was run. |

> **THE ONE-LINE ANSWER.** `ask@inspironics.net` logs in because a row in
> `app_user` has **`user_name` = `ask@inspironics.net`** (not just `email`) and
> carries a **real `$2b$` bcrypt hash**. It is the **only** account in the
> database with a usable credential. It was **not created by the seed** — the
> seed writes the literal `!seed-no-login` into every row it creates. A fresh
> clone that runs `alembic upgrade head` + `python -m seeds.run_seed` will
> therefore have **zero** accounts that can log in, even though its source code
> is byte-identical to this one. See section M.

---

## A. GIT BASELINE

### A.1 Identity

| Item | Value |
|---|---|
| Repository root | `C:/inspironics total work/ACX Platform/ACX-Platform` |
| Current branch | `develop` |
| **HEAD commit (exact hash in use)** | **`5625e812f2ca253b66a9256b2879b78c108ba096`** |
| HEAD short | `5625e81` |
| HEAD subject | `Merge branch 'feature/current-ui' into develop` |
| HEAD author | Siddharth92082225027 &lt;153817702+Siddharth92082225027@users.noreply.github.com&gt; |
| HEAD date | Thu Sep 17 12:33:58 2026 +0530 |
| Remote `origin` (fetch/push) | `https://github.com/ramanag0119/ACX-Platform` |
| Tracking branch | `origin/develop` |
| Default remote HEAD | `origin/main` |

### A.2 Comparison against origin

```
git rev-list --left-right --count origin/develop...develop
0	0
```

**0 behind, 0 ahead.** `git diff origin/develop..develop` returns nothing — the
local `develop` tree is identical to `origin/develop`. All divergence from the
remote is in the **working tree only** (uncommitted), listed below.

Local branches:

| Branch | Commit | Tracking |
|---|---|---|
| `develop` *(current)* | `5625e81` | `origin/develop` — in sync |
| `feature/current-ui` | `2370293` | `origin/feature/current-ui` |
| `feature/dashboard-acx` | `e83d9d6` | *(local only)* |
| `main` | `104d090` | `origin/main` — **behind 65** |

### A.3 Working tree status

`git status --porcelain` — **20 modified, 5 untracked, 0 staged, 0 deleted.**

**Modified (all frontend presentation; none touch auth, API or DB):**

```
frontend/src/features/bookings/pages/Bookings.tsx
frontend/src/features/config/pages/FacilityManagement.tsx
frontend/src/features/config/pages/JobOrder.tsx
frontend/src/features/config/pages/LimitConfigAlert.tsx
frontend/src/features/config/pages/UserRoles.tsx
frontend/src/features/dashboard/components/AlertsPanel.tsx
frontend/src/features/dashboard/components/CaleidoAtWork.tsx
frontend/src/features/dashboard/components/DashboardKPIs.tsx
frontend/src/features/dashboard/components/RecentActivityPanel.tsx
frontend/src/features/dashboard/pages/Dashboard.tsx
frontend/src/features/marketing/pages/Events.tsx
frontend/src/features/marketing/pages/Holidays.tsx
frontend/src/features/marketing/pages/Offers.tsx
frontend/src/features/occupancy/components/OccupancyStatisticsChart.tsx
frontend/src/features/occupancy/pages/Occupancy.tsx
frontend/src/features/reports/pages/Reports.tsx
frontend/src/features/services/pages/ServicePlanning.tsx
frontend/src/features/services/pages/ServiceTracking.tsx
frontend/src/features/tickets/pages/Tickets.tsx
frontend/src/index.css
```

**Untracked (excluding ignored):**

```
frontend/src/features/dashboard/data/energyConsumption.ts
frontend/src/hooks/use-scroll-to-top.ts
package-lock.json                          <- root stub, 91 bytes, empty "packages"
scripts/Enable-PostgresLanAccess.ps1
src/features/dashboard/components/EnergyConsumptionChart.tsx   <- stray, outside frontend/
```

**Ignored but present and load-bearing** (see section K):
`backend/.env`, `frontend/.env.local`, `backend/.venv/`, `frontend/node_modules/`.

### A.4 Tracked files

**307 tracked files.** The complete list is in **Appendix 1**.

---

## B. BACKEND ENVIRONMENT BASELINE

### B.1 `backend/.env` — variable names and presence

`backend/.env` is **git-ignored** (`backend/.gitignore` lines 1–4: `.env`,
`.env.*`, `!.env.example`). It exists locally and is the active configuration.

| Variable | Present | Value / disclosure |
|---|---|---|
| `POSTGRES_USER` | yes | `postgres` |
| `POSTGRES_PASSWORD` | **yes — value exists, non-empty. Not disclosed.** | *(redacted)* |
| `POSTGRES_HOST` | yes | `localhost` |
| `POSTGRES_PORT` | yes | `5432` |
| `POSTGRES_DB` | yes | `hms_db` |
| `POSTGRES_SCHEMA` | yes | `public` |
| `DATABASE_URL` | **COMMENTED OUT — INACTIVE** | The line exists but is prefixed with `#`. `settings.DATABASE_URL` resolves to `None`, so the URL is assembled from the six `POSTGRES_*` parts above. |
| `APP_NAME` | yes | `HMS Backend` |
| `APP_ENV` | yes | `development` |
| `DEBUG` | yes | `true` |
| `JWT_SECRET_KEY` | **yes — PLACEHOLDER, not a custom secret** | It is the literal value shipped in `.env.example` (30 characters, the `change_me...` placeholder). It is **not** the code-level dev default in `config.py` (`dev-only-insecure-secret-change-me`), so `assert_production_ready()` does not fire. **It is still a placeholder and is byte-identical to `.env.example`, which means a fresh clone copying `.env.example` gets the SAME signing key. See N.10.** |
| `JWT_ALGORITHM` | yes | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | yes | `60` |

**`CORS_ORIGINS` is NOT set in `.env`.** It falls back to the `config.py`
default: `http://localhost:8080`, `http://127.0.0.1:8080`,
`http://localhost:5173`, `http://127.0.0.1:5173`.

**`backend/.env` vs `backend/.env.example`:** structurally identical, same keys
in the same order. The only differences are the two secret values
(`POSTGRES_PASSWORD`, and the commented `DATABASE_URL` line which embeds it).
`JWT_SECRET_KEY` is **byte-identical** between the two files.

### B.2 Python

| Item | Value |
|---|---|
| **Virtual-environment Python** | **3.13.15** (`backend/.venv/Scripts/python.exe`) |
| System Python on PATH | 3.14.5 (`python` and `py` both) |
| venv location | `backend/.venv/` — git-ignored |

> The venv Python (3.13) and the system Python (3.14) differ. The venv is what
> actually runs the backend.

### B.3 `backend/requirements.txt` (tracked, verbatim pins)

```
fastapi==0.135.3
uvicorn[standard]==0.34.0
sqlalchemy==2.0.52
alembic==1.19.1
psycopg2-binary==2.9.11
pydantic==2.12.5
pydantic-settings==2.7.1
python-dotenv==1.0.1
pytest==9.1.1
httpx==0.28.1
python-jose[cryptography]==3.5.0
bcrypt==5.0.0
openpyxl==3.1.5
```

### B.4 Key installed versions (verified against the live venv)

| Package | Installed | Matches requirements.txt |
|---|---|---|
| **FastAPI** | **0.135.3** | yes |
| **Uvicorn** | **0.34.0** | yes |
| **SQLAlchemy** | **2.0.52** | yes |
| **Alembic** | **1.19.1** | yes |
| **psycopg2-binary** | **2.9.11** | yes |
| **bcrypt** | **5.0.0** | yes |
| python-jose | 3.5.0 | yes |
| pydantic | 2.12.5 | yes |
| pydantic-settings | 2.7.1 | yes |
| python-dotenv | 1.0.1 | yes |
| pytest | 9.1.1 | yes |
| httpx | 0.28.1 | yes |
| openpyxl | 3.1.5 | yes |

**Every pinned requirement is installed at exactly its pinned version.**

Full `pip freeze` (47 packages, including transitive):

```
alembic==1.19.1              annotated-doc==0.0.5         annotated-types==0.8.0
anyio==4.15.0                bcrypt==5.0.0                certifi==2026.7.22
cffi==2.1.1                  click==8.5.0                 colorama==0.4.6
cryptography==50.0.1         ecdsa==0.19.2                et_xmlfile==2.0.0
fastapi==0.135.3             greenlet==3.5.5              h11==0.16.0
httpcore==1.0.9              httptools==0.8.0             httpx==0.28.1
idna==3.19                   iniconfig==2.3.0             Mako==1.4.1
MarkupSafe==3.0.3            openpyxl==3.1.5              packaging==26.3
pluggy==1.6.0                psycopg2-binary==2.9.11      pyasn1==0.6.4
pycparser==3.0               pydantic==2.12.5             pydantic-settings==2.7.1
pydantic_core==2.41.5        Pygments==2.21.0             pytest==9.1.1
python-dotenv==1.0.1         python-jose==3.5.0           PyYAML==6.0.3
rsa==4.9.1                   six==1.17.0                  SQLAlchemy==2.0.52
starlette==1.6.0             typing-inspection==0.4.4     typing_extensions==4.16.0
uvicorn==0.34.0              watchfiles==1.2.0            websockets==17.1
```

### B.5 Alembic configuration

| Item | Value |
|---|---|
| `alembic.ini` → `script_location` | `%(here)s/migrations` |
| `alembic.ini` → `sqlalchemy.url` | **not set in the ini file** |
| URL source | `backend/migrations/env.py:18` — `config.set_main_option("sqlalchemy.url", settings.sqlalchemy_url)`. The URL comes from `.env` via `app.core.config`, never from `alembic.ini`. |
| Version table schema | `settings.POSTGRES_SCHEMA` → `public` |
| Migration files | **one**: `0e2687233b59_phase1_7_hms_92_table_foundation.py` |
| revision / down_revision | `0e2687233b59` / `None` (single-revision chain) |

---

## C. FRONTEND ENVIRONMENT BASELINE

### C.1 Runtime

| Item | Value |
|---|---|
| **Node** | **v24.9.0** |
| **npm** | **11.6.0** |

> `RUN_REPORT.md` claims Node v20.11.0 / npm 10.2.4 were the verified versions.
> The machine is actually on Node 24. The document is stale; the machine works.

### C.2 `frontend/.env.local`

Git-ignored via the root `.gitignore` pattern `*.local`. It is a **verbatim
copy of `frontend/.env.example`** — no edits, no secrets, nothing machine-
specific. Both variables are non-secret and are given in full:

| Variable | Value |
|---|---|
| **`VITE_API_BASE_URL`** | **`/api/v1`** (relative — no host, so the Vite dev proxy handles it and CORS is never involved) |
| **`VITE_API_PROXY_TARGET`** | **`http://127.0.0.1:8000`** |

No secrets exist in any frontend env file.

### C.3 Vite dev server (`frontend/vite.config.ts`)

| Item | Value |
|---|---|
| `server.host` | `::` (all interfaces) |
| **`server.port`** | **8080** |
| Proxy rule | `/api/v1` → `env.VITE_API_PROXY_TARGET` (fallback `http://127.0.0.1:8000`), `changeOrigin: true` |
| Alias | `@` → `./src` |
| Plugins | `@vitejs/plugin-react-swc`, plus `lovable-tagger` in development mode only |

### C.4 Package manifest and lockfile

| Item | Value |
|---|---|
| `frontend/package.json` | tracked. name `vite_react_shadcn_ts`, `"type": "module"`, version `0.0.0` |
| Scripts | `dev` `build` `build:dev` `lint` `preview` |
| **`frontend/package-lock.json`** | **tracked, 245,049 bytes, lockfileVersion 3, 445 resolved packages** |
| Root `package-lock.json` | **untracked, 91 bytes, `"packages": {}` — an empty stub. Not the real lockfile.** |
| Root `node_modules/` | present but **not** the frontend's; the frontend has its own |
| Direct dependencies | 66 (50 `dependencies` + 16 `devDependencies`) |
| Installed vs declared | **66/66 installed, 0 missing, every one satisfying its declared range** |

### C.5 Key installed frontend versions

| Package | Declared | **Installed** |
|---|---|---|
| **vite** | `^5.4.19` | **5.4.19** |
| **react** | `^18.3.1` | **18.3.1** |
| **react-dom** | `^18.3.1` | **18.3.1** |
| **typescript** | `^5.8.3` | **5.8.3** |
| @tanstack/react-query | `^5.83.0` | 5.83.0 |
| react-router-dom | `^6.30.1` | 6.30.1 |
| tailwindcss | `^3.4.17` | 3.4.17 |
| recharts | `^2.15.4` | 2.15.4 |
| zod | `^3.25.76` | 3.25.76 |
| @vitejs/plugin-react-swc | `^3.11.0` | 3.11.0 |

The full 66-package table is in **Appendix 2**.

---

## D. POSTGRESQL BASELINE

### D.1 Which server the backend actually uses

**Two PostgreSQL instances are installed and BOTH are running.** Only one is used.

| Instance | Service | State | **Port** | Data directory | Used by HMS? |
|---|---|---|---|---|---|
| PostgreSQL 17 | `postgresql-x64-17` | Running / Automatic | **5433** | `C:\Program Files\PostgreSQL\17\data` | **NO** |
| **PostgreSQL 18** | `postgresql-x64-18` | Running / Automatic | **5432** | `C:\Program Files\PostgreSQL\18\data` | **YES** |

> This is a real trap for a clone. `POSTGRES_PORT=5432` silently selects the
> **18** instance because 17 was moved to 5433 at install time. A clone that
> installs only PostgreSQL 16 or 17 on 5432 would connect to a *different
> server* using the same config file.

### D.2 Live connection facts (read from the running server)

| Item | Value |
|---|---|
| **`version()`** | **PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit** |
| Host | `localhost` |
| Port | `5432` |
| **Database** | **`hms_db`** |
| **Schema** | **`public`** (the only non-system schema) |
| `search_path` | `"$user", public` |
| **Database user** | **`postgres`** (`current_user` = `postgres`) |
| Data directory | `C:/Program Files/PostgreSQL/18/data` |
| Databases on the server | `Insight-flow`, **`hms_db`**, `postgres` |

### D.3 Active connection-configuration source

The resolution order is defined in `backend/app/core/config.py` →
`Settings.sqlalchemy_url`:

```
if DATABASE_URL is set  ->  use it verbatim
else                    ->  postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}
                            @{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}
```

**`DATABASE_URL` is commented out in `backend/.env`, so it resolves to `None`.**
The URL is therefore **assembled from the six `POSTGRES_*` variables**.

**Effective SQLAlchemy URL (password redacted):**

```
postgresql+psycopg2://postgres:<REDACTED>@localhost:5432/hms_db
```

Engine options (`app/db/session.py`): `pool_pre_ping=True`,
`echo = DEBUG and APP_ENV == "development"` → **SQL echo is ON** in this install.

---

## E. SCHEMA / TABLE BASELINE

### E.1 Totals

| Item | Value |
|---|---|
| **Tables in `public`** | **93** (92 application tables + `alembic_version`) |
| **`alembic_version.version_num`** | **`0e2687233b59`** |
| Migration chain | single revision, `down_revision = None` |
| Non-system schemas | `public` only |

`GET /api/v1/health/db` independently confirms
`alembic_revision: "0e2687233b59"`, `server_version: "18.6"`,
`database: "hms_db"`, `schema_name: "public"`.

### E.2 All 93 table names

```
access_key                      activity                        activity_notifier
activity_role_association       activity_type                   alembic_version
alert_type                      amenity                         amenity_condition
amenity_condition_status        amenity_status                  amenity_type
app_user                        attachment                      battery_life_stat
command_type                    country                         daily_dual_data_point
department                      device                          device_alert
device_command                  device_current_stat             device_health_stat
device_incident                 device_param                    device_stat
device_type                     energy_stat                     entity_type
facility                        facility_event                  facility_user
feature                         firmware                        import_job
incident_event                  incident_history                incident_status
invoice                         job_function                    job_order
job_order_amenity               job_order_device                key_type
lock_activity_log               maintenance_request             maintenance_request_amenity
maintenance_request_assignee    maintenance_request_recurrence  mqtt_broker
mqtt_topic                      notification                    notification_receiver
notification_result             notification_template           occasion
occasion_type                   organisation                    other_device
package                         package_feature                 promo_code
promo_code_amenity              property                        property_chain
property_type                   role                            role_module
role_module_permission          room_allocation                 room_service_request
room_service_request_item       scheduler_job                   scheduler_job_execution
sensor_operation_stat           service_category                service_category_item
service_request                 service_request_item            service_status
service_type                    stay                            stay_package
stay_user                       sub_package                     user_device
user_device_acl                 user_document                   user_role
user_token                      value_alert                     value_alert_limit_config
```

### E.3 `app_user` structure — 29 columns

| # | Column | Data type | Null | Default |
|---:|---|---|---|---|
| 1 | `user_uid` | varchar(72) | NO | |
| 2 | `first_name` | varchar(100) | NO | |
| 3 | `last_name` | varchar(100) | YES | |
| 4 | `email` | varchar(256) | YES | |
| 5 | `country` | smallint | YES | |
| 6 | `phone_number` | varchar(15) | NO | |
| 7 | `alternate_phone_number` | varchar(15) | YES | |
| 8 | `gender` | *enum (USER-DEFINED)* | YES | |
| 9 | `dob` | date | YES | |
| 10 | `is_child` | smallint | NO | `'0'::smallint` |
| 11 | `age` | smallint | YES | |
| 12 | `is_staff` | smallint | YES | `'1'::smallint` |
| 13 | `date_of_joining` | timestamptz | YES | |
| 14 | `date_of_termination` | timestamptz | YES | |
| 15 | `supervisor` | uuid | YES | |
| 16 | `address` | varchar(1000) | YES | |
| 17 | `nationality` | smallint | YES | |
| 18 | `marital_status` | *enum (USER-DEFINED)* | YES | |
| 19 | `job_function_id` | uuid | YES | |
| 20 | `department_id` | uuid | YES | |
| 21 | `emp_id` | varchar(20) | YES | |
| 22 | **`user_name`** | **varchar(100)** | **YES** | — **the login identifier** |
| 23 | **`password_hash`** | **varchar(100)** | **YES** | — **the credential** |
| 24 | `metadata` | jsonb | YES | |
| 25 | `created_by` | uuid | NO | |
| 26 | `legacy_id` | bigint | YES | |
| 27 | `created_on` | timestamptz | NO | `now()` |
| 28 | `updated_on` | timestamptz | NO | `now()` |
| 29 | `id` | uuid | NO | *(primary key)* |

### E.4 `app_user` constraints

| Type | Name | Definition |
|---|---|---|
| PK | `pk_app_user` | `PRIMARY KEY (id)` |
| **UNIQUE** | **`uq_app_user_user_name`** | **`UNIQUE (user_name)`** ← makes `user_name` the only unique login key |
| UNIQUE | `uq_app_user_user_uid` | `UNIQUE (user_uid)` |
| UNIQUE | `uq_app_user_legacy_id` | `UNIQUE (legacy_id)` |
| FK | `fk_app_user_country_country` | `country → country(id) ON DELETE RESTRICT` |
| FK | `fk_app_user_created_by_app_user` | `created_by → app_user(id) ON DELETE RESTRICT` |
| FK | `fk_app_user_department_id_department` | `department_id → department(id) ON DELETE RESTRICT` |
| FK | `fk_app_user_job_function_id_job_function` | `job_function_id → job_function(id) ON DELETE RESTRICT` |
| FK | `fk_app_user_nationality_country` | `nationality → country(id) ON DELETE RESTRICT` |
| FK | `fk_app_user_supervisor_app_user` | `supervisor → app_user(id) ON DELETE RESTRICT` |
| NOT NULL | 8 named constraints | `user_uid`, `first_name`, `phone_number`, `is_child`, `created_by`, `created_on`, `updated_on`, `id` |

> **`email` has NO unique constraint** — only an ordinary btree index. This is
> structural proof that `email` is not, and cannot be, the login key.

### E.5 `app_user` indexes

```
pk_app_user                 UNIQUE btree (id)
uq_app_user_user_name       UNIQUE btree (user_name)     <- login lookup
uq_app_user_user_uid        UNIQUE btree (user_uid)
uq_app_user_legacy_id       UNIQUE btree (legacy_id)
ix_app_user_email           btree (email)                <- NON-unique
ix_app_user_department_id   btree (department_id)
ix_app_user_is_staff        btree (is_staff)
ix_app_user_job_function_id btree (job_function_id)
ix_app_user_phone_number    btree (phone_number)
ix_app_user_metadata_gin    gin (metadata)
```

**There is no index on `password_hash`** — correct; it is never a lookup key.

### E.6 Authentication-relevant indexes on the other tables

```
user_role               pk_user_role  UNIQUE btree (facility_id, app_user_id, role_id)
                        ix_user_role_app_user_id  btree (app_user_id)
                        ix_user_role_role_id      btree (role_id)
role                    pk_role UNIQUE btree (id) · uq_role_legacy_id · ix_role_facility_id
role_module             pk_role_module UNIQUE btree (id)
role_module_permission  pk_role_module_permission UNIQUE btree (role_id, module_id)
                        ix_role_module_permission_module_id btree (module_id)
facility_user           pk_facility_user UNIQUE btree (facility_id, app_user_id)
                        ix_facility_user_app_user_id btree (app_user_id)
user_token              pk_user_token · uq_user_token_token UNIQUE btree (token)
                        uq_user_token_legacy_id · ix_user_token_app_user_id
```

> **`user_token` is NOT used by HMS Web login.** Sessions are stateless JWTs;
> nothing is written to `user_token` at login. Its 3 rows are seed data.

---

## F. AUTHENTICATION BASELINE

### F.1 The login-identifier question — definitive answer

**`backend/app/services/auth.py`, function `authenticate()`:**

```python
user = db.execute(
    select(AppUser).where(AppUser.user_name == username)
).scalar_one_or_none()

if user is None or not verify_password(password, user.password_hash):
    raise AuthError("Invalid username or password.")
```

| Question | Answer |
|---|---|
| Does the login API search by `user_name`? | **YES — exclusively.** |
| Does the login API search by `email`? | **NO. `email` is never referenced in the login path at all.** |
| Does it accept both? | **NO.** Single-column exact match on `user_name`. Case-**sensitive** — there is no `lower()` or `ilike`. |
| Which exact value does the frontend send? | Whatever the user typed in the "Username" text box, verbatim, as JSON `{"username": "...", "password": "..."}`. No trimming, no lowercasing, no `@`-detection. |
| Which backend endpoint receives it? | **`POST /api/v1/auth/login`** |

**Therefore `ask@inspironics.net` works only because that exact string is stored
in the `user_name` column.** It happens to also be the `email` value, but the
`email` column is irrelevant to login. If `user_name` were `NULL` or anything
else, the same address in `email` would produce a 401.

### F.2 Complete traced flow

| # | Step | File | Function / symbol |
|---:|---|---|---|
| 1 | Login page — `username`/`password` state, submit handler | `frontend/src/features/auth/pages/Login.tsx` | `Login`, `handleLogin` |
| 2 | Auth context — calls the API, stores the token, then fetches identity | `frontend/src/core/contexts/AuthContext.tsx` | `AuthProvider`, `login` |
| 3 | Typed endpoint wrapper | `frontend/src/lib/api/endpoints.ts:66` | `login(username, password)` → `apiClient.post<TokenResponse>("/auth/login", {username, password}, {skipAuthRedirect: true})` |
| 4 | HTTP client — headers, error envelope | `frontend/src/lib/api/client.ts` | `request()`, `apiClient.post` |
| 5 | Base URL resolution | `frontend/src/lib/api/client.ts:16` | `API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1")` → **`/api/v1`** |
| 6 | Dev proxy | `frontend/vite.config.ts` | `server.proxy["/api/v1"] → http://127.0.0.1:8000` |
| 7 | **Route** | `backend/app/api/v1/endpoints/auth.py` | `@router.post("/login")` → **`POST /api/v1/auth/login`** |
| 8 | Router mount | `backend/app/api/v1/router.py` + `backend/app/main.py` | `api_router.include_router(auth.router)`; mounted at `settings.API_V1_PREFIX` = `/api/v1` |
| 9 | **Request schema** | `backend/app/schemas/auth.py` | `LoginRequest` — `username: str (1–100)`, `password: str (1–256)`; `__repr__` masks the password |
| 10 | Endpoint handler | `backend/app/api/v1/endpoints/auth.py` | `login(payload, db)` |
| 11 | **User lookup** | `backend/app/services/auth.py` | `authenticate()` → `select(AppUser).where(AppUser.user_name == username)` |
| 12 | **Password verification** | `backend/app/core/security.py` | `verify_password(plain, stored_hash)` → `bcrypt.checkpw(...)`; returns `False` for `NULL`, for `!seed-no-login`, and for any malformed digest — never raises |
| 13 | **Platform gate** (after the credential check) | `backend/app/core/platform.py` + `services/auth.py` | `is_hms_web_role(role_type)`; `HMS_WEB_ROLE_TYPES = {admin, manager}`. Not in the set → **403** |
| 14 | Authorization assembly | `backend/app/services/auth.py` → `app/services/access.py` | `_build()` → `user_roles()`, `user_facility_ids()`, `user_permissions()` |
| 15 | **Token generation** | `backend/app/core/security.py` | `create_access_token(user_id)` — HS256, claims **`sub` (user id), `typ="access"`, `iat`, `exp`** and nothing else. No role, no email, no permission in the token. |
| 16 | Production guard | `backend/app/core/config.py` | `assert_production_ready()` — refuses to sign if `APP_ENV != "development"` and the secret is still `dev-only-insecure-secret-change-me` |
| 17 | **Response** | `backend/app/schemas/auth.py` | `TokenResponse { access_token, token_type: "bearer", expires_in }` |
| 18 | **Frontend token storage** | `frontend/src/lib/api/client.ts` | `setToken()` → **`localStorage["hms.access_token"]`** |
| 19 | Identity fetch | `frontend/src/lib/api/endpoints.ts:73` | `fetchCurrentUser()` → `GET /api/v1/auth/me` |
| 20 | **Authenticated request** | `frontend/src/lib/api/client.ts` | every call sets `Authorization: Bearer <token>`; a 401 dispatches `hms:unauthorized` → `AuthContext` signs out |
| 21 | Server-side token validation | `backend/app/api/deps.py` | `get_current_user()` → `HTTPBearer(auto_error=False)` → `decode_access_token()` → `load_hms_web_user()` |
| 22 | Re-authorization per request | `backend/app/services/auth.py` | `load_hms_web_user()` re-reads roles and permissions from PostgreSQL on **every** request; returns `None` (→ 401) if the user lost their HMS Web role |
| 23 | Module authorization | `backend/app/api/deps.py` | `require_permission(module_name, "read"\|"write")` → 403 on a missing grant |
| 24 | Route guard (client) | `frontend/src/core/components/ProtectedRoute.tsx` | redirects to `/login` when unauthenticated; waits during `isRestoring` |
| 25 | Module guard (client) | `frontend/src/core/components/ModuleGuard.tsx` | per-module read/write gating inside the shell |

### F.3 JWT baseline

| Setting | Live value |
|---|---|
| Algorithm | `HS256` |
| Lifetime | 60 minutes |
| Claims | `sub`, `typ` (`"access"`), `iat`, `exp` — identity only |
| Secret source | `JWT_SECRET_KEY` in `backend/.env` |
| Secret state | **placeholder value, byte-identical to `.env.example`** |
| Storage | `localStorage` key `hms.access_token`; not a cookie, so no CSRF surface |
| Verified | Issue → decode round-trip confirmed in-process against this configuration |

### F.4 Platform boundary (`backend/app/core/platform.py`)

`HMS_WEB_ROLE_TYPES = {"admin", "manager"}`. Credentials are checked **first**,
then the platform gate — so an unknown username and a wrong password are
indistinguishable (both 401), and only a caller who proved ownership learns
their account belongs to a mobile platform (403).

| `role.role_type` | Platform | May log in to HMS Web |
|---|---|---|
| `admin` | `hms_web` | **YES** |
| `manager` | `hms_web` | **YES** |
| `staff` | `mobile` | no — 403 |
| `guest` | `guest_mobile` | no — 403 |
| `system_user` | `service` | no — 403 |

---

## G. `ask@inspironics.net` ACCOUNT BASELINE

**Exactly one row matches** (searched `user_name` AND `email`, both
case-sensitively and case-insensitively).

### G.1 The record

| Field | Value |
|---|---|
| **`user_name`** | **`ask@inspironics.net`** ← **this is why login works** |
| **`email`** | `ask@inspironics.net` (same string, but not used by login) |
| **`id`** | `991fe519-f0e2-4974-b664-52aead94813f` |
| **`user_uid`** | **`operator-44f722df0f5b`** |
| `first_name` | `Sandy` |
| `last_name` | `Inspironics` |
| `is_staff` | `1` |
| `department_id` | **`NULL`** |
| `job_function_id` | **`NULL`** |
| **`created_on`** | **`2026-09-16 11:14:25.465633+05:30`** |

### G.2 Credential

| Property | Finding |
|---|---|
| `password_hash` exists? | **YES — non-NULL, and not the seed sentinel** |
| Algorithm / type | **bcrypt, `$2b$` variant** |
| Cost factor | **12** |
| Length | **60 characters** |
| Pattern *(shape only)* | `$2b$12$` + 22-character salt + 31-character digest |
| `has_usable_credential()` | **True** |
| Plaintext password | **NOT disclosed — never read, never derived, never tested.** |
| Full hash | **NOT disclosed.** |

### G.3 Authorization attached to the account

| Item | Value |
|---|---|
| Role | **Administrator** (`role.name`), `role_type` = **`admin`** |
| Role id | `432125fb-0b8c-590f-b1cb-984624e4eff4` |
| `user_role.facility_id` | `e19799cd-71c4-53a6-8c73-b14edf8b0171` |
| Platform resolved | **`hms_web`** → passes the boundary |
| `role_module_permission` grants | **18** |
| Readable modules | **18 of 18** |
| Writable modules | **18 of 18** |
| **`facility_user` rows** | **0** |

> **`facility_user` = 0 is a real difference from every seeded user** (each of
> the 13 seeded users has one). Consequence: `AuthenticatedUser.facility_ids` is
> empty, so every write endpoint falls through
> `access_write.default_facility_id()` to *"the single oldest facility"*. With
> exactly one facility in this database that is harmless and writes succeed —
> but it is **not** the code path the seeded users take, and it would become
> ambiguous in a multi-facility database.

### G.4 Provenance — where this account came from

**It was NOT created by the seed.** Eight independent lines of evidence:

1. **`user_uid` = `operator-44f722df0f5b`.** Every seeded user has
   `user_uid = "demo-uid-<key>"` (`seeds/steps/people.py`). The API's own
   generator produces the `PE00001` style
   (`access_write.create_user` → `next_reference(..., "PE", width=5)`).
   `operator-<hex>` matches **neither** — it was supplied explicitly by whoever
   created the row.
2. **Timestamp gap.** All 13 seeded rows share
   `created_on = 2026-09-16 11:03:28.726346+05:30`. This row is
   `2026-09-16 11:14:25.465633+05:30` — **11 minutes after the seed run**.
3. **`department_id` and `job_function_id` are NULL.** Every seeded staff user
   has both populated.
4. **Real email domain.** The seed uses only the reserved `.invalid` TLD
   (RFC 2606). `inspironics.net` is a real domain — it cannot have come from
   `seeds/steps/people.py`.
5. **A real bcrypt hash.** The seed writes the literal `!seed-no-login`.
6. **The repository documents it as drift.**
   `backend/docs/PHASE11_DASHBOARD_INTEGRATION.md` §6 names
   `ask@inspironics.net` explicitly as an extra row *"created through the
   Phase 3.0 write endpoints and never removed … carries a **real bcrypt
   password hash**"*, and §7 states *"Only the drifted `ask@inspironics.net` row
   could log in, and its password is unknown."*
7. **No trace in source.** `grep -ri "inspironics"` across the tree matches only
   `.pyc` bytecode caches and that one documentation file — **no seed file, no
   SQL file and no script creates it.**
8. **No SQL dump exists** anywhere in the tree (`find -iname "*.sql"` returns
   nothing; `backend/docs/archive/` does not exist), so it did not arrive by import.

**Conclusion: the account was provisioned manually on this machine on
2026-09-16 at 11:14 IST**, most plausibly through `POST /api/v1/users` or
`POST /api/v1/users/{id}/password`
(`backend/app/services/access_write.py` → `create_user` / `set_user_password`,
both of which call `hash_password()` → bcrypt), with `user_uid` passed
explicitly. **It exists only in this local database. Nothing in Git recreates it.**

---

## H. SEED-DATA BASELINE

### H.1 Files

| Path | Role |
|---|---|
| `backend/seeds/run_seed.py` | Runner. `python -m seeds.run_seed` (seed) / `--report` (read-only report). Single transaction, idempotent, DML only, never touches schema or `session_replication_role`. |
| **`backend/seeds/steps/people.py`** | **The only file that creates `app_user` rows.** |
| `backend/seeds/steps/{reference_data,facility,rooms,stays,services,devices,telemetry,alerts,activity,operations}.py` | The other 10 steps |
| `backend/seeds/helpers.py` | `upsert()`, `did()` (deterministic ids), `DEMO_NOW` |
| `backend/seeds/data/reference.py`, `countries.json` | Lookup data, including the 18 `ROLE_MODULES` |

### H.2 Where `app_user` rows are created

`backend/seeds/steps/people.py`, function `seed()`:

- `STAFF` list → **6 staff users** (`arjun.menon`, `kavya.iyer`, `rahul.das`,
  `sneha.pillai`, `vikram.rao`, `fatima.sheikh`)
- `GUESTS` list → **6 guest users** (`aarav.sharma`, `meera.krishnan`,
  `daniel.foster`, `priya.nair`, `chen.wei`, `ishaan.gupta`)
- plus the **`system`** bootstrap user created by an earlier step

**Total: 13 seeded accounts.**

### H.3 Is `ask@inspironics.net` created by the seed?

**NO.** It appears in no seed list, no seed file, and nowhere in tracked source.
See G.4 for the eight independent lines of evidence.

### H.4 Is a development admin / demo account created?

**Yes — `arjun.menon` is the seeded Administrator** (role `administrator`,
`role_type = admin`, department `administration`, function `administrator`,
`emp_id EMP-0001`). It is a full HMS Web admin **in every respect except that it
has no usable password**, so it cannot log in.

### H.5 Are passwords generated or assigned?

**Neither.** `backend/seeds/steps/people.py` assigns the same literal to every
row it creates:

```python
# Synthetic placeholder -- NOT a usable credential. Real hashes are
# written by the auth layer in a later phase.
password_hash="!seed-no-login",
```

No randomness, no hashing, no default password. The `system` user is left `NULL`.

### H.6 Is `!seed-no-login` intentional?

**Yes — emphatically, and it is documented in three places.**

- `backend/app/core/security.py` module docstring: *"the Phase 1.8 seed
  deliberately never wrote a usable credential."* `SEED_NO_LOGIN_SENTINEL` is a
  named constant, and both `verify_password()` and `has_usable_credential()`
  special-case it to return `False`.
- `backend/docs/PHASE2_4_AUTHENTICATION.md` §1, headed **"THE HEADLINE
  LIMITATION — no account can log in"**: *"`POST /api/v1/auth/login` returns
  **401 for every seeded account**. This is correct behaviour against the real
  data, not a defect."* It records what was deliberately **not** done: no schema
  change, no fake password, no hardcoded credential, no seed-data edit.
- `backend/app/api/v1/endpoints/auth.py` module docstring repeats it.

The documented way to enable login is an explicit operator action:

```python
from app.core.security import hash_password
# UPDATE app_user SET password_hash = :h WHERE user_name = 'arjun.menon'
hash_password("<chosen password>")
```

**This is the single most important fact for reproducing a clone.**

### H.7 Live credential audit (read-only)

```
credential_availability()
  accounts               : 14
  with_usable_credential : 1
  usable_usernames       : ['ask@inspironics.net']
```

Per-account state:

| `user_name` | `email` | `password_hash` state | `created_on` | `user_uid` |
|---|---|---|---|---|
| aarav.sharma | aarav.sharma@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| arjun.menon | arjun.menon@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| chen.wei | chen.wei@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| daniel.foster | daniel.foster@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| fatima.sheikh | fatima.sheikh@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| ishaan.gupta | ishaan.gupta@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| kavya.iyer | kavya.iyer@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| meera.krishnan | meera.krishnan@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| priya.nair | priya.nair@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| rahul.das | rahul.das@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| sneha.pillai | sneha.pillai@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| system | system@hms-demo.invalid | **NULL** | 09-16 11:03:28 | demo-uid-system-bootstrap |
| vikram.rao | vikram.rao@hms-demo.invalid | `!seed-no-login` | 09-16 11:03:28 | demo-uid-… |
| **ask@inspironics.net** | **ask@inspironics.net** | **bcrypt `$2b$` cost 12, 60 chars** | **09-16 11:14:25** | **operator-44f722df0f5b** |

**13 seeded + 1 manually provisioned = 14. Exactly one can log in.**

> Note: `PHASE11_DASHBOARD_INTEGRATION.md` §6 describes 18 accounts with 5 extra
> rows (four sharing `ramanaofficial2005@gmail.com` with NULL usernames).
> **That drift is no longer present** — the database was evidently rebuilt and
> re-seeded on 2026-09-16 at 11:03, and only `ask@inspironics.net` was
> re-provisioned afterwards. The current state is cleaner than that document
> describes.

---

## I. DATA-COUNT BASELINE

Read-only `COUNT(*)` per table. No data content was dumped.

### Core identity / access

| Table | Rows |
|---|---:|
| **`app_user`** | **14** (13 seeded + 1 operator-provisioned) |
| **`facility`** | **1** |
| **`department`** | **5** |
| **`job_function`** | **5** |
| **`facility_user`** | **13** (the 14th user has none — see G.3) |
| `role` | 7 |
| `user_role` | 14 |
| `role_module` | 18 |
| `role_module_permission` | 65 |
| `user_token` | 3 |

### Devices

| Table | Rows |
|---|---:|
| **`device`** | **14** |
| `device_type` | 4 |
| `other_device` | 12 |
| `device_current_stat` | 14 |
| `device_param` | 35 |
| `device_stat` | 504 |
| `device_alert` | 9 |

### Master / reference data

| Table | Rows |
|---|---:|
| `country` | 239 |
| `organisation` | 1 |
| `property_chain` | 3 |
| `property` | 4 |
| `property_type` | 1 |
| `amenity` | 27 |
| `amenity_type` | 5 |
| `alert_type` | 16 |
| `activity_type` | 22 |
| `notification_template` | 16 |
| `occasion_type` / `occasion` | 4 / 4 |
| `package` / `feature` | 8 / 6 |

### Operational / transactional

| Table | Rows |
|---|---:|
| `service_type` | 7 |
| `service_status` | 5 |
| `service_category` | 13 |
| `service_category_item` | 22 |
| `service_request` | 7 |
| `service_request_item` | 8 |
| `stay` | 6 |
| `stay_user` | 8 |
| `room_allocation` | 5 |
| `invoice` | 2 |
| `maintenance_request` | 3 |
| `job_order` | 3 |
| `value_alert` | 3 |
| `value_alert_limit_config` | 4 |
| `notification` | 6 |
| `activity` | 10 |
| `facility_event` | 3 |
| `energy_stat` | 72 |
| `daily_dual_data_point` | 35 |

---

## J. RUNTIME BASELINE

All three tiers were verified running at capture time.

### J.1 Listening processes

| Port | Bound | Process |
|---|---|---|
| 5432 | `0.0.0.0` | PostgreSQL **18** (PID 8184) — the one HMS uses |
| 5433 | — | PostgreSQL 17 (running, unused) |
| **8000** | **`127.0.0.1`** | FastAPI / Uvicorn |
| **8080** | **`0.0.0.0`** | Vite dev server |

### J.2 Verified endpoints

| Check | Request | Result |
|---|---|---|
| Backend liveness | `GET http://127.0.0.1:8000/health` | **200** `{"status":"ok","app":"HMS Backend","env":"development","version":"0.3.0"}` |
| **Database health** | `GET http://127.0.0.1:8000/api/v1/health/db` | **200** `{"status":"ok","database":"hms_db","schema_name":"public","server_version":"18.6","alembic_revision":"0e2687233b59","latency_ms":1.29}` |
| Frontend | `GET http://127.0.0.1:8080/` | **200** |
| Dev proxy | `GET http://127.0.0.1:8080/api/v1/health` | 404 carrying **FastAPI's** error envelope → the proxy is forwarding correctly (`/api/v1/health` has no collection route; only `/api/v1/health/db` exists) |
| Login endpoint alive | `POST /api/v1/auth/login` with a deliberately wrong password for `ask@inspironics.net` | **401** `{"error":{"code":"unauthorized","message":"Invalid username or password."}}` |
| Seeded user cannot log in | `POST /api/v1/auth/login` as `arjun.menon` | **401** — confirms the `!seed-no-login` sentinel in effect |
| Unauthenticated identity call | `GET /api/v1/auth/me` with no token | **401** `{"error":{"code":"unauthorized","message":"Not authenticated."}}` |

### J.3 Login verification for `ask@inspironics.net`

**The password was deliberately never obtained, guessed or tested**, so a real
end-to-end `POST /auth/login` with the correct credential was **not** performed.
Instead every link in the chain was verified independently and read-only:

| Link | Verification | Result |
|---|---|---|
| The account is findable by the exact query `authenticate()` runs | `select(AppUser).where(user_name == 'ask@inspironics.net')` | **1 row** |
| The stored credential is a real, usable bcrypt digest | `has_usable_credential(stored_hash)` | **True** |
| JWT issue → decode round-trip under this `.env` | `create_access_token()` → `decode_access_token()`, in memory; no token written to disk or displayed | **subject round-trips correctly**, `expires_in` honoured |
| The post-token path — exactly what `get_current_user()` does after decoding | `load_hms_web_user(db, <user id>)` | **returns a full `AuthenticatedUser`, not `None`** |
| Platform gate | resolved `platform` | **`hms_web`** — passes |
| The authorization payload `/auth/me` would return | roles / permissions projection | Administrator (`admin`), **18 modules, 18 readable, 18 writable** |

**Every step of the login path is proven working for this account except the
bcrypt comparison itself, which requires the plaintext.** Given the stored value
is a valid `$2b$12$` digest and `verify_password()` is plain `bcrypt.checkpw`,
the correct password necessarily succeeds.

---

## K. WHAT A FRESH CLONE MUST REPRODUCE

Ordered by how likely each is to be the thing that breaks login.

### K.1 Source

| Item | Required value |
|---|---|
| Remote | `https://github.com/ramanag0119/ACX-Platform` |
| Branch | `develop` |
| **Commit** | **`5625e812f2ca253b66a9256b2879b78c108ba096`** |
| Working-tree changes | The 20 modified + 5 untracked files in A.3 are **frontend presentation only** and are **not required for login**. They are required to match this machine's UI. |

> Do **not** follow `RUN_REPORT.md` §2, which says to check out
> `feature/changes-hms`. That instruction is stale; this baseline is
> `develop` @ `5625e81`.

### K.2 Backend configuration — `backend/.env` (git-ignored, must be created)

Copy `backend/.env.example` → `backend/.env`, then set:

| Variable | Value |
|---|---|
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | **the clone machine's own postgres password** — *not* copied from here |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` — **and confirm 5432 is the intended server** (see D.1) |
| `POSTGRES_DB` | `hms_db` |
| `POSTGRES_SCHEMA` | `public` |
| `DATABASE_URL` | **leave commented out** |
| `APP_ENV` | `development` |
| `DEBUG` | `true` |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `JWT_SECRET_KEY` | any value; it need not match this machine (see L) |

### K.3 Frontend configuration — `frontend/.env.local` (git-ignored, must be created)

A **verbatim copy of `frontend/.env.example`** reproduces this machine exactly:

```
VITE_API_BASE_URL=/api/v1
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

### K.4 Runtime versions

| Tier | This machine | Practical requirement |
|---|---|---|
| Python (venv) | 3.13.15 | 3.13.x |
| Node | v24.9.0 | v20 LTS or newer |
| npm | 11.6.0 | ships with Node |
| **PostgreSQL** | **18.6 on port 5432** | 16+ works for the schema; **the port must point at the server you actually migrated** |

Install with the **pinned** manifests, not loose ranges:
`pip install -r backend/requirements.txt` · `npm ci` in `frontend/`
(**`npm ci`, not `npm install`** — `frontend/package-lock.json` is tracked and
pins 445 packages).

### K.5 Database

| Item | Value |
|---|---|
| Database name | `hms_db` |
| Schema | `public` |
| **Alembic revision** | **`0e2687233b59`** — `alembic upgrade head` from the single tracked migration |
| Seed | `python -m seeds.run_seed` from `backend/` → the 13 accounts and the counts in section I |

### K.6 THE STEP THAT IS NOT IN GIT — provisioning a login

After migrating and seeding, a clone has **13 accounts and 0 usable
credentials**. Login will fail until an operator explicitly sets a password.
This is the documented procedure from
`backend/docs/PHASE2_4_AUTHENTICATION.md` §1.

**Two options:**

**(a) Reproduce this machine exactly** — an account whose `user_name` is
`ask@inspironics.net`:

| Field | Value to match |
|---|---|
| `user_name` | `ask@inspironics.net` *(must be `user_name`, not just `email`)* |
| `email` | `ask@inspironics.net` |
| `first_name` / `last_name` | `Sandy` / `Inspironics` |
| `user_uid` | any unique value (`operator-…` here) |
| `is_staff` | `1` |
| `password_hash` | a **fresh** bcrypt hash of a password you choose — the hash from this machine must not be copied (see L) |
| `user_role` | one row granting the **Administrator** role (`role_type = admin`) for the seeded facility |

**(b) Simpler and cleaner** — give the seeded `arjun.menon` a password. It is
already a full Administrator with `role_type = admin`, a `facility_user` row and
all 18 module grants, and it is fully reproducible from Git.

Either way the password itself is a local operator decision and is **not**
reproducible from source.

---

## L. LOCAL-ONLY — DO NOT COPY

| Item | Why |
|---|---|
| **`backend/.env`** | Contains this machine's PostgreSQL password. Git-ignored on purpose. Create the clone's own from `.env.example`. |
| **`POSTGRES_PASSWORD`** | Machine-specific credential. |
| **The `ask@inspironics.net` `password_hash`** | A credential. Copying a bcrypt digest between environments copies a password. Generate a fresh one. |
| **The `ask@inspironics.net` row itself** | Carries a real corporate email address. `PHASE11_DASHBOARD_INTEGRATION.md` §6 already flags real addresses in a demo database as a data-hygiene problem. |
| **`JWT_SECRET_KEY`** | Must differ per environment by design — `assert_production_ready()` exists specifically to enforce that outside development. Copying it lets a token minted on one machine be accepted by another. |
| `backend/.venv/` | Absolute Windows paths baked into `pyvenv.cfg` and the `Scripts/*.exe` shims. Recreate with `python -m venv`. |
| `frontend/node_modules/` | Platform-specific binaries (SWC, esbuild, rollup). Recreate with `npm ci`. |
| `frontend/.env.local` | Git-ignored by convention. Its *content* here is non-secret and identical to `.env.example`, so re-creating it is trivial. |
| `.vscode/` | Editor-local. |
| `dist/` | Build output. |
| Both PostgreSQL data directories | Server-local. |
| `scripts/Enable-PostgresLanAccess.ps1` | Untracked, specific to this machine's network (LAN exposure for PostgreSQL). Not needed for local login. |
| Root `package-lock.json` (91-byte stub) | Untracked artifact with an empty `packages` object. Not the real lockfile; `frontend/package-lock.json` is. |
| Stray `src/features/dashboard/components/EnergyConsumptionChart.tsx` | Untracked file at the repo root, outside `frontend/`. Nothing imports it from there — the real one is `frontend/src/features/dashboard/components/EnergyConsumptionChart.tsx` (tracked). |

---

## M. GENERATED — RECREATE, DO NOT COPY

| Item | How to recreate |
|---|---|
| `backend/.venv/` | `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt` |
| `frontend/node_modules/` | `npm ci` in `frontend/` |
| `backend/**/__pycache__/`, `*.pyc` | Automatic on import |
| **The 93-table schema** | **`alembic upgrade head` → revision `0e2687233b59`.** Never restore from a dump — the root `.gitignore` explicitly forbids committing one: *"A pg_dump of hms_db carries real password hashes and guest PII, and it is not application source: the schema comes from `alembic upgrade head` and the data from `python -m seeds.run_seed`."* |
| **All seed data** | `python -m seeds.run_seed` from `backend/`. Idempotent — deterministic ids mean a second run updates rather than duplicates. Verify with `python -m seeds.run_seed --report`. |
| `alembic_version` row | Written by `alembic upgrade head` |
| `dist/`, `*.tsbuildinfo` | `npm run build` |
| **A usable `password_hash`** | **`app.core.security.hash_password("<chosen password>")`.** Never copy a hash between machines. |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` (the recipe is in the `.env.example` comment) |

---

## N. WHY A FRESH CLONE WOULD FAIL TO LOG IN WITH IDENTICAL SOURCE

Ranked by likelihood. **Item 1 alone explains the entire symptom.**

### 1. ⭐ The account does not exist in the clone's database — THE ANSWER

`ask@inspironics.net` is **database row data, not source code.** No seed file,
migration, script or SQL dump in the repository creates it. It was provisioned
by hand on this machine on 2026-09-16 at 11:14 IST, 11 minutes after the seed
ran. A clone with byte-identical source and a correctly migrated and seeded
database will have **13 accounts, none of which can log in**.

*Symptom:* `401 Invalid username or password.` for `ask@inspironics.net`.
*Fix:* K.6.

### 2. ⭐ Every seeded account is deliberately credential-less

Falling back to a seeded admin also fails: `arjun.menon` — a full
Administrator — has `password_hash = '!seed-no-login'`, which
`verify_password()` rejects unconditionally, before bcrypt is even called.
**No password works for any seeded account. This is intentional, tested and
documented.** *Symptom:* an identical 401 for every username tried.

### 3. ⭐ Logging in with the **email** rather than the **username**

`authenticate()` filters on `AppUser.user_name` **only**. The `email` column is
never consulted and carries no unique constraint. On this machine the two
strings happen to be identical, which hides the distinction — on a clone where
someone creates the account with the address in `email` but a different
`user_name` (or `NULL`), login fails with the same opaque 401.
**The value must be in `user_name`.**

### 4. The comparison is case-sensitive and untrimmed

`user_name == username` is exact SQL equality, and the frontend sends the input
box verbatim. `Ask@Inspironics.net`, or a trailing space from a copy-paste,
produces a 401. Nothing lowercases or trims on either side.

### 5. The account exists with a credential but lacks an HMS Web role

Credentials are checked first, **then** the platform gate. An account created
without a `user_role` row, or with one whose `role.role_type` is `staff`,
`guest` or `system_user`, gets **403** — *"This account belongs to the …
application and cannot sign in to HMS Web."* Only `admin` and `manager` pass.
A user created via `POST /users` without `role_ids` lands here.

### 6. The clone points at a different PostgreSQL server

Two servers run here: **18 on 5432** (used) and **17 on 5433** (idle). A clone
that installs PostgreSQL 16 or 17 on 5432 and runs `alembic upgrade head` gets a
perfectly valid, perfectly **empty-of-your-user** database. `/health/db` returns
`ok`, the schema is right, and login still fails.
*Diagnostic:* `GET /api/v1/health/db` reports `server_version` — check it is the
server you provisioned the account on.

### 7. `alembic upgrade head` run but `run_seed` not

Schema present; `role`, `role_module` and `role_module_permission` empty. Even a
manually created user with a real hash then has no role → **403**, or
`/auth/me` returns empty permissions and the UI renders as fully denied.

### 8. `backend/.env` missing entirely

It is git-ignored, so a clone has none. `pydantic-settings` falls back to the
`config.py` defaults: `POSTGRES_PASSWORD = "postgres"` and
`JWT_SECRET_KEY = "dev-only-insecure-secret-change-me"`. If the local postgres
password is not literally `postgres`, the app fails at connect and every request
returns **503**, not 401 — a different symptom worth recognising.

### 9. `frontend/.env.local` missing **and** the backend not on 127.0.0.1:8000

`.env.local` is git-ignored. Without it, `VITE_API_BASE_URL` falls back to
`/api/v1` in the client and `VITE_API_PROXY_TARGET` to `http://127.0.0.1:8000`
in `vite.config.ts` — **the same values**, so a missing file is harmless *as
long as* the backend really is on `127.0.0.1:8000`. If it is on a different port
or host, requests 404/502 at the proxy and the UI shows *"Cannot reach the HMS
API."*

### 10. A stale token in `localStorage`

`AuthContext` re-validates `hms.access_token` against `/auth/me` on load and
signs out on failure, so this self-heals. But a clone served from the **same
origin** (`localhost:8080`) as this machine shares `localStorage`, and a token
signed with a **different** `JWT_SECRET_KEY` will be rejected — producing a brief
"restoring" flash and a bounce to `/login`. Clearing site data resolves it.
Note that because `JWT_SECRET_KEY` here is the unmodified `.env.example`
placeholder, a clone that copies `.env.example` verbatim ends up with the *same*
signing key, and tokens would cross-validate between the two machines.

### 11. `JWT_SECRET_KEY` changed while a session was live

Restarting the backend with a new secret invalidates every issued token. Login
itself still works; existing sessions 401. Expected behaviour, easily misread as
"login broken".

### 12. Node / Python major-version drift

This machine runs Node 24 and Python 3.13 while `RUN_REPORT.md` documents Node
20 and Python 3.13.3. Node 24 works here. Version drift would surface as build or
install failures, **not** as a 401 — if you are getting a clean 401, the cause is
items 1–5, not tooling.

---

## Appendix 1 — All 307 tracked files

```
.gitignore
README.md
RUN_REPORT.md
Ticket
backend/.env.example
backend/.gitignore
backend/alembic.ini
backend/app/__init__.py
backend/app/api/__init__.py
backend/app/api/deps.py
backend/app/api/errors.py
backend/app/api/v1/__init__.py
backend/app/api/v1/endpoints/__init__.py
backend/app/api/v1/endpoints/access.py
backend/app/api/v1/endpoints/access_write.py
backend/app/api/v1/endpoints/alerts.py
backend/app/api/v1/endpoints/auth.py
backend/app/api/v1/endpoints/devices.py
backend/app/api/v1/endpoints/devices_write.py
backend/app/api/v1/endpoints/energy.py
backend/app/api/v1/endpoints/facilities.py
backend/app/api/v1/endpoints/facility_write.py
backend/app/api/v1/endpoints/health.py
backend/app/api/v1/endpoints/job_orders.py
backend/app/api/v1/endpoints/maintenance.py
backend/app/api/v1/endpoints/notifications.py
backend/app/api/v1/endpoints/occupancy.py
backend/app/api/v1/endpoints/reports.py
backend/app/api/v1/endpoints/services.py
backend/app/api/v1/endpoints/services_write.py
backend/app/api/v1/endpoints/stays.py
backend/app/api/v1/endpoints/stays_write.py
backend/app/api/v1/endpoints/telemetry.py
backend/app/api/v1/router.py
backend/app/api/write_errors.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/core/platform.py
backend/app/core/security.py
backend/app/db/__init__.py
backend/app/db/base.py
backend/app/db/session.py
backend/app/db/verify_schema.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/access.py
backend/app/models/activity.py
backend/app/models/alert.py
backend/app/models/amenity.py
backend/app/models/device.py
backend/app/models/enums.py
backend/app/models/facility.py
backend/app/models/job_order.py
backend/app/models/maintenance.py
backend/app/models/marketing.py
backend/app/models/people.py
backend/app/models/reporting.py
backend/app/models/scheduler.py
backend/app/models/service.py
backend/app/models/stay.py
backend/app/schemas/__init__.py
backend/app/schemas/access.py
backend/app/schemas/access_write.py
backend/app/schemas/alert.py
backend/app/schemas/auth.py
backend/app/schemas/common.py
backend/app/schemas/device.py
backend/app/schemas/energy.py
backend/app/schemas/facility.py
backend/app/schemas/filters.py
backend/app/schemas/health.py
backend/app/schemas/job_order.py
backend/app/schemas/maintenance.py
backend/app/schemas/notification.py
backend/app/schemas/occupancy.py
backend/app/schemas/ops_write.py
backend/app/schemas/report.py
backend/app/schemas/service.py
backend/app/schemas/stay.py
backend/app/schemas/telemetry.py
backend/app/services/__init__.py
backend/app/services/access.py
backend/app/services/access_write.py
backend/app/services/alert.py
backend/app/services/auth.py
backend/app/services/catalog.py
backend/app/services/device.py
backend/app/services/devices_write.py
backend/app/services/energy.py
backend/app/services/facility.py
backend/app/services/facility_write.py
backend/app/services/job_order.py
backend/app/services/job_order_write.py
backend/app/services/limit_config.py
backend/app/services/maintenance.py
backend/app/services/maintenance_write.py
backend/app/services/notification.py
backend/app/services/occupancy.py
backend/app/services/report_export.py
backend/app/services/reports.py
backend/app/services/service.py
backend/app/services/services_write.py
backend/app/services/stay.py
backend/app/services/stays_write.py
backend/app/services/telemetry.py
backend/app/services/writes.py
backend/docs/FINAL_HMS_DATABASE_BLUEPRINT.md
backend/docs/IKANOS_HMS_SCHEMA_COMPARISON.md
backend/docs/NEEDS_REVIEW.md
backend/docs/PHASE11_DASHBOARD_INTEGRATION.md
backend/docs/PHASE1_7_DATABASE_IMPLEMENTATION.md
backend/docs/PHASE1_8_SEED_DATA.md
backend/docs/PHASE1_REPORT.md
backend/docs/PHASE2_4_AUTHENTICATION.md
backend/migrations/README
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py
backend/requirements.txt
backend/scripts/__init__.py
backend/scripts/verify_dashboard_kpis.py
backend/seeds/__init__.py
backend/seeds/data/__init__.py
backend/seeds/data/countries.json
backend/seeds/data/reference.py
backend/seeds/helpers.py
backend/seeds/run_seed.py
backend/seeds/steps/__init__.py
backend/seeds/steps/activity.py
backend/seeds/steps/alerts.py
backend/seeds/steps/devices.py
backend/seeds/steps/facility.py
backend/seeds/steps/operations.py
backend/seeds/steps/people.py
backend/seeds/steps/reference_data.py
backend/seeds/steps/rooms.py
backend/seeds/steps/services.py
backend/seeds/steps/stays.py
backend/seeds/steps/telemetry.py
backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/conftest_writes.py
backend/tests/test_access_api.py
backend/tests/test_access_write_api.py
backend/tests/test_alert_api.py
backend/tests/test_auth_api.py
backend/tests/test_catalog_write_api.py
backend/tests/test_device_api.py
backend/tests/test_device_write_api.py
backend/tests/test_facility_api.py
backend/tests/test_filter_contract.py
backend/tests/test_health_api.py
backend/tests/test_notification_api.py
backend/tests/test_occupancy_api.py
backend/tests/test_report_api.py
backend/tests/test_schema_foundation.py
backend/tests/test_seed_data.py
backend/tests/test_service_api.py
backend/tests/test_service_write_api.py
backend/tests/test_stay_write_api.py
backend/tests/test_telemetry_api.py
docs/HMS-Data-Gap-Analysis.md
frontend/.env.example
frontend/.stylelintignore
frontend/.stylelintrc.json
frontend/components.json
frontend/eslint.config.js
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/postcss.config.js
frontend/public/apple-touch-icon.png
frontend/public/favicon-16x16.png
frontend/public/favicon-32x32.png
frontend/public/favicon-48x48.png
frontend/public/favicon.ico
frontend/public/ikanos-app-icon.png
frontend/public/ikanos-logo-hex.png
frontend/public/ikanos-logo-new.png
frontend/public/ikanos-logo.png
frontend/public/placeholder.svg
frontend/public/robots.txt
frontend/src/App.tsx
frontend/src/components/layout/AppHeader.tsx
frontend/src/components/layout/AppLayout.tsx
frontend/src/components/layout/AppSidebar.tsx
frontend/src/components/layout/NavLink.tsx
frontend/src/components/layout/PageHeader.tsx
frontend/src/components/ui/accordion.tsx
frontend/src/components/ui/alert-dialog.tsx
frontend/src/components/ui/alert.tsx
frontend/src/components/ui/aspect-ratio.tsx
frontend/src/components/ui/avatar.tsx
frontend/src/components/ui/badge.tsx
frontend/src/components/ui/breadcrumb.tsx
frontend/src/components/ui/button.tsx
frontend/src/components/ui/calendar.tsx
frontend/src/components/ui/card.tsx
frontend/src/components/ui/carousel.tsx
frontend/src/components/ui/chart.tsx
frontend/src/components/ui/checkbox.tsx
frontend/src/components/ui/collapsible.tsx
frontend/src/components/ui/command.tsx
frontend/src/components/ui/context-menu.tsx
frontend/src/components/ui/dialog.tsx
frontend/src/components/ui/drawer.tsx
frontend/src/components/ui/dropdown-menu.tsx
frontend/src/components/ui/form.tsx
frontend/src/components/ui/hover-card.tsx
frontend/src/components/ui/input-otp.tsx
frontend/src/components/ui/input.tsx
frontend/src/components/ui/label.tsx
frontend/src/components/ui/menubar.tsx
frontend/src/components/ui/navigation-menu.tsx
frontend/src/components/ui/pagination.tsx
frontend/src/components/ui/popover.tsx
frontend/src/components/ui/progress.tsx
frontend/src/components/ui/radio-group.tsx
frontend/src/components/ui/resizable.tsx
frontend/src/components/ui/scroll-area.tsx
frontend/src/components/ui/select.tsx
frontend/src/components/ui/separator.tsx
frontend/src/components/ui/sheet.tsx
frontend/src/components/ui/sidebar.tsx
frontend/src/components/ui/skeleton.tsx
frontend/src/components/ui/slider.tsx
frontend/src/components/ui/sonner.tsx
frontend/src/components/ui/switch.tsx
frontend/src/components/ui/table.tsx
frontend/src/components/ui/tabs.tsx
frontend/src/components/ui/textarea.tsx
frontend/src/components/ui/toast.tsx
frontend/src/components/ui/toaster.tsx
frontend/src/components/ui/toggle-group.tsx
frontend/src/components/ui/toggle.tsx
frontend/src/components/ui/tooltip.tsx
frontend/src/components/ui/use-toast.ts
frontend/src/core/components/DataState.tsx
frontend/src/core/components/ModuleGuard.tsx
frontend/src/core/components/NoEndpointNotice.tsx
frontend/src/core/components/ProtectedRoute.tsx
frontend/src/core/contexts/AuthContext.tsx
frontend/src/core/contexts/ThemeContext.tsx
frontend/src/core/rbac/modules.ts
frontend/src/core/styles/App.css
frontend/src/features/auth/pages/Login.tsx
frontend/src/features/bookings/pages/Bookings.tsx
frontend/src/features/common/pages/NotFound.tsx
frontend/src/features/common/pages/Placeholder.tsx
frontend/src/features/config/pages/Employees.tsx
frontend/src/features/config/pages/FacilityManagement.tsx
frontend/src/features/config/pages/JobOrder.tsx
frontend/src/features/config/pages/LimitConfigAlert.tsx
frontend/src/features/config/pages/ServicesSetup.tsx
frontend/src/features/config/pages/UserRoles.tsx
frontend/src/features/dashboard/components/AlertsPanel.tsx
frontend/src/features/dashboard/components/CaleidoAtWork.tsx
frontend/src/features/dashboard/components/DashboardKPIs.tsx
frontend/src/features/dashboard/components/EnergyConsumptionChart.tsx
frontend/src/features/dashboard/components/KPICard.tsx
frontend/src/features/dashboard/components/RecentActivityPanel.tsx
frontend/src/features/dashboard/components/StatusSection.tsx
frontend/src/features/dashboard/pages/Dashboard.tsx
frontend/src/features/devices/components/AppliancesEnergyModal.tsx
frontend/src/features/devices/components/MeterHierarchyView.tsx
frontend/src/features/devices/components/MeterNodeCard.tsx
frontend/src/features/devices/components/RoomStatusPanel.tsx
frontend/src/features/devices/data/meters.ts
frontend/src/features/devices/data/useMeterHierarchy.ts
frontend/src/features/devices/pages/EnergyView.tsx
frontend/src/features/devices/pages/KeySettings.tsx
frontend/src/features/devices/pages/PowerView.tsx
frontend/src/features/marketing/pages/Events.tsx
frontend/src/features/marketing/pages/Holidays.tsx
frontend/src/features/marketing/pages/Offers.tsx
frontend/src/features/occupancy/components/OccupancyStatisticsChart.tsx
frontend/src/features/occupancy/components/ReallocateRoomDialog.tsx
frontend/src/features/occupancy/components/RoomConditionsDialog.tsx
frontend/src/features/occupancy/components/RoomDetailsModal.tsx
frontend/src/features/occupancy/components/RoomDetailsPanel.tsx
frontend/src/features/occupancy/components/RoomPowerEnergy.tsx
frontend/src/features/occupancy/lib/roomStatus.ts
frontend/src/features/occupancy/pages/Occupancy.tsx
frontend/src/features/occupancy/pages/RoomView.tsx
frontend/src/features/reports/pages/Reports.tsx
frontend/src/features/services/components/ServiceRequestActionsDialog.tsx
frontend/src/features/services/pages/ServicePlanning.tsx
frontend/src/features/services/pages/ServiceTracking.tsx
frontend/src/features/tickets/pages/Tickets.tsx
frontend/src/hooks/use-mobile.tsx
frontend/src/hooks/use-toast.ts
frontend/src/index.css
frontend/src/lib/api/client.ts
frontend/src/lib/api/endpoints.ts
frontend/src/lib/api/hooks.ts
frontend/src/lib/api/mutations.ts
frontend/src/lib/api/reports.ts
frontend/src/lib/api/types.ts
frontend/src/lib/api/writes.ts
frontend/src/lib/utils.ts
frontend/src/main.tsx
frontend/src/vite-env.d.ts
frontend/tailwind.config.ts
frontend/tsconfig.app.json
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/vite.config.ts
```

## Appendix 2 — All 66 direct frontend dependencies (declared vs installed)

| Kind | Package | Declared | Installed |
|---|---|---|---|
| dep | `@hookform/resolvers` | `^3.10.0` | **3.10.0** |
| dep | `@radix-ui/react-accordion` | `^1.2.11` | **1.2.11** |
| dep | `@radix-ui/react-alert-dialog` | `^1.1.14` | **1.1.14** |
| dep | `@radix-ui/react-aspect-ratio` | `^1.1.7` | **1.1.7** |
| dep | `@radix-ui/react-avatar` | `^1.1.10` | **1.1.10** |
| dep | `@radix-ui/react-checkbox` | `^1.3.2` | **1.3.2** |
| dep | `@radix-ui/react-collapsible` | `^1.1.11` | **1.1.11** |
| dep | `@radix-ui/react-context-menu` | `^2.2.15` | **2.2.15** |
| dep | `@radix-ui/react-dialog` | `^1.1.14` | **1.1.14** |
| dep | `@radix-ui/react-dropdown-menu` | `^2.1.15` | **2.1.15** |
| dep | `@radix-ui/react-hover-card` | `^1.1.14` | **1.1.14** |
| dep | `@radix-ui/react-label` | `^2.1.7` | **2.1.7** |
| dep | `@radix-ui/react-menubar` | `^1.1.15` | **1.1.15** |
| dep | `@radix-ui/react-navigation-menu` | `^1.2.13` | **1.2.13** |
| dep | `@radix-ui/react-popover` | `^1.1.14` | **1.1.14** |
| dep | `@radix-ui/react-progress` | `^1.1.7` | **1.1.7** |
| dep | `@radix-ui/react-radio-group` | `^1.3.7` | **1.3.7** |
| dep | `@radix-ui/react-scroll-area` | `^1.2.9` | **1.2.9** |
| dep | `@radix-ui/react-select` | `^2.2.5` | **2.2.5** |
| dep | `@radix-ui/react-separator` | `^1.1.7` | **1.1.7** |
| dep | `@radix-ui/react-slider` | `^1.3.5` | **1.3.5** |
| dep | `@radix-ui/react-slot` | `^1.2.3` | **1.2.3** |
| dep | `@radix-ui/react-switch` | `^1.2.5` | **1.2.5** |
| dep | `@radix-ui/react-tabs` | `^1.1.12` | **1.1.12** |
| dep | `@radix-ui/react-toast` | `^1.2.14` | **1.2.14** |
| dep | `@radix-ui/react-toggle` | `^1.1.9` | **1.1.9** |
| dep | `@radix-ui/react-toggle-group` | `^1.1.10` | **1.1.10** |
| dep | `@radix-ui/react-tooltip` | `^1.2.7` | **1.2.7** |
| dep | `@tanstack/react-query` | `^5.83.0` | **5.83.0** |
| dep | `class-variance-authority` | `^0.7.1` | **0.7.1** |
| dep | `clsx` | `^2.1.1` | **2.1.1** |
| dep | `cmdk` | `^1.1.1` | **1.1.1** |
| dep | `date-fns` | `^3.6.0` | **3.6.0** |
| dep | `embla-carousel-react` | `^8.6.0` | **8.6.0** |
| dep | `input-otp` | `^1.4.2` | **1.4.2** |
| dep | `lucide-react` | `^0.462.0` | **0.462.0** |
| dep | `next-themes` | `^0.3.0` | **0.3.0** |
| dep | `react` | `^18.3.1` | **18.3.1** |
| dep | `react-day-picker` | `^8.10.1` | **8.10.1** |
| dep | `react-dom` | `^18.3.1` | **18.3.1** |
| dep | `react-hook-form` | `^7.61.1` | **7.61.1** |
| dep | `react-resizable-panels` | `^2.1.9` | **2.1.9** |
| dep | `react-router-dom` | `^6.30.1` | **6.30.1** |
| dep | `recharts` | `^2.15.4` | **2.15.4** |
| dep | `sonner` | `^1.7.4` | **1.7.4** |
| dep | `tailwind-merge` | `^2.6.0` | **2.6.0** |
| dep | `tailwindcss-animate` | `^1.0.7` | **1.0.7** |
| dep | `vaul` | `^0.9.9` | **0.9.9** |
| dep | `zod` | `^3.25.76` | **3.25.76** |
| dev | `@eslint/js` | `^9.32.0` | **9.32.0** |
| dev | `@tailwindcss/typography` | `^0.5.16` | **0.5.16** |
| dev | `@types/node` | `^22.16.5` | **22.16.5** |
| dev | `@types/react` | `^18.3.23` | **18.3.23** |
| dev | `@types/react-dom` | `^18.3.7` | **18.3.7** |
| dev | `@vitejs/plugin-react-swc` | `^3.11.0` | **3.11.0** |
| dev | `autoprefixer` | `^10.4.21` | **10.4.21** |
| dev | `eslint` | `^9.32.0` | **9.32.0** |
| dev | `eslint-plugin-react-hooks` | `^5.2.0` | **5.2.0** |
| dev | `eslint-plugin-react-refresh` | `^0.4.20` | **0.4.20** |
| dev | `globals` | `^15.15.0` | **15.15.0** |
| dev | `lovable-tagger` | `^1.1.13` | **1.1.13** |
| dev | `postcss` | `^8.5.6` | **8.5.6** |
| dev | `tailwindcss` | `^3.4.17` | **3.4.17** |
| dev | `typescript` | `^5.8.3` | **5.8.3** |
| dev | `typescript-eslint` | `^8.38.0` | **8.38.0** |
| dev | `vite` | `^5.4.19` | **5.4.19** |

---

*End of baseline. Captured read-only on 2026-09-18 from `develop` @ `5625e812f2ca253b66a9256b2879b78c108ba096`. Nothing in this environment was modified.*
