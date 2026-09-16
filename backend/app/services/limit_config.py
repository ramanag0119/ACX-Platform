"""Read projection for `value_alert_limit_config`.

The thresholds behind `value_alert`. Phase 2.7 exposed the breaches but not the
configuration, which is why the Limit Config Alert screen had a table it could
not fill; this is the missing read side.

`is_percentage_value` says which pair of limit columns is meaningful, so both
pairs are returned as stored rather than merged into one.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Device, ValueAlertLimitConfig


#: `value_alert_limit_config` stores two IKANOS text flags, not booleans:
#: `limit_check` is CHAR(1) holding 'Y' (seeded) and `is_percentage_value` is
#: CHAR(3) holding 'no ' (seeded, space-padded). The API exposes them as
#: booleans and converts in both directions; the padded 'no ' is what tells us
#: the positive value is the three-character 'yes'.
TRUE_FLAGS = {"y", "yes", "true", "1"}


def flag_to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in TRUE_FLAGS


def bool_to_yn(value: bool) -> str:
    """For CHAR(1) `limit_check`."""
    return "Y" if value else "N"


def bool_to_yesno(value: bool) -> str:
    """For CHAR(3) `is_percentage_value`."""
    return "yes" if value else "no "


class LimitConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parameter: str
    device_name: str
    device_id: uuid.UUID | None
    limit_check: bool
    is_percentage_value: bool
    nominal: Decimal | None
    limit_low_percentage: Decimal | None
    limit_high_percentage: Decimal | None
    limit_low_value: Decimal | None
    limit_high_value: Decimal | None
    remarks: str
    facility_id: uuid.UUID
    created_on: datetime
    updated_on: datetime

    @field_validator("limit_check", "is_percentage_value", mode="before")
    @classmethod
    def _coerce_flag(cls, value):
        return flag_to_bool(value)


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def list_limit_configs(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_id: uuid.UUID | None = None,
    parameter: str | None = None,
    facility_id: uuid.UUID | None = None,
):
    stmt = select(ValueAlertLimitConfig).order_by(
        ValueAlertLimitConfig.device_name, ValueAlertLimitConfig.parameter
    )
    if device_id:
        stmt = stmt.where(ValueAlertLimitConfig.device_id == device_id)
    if parameter:
        stmt = stmt.where(ValueAlertLimitConfig.parameter == parameter)
    if facility_id:
        stmt = stmt.where(ValueAlertLimitConfig.facility_id == facility_id)
    total = _count(db, stmt)
    rows = (
        db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    )
    return rows, total


def device_name_for(db: Session, device_id: uuid.UUID) -> str | None:
    """`value_alert_limit_config.device_name` is stored text, so a config
    created for a known device copies the device's name at creation time."""
    return db.execute(
        select(Device.device_name).where(Device.id == device_id)
    ).scalars().first()
