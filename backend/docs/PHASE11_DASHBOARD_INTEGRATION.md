# Phase 11 — Dashboard & Operational Integration

Phase 11 connects the HMS Web dashboard and operational screens to the real
Phase 1–10 APIs and the real PostgreSQL data. It is a **read integration**: no
write endpoint, model, migration or seed row was added or changed.

Database fingerprint before and after: **93 tables** (92 domain +
`alembic_version`), **34 ENUMs**, **240 FKs**, **352 indexes**, **1,799 rows**.
`alembic check` → *No new upgrade operations detected.*

---

## 1. What the dashboard now reads

Every figure is a backend `total` — the `COUNT(*)` the list endpoint runs for
the same filter its table would use — fetched with `page_size=1`. Nothing is
counted in the browser, and nothing is summed across pages.

| Widget | Endpoint(s) | Module gate |
|---|---|---|
| KPI: Devices, Active, Inactive | `/devices`, `?health_status=` | `caleido_network` |
| KPI: Firmware outdated | `/devices?firmware_outdated=true` | `caleido_network` |
| KPI: Device alerts, critical, warning | `/alerts`, `?alert_severity=` | `caleido_network` |
| KPI: Active value alerts | `/value-alerts?status=0` | `caleido_network` |
| KPI: Incidents, unassigned | `/incidents`, `?unassigned=true` | `caleido_network` |
| KPI: Rooms in house | `/occupancy?is_occupied=true` | `occupancy` |
| KPI: Stays in house | `/stays?is_in_house=true` | `bookings` |
| KPI: Service requests, unassigned | `/service-requests` | `service_tracking` |
| KPI: Energy consumed | `/energy-stats/summary` | `reports` |
| KPI: Activities | `/activities` | `dashboard` |
| Energy chart | `/energy-stats/summary?group_by=` | `reports` |
| Occupancy chart | `/amenity-statuses`, `/occupancy?status=` | `occupancy` |
| Caleido At Work rings | `/daily-data-points` | `reports` |
| Alerts panel | `/alerts`, `/service-requests` | as above |
| Recent Activity panel | `/activities` | `dashboard` |
| Building → floor → room | `/buildings`, `/floors?building_id=`, `/occupancy?floor_id=` | `facility_management`, `occupancy` |
| Room detail | `/occupancy/{id}`, `/devices`, `/device-stats` | `occupancy`, `caleido_network` |

`scripts/verify_dashboard_kpis.py` re-checks every one of these against an
independent SQL `COUNT` and exits non-zero on any mismatch. Against the current
seed all 25 figures match.

---

## 2. KPIs deliberately NOT shown

* **"Open" / "Unresolved" incidents.** `incident_status` holds exactly
  `Unread | Read | Assigned | Resolved` — there is no Open state. `GET
  /incidents` filters `status` by a single `incident_status.id`, and no lookup
  endpoint exposes those ids, so a NOT-Resolved count cannot be requested.
  The tile shows the real total and the real unassigned count. Adding
  `GET /incident-statuses` (or a negated status filter) would make it possible.
* **Trends** ("+12% vs last week"). No endpoint returns a prior-period figure
  and no table stores one. The unused `KPICard` component, whose only
  distinctive prop was such a trend, was deleted.
* **Energy cost, carbon, kWh.** `energy_stat` has no unit column; the API
  returns `energy_unit: null` and the summary performs `SUM` and `COUNT` only.
  The tile is labelled "Energy consumed (no unit)".
* **Per-appliance AC / light / fan state.** Not stored; the tiles stay off.

---

## 3. Two sources of truth for occupancy, reported as two

A room's state is carried both by `amenity.status` and by the stay graph, and
nothing in the schema keeps them in step. Phase 11 reports both and reconciles
neither:

* the occupancy chart's **slices** are `amenity.status` (all four values);
* the **centre figure** and the "Rooms in house" KPI are the stay graph —
  `actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL`, i.e.
  `?is_occupied=true`;
* where the two disagree, the chart says so in a footnote.

In the current data 4 rooms are flagged `Occupied` while 2 have a guest in
house. `test_filter_contract.py` pins `is_occupied` to the stay graph so the
amenity flag can never be silently substituted.

---

## 4. Enum filters: 422, not 503

**The defect.** Fifteen enum-backed query filters were declared `str | None`,
so an unknown value was passed to PostgreSQL, failed on the enum cast, and
returned:

```
503 {"error": {"code": "service_unavailable", "message": "Database is unavailable."}}
```

The database was fine and the request was simply wrong. The dashboard's error
state read "The HMS database is unavailable" for a bad filter value, and a
client would retry a request that can never succeed.

**The fix.** `app/schemas/filters.py` declares one `Literal` per PostgreSQL
enum, copied from `pg_enum`. The affected filters now use them:

| Endpoint | Parameter |
|---|---|
| `/devices` | `health_status`, `device_config_status` |
| `/firmware` | `status` |
| `/alerts` | `alert_severity` |
| `/stays` | `status`, `request_source`, `document_approval_status` |
| `/occupancy`, `/rooms` | `amenity_category` |
| `/notifications` | `status`, `template_type` |
| `/notification-templates` | `type` |
| `/daily-data-points` | `metric_type` |
| `/device-params` | `data_type` |
| `/service-requests` | `request_source` |
| `/roles` | `role_type` |

FastAPI now rejects an unknown value before any query runs, naming the
permitted labels in both the 422 body and the OpenAPI document — which is what
lets the frontend derive its filter controls from the contract. A `DataError`
handler in `app/api/errors.py` is the backstop for any filter still declared as
plain text.

No schema change: these are the labels the columns already hold.

---

## 5. Fabricated values removed from the frontend

| Screen | Was | Now |
|---|---|---|
| Dashboard status tiles | room health guessed from `room.type.includes('Error')` | real `amenity_status` (four values) |
| Dashboard "Good Health / Warnings / Error" legend | static text; no such device states exist | real `Active` / `Inactive` counts from `/devices` |
| Dashboard "Affected Rooms" checkbox | inert | filters rooms with ≥1 active `amenity_condition` |
| Job Order pickers | hardcoded "Room 101–301"; device types "Tab", "Gateway" | `/rooms`, `/device-types` |
| Offers "Applicable Rooms" | hardcoded package names ("Delux Package") | real amenities from `/rooms` |
| Facility Management highlights | keyed on names no row holds | plain real values |
| Device Management severity badge | compared to `"Critical"`; never matched | `"critical"` |
| Room Details config badge | compared to `"Commissioned"`; never matched | `"commissioned"` |
| Power/Energy View room status | four DB values folded into three local ones, hiding `Allotted` | all four, as stored |

The last three were latent bugs that the tightened TypeScript unions in
`lib/api/types.ts` surfaced: `frontend/src/lib/api/types.ts` now mirrors the
`Literal` types above, so a case-mismatched comparison is a compile error.

---

## 6. Pre-existing seed drift — NEEDS SIGN-OFF

**This predates Phase 11 and Phase 11 did not change it.** The live
`hms_db` has drifted from the Phase 1.8 seed, and the backend suite has 7
failures both before and after this phase (1,043 → 1,117 passing as new tests
were added; the same 7 fail):

1. **5 extra `app_user` rows** created through the Phase 3.0 write endpoints
   and never removed. Four share the email `ramanaofficial2005@gmail.com` with
   a `NULL` username; one is `ask@inspironics.net` and carries a **real bcrypt
   password hash**. This breaks
   `test_no_seeded_account_has_a_usable_credential` (18 accounts, 13 expected)
   and `test_seed_used_synthetic_identities_only` (demo emails must use the
   reserved `.invalid` TLD). Real personal and corporate addresses in a demo
   database are a data-hygiene question, not just a failing test.
2. **`STY-2026-0001` was checked out** via the write API on 2026-08-17
   19:44, so its status is `checked out` rather than the seeded `active`, and
   its room reverted to `Available`. This breaks four tests across
   `test_facility_api`, `test_occupancy_api`, `test_seed_data` and
   `test_stay_write_api`, and is the cause of the 4-flagged-Occupied vs
   2-in-house divergence above.

Restoring the baseline means re-seeding, which destroys the write-endpoint
evidence, so **it was not done**: replacing seeded data is out of Phase 11's
remit and needs an explicit decision.

`alembic check` is clean and the schema fingerprint is untouched — the drift is
row data only.

---

## 7. Other limitations

* **No frontend test framework.** The Vite project has no vitest/jest and no
  testing-library; adding one is an architecture change Phase 11 did not make.
  Verification is instead `scripts/verify_dashboard_kpis.py` (API vs SQL),
  `tests/test_filter_contract.py`, `tsc --noEmit`, `eslint` and `vite build`.
* **Login cannot be exercised with seeded users.** Every seeded
  `app_user.password_hash` is the `!seed-no-login` sentinel, so `POST
  /auth/login` cannot succeed for any of them. Tokens for verification are
  minted through the token service, exactly as `tests/conftest.py` does. Only
  the drifted `ask@inspironics.net` row could log in, and its password is
  unknown.
* **Job Order and Service Planning remain unconnected.** `job_order`,
  `maintenance_request` and `scheduler_job` hold real rows but no endpoint
  exposes them; both screens show `NoEndpointNotice` rather than sample data.
  Their form *pickers* are now real.
* **The Add Offer dialog's write path is broken** (pre-existing): its inputs
  bind to local state while submit reads `offerForm`, so the button stays
  disabled. Phase 11 repaired only the room picker, since write operations are
  out of scope.
* **One page of rooms per floor.** `MAX_PAGE_SIZE` is 100; a floor with more
  rooms than that shows a count of what is displayed versus the real total
  rather than silently truncating.
