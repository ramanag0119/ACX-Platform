# HTNG / FIAS — Test Strategy

## 1. Principles

* Integration suites need **no seeded HMS database**. Everything runs in memory except
  the MySQL suites, which require a **disposable** database.
* Repository behaviour is tested once and run twice: `tests/integrations/test_repository_contract.py`
  is parametrised over `InMemoryIntegrationRepository` and `SqlIntegrationRepository`.
* Vendor behaviour is never asserted. Fixtures are synthetic (`Z*` records,
  `urn:acx:test:generic-xml:v1`) and labelled `PROVISIONAL_TEST`. Simulator evidence is
  kept separate from vendor interoperability evidence (there is none).
* MySQL guard: tests skip unless `INTEGRATION_TEST_MYSQL_URL` is set, and **fail** if its
  database name equals the configured HMS `MYSQL_DATABASE`.

## 2. Suites (308 tests)

| File | Tests | Covers |
|---|---|---|
| `test_core.py` | 32 | canonical JSON/hash, correlation, masking, lifecycle, retry, error taxonomy, envelope |
| `test_security.py` | 46 | authentication (missing/invalid/disabled/unknown/protocol/malformed/oversize), facility resolution, scope smuggling, cross-facility access & idempotency, unauthorized redrive, leakage |
| `test_exchange.py` | 28 | adapter/handler registries, routing, unsupported protocol/type, malformed, duplicates, conflicts, retry→DLQ, outbound enqueue/relay |
| `test_transport_tcp.py` | 25 | framing (partial, multi, empty, noise, resync, oversize), loopback TCP (roundtrip, connect/read timeout, refused, disconnect, concurrent I/O, reconnect, budget, backpressure, idle, cleanup) |
| `test_fias_adapter.py` | 40 | production BLOCKED, unverified-spec gate, parsing/validation/serialisation on synthetic spec, spec validation |
| `test_htng_adapter.py` | 39 | XXE/billion-laughs/param-entity/external DTD, limits, SOAP 1.1/1.2, faults, registry gate, decode/encode/ack, SOAP transport classification, HTTPS rule |
| `test_repository_contract.py` | 36 (18 × 2 backends) | intake, idempotency scope, leases, fencing, takeover, retry, DLQ, redrive+audit, scoping, outbox |
| `test_mysql_persistence.py` | 18 | MySQL-only: JSON reordering, hash stability, FK 1452, concurrency, forced insert race, claim index, savepoint atomicity, restart recovery, CHECK, collation, SQL stores |
| `test_domain.py` | 20 | approval gate (real register closed), stay adapter with mocked services, facility ownership, validation |
| `test_api.py` | 16 | RBAC 401/403, readiness, scoping, masked detail, redrive rules + audit, HTNG endpoint, startup imports nothing |
| `test_end_to_end.py` | 8 (incl. 3 × 2 backends) | simulator → TCP → exchange → worker → outbox → TCP; SOAP → exchange → worker → outbox → mock vendor endpoint; simulator guards |

### Round 3 additions (406 collected / 405 passed / 1 skipped as of 2026-11-20)

`test_hardening.py` (13: outage recovery, settings validation, header injection, secret
exposure), `test_hms_domain_mysql.py` (4: real `stays_write` on a seeded disposable MySQL,
needs `INTEGRATION_TEST_HMS_DB_URL`), `test_vendor_contracts.py` now 5 (1 official-sample
run, skipped; 4 harness self-tests). Helper `hms_schema_shim.py` is test-only.

### Round 2 additions (385 tests at the end of round 2)

| File | Tests | Covers |
|---|---|---|
| `test_admin.py` | 12 | client lifecycle, rotation overlap/expiry/revoke, mapping management, CLI, mapping API (MySQL) |
| `test_ordering.py` | 19 | per-entity ordering on both backends incl. 4-thread concurrency, retry/DLQ blocking |
| `test_health_view.py` | 7 | facility health counts, backlog, latency window, scoping, endpoint |
| `test_service.py` | 11 | service loop, error back-off, graceful stop, purge (both backends), rate limit |
| `test_transport_server.py` | 6 | TCP listener allow-list, single owner, pump, framing errors |
| `test_migration_candidate.py` | 3 | draft upgrade/downgrade on MySQL, Alembic heads unchanged |
| `test_vendor_contracts.py` | 1 (skip) | official vendor samples against production adapters — none supplied |

Grown: `test_core` 35, `test_security` 52, `test_domain` 25, `test_repository_contract` 40.

## 3. How to run

Host Python is not required; the commands used:

```sh
# disposable services (isolated network, no published ports)
docker network create acx-int-net
docker run -d --name acx-int-mysql --network acx-int-net \
  -e MYSQL_ROOT_PASSWORD=<root> -e MYSQL_DATABASE=inspironics_app \
  -e MYSQL_USER=inspironics_app -e MYSQL_PASSWORD=<pw> mysql:8.4
docker exec acx-int-mysql mysql -uroot -p<root> -e \
  "CREATE DATABASE acx_integration_test; GRANT ALL ON acx_integration_test.* TO 'inspironics_app'@'%';"
docker run -d --name acx-int-py --network acx-int-net -v "<repo>/backend:/app" -w /app python:3.12-slim sleep infinity
docker exec acx-int-py sh -c "python -m venv /venv && /venv/bin/pip install -r requirements.txt"

# integration suites
docker exec -e MYSQL_SSL_VERIFY_CERT=false -e MYSQL_HOST=acx-int-mysql -e MYSQL_PASSWORD=<pw> \
  -e INTEGRATION_TEST_MYSQL_URL='mysql+pymysql://inspironics_app:<pw>@acx-int-mysql:3306/acx_integration_test?charset=utf8mb4' \
  acx-int-py /venv/bin/python -m pytest tests/integrations -q
```

Without `INTEGRATION_TEST_MYSQL_URL` the MySQL-parametrised cases are skipped and the
rest still run.

## 4. Not covered

* Real vendor systems (none available).
* The legacy HMS suite against a seeded MySQL (the repository cannot build the schema on
  MySQL — see baseline §4).
* Long-running soak / throughput, multi-process worker deployment, TLS on the TCP link.
