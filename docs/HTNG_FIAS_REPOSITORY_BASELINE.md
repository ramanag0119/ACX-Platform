# HTNG / FIAS — Repository Baseline

| Item | Value |
|---|---|
| Captured | 2026-11-19 |
| Repository | `ACX-Platform` (remote `origin` = `github.com/ramanag0119/ACX-Platform`) |
| Method | Read-only inspection, then a disposable Docker test environment. Nothing was pushed; no `.env`, configured database, stash or branch was modified. |

## 1. Git state

| Item | Value |
|---|---|
| Branch found checked out | `feature/htng&fias-integration` at `45ac98a` (= `main`, 2026-09-17) |
| Working tree found | clean except untracked `docker-compose.dev.yml` (PostgreSQL dev stack, left untouched) |
| Stashes | none in this clone |
| `origin/develop` | `46904fd` (2026-11-02), **99 commits ahead of `main`**; `main`'s 3 extra commits are merge commits whose content is already in `develop` |
| Work branch created | **`feature/htng-fias-on-develop`** from `origin/develop` (`46904fd`). The original branch is untouched. |

**Why a new branch.** `main` is still the PostgreSQL application. The MySQL backend
(`inspironics_app`), the stay write services and the OSS/BSS split that this work
must integrate with exist only on `develop`. A merge into the original branch was
attempted first and did not run: git has no committer identity configured on this
machine, and configuring one was out of scope. Creating a branch needs no commit.

## 2. Existing architecture (develop @ 46904fd)

| Area | Finding | Evidence |
|---|---|---|
| Backend | FastAPI app factory, one v1 router | `backend/app/main.py`, `backend/app/api/v1/router.py` |
| Database | MySQL 8 `inspironics_app` only, PyMySQL, TLS required by default, `READ COMMITTED`, UTC session clock | `backend/app/core/config.py`, `backend/app/db/session.py` |
| Types | `GUID` = CHAR(36) on MySQL, `UTCDateTime` = DATETIME(6) UTC, `JSONB` = JSON on MySQL | `backend/app/db/types.py` |
| Models | 93 tables on `Base.metadata`, naming convention for constraints | `backend/app/models/`, `backend/app/db/base.py` |
| Auth | HS256 JWT carrying only the user id; roles/permissions re-read from DB per request; `require_permission(module, read/write)` | `backend/app/api/deps.py`, `backend/app/services/auth.py` |
| Facility scope | `AuthenticatedUser.facility_ids` from `facility_user`; **not enforced on most reads** (existing register item B-09) | `backend/app/services/access.py:338` |
| Write services | `transaction(db)` commits per call; `WriteError` → 404/409/422 | `backend/app/services/writes.py`, `backend/app/api/write_errors.py` |
| Stay services | `create_stay`, `check_in`, `check_out`, `allocate_room`, … `stay` has **no facility_id** (scope via `room_allocation → amenity.facility_id`) | `backend/app/services/stays_write.py`, `backend/app/models/stay.py` |
| Workers / scheduler | none running; seeded scheduler jobs have no executor | `backend/seeds/steps/operations.py` |
| Logging | std `logging`, `hms.*` loggers | `backend/app/api/errors.py` |
| Decision registers | OSS/BSS `B-xx` / `D-xx` register exists; **no HF-xx register** in this repository | `docs/hms-integration-analysis/HMS_GAP_AND_BLOCKER_REGISTER.md` |

## 3. Existing integration components

**None in this repository.** No `app/integrations`, no FIAS/HTNG code, WSDL, XSD,
manual or fixture on any branch of this clone (`git ls-tree -r` over all remote branches).

**Earlier work exists outside this clone.** A sibling working copy
`../HMS-Frontend/ACX-Platform` (branch `feature/htng&fias-integrate`) holds an earlier
HTNG/FIAS implementation as **untracked, uncommitted files** (about 6,400 lines under
`backend/app/integrations/`, 10 test files, 19 `docs/HTNG_FIAS_*` reports). It was read,
not copied, and not modified. Reasons it was not adopted:

* its FIAS parser hard-codes STX/ETX framing and GI/GO/WR records as production
  behaviour and its report calls the framing "RFC/Standard" — unverified vendor semantics;
* its HF numbering differs from this task's (e.g. its HF-05 is the FIAS record set,
  HF-11 is folio ownership);
* it is not committed anywhere, so it cannot be reviewed or reproduced from git.

Its decision register was used as the source for HF wording where the IDs agree
(see `HTNG_FIAS_DECISION_REGISTER.md`). **Risk:** that work exists only on one
disk; commit or archive it if it should be kept.

## 4. Database and migration state

| Item | Finding |
|---|---|
| Alembic heads | **two**: `a3f1c8e2d904` and `b3c4d5e6f7a8`, both from `7c4e2b9a1d53` |
| Fresh MySQL bootstrap | **fails**: `alembic upgrade heads` stops at `8f1e3c5a7b92` (`BOOL NOT NULL DEFAULT 'true'`, MySQL 1067); `Base.metadata.create_all` fails the same way (`is_active` default) |
| Consequence | the repo cannot build the HMS schema on an empty MySQL; the shared `inspironics_app` must have been built another way |
| Configured HMS DB | `192.168.0.120:3306/inspironics_app` per `.env.example`; **no `backend/.env` exists here**, so nothing could reach it |

## 5. Baseline tests

Environment: Docker `python:3.12-slim` (no Python on the host), `requirements.txt`
installed in a container venv, disposable `mysql:8.4` container (`inspironics_app`, empty
schema because of §4).

| Run | Result |
|---|---|
| `pytest --co` | **1,329 collected** |
| pristine `HEAD` (`git archive`), `pytest -q --tb=no -rfE` | **150 failed, 63 passed, 1 skipped, 1,115 errors** |

These failures are environmental: the suite asserts a seeded HMS database (README:
"Tests run against a live … instance and assert the seeded baseline"), which cannot be
built here. The same command is re-run after the change for comparison
(`HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` §13).

## 6. Pre-existing technical risks

1. Two Alembic heads; fresh-MySQL migration failure (§4).
2. Read endpoints not facility-scoped (B-09).
3. `JWT_SECRET_KEY` placeholder shared with `.env.example` on the reference machine (`HMS_WORKING_ENVIRONMENT_BASELINE.md` N.10).
4. Earlier HTNG/FIAS work only on one disk, uncommitted (§3).
5. Regression suite needs a seeded database that the repo cannot build on MySQL.

## 7. Files created / modified by this work

Listed exactly in `HTNG_FIAS_MASTER_IMPLEMENTATION_REPORT.md` §3–4. The only existing
file modified is `backend/app/api/v1/router.py` (one import, one `include_router`).
