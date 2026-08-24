"""Read and write schemas for Job Order Management (`job_order`).

Every field below is a real column on one of the three job-order tables
(blueprint §5, tables 60-62). Where the Job Order screen asks for something the
schema has no column for, the gap is recorded in the module docstring of
`app/services/job_order_write.py` rather than invented here.

Two things the screen shows that are NOT columns:

* the room/device pairs on the create form -- `job_order_amenity` and
  `job_order_device` are two independent many-to-many tables, so a job order
  covers a SET of rooms and a SET of devices, not a list of pairs;
* `authentication_code`, which the form never asks for but the column requires
  NOT NULL -- derived on the server, see `job_order_write`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UserRef

#: The real `job_order_type_of_work` enum. "Fresh Installation" on the form is
#: `installation`; `troubleshoot` exists in the enum and in the seeded data even
#: though the current form offers no radio for it.
JobOrderTypeOfWork = Literal["installation", "replacement", "troubleshoot"]
#: The real `job_order_status` enum -- the work lifecycle, NOT the delete flag.
JobOrderStatus = Literal["pending", "completed"]


class JobOrderRoomRef(BaseModel):
    """A room attached through `job_order_amenity`."""

    model_config = ConfigDict(from_attributes=True)

    amenity_id: uuid.UUID
    room_name: str | None = None


class JobOrderDeviceRef(BaseModel):
    """A device attached through `job_order_device`.

    `device_type` / `device_type_name` come from the device's own row -- they are
    what the screen labels "Caleido Network".
    """

    model_config = ConfigDict(from_attributes=True)

    device_id: uuid.UUID
    device_uid: str | None = None
    device_name: str | None = None
    device_type: int | None = None
    device_type_name: str | None = None
    amenity_id: uuid.UUID | None = None
    room_name: str | None = None


class JobOrderRead(BaseModel):
    """One job order, with its rooms and devices attached.

    The two status columns are separate on purpose, exactly as on
    `maintenance_request`: `job_order_status` is the work lifecycle
    (pending / completed) and `status` is the soft-delete flag (1 live, 0 removed).

    `job_order` has no `facility_id` column -- scope is reached through
    `job_order_amenity -> amenity`, which is why none is returned here.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_reference: str
    description: str | None = None
    type_of_work: str
    work_commence: datetime
    estimated_completion_date: datetime
    # `authentication_code` is deliberately ABSENT. It is the technician's
    # on-site code -- a credential, exactly like `device.authentication_code` --
    # and `test_authentication_code_cannot_be_written` asserts no schema the API
    # accepts or returns mentions it. The column is still written on create
    # (it is NOT NULL); it is simply never exposed.
    assigned_to: uuid.UUID | None = None
    assignee: UserRef | None = None
    job_order_status: str
    completed_on: datetime | None = None
    status: int | None = None
    created_on: datetime
    updated_on: datetime

    # Assembled from the two link tables.
    rooms: list[JobOrderRoomRef] = Field(default_factory=list)
    devices: list[JobOrderDeviceRef] = Field(default_factory=list)
    room_count: int = 0
    device_count: int = 0


# ---------------------------------------------------------------------------
# Write bodies
# ---------------------------------------------------------------------------


class Body(BaseModel):
    """Rejects unknown keys, so a typo is a 422 rather than a silent no-op."""

    model_config = ConfigDict(extra="forbid")


class JobOrderCreate(Body):
    """Create a job order plus its room and device links.

    `amenity_ids` and `device_ids` are REAL UUIDs -- `amenity.id` and `device.id`
    respectively. A room number ("101") or a device-type name ("Kleio") is
    rejected by UUID parsing before it reaches the service layer.

    `order_reference` is optional: left out, the server continues the seeded
    `JO-YYYY-NNNN` sequence rather than making the user invent one.
    """

    order_reference: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=200)
    type_of_work: JobOrderTypeOfWork
    work_commence: datetime
    estimated_completion_date: datetime
    #: `job_order.assigned_to` -> `app_user.id`. Optional in the schema.
    assigned_to: uuid.UUID | None = None
    #: Rooms covered -> one `job_order_amenity` row each.
    amenity_ids: list[uuid.UUID] = Field(default_factory=list)
    #: Devices covered -> one `job_order_device` row each. Optional: the seeded
    #: `JO-2026-0001` covers two rooms and no devices.
    device_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.estimated_completion_date < self.work_commence:
            raise ValueError(
                "estimated_completion_date cannot be before work_commence."
            )
        return self


class JobOrderUpdate(Body):
    """Partial update. Only the keys sent are written.

    `amenity_ids` / `device_ids` REPLACE that whole list when present; omitting
    them leaves the existing links untouched.
    """

    order_reference: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=200)
    type_of_work: JobOrderTypeOfWork | None = None
    work_commence: datetime | None = None
    estimated_completion_date: datetime | None = None
    assigned_to: uuid.UUID | None = None
    job_order_status: JobOrderStatus | None = None
    amenity_ids: list[uuid.UUID] | None = None
    device_ids: list[uuid.UUID] | None = None
