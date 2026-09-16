"""Stay (reservation) and invoice read APIs (Phase 2.8).

    GET /api/v1/stays                      · /{id}     stay
    GET /api/v1/stays/{id}/occupants                   stay_user
    GET /api/v1/stays/{id}/room-allocations            room_allocation
    GET /api/v1/stays/{id}/documents                   user_document
    GET /api/v1/invoices                   · /{id}     invoice

NOT IMPLEMENTED, and why:

    /bookings  -- Schema does not contain this concept. There is no `booking`
                  or `reservation` table; `stay` IS the reservation, and
                  booking / check-in / check-out / cancellation are states of
                  `stay.status`. A /bookings route would be an alias inventing
                  an entity the database does not have.

    /guests    -- Schema does not contain this concept. A guest is an
                  `app_user` row with `is_staff = 0`, already served by
                  `GET /api/v1/users?is_staff=0` from Phase 2.3. Guest identity
                  is resolved inline here (booker, occupants) so occupancy
                  staff who lack the `employees` grant can still see who is in
                  the room.

RBAC: `read` on `bookings` -- the module the sidebar registry uses for the
Bookings screen. 401 without a token, 403 without the grant.

READ-ONLY. See the final report for the blockers on check-in/check-out writes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import (
    DocumentApprovalStatus,
    RequestSource,
    StayStatus,
)
from app.schemas.health import ErrorResponse
from app.schemas.stay import (
    InvoiceRead,
    InvoiceRef,
    RoomAllocationRead,
    StayDetail,
    StayDocumentRead,
    StayOccupantRead,
    StayPackageRead,
    StayRead,
)
from app.services import stay as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

BOOKINGS_READ = [Depends(require_permission("bookings", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

stays_router = APIRouter(
    prefix="/stays", tags=["stays"],
    dependencies=BOOKINGS_READ, responses=AUTH_RESPONSES,
)
invoices_router = APIRouter(
    prefix="/invoices", tags=["stays"],
    dependencies=BOOKINGS_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# stay
# ---------------------------------------------------------------------------


@stays_router.get(
    "",
    response_model=Page[StayRead],
    summary="List stays (reservations)",
    description=(
        "`stay` is the reservation: booking, check-in, check-out and "
        "cancellation are all states of `stay.status`. `stay` carries no "
        "facility column, so facility/building/floor filters resolve through "
        "room_allocation -> amenity -> property_chain."
    ),
)
def list_stays(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    status_value: StayStatus | None = Query(
        None, alias="status", description="stay_status enum label",
    ),
    request_source: RequestSource | None = Query(
        None, description="request_source: ikanos | porta"
    ),
    document_approval_status: DocumentApprovalStatus | None = Query(
        None, description="document_approval_status: pending | approved"
    ),
    booking_user_id: uuid.UUID | None = Query(None, description="Who booked"),
    guest_id: uuid.UUID | None = Query(None, description="Any occupant, via stay_user"),
    facility_id: uuid.UUID | None = Query(None, description="Via room_allocation"),
    room_id: uuid.UUID | None = Query(None, description="Via room_allocation"),
    building_id: uuid.UUID | None = Query(None),
    floor_id: uuid.UUID | None = Query(None),
    is_checked_in: bool | None = Query(None, description="actual_checkin_time IS NOT NULL"),
    is_in_house: bool | None = Query(
        None, description="Checked in and not yet checked out"
    ),
    ref_number: str | None = Query(None, description="Exact internal_stay_ref_number"),
    expected_checkin_from: datetime | None = Query(None),
    expected_checkin_to: datetime | None = Query(None),
    expected_checkout_from: datetime | None = Query(None),
    expected_checkout_to: datetime | None = Query(None),
) -> Page[StayRead]:
    rows, total = svc.list_stays(
        db, page=page, page_size=page_size, status=status_value,
        request_source=request_source,
        document_approval_status=document_approval_status,
        booking_user_id=booking_user_id, guest_id=guest_id,
        facility_id=facility_id, room_id=room_id, building_id=building_id,
        floor_id=floor_id, is_checked_in=is_checked_in, is_in_house=is_in_house,
        ref_number=ref_number,
        expected_checkin_from=expected_checkin_from,
        expected_checkin_to=expected_checkin_to,
        expected_checkout_from=expected_checkout_from,
        expected_checkout_to=expected_checkout_to,
    )
    return Page[StayRead](
        items=[StayRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@stays_router.get(
    "/{stay_id}",
    response_model=StayDetail,
    responses=NOT_FOUND,
    summary="Get a stay with occupants, rooms, packages, documents and invoices",
)
def get_stay(stay_id: uuid.UUID, db: DbSession) -> StayDetail:
    row = svc.get_stay(db, stay_id)
    if row is None:
        raise _missing("Stay", stay_id)
    return StayDetail(
        **StayRead.model_validate(row).model_dump(),
        occupants=[
            StayOccupantRead.model_validate(o) for o in svc.stay_occupants(db, stay_id)
        ],
        room_allocations=[
            RoomAllocationRead.model_validate(a)
            for a in svc.stay_room_allocations(db, stay_id)
        ],
        packages=[
            StayPackageRead.model_validate(p) for p in svc.stay_packages(db, stay_id)
        ],
        documents=[
            StayDocumentRead.model_validate(d) for d in svc.stay_documents(db, stay_id)
        ],
        invoices=[
            InvoiceRef.model_validate(i) for i in svc.stay_invoice_refs(db, stay_id)
        ],
    )


@stays_router.get(
    "/{stay_id}/occupants",
    response_model=list[StayOccupantRead],
    responses=NOT_FOUND,
    summary="Occupants of a stay",
    description="`stay_user` rows. Guest identity is id and name only.",
)
def get_stay_occupants(stay_id: uuid.UUID, db: DbSession) -> list[StayOccupantRead]:
    if not svc.stay_exists(db, stay_id):
        raise _missing("Stay", stay_id)
    return [StayOccupantRead.model_validate(o) for o in svc.stay_occupants(db, stay_id)]


@stays_router.get(
    "/{stay_id}/room-allocations",
    response_model=list[RoomAllocationRead],
    responses=NOT_FOUND,
    summary="Rooms assigned to a stay",
    description=(
        "`room_allocation` rows. A re-allocation writes a new row, so this is "
        "the assignment history, not a single current room."
    ),
)
def get_stay_room_allocations(
    stay_id: uuid.UUID, db: DbSession
) -> list[RoomAllocationRead]:
    if not svc.stay_exists(db, stay_id):
        raise _missing("Stay", stay_id)
    return [
        RoomAllocationRead.model_validate(a) for a in svc.stay_room_allocations(db, stay_id)
    ]


@stays_router.get(
    "/{stay_id}/documents",
    response_model=list[StayDocumentRead],
    responses=NOT_FOUND,
    summary="Guest ID documents attached to a stay",
    description=(
        "Only the attachment pointer and approval state. There is no document "
        "type or number column in the schema."
    ),
)
def get_stay_documents(stay_id: uuid.UUID, db: DbSession) -> list[StayDocumentRead]:
    if not svc.stay_exists(db, stay_id):
        raise _missing("Stay", stay_id)
    return [StayDocumentRead.model_validate(d) for d in svc.stay_documents(db, stay_id)]


# ---------------------------------------------------------------------------
# invoice
# ---------------------------------------------------------------------------


@invoices_router.get(
    "",
    response_model=Page[InvoiceRead],
    summary="List invoices",
    description=(
        "`invoice` has NO status column -- payment state has no source in the "
        "schema (OPEN DECISION #10, unresolved). Amounts are returned as "
        "stored."
    ),
)
def list_invoices(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    stay_id: uuid.UUID | None = Query(None),
    facility_id: uuid.UUID | None = Query(None),
    billing_user_id: uuid.UUID | None = Query(None),
    invoice_number: str | None = Query(None),
    invoice_date_from: datetime | None = Query(None),
    invoice_date_to: datetime | None = Query(None),
) -> Page[InvoiceRead]:
    rows, total = svc.list_invoices(
        db, page=page, page_size=page_size, stay_id=stay_id,
        facility_id=facility_id, billing_user_id=billing_user_id,
        invoice_number=invoice_number, invoice_date_from=invoice_date_from,
        invoice_date_to=invoice_date_to,
    )
    return Page[InvoiceRead](
        items=[InvoiceRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@invoices_router.get(
    "/{invoice_id}",
    response_model=InvoiceRead,
    responses=NOT_FOUND,
    summary="Get an invoice",
)
def get_invoice(invoice_id: uuid.UUID, db: DbSession) -> InvoiceRead:
    row = svc.get_invoice(db, invoice_id)
    if row is None:
        raise _missing("Invoice", invoice_id)
    return InvoiceRead.model_validate(row)
