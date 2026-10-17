"""Read projections for the room catalogue and the marketing tables.

Six tables that exist in the schema but had no endpoint before Phase 3.0, which
is why the matching screens had nothing to show:

    amenity_type    Facility Management -> Amenity Type tab
    package         Facility Management -> Packages tab (+ package_feature)
    feature         Facility Management -> Room Amenities tab
    promo_code      Offers
    facility_event  Events
    occasion        Holidays

Each is a plain projection with an explicit column list -- no SELECT *.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    AmenityType,
    Attachment,
    Feature,
    FacilityEvent,
    Occasion,
    OccasionType,
    Package,
    PackageFeature,
    SubPackage,
    PromoCode,
    PromoCodeAmenity,
    Amenity,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AmenityTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    amenity_category: str
    facility_id: uuid.UUID | None
    status: int
    created_on: datetime
    updated_on: datetime


class FeatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feature_name: str
    is_smart_feature: int | None
    device_type: int | None
    facility_id: uuid.UUID | None
    status: int | None
    created_on: datetime
    updated_on: datetime


class PackageRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    amenity_type: uuid.UUID
    amenity_type_name: str | None
    is_sub_package: bool
    facility_id: uuid.UUID | None
    status: int
    feature_ids: list[uuid.UUID] = []
    feature_names: list[str] = []
    sub_package_ids: list[uuid.UUID] = []
    sub_package_names: list[str] = []
    parent_package_ids: list[uuid.UUID] = []
    parent_package_names: list[str] = []
    room_count: int
    created_on: datetime
    updated_on: datetime


class PromoCodeRead(BaseModel):
    id: uuid.UUID
    promo_code: str
    offer_name: str | None
    promo_code_description: str | None
    offered_by: str | None
    start_time: datetime | None
    expiry_time: datetime | None
    discount_percentage: Decimal | None
    max_discount_value: Decimal | None
    min_order_value: Decimal | None
    status: int | None
    promo_code_icon: uuid.UUID | None = None
    image_url: str | None = None
    room_names: list[str]
    created_on: datetime
    updated_on: datetime


class FacilityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    venue: str | None
    chief_guests: str | None
    description: str | None
    expected_attendees: int | None
    interested_attendees: int | None
    start_date_time: datetime | None
    end_date_time: datetime | None
    image_id: uuid.UUID | None = None
    image_url: str | None = None
    cancellation_reason: str | None
    facility_id: uuid.UUID
    status: int | None
    created_on: datetime
    updated_on: datetime


class OccasionRead(BaseModel):
    id: uuid.UUID
    occasion_name: str | None
    occasion_type: int
    occasion_type_name: str | None
    occasion_start_date: date
    occasion_end_date: date | None
    month: int
    day_of_month: int
    is_repeatable: int | None
    notify_to_hub: int | None
    facility_id: uuid.UUID | None
    status: int | None
    created_on: datetime
    updated_on: datetime


class OccasionTypeRead(BaseModel):
    """`occasion_type`'s name column is itself called `occasion_type`."""

    id: int
    name: str


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _paged(db: Session, stmt: Select, page: int, page_size: int):
    total = _count(db, stmt)
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return rows, total


def list_amenity_types(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id=None,
    amenity_category: str | None = None,
    status: int | None = None,
):
    stmt = select(AmenityType).order_by(AmenityType.name)
    if status is not None:
        stmt = stmt.where(AmenityType.status == status)
    if facility_id:
        stmt = stmt.where(AmenityType.facility_id == facility_id)
    if amenity_category:
        stmt = stmt.where(AmenityType.amenity_category == amenity_category)
    return _paged(db, stmt, page, page_size)


def list_features(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id=None,
    status: int | None = None,
):
    stmt = select(Feature).order_by(Feature.feature_name)
    if status is not None:
        stmt = stmt.where(Feature.status == status)
    if facility_id:
        stmt = stmt.where(Feature.facility_id == facility_id)
    return _paged(db, stmt, page, page_size)


def _package_extras(db: Session, package_ids: list[uuid.UUID]):
    """Feature IDs/names, sub-package IDs/names, parent-package IDs/names, and room counts for a page of packages."""
    if not package_ids:
        return {}, {}, {}, {}, {}, {}, {}

    feature_ids_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    feature_names_map: dict[uuid.UUID, list[str]] = {}
    rows = db.execute(
        select(PackageFeature.package_id, Feature.id, Feature.feature_name)
        .join(Feature, Feature.id == PackageFeature.feature_id)
        .where(PackageFeature.package_id.in_(package_ids))
        .order_by(Feature.feature_name)
    ).all()
    for package_id, f_id, name in rows:
        feature_names_map.setdefault(package_id, []).append(name)
        feature_ids_map.setdefault(package_id, []).append(f_id)

    # Sub-packages where package_id is the parent
    sub_pkg_ids_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    sub_pkg_names_map: dict[uuid.UUID, list[str]] = {}
    sub_rows = db.execute(
        select(SubPackage.parent_package_id, Package.id, Package.name)
        .join(Package, Package.id == SubPackage.sub_package_id)
        .where(SubPackage.parent_package_id.in_(package_ids))
        .order_by(Package.name)
    ).all()
    for parent_id, sp_id, sp_name in sub_rows:
        sub_pkg_ids_map.setdefault(parent_id, []).append(sp_id)
        sub_pkg_names_map.setdefault(parent_id, []).append(sp_name)

    # Parent packages where package_id is the child sub-package
    parent_pkg_ids_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    parent_pkg_names_map: dict[uuid.UUID, list[str]] = {}
    parent_rows = db.execute(
        select(SubPackage.sub_package_id, Package.id, Package.name)
        .join(Package, Package.id == SubPackage.parent_package_id)
        .where(SubPackage.sub_package_id.in_(package_ids))
        .order_by(Package.name)
    ).all()
    for sp_id, p_id, p_name in parent_rows:
        parent_pkg_ids_map.setdefault(sp_id, []).append(p_id)
        parent_pkg_names_map.setdefault(sp_id, []).append(p_name)

    counts = dict(
        db.execute(
            select(Amenity.package_id, func.count())
            .where(Amenity.package_id.in_(package_ids))
            .group_by(Amenity.package_id)
        ).all()
    )
    return (
        feature_ids_map,
        feature_names_map,
        sub_pkg_ids_map,
        sub_pkg_names_map,
        parent_pkg_ids_map,
        parent_pkg_names_map,
        counts,
    )


def list_packages(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id=None,
    is_sub_package=None,
    parent_package_id=None,
    include_removed: bool = False,
):
    """Packages plus their feature names, linked sub-packages, and room count.

    Retired packages (`status = 0`) are excluded unless `include_removed`.
    """
    stmt = select(Package).order_by(Package.name)
    if not include_removed:
        stmt = stmt.where(Package.status == 1)
    if facility_id:
        stmt = stmt.where(Package.facility_id == facility_id)
    if is_sub_package is not None:
        stmt = stmt.where(Package.is_sub_package == is_sub_package)
    if parent_package_id is not None:
        stmt = stmt.join(SubPackage, SubPackage.sub_package_id == Package.id).where(
            SubPackage.parent_package_id == parent_package_id
        )
    rows, total = _paged(db, stmt, page, page_size)

    ids = [row.id for row in rows]
    (
        feat_ids_map,
        feat_names_map,
        sub_pkg_ids_map,
        sub_pkg_names_map,
        parent_pkg_ids_map,
        parent_pkg_names_map,
        counts,
    ) = _package_extras(db, ids)
    type_names = dict(
        db.execute(select(AmenityType.id, AmenityType.name)).all()
    )
    items = [
        PackageRead(
            id=row.id,
            name=row.name,
            description=row.description,
            amenity_type=row.amenity_type,
            amenity_type_name=type_names.get(row.amenity_type),
            is_sub_package=row.is_sub_package,
            facility_id=row.facility_id,
            status=row.status,
            feature_ids=feat_ids_map.get(row.id, []),
            feature_names=feat_names_map.get(row.id, []),
            sub_package_ids=sub_pkg_ids_map.get(row.id, []),
            sub_package_names=sub_pkg_names_map.get(row.id, []),
            parent_package_ids=parent_pkg_ids_map.get(row.id, []),
            parent_package_names=parent_pkg_names_map.get(row.id, []),
            room_count=counts.get(row.id, 0),
            created_on=row.created_on,
            updated_on=row.updated_on,
        )
        for row in rows
    ]
    return items, total


def get_package(db: Session, package_id: uuid.UUID) -> PackageRead | None:
    # `include_removed` so a PATCH that retires a package can still echo the row
    # it just changed instead of 404-ing on its own write.
    items, _ = list_packages(db, page=1, page_size=1000, include_removed=True)
    return next((item for item in items if item.id == package_id), None)


def list_promo_codes(db: Session, *, page: int, page_size: int, q: str | None = None):
    stmt = (
        select(PromoCode, Attachment.file_path.label("image_url"))
        .outerjoin(Attachment, Attachment.id == PromoCode.promo_code_icon)
        .order_by(PromoCode.promo_code)
    )
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            PromoCode.promo_code.ilike(term)
            | PromoCode.offer_name.ilike(term)
            | PromoCode.offered_by.ilike(term)
        )
    total = _count(db, stmt)
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).all()

    ids = [promo.id for promo, _ in rows]
    room_names: dict[uuid.UUID, list[str]] = {}
    if ids:
        for promo_id, name in db.execute(
            select(PromoCodeAmenity.promo_code_id, Amenity.name)
            .join(Amenity, Amenity.id == PromoCodeAmenity.amenity_id)
            .where(PromoCodeAmenity.promo_code_id.in_(ids))
            .order_by(Amenity.name)
        ).all():
            room_names.setdefault(promo_id, []).append(name)

    items = [
        PromoCodeRead(
            id=promo.id,
            promo_code=promo.promo_code,
            offer_name=promo.offer_name,
            promo_code_description=promo.promo_code_description,
            offered_by=promo.offered_by,
            start_time=promo.start_time,
            expiry_time=promo.expiry_time,
            discount_percentage=promo.discount_percentage,
            max_discount_value=promo.max_discount_value,
            min_order_value=promo.min_order_value,
            status=promo.status,
            promo_code_icon=promo.promo_code_icon,
            image_url=img_url,
            room_names=room_names.get(promo.id, []),
            created_on=promo.created_on,
            updated_on=promo.updated_on,
        )
        for promo, img_url in rows
    ]
    return items, total


def get_promo_code(db: Session, promo_id: uuid.UUID) -> PromoCodeRead | None:
    items, _ = list_promo_codes(db, page=1, page_size=1000)
    return next((item for item in items if item.id == promo_id), None)


def list_events(db: Session, *, page: int, page_size: int, facility_id=None, q: str | None = None):
    stmt = (
        select(FacilityEvent, Attachment.file_path.label("image_url"))
        .outerjoin(Attachment, Attachment.id == FacilityEvent.image_id)
        .order_by(FacilityEvent.start_date_time.desc())
    )
    if facility_id:
        stmt = stmt.where(FacilityEvent.facility_id == facility_id)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            FacilityEvent.name.ilike(term)
            | FacilityEvent.venue.ilike(term)
            | FacilityEvent.chief_guests.ilike(term)
        )
    total = _count(db, stmt)
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    items = [
        FacilityEventRead(
            id=event.id,
            name=event.name,
            venue=event.venue,
            chief_guests=event.chief_guests,
            description=event.description,
            expected_attendees=event.expected_attendees,
            interested_attendees=event.interested_attendees,
            start_date_time=event.start_date_time,
            end_date_time=event.end_date_time,
            image_id=event.image_id,
            image_url=img_url,
            cancellation_reason=event.cancellation_reason,
            facility_id=event.facility_id,
            status=event.status,
            created_on=event.created_on,
            updated_on=event.updated_on,
        )
        for event, img_url in rows
    ]
    return items, total


def list_occasions(db: Session, *, page: int, page_size: int, facility_id=None):
    stmt = select(Occasion).order_by(Occasion.occasion_start_date.desc())
    if facility_id:
        stmt = stmt.where(Occasion.facility_id == facility_id)
    rows, total = _paged(db, stmt, page, page_size)
    type_names = dict(
        db.execute(select(OccasionType.id, OccasionType.occasion_type)).all()
    )
    items = [
        OccasionRead(
            id=row.id,
            occasion_name=row.occasion_name,
            occasion_type=row.occasion_type,
            occasion_type_name=type_names.get(row.occasion_type),
            occasion_start_date=row.occasion_start_date,
            occasion_end_date=row.occasion_end_date,
            month=row.month,
            day_of_month=row.day_of_month,
            is_repeatable=row.is_repeatable,
            notify_to_hub=row.notify_to_hub,
            facility_id=row.facility_id,
            status=row.status,
            created_on=row.created_on,
            updated_on=row.updated_on,
        )
        for row in rows
    ]
    return items, total


def get_occasion(db: Session, occasion_id: uuid.UUID) -> OccasionRead | None:
    items, _ = list_occasions(db, page=1, page_size=1000)
    return next((item for item in items if item.id == occasion_id), None)


def list_occasion_types(db: Session) -> list[OccasionTypeRead]:
    return [
        OccasionTypeRead(id=row.id, name=row.occasion_type)
        for row in db.execute(
            select(OccasionType).order_by(OccasionType.occasion_type)
        ).scalars()
    ]
