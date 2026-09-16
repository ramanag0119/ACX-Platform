"""Step 10 - the in-app activity feed and the notification dispatch queue.

IKANOS keeps these two things apart, and the Phase 1 foundation collapsed them
into one table. Both halves are seeded so the split is demonstrable:

    (a) feed      activity -> activity_notifier   (per-user read state)
    (b) dispatch  notification -> notification_receiver -> notification_result

`activity.activity_response_ids` links a feed item to the dispatch rows it
produced, which is the join the Header bell and the delivery log share.

`activity.entity_id` is polymorphic by design and carries no FK -- it points at
a booking, a room or a ticket depending on `entity_type_id`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    ActivityNotifier,
    ActivityRoleAssociation,
    Notification,
    NotificationReceiver,
    NotificationResult,
    NotificationTemplate,
)
from seeds.data import reference as ref
from seeds.helpers import DEMO_NOW, did, hours, upsert

# entity_type ids: 1 Booking, 2 Occupancy, 3 Service Requests,
#                  4 Maintenance Requests, 5 Default Key
BOOKING, OCCUPANCY, SERVICE_REQUESTS, MAINTENANCE_REQUESTS, DEFAULT_KEY = 1, 2, 3, 4, 5

# activity_notifier.status is enum('0','1','2') -> unread / read / clear
UNREAD, READ, CLEAR = "0", "1", "2"

# Which roles subscribe to which activity type.
ROLE_ACTIVITY = {
    "manager": [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 18, 21],
    "front-desk": [1, 5, 6, 7, 8, 17, 18, 21],
    "housekeeping": [9, 10, 11, 12, 13, 22],
    "technician": [12, 13, 21],
    "administrator": [1, 9, 12, 21],
}

# (key, activity_type id, entity_type, entity ref, actor, stay ref or None,
#  hours ago, payload, recipients [(user, status)])
ACTIVITIES = [
    ("act-booking-0001", 1, BOOKING, 1, "rahul.das", "STY-2026-0001", 50,
     {"guest": "Aarav Sharma", "room": "101"},
     [("kavya.iyer", READ), ("rahul.das", READ)]),
    ("act-checkin-0001", 17, BOOKING, 1, "rahul.das", "STY-2026-0001", 48,
     {"guest": "Aarav Sharma", "room": "101"},
     [("kavya.iyer", READ), ("rahul.das", CLEAR)]),
    ("act-keypad-key-0001", 2, BOOKING, 1, "rahul.das", "STY-2026-0001", 47,
     {"room": "101", "key_type": "Primary"},
     [("rahul.das", READ)]),
    ("act-sr-created-0002", 9, SERVICE_REQUESTS, 2, "meera.krishnan",
     "STY-2026-0002", 6,
     {"ref": "SR-2026-0002", "room": "205"},
     [("kavya.iyer", UNREAD), ("fatima.sheikh", UNREAD)]),
    ("act-sr-assigned-0002", 10, SERVICE_REQUESTS, 2, "kavya.iyer",
     "STY-2026-0002", 5,
     {"ref": "SR-2026-0002", "assignee": "Fatima Sheikh"},
     [("fatima.sheikh", READ)]),
    ("act-device-not-found", 21, BOOKING, 3, "system", None, 9,
     {"device": "106-hub", "room": "106"},
     [("vikram.rao", UNREAD), ("kavya.iyer", UNREAD)]),
    ("act-checkout-initiated", 5, OCCUPANCY, 6, "ishaan.gupta",
     "STY-2026-0006", 3,
     {"ref": "STY-2026-0006", "room": "106"},
     [("rahul.das", UNREAD), ("kavya.iyer", READ)]),
    ("act-maint-created", 12, MAINTENANCE_REQUESTS, 4, "kavya.iyer", None, 20,
     {"type": "planned", "rooms": ["104", "204"]},
     [("vikram.rao", READ)]),
    ("act-sanitization", 22, BOOKING, 5, "sneha.pillai", None, 12,
     {"rooms": ["103"]},
     [("fatima.sheikh", CLEAR)]),
    ("act-default-key-shared", 20, DEFAULT_KEY, 7, "arjun.menon", None, 30,
     {"key_type": "Default"},
     [("rahul.das", READ)]),
]

# (key, activity key, template name, channel, status, recipients)
DISPATCH = [
    ("ntf-booking-0001", "act-booking-0001", "SmartBookingSMSTemplate", "sms",
     "processed", [("aarav.sharma", "sent")]),
    ("ntf-key-0001", "act-keypad-key-0001", "KeySMSTemplate", "sms",
     "processed", [("aarav.sharma", "sent")]),
    ("ntf-checkout-0006", "act-checkout-initiated", "CheckoutInitiationTemplate",
     "push notification", "processed", [("ishaan.gupta", "sent")]),
    ("ntf-sr-0002", "act-sr-assigned-0002", "push", "push notification",
     "processed", [("fatima.sheikh", "sent")]),
    ("ntf-alert-106", "act-device-not-found", "AlertSMSTemplate", "sms",
     "error", [("vikram.rao", "failed")]),
    ("ntf-doc-approval", "act-booking-0001", "DocumentApprovalStatusNotification",
     "push notification", "pending", [("daniel.foster", "queued")]),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    users = ctx["users"]
    roles = ctx["roles"]
    stays = ctx["stays"]

    n_assoc = 0
    for role_key, activity_type_ids in ROLE_ACTIVITY.items():
        for activity_type_id in activity_type_ids:
            upsert(
                session,
                ActivityRoleAssociation,
                {"activity_type_id": activity_type_id, "role_id": roles[role_key].id},
            )
            n_assoc += 1
    counts["activity_role_association"] = n_assoc

    templates = {
        t.name: t
        for t in session.query(NotificationTemplate).all()
    }

    activities = {}
    n_notifiers = 0
    for (key, atype, entity_type, entity_id, actor, stay_ref, hours_ago,
         payload, recipients) in ACTIVITIES:
        moment = DEMO_NOW - hours(hours_ago)
        activity = upsert(
            session,
            Activity,
            {
                "activity_type_id": atype,
                "entity_type_id": entity_type,
                "entity_id": entity_id,
            },
            facility_id=facility.id,
            actor_id=users[actor].id,
            stay_id=stays[stay_ref].id if stay_ref else None,
            data_version=1,
            data=payload,
            created_on=moment,
            updated_on=moment,
        )
        activities[key] = activity
        for user_key, status in recipients:
            upsert(
                session,
                ActivityNotifier,
                {"activity_id": activity.id, "app_user_id": users[user_key].id},
                status=status,
                user_type="1",
                notification_type=1,
            )
            n_notifiers += 1
    counts["activity"] = len(activities)
    counts["activity_notifier"] = n_notifiers

    n_receivers = n_results = 0
    for key, activity_key, template_name, channel, status, recipients in DISPATCH:
        activity = activities[activity_key]
        template = templates[template_name]
        notification = upsert(
            session,
            Notification,
            {"reference_id": activity.id, "template_id": template.id},
            # `notifications.created_by` is a SERVICE NAME string in IKANOS,
            # not a user foreign key.
            created_by="notification-engine",
            status=status,
            params={"activity": activity_key, "seeded": True},
        )
        for user_key, delivery_status in recipients:
            user = users[user_key]
            receiver = upsert(
                session,
                NotificationReceiver,
                {"notification_id": notification.id, "name": f"{user.first_name} {user.last_name}"},
                app_user_id=user.id,
                email=user.email,
                phone=user.phone_number,
                device_token=f"demo-fcm-{user_key}",
                data={"activity": activity_key},
            )
            n_receivers += 1
            upsert(
                session,
                NotificationResult,
                {"receiver_id": receiver.id, "type": channel},
                status=delivery_status,
                log={"provider": "demo", "status": delivery_status},
                body=f"Demo {channel} body for {activity_key}",
            )
            n_results += 1
    counts["notification"] = len(DISPATCH)
    counts["notification_receiver"] = n_receivers
    counts["notification_result"] = n_results

    # Close the loop: record which dispatch rows each activity produced.
    for key, activity_key, *_rest in DISPATCH:
        activity = activities[activity_key]
        produced = [
            str(n.id)
            for n in session.query(Notification)
            .filter(Notification.reference_id == activity.id)
            .all()
        ]
        activity.activity_response_ids = ",".join(produced)
    session.flush()

    return counts
