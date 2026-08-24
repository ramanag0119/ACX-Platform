"""Response models for the notification dispatch queue and the activity feed.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

IKANOS runs TWO separate notification systems, and neither is a rename of the
other. Both are exposed, because collapsing them would misrepresent the design:

  (a) IN-APP FEED       activity -> activity_notifier
      Per-user read state lives on `activity_notifier.status`, an
      enum('0','1','2') meaning unread / read / clear. This is the header bell.

  (b) DISPATCH QUEUE    notification -> notification_receiver
                                     -> notification_result
      `notification.status` is a DIFFERENT enum -- pending / processing /
      processed / error -- describing delivery, not readership.
      `notification.template_id` -> `notification_template`.

THERE IS NO FOREIGN KEY FROM A NOTIFICATION TO AN ALERT OR INCIDENT.
`notification.reference_id` is a bare BIGINT with no constraint. In the seeded
data it holds an `activity.id`, but the schema neither declares nor enforces
that, so it is returned as a raw integer and labelled as unresolved.

=== FIELDS DELIBERATELY WITHHELD (security) ===

The seeded template registry includes `OTPTemplate`
(sms/user-verification-otp), `KeySMSTemplate` (amenity keypad key),
`MaintenanceKeypadKey`, `KeyNotificationTemplate` and `MaintenanceAppKey`.
In a real install the rendered message and its merge data therefore contain
one-time passwords and door keypad codes. These are NEVER exposed:

    notification.params              template merge data -> would hold the OTP/key
    notification_result.body         the RENDERED message -> same
    notification_result.log          provider response, may carry tokens
    notification_receiver.data       unbounded per-recipient bag
    notification_receiver.device_token   a push credential
    notification_receiver.email/phone    reachable via /users under its own grant
    activity.data                    unbounded activity payload
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserRef


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# notification_template
# ---------------------------------------------------------------------------


class NotificationTemplateRead(ORMModel):
    """A row of `notification_template` (IKANOS `templates`).

    A template is linked ONLY to a channel (`type`) and a file `path`. It has
    no foreign key to alert type, occasion, event or recipient -- so no such
    relationship is exposed.
    """

    id: uuid.UUID
    name: str = Field(examples=["CheckoutInitiationTemplate"])
    type: str = Field(
        examples=["push notification"],
        description="email | sms | push notification | silent notification",
    )
    path: str = Field(examples=["notification/checkout-initiation.txt.hbs"])
    created_on: datetime
    updated_on: datetime


class NotificationTemplateDetail(NotificationTemplateRead):
    notification_count: int = Field(description="Notifications using this template")


# ---------------------------------------------------------------------------
# dispatch queue
# ---------------------------------------------------------------------------


class NotificationResultRead(ORMModel):
    """A row of `notification_result` -- one delivery attempt per channel.

    `body` and `log` are withheld: `body` is the rendered message, which for
    the OTP and keypad-key templates would contain the secret itself.
    """

    id: int
    type: str = Field(examples=["sms"], description="The channel actually used")
    status: str = Field(examples=["sent"], description="Provider status string")
    created_on: datetime


class NotificationReceiverRead(ORMModel):
    """A row of `notification_receiver`.

    Contact columns (`email`, `phone`, `device_token`) and the `data` bag are
    withheld. `app_user_id` is returned instead, so contact details remain
    reachable through /users under the `employees` grant rather than leaking
    here.
    """

    id: int
    app_user_id: uuid.UUID | None = None
    name: str = Field(examples=["Vikram Rao"])
    results: list[NotificationResultRead]


class NotificationRead(ORMModel):
    """A row of `notification` -- one queued outbound message."""

    id: int = Field(examples=[1], description="BIGINT identity, not a UUID")
    status: str = Field(
        examples=["processed"],
        description="pending | processing | processed | error -- DELIVERY state, "
                    "not read/unread",
    )
    created_by: str = Field(
        examples=["notification-engine"],
        description="A SERVICE NAME string in IKANOS, not a user foreign key",
    )
    template_id: uuid.UUID | None = None
    template_name: str | None = Field(default=None, examples=["AlertSMSTemplate"])
    template_type: str | None = Field(default=None, examples=["sms"])
    reference_id: int | None = Field(
        default=None,
        description=(
            "Bare BIGINT with NO foreign key. Holds an activity.id in the "
            "seeded data, but the schema does not declare or enforce that."
        ),
    )
    receiver_count: int
    created_on: datetime
    updated_on: datetime


class NotificationDetail(NotificationRead):
    receivers: list[NotificationReceiverRead]


# ---------------------------------------------------------------------------
# in-app activity feed
# ---------------------------------------------------------------------------


class ActivityNotifierRead(ORMModel):
    """A row of `activity_notifier` -- one user's read state for one activity."""

    app_user_id: uuid.UUID
    user_name: str | None = None
    status: str = Field(
        examples=["0"],
        description="enum('0','1','2') stored as digit strings: unread / read / clear",
    )
    status_label: str = Field(examples=["unread"], description="Derived from `status`")
    user_type: str | None = Field(
        default=None, description="Selects the message template; labels undocumented"
    )
    notification_type: int | None = None


class ActivityRead(ORMModel):
    """A row of `activity` -- one business event worth telling someone about.

    `entity_id` is polymorphic and carries NO foreign key: it points at a
    booking, a room or a ticket depending on `entity_type_id`. `data` is
    withheld as an unbounded payload.
    """

    id: int = Field(description="BIGINT identity")
    activity_type_id: int
    activity_type_name: str | None = Field(
        default=None, examples=["service-request-creation"]
    )
    entity_type_id: int
    entity_type_name: str | None = Field(default=None, examples=["Service Requests"])
    entity_id: int = Field(description="Polymorphic; no foreign key exists")
    facility_id: uuid.UUID
    actor: UserRef | None = Field(default=None, description="Who caused the event")
    stay_id: uuid.UUID | None = None
    data_version: int
    activity_response_ids: str | None = Field(
        default=None,
        description="Comma-separated dispatch notification ids, as IKANOS stores it",
    )
    notifier_count: int
    unread_count: int = Field(description="activity_notifier rows with status '0'")
    created_on: datetime
    updated_on: datetime


class ActivityDetail(ActivityRead):
    notifiers: list[ActivityNotifierRead]
