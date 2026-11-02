"""OSS -> contract adapters for telemetry.

Source: `insp_device_performance` (one JSONB `param_data` blob per reading,
linked to a device by `device_uid`; `device_id` is NULL in OSS).

Mapping (confirmed compatibility decisions, see docs/DESIGN_AND_READINESS.md):
  * device-current-stats  <- latest `param_data` snapshot per device_uid (clean).
  * device-stats          <- `param_data` exploded into one row per parameter.
                             OSS has no stable per-parameter row id, so the id is
                             a derived ordinal and detail-by-id is unsupported.
  * device-params         <- derived registry over DISTINCT param_data keys;
                             data_type inferred from the value; unit null.
  * other-device-readings <- NO OSS source (no third-party meter table) ->
                             AdapterNotMapped (explicit unsupported, not fake).

Readings are returned as stored; no numeric aggregation/conversion is applied.
`insp_device_performance` holds ~hundreds of rows here; device-stats explodes in
memory, which is fine at this scale and documented as unsuitable for high volume.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.base import AdapterNotMapped
from app.db.tables import insp_device, insp_device_performance
from app.schemas.telemetry import (
    DeviceCurrentStatRead,
    DeviceParamDetail,
    DeviceParamRead,
    DeviceStatRead,
)

D = insp_device
P = insp_device_performance


def _infer_data_type(value) -> str:
    if isinstance(value, bool):
        return "Integer"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Double"
    return "String"


def _device_by_uid(db: Session) -> dict[str, dict]:
    rows = db.execute(
        select(D.c.device_uid, D.c.device_id, D.c.device_name, D.c.device_type)
    ).all()
    return {
        r.device_uid: {
            "device_id": r.device_id,
            "device_name": r.device_name,
            "device_type_name": r.device_type,
        }
        for r in rows
    }


def _paginate(seq, page, page_size):
    start = (page - 1) * page_size
    return seq[start:start + page_size]


# --------------------------------------------------------------------------
# device-current-stats  (latest snapshot per device)
# --------------------------------------------------------------------------

def _latest_perf_rows(db: Session, device_uid: str | None = None):
    stmt = select(
        P.c.record_id, P.c.device_uid, P.c.param_data,
        P.c.created_dtm_utc, P.c.updated_dtm_utc,
    ).distinct(P.c.device_uid).order_by(P.c.device_uid, P.c.time.desc())
    if device_uid:
        stmt = stmt.where(P.c.device_uid == device_uid)
    return db.execute(stmt).all()


def _to_current_stat(row, dev: dict) -> DeviceCurrentStatRead:
    d = dev.get(row.device_uid, {})
    return DeviceCurrentStatRead(
        id=row.record_id,
        device_id=d.get("device_id"),
        device_uid=row.device_uid,
        device_name=d.get("device_name"),
        device_type_name=d.get("device_type_name"),
        amenity_id=None,
        amenity_name=None,
        facility_id=None,
        device_stats=row.param_data,
        is_other_device=None,
        created_on=row.created_dtm_utc,
        updated_on=row.updated_dtm_utc,
    )


def list_device_current_stats(db: Session, *, page: int, page_size: int, **filters) -> tuple[list[DeviceCurrentStatRead], int]:
    dev = _device_by_uid(db)
    rows = _latest_perf_rows(db, filters.get("device_uid"))
    total = len(rows)
    page_rows = _paginate(rows, page, page_size)
    return [_to_current_stat(r, dev) for r in page_rows], total


def get_device_current_stat(db: Session, cur_id: uuid.UUID) -> DeviceCurrentStatRead | None:
    row = db.execute(
        select(P.c.record_id, P.c.device_uid, P.c.param_data,
               P.c.created_dtm_utc, P.c.updated_dtm_utc)
        .where(P.c.record_id == cur_id)
    ).one_or_none()
    if row is None:
        return None
    return _to_current_stat(row, _device_by_uid(db))


# --------------------------------------------------------------------------
# device-params  (derived registry from JSON keys)
# --------------------------------------------------------------------------

def _param_registry(db: Session) -> list[dict]:
    """Distinct param keys across param_data, with an inferred data_type."""
    rows = db.execute(select(P.c.param_data)).scalars().all()
    seen: dict[str, str] = {}
    for pd in rows:
        if not isinstance(pd, dict):
            continue
        for k, v in pd.items():
            seen.setdefault(k, _infer_data_type(v))
    names = sorted(seen)
    return [
        {"id": i + 1, "param_name": n, "data_type": seen[n], "unit": None,
         "device_type": None, "device_type_name": None, "device_short_code": None}
        for i, n in enumerate(names)
    ]


def list_device_params(db: Session, *, page: int, page_size: int, **filters) -> tuple[list[DeviceParamRead], int]:
    reg = _param_registry(db)
    total = len(reg)
    return [DeviceParamRead(**r) for r in _paginate(reg, page, page_size)], total


def get_device_param(db: Session, param_id: int) -> DeviceParamDetail | None:
    reg = _param_registry(db)
    match = next((r for r in reg if r["id"] == param_id), None)
    if match is None:
        return None
    # reading_count = occurrences of this key across all param_data blobs.
    name = match["param_name"]
    count = 0
    for pd in db.execute(select(P.c.param_data)).scalars().all():
        if isinstance(pd, dict) and name in pd:
            count += 1
    return DeviceParamDetail(**match, reading_count=count)


# --------------------------------------------------------------------------
# device-stats  (param_data exploded into per-parameter rows)
# --------------------------------------------------------------------------

def _explode(db: Session, device_uid: str | None, param_name: str | None):
    dev = _device_by_uid(db)
    # device_param_id is the SAME derived ordinal the /device-params registry
    # exposes for that parameter name -- consistent, not a magic placeholder.
    param_ids = {r["param_name"]: r["id"] for r in _param_registry(db)}
    stmt = select(
        P.c.device_uid, P.c.recorded_at, P.c.created_dtm_utc, P.c.param_data,
    ).order_by(P.c.time.desc())
    if device_uid:
        stmt = stmt.where(P.c.device_uid == device_uid)
    out: list[DeviceStatRead] = []
    for row in db.execute(stmt).all():
        pd = row.param_data if isinstance(row.param_data, dict) else {}
        d = dev.get(row.device_uid, {})
        for k, v in pd.items():
            if param_name and k != param_name:
                continue
            out.append(DeviceStatRead(
                id=0,  # assigned per-page in list_device_stats (derived ordinal)
                device_id=d.get("device_id"),
                device_uid=row.device_uid,
                device_name=d.get("device_name"),
                device_type_name=d.get("device_type_name"),
                amenity_id=None, facility_id=None,
                device_param_id=param_ids.get(k),
                param_name=k,
                data_type=_infer_data_type(v),
                unit=None,
                device_param_value=str(v),
                timestamp=row.recorded_at,
                is_other_device=None,
                created_on=row.created_dtm_utc,
            ))
    return out


def list_device_stats(db: Session, *, page: int, page_size: int, **filters) -> tuple[list[DeviceStatRead], int]:
    rows = _explode(db, filters.get("device_uid"), filters.get("param_name"))
    total = len(rows)
    page_rows = _paginate(rows, page, page_size)
    # re-id within the page so ids are 1-based per response (derived)
    for i, r in enumerate(page_rows, start=(page - 1) * page_size + 1):
        r.id = i
    return page_rows, total


def get_device_stat(db: Session, stat_id: int) -> DeviceStatRead | None:
    # OSS has no stable per-parameter-reading id; detail-by-id is unsupported.
    raise AdapterNotMapped("device-stats detail by id (no stable OSS id)")


# --------------------------------------------------------------------------
# other-device-readings  (no OSS source)
# --------------------------------------------------------------------------

def list_other_device_readings(db: Session, *, page: int, page_size: int, **filters):
    raise AdapterNotMapped("other-device-readings (no third-party meter table in OSS)")


def get_other_device_reading(db: Session, reading_id: int):
    raise AdapterNotMapped("other-device-readings (no third-party meter table in OSS)")
