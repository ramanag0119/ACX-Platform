"""Alert, incident and value-alert read APIs (Phase 2.7).

    GET /api/v1/alert-types    · /{id}              alert_type (16 lookup rows)
    GET /api/v1/alerts         · /{id}              device_alert
    GET /api/v1/alerts/{id}/incidents               reverse lookup, 0..N
    GET /api/v1/incidents      · /{id}              device_incident (+ history)
    GET /api/v1/value-alerts   · /{id}              value_alert

TWO ALERT ENTITIES, NOT ONE. `device_alert` is the device event stream;
`value_alert` is a threshold breach against `value_alert_limit_config`. They
have different primary keys, different columns and different status models, so
they are exposed separately rather than merged into an invented `alert`.

DIRECTION OF THE INCIDENT LINK. `device_incident.latest_alert_id ->
device_alert.id`. There is no `incident_id` on `device_alert`, so
`/alerts/{id}/incidents` is a reverse lookup returning a LIST -- 5 of the 9
seeded alerts are referenced by an incident, 4 are not.

Incidents are included here rather than split into their own module because
the schema makes them inseparable: an alert has no status of its own, and its
lifecycle is `device_incident.current_incident_status`.

RBAC: every route requires `read` on `caleido_network`, the module the
blueprint records as governing device-alert visibility. There is NO `alerts`
module in the 18-row registry.

READ-ONLY. See docs/PHASE2_7_ALERTS.md for the blockers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.alert import (
    AlertDetail,
    AlertRead,
    AlertTypeDetail,
    AlertTypeRead,
    IncidentDetail,
    IncidentHistoryRead,
    IncidentRead,
    IncidentRef,
    ValueAlertDetail,
    ValueAlertRead,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import AlertSeverity
from app.schemas.health import ErrorResponse
from app.services import alert as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

NETWORK_READ = [Depends(require_permission("caleido_network", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

alert_types_router = APIRouter(
    prefix="/alert-types", tags=["alerts"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
alerts_router = APIRouter(
    prefix="/alerts", tags=["alerts"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
incidents_router = APIRouter(
    prefix="/incidents", tags=["incidents"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)
value_alerts_router = APIRouter(
    prefix="/value-alerts", tags=["alerts"],
    dependencies=NETWORK_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# alert_type
# ---------------------------------------------------------------------------


@alert_types_router.get(
    "",
    response_model=Page[AlertTypeRead],
    summary="List alert types",
    description="16 seeded rows, (id, name) only -- the type carries no severity.",
)
def list_alert_types(
    db: DbSession, page: int = PageParam, page_size: int = SizeParam
) -> Page[AlertTypeRead]:
    rows, total = svc.list_alert_types(db, page=page, page_size=page_size)
    return Page[AlertTypeRead](
        items=[AlertTypeRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@alert_types_router.get(
    "/{alert_type_id}",
    response_model=AlertTypeDetail,
    responses=NOT_FOUND,
    summary="Get an alert type",
)
def get_alert_type(alert_type_id: int, db: DbSession) -> AlertTypeDetail:
    row = svc.get_alert_type(db, alert_type_id)
    if row is None:
        raise _missing("Alert type", alert_type_id)
    return AlertTypeDetail(
        **AlertTypeRead.model_validate(row).model_dump(),
        **svc.alert_type_counts(db, alert_type_id),
    )


# ---------------------------------------------------------------------------
# device_alert
# ---------------------------------------------------------------------------


@alerts_router.get(
    "",
    response_model=Page[AlertRead],
    summary="List device alerts",
    description=(
        "`device_alert` -- the raw device event stream. Severity is `warning` "
        "or `critical` only. Alerts have no status of their own; lifecycle "
        "lives on the incident."
    ),
)
def list_alerts(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None, description="Resolved via the device"),
    device_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None, description="The room"),
    building_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    floor_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    alert_type: int | None = Query(None, description="alert_type.id"),
    alert_severity: AlertSeverity | None = Query(
        None, description="alert_severity: warning | critical"
    ),
    device_type: int | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
) -> Page[AlertRead]:
    rows, total = svc.list_alerts(
        db, page=page, page_size=page_size, facility_id=facility_id,
        device_id=device_id, amenity_id=amenity_id, building_id=building_id,
        floor_id=floor_id, alert_type=alert_type, alert_severity=alert_severity,
        device_type=device_type, created_from=created_from, created_to=created_to,
    )
    return Page[AlertRead](
        items=[AlertRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@alerts_router.get(
    "/{alert_id}",
    response_model=AlertDetail,
    responses=NOT_FOUND,
    summary="Get a device alert",
)
def get_alert(alert_id: int, db: DbSession) -> AlertDetail:
    row = svc.get_alert(db, alert_id)
    if row is None:
        raise _missing("Alert", alert_id)
    incidents = svc.incidents_for_alert(db, alert_id)
    return AlertDetail(
        **AlertRead.model_validate(row).model_dump(),
        incidents=[IncidentRef.model_validate(i) for i in incidents],
        incident_count=len(incidents),
    )


@alerts_router.get(
    "/{alert_id}/incidents",
    response_model=list[IncidentRef],
    responses=NOT_FOUND,
    summary="Incidents raised from this alert",
    description=(
        "REVERSE lookup on `device_incident.latest_alert_id`. Returns a list "
        "because the alert holds no incident reference -- 0..N incidents may "
        "point at the same alert."
    ),
)
def get_alert_incidents(alert_id: int, db: DbSession) -> list[IncidentRef]:
    if svc.get_alert(db, alert_id) is None:
        raise _missing("Alert", alert_id)
    return [IncidentRef.model_validate(i) for i in svc.incidents_for_alert(db, alert_id)]


# ---------------------------------------------------------------------------
# device_incident
# ---------------------------------------------------------------------------


@incidents_router.get(
    "",
    response_model=Page[IncidentRead],
    summary="List incidents",
    description=(
        "`device_incident` -- the assignable, resolvable case. Status is "
        "Unread | Read | Assigned | Resolved. There is no `resolved_on` or "
        "`notes` column: both live in `incident_history`."
    ),
)
def list_incidents(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    device_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None),
    alert_type: int | None = Query(None),
    current_incident_status: int | None = Query(
        None, alias="status", description="incident_status.id: 1..4"
    ),
    assigned_to: uuid.UUID | None = Query(None),
    unassigned: bool | None = Query(None, description="assigned_to IS NULL"),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
) -> Page[IncidentRead]:
    rows, total = svc.list_incidents(
        db, page=page, page_size=page_size, facility_id=facility_id,
        device_id=device_id, amenity_id=amenity_id, alert_type=alert_type,
        current_incident_status=current_incident_status, assigned_to=assigned_to,
        unassigned=unassigned, created_from=created_from, created_to=created_to,
    )
    return Page[IncidentRead](
        items=[IncidentRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@incidents_router.get(
    "/{incident_id}",
    response_model=IncidentDetail,
    responses=NOT_FOUND,
    summary="Get an incident with its audit trail",
)
def get_incident(incident_id: uuid.UUID, db: DbSession) -> IncidentDetail:
    row = svc.get_incident(db, incident_id)
    if row is None:
        raise _missing("Incident", incident_id)
    history = svc.incident_history(db, incident_id)
    return IncidentDetail(
        **IncidentRead.model_validate(row).model_dump(),
        history=[IncidentHistoryRead.model_validate(h) for h in history],
        history_count=len(history),
    )


# ---------------------------------------------------------------------------
# value_alert
# ---------------------------------------------------------------------------


@value_alerts_router.get(
    "",
    response_model=Page[ValueAlertRead],
    summary="List value alerts",
    description=(
        "`value_alert` -- a threshold breach against a limit config. Status is "
        "an integer: 0 = Active, 1 = Resolved. A different entity from "
        "`device_alert`."
    ),
)
def list_value_alerts(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    device_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None),
    status_value: int | None = Query(
        None, alias="status", description="0 = Active, 1 = Resolved"
    ),
    limit_type: str | None = Query(None, description="Free text, e.g. high | low"),
    parameter: str | None = Query(None, description="From the limit config"),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
) -> Page[ValueAlertRead]:
    rows, total = svc.list_value_alerts(
        db, page=page, page_size=page_size, facility_id=facility_id,
        device_id=device_id, amenity_id=amenity_id, status=status_value,
        limit_type=limit_type, parameter=parameter,
        created_from=created_from, created_to=created_to,
    )
    return Page[ValueAlertRead](
        items=[ValueAlertRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@value_alerts_router.get(
    "/{value_alert_id}",
    response_model=ValueAlertDetail,
    responses=NOT_FOUND,
    summary="Get a value alert with its limit configuration",
)
def get_value_alert(value_alert_id: uuid.UUID, db: DbSession) -> ValueAlertDetail:
    row = svc.get_value_alert(db, value_alert_id)
    if row is None:
        raise _missing("Value alert", value_alert_id)
    return ValueAlertDetail.model_validate(row)
