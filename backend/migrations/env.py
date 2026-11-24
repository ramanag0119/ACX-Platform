"""Alembic environment for HMS.

The database URL is taken from application settings (.env), not from
alembic.ini, so there is a single source of truth.

PRODUCTION GUARD
----------------
That single source of truth is also a trap: `app.core.config` resolves the BSS
credentials out of the vault, so ANY process that imports it -- including a
throwaway `python -c "...command.upgrade(...)"` one-liner -- addresses the
PRODUCTION database by default. A migration intended for a local container
reaches `inspironics_app` instead, and nothing in the command says so.

That is not hypothetical: it happened. Two revisions were applied to
production from a one-liner that looked local. The only clue was the starting
revision in the Alembic log, after the fact.

`_assert_target_allowed()` closes it. A protected schema is refused unless
HMS_ALLOW_PRODUCTION_MIGRATION=1 is set, and the check runs BEFORE a
connection is opened or a single statement is emitted. The variable is spelled
out in full, like HMS_ALLOW_TESTS_ON_PRODUCTION_DB in tests/db_isolation.py,
so it cannot be set by accident or mistaken for a tuning flag -- and when it IS
set, a banner makes the target impossible to miss.

This guard is a seatbelt, not a permission system: anyone who means to migrate
production still can, in one deliberate extra step.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.session import CONNECT_ARGS

# Importing the models package registers every table on Base.metadata.
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

#: Schemas a migration must never reach by accident.
PROTECTED_SCHEMAS = frozenset({"inspironics_app"})

#: Deliberately long. See the module docstring.
OVERRIDE_ENV = "HMS_ALLOW_PRODUCTION_MIGRATION"


class ProductionMigrationRefused(RuntimeError):
    """A migration was aimed at a protected schema without an explicit override."""


def _banner(lines: list[str]) -> str:
    width = max(len(line) for line in lines) + 4
    rule = "=" * width
    body = "\n".join(f"  {line}" for line in lines)
    return f"\n{rule}\n{body}\n{rule}\n"


def _assert_target_allowed() -> None:
    """Refuse a protected schema unless the override is explicitly set.

    Called from both the offline and online paths, before anything connects.
    """
    url = settings.sqlalchemy_url
    target = url.database or ""

    if target not in PROTECTED_SCHEMAS:
        return

    if os.environ.get(OVERRIDE_ENV, "").strip() == "1":
        sys.stderr.write(_banner([
            "MIGRATING THE PRODUCTION DATABASE.",
            f"  host     : {url.host}:{url.port}",
            f"  schema   : {target}",
            f"{OVERRIDE_ENV}=1 is set, so the guard is disabled.",
            "Take a verified backup first if you have not already.",
        ]))
        return

    message = _banner([
        f"REFUSING to run migrations against {target!r} on {url.host}:{url.port}.",
        "",
        "This is a PROTECTED schema. `app.core.config` resolves the BSS",
        "credentials from the vault, so any process importing it addresses",
        "production by default -- including a command meant for a local",
        "container.",
        "",
        "For local work, point the session layer at the test database first",
        "(see backend/scripts/local_testdb.py, which does this safely).",
        "",
        f"To migrate production deliberately: {OVERRIDE_ENV}=1",
    ])
    sys.stderr.write(message)
    raise ProductionMigrationRefused(
        f"migration against protected schema {target!r} refused; "
        f"set {OVERRIDE_ENV}=1 to override"
    )

# MySQL has no schemas inside the database, so `alembic_version` and every
# table live unqualified in the connection's default database.
VERSION_TABLE_SCHEMA = None
INCLUDE_SCHEMAS = False


def include_object(obj, name, type_, reflected, compare_to):
    """Restrict autogenerate to the configured schema.

    Alembic's own bookkeeping table is excluded so it is never emitted as a
    create/drop operation in a revision.
    """
    if type_ == "table":
        if name == "alembic_version":
            return False
        if obj.schema not in (None, VERSION_TABLE_SCHEMA):
            return False
    return True


def run_migrations_offline() -> None:
    _assert_target_allowed()
    context.configure(
        url=settings.sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=INCLUDE_SCHEMAS,
        include_object=include_object,
        version_table_schema=VERSION_TABLE_SCHEMA,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _assert_target_allowed()
    # Built from settings directly: a URL object keeps the password escaped,
    # which a round trip through alembic.ini's interpolation would not.
    connectable = create_engine(
        settings.sqlalchemy_url, connect_args=CONNECT_ARGS, poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=INCLUDE_SCHEMAS,
            include_object=include_object,
            version_table_schema=VERSION_TABLE_SCHEMA,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
