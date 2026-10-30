"""OSS alert read routes.

Paths mirror the HMS contract (minus `/api/v1`). No gate here (HMS authorises).
Incidents and value alerts are HMS (BSS) data -- OSS has no table for either --
so they are not served here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.adapters import alert_adapter as svc
from app.db.session import get_db
from app.schemas.alert import (
    AlertDetail,
    AlertRead,
    AlertTypeDetail,
    AlertTypeRead,
    IncidentRef,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, paginate
from app.schemas.health import ErrorResponse

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
OSS_RESPONSES = {503: {"model": ErrorResponse, "description": "OSS DB/adapter not ready"}}

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

alert_types_router = APIRouter(prefix="/alert-types", tags=["alerts"], responses=OSS_RESPONSES)
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"], responses=OSS_RESPONSES)


def _filters(request: Request) -> dict:
    return {k: v for k, v in request.query_params.items() if k not in {"page", "page_size"}}


def _require(obj, what: str = "Resource"):
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found.")
    return obj


@alert_types_router.get("", response_model=Page[AlertTypeRead])
def list_alert_types(db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_alert_types(db, page=page, page_size=page_size)
    return paginate(rows, page=page, page_size=page_size, total=total)


@alert_types_router.get("/{type_id}", response_model=AlertTypeDetail, responses=NOT_FOUND)
def get_alert_type(type_id: int, db: Session = Depends(get_db)):
    return _require(svc.get_alert_type(db, type_id), "Alert type")


@alerts_router.get("", response_model=Page[AlertRead])
def list_alerts(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_alerts(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@alerts_router.get("/{alert_id}", response_model=AlertDetail, responses=NOT_FOUND)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    return svc.get_alert(db, alert_id)


@alerts_router.get("/{alert_id}/incidents", response_model=list[IncidentRef], responses=NOT_FOUND)
def list_alert_incidents(alert_id: int, db: Session = Depends(get_db)):
    return svc.list_alert_incidents(db, alert_id)
