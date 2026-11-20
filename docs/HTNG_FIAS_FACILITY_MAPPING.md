# HTNG / FIAS — Facility Mapping and HMS Domain Integration

## 1. External property → HMS facility

Implemented in `backend/app/integrations/security/facility.py` (+ `sql_stores.py`).

| Rule | Implementation |
|---|---|
| Mapping is owned by one integration client | `FacilityMapping(client_id, external_property_code, facility_id, enabled)`; lookups always filter by the authenticated client |
| No global uniqueness assumed | same code may map to different facilities for different clients (tested) |
| Uniqueness per client | DB unique (`client_id`, `normalized_property_code`) |
| Missing / ambiguous / disabled | rejected: `property_not_mapped`, `property_mapping_ambiguous`, `property_mapping_disabled` |
| Case sensitivity | `CaseSensitivity.EXACT` default; `INSENSITIVE` available once **HF-05** is approved. Changing policy requires re-normalising stored rows |
| Code format | printable ASCII, 1–32 chars, no spaces |
| Payload facility ids | never trusted; must match the resolved facility at any depth |
| Audit of mapping changes | **implemented (round 2)**: `admin.IntegrationAdmin` + `POST/PATCH /api/v1/integrations/mappings` — facility-scoped, created disabled, enable/disable requires a reason, audit row in the same transaction (`test_admin.py`). Who owns the mapping data is still HF-02 |

`facility_uid` (3 chars) on `facility` was **not** used as the external code: whether a
PMS property code equals an HMS facility uid is an ownership decision (HF-02 / HF-31).

## 2. HMS services inspected

| Service | Relevant functions | Used by integration |
|---|---|---|
| `app/services/stays_write.py` | `create_stay`, `check_in`, `check_out`, `extend_stay`, `cancel_stay`, `allocate_room`, `update_room_state`, `set_room_conditions` | `check_in`, `check_out` via `StayDomainAdapter` |
| `app/services/facility_write.py` | facility / room catalogue | no |
| `app/services/maintenance_write.py` | maintenance requests | no |
| `app/services/access_write.py` | users / roles | no |
| `app/services/services_write.py` | service requests | no |

Facts that shaped the adapter: `stay` has no `facility_id` (scope via
`room_allocation → amenity.facility_id`); guests are `app_user` rows with
`phone_number NOT NULL`; `stay.external_stay_ref_number` exists but is not unique.

## 3. `StayDomainAdapter` (`domain/stays.py`)

Order: validate body → `LiveWriteGate` → HMS actor (HF-18) → external reference
resolver (HF-02) → facility ownership of every allocated room → call
`stays_write.check_in/check_out` on the fenced session. HMS `WriteError`s become
`permanent` `hms_business_rule`; unknown stay → `transient` (the PMS may be ahead of HMS).

**Live writes are disabled.** `LiveWriteGate` needs `INTEGRATION_LIVE_DOMAIN_WRITES=true`
AND HF-01, HF-02, HF-05, HF-19 recorded as Approved *with evidence* in
`domain/approvals.py` (a code change). No resolver and no actor are configured in the
production runtime. Tests exercise the open path only with a TEST-ONLY register and a
mocked service.

## 4. Not mapped (needs decisions / vendor specs)

Reservation creation/modification (HF-38), guest profile and PII (HF-20), room status
and housekeeping vocabulary (HF-37), folio/postings (HF-40), keys and
devices (HF-14/15). Each needs a verified vendor message and an ownership decision.
