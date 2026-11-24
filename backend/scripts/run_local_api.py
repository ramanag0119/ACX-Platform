r"""Run the HMS API against the isolated local test database. NEVER production.

    ..\.venv\Scripts\python.exe -m scripts.run_local_api [--host H] [--port P]

WHY THIS EXISTS
---------------
`app/core/config.py` resolves the BSS host, port, user, password and schema
from the KeePass vault, and there is deliberately no DATABASE_URL override. So
`uvicorn app.main:app` -- the command in README.md and ecosystem.config.js --
addresses PRODUCTION MySQL, by design and with no way to say otherwise.

`HMS_TEST_DATABASE_URL` only reaches pytest (tests/db_isolation.py) and
`scripts.local_testdb`. Neither covers the case of serving the real app to the
frontend off the local test database, which is what local development on a
schema change or a seeded fixture actually needs.

This module closes that gap WITHOUT loosening the vault rule: it reuses
`scripts.local_testdb` for both the validation and the rebind, so there is one
guard and one rebind in the codebase rather than a second copy free to drift.
The target must be a `_test` schema on a loopback host or nothing starts.

    HMS_TEST_DATABASE_URL=mysql+pymysql://root:PASS@127.0.0.1:3307/inspironics_app_test

NO --reload
-----------
Uvicorn's reloader re-imports the app in a CHILD process that never runs this
module, so the child would resolve the vault and reach production while the
banner here still claimed the test database. Reload is therefore not offered;
restart the process after an edit.
"""

from __future__ import annotations

import argparse
import sys

from scripts.local_testdb import UnsafeTarget, _bind_app_session, resolve_url


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    try:
        url = resolve_url()
    except UnsafeTarget as exc:
        sys.stderr.write(str(exc))
        return 2

    # Must happen before `app.main` is imported: `app.db.session` builds its
    # engine at import time from `settings.sqlalchemy_url`, so a rebind after
    # that point would leave the engine pointed at the vault's target.
    _bind_app_session(url)

    import uvicorn

    from app.db.session import engine

    # Report what the ENGINE resolved, not what was asked for -- the engine is
    # what every request will actually use, and printing it is the check that
    # the rebind above took effect.
    print(f"  HMS API -> {engine.url.render_as_string(hide_password=True)}")
    print(f"  listening on http://{args.host}:{args.port}\n")

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
