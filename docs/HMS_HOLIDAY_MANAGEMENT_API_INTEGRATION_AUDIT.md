# HMS Holiday Management API Integration Audit Report

---

## 1. Existing HMS Architecture Relevant to Holidays

The Hotel Management System (HMS) application is structured as a decoupled two-tier web application consisting of a React single-page application (SPA) frontend and a Python FastAPI backend connected to PostgreSQL:

* **Frontend Framework & Layer:** React 18 with TypeScript, built via Vite. Styling is handled via Vanilla Tailwind CSS and Radix UI primitives. Data fetching and cache synchronization use TanStack Query (React Query v5).
* **Backend Framework & Layer:** Python 3.12/3.13 running FastAPI 0.135.3 with Uvicorn. Data modeling and persistence use SQLAlchemy 2.0 ORM with PostgreSQL (driver `psycopg2-binary`). Request/response schemas are validated via Pydantic v2 (`pydantic.BaseModel`).
* **Authentication & Authorization:** 
  * Authenticated sessions are established using JWT access tokens passed via the standard `Authorization: Bearer <token>` header. Token generation and decoding reside in [`app/core/security.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/core/security.py).
  * Role-Based Access Control (RBAC) is enforced on the database level via table `role_module_permission`. Holiday access is governed by the seeded module `holidays` (module ID `17` in [`reference.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/seeds/data/reference.py#L140)).
  * Endpoints are protected by the backend dependencies [`require_permission("holidays", "read")`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/deps.py#L69-L97) and [`require_permission("holidays", "write")`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/deps.py#L69-L97).
  * The frontend route `/holidays` is mapped to module `"holidays"` in [`modules.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/core/rbac/modules.ts#L68). The UI conditionally toggles submit/delete actions using `useAuth().canWrite("holidays")`.
* **Configuration & Secret Management:**
  * Backend: Managed via Pydantic [`Settings`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/core/config.py#L9-L73) loading `.env` (`pydantic-settings`).
  * Frontend: Managed via Vite client envs (`VITE_*`) through [`.env.local`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/.env.local) and [`.env.example`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/.env.example).
* **Background Jobs & Scheduling:**
  * While the database schema contains legacy metadata tables [`scheduler_job`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/models/operations.py) and [`scheduler_job_execution`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/models/operations.py), **no runtime background scheduler or worker engine (such as Celery, APScheduler, or Redis Queue) is configured or running in FastAPI**. The backend runs solely as an HTTP request-response service.

---

## 2. Holiday Management Frontend File Paths

All frontend source files relevant to Holidays Management are located within the `frontend/` directory:

| Component / Utility | File Path | Description |
| :--- | :--- | :--- |
| **Page Component** | [`frontend/src/features/marketing/pages/Holidays.tsx`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Holidays.tsx) | Complete Holidays UI: Add/Edit Form, Search, Pagination, Table Display, Soft-Delete confirmation modal. |
| **API Client & Writes** | [`frontend/src/lib/api/writes.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L521-L552) | Declares [`HolidayRead`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L521), [`HolidayWrite`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L538), [`OccasionTypeRead`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L549), and endpoints [`listHolidays`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L750), [`listOccasionTypes`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L752), [`createHoliday`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L753), and [`updateHoliday`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts#L755). |
| **Query Hooks** | [`frontend/src/lib/api/hooks.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/hooks.ts#L326-L329) | React Query hooks [`useHolidays`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/hooks.ts#L326) and [`useOccasionTypes`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/hooks.ts#L329). |
| **Mutation Hooks** | [`frontend/src/lib/api/mutations.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/mutations.ts#L446-L458) | React Query mutations [`useCreateHoliday`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/mutations.ts#L446) and [`useUpdateHoliday`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/mutations.ts#L452). |
| **RBAC Route Config** | [`frontend/src/core/rbac/modules.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/core/rbac/modules.ts#L68) | Maps `/holidays` route to the `"holidays"` backend role module. |
| **Sidebar Navigation** | [`frontend/src/components/layout/AppSidebar.tsx`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/components/layout/AppSidebar.tsx#L174) | Sidebar item linking to `/holidays` under the "Manage" group. |
| **App Routing** | [`frontend/src/App.tsx`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/App.tsx#L97) | Registers route `<Route path="/holidays" element={<Holidays />} />`. |

---

## 3. Holiday Backend API, Controller, Service & Model File Paths

All backend endpoints, domain services, Pydantic schemas, and SQLAlchemy ORM models reside in the `backend/` directory:

| Backend Component | File Path | Description |
| :--- | :--- | :--- |
| **API Endpoints (Controller)** | [`backend/app/api/v1/endpoints/facility_write.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/v1/endpoints/facility_write.py#L90) | Defines [`holidays_router`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/v1/endpoints/facility_write.py#L90) handling `GET /holidays`, `GET /holidays/types`, `POST /holidays`, and `PATCH /holidays/{occasion_id}`. |
| **Router Aggregation** | [`backend/app/api/v1/router.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/v1/router.py#L88) | Includes `holidays_router` into `/api/v1`. |
| **Read Query Service & DTOs** | [`backend/app/services/catalog.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L121-L143) | Defines [`OccasionRead`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L121), [`OccasionTypeRead`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L138), [`list_occasions`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L306), [`get_occasion`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L336), and [`list_occasion_types`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L341). |
| **Write Service** | [`backend/app/services/facility_write.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/facility_write.py#L367-L410) | Implements [`create_occasion`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/facility_write.py#L367) and [`update_occasion`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/facility_write.py#L394) with date validation and month/day derivation. |
| **Pydantic Schemas** | [`backend/app/schemas/ops_write.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/schemas/ops_write.py#L448-L469) | Defines validation models [`OccasionCreate`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/schemas/ops_write.py#L448) and [`OccasionUpdate`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/schemas/ops_write.py#L461). |
| **SQLAlchemy ORM Models** | [`backend/app/models/marketing.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/models/marketing.py#L129-L187) | Declares [`OccasionType`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/models/marketing.py#L129) and [`Occasion`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/models/marketing.py#L141). |
| **Database Migrations** | [`backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/migrations/versions/0e2687233b59_phase1_7_hms_92_table_foundation.py#L747-L772) | DDL creating table `occasion` and table `occasion_type`. |
| **Unit & Integration Tests** | [`backend/tests/test_catalog_write_api.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/tests/test_catalog_write_api.py#L426-L515) | Test cases verifying holiday CRUD operations, lookup retrieval, and validation logic. |

---

## 4. Existing Holiday Database Table and Field Mapping

### Table Structure
The HMS system **does not have a standalone table named `holiday`**. Instead, holidays are stored in the table **`occasion`**, categorized by the lookup table **`occasion_type`** (where `id = 4` is `"Holiday"`).

```
   ┌────────────────────────────────────────────────────────┐
   │                     occasion_type                      │
   ├────────────────────────────────────────────────────────┤
   │ id: SMALLINT (PK) [1: Festival, 2: Birthday,           │
   │                    3: Marriage anniversary, 4: Holiday]│
   │ occasion_type: VARCHAR(50)                             │
   │ notification_template: TEXT                            │
   │ created_on / updated_on: TIMESTAMPTZ                   │
   └───────────────────────────┬────────────────────────────┘
                               │ 1:N
   ┌───────────────────────────▼────────────────────────────┐
   │                        occasion                        │
   ├────────────────────────────────────────────────────────┤
   │ id: UUID (PK)                                          │
   │ occasion_name: VARCHAR(100) (Stores "Lock message")    │
   │ occasion_type: SMALLINT (FK -> occasion_type.id)       │
   │ occasion_start_date: DATE (NOT NULL, indexed)          │
   │ occasion_end_date: DATE (Nullable)                     │
   │ month: SMALLINT (Derived from start_date.month)        │
   │ day_of_month: SMALLINT (Derived from start_date.day)   │
   │ is_repeatable: BOOLEAN (Default FALSE)                 │
   │ notification_template: TEXT (Nullable, Hub message)    │
   │ facility_id: UUID (FK -> facility.id, Nullable)        │
   │ app_user_id: UUID (FK -> app_user.id, Nullable)        │
   │ notify_to_hub: BOOLEAN (Default TRUE)                  │
   │ status: SMALLINT (1 = active, 0 = retired / deleted)   │
   │ created_by: UUID (FK -> app_user.id, Nullable)         │
   │ legacy_id: BIGINT (Unique, Nullable)                   │
   │ created_on / updated_on: TIMESTAMPTZ (NOT NULL)        │
   └────────────────────────────────────────────────────────┘
```

### Comprehensive Field Mapping Analysis

| UI Field / Concept | Frontend Form & State | REST API Payload (JSON) | DB Column (`occasion`) | Type & Constraints | Verified Behavior & Identified Gaps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Holiday ID** | `item.id` | `id` | `id` | `UUID` (PK, default uuid4) | Direct match. |
| **Start Date** | `startDate` (`<Input type="date">`) | `occasion_start_date` | `occasion_start_date` | `DATE`, NOT NULL, indexed | Direct match (formatted as `YYYY-MM-DD`). |
| **End Date** | `endDate` (`<Input type="date">`) | `occasion_end_date` | `occasion_end_date` | `DATE`, Nullable | Direct match. Backend validates `end_date >= start_date`. |
| **Lock message** | `lockMessage` (`<Input>`) | `occasion_name` | `occasion_name` | `VARCHAR(100)`, Nullable | **Field Mismatch**: The UI labels this "Lock message", but it is stored in `occasion_name`. Table `occasion` lacks a dedicated `lock_message` column. |
| **Description** | `description` (`<Textarea>`) | *None* | *None* (or `occasion_type`) | N/A | **Data Loss**: `Holidays.tsx:98-102` matches this textarea against `occasion_type` names and discards the user's free text. The table column displays `occasion_type_name`. |
| **Month & Day** | *Implicit* | Derived server-side | `month`, `day_of_month` | `SMALLINT`, NOT NULL | Automatically derived from `occasion_start_date` by [`facility_write.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/facility_write.py#L385-L386). |
| **Repeatable** | *Not in UI* | `is_repeatable` | `is_repeatable` | `BOOLEAN`, default False | Optional boolean flag. |
| **Notify to Hub** | *Not in UI* | `notify_to_hub` | `notify_to_hub` | `BOOLEAN`, default True | Flags in-room hub notifications. |
| **Facility / Tenant** | *Not in UI* | Auto-assigned | `facility_id` | `UUID` (FK to `facility.id`) | Assigned from `current_user.facility_ids[0]` during create. |
| **Status / Delete** | Delete button | `PATCH { status: 0 }` | `status` | `SMALLINT` (default 1) | Soft delete (`0` = retired, `1` = active). **There is no HTTP DELETE endpoint**. |
| **Timestamps** | *Not in UI* | Returned in GET | `created_on`, `updated_on` | `TIMESTAMPTZ`, NOT NULL | Auto-managed by SQLAlchemy mixins. |
| **Country / State** | *Not in UI or DB* | *None* | *None* | N/A | Neither `occasion` nor `facility` carries a country code. `facility` carries `state` as text. |

### Multi-Day Holidays Analysis
* **Can a holiday span multiple days?** **Yes.** `occasion_start_date` and `occasion_end_date` can be different calendar days. For instance, the database seed defines Diwali from `2026-11-08` to `2026-11-10` and Pongal from `2027-01-14` to `2027-01-17`.
* **How the UI displays it:** The Holidays table displays `startDate` and `endDate` in distinct columns side-by-side (`TableCell`), and displays `"-"` if `endDate` is null.

---

## 5. External Holiday API Integration Status

* **Search Results:** A comprehensive regex and text search across the entire codebase, configuration files, and git commit history returned **0 occurrences** for:
  * `calendarific` / `api.calendarific.com`
  * `/api/v2/holidays`
  * `CALENDARIFIC_API_KEY`
  * `HOLIDAY_API_KEY`
* **External HTTP Requests:** Zero external HTTP requests are made anywhere in the backend application (the `httpx` package in `requirements.txt` is installed strictly for `fastapi.testclient`). The frontend `fetch()` calls are confined exclusively to `client.ts` pointing at the local `/api/v1` backend base URL.
* **Integration Status:** **Completely Non-Existent**. No code, client library, test, or stub exists for Calendarific or any third-party holiday API.

---

## 6. API-Key Configuration Status

* **Status:** **Missing Entirely**.
* **Configuration Locations Inspected:**
  * [`backend/.env`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/.env) & [`backend/.env.example`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/.env.example) — Configures only `POSTGRES_*`, `APP_*`, `JWT_*`. No holiday key variable exists.
  * [`frontend/.env.local`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/.env.local) & [`frontend/.env.example`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/.env.example) — Configures only `VITE_API_BASE_URL` and `VITE_API_PROXY_TARGET`.
  * [`backend/app/core/config.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/core/config.py) — The Pydantic `Settings` model defines no holiday configuration attributes.
* **Backend Code Reference:** Neither backend code nor test suites reference any holiday API key.
* **Security & Secret Exposure:**
  * **No secrets or credentials are hardcoded or exposed** in the frontend, backend, or documentation.
  * No external holiday credentials exist in the environment.

---

## 7. Security Problems & Existing Codebase Anomalies

1. **Frontend Discards Holiday Description (Action Item A7):**
   * *Location:* [`frontend/src/features/marketing/pages/Holidays.tsx:98-106`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Holidays.tsx#L98-L106).
   * *Issue:* The form presents a multiline "Description" textarea. However, `Holidays.tsx` attempts to match the typed text against the names of lookup types (`Festival`, `Birthday`, `Marriage anniversary`, `Holiday`) to pick an `occasion_type` ID. The actual text typed by the operator is dropped completely and never sent in the payload.
2. **GET /holidays Returns Soft-Deleted and Non-Holiday Occasions (Action Item A6):**
   * *Location:* [`backend/app/services/catalog.py:306-334`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/services/catalog.py#L306-L334).
   * *Issue:* `list_occasions` executes `select(Occasion)` without filtering by `status == 1` or `occasion_type == 4`. As a result, retired occasions (`status = 0`) and personal/facility occasions (like birthdays and anniversaries) are returned to the Holidays Management screen.
3. **Missing HTTP DELETE Endpoint:**
   * *Location:* [`backend/app/api/v1/endpoints/facility_write.py:90`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/v1/endpoints/facility_write.py#L90).
   * *Issue:* There is no `DELETE /api/v1/holidays/{id}` route. Deletion is simulated via `PATCH /holidays/{id}` setting `status: 0`. Any future bulk import integration must be aware of this soft-delete pattern to avoid unretiring or colliding with retired holidays.

---

## 8. Recommended Integration Flow

To safeguard existing HMS functionality while enabling automated or semi-automated holiday importing, the integration must follow a **backend-mediated preview-and-import** pattern:

```
┌────────────────────────┐
│ External Holiday API   │ (Calendarific / Official Source)
└───────────┬────────────┘
            │ HTTPS (API Key held in backend .env only)
            ▼
┌────────────────────────────────────────────────────────┐
│ HMS Backend (FastAPI)                                  │
│                                                        │
│ 1. POST /api/v1/holidays/external/preview              │
│    - Accepts { year, country, state? }                 │
│    - Fetches external holidays via backend httpx client│
│    - Normalizes payload to HMS schema                  │
│    - Duplicate Detection against table `occasion`      │
│    - Returns comparison: [NEW], [EXISTS], [CONFLICT]   │
│                                                        │
│ 2. POST /api/v1/holidays/external/import               │
│    - Accepts selected holiday array                    │
│    - Derives `month`, `day_of_month`, `facility_id`    │
│    - Writes atomically to `occasion` table             │
└───────────┬────────────────────────────────────────────┘
            │ JSON Responses
            ▼
┌────────────────────────────────────────────────────────┐
│ HMS Frontend (Holidays.tsx)                            │
│                                                        │
│ - Preserves manual Add/Edit/Delete form as fallback    │
│ - New "Import Holidays" Dialog:                        │
│   * Year selector, Country/State selectors             │
│   * "Fetch / Preview Holidays" action                  │
│   * Interactive review table with checkboxes           │
│   * Badges indicating [New], [Duplicate / Skip]        │
│   * Single-click Confirm & Import                      │
│ - React Query automatically refreshes existing table   │
└────────────────────────────────────────────────────────┘
```

### Detailed Flow Steps:
1. **Operator Initiation:** From the Holidays screen, the operator clicks **"Import Holidays"**, opens a dialog, and selects the desired Year, Country (e.g., `IN`), and optional State (e.g., `TN`).
2. **Backend Fetch & Normalization:** The frontend calls `POST /api/v1/holidays/external/preview`. The backend validates authorization (`HOLIDAYS_WRITE`), calls the external API with the backend-stored credential, and standardizes incoming dates and holiday names.
3. **Duplicate Detection:** The backend queries existing `occasion` records for the facility and target year:
   * Matches by identical date and normalized name.
   * Categorizes each record: `to_create` (new), `already_exists` (identical match), or `updated` (date match with different name).
4. **Interactive Review:** The modal presents the preview list with clear visual status tags and selection checkboxes. Existing holidays are unchecked by default to prevent unwanted overwrites.
5. **Execution & Persistence:** Upon operator confirmation, the selected records are sent to `POST /api/v1/holidays/external/import`. The backend inserts the records into `occasion` with `occasion_type = 4` ("Holiday"), `status = 1`, and auto-derived `month` and `day_of_month`.
6. **UI Refresh:** The mutation invalidates `["holidays"]` in React Query, automatically refreshing the main table. Manual Add, Edit, and Delete remain completely unchanged.

---

## 9. Required Changes Grouped by Layer

### Frontend (`frontend/`)
* **Page Enhancements (`Holidays.tsx`):**
  * Add an **"Import Holidays"** action button in the card header.
  * Implement an `ImportHolidaysDialog` component featuring:
    * Selectors for Year, Country code, and optional State/Region.
    * "Fetch Preview" button triggering preview query.
    * Preview table displaying Holiday Name, Start Date, End Date, Type, and duplicate status badge.
    * Checkbox selection (Select All New, Deselect Duplicates).
    * Clear error alert banner showing friendly messages for API rate limits, network timeouts, or invalid keys.
* **API Client & Hooks (`writes.ts`, `hooks.ts`, `mutations.ts`):**
  * Add types `ExternalHolidayPreviewRequest`, `ExternalHolidayItem`, `ExternalHolidayImportRequest`.
  * Add `previewExternalHolidays` and `importExternalHolidays` API client functions.
  * Add corresponding React Query hooks and mutations.
* **Bug Fix (Optional / Recommended):**
  * Correct the "Description" textarea behavior in `Holidays.tsx` so user descriptions are either saved into `notification_template` or mapped clearly rather than dropped.

### Backend (`backend/`)
* **Configuration (`app/core/config.py`):**
  * Add configuration variables to `Settings`:
    * `CALENDARIFIC_API_KEY: str | None = None`
    * `CALENDARIFIC_BASE_URL: str = "https://calendarific.com/api/v2"`
    * `CALENDARIFIC_TIMEOUT_SECONDS: int = 10`
* **External Client Service (`app/services/holiday_provider.py`):**
  * Implement an asynchronous HTTP client using `httpx.AsyncClient` to query the external provider.
  * Translate provider-specific errors (HTTP 401 Unauthorized, HTTP 429 Rate Limit Exceeded, 5xx outages) into structured HMS `ApiError` responses.
* **Import & Matching Logic (`app/services/holiday_import.py`):**
  * Implement normalization and duplicate comparison against table `occasion`.
  * Implement atomic batch insertion ensuring `occasion_type = 4`, `month = date.month`, `day_of_month = date.day`, `status = 1`, and `facility_id` are correctly populated.
* **Endpoints (`app/api/v1/endpoints/facility_write.py` or new `holidays_external.py`):**
  * `POST /api/v1/holidays/external/preview` (Dependencies: `HOLIDAYS_WRITE`)
  * `POST /api/v1/holidays/external/import` (Dependencies: `HOLIDAYS_WRITE`)
* **Bug Fix (Optional / Recommended in `catalog.py`):**
  * Update `list_occasions` to default `where(Occasion.status == 1)` so deleted holidays do not clutter the list.

### Database (`backend/`)
* **Zero Schema Changes Required:** No new tables, migrations, or DDL alters are needed. The existing `occasion` table contains all fields necessary to store imported holidays (`id`, `occasion_name`, `occasion_type`, `occasion_start_date`, `occasion_end_date`, `month`, `day_of_month`, `facility_id`, `status`).

### Configuration & Deployment
* Add placeholder `CALENDARIFIC_API_KEY=` in [`backend/.env.example`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/.env.example).
* Configure `CALENDARIFIC_API_KEY` in [`backend/.env`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/.env) on target environments.
* **Never** commit API keys to version control, and **never** prefix the variable with `VITE_` or expose it in `frontend/`.

---

## 10. Risks, Dependencies, and Licensing Blockers

### 1. Calendarific Terms of Service & Legal Licensing Blockers (Critical)
* **30-Day Caching / Storage Restriction:** Standard Calendarific Terms of Service explicitly restrict subscribers from caching or storing holiday data for longer than 30 days without an explicit commercial license. Permanently writing holiday records into PostgreSQL `occasion` table violates standard free/basic tier terms.
* **Attribution Requirement:** Free/Standard plans mandate public attribution ("Powered by Calendarific"). If HMS displays holidays on client-facing guest hubs or lock screens without attribution, this creates non-compliance.
* **Systematic Extraction Prohibition:** Calendarific forbids scraping, bulk downloading, or systematic extraction of complete datasets.
* **Blocker Resolution:** Written confirmation or an Enterprise/Custom data license from Calendarific permitting permanent storage and hub redistribution must be secured prior to production deployment.

### 2. Assessment of Previously Investigated Government Holiday Source
* **Suitability:** **Unsuitable for production use**.
* **Rationale:** An undocumented internal government portal or website endpoint has no SLA, is vulnerable to breaking UI/markup changes, lacks authentication stability, lacks versioning, and could be blocked by anti-bot or IP restrictions at any moment. It must not be relied upon as an official or stable API integration.

### 3. Operational & Quota Risks
* **Rate Limits (HTTP 429):** Calendarific enforces strict monthly call quotas (e.g., 500 calls/month on basic tiers). Uncontrolled automatic syncing or polling would exhaust quotas rapidly. The recommended Preview-and-Import on-demand model prevents quota drain.

---

## 11. Step-by-Step Implementation Plan

### Step 1: Legal & Provider Prerequisite Clearance
* Secure an approved API subscription and written confirmation regarding database persistence rights from Calendarific (or choose an open-license provider such as Nager.Date).
* Define the approved backend configuration key name (`CALENDARIFIC_API_KEY`).

### Step 2: Backend Provider Client & Service Implementation
1. Add `CALENDARIFIC_API_KEY` to [`backend/app/core/config.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/core/config.py).
2. Create `backend/app/services/holiday_provider.py` to handle external HTTP calls, query parameters (`api_key`, `country`, `year`, `location`), and provider error mapping.
3. Create `backend/app/services/holiday_import.py` to perform deduplication against the `occasion` table and execute atomic batch inserts.
4. Add Pydantic request/response schemas in `backend/app/schemas/holidays_external.py`.
5. Register endpoints `POST /holidays/external/preview` and `POST /holidays/external/import` in [`backend/app/api/v1/endpoints/facility_write.py`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/backend/app/api/v1/endpoints/facility_write.py), guarded by `HOLIDAYS_WRITE`.
6. Write backend unit tests in `backend/tests/test_holiday_integration.py` using mocked HTTP responses.

### Step 3: Frontend Client & Modal Integration
1. Extend [`frontend/src/lib/api/writes.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/writes.ts) with preview and import types and functions.
2. Add mutation hooks in [`frontend/src/lib/api/mutations.ts`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/lib/api/mutations.ts) that invalidate `["holidays"]` on import completion.
3. Build the `ImportHolidaysDialog` modal in [`frontend/src/features/marketing/pages/Holidays.tsx`](file:///c:/inspironics%20total%20work/ACX%20Platform/ACX-Platform/frontend/src/features/marketing/pages/Holidays.tsx).
4. Verify that manual Add, Edit, and Delete forms continue to operate without interference.

### Step 4: Verification & End-to-End Validation
1. Verify RBAC enforcement: Ensure operators with `read` permission can view imported holidays but cannot open or trigger the import modal.
2. Verify duplicate prevention: Run consecutive previews and verify that existing database records are flagged as duplicates and not duplicated upon re-import.
3. Verify multi-day holiday display: Confirm that multi-day holidays correctly render start and end dates in the UI table.

---

## 12. Separation of Verified Findings vs. Working Assumptions

### Verified Findings (Observed Directly in Codebase & Database Migrations)
1. Table `occasion` is the actual database table backing the Holidays Management module; there is no table named `holiday`.
2. Column `occasion_type` links to lookup table `occasion_type`, where `id = 4` represents `"Holiday"`.
3. Table `occasion` has no `lock_message` column; the UI inputs "Lock message" and stores it in `occasion.occasion_name`.
4. Multi-day holidays are natively supported by `occasion_start_date` and `occasion_end_date` and are rendered in separate columns in the UI.
5. Soft-delete is implemented in `Holidays.tsx` by setting `status: 0`; there is no HTTP DELETE endpoint.
6. The frontend currently drops the user's free text entered into the "Description" textarea due to an `occasion_type` lookup mapping bug.
7. No Calendarific or external holiday API code, URL, or credential exists anywhere in the repository.
8. No runtime background scheduler is executing in FastAPI.

### Working Assumptions (Subject to External Confirmation)
1. **Target Holiday Scope:** It is assumed the hotel operator wants to import national and regional/state public holidays for the facility's jurisdiction rather than religious observance days that are not official holidays.
2. **Attribution Display:** It is assumed the frontend will display any provider-required attribution text (e.g., "Holiday data powered by Calendarific") inside the import dialog or footer if a commercial license without whitelabeling is chosen.

---

## Single Most Important Next Action Required Before Implementation

> [!IMPORTANT]
> **Obtain formal written confirmation or an appropriate commercial license from Calendarific permitting permanent database storage and guest-facing display of their holiday data, or formally select an open-licensed alternative (such as Nager.Date) whose terms do not prohibit permanent caching and database persistence.**
