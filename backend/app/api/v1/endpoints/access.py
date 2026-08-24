"""Users, roles, modules and permissions read APIs (Phase 2.3).

Read-only, assembled from live PostgreSQL rows.

    GET /api/v1/users                        app_user
    GET /api/v1/users/{id}
    GET /api/v1/users/{id}/permissions       effective access, OR across roles
    GET /api/v1/roles                        role
    GET /api/v1/roles/{id}
    GET /api/v1/roles/{id}/permissions       role_module_permission for one role
    GET /api/v1/modules                      role_module  (the module registry)
    GET /api/v1/modules/{id}
    GET /api/v1/permissions                  role_module_permission
    GET /api/v1/permissions/{role_id}/{module_id}

NOT IMPLEMENTED, and why: `GET /permissions/{id}` cannot exist. A permission is
a `role_module_permission` row whose primary key is the composite
(role_id, module_id); there is no single permission id to route on. Inventing a
synthetic one would misrepresent the schema, so the detail route uses the real
composite key instead.

Phase 2.4: `/users` requires `read` on `employees`; `/roles`, `/modules` and
`/permissions` require `read` on `user_roles`. 401 without a valid token,
403 without the grant. Nothing here returns a credential: `password_hash`
and the `metadata` bag are excluded at the query level.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, require_permission
from app.schemas.access import (
    ModuleDetail,
    ModuleRead,
    PermissionRead,
    RoleDetail,
    RolePermissionRead,
    RoleRead,
    UserDetail,
    UserPermissionRead,
    UserRead,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.filters import RoleType
from app.schemas.health import ErrorResponse
from app.services import access as service

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource does not exist"}}
AUTH_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
}

# Phase 2.4 module mapping, verified against the seeded registry:
#   /users                          -> `employees`   (Employees screen)
#   /roles /modules /permissions    -> `user_roles`  (User Roles screen)
# The seeded Duty Manager holds `employees` but NOT `user_roles`, which is
# exactly the KT handbook rule "Manager: NO role administration" -- enforced
# here by the data, not by a role-name check.
EMPLOYEES_READ = [Depends(require_permission("employees", "read"))]
USER_ROLES_READ = [Depends(require_permission("user_roles", "read"))]

PageParam = Query(1, ge=1, description="1-based page number")
SizeParam = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page")

users_router = APIRouter(
    prefix="/users", tags=["users"],
    dependencies=EMPLOYEES_READ, responses=AUTH_RESPONSES,
)
roles_router = APIRouter(
    prefix="/roles", tags=["roles"],
    dependencies=USER_ROLES_READ, responses=AUTH_RESPONSES,
)
modules_router = APIRouter(
    prefix="/modules", tags=["modules"],
    dependencies=USER_ROLES_READ, responses=AUTH_RESPONSES,
)
permissions_router = APIRouter(
    prefix="/permissions", tags=["permissions"],
    dependencies=USER_ROLES_READ, responses=AUTH_RESPONSES,
)


def _missing(resource: str, resource_id) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} {resource_id} does not exist.",
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@users_router.get("", response_model=Page[UserRead], summary="List users")
def list_users(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None, description="Via user_role"),
    role_id: uuid.UUID | None = Query(None, description="Via user_role"),
    is_staff: int | None = Query(None, ge=0, le=1, description="1 staff, 0 guest"),
    department_id: uuid.UUID | None = Query(None),
    job_function_id: uuid.UUID | None = Query(None),
) -> Page[UserRead]:
    rows, total = service.list_users(
        db,
        page=page,
        page_size=page_size,
        facility_id=facility_id,
        role_id=role_id,
        is_staff=is_staff,
        department_id=department_id,
        job_function_id=job_function_id,
    )
    return Page[UserRead](
        items=[UserRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@users_router.get(
    "/{user_id}", response_model=UserDetail, responses=NOT_FOUND, summary="Get a user"
)
def get_user(user_id: uuid.UUID, db: DbSession) -> UserDetail:
    row = service.get_user(db, user_id)
    if row is None:
        raise _missing("User", user_id)
    return UserDetail(
        **UserRead.model_validate(row).model_dump(),
        roles=service.user_roles(db, user_id),
        facility_ids=service.user_facility_ids(db, user_id),
    )


@users_router.get(
    "/{user_id}/permissions",
    response_model=list[UserPermissionRead],
    responses=NOT_FOUND,
    summary="Effective permissions for a user",
    description=(
        "The OR of every module grant across the roles the user holds. "
        "`user_role` is facility-scoped, so `facility_id` narrows the result "
        "to the roles held at that facility."
    ),
)
def get_user_permissions(
    user_id: uuid.UUID,
    db: DbSession,
    facility_id: uuid.UUID | None = Query(None),
) -> list[UserPermissionRead]:
    if not service.user_exists(db, user_id):
        raise _missing("User", user_id)
    return [
        UserPermissionRead.model_validate(p)
        for p in service.user_permissions(db, user_id, facility_id=facility_id)
    ]


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


@roles_router.get("", response_model=Page[RoleRead], summary="List roles")
def list_roles(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    facility_id: uuid.UUID | None = Query(None),
    role_type: RoleType | None = Query(
        None, description="role_type enum label"
    ),
) -> Page[RoleRead]:
    rows, total = service.list_roles(
        db, page=page, page_size=page_size, facility_id=facility_id, role_type=role_type
    )
    return Page[RoleRead](
        items=[RoleRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@roles_router.get(
    "/{role_id}", response_model=RoleDetail, responses=NOT_FOUND, summary="Get a role"
)
def get_role(role_id: uuid.UUID, db: DbSession) -> RoleDetail:
    row = service.get_role(db, role_id)
    if row is None:
        raise _missing("Role", role_id)
    permissions = service.role_permissions(db, role_id)
    return RoleDetail(
        **RoleRead.model_validate(row).model_dump(),
        user_count=service.role_user_count(db, role_id),
        module_count=len(permissions),
        permissions=[RolePermissionRead.model_validate(p) for p in permissions],
    )


@roles_router.get(
    "/{role_id}/permissions",
    response_model=list[RolePermissionRead],
    responses=NOT_FOUND,
    summary="Module grants held by a role",
)
def get_role_permissions(role_id: uuid.UUID, db: DbSession) -> list[RolePermissionRead]:
    if service.get_role(db, role_id) is None:
        raise _missing("Role", role_id)
    return [
        RolePermissionRead.model_validate(p) for p in service.role_permissions(db, role_id)
    ]


# ---------------------------------------------------------------------------
# Modules -- the `role_module` registry
# ---------------------------------------------------------------------------


@modules_router.get(
    "",
    response_model=Page[ModuleRead],
    summary="List modules",
    description=(
        "There is no `module` table. `role_module` is the authoritative "
        "registry -- 18 rows matching the HMS sidebar."
    ),
)
def list_modules(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    write_applicable: bool | None = Query(
        None, description="False selects the read-only modules"
    ),
) -> Page[ModuleRead]:
    rows, total = service.list_modules(
        db, page=page, page_size=page_size, write_applicable=write_applicable
    )
    return Page[ModuleRead](
        items=[ModuleRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@modules_router.get(
    "/{module_id}",
    response_model=ModuleDetail,
    responses=NOT_FOUND,
    summary="Get a module",
)
def get_module(module_id: int, db: DbSession) -> ModuleDetail:
    row = service.get_module(db, module_id)
    if row is None:
        raise _missing("Module", module_id)
    return ModuleDetail(
        **ModuleRead.model_validate(row).model_dump(),
        role_count=service.module_role_count(db, module_id),
    )


# ---------------------------------------------------------------------------
# Permissions -- role_module_permission
# ---------------------------------------------------------------------------


@permissions_router.get(
    "",
    response_model=Page[PermissionRead],
    summary="List permissions",
    description=(
        "There is no `permission` table. Each row is a `role_module_permission` "
        "record keyed by the composite (role_id, module_id)."
    ),
)
def list_permissions(
    db: DbSession,
    page: int = PageParam,
    page_size: int = SizeParam,
    role_id: uuid.UUID | None = Query(None),
    module_id: int | None = Query(None),
) -> Page[PermissionRead]:
    rows, total = service.list_permissions(
        db, page=page, page_size=page_size, role_id=role_id, module_id=module_id
    )
    return Page[PermissionRead](
        items=[PermissionRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@permissions_router.get(
    "/{role_id}/{module_id}",
    response_model=PermissionRead,
    responses=NOT_FOUND,
    summary="Get one permission by its composite key",
    description=(
        "Routed on (role_id, module_id) because that is the actual primary key. "
        "A single-id detail route is not possible without inventing an "
        "identifier the schema does not have."
    ),
)
def get_permission(role_id: uuid.UUID, module_id: int, db: DbSession) -> PermissionRead:
    row = service.get_permission(db, role_id, module_id)
    if row is None:
        raise _missing("Permission", f"({role_id}, {module_id})")
    return PermissionRead.model_validate(row)
