# HMS HTNG & FIAS — Phase 9: Adversarial Security & Recovery Verification Report

**Date:** 2026-11-18  
**Repository:** `ACX-Platform`  
**Branch:** `feature/htng&fias-integrate`  
**Current Alembic Head:** `a3f1c8e2d904`  
**Draft Migration:** `backend/migrations/drafts/b74e92a1d044_create_integration_persistence_tables.py`  
**Test Suite Status:** 103 items collected — **98 passed, 5 skipped, 0 failed** in 1.24s  
**Audit & Verification Status:** Complete  
**Overall Readiness Assessment:** **FOUNDATION READY — EXTERNAL VALIDATION PENDING**

---

## 1. Executive Summary

Phase 9 performed an adversarial security, concurrency, and failure-recovery stress test across the HMS HTNG and FIAS integration subsystem. Rather than accepting Phase 8 claims at face value, Phase 9 subjected the codebase to hostile probe scenarios, including fail-open authentication conditions, timing attacks, recursive multi-tenant payload smuggling, unauthorized dead-letter redrive, concurrency lease expiration race conditions, and deep PII/credential exposure.

### Primary Audit Achievements
1. **Critical Authentication Fail-Open Closed:** Discovered and eliminated a critical vulnerability where an unconfigured `OSS_SERVICE_TOKEN` in production would accept any arbitrary token and grant full wildcard `("*",)` access. The gateway now strictly **fails closed** with HTTP 503 if credentials are unconfigured in non-development environments.
2. **Timing Side-Channel Hardening:** Replaced standard equality comparisons on authorization secrets with constant-time `secrets.compare_digest`.
3. **Recursive Facility Isolation (HF-19):** Enhanced the dispatcher to recursively inspect arbitrary nested payload models, dictionaries, and list items for `facility_id` and `property_id`, rejecting cross-property smuggling even in deeply embedded sub-objects.
4. **Dead-Letter Redrive Authorization & Audit Logging:** Scoped `replay_dead_letter` to caller principal permissions, prevented redriving non-dead-letter messages, validated redrive reasons, and established structured administrative audit trails.
5. **Worker Concurrency & Lease Loss Protection:** Implemented `ConcurrencyLockLostError` and lease ownership verification in `update_status(..., expected_worker_id=...)`, preventing timed-out zombie workers from overwriting messages acquired by successor workers.
6. **Deep Credential & PII Masking:** Expanded pattern recognition to cover 13–19 digit payment cards, Bearer tokens, API keys, client secrets, passports, and compound field keys in nested structures.
7. **Regression & Safety Verification:** Preserved working tree integrity, maintained the active Alembic head at `a3f1c8e2d904`, and expanded the test suite to **103 tests** (98 passed, 5 skipped due to live PMS socket absence, 0 failed).

---

## 2. Exact Files Inspected

The following integration subsystem files were forensically inspected and adversarially tested:

- **Ingress & Gateway Security:**
  - `backend/app/integrations/gateway/router.py`: Header parsing, `get_integration_principal` dependency, health/readiness endpoints.
  - `backend/app/integrations/gateway/dispatcher.py`: Envelope routing, payload validation, idempotency coordination.
  - `backend/app/integrations/security/auth.py`: `IntegrationPrincipal` identity model, facility access checking.
  - `backend/app/integrations/security/isolation.py`: `validate_facility_scope` multi-tenant facility scope enforcement.
  - `backend/app/integrations/security/masking.py`: Regex scrubbers, recursive payload sanitization.
- **Message Processing & Concurrency:**
  - `backend/app/integrations/processing/lifecycle.py`: `MessageLifecycleValidator`, transition graphs, terminal state rules.
  - `backend/app/integrations/processing/models.py`: `DurableMessageRecord`, `ProcessingResult`.
  - `backend/app/integrations/processing/repository.py`: `DurableMessageRepository`, `InMemoryDurableMessageRepository`.
  - `backend/app/integrations/processing/sqla_repository.py`: `SqlAlchemyDurableMessageRepository`, `SqlAlchemyIdempotencyRepository`.
  - `backend/app/integrations/processing/worker.py`: `DurableMessageWorker`, batch loops, claim leases, shutdown hooks.
- **Core Abstractions & Exceptions:**
  - `backend/app/integrations/core/exceptions.py`: Integration exception hierarchy.
  - `backend/app/integrations/core/envelope.py`: `IntegrationEnvelope`, `TraceContext`, `MessageMetadata`.
  - `backend/app/integrations/core/idempotency.py`: Composite key storage `(facility_id, key)`.
- **Database & Migration Manifests:**
  - `backend/migrations/drafts/b74e92a1d044_create_integration_persistence_tables.py`: Quarantined DDL.
  - `backend/migrations/env.py`: Alembic environment configuration.

---

## 3. Security Bypasses Tested

| Probe ID | Attack Vector / Scenario | Target Component | Initial Behavior | Remediated Behavior |
|---|---|---|---|---|
| **ADV-01** | Missing `OSS_SERVICE_TOKEN` in production with arbitrary token | `router.py:get_integration_principal` | **FAIL-OPEN:** Bypassed auth check; granted wildcard `("*",)` access | **FAIL-CLOSED:** Raises HTTP 503 Service Unavailable when secret unconfigured |
| **ADV-02** | Timing side-channel attack on authentication secret | `router.py:get_integration_principal` | `token_str != settings.OSS_SERVICE_TOKEN` (early-exit byte comparison) | Uses constant-time `secrets.compare_digest` |
| **ADV-03** | Missing token in production / blank whitespace token | `router.py:get_integration_principal` | Correctly raised 401 | Verified; raises HTTP 401 |
| **ADV-04** | Nested payload tenant smuggling (sub-dict `room.facility_id`) | `dispatcher.py:dispatch` | **BYPASS:** Only checked top-level payload key | **REJECTED:** Recursively validates all nested facility fields |
| **ADV-05** | Nested payload tenant smuggling (list `charges[1].facility_id`) | `dispatcher.py:dispatch` | **BYPASS:** List items skipped | **REJECTED:** Recursively inspects lists; raises `PropertyAuthorizationError` |
| **ADV-06** | Cross-facility dead-letter redrive by scoped principal | `repository.py:replay_dead_letter` | **BYPASS:** Did not verify caller permissions on message facility | **REJECTED:** Validates `principal.can_access_facility(rec.facility_id)` |
| **ADV-07** | Replaying already processed/replayed message | `repository.py:replay_dead_letter` | Idempotent or unvalidated | **REJECTED:** Enforces `DEAD_LETTER` precondition; raises `InvalidLifecycleTransitionError` |
| **ADV-08** | Blank or whitespace administrative redrive reason | `repository.py:replay_dead_letter` | Accepted blank string | **REJECTED:** Raises `ValueError` if reason is whitespace-only |
| **ADV-09** | Worker lease expiration & zombie worker status overwrite | `worker.py` / `sqla_repository.py` | Overwrote successor worker lock | **PROTECTED:** Raises `ConcurrencyLockLostError`; aborts zombie update |
| **ADV-10** | Unsanitized credentials in exception strings (`Bearer`, `api_key`) | `masking.py:mask_sensitive_string` | Leaked raw bearer token and api_key | **MASKED:** Regex replaces tokens with `bearer=******`, `api_key=******` |

---

## 4. Test Cases and Exact Results

### Test Suite Execution
Across all 7 integration test suites, **103 total items were collected and executed**:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\user\OneDrive - Inspironics India\Insp Total Work\HMS-Frontend\ACX-Platform\backend
plugins: anyio-4.15.1
collected 103 items

tests\test_integration_foundation.py ................................    [ 31%]
tests\test_integration_local_tcp.py .....sssss                           [ 40%]
tests\test_integration_persistence_sqla.py .............                 [ 53%]
tests\test_integration_processing.py ..........                          [ 63%]
tests\test_integration_transport.py ...............                      [ 77%]
tests\test_integration_security_and_recovery.py .........                [ 86%]
tests\test_integration_phase9_adversarial.py ..............              [100%]

================== 98 passed, 5 skipped, 1 warning in 1.24s ===================
```

### Breakdown of Phase 9 Adversarial Tests (`test_integration_phase9_adversarial.py`):
1. `test_auth_production_fails_closed_when_secret_unconfigured` — **PASSED** (verifies 503 on None and whitespace).
2. `test_auth_production_requires_token_and_validates_constant_time` — **PASSED** (verifies 401 on missing, 403 on invalid, token not leaked).
3. `test_auth_development_allows_fallback_but_validates_if_secret_configured` — **PASSED** (verifies dev fallback vs token validation).
4. `test_dispatcher_rejects_nested_payload_facility_smuggling` — **PASSED** (verifies sub-dict and list tenant smuggling rejection).
5. `test_facility_scope_case_insensitivity_and_whitespace` — **PASSED** (verifies case-insensitive matching and whitespace stripping).
6. `test_sqla_repository_invalid_uuid_rejected_cleanly` — **PASSED** (verifies clean PropertyAuthorizationError on malformed UUID).
7. `test_redrive_cross_facility_denied_for_scoped_principal` — **PASSED** (verifies cross-property redrive denial).
8. `test_redrive_audit_logging_and_reason_validation` — **PASSED** (verifies metadata audit record and blank reason rejection).
9. `test_redrive_already_replayed_or_non_dead_letter_rejected` — **PASSED** (verifies rejection of non-dead-letter replay).
10. `test_worker_pre_claim_shutdown_no_ops` — **PASSED** (verifies 0 claims and zero DB mutations when stopped).
11. `test_worker_lease_loss_concurrency_protection` — **PASSED** (verifies ConcurrencyLockLostError on lease loss).
12. `test_worker_cannot_release_another_workers_lock` — **PASSED** (verifies lease ownership enforcement on release).
13. `test_masking_comprehensive_credential_and_pii_coverage` — **PASSED** (verifies 13-19 digit cards, emails, phones, bearer tokens, passports).
14. `test_sanitize_payload_deep_nested_and_compound_keys` — **PASSED** (verifies compound keys in nested payloads).

---

## 5. Defects Found and Fixed

### Defect 1: Fail-Open Ingress Authentication in Production
- **Severity:** High (Critical Security Vulnerability)
- **Root Cause:** When `settings.OSS_SERVICE_TOKEN` was unset or empty string in production, the condition `if settings.OSS_SERVICE_TOKEN and token_str:` evaluated to `False`. The logic fell through to returning an authenticated principal with `authorized_facility_ids=("*",)`.
- **Fix in `router.py`:** Added mandatory validation in non-development environments: if `configured_secret` is falsy, the gateway immediately fails closed with `HTTP 503 Service Unavailable`. If `token_str` does not match via `secrets.compare_digest`, it rejects with `HTTP 403 Forbidden`.

### Defect 2: Timing Side-Channel on Token Comparison
- **Severity:** Medium
- **Root Cause:** Token validation used standard Python `!=` operator, which is vulnerable to character-by-character timing inference.
- **Fix in `router.py`:** Migrated to `secrets.compare_digest(token_str, configured_secret)`.

### Defect 3: Shallow Payload Facility Alignment (Tenant Smuggling Vulnerability)
- **Severity:** High
- **Root Cause:** `dispatcher.py` checked only top-level `payload["facility_id"]`. Nested models (e.g. `payload["room"]["facility_id"]`) were ignored, allowing cross-property data smuggling into downstream services.
- **Fix in `dispatcher.py`:** Added cycle-safe recursive scanner `_extract_all_facility_ids()` that inspects all nested dicts, lists, and objects for `facility_id` and `property_id` fields.

### Defect 4: Unauthenticated & Cross-Facility Dead-Letter Redrive
- **Severity:** High
- **Root Cause:** `replay_dead_letter` did not accept or validate caller identity, allowing any internal caller to redrive messages belonging to other properties without audit tracking.
- **Fix in `repository.py` & `sqla_repository.py`:** Added `principal` and `reason` arguments. Enforces `principal.can_access_facility(record.facility_id)`, rejects blank reasons, and logs structured audit entries into `metadata_fields["redrive_audit"]`.

### Defect 5: Zombie Worker Race Condition on Expired Leases
- **Severity:** Medium
- **Root Cause:** If a worker's lock lease expired and another worker claimed the message, the original worker could still call `update_status()` and overwrite the database record.
- **Fix in `repository.py`, `sqla_repository.py` & `worker.py`:** Added `expected_worker_id` checking to `update_status()`. Raises `ConcurrencyLockLostError` if the lock is held by another worker, preventing database state corruption.

### Defect 6: Incomplete PII & Credential Masking in Strings
- **Severity:** Low-Medium
- **Root Cause:** Masking regexes did not cover 19-digit payment cards, Bearer tokens, or embedded passport numbers in raw exception messages.
- **Fix in `masking.py`:** Expanded `_CREDIT_CARD_REGEX` to 13–19 digits, added `_AUTH_TOKEN_REGEX` and `_PASSPORT_REGEX`, and added compound key substring matching in `sanitize_payload`.

---

## 6. Remaining Risks

1. **In-Memory Transport State in Web Process:** The physical TCP transport client (`transport/client.py`) must be supervised by a standalone background daemon process in production, never within the multi-worker web tier (e.g. Uvicorn/Gunicorn).
2. **Missing Out-of-Band Redrive UI/CLI:** While `replay_dead_letter` is cryptographically and tenant-isolated at the repository layer, an administrative HTTP endpoint with role-based access control (RBAC) has not yet been exposed in `router.py`.
3. **Database Clock Skew:** MySQL `SELECT ... FOR UPDATE SKIP LOCKED` and lease expiration checks rely on synchronized UTC system clocks across application servers and the database engine.

---

## 7. MySQL Runtime Verification Status

- **DDL & Query Compilation:** Fully verified against MySQL 8.0 dialect via SQLAlchemy `CreateTable(InboundMessageModel.__table__).compile(dialect=mysql.dialect())` and `with_for_update(skip_locked=True)`.
- **Live Database Connection:** **RETAINED AS PENDING**. Live MySQL and Docker services remain unavailable in the local execution sandbox.
- **Migration Quarantining:** Draft migration `b74e92a1d044_create_integration_persistence_tables.py` remains strictly parked in `backend/migrations/drafts/`. The active Alembic head is untouched at `a3f1c8e2d904`.

---

## 8. Vendor and Business Blockers

Live integration testing cannot proceed until external stakeholders fulfill the following prerequisites:

1. **Vendor FIAS Specification:** Official Oracle Hospitality / Micros / Fidelio FIAS specification manual detailing exact record layouts, delimiters, and dialect versions.
2. **Vendor HTNG Schemas:** Official HTNG 2008b / 2009a SOAP/REST WSDL and XSD schemas, endpoint definitions, and test credentials.
3. **Vendor Sandbox Endpoint:** Network connectivity (IP, port, VPN) to a certified PMS/PBX test simulator or staging gateway.
4. **DBA Authorization:** Lead DBA formal review and execution sign-off for migration `b74e92a1d044`.
5. **Business Stakeholder Sign-Off:** Execution of decisions documented in `HTNG_FIAS_BUSINESS_DECISION_MEETING_PACK.md`.

---

## 9. Final Git Status

The working tree has been preserved with zero commits, pushes, merges, or rebases:

```text
On branch feature/htng&fias-integrate
Changes not staged for commit:
  modified:   backend/app/api/v1/router.py

Untracked files:
  backend/app/integrations/
  backend/migrations/drafts/
  backend/tests/test_integration_foundation.py
  backend/tests/test_integration_local_tcp.py
  backend/tests/test_integration_persistence_sqla.py
  backend/tests/test_integration_phase9_adversarial.py
  backend/tests/test_integration_processing.py
  backend/tests/test_integration_security_and_recovery.py
  backend/tests/test_integration_transport.py
  docs/HTNG_FIAS_... (all documentation packs)
```

---

## 10. Final Readiness Assessment

The integration foundation, transport architecture, persistence layer, multi-tenant security boundaries, concurrency controls, and failure-recovery mechanisms have been verified under adversarial conditions and hardened against exploit vectors.

```text
FOUNDATION READY — EXTERNAL VALIDATION PENDING
```
