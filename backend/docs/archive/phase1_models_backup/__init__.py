"""HMS ORM models — import surface for Alembic autogenerate.

Importing this package registers every table on `Base.metadata`.
"""

from app.db.base import Base
from app.models.alert import (
    AlertType,
    CurrentIncidentStatus,
    DeviceIncident,
    LimitConfig,
    ValueAlert,
)
from app.models.core import (
    Amenity,
    AmenityType,
    AppUser,
    AppUserUserRole,
    Booking,
    Department,
    Employee,
    Event,
    Facility,
    FoodCategory,
    FoodMenu,
    Holiday,
    Invoice,
    JobFunction,
    Occupant,
    Offer,
    Package,
    PropertyType,
    ServiceRequest,
    Stay,
    UserRole,
)
from app.models.device import Device, Firmware, JobOrder, JobOrderDevice
from app.models.notification import FcmToken, Notification
from app.models.schedule import MaintenanceSchedule, ScheduledTask
from app.models.sensor import (
    DeviceHealthLog,
    DeviceUptime,
    EnergyAggregate,
    EnergyData,
    SensorReading,
)

__all__ = [
    "Base",
    # core
    "Facility",
    "UserRole",
    "AppUser",
    "AppUserUserRole",
    "PropertyType",
    "AmenityType",
    "Package",
    "Amenity",
    "Department",
    "JobFunction",
    "Employee",
    "Booking",
    "Occupant",
    "Stay",
    "Invoice",
    "ServiceRequest",
    "FoodCategory",
    "FoodMenu",
    "Event",
    "Offer",
    "Holiday",
    # device
    "Device",
    "Firmware",
    "JobOrder",
    "JobOrderDevice",
    # alert
    "DeviceIncident",
    "ValueAlert",
    "LimitConfig",
    "AlertType",
    "CurrentIncidentStatus",
    # notification
    "Notification",
    "FcmToken",
    # schedule
    "MaintenanceSchedule",
    "ScheduledTask",
    # sensor / health
    "EnergyData",
    "SensorReading",
    "EnergyAggregate",
    "DeviceHealthLog",
    "DeviceUptime",
]
