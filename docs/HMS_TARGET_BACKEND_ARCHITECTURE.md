# HMS Target Backend Architecture: Modular Monolith to Dual-Service Evolution
**Document Version:** 1.0.0  
**Date:** 2026-10-26  
**Auditor:** Senior Backend Architect & Microservices Integration Specialist  
**Target Architecture:** HMS OSS/BSS v3 Integrated Architecture  

---

## 1. Architecture Evaluation & Evolution Strategy

### 1.1 Why a Two-Phase Evolution is Required
Splitting an existing, functioning codebase directly into distributed microservices on day one introduces distributed transactions, network latency, deployment complexity, and debugging overhead without solving the immediate business requirements.

The forensic audit confirms:
1. HMS currently operates as a **modular monolith** in FastAPI with 94 PostgreSQL tables.
2. The team has active frontend features communicating through `/api/v1` via a single Vite dev proxy target (`http://127.0.0.1:8000`).
3. MySQL 8.0 is running on the host machine (port 3307), but no BSS database has been initialized.

**Recommendation:**  
Execute a structured **Two-Phase Evolution Strategy**:
- **Phase 1 (Immediate / Pragmatic): Modular Monolith with Dual-Engine Connections.**  
  Keep a unified FastAPI process, but establish strict internal boundaries: dual SQLAlchemy engines (`oss_engine` connecting to PostgreSQL `hms_db`, and `bss_engine` connecting to MySQL `hms_bss`), dedicated repository layers, and a domain bridge layer.
- **Phase 2 (Future / Scaling): Distributed Dual Microservices.**  
  Extract the BSS domain into a dedicated deployable service (`hms-bss-service`) when transaction volume, team autonomy, or independent deployment cadence demands it.

---

## 2. Phase 1 Architecture: Dual-Database Modular Monolith

In Phase 1, the backend runs as a single FastAPI application with strict boundary enforcement:

```
                            +-----------------------------+
                            |        FASTAPI APP          |
                            |       (backend/app)         |
                            +-----------------------------+
                                           |
               +---------------------------+---------------------------+
               |                                                       |
               v                                                       v
+-----------------------------+                         +-----------------------------+
|        OSS DOMAIN           |                         |         BSS DOMAIN          |
|  (app/models/oss, api/oss)  |                         |  (app/models/bss, api/bss)  |
+-----------------------------+                         +-----------------------------+
| Repositories:               |                         | Repositories:               |
| - FacilityRepo              |                         | - ReservationRepo           |
| - AmenityRepo               |                         | - RoomRepo                  |
| - DeviceRepo                |                         | - FolioRepo                 |
| - TelemetryRepo             |                         | - GuestRepo                 |
| - AccessKeyRepo             |                         | - HousekeepingRepo          |
| - IdentityRepo (AppUser)    |                         | - MaintenanceRepo           |
+-----------------------------+                         +-----------------------------+
               |                                                       |
               v                                                       v
+-----------------------------+                         +-----------------------------+
|      app.db.oss_session     |                         |      app.db.bss_session     |
|   (SQLAlchemy PostgreSQL)   |                         |     (SQLAlchemy MySQL 8.0)  |
+-----------------------------+                         +-----------------------------+
               |                                                       |
               v                                                       v
+-----------------------------+                         +-----------------------------+
|    POSTGRESQL 18 (hms_db)   |                         |       MYSQL 8.0 (hms_bss)   |
|   Port: 5432 / Timescale    |                         |           Port: 3307        |
+-----------------------------+                         +-----------------------------+
```

### 2.1 Backend Directory Reorganization (Non-Destructive)
```
backend/app/
├── core/
│   ├── config.py                 # Multi-DB settings (PostgreSQL + MySQL)
│   ├── security.py               # Unified JWT & bcrypt auth
│   └── events.py                 # Startup/shutdown lifecycle hooks
├── db/
│   ├── session.py                # Backward-compatible engine router
│   ├── oss_session.py            # PostgreSQL engine & sessionmaker (hms_db)
│   └── bss_session.py            # MySQL engine & sessionmaker (hms_bss)
├── models/
│   ├── oss/                      # Existing 94 models mapped to PostgreSQL
│   │   ├── facility.py, amenity.py, device.py, people.py, stay.py, ...
│   └── bss/                      # 54 new BSS entities mapped to MySQL
│       ├── properties.py, rooms.py, reservations.py, stays.py, folios.py, guests.py, ...
├── repositories/
│   ├── oss/                      # Isolated queries against PostgreSQL
│   └── bss/                      # Isolated queries against MySQL
├── services/
│   ├── bridge/                   # Cross-system orchestration layer
│   │   ├── room_sync_service.py      # Binds bss_rooms to oss_amenity
│   │   ├── checkin_service.py        # Coordinates bss_stays with oss_stay & lock PIN
│   │   ├── alert_workorder_bridge.py # Dispatches bss_maintenance from oss_device_alert
│   │   └── health_snapshot_sync.py   # Updates bss_room_device_registry snapshot
│   ├── oss/                      # Pure OSS business logic
│   └── bss/                      # Pure BSS business logic
└── api/
    └── v1/
        ├── endpoints/            # Retained legacy endpoints (preserved for UI)
        ├── oss/                  # Formal OSS platform endpoints
        └── bss/                  # Formal BSS commercial endpoints
```

---

## 3. Database Connection & Session Management

### 3.1 Pydantic Settings Update (`backend/app/core/config.py`)
```python
class Settings(BaseSettings):
    # --- PostgreSQL (OSS) ---
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hms_db"
    POSTGRES_SCHEMA: str = "public"
    
    # --- MySQL 8.0 (BSS) ---
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3307
    MYSQL_DB: str = "hms_bss"
    
    @property
    def oss_sqlalchemy_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def bss_sqlalchemy_url(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
```

### 3.2 Multi-Database Dependency Injection (`backend/app/api/deps.py`)
```python
def get_oss_db() -> Generator[Session, None, None]:
    """Yields a database session bound strictly to PostgreSQL (OSS)."""
    db = OssSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_bss_db() -> Generator[Session, None, None]:
    """Yields a database session bound strictly to MySQL 8.0 (BSS)."""
    db = BssSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 4. Bridge Layer Design & Cross-System Workflows

The bridge layer (`app/services/bridge/`) ensures that no SQL joins occur across databases. Cross-system operations are orchestrated via application transactions.

### 4.1 Workflow 1: Check-in & Digital Key Issuance
```
[Frontend Client]
       |
       | 1. POST /api/v1/bss/stays/{stay_id}/check-in
       v
[BSS Checkin Service]
       |
       | 2. Verify reservation, payment deposit, room readiness in MySQL
       | 3. Set bss_stays.status = 'CheckedIn', actual_check_in = NOW()
       |
       +-----> [Bridge: checkin_service.py]
                   |
                   | 4. Fetch room assignment: bss_rooms.oss_asset_id
                   | 5. Call OSS internal service:
                   |    - Create oss_stay context record (bss_stay_id = stay.id)
                   |    - Generate smart lock keypad PIN & mobile credential in oss_access_key
                   |    - Issue MQTT unlock policy to device gateway
                   v
              [OSS Service]
                   |
                   | 6. Return oss_access_key details
                   v
[BSS Checkin Service]
       |
       | 7. Store pass in bss_digital_keys
       | 8. Commit BSS transaction
       v
[200 OK + Digital Key Details to Frontend]
```

### 4.2 Workflow 2: Checkout to Housekeeping Automation
```
[Frontend / Front Desk]
       |
       | 1. POST /api/v1/bss/stays/{stay_id}/check-out
       v
[BSS Service]
       | 2. Finalize folios, verify zero balance in bss_folios
       | 3. Update bss_stays.actual_check_out = NOW(), status = 'CheckedOut'
       | 4. Update bss_rooms.status = 'Dirty'
       | 5. Create bss_housekeeping_tasks (assigned_to = supervisor_user_id)
       | 6. Audit in bss_automation_events (event = 'checkout_cleaning_dispatched')
       |
       +-----> [Bridge]
                   | 7. Revoke credentials in oss_access_key (status = Expired)
                   | 8. Dispatch HVAC power-save command via oss_device_command
                   v
              [OSS Service (PostgreSQL + MQTT)]
```

### 4.3 Workflow 3: Telemetry Health Snapshot Sync (Rule 2)
```
[OSS Background Task / Cron]
       |
       | 1. Read latest device health from oss_device_health_stat (PostgreSQL)
       v
[Health Snapshot Sync Worker]
       |
       | 2. Map oss_device_id to bss_room_device_registry
       | 3. Batch UPDATE bss_room_device_registry
       |    SET last_known_health_status = 'online', last_checked_at = NOW()
       v
[MySQL hms_bss]
       |
       | (HMS Staff Dashboard reads room cards directly from MySQL without hitting PostgreSQL)
```

---

## 5. Security, Authentication & Module-Aware RBAC

### 5.1 Single Identity Architecture (Rule 1)
- Authentication is handled centrally by `app.api.v1.endpoints.auth`.
- Authenticates credentials against `app_user` (`oss_app_user`) using bcrypt.
- JWT Payload:
  ```json
  {
    "sub": "user_uid_or_username",
    "user_id": "b789e023-4412-4a0b-9304-d4b97ea3c19e",
    "is_staff": 1,
    "facility_ids": ["c1234567-89ab-cdef-0123-456789abcdef"],
    "roles": ["Administrator", "FrontDesk"],
    "modules": [
      {"module_code": "bookings", "access": "read_write"},
      {"module_code": "occupancy", "access": "read_write"},
      {"module_code": "facility_mgmt", "access": "read_only"}
    ],
    "exp": 1793084400
  }
  ```

### 5.2 Module-Aware RBAC Enforcement (Rule 4)
- Current HMS frontend routes are protected by checking permissions in `role_module_permission`.
- In v3, roles are associated with `module_id`.
- HMS hotel staff roles (e.g. `FrontDesk`, `Housekeeper`) have access only to hotel commercial modules (`bookings`, `rooms`, `guests`, `billing`).
- FleetExplorer hardware management modules (`telemetry_config`, `mqtt_brokers`, `device_firmware`) require administrative infrastructure roles.

---

## 6. Phase 2 Target Architecture: Distributed Microservices

When operational scale dictates independent deployability, the codebase splits into two autonomous containers:

| Service | Technology | Primary Database | Exposed Ports | Responsibilities |
|---|---|---|---|---|
| **HMS-OSS Platform Service** | Python / FastAPI | PostgreSQL 18 + Timescale | `8001` (Internal) | Facilities, Devices, Gateways, Telemetry, Access Control, Global Identity |
| **HMS-BSS Commercial Service**| Python / FastAPI | MySQL 8.0 | `8002` (Internal) | Reservations, Rooms, Rates, Guests, Folios, Payments, Housekeeping |
| **HMS API Gateway / BFF** | Traefik / NGINX / Envoy | Redis (Cache/Tokens) | `8000` (Public API) | TLS termination, JWT validation, rate limiting, path routing (`/api/v1/oss/*`, `/api/v1/bss/*`) |
| **HMS Staff UI** | React 18 / Vite | Browser Client | `8080` (Web) | Single pane of glass for hotel front desk, managers, and housekeeping staff |

### Service-to-Service Communication:
- **Synchronous:** mTLS REST APIs over Docker/Kubernetes internal network with strict circuit-breaker timeouts (2.0s timeout).
- **Asynchronous:** Outbox table pattern in MySQL/PostgreSQL polled by a lightweight worker or Redis stream to guarantee at-least-once delivery of check-in, check-out, and alert events.
