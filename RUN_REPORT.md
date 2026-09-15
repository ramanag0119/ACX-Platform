# RUN_REPORT — ACX Platform (HMS)

How to get this project running from a fresh clone. Every command below was
executed against this tree; versions are the ones actually verified.

- **Project:** ACX Platform — Hotel Management System (HMS) for the IKANOS portal
- **Repository:** https://github.com/ramanag0119/ACX-Platform
- **Stack:** FastAPI + SQLAlchemy + Alembic + PostgreSQL (backend) · Vite + React + TypeScript + shadcn-ui + Tailwind (frontend)
- **Layout:** `backend/` · `frontend/` · `docs/`

---

## 1. Required software

| Tool | Verified version | Notes |
|---|---|---|
| Git | any recent | — |
| Node.js | **v20.11.0** | v20 LTS or newer |
| npm | **10.2.4** | ships with Node 20 |
| Python | **3.13.3** | 3.11+ should work; 3.13 is what is verified |
| PostgreSQL | **16.12** | server must be running before any backend step |

The backend needs a reachable PostgreSQL **server**; the schema itself is created
by Alembic, not by hand.

### Install commands

Windows (winget):

```sh
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.13
winget install PostgreSQL.PostgreSQL.16
```

macOS (Homebrew):

```sh
brew install node@20 python@3.13 postgresql@16
brew services start postgresql@16
```

Debian/Ubuntu:

```sh
sudo apt update
sudo apt install -y nodejs npm python3.13 python3.13-venv postgresql-16
sudo systemctl start postgresql
```

---

## 2. Clone

```sh
git clone https://github.com/ramanag0119/ACX-Platform.git
cd ACX-Platform
git checkout feature/changes-hms
```

`feature/changes-hms` is the branch holding the latest complete code.

---

## 3. Database setup

Create an empty database. Alembic builds the 92-table schema into it.

```sh
psql -U postgres -c "CREATE DATABASE hms_db;"
```

On Windows, `psql` lives in `C:\Program Files\PostgreSQL\16\bin` — add it to
`PATH` or call it by full path.

---

## 4. Backend

```sh
cd backend

# 1. Virtual environment
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

# 2. Dependencies
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env             # copy .env.example .env  on Windows cmd
#    then edit .env (see the table below)

# 4. Schema
alembic upgrade head

# 5. Demo data (recommended — the UI is empty without it)
python -m seeds.run_seed

# 6. Run
uvicorn app.main:app --reload
```

Backend serves on **http://127.0.0.1:8000** · interactive docs at
**http://127.0.0.1:8000/docs**.

### Backend `.env` variables

Copied from `backend/.env.example`. Placeholders you **must** change are marked.

| Variable | Placeholder / default | Required? |
|---|---|---|
| `POSTGRES_USER` | `postgres` | yes |
| `POSTGRES_PASSWORD` | `change_me` | **yes — set to your real password** |
| `POSTGRES_HOST` | `localhost` | yes |
| `POSTGRES_PORT` | `5432` | yes |
| `POSTGRES_DB` | `hms_db` | yes |
| `POSTGRES_SCHEMA` | `public` | yes |
| `DATABASE_URL` | commented out | optional — overrides the `POSTGRES_*` parts when set |
| `APP_NAME` | `HMS Backend` | no |
| `APP_ENV` | `development` | no |
| `DEBUG` | `true` | no |
| `JWT_SECRET_KEY` | `change_me_in_every_environment` | **yes — generate a real one** |
| `JWT_ALGORITHM` | `HS256` | no |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | no |

Generate a JWT secret:

```sh
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`.env` is git-ignored. Never commit it.

---

## 5. Create a login (REQUIRED — the app is unusable without it)

**The seed deliberately writes no usable credential.** Every seeded account
carries the sentinel `password_hash = '!seed-no-login'`, so
`POST /api/v1/auth/login` returns 401 for all of them and the frontend cannot
get past `/login`. This is intended behaviour, not a bug — see
`backend/docs/PHASE2_4_AUTHENTICATION.md` §1.

Set a password for one seeded account after seeding. From `backend/`, with the
venv active:

```sh
python -c "from app.core.security import hash_password; print(hash_password('YourPassword123'))"
```

Then apply the printed hash:

```sh
psql -U postgres -d hms_db -c "UPDATE app_user SET password_hash = '<paste-hash-here>' WHERE user_name = 'arjun.menon';"
```

Log in as `arjun.menon` with the password you chose. Other seeded usernames
include `aarav.sharma`, `priya.nair`, `vikram.rao`, `meera.krishnan`. (Skip the
`system` account — it is a non-interactive service account.)

---

## 6. Frontend

In a second terminal:

```sh
cd frontend
npm install
cp .env.example .env.local       # copy .env.example .env.local  on Windows cmd
npm run dev
```

Frontend serves on **http://localhost:8080**.

The dev server proxies `/api/v1` to `VITE_API_PROXY_TARGET`, so there is no CORS
setup to do locally.

### Frontend `.env.local` variables

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | leave relative in development; set to an absolute API base when deployed |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | where FastAPI is listening locally |

Other scripts: `npm run build` (production build to `dist/`), `npm run lint`,
`npm run preview`.

---

## 7. Run the complete project

Two terminals, both from the repo root:

```sh
# Terminal 1 — backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Then open **http://localhost:8080** and log in with the account you created in
step 5.

---

## 8. Tests

```sh
# Backend (1195 tests)
cd backend && python -m pytest

# Frontend typecheck / build
cd frontend && npx tsc -b --noEmit && npm run build
```

**Backend tests require a freshly seeded database.** They assert the exact
seeded baseline (row counts, statuses, reference vocabularies), so any data
created through the UI or the write endpoints will make some of them fail. Run
them right after `python -m seeds.run_seed`, before using the app.

---

## 9. Known issues

1. **No seeded account can log in out of the box.** Step 5 is mandatory. This is
   a deliberate seed-data property, documented in
   `backend/docs/PHASE2_4_AUTHENTICATION.md`.
2. **Backend tests fail against a used database.** On a developer machine where
   the app has already been exercised, roughly a dozen seeded-baseline tests
   fail (room statuses changed, extra `app_user` rows, extra condition rows).
   Re-seed to get a green run. This is environment state, not a code defect.
3. **Frontend bundle size warning.** `npm run build` warns that the main chunk
   exceeds 500 kB. Build succeeds; this is a performance note only.
4. **Browserslist data is ~15 months old.** A cosmetic build warning. Clear it
   with `npx update-browserslist-db@latest` if it bothers you.
5. **Windows line endings.** Git reports `LF will be replaced by CRLF` on some
   frontend files. Harmless; the repo has no `.gitattributes` pinning EOL.
6. **`python` vs `python3`.** On macOS/Linux use `python3` and `pip3` where the
   commands above say `python` / `pip`.
