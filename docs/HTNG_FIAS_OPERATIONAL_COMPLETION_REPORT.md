# HTNG / FIAS — Operational Completion Report (2026-11-20)

Official status (unchanged): **FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.**
Nothing in this report is vendor evidence. All tests used synthetic data in disposable
environments; no real HMS database, vendor endpoint or vendor credential was used.

| Repository | Branch | HEAD before / after | Staged / committed / pushed |
|---|---|---|---|
| `ACX_PLATFORM\ACX-Platform` | `feature/htng-fias-on-develop` | `46904fd` / `46904fd` | nothing |

The separate copy `HMS-Frontend\ACX-Platform` was not touched (HEAD `754bd8a`, 35 status entries,
identical before and after). `docker-compose.dev.yml` and `backend/app/api/v1/router.py` checksums
are unchanged.

## 1. Original dashboard symptoms

| Card | Showed |
|---|---|
| HTNG production readiness | Not ready |
| HTNG connection | Disabled |
| HTNG processing | Backlog stalled |
| FIAS production readiness | Not ready |
| FIAS connection | Not observable |
| FIAS processing | Backlog stalled |
| Vendor validation | Pending |

## 2. Root cause of every symptom (verified in current source, not taken from old reports)

| Symptom | Root cause | Defect? | Action |
|---|---|---|---|
| **Backlog stalled (HTNG, FIAS)** | (a) **Real:** no worker runs anywhere. `python -m app.integrations.service` refuses to start while `INTEGRATION_ENABLED=false` (exit 3), so stored messages are never processed. (b) **Calculation defect:** `observability._processing` measured the age of the oldest *unfinished* message by `received_on`, so a retry legitimately scheduled for tomorrow (`RETRY_WAIT`) and a message under a *live* worker lease (`PROCESSING`) were both reported as a stall. (c) **Robustness defect:** one stored row with an unknown `direction`/`protocol` made `SqlIntegrationRepository.claim()` raise inside the transaction — the whole batch rolled back on every poll, which would genuinely stall a running worker forever | (b), (c) yes | (b) status now derived from **due** work; (c) such rows are quarantined. (a) is configuration, verified to clear when the service runs (§10) |
| HTNG connection: Disabled | `INTEGRATION_ENABLED` and `INTEGRATION_HTNG_INBOUND_ENABLED` default to false (by design). Even if switched on, the production HTNG adapter is BLOCKED (empty schema registry: HF-07/HF-08) | No | unchanged — must stay off until approved |
| FIAS connection: Not observable | No process creates a FIAS link: `runtime.py` registers no transport and `service.main()` started only the inbound worker. The production FIAS adapter is BLOCKED (`PRODUCTION_SPECIFICATION is None`, HF-11) and there is no verified framing / ACK / heartbeat (HF-06) | Wiring gap | link lifecycle **implemented** (`LinkSupervisor`), production start **refused** with the missing decision named |
| Production readiness: Not ready | `_readiness()` reasons: vendor validation pending, business approval pending, DBA approval pending, synthetic certification not reported, integration disabled, live-write gate closed, transport disabled | No (correct) | the single label now carries **blocked-by categories** |
| Vendor validation: Pending | static, from the in-code approval register (`domain/approvals.py`) and adapter readiness; no vendor document exists | No | unchanged (must not change without evidence) |
| (found during audit) Outbound rows of a protocol without a sender were dead-lettered (`sender_not_configured`) the moment any relay ran | `OutboxRelay` claimed every protocol | Yes | relay claims only deliverable protocols |
| (found during audit) `HtngSoapSender` existed but nothing registered it; `service.main()` passed `relay=None` | wiring gap | Yes | relay wired with a validated, gated sender builder |
| (found during audit, previously reported in E2E finding 1) an invalid stored `direction` made `/observability/messages` and `/dlq` return HTTP 500 | strict enum mapping on read paths | Yes | tolerant read-only mapping |

## 3. Files inspected

`backend/app/integrations/`: `service.py`, `runtime.py`, `config.py`, `observability.py`,
`api/router.py`, `exchange/gateway.py`, `exchange/registry.py`, `processing/activity.py`,
`processing/repository.py`, `processing/sql_repository.py`, `processing/sql_models.py`,
`processing/worker.py`, `processing/health.py`, `core/retry.py`, `core/lifecycle.py`,
`core/errors.py`, `core/envelope.py`, `domain/approvals.py`, `domain/stays.py`,
`adapters/base.py`, `adapters/htng/adapter.py`, `adapters/htng/schema.py`,
`adapters/htng/sender.py`, `adapters/fias/adapter.py`, `adapters/fias/spec.py`,
`adapters/fias/codec.py`, `transport/soap.py`, `transport/xml_security.py`, `transport/tcp.py`,
`transport/tcp_server.py`, `transport/framing.py`, `security/clients.py`, `security/facility.py`,
`admin.py`, `metrics.py`, `simulators/fias_simulator.py`, `simulators/fixtures.py`;
`backend/tests/integrations/conftest.py` and the affected test modules;
`frontend/src/features/integrations/**`, `frontend/src/lib/api/integrations.ts`,
`frontend/src/lib/api/hooks.ts`; `docs/HTNG_FIAS_DECISION_REGISTER.md`,
`docs/HTNG_FIAS_FULLSTACK_E2E_VERIFICATION_REPORT.md`,
`docs/HTNG_FIAS_OBSERVABILITY_IMPLEMENTATION_REPORT.md`, `docs/HTNG_FIAS_BLOCKER_REGISTER.md`.

## 4. Files changed

| File | Change (+/− lines) |
|---|---|
| `backend/app/integrations/processing/activity.py` | +154: `BacklogSnapshot`, `backlog_from_memory`, `backlog_from_sql` |
| `backend/app/integrations/processing/repository.py` | +41 −3: `backlog()` (non-abstract), `claim_outbox(protocols=…)`, `outbox_dead_letter_audit` |
| `backend/app/integrations/processing/sql_repository.py` | +97 −9: backlog, protocol-filtered outbox claim, outbox dead-letter audit, corrupt-row quarantine in `claim`, tolerant `_to_view` for read paths |
| `backend/app/integrations/processing/worker.py` | +5 −1: relay claims only protocols it has senders for |
| `backend/app/integrations/observability.py` | +137 −11: due-work processing status, `outbound_processing`, `outbound_sender`, `blocked_by` |
| `backend/app/integrations/config.py` | +39: HTNG outbound endpoint and FIAS link settings (all OFF) with validation |
| `backend/app/integrations/service.py` | +62 −4: `build_outbound_senders`, relay wiring, FIAS link start / refusal / stop |
| `backend/app/integrations/transport/link_runtime.py` | **new**, 188 lines: `LinkSupervisor`, `build_fias_link_supervisor`, `LinkNotStartable` |
| `backend/tests/integrations/test_operational_completion.py` | **new**, 558 lines, 47 tests (+2 SQL-only skips on the in-memory variant) |
| `backend/tests/integrations/test_exchange.py` | +10 −2: one test updated to the changed outbox contract (§5.4) |
| `frontend/src/lib/api/integrations.ts` | optional new response fields (types only) |
| `frontend/src/features/integrations/lib/presentation.ts` | +29 −3: new status labels / explanations, `blockerLabel` |
| `frontend/src/features/integrations/views/ProtocolView.tsx` | +36 −10: backlog breakdown and outbound delivery in the Processing panel |
| `frontend/src/features/integrations/views/OverviewView.tsx` | +24 −4: "Blocked by" under each production-readiness badge |
| `frontend/src/features/integrations/__tests__/integrations.test.cjs` | +56: 5 tests |
| `frontend/src/features/integrations/__tests__/observability-fixtures.json` | + `overview_operational` (generated by the **real** backend code, synthetic data; existing entries byte-identical) |
| `docs/HTNG_FIAS_OPERATIONAL_COMPLETION_REPORT.md` | this report |

No schema, migration, seed, `docker-compose.dev.yml`, HMS module, decision-register or
approval-register change.

## 5. Exact code-level fixes

### 5.1 Processing status from due work (the false "stalled")

`next_attempt_at` already encodes when a row may be claimed (PENDING → intake time, RETRY_WAIT →
retry time, PROCESSING → lease expiry). The new snapshot counts, per protocol and facility scope:

```sql
SELECT protocol, COUNT(*),
       SUM(CASE WHEN COALESCE(next_attempt_at, received_on) <= :now THEN 1 ELSE 0 END)          AS due_now,
       SUM(CASE WHEN COALESCE(next_attempt_at, received_on) >  :now AND status='PROCESSING' THEN 1 ELSE 0 END) AS in_progress,
       MIN(CASE WHEN COALESCE(next_attempt_at, received_on) <= :now THEN COALESCE(next_attempt_at, received_on) END) AS oldest_due_at
  FROM integration_inbound_messages
 WHERE status IN ('PENDING','PROCESSING','RETRY_WAIT') AND facility_id IN (:scope)
 GROUP BY protocol;
```

plus `ordering_blocked` (unfinished rows with an earlier same-key `DEAD_LETTER`) and the same
due/scheduled split for the outbox. Status rules (`observability._processing`):

| Condition | Status |
|---|---|
| nothing unfinished | `idle` |
| due work, oldest due wait > threshold (900 s) | `backlog_stalled` — a genuine old backlog **stays visibly stalled** |
| due work within threshold | `backlog_within_threshold` |
| nothing due, a live lease | `processing` |
| only future retries | `waiting_for_retry` (not a stall) |
| breakdown unavailable | previous received-age rule, labelled `classification: received_age` |
| tables unreadable | `not_available` (null, never 0) |

### 5.2 Outbound delivery state

`entry.outbound_processing`: `idle`, **`queued_no_sender`** (rows waiting because no sender may
deliver them — not a stall), `backlog_within_threshold`, `backlog_stalled`, `waiting_for_retry`,
`not_available`; plus `sender_configured`, `sender_reason`, `relay_heartbeat_observed` (always
false from the API process — stated, not faked).

### 5.3 "Not ready" broken down

`readiness.production_readiness.blocked_by`: `vendor_specification`, `business_approval`,
`dba_approval`, `infrastructure`, `certification_not_reported`, `switched_off` (mapping in
`observability.BLOCKER_CATEGORY`). Production readiness still cannot become `ready` while any
reason exists.

### 5.4 Outbound relay

* `claim_outbox(protocols=…)` (memory + SQL); `OutboxRelay.run_once` passes its sender keys, so
  rows of protocols nobody can deliver stay **PENDING** instead of being dead-lettered.
  **Changed contract:** `test_exchange.test_relay_without_sender_dead_letters` asserted the old
  behaviour; it is now `test_relay_without_sender_leaves_rows_pending`. The new behaviour is the
  one `service.py` always documented ("outbox rows then wait (PENDING) instead of being
  dead-lettered").
* Outbox `DEAD_LETTER` writes an `outbox.dead_letter` audit row in the same transaction
  (identifiers and error code only, never the body).
* `service.build_outbound_senders(rt)` registers `HtngSoapSender` only when
  `INTEGRATION_HTNG_OUTBOUND_ENDPOINT_URL` is set (https enforced by settings and `SoapEndpoint`)
  **and** the HTNG adapter is not BLOCKED; otherwise it returns an explicit note. `main()` starts
  an `OutboxRelay` only if a sender exists. Delivery semantics reused unchanged from
  `SoapTransport`: timeout / connect error / 5xx / Server fault → transient (retry with
  exponential back-off, full jitter in the service); 4xx / Client fault → permanent; one lease
  per attempt with fencing; `X-Correlation-ID` sent for receiver-side de-duplication.

### 5.5 Corrupt stored rows

* `claim()`: a row that cannot be mapped (unknown protocol / direction) is moved to
  `DEAD_LETTER` with `last_error_code = invalid_stored_record`, category `validation`, and a
  `message.quarantined` audit row containing the stored values. Nothing is deleted; the rest of
  the batch is claimed. (This deliberately bypasses the PENDING→DEAD_LETTER lifecycle rule for a
  row the lifecycle cannot interpret; it is redrivable once fixed.)
* `get`, `list_messages`, `search_messages` (dashboard) and the redrive response use a tolerant
  read-only mapping, so one bad row no longer turns a listing into HTTP 500.

### 5.6 FIAS link lifecycle

`transport/link_runtime.LinkSupervisor` runs one `TcpLink` (client) or `TcpListenerLink`
(server) and its `LinkPump` on a dedicated event loop thread: `start()`, `stop()` (pump first so
no new frame is taken, then sockets / listener closed, bounded join), `health()`.
`build_fias_link_supervisor(rt)` (used by `service.main()` when
`INTEGRATION_FIAS_LINK_ENABLED=true`) authenticates the configured integration client once and
**refuses** with `LinkNotStartable` naming the missing decision:

1. FIAS adapter not READY → "a verified FIAS specification is required (HF-11)";
2. no verified framing → "No verified FIAS framing / link rules (HF-06)"
   (`VERIFIED_FIAS_FRAMER_FACTORY = None`).

The service then exits with code 4 instead of silently running without the link. No ACK, NAK,
heartbeat, handshake, sequence or resynchronisation is implemented — none is specified.

### 5.7 Settings added (all default OFF / None)

`INTEGRATION_HTNG_OUTBOUND_ENDPOINT_URL` (https only), `_HTNG_OUTBOUND_SOAP_VERSION` (1.1 / 1.2),
`_HTNG_OUTBOUND_TIMEOUT_SECONDS`; `INTEGRATION_FIAS_LINK_ENABLED` (requires `INTEGRATION_ENABLED`),
`_FIAS_LINK_MODE` (client / listener), `_FIAS_LINK_HOST` (client), `_FIAS_LINK_PORT`,
`_FIAS_LINK_ALLOWED_PEERS` (listener, mandatory), `_FIAS_LINK_CLIENT_CODE` / `_SECRET`.

## 6. Architecture changes

* The API's processing status is now a function of **due** work, not received age.
* Inbound processing and outbound delivery are reported separately.
* The integration service can own an outbound relay and a FIAS link; both are gated on approved
  contracts and both are off by default. Ownership of a FIAS link by one process (HF-25/26) is
  preserved: the link lives in the service, not in the API.
* No new table, column or dependency.

## 7. Test cases executed

| Suite | Environment | Result |
|---|---|---|
| Backend `tests/integrations` **baseline** (before any change) | disposable MySQL 8.4 (`acx-int-mysql`) via `acx-int-py`; app DB host defaults to the container's localhost, so the real HMS DB is unreachable | **516 passed, 1 skipped** |
| Backend `tests/integrations` after changes (first full run) | same | 562 passed, **1 failed** (`test_relay_without_sender_dead_letters` — the intentionally changed contract, §5.4), 3 skipped |
| Backend `tests/integrations` **final** | same | **563 passed, 3 skipped, 0 failed** (§7.1) |
| New `test_operational_completion.py` | memory + MySQL | **47 passed, 2 skipped** (SQL-only corruption tests skip on the memory variant) |
| Affected existing suites (observability, repository contract, service, end-to-end, health view, API) mid-way | MySQL | 104 passed |
| Frontend `node --test` | frontend container | **59 / 59** (baseline 54 + 5 new) |
| `tsc -p tsconfig.app.json --noEmit` | frontend container | 6 errors — the same pre-existing 6, none in Integrations |
| `eslint .` | frontend container | 3 errors, 7 warnings — identical to baseline, none in Integrations |
| `vite build` | frontend container | success |
| `ruff check --select E,F,W,B,S --ignore S101,S105,S106,S311,E501 app/integrations tests/integrations/test_operational_completion.py` | `acx-int-py` | all checks passed |
| API E2E (real backend, demo stack, synthetic DB) | `acx-demo-*`, internal network | §9 |
| Browser E2E (headless Edge 157, demo stack, new build) | only `127.0.0.1:4320` reachable | §9 |
| Real service process recovery | disposable `acx_integration_test` | §10 |

New test coverage (`test_operational_completion.py`): empty → idle; fresh pending within
threshold / old pending stalled; future retry → `waiting_for_retry`, then stalled once overdue;
live lease → `processing`, abandoned lease → stalled; ordering-blocked count; worker crash and
lease-expiry recovery with status transitions (FIAS record through the real gateway); outbound
`queued_no_sender`; configured sender reports a real backlog; production HTNG adapter never gets
a sender; no endpoint → explicit note; relay claims only deliverable protocols; outbox dead
letter audited; HTNG outbound to a local mock SOAP receiver — success (SOAPAction and
correlation header verified), 5xx retry then replay success, timeout transient, Client fault
dead-lettered and audited, retry exhaustion; corrupt row quarantined without losing the batch
and audited; dashboard search tolerant of a corrupt row; six unsafe-settings cases refused;
defaults off; production FIAS link refused for BLOCKED (HF-11) and TEST_ONLY adapters and for
missing framing (HF-06); disabled link never built; `LinkSupervisor` client mode — complete and
partial frames, connection loss and automatic reconnect, graceful stop; listener mode —
non-allow-listed peer refused with nothing stored, allowed peer with two frames in one write,
clean stop.

Already covered by the existing suite (re-run, passing): SOAP 1.1 / 1.2, malformed XML, XXE,
size limits, wrong credentials, duplicates, invalid facility, schema missing (BLOCKED), worker
processing, DB outage during intake (transient, FIAS frame retried not dropped), retry / DLQ,
redrive audit, idempotency races, per-stay ordering, lease fencing, facility isolation, RBAC,
no PII / credential leakage.

### 7.1 Final full backend run

```text
SKIPPED [2] tests/integrations/test_operational_completion.py:373: stored-row corruption only exists in the SQL store
SKIPPED [1] tests/integrations/test_vendor_contracts.py:33: No official vendor samples supplied (HF-07 HTNG WSDL/XSD, HF-11 FIAS manual).
563 passed, 3 skipped in 1518.45s (0:25:18)
```

516 baseline + 47 new = 563 (the one changed test is counted in both).

**Run time.** The baseline full run took 482 s; the runs after the change took ~1 460–1 520 s.
This was checked rather than assumed: the same four heavy files (`test_repository_contract`,
`test_observability`, `test_hardening`, `test_api`; 91 tests) were run back-to-back in the same
container against a copy of the **pre-change** code and against the **new** code: **237.34 s vs
237.52 s**. The slowdown is environmental (the disposable MySQL was slower later in the day,
including after a Docker restart that interrupted one run), not a regression from this change.

## 8. Before / after dashboard status (demo stack, synthetic data, no worker running)

| Field | Before (old code) | After (new code) |
|---|---|---|
| HTNG processing | Backlog stalled (oldest *unfinished* 63 819 s — included 3 future retries and 2 live leases) | **Backlog stalled** — 3 due now, oldest due wait 19 h 25 m; 3 retries scheduled later, 2 being processed are no longer counted as stall |
| FIAS processing | Backlog stalled (101 559 s) | **Backlog stalled** — 2 due now, oldest 1 d 6 h; 2 scheduled, 1 being processed |
| HTNG / FIAS outbound | not shown (2 / 1 outbox rows silently PENDING) | **Queued · no sender** — "No outbound vendor endpoint is configured (HF-24)" / FIAS link needed (HF-06, HF-11) |
| Production readiness | Not ready | Not ready · **Blocked by:** Vendor specification · Business approval · DBA approval · Test results not published · Switched off |
| Connection | HTNG Disabled · FIAS Not observable | unchanged (correct) |
| Vendor validation | Pending | unchanged (correct) |

The demo's stall is **genuine**: those messages are due and no worker is running. The dashboard
must keep showing it. §10 shows it clearing when the real service runs.

## 9. Full-stack evidence

* API (demo API restarted onto the new code; read as the synthetic `e2e.operator`):
  `processing` and `outbound_processing` exactly as in §8; messages (7-day) 38, DLQ 5 —
  unchanged counts, nothing reset.
* Browser (headless Edge, sign-in through the real login page, new production build):
  Overview shows two "Blocked by" lists and the true statuses; HTNG and FIAS pages show
  `Due now / Oldest due wait / Retries scheduled later / Being processed / Worker activity = Not
  currently observable / Outbound delivery = Queued · no sender / Vendor delivery = Not
  configured / Queued outbound`; no horizontal overflow at 1440×900 or 390×844; no `ready` badge.
  Screenshots: `scratchpad\op\shots\after-*.png` (session scratchpad, not committed).

## 10. Worker and backlog recovery evidence (real service process)

Disposable DB `acx_integration_test` on `acx-int-mysql` (connected `DATABASE()` and `@@hostname`
printed and checked by the script before any write). Seeded: 4 `stay.check_in` messages received
2 h ago (2 HTNG, 2 FIAS), 1 FIAS message in `RETRY_WAIT` until tomorrow, 1 HTNG outbox row.

| | HTNG | FIAS |
|---|---|---|
| Before | `backlog_stalled`, due 2, oldest due 7 260 s, inbound {PENDING 2}, outbound `queued_no_sender` | `backlog_stalled`, due 2, scheduled 1, oldest due 7 380 s, inbound {PENDING 2, RETRY_WAIT 1} |
| Run | `INTEGRATION_ENABLED=true python -m app.integrations.service` (started, logged both outbound notes, claimed the due messages; each failed with `approval_required` because the live-write gate is closed → `DEAD_LETTER (non_retryable:approval_blocked)`); stopped with SIGTERM | |
| After | **`idle`**, inbound {DEAD_LETTER 2}, outbound `queued_no_sender` (1) | **`waiting_for_retry`**, inbound {DEAD_LETTER 2, RETRY_WAIT 1} — the scheduled retry was not touched |

So the stall clears as soon as a worker runs. Today every processed `stay.check_in` necessarily
ends in the DLQ with `approval_required` (live HMS writes are not approved — HF-01, 02, 05, 19,
18); that is the correct, explicit outcome, and those messages remain redrivable. A first attempt
with an 8-second window showed no processing: start-up takes ≈5 s (import 4.6 s) — a test-window
issue, not a defect.

Also verified with the real entry point: `INTEGRATION_FIAS_LINK_ENABLED=true` → "integration
service not started: FIAS link not startable: FIAS adapter is not READY (blocked); a verified
FIAS specification is required (HF-11)", exit 4; switched off → exit 3.

## 11. HTNG inbound / outbound evidence

Inbound: existing suite (SOAP 1.1 / 1.2, faults in the request version, 401 / 413 / 415 / 429,
safe XML, duplicates, facility mapping, DB outage → 503) re-run and passing. Outbound: §7 mock
receiver tests (HTTP on 127.0.0.1 only, `allow_insecure_loopback=True` in tests; production
settings accept https only). The production HTNG adapter remains BLOCKED, so no production
outbound sender is registered.

## 12. FIAS TCP lifecycle evidence

`LinkSupervisor` client and listener tests (§7) plus the existing transport suites
(`test_transport_tcp.py`, `test_transport_server.py`, `test_end_to_end.py`: partial frames,
multiple frames per read, invalid / oversized frames, read timeouts, reconnect back-off, intake
retry of the same frame during a DB outage, unprocessed frames not acknowledged on stop). All
with the PROVISIONAL TEST framing (0x02 / 0x03) and record set — never presented as FIAS.

## 13. Security and facility isolation

Re-run and passing: per-user facility scope on every observability query, 403 for out-of-scope
filters, RBAC (`facility_management` read / write), no payload / secret / client code / hash in
responses, audit integrity. New: outbound endpoints https-only; FIAS listener requires an
allow-list (tested); FIAS link authenticated as a configured integration client; audit rows carry
identifiers and codes only. The live-write gate was never opened.

## 14. Remaining vendor blockers

HF-03 (vendor / product), HF-04 (protocol), HF-07 (HTNG profile / WSDL / XSD), HF-08 (HTNG
security), HF-11 (FIAS specification), HF-06 (FIAS link rules: framing, ACK / NAK, heartbeat,
listening side), HF-05 (property-code case), HF-09 (vendor test environment), HF-24 (network /
TLS / vendor endpoint), BLK-V7 (volumes). Production capabilities blocked by them:

| Capability | Blocked by |
|---|---|
| HTNG inbound in production | HF-07, HF-08 (adapter BLOCKED), switches |
| HTNG outbound delivery | HF-07, HF-08, HF-24 |
| FIAS link start | HF-11, HF-06 (and HF-25/26 hosting) |
| FIAS ACK / NAK / heartbeat | HF-06 |
| Vendor validation | all of the above + HF-09 |

## 15. Remaining business / DBA approvals

Business: HF-01, HF-02, HF-19 (live-write gate), HF-18 (integration actor), HF-21 (retention /
encryption), HF-27 (final retry / ordering policy). DBA: HF-39.

**Proposals prepared, NOT applied (require HF-39):**

```sql
-- PROPOSED: reject invalid values at the database (finding: corrupt direction / protocol rows)
ALTER TABLE integration_inbound_messages
  ADD CONSTRAINT ck_integration_inbound_messages_direction_valid CHECK (direction IN ('inbound','outbound')),
  ADD CONSTRAINT ck_integration_inbound_messages_protocol_valid  CHECK (protocol  IN ('htng','fias'));
ALTER TABLE integration_outbox_messages
  ADD CONSTRAINT ck_integration_outbox_messages_protocol_valid   CHECK (protocol  IN ('htng','fias'));

-- PROPOSED: durable component heartbeats so the dashboard can observe the worker, relay and
-- FIAS link across processes (today "Not currently observable" by design)
CREATE TABLE integration_component_heartbeats (
  component   VARCHAR(64)  NOT NULL PRIMARY KEY,   -- inbound_worker | outbox_relay | fias_link:<name>
  host_label  VARCHAR(96)  NULL,
  state       VARCHAR(32)  NULL,                   -- link state where relevant
  last_seen   DATETIME(6)  NOT NULL,
  detail      JSON         NULL                    -- counters only, no payloads
) ENGINE=InnoDB;
```

(The `test` protocol used by the test suite would need adding to the CHECK list or the tests
adjusting; that is part of the DBA review.)

## 16. Production deployment prerequisites

1. HF-39 approved; integration tables (and the proposals above, if accepted) migrated by the DBA.
2. Vendor named and contracts received (§14); verified profile / specification / framing
   registered in code with evidence.
3. Approvals recorded **in code** with evidence (`domain/approvals.py`); `INTEGRATION_ACTOR_USER_ID`.
4. Network path and TLS (HF-24); vendor endpoint configured (https).
5. Hosting and restart policy for the integration service and the FIAS link (HF-25/26).
6. Retention / encryption values (HF-21); rate limit from vendor volumes (BLK-V7).
7. Vendor validation executed and recorded; then switches enabled per environment, one property
   at a time.

## 17. Rollback procedure

All changes are additive or behind switches that default off:

* Frontend: the new fields are optional; reverting the five frontend files restores the previous
  display. The backend change does not require the frontend change.
* Backend: revert the files in §4 (backups of the pre-change trees were taken for this sprint).
  No data migration is involved; no stored row format changed. Rows quarantined by §5.5 (if any
  existed) remain DEAD_LETTER with code `invalid_stored_record` and an audit row; they can be
  redriven after correction.
* Operationally: leaving `INTEGRATION_HTNG_OUTBOUND_ENDPOINT_URL` unset and
  `INTEGRATION_FIAS_LINK_ENABLED=false` (the defaults) disables both new paths entirely.

## 18. Git diff summary

```text
Modified (pre-existing untracked feature tree, so `git status` lists the folders, not the files):
  backend/app/integrations/{config.py, observability.py, service.py,
    processing/activity.py, processing/repository.py, processing/sql_repository.py, processing/worker.py}
  backend/tests/integrations/test_exchange.py
  frontend/src/lib/api/integrations.ts
  frontend/src/features/integrations/{lib/presentation.ts, views/OverviewView.tsx, views/ProtocolView.tsx,
    __tests__/integrations.test.cjs, __tests__/observability-fixtures.json}
Added:
  backend/app/integrations/transport/link_runtime.py
  backend/tests/integrations/test_operational_completion.py
  docs/HTNG_FIAS_OPERATIONAL_COMPLETION_REPORT.md
Unchanged (checksum-verified): docker-compose.dev.yml, backend/app/api/v1/router.py
Not staged, not committed, not pushed. HEAD 46904fd.
```

`git status` compared with the start of the sprint: the only new entry from this work is this
report (the code changes are inside folders that were already untracked). Four other new files
appeared in `docs/` during the sprint that this work did not create
(`HFTP_HTNG_FIAS_INTEGRATION_ANALYSIS.html/.pdf`, `HTNG_FIAS_TEAM_CLIENT_EXPLANATION_TANGLISH.html/.pdf`);
they were left untouched.

**Temporary test infrastructure.** The mock SOAP receivers and TCP simulators live inside the
tests and stop with them. Scratch scripts copied into `acx-int-py` were deleted. The disposable
containers (`acx-int-*`) were stopped afterwards. The demo stack (`acx-demo-*`) — which the
project owner had asked to run earlier — was stopped by a Docker restart during the sprint; its
web build was updated to the new frontend (previous build kept beside it as
`dist.pre-operational` in the session scratchpad), and two read-only helper scripts remain in the
stopped `acx-demo-api` container's `/tmp` (they read the demo password at run time and contain
no secret).

## Final status

| Area | Status |
|---|---|
| Internally controllable defects found in this audit (false stall, corrupt-row stall / 500, outbound dead-lettering, relay / sender wiring, FIAS link lifecycle, status granularity) | **INTERNAL IMPLEMENTATION COMPLETE** (with regression tests) |
| Cross-process worker / relay / FIAS-link visibility; DB-level value constraints | **BLOCKED BY DBA APPROVAL** (proposals in §15) |
| HTNG production inbound / outbound, FIAS production link, ACK / NAK / heartbeat | **BLOCKED BY EXTERNAL SPECIFICATION** |
| Live HMS writes (every processed message currently ends in the DLQ with `approval_required`) | **BLOCKED BY BUSINESS APPROVAL** |
| Vendor certification | **VENDOR VALIDATION PENDING** |

**FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDING.** No production readiness is claimed.
