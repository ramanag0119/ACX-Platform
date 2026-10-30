"""OSS device inventory, types and health read routes.

Paths mirror the HMS contract (minus `/api/v1`). No `require_permission` gate
here -- HMS authorises before forwarding. List endpoints accept arbitrary query
filters via the request and pass them to the adapter, so HMS can forward exactly
the (already-validated) query string it received.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.adapters import device_adapter as svc
from app.db.session import get_db
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, paginate
from app.schemas.device import (
    DeviceDetail,
    DeviceHealthRead,
    DeviceRead,
    DeviceTypeDetail,
    DeviceTypeRead,
)
from app.schemas.health import ErrorResponse

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
OSS_RESPONSES = {503: {"model": ErrorResponse, "description": "OSS DB/adapter not ready"}}

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

device_types_router = APIRouter(prefix="/device-types", tags=["devices"], responses=OSS_RESPONSES)
devices_router = APIRouter(prefix="/devices", tags=["devices"], responses=OSS_RESPONSES)


def _filters(request: Request) -> dict:
    """Pass-through query filters (everything except pagination)."""
    filters = {
        k: v for k, v in request.query_params.items() if k not in {"page", "page_size"}
    }
    if "device_ids" in filters:
        # Comma-separated OSS device ids, sent by HMS from its room mapping.
        try:
            filters["device_ids"] = [
                uuid.UUID(v) for v in filters["device_ids"].split(",") if v.strip()
            ]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="device_ids must be comma-separated UUIDs.",
            ) from None
    return filters


def _require(obj, what: str = "Resource"):
    """404 when the adapter found nothing, instead of failing response validation."""
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found.")
    return obj


@device_types_router.get("", response_model=Page[DeviceTypeRead])
def list_device_types(
    db: Session = Depends(get_db), page: int = PageParam, page_size: int = SizeParam
):
    rows, total = svc.list_device_types(db, page=page, page_size=page_size)
    return paginate(rows, page=page, page_size=page_size, total=total)


@device_types_router.get("/{type_id}", response_model=DeviceTypeDetail, responses=NOT_FOUND)
def get_device_type(type_id: int, db: Session = Depends(get_db)):
    return _require(svc.get_device_type(db, type_id), "Device type")


@devices_router.get("", response_model=Page[DeviceRead])
def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    page: int = PageParam,
    page_size: int = SizeParam,
):
    rows, total = svc.list_devices(db, page=page, page_size=page_size, **_filters(request))
    return paginate(rows, page=page, page_size=page_size, total=total)


@devices_router.get("/{device_id}", response_model=DeviceDetail, responses=NOT_FOUND)
def get_device(device_id: uuid.UUID, db: Session = Depends(get_db)):
    return _require(svc.get_device(db, device_id), "Device")


@devices_router.get("/{device_id}/health", response_model=DeviceHealthRead, responses=NOT_FOUND)
def get_device_health(device_id: uuid.UUID, db: Session = Depends(get_db)):
    return _require(svc.get_device_health(db, device_id), "Device")
