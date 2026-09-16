"""Query logic for alerts, incidents and value alerts.

Reads live from PostgreSQL through the caller's session.

Person columns go through the same narrow allow-list used since Phase 2.3
(`id` plus name parts). `device.authentication_code` and `device.metadata` are
never joined in, matching Phase 2.6.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Amenity,
    AlertType,
    AppUser,
    Device,
    DeviceAlert,
    DeviceIncident,
    DeviceType,
    IncidentEvent,
    IncidentHistory,
    IncidentStatus,
    Property,
    PropertyChain,
    ValueAlert,
    ValueAlertLimitConfig,
)

BuildingProp = aliased(Property, name="building_property")
FloorProp = aliased(Property, name="floor_property")
Assignee = aliased(AppUser, name="assignee")
UpdatedBy = aliased(AppUser, name="updated_by_user")
HistoryActor = aliased(AppUser, name="history_actor")
LatestAlert = aliased(DeviceAlert, name="latest_alert")


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


def _user_ref(user_id, first, last) -> dict | None:
    if user_id is None:
        return None
    return {"id": user_id, "name": " ".join(p for p in (first, last) if p)}


# ---------------------------------------------------------------------------
# alert_type
# ---------------------------------------------------------------------------


def list_alert_types(db: Session, *, page: int, page_size: int):
    stmt = select(AlertType).order_by(AlertType.id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_alert_type(db: Session, alert_type_id: int) -> AlertType | None:
    return db.get(AlertType, alert_type_id)


def alert_type_counts(db: Session, alert_type_id: int) -> dict[str, int]:
    return {
        "alert_count": db.execute(
            select(func.count())
            .select_from(DeviceAlert)
            .where(DeviceAlert.alert_type == alert_type_id)
        ).scalar_one(),
        "incident_count": db.execute(
            select(func.count())
            .select_from(DeviceIncident)
            .where(DeviceIncident.alert_type == alert_type_id)
        ).scalar_one(),
    }


# ---------------------------------------------------------------------------
# device_alert
# ---------------------------------------------------------------------------


def _alert_stmt() -> Select:
    return (
        select(
            DeviceAlert.id,
            DeviceAlert.alert_type,
            AlertType.name.label("alert_type_name"),
            DeviceAlert.alert_severity,
            DeviceAlert.alert_data,
            DeviceAlert.device_id,
            Device.device_uid,
            Device.device_name,
            DeviceType.name.label("device_type_name"),
            # `device_alert` has no facility column -- resolved from the device.
            Device.facility_id,
            DeviceAlert.amenity_id,
            Amenity.name.label("amenity_name"),
            BuildingProp.id.label("building_id"),
            BuildingProp.property_name.label("building_name"),
            FloorProp.id.label("floor_id"),
            FloorProp.property_name.label("floor_name"),
            DeviceAlert.created_on,
            DeviceAlert.updated_on,
        )
        .select_from(DeviceAlert)
        .join(AlertType, AlertType.id == DeviceAlert.alert_type)
        .join(Device, Device.id == DeviceAlert.device_id)
        .join(DeviceType, DeviceType.id == Device.device_type)
        .join(Amenity, Amenity.id == DeviceAlert.amenity_id)
        .outerjoin(PropertyChain, PropertyChain.id == Amenity.property_chain_id)
        .outerjoin(BuildingProp, BuildingProp.id == PropertyChain.level_one_id)
        .outerjoin(FloorProp, FloorProp.id == PropertyChain.level_two_id)
    )


def list_alerts(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    alert_type: int | None = None,
    alert_severity: str | None = None,
    device_type: int | None = None,
    building_id: uuid.UUID | None = None,
    floor_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _alert_stmt().order_by(DeviceAlert.created_on.desc())
    if facility_id:
        stmt = stmt.where(Device.facility_id == facility_id)
    if device_id:
        stmt = stmt.where(DeviceAlert.device_id == device_id)
    if amenity_id:
        stmt = stmt.where(DeviceAlert.amenity_id == amenity_id)
    if alert_type is not None:
        stmt = stmt.where(DeviceAlert.alert_type == alert_type)
    if alert_severity:
        stmt = stmt.where(DeviceAlert.alert_severity == alert_severity)
    if device_type is not None:
        stmt = stmt.where(Device.device_type == device_type)
    if building_id:
        stmt = stmt.where(BuildingProp.id == building_id)
    if floor_id:
        stmt = stmt.where(FloorProp.id == floor_id)
    if created_from:
        stmt = stmt.where(DeviceAlert.created_on >= created_from)
    if created_to:
        stmt = stmt.where(DeviceAlert.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_alert(db: Session, alert_id: int):
    return db.execute(
        _alert_stmt().where(DeviceAlert.id == alert_id)
    ).mappings().one_or_none()


def incidents_for_alert(db: Session, alert_id: int) -> list[dict]:
    """Reverse lookup: incidents whose latest_alert_id points at this alert.

    The alert holds no incident_id, so this is 0..N and never a single object.
    """
    rows = db.execute(
        select(
            DeviceIncident.id,
            DeviceIncident.subject,
            DeviceIncident.current_incident_status,
            IncidentStatus.name.label("status_name"),
        )
        .outerjoin(
            IncidentStatus, IncidentStatus.id == DeviceIncident.current_incident_status
        )
        .where(DeviceIncident.latest_alert_id == alert_id)
        .order_by(DeviceIncident.created_on)
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# device_incident
# ---------------------------------------------------------------------------


def _incident_stmt() -> Select:
    return (
        select(
            DeviceIncident.id,
            DeviceIncident.subject,
            DeviceIncident.description,
            DeviceIncident.alert_type,
            AlertType.name.label("alert_type_name"),
            DeviceIncident.current_incident_status,
            IncidentStatus.name.label("status_name"),
            DeviceIncident.facility_id,
            DeviceIncident.device_id,
            Device.device_uid,
            Device.device_name,
            DeviceIncident.amenity_id,
            Amenity.name.label("amenity_name"),
            DeviceIncident.latest_alert_id,
            LatestAlert.alert_severity.label("latest_alert_severity"),
            DeviceIncident.assigned_to,
            Assignee.first_name.label("assignee_first_name"),
            Assignee.last_name.label("assignee_last_name"),
            DeviceIncident.updated_by,
            UpdatedBy.first_name.label("updated_by_first_name"),
            UpdatedBy.last_name.label("updated_by_last_name"),
            DeviceIncident.created_on,
            DeviceIncident.updated_on,
        )
        .select_from(DeviceIncident)
        .join(AlertType, AlertType.id == DeviceIncident.alert_type)
        .join(Device, Device.id == DeviceIncident.device_id)
        .join(Amenity, Amenity.id == DeviceIncident.amenity_id)
        .outerjoin(
            IncidentStatus, IncidentStatus.id == DeviceIncident.current_incident_status
        )
        .outerjoin(LatestAlert, LatestAlert.id == DeviceIncident.latest_alert_id)
        .outerjoin(Assignee, Assignee.id == DeviceIncident.assigned_to)
        .outerjoin(UpdatedBy, UpdatedBy.id == DeviceIncident.updated_by)
    )


def _shape_incident(row) -> dict:
    data = dict(row)
    data["assignee"] = _user_ref(
        data.pop("assigned_to"),
        data.pop("assignee_first_name"),
        data.pop("assignee_last_name"),
    )
    data["updated_by_user"] = _user_ref(
        data.pop("updated_by"),
        data.pop("updated_by_first_name"),
        data.pop("updated_by_last_name"),
    )
    return data


def list_incidents(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    alert_type: int | None = None,
    current_incident_status: int | None = None,
    assigned_to: uuid.UUID | None = None,
    unassigned: bool | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _incident_stmt().order_by(DeviceIncident.created_on.desc())
    if facility_id:
        stmt = stmt.where(DeviceIncident.facility_id == facility_id)
    if device_id:
        stmt = stmt.where(DeviceIncident.device_id == device_id)
    if amenity_id:
        stmt = stmt.where(DeviceIncident.amenity_id == amenity_id)
    if alert_type is not None:
        stmt = stmt.where(DeviceIncident.alert_type == alert_type)
    if current_incident_status is not None:
        stmt = stmt.where(
            DeviceIncident.current_incident_status == current_incident_status
        )
    if assigned_to:
        stmt = stmt.where(DeviceIncident.assigned_to == assigned_to)
    if unassigned is not None:
        column = DeviceIncident.assigned_to
        stmt = stmt.where(column.is_(None) if unassigned else column.is_not(None))
    if created_from:
        stmt = stmt.where(DeviceIncident.created_on >= created_from)
    if created_to:
        stmt = stmt.where(DeviceIncident.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return [_shape_incident(r) for r in rows], total


def get_incident(db: Session, incident_id: uuid.UUID):
    row = db.execute(
        _incident_stmt().where(DeviceIncident.id == incident_id)
    ).mappings().one_or_none()
    return _shape_incident(row) if row is not None else None


def incident_history(db: Session, incident_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(
            IncidentHistory.id,
            IncidentHistory.incident_event_id,
            IncidentEvent.name.label("incident_event_name"),
            IncidentHistory.incident_event_data,
            IncidentHistory.created_by,
            HistoryActor.first_name,
            HistoryActor.last_name,
            IncidentHistory.created_on,
        )
        .join(IncidentEvent, IncidentEvent.id == IncidentHistory.incident_event_id)
        .outerjoin(HistoryActor, HistoryActor.id == IncidentHistory.created_by)
        .where(IncidentHistory.incident_id == incident_id)
        .order_by(IncidentHistory.incident_event_id)
    ).all()
    return [
        {
            "id": r.id,
            "incident_event_id": r.incident_event_id,
            "incident_event_name": r.incident_event_name,
            "incident_event_data": r.incident_event_data,
            "created_by": _user_ref(r.created_by, r.first_name, r.last_name),
            "created_on": r.created_on,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# value_alert
# ---------------------------------------------------------------------------


def _value_alert_stmt(*, detailed: bool = False) -> Select:
    columns = [
        ValueAlert.id,
        ValueAlert.device_id,
        Device.device_uid,
        ValueAlert.device_name,
        ValueAlert.device_type_id,
        DeviceType.name.label("device_type_name"),
        ValueAlert.amenity_id,
        Amenity.name.label("amenity_name"),
        ValueAlert.facility_id,
        ValueAlert.limit_config_id,
        ValueAlertLimitConfig.parameter,
        ValueAlert.limit_type,
        ValueAlert.limit_value,
        ValueAlert.description,
        ValueAlert.status,
        ValueAlert.device_status_id,
        ValueAlert.timestamp,
        ValueAlert.created_on,
        ValueAlert.updated_on,
    ]
    if detailed:
        columns += [
            ValueAlertLimitConfig.nominal,
            ValueAlertLimitConfig.limit_low_value,
            ValueAlertLimitConfig.limit_high_value,
            ValueAlertLimitConfig.limit_low_percentage,
            ValueAlertLimitConfig.limit_high_percentage,
            ValueAlertLimitConfig.is_percentage_value,
            ValueAlertLimitConfig.limit_check,
            ValueAlertLimitConfig.remarks,
        ]
    return (
        select(*columns)
        .select_from(ValueAlert)
        .join(Device, Device.id == ValueAlert.device_id)
        .join(DeviceType, DeviceType.id == ValueAlert.device_type_id)
        .join(Amenity, Amenity.id == ValueAlert.amenity_id)
        .join(
            ValueAlertLimitConfig,
            ValueAlertLimitConfig.id == ValueAlert.limit_config_id,
        )
    )


def list_value_alerts(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    status: int | None = None,
    limit_type: str | None = None,
    parameter: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    stmt = _value_alert_stmt().order_by(ValueAlert.timestamp.desc())
    if facility_id:
        stmt = stmt.where(ValueAlert.facility_id == facility_id)
    if device_id:
        stmt = stmt.where(ValueAlert.device_id == device_id)
    if amenity_id:
        stmt = stmt.where(ValueAlert.amenity_id == amenity_id)
    if status is not None:
        stmt = stmt.where(ValueAlert.status == status)
    if limit_type:
        stmt = stmt.where(ValueAlert.limit_type == limit_type)
    if parameter:
        stmt = stmt.where(ValueAlertLimitConfig.parameter == parameter)
    if created_from:
        stmt = stmt.where(ValueAlert.created_on >= created_from)
    if created_to:
        stmt = stmt.where(ValueAlert.created_on <= created_to)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_value_alert(db: Session, value_alert_id: uuid.UUID):
    return db.execute(
        _value_alert_stmt(detailed=True).where(ValueAlert.id == value_alert_id)
    ).mappings().one_or_none()
