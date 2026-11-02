# OSS Microservice — Design, Security & Production Readiness

Addresses the governance conditions attached to PoC approval. Scope of the
current phase: **read path + read-only schema discovery**. Write path follows
after review.

---

## 1. Service-to-service security

**Current (PoC):** trusted-LAN, no inter-service auth, OSS bound to a private
interface (`HOST=127.0.0.1`). HMS remains the security boundary — it
authenticates the end user (JWT) and enforces `require_permission` **before**
forwarding, so an unauthorised caller never reaches OSS.

**Equivalent control (must be approved before any non-PoC/shared network):**
an optional shared **service token** is already wired and off by default:
- Set `OSS_SERVICE_TOKEN` to the same value in `backend/.env` and
  `oss-service/.env`.
- HMS `oss_client` then sends `X-OSS-Service-Token`; OSS
  `require_service_token` rejects mismatches with 401 (constant-time compare,
  never logged). Health stays ungated for probes.

**Production options (ranked), to formalise before go-live:**
1. **mTLS** between HMS and OSS (strongest; network-level identity).
2. Shared service token over TLS (the built-in control above) + IP allow-list.
3. Network isolation only (private subnet / security group) — acceptable only
   with compensating controls and explicit sign-off.

**Hard rule:** trusted-LAN-no-auth must not leave the PoC environment without a
formally approved equivalent control from the list above. This is enforced: with
any `APP_ENV` other than `development`, the service refuses to start unless
`OSS_SERVICE_TOKEN` is set.

## 2. Write-path design (authorization, validation, audit) — built after read review

Writes (`POST/PATCH /devices`, `/devices/{id}/commission|decommission|maintenance`)
currently stay in HMS and are **not** proxied yet. `PATCH /incidents/{id}` and
`/limit-configs` are not on this path at all: incidents and limit configs are
HMS (BSS) data with no OSS table, so they are written in HMS for good. When implemented they follow this contract:

- **Authorization:** unchanged HMS gate `require_permission("caleido_network",
  "write")` runs in HMS before any forward. OSS performs no authorization of its
  own (trusted caller) but honours the service token when enabled.
- **Validation:** full HMS-side Pydantic body validation is **reintroduced per
  write endpoint** (reads rely on OSS validation; writes do not). OSS re-validates
  types at the adapter boundary before touching the OSS DB, and maps constraint
  violations to the shared `409/422` envelope.
- **Audit logging:** every state-changing call is logged on BOTH sides with
  `actor_id` (the HMS user), action, target id, outcome and a correlation id —
  never the payload secrets. HMS logs intent+actor; OSS logs the DB effect.
  (A persistent audit table in the OSS DB is a follow-up once its schema is known.)
- **Transactions:** OSS writes run in a single transaction per request; partial
  failures roll back and surface as `409/422`, never a partial 200.

## 3. "Unknown ≠ zero" guarantee (occupancy device_count)

`OccupancyDetail.device_count` is `int | None`. When OSS is enabled but
unreachable/not-ready, `oss_client.device_count()` returns **None (unknown)**,
and the field serialises as `null` — explicitly distinguished from `0` (room
genuinely has no devices). Verified by test
`backend/tests/test_oss_dispatch.py::test_device_count_unknown_on_oss_failure`.

## 4. API compatibility checks

- **Contract parity:** OSS copies the HMS Pydantic response models verbatim
  (`oss-service/app/schemas/*` mirror `backend/app/schemas/*`). A parity test
  asserts the field sets match, so drift is caught in CI.
- **Path parity:** `backend/app/core/oss_routes.OSS_READ_PREFIXES` is the single
  source of truth; a test asserts the OSS OpenAPI exposes exactly these prefixes
  and that `/daily-data-points` is absent from OSS.
- **Frontend contract:** unchanged — same paths under `/api/v1`, same JSON
  shapes; the split is invisible to the frontend.

## 5. Test baseline

- **HMS (existing):** 1225 passed / 17 failed on the shared dev DB, where the 17
  are known seed-divergence (a provisioned credential + diverged occupancy
  data), not regressions. The OSS change adds `test_oss_dispatch.py` and must not
  increase that failure count with `OSS_ENABLED=false` (default).
- **OSS service:** scaffold tests pass with no DB (liveness, 503 degradation,
  path surface, token gate). Adapter/pagination tests are added after schema
  discovery.
- **Gate for merge:** HMS suite green modulo the known 17; OSS scaffold green.

## 6. Deployment & rollback

- **Deploy:** run `oss-service` (uvicorn :8001) with `OSS_DATABASE_URL` set;
  then flip `OSS_ENABLED=true` on HMS.
- **Rollback (instant, no redeploy):** set `OSS_ENABLED=false` on HMS and
  restart — HMS resumes serving device reads locally from `hms_db`. The feature
  flag is the rollback switch; the OSS service can be stopped independently.
- **Degraded mode:** if OSS is down while enabled, OSS read routes return 503
  (clear, retryable) and occupancy device_count shows `null` (unknown) — the
  rest of HMS is unaffected.

## 7. Production-readiness criteria (exit checklist)

- [ ] OSS schema discovered; `SCHEMA_MAPPING_TEMPLATE.md` completed; adapters
      implemented and returning real data.
- [ ] Read-path validated end-to-end (frontend→HMS→OSS→OSS DB→HMS→frontend) and
      reviewed.
- [ ] Contract + path parity tests green; HMS suite green modulo known 17.
- [ ] Approved service-to-service control enabled (mTLS or token+TLS) — not
      trusted-LAN-no-auth.
- [ ] Write path implemented with authz + validation + audit as in §2, reviewed
      separately.
- [ ] Observability: request/correlation id propagated HMS↔OSS; OSS logs ship to
      the same sink; health checks wired to the platform.
- [ ] Timeout/retry/circuit behaviour load-tested; occupancy N+1 avoided
      (batch device_count).
- [ ] Runbook: start order, flag flip, rollback, and OSS-down behaviour
      documented and rehearsed.
