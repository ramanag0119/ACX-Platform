"""Room <-> OSS device mapping shapes."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ops_write import Body


class RoomDeviceCreate(Body):
    amenity_id: uuid.UUID = Field(description="The HMS room the device is installed in")
    oss_device_id: uuid.UUID = Field(description="`id` of the device as served by /devices (OSS)")


class RoomDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    oss_device_id: uuid.UUID
    amenity_id: uuid.UUID
    amenity_name: str = Field(examples=["211"])
    facility_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    building_name: str | None = None
    floor_id: uuid.UUID | None = None
    floor_name: str | None = None
    created_on: datetime
