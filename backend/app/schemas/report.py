"""Report response shapes.

A report row is deliberately an open mapping rather than a fixed model: the
columns differ per report and are declared in `app.services.reports`, so the
column list travels WITH the data. The frontend renders whatever columns it is
given, which is what keeps the on-screen table and the exported spreadsheet
from drifting apart.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportColumnOut(BaseModel):
    """One column, as the UI should render it."""

    key: str
    header: str
    #: text | number | date | datetime | boolean -- drives alignment and format.
    kind: str = "text"


class ReportFilterOut(BaseModel):
    """A filter the report accepts."""

    name: str
    label: str
    kind: str = "text"
    #: The existing list endpoint a `select` draws its options from, when the
    #: options come from a real table rather than a fixed enum.
    options_from: str | None = None


class ReportInfo(BaseModel):
    """A report's identity and shape, without any rows."""

    key: str
    title: str
    #: The PostgreSQL tables behind it, printed in the report header.
    source: str
    description: str = ""
    columns: list[ReportColumnOut] = Field(default_factory=list)
    filters: list[ReportFilterOut] = Field(default_factory=list)


class ReportPage(BaseModel):
    """A page of report rows, with the columns needed to render them."""

    key: str
    title: str
    source: str
    description: str = ""
    columns: list[ReportColumnOut] = Field(default_factory=list)
    #: Row values keyed by `ReportColumnOut.key`. Only declared columns appear.
    items: list[dict[str, Any]] = Field(default_factory=list)
    #: Echoes the filters that produced this page, so a header or a footer can
    #: state what the reader is looking at.
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0, description="Rows matching the filters")
