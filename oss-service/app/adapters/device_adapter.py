"""OSS -> contract adapters for devices and device types.

Source: `insp_device` (+ `insp_device_health`, `insp_device_state(_type)`).
All queries are read-only, parameterised SQLAlchemy Core over the explicit
tables in `app/db/tables.py`.

Compatibility decisions (confirmed, documented in docs/DESIGN_AND_READINESS.md):
  * OSS has no device-type table: `device_type` is free text. We derive a
    stable registry (ordinal id over DISTINCT names) and map a short code from
    the known families. `device_type` int on a device is that ordinal.
  * OSS is site/customer-scoped with no room/amenity: `amenity_id` has no
    source (null) and `facility_id` <- `site_id` (currently null on all rows).
    Filtering devices by amenity/facility is therefore unsupported -> 503.
  * Fields with no OSS source (mfg_date, firmware target, power/op flags, the
    smallint soft-delete `status`) are served as null, never fabricated.
"""

from __future__ import annotations

import uuid

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.adapters.base import AdapterNotMapped
from app.db.tables import (
    insp_device,
    insp_device_health,
    insp_device_state,
    insp_device_state_type,
)
from app.schemas.device import (
    DeviceDetail,
    DeviceHealthRead,
    DeviceHealthSample,
    DeviceRead,
    DeviceRef,
    DeviceTypeDetail,
    DeviceTypeRead,
)

D = insp_device
H = insp_device_health
S = insp_device_state
ST = insp_device_state_type

def _health_label(value) -> str | None:
    """Health status returned AS STORED. OSS has no health-status lookup table,
    so the raw code is surfaced rather than relabelled with an invented meaning.
    If the business later confirms a mapping, apply it via configuration."""
    return None if value is None else str(value)


def _short_code(name: str | None) -> str | None:
    """OSS has NO device short-code source. Returned as null rather than
    fabricated from a hardcoded name->code table."""
    return None


# --------------------------------------------------------------------------
# Device types (derived registry)
# --------------------------------------------------------------------------

def _type_registry(db: Session) -> list[dict]:
    """Stable ordinal registry over DISTINCT non-null device_type names."""
    names = db.execute(
        select(distinct(D.c.device_type))
        .where(D.c.device_type.is_not(None))
        .order_by(D.c.device_type)
    ).scalars().all()
    return [
        {"id": i + 1, "name": n, "device_short_code": _short_code(n)}
        for i, n in enumerate(names)
    ]


def _type_id_by_name(registry: list[dict]) -> dict[str, int]:
    return {r["name"]: r["id"] for r in registry}


def list_device_types(db: Session, *, page: int, page_size: int) -> tuple[list[DeviceTypeRead], int]:
    registry = _type_registry(db)
    total = len(registry)
    start = (page - 1) * page_size
    page_rows = registry[start:start + page_size]
    return [DeviceTypeRead(**r) for r in page_rows], total


def get_device_type(db: Session, type_id: int) -> DeviceTypeDetail | None:
    registry = _type_registry(db)
    match = next((r for r in registry if r["id"] == type_id), None)
    if match is None:
        return None
    device_count = db.execute(
        select(func.count()).select_from(D).where(D.c.device_type == match["name"])
    ).scalar_one()
    firmware_count = db.execute(
        select(func.count(distinct(D.c.firmware_version)))
        .where(D.c.device_type == match["name"], D.c.firmware_version.is_not(None))
    ).scalar_one()
    return DeviceTypeDetail(
        **match, device_count=device_count, firmware_count=firmware_count
    )


# --------------------------------------------------------------------------
# Latest-health / latest-state (batched; DISTINCT ON avoids N+1)
# --------------------------------------------------------------------------

def _latest_health(db: Session, device_uids: list[str]) -> dict[str, dict]:
    """Latest health per device_uid. `insp_device_health.device_id` is always
    NULL in OSS, so health is linked by `device_uid` (verified)."""
    uids = [u for u in device_uids if u]
    if not uids:
        return {}
    ts = func.coalesce(H.c.recorded_at, H.c.time)
    rows = db.execute(
        select(H.c.device_uid, H.c.health_status, H.c.temperature, ts.label("ts"))
        .where(H.c.device_uid.in_(uids))
        .distinct(H.c.device_uid)
        .order_by(H.c.device_uid, ts.desc())
    ).all()
    return {
        r.device_uid: {
            "health_status": _health_label(r.health_status),
            "temperature": r.temperature,
            "last_reported_on": r.ts,
        }
        for r in rows
    }


def _latest_state(db: Session, device_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not device_ids:
        return {}
    rows = db.execute(
        select(S.c.device_id, ST.c.device_state_name)
        .select_from(S.join(ST, ST.c.device_state_type_id == S.c.device_state_type_id))
        .where(S.c.device_id.in_(device_ids))
        .distinct(S.c.device_id)
        .order_by(S.c.device_id, S.c.state_effective_dtm_utc.desc())
    ).all()
    return {r.device_id: r.device_state_name for r in rows}


def _to_device_read(row, type_ids: dict[str, int], health: dict, state: dict) -> DeviceRead:
    h = health.get(row.device_uid, {})
    return DeviceRead(
        id=row.device_id,
        device_uid=row.device_uid,
        device_name=row.device_name,
        appliance_name=row.appliance,
        part_number=row.model_number,
        model=row.model,
        manufacturer_name=row.manufacturer,
        mfg_date=None,            # no OSS source (documented)
        installed_on=None,        # no OSS source
        device_type=type_ids.get(row.device_type),
        device_type_name=row.device_type,
        device_short_code=_short_code(row.device_type),
        facility_id=row.site_id,  # site = facility (currently null in OSS data)
        amenity_id=None,          # OSS has no room/amenity
        parent_device_id=row.parent_device_id,
        health_status=h.get("health_status"),
        device_config_status=state.get(row.device_id),  # OSS lifecycle name
        device_temperature=h.get("temperature"),
        is_power_off=None,
        operational_mode=None,
        is_other_device=None,
        status=None,              # OSS `status` is text, not the smallint soft-delete
        current_firmware=row.firmware_version,
        created_on=row.created_dtm_utc,
        updated_on=row.updated_dtm_utc,
    )


# --------------------------------------------------------------------------
# Devices
# --------------------------------------------------------------------------

_UNSUPPORTED_FILTERS = ("amenity_id", "facility_id", "building_id", "floor_id")


def _apply_filters(stmt, registry: list[dict], filters: dict):
    for key in _UNSUPPORTED_FILTERS:
        if filters.get(key):
            # OSS has no room/facility linkage; refuse rather than mislead.
            raise AdapterNotMapped("devices filtered by amenity/facility (no OSS linkage)")
    if filters.get("device_ids"):
        # HMS owns the room<->device mapping; it resolves a room (or floor,
        # building, facility) to OSS device ids and asks for exactly those.
        stmt = stmt.where(D.c.device_id.in_(filters["device_ids"]))
    if filters.get("device_type"):
        val = filters["device_type"]
        # Accept either the type name or the derived ordinal id.
        name = val
        if str(val).isdigit():
            name = next((r["name"] for r in registry if r["id"] == int(val)), None)
        stmt = stmt.where(D.c.device_type == name)
    if filters.get("node_type"):
        stmt = stmt.where(D.c.node_type == filters["node_type"])
    if filters.get("status"):
        stmt = stmt.where(D.c.status == filters["status"])
    if filters.get("parent_device_id"):
        stmt = stmt.where(D.c.parent_device_id == filters["parent_device_id"])
    q = filters.get("q")
    if q and str(q).strip():
        term = f"%{str(q).strip()}%"
        stmt = stmt.where(
            D.c.device_uid.ilike(term)
            | D.c.device_name.ilike(term)
            | D.c.serial_number.ilike(term)
        )
    return stmt


def list_devices(db: Session, *, page: int, page_size: int, **filters) -> tuple[list[DeviceRead], int]:
    registry = _type_registry(db)
    base = _apply_filters(select(D), registry, filters)

    total = db.execute(
        select(func.count()).select_from(base.order_by(None).subquery())
    ).scalar_one()

    rows = db.execute(
        base.order_by(D.c.device_name, D.c.device_id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    ids = [r.device_id for r in rows]
    uids = [r.device_uid for r in rows]
    health = _latest_health(db, uids)
    state = _latest_state(db, ids)
    type_ids = _type_id_by_name(registry)
    return [_to_device_read(r, type_ids, health, state) for r in rows], total


def _device_ref(row) -> DeviceRef:
    registry_name = row.device_type
    return DeviceRef(
        id=row.device_id,
        device_uid=row.device_uid,
        device_name=row.device_name,
        device_type=None,  # ref is lightweight; full type id resolved on detail rows
        device_type_name=registry_name,
    )


def get_device(db: Session, device_id: uuid.UUID) -> DeviceDetail | None:
    row = db.execute(select(D).where(D.c.device_id == device_id)).one_or_none()
    if row is None:
        return None
    registry = _type_registry(db)
    type_ids = _type_id_by_name(registry)
    health = _latest_health(db, [row.device_uid])
    state = _latest_state(db, [device_id])
    base = _to_device_read(row, type_ids, health, state)

    parent = None
    if row.parent_device_id is not None:
        prow = db.execute(
            select(D).where(D.c.device_id == row.parent_device_id)
        ).one_or_none()
        parent = _device_ref(prow) if prow is not None else None

    child_rows = db.execute(
        select(D).where(D.c.parent_device_id == device_id).order_by(D.c.device_name)
    ).all()
    children = [_device_ref(c) for c in child_rows]

    return DeviceDetail(
        **base.model_dump(),
        parent_device=parent,
        child_devices=children,
        child_count=len(children),
    )


def get_device_health(db: Session, device_id: uuid.UUID, *, sample_limit: int = 20) -> DeviceHealthRead | None:
    drow = db.execute(select(D).where(D.c.device_id == device_id)).one_or_none()
    if drow is None:
        return None

    # Health links by device_uid (insp_device_health.device_id is always NULL).
    uid = drow.device_uid
    sample_count = db.execute(
        select(func.count()).select_from(H).where(H.c.device_uid == uid)
    ).scalar_one()

    ts = func.coalesce(H.c.recorded_at, H.c.time)
    sample_rows = db.execute(
        select(H.c.health_status, H.c.temperature, ts.label("ts"))
        .where(H.c.device_uid == uid)
        .order_by(ts.desc())
        .limit(sample_limit)
    ).all()
    recent = [
        DeviceHealthSample(
            id=i + 1,
            device_health_status=_health_label(r.health_status),
            device_temperature=r.temperature,
            created_on=r.ts,
        )
        for i, r in enumerate(sample_rows)
    ]
    latest = _latest_health(db, [uid]).get(uid, {})
    state = _latest_state(db, [device_id]).get(device_id)

    return DeviceHealthRead(
        device_id=drow.device_id,
        device_uid=drow.device_uid,
        device_name=drow.device_name,
        device_type_name=drow.device_type,
        health_status=latest.get("health_status"),
        device_config_status=state,
        device_temperature=latest.get("temperature"),
        is_power_off=None,
        operational_mode=None,
        last_reported_on=latest.get("last_reported_on"),
        health_sample_count=sample_count,
        recent_samples=recent,
        battery_cycles=[],       # no OSS battery-cycle source
        operation_history=[],    # no OSS operation-percentage source
    )
