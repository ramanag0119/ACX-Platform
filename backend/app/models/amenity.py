"""Group B - rooms, amenities and packages (9 tables).

Blueprint §5, tables 9-17.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, SmallIntLookupPk, TimestampMixin, UUIDPk
from app.models import enums
from app.models.facility import attachment_fk, user_fk


class AmenityType(HMSBase, UUIDPk):
    """Category of bookable / non-bookable space. IKANOS `amenity_types`. ADAPT."""

    __tablename__ = "amenity_type"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amenity_category: Mapped[str] = mapped_column(
        enums.amenity_category, nullable=False, server_default="others"
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class AmenityStatus(Base, TimestampMixin, SmallIntLookupPk):
    """The 4-value room status vocabulary. IKANOS `amenity_statuses`. USE.

    Seeded 0 Available / 1 Occupied / 2 Unavailable / 3 Allotted.
    """

    __tablename__ = "amenity_status"

    amenity_status_name: Mapped[str] = mapped_column(String(100), nullable=False)


class AmenityCondition(Base, TimestampMixin, SmallIntLookupPk):
    """Housekeeping condition badges, independent of status.
    IKANOS `amenity_conditions`. USE.

    Seeded Dirty / Low battery / Under maintenance / Sanitation.
    """

    __tablename__ = "amenity_condition"

    name: Mapped[str] = mapped_column(String(45), nullable=False)


class Amenity(HMSBase, UUIDPk):
    """A room or space. The central operational object.
    IKANOS `amenities` + `amenity_metadata` (MERGE). ADAPT."""

    __tablename__ = "amenity"

    name: Mapped[str] = mapped_column(String(6), nullable=False)
    parent_amenity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("amenity.id", ondelete="CASCADE"), nullable=True
    )
    amenity_type_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Replaces the Phase 1 `floor VARCHAR` + `property_type_id`.
    property_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property_chain.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # [INFER] IKANOS declares `amenities.status tinyint DEFAULT 2` with no FK,
    # but `amenity_statuses` holds exactly ids 0-3. Blueprint §11.4 / §10 #5.
    status: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("amenity_status.id", ondelete="RESTRICT"),
        nullable=True,
        server_default="2",
        index=True,
    )
    is_dnd: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    power_save_mode: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # MERGE: absorbed `amenity_metadata` (blueprint §3.3).
    amenity_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("ix_amenity_metadata_gin", "metadata", postgresql_using="gin"),
    )


class AmenityConditionStatus(Base, TimestampMixin):
    """Which conditions are currently set on which room.
    IKANOS `amenity_condition_status`. USE. Composite natural PK."""

    __tablename__ = "amenity_condition_status"

    amenity_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    amenity_condition_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("amenity_condition.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )


class Package(HMSBase, UUIDPk):
    """Room package / rate plan. IKANOS `packages`. ADAPT.

    `price` is NOT a column: `packages` has no price in the dump. The only
    price in the schema is `service_category_item.price_per_unit`.
    Room tariff has no source -> blueprint §11.3 / OPEN DECISION #10.
    """

    __tablename__ = "package"

    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # [INFER] `packages.amenity_type smallint` carries no FK in IKANOS.
    amenity_type: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("amenity_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_sub_package: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class SubPackage(Base, TimestampMixin):
    """Parent package -> child package composition. IKANOS `sub_packages`. USE."""

    __tablename__ = "sub_package"

    parent_package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    sub_package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class Feature(HMSBase, UUIDPk):
    """Room feature, optionally tied to a smart device type.
    IKANOS `features`. USE."""

    __tablename__ = "feature"

    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_smart_feature: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    device_type: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("device_type.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class PackageFeature(HMSBase, UUIDPk):
    """Which features a package includes. IKANOS `package_features`. USE.

    IKANOS uses a surrogate PK here, not a composite -- preserved.
    """

    __tablename__ = "package_feature"

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("feature.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )
