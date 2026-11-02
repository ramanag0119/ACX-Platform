r"""Validate the BSS MySQL connection. READ-ONLY -- nothing is written.

    ..\.venv\Scripts\python.exe -m scripts.verify_mysql_connection

or, with the password supplied from the KeePass vault instead of .env:

    ..\secure-local\run_with_secret.py --check

Checks, in order, and reports each one honestly rather than stopping at the
first success:

    1. settings resolve (password presence only -- never its value)
    2. TCP reachability
    3. authentication
    4. TLS cipher actually in use        <- proves encryption, not just config
    5. server version
    6. selected database
    7. granted permissions
    8. a trivial SELECT
    9. SQLAlchemy ORM session
   10. alembic revision, if the table exists

No password is ever printed. The DSN is never echoed.
"""

from __future__ import annotations

import socket
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"


def line(step: str, status: str, detail: str = "") -> None:
    print(f"  [{status:4}] {step:<34} {detail}")


def main() -> int:
    print("BSS MySQL connection verification (read-only)")
    print(f"  target: {settings.MYSQL_USER}@{settings.MYSQL_HOST}:"
          f"{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    print()

    if not settings.MYSQL_PASSWORD:
        line("password configured", FAIL, "MYSQL_PASSWORD is empty")
        print("\n  Supply it from the vault:")
        print("    secure-local\\run_with_secret.py --check")
        return 2
    line("password configured", PASS, "(value not shown)")

    try:
        ssl_args = settings.mysql_ssl_args
    except RuntimeError as exc:
        line("TLS configuration", FAIL, str(exc).splitlines()[0])
        print(f"\n{exc}")
        return 2
    verifying = "ssl_ca" in ssl_args
    line("TLS configuration", PASS if verifying else WARN,
         "CA verification ON" if verifying else "encrypted, NOT verified")

    sock = socket.socket()
    sock.settimeout(6)
    try:
        sock.connect((settings.MYSQL_HOST, settings.MYSQL_PORT))
        line("TCP reachable", PASS)
    except OSError as exc:
        line("TCP reachable", FAIL, str(exc))
        return 1
    finally:
        sock.close()

    from app.db.session import CONNECT_ARGS

    try:
        engine = create_engine(
            settings.sqlalchemy_url,
            connect_args={**CONNECT_ARGS, "connect_timeout": 10},
            echo=False,  # never echo: the DSN carries the password
        )
        conn = engine.connect()
    except SQLAlchemyError as exc:
        msg = str(exc.__cause__ or exc).splitlines()[0]
        line("authentication", FAIL, msg[:110])
        return 1
    line("authentication", PASS)

    exit_code = 0
    with conn:
        conn.execute(text("SET SESSION TRANSACTION READ ONLY"))

        cipher = conn.execute(
            text("SELECT VARIABLE_VALUE FROM performance_schema.session_status "
                 "WHERE VARIABLE_NAME = 'Ssl_cipher'")
        ).scalar()
        if cipher:
            line("TLS in use", PASS, cipher)
        else:
            line("TLS in use", FAIL, "connection is NOT encrypted")
            exit_code = 1

        version = conn.execute(text("SELECT VERSION()")).scalar_one()
        line("server version", PASS, version)

        db = conn.execute(text("SELECT DATABASE()")).scalar()
        line("database selected", PASS if db else FAIL, db or "none")

        user = conn.execute(text("SELECT CURRENT_USER()")).scalar_one()
        line("authenticated as", PASS, user)

        grants = [r[0] for r in conn.execute(text("SHOW GRANTS"))]
        line("permissions", PASS, f"{len(grants)} grant statement(s)")
        for g in grants:
            print(f"         {g}")

        line("SELECT works", PASS,
             f"1+1={conn.execute(text('SELECT 1+1')).scalar_one()}")

        tables = conn.execute(
            text("SELECT COUNT(*) FROM information_schema.TABLES "
                 "WHERE TABLE_SCHEMA = :d"), {"d": settings.MYSQL_DATABASE}
        ).scalar_one()
        line("tables in database", PASS, str(tables))

        has_alembic = conn.execute(
            text("SELECT COUNT(*) FROM information_schema.TABLES "
                 "WHERE TABLE_SCHEMA = :d AND TABLE_NAME = 'alembic_version'"),
            {"d": settings.MYSQL_DATABASE},
        ).scalar_one()
        if has_alembic:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            line("alembic revision", PASS, str(rev))
        else:
            line("alembic revision", WARN, "no alembic_version table yet")

    # ORM session, the path the application actually uses.
    try:
        from app.db.session import SessionLocal

        with SessionLocal() as s:
            s.execute(text("SELECT 1")).scalar_one()
        line("SQLAlchemy ORM session", PASS)
    except SQLAlchemyError as exc:
        line("SQLAlchemy ORM session", FAIL, str(exc)[:110])
        exit_code = 1

    print()
    print("Verified read-only. No row was inserted, updated or deleted.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
