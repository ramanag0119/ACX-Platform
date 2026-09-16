"""Step 1 - lookup / reference data (16 T1 tables + notification templates).

Every row here comes from the IKANOS dump via `seeds/data/reference.py` and
`seeds/data/countries.json`. IKANOS integer ids are preserved verbatim, which
is what the blueprint's T1 primary-key tier requires (§2.3).
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import (
    ActivityType,
    AlertType,
    AmenityCondition,
    AmenityStatus,
    CommandType,
    Country,
    DeviceParam,
    DeviceType,
    EntityType,
    IncidentEvent,
    IncidentStatus,
    KeyType,
    NotificationTemplate,
    OccasionType,
    RoleModule,
    ServiceStatus,
    ServiceType,
)
from seeds.data import reference as ref
from seeds.helpers import did, upsert

_COUNTRIES = Path(__file__).resolve().parent.parent / "data" / "countries.json"


def seed(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}

    countries = json.loads(_COUNTRIES.read_text(encoding="utf-8"))
    for row in countries:
        upsert(
            session,
            Country,
            {"id": row["id"]},
            name=row["name"],
            phone_code=row["phone_code"],
            iso_code=row["iso_code"],
            nice_name=row["nice_name"],
            iso3=row["iso3"],
            num_code=row["num_code"],
        )
    counts["country"] = len(countries)

    for cid, name in ref.AMENITY_STATUSES:
        upsert(session, AmenityStatus, {"id": cid}, amenity_status_name=name)
    counts["amenity_status"] = len(ref.AMENITY_STATUSES)

    for cid, name in ref.AMENITY_CONDITIONS:
        upsert(session, AmenityCondition, {"id": cid}, name=name)
    counts["amenity_condition"] = len(ref.AMENITY_CONDITIONS)

    for cid, name in ref.SERVICE_TYPES:
        upsert(session, ServiceType, {"id": cid}, name=name)
    counts["service_type"] = len(ref.SERVICE_TYPES)

    for cid, name in ref.SERVICE_STATUSES:
        upsert(session, ServiceStatus, {"id": cid}, name=name)
    counts["service_status"] = len(ref.SERVICE_STATUSES)

    for cid, name, read_ok, write_ok in ref.ROLE_MODULES:
        upsert(
            session,
            RoleModule,
            {"id": cid},
            module_name=name,
            read_applicable=read_ok,
            write_applicable=write_ok,
        )
    counts["role_module"] = len(ref.ROLE_MODULES)

    for cid, name, short_code in ref.DEVICE_TYPES:
        upsert(session, DeviceType, {"id": cid}, name=name, device_short_code=short_code)
    counts["device_type"] = len(ref.DEVICE_TYPES)

    for cid, dtype, param, data_type, unit in ref.DEVICE_PARAMS:
        upsert(
            session,
            DeviceParam,
            {"id": cid},
            device_type=dtype,
            param_name=param,
            data_type=data_type,
            unit=unit,
        )
    counts["device_param"] = len(ref.DEVICE_PARAMS)

    for cid, name, dtype in ref.COMMAND_TYPES:
        upsert(session, CommandType, {"id": cid}, name=name, device_type_id=dtype)
    counts["command_type"] = len(ref.COMMAND_TYPES)

    for cid, name in ref.KEY_TYPES:
        upsert(session, KeyType, {"id": cid}, name=name)
    counts["key_type"] = len(ref.KEY_TYPES)

    for cid, name in ref.ALERT_TYPES:
        upsert(session, AlertType, {"id": cid}, name=name)
    counts["alert_type"] = len(ref.ALERT_TYPES)

    for cid, name in ref.INCIDENT_STATUSES:
        upsert(session, IncidentStatus, {"id": cid}, name=name)
    counts["incident_status"] = len(ref.INCIDENT_STATUSES)

    for cid, name in ref.INCIDENT_EVENTS:
        upsert(session, IncidentEvent, {"id": cid}, name=name)
    counts["incident_event"] = len(ref.INCIDENT_EVENTS)

    for cid, name in ref.ENTITY_TYPES:
        upsert(session, EntityType, {"id": cid}, entity_type=name)
    counts["entity_type"] = len(ref.ENTITY_TYPES)

    for cid, name, entity_id, notif_type, subscribable in ref.ACTIVITY_TYPES:
        upsert(
            session,
            ActivityType,
            {"id": cid},
            activity_type=name,
            entity_type_id=entity_id,
            notification_type=notif_type,
            is_subscribable=subscribable,
        )
    counts["activity_type"] = len(ref.ACTIVITY_TYPES)

    for cid, name in ref.OCCASION_TYPES:
        upsert(session, OccasionType, {"id": cid}, occasion_type=name)
    counts["occasion_type"] = len(ref.OCCASION_TYPES)

    for name, channel, path in ref.NOTIFICATION_TEMPLATES:
        upsert(
            session,
            NotificationTemplate,
            {"id": did("notification_template", f"{name}|{channel}")},
            name=name,
            type=channel,
            path=path,
        )
    counts["notification_template"] = len(ref.NOTIFICATION_TEMPLATES)

    return counts
