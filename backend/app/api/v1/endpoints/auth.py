"""HMS Web authentication (Phase 2.4).

    POST /api/v1/auth/login    username + password -> JWT access token
    GET  /api/v1/auth/me       Bearer token -> the authenticated HMS Web user

PLATFORM BOUNDARY. Only roles whose `role.role_type` is `admin` or `manager`
may authenticate here (see `app.core.platform`). Staff, Technician and Guest
belong to the mobile applications and are rejected with 403 even when their
credentials are correct. No /staff/login, /technician/login or /guest/login
route exists, and none is planned for this phase.

CREDENTIAL AVAILABILITY. No seeded account currently holds a usable password
hash -- every row carries the Phase 1.8 `!seed-no-login` sentinel -- so login
returns 401 for every seeded user. That is the honest state of the data, not a
bug: the seed deliberately never wrote a credential. Provisioning real hashes
is an operational step, documented in docs/PHASE2_4_AUTHENTICATION.md.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import CurrentUser as CurrentUserSchema
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.health import ErrorResponse
from app.core.security import create_access_token
from app.services import auth as service

logger = logging.getLogger("hms.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="HMS Web login",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid username or password"},
        403: {"model": ErrorResponse, "description": "Role belongs to another platform"},
    },
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    try:
        user = service.authenticate(db, payload.username, payload.password)
    except service.AuthError as exc:
        # Identical response for unknown user and wrong password -- the caller
        # learns nothing about which accounts exist. The password is never
        # logged, here or anywhere else.
        logger.info("failed HMS Web login attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except service.PlatformError as exc:
        platform = exc.platform.value if exc.platform else "unknown"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account belongs to the "
                f"{platform.replace('_', ' ')} application and cannot sign in "
                "to HMS Web."
            ),
        ) from exc

    token, expires_in = create_access_token(user.id)
    logger.info("HMS Web login succeeded for user id %s", user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=CurrentUserSchema,
    summary="The authenticated HMS Web user",
    responses={401: {"model": ErrorResponse, "description": "Missing/invalid token"}},
)
def read_current_user(current_user: CurrentUser) -> CurrentUserSchema:
    """Roles and permissions are re-read from PostgreSQL, never taken from the
    token, so this always reflects the user's current authority."""
    return CurrentUserSchema(
        id=current_user.id,
        user_name=current_user.user_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        is_staff=current_user.is_staff,
        platform=current_user.platform.value,
        role_types=current_user.role_types,
        roles=current_user.roles,
        facility_ids=current_user.facility_ids,
        permissions=current_user.permissions,
    )
