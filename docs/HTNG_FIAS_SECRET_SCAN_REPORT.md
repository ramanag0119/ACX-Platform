# HTNG / FIAS — Secret Scan Report

Date 2026-11-20 · branch `feature/htng-fias-on-develop` · read-only scan of the working tree.
No values are reproduced here; only locations and categories.

## 1. Method

| Step | Tool | Scope |
|---|---|---|
| 1 | gitleaks v8.21.2 (Docker, repository mounted read-only, `--redact`) | `backend/app/integrations/`, `backend/tests/integrations/`, `backend/migrations/drafts/`, `backend/app/api/v1/router.py`, `backend/tests/test_health_api.py`, `docs/` (incl. `docs/HTNG-FIAS/`), `docker-compose.dev.yml` |
| 2 | Positive control: a synthetic `ghp_…` token in a scratch directory **outside the repository** | gitleaks reported it (1 leak) → the scanner works in this setup; control file deleted |
| 3 | Pattern scan (grep): private keys, certificates, credentials in URLs, quoted and unquoted password/secret/token assignments, bearer tokens, organisation/personal e-mail domains, private IPs | same scope |
| 4 | `.gitignore` coverage via `git check-ignore` | `.env*`, venvs, bytecode, caches, DB dumps |

## 2. Findings

| # | Location | Category | Assessment | Action |
|---|---|---|---|---|
| S-1 | gitleaks, all scopes | — | **0 findings** | none |
| S-2 | 26 lines in `backend/app/integrations/**` and `backend/tests/integrations/**` | identifier named *secret/token* | **false positives**: type annotations (`secret_hash: Mapped[str]`), runtime generation (`generate_secret()`), lease tokens (`uuid4().hex`), a length constant. No literal credential | none |
| S-3 | `docker-compose.dev.yml` lines 9, 24 | development database password (local container default) | **pre-existing file, not part of this work**, untracked | do **not** stage; owner decides |
| S-4 | `docs/HTNG_FIAS_REPOSITORY_BASELINE.md` line 69 | private IP address of the configured HMS database host | low sensitivity; the same value is already in the tracked `backend/.env.example` | optional: replace with "configured host" before publishing outside the team |
| S-5 | test databases | the disposable test-container password | **not present in any repository file** (passed only via environment) | none |
| S-6 | `docs/HTNG-FIAS/*` (earlier implementation's reports) | local file-system paths in links | not secrets | exclude from commits unless the owner decides |

No private keys, certificates, bearer tokens, credentialed URLs or personal e-mail addresses
were found in candidate files.

## 3. `.gitignore` coverage

Ignored as required: `backend/.env`, `backend/.env.*` (except example), `backend/.venv/`,
`__pycache__/`, `.pytest_cache/`, `frontend/.env.local`, `*_backup.sql`, `*_dump.sql`.
A `backend/tests/integrations/__pycache__/` exists locally and is ignored.

**Gap (recommendation, not changed):** `backend/tests/integrations/vendor_contracts/` will
hold vendor sample messages, which may contain **real guest PII**. Before the first vendor
sample arrives, decide (HF-21 / LEGAL) whether samples must be anonymised before commit, or
whether that directory is git-ignored and samples are stored in an access-controlled location.

## 4. Commit preparation status

No candidate implementation file is blocked by a finding. Files excluded from any commit until
their owner decides: `docker-compose.dev.yml`, `docs/HTNG-FIAS/`. Re-run gitleaks on the
staged diff (`gitleaks git --staged`) immediately before the first commit.
