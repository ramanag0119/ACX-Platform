"""Response models for users, roles, modules and permissions.

Every field maps to a real column, or is an explicitly-named value derived from
a real foreign key. Nothing is invented.

WHAT THE SCHEMA ACTUALLY CONTAINS (verified against the live database):

  * There is **no `module` table**. The authoritative module registry is
    `role_module` -- 18 rows matching the HMS sidebar.
  * There is **no `permission` table**. A permission exists only as a
    `role_module_permission` row: (role_id, module_id, read_access,
    write_access) with a COMPOSITE primary key. It has no id of its own, which
    is why the detail route is `/permissions/{role_id}/{module_id}`.
  * `user_role` is facility-scoped: PK (facility_id, app_user_id, role_id).

NEVER EXPOSED: `app_user.password_hash` (credential) and `app_user.metadata`
(an unbounded key-value bag that may hold anything in a real install).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Modules -- the `role_module` registry
# ---------------------------------------------------------------------------


class ModuleRead(ORMModel):
    """A row of `role_module`, the authoritative module registry."""

    id: int = Field(examples=[1], description="Small integer id, seeded from IKANOS")
    module_name: str = Field(examples=["dashboard"])
    read_applicable: bool | None = Field(
        default=None, description="Whether read access is meaningful for this module"
    )
    write_applicable: bool | None = Field(
        default=None,
        description="False for read-only modules such as dashboard and reports",
    )
    created_on: datetime
    updated_on: datetime


class ModuleDetail(ModuleRead):
    role_count: int = Field(description="Roles granted any access to this module")


# ---------------------------------------------------------------------------
# Permissions -- projections over `role_module_permission`
# ---------------------------------------------------------------------------


class PermissionRead(ORMModel):
    """One `role_module_permission` row, joined to its role and module.

    Identified by the composite key (role_id, module_id); there is no
    standalone permission id in the schema.
    """

    role_id: uuid.UUID
    role_name: str = Field(examples=["Front Desk"])
    module_id: int = Field(examples=[3])
    module_name: str = Field(examples=["bookings"])
    read_access: bool
    write_access: bool | None = None
    created_on: datetime
    updated_on: datetime


class RolePermissionRead(ORMModel):
    """A module entry inside one role's access list.

    `read_applicable` / `write_applicable` come from the module registry and
    say whether the grant is meaningful at all -- `reports`, for instance, is
    read-only by registry.
    """

    module_id: int
    module_name: str
    read_access: bool
    write_access: bool | None = None
    read_applicable: bool | None = None
    write_applicable: bool | None = None


class UserPermissionRead(ORMModel):
    """A user's EFFECTIVE access to one module.

    A user may hold several roles (`user_role` is facility-scoped), so the
    booleans are the OR across every role they hold, and `granted_by_roles`
    names the roles that produced the grant.
    """

    module_id: int
    module_name: str
    read_access: bool
    write_access: bool
    granted_by_roles: list[str] = Field(examples=[["Administrator"]])


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


class RoleRead(ORMModel):
    """A row of `role`."""

    id: uuid.UUID
    name: str = Field(examples=["Duty Manager"])
    description: str | None = None
    role_type: str = Field(
        examples=["manager"],
        description="admin | system_user | manager | guest | staff",
    )
    status: int | None = None
    facility_id: uuid.UUID
    created_on: datetime
    updated_on: datetime


class RoleDetail(RoleRead):
    user_count: int = Field(description="Rows in `user_role` for this role")
    module_count: int = Field(description="Modules this role has any grant on")
    permissions: list[RolePermissionRead]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserRoleRead(ORMModel):
    """A `user_role` assignment. Always carries its facility -- the same user
    can hold different roles at different facilities."""

    role_id: uuid.UUID
    role_name: str
    role_type: str
    facility_id: uuid.UUID


class UserRead(ORMModel):
    """A row of `app_user`.

    One table covers guests and staff; `is_staff` distinguishes them. There is
    no `employee` table and no `is_active` / `last_login` / `status` column.
    """

    id: uuid.UUID
    user_uid: str
    user_name: str | None = Field(default=None, description="Login name; no credential")
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone_number: str
    alternate_phone_number: str | None = None
    gender: str | None = None
    dob: date | None = None
    age: int | None = None
    is_child: int
    is_staff: int | None = Field(default=None, examples=[1], description="1 staff, 0 guest")
    emp_id: str | None = None
    date_of_joining: datetime | None = None
    date_of_termination: datetime | None = None
    supervisor: uuid.UUID | None = None
    address: str | None = None
    country: int | None = Field(default=None, description="country.id")
    nationality: int | None = Field(default=None, description="country.id")
    marital_status: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = Field(default=None, examples=["Front Office"])
    job_function_id: uuid.UUID | None = None
    job_function_name: str | None = Field(default=None, examples=["Supervisor"])
    created_on: datetime
    updated_on: datetime


class UserDetail(UserRead):
    roles: list[UserRoleRead]
    facility_ids: list[uuid.UUID] = Field(description="From `facility_user`")
