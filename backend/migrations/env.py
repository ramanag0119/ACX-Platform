"""Alembic environment for HMS.

The database URL is taken from application settings (.env), not from
alembic.ini, so there is a single source of truth.
"""

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

# MySQL has no schemas inside the database; on PostgreSQL the version table
# lives in the configured schema.
VERSION_TABLE_SCHEMA = None if settings.is_mysql else settings.POSTGRES_SCHEMA
# Only walk multiple schemas when we are not simply using the default one.
INCLUDE_SCHEMAS = settings.db_schema is not None


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
