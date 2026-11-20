# HTNG / FIAS — Operations Runbook

Status: **nothing vendor-facing is enabled.** Integration tables do not exist in the HMS
database until the DBA approves HF-39; every procedure below assumes that has happened.

## 1. Configuration (`INTEGRATION_` prefix, `backend/app/integrations/config.py`)

| Variable | Default | Effect |
|---|---|---|
| `INTEGRATION_ENABLED` | `false` | master switch: inbound endpoints and the service process |
| `INTEGRATION_HTNG_INBOUND_ENABLED` | `false` | serves `POST /api/v1/integrations/htng/inbound` |
| `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE` | unset | per-client limit per API process (429 SOAP fault) |
| `INTEGRATION_LIVE_DOMAIN_WRITES` | `false` | one of two gates for HMS writes (the other is the approval register in code) |
| `INTEGRATION_ACTOR_USER_ID` | unset | HMS user stamped on integration writes (HF-18) |
| `INTEGRATION_STORE_RAW_WIRE_PAYLOAD` | `false` | keep raw wire bytes (HF-21) |
| `INTEGRATION_RETENTION_DAYS` | unset | purge completed rows older than N days; also the duplicate-protection window (HF-21) |
| `INTEGRATION_SIMULATOR_ENABLED` | `false` | allows the TEST simulator (loopback only) |
| `INTEGRATION_MAX_MESSAGE_BYTES` | 262144 | per-message limit |
| `INTEGRATION_WORKER_LEASE_SECONDS` | 60 | worker lease |
| `INTEGRATION_RETRY_MAX_ATTEMPTS` / `_BASE_SECONDS` / `_MAX_SECONDS` | 5 / 5 / 900 | retry policy |

## 2. Initial configuration (per vendor)

Follow `HTNG_FIAS_VENDOR_ONBOARDING_CHECKLIST.md`. In short:

```sh
python -m app.integrations.cli create-client --code pms-hotel-a --protocol fias --actor <you>
#   -> prints the secret ONCE; deliver via the HF-22 channel
# mappings (facility-scoped operator API, created DISABLED):
POST  /api/v1/integrations/mappings   {"client_code","external_property_code","facility_id"}
PATCH /api/v1/integrations/mappings/{id}   {"enabled": true, "reason": "..."}
python -m app.integrations.cli enable-client --code pms-hotel-a --actor <you>
INTEGRATION_ENABLED=true python -m app.integrations.service      # worker process
```

## 3. Health

| Endpoint | Auth | Meaning |
|---|---|---|
| `GET /health`, `GET /api/v1/health/db` | none | process / HMS DB (existing) |
| `GET /api/v1/integrations/health` | none | router mounted; no data |
| `GET /api/v1/integrations/readiness` | read | 200/503 with reasons: tables, adapters, worker heartbeats, transports, live-write gate |
| `GET /api/v1/integrations/facilities/health?window_minutes=60` | read | per facility (own scope): inbound/outbound by status, pending, retrying, DLQ, oldest pending age, latency p50/p95/max, per client last received / last succeeded; link states; auth-failure counters |
| `GET /api/v1/integrations/metrics` | read | in-process counters (per process) |

Expected today: readiness 503 (`integration_tables_missing (HF-39)`, `no_adapter_ready`,
`integration_disabled`).

## 4. Connection troubleshooting

| Symptom | Check |
|---|---|
| Link state `disconnected`, `reconnect_attempts` rising | network path (HF-24), vendor side up, `last_error_code` (`connect_failed`, `connect_timeout`) |
| Listener `rejected_peers` rising | peer IP not in `allowed_peers` |
| Listener `rejected_busy` | a second connection while one is active (single owner) — find the duplicate sender |
| `framing_errors` rising | framing configuration vs vendor document |
| `read_timeouts` only | idle link — not an error until heartbeat rules are known |
| HTNG 401 | client code/secret, client enabled, protocol allowed, rotation expired |
| HTNG 403 | property code not mapped / disabled for this client, or payload scope mismatch |
| HTNG 429 | rate limit |

## 5. Credential rotation

```sh
python -m app.integrations.cli rotate-secret --code pms-hotel-a --overlap-hours 24 --actor <you>
# vendor switches to the new secret within the overlap window, then:
python -m app.integrations.cli revoke-previous-secret --code pms-hotel-a --actor <you>
```
Overlap 0–7 days; 0 invalidates the old secret immediately (compromise). Every step is
audited (`client.secret_rotated`, `client.previous_secret_revoked`); secrets never are.

## 6. Message replay / DLQ recovery

1. `GET /api/v1/integrations/dlq` → pick a message; `GET …/messages/{id}` (masked body).
2. Read `last_error_code` / category:
   * `transient` exhausted → fix the dependency, then redrive.
   * `validation`, `protocol`, `unsupported`, `security` → will fail again unless data
     or configuration changed (mapping, spec). Fix first.
   * `approval_blocked` → succeeds only once the gate opens.
   * `hms_business_rule` → HMS rejected the change (e.g. stay already checked out); usually
     needs a business decision, not a redrive.
3. `POST …/messages/{id}/redrive {"reason": "..."}` (write permission, own facility).
4. **Ordering:** later messages for the same entity (e.g. the same stay) wait behind a
   dead-lettered one. Redriving it releases the chain in order.
5. Vendor-side resend of a message already accepted returns `duplicate` (within the
   retention window).

## 7. Incident investigation

1. Get the correlation id (`X-Correlation-ID` header, or from the message row).
2. `GET …/messages?…` / message detail → status, attempts, last error.
3. `GET …/audit` → privileged actions (redrive, mapping, client, retention) and security
   rejections (auth failures carry only well-formed client codes).
4. Logs (`hms.integrations.*`) carry ids, codes and categories only — never payloads.
5. Outbound side: `GET …/outbox?status=DEAD_LETTER`.

## 8. Service process

`python -m app.integrations.service` (exits 3 unless `INTEGRATION_ENABLED=true`). Graceful
on SIGTERM/SIGINT; survives DB outages with bounded back-off; several instances are safe
(SKIP LOCKED + fencing). PM2/systemd supervision and the single FIAS-link owner rule are
HF-25/HF-26. No outbound sender is wired until a vendor endpoint/link exists — outbox rows
then stay PENDING rather than failing.

## 9. Test simulator (development only)

```sh
INTEGRATION_SIMULATOR_ENABLED=true python -m app.integrations.simulators.fias_simulator --port 5010
```
