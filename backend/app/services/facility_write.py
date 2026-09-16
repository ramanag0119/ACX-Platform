"""Write logic for the facility, rooms, the room catalogue and marketing rows.

Schema facts behind each rule:

* A "room" is an `amenity`. `amenity_type_id` and `package_id` are NOT NULL, so
  both must exist before a room can be created -- which is exactly why the
  Facility Management screen has Amenity Type and Packages tabs.
* `amenity.property_chain_id` is what places a room on a building/floor. There
  is no building or floor table; `property_chain` is the projection Phase 2.2
  established.
* Room names are unique per facility in the seeded data, so a duplicate is 409.
* `package_feature` links a package to `feature` rows -- the "features" the
  Packages tab lists. Sub-packages are `package.is_sub_package`.
* `promo_code_amenity` scopes an offer to rooms.
* `occasion` (holidays) stores `month` and `day_of_month` NOT NULL alongside the
  start date; they are derived from the start date rather than asked for twice.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AmenityType,
    AppUser,
    Facility,
    FacilityEvent,
    Feature,
    Occasion,
    OccasionType,
    Package,
    PackageFeature,
    PromoCode,
    PromoCodeAmenity,
    PropertyChain,
)
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    require_exists,
    require_row,
    transaction,
)


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------


def update_facility(db: Session, facility_id: uuid.UUID, *, changes: dict) -> Facility:
    with transaction(db):
        facility = require_row(db, Facility, facility_id, "Facility")
        require_exists(db, AppUser, changes.get("default_key_user"), "Default key user")
        apply_changes(facility, changes)
    db.refresh(facility)
    return facility


# ---------------------------------------------------------------------------
# Rooms (amenity)
# ---------------------------------------------------------------------------


def _assert_room_name_free(
    db: Session, name: str, facility_id: uuid.UUID | None, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(Amenity.id).where(Amenity.name == name)
    if facility_id is not None:
        stmt = stmt.where(Amenity.facility_id == facility_id)
    if exclude_id is not None:
        stmt = stmt.where(Amenity.id != exclude_id)
    if db.execute(stmt).scalars().first() is not None:
        raise Conflict(f"Room '{name}' already exists in this facility.")


def create_room(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Amenity:
    with transaction(db):
        require_exists(db, AmenityType, data["amenity_type_id"], "Amenity type")
        require_exists(db, Package, data["package_id"], "Package")
        require_exists(db, PropertyChain, data.get("property_chain_id"), "Property chain")
        require_exists(db, Amenity, data.get("parent_amenity_id"), "Parent room")

        target_facility = data.pop("facility_id", None) or facility_id
        _assert_room_name_free(db, data["name"], target_facility)

        # A brand-new room is Unavailable (2) until it is made ready -- the
        # schema's own column default.
        status = data.pop("status", None)
        room = Amenity(
            id=uuid.uuid4(),
            facility_id=target_facility,
            status=2 if status is None else status,
            created_by=actor_id,
            **data,
        )
        db.add(room)
    db.refresh(room)
    return room


def update_room(db: Session, room_id: uuid.UUID, *, changes: dict) -> Amenity:
    with transaction(db):
        room = require_row(db, Amenity, room_id, "Room")
        require_exists(db, AmenityType, changes.get("amenity_type_id"), "Amenity type")
        require_exists(db, Package, changes.get("package_id"), "Package")
        require_exists(db, PropertyChain, changes.get("property_chain_id"), "Property chain")
        if changes.get("parent_amenity_id") == room_id:
            raise Invalid("A room cannot be its own parent.")
        require_exists(db, Amenity, changes.get("parent_amenity_id"), "Parent room")

        if changes.get("name"):
            _assert_room_name_free(db, changes["name"], room.facility_id, exclude_id=room_id)
        apply_changes(room, changes)
    db.refresh(room)
    return room


# ---------------------------------------------------------------------------
# Amenity types, packages, features
# ---------------------------------------------------------------------------


def create_amenity_type(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> AmenityType:
    with transaction(db):
        ensure_unique(db, AmenityType, AmenityType.name, data["name"], "Amenity type")
        row = AmenityType(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_amenity_type(
    db: Session, amenity_type_id: uuid.UUID, *, changes: dict
) -> AmenityType:
    with transaction(db):
        row = require_row(db, AmenityType, amenity_type_id, "Amenity type")
        if changes.get("name"):
            ensure_unique(
                db, AmenityType, AmenityType.name, changes["name"], "Amenity type",
                exclude_id=amenity_type_id,
            )
        apply_changes(row, changes)
    db.refresh(row)
    return row


def create_package(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Package:
    feature_ids = data.pop("feature_ids", None) or []
    with transaction(db):
        ensure_unique(db, Package, Package.name, data["name"], "Package")
        require_exists(db, AmenityType, data["amenity_type"], "Amenity type")
        row = Package(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
        db.flush()
        _replace_package_features(db, row.id, feature_ids, actor_id)
    db.refresh(row)
    return row


def _assert_package_unused(db: Session, package_id: uuid.UUID) -> None:
    """Refuse to retire a package that rooms still point at.

    `amenity.package_id` is NOT NULL, so a retired package with rooms on it
    would leave those rooms referencing a package no list returns. The rooms
    have to be moved to another package first. `package_feature` rows are left
    alone -- they are the package's own definition, not a dependent record.
    """
    names = db.execute(
        select(Amenity.name).where(Amenity.package_id == package_id).order_by(Amenity.name)
    ).scalars().all()
    if names:
        shown = ", ".join(names[:5])
        if len(names) > 5:
            shown += f" and {len(names) - 5} more"
        raise Conflict(
            f"{len(names)} room(s) still use this package ({shown}). "
            "Move them to another package before deleting it."
        )


def update_package(
    db: Session, package_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> Package:
    feature_ids = changes.pop("feature_ids", None)
    with transaction(db):
        row = require_row(db, Package, package_id, "Package")
        if changes.get("name"):
            ensure_unique(
                db, Package, Package.name, changes["name"], "Package", exclude_id=package_id
            )
        require_exists(db, AmenityType, changes.get("amenity_type"), "Amenity type")
        if changes.get("status") == 0:
            _assert_package_unused(db, package_id)
        apply_changes(row, changes)
        if feature_ids is not None:
            _replace_package_features(db, package_id, feature_ids, actor_id)
    db.refresh(row)
    return row


def _replace_package_features(
    db: Session, package_id: uuid.UUID, feature_ids: list[uuid.UUID], actor_id: uuid.UUID
) -> None:
    for feature_id in feature_ids:
        require_exists(db, Feature, feature_id, "Feature")
    db.execute(delete(PackageFeature).where(PackageFeature.package_id == package_id))
    for feature_id in feature_ids:
        db.add(
            PackageFeature(
                # UUID primary key and a NOT NULL audit column.
                id=uuid.uuid4(),
                package_id=package_id,
                feature_id=feature_id,
                status=1,
                created_by=actor_id,
            )
        )


def create_feature(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Feature:
    with transaction(db):
        ensure_unique(db, Feature, Feature.feature_name, data["feature_name"], "Feature")
        row = Feature(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_feature(db: Session, feature_id: uuid.UUID, *, changes: dict) -> Feature:
    with transaction(db):
        row = require_row(db, Feature, feature_id, "Feature")
        if changes.get("feature_name"):
            ensure_unique(
                db, Feature, Feature.feature_name, changes["feature_name"], "Feature",
                exclude_id=feature_id,
            )
        apply_changes(row, changes)
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Offers (promo_code)
# ---------------------------------------------------------------------------


def create_promo_code(db: Session, *, data: dict, actor_id: uuid.UUID) -> PromoCode:
    amenity_ids = data.pop("amenity_ids", None) or []
    with transaction(db):
        ensure_unique(db, PromoCode, PromoCode.promo_code, data["promo_code"], "Promo code")
        _validate_window(data.get("start_time"), data.get("expiry_time"))
        row = PromoCode(id=uuid.uuid4(), created_by=actor_id, **data)
        db.add(row)
        db.flush()
        _replace_promo_amenities(db, row.id, amenity_ids, actor_id)
    db.refresh(row)
    return row


def update_promo_code(
    db: Session, promo_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> PromoCode:
    amenity_ids = changes.pop("amenity_ids", None)
    with transaction(db):
        row = require_row(db, PromoCode, promo_id, "Promo code")
        _validate_window(
            changes.get("start_time", row.start_time),
            changes.get("expiry_time", row.expiry_time),
        )
        apply_changes(row, changes)
        if amenity_ids is not None:
            _replace_promo_amenities(db, promo_id, amenity_ids, actor_id)
    db.refresh(row)
    return row


def _replace_promo_amenities(
    db: Session, promo_id: uuid.UUID, amenity_ids: list[uuid.UUID], actor_id: uuid.UUID
) -> None:
    for amenity_id in amenity_ids:
        require_exists(db, Amenity, amenity_id, "Room")
    db.execute(delete(PromoCodeAmenity).where(PromoCodeAmenity.promo_code_id == promo_id))
    for amenity_id in amenity_ids:
        db.add(
            PromoCodeAmenity(
                promo_code_id=promo_id,
                amenity_id=amenity_id,
                status=1,
                created_by=actor_id,
            )
        )


def _validate_window(start, end) -> None:
    if start and end and end <= start:
        raise Invalid("The end of the window must be after its start.")


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def create_event(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> FacilityEvent:
    with transaction(db):
        _validate_window(data.get("start_date_time"), data.get("end_date_time"))
        row = FacilityEvent(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_event(db: Session, event_id: uuid.UUID, *, changes: dict) -> FacilityEvent:
    with transaction(db):
        row = require_row(db, FacilityEvent, event_id, "Event")
        _validate_window(
            changes.get("start_date_time", row.start_date_time),
            changes.get("end_date_time", row.end_date_time),
        )
        apply_changes(row, changes)
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Holidays (occasion)
# ---------------------------------------------------------------------------


def create_occasion(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Occasion:
    with transaction(db):
        if db.get(OccasionType, data["occasion_type"]) is None:
            raise Invalid(f"Occasion type {data['occasion_type']} does not exist.")

        start = data["occasion_start_date"]
        end = data.get("occasion_end_date")
        if end and end < start:
            raise Invalid("The end date cannot be before the start date.")

        row = Occasion(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            # `month` and `day_of_month` are NOT NULL and are what makes a
            # repeatable occasion recur; they follow from the start date.
            month=start.month,
            day_of_month=start.day,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_occasion(db: Session, occasion_id: uuid.UUID, *, changes: dict) -> Occasion:
    with transaction(db):
        row = require_row(db, Occasion, occasion_id, "Occasion")
        if "occasion_type" in changes and db.get(OccasionType, changes["occasion_type"]) is None:
            raise Invalid(f"Occasion type {changes['occasion_type']} does not exist.")

        start = changes.get("occasion_start_date", row.occasion_start_date)
        end = changes.get("occasion_end_date", row.occasion_end_date)
        if end and start and end < start:
            raise Invalid("The end date cannot be before the start date.")

        apply_changes(row, changes)
        if "occasion_start_date" in changes and changes["occasion_start_date"]:
            row.month = changes["occasion_start_date"].month
            row.day_of_month = changes["occasion_start_date"].day
    db.refresh(row)
    return row
