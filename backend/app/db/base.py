"""SQLAlchemy declarative base, PK tiers and shared column mixins.

Implements the primary-key policy of FINAL_HMS_DATABASE_BLUEPRINT.md §2.3:

    T1  lookup / reference   -> native SMALLINT or INTEGER, IKANOS ids preserved
    T2  business entity      -> UUID (uuid4)
    T3  high-volume log      -> BIGINT GENERATED ALWAYS AS IDENTITY

plus the two structural additions declared in §2.3 / §2.4:

    legacy_id                -> BIGINT NULL UNIQUE, the original IKANOS key
    created_on / updated_on  -> TIMESTAMPTZ NOT NULL DEFAULT now()

IKANOS audit-column naming (`created_on` / `updated_on`) is used throughout;
the Phase 1 `created_at` / `updated_at` naming is retired (blueprint §2.2).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Identity, Integer, MetaData, SmallInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings
from app.db.types import GUID, NOW, UTCDateTime

# Deterministic constraint naming so Alembic autogenerate produces stable names.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# MySQL has no schema beyond the database, and PostgreSQL's `public` is already
# on the search_path. Setting it explicitly makes SQLAlchemy schema-qualify
# every ForeignKey while reflection reports them unqualified, which shows up as
# permanent phantom drift in `alembic check`. Only pin a non-default PG schema.
_SCHEMA = settings.db_schema


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention=NAMING_CONVENTION,
        schema=_SCHEMA,
    )


# --------------------------------------------------------------------------
# Primary-key tiers (blueprint §2.3)
# --------------------------------------------------------------------------


class UUIDPk:
    """T2 — business / transactional entity."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )


class BigIntPk:
    """T3 — append-only high-volume telemetry, alert, notification or audit log."""

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )


class SmallIntLookupPk:
    """T1 — lookup table. The IKANOS integer id IS the key and is seeded, so it
    is never generated."""

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)


class IntLookupPk:
    """T1 — lookup table needing the wider INTEGER range (`device_param`)."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)


# --------------------------------------------------------------------------
# Shared columns (blueprint §2.3, §2.4, §5.0)
# --------------------------------------------------------------------------


class LegacyIdMixin:
    """The original IKANOS integer key, so a live install can be migrated
    without key collision. Blueprint §2.3 declares this on every table."""

    legacy_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)


class TimestampMixin:
    """IKANOS carries `created_on` / `updated_on` on 99 of its 101 tables.
    Blueprint §5.0 declares them on all 92."""

    created_on: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=NOW, nullable=False
    )
    updated_on: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        server_default=NOW,
        onupdate=NOW,
        nullable=False,
    )


class HMSBase(Base, LegacyIdMixin, TimestampMixin):
    """Everything shared by all 92 tables except the primary key itself."""

    __abstract__ = True
