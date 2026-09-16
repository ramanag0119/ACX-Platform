"""Service catalogue and service request read APIs (Phase 2.5).

    GET /api/v1/service-types        · /{id}    service_type   (7 lookup rows)
    GET /api/v1/service-statuses     · /{id}    service_status (5 lookup rows)
    GET /api/v1/service-categories   · /{id}    service_category
    GET /api/v1/service-items        · /{id}    service_category_item
    GET /api/v1/service-requests     · /{id}    service_request (+ items)

NAMING. The requested `/services` and `/service-items` do not map one-to-one
onto the schema: there is no `service` table and no `service_item` table. The
catalogue is three levels -- service_type -> service_category ->
service_category_item -- so each level is exposed under a route named after the
table it reads. Nothing is flattened into an invented "service" entity.

RBAC, taken from the seeded `role_module` registry rather than assumed:

    catalogue configuration  ->  `service_setup`     (Services Setup screen)
        /service-categories, /service-items
    day-to-day tracking      ->  `service_tracking`  (Services Tracking screen)
        /service-types, /service-statuses, /service-requests

That split is what the database already says: the Duty Manager role holds
`service_tracking` but NOT `service_setup`, which matches the KT handbook --
Manager runs operations, Admin owns configuration.

READ-ONLY. No POST/PATCH/PUT/DELETE. See docs/PHASE2_5_SERVICES.md for the
four blockers that make a safe write path impossible from the current schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import RequestSource
from app.schemas.health import ErrorResponse
from app.schemas.service import (
    ServiceCategoryDetail,
    ServiceCategoryRead,
    ServiceItemRead,
    ServiceRequestDetail,
    ServiceRequestItemRead,
    ServiceRequestRead,
    ServiceStatusRead,
    ServiceTypeDetail,
    ServiceTypeRead,
)
from app.services import service as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

SETUP_READ = [Depends(require_permission("service_setup", "read"))]
TRACKING_READ = [Depends(require_permission("service_tracking", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

service_types_router = APIRouter(
    prefix="/service-types", tags=["services"],
    dependencies=TRACKING_READ, responses=AUTH_RESPONSES,
)
service_statuses_router = APIRouter(
    prefix="/service-statuses", tags=["services"],
    dependencies=TRACKING_READ, responses=AUTH_RESPONSES,
)
service_categories_router = APIRouter(
    prefix="/service-categories", tags=["services"],
    dependencies=SETUP_READ, responses=AUTH_RESPONSES,
)
service_items_router = APIRouter(
    prefix="/service-items", tags=["services"],
    dependencies=SETUP_READ, responses=AUTH_RESPONSES,
)
service_requests_router = APIRouter(
    prefix="/service-requests", tags=["service-requests"],
    dependencies=TRACKING_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# service_type
# ---------------------------------------------------------------------------


@service_types_router.get(
    "",
    response_model=Page[ServiceTypeRead],
    summary="List service types",
    description="The 7 IKANOS service types -- the Services Tracking tabs.",
)
def list_service_types(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[ServiceTypeRead]:
    rows, total = svc.list_service_types(db, page=page, page_size=page_size)
    return Page[ServiceTypeRead](
        items=[ServiceTypeRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@service_types_router.get(
    "/{service_type_id}",
    response_model=ServiceTypeDetail,
    responses=NOT_FOUND,
    summary="Get a service type",
)
def get_service_type(service_type_id: int, db: DbSession) -> ServiceTypeDetail:
    row = svc.get_service_type(db, service_type_id)
    if row is None:
        raise _missing("Service type", service_type_id)
    return ServiceTypeDetail(
        **ServiceTypeRead.model_validate(row).model_dump(),
        **svc.service_type_counts(db, service_type_id),
    )


# ---------------------------------------------------------------------------
# service_status
# ---------------------------------------------------------------------------


@service_statuses_router.get(
    "",
    response_model=Page[ServiceStatusRead],
    summary="List service statuses",
    description=(
        "Pending, Assigned, Partially completed, Completed, Canceled. "
        "The schema holds no status-transition table."
    ),
)
def list_service_statuses(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[ServiceStatusRead]:
    rows, total = svc.list_service_statuses(db, page=page, page_size=page_size)
    return Page[ServiceStatusRead](
        items=[ServiceStatusRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@service_statuses_router.get(
    "/{status_id}",
    response_model=ServiceStatusRead,
    responses=NOT_FOUND,
    summary="Get a service status",
)
def get_service_status(status_id: int, db: DbSession) -> ServiceStatusRead:
    row = svc.get_service_status(db, status_id)
    if row is None:
        raise _missing("Service status", status_id)
    return ServiceStatusRead.model_validate(row)


# ---------------------------------------------------------------------------
# service_category
# ---------------------------------------------------------------------------


@service_categories_router.get(
    "", response_model=Page[ServiceCategoryRead], summary="List service categories"
)
def list_service_categories(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    service_type: int | None = Query(None, description="service_type.id"),
    status_id: int | None = Query(None, alias="status"),
) -> Page[ServiceCategoryRead]:
    rows, total = svc.list_service_categories(
        db, page=page, page_size=page_size, facility_id=facility_id,
        service_type=service_type, status=status_id,
    )
    return Page[ServiceCategoryRead](
        items=[ServiceCategoryRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@service_categories_router.get(
    "/{category_id}",
    response_model=ServiceCategoryDetail,
    responses=NOT_FOUND,
    summary="Get a service category",
)
def get_service_category(category_id: uuid.UUID, db: DbSession) -> ServiceCategoryDetail:
    row = svc.get_service_category(db, category_id)
    if row is None:
        raise _missing("Service category", category_id)
    return ServiceCategoryDetail(
        **ServiceCategoryRead.model_validate(row).model_dump(),
        item_count=svc.category_item_count(db, category_id),
    )


# ---------------------------------------------------------------------------
# service_category_item
# ---------------------------------------------------------------------------


@service_items_router.get(
    "",
    response_model=Page[ServiceItemRead],
    summary="List service items",
    description=(
        "`price_per_unit` is a real column and is the ONLY price in the schema. "
        "It prices a service item, not a room -- OPEN DECISION #10 "
        "(package.price, invoice.status) remains unresolved."
    ),
)
def list_service_items(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    service_type: int | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None, description="Venue, e.g. a restaurant"),
    status_id: int | None = Query(None, alias="status"),
    has_price: bool | None = Query(None, description="Filter on price_per_unit IS NULL"),
) -> Page[ServiceItemRead]:
    rows, total = svc.list_service_items(
        db, page=page, page_size=page_size, facility_id=facility_id,
        category_id=category_id, service_type=service_type, amenity_id=amenity_id,
        status=status_id, has_price=has_price,
    )
    return Page[ServiceItemRead](
        items=[ServiceItemRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@service_items_router.get(
    "/{item_id}",
    response_model=ServiceItemRead,
    responses=NOT_FOUND,
    summary="Get a service item",
)
def get_service_item(item_id: uuid.UUID, db: DbSession) -> ServiceItemRead:
    row = svc.get_service_item(db, item_id)
    if row is None:
        raise _missing("Service item", item_id)
    return ServiceItemRead.model_validate(row)


# ---------------------------------------------------------------------------
# service_request
# ---------------------------------------------------------------------------


@service_requests_router.get(
    "", response_model=Page[ServiceRequestRead], summary="List service requests"
)
def list_service_requests(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    service_type: int | None = Query(None, description="service_type.id"),
    status_id: int | None = Query(
        None, alias="status",
        description="service_status.id: 1 Pending, 2 Assigned, "
                    "3 Partially completed, 4 Completed, 5 Canceled",
    ),
    category_id: uuid.UUID | None = Query(None),
    assigned_to: uuid.UUID | None = Query(None),
    app_user_id: uuid.UUID | None = Query(None, description="The requester"),
    stay_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None, description="The room"),
    department_id: uuid.UUID | None = Query(None),
    request_source: RequestSource | None = Query(
        None, description="request_source: ikanos | porta"
    ),
    unassigned: bool | None = Query(None, description="assigned_to IS NULL"),
    created_from: datetime | None = Query(None, description="created_on >="),
    created_to: datetime | None = Query(None, description="created_on <="),
) -> Page[ServiceRequestRead]:
    rows, total = svc.list_service_requests(
        db, page=page, page_size=page_size, facility_id=facility_id,
        service_type=service_type, status=status_id, category_id=category_id,
        assigned_to=assigned_to, app_user_id=app_user_id, stay_id=stay_id,
        amenity_id=amenity_id, department_id=department_id,
        request_source=request_source, unassigned=unassigned,
        created_from=created_from, created_to=created_to,
    )
    return Page[ServiceRequestRead](
        items=[ServiceRequestRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@service_requests_router.get(
    "/{request_id}",
    response_model=ServiceRequestDetail,
    responses=NOT_FOUND,
    summary="Get a service request with its line items",
)
def get_service_request(request_id: uuid.UUID, db: DbSession) -> ServiceRequestDetail:
    row = svc.get_service_request(db, request_id)
    if row is None:
        raise _missing("Service request", request_id)
    items = svc.request_items(db, [request_id]).get(request_id, [])
    return ServiceRequestDetail(
        **ServiceRequestRead.model_validate(row).model_dump(),
        items=[ServiceRequestItemRead.model_validate(i) for i in items],
        item_count=len(items),
    )
