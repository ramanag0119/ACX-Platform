"""Group A - organisation, facility and the property hierarchy (8 tables).

Blueprint §5, tables 1-8.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, SmallIntLookupPk, TimestampMixin, UUIDPk

# ---------------------------------------------------------------------------
# Cycle-breaking foreign keys (blueprint §12.6).
#
#   facility.created_by        -> app_user
#   app_user.created_by        -> app_user
#   app_user.department_id     -> department -> facility
#   facility.facility_image_id -> attachment -> facility
#
# Every edge pointing at `app_user` or `attachment` is declared with
# use_alter=True, so PostgreSQL creates all 92 tables first and adds those
# constraints afterwards with ALTER TABLE. No FK is weakened or dropped.
# ---------------------------------------------------------------------------


def user_fk(column: str = "app_user.id", **kw) -> ForeignKey:
    return ForeignKey(column, use_alter=True, **kw)


def attachment_fk(**kw) -> ForeignKey:
    return ForeignKey("attachment.id", use_alter=True, **kw)


class Organisation(HMSBase, UUIDPk):
    """Top-level tenant that owns facilities. IKANOS `organisations`. USE."""

    __tablename__ = "organisation"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    org_uid: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class Facility(HMSBase, UUIDPk):
    """A hotel / premise. Tenant root for 32 downstream tables.
    IKANOS `facilities`. ADAPT."""

    __tablename__ = "facility"

    org_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organisation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The canonical copy. The denormalised copies IKANOS keeps on 91 other
    # tables are dropped -- blueprint §2.5, OPEN DECISION #2.
    facility_uid: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # REVIEW: no `currencies` table exists in the dump, so no FK is declared.
    currency_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pin_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guest_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email: Mapped[str] = mapped_column(String(500), nullable=False)
    additional_email: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_map_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cloud_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    facility_image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="CASCADE"), nullable=True
    )
    # Drives the Default Key Settings module.
    default_key_user: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    # NOT PRESENT, NOT ADDED (blueprint §11.9 / OPEN DECISION #9):
    #   address (single line), timezone, default_checkin_time,
    #   default_checkout_time, logo-as-varchar.


class FacilityUser(Base, TimestampMixin):
    """Which users belong to which facility. IKANOS `facility_users`. USE.

    Composite natural PK -- no surrogate id, and no legacy_id: IKANOS has no
    single integer key for this row.
    """

    __tablename__ = "facility_user"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        primary_key=True,
    )
    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        user_fk(ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class PropertyType(HMSBase, UUIDPk):
    """Kind of structure and how many chain levels it uses.
    IKANOS `property_types`. ADAPT."""

    __tablename__ = "property_type"

    property_type_name: Mapped[str] = mapped_column(String(200), nullable=False)
    property_type_image_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), attachment_fk(ondelete="RESTRICT"), nullable=True
    )
    # 1-3; drives property_chain depth. tinyint(1) in IKANOS but not a boolean.
    levels: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )


class Property(HMSBase, UUIDPk):
    """A named physical unit -- one building, one wing, one floor.
    IKANOS `properties`. USE."""

    __tablename__ = "property"

    property_name: Mapped[str] = mapped_column(String(200), nullable=False)
    property_type_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )


class PropertyChain(HMSBase, UUIDPk):
    """One materialised building -> wing -> floor path. An amenity points at a
    chain, not at a floor string. IKANOS `property_chains`. USE."""

    __tablename__ = "property_chain"

    level_one_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    level_two_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    level_three_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )


class Attachment(HMSBase, UUIDPk):
    """Uploaded file registry. IKANOS `attachments`. USE."""

    __tablename__ = "attachment"

    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE", use_alter=True),
        nullable=True,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(256), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True, index=True
    )


class Country(Base, TimestampMixin, SmallIntLookupPk):
    """Country reference data. IKANOS `countries` (239 rows). USE.

    T1 lookup: the IKANOS integer ids are the key and are seeded verbatim, so
    `legacy_id` would duplicate the PK and is not declared.
    """

    __tablename__ = "country"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    iso_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nice_name: Mapped[str] = mapped_column(String(50), nullable=False)
    iso3: Mapped[str | None] = mapped_column(String(3), nullable=True)
    num_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
