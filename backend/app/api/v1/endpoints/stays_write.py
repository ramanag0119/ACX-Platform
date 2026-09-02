"""Write endpoints for stays, allocation, occupants and room state.

    POST   /stays                            create a reservation
    PATCH  /stays/{id}                       edit it
    POST   /stays/{id}/check-in              arrival  -> rooms Occupied
    POST   /stays/{id}/check-out             departure -> rooms Available
    POST   /stays/{id}/extend                push the expected checkout
    POST   /stays/{id}/status                checkout-approval statuses
    POST   /stays/{id}/documents/approval    approve / reject documents
    POST   /stays/{id}/cancel                cancel  -> rooms Available
    POST   /stays/{id}/room-allocations      allocate a room -> Allotted
    PATCH  /room-allocations/{id}            REALLOCATE (old room released)
    DELETE /room-allocations/{id}            release a room
    POST   /stays/{id}/occupants             add an occupant
    DELETE /stay-occupants/{id}              remove one
    PATCH  /occupancy/{amenity_id}           room status / DND / power save
    PUT    /occupancy/{amenity_id}/conditions housekeeping conditions

Each of these is one PostgreSQL transaction: a check-in that cannot mark its
rooms Occupied does not record the arrival either.

RBAC: `bookings` write for the stay lifecycle (the Bookings screen),
`occupancy` write for room state (the Occupancy screen) -- exactly the modules
the matching read endpoints are gated on.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.facility import RoomRead
from app.schemas.health import ErrorResponse
from app.schemas.occupancy import OccupancyDetail
from app.schemas.ops_write import (
    AllocateRoomBody,
    CheckInBody,
    CheckOutBody,
    DocumentApprovalBody,
    ExtendStayBody,
    OccupantBody,
    ReallocateRoomBody,
    RoomConditionsBody,
    RoomStateUpdate,
    StayCreate,
    StayStatusBody,
    StayUpdate,
)
from app.schemas.stay import RoomAllocationRead, StayDetail, StayOccupantRead, StayRead
from app.services import facility as facility_read
from app.services import occupancy as occupancy_read
from app.services import stay as read_service
from app.services import stays_write as service

WRITE_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with current state"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}

BOOKINGS_WRITE = [Depends(require_permission("bookings", "write"))]
OCCUPANCY_WRITE = [Depends(require_permission("occupancy", "write"))]

stays_write_router = APIRouter(prefix="/stays", tags=["stays"], responses=WRITE_RESPONSES)
allocations_router = APIRouter(
    prefix="/room-allocations", tags=["stays"], responses=WRITE_RESPONSES
)
occupants_router = APIRouter(
    prefix="/stay-occupants", tags=["stays"], responses=WRITE_RESPONSES
)
occupancy_write_router = APIRouter(
    prefix="/occupancy", tags=["occupancy"], responses=WRITE_RESPONSES
)


def _stay_detail(db, stay_id: uuid.UUID) -> StayDetail:
    """Re-read through the read projection after every mutation."""
    row = read_service.get_stay(db, stay_id)
    occupants = read_service.stay_occupants(db, stay_id)
    allocations = read_service.stay_room_allocations(db, stay_id)
    return StayDetail(
        **StayRead.model_validate(row).model_dump(),
        occupants=occupants,
        room_allocations=allocations,
        packages=read_service.stay_packages(db, stay_id),
        documents=read_service.stay_documents(db, stay_id),
        invoices=read_service.stay_invoice_refs(db, stay_id),
    )


# ---------------------------------------------------------------------------
# Stay lifecycle
# ---------------------------------------------------------------------------


@stays_write_router.post(
    "",
    response_model=StayDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=BOOKINGS_WRITE,
    summary="Create a stay (reservation)",
    description=(
        "There is no booking table: a reservation IS a `stay`. Rooms listed in "
        "`room_ids` are allocated in the same transaction and become Allotted; "
        "guests in `occupant_ids` become `stay_user` rows. The reference "
        "follows the seeded STY-YYYY-NNNN format."
    ),
)
def create_stay(
    payload: StayCreate, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    stay = service.create_stay(
        db, data=payload.model_dump(), actor_id=current_user.id
    )
    return _stay_detail(db, stay.id)


@stays_write_router.patch(
    "/{stay_id}",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Update a stay",
)
def update_stay(
    stay_id: uuid.UUID, payload: StayUpdate, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.update_stay(
        db, stay_id, changes=payload.model_dump(exclude_unset=True), actor_id=current_user.id
    )
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/check-in",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Check a stay in",
    description=(
        "Stamps `actual_checkin_time`, moves the stay to 'active' and sets every "
        "allocated room to Occupied -- the state every seeded active stay is in. "
        "Rejected with 409 if already checked in, or 422 if no room is allocated."
    ),
)
def check_in(
    stay_id: uuid.UUID, payload: CheckInBody, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.check_in(db, stay_id, actor_id=current_user.id, when=payload.when)
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/check-out",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Check a stay out",
    description=(
        "Stamps `actual_checkout_time`, moves the stay to 'checked out' and "
        "releases every allocated room to Available."
    ),
)
def check_out(
    stay_id: uuid.UUID, payload: CheckOutBody, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.check_out(db, stay_id, actor_id=current_user.id, when=payload.when)
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/extend",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Extend the expected check-out",
)
def extend_stay(
    stay_id: uuid.UUID, payload: ExtendStayBody, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.extend_stay(
        db,
        stay_id,
        expected_checkout_time=payload.expected_checkout_time,
        actor_id=current_user.id,
    )
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/status",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Set a stay's status",
    description=(
        "For the checkout-approval statuses the `stay_status` enum carries. "
        "'checked out' and 'cancelled' are refused here and must go through "
        "check-out / cancel, so room state is always released with them."
    ),
)
def set_status(
    stay_id: uuid.UUID, payload: StayStatusBody, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.set_stay_status(db, stay_id, status=payload.status, actor_id=current_user.id)
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/documents/approval",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Approve or reject a stay's documents",
)
def set_document_approval(
    stay_id: uuid.UUID,
    payload: DocumentApprovalBody,
    db: DbSession,
    current_user: CurrentUser,
) -> StayDetail:
    service.set_document_approval(
        db,
        stay_id,
        approval_status=payload.document_approval_status,
        actor_id=current_user.id,
    )
    return _stay_detail(db, stay_id)


@stays_write_router.post(
    "/{stay_id}/cancel",
    response_model=StayDetail,
    dependencies=BOOKINGS_WRITE,
    summary="Cancel a stay",
    description="Refused with 409 once the guest has checked in -- check out instead.",
)
def cancel_stay(
    stay_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> StayDetail:
    service.cancel_stay(db, stay_id, actor_id=current_user.id)
    return _stay_detail(db, stay_id)


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------


@stays_write_router.post(
    "/{stay_id}/room-allocations",
    response_model=list[RoomAllocationRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=BOOKINGS_WRITE,
    summary="Allocate a room to a stay",
    description=(
        "Inserts `room_allocation` and marks the room Allotted (or Occupied if "
        "the stay is already in-house). A room held by another live stay is a "
        "409 -- the schema has no exclusion constraint, so the check is explicit."
    ),
)
def allocate_room(
    stay_id: uuid.UUID,
    payload: AllocateRoomBody,
    db: DbSession,
    current_user: CurrentUser,
) -> list[RoomAllocationRead]:
    service.allocate_room(
        db,
        stay_id,
        room_id=payload.room_id,
        package_id=payload.package_id,
        actor_id=current_user.id,
    )
    return read_service.stay_room_allocations(db, stay_id)


@allocations_router.patch(
    "/{allocation_id}",
    response_model=list[RoomAllocationRead],
    dependencies=BOOKINGS_WRITE,
    summary="Reallocate a stay to a different room",
    description=(
        "One transaction: the allocation moves, the old room goes Available and "
        "the new one takes the stay's current state. A partial move cannot occur."
    ),
)
def reallocate_room(
    allocation_id: uuid.UUID,
    payload: ReallocateRoomBody,
    db: DbSession,
    current_user: CurrentUser,
) -> list[RoomAllocationRead]:
    allocation = service.reallocate_room(
        db, allocation_id, room_id=payload.room_id, actor_id=current_user.id
    )
    return read_service.stay_room_allocations(db, allocation.stay_id)


@allocations_router.delete(
    "/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=BOOKINGS_WRITE,
    summary="Release a room from a stay",
)
def release_allocation(
    allocation_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> None:
    service.release_allocation(db, allocation_id, actor_id=current_user.id)


# ---------------------------------------------------------------------------
# Occupants
# ---------------------------------------------------------------------------


@stays_write_router.post(
    "/{stay_id}/occupants",
    response_model=list[StayOccupantRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=BOOKINGS_WRITE,
    summary="Add an occupant to a stay",
    description=(
        "`stay_user` row. Guests are `app_user` rows with is_staff = 0 -- create "
        "one through POST /users first if the guest is new."
    ),
)
def add_occupant(
    stay_id: uuid.UUID, payload: OccupantBody, db: DbSession, current_user: CurrentUser
) -> list[StayOccupantRead]:
    service.add_occupant(
        db,
        stay_id,
        guest_id=payload.guest_id,
        room_id=payload.room_id,
        is_key_required=payload.is_key_required,
        actor_id=current_user.id,
    )
    return read_service.stay_occupants(db, stay_id)


@occupants_router.delete(
    "/{occupant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=BOOKINGS_WRITE,
    summary="Remove an occupant from a stay",
)
def remove_occupant(
    occupant_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> None:
    service.remove_occupant(db, occupant_id, actor_id=current_user.id)


# ---------------------------------------------------------------------------
# Room state
# ---------------------------------------------------------------------------


@occupancy_write_router.patch(
    "/{amenity_id}",
    response_model=OccupancyDetail,
    dependencies=OCCUPANCY_WRITE,
    summary="Set a room's status or flags",
    description=(
        "Writes `amenity.status`, `is_dnd` and `power_save_mode`. Marking a room "
        "Available or Unavailable while a live stay still holds it is a 409: "
        "releasing a room goes through check-out or cancellation, which is what "
        "keeps room state and the stay graph in step."
    ),
)
def update_room_state(
    amenity_id: uuid.UUID, payload: RoomStateUpdate, db: DbSession
) -> OccupancyDetail:
    service.update_room_state(
        db, amenity_id, changes=payload.model_dump(exclude_unset=True)
    )
    return occupancy_read.get_occupancy(db, amenity_id)


@occupancy_write_router.put(
    "/{amenity_id}/conditions",
    response_model=RoomRead,
    dependencies=OCCUPANCY_WRITE,
    summary="Set a room's housekeeping conditions",
    description=(
        "Replaces the room's `amenity_condition_status` rows. Conditions are the "
        "four seeded ones: Dirty, Low battery, Under maintenance, Sanitation."
    ),
)
def set_room_conditions(
    amenity_id: uuid.UUID, payload: RoomConditionsBody, db: DbSession
) -> RoomRead:
    service.set_room_conditions(db, amenity_id, condition_ids=payload.condition_ids)
    return RoomRead.model_validate(facility_read.get_room(db, amenity_id))
