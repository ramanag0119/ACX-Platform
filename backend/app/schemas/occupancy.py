"""Response models for the room-centric occupancy view.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * **There is no `occupancy` table.** Occupancy is a room-centric READ over
    `amenity`, joined to its status lookup, its active conditions, and the
    stay currently allocated to it.

  * A room's state is carried by TWO independent mechanisms:
      - `amenity.status`  -> `amenity_status` (0 Available, 1 Occupied,
                             2 Unavailable, 3 Allotted)
      - the stay/allocation graph (room_allocation -> stay)

    **Nothing in the schema keeps those two in agreement**, and in the seeded
    data they disagree: 5 amenities are flagged Occupied while only 3 have a
    guest actually in house. Both are reported exactly as stored --
    `status` / `status_name` from the amenity row, `current_stay` derived from
    the stay columns. They are deliberately NOT reconciled.

  * `current_stay` means: a room_allocation whose stay has
    `actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL`. That is
    a factual reading of two real columns, not an invented occupancy rule.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AmenityStatusRead(ORMModel):
    """A row of `amenity_status`. Seeded with the real IKANOS ids, 0 included."""

    id: int = Field(examples=[0])
    amenity_status_name: str = Field(examples=["Available"])
    created_on: datetime
    updated_on: datetime


class AmenityConditionRead(ORMModel):
    """A row of `amenity_condition` or status-specific applicable condition option."""

    id: int = Field(examples=[3])
    name: str = Field(examples=["Under maintenance"])
    display_name: str | None = Field(default=None, examples=["Under Maintenance"])
    is_active: bool = Field(default=True)
    is_applicable: bool = Field(default=True)
    blocks_checkin: bool = Field(default=False)
    blocks_readiness: bool = Field(default=False)
    created_on: datetime | None = None
    updated_on: datetime | None = None



class OccupantRef(ORMModel):
    guest: UserRef
    is_key_required: int | None = None


class CurrentStayRef(ORMModel):
    """The stay currently in house in this room, if any."""

    stay_id: uuid.UUID
    internal_stay_ref_number: str
    status: str | None = None
    booker: UserRef | None = None
    expected_checkin_time: datetime
    expected_checkout_time: datetime
    actual_checkin_time: datetime | None = None
    no_of_guests: int


class OccupancyRead(ORMModel):
    """One room and everything the schema knows about its current occupancy."""

    amenity_id: uuid.UUID
    room_name: str = Field(examples=["101"])
    amenity_type_id: uuid.UUID
    amenity_type_name: str | None = Field(default=None, examples=["Guest Room"])
    amenity_category: str | None = Field(
        default=None, examples=["room"], description="room | restaurant | others"
    )
    package_id: uuid.UUID
    package_name: str | None = None

    status: int | None = Field(default=None, description="amenity_status.id")
    status_name: str | None = Field(default=None, examples=["Occupied"])
    occupancy_status: str | None = Field(
        default=None,
        examples=["Available"],
        description="Authoritative derived occupancy category: Available | Occupied | Allotted | Unavailable",
    )
    occupancy_status_id: int | None = Field(
        default=None,
        examples=[0],
        description="Authoritative derived occupancy status ID: 0 Available | 1 Occupied | 2 Unavailable | 3 Allotted",
    )
    room_status: str | None = Field(
        default=None,
        examples=["Ready to Occupy"],
        description="Authoritative unified Room Status: Ready to Occupy | Need Maintenance | Under Maintenance | Sanitation | Low Battery",
    )
    room_status_id: int | None = Field(
        default=None,
        examples=[5],
        description="Authoritative unified Room Status ID from amenity_condition",
    )
    conditions: list[AmenityConditionRead] = Field(
        default_factory=list, description="Active rows from amenity_condition_status"
    )

    facility_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None

    is_dnd: int | None = None
    power_save_mode: int | None = None

    current_stay: CurrentStayRef | None = Field(
        default=None,
        description=(
            "Derived from room_allocation + stay check-in/out timestamps. "
            "May be null even when `status_name` says Occupied -- the schema "
            "does not keep the two in step, and neither does this API."
        ),
    )
    allocation_count: int = Field(description="Total room_allocation rows, all time")


class OccupancyDetail(OccupancyRead):
    occupants: list[OccupantRef] = Field(
        description="stay_user rows for the current in-house stay"
    )
    device_count: int = Field(description="Devices installed in this room")


class OccupancyStatusSummary(BaseModel):
    status_id: int | None = None
    status: str
    count: int
    percent: float


class DailyOccupancyMetrics(BaseModel):
    target_date: date
    start_of_day: int
    start_of_day_percent: float
    realized_check_in: int
    realized_check_in_percent: float
    realized_check_out: int
    realized_check_out_percent: float
    current_status: int
    current_status_percent: float
    expected_check_in: int
    expected_check_in_percent: float
    expected_check_out: int
    expected_check_out_percent: float
    end_of_day: int
    end_of_day_percent: float


class OccupancyDailyPoint(BaseModel):
    metric_date: date
    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    occupancy_percent: float
    check_ins: int
    check_outs: int
    has_data: bool


class OccupancySummaryRead(BaseModel):
    total_rooms: int
    occupied: int
    available: int
    allotted: int
    unavailable: int
    unknown: int
    unclassified: int = 0
    occupied_percent: float
    available_percent: float
    allotted_percent: float
    unavailable_percent: float
    unknown_percent: float
    unclassified_percent: float = 0.0
    by_status: list[OccupancyStatusSummary]
    daily_metrics: DailyOccupancyMetrics
