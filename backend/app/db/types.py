"""Column types that mean the same thing on MySQL and PostgreSQL.

The models were written for PostgreSQL; MySQL is now the HMS database of
record. Rather than fork the schema, every column whose native type differs
goes through one of these, so both dialects store the same values and the
application code sees the same Python objects either way:

    GUID          native UUID on PostgreSQL; CHAR(36) with dashes on MySQL
    UTCDateTime   TIMESTAMPTZ on PostgreSQL; DATETIME(6) holding UTC on MySQL,
                  returned timezone-aware so comparisons never mix naive/aware
    JSONB         JSONB on PostgreSQL; JSON on MySQL
    DOUBLE        DOUBLE PRECISION on both
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CHAR, JSON, DateTime, Double, text
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.types import TypeDecorator

#: `DEFAULT` for created_on / updated_on. CURRENT_TIMESTAMP(6) is valid on both
#: dialects, and MySQL requires the precision to match the DATETIME(6) column.
NOW = text("CURRENT_TIMESTAMP(6)")


class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = True) -> None:  # noqa: ARG002 - PGUUID signature
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def __init__(self, timezone: bool = True) -> None:  # noqa: ARG002 - DateTime signature
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | str | None, dialect):
        # Strings (an ISO date from a query string) go through as-is, the same
        # as the PostgreSQL driver would pass them.
        if not isinstance(value, datetime) or dialect.name != "mysql":
            return value
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None or dialect.name != "mysql":
            return value
        return value.replace(tzinfo=UTC)


JSONB = JSON().with_variant(postgresql.JSONB(), "postgresql")
DOUBLE = Double()
