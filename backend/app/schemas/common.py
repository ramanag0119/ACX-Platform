"""Shared response primitives.

`Page` is the single pagination envelope for every list endpoint, so a client
parses one shape regardless of resource.
"""

from __future__ import annotations

from typing import Generic, Sequence, TypeVar

import uuid

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

#: Safe defaults -- a list endpoint never returns an unbounded result set.
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    """A page of results plus the counters needed to render a pager."""

    items: Sequence[T]
    page: int = Field(examples=[1], ge=1)
    page_size: int = Field(examples=[20], ge=1)
    total: int = Field(examples=[27], ge=0, description="Rows matching the filters")


def paginate(items: Sequence[T], *, page: int, page_size: int, total: int) -> Page[T]:
    return Page[T](items=items, page=page, page_size=page_size, total=total)


class UserRef(BaseModel):
    """A minimal person reference shared by every domain.

    Defined once so the OpenAPI component name cannot collide, and narrow by
    design: id and name only, plus the staff number where the caller has it.
    A credential can never travel through this shape.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(examples=["Vikram Rao"])
    emp_id: str | None = None
