"""Shared seed helpers: deterministic ids and idempotent upserts.

Every demo record is addressed by a *stable* identifier derived from a natural
key, so running the seed twice updates the same rows instead of creating a
second copy. No random UUID is ever generated.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

#: Fixed namespace for every HMS demo record. Changing it re-keys the whole
#: dataset, so it must stay constant.
DEMO_NAMESPACE = uuid.UUID("6f1d9c2a-3b47-5e88-9a10-4c7e2f0b8d31")

T = TypeVar("T")


def did(table: str, key: str) -> uuid.UUID:
    """Deterministic UUID for a demo row: uuid5(namespace, "table:key")."""
    return uuid.uuid5(DEMO_NAMESPACE, f"{table}:{key}")


def upsert(
    session: Session, model: type[T], match: dict[str, Any], /, **values: Any
) -> T:
    """Insert the row if it is absent, otherwise refresh it in place.

    `match` is the natural key used to recognise an existing demo row. This is
    what makes repeated runs safe: the second run finds every row via `match`
    and updates it rather than inserting a duplicate.

    The first three parameters are positional-only: several models have columns
    called `model`, `session` or `match` (`device.model`, for one), and those
    must land in `**values` instead of shadowing the helper's own arguments.
    """
    obj = session.execute(select(model).filter_by(**match)).scalar_one_or_none()
    if obj is None:
        obj = model(**match, **values)
        session.add(obj)
        session.flush()
        return obj
    for field, value in values.items():
        setattr(obj, field, value)
    session.flush()
    return obj


# ---------------------------------------------------------------------------
# Demo clock
# ---------------------------------------------------------------------------
# The dataset is anchored to a fixed instant so repeated runs produce identical
# timestamps. Anchoring to "now" would make every run write different values
# and defeat idempotency.

DEMO_NOW = datetime(2026, 8, 17, 12, 0, 0, tzinfo=UTC)
DEMO_TODAY = DEMO_NOW.date()


def hours(n: int) -> timedelta:
    return timedelta(hours=n)


def days(n: int) -> timedelta:
    return timedelta(days=n)


def ikanos_hour(moment: datetime) -> int:
    """IKANOS `energy_stats.hour` = whole hours elapsed since 2000-01-01.

    Read from the column comment in the dump: "primary key with, hours elapsed
    from 2000". Not a timestamp.
    """
    epoch = datetime(2000, 1, 1, tzinfo=UTC)
    return int((moment - epoch).total_seconds() // 3600)
