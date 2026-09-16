"""Energy statistics and daily KPI read APIs (Phase 2.9).

    GET /api/v1/energy-stats                            energy_stat (hourly)
    GET /api/v1/energy-stats/summary                    SUM/COUNT rollup
    GET /api/v1/daily-data-points                       daily_dual_data_point
    GET /api/v1/daily-data-points/{metric_date}/{metric_type}

NOT IMPLEMENTED, and why:

    GET /energy-stats/{id} -- `energy_stat` has the four-column natural
                              primary key (device_name, facility_id,
                              amenity_id, hour). There is no single id to
                              route on, and inventing one would misrepresent
                              the schema. The same reasoning gives
                              /daily-data-points its two-part composite path.

=== NOTHING IS CALCULATED BEYOND SUM AND COUNT ===

`energy_stat.energy_consumed` is the only numeric energy value in the schema,
and the table stores NO unit -- `energy_unit` is therefore always null and
callers must not assume kWh. There is no tariff, currency, carbon-factor,
baseline or efficiency column anywhere in the 92 tables, so cost, CO2,
savings and efficiency are NOT derived and NOT returned.

`hour` is not a timestamp: the IKANOS column comment reads "hours elapsed from
2000" and the data agrees (hour 233388 = 2026-08-16 12:00 UTC). Both the raw
integer and the derived timestamp are returned, the latter labelled as derived.

RBAC: `read` on `reports` -- the module behind the Reports screen, whose tabs
include the Energy report. There is no `energy` or `power` module in the
18-row registry.

READ-ONLY.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import DbSession, require_permission
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.energy import (
    DailyDataPointRead,
    EnergyStatRead,
    EnergySummaryRead,
)
from app.schemas.filters import DailyMetricType
from app.schemas.health import ErrorResponse
from app.services import energy as svc

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

REPORTS_READ = [Depends(require_permission("reports", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

energy_stats_router = APIRouter(
    prefix="/energy-stats", tags=["energy"],
    dependencies=REPORTS_READ, responses=AUTH_RESPONSES,
)
daily_data_points_router = APIRouter(
    prefix="/daily-data-points", tags=["energy"],
    dependencies=REPORTS_READ, responses=AUTH_RESPONSES,
)


# ---------------------------------------------------------------------------
# energy_stat
# ---------------------------------------------------------------------------
# `/summary` is declared BEFORE any parameterised path so it can never be
# shadowed. (There is no /{id} route here -- the PK is composite.)


@energy_stats_router.get(
    "/summary",
    response_model=EnergySummaryRead,
    summary="Aggregate energy consumption",
    description=(
        "SUM and COUNT over the stored `energy_consumed`, grouped at query "
        "time. IKANOS stores energy hourly only, so day and per-room views are "
        "aggregated on read. No tariff, carbon factor or baseline is applied, "
        "and the result carries no unit because the table stores none."
    ),
)
def energy_summary(
    db: DbSession,
    group_by: str = Query(
        "day", description="hour | day | amenity | device"
    ),
    facility_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None),
    building_id: uuid.UUID | None = Query(None),
    floor_id: uuid.UUID | None = Query(None),
    device_name: str | None = Query(None),
    hour_from: int | None = Query(None, description="Raw `hour` lower bound"),
    hour_to: int | None = Query(None, description="Raw `hour` upper bound"),
) -> EnergySummaryRead:
    try:
        data = svc.energy_summary(
            db, group_by=group_by, facility_id=facility_id, amenity_id=amenity_id,
            building_id=building_id, floor_id=floor_id, device_name=device_name,
            hour_from=hour_from, hour_to=hour_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return EnergySummaryRead.model_validate(data)


@energy_stats_router.get(
    "",
    response_model=Page[EnergyStatRead],
    summary="List hourly energy statistics",
    description=(
        "One row per (device_name, facility, amenity, hour). `energy_consumed` "
        "is returned raw and `energy_unit` is always null -- `energy_stat` has "
        "no unit column. There is no FK to `device`; `device_name` is free text."
    ),
)
def list_energy_stats(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    amenity_id: uuid.UUID | None = Query(None, description="The room"),
    building_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    floor_id: uuid.UUID | None = Query(None, description="Via property_chain"),
    device_name: str | None = Query(None, description="Free text, exact match"),
    hour_from: int | None = Query(None, description="Hours since 2000-01-01 UTC"),
    hour_to: int | None = Query(None, description="Hours since 2000-01-01 UTC"),
    timestamp_from: datetime | None = Query(
        None, description="Convenience: converted to `hour` server-side"
    ),
    timestamp_to: datetime | None = Query(None),
) -> Page[EnergyStatRead]:
    if timestamp_from is not None:
        converted = svc.timestamp_to_hour(timestamp_from)
        hour_from = converted if hour_from is None else max(hour_from, converted)
    if timestamp_to is not None:
        converted = svc.timestamp_to_hour(timestamp_to)
        hour_to = converted if hour_to is None else min(hour_to, converted)

    rows, total = svc.list_energy_stats(
        db, page=page, page_size=page_size, facility_id=facility_id,
        amenity_id=amenity_id, building_id=building_id, floor_id=floor_id,
        device_name=device_name, hour_from=hour_from, hour_to=hour_to,
    )
    return Page[EnergyStatRead](
        items=[EnergyStatRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


# ---------------------------------------------------------------------------
# daily_dual_data_point
# ---------------------------------------------------------------------------


@daily_data_points_router.get(
    "",
    response_model=Page[DailyDataPointRead],
    summary="List daily KPI data points",
    description=(
        "`daily_dual_data_point`. `metric_type` is the Caleido At Work KPI "
        "set, and dp_1/dp_2 are the numerator/denominator behind the "
        "Dashboard rings. `facility_id` is NOT part of the primary key, so "
        "the table is single-facility as built."
    ),
)
def list_daily_data_points(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    metric_type: DailyMetricType | None = Query(
        None, description="daily_metric_type enum label",
    ),
    metric_date_from: date | None = Query(None),
    metric_date_to: date | None = Query(None),
) -> Page[DailyDataPointRead]:
    rows, total = svc.list_daily_data_points(
        db, page=page, page_size=page_size, facility_id=facility_id,
        metric_type=metric_type, metric_date_from=metric_date_from,
        metric_date_to=metric_date_to,
    )
    return Page[DailyDataPointRead](
        items=[DailyDataPointRead.model_validate(r) for r in rows],
        page=page, page_size=page_size, total=total,
    )


@daily_data_points_router.get(
    "/{metric_date}/{metric_type}",
    response_model=DailyDataPointRead,
    responses=NOT_FOUND,
    summary="Get one daily KPI data point",
    description=(
        "Routed on the real composite primary key (metric_date, metric_type). "
        "A single-id route is not possible -- the table has no id column."
    ),
)
def get_daily_data_point(
    metric_date: date, metric_type: DailyMetricType, db: DbSession
) -> DailyDataPointRead:
    row = svc.get_daily_data_point(db, metric_date, metric_type)
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Daily data point ({metric_date}, {metric_type}) does not exist.",
        )
    return DailyDataPointRead.model_validate(row)
