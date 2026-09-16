"""Shared helpers for every Phase 3.0 write service.

Three things every mutation needs and none should re-invent:

* `Conflict` / `NotFound` / `Invalid` -- domain errors the endpoint layer turns
  into the standard 409 / 404 / 422 envelope. Services never raise HTTP.
* `transaction()` -- one commit per request, rollback on any failure, so a
  multi-table workflow can never half-apply.
* `require_row()` -- fetch-or-NotFound, used before every update so a bad id is
  a clean 404 rather than a silent no-op.

Audit columns follow the IKANOS convention already in the schema: `created_by`
and, where the table has them, `updated_by` / `modified_by` are set from the
authenticated caller -- never from the request body.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base


class WriteError(Exception):
    """Base class for the errors a write service is allowed to raise."""

    def __init__(self, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFound(WriteError):
    """A referenced row does not exist -> 404."""


class Conflict(WriteError):
    """The request contradicts current state or a uniqueness rule -> 409."""


class Invalid(WriteError):
    """The payload is well-formed but not acceptable -> 422."""


ModelT = TypeVar("ModelT", bound=Base)


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """Run a unit of work as one PostgreSQL transaction.

    The session is committed once at the end. Any exception -- a domain error,
    an integrity violation, anything -- rolls the whole thing back, so a
    workflow touching several tables either lands completely or not at all.
    """
    try:
        yield db
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # A constraint the service did not pre-check (a race, or a unique index
        # we do not know by name) is still a conflict, not a 500.
        raise Conflict("The change violates a database constraint.",
                       detail=_constraint_name(exc)) from exc
    except Exception:
        db.rollback()
        raise


def _constraint_name(exc: IntegrityError) -> str | None:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)


def require_row(db: Session, model: type[ModelT], row_id: Any, label: str) -> ModelT:
    """Load a row by primary key or raise NotFound."""
    row = db.get(model, row_id)
    if row is None:
        raise NotFound(f"{label} {row_id} does not exist.")
    return row


def require_exists(db: Session, model: type[Base], row_id: Any, label: str) -> None:
    """Validate a foreign-key reference before using it."""
    if row_id is None:
        return
    if db.get(model, row_id) is None:
        raise Invalid(f"{label} {row_id} does not exist.")


def ensure_unique(
    db: Session, model: type[Base], column, value: Any, label: str, *, exclude_id: Any = None
) -> None:
    """Pre-check a uniqueness rule so the user gets a clear 409, not a raw error."""
    stmt = select(model).where(column == value)
    existing = db.execute(stmt).scalars().first()
    if existing is not None and (exclude_id is None or getattr(existing, "id", None) != exclude_id):
        raise Conflict(f"{label} '{value}' already exists.")


def apply_changes(row: Base, changes: dict[str, Any]) -> bool:
    """Assign only the fields the caller actually sent.

    Pydantic's `exclude_unset` gives us "sent" vs "omitted"; this keeps a PATCH
    from overwriting a column with None just because it was not mentioned.
    Returns True when something changed.
    """
    changed = False
    for field, value in changes.items():
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True
    return changed


def next_reference(db: Session, model: type[Base], column, prefix: str, width: int = 5) -> str:
    """Build the next `PREFIX00001` style reference for a table.

    The pattern (and the widths) are taken from the seeded IKANOS data rather
    than invented: existing values are scanned, the highest numeric suffix
    wins, and the sequence continues from there.
    """
    existing = db.execute(select(column)).scalars().all()
    highest = 0
    for value in existing:
        if not value or not value.startswith(prefix):
            continue
        suffix = value[len(prefix):]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:0{width}d}"


def next_yearly_reference(db: Session, column, prefix: str, *, year: int, width: int = 4) -> str:
    """Build the next `PREFIX-YYYY-NNNN` reference.

    This is the format the seeded IKANOS data uses for stays (STY-2026-0001),
    service requests (SR-2026-0001) and invoices (INV-2026-0001). The counter
    is per prefix and per year, continuing from the highest existing value.
    """
    stem = f"{prefix}-{year}-"
    highest = 0
    for value in db.execute(select(column)).scalars().all():
        if not value or not value.startswith(stem):
            continue
        suffix = value[len(stem):]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{stem}{highest + 1:0{width}d}"


def new_id() -> uuid.UUID:
    """A fresh UUID primary key for a T2 entity table."""
    return uuid.uuid4()
