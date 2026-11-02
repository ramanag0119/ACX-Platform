"""Response models for the facility and property hierarchy.

Every field below maps to a real column in the approved 92-table schema, or is
an explicitly-named count derived from a real foreign key. Nothing is invented.

IMPORTANT -- there are no `building` or `floor` tables. IKANOS models the
hierarchy as:

    facility -> property_type -> property
                                    ^
                property_chain(level_one_id, level_two_id, level_three_id)
                                    |
                                 amenity.property_chain_id

A "building" is a `property` referenced as `property_chain.level_one_id`.
A "floor"    is a `property` referenced as `property_chain.level_two_id`.

Both are therefore projections over real rows and real foreign keys, not new
entities. See `BuildingRead` / `FloorRead` for the consequences.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Reference data: Country & Gender
# ---------------------------------------------------------------------------


class CountryRead(ORMModel):
    """A row of `country` reference data."""

    id: int
    name: str = Field(examples=["INDIA"])
    nice_name: str = Field(examples=["India"])
    phone_code: str = Field(examples=["91"])
    iso_code: str | None = Field(default=None, examples=["IN"])
    iso3: str | None = Field(default=None, examples=["IND"])
    num_code: int | None = None


class GenderOption(BaseModel):
    """Database-backed enum option for gender."""

    value: str = Field(examples=["male"])
    label: str = Field(examples=["Male"])


class CurrencyRead(ORMModel):
    """Authoritative ISO 4217 currency."""

    id: int = Field(examples=[1])
    code: str = Field(examples=["INR"])
    name: str = Field(examples=["Indian Rupee"])
    symbol: str = Field(examples=["₹"])
    minor_units: int = Field(examples=[2])
    is_active: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------


class FacilityRead(ORMModel):
    """A row of `facility`."""

    id: uuid.UUID
    facility_uid: str = Field(examples=["ikg"])
    name: str = Field(examples=["Ikanos Grand Chennai"])
    org_id: uuid.UUID
    city: str | None = None
    state: str | None = None
    pin_code: str | None = None
    guest_rooms: int | None = None
    email: str
    additional_email: str | None = None
    google_map_link: str | None = None
    currency_id: int | None = Field(
        default=None,
        description="Foreign key to `currency.id`.",
    )
    currency: CurrencyRead | None = None
    facility_image_id: uuid.UUID | None = None
    default_key_user: uuid.UUID | None = None
    created_on: datetime
    updated_on: datetime


class FacilityDetail(FacilityRead):
    """Facility plus counts derived from real foreign keys."""

    property_count: int = Field(description="Rows in `property` for this facility")
    amenity_count: int = Field(description="Rows in `amenity` for this facility")


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------


class PropertyRead(ORMModel):
    """A row of `property`. Buildings and floors are both property rows."""

    id: uuid.UUID
    property_name: str = Field(examples=["Tower A"])
    property_type_id: uuid.UUID
    property_type_name: str | None = Field(default=None, examples=["Hotel Building"])
    property_type_levels: int | None = Field(
        default=None, description="`property_type.levels` -- chain depth, 1-3"
    )
    facility_id: uuid.UUID | None = None
    status: int
    created_on: datetime
    updated_on: datetime


# ---------------------------------------------------------------------------
# Building / Floor -- projections, not tables
# ---------------------------------------------------------------------------


class BuildingRead(ORMModel):
    """A `property` that appears at `property_chain.level_one_id`.

    `id` is the property id: a building has no identity of its own.
    """

    id: uuid.UUID
    name: str = Field(examples=["Tower A"], description="property.property_name")
    facility_id: uuid.UUID | None = None
    property_type_id: uuid.UUID
    property_type_name: str | None = None
    status: int
    floor_count: int = Field(description="Distinct level_two_id under this building")
    room_count: int = Field(description="Amenities whose chain starts at this building")


class FloorRead(ORMModel):
    """A `property` that appears at `property_chain.level_two_id`.

    A floor is only meaningful inside a chain, so `building_id` and
    `property_chain_id` are always populated.
    """

    id: uuid.UUID
    name: str = Field(examples=["Floor 1"], description="property.property_name")
    facility_id: uuid.UUID | None = None
    property_chain_id: uuid.UUID
    building_id: uuid.UUID
    building_name: str
    status: int
    room_count: int = Field(description="Amenities on this floor")


# ---------------------------------------------------------------------------
# Room (= amenity)
# ---------------------------------------------------------------------------


class AmenityConditionRead(ORMModel):
    """A row of `amenity_condition` currently set on a room."""

    id: int
    name: str = Field(examples=["Under maintenance"])


class RoomRead(ORMModel):
    """A row of `amenity`.

    "Room" is the IKANOS `amenity` entity, which also covers non-room spaces
    (restaurant, gym, conference). `amenity_category` distinguishes them.
    """

    id: uuid.UUID
    name: str = Field(examples=["101"], description="Room number; varchar(6)")
    facility_id: uuid.UUID | None = None
    amenity_type_id: uuid.UUID
    amenity_type_name: str | None = Field(default=None, examples=["Guest Room"])
    amenity_category: str | None = Field(
        default=None, examples=["room"], description="room | restaurant | others"
    )
    package_id: uuid.UUID
    package_name: str | None = Field(default=None, examples=["Deluxe"])
    status: int | None = Field(default=None, examples=[1])
    status_name: str | None = Field(
        default=None,
        examples=["Occupied"],
        description="amenity_status: Available / Occupied / Unavailable / Allotted",
    )
    property_chain_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    parent_amenity_id: uuid.UUID | None = None
    is_dnd: int | None = None
    power_save_mode: int | None = None
    conditions: list[AmenityConditionRead] = Field(
        default_factory=list,
        description="Active rows from amenity_condition_status",
    )
    created_on: datetime
    updated_on: datetime


class KeySettingsRead(ORMModel):
    facility_id: uuid.UUID
    default_key_user: uuid.UUID | None = None
    manager_name: str | None = None
    manager_email: str | None = None
    active_keys_count: int = 0


class KeySettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_key_user: uuid.UUID | None = None
