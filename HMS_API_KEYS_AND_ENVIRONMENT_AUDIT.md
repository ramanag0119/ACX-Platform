# HMS — Complete API Keys & Environment Variables Audit Report

**Document Title:** HMS Application Environment Configuration, Secrets & Credentials Audit  
**Target Application:** Hotel Management System (HMS Web & Backend)  
**Repository Root:** `ACX-Platform`  
**Inspection Date:** 2026-10-26  
**Auditor:** Antigravity AI Senior Backend Architect & Security Specialist  
**Methodology:** 100% Read-Only Codebase, Configuration & Live Runtime Inspection  
**Audit Standard:** Strict Non-Modifying Policy; No Code, Schema, or Secrets Altered; Real Secrets Redacted as `[REDACTED]`.

---

## 1. Executive Summary

This report provides an exhaustive, evidence-based inventory of all environment variables, connection strings, credentials, signing keys, and runtime configuration settings discovered across the HMS backend and frontend codebases.

### Headline Security & Configuration Findings:
1. **Zero External SaaS Dependencies:** The HMS application currently contains **zero third-party API keys** (no payment gateways, no cloud SMS/email providers, no LLM API keys, and no AWS S3/cloud storage credentials). All business operations run autonomously on self-hosted PostgreSQL.
2. **Centralized Backend Configuration:** The backend uses a single Pydantic V2 `BaseSettings` class located in [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py). Configuration is strictly loaded from `backend/.env` with typed defaults. `os.getenv` and `os.environ` are not used anywhere in `app/`.
3. **Stateless JWT with Dev Guard:** Access tokens are signed using `python-jose` HS256. A built-in guard (`assert_production_ready()`) prevents the application from starting outside development if the default insecure key (`dev-only-insecure-secret-change-me`) is retained.
4. **Decoupled Frontend via Dev Proxy:** The frontend avoids CORS in development by using relative `/api/v1` routes forwarded to `VITE_API_PROXY_TARGET` (`http://127.0.0.1:8000`) via Vite's proxy in [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts). No backend secrets are exposed to the client bundle.
5. **Secondary Database Hook:** The backend defines lazy initialization settings for a secondary MySQL 8.0 commercial database (`hms_bss`), but it is currently unprovisioned and inactive (`/api/v1/health/bss-db` returns `status="pending_provision"`).

---

## 2. API Key and Configuration Inventory

The following table catalogs every configuration variable, secret, and credential identified in the repository:

| Variable / Key | Purpose | Service / Module | Defined In | Used In | Required? | Missing Impact | Secret Classification |
|---|---|---|---|---|---|---|---|
| `POSTGRES_USER` | Database username | PostgreSQL 18 / Database Layer | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) | Conditionally Required | Falls back to `"postgres"`; fails connection if server requires another user | Non-sensitive internal identifier |
| `POSTGRES_PASSWORD` | Database password | PostgreSQL 18 / Database Layer | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) | **Required** | Falls back to `"postgres"`; HTTP 503 if password does not match server | **High Secret** (Database Credential) |
| `POSTGRES_HOST` | Database host address | PostgreSQL 18 / Network Layer | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) | Conditionally Required | Falls back to `"localhost"`; connection refused if database on remote host | Non-sensitive network configuration |
| `POSTGRES_PORT` | Database TCP port | PostgreSQL 18 / Network Layer | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) | Conditionally Required | Falls back to `5432`; connection fails or selects wrong instance if alternate port | Non-sensitive network configuration |
| `POSTGRES_DB` | Database catalog name | PostgreSQL 18 / Database Layer | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) | Conditionally Required | Falls back to `"hms_db"`; database not found error if absent | Non-sensitive internal identifier |
| `POSTGRES_SCHEMA` | Active PostgreSQL schema | PostgreSQL 18 / Schema & Alembic | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/migrations/env.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/migrations/env.py), [backend/app/api/v1/endpoints/health.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/health.py) | Optional | Falls back to `"public"`; Alembic creates version table in default schema | Non-sensitive internal identifier |
| `DATABASE_URL` | Complete SQLAlchemy connection string | SQLAlchemy Engine (Overrides individual `POSTGRES_*`) | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) (commented) | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) (`sqlalchemy_url`) | Optional | If commented/unset, URL is automatically assembled from `POSTGRES_*` parts | **High Secret** (Contains embedded password) |
| `JWT_SECRET_KEY` | HMAC signing key for JWT tokens | Authentication & Authorization / Security | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py) (`create_access_token`, `decode_access_token`) | **Mandatory outside Dev** | In `APP_ENV != "development"`, backend crashes on startup via `assert_production_ready()` | **High Secret** (Cryptographic Signing Key) |
| `JWT_ALGORITHM` | Cryptographic signing algorithm | Authentication / Security | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py) | Optional | Falls back to `"HS256"` | Non-sensitive algorithm identifier |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Session validity duration | Authentication / Security | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py) (`create_access_token`) | Optional | Falls back to `60` minutes | Non-sensitive configuration |
| `DEV_JWT_SECRET` | Insecure dev sentinel check | Security Guard | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) (`assert_production_ready`) | Built-in ClassVar | Detects if dev secret is used in staging/production | Non-sensitive static sentinel |
| `APP_NAME` | Service title string | Application Metadata | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py) | Optional | Falls back to `"HMS Backend"`; displayed in OpenAPI docs and `/health` | Non-sensitive application metadata |
| `APP_ENV` | Environment mode switch (`development`, `staging`, `production`) | Core Application / Security | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py), [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py) | **Critical** | Falls back to `"development"`; triggers production security assertion when changed | Non-sensitive environment flag |
| `DEBUG` | Verbose debug flag | Core Application / SQLAlchemy Logging | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`echo=DEBUG and APP_ENV=='development'`) | Optional | Falls back to `True`; controls console SQL echo | Non-sensitive operational flag |
| `API_V1_PREFIX` | Versioned route mount prefix | FastAPI Routing | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py) | Optional | Falls back to `"/api/v1"` | Non-sensitive URL path |
| `CORS_ORIGINS` | Permitted browser origins (comma-separated) | FastAPI CORS Middleware | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py) | Optional | Falls back to localhost ports `8080`, `8081`, `5173`; browser blocks cross-origin requests in non-standard ports if not set | Non-sensitive security policy |
| `MYSQL_USER` | BSS database username | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Falls back to `"root"`; unused until BSS is provisioned | Non-sensitive internal identifier |
| `MYSQL_PASSWORD` | BSS database password | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Falls back to `"root"`; unused until BSS is provisioned | **High Secret** (Database Credential) |
| `MYSQL_HOST` | BSS database host | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Falls back to `"127.0.0.1"` | Non-sensitive network configuration |
| `MYSQL_PORT` | BSS database port | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Falls back to `3307` | Non-sensitive network configuration |
| `MYSQL_DB` | BSS database name | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Falls back to `"hms_bss"` | Non-sensitive internal identifier |
| `BSS_DATABASE_URL` | Full MySQL BSS connection URL | MySQL 8.0 BSS Domain | [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`) | Optional (Inactive) | Overrides individual `MYSQL_*` settings if provided | **High Secret** (Contains embedded password) |
| `VITE_API_BASE_URL` | Frontend API client target | Frontend API Client | [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example), [frontend/.env.local](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.local) | [frontend/src/lib/api/client.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/src/lib/api/client.ts) (line 15) | Optional in Dev / **Required in Prod** | Falls back to `"/api/v1"` (relative). In production without proxy, calls 404 if not set to absolute backend URL | Public URL (Client Bundle) |
| `VITE_API_PROXY_TARGET` | Dev-server proxy destination | Frontend Dev Server | [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example), [frontend/.env.local](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.local) | [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) (line 11) | Optional in Dev | Falls back to `"http://127.0.0.1:8000"`; dev proxy returns 502/ECONNREFUSED if backend on another port | Non-sensitive internal host |
| `VITE_PLATFORM_RELEASE_DATE` | Release date display pin | Frontend Build / About View | [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) (commented) | [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) (line 15) | Optional | Falls back to current build date `YYYY-MM-DD` | Public metadata |
| `VITE_PLATFORM_LICENSE` | Commercial license label | Frontend Branding | [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) (commented) | [frontend/src/core/config/platform.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/src/core/config/platform.ts) (line 12) | Optional | Falls back to `"Enterprise"` | Public metadata |
| `VITE_HOST` | Dev server listening interface | Frontend Dev Server | Implicit / Vite CLI | [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) (line 19) | Optional | Falls back to `"localhost"` | Non-sensitive network configuration |
| `PORT` / `VITE_PORT` | Dev server listening port | Frontend Dev Server | Implicit / Vite CLI | [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) (line 20) | Optional | Falls back to `8081` | Non-sensitive network configuration |

---

## 3. Detailed Plain-Language Explanation of Every Key

### `POSTGRES_USER`
- **What it is:** The PostgreSQL database user account name.
- **Why HMS needs it:** The SQLAlchemy engine requires an authorized database role to open client connections, execute DDL migrations, and perform CRUD operations across all 94 tables.
- **Which service uses it:** Core PostgreSQL connection factory in [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py).
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 4 (`POSTGRES_USER=postgres`).
- **Where it is consumed:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) via `settings.sqlalchemy_url`.
- **How it works:** Injected into the PostgreSQL DSN URL: `postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}`.
- **Required status:** Conditionally required (defaults to `"postgres"` if absent).
- **If missing or invalid:** Connection rejected with `psycopg2.OperationalError: FATAL: role does not exist`.
- **Security notes:** Internal non-secret identifier; should not be exposed externally.

### `POSTGRES_PASSWORD`
- **What it is:** The database authentication password for `POSTGRES_USER`.
- **Why HMS needs it:** Authenticates the backend process against PostgreSQL.
- **Which service uses it:** Database connection factory and Alembic migration runner.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 5 (`POSTGRES_PASSWORD=[REDACTED]`).
- **Where it is consumed:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) and [backend/migrations/env.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/migrations/env.py).
- **How it works:** Embedded securely in the compiled SQLAlchemy URL.
- **Required status:** **Mandatory**.
- **If missing or invalid:** All database queries fail; health check returns HTTP 503 (`Database is unavailable`); endpoints fail with `psycopg2.OperationalError: password authentication failed`.
- **Security notes:** **High Secret**. Must never be committed to Git. Redacted in all reports.

### `POSTGRES_HOST`
- **What it is:** Hostname or IP address where the PostgreSQL database server is listening.
- **Why HMS needs it:** Establishes the TCP socket connection to PostgreSQL.
- **Which service uses it:** Database connection factory.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 6 (`POSTGRES_HOST=localhost`).
- **Where it is consumed:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py).
- **How it works:** Passed as the target host in the connection string.
- **Required status:** Optional (defaults to `"localhost"`).
- **If missing or invalid:** Connection times out or returns `psycopg2.OperationalError: could not connect to server`.
- **Security notes:** Non-sensitive internal address.

### `POSTGRES_PORT`
- **What it is:** The TCP port number where PostgreSQL is bound.
- **Why HMS needs it:** Ensures connection to the intended database instance. As documented in the environment baseline, PostgreSQL 18 is on `5432` while an idle PostgreSQL 17 is on `5433`.
- **Which service uses it:** Database connection factory.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 7 (`POSTGRES_PORT=5432`).
- **Where it is consumed:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py).
- **How it works:** Appended as the port segment in the PostgreSQL DSN.
- **Required status:** Optional (defaults to `5432`).
- **If missing or invalid:** Connects to wrong instance if default altered, or fails with connection refused.
- **Security notes:** Non-sensitive networking parameter.

### `POSTGRES_DB`
- **What it is:** Name of the specific PostgreSQL database catalog.
- **Why HMS needs it:** Directs the connection pool to the `hms_db` catalog containing the 94 tables.
- **Which service uses it:** Database connection factory.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 8 (`POSTGRES_DB=hms_db`).
- **Where it is consumed:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py).
- **How it works:** Specifies database name in connection string.
- **Required status:** Optional (defaults to `"hms_db"`).
- **If missing or invalid:** Fails with `FATAL: database "..." does not exist`.
- **Security notes:** Non-sensitive internal identifier.

### `POSTGRES_SCHEMA`
- **What it is:** The PostgreSQL schema namespace within `hms_db`.
- **Why HMS needs it:** Scopes table queries and tells Alembic where to read/write `alembic_version`.
- **Which service uses it:** [backend/migrations/env.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/migrations/env.py) and health endpoint.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env), line 9 (`POSTGRES_SCHEMA=public`).
- **Where it is consumed:** [backend/migrations/env.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/migrations/env.py) (`VERSION_TABLE_SCHEMA`).
- **How it works:** Injected into Alembic's context configuration and `/health/db` report.
- **Required status:** Optional (defaults to `"public"`).
- **If missing or invalid:** Falls back to `"public"`.
- **Security notes:** Non-sensitive schema name.

### `DATABASE_URL`
- **What it is:** Complete, self-contained PostgreSQL connection URI string.
- **Why HMS needs it:** Allows deployment platforms (Docker, Kubernetes, cloud hosts) to pass the full database connection string in a single variable rather than 6 distinct parts.
- **Which service uses it:** Database connection factory property `settings.sqlalchemy_url`.
- **Where it is configured:** Commented out in [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env) line 12.
- **Where it is consumed:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) (lines 73-78).
- **How it works:** When non-empty, `settings.sqlalchemy_url` returns it verbatim and ignores `POSTGRES_*` settings.
- **Required status:** Optional (commented by default).
- **If missing or invalid:** Safely ignored; individual `POSTGRES_*` variables are used instead.
- **Security notes:** **High Secret** when set, because it embeds the password in plaintext.

### `JWT_SECRET_KEY`
- **What it is:** Cryptographic symmetric secret key used by HMAC-SHA256 (HS256) to sign and verify JSON Web Tokens.
- **Why HMS needs it:** Powers stateless authentication for HMS Web operators. Tokens minted at `/api/v1/auth/login` are cryptographically signed with this key to prevent forgery.
- **Which service uses it:** [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py) and auth dependency [backend/app/api/deps.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/api/deps.py).
- **Where it is configured:** [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example), line 21. Not set in local `backend/.env` (falls back to dev default in `config.py`).
- **Where it is consumed:** `create_access_token()` and `decode_access_token()`.
- **How it works:**
  1. `POST /auth/login` verifies user password hash.
  2. `create_access_token()` encodes `sub: user_uuid` signed with `JWT_SECRET_KEY`.
  3. Subsequent requests send `Authorization: Bearer <token>`.
  4. `decode_access_token()` verifies signature with `JWT_SECRET_KEY` and extracts `user_uuid`.
- **Required status:** **Mandatory outside Development**.
- **If missing or invalid:** In development, uses fallback dev key. In staging/production (`APP_ENV != "development"`), `settings.assert_production_ready()` raises `RuntimeError` and refuses to start.
- **Security notes:** **Critical Secret**. Must be generated using `secrets.token_urlsafe(64)` and kept strictly server-side.

### `JWT_ALGORITHM`
- **What it is:** JWT signature algorithm identifier.
- **Why HMS needs it:** Specifies the cryptographic hashing algorithm used by `jose.jwt`.
- **Which service uses it:** Security module [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py).
- **Where it is configured:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) line 26; [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) line 22.
- **Where it is consumed:** `jwt.encode(..., algorithm=settings.JWT_ALGORITHM)`.
- **Required status:** Optional (defaults to `"HS256"`).
- **If missing or invalid:** Falls back to `"HS256"`.
- **Security notes:** Standard algorithm identifier.

### `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- **What it is:** Access token validity lifetime in minutes.
- **Why HMS needs it:** Calculates the `exp` (expiration) timestamp claim when minting JWT access tokens.
- **Which service uses it:** [backend/app/core/security.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py).
- **Where it is configured:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) line 27; [backend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env.example) line 23.
- **Where it is consumed:** `create_access_token()`.
- **Required status:** Optional (defaults to `60` minutes).
- **If missing or invalid:** Defaults to 60 minutes.
- **Security notes:** Non-sensitive session duration parameter.

### `APP_NAME`
- **What it is:** Human-readable application title.
- **Why HMS needs it:** Appears in FastAPI `/docs` header and `/health` response envelope.
- **Which service uses it:** [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py).
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env) line 15 (`APP_NAME=HMS Backend`).
- **Where it is consumed:** `create_app()` and `GET /health`.
- **Required status:** Optional (defaults to `"HMS Backend"`).
- **If missing or invalid:** Uses fallback name.
- **Security notes:** Non-sensitive metadata.

### `APP_ENV`
- **What it is:** Environment mode designation (`development`, `test`, `staging`, `production`).
- **Why HMS needs it:** Critical operational gate. Triggers production security enforcement in `assert_production_ready()` and enables SQL query logging in development.
- **Which service uses it:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py), [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py), and [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py).
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env) line 16 (`APP_ENV=development`).
- **Where it is consumed:** Security assertions, database echo options, and `/health` payload.
- **Required status:** **Critical**.
- **If missing or invalid:** Defaults to `"development"`.
- **Security notes:** Non-sensitive mode flag.

### `DEBUG`
- **What it is:** Boolean flag controlling developer diagnostics.
- **Why HMS needs it:** Toggles verbose SQLAlchemy query logging (`echo=True`).
- **Which service uses it:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) line 14.
- **Where it is configured:** [backend/.env](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/.env) line 17 (`DEBUG=true`).
- **Where it is consumed:** Engine creation (`echo=settings.DEBUG and settings.APP_ENV == "development"`).
- **Required status:** Optional (defaults to `True`).
- **If missing or invalid:** Defaults to `True`.
- **Security notes:** Non-sensitive operational flag. Should be set to `false` in production to prevent query logs in stdout.

### `API_V1_PREFIX`
- **What it is:** URI path prefix for version 1 API endpoints.
- **Why HMS needs it:** Namespaces all business endpoints under `/api/v1`.
- **Which service uses it:** [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py) line 58.
- **Where it is configured:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) line 19.
- **Where it is consumed:** `app.include_router(api_router, prefix=settings.API_V1_PREFIX)`.
- **Required status:** Optional (defaults to `"/api/v1"`).
- **If missing or invalid:** Defaults to `"/api/v1"`.
- **Security notes:** Non-sensitive path string.

### `CORS_ORIGINS`
- **What it is:** Comma-separated list of browser origins permitted to execute cross-origin requests.
- **Why HMS needs it:** Prevents browsers from blocking frontend requests served from Vite dev ports (8080, 8081, 5173).
- **Which service uses it:** FastAPI `CORSMiddleware` in [backend/app/main.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/main.py).
- **Where it is configured:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) lines 42-46.
- **Where it is consumed:** `app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)`.
- **Required status:** Optional (defaults to 6 standard local origins).
- **If missing or invalid:** Uses local defaults. In production, must be explicitly set to the production frontend domain.
- **Security notes:** Security policy setting. Must never be set to `*` in production with `allow_credentials=True`.

### `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`, `BSS_DATABASE_URL`
- **What they are:** Configuration settings for a secondary MySQL 8.0 commercial BSS database (`hms_bss`).
- **Why HMS needs them:** Preparedness hooks for the planned v3 architectural split between OSS (PostgreSQL) and BSS (MySQL).
- **Which service uses them:** [backend/app/db/session.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) (`get_bss_engine`, `get_bss_db`) and [backend/app/api/v1/endpoints/health.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/health.py) (`bss_database_health`).
- **Where it is configured:** [backend/app/core/config.py](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) lines 59-64.
- **Where it is consumed:** Lazy engine initialization in `get_bss_engine()`.
- **Required status:** **Inactive / Optional**.
- **If missing or invalid:** `/api/v1/health/bss-db` returns `{"status": "pending_provision"}`. Has zero impact on active HMS operations.
- **Security notes:** `MYSQL_PASSWORD` and `BSS_DATABASE_URL` are **High Secrets** if activated.

### `VITE_API_BASE_URL`
- **What it is:** Base endpoint URL consumed by the frontend API client.
- **Why HMS needs it:** Dictates where frontend HTTP requests (`apiClient.get`, `apiClient.post`) are dispatched.
- **Which service uses it:** [frontend/src/lib/api/client.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/src/lib/api/client.ts) (line 15).
- **Where it is configured:** [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) and [frontend/.env.local](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.local) line 9 (`VITE_API_BASE_URL=/api/v1`).
- **Where it is consumed:** `const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1"`.
- **How it works:**
  - In local development: Kept as relative `/api/v1`. Vite dev proxy intercepts and forwards to `VITE_API_PROXY_TARGET`.
  - In deployed production: Set to full backend origin (e.g. `https://api.hms.example.com/api/v1`).
- **Required status:** Optional in dev; **Required in production** if frontend and backend are hosted on separate domains.
- **If missing or invalid:** Defaults to `/api/v1`.
- **Security notes:** Public variable; embedded directly into compiled JavaScript bundle.

### `VITE_API_PROXY_TARGET`
- **What it is:** Dev server proxy target address.
- **Why HMS needs it:** Enables Vite's development server to proxy `/api/v1` traffic to the local Uvicorn/FastAPI backend, eliminating CORS preflight overhead.
- **Which service uses it:** [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) line 11.
- **Where it is configured:** [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) and [frontend/.env.local](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.local) line 12 (`VITE_API_PROXY_TARGET=http://127.0.0.1:8000`).
- **Where it is consumed:** `proxy: { "/api/v1": { target: apiTarget, changeOrigin: true } }`.
- **Required status:** Optional in local dev (defaults to `"http://127.0.0.1:8000"`). Not used in production build.
- **If missing or invalid:** If backend is running on a non-default port, proxy returns HTTP 502/504 and UI displays `Cannot reach the HMS API`.
- **Security notes:** Local development tooling configuration; not exposed in production builds.

### `VITE_PLATFORM_RELEASE_DATE`
- **What it is:** Static build release date override.
- **Why HMS needs it:** Allows CI/CD release pipelines to pin an authoritative release date shown on the About screen.
- **Which service uses it:** [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) line 15.
- **Where it is configured:** [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) line 13.
- **Where it is consumed:** Replaces compile-time global `__PLATFORM_RELEASE_DATE__`.
- **Required status:** Optional (defaults to current date at build time).
- **If missing or invalid:** Defaults to `new Date().toISOString().slice(0, 10)`.
- **Security notes:** Public build metadata.

### `VITE_PLATFORM_LICENSE`
- **What it is:** Commercial software license tier display string.
- **Why HMS needs it:** Renders the license badge in the application layout and about view.
- **Which service uses it:** [frontend/src/core/config/platform.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/src/core/config/platform.ts) line 12.
- **Where it is configured:** [frontend/.env.example](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/.env.example) line 14.
- **Where it is consumed:** `export const PLATFORM_LICENSE = import.meta.env.VITE_PLATFORM_LICENSE || "Enterprise"`.
- **Required status:** Optional (defaults to `"Enterprise"`).
- **If missing or invalid:** Displays default label `"Enterprise"`.
- **Security notes:** Public display metadata.

### `VITE_HOST` & `PORT` / `VITE_PORT`
- **What they are:** Host interface and TCP port for the Vite development HTTP server.
- **Why HMS needs it:** Controls network binding for the frontend dev server.
- **Which service uses it:** [frontend/vite.config.ts](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/frontend/vite.config.ts) lines 19-20.
- **Where it is configured:** Passed via CLI or `.env.local`.
- **Where it is consumed:** Vite server options.
- **Required status:** Optional (defaults to host `"localhost"` and port `8081`).
- **If missing or invalid:** Falls back to defaults.
- **Security notes:** Local tooling settings.

---

## 4. Integration Flow Architecture

The following diagrams map the exact flow of configuration and credentials from environment files to executing code:

### Flow 1: Primary Database Connection (PostgreSQL 18)
```
[backend/.env]
  |  POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
  v
[backend/app/core/config.py]
  |  Settings.sqlalchemy_url property assembles DSN:
  |  postgresql+psycopg2://<user>:<password>@<host>:<port>/<db>
  v
[backend/app/db/session.py]
  |  create_engine(settings.sqlalchemy_url, pool_pre_ping=True)
  |  SessionLocal = sessionmaker(bind=engine)
  v
[backend/app/api/deps.py]
  |  DbSession = Annotated[Session, Depends(get_db)]
  v
[backend/app/services/*.py]
  |  Executes queries against live PostgreSQL tables
```

### Flow 2: JWT Authentication & Request Authorization
```
[backend/.env]
  |  JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, APP_ENV
  v
[backend/app/core/config.py]
  |  Settings.assert_production_ready() enforces valid key outside dev
  v
[backend/app/api/v1/endpoints/auth.py]
  |  POST /api/v1/auth/login validates credentials -> calls security.create_access_token()
  v
[backend/app/core/security.py]
  |  jwt.encode({"sub": user_id, "typ": "access", ...}, settings.JWT_SECRET_KEY)
  |  Returns bearer access token
  v
[frontend/src/lib/api/client.ts]
  |  setToken() stores token in browser localStorage['hms.access_token']
  |  Subsequent requests attach header: 'Authorization: Bearer <token>'
  v
[backend/app/api/deps.py]
  |  get_current_user() intercepts header -> security.decode_access_token()
  |  Validates signature using settings.JWT_SECRET_KEY -> extracts user_id
  |  auth_service.load_hms_web_user() re-reads permissions from PostgreSQL
  |  require_permission() gates access to requested endpoint
```

### Flow 3: Frontend API Call & Dev Proxy
```
[frontend/.env.local]
  |  VITE_API_BASE_URL=/api/v1
  |  VITE_API_PROXY_TARGET=http://127.0.0.1:8000
  v
[frontend/vite.config.ts]
  |  Configures Vite dev server proxy:
  |  proxy: { "/api/v1": { target: "http://127.0.0.1:8000", changeOrigin: true } }
  v
[frontend/src/lib/api/client.ts]
  |  API_BASE_URL = "/api/v1"
  |  Dispatches fetch('/api/v1/occupancy')
  v
[Vite Dev Server Proxy (Port 8081)]
  |  Forwards request over loopback to http://127.0.0.1:8000/api/v1/occupancy
  v
[FastAPI / Uvicorn Server (Port 8000)]
  |  Handles request, executes service logic, returns JSON payload
```

---

## 5. Frontend vs Backend Security Analysis

### 5.1 Secrets Restricted to Backend Only
The following items must strictly exist on the backend and **never** be copied into frontend environment files or referenced in React source:
- `POSTGRES_PASSWORD` and `DATABASE_URL`
- `JWT_SECRET_KEY`
- `MYSQL_PASSWORD` and `BSS_DATABASE_URL`
- Database row-level bcrypt hashes (`app_user.password_hash`)

### 5.2 Public Frontend Variables
Vite prefixes public variables with `VITE_`. All variables prefixed with `VITE_` are intentionally embedded into the compiled JavaScript bundle delivered to client browsers:
- `VITE_API_BASE_URL` (Public URL pointer)
- `VITE_API_PROXY_TARGET` (Build/dev config only)
- `VITE_PLATFORM_RELEASE_DATE` (Public release date)
- `VITE_PLATFORM_LICENSE` (Public license label)

### 5.3 Client-Side Token Storage Audit
- **Storage Location:** Browser `localStorage` under key `hms.access_token`.
- **Security Assessment:**
  - `localStorage` is accessible to client-side JavaScript. While standard for single-page applications without server-side rendering, it is vulnerable to Cross-Site Scripting (XSS) if untrusted scripts run.
  - **Mitigation Present:** Tokens carry **zero roles or permissions**. Stolen tokens cannot elevate privileges because the backend re-reads authorization from PostgreSQL on every request.
  - **Recommendation:** In high-security production deployments, consider transitioning to `HttpOnly`, `Secure`, `SameSite=Strict` cookies.

### 5.4 Hardcoded Credentials & Secrets Scan
An automated scan of all tracked source code identified **zero production secrets or API keys**.
The only hardcoded passwords found are synthetic fixtures used strictly in automated unit tests:
- `backend/tests/test_access_write_api.py:287` (`SecurePass#2026`)
- `backend/tests/test_access_write_api.py:340` (`LoginTest#2026`)
- `backend/tests/test_access_write_api.py:369` (`RightPass#2026`)

---

## 6. Environment and Deployment Checklist

### Category A: Required for Local Backend Startup
- [x] Python 3.13+ virtual environment with dependencies installed from [backend/requirements.txt](file:///c:/Users/user/OneDrive%20-%20Inspironics%20India/Insp%20Total%20Work/HMS-Frontend/ACX-Platform/backend/requirements.txt).
- [x] `backend/.env` created from `backend/.env.example`.
- [x] `POSTGRES_PASSWORD` set to match the local PostgreSQL instance password.
- [x] `POSTGRES_PORT=5432` verified pointing at active PostgreSQL 18 server.
- [x] `APP_ENV=development` confirmed.
- [x] PostgreSQL database `hms_db` running and migrated to revision `9a2b3c4d5e6f`.

### Category B: Required for Production Backend Deployment
- [ ] Set `APP_ENV=production`.
- [ ] Generate high-entropy secret for `JWT_SECRET_KEY`:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- [ ] Set `DEBUG=false` to disable verbose SQL echo in logs.
- [ ] Set `CORS_ORIGINS` to the exact production frontend HTTPS domain (e.g. `https://hms.inspironics.net`).
- [ ] Set `POSTGRES_HOST`, `POSTGRES_USER`, and strong `POSTGRES_PASSWORD` for the managed database cluster.

### Category C: Required for Frontend Build and Runtime
- [x] Node.js 20+ and npm dependencies installed via `npm ci` in `frontend/`.
- [x] Local dev: `frontend/.env.local` with `VITE_API_BASE_URL=/api/v1` and `VITE_API_PROXY_TARGET=http://127.0.0.1:8000`.
- [ ] Production build: Set `VITE_API_BASE_URL` to the public production API URL (or leave relative if hosted behind a reverse proxy like NGINX).

### Category D: Inactive / Obsolete Variables
- `MYSQL_*` / `BSS_DATABASE_URL`: Inactive until BSS MySQL domain is provisioned.
- `DATABASE_URL`: Redundant when individual `POSTGRES_*` parts are set. Keep commented unless required by container orchestration.

---

## 7. Audit Conclusion & Compliance Summary

- **Total Configuration & Credential Keys Analyzed:** **28 items**
- **External Third-Party API Keys:** **0** (No SaaS dependencies)
- **Active Secrets:** **2** (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`)
- **Compliance Status:** The repository follows sound separation of secrets. Local credentials are git-ignored in `.env` and `.env.local`. Test fixtures use isolated synthetic passwords. Production guards are actively enforced in code.
