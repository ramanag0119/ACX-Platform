"""Request bodies for the service, stay, occupancy, device and catalogue writes.

Enum-backed columns are typed with `Literal` on the real PostgreSQL labels, so
an invalid value is rejected by Pydantic before it reaches the database.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StayStatus = Literal[
    "pending",
    "active",
    "checkout accepted",
    "checkout pending",
    "checkout rejected",
    "checked out",
    "cancelled",
]
#: `stay.document_approval_status` uses the two-value enum.
DocumentApproval = Literal["pending", "approved"]
RequestSource = Literal["ikanos", "porta"]
DeviceConfigStatus = Literal[
    "configured",
    "bad_configuration",
    "commissioned",
    "decommissioned",
    "under_maintenance",
    "missing",
]
DeviceHealthStatus = Literal["Active", "Inactive"]
FirmwareStatus = Literal["active", "decommissioned"]
AmenityCategory = Literal["room", "restaurant", "others"]
JobOrderTypeOfWork = Literal["installation", "replacement", "troubleshoot"]
JobOrderStatus = Literal["pending", "completed"]


class Body(BaseModel):
    """Reject unknown keys everywhere: a typo is a 422, not a silent no-op."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


class ServiceRequestItemWrite(Body):
    item_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    quantity: int = Field(default=1, ge=1, le=999)
    #: Omit to copy the catalogue price (the only price the schema stores).
    price_per_unit: Decimal | None = Field(default=None, ge=0)
    assigned_to: uuid.UUID | None = None
    status: int | None = Field(default=None, ge=1, le=5)


class ServiceRequestCreate(Body):
    service_type: int = Field(ge=1)
    category_id: uuid.UUID | None = None
    description: str | None = None
    amenity_id: uuid.UUID | None = None
    stay_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    #: The guest or staff member the request is for (`app_user_id`).
    app_user_id: uuid.UUID | None = None
    promo_code_id: uuid.UUID | None = None
    expected_date: datetime | None = None
    status: int | None = Field(default=None, ge=1, le=5)
    status_reason: str | None = Field(default=None, max_length=255)
    request_source: RequestSource | None = None
    facility_id: uuid.UUID | None = None
    items: list[ServiceRequestItemWrite] = Field(default_factory=list)


class ServiceRequestUpdate(Body):
    category_id: uuid.UUID | None = None
    description: str | None = None
    amenity_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    expected_date: datetime | None = None
    status: int | None = Field(default=None, ge=1, le=5)
    status_reason: str | None = Field(default=None, max_length=255)


class ServiceRequestItems(Body):
    items: list[ServiceRequestItemWrite]


class CancelBody(Body):
    reason: str | None = Field(default=None, max_length=255)


class ServiceCategoryCreate(Body):
    category_name: str = Field(min_length=1, max_length=255)
    service_type: int = Field(ge=1)
    description: str | None = None
    service_category_key: str | None = Field(default=None, max_length=100)
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class ServiceCategoryUpdate(Body):
    category_name: str | None = Field(default=None, min_length=1, max_length=255)
    service_type: int | None = Field(default=None, ge=1)
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)


class ServiceItemCreate(Body):
    item_name: str = Field(min_length=1, max_length=255)
    category_id: uuid.UUID
    description: str | None = None
    price_per_unit: Decimal | None = Field(default=None, ge=0)
    amenity_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class ServiceItemUpdate(Body):
    item_name: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: uuid.UUID | None = None
    description: str | None = None
    price_per_unit: Decimal | None = Field(default=None, ge=0)
    amenity_id: uuid.UUID | None = None
    status: int | None = Field(default=None, ge=0, le=1)


# ---------------------------------------------------------------------------
# Stays, allocation and occupants
# ---------------------------------------------------------------------------


class StayCreate(Body):
    #: `app_user.id` of the booker. Guests are app_user rows with is_staff = 0.
    booking_user_id: uuid.UUID
    expected_checkin_time: datetime
    expected_checkout_time: datetime
    no_of_guests: int = Field(default=1, ge=0, le=999)
    external_stay_ref_number: str | None = Field(default=None, max_length=100)
    gst: str | None = Field(default=None, max_length=50)
    comments: str | None = None
    status: StayStatus | None = None
    request_source: RequestSource | None = None
    #: Rooms to allocate immediately; each becomes a `room_allocation` row.
    room_ids: list[uuid.UUID] = Field(default_factory=list)
    #: Additional occupants; each becomes a `stay_user` row.
    occupant_ids: list[uuid.UUID] = Field(default_factory=list)


class StayUpdate(Body):
    booking_user_id: uuid.UUID | None = None
    expected_checkin_time: datetime | None = None
    expected_checkout_time: datetime | None = None
    no_of_guests: int | None = Field(default=None, ge=0, le=999)
    external_stay_ref_number: str | None = Field(default=None, max_length=100)
    gst: str | None = Field(default=None, max_length=50)
    comments: str | None = None


class CheckInBody(Body):
    #: Defaults to now; supplied only when back-dating a real arrival.
    when: datetime | None = None


class CheckOutBody(Body):
    when: datetime | None = None


class ExtendStayBody(Body):
    expected_checkout_time: datetime


class StayStatusBody(Body):
    status: StayStatus


class DocumentApprovalBody(Body):
    document_approval_status: DocumentApproval


class AllocateRoomBody(Body):
    room_id: uuid.UUID
    #: Omit to inherit the room's own package.
    package_id: uuid.UUID | None = None


class ReallocateRoomBody(Body):
    room_id: uuid.UUID


class OccupantBody(Body):
    guest_id: uuid.UUID
    room_id: uuid.UUID | None = None
    is_key_required: int | None = Field(default=None, ge=0, le=1)


class RoomStateUpdate(Body):
    """`amenity` status and flags -- the Occupancy screen's own controls."""

    status: int | None = Field(default=None, ge=0, le=3)
    is_dnd: int | None = Field(default=None, ge=0, le=1)
    power_save_mode: int | None = Field(default=None, ge=0, le=1)


class RoomConditionsBody(Body):
    #: `amenity_condition` ids: 1 Dirty, 2 Low battery, 3 Under maintenance, 4 Sanitation.
    condition_ids: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Devices, firmware, incidents, limit configs
# ---------------------------------------------------------------------------


class DeviceCreate(Body):
    device_type: int = Field(ge=1)
    amenity_id: uuid.UUID
    device_name: str | None = Field(default=None, max_length=255)
    device_uid: str | None = Field(default=None, max_length=255)
    appliance_name: str | None = Field(default=None, max_length=255)
    manufacturer_name: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    part_number: str | None = Field(default=None, max_length=255)
    mfg_date: datetime | None = None
    installed_on: datetime | None = None
    parent_device_id: uuid.UUID | None = None
    device_config_status: DeviceConfigStatus | None = None
    facility_id: uuid.UUID | None = None
    #: NOTE: `authentication_code` is intentionally NOT accepted here. It is a
    #: device credential; it is never set from, or returned to, the browser.


class DeviceUpdate(Body):
    device_name: str | None = Field(default=None, max_length=255)
    appliance_name: str | None = Field(default=None, max_length=255)
    manufacturer_name: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    part_number: str | None = Field(default=None, max_length=255)
    amenity_id: uuid.UUID | None = None
    parent_device_id: uuid.UUID | None = None
    installed_on: datetime | None = None
    device_config_status: DeviceConfigStatus | None = None
    #: A `firmware.id`. The column name says "version" but it is a UUID FK.
    expected_firmware_version: uuid.UUID | None = None


class DeviceDecommissionBody(Body):
    reason: str | None = Field(default=None, max_length=255)


class FirmwareCreate(Body):
    device_type_id: int = Field(ge=1)
    firmware_version: str = Field(min_length=1, max_length=20)
    firmware_filename: str = Field(min_length=1, max_length=255)
    firmware_url: str = Field(min_length=1, max_length=500)
    crc: str = Field(min_length=1, max_length=100)
    firmware_size: str | None = Field(default=None, max_length=50)
    release_date: datetime | None = None
    release_notes: str | None = None
    status: FirmwareStatus = "active"


class FirmwareUpdate(Body):
    firmware_filename: str | None = Field(default=None, min_length=1, max_length=255)
    firmware_url: str | None = Field(default=None, min_length=1, max_length=500)
    crc: str | None = Field(default=None, min_length=1, max_length=100)
    release_date: datetime | None = None
    release_notes: str | None = None
    status: FirmwareStatus | None = None
    decommission_reason: str | None = Field(default=None, max_length=255)


class FirmwareAssignBody(Body):
    """Set `device.expected_firmware_version` for the chosen devices.

    That column IS the assignment: the hub reads it and pulls the build. There
    is no command table, so nothing is queued or pushed from here.
    """

    device_ids: list[uuid.UUID] = Field(min_length=1)


class IncidentUpdate(Body):
    #: `incident_status`: 1 Unread, 2 Read, 3 Assigned, 4 Resolved.
    current_incident_status: int | None = Field(default=None, ge=1, le=4)
    assigned_to: uuid.UUID | None = None
    subject: str | None = Field(default=None, max_length=255)
    description: str | None = None


class LimitConfigCreate(Body):
    parameter: str = Field(min_length=1, max_length=100)
    device_name: str = Field(min_length=1, max_length=255)
    device_id: uuid.UUID | None = None
    limit_check: bool = True
    is_percentage_value: bool = True
    nominal: Decimal | None = None
    limit_low_percentage: Decimal | None = None
    limit_high_percentage: Decimal | None = None
    limit_low_value: Decimal | None = None
    limit_high_value: Decimal | None = None
    remarks: str = Field(default="", max_length=500)
    facility_id: uuid.UUID | None = None


class LimitConfigUpdate(Body):
    limit_check: bool | None = None
    is_percentage_value: bool | None = None
    nominal: Decimal | None = None
    limit_low_percentage: Decimal | None = None
    limit_high_percentage: Decimal | None = None
    limit_low_value: Decimal | None = None
    limit_high_value: Decimal | None = None
    remarks: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Facility, rooms and the room catalogue
# ---------------------------------------------------------------------------


class FacilityUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pin_code: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    additional_email: str | None = Field(default=None, max_length=500)
    google_map_link: str | None = Field(default=None, max_length=500)
    guest_rooms: int | None = Field(default=None, ge=0)
    default_key_user: uuid.UUID | None = None


class RoomCreate(Body):
    """A room IS an `amenity`.

    `status` is deliberately absent: room state belongs to the occupancy
    workflow (PATCH /occupancy/{amenity_id}), which guards against releasing a
    room a live stay still holds. A new room starts Unavailable.
    """

    name: str = Field(min_length=1, max_length=255)
    amenity_type_id: uuid.UUID
    package_id: uuid.UUID
    property_chain_id: uuid.UUID | None = None
    parent_amenity_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None


class RoomUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    amenity_type_id: uuid.UUID | None = None
    package_id: uuid.UUID | None = None
    property_chain_id: uuid.UUID | None = None
    parent_amenity_id: uuid.UUID | None = None


class AmenityTypeCreate(Body):
    name: str = Field(min_length=1, max_length=255)
    amenity_category: AmenityCategory
    facility_id: uuid.UUID | None = None
    status: int = Field(default=1, ge=0, le=1)


class AmenityTypeUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    amenity_category: AmenityCategory | None = None
    status: int | None = Field(default=None, ge=0, le=1)


class PackageCreate(Body):
    name: str = Field(min_length=1, max_length=255)
    amenity_type: uuid.UUID
    description: str | None = None
    is_sub_package: bool = False
    facility_id: uuid.UUID | None = None
    status: int = Field(default=1, ge=0, le=1)
    #: `package_feature` rows; each references a `feature`.
    feature_ids: list[uuid.UUID] = Field(default_factory=list)


class PackageUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    amenity_type: uuid.UUID | None = None
    description: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    feature_ids: list[uuid.UUID] | None = None


class FeatureCreate(Body):
    feature_name: str = Field(min_length=1, max_length=255)
    is_smart_feature: int | None = Field(default=None, ge=0, le=1)
    device_type: int | None = None
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class FeatureUpdate(Body):
    feature_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_smart_feature: int | None = Field(default=None, ge=0, le=1)
    status: int | None = Field(default=None, ge=0, le=1)


# ---------------------------------------------------------------------------
# Offers, events, holidays
# ---------------------------------------------------------------------------


class PromoCodeCreate(Body):
    promo_code: str = Field(min_length=1, max_length=100)
    offer_name: str | None = Field(default=None, max_length=255)
    promo_code_description: str | None = Field(default=None, max_length=500)
    offered_by: str | None = Field(default=None, max_length=255)
    start_time: datetime | None = None
    expiry_time: datetime | None = None
    discount_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    max_discount_value: Decimal | None = Field(default=None, ge=0)
    min_order_value: Decimal | None = Field(default=None, ge=0)
    status: int | None = Field(default=1, ge=0, le=1)
    #: `promo_code_amenity` rows -- which rooms the offer applies to.
    amenity_ids: list[uuid.UUID] = Field(default_factory=list)


class PromoCodeUpdate(Body):
    offer_name: str | None = Field(default=None, max_length=255)
    promo_code_description: str | None = Field(default=None, max_length=500)
    offered_by: str | None = Field(default=None, max_length=255)
    start_time: datetime | None = None
    expiry_time: datetime | None = None
    discount_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    max_discount_value: Decimal | None = Field(default=None, ge=0)
    min_order_value: Decimal | None = Field(default=None, ge=0)
    status: int | None = Field(default=None, ge=0, le=1)
    amenity_ids: list[uuid.UUID] | None = None


class FacilityEventCreate(Body):
    name: str = Field(min_length=1, max_length=255)
    venue: str | None = Field(default=None, max_length=255)
    chief_guests: str | None = Field(default=None, max_length=500)
    description: str | None = None
    expected_attendees: int | None = Field(default=None, ge=0)
    start_date_time: datetime | None = None
    end_date_time: datetime | None = None
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class FacilityEventUpdate(Body):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    venue: str | None = Field(default=None, max_length=255)
    chief_guests: str | None = Field(default=None, max_length=500)
    description: str | None = None
    expected_attendees: int | None = Field(default=None, ge=0)
    start_date_time: datetime | None = None
    end_date_time: datetime | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    cancellation_reason: str | None = Field(default=None, max_length=255)


class OccasionCreate(Body):
    """A holiday / occasion. `occasion_type` is the seeded lookup id."""

    occasion_type: int = Field(ge=1)
    occasion_name: str | None = Field(default=None, max_length=255)
    occasion_start_date: date
    occasion_end_date: date | None = None
    is_repeatable: int | None = Field(default=None, ge=0, le=1)
    notify_to_hub: int | None = Field(default=None, ge=0, le=1)
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class OccasionUpdate(Body):
    occasion_name: str | None = Field(default=None, max_length=255)
    occasion_type: int | None = Field(default=None, ge=1)
    occasion_start_date: date | None = None
    occasion_end_date: date | None = None
    is_repeatable: int | None = Field(default=None, ge=0, le=1)
    notify_to_hub: int | None = Field(default=None, ge=0, le=1)
    status: int | None = Field(default=None, ge=0, le=1)
