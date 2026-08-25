"""Reporting APIs.

    GET /api/v1/reports                          the nine reports and their shape
    GET /api/v1/reports/{report_key}             a page of rows, filtered
    GET /api/v1/reports/{report_key}/export.xlsx the same rows as a spreadsheet

NO NEW QUERIES AND NO NEW TABLES. Every report is assembled by
`app.services.reports`, which delegates to the read service already backing the
corresponding screen. That is deliberate: a report must agree with the module it
reports on, so a row created, edited or soft deleted through an existing module
is reflected here on the next request, and the soft-delete and facility-scoping
rules those services enforce apply unchanged.

The column list travels with the data. The screen renders whatever columns it is
given and the spreadsheet writer consumes the same list, so the table and the
download cannot drift apart.

FILTERS. `date_from` / `date_to` are mapped per report onto the column that
report is actually keyed on -- expected check-in for bookings, `created_on` for
tickets and alerts, the start date for housekeeping and sanitization, and the
hours-since-2000 `hour` for energy. Occupancy, Room Status and Employee have no
date column in the schema and therefore accept no date range: they are
point-in-time positions, and inventing a date filter would make them lie.

PDF is not exposed yet. The layout is being taken from a reference document;
`.xlsx` is delivered and `.pdf` will join it behind the same route shape.

RBAC: `read` on the `reports` module for every route here, which is the grant
the seeded registry already carries (Administrator and System read/write, Duty
Manager read-only). Report data is never wider than the caller's grant on the
reports module itself.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.health import ErrorResponse
from app.schemas.report import (
    ReportColumnOut,
    ReportFilterOut,
    ReportInfo,
    ReportPage,
)
from app.services import report_export
from app.services import reports as svc

AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "No such report"}}

REPORTS_READ = [Depends(require_permission("reports", "read"))]

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

reports_router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=REPORTS_READ,
    responses=AUTH_RESPONSES,
)


def _display_name(user) -> str:
    """Who ran the report, for the sheet header."""
    parts = [user.first_name, user.last_name]
    return " ".join(p for p in parts if p) or (user.user_name or "")


def _definition(report_key: str) -> svc.ReportDef:
    definition = svc.get_report(report_key)
    if definition is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=(
                f"No report named {report_key!r}. Available: "
                f"{', '.join(svc.REPORT_ORDER)}."
            ),
        )
    return definition


def _info(definition: svc.ReportDef) -> ReportInfo:
    return ReportInfo(
        key=definition.key,
        title=definition.title,
        source=definition.source,
        description=definition.description,
        columns=[
            ReportColumnOut(key=c.key, header=c.header, kind=c.kind)
            for c in definition.columns
        ],
        filters=[
            ReportFilterOut(
                name=f.name, label=f.label, kind=f.kind, options_from=f.options_from
            )
            for f in definition.filters
        ],
    )


def _coerce(value: Any, value_type: str | None) -> Any:
    """Turn a raw query value into what the read service expects.

    Driven by the filter's declared `value_type`, because the same parameter
    name is not the same type in every report -- `status` is a
    `service_status.id` for tickets but the `stay.status` enum label for
    bookings. A value that will not convert is a 422, not a silent no-op.
    """
    if value is None or value == "" or value_type is None:
        return value
    try:
        if value_type == "int":
            return int(value)
        if value_type == "uuid":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("1", "true", "yes", "on")
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Expected {value_type} but got {value!r}.",
        ) from exc
    return value


def _collect_filters(definition: svc.ReportDef, raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only the filters this report declares, dropping blanks.

    A parameter the report does not declare is ignored rather than passed on,
    so a stray query string can never reach a read service as a filter, and a
    date range sent to a report with no date column is simply not applied.
    """
    declared = {f.name: f for f in definition.filters}
    out: dict[str, Any] = {}
    for name, value in raw.items():
        spec = declared.get(name)
        if spec is None or value is None or value == "":
            continue
        # `date_from`/`date_to` arrive already widened to timestamps.
        out[name] = value if name in ("date_from", "date_to") else _coerce(
            value, spec.value_type
        )
    return out


def _echo_filters(
    definition: svc.ReportDef, filters: dict, date_from, date_to
) -> dict[str, Any]:
    """The filters that were really applied, for the header and the footer.

    Dates are echoed as the caller sent them, not as the widened timestamps,
    and only if the report declares them -- `_collect_filters` has already
    dropped a range the report cannot use.
    """
    out = {k: str(v) for k, v in filters.items() if k not in ("date_from", "date_to")}
    if date_from and "date_from" in filters:
        out["date_from"] = str(date_from)
    if date_to and "date_to" in filters:
        out["date_to"] = str(date_to)
    return out


def _as_range(date_from, date_to) -> tuple[datetime | None, datetime | None]:
    """A date range is inclusive of both days.

    The underlying services compare against timestamps, so the end date has to
    cover its whole day or "to = today" would exclude everything recorded today.
    """
    start = datetime.combine(date_from, time.min) if date_from else None
    end = datetime.combine(date_to, time.max) if date_to else None
    return start, end


@reports_router.get(
    "",
    response_model=list[ReportInfo],
    summary="List the available reports",
    description=(
        "Each entry carries the report's columns and the filters it accepts, "
        "so the screen renders from the definition rather than hardcoding it."
    ),
)
def list_reports() -> list[ReportInfo]:
    return [_info(svc.REPORTS[key]) for key in svc.REPORT_ORDER]


@reports_router.get(
    "/{report_key}",
    response_model=ReportPage,
    responses=NOT_FOUND,
    summary="Run a report",
    description=(
        "Returns a page of rows plus the columns to render them. Filters not "
        "declared by the report are ignored. `date_from` / `date_to` are "
        "inclusive and are applied to whichever column that report is keyed on; "
        "reports with no date column ignore them."
    ),
)
def run_report(
    report_key: str,
    db: DbSession,
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page"
    ),
    date_from: date | None = Query(None, description="Inclusive lower bound (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Inclusive upper bound (YYYY-MM-DD)"),
    facility_id: str | None = Query(None),
    building_id: str | None = Query(None),
    floor_id: str | None = Query(None),
    amenity_id: str | None = Query(None, description="Room"),
    amenity_type_id: str | None = Query(None),
    department_id: str | None = Query(None),
    job_function_id: str | None = Query(None),
    role_id: str | None = Query(None),
    category_id: str | None = Query(None),
    device_id: str | None = Query(None),
    assigned_to: str | None = Query(None),
    status: str | None = Query(None, description="Status id, or the status name where that column is text"),
    condition_id: int | None = Query(None),
    service_type: int | None = Query(None),
    alert_type: int | None = Query(None),
    alert_severity: str | None = Query(None),
    request_type: str | None = Query(None, description="Narrow to one maintenance tab"),
    request_source: str | None = Query(None),
    document_approval_status: str | None = Query(None),
    device_name: str | None = Query(None),
    is_occupied: bool | None = Query(None),
    is_in_house: bool | None = Query(None),
    is_checked_in: bool | None = Query(None),
    is_recurring: bool | None = Query(None),
) -> ReportPage:
    definition = _definition(report_key)
    start, end = _as_range(date_from, date_to)
    filters = _collect_filters(definition, {
        "date_from": start, "date_to": end,
        "facility_id": facility_id, "building_id": building_id, "floor_id": floor_id,
        "amenity_id": amenity_id, "amenity_type_id": amenity_type_id,
        "department_id": department_id, "job_function_id": job_function_id,
        "role_id": role_id, "category_id": category_id, "device_id": device_id,
        "assigned_to": assigned_to, "status": status, "condition_id": condition_id,
        "service_type": service_type, "alert_type": alert_type,
        "alert_severity": alert_severity, "request_type": request_type,
        "request_source": request_source,
        "document_approval_status": document_approval_status,
        "device_name": device_name, "is_occupied": is_occupied,
        "is_in_house": is_in_house, "is_checked_in": is_checked_in,
        "is_recurring": is_recurring,
    })
    rows, total = svc.run_report(
        db, definition, page=page, page_size=page_size, filters=filters
    )
    return ReportPage(
        key=definition.key,
        title=definition.title,
        source=definition.source,
        description=definition.description,
        columns=_info(definition).columns,
        items=rows,
        # Echo the dates the caller sent rather than the widened timestamps,
        # and only when this report actually accepts a range -- Occupancy,
        # Room Status and Employee have no date column, so claiming one would
        # print a filter on the report that never narrowed anything.
        filters_applied=_echo_filters(definition, filters, date_from, date_to),
        page=page,
        page_size=page_size,
        total=total,
    )


@reports_router.get(
    "/{report_key}/export.xlsx",
    responses={
        **NOT_FOUND,
        200: {
            "content": {XLSX_MEDIA_TYPE: {}},
            "description": "The report as an .xlsx workbook",
        },
    },
    summary="Download a report as Excel",
    description=(
        "The same rows `GET /reports/{report_key}` returns for the same "
        "filters, written to a single sheet with a header block naming the "
        "source tables, the filters applied and who generated it. Export is "
        "NOT paginated -- it walks every matching row up to `max_rows`."
    ),
)
def export_report_xlsx(
    report_key: str,
    db: DbSession,
    current_user: CurrentUser,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    facility_id: str | None = Query(None),
    building_id: str | None = Query(None),
    floor_id: str | None = Query(None),
    amenity_id: str | None = Query(None),
    amenity_type_id: str | None = Query(None),
    department_id: str | None = Query(None),
    job_function_id: str | None = Query(None),
    role_id: str | None = Query(None),
    category_id: str | None = Query(None),
    device_id: str | None = Query(None),
    assigned_to: str | None = Query(None),
    status: str | None = Query(None),
    condition_id: int | None = Query(None),
    service_type: int | None = Query(None),
    alert_type: int | None = Query(None),
    alert_severity: str | None = Query(None),
    request_type: str | None = Query(None),
    request_source: str | None = Query(None),
    document_approval_status: str | None = Query(None),
    device_name: str | None = Query(None),
    is_occupied: bool | None = Query(None),
    is_in_house: bool | None = Query(None),
    is_checked_in: bool | None = Query(None),
    is_recurring: bool | None = Query(None),
    max_rows: int = Query(
        10_000, ge=1, le=50_000,
        description="Hard ceiling, so one download cannot exhaust the server",
    ),
) -> Response:
    definition = _definition(report_key)
    start, end = _as_range(date_from, date_to)
    filters = _collect_filters(definition, {
        "date_from": start, "date_to": end,
        "facility_id": facility_id, "building_id": building_id, "floor_id": floor_id,
        "amenity_id": amenity_id, "amenity_type_id": amenity_type_id,
        "department_id": department_id, "job_function_id": job_function_id,
        "role_id": role_id, "category_id": category_id, "device_id": device_id,
        "assigned_to": assigned_to, "status": status, "condition_id": condition_id,
        "service_type": service_type, "alert_type": alert_type,
        "alert_severity": alert_severity, "request_type": request_type,
        "request_source": request_source,
        "document_approval_status": document_approval_status,
        "device_name": device_name, "is_occupied": is_occupied,
        "is_in_house": is_in_house, "is_checked_in": is_checked_in,
        "is_recurring": is_recurring,
    })

    # A spreadsheet of one page would be useless, so walk the pages the read
    # services already paginate rather than adding an unbounded query.
    rows: list[dict] = []
    page = 1
    while len(rows) < max_rows:
        batch, total = svc.run_report(
            db, definition, page=page, page_size=MAX_PAGE_SIZE, filters=filters
        )
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
        page += 1
    rows = rows[:max_rows]

    display = _echo_filters(definition, filters, date_from, date_to)

    payload = report_export.to_xlsx(
        definition, rows, filters=display, generated_by=_display_name(current_user)
    )
    filename = report_export.filename_for(definition, "xlsx")
    return Response(
        content=payload,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # The browser fetch reads the name from here.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
