"""Response shapes for the Caleido At Work operational KPIs.

`percentage` is deliberately nullable. A ring with no computable ratio (no
mapped smart rooms, no requests raised today) must render as "-" and NOT as
0 %, so the schema refuses to supply a zero the data does not support.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class OperationalKPIRead(BaseModel):
    """One Caleido At Work ring."""

    key: str = Field(
        description="Stable identifier: smart_rooms_online | service_request_status "
        "| rooms_for_checkout | pending_bookings",
        examples=["rooms_for_checkout"],
    )
    label: str = Field(description="Display label", examples=["Rooms For Check-Out"])
    semantics: str = Field(
        description=(
            "`live` -- a current operational state, unaffected by the window. "
            "`period` -- activity inside the selected window."
        ),
        examples=["live"],
    )
    source: str = Field(description="Owning data source", examples=["BSS", "BSS+OSS"])

    available: bool = Field(
        description="False when the figure cannot be computed at all. A genuine "
        "zero is available=True with numerator=0 -- the two are never conflated."
    )
    unavailable_reason: str | None = Field(
        default=None, description="Why the KPI could not be computed, for the UI to show"
    )

    numerator: int | None = Field(default=None, description="e.g. rooms online")
    denominator: int | None = Field(default=None, description="e.g. mapped smart rooms")
    percentage: int | None = Field(
        default=None,
        description="numerator/denominator as a percent. NULL when the denominator "
        "is 0 or the KPI is unavailable -- never a substituted 0.",
    )
    count: int | None = Field(default=None, description="Headline count for the label")
    detail: str = Field(default="", description="Short human-readable breakdown")

    window_from: date | None = Field(default=None, description="Inclusive window start")
    window_to: date | None = Field(default=None, description="Inclusive window end")


class OperationalKPIsRead(BaseModel):
    """The whole Caleido At Work payload: four rings plus the window applied."""

    range: str = Field(description="today | week | month", examples=["today"])
    period_from: date
    period_to: date
    generated_at: datetime = Field(description="When the figures were computed")
    kpis: list[OperationalKPIRead]
