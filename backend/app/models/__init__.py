"""The approved 93-table HMS schema.

Source of truth: ``backend/docs/FINAL_HMS_DATABASE_BLUEPRINT.md``.

Importing this package registers all 93 tables on ``Base.metadata``, which is
what ``migrations/env.py`` hands to Alembic as ``target_metadata``.

Module layout follows the blueprint's own grouping (§12.1):

    facility.py     A  organisation, facility, property hierarchy    8
    amenity.py      B  rooms, amenities, packages                    9
    stay.py         C  guests, stays, billing                        7
    people.py       D  people, authentication, RBAC                  9
    service.py      E  services, tickets, catalogue                  8
    maintenance.py  F  maintenance / Services Planning               4
    device.py       G  devices, telemetry, IoT                      15
    job_order.py    H  job orders                                    3
    access.py       I  access control and digital keys               4
    alert.py        J  alerts, incidents, value limits               8
    activity.py     K  activity feed and notification dispatch       9
    scheduler.py    L  scheduler                                     2
    marketing.py    M  marketing, events, occasions                  5
    reporting.py    N  energy and reporting                          2
                                                                   ---
                                                                    93
"""

from app.db.base import Base
from app.models import enums
from app.models.access import AccessKey, KeyType, LockActivityLog, UserDeviceAcl
from app.models.activity import (
    Activity,
    ActivityNotifier,
    ActivityRoleAssociation,
    ActivityType,
    EntityType,
    Notification,
    NotificationReceiver,
    NotificationResult,
    NotificationTemplate,
)
from app.models.alert import (
    AlertType,
    DeviceAlert,
    DeviceIncident,
    IncidentEvent,
    IncidentHistory,
    IncidentStatus,
    ValueAlert,
    ValueAlertLimitConfig,
)
from app.models.amenity import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    Feature,
    Package,
    PackageFeature,
    RoomStatusConditionApplicability,
    SubPackage,
)
from app.models.device import (
    BatteryLifeStat,
    CommandType,
    Device,
    DeviceCommand,
    DeviceCurrentStat,
    DeviceHealthStat,
    DeviceParam,
    DeviceStat,
    DeviceType,
    Firmware,
    MqttBroker,
    MqttTopic,
    OtherDevice,
    RoomDeviceMap,
    SensorOperationStat,
)
from app.models.facility import (
    Attachment,
    Country,
    Currency,
    Facility,
    FacilityUser,
    Organisation,
    Property,
    PropertyChain,
    PropertyType,
)
from app.models.job_order import JobOrder, JobOrderAmenity, JobOrderDevice
from app.models.maintenance import (
    MaintenanceRequest,
    MaintenanceRequestAmenity,
    MaintenanceRequestAssignee,
    MaintenanceRequestRecurrence,
)
from app.models.marketing import (
    FacilityEvent,
    Occasion,
    OccasionType,
    PromoCode,
    PromoCodeAmenity,
)
from app.models.people import (
    AppUser,
    Department,
    JobFunction,
    Role,
    RoleModule,
    RoleModulePermission,
    UserDevice,
    UserRole,
    UserToken,
)
from app.models.reporting import DailyDualDataPoint, EnergyStat
from app.models.scheduler import SchedulerJob, SchedulerJobExecution
from app.models.service import (
    RoomServiceRequest,
    RoomServiceRequestItem,
    ServiceCategory,
    ServiceCategoryItem,
    ServiceRequest,
    ServiceRequestItem,
    ServiceStatus,
    ServiceType,
)
from app.models.stay import (
    ImportJob,
    Invoice,
    RoomAllocation,
    Stay,
    StayPackage,
    StayUser,
    UserDocument,
)

#: The approved table list, verbatim from FINAL_HMS_DATABASE_BLUEPRINT.md §12.2.
#: The schema test asserts the live database matches this set exactly, so an
#: unapproved table cannot reach the database unnoticed.
APPROVED_TABLES: tuple[str, ...] = (
    # A -- organisation, facility, property hierarchy (8)
    "organisation",
    "facility",
    "facility_user",
    "property_type",
    "property",
    "property_chain",
    "attachment",
    "country",
    # B -- rooms, amenities, packages (9)
    "amenity_type",
    "amenity",
    "amenity_status",
    "amenity_condition",
    "amenity_condition_status",
    "package",
    "sub_package",
    "feature",
    "package_feature",
    # C -- guests, stays, billing (7)
    "stay",
    "stay_user",
    "stay_package",
    "room_allocation",
    "user_document",
    "invoice",
    "import_job",
    # D -- people, authentication, RBAC (9)
    "app_user",
    "user_token",
    "user_device",
    "role",
    "user_role",
    "role_module",
    "role_module_permission",
    "department",
    "job_function",
    # E -- services, tickets, catalogue (8)
    "service_type",
    "service_status",
    "service_category",
    "service_category_item",
    "service_request",
    "service_request_item",
    "room_service_request",
    "room_service_request_item",
    # F -- maintenance / Services Planning (4)
    "maintenance_request",
    "maintenance_request_recurrence",
    "maintenance_request_amenity",
    "maintenance_request_assignee",
    # G -- devices, telemetry, IoT (15)
    "device_type",
    "device",
    "firmware",
    "device_param",
    "device_stat",
    "device_current_stat",
    "device_health_stat",
    "device_command",
    "command_type",
    "mqtt_broker",
    "mqtt_topic",
    "other_device",
    "battery_life_stat",
    "sensor_operation_stat",
    "room_device_map",
    # Added after the blueprint's 92, by approved migration:
    #   room_status_condition_applicability (c7a1b2d3e4f5) -- the room-status
    #     x condition policy the occupancy screen and every stay-lifecycle
    #     write read through `_has_blocking_condition`.
    #   currency (d8e4f1a6b207) -- ISO 4217 master, joined by stay, service
    #     and catalogue reads.
    # Both were declared by the models long before MySQL had them; listing
    # them here is what lets `test_no_unapproved_table_exists` stay a real
    # guard instead of a permanent failure.
    "room_status_condition_applicability",
    "currency",
    # H -- job orders (3)
    "job_order",
    "job_order_device",
    "job_order_amenity",
    # I -- access control and digital keys (4)
    "key_type",
    "access_key",
    "user_device_acl",
    "lock_activity_log",
    # J -- alerts, incidents, value limits (8)
    "alert_type",
    "device_alert",
    "device_incident",
    "incident_status",
    "incident_event",
    "incident_history",
    "value_alert",
    "value_alert_limit_config",
    # K -- activity feed and notification dispatch (9)
    "entity_type",
    "activity_type",
    "activity",
    "activity_notifier",
    "activity_role_association",
    "notification",
    "notification_template",
    "notification_receiver",
    "notification_result",
    # L -- scheduler (2)
    "scheduler_job",
    "scheduler_job_execution",
    # M -- marketing, events, occasions (5)
    "promo_code",
    "promo_code_amenity",
    "facility_event",
    "occasion_type",
    "occasion",
    # N -- energy and reporting (2)
    "energy_stat",
    "daily_dual_data_point",
)

#: Tables whose primary key is a seeded IKANOS integer id (blueprint §2.3 T1).
LOOKUP_TABLES: frozenset[str] = frozenset(
    {
        "country",
        "amenity_status",
        "amenity_condition",
        "service_type",
        "service_status",
        "role_module",
        "device_type",
        "device_param",
        "command_type",
        "key_type",
        "alert_type",
        "incident_status",
        "incident_event",
        "entity_type",
        "activity_type",
        "occasion_type",
        # `Currency` is declared `SmallIntLookupPk` -- a seeded SMALLINT id,
        # autoincrement=False, exactly like every entry above. Listing it here
        # is what the model already says; leaving it out would class it as a
        # T2 entity and assert a UUID primary key it does not have.
        "currency",
    }
)

#: Configuration tables HMS created itself, with a documented exemption from
#: the blueprint's §2.3 primary-key policy and its `legacy_id` rule.
#:
#: Both rules exist to carry IKANOS forward: a UUID primary key replaces the
#: IKANOS integer surrogate, and `legacy_id` preserves the original so the two
#: systems can still be reconciled. A table that never existed in IKANOS has
#: no original integer to preserve and nothing to reconcile against, so
#: applying either rule would add a column and a key format that mean nothing.
#:
#: `room_status_condition_applicability` (migration c7a1b2d3e4f5) is policy
#: data: 42 rows seeded by the migration itself, keyed by
#: (room_status, condition_id) through `uq_room_status_condition`. Its `id` is
#: an INT AUTO_INCREMENT surrogate that nothing references -- confirmed: the
#: table has ZERO inbound foreign keys -- so a UUID would buy no stability.
#:
#: This set is deliberately narrow. A table belongs here only if HMS created
#: it AND nothing foreign-keys to its surrogate id; anything else still owes
#: the blueprint a UUID and a legacy_id.
CONFIG_TABLES: frozenset[str] = frozenset(
    {
        "room_status_condition_applicability",
    }
)

#: Append-only high-volume tables using BIGINT IDENTITY (blueprint §2.3 T3).
HIGH_VOLUME_TABLES: frozenset[str] = frozenset(
    {
        "device_stat",
        "device_health_stat",
        "device_alert",
        "incident_history",
        "lock_activity_log",
        "activity",
        "notification",
        "notification_receiver",
        "notification_result",
        "scheduler_job_execution",
        "other_device",
        "battery_life_stat",
    }
)

#: Tables with a composite natural primary key, carried over from IKANOS.
COMPOSITE_PK_TABLES: frozenset[str] = frozenset(
    {
        "facility_user",
        "amenity_condition_status",
        "sub_package",
        "user_role",
        "role_module_permission",
        "maintenance_request_recurrence",
        "sensor_operation_stat",
        "job_order_device",
        "job_order_amenity",
        "activity_notifier",
        "activity_role_association",
        "promo_code_amenity",
        "energy_stat",
        "daily_dual_data_point",
    }
)

__all__ = [
    "Base",
    "enums",
    "APPROVED_TABLES",
    "LOOKUP_TABLES",
    "CONFIG_TABLES",
    "HIGH_VOLUME_TABLES",
    "COMPOSITE_PK_TABLES",
    # A
    "Organisation",
    "Facility",
    "FacilityUser",
    "PropertyType",
    "Property",
    "PropertyChain",
    "Attachment",
    "Country",
    "Currency",
    # B
    "AmenityType",
    "Amenity",
    "AmenityStatus",
    "AmenityCondition",
    "AmenityConditionStatus",
    "Package",
    "SubPackage",
    "Feature",
    "PackageFeature",
    "RoomStatusConditionApplicability",

    # C
    "Stay",
    "StayUser",
    "StayPackage",
    "RoomAllocation",
    "UserDocument",
    "Invoice",
    "ImportJob",
    # D
    "AppUser",
    "UserToken",
    "UserDevice",
    "Role",
    "UserRole",
    "RoleModule",
    "RoleModulePermission",
    "Department",
    "JobFunction",
    # E
    "ServiceType",
    "ServiceStatus",
    "ServiceCategory",
    "ServiceCategoryItem",
    "ServiceRequest",
    "ServiceRequestItem",
    "RoomServiceRequest",
    "RoomServiceRequestItem",
    # F
    "MaintenanceRequest",
    "MaintenanceRequestRecurrence",
    "MaintenanceRequestAmenity",
    "MaintenanceRequestAssignee",
    # G
    "DeviceType",
    "Device",
    "Firmware",
    "DeviceParam",
    "DeviceStat",
    "DeviceCurrentStat",
    "DeviceHealthStat",
    "DeviceCommand",
    "CommandType",
    "MqttBroker",
    "MqttTopic",
    "OtherDevice",
    "RoomDeviceMap",
    "BatteryLifeStat",
    "SensorOperationStat",
    # H
    "JobOrder",
    "JobOrderDevice",
    "JobOrderAmenity",
    # I
    "KeyType",
    "AccessKey",
    "UserDeviceAcl",
    "LockActivityLog",
    # J
    "AlertType",
    "DeviceAlert",
    "DeviceIncident",
    "IncidentStatus",
    "IncidentEvent",
    "IncidentHistory",
    "ValueAlert",
    "ValueAlertLimitConfig",
    # K
    "EntityType",
    "ActivityType",
    "Activity",
    "ActivityNotifier",
    "ActivityRoleAssociation",
    "Notification",
    "NotificationTemplate",
    "NotificationReceiver",
    "NotificationResult",
    # L
    "SchedulerJob",
    "SchedulerJobExecution",
    # M
    "PromoCode",
    "PromoCodeAmenity",
    "FacilityEvent",
    "OccasionType",
    "Occasion",
    # N
    "EnergyStat",
    "DailyDualDataPoint",
]
