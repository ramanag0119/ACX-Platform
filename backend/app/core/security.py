"""Password verification and JWT issuing/validation.

Nothing here reads or writes the database, and nothing here ever logs a
password, a hash or a token.

CREDENTIAL STATE OF THIS INSTALL: `app_user.password_hash` exists as a column,
but every seeded row holds the literal `!seed-no-login` (or NULL). That value
is not a valid bcrypt hash and cannot be produced by any hashing scheme, so
`verify_password` returns False for every seeded account by design -- the
Phase 1.8 seed deliberately never wrote a usable credential. See
`docs/PHASE2_4_AUTHENTICATION.md`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("hms.auth")

#: Marker written by the Phase 1.8 seed. Present == "this account has no
#: usable credential", never == "this password is correct".
SEED_NO_LOGIN_SENTINEL = "!seed-no-login"

TOKEN_TYPE = "access"  # nbf/typ guard, so a future refresh token cannot be reused here


class TokenError(Exception):
    """Raised when a token is absent, malformed, expired or not ours."""


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Provided so credentials can be provisioned later by an operator tool.

    Not used by the API: Phase 2.4 is read-only with respect to user rows.
    """
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, stored_hash: str | None) -> bool:
    """Constant-failure verification against a stored bcrypt hash.

    Returns False -- never raises -- for NULL hashes, the seed sentinel, and
    anything else that is not a well-formed bcrypt digest.
    """
    if not stored_hash or stored_hash == SEED_NO_LOGIN_SENTINEL:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode(), stored_hash.encode())
    except (ValueError, TypeError):
        # A malformed hash is an unusable credential, not a server error.
        # The value itself is never logged.
        logger.warning("stored password hash is not a valid bcrypt digest")
        return False


def has_usable_credential(stored_hash: str | None) -> bool:
    """Whether an account could ever authenticate, ignoring the password."""
    if not stored_hash or stored_hash == SEED_NO_LOGIN_SENTINEL:
        return False
    return stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: uuid.UUID, *, expires_minutes: int | None = None
) -> tuple[str, int]:
    """Mint an access token carrying identity ONLY.

    The subject is the user id and nothing else. No role, no permission, no
    email, and certainly no credential goes into the token: authorization is
    re-read from PostgreSQL on every request, so a token cannot carry stale or
    forged privileges.

    Returns (token, expires_in_seconds).
    """
    settings.assert_production_ready()
    minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "typ": TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int((expires_at - now).total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    """Validate signature, expiry and type; return the subject user id."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        # Covers bad signature, malformed token and expiry alike.
        raise TokenError("Token is invalid or expired.") from exc

    if payload.get("typ") != TOKEN_TYPE:
        raise TokenError("Token is not an access token.")

    subject = payload.get("sub")
    if not subject:
        raise TokenError("Token has no subject.")
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise TokenError("Token subject is not a valid user id.") from exc
