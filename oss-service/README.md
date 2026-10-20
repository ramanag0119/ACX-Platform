# HMS OSS (device/operations) microservice

Serves the **device / telemetry / alert / energy** read surface from the
existing, externally-owned **OSS PostgreSQL**, mapping its (differently-shaped)
rows into the exact API contract the HMS frontend already consumes. HMS stays
the single entry point and forwards OSS-surfaced requests here.

```
frontend ──▶ HMS :8000  ──(OSS path? auth+RBAC first)──▶  OSS service :8001  ──▶  OSS PostgreSQL
                └── BSS paths handled locally against hms_db ──┘
```

See [`docs/DESIGN_AND_READINESS.md`](docs/DESIGN_AND_READINESS.md) for the
security model, write-path design, compatibility checks, rollback and
production-readiness criteria.

## Boundary
- **This service (OSS):** `/device-types`, `/devices`, `/device-params`,
  `/device-stats`, `/device-current-stats`, `/other-device-readings`,
  `/alert-types`, `/alerts`, `/incidents`, `/value-alerts`, `/energy-stats`.
- **Stays in HMS (BSS):** everything else, incl. `/daily-data-points` (mixed KPIs).

## Run (local)
```bash
cd oss-service
python -m venv .venv && . .venv/Scripts/activate      # or reuse ../backend/.venv
pip install -r requirements.txt
cp .env.example .env            # then set OSS_DATABASE_URL (never commit .env)

PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
#  → http://127.0.0.1:8001/docs   /health   /health/db
```
Then enable dispatch on HMS by setting in `backend/.env`:
```
OSS_ENABLED=true
OSS_SERVICE_URL=http://127.0.0.1:8001
# optional equivalent control (set the SAME value on both sides):
# OSS_SERVICE_TOKEN=<shared-secret>
```

## State of the data layer
Until `OSS_DATABASE_URL` is set, the service runs and serves `/health`, but data
routes return a clean **503** (`oss_not_configured`). Until the OSS schema is
mapped (step 1, `tools/discover_schema.py`), adapters return **503**
(`oss_adapter_not_mapped`). Neither ever returns fabricated data.

## Tests
```bash
cd oss-service
PYTHONPATH=. python -m pytest -q      # scaffold tests, no OSS DB needed
```

## Layout
```
app/
  main.py            app factory (health ungated; data routes token-guarded)
  core/config.py     env config (OSS_DATABASE_URL, OSS_SERVICE_TOKEN, ...)
  db/session.py      lazy engine (OssDbNotConfigured until configured)
  api/               health + device/telemetry/alert/energy routers + errors + security
  schemas/           verbatim copies of the HMS contract (byte-identical JSON)
  adapters/          OSS row -> contract mapping (AdapterNotMapped until step 1)
  models/            reflection helpers; hand models written after discovery
tools/               discover_schema.py (read-only) + SCHEMA_MAPPING_TEMPLATE.md
```
