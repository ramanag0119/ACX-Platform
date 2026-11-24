"""Keep the test suite off the production BSS database.

THE PROBLEM THIS SOLVES
-----------------------
`tests/conftest_writes.py` opens a real `SessionLocal()` against whatever
`app.db.session` was configured with -- which is the production MySQL
`inspironics_app`. The write suites create and delete rows there on every run.
Their contract is self-cleanup, and that contract breaks whenever a run is
interrupted: measured drift against the documented 1,792-row baseline went
+90 -> +192 -> +212 over three audits, and `stay` grew from 69 rows to 148
(142 of them `pending`). That residue is also what starves the `free_room`
fixture, which is the single largest cause of the suite's ~274 failures.

WHAT THIS MODULE DOES
---------------------
One rule, applied before any test imports the session layer:

    tests run against HMS_TEST_DATABASE_URL, or they do not run at all.

`bind_test_database()` rebinds `app.db.session.engine` / `.SessionLocal` to the
dedicated test database. It must be called from `tests/conftest.py` at import
time, BEFORE `conftest_writes.py` does `from app.db.session import SessionLocal`
-- that import copies the object, so rebinding afterwards would miss it.
`app.db.session.get_db` reads the module global on each call, so the FastAPI
dependency follows the rebind automatically.

With no test URL configured the session is ABORTED, not silently pointed at
production. Refusing to run is the safe default: a suite that does not run
costs a developer a minute, while a suite that quietly writes to the live
hotel database costs real data.

THE ESCAPE HATCH, AND WHY IT IS UGLY ON PURPOSE
-----------------------------------------------
`HMS_ALLOW_TESTS_ON_PRODUCTION_DB=1` restores the old behaviour. It is spelled
out in full so it cannot be set by accident or mistaken for a tuning flag, and
it logs a loud banner every run. It exists only because the dedicated test
database cannot be provisioned yet (see below) -- it is a temporary bridge, not
a supported mode.

PROVISIONING (blocked on privileges, not on code)
-------------------------------------------------
The `inspironics_app` account holds `ALL PRIVILEGES` on its own schema and only
`CREATE` globally, so it can create an empty database but cannot read, write,
alter or drop one. A DBA has to run, once::

    CREATE DATABASE inspironics_app_test
      CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
    GRANT ALL PRIVILEGES ON `inspironics_app_test`.* TO `inspironics_app`@`%`;
    FLUSH PRIVILEGES;

Then set, in the environment (never committed)::

    HMS_TEST_DATABASE_URL=mysql+pymysql://USER:PASSWORD@192.168.0.120:3306/inspironics_app_test

and the suite runs there with no further code change.
"""

from __future__ import annotations

import os
import sys

#: Full SQLAlchemy URL of the dedicated test database.
TEST_URL_ENV = "HMS_TEST_DATABASE_URL"

#: Deliberately long. See the module docstring.
OVERRIDE_ENV = "HMS_ALLOW_TESTS_ON_PRODUCTION_DB"

#: Schemas the suite must never write to.
PROTECTED_SCHEMAS = frozenset({"inspironics_app"})


class ProductionDatabaseRefused(RuntimeError):
    """The suite was pointed at a protected schema without an explicit override."""


def _banner(lines: list[str]) -> str:
    width = max(len(line) for line in lines) + 4
    rule = "=" * width
    body = "\n".join(f"  {line}" for line in lines)
    return f"\n{rule}\n{body}\n{rule}\n"


def _fail(message: str) -> None:
    """Abort collection before a single test can open a connection."""
    sys.stderr.write(message)
    raise ProductionDatabaseRefused(message.strip())


def bind_test_database() -> str:
    """Point the session layer at the test database, or refuse to run.

    Returns a short description of the mode chosen, for reporting.
    """
    test_url = os.environ.get(TEST_URL_ENV, "").strip()
    override = os.environ.get(OVERRIDE_ENV, "").strip() == "1"

    if test_url:
        target = _rebind(test_url)
        if target in PROTECTED_SCHEMAS and not override:
            _fail(_banner([
                f"{TEST_URL_ENV} points at the PRODUCTION schema {target!r}.",
                "A dedicated test database must be a DIFFERENT schema.",
                "Refusing to run so the suite cannot write to production.",
            ]))
        return f"dedicated test database: {target}"

    if override:
        sys.stderr.write(_banner([
            "WARNING: running the suite against the PRODUCTION database.",
            f"{OVERRIDE_ENV}=1 is set, so the safety guard is disabled.",
            "Write tests WILL create and delete rows in inspironics_app.",
            f"Set {TEST_URL_ENV} to a dedicated schema to stop this.",
        ]))
        return "PRODUCTION (explicit override)"

    _fail(_banner([
        "No test database configured -- refusing to run the suite.",
        "",
        f"The write suites open real sessions, and without {TEST_URL_ENV}",
        "they would create and delete rows in the production database",
        "`inspironics_app`.",
        "",
        "Fix (ask a DBA to run once):",
        "  CREATE DATABASE inspironics_app_test",
        "    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        "  GRANT ALL PRIVILEGES ON `inspironics_app_test`.*",
        "    TO `inspironics_app`@`%`;",
        "",
        "Then export:",
        f"  {TEST_URL_ENV}=mysql+pymysql://USER:PASS@HOST:3306/inspironics_app_test",
        "",
        f"To knowingly run against production anyway: {OVERRIDE_ENV}=1",
    ]))
    raise AssertionError("unreachable")  # pragma: no cover


def _rebind(url: str) -> str:
    """Rebuild the engine/sessionmaker against `url`. Returns the schema name."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker

    import app.db.session as session_module

    parsed = make_url(url)
    engine = create_engine(
        parsed,
        connect_args=session_module.CONNECT_ARGS,
        isolation_level="READ COMMITTED",
        pool_pre_ping=True,
        echo=False,
    )
    session_module.engine = engine
    session_module.SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    return parsed.database or ""


def active_schema() -> str | None:
    """The schema the session layer is currently bound to."""
    import app.db.session as session_module

    return session_module.engine.url.database
