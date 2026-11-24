"""The four Caleido At Work operational KPIs, computed from live records.

WHY THIS EXISTS
---------------
The widget used to read `daily_dual_data_point` -- a table of pre-computed
daily snapshots. That table stopped being written on 2026-08-17, so with the
Today filter the window contained no rows and the card rendered "No daily KPI
data points recorded". The data was not missing; the SNAPSHOT was stale.

This module computes the same four indicators from the records that already
exist, so the figures cannot go stale while the business data is current.
`daily_dual_data_point` is left untouched and its endpoint still works -- this
is an additional read path, not a replacement of anything.

NO NEW TABLES, NO NEW BUSINESS RULES. Every figure below comes from tables the
platform already owns, through the statuses the platform already defines:

    smart_rooms_online    room_device_map (BSS)  x  OSS device liveness
    service_request_status  service_request x service_status (BSS)
    rooms_for_checkout    stay x room_allocation (BSS)
    pending_bookings      stay (BSS)

OSS is reached ONLY through `oss_client`, the existing proxy. Nothing here
opens a PostgreSQL connection, and `insp_iot` is never addressed directly.

LIVE vs PERIOD
--------------
Each KPI declares its own `semantics`, because the Today/Week/Month selector
must not change what an indicator MEANS:

* `live`   -- a current operational state. Smart Rooms Online is connectivity
              right now; it does not become a historical average because the
              user picked Month.
* `period` -- activity inside the selected window, filtered on the date column
              that actually carries that activity.

AVAILABLE vs ZERO
-----------------
`available=False` means the figure cannot be computed at all (the inputs do
not exist). A genuine zero -- no service requests raised today -- is
`available=True` with `numerator=0`. The two are never collapsed, so the card
can tell "nothing happened" apart from "we cannot know".
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    RoomAllocation,
    RoomDeviceMap,
    ServiceRequest,
    ServiceStatus,
    Stay,
)
from app.services import oss_client

logger = logging.getLogger("hms.caleido")

#: Window sizes in days, matching the selector the dashboard already shows.
RANGE_DAYS: dict[str, int] = {"today": 0, "week": 6, "month": 29}

#: Stay statuses that mean a guest currently holds the room. Taken from
#: `enums.stay_status`; the same set `services/occupancy.py` treats as in-house
#: plus the checkout-initiated states, so the two screens cannot disagree.
OCCUPYING_STATUSES = (
    "active",
    "checkout pending",
    "checkout accepted",
    "checkout rejected",
)

#: `service_status` primary keys, as used by `services/service.py`'s existing
#: tracking summary. Referenced rather than re-derived so one definition of
#: "completed" serves both screens.
SR_PENDING, SR_ASSIGNED, SR_IN_PROGRESS, SR_COMPLETED, SR_CANCELED = 1, 2, 3, 4, 5

#: How recently an OSS device must have reported to count as ONLINE NOW.
#:
#: The OSS device payload carries `health_status`, but the OSS adapter
#: deliberately refuses to interpret it -- "OSS has no health-status lookup
#: table, so the raw code is surfaced rather than relabelled with an invented
#: meaning" (oss-service/app/adapters/device_adapter.py::_health_label).
#: Treating `health_status == "1"` as online would be exactly that invention,
#: and it would also call a device online on a reading that is weeks old.
#:
#: Reporting recency is a real connectivity signal that needs no lookup table:
#: a device that has reported inside this window is demonstrably talking to
#: FleetXplorer. Widen or narrow it here if the business defines the threshold
#: differently; it is a tuning constant, not a business rule invented below.
ONLINE_WITHIN_MINUTES = 15


def _window(range_key: str, today: date) -> tuple[date, date, int]:
    """(period_start, period_end, days) for a selector key. Backward-looking:
    `period_end` is today and `period_start` is `days` before it, which is the
    window the existing dashboard selector has always described."""
    days = RANGE_DAYS[range_key]
    return today - timedelta(days=days), today, days


def _kpi(
    key: str,
    label: str,
    semantics: str,
    source: str,
    *,
    available: bool = True,
    unavailable_reason: str | None = None,
    numerator: int | None = None,
    denominator: int | None = None,
    count: int | None = None,
    detail: str = "",
    window_from: date | None = None,
    window_to: date | None = None,
) -> dict[str, Any]:
    """Assemble one KPI row. The percentage is computed here from numerator and
    denominator and nowhere else; when the denominator is 0 it stays None
    rather than becoming a misleading 0 %."""
    percentage: int | None = None
    if available and numerator is not None and denominator:
        # floor(x + 0.5): Python's round() is banker's rounding, which would
        # make round(2.5) == 2 and disagree with the stored-snapshot widget
        # this replaces. Percentages here are never negative.
        percentage = int((numerator / denominator) * 100 + 0.5)
    return {
        "key": key,
        "label": label,
        "semantics": semantics,
        "source": source,
        "available": available,
        "unavailable_reason": unavailable_reason,
        "numerator": numerator,
        "denominator": denominator,
        "percentage": percentage,
        "count": count,
        "detail": detail,
        "window_from": window_from,
        "window_to": window_to,
    }


# ---------------------------------------------------------------------------
# KPI 1 -- Smart Rooms Online   (BSS room_device_map  x  OSS liveness)
# ---------------------------------------------------------------------------


def _smart_rooms_online(db: Session, facility_id: uuid.UUID | None) -> dict[str, Any]:
    """Unique ROOMS whose mapped OSS devices are reporting right now.

    Rooms, never devices: two devices in one room are one smart room. A room
    with no mapping is not counted in either side of the ratio, because HMS has
    no basis to call it smart.
    """
    mapped = select(
        RoomDeviceMap.amenity_id, RoomDeviceMap.oss_device_id
    ).join(Amenity, Amenity.id == RoomDeviceMap.amenity_id)
    if facility_id:
        mapped = mapped.where(Amenity.facility_id == facility_id)
    rows = db.execute(mapped).all()

    rooms_total = len({r.amenity_id for r in rows})
    if rooms_total == 0:
        # The mapping table is empty. Inventing a denominator here -- "6 OSS
        # devices, so 6 smart rooms" -- would be fabricating a room count out
        # of a device count. Report it as unknown instead.
        return _kpi(
            "smart_rooms_online", "Smart Rooms Online", "live", "BSS+OSS",
            available=False,
            unavailable_reason=(
                "No device-to-room mappings exist in room_device_map, so the "
                "number of smart rooms is unknown. Assign devices to rooms in "
                "Config -> Room Devices."
            ),
            detail="Device-to-room mapping required",
        )

    device_to_rooms: dict[str, set[uuid.UUID]] = {}
    for row in rows:
        device_to_rooms.setdefault(str(row.oss_device_id), set()).add(row.amenity_id)

    online_rooms: set[uuid.UUID] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WITHIN_MINUTES)
    unreachable = 0

    for device_id, room_ids in device_to_rooms.items():
        try:
            status_code, body = oss_client.forward("GET", f"/devices/{device_id}/health")
        except oss_client.OssUnavailable:
            unreachable += 1
            continue
        if status_code != 200 or not isinstance(body, dict):
            continue
        reported = body.get("last_reported_on")
        if not reported:
            continue
        try:
            seen = datetime.fromisoformat(str(reported))
        except ValueError:
            continue
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        if seen >= cutoff:
            online_rooms.update(room_ids)

    if unreachable and not online_rooms:
        # Every mapped device was unreachable -- that is an OSS outage, not a
        # building full of offline rooms. Saying 0 % would be a lie.
        return _kpi(
            "smart_rooms_online", "Smart Rooms Online", "live", "BSS+OSS",
            available=False,
            unavailable_reason="OSS device service is unreachable; live connectivity is unknown.",
            detail="OSS unavailable",
        )

    online = len(online_rooms)
    return _kpi(
        "smart_rooms_online", "Smart Rooms Online", "live", "BSS+OSS",
        numerator=online, denominator=rooms_total, count=online,
        detail=f"{online} of {rooms_total} mapped rooms reporting",
    )


# ---------------------------------------------------------------------------
# KPI 2 -- Service Request Status   (BSS)
# ---------------------------------------------------------------------------


def _service_request_status(
    db: Session, facility_id: uuid.UUID | None, start: date, end: date
) -> dict[str, Any]:
    """Completed share of the service requests RAISED in the window.

    The status ids are the ones `services/service.py` already uses for the
    Service Tracking summary, so this cannot drift from that screen. Scoped by
    `created_on`, the column that records when the request was raised.
    """
    stmt = select(
        func.count(ServiceRequest.id),
        func.sum(func.if_(ServiceRequest.status == SR_COMPLETED, 1, 0)),
        func.sum(func.if_(ServiceRequest.status == SR_CANCELED, 1, 0)),
    ).where(func.date(ServiceRequest.created_on).between(start, end))
    if facility_id:
        stmt = stmt.where(ServiceRequest.facility_id == facility_id)
    total, completed, canceled = db.execute(stmt).one()
    total = int(total or 0)
    completed = int(completed or 0)
    canceled = int(canceled or 0)

    if total == 0:
        # A real, defensible zero: nothing was raised in this window.
        return _kpi(
            "service_request_status", "Service Request Status", "period", "BSS",
            numerator=0, denominator=0, count=0,
            detail="No requests raised in this period",
            window_from=start, window_to=end,
        )

    open_count = total - completed - canceled
    return _kpi(
        "service_request_status", "Service Request Status", "period", "BSS",
        numerator=completed, denominator=total, count=open_count,
        detail=f"{completed} completed of {total} raised · {open_count} open",
        window_from=start, window_to=end,
    )


# ---------------------------------------------------------------------------
# KPI 3 -- Rooms For Check-Out   (BSS)
# ---------------------------------------------------------------------------


def _rooms_for_checkout(
    db: Session, facility_id: uuid.UUID | None, today: date, days: int
) -> dict[str, Any]:
    """Occupied rooms whose stay is due to check out by the end of the window.

    Forward-looking on purpose: "rooms for check-out" is a workload that lies
    ahead, so the window runs from today to `today + days` rather than into the
    past. A stay whose expected checkout has already passed is still awaiting
    checkout, so it stays in the count -- dropping it would hide exactly the
    rooms housekeeping most needs to see.

    Cancelled and completed stays are excluded by construction: neither
    `cancelled` nor `checked out` is in OCCUPYING_STATUSES.
    """
    due_by = today + timedelta(days=days)

    occupied = (
        select(func.count(func.distinct(RoomAllocation.room_id)))
        .select_from(RoomAllocation)
        .join(Stay, Stay.id == RoomAllocation.stay_id)
        .where(Stay.status.in_(OCCUPYING_STATUSES))
    )
    due = occupied.where(func.date(Stay.expected_checkout_time) <= due_by)

    if facility_id:
        rooms_here = select(Amenity.id).where(Amenity.facility_id == facility_id)
        occupied = occupied.where(RoomAllocation.room_id.in_(rooms_here))
        due = due.where(RoomAllocation.room_id.in_(rooms_here))

    total_occupied = int(db.execute(occupied).scalar_one() or 0)
    rooms_due = int(db.execute(due).scalar_one() or 0)

    if total_occupied == 0:
        return _kpi(
            "rooms_for_checkout", "Rooms For Check-Out", "live", "BSS",
            numerator=0, denominator=0, count=0,
            detail="No rooms currently occupied",
            window_from=today, window_to=due_by,
        )

    return _kpi(
        "rooms_for_checkout", "Rooms For Check-Out", "live", "BSS",
        numerator=rooms_due, denominator=total_occupied, count=rooms_due,
        detail=f"{rooms_due} of {total_occupied} occupied rooms due by {due_by:%d %b}",
        window_from=today, window_to=due_by,
    )


# ---------------------------------------------------------------------------
# KPI 4 -- Pending Bookings   (BSS)
# ---------------------------------------------------------------------------


def _pending_bookings(
    db: Session, facility_id: uuid.UUID | None, start: date, end: date
) -> dict[str, Any]:
    """Stays still `pending` among those arriving in the window.

    `pending` is the stay_status the schema already defines for a reservation
    that has not been checked in; no new status is introduced. Scoped by
    `expected_checkin_time`, the column that says when the booking is for.
    Cancelled, active and checked-out stays are not pending and are excluded.
    """
    arriving = select(func.count(Stay.id)).where(
        func.date(Stay.expected_checkin_time).between(start, end)
    )
    pending = arriving.where(Stay.status == "pending")

    if facility_id:
        rooms_here = select(RoomAllocation.stay_id).join(
            Amenity, Amenity.id == RoomAllocation.room_id
        ).where(Amenity.facility_id == facility_id)
        arriving = arriving.where(Stay.id.in_(rooms_here))
        pending = pending.where(Stay.id.in_(rooms_here))

    total = int(db.execute(arriving).scalar_one() or 0)
    pending_count = int(db.execute(pending).scalar_one() or 0)

    if total == 0:
        return _kpi(
            "pending_bookings", "Pending Bookings", "period", "BSS",
            numerator=0, denominator=0, count=0,
            detail="No arrivals in this period",
            window_from=start, window_to=end,
        )

    return _kpi(
        "pending_bookings", "Pending Bookings", "period", "BSS",
        numerator=pending_count, denominator=total, count=pending_count,
        detail=f"{pending_count} pending of {total} arrivals",
        window_from=start, window_to=end,
    )


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def operational_kpis(
    db: Session,
    *,
    range_key: str = "today",
    facility_id: uuid.UUID | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """The four Caleido At Work rings, in display order.

    `today` is injectable so the suite can pin a date; it defaults to the
    server's current date and is never hardcoded.
    """
    key = range_key.lower()
    if key not in RANGE_DAYS:
        raise ValueError(f"unknown range {range_key!r}")
    anchor = today or date.today()
    start, end, days = _window(key, anchor)

    return {
        "range": key,
        "period_from": start,
        "period_to": end,
        "generated_at": datetime.now(timezone.utc),
        "kpis": [
            _smart_rooms_online(db, facility_id),
            _service_request_status(db, facility_id, start, end),
            _rooms_for_checkout(db, facility_id, anchor, days),
            _pending_bookings(db, facility_id, start, end),
        ],
    }
