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

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AppUser,
    Facility,
    FacilityUser,
    ImportJob,
    Package,
    RoomAllocation,
    RoomStatusConditionApplicability,
    Stay,
    StayUser,
)
from app.services.occupancy import determine_room_status_for_applicability
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    next_reference,
    next_yearly_reference,
    require_exists,
    require_row,
    transaction,
)

#: `amenity_status.amenity_status_name` values. The vocabulary this module
#: reasons about is the NAME; the id is resolved from the lookup table on every
#: use (see `_room_status_id`). Previously these were the literal ids 0-3
#: "as seeded", which made a reordered or re-seeded `amenity_status` table
#: silently write the wrong room state on check-in, check-out and reallocation.
ROOM_AVAILABLE = "Available"
ROOM_OCCUPIED = "Occupied"
ROOM_UNAVAILABLE = "Unavailable"
ROOM_ALLOTTED = "Allotted"

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


def _has_blocking_condition(db: Session, room_id: uuid.UUID) -> bool:
    """Check whether a room currently has an active blocking condition from DB configuration.

    Driven by `room_status_condition_applicability` where blocks_readiness=True
    or blocks_checkin=True for active conditions.
    """
    return db.execute(
        select(AmenityConditionStatus.amenity_id)
        .join(
            RoomStatusConditionApplicability,
            RoomStatusConditionApplicability.condition_id == AmenityConditionStatus.amenity_condition_id,
        )
        .where(
            AmenityConditionStatus.amenity_id == room_id,
            AmenityConditionStatus.status == 1,
            RoomStatusConditionApplicability.is_active == True,
            or_(
                RoomStatusConditionApplicability.blocks_readiness == True,
                RoomStatusConditionApplicability.blocks_checkin == True,
            ),
        )
    ).first() is not None


def sync_room_status_for_condition(
    db: Session,
    room: Amenity,
    target_condition_id: int,
    cond: AmenityCondition,
) -> None:
    """Synchronize room status (Amenity.status) with its operational condition.

    Business Rules:
    - If the room is Occupied (active in-house stay or stored status=Occupied):
      Preserve Occupied status. Operational issues can be recorded without altering
      current guest occupancy.
    - If the room is Allotted (pending allocation or stored status=Allotted):
      Preserve Allotted status.
    - If the room is not Occupied and not Allotted (vacant & unallocated):
      - If the condition is a blocking condition (blocks_readiness=True or blocks_checkin=True
        in room_status_condition_applicability, e.g. Under maintenance, Dirty, Sanitation):
        Transition room status to Unavailable.
      - If the condition is a readiness condition (e.g. Ready for occupant):
        Transition room status to Available.
      - If the condition is an operational device condition (e.g. Low Battery, Device Offline)
        that does not block readiness/checkin:
        Preserve the existing valid status (no unnecessary status mutation).
    """
    # Check for in-house stay
    in_house = db.execute(
        select(Stay.id)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id == room.id,
            Stay.actual_checkin_time.is_not(None),
            Stay.actual_checkout_time.is_(None),
        )
    ).first() is not None

    if room.status == _room_status_id(db, ROOM_OCCUPIED) or in_house:
        # Preserve Occupied status
        return

    # Check for pending allocation (Allotted)
    pending_alloc = db.execute(
        select(Stay.id)
        .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
        .where(
            RoomAllocation.room_id == room.id,
            Stay.status == STAY_PENDING,
            Stay.actual_checkin_time.is_(None),
            Stay.actual_checkout_time.is_(None),
        )
    ).first() is not None

    if room.status == _room_status_id(db, ROOM_ALLOTTED) or pending_alloc:
        # Preserve Allotted status
        return

    # For non-occupied, non-allotted rooms:
    # Query database configuration for blocking conditions
    is_blocking = db.execute(
        select(RoomStatusConditionApplicability.id).where(
            RoomStatusConditionApplicability.condition_id == target_condition_id,
            RoomStatusConditionApplicability.is_active == True,
            or_(
                RoomStatusConditionApplicability.blocks_readiness == True,
                RoomStatusConditionApplicability.blocks_checkin == True,
            ),
        )
    ).first() is not None

    is_ready = (
        "ready" in (cond.name or "").lower()
        or "ready" in (cond.display_name or "").lower()
    )

    if is_blocking:
        room.status = _room_status_id(db, ROOM_UNAVAILABLE)
    elif is_ready:
        room.status = _room_status_id(db, ROOM_AVAILABLE)


def _room_status_id(db: Session, status_name: str) -> int:
    """Resolve an `amenity_status` NAME to the id stored in `amenity.status`.

    `amenity.status` is a smallint FK, so a name has to become an id before it
    can be written. Looking it up on every use is what lets this module reason
    in names: a re-seeded or reordered `amenity_status` table changes the id and
    this still writes the right row.

    A name the table does not hold is a deployment problem, not a request
    problem, so it raises rather than falling back to a literal.
    """
    status_id = db.execute(
        select(AmenityStatus.id).where(
            AmenityStatus.amenity_status_name == status_name
        )
    ).scalars().first()
    if status_id is None:
        raise Invalid(f"Amenity status {status_name!r} is not seeded.")
    return status_id


def _room_status_name(db: Session, status_id: int) -> str | None:
    """The reverse: the name stored under an id, or None if there is no row."""
    row = db.get(AmenityStatus, status_id)
    return row.amenity_status_name if row is not None else None


def _set_room_status(db: Session, room_id: uuid.UUID, status_name: str) -> None:
    """Write a room's status, given the NAME. The id is resolved here."""
    room = db.get(Amenity, room_id)
    if room is None:
        raise Invalid(f"Room {room_id} does not exist.")
    room.status = _room_status_id(db, status_name)


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

        for allocation in allocations:
            if _has_blocking_condition(db, allocation.room_id):
                room = db.get(Amenity, allocation.room_id)
                r_name = room.name if room else str(allocation.room_id)
                raise Conflict(
                    f"Room {r_name} cannot be checked in because it has an active maintenance condition. "
                    "Room must be Ready to Occupy."
                )

        stay.actual_checkin_time = when or datetime.now(UTC)
        stay.status = STAY_ACTIVE
        stay.modified_by = actor_id

        for allocation in allocations:
            _set_room_status(db, allocation.room_id, ROOM_OCCUPIED)
            # Conditions not applicable to an occupied room (e.g. Ready for occupant) must be cleared
            inapplicable_cond_ids = select(AmenityCondition.id).where(
                or_(
                    AmenityCondition.applicable_to_occupied == False,
                    func.lower(AmenityCondition.name).in_(["ready for occupant", "ready to occupy"]),
                )
            )
            for r_row in db.execute(
                select(AmenityConditionStatus).where(
                    AmenityConditionStatus.amenity_id == allocation.room_id,
                    AmenityConditionStatus.amenity_condition_id.in_(inapplicable_cond_ids),
                )
            ).scalars().all():
                db.delete(r_row)

    db.refresh(stay)
    return stay


def check_out(
    db: Session, stay_id: uuid.UUID, *, actor_id: uuid.UUID, when: datetime | None = None
) -> Stay:
    """Check a stay out: stamp departure, close stay, release rooms with status synchronization."""
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
            # Clear conditions not applicable to vacant rooms (e.g. Guest Assistance Required)
            inapplicable_cond_ids = select(AmenityCondition.id).where(
                AmenityCondition.applicable_to_vacant == False
            )
            for r_row in db.execute(
                select(AmenityConditionStatus).where(
                    AmenityConditionStatus.amenity_id == allocation.room_id,
                    AmenityConditionStatus.amenity_condition_id.in_(inapplicable_cond_ids),
                )
            ).scalars().all():
                db.delete(r_row)

            if _has_blocking_condition(db, allocation.room_id):
                _set_room_status(db, allocation.room_id, ROOM_UNAVAILABLE)
            else:
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
            if _has_blocking_condition(db, allocation.room_id):
                _set_room_status(db, allocation.room_id, ROOM_UNAVAILABLE)
            else:
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

    # If the stay is already checked in (in-house), ensure target room does not have a blocking condition
    if stay.actual_checkin_time is not None and _has_blocking_condition(db, room_id):
        raise Conflict(
            f"Room {room.name} cannot be allocated to an in-house stay because it has an active maintenance condition."
        )

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

        if stay.actual_checkin_time is not None and _has_blocking_condition(db, room_id):
            raise Conflict(
                f"Room {new_room.name} cannot be allocated because it has an active maintenance condition."
            )

        old_room_id = allocation.room_id
        allocation.room_id = room_id
        allocation.package_id = new_room.package_id

        if _has_blocking_condition(db, old_room_id):
            _set_room_status(db, old_room_id, ROOM_UNAVAILABLE)
        else:
            _set_room_status(db, old_room_id, ROOM_AVAILABLE)

        _set_room_status(
            db, room_id, ROOM_OCCUPIED if stay.actual_checkin_time else ROOM_ALLOTTED
        )
        # If in-house move, remove ready / inapplicable conditions from new room
        if stay.actual_checkin_time is not None:
            inapplicable_cond_ids = select(AmenityCondition.id).where(
                or_(
                    AmenityCondition.applicable_to_occupied == False,
                    func.lower(AmenityCondition.name).in_(["ready for occupant", "ready to occupy"]),
                )
            )
            for r_row in db.execute(
                select(AmenityConditionStatus).where(
                    AmenityConditionStatus.amenity_id == room_id,
                    AmenityConditionStatus.amenity_condition_id.in_(inapplicable_cond_ids),
                )
            ).scalars().all():
                db.delete(r_row)

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
        if _has_blocking_condition(db, room_id):
            _set_room_status(db, room_id, ROOM_UNAVAILABLE)
        else:
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
            # The request carries the id; the guard rail below is written in
            # names, so the id is resolved back through `amenity_status`. This
            # comparison must not be made against the raw id -- that is the
            # seeded-value assumption this module exists to avoid.
            new_status = changes["status"]
            new_status_name = _room_status_name(db, new_status)
            if new_status_name is None:
                raise Invalid(f"Amenity status {new_status} does not exist.")
            if new_status_name in (ROOM_AVAILABLE, ROOM_UNAVAILABLE):
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
            if new_status_name == ROOM_AVAILABLE:
                if _has_blocking_condition(db, amenity_id):
                    raise Conflict(
                        f"Room {room.name} has an active maintenance condition and cannot be marked Available. Resolve maintenance first."
                    )

        apply_changes(room, changes)
    db.refresh(room)
    return room


def set_room_conditions(
    db: Session, amenity_id: uuid.UUID, *, condition_ids: list[int]
) -> list[int]:
    """Replace a room's condition (`amenity_condition_status`).

    A room maintains its active operational condition.
    Applicable conditions are validated against the PostgreSQL database
    configuration table `room_status_condition_applicability` for the room's
    actual workflow status.
    """
    with transaction(db):
        room = require_row(db, Amenity, amenity_id, "Room")

        # Deduplicate while preserving order
        condition_ids = list(dict.fromkeys(condition_ids))

        # Enforce single-active-condition business rule
        if len(condition_ids) != 1:
            raise Invalid("A room must have exactly one active condition.")

        # Read existing condition status rows for this room
        current_rows = db.execute(
            select(AmenityConditionStatus).where(
                AmenityConditionStatus.amenity_id == amenity_id
            )
        ).scalars().all()

        target_condition_id = condition_ids[0]
        cond = db.get(AmenityCondition, target_condition_id)
        if cond is None:
            raise Invalid(f"Amenity condition {target_condition_id} does not exist.")
        if not getattr(cond, "is_active", True):
            raise Invalid(f"Amenity condition {target_condition_id} is inactive and cannot be selected.")

        # Determine authoritative room status from PostgreSQL
        canonical_status = determine_room_status_for_applicability(db, amenity_id)

        # Validate applicability against PostgreSQL room_status_condition_applicability table
        status_candidates = [canonical_status]
        if canonical_status.lower() == "allocated":
            status_candidates.append("Allotted")
        elif canonical_status.lower() == "allotted":
            status_candidates.append("Allocated")

        applicability = db.execute(
            select(RoomStatusConditionApplicability).where(
                func.lower(RoomStatusConditionApplicability.room_status).in_([s.lower() for s in status_candidates]),
                RoomStatusConditionApplicability.condition_id == target_condition_id,
                RoomStatusConditionApplicability.is_active == True,
            )
        ).scalars().first()

        if applicability is None or not applicability.is_applicable:
            raise Invalid(
                f"Condition '{cond.name}' is not applicable to room {room.name} with status '{canonical_status}'."
            )

        # Business Rule: An occupied room (active in-house stay) CANNOT be marked Ready to Occupy
        is_ready_cond = (
            "ready" in (cond.name or "").lower()
            or "ready" in (cond.display_name or "").lower()
            or not getattr(cond, "applicable_to_occupied", True)
        )
        if is_ready_cond:
            in_house_stay = db.execute(
                select(Stay.internal_stay_ref_number)
                .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
                .where(
                    RoomAllocation.room_id == amenity_id,
                    Stay.actual_checkin_time.is_not(None),
                    Stay.actual_checkout_time.is_(None),
                )
            ).scalars().first()
            if in_house_stay:
                raise Conflict(
                    f"Room {room.name} has an active in-house stay ({in_house_stay}) and cannot be marked Ready to Occupy."
                )

        already_set = False
        for row in current_rows:
            if row.amenity_condition_id == target_condition_id and row.status == 1:
                already_set = True
            else:
                db.delete(row)

        if not already_set:
            db.add(
                AmenityConditionStatus(
                    amenity_id=amenity_id,
                    amenity_condition_id=target_condition_id,
                    status=1,
                )
            )

        # Synchronize room status with operational condition according to business rules
        sync_room_status_for_condition(db, room, target_condition_id, cond)

    return [target_condition_id]


# ---------------------------------------------------------------------------
# Bulk Reservations Upload
# ---------------------------------------------------------------------------


def _parse_datetime(val: str) -> datetime:
    val = val.strip()
    if not val:
        raise ValueError("Date string is empty")
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date/time format: {val!r}")


def process_bulk_reservations_csv(
    db: Session,
    *,
    file_bytes: bytes,
    filename: str,
    actor_id: uuid.UUID,
    facility_id: uuid.UUID,
) -> dict:
    import csv
    import io

    if not file_bytes:
        raise Invalid("Uploaded file is empty.")

    try:
        text_content = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text_content = file_bytes.decode("latin-1")
        except Exception:
            raise Invalid("Unable to decode uploaded file as text/CSV.")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise Invalid("CSV file must contain a header row.")

    headers_map = {fn.strip().lower().replace(" ", "_"): fn for fn in reader.fieldnames}

    has_guest = "guest_email" in headers_map or "email" in headers_map
    has_name = "guest_name" in headers_map or "name" in headers_map or "booker_name" in headers_map
    has_checkin = "checkin" in headers_map or "checkin_date" in headers_map or "expected_checkin_time" in headers_map
    has_checkout = "checkout" in headers_map or "checkout_date" in headers_map or "expected_checkout_time" in headers_map
    has_room = "room_number" in headers_map or "room" in headers_map or "room_name" in headers_map

    missing = []
    if not has_guest:
        missing.append("guest_email")
    if not has_name:
        missing.append("guest_name")
    if not has_checkin:
        missing.append("checkin_date")
    if not has_checkout:
        missing.append("checkout_date")
    if not has_room:
        missing.append("room_number")

    if missing:
        raise Invalid(f"CSV is missing required columns: {', '.join(missing)}")

    job = ImportJob(
        id=uuid.uuid4(),
        import_job_name=f"Bulk Reservation - {filename[:50]}",
        entity_type="booking",
        import_status="processing",
        import_file_name=filename[:100],
        created_by=actor_id,
    )
    job_id = job.id
    db.add(job)
    db.commit()

    total_records = 0
    success_count = 0
    errors: list[dict] = []
    imported_stay_ids: list[uuid.UUID] = []

    def get_val(row: dict, *keys: str) -> str:
        for k in keys:
            orig = headers_map.get(k)
            if orig and orig in row and row[orig] is not None:
                v = str(row[orig]).strip()
                if v:
                    return v
        return ""

    for row_idx, row in enumerate(reader, start=2):
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue

        total_records += 1
        guest_email = get_val(row, "guest_email", "email")
        guest_name = get_val(row, "guest_name", "name", "booker_name")
        checkin_str = get_val(row, "checkin", "checkin_date", "expected_checkin_time")
        checkout_str = get_val(row, "checkout", "checkout_date", "expected_checkout_time")
        room_str = get_val(row, "room_number", "room", "room_name")
        phone_str = get_val(row, "guest_phone_number", "phone_number", "phone")
        no_of_guests_str = get_val(row, "no_of_guests", "guests", "number_of_guests") or "1"
        comments_str = get_val(row, "comments", "special_requests", "notes")

        if not guest_email or "@" not in guest_email:
            errors.append({"row": row_idx, "error": f"Invalid or missing guest_email: '{guest_email}'"})
            continue
        if not guest_name:
            errors.append({"row": row_idx, "error": "Missing guest_name"})
            continue
        if not checkin_str:
            errors.append({"row": row_idx, "error": "Missing checkin_date"})
            continue
        if not checkout_str:
            errors.append({"row": row_idx, "error": "Missing checkout_date"})
            continue
        if not room_str:
            errors.append({"row": row_idx, "error": "Missing room_number"})
            continue

        try:
            checkin_dt = _parse_datetime(checkin_str)
            checkout_dt = _parse_datetime(checkout_str)
        except Exception as e:
            errors.append({"row": row_idx, "error": f"Date error: {e}"})
            continue

        if checkout_dt <= checkin_dt:
            errors.append({"row": row_idx, "error": f"Check-out ({checkout_str}) must be after check-in ({checkin_str})"})
            continue

        try:
            no_of_guests = max(1, int(no_of_guests_str))
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid number of guests: '{no_of_guests_str}'"})
            continue

        room_match = db.execute(
            select(Amenity).where(
                Amenity.facility_id == facility_id,
                or_(
                    func.lower(Amenity.name) == room_str.lower(),
                    func.lower(Amenity.name) == f"room {room_str.lower()}",
                    func.lower(Amenity.name) == f"rm {room_str.lower()}",
                ),
            )
        ).scalars().first()

        if not room_match:
            errors.append({"row": row_idx, "error": f"Room '{room_str}' not found in this facility"})
            continue

        clash = db.execute(
            select(Stay.internal_stay_ref_number)
            .join(RoomAllocation, RoomAllocation.stay_id == Stay.id)
            .where(
                RoomAllocation.room_id == room_match.id,
                Stay.status.in_(LIVE_STAY_STATUSES),
                Stay.expected_checkin_time < checkout_dt,
                Stay.expected_checkout_time > checkin_dt,
            )
        ).scalars().first()

        if clash:
            errors.append({"row": row_idx, "error": f"Room '{room_str}' is already allocated to stay {clash} for these dates"})
            continue

        try:
            user = db.execute(
                select(AppUser).where(func.lower(AppUser.email) == guest_email.lower())
            ).scalars().first()

            if not user:
                name_parts = guest_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                user_uid = next_reference(db, AppUser, AppUser.user_uid, "PE", width=5)
                user = AppUser(
                    id=uuid.uuid4(),
                    user_uid=user_uid,
                    first_name=first_name,
                    last_name=last_name or None,
                    email=guest_email.lower(),
                    phone_number=phone_str or None,
                    is_staff=0,
                    created_by=actor_id,
                )
                db.add(user)
                db.flush()
                db.add(
                    FacilityUser(
                        facility_id=facility_id,
                        app_user_id=user.id,
                        created_by=actor_id,
                    )
                )

            stay = create_stay(
                db,
                data={
                    "booking_user_id": user.id,
                    "expected_checkin_time": checkin_dt,
                    "expected_checkout_time": checkout_dt,
                    "no_of_guests": no_of_guests,
                    "comments": comments_str or None,
                    "room_ids": [room_match.id],
                },
                actor_id=actor_id,
            )
            success_count += 1
            imported_stay_ids.append(stay.id)
        except Exception as err:
            errors.append({"row": row_idx, "error": str(err)})

    job = db.get(ImportJob, job_id)
    if job is not None:
        job.total_records = total_records
        job.success_count = success_count
        job.error_count = len(errors)
        job.completed_on = datetime.now(UTC)
        if success_count > 0:
            job.import_status = "success"
        else:
            job.import_status = "error" if total_records > 0 else "success"

        if errors:
            job.error_file_name = f"{len(errors)} row(s) failed validation"

        db.commit()
        db.refresh(job)

    return {
        "import_job_id": job.id,
        "total_records": total_records,
        "success_count": success_count,
        "error_count": len(errors),
        "status": job.import_status,
        "errors": errors,
    }


def get_last_reservation_import_job(db: Session, facility_id: uuid.UUID | None = None) -> ImportJob | None:
    return db.execute(
        select(ImportJob)
        .where(ImportJob.entity_type == "booking")
        .order_by(ImportJob.created_on.desc())
        .limit(1)
    ).scalars().first()
