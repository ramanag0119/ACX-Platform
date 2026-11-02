"""OSS -> contract adapters for alerts and alert types.

Verified OSS reality (see docs/DESIGN_AND_READINESS.md):
  * `insp_device_alert` exists (device event stream) -> alerts + alert-types.
    It has NO alert-type lookup table, so alert type NAMES are the stored code
    (no fabricated label), and NO stable integer id (PK is uuid+time), so
    detail-by-id is unsupported.
  * There is NO `device_incident` table. OSS has `insp_service_request`
    (support tickets) + status/issue/priority lookups, which is a DIFFERENT
    concept. Incidents are therefore HMS (BSS) data and not served here.
  * There is NO value-alert (threshold-breach) table. `insp_limit_config` is
    threshold CONFIG only, not breach events -> value alerts are HMS data too.

All queries are read-only. `insp_device_alert` is currently empty (0 rows), so
the supported list endpoints return empty pages, which is correct (not an error).
"""

from __future__ import annotations

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.adapters.base import AdapterNotMapped
from app.db.tables import insp_device, insp_device_alert
from app.schemas.alert import AlertRead, AlertTypeRead
from app.schemas.common import UserRef  # noqa: F401  (contract re-export parity)

A = insp_device_alert
D = insp_device


def _device_by_uid(db: Session) -> dict:
    """Devices keyed by device_uid. insp_device_alert.device_id is NULL, so the
    real device is resolved via device_uid (same linkage as health/telemetry)."""
    rows = db.execute(
        select(D.c.device_id, D.c.device_uid, D.c.device_name, D.c.device_type)
    ).all()
    return {r.device_uid: r for r in rows}


# --------------------------------------------------------------------------
# alert-types (derived from DISTINCT device_alert.alert_type; no name lookup)
# --------------------------------------------------------------------------

def _alert_type_registry(db: Session) -> list[dict]:
    codes = db.execute(
        select(distinct(A.c.alert_type)).where(A.c.alert_type.is_not(None)).order_by(A.c.alert_type)
    ).scalars().all()
    # No OSS alert-type name table -> name is the stored code (as-stored).
    return [{"id": int(code), "name": str(code)} for code in codes]


def list_alert_types(db: Session, *, page: int, page_size: int) -> tuple[list[AlertTypeRead], int]:
    reg = _alert_type_registry(db)
    total = len(reg)
    start = (page - 1) * page_size
    return [AlertTypeRead(**r) for r in reg[start:start + page_size]], total


def get_alert_type(db: Session, type_id: int):
    reg = _alert_type_registry(db)
    match = next((r for r in reg if r["id"] == type_id), None)
    if match is None:
        return None
    count = db.execute(
        select(func.count()).select_from(A).where(A.c.alert_type == type_id)
    ).scalar_one()
    # incident_count is null (unknown): OSS has no device_incident table, so a
    # count cannot be derived -- it is NOT reported as 0.
    from app.schemas.alert import AlertTypeDetail
    return AlertTypeDetail(**match, alert_count=count, incident_count=None)


# --------------------------------------------------------------------------
# alerts (device_alert stream)
# --------------------------------------------------------------------------

def list_alerts(db: Session, *, page: int, page_size: int, **filters) -> tuple[list[AlertRead], int]:
    stmt = select(A)
    if filters.get("device_uid"):
        stmt = stmt.where(A.c.device_uid == filters["device_uid"])
    if filters.get("alert_severity"):
        stmt = stmt.where(A.c.alert_severity == filters["alert_severity"])
    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    rows = db.execute(
        stmt.order_by(A.c.time.desc()).limit(page_size).offset((page - 1) * page_size)
    ).all()
    dev = _device_by_uid(db)
    out: list[AlertRead] = []
    for i, r in enumerate(rows, start=(page - 1) * page_size + 1):
        d = dev.get(r.device_uid)
        out.append(AlertRead(
            id=i,  # derived ordinal: OSS PK is (record_id uuid, time), no int id
            alert_type=r.alert_type,
            alert_type_name=None if r.alert_type is None else str(r.alert_type),
            alert_severity=r.alert_severity,  # as stored
            alert_data=r.alert_data,
            device_id=d.device_id if d else r.device_id,  # resolve real id via uid
            device_uid=r.device_uid,
            device_name=d.device_name if d else None,
            device_type_name=d.device_type if d else None,
            amenity_id=None,
            facility_id=None,
            created_on=r.created_dtm_utc,
            updated_on=r.updated_dtm_utc,
        ))
    return out, total


def get_alert(db: Session, alert_id: int):
    # OSS device_alert has no stable integer id (PK is record_id uuid + time).
    raise AdapterNotMapped("alerts detail by id (no stable OSS integer id)")


def list_alert_incidents(db: Session, alert_id: int):
    # OSS has no device_incident table and no alert<->incident linkage.
    raise AdapterNotMapped("alert incidents (no device_incident linkage in OSS)")
