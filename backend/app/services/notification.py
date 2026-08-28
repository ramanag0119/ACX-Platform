"""Query logic for the notification dispatch queue and the in-app activity feed.

SECURITY: the projections below are explicit allow-lists that deliberately
OMIT `notification.params`, `notification_result.body`, `notification_result
.log`, `notification_receiver.data`, `notification_receiver.device_token`,
`notification_receiver.email`, `notification_receiver.phone` and
`activity.data`.

That is not caution for its own sake: the seeded template registry contains
`OTPTemplate`, `KeySMSTemplate`, `MaintenanceKeypadKey`,
`KeyNotificationTemplate` and `MaintenanceAppKey`, so in a real install the
rendered body and its merge params hold one-time passwords and door keypad
codes. Selecting those columns here would publish them over HTTP.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Activity,
    ActivityNotifier,
    ActivityType,
    AppUser,
    EntityType,
    Notification,
    NotificationReceiver,
    NotificationResult,
    NotificationTemplate,
)

#: activity_notifier.status is enum('0','1','2') -- digit strings, not ints.
NOTIFIER_STATUS_LABELS = {"0": "unread", "1": "read", "2": "clear"}


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# notification_template
# ---------------------------------------------------------------------------


def list_templates(
    db: Session, *, page: int, page_size: int, template_type: str | None = None
):
    stmt = select(NotificationTemplate).order_by(NotificationTemplate.name)
    if template_type:
        stmt = stmt.where(NotificationTemplate.type == template_type)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_template(db: Session, template_id: uuid.UUID) -> NotificationTemplate | None:
    return db.get(NotificationTemplate, template_id)


def template_notification_count(db: Session, template_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.template_id == template_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# notification (dispatch queue)
# ---------------------------------------------------------------------------


def _notification_stmt() -> Select:
    receiver_count = (
        select(func.count())
        .select_from(NotificationReceiver)
        .where(NotificationReceiver.notification_id == Notification.id)
        .scalar_subquery()
    )
    return (
        select(
            Notification.id,
            Notification.status,
            Notification.created_by,
            Notification.template_id,
            NotificationTemplate.name.label("template_name"),
            NotificationTemplate.type.label("template_type"),
            Notification.reference_id,
            receiver_count.label("receiver_count"),
            Notification.created_on,
            Notification.updated_on,
        )
        # `params` is NOT selected -- it would carry the OTP / keypad key.
        .select_from(Notification)
        .outerjoin(
            NotificationTemplate, NotificationTemplate.id == Notification.template_id
        )
    )


def list_notifications(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    template_id: uuid.UUID | None = None,
    template_type: str | None = None,
    app_user_id: uuid.UUID | None = None,
    reference_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _notification_stmt().order_by(Notification.created_on.desc())
    if status:
        stmt = stmt.where(Notification.status == status)
    if template_id:
        stmt = stmt.where(Notification.template_id == template_id)
    if template_type:
        stmt = stmt.where(NotificationTemplate.type == template_type)
    if reference_id is not None:
        stmt = stmt.where(Notification.reference_id == reference_id)
    if app_user_id:
        stmt = stmt.where(
            select(NotificationReceiver)
            .where(
                NotificationReceiver.notification_id == Notification.id,
                NotificationReceiver.app_user_id == app_user_id,
            )
            .exists()
        )
    if created_from:
        stmt = stmt.where(Notification.created_on >= created_from)
    if created_to:
        stmt = stmt.where(Notification.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_notification(db: Session, notification_id: int):
    return db.execute(
        _notification_stmt().where(Notification.id == notification_id)
    ).mappings().one_or_none()


def notification_receivers(db: Session, notification_id: int) -> list[dict]:
    """Recipients and their per-channel delivery results.

    Contact columns and both JSON bags are omitted; `app_user_id` is returned
    so contact details stay behind the /users endpoint and its own grant.
    """
    receivers = db.execute(
        select(
            NotificationReceiver.id,
            NotificationReceiver.app_user_id,
            NotificationReceiver.name,
        )
        .where(NotificationReceiver.notification_id == notification_id)
        .order_by(NotificationReceiver.id)
    ).mappings().all()
    if not receivers:
        return []

    results = db.execute(
        select(
            NotificationResult.receiver_id,
            NotificationResult.id,
            NotificationResult.type,
            NotificationResult.status,
            NotificationResult.created_on,
        )
        # `body` and `log` are NOT selected -- the rendered message and the
        # provider response can both contain secrets.
        .where(NotificationResult.receiver_id.in_([r["id"] for r in receivers]))
        .order_by(NotificationResult.id)
    ).all()

    by_receiver: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        by_receiver[r.receiver_id].append(
            {
                "id": r.id,
                "type": r.type,
                "status": r.status,
                "created_on": r.created_on,
            }
        )

    return [
        {**dict(r), "results": by_receiver.get(r["id"], [])} for r in receivers
    ]


# ---------------------------------------------------------------------------
# activity (in-app feed)
# ---------------------------------------------------------------------------


def _activity_stmt() -> Select:
    notifier_count = (
        select(func.count())
        .select_from(ActivityNotifier)
        .where(ActivityNotifier.activity_id == Activity.id)
        .scalar_subquery()
    )
    unread_count = (
        select(func.count())
        .select_from(ActivityNotifier)
        .where(
            ActivityNotifier.activity_id == Activity.id,
            ActivityNotifier.status == "0",
        )
        .scalar_subquery()
    )
    return (
        select(
            Activity.id,
            Activity.activity_type_id,
            ActivityType.activity_type.label("activity_type_name"),
            Activity.entity_type_id,
            EntityType.entity_type.label("entity_type_name"),
            Activity.entity_id,
            Activity.facility_id,
            Activity.actor_id,
            AppUser.first_name.label("actor_first_name"),
            AppUser.last_name.label("actor_last_name"),
            Activity.stay_id,
            Activity.data_version,
            Activity.activity_response_ids,
            notifier_count.label("notifier_count"),
            unread_count.label("unread_count"),
            Activity.created_on,
            Activity.updated_on,
        )
        # `data` is NOT selected -- unbounded activity payload.
        .select_from(Activity)
        .join(ActivityType, ActivityType.id == Activity.activity_type_id)
        .join(EntityType, EntityType.id == Activity.entity_type_id)
        .outerjoin(AppUser, AppUser.id == Activity.actor_id)
    )


def _shape_activity(row) -> dict:
    data = dict(row)
    actor_id = data.pop("actor_id")
    first = data.pop("actor_first_name")
    last = data.pop("actor_last_name")
    data["actor"] = (
        None
        if actor_id is None
        else {"id": actor_id, "name": " ".join(p for p in (first, last) if p)}
    )
    return data


def list_activities(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    activity_type_id: int | None = None,
    entity_type_id: int | None = None,
    actor_id: uuid.UUID | None = None,
    stay_id: uuid.UUID | None = None,
    app_user_id: uuid.UUID | None = None,
    unread_only: bool | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _activity_stmt().order_by(Activity.created_on.desc())
    if facility_id:
        stmt = stmt.where(Activity.facility_id == facility_id)
    if activity_type_id is not None:
        stmt = stmt.where(Activity.activity_type_id == activity_type_id)
    if entity_type_id is not None:
        stmt = stmt.where(Activity.entity_type_id == entity_type_id)
    if actor_id:
        stmt = stmt.where(Activity.actor_id == actor_id)
    if stay_id:
        stmt = stmt.where(Activity.stay_id == stay_id)
    if app_user_id or unread_only:
        conditions = [ActivityNotifier.activity_id == Activity.id]
        if app_user_id:
            conditions.append(ActivityNotifier.app_user_id == app_user_id)
        if unread_only:
            conditions.append(ActivityNotifier.status == "0")
        stmt = stmt.where(select(ActivityNotifier).where(*conditions).exists())
    if created_from:
        stmt = stmt.where(Activity.created_on >= created_from)
    if created_to:
        stmt = stmt.where(Activity.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return [_shape_activity(r) for r in rows], total


def get_activity(db: Session, activity_id: int):
    row = db.execute(
        _activity_stmt().where(Activity.id == activity_id)
    ).mappings().one_or_none()
    return _shape_activity(row) if row is not None else None


def activity_notifiers(db: Session, activity_id: int) -> list[dict]:
    rows = db.execute(
        select(
            ActivityNotifier.app_user_id,
            AppUser.user_name,
            ActivityNotifier.status,
            ActivityNotifier.user_type,
            ActivityNotifier.notification_type,
        )
        .outerjoin(AppUser, AppUser.id == ActivityNotifier.app_user_id)
        .where(ActivityNotifier.activity_id == activity_id)
        .order_by(AppUser.user_name)
    ).mappings().all()
    return [
        {
            **dict(r),
            "status_label": NOTIFIER_STATUS_LABELS.get(r["status"], r["status"]),
        }
        for r in rows
    ]
