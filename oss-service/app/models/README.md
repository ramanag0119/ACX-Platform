# OSS models — discovery gate

The OSS database is **externally owned** and its schema **differs** from the HMS
device tables, so models are not written here until **step 1 — OSS schema
discovery** is done.

## Why there are no hand-written models yet
Writing models before the real schema is known would be guessing. Instead:

1. Set `OSS_DATABASE_URL` in `oss-service/.env` (never commit it).
2. Run the read-only discovery (see `reflect.py`) **only after the DB owner
   authorises access to `192.168.x.120`**.
3. Record the mapping: OSS table/column → HMS contract field (the fields in
   `app/schemas/device.py`, `telemetry.py`, `alert.py`, `energy.py`).
4. Implement the adapters in `app/adapters/*` against the reflected models.

Until then every adapter raises `AdapterNotMapped`, which the API returns as a
clear 503 — never fabricated data.
