"""Query logic for users, roles, modules and permissions.

Reads live from PostgreSQL through the caller's session. No cache, no fixture,
no fallback data path.

Two structural facts drive the shape of everything here:

  * `role_module` IS the module registry -- there is no `module` table.
  * `role_module_permission` IS the permission -- there is no `permission`
    table, and its primary key is the composite (role_id, module_id).

`app_user.password_hash` is never selected. `app_user.metadata` is never
selected either: it is an unbounded key-value bag and could hold anything in a
real install.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    AppUser,
    Department,
    Facility,
    FacilityUser,
    JobFunction,
    Role,
    RoleModule,
    RoleModulePermission,
    UserRole,
)

#: Columns of `app_user` that are safe to return. Building the select from an
#: explicit allow-list means a newly added sensitive column cannot leak by
#: default -- it has to be added here deliberately.
_USER_COLUMNS = (
    AppUser.id,
    AppUser.user_uid,
    AppUser.user_name,
    AppUser.first_name,
    AppUser.last_name,
    AppUser.email,
    AppUser.phone_number,
    AppUser.alternate_phone_number,
    AppUser.gender,
    AppUser.dob,
    AppUser.age,
    AppUser.is_child,
    AppUser.is_staff,
    AppUser.emp_id,
    AppUser.date_of_joining,
    AppUser.date_of_termination,
    AppUser.supervisor,
    AppUser.address,
    AppUser.country,
    AppUser.nationality,
    AppUser.marital_status,
    AppUser.department_id,
    AppUser.job_function_id,
    AppUser.created_on,
    AppUser.updated_on,
)


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _page(stmt: Select, *, page: int, page_size: int) -> Select:
    return stmt.limit(page_size).offset((page - 1) * page_size)


# ---------------------------------------------------------------------------
# Modules (role_module)
# ---------------------------------------------------------------------------


def list_modules(
    db: Session, *, page: int, page_size: int, write_applicable: bool | None = None
):
    stmt = select(RoleModule).order_by(RoleModule.id)
    if write_applicable is not None:
        stmt = stmt.where(RoleModule.write_applicable.is_(write_applicable))
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_module(db: Session, module_id: int) -> RoleModule | None:
    return db.get(RoleModule, module_id)


def module_role_count(db: Session, module_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(RoleModulePermission)
        .where(RoleModulePermission.module_id == module_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# Permissions (role_module_permission)
# ---------------------------------------------------------------------------


def _permission_stmt() -> Select:
    return (
        select(
            RoleModulePermission.role_id,
            Role.name.label("role_name"),
            RoleModulePermission.module_id,
            RoleModule.module_name,
            RoleModulePermission.read_access,
            RoleModulePermission.write_access,
            RoleModulePermission.created_on,
            RoleModulePermission.updated_on,
        )
        .join(Role, Role.id == RoleModulePermission.role_id)
        .join(RoleModule, RoleModule.id == RoleModulePermission.module_id)
    )


def list_permissions(
    db: Session,
    *,
    page: int,
    page_size: int,
    role_id: uuid.UUID | None = None,
    module_id: int | None = None,
):
    stmt = _permission_stmt().order_by(Role.name, RoleModule.id)
    if role_id:
        stmt = stmt.where(RoleModulePermission.role_id == role_id)
    if module_id is not None:
        stmt = stmt.where(RoleModulePermission.module_id == module_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_permission(db: Session, role_id: uuid.UUID, module_id: int):
    """Looked up by the real composite key -- there is no single permission id."""
    return db.execute(
        _permission_stmt().where(
            RoleModulePermission.role_id == role_id,
            RoleModulePermission.module_id == module_id,
        )
    ).mappings().one_or_none()


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def list_roles(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    role_type: str | None = None,
):
    stmt = select(Role).order_by(Role.name)
    if facility_id:
        stmt = stmt.where(Role.facility_id == facility_id)
    if role_type:
        stmt = stmt.where(Role.role_type == role_type)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def get_role(db: Session, role_id: uuid.UUID) -> Role | None:
    return db.get(Role, role_id)


def role_permissions(db: Session, role_id: uuid.UUID) -> list[dict]:
    """Every module grant held by one role, with the registry's applicability."""
    rows = db.execute(
        select(
            RoleModulePermission.module_id,
            RoleModule.module_name,
            RoleModulePermission.read_access,
            RoleModulePermission.write_access,
            RoleModule.read_applicable,
            RoleModule.write_applicable,
        )
        .join(RoleModule, RoleModule.id == RoleModulePermission.module_id)
        .where(RoleModulePermission.role_id == role_id)
        .order_by(RoleModulePermission.module_id)
    ).mappings().all()
    return [dict(r) for r in rows]


def role_user_count(db: Session, role_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
    ).scalar_one()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _user_stmt() -> Select:
    return (
        select(
            *_USER_COLUMNS,
            Department.department_name.label("department_name"),
            JobFunction.function_name.label("job_function_name"),
        )
        .select_from(AppUser)
        .outerjoin(Department, Department.id == AppUser.department_id)
        .outerjoin(JobFunction, JobFunction.id == AppUser.job_function_id)
    )


def list_users(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    role_id: uuid.UUID | None = None,
    is_staff: int | None = None,
    department_id: uuid.UUID | None = None,
    job_function_id: uuid.UUID | None = None,
):
    stmt = _user_stmt().order_by(AppUser.first_name, AppUser.last_name)

    # facility and role both live on `user_role`, so one EXISTS covers either.
    if facility_id or role_id:
        conditions = [UserRole.app_user_id == AppUser.id]
        if facility_id:
            conditions.append(UserRole.facility_id == facility_id)
        if role_id:
            conditions.append(UserRole.role_id == role_id)
        stmt = stmt.where(select(UserRole).where(*conditions).exists())
    if is_staff is not None:
        stmt = stmt.where(AppUser.is_staff == is_staff)
    if department_id:
        stmt = stmt.where(AppUser.department_id == department_id)
    if job_function_id:
        stmt = stmt.where(AppUser.job_function_id == job_function_id)

    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).mappings().all()
    return rows, total


def get_user(db: Session, user_id: uuid.UUID):
    return db.execute(_user_stmt().where(AppUser.id == user_id)).mappings().one_or_none()


def user_exists(db: Session, user_id: uuid.UUID) -> bool:
    return db.execute(
        select(func.count()).select_from(AppUser).where(AppUser.id == user_id)
    ).scalar_one() > 0


def user_roles(db: Session, user_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(
            UserRole.role_id,
            Role.name.label("role_name"),
            Role.role_type,
            UserRole.facility_id,
        )
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.app_user_id == user_id)
        .order_by(Role.name)
    ).mappings().all()
    return [dict(r) for r in rows]


def user_facility_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.execute(
            select(FacilityUser.facility_id)
            .where(FacilityUser.app_user_id == user_id)
            .order_by(FacilityUser.facility_id)
        ).scalars().all()
    )


def user_permissions(
    db: Session, user_id: uuid.UUID, *, facility_id: uuid.UUID | None = None
) -> list[dict]:
    """A user's EFFECTIVE permissions: the OR across every role they hold.

    `user_role` is facility-scoped, so `facility_id` narrows the calculation to
    the roles held at one facility.
    """
    stmt = (
        select(
            RoleModulePermission.module_id,
            RoleModule.module_name,
            func.bool_or(RoleModulePermission.read_access).label("read_access"),
            func.bool_or(
                func.coalesce(RoleModulePermission.write_access, False)
            ).label("write_access"),
            func.array_agg(func.distinct(Role.name)).label("granted_by_roles"),
        )
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .join(RoleModulePermission, RoleModulePermission.role_id == Role.id)
        .join(RoleModule, RoleModule.id == RoleModulePermission.module_id)
        .where(UserRole.app_user_id == user_id)
        .group_by(RoleModulePermission.module_id, RoleModule.module_name)
        .order_by(RoleModulePermission.module_id)
    )
    if facility_id:
        stmt = stmt.where(UserRole.facility_id == facility_id)

    return [
        {
            "module_id": r.module_id,
            "module_name": r.module_name,
            "read_access": bool(r.read_access),
            "write_access": bool(r.write_access),
            "granted_by_roles": sorted(r.granted_by_roles),
        }
        for r in db.execute(stmt).all()
    ]


# ---------------------------------------------------------------------------
# Departments and job functions (Phase 3.0)
# ---------------------------------------------------------------------------
# These two tables had no endpoint before Phase 3.0: the Employees screen used
# to derive their names from user rows, which silently hid any department with
# no staff assigned.


def list_departments(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
):
    stmt = select(Department).order_by(Department.department_name)
    if facility_id:
        stmt = stmt.where(Department.facility_id == facility_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total


def list_job_functions(
    db: Session,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
):
    stmt = select(JobFunction).order_by(JobFunction.function_name)
    if facility_id:
        stmt = stmt.where(JobFunction.facility_id == facility_id)
    total = _count(db, stmt)
    rows = db.execute(_page(stmt, page=page, page_size=page_size)).scalars().all()
    return rows, total
