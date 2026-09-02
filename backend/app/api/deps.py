"""Shared FastAPI dependencies.

This module contains no connection logic of its own. The engine, sessionmaker
and request-scoped `get_db` generator already exist in `app.db.session` and are
re-exposed here as a typed annotation, so routers never import the session
layer directly.

Phase 2.4 adds authentication and authorization dependencies. Both are defined
once here and reused; no endpoint re-implements token or permission handling.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.services import auth as auth_service
from app.services.auth import AuthenticatedUser

#: Request-scoped SQLAlchemy session. Use as `db: DbSession` in any endpoint.
DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False so a missing header produces OUR 401 envelope rather than
# Starlette's bare 403.
_bearer = HTTPBearer(auto_error=False, description="HMS Web JWT access token")

UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> AuthenticatedUser:
    """Resolve the caller from a Bearer token.

    1. read the token   2. validate signature/expiry/type   3. extract identity
    4. load the user from PostgreSQL   5. confirm they are still an HMS Web user

    Authorization data is re-read from the database every request. Nothing is
    trusted from the token beyond the subject id, so a role change or a
    revoked assignment takes effect immediately instead of at token expiry.
    """
    if credentials is None or not credentials.credentials:
        raise UNAUTHENTICATED
    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise UNAUTHENTICATED from exc

    user = auth_service.load_hms_web_user(db, user_id)
    if user is None:
        # Deleted user, or one who no longer holds an HMS Web role.
        raise UNAUTHENTICATED
    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_permission(module_name: str, permission: str = "read"):
    """Build a dependency enforcing one database-backed module grant.

    `module_name` MUST be a real `role_module.module_name` and `permission` is
    the column on `role_module_permission` -- 'read' -> read_access,
    'write' -> write_access. Nothing is hardcoded beyond those two column
    names; the grant itself is whatever the database says for the caller's
    roles.

    401 when unauthenticated, 403 when authenticated but not granted.
    """
    if permission not in {"read", "write"}:
        raise ValueError(
            f"permission must be 'read' or 'write' (role_module_permission "
            f"has no other access column); got {permission!r}"
        )

    def dependency(current_user: CurrentUser) -> AuthenticatedUser:
        if not current_user.may(module_name, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role does not grant {permission} access to "
                    f"the '{module_name}' module."
                ),
            )
        return current_user

    return dependency


__all__ = [
    "DbSession",
    "get_db",
    "get_current_user",
    "CurrentUser",
    "require_permission",
]
