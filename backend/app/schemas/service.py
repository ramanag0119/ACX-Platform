"""Response models for the service catalogue and service requests.

Every field maps to a real column or is an explicitly-named value derived from
a real foreign key.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * There is **no `service` table and no `service_item` table**. The catalogue
    is three levels deep:

        service_type  (7 lookup rows -- the Services Tracking tabs)
            -> service_category        (Services Setup groups)
                -> service_category_item

  * A service request is `service_request`, with line items in
    `service_request_item`. Status is an FK to `service_status` (5 rows);
    there is no separate `service_request_status` table.

  * `service_category_item.price_per_unit` is a real column and IS exposed.
    It is the price of a SERVICE ITEM (laundry, breakfast, airport transfer).
    It is NOT room tariff and does NOT resolve OPEN DECISION #10, which
    concerns `package.price` and `invoice.status` -- both still absent.

NOT PRESENT, and therefore not exposed: SLA, priority, duration, availability,
service-level tariff.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Catalogue level 1 -- service_type
# ---------------------------------------------------------------------------


class ServiceTypeRead(ORMModel):
    """A row of `service_type`. These 7 rows are the Services Tracking tabs."""

    id: int = Field(examples=[1])
    name: str = Field(examples=["Room Service"])
    created_on: datetime
    updated_on: datetime


class ServiceTypeDetail(ServiceTypeRead):
    category_count: int = Field(description="Categories under this service type")
    request_count: int = Field(description="Service requests of this type")


# ---------------------------------------------------------------------------
# Status vocabulary -- service_status
# ---------------------------------------------------------------------------


class ServiceStatusRead(ORMModel):
    """A row of `service_status`: Pending, Assigned, Partially completed,
    Completed, Canceled. There is no status-transition table in the schema."""

    id: int = Field(examples=[1])
    name: str = Field(examples=["Pending"])
    created_on: datetime
    updated_on: datetime


# ---------------------------------------------------------------------------
# Catalogue level 2 -- service_category
# ---------------------------------------------------------------------------


class ServiceCategoryRead(ORMModel):
    """A row of `service_category` -- a Services Setup group."""

    id: uuid.UUID
    category_name: str | None = Field(default=None, examples=["Housekeeping"])
    description: str | None = None
    service_type: int = Field(examples=[1], description="service_type.id")
    service_type_name: str | None = Field(default=None, examples=["Room Service"])
    service_category_key: str | None = Field(default=None, examples=["HOUSEKEEPING"])
    category_icon: uuid.UUID | None = Field(default=None, description="attachment.id")
    facility_id: uuid.UUID | None = None
    status: int | None = None
    created_on: datetime
    updated_on: datetime


class ServiceCategoryDetail(ServiceCategoryRead):
    item_count: int = Field(description="Rows in service_category_item")


# ---------------------------------------------------------------------------
# Catalogue level 3 -- service_category_item
# ---------------------------------------------------------------------------


class ServiceItemRead(ORMModel):
    """A row of `service_category_item`."""

    id: uuid.UUID
    item_name: str = Field(examples=["Wash & Fold (per kg)"])
    description: str | None = None
    category_id: uuid.UUID
    category_name: str | None = Field(default=None, examples=["Laundry"])
    service_type: int | None = Field(default=None, examples=[1])
    service_type_name: str | None = Field(default=None, examples=["Room Service"])
    price_per_unit: Decimal | None = Field(
        default=None,
        examples=["150.00"],
        description=(
            "Real column. Service-item price only -- NOT room tariff. "
            "OPEN DECISION #10 (package.price, invoice.status) remains unresolved."
        ),
    )
    amenity_id: uuid.UUID | None = Field(
        default=None, description="Venue this item belongs to, e.g. a restaurant"
    )
    item_icon: uuid.UUID | None = Field(default=None, description="attachment.id")
    facility_id: uuid.UUID | None = None
    status: int | None = None
    created_on: datetime
    updated_on: datetime


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


class ServiceRequestItemRead(ORMModel):
    """A row of `service_request_item`.

    Line items carry their own status, which is how a request reaches
    "Partially completed": its items differ in status.
    """

    id: uuid.UUID
    item_id: uuid.UUID | None = None
    item_name: str | None = Field(default=None, examples=["Extra Towels"])
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    quantity: int | None = None
    price_per_unit: Decimal | None = None
    assigned_to: UserRef | None = None
    status: int | None = None
    status_name: str | None = Field(default=None, examples=["Completed"])
    created_on: datetime
    updated_on: datetime


class ServiceRequestRead(ORMModel):
    """A row of `service_request`.

    There is NO `priority` column and none is simulated. `net_amount`,
    `total_tax` and `total_amount` are real columns but are NULL throughout the
    seeded data -- no amount-computation rule exists in the schema.
    """

    id: uuid.UUID
    ref_number: str | None = Field(default=None, examples=["SR-2026-0001"])
    description: str | None = None
    service_type: int
    service_type_name: str | None = Field(default=None, examples=["Room Service"])
    category_id: uuid.UUID | None = None
    category_name: str | None = Field(default=None, examples=["Housekeeping"])
    status: int | None = None
    status_name: str | None = Field(default=None, examples=["Assigned"])
    status_reason: str | None = None
    request_source: str | None = Field(
        default=None, examples=["ikanos"], description="ikanos | porta"
    )
    facility_id: uuid.UUID | None = None
    amenity_id: uuid.UUID | None = Field(default=None, description="The room")
    amenity_name: str | None = Field(default=None, examples=["101"])
    stay_id: uuid.UUID | None = None
    stay_ref_number: str | None = Field(default=None, examples=["STY-2026-0001"])
    department_id: uuid.UUID | None = None
    department_name: str | None = Field(default=None, examples=["Housekeeping"])
    requester: UserRef | None = Field(default=None, description="app_user_id")
    assignee: UserRef | None = Field(default=None, description="assigned_to")
    promo_code_id: uuid.UUID | None = None
    net_amount: Decimal | None = None
    total_tax: Decimal | None = None
    total_amount: Decimal | None = None
    expected_date: datetime | None = None
    completed_on: datetime | None = None
    created_on: datetime
    updated_on: datetime


class ServiceRequestDetail(ServiceRequestRead):
    items: list[ServiceRequestItemRead]
    item_count: int
