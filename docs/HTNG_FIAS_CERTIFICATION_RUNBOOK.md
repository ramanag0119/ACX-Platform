# HTNG / FIAS — Certification Runbook

All commands run from `backend/`, in a development or CI environment with disposable
databases. Never point any variable below at the HMS database.

| Variable | Purpose |
|---|---|
| `INTEGRATION_TEST_MYSQL_URL` | disposable MySQL for persistence tests (not needed by the harness itself) |
| `INTEGRATION_TEST_HMS_DB_URL` | disposable MySQL that the harness builds and seeds with the HMS schema; without it HMS scenarios are NOT RUN |

## Commands

```sh
python -m tests.integrations.certification list
python -m tests.integrations.certification run --json run.json --md run.md --label nightly
python -m tests.integrations.certification run --id FIAS-SYN-011 --id HTNG-SYN-002
python -m tests.integrations.certification replay-vendor tests/integrations/vendor_contracts --json replay.json
python -m tests.integrations.certification compare previous.json run.json
pytest tests/integrations/test_certification_harness.py -q
```

Exit codes: `run` 0 = no FAIL (BLOCKED / NOT RUN are reported, never counted as PASS), 1 =
at least one FAIL, 2 = unknown scenario id; `compare` 1 = regression (a PASS became non-PASS).

## Reading a report

* **PASS** — engineering behaviour verified with synthetic input. Not vendor evidence.
* **FAIL** — investigate before merging; evidence has codes, statuses and the reason.
* **BLOCKED** — waiting for vendor material or an approval; the reason names the HF ID.
* **NOT RUN** — environment missing (e.g. no `INTEGRATION_TEST_HMS_DB_URL`).

## When official vendor material arrives

1. Record receipt in the vendor tracker (`HTNG_FIAS_VENDOR_REQUEST_PACKAGE.md` Part E).
2. Confirm HF-21 handling for any sample containing guest data; until approved, only
   `synthetic-by-vendor` or `anonymised` samples may be used.
3. Place samples **outside the repository** or as approved by the owner (`.gitignore` is not
   changed by this harness), with a `manifest.json` carrying full provenance.
4. Encode the verified specification/profile (`VERIFIED_OFFICIAL`) in the adapters.
5. `replay-vendor`; then replace the `*-OFF-*` placeholders with real scenarios driven by the
   samples. Only then can those scenarios report PASS.
