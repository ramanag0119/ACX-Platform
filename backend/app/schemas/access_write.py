"""Request bodies for the user, role, permission, department and function writes.

Only fields the schema actually has appear here. Enum-backed columns are typed
with `Literal` on the real PostgreSQL labels, so a bad value is a 422 from
Pydantic rather than a database error.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["male", "female", "other"]
MaritalStatus = Literal["married", "unmarried", "divorced", "other"]
RoleType = Literal["admin", "system_user", "manager", "guest", "staff"]

#: Passwords are hashed with bcrypt, which only uses the first 72 bytes.
PASSWORD_MIN = 8
PASSWORD_MAX = 72


class PermissionEntry(BaseModel):
    """One row of `role_module_permission`."""

    module_id: int
    read_access: bool = False
    write_access: bool = False


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    phone_number: str = Field(min_length=3, max_length=20)
    alternate_phone_number: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    user_name: str | None = Field(default=None, min_length=3, max_length=100)
    password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    #: `app_user.user_uid` -- the employee id the UI shows. Generated when absent.
    user_uid: str | None = Field(default=None, max_length=100)
    emp_id: str | None = Field(default=None, max_length=100)
    gender: Gender | None = None
    dob: date | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    is_child: int = Field(default=0, ge=0, le=1)
    #: 1 = staff, 0 = guest. There is no separate guest table.
    is_staff: int = Field(default=1, ge=0, le=1)
    date_of_joining: datetime | None = None
    supervisor: uuid.UUID | None = None
    address: str | None = Field(default=None, max_length=500)
    marital_status: MaritalStatus | None = None
    department_id: uuid.UUID | None = None
    job_function_id: uuid.UUID | None = None
    country: int | None = None
    nationality: int | None = None
    #: Rows in `user_role`; a user can hold several.
    role_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, value: str | None) -> str | None:
        if value and "@" not in value:
            raise ValueError("email must contain '@'")
        return value


class UserUpdate(BaseModel):
    """PATCH body: every field optional, only what is sent is written."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, min_length=3, max_length=20)
    alternate_phone_number: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    user_name: str | None = Field(default=None, min_length=3, max_length=100)
    password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    emp_id: str | None = Field(default=None, max_length=100)
    gender: Gender | None = None
    dob: date | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    is_staff: int | None = Field(default=None, ge=0, le=1)
    date_of_joining: datetime | None = None
    supervisor: uuid.UUID | None = None
    address: str | None = Field(default=None, max_length=500)
    marital_status: MaritalStatus | None = None
    department_id: uuid.UUID | None = None
    job_function_id: uuid.UUID | None = None
    country: int | None = None
    nationality: int | None = None
    role_ids: list[uuid.UUID] | None = None


class PasswordSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    role_type: RoleType = "staff"
    status: int | None = Field(default=1, ge=0, le=1)
    facility_id: uuid.UUID | None = None
    permissions: list[PermissionEntry] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    role_type: RoleType | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    permissions: list[PermissionEntry] | None = None


class PermissionMatrix(BaseModel):
    """PUT body for the whole Web Modules matrix of one role."""

    model_config = ConfigDict(extra="forbid")

    permissions: list[PermissionEntry]


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_name: str = Field(min_length=1, max_length=255)
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: int | None = Field(default=None, ge=0, le=1)


class JobFunctionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    function_name: str = Field(min_length=1, max_length=100)
    facility_id: uuid.UUID | None = None
    status: int | None = Field(default=1, ge=0, le=1)


class JobFunctionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    function_name: str | None = Field(default=None, min_length=1, max_length=100)
    status: int | None = Field(default=None, ge=0, le=1)


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_name: str
    facility_id: uuid.UUID
    status: int | None
    created_on: datetime
    updated_on: datetime


class JobFunctionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    function_name: str
    facility_id: uuid.UUID | None
    status: int | None
    created_on: datetime
    updated_on: datetime
