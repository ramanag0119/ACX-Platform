# HTNG / FIAS — Infrastructure and Security Readiness (draft for OPS / ARCH / SEC)

Status: **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** This document fills the
"no infrastructure/deployment design" gap. It states **what exists in code** (verified
2026-11-20) and **what is undecided**. It decides nothing: HF-22, HF-23, HF-24, HF-25 and HF-26
are **Open** or **Awaiting Vendor Confirmation** in `HTNG_FIAS_DECISION_REGISTER.md`. No real
host, address or credential appears here.

## 1. Runtime components as implemented

| Component | How it runs | Default | Verified in |
|---|---|---|---|
| HTNG inbound endpoint | Inside the existing FastAPI app: `POST /api/v1/integrations/htng/inbound` | **disabled**: answers 503 unless `INTEGRATION_ENABLED` and `INTEGRATION_HTNG_INBOUND_ENABLED` are set | `api/router.py`, `config.py` |
| Operator, observability and mapping APIs | Inside the FastAPI app; HMS JWT + `facility_management` RBAC + facility scope | on (read APIs); mapping writes need the write grant | `api/router.py` |
| Integration service (inbound worker, outbox relay, retention purge) | Separate process: `python -m app.integrations.service` | **refuses to start** (exit code 3) unless `INTEGRATION_ENABLED=true`; SIGTERM/SIGINT finish the batch and stop | `service.py` |
| FIAS TCP link | `TcpLink` (client, bounded reconnect back-off) or `TcpListenerLink` (listener: `allowed_peers` **required**; extra connections rejected and counted) | **not wired into any production process yet**; the link role is HF-06/B7 | `transport/tcp.py`, `transport/tcp_server.py` |
| Outbound sender | none configured; outbox rows wait as PENDING | — | `service.py` docstring |
| FIAS test simulator | development only; needs `INTEGRATION_SIMULATOR_ENABLED=true` and a loopback bind | off | `simulators/fias_simulator.py` |
| Client and credential admin | CLI only: `python -m app.integrations.cli` (`create-client`, `rotate-secret`, …); the secret is printed once | — | `cli.py`, `admin.py` |
| Database | the HMS MySQL; integration tables only after HF-39; TLS to MySQL **required** (`MYSQL_SSL_CA`, certificate verification on by default) | — | `app/core/config.py` |

Production switches (all off by default): `INTEGRATION_ENABLED`,
`INTEGRATION_HTNG_INBOUND_ENABLED`, `INTEGRATION_LIVE_DOMAIN_WRITES`,
`INTEGRATION_STORE_RAW_WIRE_PAYLOAD`, `INTEGRATION_SIMULATOR_ENABLED`.
`INTEGRATION_RETENTION_DAYS` and `INTEGRATION_HTNG_RATE_LIMIT_PER_MINUTE` are unset.

## 2. Logical network flow (no real endpoints; decisions in brackets)

```text
 PMS (vendor, HF-03)                         HMS environment
 ───────────────────                         ────────────────────────────────────────────
 HTNG client ──HTTPS [HF-24 TLS, HF-08 WS-Sec/mTLS]──► reverse proxy [HF-24] ──► FastAPI
                                                                     /integrations/htng/inbound
 FIAS ◄──TCP [HF-06 who listens, framing; HF-24 VPN/IP]──► FIAS link process [HF-25 placement,
                                                            HF-26 single owner, allow-list]
                                                                     │
 FastAPI ─┬─ MySQL (TLS) ◄── integration service (workers, relay, purge) [HF-25/26]
          └─ operators: dashboard / APIs (HMS JWT, RBAC, facility scope)
```

## 3. Decisions required (owner roles from the canonical register)

| Area | Decision | ID | Owner | Input already available |
|---|---|---|---|---|
| Hosting | Where the integration service and the FIAS link process run (same host as the API or separate); supervision (the runbook names PM2 or systemd as candidates) | HF-25 | ARCH, OPS | §1; `OPERATIONS_RUNBOOK.md` §8 |
| Restart | Restart policy; **exactly one owner process per FIAS link** (a second listener or client would double-connect); behaviour after crash (leases expire and messages are re-claimed) | HF-26 | ARCH, OPS | leases, fencing and SKIP LOCKED are implemented and tested |
| Network | VPN / IP ranges, which side listens, firewall rules, TLS termination for HTNG | HF-24 | OPS, SEC, VENDOR | vendor items B12 / C10 / B7 |
| Message security | WS-Security / mTLS profile for HTNG | HF-08 | VENDOR, SEC | vendor item C5 |
| Credentials | Where client secrets are kept and the delivery channel to the vendor; rotation cadence (an overlap of 0–7 days is supported) | HF-22 | SEC, OPS | hash-only storage; CLI rotation and revocation |
| Database TLS | How the CA for the target MySQL is distributed (`MYSQL_SSL_CA`) | (part of HF-24/HF-39) | OPS, DBA | settings validation refuses to start without it |
| Payload data | Retention days, encryption at rest, payload access | HF-21 | LEGAL, SEC | `INTEGRATION_RETENTION_DAYS`; raw wire bytes off |
| Audit | Retention and immutability of `integration_audit_events` | HF-23 | SEC, LEGAL | append-only by convention |
| PII | Guest PII scope | HF-20 | LEGAL, PO, SEC | logs and reports already exclude PII (tested) |
| Rate limit | Per-client limit value | BLK-V7 | VENDOR, OPS | setting exists, unset |

## 4. Monitoring, escalation and recovery

| Need | Available in code / runbook | Owner |
|---|---|---|
| Liveness / readiness | `GET /integrations/health`, `/integrations/readiness` | **unassigned** |
| Backlog, DLQ, latency, link state | `/integrations/facilities/health`, `/integrations/observability/*`, dashboard | **unassigned** |
| Alert routing | none implemented (no Prometheus client approved) | **unassigned** |
| DLQ recovery | audited redrive (write grant); runbook §6 | **unassigned** |
| Credential incident | rotation / revocation CLI; runbook §5 | SEC (HF-22) |
| Link faults | runbook §4 | OPS (after HF-06) |

**Monitoring ownership is the open organisational item.** It is proposed for OPS, but the PO
must confirm it.

## 5. Backup and rollback

* **Database:** follow the DBA package §6. Back up before applying; roll back with the
  downgrade, which drops only the seven integration tables. No HMS data is lost; integration
  history is.
* **Application:** all features sit behind switches that default to off, so rolling back means
  disabling the switches and stopping the service process. Live HMS writes additionally need the
  code approval gate (HF-01, 02, 05, 19).
* **Credentials:** revoke the client, or end the overlap early.

## 6. Exit criteria for this area

HF-22, 23, 24, 25 and 26 decided and recorded. Monitoring owner named. A non-production
deployment with the service supervised. A kill/restart drill and a link-loss drill executed and
documented. Security review of `HTNG_FIAS_SECURITY_DESIGN.md` signed.
