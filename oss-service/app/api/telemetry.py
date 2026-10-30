"""OSS telemetry read routes: params, readings, snapshots, third-party meters.

Paths mirror the HMS contract (minus `/api/v1`). No gate here (HMS authorises).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.adapters import telemetry_adapter as svc
from app.db.session import get_db
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, paginate
from app.schemas.health import ErrorResponse
from app.schemas.telemetry import (
    DeviceCurrentStatRead,
    DeviceParamDetail,
    DeviceParamRead,
    DeviceStatRead,
    OtherDeviceReadingRead,
)

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
OSS_RESPONSES = {503: {"model": ErrorResponse, "description": "OSS DB/adapter not ready"}}

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

device_params_router = APIRouter(prefix="/device-params", tags=["telemetry"], responses=OSS_RESPONSES)
device_stats_router = APIRouter(prefix="/device-stats", tags=["telemetry"], responses=OSS_RESPONSES)
device_current_stats_router = APIRouter(prefix="/device-current-stats", tags=["telemetry"], responses=OSS_RESPONSES)
other_device_readings_router = APIRouter(prefix="/other-device-readings", tags=["telemetry"], responses=OSS_RESPONSES)


def _filters(request: Request) -> dict:
    return {k: v for k, v in request.query_params.items() if k not in {"page", "page_size"}}


def _require(obj, what: str = "Resource"):
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found.")
    return obj


@device_params_router.get("", response_model=Page[DeviceParamRead])
def list_device_params(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_device_params(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@device_params_router.get("/{param_id}", response_model=DeviceParamDetail, responses=NOT_FOUND)
def get_device_param(param_id: int, db: Session = Depends(get_db)):
    return _require(svc.get_device_param(db, param_id), "Device param")


@device_stats_router.get("", response_model=Page[DeviceStatRead])
def list_device_stats(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_device_stats(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@device_stats_router.get("/{stat_id}", response_model=DeviceStatRead, responses=NOT_FOUND)
def get_device_stat(stat_id: int, db: Session = Depends(get_db)):
    return svc.get_device_stat(db, stat_id)


@device_current_stats_router.get("", response_model=Page[DeviceCurrentStatRead])
def list_device_current_stats(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_device_current_stats(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@device_current_stats_router.get("/{cur_id}", response_model=DeviceCurrentStatRead, responses=NOT_FOUND)
def get_device_current_stat(cur_id: uuid.UUID, db: Session = Depends(get_db)):
    return _require(svc.get_device_current_stat(db, cur_id), "Device current stat")


@other_device_readings_router.get("", response_model=Page[OtherDeviceReadingRead])
def list_other_device_readings(request: Request, db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam):
    rows, total = svc.list_other_device_readings(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@other_device_readings_router.get("/{reading_id}", response_model=OtherDeviceReadingRead, responses=NOT_FOUND)
def get_other_device_reading(reading_id: int, db: Session = Depends(get_db)):
    return svc.get_other_device_reading(db, reading_id)
