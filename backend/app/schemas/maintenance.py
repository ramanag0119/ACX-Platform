"""Read and write schemas for Services Planning (`maintenance_request`).

Every field below exists on one of the four maintenance tables. Nothing is
added for the frontend's convenience: where the screen wants something the
schema has no column for, the gap is recorded in the module docstring of
`app/services/maintenance_write.py` rather than filled in.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UserRef

#: The three Services Planning tabs -- the real `maintenance_request_type` enum.
MaintenanceRequestType = Literal["scheduled", "planned", "disinfection"]
#: `recurrence_type` holds exactly one label.
RecurrenceType = Literal["weekly"]
DayLabel = Literal["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class RoomRef(BaseModel):
    """A room attached through `maintenance_request_amenity`."""

    model_config = ConfigDict(from_attributes=True)

    amenity_id: uuid.UUID
    room_name: str | None = None


class RecurrenceRead(BaseModel):
    """`maintenance_request_recurrence`, present only when the request recurs."""

    model_config = ConfigDict(from_attributes=True)

    recurrence_type: str
    #: The stored bitmask, as-is.
    days_of_week: int | None = None
    #: The same value decoded, so the UI need not know the bit layout.
    day_labels: list[str] = Field(default_factory=list)
    max_no_of_occurrences: int | None = None


class MaintenanceRequestRead(BaseModel):
    """One planned service.

    `service_type` / `service_type_name` are resolved THROUGH `category_id` --
    `maintenance_request` has no service-type column of its own.

    The two status columns are separate on purpose: `maintenance_request_status`
    (+ `status_name`) is the lifecycle, `status` is the soft-delete flag.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    maintenance_request_type: str
    maintenance_start_date: date | None = None
    maintenance_end_date: date | None = None
    maintenance_start_time: datetime | None = None
    maintenance_end_time: datetime | None = None
    is_recurring: int | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    service_type: int | None = None
    service_type_name: str | None = None
    item_id: uuid.UUID | None = None
    item_name: str | None = None
    facility_id: uuid.UUID | None = None
    completed_on: datetime | None = None
    is_room: int | None = None
    non_room_comments: str | None = None
    parent_id: uuid.UUID | None = None
    maintenance_request_status: int
    status_name: str | None = None
    status_reason: str | None = None
    delete_comments: str | None = None
    under_maintenance: bool | None = None
    status: int | None = None
    created_on: datetime
    updated_on: datetime

    # Assembled from the three child tables.
    rooms: list[RoomRef] = Field(default_factory=list)
    assignees: list[UserRef] = Field(default_factory=list)
    recurrence: RecurrenceRead | None = None
    room_count: int = 0
    assignee_count: int = 0


# ---------------------------------------------------------------------------
# Write bodies
# ---------------------------------------------------------------------------


class Body(BaseModel):
    """Rejects unknown keys, so a typo is a 422 rather than a silent no-op."""

    model_config = ConfigDict(extra="forbid")


class RecurrenceWrite(Body):
    """A recurrence rule.

    Give either `days_of_week` (the raw bitmask, Sunday = 1) or `day_labels`
    (["Mon", "Thu"]); the service encodes the labels when the mask is omitted.
    """

    recurrence_type: RecurrenceType = "weekly"
    days_of_week: int | None = Field(default=None, ge=0, le=127)
    day_labels: list[DayLabel] | None = None
    max_no_of_occurrences: int | None = Field(default=None, ge=1, le=32767)


class MaintenanceRequestCreate(Body):
    """Create a planned service.

    `facility_id`, `is_room`, `maintenance_request_status`, `status`,
    `created_by` and `updated_by` are NOT accepted: they are derived from the
    authenticated caller and the payload, never sent by the client.
    """

    maintenance_request_type: MaintenanceRequestType
    maintenance_start_date: date | None = None
    maintenance_end_date: date | None = None
    maintenance_start_time: datetime | None = None
    maintenance_end_time: datetime | None = None
    department_id: uuid.UUID | None = None
    #: "Facility Services" on the form -- a `service_category` row.
    category_id: uuid.UUID | None = None
    #: The category's item, when the form narrows to one.
    item_id: uuid.UUID | None = None
    under_maintenance: bool | None = None
    non_room_comments: str | None = Field(default=None, max_length=2000)
    amenity_ids: list[uuid.UUID] = Field(default_factory=list)
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)
    recurrence: RecurrenceWrite | None = None

    @model_validator(mode="after")
    def _rooms_or_comments(self):
        """`is_room` is derived, so the payload must say which shape it is."""
        if not self.amenity_ids and not self.non_room_comments:
            raise ValueError(
                "Provide amenity_ids, or non_room_comments for a non-room service."
            )
        return self


class MaintenanceRequestUpdate(Body):
    """Partial update. Only the fields sent are written.

    Sending `recurrence: null` DROPS the rule; omitting the key leaves it alone.
    Sending `amenity_ids` or `assignee_ids` REPLACES that list.
    """

    maintenance_request_type: MaintenanceRequestType | None = None
    maintenance_start_date: date | None = None
    maintenance_end_date: date | None = None
    maintenance_start_time: datetime | None = None
    maintenance_end_time: datetime | None = None
    department_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    under_maintenance: bool | None = None
    non_room_comments: str | None = Field(default=None, max_length=2000)
    #: `service_status.id`: 1 Pending, 2 Assigned, 3 Partially completed,
    #: 4 Completed, 5 Canceled.
    maintenance_request_status: int | None = Field(default=None, ge=1)
    status_reason: str | None = Field(default=None, max_length=100)
    amenity_ids: list[uuid.UUID] | None = None
    assignee_ids: list[uuid.UUID] | None = None
    recurrence: RecurrenceWrite | None = None


class CancelBody(Body):
    reason: str | None = Field(default=None, max_length=100)


class RemoveBody(Body):
    """The soft delete's audit note -> `maintenance_request.delete_comments`."""

    comments: str | None = Field(default=None, max_length=2000)
