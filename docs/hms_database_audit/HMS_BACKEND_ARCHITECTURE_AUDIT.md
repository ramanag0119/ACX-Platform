# HMS Backend Architecture Audit Report

**Audit Type:** Read-Only Backend & Database Architecture Inspection  
**Date:** 2026-10-26  
**Auditor:** Antigravity AI Senior Backend & Database Architect  
**Repository:** [ACX-Platform](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform) / [backend](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend)  
**Authority Standards:** Strict Read-Only Policy; Zero Code / Schema / DML Modifications.

---

## 1. Executive Architecture Overview

The Hotel Management System (HMS) backend in this repository is built as a single, synchronous REST service providing operational PMS (Property Management System) APIs, hotel asset hierarchy management, guest check-in/checkout workflows, housekeeping tracking, service ticket workflows, and device telemetry integration.

### Core Technology Stack

| Layer | Technology | Version | Location / Entrypoint | Evidence / Role |
|---|---|---|---|---|
| **Web Framework** | FastAPI | `0.135.3` | [app/main.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/main.py) | Application factory, middleware, CORS, exception handlers |
| **ASGI Server** | Uvicorn | `0.34.0` | `uvicorn app.main:app` | ASGI server runtime on port 8000 |
| **ORM / Query Engine** | SQLAlchemy | `2.0.52` | [app/db/base.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/db/base.py) | Declarative mapping, session management, type annotations |
| **Database Driver** | psycopg2-binary | `2.9.11` | [app/core/config.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | PostgreSQL C-extension driver |
| **Schema Migrations** | Alembic | `1.19.1` | [migrations/env.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/migrations/env.py) | Version tracking via `alembic_version` |
| **Authentication** | python-jose & bcrypt | `3.5.0` & `5.0.0` | [app/core/security.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/core/security.py) | HS256 JWT tokens & bcrypt password hashing |
| **Configuration** | pydantic-settings | `2.7.1` | [app/core/config.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py) | Typed settings loaded from `.env` |
| **Data Validation** | Pydantic v2 | `2.12.5` | [app/schemas/](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/schemas) | Request parsing, response serialization |

---

## 2. Application Entry Point & Lifecycle

The backend application is initialized via [app/main.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/main.py) using the application factory `create_app()`:

```python
# app/main.py:26-79
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=API_VERSION,
        description="HMS backend for IKANOS HMS Web...",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    # CORS Middleware with origins from settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
    # Centralized exception handlers
    install_exception_handlers(app)
    install_write_error_handlers(app)
    # Mount aggregate v1 API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    ...
```

### Key Architectural Findings:
1. **Stateless Process:** The FastAPI process maintains no long-lived in-memory business state; all state resides in PostgreSQL.
2. **Zero In-Process Background Workers:** No Celery, APScheduler, or background worker threads are launched in `main.py`. Scheduled tasks and async telemetry queues defined in the schema (`scheduler_job`, `mqtt_broker`, `device_command`) are legacy schema constructs from IKANOS and are dormant within the active Python service.
3. **CORS Configuration:** Defaults to `http://localhost:8080`, `http://127.0.0.1:8080`, `http://localhost:5173`, `http://127.0.0.1:5173` if not explicitly provided in `backend/.env`.

---

## 3. API Router & Endpoint Architecture

The application mounts a single unified v1 router [app/api/v1/router.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/router.py) under prefix `/api/v1`. It aggregates 20 dedicated endpoint modules:

| Sub-Router Module | Endpoint File | Mounted Routers | Core Endpoints | Module Responsibility |
|---|---|---|---|---|
| **Health** | [endpoints/health.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/health.py) | `router` | `GET /health`, `GET /health/version`, `GET /health/db`, `GET /health/bss-db` | Process liveness, database latency, server version |
| **Auth** | [endpoints/auth.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/auth.py) | `router` | `POST /auth/login`, `GET /auth/me` | Operator login, token generation, identity hydration |
| **Facilities (Read)** | [endpoints/facilities.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/facilities.py) | 6 routers | `GET /facilities`, `GET /properties`, `GET /buildings`, `GET /floors`, `GET /rooms`, `GET /countries` | Physical property hierarchy queries |
| **Facilities (Write)** | [endpoints/facility_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/facility_write.py) | 9 routers | `POST/PATCH/DELETE /facilities`, `/rooms`, `/amenity-types`, `/packages`, `/features`, `/offers`, `/events`, `/holidays`, `/key-settings` | Physical asset mutations and marketing setups |
| **Access (Read)** | [endpoints/access.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/access.py) | 4 routers | `GET /users`, `GET /roles`, `GET /modules`, `GET /permissions` | Staff/guest directory and RBAC permissions |
| **Access (Write)** | [endpoints/access_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/access_write.py) | 4 routers | `POST/PATCH/DELETE /users`, `/roles`, `/departments`, `/job-functions` | User provisioning, role edits, org departments |
| **Services (Read)** | [endpoints/services.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/services.py) | 5 routers | `GET /service-types`, `/service-statuses`, `/service-categories`, `/service-items`, `/service-requests` | Service catalog and guest ticket queues |
| **Services (Write)** | [endpoints/services_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/services_write.py) | 3 routers | `POST/PATCH /service-requests`, `POST/PATCH /service-categories`, `/service-items` | Service orders creation, item updates, ticket lifecycle |
| **Maintenance** | [endpoints/maintenance.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/maintenance.py) | 2 routers | `GET/POST/PATCH/DELETE /maintenance-requests` | Preventive & corrective facility work orders |
| **Job Orders** | [endpoints/job_orders.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/job_orders.py) | 2 routers | `GET/POST/PATCH/DELETE /job-orders` | Technical facility work orders & device maintenance |
| **Stays (Read)** | [endpoints/stays.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/stays.py) | 2 routers | `GET /stays`, `GET /stays/<built-in function id>`, `GET /invoices` | Booking reservations, stay history, billing folios |
| **Stays (Write)** | [endpoints/stays_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/stays_write.py) | 4 routers | `POST /stays`, `POST /stays/<built-in function id>/check-in`, `POST /stays/<built-in function id>/check-out`, `/allocations`, `/occupants`, `/bulk` | Reservation creation, check-in, room swaps |
| **Occupancy** | [endpoints/occupancy.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/occupancy.py) | 3 routers | `GET /occupancy`, `GET /amenity-statuses`, `GET /amenity-conditions`, `GET /applicable-conditions` | Real-time room status, housekeeping condition badges |
| **Devices (Read)** | [endpoints/devices.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/devices.py) | 2 routers | `GET /device-types`, `GET /devices`, `GET /devices/<built-in function id>/health` | Hardware registry and online health telemetry |
| **Devices (Write)** | [endpoints/devices_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/devices_write.py) | 3 routers | `POST/PATCH /devices`, `POST/PATCH /incidents`, `POST/PATCH /limit-configs` | Hardware provisioning, incident tickets, threshold limits |
| **Alerts** | [endpoints/alerts.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/alerts.py) | 4 routers | `GET /alert-types`, `GET /alerts`, `GET /incidents`, `GET /value-alerts` | Hardware alarms, incident tracker, threshold alarms |
| **Notifications** | [endpoints/notifications.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/notifications.py) | 3 routers | `GET /notification-templates`, `GET /notifications`, `GET /activities` | In-app user notifications and audit activity feed |
| **Telemetry** | [endpoints/telemetry.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/telemetry.py) | 4 routers | `GET /device-params`, `GET /device-stats`, `GET /device-current-stats`, `/other-device-readings` | Sensor telemetry time-series and current readings |
| **Energy** | [endpoints/energy.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/energy.py) | 2 routers | `GET /energy-stats`, `GET /daily-data-points` | Hourly kWh consumption and daily dual KPI rollups |
| **Reports** | [endpoints/reports.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/api/v1/endpoints/reports.py) | 1 router | `GET /reports`, `GET /reports/{key}`, `GET /reports/{key}/export.xlsx` | 9 operational Excel/JSON business reports |

**Total Verified Endpoints in Application:** **182 endpoints** (verified via `app.routes` introspection).

---

## 4. Service & Repository Layer Design

The HMS backend employs a **Service-Oriented Architecture without an isolated Repository abstraction**. Data access logic is integrated directly into domain services located in [app/services/](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services):

- Direct SQLAlchemy 2.0 executable queries (`select()`, `insert()`, `update()`, `delete()`) are authored inside service functions.
- Every service function accepts an explicit `db: Session` instance injected by FastAPI's dependency injection (`DbSession`).
- Transactions are managed cleanly at the service boundary: read services execute within the request session without committing; write services invoke `db.commit()` and `db.refresh()` upon successful domain validation.
- Concurrency and optimistic conflict prevention are enforced via explicit validation queries rather than database-level row locks.

### Core Service Modules:
1. [services/auth.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/auth.py): Credential verification, JWT generation, user hydration.
2. [services/access.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/access.py) & [services/access_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/access_write.py): RBAC resolution, user and role CRUD.
3. [services/facility.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/facility.py) & [services/facility_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/facility_write.py): Physical building hierarchy and room asset operations.
4. [services/stay.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/stay.py) & [services/stays_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/stays_write.py): Check-in, checkout, reservation lifecycle, bulk CSV ingest.
5. [services/occupancy.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/occupancy.py): Room occupancy projection joining `amenity`, `amenity_status`, `amenity_condition_status`, and `stay`.
6. [services/service.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/service.py) & [services/services_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/services_write.py): Service requests and menu item management.
7. [services/maintenance.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/maintenance.py) & [services/maintenance_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/maintenance_write.py): Maintenance schedules and assignees.
8. [services/job_order.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/job_order.py) & [services/job_order_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/job_order_write.py): Job orders and device maintenance links.
9. [services/device.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/device.py) & [services/devices_write.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/devices_write.py): Device inventory, incidents, threshold limit configurations.
10. [services/reports.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/reports.py) & [services/report_export.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/services/report_export.py): Multi-module projection and OpenPyXL Excel export.

---

## 5. Database Connection & Session Management

Session and connection pooling are handled in [app/db/session.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) and [app/core/config.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/core/config.py):

```python
# app/db/session.py:10-36
engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    echo=settings.DEBUG and settings.APP_ENV == "development",
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### URL Assembly:
- As documented in the environment baseline, `DATABASE_URL` is commented out in `backend/.env`.
- SQLAlchemy URL is assembled from individual parameters: `postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}`.
- Target server is confirmed live: **PostgreSQL 18.6 on port 5432**, database `hms_db`, schema `public`.
- `pool_pre_ping=True` ensures stale or severed database connections are transparently re-established.

---

## 6. Authentication, Authorization & RBAC

The HMS backend implements a high-security, database-backed RBAC model:

```
[HTTP Request with Authorization: Bearer <JWT>]
                       |
                       v
         [get_current_user(deps.py)]
                       |
                       v
      [decode_access_token(security.py)] -> Validates HS256 & expiry; extracts user_id
                       |
                       v
     [load_hms_web_user(services/auth.py)]
                       |
         +-------------+-------------+
         | Queries app_user          |
         | Queries user_role         | -> Re-reads live permissions on EVERY request!
         | Queries role              |
         | Queries role_module_perm  |
         +-------------+-------------+
                       |
                       v
       [Platform Gate: is_hms_web_role()] -> role_type in {admin, manager}?
                       | (YES)
                       v
 [require_permission(module, perm)] -> Checked against role_module_permission table
```

### Critical Security Properties:
1. **Stateless JWTs:** Tokens contain only standard claims (`sub` = user UUID, `typ="access"`, `iat`, `exp`). Permissions, emails, and roles are **never trusted from the token payload**.
2. **Real-Time Revocation:** Every authenticated request executes SQL queries in `load_hms_web_user()` against `app_user`, `user_role`, `role`, and `role_module_permission`. A deactivated user or revoked permission takes effect instantaneously.
3. **Strict Platform Boundary:** Accounts with `role_type` in `staff`, `guest`, or `system_user` are barred with HTTP 403. Only `admin` and `manager` roles may access HMS Web.
4. **Data-Driven Permissions:** 18 distinct modules (`role_module`) define granular `read_access` and `write_access` flags across 65 permission rows.

---

## 7. Background Tasks & External Integrations

### Background Schedulers:
- **No In-Process Worker:** The FastAPI application runs zero cron jobs, Celery workers, or scheduler loops.
- **Dormant Schema Tables:** The tables `scheduler_job` and `scheduler_job_execution` are present from the legacy `caleido_scheduler` MySQL service. They are unreferenced by active service logic.
- **Synchronous CSV Ingest:** The endpoint `/api/v1/stays/bulk` parses guest reservation CSVs synchronously in-request and updates `import_job` with status, rows processed, and error summaries.

### External & OSS Integrations:
- **No Outbound HTTP/MQTT Clients:** The Python backend currently contains zero active outbound HTTP requests to external APIs, zero MQTT client listeners, and zero hardware sockets.
- **Dual-Database Preparedness:** [app/db/session.py](file:///C:/Users/user/OneDrive - Inspironics India/Insp Total Work/HMS-Frontend/ACX-Platform/backend/app/db/session.py) defines lazy connection factories for a secondary BSS MySQL database (`get_bss_engine`, `get_bss_db`), and `/api/v1/health/bss-db` provides a probe endpoint returning `status="pending_provision"`.
- **Active Operational State:** The HMS backend operates 100% against the single PostgreSQL `hms_db` database instance.
