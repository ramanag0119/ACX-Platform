# HMS Complete Technical Glossary and Reference

**Audit date:** 2026-10-16  
**Scope:** Terms used by the current HMS frontend, FastAPI backend, SQLAlchemy/PostgreSQL layer, and API integration. Each explanation is tied to repository evidence. “Tanglish” is a simple Tamil-English explanation written in Latin letters.

## 1. HMS Architecture Explained

The browser runs a React single-page application. React Router chooses a page; components read state and hooks. API hooks call typed functions through one HTTP client. FastAPI validates requests, checks dependencies such as authentication, calls service functions, and returns Pydantic response objects. SQLAlchemy turns service queries into PostgreSQL operations. The database stores facilities, rooms, stays, devices, service requests, alerts, permissions, and other records.

**Tanglish:** Browser-la React UI irukku. User page open pannumbodhu Router correct screen-a kaattum. UI API request anuppum; FastAPI validate/authenticate pannitu service moolama PostgreSQL-la read/write seyyum. Response thirumbi UI-la render aagum.

Main evidence: `frontend/src/App.tsx`, `frontend/src/lib/api/client.ts`, `backend/app/main.py`, `backend/app/api/v1/router.py`, `backend/app/db/session.py`.

## 2. Complete Verified Technology Stack

| Technology | Meaning and HMS use | Tanglish | Evidence/status |
|---|---|---|---|
| React | Component-based browser UI library. HMS pages compose reusable controls/cards/tables. | Chinna UI parts-a component-aa pirichu page build pannuvanga. | React 18 dependency; active. |
| TypeScript | JavaScript with compile-time types/interfaces. API responses and component props have declared types. | Code run aagurathukku munnaadi type thappu irukka-nu check pannum. | TypeScript 5; active. |
| Vite | Frontend development server/build tool; reads frontend environment variables. | Frontend dev/build quick-aa nadakka use aagum. | `frontend/vite.config.ts`; active. |
| React Router | Maps browser URL paths to feature pages and redirects. | URL paathu entha screen kaattanum-nu decide pannum. | `frontend/src/App.tsx`; active. |
| TanStack React Query | Fetch/cache/refetch/retry and mutation state for server data. | Server data fetch panni cache pannum; update aana refetch panna help pannum. | `frontend/src/lib/api/hooks.ts`; active. |
| Radix UI / shadcn-style | Accessible low-level dialog/select/tabs primitives wrapped in app UI components. | Keyboard/accessibility support-oda reusable controls. | `frontend/src/components/ui/`; active. |
| Tailwind CSS | Utility classes for layout and styling. | Ready-made CSS class use panni style set pannuvanga. | `frontend/tailwind.config.ts`; active. |
| Recharts | React chart rendering library for metrics/energy/occupancy. | Data-va chart-a kaattum library. | Dashboard and occupancy charts; active. |
| FastAPI | Python HTTP API framework; routes, dependency injection, OpenAPI. | Python-la URL/API define panni request handle pannum framework. | `backend/app/main.py`; active. |
| Pydantic | Request/response data validation and serialization. | API-ku varra data sariyaa irukka validate pannum. | `backend/app/schemas/`; active. |
| SQLAlchemy | Python ORM and SQL expression toolkit. | Python model/query moolama SQL database-oda pesum. | `backend/app/models/`, `backend/app/services/`; active. |
| PostgreSQL | Relational database connected as `hms_db/public` in this environment. | Tables/rows-la HMS data store pannura database. | Read-only connection verified locally. |
| Alembic | Versioned database schema/data migrations. | Database structure/version change-a ordered-aa manage pannum. | `backend/migrations/`; live DB one revision behind source head. |
| pytest | Python test runner. | Automated test run pannura tool. | 19 test modules present; not run here. |

## 3. Frontend Concepts and Their Actual Usage

| Term | Exact meaning | Tanglish | HMS evidence and status |
|---|---|---|---|
| Component | Reusable function that returns UI. | Oru UI piece; pala idathula reuse pannalaam. | `frontend/src/features/`, `frontend/src/components/`; active. |
| Page / route | Screen selected by URL. | URL-ku match aana screen. | `frontend/src/App.tsx`; 11 feature folders, routes registered there. |
| Props | Inputs passed from a parent component to a child. | Parent component child-kku kudukkura values/functions. | `StatusSection`, dialogs, shared components. |
| State | Values held by a component/context and updated over time. | UI current value; change aana render update aagum. | `useState` in forms, filters, tabs. |
| Hook | React function for state/effects or reusable logic. | React behavior-a component-kulla use panna function. | `useState`, `useEffect`, `useMemo`, API hooks. |
| `useEffect` | Runs side effects after render; e.g. restore or subscribe. | Render apram API/event maadhiri side work seyyum. | Auth restore and event listeners. |
| `useMemo` | Caches a derived calculation until dependencies change. | Input maaralana calculation marubadiyum pannaama reuse pannum. | Dashboard and data mapping. |
| Context | Shares app-wide state without passing props through every component. | Auth/theme maadhiri common state ellaa child-kum share pannum. | `AuthContext`, `ThemeContext`. |
| Controlled input | Form value is driven by React state and changed by an event. | Input value React state-la irundhu control aagum. | Login, reservations, employee/config forms. |
| Event handler | Function called on click, input, or submit. | User click/type pannumbodhu run aagura function. | Forms and actions throughout feature pages. |
| Conditional rendering | Displays UI based on state/permissions/query result. | Condition true/false-ku etha maadhiri UI kaattum. | `DataState`, access-gated controls, modal state. |
| Type/interface/generic | TypeScript contracts for data and reusable typed functions. | Data shape enna-nu compiler-ku sollura definition. | `frontend/src/lib/api/types.ts`, API generics. |
| Data mapping | Converts an API response object into fields a component displays. | Backend response-a screen-ku thevaiyana format-ku maathurathu. | `Reservations.tsx`, `Offers.tsx`, `Occupancy.tsx`. |
| React Query query key | Cache identity for a request, including filters. | Endha filter/data-ku cache nu identify pannum key. | `hooks.ts`; keys include params. |
| Mutation | A request that changes server state. | Server data create/update/delete seyyura request. | `mutations.ts`; none executed in audit. |
| Loading/empty/error state | UI state while waiting, with no rows, or after a request failure. | Wait pannumbodhu / data illa / error vandha kaattura state. | `core/components/DataState.tsx`. |
| Client-side pagination | Browser slices data already fetched. | Vantha data-va browser-la page-aa pirikkurathu. | Multiple tables; can be incomplete if only first API page was fetched. |
| Chart series/config | Labels/colors/series specify chart rendering; data may still be dynamic. | Chart eppadi theriyanum-nu config; count/reading API-la irukkalaam. | Dashboard components; metrics are fetched. |

## 4. Backend Concepts and Their Actual Usage

| Term | Exact meaning | Tanglish | HMS evidence and status |
|---|---|---|---|
| Application factory | Function builds and configures the FastAPI app. | App setup ellam oru function-la seyyum. | `backend/app/main.py:create_app`. |
| Router | Groups related endpoint functions and prefixes. | Oru module-oda API routes group. | `backend/app/api/v1/router.py`. |
| Endpoint/route handler | Function invoked for an HTTP method and path. | URL request vandha execute aagura Python function. | `backend/app/api/v1/endpoints/`. |
| Dependency injection | Framework supplies shared dependencies such as DB session/current user. | Framework thevaiyana object-a function-kku automatic-aa kodukkum. | `backend/app/api/deps.py`. |
| Service layer | Business queries and transformations separated from route parsing. | Business logic / database query handle pannura layer. | `backend/app/services/`. |
| ORM model | Python class mapped to database table/columns. | Python class database table-a represent pannum. | `backend/app/models/`; 92 mapped tables match live columns. |
| Schema / DTO | Pydantic request/response contract; DTO means Data Transfer Object. | API-la send/receive aagura data shape. | `backend/app/schemas/`. |
| Serialization | Convert Python objects to response JSON. | Python data-va JSON format-ku maathurathu. | FastAPI/Pydantic response models. |
| Authentication | Identifies the caller. | Yaar request pannuraanga-nu verify pannurathu. | `/auth/login`, `/auth/me`, bearer token. |
| Authorization | Decides what the identified caller may do. | Login user-ku enna permission irukku-nu check pannurathu. | Backend dependencies and role-module permissions. |
| RBAC | Role-Based Access Control: permissions assigned through roles/modules. | Role/module base-la read/write access decide pannurathu. | `role`, `role_module`, `role_module_permission`. |
| Exception handler | Converts exceptions into standard HTTP error responses. | Error-a standard API response-aa maathurathu. | `backend/app/api/errors.py`, `write_errors.py`. |
| Transaction | Groups database writes so they commit/rollback together. | Write set success aana commit; thappu aana rollback. | `backend/app/services/writes.py`. |
| Middleware | Request/response wrapper for cross-cutting behavior. | Ella request-kum nadakkura common processing. | CORS middleware in `backend/app/main.py`. |
| Query aggregation | Database computes count/sum/grouping before response. | Database-ey count/sum calculate pannum. | Energy service; dashboard count endpoints. |
| Seed data | Script inserts setup/reference/demo records. | Initial/reference data database-la populate pannum. | `backend/seeds/`; not the same as frontend fallback. |
| Logging | Records events and diagnostics. | Debug/operation details log file/console-la write pannum. | SQL echo enabled by DEBUG + development config; data redaction needs review. |

## 5. Database Concepts and Their Actual Usage

| Term | Exact meaning | Tanglish | HMS example |
|---|---|---|---|
| Database/schema | Database holds data; schema groups its objects. | Database main storage; schema athukkulla organization. | `hms_db`, `public`. |
| Table/row/column | Table is a structured set; row is one record; column is a field. | Table = data list; row = oru record; column = oru property. | `amenity`, one room row, `name` column. |
| Data type/nullability | Column's accepted type and whether missing value is allowed. | Enna type data, empty-aa irukkalaama-nu define pannum. | Live inventory includes PostgreSQL type and NULL/NOT NULL. |
| Primary key (PK) | Unique identifier for a row. | Oru row-a thaniyaa identify pannura key. | `amenity.id`; lookup tables may use integer keys. |
| Foreign key (FK) | Constraint linking a row to another table's key. | Oru table row innoru table row-oda sambandham. | `room_allocation` links stay and room. |
| One-to-many | One parent relates to many child rows. | Oru parent-kku pala child records. | Stay with room allocations/occupants. |
| Many-to-many | Link table connects multiple rows on each side. | Rendu pakkam pala-pala sambandham; join table use pannum. | `package_feature`, `user_role`. |
| Join | Query combines related tables using keys. | Related tables-a common key moolama serkkurathu. | Occupancy service joins amenity/status/stay relationships. |
| ORM | Object-Relational Mapper maps classes/objects to SQL tables. | Python object-a SQL table-oda connect pannum. | SQLAlchemy models/services. |
| Migration | Ordered database change with upgrade/downgrade. | Schema/data change version-by-version record pannum. | Current DB is at foundation migration; one source child pending. |
| Index | Extra lookup structure intended to speed filters/joins. | Search/filter fast aaga database maintain pannura structure. | Schema index metadata included per table in Appendix A. |
| Constraint | Database-enforced rule such as PK/FK/unique/check. | Database itself enforce pannura validity rule. | Appendix A reports keys and constraint counts. |
| Normalization | Structuring data to reduce duplication and preserve relations. | Duplicate data kammi panna related table split design. | Lookup and association tables in schema. |
| Pagination | Limits a result page and provides total/page metadata. | Result-a chinna pages-aa divide pannurathu. | API page size max 100; frontend must honor `total`. |
| Migration drift | Connected DB revision differs from source migration head. | Code-la irukkura latest DB change live DB-la innum apply aagala. | `0e2687233b59` -> pending `7c4e2b9a1d53`. |

## 6. API and HTTP Concepts and Their Actual Usage

| Term | Exact meaning | Tanglish | HMS example/status |
|---|---|---|---|
| REST API | Resource-oriented HTTP interface. | URL/method moolama data resource access pannum API style. | `/api/v1/rooms`, `/api/v1/stays`. |
| HTTP method | Verb states operation intent. | Request enna seyyudhu-nu method sollum. | GET read, POST create/action, PATCH partial update, PUT replace, DELETE remove. |
| Path parameter | Identifier embedded in URL path. | URL-kulla record ID. | `/stays/{stay_id}`. |
| Query parameter | Filter/page option after `?`. | URL-la filter/page value. | `?page=1&page_size=100`. |
| Request body | JSON data submitted to create/update operation. | Server-kku send pannura JSON payload. | Pydantic-validated write schemas. |
| Response schema | Contract for returned JSON fields/types. | API thiruppi anuppura data shape. | `backend/app/schemas/`, OpenAPI. |
| HTTP status | Standard numeric result of the request. | Request success/error code. | Tested 200, 401; route inventory documents expected responses. |
| 401 vs 403 | 401 means caller is unauthenticated; 403 means authenticated but denied. | 401 login illa; 403 login irukku aana permission illa. | Anonymous facilities request returned 401 in local test. |
| CORS | Browser policy controlling cross-origin requests. | Vera domain-la irukkura frontend API call panna allow rules. | Configured in `backend/app/main.py`. |
| OpenAPI | Machine-readable route/schema document. | API routes and data contract-oda generated specification. | Used to enumerate 161 registered operations. |
| JSON | Text representation for API objects/arrays. | API data exchange panna common text format. | Frontend `apiClient` and FastAPI responses. |
| API error envelope | Consistent structured failure representation. | Error details standard shape-la varum. | `client.ts`, backend exception handlers. |
| API version prefix | Version namespace for evolving routes. | API version path; changes safe-aa manage panna. | `/api/v1`. |

## 7. Data Fetching and State Management

`apiClient` builds requests and handles bearer tokens/errors. Endpoint modules bind resource paths to TypeScript response types. Hooks wrap requests in React Query, which stores cached results by query key and can refetch on invalidation. Components map hook data to UI. Mutations submit state changes and invalidate relevant cache keys. Loading/error/empty states are rendered separately from business data.

**Tanglish:** Component direct-aa raw HTTP logic pannama endpoint + hook use pannum. Hook data fetch/cache pannum. Response state-la vandha component map panni table/card-la kaattum. Save/update mudinja cache invalidate aagi fresh data varum.

Important caveat: if a screen fetches one page of 100 rows and then paginates only that array, it does not have all database rows. RoomView has a confirmed count case; other pages require dataset-size tests.

## 8. Authentication, Authorization, and RBAC

Login sends credentials to the backend; successful response token is stored under a localStorage key. AuthContext revalidates the current user from `/auth/me`. The UI uses permission-derived `canRead`/`canWrite` gates. The backend also checks current-user/module permissions; hiding a button in React is not the only security layer.

**Tanglish:** Login token kudukkum; app token vechchu current user details edukkum. Role/module permission base-la UI access control pannum; backend-um request time-la permission check pannanum.

Evidence: `frontend/src/core/contexts/AuthContext.tsx`, `frontend/src/lib/api/client.ts`, `backend/app/api/deps.py`, `backend/app/services/auth.py`. Live RBAC behavior per role was not tested.

## 9. Database Table and Column Reference

The **complete connected database table/column reference** is Appendix A of `HMS_COMPLETE_DATA_FLOW_AUDIT.md`. It is generated from the live read-only schema and includes types, nullability, PK/FK, per-table count and constraint/index counts. The connected DB contains 93 public tables, 92 of which are ORM-mapped; no mapped column-name mismatch was detected.

The principal domains are:

- Facility/room hierarchy: `organisation`, `facility`, `property`, `property_chain`, `amenity`, status/condition lookups.
- People/access: `app_user`, `department`, `job_function`, `role`, module/permission association tables.
- Stay lifecycle: `stay`, `stay_user`, `stay_package`, `room_allocation`, `user_document`, `invoice`.
- Operations: service catalogue/requests, maintenance requests, job orders.
- Device/telemetry: device inventory/config, device stats, energy, alerts/incidents, MQTT/command/support tables.
- Marketing: promo codes, events, occasions.
- System: activity, notification, scheduler, attachment, import and migration tables.

Country master data exists and has 239 rows, but a country API/frontend hook was not found. A complete field-by-field business definition for every column is not assumed where neither schema comments nor an active screen establishes semantics.

## 10. API Request and Response Reference

The complete route list and OpenAPI operation contracts (method/path, operation ID, tags, parameter names, JSON request schema, response schema/statuses and security declaration) are in **Appendix B** of the data-flow audit. Total operations: 161. The frontend wrapper/client files are `frontend/src/lib/api/endpoints.ts`, `writes.ts`, and `reports.ts`.

OpenAPI documents route contracts; it does not prove a request succeeds at runtime. Only health/version/database-health and an unauthorized facility-list request were exercised locally. Authenticated payload shape, business errors, and writes remain unverified.

## 11. HMS Business Logic and Status Definitions

- Occupancy status vocabulary: Available, Occupied, Allotted, Unavailable. `Allotted` is a pending room allocation and is not synonymous with in-house Occupied.
- Backend occupancy service derives status based on in-house stay/allocation, amenity status, and active blocking conditions. “Unknown” is a frontend fallback bucket, not one of the four authoritative lookup statuses.
- Room conditions are a separate concept from room status. Conditions include examples such as Dirty, Low battery, Under maintenance, Sanitation, and Ready for occupant. Frontend presentation relabels selected condition names; it does not make them occupancy status.
- Service request status names come from `service_status`; current DB is one migration behind source. The pending migration renames id 3 from “Partially completed” to “In Progress”.
- Device health/status enums, alert severity and role types have backend schema contracts. UI colors/order/labels are frontend presentation mappings.
- Dashboard KPI counts are obtained from count endpoints; energy is aggregated over stored readings; energy unit is resolved from the device parameter registry when available.

## 12. Complete Request Lifecycle Examples

### Occupancy Statistics

1. `OccupancyStatisticsChart` calls status and count hooks.
2. Frontend hooks use `/amenity-statuses` and count requests against `/occupancy`.
3. Backend endpoint calls occupancy service; the service selects amenity/status and related stay/condition data and the database executes the query.
4. Count response totals become chart slice values; status response names become labels.
5. Component assigns a presentation color and renders the donut/legend.
6. This source flow is verified. An authenticated request payload/visual count comparison was not run. Do not use RoomView's separate capped list calculation as evidence that the donut uses fixed counts.

### Reservation and check-in

1. `Reservations.tsx` initializes controlled form state.
2. Submit creates a guest through `/users`, then a stay through `/stays`; optional room allocation follows the stay data contract.
3. FastAPI validates body schemas and calls write services using a DB session.
4. Guest/stay/allocation data is returned and query caches/lists refresh through mutation hooks.
5. Source integrations are verified; writes were not executed. Nationality is currently not passed, and the phone prefix is composed from a hardcoded list.

### Service request / maintenance

1. Tracking/planning pages fetch service/status/category/department/staff/room/maintenance options through React Query hooks.
2. User submits create/update/cancel mutation.
3. FastAPI validates Pydantic schema and invokes service/write functions.
4. SQLAlchemy persists to service/maintenance tables; mutation invalidates query data.
5. Route registration and code paths are verified; no write or authenticated read was runtime tested.

### Dashboard energy

1. Energy chart computes a date window and calls `/energy-stats/summary`.
2. Backend groups `energy_stat` records and aggregates SUM and COUNT; it resolves unit from `device_param`.
3. Frontend transforms buckets for axis labels and calculates average as sum/count, then chart renders returned values.
4. Source/database relation is verified; authenticated payload and chart rendering were not runtime-tested.

## 13. Hardcoding, Mock Data, and Fallback Concepts

- A **hardcoded operational value** is a business-specific value embedded in code where a real record should come from a data source. Example: Facility Management's fixed editor facility details.
- A **static UI label** is interface copy such as “Save” or “Occupancy Statistics”; static does not mean incorrect.
- A **configuration constant** is a fixed choice/rule such as chart color, range options, or page size. It can be valid if the product requirements define it.
- **Mock/demo data** resembles real operational records but is not a live record. The fixed Facility Management edit dialog is demo-like; current main list rows are API-derived.
- A **fallback** handles absent data. It is risky when it changes meaning, e.g. missing room status -> “Available”.
- **Seed data** is inserted by a setup script into a database; it is separate from frontend mock data and may be present in development/test databases.

## 14. Validation, Error Handling, and Debugging

Frontend API errors are normalized by `ApiError`; React Query retry avoids retrying some client-side statuses. Shared `DataState` renders loading/error/empty conditions. Backend Pydantic schemas validate body/query values; FastAPI returns HTTP errors; application handlers normalize exceptions. DB session dependency closes each request session; write helper commits or rolls back.

**Tanglish:** User input frontend-la form checks pass pannum; backend schema marubadiyum validate pannum. Query/database failure success maadhiri nadikkaama error response-aaga varanum. Debug log-la sensitive values varaama settings safe-aa irukkanum.

Debug SQL echo is enabled when `DEBUG` and development mode are both true; local endpoint testing emitted SQL logs. Confirm deployed settings and redact bind values where needed.

## 15. Testing, Configuration, Build, and Deployment

- Frontend scripts: `dev`, `build`, `build:dev`, `lint`, `preview` in `frontend/package.json`.
- Backend requirements: `backend/requirements.txt`; pytest files under `backend/tests/`.
- Config: frontend `VITE_API_BASE_URL`, platform version/license environment; backend settings in `backend/app/core/config.py` and `.env` (secrets intentionally omitted).
- CORS origins are configurable in backend settings.
- Alembic migration head in source is one revision ahead of the connected DB; this audit did not run migrations.
- Test/build/lint commands were not run. Four safe GET calls only were made through an in-process TestClient.

## 16. Unused, Missing, Partially Implemented, and Unverified Concepts

| Area | Status |
|---|---|
| Country reference data | Table and seed data verified; no API/client route found. Reservation nationality selection is not integrated. |
| Device/IoT support tables | Tables/models exist; several command, MQTT, firmware, lock/access and scheduler concerns have no current UI route evidenced. May be consumed externally or by workers; not established unused. |
| Facility edit dialogs | Partially implemented; fixed example fields and inert close-only submit behavior. |
| Power/Energy standalone screens | Not currently registered as pages; routes redirect into Occupancy room details, where telemetry is shown. |
| Service-status migration | Source-defined but pending in connected DB. |
| Authenticated endpoint responses | Not verified because no credentials were used. |
| External integrations/background tasks | Not verified at runtime. |
| Localization | Static UI strings present; no localization workflow established by inspected code. |
| Caching beyond React Query | No separate frontend cache service established; backend caching not established in audit. |
| Deployment environment | Production host, proxy, secrets manager, external rate limiting and production DB not verified. |

## 17. Technical Problems and Their Root Causes

1. **Stale migration head:** source migration added after the DB revision was not applied to connected DB; approved migration deployment is needed.
2. **UI record/config split:** Facility Management still mixes backend-driven main tables with old literal dialog content.
3. **Wrong aggregation boundary:** RoomView calculates a total from a single paginated API result instead of using total/grouped backend query.
4. **Form/API contract mismatch:** nationality UI choices are not country IDs and never enter request body.
5. **Ambiguous absence behavior:** missing occupancy status maps to Available rather than explicit Unknown.
6. **Observability exposure risk:** unauthenticated DB-health route returns infrastructure details; SQL echo may emit bind values in development.

## 18. Frequently Asked Technical Questions

**Is the UI fully hardcoded?** No. Many operational lists, counts, charts, and configuration options are loaded from APIs. Some facility-dialog content, form options, defaults, status mapping, labels, and a few fallback/calculation behaviors remain fixed.

**Does every endpoint run successfully because it appears in OpenAPI?** No. Route registration is verified; only four safe GET requests were tested. Three returned 200 and the protected facility list returned 401 without authentication.

**Are all 93 tables displayed in the UI?** No. Tables support API resources, joins, operational integrations, and system behavior. Table presence does not mean frontend display. Appendix A labels observed/inferred integration conservatively.

**Is the connected database schema current?** The 92 application model column sets match, but migration revision is behind source by one migration.

**Are seeded records proof of production data?** No. Row counts are real for the connected local database at audit time; record provenance/deployment identity is not established.

**Tanglish:** “UI-la ella data-um hardcode-aa?” Illai. Neraya counts, room/stay/service/device data API-la irundhu varudhu. Aana sila Facility details, dropdown options, defaults, fallback logic innum fixed-aa irukku.

---

For exact live table/column detail and all registered API operations, use Appendices A and B in `HMS_COMPLETE_DATA_FLOW_AUDIT.md`.
