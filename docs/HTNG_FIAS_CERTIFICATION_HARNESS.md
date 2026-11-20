# HTNG / FIAS — Integration Certification Harness

**What it is:** a test-only engineering layer that validates the HTNG and FIAS integration
paths without a PMS vendor. **What it is not:** vendor certification. Official-contract
scenarios are BLOCKED until vendor documents and samples exist (HF-06, HF-07, HF-08, HF-11).

Location: `backend/tests/integrations/certification/` — under `tests/` on purpose: never
imported by the application, no production API, CLI and pytest only.

## 1. Existing capability audit (Phase 1)

| Capability | Existing implementation | Missing capability | Reuse strategy |
|---|---|---|---|
| HTNG "simulator" | `test_api.env_impl` (real app + inbound endpoint + in-memory engine), generic XML profile in `simulators/fixtures.py` | named, repeatable scenarios; evidence | reuse `env_impl` per scenario |
| FIAS simulator | `simulators/fias_simulator.FiasTestSimulator` (loopback, opt-in) | scenario-driven failure injection | reuse as-is with `TcpLink` + `LinkPump` |
| SOAP adapters / endpoint | `transport/soap.py`, `adapters/htng/`, `api/router.py` | — | used unchanged |
| FIAS framing / parser | `transport/framing.py`, `adapters/fias/` | — | used unchanged (synthetic spec) |
| Contract runner | `app/integrations/contracts.py` | provenance, PII gate, size limits, immutability check | wrapped by `certification/replay.py` |
| Test fixtures | `conftest.build_stack`, `JsonTestAdapter`, `RecordingHandler` | — | reused |
| E2E HMS simulation | `test_e2e_hms_simulation.build`, `test_hms_domain_mysql` helpers (`hms_engine_impl`, `reset_stay`, `stay`) | catalogued HMS scenarios with before/after state | reused |
| Worker / retry / DLQ | `processing/worker.py`, repositories | — | used unchanged |
| Health / operator APIs | `api/router.py` | — | not extended (no certification controls in production APIs) |
| Reports | `contracts.to_markdown` (contract-only) | run reports, comparison | new `certification/report.py` |

No new transport, adapter, gateway, worker or HMS integration was written.

## 2. Architecture

```text
CLI (python -m tests.integrations.certification)  /  pytest (test_certification_harness.py)
        |
  core.py  Scenario registry (deterministic IDs  PROTO-SYN|OFF-NNN)
           Execution engine: requirement check -> run -> PASS/FAIL/BLOCKED/NOT RUN
           Evidence collector (identifiers/outcomes only; secrets refused, PII masked)
        |
  scenarios_htng.py  -> test_api.env_impl -> real endpoint -> gateway -> repo -> worker
  scenarios_fias.py  -> FiasTestSimulator -> TcpLink -> LinkPump -> FIASAdapter -> gateway -> worker
  scenarios_hms.py   -> test_e2e_hms_simulation.build -> gateway -> SQL repo -> worker
                        -> StayDomainAdapter -> app.services.stays_write (disposable seeded MySQL)
  replay.py          -> provenance / PII / size checks -> app.integrations.contracts (production adapters)
  report.py          -> JSON + Markdown reports, run comparison
```

### Status rules

| Status | When |
|---|---|
| PASS | scenario ran and every expectation held |
| FAIL | an expectation failed or the scenario raised |
| BLOCKED | needs vendor material (`requires=vendor`) or raised `Blocked`; **official vendor scenarios are forced to BLOCKED even if they would pass** |
| NOT RUN | a required disposable environment (`mysql`, `hms_db`) is not configured |

### Evidence

Per scenario: correlation id, adapter, input reference, processing result, failure
category/code, HTTP/SOAP response summary, HMS state before/after (status flags only),
audit actions, retry/DLQ outcome, observations, timestamp, duration. Secrets known to the
scenario are checked **before** masking (a match aborts the record); everything is then
passed through `mask_mapping` (guest fields, e-mails, long digit runs). Synthetic stays
`PMS-0001/0003/0004` come from the repository's own seed; no real guest data is used.

## 3. Vendor sample replay

`certification/replay.py` (+ CLI `replay-vendor`): manifest provenance (vendor, product,
protocol, protocol_version, source, received_on, pii_status), ≤ 1 MiB per sample, sample
directory may not be a synthetic-fixture location, files hashed before/after (never
rewritten), `pii_status = contains-guest-data` refused unless HF-21 is Approved (it is not),
results mapped PASS/FAIL only from the production-adapter contract run — which today yields
BLOCKED. No samples exist; `.gitignore` was not changed and no samples were added.

## 4. Safety

Simulator binds loopback only and needs explicit opt-in; HMS scenarios need
`INTEGRATION_TEST_HMS_DB_URL` and refuse the HMS database name; the live-write gate is
opened only by the TEST-ONLY register inside `build()`; production switches untouched.
