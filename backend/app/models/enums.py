"""PostgreSQL ENUM types, transcribed verbatim from the IKANOS DDL.

Source of truth: FINAL_HMS_DATABASE_BLUEPRINT.md, which was itself built by
reading the 108 `CREATE TABLE` blocks in `Dump20230928 (1).sql`.

Rules enforced here (blueprint §2.7):
  * literals are byte-for-byte what the dump stores -- including spaces
    (`checkout accepted`, `push notification`, `Date Time`, `job order`,
    `smart room`) and mixed case (`Active`, `Queued`, `DeviceData`, `HUB`);
  * capitalisation is never normalised;
  * no value is invented, and no value is dropped;
  * all 13 Phase 1 enums are gone -- zero of them matched IKANOS.

Every type is built with ``create_type=False``. Type creation and dropping is
performed explicitly and exactly once by the Alembic migration, which keeps a
type shared by several tables (``device_health_status``, ``request_source``,
``notification_channel``) from being emitted more than once.
"""

from sqlalchemy.dialects.postgresql import ENUM


def _enum(name: str, *values: str) -> ENUM:
    """Declare a native PG enum whose lifecycle the migration owns."""
    return ENUM(*values, name=name, create_type=False)


# --- Rooms and packages ----------------------------------------------------
# amenity_types.amenity_category
amenity_category = _enum("amenity_category", "room", "restaurant", "others")

# --- Stays -----------------------------------------------------------------
# stays.status
stay_status = _enum(
    "stay_status",
    "pending",
    "active",
    "checkout accepted",
    "checkout pending",
    "checkout rejected",
    "checked out",
    "cancelled",
)
# stays.document_approval_status -- 2 values
document_approval_status = _enum("document_approval_status", "pending", "approved")
# user_documents.document_approval_status -- 3 values, a DIFFERENT type [FACT]
user_document_approval_status = _enum(
    "user_document_approval_status", "approved", "rejected", "pending"
)
# stays.request_source and service_requests.request_source share one type
request_source = _enum("request_source", "ikanos", "porta")

# --- Bulk import -----------------------------------------------------------
import_entity_type = _enum("import_entity_type", "booking", "job order")
import_status = _enum("import_status", "queued", "success", "error", "processing")

# --- People and RBAC -------------------------------------------------------
gender = _enum("gender", "male", "female", "other")
marital_status = _enum("marital_status", "married", "unmarried", "divorced", "other")
# roles.role_type -- 5 values incl. `system_user`, which the UI hides
role_type = _enum("role_type", "admin", "system_user", "manager", "guest", "staff")
# departments.department_key / functions.function_key -- single-valued [FACT]
department_key = _enum("department_key", "admin")
function_key = _enum("function_key", "admin")

# --- Services --------------------------------------------------------------
# room_service_requests.service_request_status -- separate from service_statuses
room_service_request_status = _enum(
    "room_service_request_status", "unassigned", "assigned", "cancelled", "completed"
)

# --- Maintenance -----------------------------------------------------------
maintenance_request_type = _enum(
    "maintenance_request_type", "scheduled", "planned", "disinfection"
)
recurrence_type = _enum("recurrence_type", "weekly")

# --- Devices ---------------------------------------------------------------
device_short_code = _enum("device_short_code", "HUB", "KLE", "MIK", "AIR")
# devices.health_status and device_health_stats.device_health_status
device_health_status = _enum("device_health_status", "Active", "Inactive")
device_config_status = _enum(
    "device_config_status",
    "configured",
    "bad_configuration",
    "commissioned",
    "decommissioned",
    "under_maintenance",
    "missing",
)
firmware_status = _enum("firmware_status", "active", "decommissioned")
param_data_type = _enum("param_data_type", "Integer", "Double", "String", "Date Time")
command_processing_status = _enum(
    "command_processing_status", "Queued", "Processing", "Processed", "Error"
)
mqtt_topic_type = _enum(
    "mqtt_topic_type",
    "DeviceData",
    "DeviceAlert",
    "DeviceHealth",
    "LastWill",
    "ServerBroadCast",
    "ServerToHub",
    "DeviceToIkanos",
    "IkanosToDevice",
)

# --- Job orders ------------------------------------------------------------
job_order_type_of_work = _enum(
    "job_order_type_of_work", "installation", "replacement", "troubleshoot"
)
job_order_status = _enum("job_order_status", "pending", "completed")

# --- Locks -----------------------------------------------------------------
lock_event = _enum("lock_event", "locked", "unlocked")
lock_unlock_mode = _enum("lock_unlock_mode", "app", "keypad")

# --- Alerts ----------------------------------------------------------------
# device_alerts.alert_severity -- only two values; `Info` does not exist
alert_severity = _enum("alert_severity", "warning", "critical")

# --- Activity feed ---------------------------------------------------------
# IKANOS stores these as enum('0','1','2') -- string enums of digits [FACT].
# 0 unread / 1 read / 2 clear. `user_type` label meanings are undocumented.
activity_notifier_status = _enum("activity_notifier_status", "0", "1", "2")
activity_notifier_user_type = _enum("activity_notifier_user_type", "0", "1", "2")

# --- Notification dispatch -------------------------------------------------
notification_status = _enum(
    "notification_status", "pending", "processing", "processed", "error"
)
# templates.type and notification_results.type share one type
notification_channel = _enum(
    "notification_channel", "email", "sms", "push notification", "silent notification"
)

# --- Scheduler -------------------------------------------------------------
scheduler_job_status = _enum("scheduler_job_status", "active", "inactive")
scheduler_execution_status = _enum("scheduler_execution_status", "passed", "failed")

# --- Reporting -------------------------------------------------------------
daily_metric_type = _enum(
    "daily_metric_type",
    "smart room",
    "service request",
    "checkout",
    "booking",
    "guest room",
)


#: Every enum type, in creation order. The migration iterates this list so a
#: type is created and dropped exactly once regardless of how many tables use
#: it. Adding an enum above without adding it here will fail the schema test.
ALL_ENUMS: tuple[ENUM, ...] = (
    amenity_category,
    stay_status,
    document_approval_status,
    user_document_approval_status,
    request_source,
    import_entity_type,
    import_status,
    gender,
    marital_status,
    role_type,
    department_key,
    function_key,
    room_service_request_status,
    maintenance_request_type,
    recurrence_type,
    device_short_code,
    device_health_status,
    device_config_status,
    firmware_status,
    param_data_type,
    command_processing_status,
    mqtt_topic_type,
    job_order_type_of_work,
    job_order_status,
    lock_event,
    lock_unlock_mode,
    alert_severity,
    activity_notifier_status,
    activity_notifier_user_type,
    notification_status,
    notification_channel,
    scheduler_job_status,
    scheduler_execution_status,
    daily_metric_type,
)
