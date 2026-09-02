"""Write endpoints for users, roles, permissions, departments and functions.

    POST   /users                        create staff or guest
    PATCH  /users/{id}                   update, including role assignment
    POST   /users/{id}/password          set a login credential
    POST   /users/{id}/deactivate        record a termination date
    POST   /users/{id}/reactivate        clear it
    POST   /roles                        create a role (with its matrix)
    PATCH  /roles/{id}                   update a role
    PUT    /roles/{id}/permissions       replace the whole module matrix
    GET/POST/PATCH /departments          department list + create + update
    GET/POST/PATCH /job-functions        job function list + create + update

RBAC, all database-driven and never role-name based:
    `employees` write  -> user records, departments, job functions
    `user_roles` write -> roles and permission matrices

That split mirrors the seeded grants exactly: a Duty Manager holds `employees`
but not `user_roles`, so they can maintain staff records and cannot hand out
privileges.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.schemas.access import RolePermissionRead, RoleRead, UserDetail, UserRead
from app.schemas.access_write import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    JobFunctionCreate,
    JobFunctionRead,
    JobFunctionUpdate,
    PasswordSet,
    PermissionMatrix,
    RoleCreate,
    RoleUpdate,
    UserCreate,
    UserUpdate,
)
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from app.schemas.health import ErrorResponse
from app.services import access as read_service
from app.services import access_write as service

WRITE_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role lacks the module grant"},
    404: {"model": ErrorResponse, "description": "Resource does not exist"},
    409: {"model": ErrorResponse, "description": "Conflicts with existing data"},
    422: {"model": ErrorResponse, "description": "Payload rejected"},
}

EMPLOYEES_WRITE = [Depends(require_permission("employees", "write"))]
USER_ROLES_WRITE = [Depends(require_permission("user_roles", "write"))]
EMPLOYEES_READ = [Depends(require_permission("employees", "read"))]

users_write_router = APIRouter(prefix="/users", tags=["users"], responses=WRITE_RESPONSES)
roles_write_router = APIRouter(prefix="/roles", tags=["roles"], responses=WRITE_RESPONSES)
departments_router = APIRouter(prefix="/departments", tags=["employees"], responses=WRITE_RESPONSES)
job_functions_router = APIRouter(
    prefix="/job-functions", tags=["employees"], responses=WRITE_RESPONSES
)


def _user_detail(db, user_id: uuid.UUID) -> UserDetail:
    """Re-read through the READ projection, so a write can never return a
    column the read allow-list withholds (password_hash, metadata)."""
    row = read_service.get_user(db, user_id)
    return UserDetail(
        **UserRead.model_validate(row).model_dump(),
        roles=read_service.user_roles(db, user_id),
        facility_ids=read_service.user_facility_ids(db, user_id),
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@users_write_router.post(
    "",
    response_model=UserDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=EMPLOYEES_WRITE,
    summary="Create a staff member or guest",
    description=(
        "`is_staff` picks which: 1 = staff, 0 = guest. There is no guest table. "
        "`user_uid` is generated in the seeded PE00001 style when omitted. A "
        "`password` is hashed with bcrypt and never returned."
    ),
)
def create_user(payload: UserCreate, db: DbSession, current_user: CurrentUser) -> UserDetail:
    facility_id = service.default_facility_id(db, current_user.facility_ids)
    user = service.create_user(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return _user_detail(db, user.id)


@users_write_router.patch(
    "/{user_id}",
    response_model=UserDetail,
    dependencies=EMPLOYEES_WRITE,
    summary="Update a user",
)
def update_user(
    user_id: uuid.UUID, payload: UserUpdate, db: DbSession, current_user: CurrentUser
) -> UserDetail:
    facility_id = service.default_facility_id(db, current_user.facility_ids)
    service.update_user(
        db,
        user_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return _user_detail(db, user_id)


@users_write_router.post(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=USER_ROLES_WRITE,
    summary="Set a user's password",
    description=(
        "Stores a bcrypt hash in `app_user.password_hash`. Gated on `user_roles` "
        "write rather than `employees`, because granting the ability to sign in "
        "is an access-control action. The plaintext is never stored or returned."
    ),
)
def set_password(user_id: uuid.UUID, payload: PasswordSet, db: DbSession) -> None:
    service.set_user_password(db, user_id, password=payload.password)


@users_write_router.post(
    "/{user_id}/deactivate",
    response_model=UserDetail,
    dependencies=EMPLOYEES_WRITE,
    summary="Record a termination date",
    description=(
        "The schema has no active flag; `date_of_termination` is how IKANOS "
        "retires a staff member, and the list view derives Active/InActive "
        "from it. The row is kept -- stays and service requests reference it."
    ),
)
def deactivate_user(user_id: uuid.UUID, db: DbSession) -> UserDetail:
    service.deactivate_user(db, user_id, terminated_on=datetime.now(UTC))
    return _user_detail(db, user_id)


@users_write_router.post(
    "/{user_id}/reactivate",
    response_model=UserDetail,
    dependencies=EMPLOYEES_WRITE,
    summary="Clear a termination date",
)
def reactivate_user(user_id: uuid.UUID, db: DbSession) -> UserDetail:
    service.reactivate_user(db, user_id)
    return _user_detail(db, user_id)


# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------


@roles_write_router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=USER_ROLES_WRITE,
    summary="Create a role",
)
def create_role(payload: RoleCreate, db: DbSession, current_user: CurrentUser) -> RoleRead:
    facility_id = service.default_facility_id(db, current_user.facility_ids)
    data = payload.model_dump()
    data["permissions"] = [p.model_dump() for p in payload.permissions]
    role = service.create_role(
        db, data=data, actor_id=current_user.id, facility_id=facility_id
    )
    return RoleRead.model_validate(role)


@roles_write_router.patch(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=USER_ROLES_WRITE,
    summary="Update a role",
)
def update_role(role_id: uuid.UUID, payload: RoleUpdate, db: DbSession) -> RoleRead:
    changes = payload.model_dump(exclude_unset=True)
    if payload.permissions is not None:
        changes["permissions"] = [p.model_dump() for p in payload.permissions]
    role = service.update_role(db, role_id, changes=changes)
    return RoleRead.model_validate(role)


@roles_write_router.put(
    "/{role_id}/permissions",
    response_model=list[RolePermissionRead],
    dependencies=USER_ROLES_WRITE,
    summary="Replace a role's module permissions",
    description=(
        "Upserts `role_module_permission` for every module sent, in one "
        "transaction. Write access requires read access, and a module whose "
        "`write_applicable` is false rejects write -- both enforced from "
        "`role_module`, not from a hardcoded list."
    ),
)
def replace_permissions(
    role_id: uuid.UUID, payload: PermissionMatrix, db: DbSession
) -> list[RolePermissionRead]:
    service.replace_role_permissions(
        db, role_id, permissions=[entry.model_dump() for entry in payload.permissions]
    )
    return [
        RolePermissionRead.model_validate(row)
        for row in read_service.role_permissions(db, role_id)
    ]


# ---------------------------------------------------------------------------
# Departments and job functions
# ---------------------------------------------------------------------------


@departments_router.get(
    "",
    response_model=Page[DepartmentRead],
    dependencies=EMPLOYEES_READ,
    summary="List departments",
    description=(
        "The `department` table, which had no endpoint before Phase 3.0 -- the "
        "Employees screen previously derived department names from user rows "
        "and could not see a department with no staff."
    ),
)
def list_departments(
    db: DbSession,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    facility_id: uuid.UUID | None = None,
) -> Page[DepartmentRead]:
    page_size = min(page_size, MAX_PAGE_SIZE)
    rows, total = read_service.list_departments(
        db, page=page, page_size=page_size, facility_id=facility_id
    )
    return Page[DepartmentRead](
        items=[DepartmentRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@departments_router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=EMPLOYEES_WRITE,
    summary="Create a department",
)
def create_department(
    payload: DepartmentCreate, db: DbSession, current_user: CurrentUser
) -> DepartmentRead:
    facility_id = service.default_facility_id(db, current_user.facility_ids)
    row = service.create_department(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return DepartmentRead.model_validate(row)


@departments_router.patch(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=EMPLOYEES_WRITE,
    summary="Update a department",
)
def update_department(
    department_id: uuid.UUID, payload: DepartmentUpdate, db: DbSession
) -> DepartmentRead:
    row = service.update_department(
        db, department_id, changes=payload.model_dump(exclude_unset=True)
    )
    return DepartmentRead.model_validate(row)


@job_functions_router.get(
    "",
    response_model=Page[JobFunctionRead],
    dependencies=EMPLOYEES_READ,
    summary="List job functions",
)
def list_job_functions(
    db: DbSession,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    facility_id: uuid.UUID | None = None,
) -> Page[JobFunctionRead]:
    page_size = min(page_size, MAX_PAGE_SIZE)
    rows, total = read_service.list_job_functions(
        db, page=page, page_size=page_size, facility_id=facility_id
    )
    return Page[JobFunctionRead](
        items=[JobFunctionRead.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@job_functions_router.post(
    "",
    response_model=JobFunctionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=EMPLOYEES_WRITE,
    summary="Create a job function",
)
def create_job_function(
    payload: JobFunctionCreate, db: DbSession, current_user: CurrentUser
) -> JobFunctionRead:
    facility_id = service.default_facility_id(db, current_user.facility_ids)
    row = service.create_job_function(
        db,
        data=payload.model_dump(),
        actor_id=current_user.id,
        facility_id=facility_id,
    )
    return JobFunctionRead.model_validate(row)


@job_functions_router.patch(
    "/{function_id}",
    response_model=JobFunctionRead,
    dependencies=EMPLOYEES_WRITE,
    summary="Update a job function",
)
def update_job_function(
    function_id: uuid.UUID, payload: JobFunctionUpdate, db: DbSession
) -> JobFunctionRead:
    row = service.update_job_function(
        db, function_id, changes=payload.model_dump(exclude_unset=True)
    )
    return JobFunctionRead.model_validate(row)
