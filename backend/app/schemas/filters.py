"""Literal types for the PostgreSQL enum labels used as query filters.

WHY THIS EXISTS. A filter declared `str | None` is passed through to the query
untouched, so an unknown value reaches PostgreSQL and fails on the enum cast.
SQLAlchemy raises `DataError`, which the shared handler could only read as "the
database refused this", and it answered 503 -- telling the client the backend
was down when in fact the request was simply wrong, and inviting a retry that
can never succeed.

Declared as Literal, FastAPI rejects the value before any query runs: 422, with
the permitted labels named in the response and in the OpenAPI document, which
is also what lets the frontend build its filter controls from the contract
rather than from a hand-copied list.

EVERY LABEL BELOW IS COPIED FROM THE DATABASE, not chosen. They are the
`pg_enum` labels of the corresponding type, in `enumsortorder`. Nothing is
added: notably there is no "Open" or "Info" state anywhere, because no enum has
one. Adding a label here without adding it to the enum would put a value in the
contract that the column cannot hold.
"""

from __future__ import annotations

from typing import Literal

#: device_health_status -- the device's own health flag. TWO values; there is
#: no warning or error state on a device.
DeviceHealthStatus = Literal["Active", "Inactive"]

#: device_config_status
DeviceConfigStatus = Literal[
    "configured",
    "bad_configuration",
    "commissioned",
    "decommissioned",
    "under_maintenance",
    "missing",
]

#: firmware_status
FirmwareStatus = Literal["active", "decommissioned"]

#: alert_severity -- carried by an ALERT. Incident lifecycle status is a
#: separate lookup table (`incident_status`) and an integer id.
AlertSeverity = Literal["warning", "critical"]

#: amenity_category
AmenityCategory = Literal["room", "restaurant", "others"]

#: stay_status
StayStatus = Literal[
    "pending",
    "active",
    "checkout accepted",
    "checkout pending",
    "checkout rejected",
    "checked out",
    "cancelled",
]

#: document_approval_status (on `stay`)
DocumentApprovalStatus = Literal["pending", "approved"]

#: request_source -- shared by `stay` and `service_request`.
RequestSource = Literal["ikanos", "porta"]

#: notification_status
NotificationStatus = Literal["pending", "processing", "processed", "error"]

#: notification_channel -- the template's delivery channel.
NotificationChannel = Literal[
    "email", "sms", "push notification", "silent notification"
]

#: daily_metric_type -- the KPI rows behind the dashboard rings.
DailyMetricType = Literal[
    "smart room", "service request", "checkout", "booking", "guest room"
]

#: param_data_type -- how a `device_stat.device_param_value` should be read.
ParamDataType = Literal["Integer", "Double", "String", "Date Time"]

#: role_type
RoleType = Literal["admin", "system_user", "manager", "guest", "staff"]
