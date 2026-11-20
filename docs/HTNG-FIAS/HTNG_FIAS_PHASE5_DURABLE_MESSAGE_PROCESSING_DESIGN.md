# HMS — HTNG & FIAS Phase 5: Durable Message Processing Foundation & Architecture Design

**Document Reference:** `ACX-Platform/docs/HTNG_FIAS_PHASE5_DURABLE_MESSAGE_PROCESSING_DESIGN.md`  
**Date:** November 18, 2026  
**Auditor / Engineer:** Senior Integration Architect & Senior Backend Engineer  
**Repository:** `ACX-Platform`  
**Branch:** `feature/htng&fias-integrate`  
**Git HEAD:** `754bd8ac07afa01d4f8c246916bc0955e410e0bd`  
**Status:** Architecture Ratified, Safe Core Implemented & Tested (67/67 Tests Passing)

---

## Executive Summary

Phase 5 addresses the architectural challenge of transforming transient, in-memory integration processing into a **durable, auditable, crash-resilient message processing foundation**. 

In previous phases, message deduplication relied on `InMemoryIdempotencyStore`, which was susceptible to process restarts, unrecoverable worker crashes, and lacked persistent audit trails. Phase 5 establishes the formal **Message Lifecycle State Machine**, **Candidate Database Schemas** (`integration_message_log`, `integration_idempotency_keys`, `integration_outbox`), **Worker Claim & Lock Policies**, and the **External TCP ACK Failure Window Design**.

In strict adherence to project governance boundaries:
- **Zero database migrations** were executed (awaiting formal DBA review).
- **Zero production message tables** were created.
- **Zero external broker dependencies** (Redis/RabbitMQ) were added.
- **All lifecycle transition logic, repository contracts, worker coordination, and idempotency guarantees** were implemented in Python and verified via an in-memory test harness, expanding the test suite to **67 passing tests** (67 passed, 0 failed, 0 skipped in **1.10s**).

---

## 1. Repository & Runtime Verification

### 1.1 Repository State
- **Branch:** `feature/htng&fias-integrate`
- **HEAD Commit:** `754bd8ac07afa01d4f8c246916bc0955e410e0bd`
- **Active Database Engine:** Verified in `backend/app/core/config.py`:
  ```python
  DB_ENGINE: str = "mysql"  # HMS database of record
  ```
  MySQL is the configured default engine (`pymysql` driver), with PostgreSQL compatibility supported via SQLAlchemy URL conventions.
- **Existing Migration Structure:** Alembic migrations are located in `backend/migrations/versions/`:
  - `0e2687233b59_phase1_7_hms_92_table_foundation.py`
  - `7c4e2b9a1d53_rename_service_status_in_progress.py`
  - `a3f1c8e2d904_room_device_map.py`
- **Database Availability in Workspace:** Local MySQL (port 3306) and PostgreSQL (port 5432) remain offline on this development host. The integration test suite is intentionally designed with zero socket/database coupling.

---

## 2. Durable Message Lifecycle State Machine

The durable message processing pipeline enforces eight explicit, deterministic lifecycle states:

```
                          [ External Wire Message ]
                                     │
                                     ▼
                               +------------+
                               |  RECEIVED  |
                               +------------+
                                     │
                 ┌───────────────────┼────────────────────┐
                 │ (Duplicate Hash)  │ (Syntax/Auth Fail) │ (Valid/Claimed)
                 ▼                   ▼                    ▼
          +-------------+     +------------+      +---------------+
          |  DUPLICATE  |     |   FAILED   |      |   VALIDATED   |
          +-------------+     +------------+      +---------------+
             [Terminal]          [Terminal]               │
                                                          ▼
                                                  +---------------+
                                 ┌───────────────►|  PROCESSING   |
                                 │                +---------------+
                                 │                        │
                 ┌───────────────┴───────────────┐        │ (Business Success)
                 │ (Transient Error & Retries)   │        ▼
                 ▼                               │ +-------------+
        +------------------+                     │ |  PROCESSED  |
        |  RETRY_PENDING   |                     │ +-------------+
        +------------------+                     │    [Terminal]
                 │                               │
                 │ (Retries Exhausted)           ▼
                 └───────────────────────►+-------------+
                                          | DEAD_LETTER |
                                          +-------------+
                                             [Terminal]
```

### 2.1 State Definitions

| State | Lifecycle Stage | Description |
|:------|:----------------|:------------|
| **`RECEIVED`** | Ingestion | Raw wire payload (TCP or HTTP) accepted by gateway; message ID assigned, payload hashed, and audit log persisted. |
| **`VALIDATED`** | Ingress Audit | Message parsed into canonical envelope; property tenant scope validated (`HF-19`); schema verified. |
| **`PROCESSING`** | Active Claim | Message claimed by worker or synchronous dispatcher; locked with `worker_id` and `locked_at` lease timestamp. |
| **`PROCESSED`** | Terminal Success | Business transaction committed to HMS domain database; transactional outbox records enqueued; terminal. |
| **`DUPLICATE`** | Terminal Bypass | Message previously processed with identical SHA-256 payload digest; duplicate lease blocked; returned success ACK without re-running business logic. |
| **`RETRY_PENDING`** | Transient Failure | Reversible error occurred (e.g. database lock timeout, network glitch); eligible for delayed worker claim. |
| **`FAILED`** | Terminal Failure | Irrecoverable non-transient error (e.g. malformed XML/pipe syntax, unauthorized property, unknown account); terminal. |
| **`DEAD_LETTER`** | Terminal Quarantine | Message failed repeatedly and exceeded `max_retries` (default: 3); quarantined for operator review; terminal. |

### 2.2 Transition Rules & Invariants
- **Strict Monotonic Progression:** States move strictly forward. Skips (e.g. `RECEIVED` → `PROCESSED`) are prohibited and raise `InvalidLifecycleTransitionError`.
- **Terminal State Lock:** Once a message reaches `PROCESSED`, `DUPLICATE`, `FAILED`, or `DEAD_LETTER`, no automated worker can alter its state.
- **Operator Redrive Boundary:** Reprocessing a quarantined `DEAD_LETTER` message requires explicit administrator override to reset its state back to `RETRY_PENDING` or `RECEIVED`.

---

## 3. Database Ownership & Candidate Schema Design

To ensure long-term auditability, multi-tenant property isolation, and high-throughput locking, three candidate database tables are designed.

### A. Candidate Table: `integration_message_log`

Tracks the historical audit trail and execution state of every integration message entering or leaving HMS.

```sql
CREATE TABLE integration_message_log (
    message_id VARCHAR(36) NOT NULL PRIMARY KEY,            -- UUID v4
    external_message_id VARCHAR(128) NULL,                  -- External vendor ID (e.g. FIAS seq or HTNG msg ID)
    protocol VARCHAR(32) NOT NULL,                          -- 'FIAS', 'HTNG', 'POS', 'PBX'
    facility_id VARCHAR(64) NOT NULL,                       -- Multi-tenant property scope
    event_type VARCHAR(64) NOT NULL,                        -- e.g. 'GI', 'GO', 'RE', 'OTA_HotelResNotif'
    direction VARCHAR(16) NOT NULL DEFAULT 'INBOUND',       -- 'INBOUND' or 'OUTBOUND'
    correlation_id VARCHAR(64) NOT NULL,                    -- End-to-end tracing correlation ID
    payload_hash VARCHAR(64) NOT NULL,                      -- SHA-256 hex digest of wire payload
    status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',         -- MessageLifecycleState
    retry_count INT NOT NULL DEFAULT 0,                     -- Current retry count
    max_retries INT NOT NULL DEFAULT 3,                     -- Maximum allowed retry attempts
    locked_by VARCHAR(64) NULL,                             -- Worker ID holding claim
    locked_at DATETIME NULL,                                -- Timestamp when lease was acquired
    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- Ingestion timestamp
    processed_at DATETIME NULL,                             -- Completion timestamp
    next_retry_at DATETIME NULL,                            -- Scheduled retry execution time
    last_error_code VARCHAR(64) NULL,                       -- Safe structured error code
    last_error_message VARCHAR(512) NULL,                   -- Sanitized, non-PII error description
    metadata_json JSON NULL,                                -- Non-sensitive routing parameters

    -- Indexes & Constraints
    INDEX ix_iml_facility_status (facility_id, status),
    INDEX ix_iml_claimable (status, next_retry_at, locked_at),
    INDEX ix_iml_correlation_id (correlation_id),
    INDEX ix_iml_received_at (received_at),
    UNIQUE INDEX uq_iml_facility_external (facility_id, external_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### B. Candidate Table: `integration_idempotency_keys`

Provides durable cluster-wide deduplication leases across multiple API and worker nodes, surviving application restarts.

```sql
CREATE TABLE integration_idempotency_keys (
    facility_id VARCHAR(64) NOT NULL,                       -- Multi-tenant property scope
    idempotency_key VARCHAR(128) NOT NULL,                  -- Vendor or canonical idempotency key
    payload_hash VARCHAR(64) NOT NULL,                      -- SHA-256 digest to verify payload integrity
    message_id VARCHAR(36) NOT NULL,                        -- Reference to integration_message_log
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,                           -- TTL expiration timestamp

    -- Primary composite key enforces property-level isolation
    PRIMARY KEY (facility_id, idempotency_key),
    INDEX ix_iik_expires_at (expires_at),
    CONSTRAINT fk_iik_message_id FOREIGN KEY (message_id) 
        REFERENCES integration_message_log (message_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### C. Candidate Table: `integration_outbox`

Enables the Transactional Outbox Pattern to guarantee that outbound integration dispatches are atomically committed alongside internal HMS domain changes.

```sql
CREATE TABLE integration_outbox (
    outbox_id VARCHAR(36) NOT NULL PRIMARY KEY,             -- UUID v4
    event_type VARCHAR(64) NOT NULL,                        -- e.g. 'STAY_CHECKED_IN', 'ROOM_STATUS_CHANGED'
    facility_id VARCHAR(64) NOT NULL,                       -- Target property
    aggregate_id VARCHAR(64) NOT NULL,                      -- HMS Domain entity ID (e.g. stay_id)
    payload JSON NOT NULL,                                  -- Sanitized, masked domain payload
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',          -- 'PENDING', 'DISPATCHED', 'FAILED', 'ABANDONED'
    retry_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    next_attempt_at DATETIME NULL,
    dispatched_at DATETIME NULL,
    error_detail VARCHAR(512) NULL,

    INDEX ix_io_status_attempt (status, next_attempt_at),
    INDEX ix_io_facility_aggregate (facility_id, aggregate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2.3 Retention & PII Considerations
- **PII / PCI Data Protection:** Payloads in `integration_message_log` and `integration_outbox` are scrubbed of credit card numbers, CVVs, passwords, and tokens before persistence. Raw guest identification is represented by SHA-256 `payload_hash` and canonical IDs.
- **Partitioning & Retention:** High-volume hotel properties generate thousands of equipment/PBX records daily. `integration_message_log` must be partitioned by month (`received_at`), with processed records archived to cold storage after 90 days.

---

## 4. Transaction Boundaries & The External TCP ACK Failure Window

A fundamental flaw in distributed system integration is the assumption that a relational database transaction can atomically commit an external TCP acknowledgement.

### 4.1 The Step-by-Step Distributed Protocol Flow

```
External PMS                   HMS Integration Gateway              HMS MySQL Database
    │                                    │                                  │
    │ 1. TCP Send Record ("GI|RN101...") │                                  │
    ├───────────────────────────────────►│                                  │
    │                                    │ 2. Insert integration_message_log│
    │                                    │    and acquire idempotency lease │
    │                                    ├─────────────────────────────────►│
    │                                    │    (Status: RECEIVED)            │
    │                                    │◄─────────────────────────────────┤
    │                                    │                                  │
    │                                    │ 3. Execute Domain Transaction:   │
    │                                    │    - Insert Stay & RoomAllocation│
    │                                    │    - Enqueue integration_outbox  │
    │                                    │    - Update message -> PROCESSED │
    │                                    ├─────────────────────────────────►│
    │                                    │ 4. DB COMMIT SUCCEEDS           │
    │                                    │◄─────────────────────────────────┤
    │                                    │                                  │
    │                                    │=== [THE ACK FAILURE WINDOW] =====│
    │                                    │ (Socket reset / network timeout) │
    │ 5. TCP ACK (0x06) FAILS TO ARRIVE  │   (PMS never receives ACK!)      │
    │ - - - - - - - - - - - - - - - - - ✕│                                  │
    │                                                                       │
    │ 6. PMS Timeout expires (10s) -> PMS RE-SENDS SAME RECORD:             │
    │    TCP Send Record ("GI|RN101...")                                    │
    ├───────────────────────────────────►│                                  │
    │                                    │ 7. Query idempotency lease:      │
    │                                    ├─────────────────────────────────►│
    │                                    │    Found PROCESSED record with   │
    │                                    │    identical payload_hash!       │
    │                                    │◄─────────────────────────────────┤
    │                                    │                                  │
    │ 8. RETURN IMMEDIATE TCP ACK (0x06) │ (DO NOT RE-RUN CHECK-IN!)        │
    │◄───────────────────────────────────┤ (Status logged as DUPLICATE)     │
```

### 4.2 Failure Window Analysis & Guarantees
- **At-Least-Once Delivery:** The external transport guarantees at-least-once delivery; messages may arrive 1, 2, or more times.
- **Idempotent Execution:** When a duplicate message arrives during step 6, `InMemoryDurableMessageRepository.acquire()` identifies that the message has already been processed with the identical SHA-256 digest.
- **Zero Double-Execution:** The stay check-in transaction is **not** executed again. The gateway immediately formats the protocol acknowledgement (e.g. `ACK` byte `0x06`), safely resolving the external sender's timeout.
- **Payload Tampering Detection:** If the external PMS attempts to re-use an existing message identifier with altered guest/room data, the system detects a `payload_hash` mismatch and raises `IdempotencyConflictError`, rejecting the corrupted request.

---

## 5. Worker & Recovery Architecture

### 5.1 Concurrency & Worker Claiming Model
To process messages across distributed worker nodes without duplication:
1. **Atomic Batch Claiming:** Workers query the database using optimistic lock timestamps or pessimistic row locks:
   ```sql
   SELECT message_id FROM integration_message_log
   WHERE status IN ('RECEIVED', 'VALIDATED', 'RETRY_PENDING')
     AND (next_retry_at IS NULL OR next_retry_at <= NOW())
     AND (locked_at IS NULL OR locked_at < DATE_SUB(NOW(), INTERVAL 300 SECOND))
   ORDER BY received_at ASC
   LIMIT 10
   FOR UPDATE SKIP LOCKED;
   ```
2. **Lease Expiration & Crash Recovery:** If worker node A crashes mid-execution, its lock expires after 300 seconds (`WorkerClaimPolicy.lock_timeout_seconds`). Worker node B automatically reclaims the message and resumes processing.
3. **Dead-Letter Quarantine:** If a message repeatedly causes worker crashes or database lock timeouts, `DeadLetterPolicy` transitions it to `DEAD_LETTER` after 3 failed attempts, preventing poison-pill messages from blocking the processing queue.

### 5.2 Process Supervision Recommendation for Python Backend
- **Recommended Architecture:** Standalone Python Worker Daemon (`backend/app/integrations/workers/durable_worker.py`) managed under **PM2** (to align with HMS's existing PM2 infrastructure) or native **systemd** service units in Linux production.
- **Prohibited Architecture:** Running persistent streaming socket listeners or polling workers inside FastAPI Uvicorn web workers is strictly prohibited because web workers scale ephemerally and drop active TCP connections on restart.

---

## 6. Implementation Summary & Artifacts

All core contracts, domain models, and processing state machines were implemented in Python under `backend/app/integrations/processing/`:

| Module | Implemented Components | Verification Scope |
|:-------|:-----------------------|:-------------------|
| `processing/lifecycle.py` | `MessageLifecycleState`, `MessageLifecycleValidator`, `VALID_TRANSITIONS`, `TERMINAL_STATES`, `InvalidLifecycleTransitionError` | Enforces allowable state transitions and terminal states. |
| `processing/models.py` | `DurableMessageRecord`, `IdempotencyRecord`, `OutboxRecord`, `ProcessingResult`, `ClaimResult` | Candidate Pydantic entity schemas matching MySQL/PostgreSQL requirements. |
| `processing/policies.py` | `DeadLetterPolicy`, `WorkerClaimPolicy`, `NON_RETRYABLE_ERROR_CODES` | Backoff delay progression, jitter calculation, and fatal error filters. |
| `processing/repository.py` | `DurableMessageRepository`, `DurableIdempotencyRepository`, `OutboxRepository`, `InMemoryDurableMessageRepository` | Abstract contracts + thread-safe in-memory engine with lock timeout recovery. |
| `processing/worker.py` | `DurableMessageWorker` | Claiming, execution supervision, retry scheduling, and dead-letter handling. |
| `processing/__init__.py` | Public package exports | Clean modular interface. |

---

## 7. Security & Observability

### 7.1 Security Safeguards
- **SHA-256 Payload Hashes:** Hashes are one-way cryptographic digests; wire payloads cannot be derived from stored digests.
- **No Cleartext PII/PCI in Message Logs:** Card numbers (PAN), CVVs, and authorization tokens are redacted via `sanitize_payload()` prior to logging.
- **Property Tenant Boundaries:** Every database query, claim, and idempotency lease requires explicit `facility_id` scoping, preventing multi-tenant data leaks.

### 7.2 Observability & Operational Metrics
The durable message worker and repository emit structured telemetry counters:
- `messages_received_total` (counter, by protocol & facility)
- `messages_processed_total` (counter, by status)
- `idempotency_duplicates_total` (counter)
- `idempotency_conflicts_total` (counter)
- `retries_scheduled_total` (counter)
- `dead_letter_quarantined_total` (counter)
- `worker_claim_latency_seconds` (histogram)
- `oldest_pending_message_age_seconds` (gauge)

---

## 8. Test Execution & Verification

Independent test verification was executed across all four test suites using the project virtual environment (`Python 3.13.9`, `pytest-9.1.1`):

```powershell
ACX-Platform\backend\.venv\Scripts\python.exe -m pytest `
  ACX-Platform/backend/tests/test_integration_foundation.py `
  ACX-Platform/backend/tests/test_integration_transport.py `
  ACX-Platform/backend/tests/test_integration_local_tcp.py `
  ACX-Platform/backend/tests/test_integration_processing.py -v
```

### 8.1 Results Breakdown

| Test Suite | Tests Run | Passed | Failed | Skipped | Duration |
|:-----------|:----------|:-------|:-------|:--------|:---------|
| `test_integration_foundation.py` | 32 | 32 | 0 | 0 | 0.38s |
| `test_integration_transport.py` | 15 | 15 | 0 | 0 | 0.22s |
| `test_integration_local_tcp.py` | 10 | 10 | 0 | 0 | 0.28s |
| `test_integration_processing.py` | 10 | 10 | 0 | 0 | 0.22s |
| **TOTAL** | **67** | **67** | **0** | **0** | **1.10s** |

### 8.2 Detailed Verification of New Processing Suite
1. `test_lifecycle_valid_transitions` (PASSED): Validates standard progression (`RECEIVED` → `VALIDATED` → `PROCESSING` → `PROCESSED`).
2. `test_lifecycle_invalid_transitions` (PASSED): Enforces terminal state protections and prevents backwards transitions.
3. `test_durable_idempotency_duplicate_and_conflict` (PASSED): Verifies duplicate suppression and raises `IdempotencyConflictError` on payload tampering.
4. `test_durable_idempotency_multi_property_isolation` (PASSED): Verifies identical keys across different properties execute independently without collision.
5. `test_worker_batch_claim_mutual_exclusion` (PASSED): Confirms two concurrent workers cannot claim the same message.
6. `test_worker_abandoned_lock_reclamation` (PASSED): Verifies abandoned messages from dead workers are safely reclaimed after lock expiration.
7. `test_worker_successful_processing_progression` (PASSED): Verifies transition to `PROCESSED` on handler success.
8. `test_worker_fatal_error_fails_immediately` (PASSED): Verifies validation/auth errors transition to `FAILED` without retry.
9. `test_worker_retry_scheduling_and_dead_letter_exhaustion` (PASSED): Verifies exponential backoff and quarantine to `DEAD_LETTER`.
10. `test_outbox_enqueue_and_dispatch` (PASSED): Verifies outbox records are enqueued and claimed for dispatch.

---

## 9. Required Approvals & Remaining Blockers

### 9.1 Approvals Required Before Database Migrations
1. **DBA Schema Ratification:** Formal DBA approval of the three candidate table schemas (`integration_message_log`, `integration_idempotency_keys`, `integration_outbox`), index layouts, and partitioning strategy.
2. **Business Ownership Decisions (HF-01 to HF-39):**
   - `HF-01`: Authority of Record (PMS vs HMS for Guest & Stay lifecycle).
   - `HF-07`: Target HTNG Profile & Message Scope (WSDL/XSD missing).
   - `HF-11`: FIAS Vendor Specification Manual (record codes, status digits, link-alive interval).
   - `HF-18`: System of Record for Room Cleanliness States.

### 9.2 Recommended Next Milestone: Phase 6
Once DBA and stakeholder approvals are ratified:
1. **Alembic Migration Authoring:** Generate migration script `004_create_integration_schema.py` creating the candidate tables.
2. **SQLAlchemy Repository Implementation:** Build the concrete SQLAlchemy implementation of `DurableMessageRepository`, `DurableIdempotencyRepository`, and `OutboxRepository`.
3. **Transactional Outbox Hook:** Wire the outbox dispatch into `stays_write.py` and `facility_write.py` under feature flags.
