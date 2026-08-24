# PHASE 2.4 — HMS WEB AUTHENTICATION & RBAC

**Date:** 2026-08-17 · **Alembic:** `0e2687233b59` (unchanged) · **Tests:** 417

Sources of truth: the PostgreSQL schema, the seeded data, and the IKANOS KT
Handbook. Where they disagree, the disagreement is reported below — nothing was
reconciled by changing the database.

---

## 1. THE HEADLINE LIMITATION — no account can log in

> **Authentication credential source is not present in the approved seed data.**

`app_user.password_hash` **exists** as a column (`VARCHAR(100)`), so the *schema*
supports credentials. The *data* does not:

| password_hash value | accounts |
|---|---:|
| `!seed-no-login` | 12 |
| `NULL` | 1 |
| **usable bcrypt digest** | **0** |

`!seed-no-login` is the sentinel the Phase 1.8 seed wrote deliberately — that
phase asserted "the seed must never write a usable credential". It is not a
valid bcrypt digest and cannot be produced by any hashing scheme.

**Consequence:** `POST /api/v1/auth/login` returns **401 for every seeded
account**. This is correct behaviour against the real data, not a defect.

**What was NOT done to work around it:** no password column added, no schema
change, no fake password, no hardcoded credential, no seed-data edit.

**To enable login** (an operational step, outside this phase):

```python
from app.core.security import hash_password
# UPDATE app_user SET password_hash = :h WHERE user_name = 'arjun.menon'
hash_password("<chosen password>")
```

`hash_password()` ships and is tested; the verifier is real bcrypt and starts
working the moment a hash exists.

---

## 2. Platform boundary

Derived from **`role.role_type`** — the database's own constrained ENUM — never
from role display names, which an operator can rename at will.

| DB role (name / role_type) | KT handbook role | Platform | Evidence |
|---|---|---|---|
| Administrator / `admin` | Admin | **HMS Web** | role_type enum |
| Duty Manager / `manager` | Manager | **HMS Web** | role_type enum |
| Front Desk / `staff` | Staff | Mobile | role_type enum |
| Housekeeping / `staff` | Staff | Mobile | role_type enum |
| Technician / `staff` | Technician | Mobile | **name only — see mismatch 1** |
| Guest / `guest` | Guest | Guest mobile | role_type enum |
| System / `system_user` | *(absent from handbook)* | Service account | **mismatch 2** |

`HMS_WEB_ROLE_TYPES = {admin, manager}` (`app/core/platform.py`).

### Handbook ↔ database mismatches

1. **There is no `technician` value in the `role_type` enum.** The seeded
   "Technician" role carries `role_type='staff'`. The boundary still lands
   correctly (Technician → staff → Mobile), but Technician is **not separable
   from other staff at the type level** — only by role name. A future mobile
   phase that needs to distinguish them must match on the role name or add a
   `job_function` check. Asserted by
   `test_technician_is_not_a_role_type_in_the_database`.

2. **`system_user` exists in the database but not in the handbook.** Treated as
   a non-interactive service account and **excluded** from HMS Web login.
   Granting a service account an interactive session is a security decision the
   handbook never authorises.

---

## 3. Authentication fields (actual)

| Purpose | Column | Note |
|---|---|---|
| Login identifier | `app_user.user_name` | 13/13 distinct; the only unique login id |
| Credential | `app_user.password_hash` | present, but see §1 |
| User → role | `user_role(facility_id, app_user_id, role_id)` | **facility-scoped**, 3-col PK |
| Role | `role.role_type` | ENUM: admin, system_user, manager, guest, staff |
| Role → module | `role_module_permission(role_id, module_id)` | composite PK |
| Module registry | `role_module` | 18 rows; **there is no `module` table** |
| Permission | `read_access` / `write_access` | **there is no `permission` table** |

---

## 4. Role → module → permission (seeded)

| Role | modules | writable | has `user_roles`? |
|---|---:|---:|---|
| Administrator | 18 | 18 | yes |
| System | 18 | 18 | yes |
| Duty Manager | 13 | 10 | **no** |
| Front Desk | 6 | 4 | no |
| Technician | 5 | 4 | no |
| Housekeeping | 4 | 2 | no |
| Guest | 1 | 1 | no |

**The database independently corroborates the handbook**: the Duty Manager role
holds `employees` (read+write) but has **no `user_roles` grant** — exactly
"Manager: NO role administration". That rule is enforced by the data, not by a
role-name check in code.

---

## 5. JWT

| Setting | Default | Source |
|---|---|---|
| `JWT_SECRET_KEY` | dev-only placeholder | env / `.env` |
| `JWT_ALGORITHM` | `HS256` | env |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | env |

Added to the existing `Settings` class — no second configuration system.
`settings.assert_production_ready()` **raises** if the shipped development
secret is still in use outside development, so it can never silently sign
production tokens.

**Token payload is `{sub, typ, iat, exp}` and nothing else.** No role, no
permission, no email, no credential. `typ` must be `access`, so a future
refresh token cannot be replayed here.

**Authorization is never read from the token.** `get_current_user` re-loads
roles and permissions from PostgreSQL on every request, so a revoked role takes
effect immediately rather than at token expiry.

---

## 6. RBAC

```python
require_permission("<role_module.module_name>", "read" | "write")
```

`permission` maps to the real columns `read_access` / `write_access`; anything
else raises `ValueError` at import time. Module names are validated against the
live registry by `test_rbac_module_names_are_real_registry_entries`.

### Protected endpoints and their verified module

| Endpoint(s) | Module | Admin | Manager |
|---|---|---|---|
| `/users` | `employees` | 200 | **200** |
| `/roles`, `/modules`, `/permissions` | `user_roles` | 200 | **403** |
| `/facilities`, `/properties`, `/buildings`, `/floors`, `/rooms` | `facility_management` | 200 | **403** |

`/health`, `/api/v1/health/db`, `/docs` and `/auth/login` stay public.

### 401 vs 403

- **401** — no token, malformed token, bad signature, expired, wrong `typ`,
  deleted user, or a user who no longer holds an HMS Web role.
- **403** — authenticated HMS Web user whose roles lack the module grant, or a
  correct credential belonging to a mobile/guest platform role.

---

## 7. Known consequence to decide on

**Duty Manager gets 403 on `/rooms`.** The seeded Duty Manager role has no
`facility_management` grant, and `/rooms` is mapped to that module because room
inventory is configured on the Facility Management screen. But the Occupancy
screen — which *is* a Manager responsibility — also lists rooms.

Two legitimate resolutions, both **out of scope** for this phase because each
is a decision, not a bug:

1. Grant `facility_management` read to the Duty Manager role (a data change), or
2. Expose an occupancy-scoped room endpoint gated on the `occupancy` module,
   which the Manager already holds.

This was **not** resolved by overriding the check in code. The database remains
the source of truth.

---

## 8. Out of scope, deliberately

No `/staff/login`, `/technician/login`, `/guest/login`, `/mobile/login` or
`/auth/register` route exists — asserted by
`test_no_mobile_or_guest_login_routes_exist`.

- **Staff → mobile application phase**
- **Technician → mobile application phase**
- **Guest → separate guest mobile application**

The same backend may later serve mobile authentication, but that is not Phase 2.4.

No refresh tokens, no logout/revocation, no password reset, no rate limiting,
no account lockout, no frontend change.

---

## 9. Testing note

Tokens in tests are minted through the real `create_access_token` for real
seeded users, because no credential exists to log in with. The login *flow*
(including the platform boundary) is exercised by monkeypatching
`verify_password` to simulate a provisioned hash — the database is never
touched, and the credential gap itself is asserted directly by
`test_no_seeded_account_has_a_usable_credential`.
