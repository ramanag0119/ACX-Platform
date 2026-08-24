"""Enumerations transcribed verbatim from the IKANOS documentation.

Every member below is quoted from a specific documented source. Values are
NOT invented. Where the documentation states an enum but does not enumerate
its members, no Python enum is defined and the column is left as text with a
NEEDS_REVIEW note on the model.

Sources (under d:\\Inspornics\\HMS_ikanos\\Ikanos_code):
  FM  = 1_FACILITI_MANAGER_DOCUMENTATION.md
  DM  = 2_DEVICE_MANAGER_DOCUMENTATION.md
  AM  = 4_ALARM_MANAGER_DOCUMENTATION.md
  NE  = 5_NOTIFICATION_ENGINE_DOCUMENTATION.md
  SH  = 7_SCHEDULE_HANDLER_DOCUMENTATION.md
  SDP = 8_SENSOR_DATA_PROCESSOR_DOCUMENTATION.md
  HM  = 9_HEALTH_MONITOR_DOCUMENTATION.md
"""

import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str | None = None) -> SAEnum:
    """Build a PostgreSQL ENUM that stores the documented *values*.

    SQLAlchemy defaults to persisting Python member *names*, which would write
    `CRITICAL` / `FIVE_MIN` / `IN_PROGRESS` into the database. IKANOS documents
    the literals as `Critical` / `5min` / `InProgress`, so `values_callable`
    is used to keep stored data faithful to the documentation.
    """
    return SAEnum(
        enum_cls,
        name=name or _snake(enum_cls.__name__),
        values_callable=lambda members: [m.value for m in members],
        native_enum=True,
        create_constraint=False,
        validate_strings=True,
    )


def _snake(camel: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(camel):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


class RoleType(str, enum.Enum):
    """FM §4 login response: roleType: "ADMIN"|"STAFF"|"MANAGER"|"GUEST"."""

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"
    GUEST = "GUEST"


class DeviceType(str, enum.Enum):
    """DM §10 `device.type`: HUB, LOCK, SENSOR, SWITCH, CONTROLLER, MIKOS."""

    HUB = "HUB"
    LOCK = "LOCK"
    SENSOR = "SENSOR"
    SWITCH = "SWITCH"
    CONTROLLER = "CONTROLLER"
    MIKOS = "MIKOS"


class DeviceConfigStatus(str, enum.Enum):
    """DM §10 `device.deviceConfigStatus`: active, inactive, decommissioned."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DECOMMISSIONED = "decommissioned"


class DeviceStatus(str, enum.Enum):
    """DM §10 `device.status` and HM §10 `deviceHealthLog.status`."""

    ONLINE = "Online"
    OFFLINE = "Offline"
    ERROR = "Error"


class JobOrderType(str, enum.Enum):
    """DM §10 `jobOrder.jobType`: Commission, Decommission, Maintenance."""

    COMMISSION = "Commission"
    DECOMMISSION = "Decommission"
    MAINTENANCE = "Maintenance"


class JobOrderStatus(str, enum.Enum):
    """DM §10 `jobOrder.status`: Created, InProgress, Completed."""

    CREATED = "Created"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class IncidentStatus(str, enum.Enum):
    """AM §11 `deviceIncident.status`: Open, Unread, Read, Assigned, Resolved."""

    OPEN = "Open"
    UNREAD = "Unread"
    READ = "Read"
    ASSIGNED = "Assigned"
    RESOLVED = "Resolved"


class AlertSeverity(str, enum.Enum):
    """AM §11 `deviceIncident.severity`: Critical, Warning, Info."""

    CRITICAL = "Critical"
    WARNING = "Warning"
    INFO = "Info"


class LimitType(str, enum.Enum):
    """AM §11 `valueAlerts.limitType`: "high" or "low"."""

    HIGH = "high"
    LOW = "low"


class NotificationType(str, enum.Enum):
    """NE §8 `notification.type`: alert, service, booking, system, event."""

    ALERT = "alert"
    SERVICE = "service"
    BOOKING = "booking"
    SYSTEM = "system"
    EVENT = "event"


class ScheduledTaskType(str, enum.Enum):
    """SH §10 `scheduledTask.type`.

    maintenance, housekeeping, sanitation, checkout, system
    """

    MAINTENANCE = "maintenance"
    HOUSEKEEPING = "housekeeping"
    SANITATION = "sanitation"
    CHECKOUT = "checkout"
    SYSTEM = "system"


class ScheduledTaskStatus(str, enum.Enum):
    """SH §10 `scheduledTask.status`: Pending, Executed, Cancelled, Failed."""

    PENDING = "Pending"
    EXECUTED = "Executed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"


class AggregateInterval(str, enum.Enum):
    """SDP §9 `energyAggregate.interval`: 5min, hourly, daily."""

    FIVE_MIN = "5min"
    HOURLY = "hourly"
    DAILY = "daily"


class WeekDay(str, enum.Enum):
    """SH §10 `maintenanceSchedule.days`: Days of week (MON-SUN)."""

    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"
