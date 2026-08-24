"""Write endpoints for service requests and the service catalogue.

    POST   /service-requests                 raise a request (Tickets, guest flow)
    PATCH  /service-requests/{id}            edit / assign / change status
    PUT    /service-requests/{id}/items      replace the item lines
    POST   /service-requests/{id}/cancel     cancel with a reason
    POST   /service-categories               catalogue: category
    PATCH  /service-categories/{id}
    POST   /service-items                    catalogue: item
    PATCH  /service-items/{id}

RBAC mirrors the read side, which is also how IKANOS splits these screens:
    `service_tracking` write -> requests (Services Tracking, Tickets)
    `service_setup` write    -> the catalogue (Services Setup)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.health import ErrorResponse
from app.schemas.ops_write import (
    CancelBody,
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceItemCreate,
    ServiceItemUpdate,
    ServiceRequestCreate,
    ServiceRequestItems,
    ServiceRequestUpdate,
)
from app.schemas.service import (
    ServiceCategoryRead,
    ServiceItemRead,
    ServiceRequestDetail,
    ServiceRequestRead,
)
from app.services import access_write
from app.services import service as read_service
from app.services import services_write as service

WRITE_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with existing data"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}

TRACKING_WRITE = [Depends(require_permission("service_tracking", "write"))]
SETUP_WRITE = [Depends(require_permission("service_setup", "write"))]

service_requests_write_router = APIRouter(
    prefix="/service-requests", tags=["service-requests"], responses=WRITE_RESPONSES
)
service_categories_write_router = APIRouter(
    prefix="/service-categories", tags=["services"], responses=WRITE_RESPONSES
)
service_items_write_router = APIRouter(
    prefix="/service-items", tags=["services"], responses=WRITE_RESPONSES
)


def _request_detail(db, request_id: uuid.UUID) -> ServiceRequestDetail:
    """Return through the read projection so the write cannot widen the payload."""
    row = read_service.get_service_request(db, request_id)
    # `request_items` batches by id list -- the same call the list endpoint makes.
    items = read_service.request_items(db, [request_id]).get(request_id, [])
    return ServiceRequestDetail(
        **ServiceRequestRead.model_validate(row).model_dump(),
        items=items,
        item_count=len(items),
    )


@service_requests_write_router.post(
    "",
    response_model=ServiceRequestDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=TRACKING_WRITE,
    summary="Raise a service request",
    description=(
        "Inserts `service_request` plus one `service_request_item` per line, in "
        "a single transaction. `ref_number` follows the seeded SR-YYYY-NNNN "
        "format. Naming an assignee moves the request straight to Assigned, "
        "which is what every seeded row with an assignee shows. Item prices are "
        "copied from the catalogue -- the only price the schema holds."
    ),
)
def create_service_request(
    payload: ServiceRequestCreate, db: DbSession, current_user: CurrentUser
) -> ServiceRequestDetail:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    data = payload.model_dump()
    data["items"] = [item.model_dump() for item in payload.items]
    request = service.create_service_request(
        db, data=data, actor_id=current_user.id, facility_id=facility_id
    )
    return _request_detail(db, request.id)


@service_requests_write_router.patch(
    "/{request_id}",
    response_model=ServiceRequestDetail,
    dependencies=TRACKING_WRITE,
    summary="Update, assign or progress a service request",
    description=(
        "`completed_on` is stamped when the request reaches Completed (status 4) "
        "and cleared when it leaves -- the invariant every seeded row holds."
    ),
)
def update_service_request(
    request_id: uuid.UUID,
    payload: ServiceRequestUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ServiceRequestDetail:
    service.update_service_request(
        db,
        request_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return _request_detail(db, request_id)


@service_requests_write_router.put(
    "/{request_id}/items",
    response_model=ServiceRequestDetail,
    dependencies=TRACKING_WRITE,
    summary="Replace a request's item lines",
)
def replace_items(
    request_id: uuid.UUID,
    payload: ServiceRequestItems,
    db: DbSession,
    current_user: CurrentUser,
) -> ServiceRequestDetail:
    service.replace_service_request_items(
        db,
        request_id,
        items=[item.model_dump(exclude_unset=True) for item in payload.items],
        actor_id=current_user.id,
    )
    return _request_detail(db, request_id)


@service_requests_write_router.post(
    "/{request_id}/cancel",
    response_model=ServiceRequestDetail,
    dependencies=TRACKING_WRITE,
    summary="Cancel a service request",
)
def cancel_service_request(
    request_id: uuid.UUID,
    payload: CancelBody,
    db: DbSession,
    current_user: CurrentUser,
) -> ServiceRequestDetail:
    service.cancel_service_request(
        db, request_id, reason=payload.reason, actor_id=current_user.id
    )
    return _request_detail(db, request_id)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


@service_categories_write_router.post(
    "",
    response_model=ServiceCategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=SETUP_WRITE,
    summary="Create a service category",
)
def create_category(
    payload: ServiceCategoryCreate, db: DbSession, current_user: CurrentUser
) -> ServiceCategoryRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_service_category(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return ServiceCategoryRead.model_validate(read_service.get_service_category(db, row.id))


@service_categories_write_router.patch(
    "/{category_id}",
    response_model=ServiceCategoryRead,
    dependencies=SETUP_WRITE,
    summary="Update a service category",
)
def update_category(
    category_id: uuid.UUID, payload: ServiceCategoryUpdate, db: DbSession
) -> ServiceCategoryRead:
    service.update_service_category(
        db, category_id, changes=payload.model_dump(exclude_unset=True)
    )
    return ServiceCategoryRead.model_validate(
        read_service.get_service_category(db, category_id)
    )


@service_items_write_router.post(
    "",
    response_model=ServiceItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=SETUP_WRITE,
    summary="Create a service item",
)
def create_item(
    payload: ServiceItemCreate, db: DbSession, current_user: CurrentUser
) -> ServiceItemRead:
    facility_id = access_write.default_facility_id(db, current_user.facility_ids)
    row = service.create_service_item(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return ServiceItemRead.model_validate(read_service.get_service_item(db, row.id))


@service_items_write_router.patch(
    "/{item_id}",
    response_model=ServiceItemRead,
    dependencies=SETUP_WRITE,
    summary="Update a service item",
)
def update_item(
    item_id: uuid.UUID, payload: ServiceItemUpdate, db: DbSession
) -> ServiceItemRead:
    service.update_service_item(
        db, item_id, changes=payload.model_dump(exclude_unset=True)
    )
    return ServiceItemRead.model_validate(read_service.get_service_item(db, item_id))
