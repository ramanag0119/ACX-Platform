"""CORE domain models.

Every column below is transcribed from the IKANOS documentation:
  FM  = 1_FACILITI_MANAGER_DOCUMENTATION.md §12 "Database Tables"
  CPA = COMPLETE_PROJECT_ANALYSIS_REPORT.md §8 "Core Tables"
  LAD = 8_LAYERS_ARCHITECTURE_DIAGRAMS.md

Undocumented business fields are NOT invented. Where an entity plainly needs
more columns to be operationally useful, the shortfall is recorded in
`docs/NEEDS_REVIEW.md` rather than guessed at here.

Table naming: IKANOS camelCase entity names are mapped to PostgreSQL
snake_case. Two names collide with SQL reserved/ambiguous words and are
remapped (documented in the Phase 1 report):
    user      -> app_user
    function  -> job_function
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RoleType, pg_enum

# --------------------------------------------------------------------------
# facility  (CPA §8: id, name, address, settings | FM §12: facility config)
# Root aggregate — nearly every other entity carries facilityId.
# --------------------------------------------------------------------------


class Facility(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "facility"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict | None] = mapped_column(JSONB)

    property_types: Mapped[list["PropertyType"]] = relationship(
        back_populates="facility"
    )
    amenities: Mapped[list["Amenity"]] = relationship(back_populates="facility")


# --------------------------------------------------------------------------
# userRole  (CPA §8: id, name, roleType, permissions)
# `permissions` kept as JSONB: FM §10 documents a permissions API and a
# module matrix, but no permission table structure. See NEEDS_REVIEW.
# --------------------------------------------------------------------------


class UserRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    role_type: Mapped[RoleType] = mapped_column(pg_enum(RoleType), nullable=False)
    permissions: Mapped[dict | None] = mapped_column(JSONB)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# user  ->  app_user  (CPA §8: id, email, password, userRoles, facilityId)
# --------------------------------------------------------------------------


class AppUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_user"
    __table_args__ = (UniqueConstraint("facility_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    roles: Mapped[list[UserRole]] = relationship(
        secondary="app_user_user_role", backref="users"
    )


class AppUserUserRole(Base):
    """Junction for the documented `user.userRoles` collection.

    FM §4 login response returns `userRoles: [{ role: {...} }]` — a list —
    so a many-to-many link table is technically required for referential
    integrity. No business columns are added.
    """

    __tablename__ = "app_user_user_role"

    app_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    user_role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_role.id", ondelete="CASCADE"), primary_key=True
    )


# --------------------------------------------------------------------------
# propertyType  (CPA §8 / FM §12: id, name, facilityId)
# --------------------------------------------------------------------------


class PropertyType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "property_type"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    facility: Mapped[Facility] = relationship(back_populates="property_types")


# --------------------------------------------------------------------------
# amenityType  (FM §12: id, name, image)
# NOTE: documented in FM §12 but absent from the 36-entity brief. Included
# because `package.amenityType` and /api/facility/{ID}/amenity-types depend
# on it. Flagged in the Phase 1 report.
# --------------------------------------------------------------------------


class AmenityType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "amenity_type"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    image: Mapped[str | None] = mapped_column(String(500))

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# package  (CPA §8: id, name, price, amenityType)
# --------------------------------------------------------------------------


class Package(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "package"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))

    amenity_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity_type.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# amenity  (CPA §8 / FM §12: id, name, type, floor, packageId, status)
# "Rooms/locations" per CPA §8.
# --------------------------------------------------------------------------


class Amenity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "amenity"
    __table_args__ = (
        UniqueConstraint("facility_id", "name"),
        Index("ix_amenity_facility_id_status", "facility_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("package.id", ondelete="SET NULL")
    )
    property_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("property_type.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    facility: Mapped[Facility] = relationship(back_populates="amenities")


# --------------------------------------------------------------------------
# department  (CPA §8: id, name, facilityId)
# --------------------------------------------------------------------------


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "department"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# function -> job_function  (CPA §8: id, name, departmentId)
# --------------------------------------------------------------------------


class JobFunction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_function"

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("department.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# employee  (CPA §8: id, email, departmentId, userRoleId)
# FM §13 documents uniqueness on e-mail and on phone number.
# --------------------------------------------------------------------------


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee"
    __table_args__ = (UniqueConstraint("facility_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("department.id", ondelete="SET NULL")
    )
    job_function_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_function.id", ondelete="SET NULL")
    )
    user_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_role.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# booking  (CPA §8: id, firstName, checkinDate, packageId)
# --------------------------------------------------------------------------


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "booking"
    __table_args__ = (
        Index("ix_booking_facility_id_checkin_date", "facility_id", "checkin_date"),
    )

    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    checkin_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("package.id", ondelete="RESTRICT")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    occupants: Mapped[list["Occupant"]] = relationship(back_populates="booking")
    stays: Mapped[list["Stay"]] = relationship(back_populates="booking")


# --------------------------------------------------------------------------
# occupant  (CPA §8: id, bookingId, firstName, phoneNumber)
# --------------------------------------------------------------------------


class Occupant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "occupant"

    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(50))

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking.id", ondelete="CASCADE"), nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="occupants")


# --------------------------------------------------------------------------
# stay  (CPA §8: id, bookingId, amenityId, status)
# --------------------------------------------------------------------------


class Stay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stay"
    __table_args__ = (Index("ix_stay_facility_id_status", "facility_id", "status"),)

    status: Mapped[str | None] = mapped_column(String(50))

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking.id", ondelete="CASCADE"), nullable=False
    )
    amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="stays")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="stay")


# --------------------------------------------------------------------------
# invoice  (CPA §8: id, stayId, amount, status)
# --------------------------------------------------------------------------


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoice"

    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str | None] = mapped_column(String(50))

    stay_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stay.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )

    stay: Mapped[Stay] = relationship(back_populates="invoices")


# --------------------------------------------------------------------------
# serviceRequest
#   CPA §8 : id, serviceType/requestType, roomId, assignedTo, status
#   LAD    : id, guestId, roomId, subject, status, createdOn
# --------------------------------------------------------------------------


class ServiceRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_request"
    __table_args__ = (
        Index("ix_service_request_facility_id_status", "facility_id", "status"),
        Index("ix_service_request_assigned_to_status", "assigned_to", "status"),
    )

    service_type: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str | None] = mapped_column(String(50))
    created_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    room_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("amenity.id", ondelete="SET NULL")
    )
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# foodCategory  (CPA §8: id, name)
# --------------------------------------------------------------------------


class FoodCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_category"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# foodMenu  (CPA §8: id, name, foodCode, categoryId, price)
# --------------------------------------------------------------------------


class FoodMenu(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_menu"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    food_code: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("food_category.id", ondelete="SET NULL")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# event  (CPA §8: id, name, venue, startDate, status)
# --------------------------------------------------------------------------


class Event(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(50))

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# offer  (CPA §8: id, name, couponCode, validFrom)
# --------------------------------------------------------------------------


class Offer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offer"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(100))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )


# --------------------------------------------------------------------------
# holiday  (CPA §8: id, startDate, lockMessage)
# --------------------------------------------------------------------------


class Holiday(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holiday"

    start_date: Mapped[date | None] = mapped_column(Date)
    lock_message: Mapped[str | None] = mapped_column(Text)

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facility.id", ondelete="CASCADE"), nullable=False
    )
