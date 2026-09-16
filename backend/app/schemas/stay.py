"""Response models for stays, occupants, room allocations and invoices.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * **There is no `booking` / `reservation` table.** `stay` IS the reservation.
    Booking, check-in, check-out and cancellation are all states of one row,
    carried by `stay.status`:
        pending · active · checkout accepted · checkout pending ·
        checkout rejected · checked out · cancelled

  * **There is no `guest` table.** A guest is an `app_user` row with
    `is_staff = 0`. `stay.booking_user_id -> app_user` names the booker, and
    `stay_user` lists every occupant.

  * **There are no `check_in` / `check_out` tables.** They are four columns on
    `stay`: expected_checkin_time, expected_checkout_time (both NOT NULL) and
    actual_checkin_time, actual_checkout_time (both nullable -- NULL means the
    step has not happened).

  * **`stay` has NO `facility_id`.** Facility is reached through
    room_allocation -> amenity -> facility, which is also why the facility
    filter is an EXISTS over allocations.

  * `room_allocation` is the stay-to-room assignment; a re-allocation writes a
    new row rather than mutating one.

NOT PRESENT, and therefore not exposed: room rate, tariff, payment state,
deposit, booking channel/source beyond `request_source` (ikanos | porta),
guest ID document type or number.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# stay_user -- occupants
# ---------------------------------------------------------------------------


class StayOccupantRead(ORMModel):
    """A row of `stay_user`. The occupant identity lives in `app_user`."""

    id: uuid.UUID
    guest: UserRef
    room_id: uuid.UUID | None = None
    room_name: str | None = Field(default=None, examples=["101"])
    is_key_required: int | None = Field(
        default=None, description="Drives digital key generation"
    )
    status: int | None = None
    created_on: datetime


# ---------------------------------------------------------------------------
# room_allocation
# ---------------------------------------------------------------------------


class RoomAllocationRead(ORMModel):
    """A row of `room_allocation` -- which room a stay was assigned."""

    id: uuid.UUID
    stay_id: uuid.UUID
    room_id: uuid.UUID
    room_name: str | None = Field(default=None, examples=["101"])
    amenity_type_name: str | None = None
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    facility_id: uuid.UUID | None = None
    package_id: uuid.UUID | None = None
    package_name: str | None = Field(
        default=None,
        examples=["Deluxe"],
        description="Package name only -- `package` has no price column",
    )
    status: int | None = None
    created_on: datetime
    updated_on: datetime


# ---------------------------------------------------------------------------
# user_document
# ---------------------------------------------------------------------------


class StayDocumentRead(ORMModel):
    """A row of `user_document` -- a guest ID scan and its approval state.

    Only the attachment POINTER is returned. There is no document type or
    document number column in the schema, so neither is exposed.
    """

    id: uuid.UUID
    guest: UserRef
    attachment_id: uuid.UUID
    document_approval_status: str | None = Field(
        default=None, description="approved | rejected | pending"
    )
    status: int | None = None
    created_on: datetime


# ---------------------------------------------------------------------------
# stay
# ---------------------------------------------------------------------------


class StayRead(ORMModel):
    """A row of `stay` -- the reservation."""

    id: uuid.UUID
    internal_stay_ref_number: str = Field(examples=["STY-2026-0001"])
    external_stay_ref_number: str | None = Field(
        default=None, description="PMS / OTA reference"
    )
    status: str | None = Field(examples=["active"])
    document_approval_status: str = Field(examples=["approved"])
    request_source: str | None = Field(
        default=None, examples=["ikanos"], description="ikanos | porta"
    )
    booker: UserRef | None = Field(
        default=None, description="stay.booking_user_id -- who made the booking"
    )
    no_of_rooms: int | None = None
    no_of_guests: int
    expected_checkin_time: datetime
    expected_checkout_time: datetime
    actual_checkin_time: datetime | None = Field(
        default=None, description="NULL until check-in happens"
    )
    actual_checkout_time: datetime | None = None
    is_checked_in: bool = Field(
        description="Derived: actual_checkin_time IS NOT NULL"
    )
    is_in_house: bool = Field(
        description=(
            "Derived: checked in and not yet checked out. This is a factual "
            "reading of two columns, not a business rule the schema encodes."
        )
    )
    gst: str | None = Field(default=None, description="Tax registration on the stay")
    comments: str | None = None
    checkout_initiated_by: uuid.UUID | None = None
    occupant_count: int
    room_count: int = Field(description="Rows in room_allocation")
    created_on: datetime
    updated_on: datetime


class StayDetail(StayRead):
    occupants: list[StayOccupantRead]
    room_allocations: list[RoomAllocationRead]
    packages: list["StayPackageRead"]
    documents: list[StayDocumentRead]
    invoices: list["InvoiceRef"]


class StayPackageRead(ORMModel):
    """A row of `stay_package`."""

    id: uuid.UUID
    package_id: uuid.UUID
    package_name: str | None = None
    status: int


class InvoiceRef(ORMModel):
    id: uuid.UUID
    invoice_number: str
    total_amount: Decimal | None = None


# ---------------------------------------------------------------------------
# invoice
# ---------------------------------------------------------------------------


class InvoiceRead(ORMModel):
    """A row of `invoice`.

    There is NO `status` column: payment state has no source in the schema
    (OPEN DECISION #10, still unresolved). The billing and facility snapshot
    columns are point-in-time copies IKANOS stores on the invoice itself.
    """

    id: uuid.UUID
    invoice_number: str = Field(examples=["INV-2026-0001"])
    invoice_date: datetime
    invoice_due_date: datetime | None = None
    stay_id: uuid.UUID
    stay_ref_number: str | None = None
    billing_user_id: uuid.UUID
    billing_user_name: str | None = Field(default=None, description="Snapshot")
    billing_address: str | None = Field(default=None, description="Snapshot")
    facility_id: uuid.UUID | None = None
    facility_name: str | None = Field(default=None, description="Snapshot")
    facility_address: str | None = Field(default=None, description="Snapshot")
    net_amount: Decimal | None = None
    total_tax: Decimal | None = None
    total_amount: Decimal | None = None
    created_on: datetime
    updated_on: datetime


StayDetail.model_rebuild()
