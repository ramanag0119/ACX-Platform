"""The nine HMS reports.

This module adds NO SQL of its own. Every report delegates to the read service
that already backs the corresponding screen -- `occupancy.list_occupancy`,
`stay.list_stays`, `service.list_service_requests`,
`maintenance.list_maintenance_requests`, `alert.list_alerts`,
`energy.list_energy_stats` and `access.list_users` -- so a report can never
disagree with the module it reports on, and a row created, edited or soft
deleted through an existing module shows up here on the next request.

Each report is one `ReportDef`: the columns it exposes, the filters it accepts,
and a fetch that maps this layer's filter names onto that service's keyword
arguments. The column list is served to the frontend (GET /reports/{key}) AND
used to write the spreadsheet (GET /reports/{key}/export.xlsx), which is what
keeps the table on screen and the downloaded file identical.

Only fields that genuinely exist on those payloads appear below; nothing is
invented, and no report carries a metric the schema cannot answer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Iterable, Sequence

from sqlalchemy.orm import Session

from app.services import access, alert, energy, maintenance, occupancy, service, stay

# --- column value shaping ---------------------------------------------------

#: How a value should be rendered. The frontend right-aligns numbers and the
#: spreadsheet writer applies a matching cell format.
ColumnKind = str  # "text" | "number" | "date" | "datetime" | "boolean"


@dataclass(frozen=True)
class ReportColumn:
    """One column. `key` is the field on the row dict this layer produces."""

    key: str
    header: str
    kind: ColumnKind = "text"
    #: Spreadsheet column width in characters.
    width: int = 18


@dataclass(frozen=True)
class ReportFilter:
    """A filter this report accepts, described so the UI can render it.

    `kind` also decides how the raw query value is coerced, which is what lets
    one endpoint serve reports whose same-named filter has a different type --
    `status` is a `service_status.id` for tickets but the `stay.status` enum
    label for bookings.
    """

    name: str
    label: str
    #: "text" | "date" | "select" | "boolean" | "int" | "uuid"
    kind: str = "text"
    #: For `select`, where the options come from -- an existing list endpoint.
    options_from: str | None = None
    #: Coercion applied to the raw value: "int", "uuid", "bool" or None (text).
    value_type: str | None = None


@dataclass(frozen=True)
class ReportDef:
    key: str
    title: str
    #: Which module/table the numbers come from, shown in the report header.
    source: str
    columns: Sequence[ReportColumn]
    filters: Sequence[ReportFilter]
    fetch: Callable[..., tuple[list[dict], int]]
    description: str = ""


def _name(person: Any) -> str | None:
    """A `UserRef`-shaped dict -> its display name."""
    if not person:
        return None
    if isinstance(person, dict):
        return person.get("name") or person.get("user_name")
    return getattr(person, "name", None)


def _join(values: Iterable[Any], key: str | None = None) -> str:
    out = []
    for v in values or []:
        text = (v.get(key) if key and isinstance(v, dict) else v)
        if text:
            out.append(str(text))
    return ", ".join(out)


# --- per-report fetches -----------------------------------------------------
# Each takes the report filters and forwards them to the existing service.
# `page`/`page_size` are always passed through so exports and the on-screen
# table share one pagination contract.


def _occupancy_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    rows, total = occupancy.list_occupancy(
        db, page=page, page_size=page_size,
        facility_id=f.get("facility_id"), building_id=f.get("building_id"),
        floor_id=f.get("floor_id"), amenity_type_id=f.get("amenity_type_id"),
        amenity_category=f.get("amenity_category"), status=f.get("status"),
        condition_id=f.get("condition_id"), is_occupied=f.get("is_occupied"),
    )
    out = []
    for r in rows:
        d = dict(r)
        current = d.get("current_stay") or {}
        out.append({
            **d,
            "conditions_text": _join(d.get("conditions") or [], "name"),
            # `current_stay` is present only while a stay holds the room.
            "stay_ref": current.get("internal_stay_ref_number") if current else None,
            "guest_name": _name(current.get("booker")) if current else None,
        })
    return out, total


def _room_status_rows(db: Session, **kw) -> tuple[list[dict], int]:
    # Same projection as Occupancy -- `amenity` + `amenity_status` +
    # `amenity_condition` is the only place room state lives -- but reported on
    # state and serviceability rather than who is in the room.
    return _occupancy_rows(db, **kw)


def _employee_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    rows, total = access.list_users(
        db, page=page, page_size=page_size,
        facility_id=f.get("facility_id"), role_id=f.get("role_id"),
        department_id=f.get("department_id"), job_function_id=f.get("job_function_id"),
        # An employee report is staff only; guests are not employees.
        is_staff=1,
    )
    out = []
    for r in rows:
        d = dict(r)
        full = " ".join(x for x in (d.get("first_name"), d.get("last_name")) if x)
        out.append({
            **d,
            "full_name": full or d.get("user_name"),
            # `date_of_termination` set = no longer serving.
            "employment_status": "Terminated" if d.get("date_of_termination") else "Active",
        })
    return out, total


def _booking_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    rows, total = stay.list_stays(
        db, page=page, page_size=page_size,
        status=f.get("status"), request_source=f.get("request_source"),
        document_approval_status=f.get("document_approval_status"),
        facility_id=f.get("facility_id"), room_id=f.get("room_id"),
        building_id=f.get("building_id"), floor_id=f.get("floor_id"),
        is_checked_in=f.get("is_checked_in"), is_in_house=f.get("is_in_house"),
        expected_checkin_from=f.get("date_from"), expected_checkin_to=f.get("date_to"),
    )
    return [{**dict(r), "booker_name": _name(dict(r).get("booker"))} for r in rows], total


def _ticket_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    rows, total = service.list_service_requests(
        db, page=page, page_size=page_size,
        facility_id=f.get("facility_id"), service_type=f.get("service_type"),
        status=f.get("status"), category_id=f.get("category_id"),
        assigned_to=f.get("assigned_to"), amenity_id=f.get("amenity_id"),
        department_id=f.get("department_id"), request_source=f.get("request_source"),
        created_from=f.get("date_from"), created_to=f.get("date_to"),
    )
    out = []
    for r in rows:
        d = dict(r)
        out.append({**d,
                    "assignee_name": _name(d.get("assignee")),
                    "requester_name": _name(d.get("requester"))})
    return out, total


def _maintenance_rows(types: list[str]):
    """Housekeeping and Sanitization are both `maintenance_request`, split by
    `maintenance_request_type` -- one table with an enum, not two tables."""

    def fetch(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
        rows, total = maintenance.list_maintenance_requests(
            db, page=page, page_size=page_size,
            # A caller may narrow to one tab; otherwise the report's own set.
            request_type=f.get("request_type"),
            request_types=types,
            facility_id=f.get("facility_id"), department_id=f.get("department_id"),
            category_id=f.get("category_id"), request_status=f.get("status"),
            assigned_to=f.get("assigned_to"), amenity_id=f.get("amenity_id"),
            is_recurring=f.get("is_recurring"),
            start_date_from=f.get("date_from"), start_date_to=f.get("date_to"),
        )
        # Rooms and assignees live in the junction tables; the read service
        # returns the request row, so attach them the way the endpoint does.
        ids = [dict(r)["id"] for r in rows]
        rooms = maintenance.rooms_for(db, ids)
        assignees = maintenance.assignees_for(db, ids)
        out = []
        for r in rows:
            d = dict(r)
            out.append({
                **d,
                "rooms_text": _join(rooms.get(d["id"], []), "room_name"),
                "assignees_text": _join(
                    [{"n": _name(a)} for a in assignees.get(d["id"], [])], "n"
                ),
            })
        return out, total

    return fetch


def _alert_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    rows, total = alert.list_alerts(
        db, page=page, page_size=page_size,
        facility_id=f.get("facility_id"), device_id=f.get("device_id"),
        amenity_id=f.get("amenity_id"), alert_type=f.get("alert_type"),
        alert_severity=f.get("alert_severity"), device_type=f.get("device_type"),
        building_id=f.get("building_id"), floor_id=f.get("floor_id"),
        created_from=f.get("date_from"), created_to=f.get("date_to"),
    )
    out = []
    for r in rows:
        d = dict(r)
        data = d.get("alert_data")
        # `alert_data` is the reported payload -- keep it readable, not JSON.
        readable = ", ".join(f"{k}: {v}" for k, v in data.items()) if isinstance(data, dict) else None
        out.append({**d, "alert_data_text": readable})
    return out, total


def _energy_rows(db: Session, *, page: int, page_size: int, **f) -> tuple[list[dict], int]:
    # `energy_stat.hour` is hours-since-2000, not a timestamp, so a date filter
    # is converted the same way GET /energy-stats converts it.
    hour_from = energy.timestamp_to_hour(f["date_from"]) if f.get("date_from") else None
    hour_to = energy.timestamp_to_hour(f["date_to"]) if f.get("date_to") else None
    rows, total = energy.list_energy_stats(
        db, page=page, page_size=page_size,
        facility_id=f.get("facility_id"), amenity_id=f.get("amenity_id"),
        building_id=f.get("building_id"), floor_id=f.get("floor_id"),
        device_name=f.get("device_name"), hour_from=hour_from, hour_to=hour_to,
    )
    return [dict(r) for r in rows], total


# --- shared filter descriptors ---------------------------------------------

DATE_FROM = ReportFilter("date_from", "From Date", "date", None, "date")
DATE_TO = ReportFilter("date_to", "To Date", "date", None, "date")
FACILITY = ReportFilter("facility_id", "Facility", "select", "/facilities", "uuid")
BUILDING = ReportFilter("building_id", "Building", "select", "/buildings", "uuid")
FLOOR = ReportFilter("floor_id", "Floor", "select", "/floors", "uuid")
ROOM = ReportFilter("amenity_id", "Room No", "select", "/rooms", "uuid")
DEPARTMENT = ReportFilter("department_id", "Department", "select", "/departments", "uuid")


REPORTS: dict[str, ReportDef] = {
    "occupancy": ReportDef(
        key="occupancy",
        title="Occupancy Report",
        source="amenity, amenity_status, amenity_condition, stay",
        description=(
            "Room-by-room occupancy state. `amenity_status` is the stored state "
            "(Available, Occupied, Allotted, Unavailable); there is no "
            "occupancy date column, so this is a point-in-time position."
        ),
        columns=[
            ReportColumn("room_name", "Room No", width=12),
            ReportColumn("amenity_type_name", "Room Type"),
            ReportColumn("package_name", "Package"),
            ReportColumn("building_name", "Building", width=14),
            ReportColumn("floor_name", "Floor", width=12),
            ReportColumn("status_name", "Status", width=14),
            ReportColumn("stay_ref", "Stay Ref", width=18),
            ReportColumn("guest_name", "Guest", width=22),
            ReportColumn("allocation_count", "Allocations", "number", 12),
            ReportColumn("conditions_text", "Conditions", width=28),
        ],
        filters=[FACILITY, BUILDING, FLOOR,
                 ReportFilter("amenity_type_id", "Room Type", "select", "/amenity-types", "uuid"),
                 ReportFilter("status", "Status", "select", "/amenity-statuses", "int"),
                 ReportFilter("is_occupied", "Occupied only", "boolean", None, "bool")],
        fetch=_occupancy_rows,
    ),
    "employee": ReportDef(
        key="employee",
        title="Employee Report",
        source="app_user, department, job_function, user_role",
        description=(
            "Staff roster (`is_staff = 1`). `app_user` carries no per-day "
            "history, so this report has no date range -- it is the roster as "
            "it stands, with joining and termination dates per row."
        ),
        columns=[
            ReportColumn("emp_id", "Employee ID", width=14),
            ReportColumn("full_name", "Name", width=24),
            ReportColumn("user_name", "Username", width=18),
            ReportColumn("email", "Email", width=30),
            ReportColumn("phone_number", "Phone", width=18),
            ReportColumn("department_name", "Department", width=20),
            ReportColumn("job_function_name", "Job Function", width=20),
            ReportColumn("date_of_joining", "Date of Joining", "date", 18),
            ReportColumn("date_of_termination", "Date of Termination", "date", 20),
            ReportColumn("employment_status", "Status", width=14),
        ],
        filters=[FACILITY, DEPARTMENT,
                 ReportFilter("job_function_id", "Job Function", "select", "/job-functions", "uuid"),
                 ReportFilter("role_id", "Role", "select", "/roles", "uuid")],
        fetch=_employee_rows,
    ),
    "room-status": ReportDef(
        key="room-status",
        title="Room Status Report",
        source="amenity, amenity_status, amenity_condition",
        description=(
            "Serviceability of every room: stored status, reported conditions "
            "and the DND / power-save flags. Same tables as the Occupancy "
            "report -- room state lives in one place -- reported on condition "
            "rather than on who holds the room."
        ),
        columns=[
            ReportColumn("room_name", "Room No", width=12),
            ReportColumn("amenity_type_name", "Room Type"),
            ReportColumn("amenity_category", "Category", width=14),
            ReportColumn("building_name", "Building", width=14),
            ReportColumn("floor_name", "Floor", width=12),
            ReportColumn("status_name", "Status", width=14),
            ReportColumn("conditions_text", "Conditions", width=32),
            ReportColumn("is_dnd", "DND", "boolean", 10),
            ReportColumn("power_save_mode", "Power Save", "boolean", 12),
        ],
        filters=[FACILITY, BUILDING, FLOOR,
                 ReportFilter("amenity_type_id", "Room Type", "select", "/amenity-types", "uuid"),
                 ReportFilter("status", "Status", "select", "/amenity-statuses", "int"),
                 ReportFilter("condition_id", "Condition", "select", "/amenity-conditions", "int")],
        fetch=_room_status_rows,
    ),
    "booking": ReportDef(
        key="booking",
        title="Booking Report",
        source="stay, room_allocation, stay_occupant",
        description=(
            "Stays and their lifecycle. The date range filters EXPECTED "
            "check-in, which is the column `stay` orders on."
        ),
        columns=[
            ReportColumn("internal_stay_ref_number", "Booking Ref", width=18),
            ReportColumn("external_stay_ref_number", "External Ref", width=18),
            ReportColumn("booker_name", "Booked By", width=22),
            ReportColumn("status", "Status", width=16),
            ReportColumn("no_of_guests", "Guests", "number", 10),
            ReportColumn("room_count", "Rooms", "number", 10),
            ReportColumn("expected_checkin_time", "Expected Check-in", "datetime", 22),
            ReportColumn("expected_checkout_time", "Expected Check-out", "datetime", 22),
            ReportColumn("actual_checkin_time", "Actual Check-in", "datetime", 22),
            ReportColumn("actual_checkout_time", "Actual Check-out", "datetime", 22),
            ReportColumn("document_approval_status", "Documents", width=16),
            ReportColumn("request_source", "Source", width=14),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, BUILDING, FLOOR,
                 ReportFilter("status", "Stay Status", "text"),
                 ReportFilter("request_source", "Source", "text"),
                 ReportFilter("document_approval_status", "Document Status", "text"),
                 ReportFilter("is_in_house", "In house only", "boolean", None, "bool")],
        fetch=_booking_rows,
    ),
    "ticket": ReportDef(
        key="ticket",
        title="Ticket Report",
        source="service_request, service_type, service_status, service_category",
        description="Guest and internal service requests, filtered on `created_on`.",
        columns=[
            ReportColumn("ref_number", "Ticket Ref", width=18),
            ReportColumn("service_type_name", "Service Type", width=22),
            ReportColumn("category_name", "Category", width=20),
            ReportColumn("description", "Description", width=34),
            ReportColumn("amenity_name", "Room No", width=12),
            ReportColumn("department_name", "Department", width=18),
            ReportColumn("assignee_name", "Assigned To", width=22),
            ReportColumn("status_name", "Status", width=16),
            ReportColumn("request_source", "Source", width=12),
            ReportColumn("expected_date", "Expected", "datetime", 20),
            ReportColumn("completed_on", "Completed On", "datetime", 20),
            ReportColumn("created_on", "Created On", "datetime", 20),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, DEPARTMENT, ROOM,
                 ReportFilter("service_type", "Service Type", "select", "/service-types", "int"),
                 ReportFilter("status", "Status", "select", "/service-statuses", "int"),
                 ReportFilter("category_id", "Category", "select", "/service-categories", "uuid"),
                 ReportFilter("assigned_to", "Assigned To", "select", "/users", "uuid")],
        fetch=_ticket_rows,
    ),
    "housekeeping": ReportDef(
        key="housekeeping",
        title="Housekeeping Report",
        source="maintenance_request (scheduled, planned) + amenity / assignee links",
        description=(
            "Planned housekeeping work -- the `scheduled` and `planned` "
            "`maintenance_request_type` values. Sanitization is the third "
            "value and has its own report. Filtered on the start date."
        ),
        columns=[
            ReportColumn("maintenance_request_type", "Type", width=14),
            ReportColumn("category_name", "Service", width=22),
            ReportColumn("service_type_name", "Service Type", width=26),
            ReportColumn("department_name", "Department", width=20),
            ReportColumn("rooms_text", "Rooms", width=24),
            ReportColumn("assignees_text", "Assigned To", width=24),
            ReportColumn("maintenance_start_date", "Start Date", "date", 14),
            ReportColumn("maintenance_end_date", "End Date", "date", 14),
            ReportColumn("maintenance_start_time", "Start Time", "datetime", 20),
            ReportColumn("maintenance_end_time", "End Time", "datetime", 20),
            ReportColumn("is_recurring", "Recurring", "boolean", 12),
            ReportColumn("status_name", "Status", width=18),
            ReportColumn("completed_on", "Completed On", "datetime", 20),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, DEPARTMENT, ROOM,
                 ReportFilter("request_type", "Type", "select", "maintenance-types"),
                 ReportFilter("status", "Status", "select", "/service-statuses", "int"),
                 ReportFilter("assigned_to", "Assigned To", "select", "/users", "uuid"),
                 ReportFilter("is_recurring", "Recurring only", "boolean", None, "bool")],
        fetch=_maintenance_rows(["scheduled", "planned"]),
    ),
    "sanitization": ReportDef(
        key="sanitization",
        title="Sanitization Report",
        source="maintenance_request (disinfection) + amenity / assignee links",
        description=(
            "Disinfection schedules -- `maintenance_request_type = "
            "'disinfection'`, the Disinfection Schedule tab of Services "
            "Planning. Filtered on the start date."
        ),
        columns=[
            ReportColumn("category_name", "Sanitizer Service", width=24),
            ReportColumn("item_name", "Service Item", width=24),
            ReportColumn("service_type_name", "Service Type", width=28),
            ReportColumn("department_name", "Department", width=20),
            ReportColumn("rooms_text", "Rooms", width=24),
            ReportColumn("assignees_text", "Assigned To", width=24),
            ReportColumn("maintenance_start_date", "Date", "date", 14),
            ReportColumn("maintenance_start_time", "Start Time", "datetime", 20),
            ReportColumn("maintenance_end_time", "End Time", "datetime", 20),
            ReportColumn("is_recurring", "Recurring", "boolean", 12),
            ReportColumn("under_maintenance", "Under Maintenance", "boolean", 18),
            ReportColumn("status_name", "Status", width=18),
            ReportColumn("completed_on", "Completed On", "datetime", 20),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, DEPARTMENT, ROOM,
                 ReportFilter("status", "Status", "select", "/service-statuses", "int"),
                 ReportFilter("assigned_to", "Assigned To", "select", "/users", "uuid")],
        fetch=_maintenance_rows(["disinfection"]),
    ),
    "alert": ReportDef(
        key="alert",
        title="Alert Report",
        source="device_alert, alert_type, device, amenity",
        description=(
            "Alerts devices reported, filtered on `created_on`. An alert is a "
            "recorded fact and has no status of its own -- the lifecycle lives "
            "on the incident."
        ),
        columns=[
            ReportColumn("id", "Alert ID", "number", 10),
            ReportColumn("alert_type_name", "Alert Type", width=24),
            ReportColumn("alert_severity", "Severity", width=12),
            ReportColumn("device_uid", "Device UID", width=18),
            ReportColumn("device_name", "Device", width=16),
            ReportColumn("device_type_name", "Device Type", width=16),
            ReportColumn("amenity_name", "Room No", width=12),
            ReportColumn("building_name", "Building", width=14),
            ReportColumn("floor_name", "Floor", width=12),
            ReportColumn("alert_data_text", "Reported Values", width=34),
            ReportColumn("created_on", "Raised On", "datetime", 22),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, BUILDING, FLOOR, ROOM,
                 ReportFilter("alert_type", "Alert Type", "select", "/alert-types", "int"),
                 ReportFilter("alert_severity", "Severity", "text"),
                 ReportFilter("device_id", "Device", "select", "/devices", "uuid")],
        fetch=_alert_rows,
    ),
    "energy": ReportDef(
        key="energy",
        title="Energy Report",
        source="energy_stat, device, amenity",
        description=(
            "Hourly energy per device per room. NO UNIT is shown: `energy_stat` "
            "stores none, and nothing here is costed or carbon-weighted. The "
            "date range is converted to the stored hours-since-2000 `hour`."
        ),
        columns=[
            ReportColumn("hour_timestamp", "Hour", "datetime", 22),
            ReportColumn("device_name", "Device", width=16),
            ReportColumn("amenity_name", "Room No", width=12),
            ReportColumn("building_name", "Building", width=14),
            ReportColumn("floor_name", "Floor", width=12),
            ReportColumn("energy_consumed", "Energy Consumed", "number", 18),
        ],
        filters=[DATE_FROM, DATE_TO, FACILITY, BUILDING, FLOOR, ROOM,
                 ReportFilter("device_name", "Device", "select", "/devices")],
        fetch=_energy_rows,
    ),
}

#: Tab order on the Reports screen.
REPORT_ORDER = [
    "occupancy", "employee", "room-status", "booking", "ticket",
    "housekeeping", "sanitization", "alert", "energy",
]


def get_report(key: str) -> ReportDef | None:
    return REPORTS.get(key)


def run_report(
    db: Session, definition: ReportDef, *, page: int, page_size: int, filters: dict
) -> tuple[list[dict], int]:
    """Fetch a page, then narrow each row to the report's declared columns.

    Projecting to the columns is what stops a report leaking a field the
    underlying read service happens to return but the report does not declare.
    """
    rows, total = definition.fetch(db, page=page, page_size=page_size, **filters)
    keys = [c.key for c in definition.columns]
    return [{k: row.get(k) for k in keys} for row in rows], total
