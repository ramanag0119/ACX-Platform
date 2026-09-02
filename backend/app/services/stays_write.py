"""Write logic for stays, room allocation and room state.

THE ROOM-STATE MAPPING IS READ OUT OF THE SEEDED DATA, NOT INVENTED. Every
seeded stay agrees on it:

    stay 'pending',          allocated, not checked in  -> amenity.status 3 Allotted
    stay 'active',           checked in                 -> amenity.status 1 Occupied
    stay 'checkout pending', checked in                 -> amenity.status 1 Occupied
    stay 'checked out'                                  -> amenity.status 0 Available
    stay 'cancelled'                                    -> no allocation at all

So: allocating a room marks it Allotted, checking in marks it Occupied,
checking out and cancelling release it to Available. `room_allocation.status` is
1 in every seeded row and is therefore left at 1 -- inventing a second value
would be guessing.

Other facts the schema fixes:

* `stay.status` is the `stay_status` enum: pending | active | checkout accepted
  | checkout pending | checkout rejected | checked out | cancelled.
* `internal_stay_ref_number` follows the seeded STY-YYYY-NNNN format.
* Occupants are `stay_user` rows; guests are `app_user` with is_staff = 0.
  There is no guest table and no booking table.
* A room cannot be double-booked: an allocation to a room already held by
  another stay that has not checked out is a 409.

NOT IMPLEMENTED, and why:
* Invoice generation. `invoice` stores net_amount / total_tax / total_amount but
  the schema encodes no tariff, no room rate (`package` has no price) and no tax
  rate, so the amounts cannot be derived. Reported as a business-rule gap.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AppUser,
    Package,
    RoomAllocation,
    Stay,
    StayUser,
)
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    next_yearly_reference,
    require_exists,
    require_row,
    transaction,
)

#: `amenity_status` ids as seeded: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted.
ROOM_AVAILABLE = 0
ROOM_OCCUPIED = 1
ROOM_UNAVAILABLE = 2
ROOM_ALLOTTED = 3

#: `stay_status` enum labels.
STAY_PENDING = "pending"
STAY_ACTIVE = "active"
STAY_CHECKOUT_PENDING = "checkout pending"
STAY_CHECKOUT_ACCEPTED = "checkout accepted"
STAY_CHECKOUT_REJECTED = "checkout rejected"
STAY_CHECKED_OUT = "checked out"
STAY_CANCELLED = "cancelled"

#: Statuses that still hold their rooms.
LIVE_STAY_STATUSES = (
    STAY_PENDING,
    STAY_ACTIVE,
    STAY_CHECKOUT_PENDING,
    STAY_CHECKOUT_ACCEPTED,
    STAY_CHECKOUT_REJECTED,
)

ALLOCATION_ACTIVE = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_room_status(db: Session, room_id: uuid.UUID, status: int) -> None:
    room = db.get(Amenity, room_id)
    if room is None:
        raise Invalid(f"Room {room_id} does not exist.")
    if db.get(AmenityStatus, status) is None:
        raise Invalid(f"Amenity status {status} does not exist.")
    room.status = status


def _stay_rooms(db: Session, stay_id: uuid.UUID) -> list[RoomAllocation]:
    return list(
        db.execute(
            select(RoomAllocation).where(RoomAllocation.stay_id == stay_id)
        ).scalars()
    )


def _assert_room_free(
    db: Session, room_id: uuid.UUID, *, ignore_stay_id: uuid.UUID | None = None
) -> None:
    """A room held by another live stay cannot be allocated again."""
    stmt = (
        select(Stay.internal_stay_ref_number)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(RoomAllocation.room_id == room_id)
        .where(Stay.status.in_(LIVE_STAY_STATUSES))
    )
    if ignore_stay_id is not None:
        stmt = stmt.where(Stay.id != ignore_stay_id)
    clash = db.execute(stmt).scalars().first()
    if clash:
        raise Conflict(f"That room is already allocated to stay {clash}.")


def _refresh_room_count(db: Session, stay: Stay) -> None:
    """`stay.no_of_rooms` is a stored column; keep it equal to the allocations."""
    stay.no_of_rooms = len(_stay_rooms(db, stay.id))


# ---------------------------------------------------------------------------
# Stays
# ---------------------------------------------------------------------------


def create_stay(
    db: Session, *, data: dict, actor_id: uuid.UUID
) -> Stay:
    """Create a reservation. This is what the Bookings screen calls a booking."""
    room_ids: list[uuid.UUID] = data.pop("room_ids", None) or []
    occupant_ids: list[uuid.UUID] = data.pop("occupant_ids", None) or []

    with transaction(db):
        require_exists(db, AppUser, data["booking_user_id"], "Booking user")

        if data["expected_checkout_time"] <= data["expected_checkin_time"]:
            raise Invalid("Expected check-out must be after expected check-in.")

        ref = data.pop("internal_stay_ref_number", None) or next_yearly_reference(
            db, Stay.internal_stay_ref_number, "STY", year=datetime.now(UTC).year
        )
        ensure_unique(db, Stay, Stay.internal_stay_ref_number, ref, "Stay reference")

        stay = Stay(
            id=uuid.uuid4(),
            internal_stay_ref_number=ref,
            status=data.pop("status", None) or STAY_PENDING,
            request_source=data.pop("request_source", None) or "ikanos",
            created_by=actor_id,
            modified_by=actor_id,
            **data,
        )
        db.add(stay)
        db.flush()

        for room_id in room_ids:
            _allocate(db, stay, room_id, package_id=None, actor_id=actor_id)
        for guest_id in occupant_ids:
            _add_occupant(db, stay, guest_id, room_id=None, actor_id=actor_id)

        _refresh_room_count(db, stay)

    db.refresh(stay)
    return stay


def update_stay(
    db: Session, stay_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> Stay:
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        require_exists(db, AppUser, changes.get("booking_user_id"), "Booking user")

        checkin = changes.get("expected_checkin_time", stay.expected_checkin_time)
        checkout = changes.get("expected_checkout_time", stay.expected_checkout_time)
        if checkout <= checkin:
            raise Invalid("Expected check-out must be after expected check-in.")

        apply_changes(stay, changes)
        stay.modified_by = actor_id
    db.refresh(stay)
    return stay


def check_in(
    db: Session, stay_id: uuid.UUID, *, actor_id: uuid.UUID, when: datetime | None = None
) -> Stay:
    """Check a stay in: stamp the arrival, activate it, occupy its rooms."""
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")

        if stay.actual_checkin_time is not None:
            raise Conflict("This stay is already checked in.")
        if stay.status in (STAY_CANCELLED, STAY_CHECKED_OUT):
            raise Conflict(f"A stay with status '{stay.status}' cannot be checked in.")

        allocations = _stay_rooms(db, stay_id)
        if not allocations:
            raise Invalid("Allocate a room before checking this stay in.")

        stay.actual_checkin_time = when or datetime.now(UTC)
        stay.status = STAY_ACTIVE
        stay.modified_by = actor_id

        for allocation in allocations:
            _set_room_status(db, allocation.room_id, ROOM_OCCUPIED)

    db.refresh(stay)
    return stay


def check_out(
    db: Session, stay_id: uuid.UUID, *, actor_id: uuid.UUID, when: datetime | None = None
) -> Stay:
    """Check a stay out: stamp the departure, close it, release its rooms.

    Room condition is deliberately NOT touched: `amenity_condition` has a
    'Dirty' row, but no seeded stay links check-out to a condition change, so
    setting one would be an invented rule. Housekeeping sets conditions
    explicitly through the occupancy endpoint.
    """
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")

        if stay.actual_checkin_time is None:
            raise Conflict("This stay has not been checked in.")
        if stay.actual_checkout_time is not None:
            raise Conflict("This stay is already checked out.")

        stay.actual_checkout_time = when or datetime.now(UTC)
        stay.status = STAY_CHECKED_OUT
        stay.checkout_initiated_by = actor_id
        stay.modified_by = actor_id

        for allocation in _stay_rooms(db, stay_id):
            _set_room_status(db, allocation.room_id, ROOM_AVAILABLE)

    db.refresh(stay)
    return stay


def extend_stay(
    db: Session, stay_id: uuid.UUID, *, expected_checkout_time: datetime, actor_id: uuid.UUID
) -> Stay:
    """Push the expected departure out. Only that one column changes."""
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        if stay.actual_checkout_time is not None:
            raise Conflict("This stay has already checked out.")
        if expected_checkout_time <= stay.expected_checkout_time:
            raise Invalid(
                "The new check-out time must be later than the current one "
                f"({stay.expected_checkout_time.isoformat()})."
            )
        stay.expected_checkout_time = expected_checkout_time
        stay.modified_by = actor_id
    db.refresh(stay)
    return stay


def set_stay_status(
    db: Session, stay_id: uuid.UUID, *, status: str, actor_id: uuid.UUID
) -> Stay:
    """Move a stay along its checkout-approval statuses.

    The `stay_status` enum carries 'checkout pending', 'checkout accepted' and
    'checkout rejected', which is the approval flow the Bookings screen shows.
    Reaching a terminal state uses check_out()/cancel_stay() so the room state
    is always updated with it.
    """
    terminal = {STAY_CHECKED_OUT: "check_out", STAY_CANCELLED: "cancel_stay"}
    if status in terminal:
        raise Invalid(
            f"Use the {terminal[status]} action to move a stay to '{status}', "
            "so room state is released with it."
        )
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        if stay.status in (STAY_CHECKED_OUT, STAY_CANCELLED):
            raise Conflict(f"A stay with status '{stay.status}' is closed.")
        stay.status = status
        stay.modified_by = actor_id
    db.refresh(stay)
    return stay


def set_document_approval(
    db: Session, stay_id: uuid.UUID, *, approval_status: str, actor_id: uuid.UUID
) -> Stay:
    """Approve or reject the stay's documents (`document_approval_status`)."""
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        stay.document_approval_status = approval_status
        stay.modified_by = actor_id
    db.refresh(stay)
    return stay


def cancel_stay(
    db: Session, stay_id: uuid.UUID, *, actor_id: uuid.UUID
) -> Stay:
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        if stay.actual_checkin_time is not None:
            raise Conflict(
                "A checked-in stay cannot be cancelled; check it out instead."
            )
        if stay.status == STAY_CANCELLED:
            raise Conflict("This stay is already cancelled.")

        stay.status = STAY_CANCELLED
        stay.modified_by = actor_id
        for allocation in _stay_rooms(db, stay_id):
            _set_room_status(db, allocation.room_id, ROOM_AVAILABLE)
    db.refresh(stay)
    return stay


# ---------------------------------------------------------------------------
# Room allocation
# ---------------------------------------------------------------------------


def _allocate(
    db: Session,
    stay: Stay,
    room_id: uuid.UUID,
    *,
    package_id: uuid.UUID | None,
    actor_id: uuid.UUID,
) -> RoomAllocation:
    room = db.get(Amenity, room_id)
    if room is None:
        raise Invalid(f"Room {room_id} does not exist.")
    _assert_room_free(db, room_id, ignore_stay_id=stay.id)

    existing = db.execute(
        select(RoomAllocation)
        .where(RoomAllocation.stay_id == stay.id)
        .where(RoomAllocation.room_id == room_id)
    ).scalars().first()
    if existing is not None:
        raise Conflict("That room is already allocated to this stay.")

    if package_id is not None:
        require_exists(db, Package, package_id, "Package")

    allocation = RoomAllocation(
        id=uuid.uuid4(),
        stay_id=stay.id,
        room_id=room_id,
        # The room's own package is the one the schema knows about.
        package_id=package_id or room.package_id,
        status=ALLOCATION_ACTIVE,
        created_by=actor_id,
    )
    db.add(allocation)

    # Allotted before arrival, Occupied once the guest is in-house.
    _set_room_status(
        db, room_id, ROOM_OCCUPIED if stay.actual_checkin_time else ROOM_ALLOTTED
    )
    return allocation


def allocate_room(
    db: Session,
    stay_id: uuid.UUID,
    *,
    room_id: uuid.UUID,
    package_id: uuid.UUID | None,
    actor_id: uuid.UUID,
) -> RoomAllocation:
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        if stay.status in (STAY_CANCELLED, STAY_CHECKED_OUT):
            raise Conflict(f"A stay with status '{stay.status}' cannot take a room.")
        allocation = _allocate(db, stay, room_id, package_id=package_id, actor_id=actor_id)
        db.flush()
        _refresh_room_count(db, stay)
    db.refresh(allocation)
    return allocation


def reallocate_room(
    db: Session,
    allocation_id: uuid.UUID,
    *,
    room_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> RoomAllocation:
    """Move a stay from one room to another in a single transaction.

    The old room is released and the new one takes the state the old one had,
    so a partial move can never leave two rooms occupied by one stay.
    """
    with transaction(db):
        allocation = require_row(db, RoomAllocation, allocation_id, "Room allocation")
        stay = require_row(db, Stay, allocation.stay_id, "Stay")

        if room_id == allocation.room_id:
            raise Invalid("The stay is already in that room.")
        if stay.status in (STAY_CANCELLED, STAY_CHECKED_OUT):
            raise Conflict(f"A stay with status '{stay.status}' cannot be moved.")

        new_room = db.get(Amenity, room_id)
        if new_room is None:
            raise Invalid(f"Room {room_id} does not exist.")
        _assert_room_free(db, room_id, ignore_stay_id=stay.id)

        old_room_id = allocation.room_id
        allocation.room_id = room_id
        allocation.package_id = new_room.package_id

        _set_room_status(db, old_room_id, ROOM_AVAILABLE)
        _set_room_status(
            db, room_id, ROOM_OCCUPIED if stay.actual_checkin_time else ROOM_ALLOTTED
        )
        stay.modified_by = actor_id

    db.refresh(allocation)
    return allocation


def release_allocation(
    db: Session, allocation_id: uuid.UUID, *, actor_id: uuid.UUID
) -> None:
    with transaction(db):
        allocation = require_row(db, RoomAllocation, allocation_id, "Room allocation")
        stay = require_row(db, Stay, allocation.stay_id, "Stay")
        if stay.actual_checkin_time is not None and stay.actual_checkout_time is None:
            raise Conflict(
                "This stay is in-house; check it out before releasing the room."
            )
        room_id = allocation.room_id
        db.delete(allocation)
        db.flush()
        _set_room_status(db, room_id, ROOM_AVAILABLE)
        _refresh_room_count(db, stay)
        stay.modified_by = actor_id


# ---------------------------------------------------------------------------
# Occupants
# ---------------------------------------------------------------------------


def _add_occupant(
    db: Session,
    stay: Stay,
    guest_id: uuid.UUID,
    *,
    room_id: uuid.UUID | None,
    actor_id: uuid.UUID,
    is_key_required: int | None = None,
) -> StayUser:
    guest = db.get(AppUser, guest_id)
    if guest is None:
        raise Invalid(f"Guest {guest_id} does not exist.")
    existing = db.execute(
        select(StayUser)
        .where(StayUser.stay_id == stay.id)
        .where(StayUser.app_user_id == guest_id)
    ).scalars().first()
    if existing is not None:
        raise Conflict("That guest is already an occupant of this stay.")
    if room_id is not None:
        require_exists(db, Amenity, room_id, "Room")

    row = StayUser(
        id=uuid.uuid4(),
        stay_id=stay.id,
        app_user_id=guest_id,
        room_id=room_id,
        is_key_required=is_key_required,
        status=1,
        created_by=actor_id,
    )
    db.add(row)
    return row


def add_occupant(
    db: Session,
    stay_id: uuid.UUID,
    *,
    guest_id: uuid.UUID,
    room_id: uuid.UUID | None,
    is_key_required: int | None,
    actor_id: uuid.UUID,
) -> StayUser:
    with transaction(db):
        stay = require_row(db, Stay, stay_id, "Stay")
        row = _add_occupant(
            db, stay, guest_id, room_id=room_id, actor_id=actor_id,
            is_key_required=is_key_required,
        )
        db.flush()
        stay.no_of_guests = db.query(StayUser).filter(StayUser.stay_id == stay_id).count()
        stay.modified_by = actor_id
    db.refresh(row)
    return row


def remove_occupant(db: Session, occupant_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
    with transaction(db):
        row = require_row(db, StayUser, occupant_id, "Occupant")
        stay = require_row(db, Stay, row.stay_id, "Stay")
        db.delete(row)
        db.flush()
        stay.no_of_guests = db.query(StayUser).filter(StayUser.stay_id == stay.id).count()
        stay.modified_by = actor_id


# ---------------------------------------------------------------------------
# Room state (the Occupancy screen's own actions)
# ---------------------------------------------------------------------------


def update_room_state(
    db: Session,
    amenity_id: uuid.UUID,
    *,
    changes: dict,
) -> Amenity:
    """Set a room's status, DND flag or power-save flag.

    Guard rail: a room cannot be marked Available while a live stay still holds
    it, because that is the divergence Phase 2.8 found in the seeded data
    (rooms flagged Occupied with no in-house stay). Releasing a room goes
    through check-out or cancellation.
    """
    with transaction(db):
        room = require_row(db, Amenity, amenity_id, "Room")

        if "status" in changes:
            new_status = changes["status"]
            if db.get(AmenityStatus, new_status) is None:
                raise Invalid(f"Amenity status {new_status} does not exist.")
            if new_status in (ROOM_AVAILABLE, ROOM_UNAVAILABLE):
                holder = db.execute(
                    select(Stay.internal_stay_ref_number)
                    .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
                    .where(RoomAllocation.room_id == amenity_id)
                    .where(Stay.status.in_(LIVE_STAY_STATUSES))
                ).scalars().first()
                if holder:
                    raise Conflict(
                        f"Stay {holder} still holds this room; check it out first."
                    )

        apply_changes(room, changes)
    db.refresh(room)
    return room


def set_room_conditions(
    db: Session, amenity_id: uuid.UUID, *, condition_ids: list[int]
) -> list[int]:
    """Replace a room's conditions (`amenity_condition_status`).

    Housekeeping flags -- Dirty, Low battery, Under maintenance, Sanitation --
    are rows in a composite-key link table, so setting them means inserting and
    deleting rows, not writing a column.
    """
    with transaction(db):
        require_row(db, Amenity, amenity_id, "Room")
        for condition_id in condition_ids:
            if db.get(AmenityCondition, condition_id) is None:
                raise Invalid(f"Amenity condition {condition_id} does not exist.")

        current = {
            row.amenity_condition_id: row
            for row in db.execute(
                select(AmenityConditionStatus).where(
                    AmenityConditionStatus.amenity_id == amenity_id
                )
            ).scalars()
        }
        wanted = set(condition_ids)

        for condition_id, row in current.items():
            if condition_id not in wanted:
                db.delete(row)
        for condition_id in wanted - set(current):
            db.add(
                AmenityConditionStatus(
                    amenity_id=amenity_id, amenity_condition_id=condition_id, status=1
                )
            )
    return sorted(condition_ids)
