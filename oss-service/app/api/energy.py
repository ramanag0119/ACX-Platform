"""OSS energy statistics read routes (device-derived only).

`/energy-stats` and `/energy-stats/summary`. `/daily-data-points` stays in
HMS/BSS (mixed KPIs). No gate here (HMS authorises).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.adapters import energy_adapter as svc
from app.db.session import get_db
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, paginate
from app.schemas.energy import EnergyStatRead, EnergySummaryRead
from app.schemas.health import ErrorResponse

OSS_RESPONSES = {503: {"model": ErrorResponse, "description": "OSS DB/adapter not ready"}}

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

energy_stats_router = APIRouter(prefix="/energy-stats", tags=["energy"], responses=OSS_RESPONSES)


def _filters(request: Request, drop: set[str]) -> dict:
    return {k: v for k, v in request.query_params.items() if k not in drop}


@energy_stats_router.get("", response_model=Page[EnergyStatRead])
def list_energy_stats(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_energy_stats(
        db, page=page, page_size=page_size, **_filters(request, {"page", "page_size"})
    )
    return paginate(rows, page=page, page_size=page_size, total=total)


@energy_stats_router.get("/summary", response_model=EnergySummaryRead)
def energy_summary(request: Request, db: Session = Depends(get_db), group_by: str = Query("day")):
    return svc.energy_summary(db, group_by=group_by, **_filters(request, {"group_by"}))
