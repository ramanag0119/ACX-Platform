"""Alembic environment for HMS.

The database URL is taken from application settings (.env), not from
alembic.ini, so there is a single source of truth.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings

# Importing the models package registers every table on Base.metadata.
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.sqlalchemy_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

VERSION_TABLE_SCHEMA = settings.POSTGRES_SCHEMA
# Only walk multiple schemas when we are not simply using the default one.
INCLUDE_SCHEMAS = settings.POSTGRES_SCHEMA != "public"


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
        url=config.get_main_option("sqlalchemy.url"),
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
