"""Query logic for the notification dispatch queue.

SECURITY: the projections below are explicit allow-lists that deliberately
OMIT `notification.params`, `notification_result.body`, `notification_result
.log`, `notification_receiver.data`, `notification_receiver.device_token`,
`notification_receiver.email`, `notification_receiver.phone`.

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

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationReceiver,
    NotificationResult,
    NotificationTemplate,
)


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
