"""Reference / lookup rows, read verbatim from the IKANOS SQL dump.

Every tuple below was extracted from an `INSERT INTO` statement in
`Dump20230928 (1).sql`. Ids are the real IKANOS ids, preserved because the
blueprint's T1 primary-key tier depends on them (§2.3) and because the HMS
frontend renders these values directly.

Nothing here is invented. If a value is not in the dump, it is not in this file.
"""

# device_types (4) -- (id, name, device_short_code)
DEVICE_TYPES = [
    (1, "Intellihub", "HUB"),
    (2, "AirQ", "AIR"),
    (3, "Mikos", "MIK"),
    (4, "Kleio", "KLE"),
]

# service_types (7) -- these ARE the 7 Services Tracking tabs
SERVICE_TYPES = [
    (1, "Room Service"),
    (2, "Travel Desk"),
    (3, "Business Center"),
    (4, "Food Order"),
    (5, "Facility Maintenance Service"),
    (6, "Health & Fitness"),
    (7, "Sanitation Maintenance Service"),
]

# service_statuses (5)
SERVICE_STATUSES = [
    (1, "Pending"),
    (2, "Assigned"),
    (3, "Partially completed"),
    (4, "Completed"),
    (5, "Canceled"),
]

# alert_types (16) -- (id, name) only; severity lives on device_alert
ALERT_TYPES = [
    (1, "BatteryLow"),
    (2, "DeviceDisconnection"),
    (3, "LoginAttemptsFailure"),
    (4, "ImproperShaftMovement"),
    (5, "DeviceOverheating"),
    (6, "PreventiveMaintenance"),
    (7, "MikosOvercurrentTrip"),
    (8, "RoomAirQualityPoor"),
    (9, "RoomInternalHot"),
    (10, "AirConditioningFail"),
    (11, "TamperingAttempt"),
    (12, "DoorAjar"),
    (13, "HubOffline"),
    (14, "MikosOffline"),
    (15, "LockOffline"),
    (16, "AirqOffline"),
]

# amenity_statuses (4) -- note id 0 is a real, meaningful id
AMENITY_STATUSES = [
    (0, "Available"),
    (1, "Occupied"),
    (2, "Unavailable"),
    (3, "Allotted"),
]

# amenity_conditions (4)
AMENITY_CONDITIONS = [
    (1, "Dirty"),
    (2, "Low battery"),
    (3, "Under maintenance"),
    (4, "Sanitation"),
]

# incident_statuses (4) -- `Open` is NOT one of them
INCIDENT_STATUSES = [
    (1, "Unread"),
    (2, "Read"),
    (3, "Assigned"),
    (4, "Resolved"),
]

# incident_events (5) -- `Reopened` exists only as an event, never as a status
INCIDENT_EVENTS = [
    (1, "Unread"),
    (2, "Read"),
    (3, "Assigned"),
    (4, "Resolved"),
    (5, "Reopened"),
]

# key_types (4)
KEY_TYPES = [
    (1, "Primary"),
    (2, "Shared"),
    (3, "Staff"),
    (4, "Default"),
]

# entity_types (5) -- the real notification-type axis
ENTITY_TYPES = [
    (1, "Booking"),
    (2, "Occupancy"),
    (3, "Service Requests"),
    (4, "Maintenance Requests"),
    (5, "Default Key"),
]

# occasion_types (4) -- `Holiday` is a row here, not a table
OCCASION_TYPES = [
    (1, "Festival"),
    (2, "Birthday"),
    (3, "Marriage anniversary"),
    (4, "Holiday"),
]

# role_modules (18) -- (id, module_name, read_applicable, write_applicable)
# These match the HMS sidebar exactly.
ROLE_MODULES = [
    (1, "dashboard", True, False),
    (2, "occupancy", True, True),
    (3, "bookings", True, True),
    (4, "service_tracking", True, True),
    (5, "service_planning", True, True),
    (6, "facility_management", True, True),
    (7, "user_roles", True, True),
    (8, "service_setup", True, True),
    (9, "employees", True, True),
    (10, "job_order", True, True),
    (11, "offers", True, True),
    (12, "events", True, True),
    (13, "caleido_network", True, True),
    (14, "firmware_management", True, True),
    (15, "reports", True, False),
    (16, "tickets", True, True),
    (17, "holidays", True, True),
    (18, "default_key", True, True),
]

# command_types (10) -- device_type_id is NULL for all of them in the dump
COMMAND_TYPES = [
    (1, "Keys", None),
    (2, "FirmwareUpdates", None),
    (3, "Checkout", None),
    (4, "ExtendCheckOutTime", None),
    (5, "SetDNDMode", None),
    (6, "MaintenanceMode", None),
    (7, "DisplaySpecialMessages", None),
    (8, "ResolvingAlerts", None),
    (9, "DefaultKey", None),
    (10, "DeviceCommands", None),
]

# device_params (35) -- (id, device_type, param_name, data_type, unit)
# The telemetry vocabulary. `unit` is the missing Y-axis unit of gap D4.
DEVICE_PARAMS = [
    (1, 2, "room_temperature", "Double", "C/F"),
    (2, 2, "air_quality", "Double", None),
    (3, 2, "humidity", "Double", "r.h"),
    (4, 2, "pressure", "Double", "Pa"),
    (5, 3, "voltage", "Double", "V"),
    (6, 3, "current", "Double", "Amps"),
    (7, 3, "active_energy", "Double", "kWh"),
    (8, 4, "battery_percentage", "Double", None),
    (9, 4, "lock_status", "Integer", None),
    (10, 4, "temperature", "Double", "C/F"),
    (11, 1, "active_energy", "Double", "kWh"),
    (12, 1, "temperature", "Double", "C"),
    (13, 1, "relay_cutoff", "Integer", None),
    (14, 4, "lock_operations", "Integer", None),
    (15, 3, "relay_operations", "Integer", None),
    (16, 2, "relay_operations", "Integer", None),
    (17, 1, "relay_operations", "Integer", None),
    (18, 3, "active_power", "Double", "KW"),
    (19, 3, "relay_status", "Integer", None),
    (20, 3, "reactive_energy", "Double", "kvarh"),
    (21, 3, "frequency", "Integer", "Hz"),
    (22, 3, "power_factor", "Integer", None),
    (23, 3, "reactive_power", "Double", "kvar"),
    (24, 3, "apparent_power", "Double", "kVA"),
    (25, 1, "voltage", "Double", "V"),
    (26, 1, "current", "Double", "Amps"),
    (27, 1, "active_power", "Double", "KW"),
    (28, 1, "frequency", "Integer", "Hz"),
    (29, 1, "power_factor", "Integer", None),
    (30, 1, "relay_status", "Integer", None),
    (31, 1, "relay_status", "Double", "kvarh"),
    (32, 1, "relay_status", "Double", "kvar"),
    (33, 1, "relay_status", "Double", "kVA"),
    (34, 3, "temperature", "Double", "C"),
    (35, 2, "temperature", "Double", "C"),
]

# activity_types (22) -- (id, activity_type, entity_type_id, notification_type,
#                         is_subscribable)
ACTIVITY_TYPES = [
    (1, "booking-confirmation", 1, "014", True),
    (2, "keypad-access-key-generation", 1, "010", False),
    (3, "app-access-key-generation", 1, "080", False),
    (4, "bulk-upload", 1, "400", False),
    (5, "checkout-initiation", 2, "044", True),
    (6, "checkout-acception", 2, "044", True),
    (7, "checkout-confirmation", 2, "044", True),
    (8, "checkout-reminder", 2, "044", True),
    (9, "service-request-creation", 3, "044", True),
    (10, "service-request-assigned", 3, "444", True),
    (11, "service-request-status-change", 3, "444", True),
    (12, "maintenance-request-creation", 4, "044", True),
    (13, "maintenance-request-status-update", 4, "404", True),
    (14, "maintenance-request-keypad-access-key", 4, "010", False),
    (15, "maintenance-request-app-access-key", 4, "080", False),
    (16, "reallocate-room", 2, "040", False),
    (17, "checkin-confirmation", 1, "004", True),
    (18, "checkout-extend", 2, "044", True),
    (19, "share-key", 2, "010", False),
    (20, "share-default-key", 5, "080", True),
    (21, "device-not-found", 1, "044", True),
    (22, "room-sanitization", 1, "010", False),
]

# templates (16) -> notification_template -- (name, type, path)
NOTIFICATION_TEMPLATES = [
    ("CheckoutInitiationTemplate", "push notification", "notification/checkout-initiation.txt.hbs"),
    ("CheckoutAcceptanceTemplate", "push notification", "notification/checkout-acceptance.txt.hbs"),
    ("CheckoutConfirmationTemplate", "push notification", "notification/checkout-confirmation.txt.hbs"),
    ("OTPTemplate", "sms", "sms/user-verification-otp.txt.hbs"),
    ("KeySMSTemplate", "sms", "sms/amenity-keypad-key.txt.hbs"),
    ("KeyNotificationTemplate", "silent notification", "notification/app-key.txt.hbs"),
    ("DocumentApprovalStatusNotification", "push notification", "notification/document-verification-status.txt.hbs"),
    ("PreCheckoutNotification", "push notification", "notification/checkout-reminder.txt.hbs"),
    ("SmartBookingSMSTemplate", "sms", "sms/smart-booking-sms.txt.hbs"),
    ("MaintenanceKeypadKey", "sms", "sms/maintenance-keypad-key.txt.hbs"),
    ("MaintenanceAppKey", "silent notification", "notification/maintenance-app-key.txt.hbs"),
    ("AlertSMSTemplate", "sms", "sms/alert.txt.hbs"),
    ("sms", "sms", "generic/generic.hbs"),
    ("email", "email", "generic/generic.hbs"),
    ("push", "push notification", "generic/generic.hbs"),
    ("silent", "silent notification", "generic/generic.hbs"),
]
