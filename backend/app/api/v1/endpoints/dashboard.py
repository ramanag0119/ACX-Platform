"""Dashboard composition APIs.

    GET /api/v1/dashboard/caleido-at-work    the four operational KPI rings

Composition only: every figure is computed by `services/caleido.py` from
records the platform already owns. No table is introduced here, and OSS is
reached exclusively through the existing proxy client.

RBAC: `read` on `dashboard`, the module the HMS dashboard already gates on.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_permission
from app.schemas.dashboard import OperationalKPIsRead
from app.schemas.health import ErrorResponse
from app.services import caleido as svc

AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

DASHBOARD_READ = [Depends(require_permission("dashboard", "read"))]

dashboard_router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=DASHBOARD_READ,
    responses=AUTH_RESPONSES,
)


@dashboard_router.get(
    "/caleido-at-work",
    response_model=OperationalKPIsRead,
    summary="Caleido At Work operational KPIs",
    description=(
        "Smart Rooms Online, Service Request Status, Rooms For Check-Out and "
        "Pending Bookings, computed from live records rather than from a "
        "pre-computed daily snapshot.\n\n"
        "Each KPI declares its own `semantics`. `live` indicators describe a "
        "current operational state and are NOT re-scoped by the window -- "
        "Smart Rooms Online stays present-tense connectivity whichever period "
        "is selected. `period` indicators are filtered on the date column that "
        "carries that activity.\n\n"
        "`available=false` means the figure cannot be computed; a genuine zero "
        "is `available=true` with `numerator=0`. `percentage` is null rather "
        "than 0 whenever no ratio exists."
    ),
)
def caleido_at_work(
    db: DbSession,
    range: str = Query(
        "today",
        pattern="^(today|week|month)$",
        description="Window for the `period` KPIs: today | week | month",
    ),
    facility_id: uuid.UUID | None = Query(None),
    today: date | None = Query(
        None,
        description="Override the anchor date (testing). Defaults to the server date.",
    ),
) -> OperationalKPIsRead:
    return OperationalKPIsRead(
        **svc.operational_kpis(
            db, range_key=range, facility_id=facility_id, today=today
        )
    )
