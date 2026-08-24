"""Notification dispatch and in-app activity feed read APIs (Phase 2.7).

    GET /api/v1/notification-templates · /{id}   notification_template
    GET /api/v1/notifications          · /{id}   notification (+ receivers)
    GET /api/v1/activities             · /{id}   activity (+ per-user read state)

TWO SYSTEMS, BOTH EXPOSED. IKANOS separates the in-app feed from the dispatch
queue and they use different status vocabularies:

    activity -> activity_notifier      status '0'/'1'/'2' = unread/read/clear
    notification -> notification_receiver -> notification_result
                                       status pending/processing/processed/error

Collapsing them would misrepresent the design, so both halves are returned.

NO ALERT LINK EXISTS. `notification.reference_id` is a bare BIGINT with no
foreign key. It holds an `activity.id` in the seeded data, but the schema
neither declares nor enforces that, so it is returned as a raw integer and
documented as unresolved. There is no path from a notification to an alert or
an incident in this schema.

RBAC: `read` on `dashboard`. There is NO notifications module in the 18-row
`role_module` registry -- see docs/PHASE2_7_ALERTS.md, this is an assumption
requiring sign-off, not a database fact.

SECURITY: the rendered message body, the template merge params, the provider
log, the per-recipient data bag, push tokens and recipient email/phone are all
withheld. The seeded template registry includes OTP and keypad-key templates,
so those columns would carry secrets in a real install.

READ-ONLY. Nothing here sends email, SMS or push.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import (
    NotificationChannel,
    NotificationStatus,
)
from app.schemas.health import ErrorResponse
from app.schemas.notification import (
    ActivityDetail,
    ActivityNotifierRead,
    ActivityRead,
    NotificationDetail,
    NotificationRead,
    NotificationReceiverRead,
    NotificationTemplateDetail,
    NotificationTemplateRead,
)
from app.services import notification as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

DASHBOARD_READ = [Depends(require_permission("dashboard", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

notification_templates_router = APIRouter(
    prefix="/notification-templates", tags=["notifications"],
    dependencies=DASHBOARD_READ, responses=AUTH_RESPONSES,
)
notifications_router = APIRouter(
    prefix="/notifications", tags=["notifications"],
    dependencies=DASHBOARD_READ, responses=AUTH_RESPONSES,
)
activities_router = APIRouter(
    prefix="/activities", tags=["notifications"],
    dependencies=DASHBOARD_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# notification_template
# ---------------------------------------------------------------------------


@notification_templates_router.get(
    "",
    response_model=Page[NotificationTemplateRead],
    summary="List notification templates",
    description=(
        "A template links only to a channel and a file path. It has no foreign "
        "key to alert type, occasion, event or recipient, so no such "
        "relationship is exposed."
    ),
)
def list_templates(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    template_type: NotificationChannel | None = Query(
        None, alias="type", description="notification_channel enum label",
    ),
) -> Page[NotificationTemplateRead]:
    rows, total = svc.list_templates(
        db, page=page, page_size=page_size, template_type=template_type
    )
    return Page[NotificationTemplateRead](
        items=[NotificationTemplateRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@notification_templates_router.get(
    "/{template_id}",
    response_model=NotificationTemplateDetail,
    responses=NOT_FOUND,
    summary="Get a notification template",
)
def get_template(template_id: uuid.UUID, db: DbSession) -> NotificationTemplateDetail:
    row = svc.get_template(db, template_id)
    if row is None:
        raise _missing("Notification template", template_id)
    return NotificationTemplateDetail(
        **NotificationTemplateRead.model_validate(row).model_dump(),
        notification_count=svc.template_notification_count(db, template_id),
    )


# ---------------------------------------------------------------------------
# notification (dispatch queue)
# ---------------------------------------------------------------------------


@notifications_router.get(
    "",
    response_model=Page[NotificationRead],
    summary="List dispatch notifications",
    description=(
        "`notification.status` is DELIVERY state (pending/processing/"
        "processed/error), not read/unread. Read state lives on "
        "`activity_notifier` -- see /activities."
    ),
)
def list_notifications(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    status_value: NotificationStatus | None = Query(
        None, alias="status", description="notification_status enum label",
    ),
    template_id: uuid.UUID | None = Query(None),
    template_type: NotificationChannel | None = Query(
        None, description="Channel of the template"
    ),
    app_user_id: uuid.UUID | None = Query(None, description="Via notification_receiver"),
    reference_id: int | None = Query(
        None, description="Raw BIGINT; no foreign key exists"
    ),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
) -> Page[NotificationRead]:
    rows, total = svc.list_notifications(
        db, page=page, page_size=page_size, status=status_value,
        template_id=template_id, template_type=template_type,
        app_user_id=app_user_id, reference_id=reference_id,
        created_from=created_from, created_to=created_to,
    )
    return Page[NotificationRead](
        items=[NotificationRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@notifications_router.get(
    "/{notification_id}",
    response_model=NotificationDetail,
    responses=NOT_FOUND,
    summary="Get a notification with its recipients and delivery results",
    description=(
        "Recipient contact details, the rendered body, the template params and "
        "the provider log are deliberately withheld -- they can contain OTPs "
        "and door keypad codes."
    ),
)
def get_notification(notification_id: int, db: DbSession) -> NotificationDetail:
    row = svc.get_notification(db, notification_id)
    if row is None:
        raise _missing("Notification", notification_id)
    receivers = svc.notification_receivers(db, notification_id)
    return NotificationDetail(
        **NotificationRead.model_validate(row).model_dump(),
        receivers=[NotificationReceiverRead.model_validate(r) for r in receivers],
    )


# ---------------------------------------------------------------------------
# activity (in-app feed)
# ---------------------------------------------------------------------------


@activities_router.get(
    "",
    response_model=Page[ActivityRead],
    summary="List activity-feed entries",
    description=(
        "The in-app feed behind the header bell. `unread_count` counts "
        "`activity_notifier` rows with status '0'."
    ),
)
def list_activities(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    activity_type_id: int | None = Query(None),
    entity_type_id: int | None = Query(
        None, description="1 Booking, 2 Occupancy, 3 Service Requests, "
                          "4 Maintenance Requests, 5 Default Key"
    ),
    actor_id: uuid.UUID | None = Query(None, description="Who caused the event"),
    stay_id: uuid.UUID | None = Query(None),
    app_user_id: uuid.UUID | None = Query(
        None, description="Recipient, via activity_notifier"
    ),
    unread_only: bool | None = Query(
        None, description="Has at least one notifier with status '0'"
    ),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
) -> Page[ActivityRead]:
    rows, total = svc.list_activities(
        db, page=page, page_size=page_size, facility_id=facility_id,
        activity_type_id=activity_type_id, entity_type_id=entity_type_id,
        actor_id=actor_id, stay_id=stay_id, app_user_id=app_user_id,
        unread_only=unread_only, created_from=created_from, created_to=created_to,
    )
    return Page[ActivityRead](
        items=[ActivityRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@activities_router.get(
    "/{activity_id}",
    response_model=ActivityDetail,
    responses=NOT_FOUND,
    summary="Get an activity with per-user read state",
)
def get_activity(activity_id: int, db: DbSession) -> ActivityDetail:
    row = svc.get_activity(db, activity_id)
    if row is None:
        raise _missing("Activity", activity_id)
    return ActivityDetail(
        **ActivityRead.model_validate(row).model_dump(),
        notifiers=[
            ActivityNotifierRead.model_validate(n)
            for n in svc.activity_notifiers(db, activity_id)
        ],
    )
