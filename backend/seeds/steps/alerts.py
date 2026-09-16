"""Step 9 - alerts, incidents, incident history and value-limit alerts.

The IKANOS model that the Phase 1 foundation was missing entirely:

    device -> device_alert -> device_incident -> incident_history
                                 |                    |
                            alert_type          incident_event

An alert is the raw event stream. An incident is the deduplicated, assignable
case, and it points back at the alert that last fired via `latest_alert_id`.

NOTE: `alert_type` is (id, name) ONLY -- severity lives on
`device_alert.alert_severity`, whose enum has exactly two values,
`warning` and `critical`. `Info` does not exist and is not seeded.
`device_incident` has no `severity`, `notes` or `resolved_on`: resolution time
and notes live in `incident_history`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    DeviceAlert,
    DeviceIncident,
    IncidentHistory,
    ValueAlert,
    ValueAlertLimitConfig,
)
from seeds.helpers import DEMO_NOW, days, did, hours, upsert

# alert_type ids from IKANOS
BATTERY_LOW, DEVICE_DISCONNECTION = 1, 2
DEVICE_OVERHEATING, PREVENTIVE_MAINTENANCE = 5, 6
MIKOS_OVERCURRENT, ROOM_AIR_QUALITY_POOR, ROOM_INTERNAL_HOT = 7, 8, 9
DOOR_AJAR, HUB_OFFLINE, MIKOS_OFFLINE, LOCK_OFFLINE, AIRQ_OFFLINE = 12, 13, 14, 15, 16

# incident_status ids: 1 Unread, 2 Read, 3 Assigned, 4 Resolved
UNREAD, READ, ASSIGNED, RESOLVED = 1, 2, 3, 4
# incident_event ids: adds 5 Reopened
EV_UNREAD, EV_READ, EV_ASSIGNED, EV_RESOLVED, EV_REOPENED = 1, 2, 3, 4, 5

# (key, device, alert_type, severity, hours ago, alert payload)
ALERTS = [
    ("al-hub-offline-106", "106-hub", HUB_OFFLINE, "critical", 9,
     {"reason": "no heartbeat", "missed_beats": 18}),
    ("al-mikos-offline-106", "106-mik", MIKOS_OFFLINE, "warning", 9,
     {"reason": "parent hub offline"}),
    ("al-airq-offline-106", "106-air", AIRQ_OFFLINE, "warning", 9,
     {"reason": "parent hub offline"}),
    ("al-airq-poor-205", "205-air", ROOM_AIR_QUALITY_POOR, "warning", 5,
     {"iaq": 178, "threshold": 150}),
    ("al-overheat-205", "205-mik", DEVICE_OVERHEATING, "critical", 4,
     {"device_temperature": 66.0, "threshold": 60.0}),
    ("al-battery-104", "104-kle", BATTERY_LOW, "warning", 30,
     {"battery_percentage": 11.0, "threshold": 15.0}),
    ("al-lock-offline-104", "104-kle", LOCK_OFFLINE, "critical", 28,
     {"reason": "under maintenance"}),
    ("al-room-hot-101", "101-air", ROOM_INTERNAL_HOT, "warning", 2,
     {"room_temperature": 31.8, "threshold": 30.0}),
    ("al-preventive-rest", "rest-mik", PREVENTIVE_MAINTENANCE, "warning", 40,
     {"runtime_hours": 8600}),
]

# (key, alert key, subject, status, assignee, updated_by, history events)
# `history` is a list of (event id, note) applied in order.
INCIDENTS = [
    ("inc-hub-106", "al-hub-offline-106",
     "Intellihub offline in room 106", ASSIGNED, "vikram.rao", "kavya.iyer",
     [(EV_UNREAD, "Alert raised by health monitor"),
      (EV_READ, "Reviewed by duty manager"),
      (EV_ASSIGNED, "Assigned to Vikram Rao for on-site check")]),
    ("inc-overheat-205", "al-overheat-205",
     "Mikos overheating in room 205", READ, None, "kavya.iyer",
     [(EV_UNREAD, "Temperature threshold breached"),
      (EV_READ, "Acknowledged, monitoring")]),
    ("inc-airq-205", "al-airq-poor-205",
     "Poor air quality in room 205", RESOLVED, "vikram.rao", "vikram.rao",
     [(EV_UNREAD, "IAQ above threshold"),
      (EV_READ, "Acknowledged"),
      (EV_ASSIGNED, "Assigned to maintenance"),
      (EV_RESOLVED, "Filter replaced, IAQ back to normal")]),
    ("inc-battery-104", "al-battery-104",
     "Kleio battery low in room 104", RESOLVED, "vikram.rao", "vikram.rao",
     [(EV_UNREAD, "Battery below 15%"),
      (EV_ASSIGNED, "Battery replacement scheduled"),
      (EV_RESOLVED, "Battery replaced"),
      (EV_REOPENED, "Battery drained again within 24h")]),
    ("inc-room-hot-101", "al-room-hot-101",
     "Room 101 running hot", UNREAD, None, "kavya.iyer",
     [(EV_UNREAD, "Room temperature above threshold")]),
]

# (key, parameter, device, nominal, low%, high%, low, high, remarks)
LIMIT_CONFIGS = [
    ("lc-voltage-mikos", "voltage", "205-mik", 240, 10, 10, 216, 264,
     "Mains voltage window for Mikos energy meters"),
    ("lc-current-mikos", "current", "205-mik", 16, 0, 25, 0, 20,
     "Overcurrent trip threshold"),
    ("lc-frequency-mikos", "frequency", "205-mik", 50, 4, 4, 48, 52,
     "Grid frequency window"),
    ("lc-temperature-hub", "temperature", "101-hub", 45, 0, 33, 0, 60,
     "Intellihub internal temperature ceiling"),
]

# (key, limit config, device, limit type, breached value, status, hours ago)
# value_alert.status is an integer: 0 = Active, 1 = Resolved (NEEDS_REVIEW D8).
VALUE_ALERTS = [
    ("va-overheat-205", "lc-temperature-hub", "205-mik", "high", "60", 0, 4),
    ("va-frequency-205", "lc-frequency-mikos", "205-mik", "low", "48", 1, 26),
    ("va-voltage-101", "lc-voltage-mikos", "101-mik", "high", "264", 1, 30),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    users = ctx["users"]
    devices = ctx["devices"]

    alerts = {}
    for key, device_key, alert_type, severity, hours_ago, payload in ALERTS:
        device = devices[device_key]
        moment = DEMO_NOW - hours(hours_ago)
        alerts[key] = upsert(
            session,
            DeviceAlert,
            {
                "device_id": device.id,
                "alert_type": alert_type,
                "created_on": moment,
            },
            amenity_id=device.amenity_id,
            alert_severity=severity,
            alert_data=payload,
            created_by=users["system"].id,
            updated_on=moment,
        )
    counts["device_alert"] = len(alerts)

    n_history = 0
    for key, alert_key, subject, status, assignee, updated_by, history in INCIDENTS:
        # Device and room come straight off the alert row, so an incident can
        # never disagree with the alert it was raised from.
        alert = alerts[alert_key]
        incident = upsert(
            session,
            DeviceIncident,
            {"id": did("device_incident", key)},
            facility_id=facility.id,
            amenity_id=alert.amenity_id,
            device_id=alert.device_id,
            alert_type=alert.alert_type,
            subject=subject,
            description=f"{subject}. Raised from device alert stream.",
            assigned_to=users[assignee].id if assignee else None,
            latest_alert_id=alert.id,
            current_incident_status=status,
            updated_by=users[updated_by].id,
        )
        for order, (event_id, note) in enumerate(history):
            upsert(
                session,
                IncidentHistory,
                {"incident_id": incident.id, "incident_event_id": event_id},
                incident_event_data={"note": note, "sequence": order},
                created_by=users[updated_by].id,
            )
            n_history += 1
    counts["device_incident"] = len(INCIDENTS)
    counts["incident_history"] = n_history

    configs = {}
    for (key, parameter, device_key, nominal, low_pct, high_pct,
         low_val, high_val, remarks) in LIMIT_CONFIGS:
        device = devices[device_key]
        configs[key] = upsert(
            session,
            ValueAlertLimitConfig,
            {"id": did("value_alert_limit_config", key)},
            parameter=parameter,
            device_name=device_key[:50],
            device_id=device.id,
            limit_check="Y",
            is_percentage_value="no",
            nominal=nominal,
            limit_low_percentage=low_pct,
            limit_high_percentage=high_pct,
            limit_low_value=low_val,
            limit_high_value=high_val,
            remarks=remarks,
            facility_id=facility.id,
        )
    counts["value_alert_limit_config"] = len(configs)

    for key, config_key, device_key, limit_type, value, status, hours_ago in VALUE_ALERTS:
        device = devices[device_key]
        upsert(
            session,
            ValueAlert,
            {"id": did("value_alert", key)},
            device_id=device.id,
            device_type_id=device.device_type,
            device_name=device_key[:50],
            amenity_id=device.amenity_id,
            limit_config_id=configs[config_key].id,
            # REVIEW: `device_status_id` has no documented meaning and no FK
            # target in IKANOS. Seeded as 1 purely to satisfy NOT NULL.
            device_status_id=1,
            timestamp=DEMO_NOW - hours(hours_ago),
            limit_value=value,
            limit_type=limit_type,
            description=(
                f"{configs[config_key].parameter} crossed the {limit_type} limit"
            ),
            status=status,
            facility_id=facility.id,
        )
    counts["value_alert"] = len(VALUE_ALERTS)

    return counts
