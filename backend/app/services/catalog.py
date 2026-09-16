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
    Feature,
    FacilityEvent,
    Occasion,
    OccasionType,
    Package,
    PackageFeature,
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
    feature_names: list[str]
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


def list_amenity_types(db: Session, *, page: int, page_size: int, facility_id=None):
    stmt = select(AmenityType).order_by(AmenityType.name)
    if facility_id:
        stmt = stmt.where(AmenityType.facility_id == facility_id)
    return _paged(db, stmt, page, page_size)


def list_features(db: Session, *, page: int, page_size: int, facility_id=None):
    stmt = select(Feature).order_by(Feature.feature_name)
    if facility_id:
        stmt = stmt.where(Feature.facility_id == facility_id)
    return _paged(db, stmt, page, page_size)


def _package_extras(db: Session, package_ids: list[uuid.UUID]):
    """Feature names and room counts for a page of packages, in two queries."""
    if not package_ids:
        return {}, {}
    features: dict[uuid.UUID, list[str]] = {}
    rows = db.execute(
        select(PackageFeature.package_id, Feature.feature_name)
        .join(Feature, Feature.id == PackageFeature.feature_id)
        .where(PackageFeature.package_id.in_(package_ids))
        .order_by(Feature.feature_name)
    ).all()
    for package_id, name in rows:
        features.setdefault(package_id, []).append(name)

    counts = dict(
        db.execute(
            select(Amenity.package_id, func.count())
            .where(Amenity.package_id.in_(package_ids))
            .group_by(Amenity.package_id)
        ).all()
    )
    return features, counts


def list_packages(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id=None,
    is_sub_package=None,
    include_removed: bool = False,
):
    """Packages plus their feature names and room count.

    Retired packages (`status = 0`) are excluded unless `include_removed`,
    which is the same soft-delete read rule `list_maintenance_requests` uses.
    Without this filter a retired package stayed on the Packages tab and the
    delete action looked like it had done nothing.
    """
    stmt = select(Package).order_by(Package.name)
    if not include_removed:
        stmt = stmt.where(Package.status == 1)
    if facility_id:
        stmt = stmt.where(Package.facility_id == facility_id)
    if is_sub_package is not None:
        stmt = stmt.where(Package.is_sub_package == is_sub_package)
    rows, total = _paged(db, stmt, page, page_size)

    ids = [row.id for row in rows]
    features, counts = _package_extras(db, ids)
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
            feature_names=features.get(row.id, []),
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


def list_promo_codes(db: Session, *, page: int, page_size: int):
    stmt = select(PromoCode).order_by(PromoCode.promo_code)
    rows, total = _paged(db, stmt, page, page_size)

    ids = [row.id for row in rows]
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
            id=row.id,
            promo_code=row.promo_code,
            offer_name=row.offer_name,
            promo_code_description=row.promo_code_description,
            offered_by=row.offered_by,
            start_time=row.start_time,
            expiry_time=row.expiry_time,
            discount_percentage=row.discount_percentage,
            max_discount_value=row.max_discount_value,
            min_order_value=row.min_order_value,
            status=row.status,
            room_names=room_names.get(row.id, []),
            created_on=row.created_on,
            updated_on=row.updated_on,
        )
        for row in rows
    ]
    return items, total


def get_promo_code(db: Session, promo_id: uuid.UUID) -> PromoCodeRead | None:
    items, _ = list_promo_codes(db, page=1, page_size=1000)
    return next((item for item in items if item.id == promo_id), None)


def list_events(db: Session, *, page: int, page_size: int, facility_id=None):
    stmt = select(FacilityEvent).order_by(FacilityEvent.start_date_time.desc())
    if facility_id:
        stmt = stmt.where(FacilityEvent.facility_id == facility_id)
    return _paged(db, stmt, page, page_size)


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
