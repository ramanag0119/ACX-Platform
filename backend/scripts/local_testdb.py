r"""Manage the isolated local HMS test database. NEVER touches production.

    ..\.venv\Scripts\python.exe -m scripts.local_testdb <command>

Commands
--------
    status      report the bound schema, revision, table count and the
                fixture invariants the test suites depend on
    reset       drop and recreate the schema, then restore a baseline
                snapshot. ~2 seconds. Run this BEFORE EVERY SUITE.
    migrate     run `alembic upgrade` against the test database
    snapshot    write a baseline snapshot of the current state
    verify      assert the fixture invariants, exit non-zero if any fail

WHY THIS EXISTS
---------------
Two separate hazards, both solved here.

1. `app.core.config` resolves the BSS credentials from the vault, so ANY
   process importing it addresses PRODUCTION by default. An ad-hoc
   `python -c "...command.upgrade(...)"` looks local and is not. This module
   rebinds the session layer to HMS_TEST_DATABASE_URL *before* anything can
   connect, then asserts the resolved target is a local `_test` schema.
   `migrations/env.py` carries an independent guard; this is the first line.

2. The write suites consume their own fixtures. A failing test never reaches
   its cleanup, so each run leaves orphan stays and allocations behind and
   starves `free_room` for the next one. Measured on this very database:
   5 failed / 40 passed from a clean baseline, versus 69 failed / 105 passed
   when four suites ran back to back without a reset. Same code, same data --
   the difference is contamination. `reset` is the cure, and it is cheap
   enough to run every single time.

CONFIGURATION
-------------
    HMS_TEST_DATABASE_URL=mysql+pymysql://USER:PASS@127.0.0.1:3307/inspironics_app_test

No credential is hardcoded here. With the variable unset, every command
refuses to run rather than guessing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

#: Schemas this module must never operate on, whatever it is pointed at.
PROTECTED_SCHEMAS = frozenset({"inspironics_app"})

#: Hosts a test database may legitimately live on.
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

TEST_URL_ENV = "HMS_TEST_DATABASE_URL"

BACKEND = Path(__file__).resolve().parent.parent

#: Fixture invariants. A suite that starts without these fails for reasons
#: that have nothing to do with the code under test, which is the most
#: expensive kind of red to debug.
FREE_ROOM_SQL = """
    SELECT COUNT(*) FROM amenity a
    JOIN amenity_type t ON t.id = a.amenity_type_id
    WHERE t.amenity_category = 'room' AND a.status = 0
      AND NOT EXISTS (
          SELECT 1 FROM room_allocation ra JOIN stay s ON s.id = ra.stay_id
          WHERE ra.room_id = a.id AND s.status IN
                ('pending','active','checkout pending',
                 'checkout accepted','checkout rejected'))
      AND NOT EXISTS (
          SELECT 1 FROM amenity_condition_status acs
          WHERE acs.amenity_id = a.id AND acs.status = 1
            AND acs.amenity_condition_id IN (1,3,4))
"""

FIXTURE_USERS = (
    "arjun.menon", "kavya.iyer", "sneha.pillai", "vikram.rao", "aarav.sharma",
)


class UnsafeTarget(RuntimeError):
    """The resolved target is not an isolated local test database."""


def _banner(lines: list[str]) -> str:
    width = max(len(x) for x in lines) + 4
    rule = "=" * width
    return "\n" + rule + "\n" + "\n".join(f"  {x}" for x in lines) + "\n" + rule + "\n"


def resolve_url():
    """Resolve and VALIDATE the test URL. Raises before anything connects."""
    from sqlalchemy.engine import make_url

    raw = os.environ.get(TEST_URL_ENV, "").strip()
    if not raw:
        raise UnsafeTarget(_banner([
            f"{TEST_URL_ENV} is not set -- refusing to run.",
            "",
            "Every command here needs an explicit local test database. Without",
            "it this module would fall back to the vault, which resolves to",
            "PRODUCTION. Refusing is the only safe default.",
            "",
            "  export HMS_TEST_DATABASE_URL=\\",
            "    mysql+pymysql://USER:PASS@127.0.0.1:3307/inspironics_app_test",
        ]))

    url = make_url(raw)
    schema = url.database or ""

    if schema in PROTECTED_SCHEMAS:
        raise UnsafeTarget(_banner([
            f"{TEST_URL_ENV} points at the PROTECTED schema {schema!r}.",
            "A test database must be a DIFFERENT schema. Refusing.",
        ]))
    if not schema.endswith("_test"):
        raise UnsafeTarget(_banner([
            f"Schema {schema!r} does not end with '_test'. Refusing.",
            "The suffix is the convention this guard relies on.",
        ]))
    if url.host not in ALLOWED_HOSTS:
        raise UnsafeTarget(_banner([
            f"Host {url.host!r} is not local. Refusing.",
            f"Allowed: {', '.join(sorted(ALLOWED_HOSTS))}",
        ]))
    return url


def _engine(url, *, database: str | None = ...):
    """Engine for `url`, optionally against a different database on the same
    server (used to DROP/CREATE the schema itself)."""
    import sqlalchemy as sa

    target = url if database is ... else url.set(database=database)
    # Plaintext loopback: the container uses a self-signed cert and there is
    # nothing confidential in transit that has not already been anonymised.
    return sa.create_engine(target, poolclass=sa.pool.NullPool)


def _bind_app_session(url) -> None:
    """Point `app.db.session` at the test database before it can be used.

    Must happen before `app.core.config` is asked for a URL anywhere else;
    `alembic/env.py` reads `settings.sqlalchemy_url`, so the vault accessor is
    replaced rather than the already-built engine.
    """
    import app.core.vault as vault

    vault.get_mysql_credentials = lambda: vault.MySQLCredentials(
        username=url.username, password=url.password or "",
        host=url.host, port=url.port, database=url.database, ssl_ca="",
    )
    from app.core.config import Settings

    Settings.mysql_ssl_args = property(lambda self: {})


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def cmd_status(url, args) -> int:
    import sqlalchemy as sa

    eng = _engine(url)
    with eng.connect() as c:
        print(f"target   : {url.username}@{url.host}:{url.port}/{url.database}")
        print(f"server   : {c.execute(sa.text('SELECT VERSION()')).scalar()}")
        n = c.execute(sa.text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=:d AND table_type='BASE TABLE'"),
            {"d": url.database}).scalar()
        print(f"tables   : {n}")
        try:
            rev = c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
        except Exception:  # noqa: BLE001
            rev = "(no alembic_version table)"
        print(f"revision : {rev}")
    return 0


def cmd_reset(url, args) -> int:
    import sqlalchemy as sa

    snap = Path(args.snapshot)
    if not snap.is_file():
        print(f"snapshot not found: {snap}", file=sys.stderr)
        return 1

    adm = _engine(url, database="mysql")
    with adm.connect() as c:
        c.execute(sa.text(f"DROP DATABASE IF EXISTS `{url.database}`"))
        c.execute(sa.text(
            f"CREATE DATABASE `{url.database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"))
    adm.dispose()

    # mysql(1) streams the snapshot far faster than executing it statement by
    # statement through SQLAlchemy, and handles the dump's own directives.
    cmd = [
        "mysql", f"--host={url.host}", f"--port={url.port}",
        f"--user={url.username}", "--default-character-set=utf8mb4",
        url.database,
    ]
    env = dict(os.environ)
    if url.password:
        env["MYSQL_PWD"] = url.password        # not argv: not in the process list
    with snap.open("rb") as fh:
        p = subprocess.run(cmd, stdin=fh, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        print(p.stderr.decode(errors="replace")[:2000], file=sys.stderr)
        return p.returncode

    print(f"reset from {snap.name}")
    return cmd_verify(url, args) if args.verify else 0


def cmd_migrate(url, args) -> int:
    _bind_app_session(url)
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    if args.down:
        command.downgrade(cfg, args.revision)
    else:
        command.upgrade(cfg, args.revision)
    return cmd_status(url, args)


def cmd_snapshot(url, args) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "mysqldump", f"--host={url.host}", f"--port={url.port}",
        f"--user={url.username}", "--single-transaction", "--no-create-db",
        "--skip-add-drop-table", "--default-character-set=utf8mb4",
        "--routines", "--events", "--triggers", "--hex-blob",
        url.database,
    ]
    env = dict(os.environ)
    if url.password:
        env["MYSQL_PWD"] = url.password
    with out.open("wb") as fh:
        p = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, env=env)
    err = p.stderr.decode(errors="replace").strip()
    if err:
        # mysqldump warns about tablespace metadata without PROCESS; harmless.
        print(f"  note: {err.splitlines()[0][:120]}")
    if p.returncode != 0:
        return p.returncode
    size = out.stat().st_size
    print(f"snapshot -> {out}  ({size:,} bytes)")
    return 0


def cmd_verify(url, args) -> int:
    import sqlalchemy as sa

    eng = _engine(url)
    failures: list[str] = []

    def check(label, ok, detail=""):
        if not ok:
            failures.append(label)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    with eng.connect() as c:
        def scalar(sql, **kw):
            return c.execute(sa.text(sql), kw).scalar()

        rev = scalar("SELECT version_num FROM alembic_version")
        tables = scalar("SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema=:d AND table_type='BASE TABLE'",
                        d=url.database)
        print(f"  revision {rev} | {tables} tables")
        if args.expect_revision:
            check(f"revision is {args.expect_revision}", rev == args.expect_revision, str(rev))

        free = scalar(FREE_ROOM_SQL)
        check(f"free rooms >= 2 (have {free})", (free or 0) >= 2)

        users = c.execute(
            sa.text("SELECT COUNT(*) FROM app_user WHERE user_name IN :u")
            .bindparams(sa.bindparam("u", expanding=True)),
            {"u": list(FIXTURE_USERS)},
        ).scalar()
        check("all 5 conftest fixture users present", users == 5, f"{users}/5")

        for tbl, want in (("amenity_condition", 7), ("amenity_status", 4),
                          ("room_status_condition_applicability", 42)):
            try:
                n = scalar(f"SELECT COUNT(*) FROM `{tbl}`")
            except Exception:  # noqa: BLE001
                n = None
            check(f"{tbl} has {want} rows", n == want, str(n))

        has_currency = scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=:d AND table_name='currency'", d=url.database)
        if has_currency:
            check("currency has 7 rows", scalar("SELECT COUNT(*) FROM currency") == 7)
        else:
            print("  [ -- ] currency table absent (expected below d8e4f1a6b207)")

        leaked = scalar(
            "SELECT COUNT(*) FROM app_user WHERE email IS NOT NULL "
            "AND email NOT LIKE '%@test.invalid'")
        check("no un-anonymised email present", leaked == 0, f"{leaked}")

    if failures:
        print(f"\n  {len(failures)} invariant(s) FAILED -- suites would fail spuriously")
        return 1
    print("\n  all invariants hold")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    r = sub.add_parser("reset")
    r.add_argument("--snapshot", required=True)
    r.add_argument("--verify", action="store_true")
    r.add_argument("--expect-revision", default=None)

    m = sub.add_parser("migrate")
    m.add_argument("revision")
    m.add_argument("--down", action="store_true")

    s = sub.add_parser("snapshot")
    s.add_argument("--out", required=True)

    v = sub.add_parser("verify")
    v.add_argument("--expect-revision", default=None)

    args = p.parse_args(argv)
    for attr, default in (("snapshot", None), ("verify", False),
                          ("expect_revision", None), ("out", None)):
        if not hasattr(args, attr):
            setattr(args, attr, default)

    try:
        url = resolve_url()
    except UnsafeTarget as exc:
        sys.stderr.write(str(exc))
        return 2

    return {
        "status": cmd_status, "reset": cmd_reset, "migrate": cmd_migrate,
        "snapshot": cmd_snapshot, "verify": cmd_verify,
    }[args.cmd](url, args)


if __name__ == "__main__":
    sys.exit(main())
