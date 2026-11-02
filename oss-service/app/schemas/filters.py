"""Literal types for the PostgreSQL enum labels used as query filters.

Copied from the HMS backend (`backend/app/schemas/filters.py`). Only the
device/OSS-relevant labels are needed here, but the file is kept whole so it
stays a verbatim mirror of the HMS contract.
"""

from __future__ import annotations

from typing import Literal

DeviceHealthStatus = Literal["Active", "Inactive"]

DeviceConfigStatus = Literal[
    "configured",
    "bad_configuration",
    "commissioned",
    "decommissioned",
    "under_maintenance",
    "missing",
]

FirmwareStatus = Literal["active", "decommissioned"]

AlertSeverity = Literal["warning", "critical"]

AmenityCategory = Literal["room", "restaurant", "others"]

StayStatus = Literal[
    "pending",
    "active",
    "checkout accepted",
    "checkout pending",
    "checkout rejected",
    "checked out",
    "cancelled",
]

DocumentApprovalStatus = Literal["pending", "approved"]

RequestSource = Literal["ikanos", "porta"]

NotificationStatus = Literal["pending", "processing", "processed", "error"]

NotificationChannel = Literal[
    "email", "sms", "push notification", "silent notification"
]

DailyMetricType = Literal[
    "smart room", "service request", "checkout", "booking", "guest room"
]

ParamDataType = Literal["Integer", "Double", "String", "Date Time"]

RoleType = Literal["admin", "system_user", "manager", "guest", "staff"]
