"""Write logic for users, roles, permissions, departments and job functions.

Every rule enforced here comes from the schema or the seeded IKANOS data:

* `app_user.user_uid` is UNIQUE, and `user_name` must be unique to be usable as
  a login, so both are pre-checked and surface as 409.
* A user's roles live in `user_role` (composite PK app_user_id + role_id +
  facility_id), so replacing a user's roles means deleting and re-inserting
  those rows -- there is no role column on `app_user`.
* `role_module_permission` IS the permission, keyed (role_id, module_id).
  `read_applicable` / `write_applicable` on `role_module` decide whether a flag
  is meaningful; asking for write on a module that has `write_applicable` false
  is rejected rather than silently stored.
* `department.facility_id` and `role.facility_id` are NOT NULL, so both are
  scoped to a facility the caller actually belongs to.

PASSWORDS: `app_user.password_hash` already exists in the schema. It is written
only through `hash_password()` (bcrypt) and never read back, never logged and
never returned. Phase 1.8 left every seeded row with the `!seed-no-login`
sentinel; setting a real password is an explicit operator action, not something
inferred.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AppUser,
    Department,
    Facility,
    JobFunction,
    Role,
    RoleModule,
    RoleModulePermission,
    UserRole,
)
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    next_reference,
    require_exists,
    require_row,
    transaction,
)

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _validate_user_refs(db: Session, data: dict) -> None:
    require_exists(db, Department, data.get("department_id"), "Department")
    require_exists(db, JobFunction, data.get("job_function_id"), "Job function")
    require_exists(db, AppUser, data.get("supervisor"), "Supervisor")


def create_user(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> AppUser:
    """Create a staff member or a guest.

    `is_staff` distinguishes the two (1 = staff, 0 = guest) -- there is no
    separate guest table, exactly as Phase 2.8 established.
    """
    role_ids: list[uuid.UUID] = data.pop("role_ids", None) or []
    password: str | None = data.pop("password", None)

    with transaction(db):
        _validate_user_refs(db, data)

        # `user_uid` is the human-facing unique key. Generate one when the
        # caller does not supply it, following the seeded PE00001 pattern.
        user_uid = data.pop("user_uid", None) or next_reference(
            db, AppUser, AppUser.user_uid, "PE", width=5
        )
        ensure_unique(db, AppUser, AppUser.user_uid, user_uid, "Employee id")

        user_name = data.get("user_name")
        if user_name:
            ensure_unique(db, AppUser, AppUser.user_name, user_name, "Username")

        user = AppUser(
            id=uuid.uuid4(),
            user_uid=user_uid,
            created_by=actor_id,
            **data,
        )
        if password:
            user.password_hash = hash_password(password)
        db.add(user)
        db.flush()

        _replace_user_roles(db, user.id, role_ids, facility_id, actor_id)

    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    changes: dict,
    actor_id: uuid.UUID,
    facility_id: uuid.UUID,
) -> AppUser:
    role_ids = changes.pop("role_ids", None)
    password = changes.pop("password", None)

    with transaction(db):
        user = require_row(db, AppUser, user_id, "User")
        _validate_user_refs(db, changes)

        if "user_name" in changes and changes["user_name"]:
            ensure_unique(
                db, AppUser, AppUser.user_name, changes["user_name"], "Username",
                exclude_id=user_id,
            )
        if changes.get("supervisor") == user_id:
            raise Invalid("A user cannot be their own supervisor.")

        apply_changes(user, changes)
        if password:
            user.password_hash = hash_password(password)
        if role_ids is not None:
            _replace_user_roles(db, user_id, role_ids, facility_id, actor_id)

    db.refresh(user)
    return user


def set_user_password(
    db: Session, user_id: uuid.UUID, *, password: str
) -> None:
    """Set a login credential. The plaintext never leaves this call."""
    with transaction(db):
        user = require_row(db, AppUser, user_id, "User")
        if not user.user_name:
            raise Invalid(
                "This user has no username, so a password cannot be used to sign in."
            )
        user.password_hash = hash_password(password)


def _replace_user_roles(
    db: Session,
    user_id: uuid.UUID,
    role_ids: list[uuid.UUID],
    facility_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    """Rewrite `user_role` for one user. Roles are rows, not a column."""
    for role_id in role_ids:
        require_exists(db, Role, role_id, "Role")
    db.execute(delete(UserRole).where(UserRole.app_user_id == user_id))
    for role_id in role_ids:
        db.add(
            UserRole(
                app_user_id=user_id,
                role_id=role_id,
                facility_id=facility_id,
                created_by=actor_id,
            )
        )


def deactivate_user(db: Session, user_id: uuid.UUID, *, terminated_on) -> AppUser:
    """Retire a staff member.

    The schema has no `is_active` flag: `date_of_termination` is how IKANOS
    marks a leaver, and the read model already derives Active/InActive from it.
    Rows are never deleted -- service requests and stays reference them.
    """
    with transaction(db):
        user = require_row(db, AppUser, user_id, "User")
        user.date_of_termination = terminated_on
    db.refresh(user)
    return user


def reactivate_user(db: Session, user_id: uuid.UUID) -> AppUser:
    with transaction(db):
        user = require_row(db, AppUser, user_id, "User")
        user.date_of_termination = None
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------


def create_role(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Role:
    permissions = data.pop("permissions", None) or []
    with transaction(db):
        ensure_unique(db, Role, Role.name, data["name"], "Role")
        role = Role(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            **data,
        )
        db.add(role)
        db.flush()
        if permissions:
            _apply_permissions(db, role.id, permissions)
    db.refresh(role)
    return role


def update_role(db: Session, role_id: uuid.UUID, *, changes: dict) -> Role:
    permissions = changes.pop("permissions", None)
    with transaction(db):
        role = require_row(db, Role, role_id, "Role")
        if "name" in changes:
            ensure_unique(db, Role, Role.name, changes["name"], "Role", exclude_id=role_id)
        apply_changes(role, changes)
        if permissions is not None:
            _apply_permissions(db, role_id, permissions)
    db.refresh(role)
    return role


def replace_role_permissions(
    db: Session, role_id: uuid.UUID, *, permissions: list[dict]
) -> list[dict]:
    """Set the whole module matrix for one role in a single transaction."""
    with transaction(db):
        require_row(db, Role, role_id, "Role")
        _apply_permissions(db, role_id, permissions)
    return permissions


def _apply_permissions(db: Session, role_id: uuid.UUID, permissions: list[dict]) -> None:
    """Upsert `role_module_permission` rows, honouring what each module allows."""
    modules = {module.id: module for module in db.execute(select(RoleModule)).scalars()}

    for entry in permissions:
        module_id = entry["module_id"]
        module = modules.get(module_id)
        if module is None:
            raise Invalid(f"Module {module_id} does not exist.")

        read_access = bool(entry.get("read_access", False))
        write_access = bool(entry.get("write_access", False))

        if write_access and module.write_applicable is False:
            raise Invalid(
                f"Module '{module.module_name}' does not support write access."
            )
        if read_access is False and module.read_applicable is False and write_access:
            raise Invalid(
                f"Module '{module.module_name}' does not support read access."
            )
        # Write without read would hide a module the role can still change.
        if write_access and not read_access:
            raise Invalid(
                f"Module '{module.module_name}': write access requires read access."
            )

        existing = db.get(RoleModulePermission, {"role_id": role_id, "module_id": module_id})
        if existing is None:
            db.add(
                RoleModulePermission(
                    role_id=role_id,
                    module_id=module_id,
                    read_access=read_access,
                    write_access=write_access,
                )
            )
        else:
            existing.read_access = read_access
            existing.write_access = write_access


# ---------------------------------------------------------------------------
# Departments and job functions
# ---------------------------------------------------------------------------


def create_department(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Department:
    with transaction(db):
        ensure_unique(
            db, Department, Department.department_name, data["department_name"], "Department"
        )
        row = Department(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            status=data.pop("status", 1),
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_department(db: Session, department_id: uuid.UUID, *, changes: dict) -> Department:
    with transaction(db):
        row = require_row(db, Department, department_id, "Department")
        if "department_name" in changes:
            ensure_unique(
                db, Department, Department.department_name, changes["department_name"],
                "Department", exclude_id=department_id,
            )
        apply_changes(row, changes)
    db.refresh(row)
    return row


def create_job_function(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> JobFunction:
    with transaction(db):
        ensure_unique(
            db, JobFunction, JobFunction.function_name, data["function_name"], "Job function"
        )
        row = JobFunction(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            created_by=actor_id,
            status=data.pop("status", 1),
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_job_function(db: Session, function_id: uuid.UUID, *, changes: dict) -> JobFunction:
    with transaction(db):
        row = require_row(db, JobFunction, function_id, "Job function")
        if "function_name" in changes:
            ensure_unique(
                db, JobFunction, JobFunction.function_name, changes["function_name"],
                "Job function", exclude_id=function_id,
            )
        apply_changes(row, changes)
    db.refresh(row)
    return row


def default_facility_id(db: Session, user_facility_ids: list[uuid.UUID]) -> uuid.UUID:
    """The facility a new row belongs to.

    The caller's own facility when they have one; otherwise the single seeded
    facility. Never a literal.
    """
    if user_facility_ids:
        return user_facility_ids[0]
    facility_id = db.execute(select(Facility.id).order_by(Facility.created_on)).scalars().first()
    if facility_id is None:
        raise Conflict("No facility exists to attach this record to.")
    return facility_id
