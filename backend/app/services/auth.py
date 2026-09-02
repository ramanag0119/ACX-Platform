"""Authentication and authorization queries.

Everything is read live from PostgreSQL. `password_hash` is fetched only
inside `authenticate` and never leaves this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.platform import Platform, is_hms_web_role, platform_for
from app.core.security import has_usable_credential, verify_password
from app.models import AppUser, Role, RoleModule, RoleModulePermission, UserRole
from app.services import access as access_service


class AuthError(Exception):
    """Credential rejected. Deliberately carries no detail about why."""


class PlatformError(Exception):
    """Credential accepted, but this role belongs to another application."""

    def __init__(self, platform: Platform | None, role_types: list[str]):
        self.platform = platform
        self.role_types = role_types
        super().__init__("Role is not permitted on HMS Web.")


@dataclass
class AuthenticatedUser:
    """An HMS Web user plus the authorization data read from the database."""

    id: uuid.UUID
    user_name: str | None
    first_name: str
    last_name: str | None
    email: str | None
    is_staff: int | None
    role_types: list[str]
    platform: Platform
    roles: list[dict] = field(default_factory=list)
    facility_ids: list[uuid.UUID] = field(default_factory=list)
    permissions: list[dict] = field(default_factory=list)

    def may(self, module_name: str, permission: str) -> bool:
        """Does this user hold `permission` ('read'|'write') on `module_name`?"""
        column = "read_access" if permission == "read" else "write_access"
        for entry in self.permissions:
            if entry["module_name"] == module_name:
                return bool(entry[column])
        return False


def _role_types(db: Session, user_id: uuid.UUID) -> list[str]:
    return sorted(
        set(
            db.execute(
                select(Role.role_type)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.app_user_id == user_id)
            ).scalars().all()
        )
    )


def _build(db: Session, user_row, role_types: list[str]) -> AuthenticatedUser:
    hms_web_types = [t for t in role_types if is_hms_web_role(t)]
    return AuthenticatedUser(
        id=user_row.id,
        user_name=user_row.user_name,
        first_name=user_row.first_name,
        last_name=user_row.last_name,
        email=user_row.email,
        is_staff=user_row.is_staff,
        role_types=role_types,
        platform=platform_for(hms_web_types[0]) if hms_web_types else Platform.HMS_WEB,
        roles=access_service.user_roles(db, user_row.id),
        facility_ids=access_service.user_facility_ids(db, user_row.id),
        permissions=access_service.user_permissions(db, user_row.id),
    )


def authenticate(db: Session, username: str, password: str) -> AuthenticatedUser:
    """Verify credentials, then enforce the HMS Web platform boundary.

    Order matters. Credentials are checked FIRST so that a wrong password and
    an unknown username are indistinguishable (both raise `AuthError`). Only a
    caller who already proved they own the account learns that the account
    belongs to a different application.
    """
    user = db.execute(
        select(AppUser).where(AppUser.user_name == username)
    ).scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid username or password.")

    role_types = _role_types(db, user.id)
    if not any(is_hms_web_role(t) for t in role_types):
        platform = platform_for(role_types[0]) if role_types else None
        raise PlatformError(platform, role_types)

    return _build(db, user, role_types)


def load_hms_web_user(db: Session, user_id: uuid.UUID) -> AuthenticatedUser | None:
    """Re-load an authenticated user for a request carrying a valid token.

    Returns None when the user no longer exists OR no longer holds an HMS Web
    role -- a token must not outlive the authority that justified it.
    """
    user = db.get(AppUser, user_id)
    if user is None:
        return None
    role_types = _role_types(db, user.id)
    if not any(is_hms_web_role(t) for t in role_types):
        return None
    return _build(db, user, role_types)


# ---------------------------------------------------------------------------
# Introspection used by the credential-availability report and its test
# ---------------------------------------------------------------------------


def credential_availability(db: Session) -> dict:
    """How many accounts could actually authenticate.

    Phase 2.4 reports this rather than inventing credentials to make login
    succeed.
    """
    hashes = db.execute(select(AppUser.user_name, AppUser.password_hash)).all()
    usable = [u for u, h in hashes if has_usable_credential(h)]
    return {
        "accounts": len(hashes),
        "with_usable_credential": len(usable),
        "usable_usernames": sorted(usable),
    }


def module_names(db: Session) -> set[str]:
    """The real module registry, used to validate RBAC declarations at import."""
    return set(db.execute(select(RoleModule.module_name)).scalars().all())


def role_module_grant_count(db: Session) -> int:
    return db.execute(
        select(func.count()).select_from(RoleModulePermission)
    ).scalar_one()
