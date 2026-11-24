"""Translate device types between BSS ids and OSS names.

THE PROBLEM
-----------
`device_type.id` in the BSS MySQL is a real primary key in insertion order.
OSS has no device-type table at all: its adapter derives a registry by taking
`DISTINCT insp_device.device_type`, sorting alphabetically and numbering from
1. The two orderings disagree::

    id   BSS (device_type.id)      OSS (derived ordinal)
     1   Intellihub                AirQ
     2   AirQ                      IntelliHub
     3   Mikos                     Kleio
     4   Kleio                     Mikos

Worse, the OSS number is POSITIONAL, not an identity: adding one device type in
FleetXplorer renumbers every type after it alphabetically. So no fixed id->id
mapping can stay correct, and none is attempted here.

THE RULE
--------
**Name is the only stable key.** Everything below matches on the name, folded
with `casefold()` because the two systems spell it differently ("Intellihub"
vs "IntelliHub"). Ids are translated only as a derived consequence of a name
match.

WHAT THIS PRESERVES
-------------------
The frontend keeps using BSS `device_type.id` exactly as it does today --
filter values, stored selections and `device_short_code` are unchanged. The
translation happens entirely inside the OSS dispatch layer:

    request   frontend sends BSS id  ->  resolved to its BSS name  ->  sent to OSS
    response  OSS returns its own id  ->  matched by name  ->  rewritten to BSS id

No table is created, altered or dropped, and no row is written. The BSS
`device_type` table is read as the naming authority it already is.

A type present in OSS but absent from BSS keeps the name OSS reported and
carries a null id rather than being dropped or given an invented id -- the
device is real and must still appear.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeviceType

#: Response keys holding a device-type id / name, as they appear across the
#: device and telemetry contracts.
_ID_KEYS = ("device_type", "device_type_id")
_NAME_KEYS = ("device_type_name",)


@dataclass(frozen=True)
class BssType:
    id: int
    name: str
    short_code: str | None


def _bss_types(db: Session) -> list[BssType]:
    rows = db.execute(
        select(DeviceType.id, DeviceType.name, DeviceType.device_short_code)
    ).all()
    return [BssType(id=r[0], name=r[1], short_code=r[2]) for r in rows]


def by_name(db: Session) -> dict[str, BssType]:
    """BSS types keyed by casefolded name."""
    return {t.name.casefold(): t for t in _bss_types(db) if t.name}


def by_id(db: Session) -> dict[int, BssType]:
    return {t.id: t for t in _bss_types(db)}


def name_for_bss_id(db: Session, value: str | int) -> str | None:
    """The BSS type NAME for a BSS id, for forwarding to OSS.

    Returns None when `value` is not a known BSS id, so the caller can forward
    it untouched rather than silently dropping a filter it did not understand.
    """
    try:
        type_id = int(value)
    except (TypeError, ValueError):
        return None
    found = by_id(db).get(type_id)
    return found.name if found else None


def apply_to_item(item: dict, names: dict[str, BssType]) -> dict:
    """Rewrite one OSS item's device-type id/name/short_code to BSS values.

    Matching is by `device_type_name`, which OSS always sends alongside its
    ordinal; the ordinal itself is never used to look anything up.
    """
    if not isinstance(item, dict):
        return item

    raw_name = next(
        (item[k] for k in _NAME_KEYS if isinstance(item.get(k), str)), None
    )
    if not raw_name:
        return item

    match = names.get(raw_name.casefold())
    if match is None:
        # Present in OSS, absent from BSS. Keep OSS's name, drop the ordinal:
        # a positional number would be read as a BSS id and point at the wrong
        # type. Null says "unknown here", which is true.
        for key in _ID_KEYS:
            if key in item:
                item[key] = None
        return item

    for key in _ID_KEYS:
        if key in item:
            item[key] = match.id
    for key in _NAME_KEYS:
        if key in item:
            item[key] = match.name  # canonical BSS spelling
    if "device_short_code" in item and item.get("device_short_code") is None:
        # OSS has no short-code source and sends null; BSS does. Filling it
        # keeps the column populated on screens exactly as it is today.
        item["device_short_code"] = match.short_code
    return item


def apply_to_body(db: Session, body):
    """Rewrite device-type fields anywhere in an OSS response body."""
    names = by_name(db)

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if isinstance(node, dict):
            node = apply_to_item(node, names)
            return {k: walk(v) for k, v in node.items()}
        return node

    return walk(body)


def device_types_as_bss(db: Session, body):
    """Rewrite a `/device-types` page so ids are BSS ids.

    The derived OSS `id` is replaced by the BSS id for the same name, so the
    frontend's existing type filter values keep working untouched.
    """
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        return body
    names = by_name(db)
    for item in body["items"]:
        if not isinstance(item, dict):
            continue
        raw = item.get("name")
        match = names.get(raw.casefold()) if isinstance(raw, str) else None
        if match is None:
            item["id"] = None
            continue
        item["id"] = match.id
        item["name"] = match.name
        if item.get("device_short_code") is None:
            item["device_short_code"] = match.short_code
    body["items"].sort(key=lambda i: (i.get("id") is None, i.get("id") or 0))
    return body
