"""Shared test fixtures.

Phase 2.4 put the Phase 2.2 and 2.3 endpoints behind RBAC, so those suites now
need a token. Tokens are minted directly through the real token service for a
real seeded user.

Why minting rather than logging in: no seeded account holds a usable password
hash (every row carries the Phase 1.8 `!seed-no-login` sentinel), so
`POST /auth/login` cannot succeed for anyone. Inventing a credential -- or
writing one into the database to make tests pass -- is explicitly forbidden.
Minting a token exercises the genuine issuing and validation path without
fabricating a credential, and the credential gap itself is asserted directly in
tests/test_auth_api.py.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.session import SessionLocal


def _user_id(username: str):
    session = SessionLocal()
    try:
        return session.execute(
            text("SELECT id FROM app_user WHERE user_name = :u"), {"u": username}
        ).scalar_one_or_none()
    finally:
        session.close()


def _headers_for(username: str) -> dict[str, str]:
    user_id = _user_id(username)
    if user_id is None:
        pytest.skip(f"seeded user {username!r} is absent; run `python -m seeds.run_seed`")
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers() -> dict[str, str]:
    """Administrator -- role_type 'admin', holds all 18 module grants."""
    return _headers_for("arjun.menon")


@pytest.fixture(scope="session")
def manager_headers() -> dict[str, str]:
    """Duty Manager -- role_type 'manager', 13 grants, no `user_roles`."""
    return _headers_for("kavya.iyer")


@pytest.fixture(scope="session")
def staff_headers() -> dict[str, str]:
    """Housekeeping -- role_type 'staff'. Belongs to the mobile application."""
    return _headers_for("sneha.pillai")


@pytest.fixture(scope="session")
def technician_headers() -> dict[str, str]:
    """Technician -- seeded with role_type 'staff'. Mobile application."""
    return _headers_for("vikram.rao")


@pytest.fixture(scope="session")
def guest_headers() -> dict[str, str]:
    """Guest -- role_type 'guest'. Separate guest mobile application."""
    return _headers_for("aarav.sharma")


# ---------------------------------------------------------------------------
# Phase 3.0 write fixtures
# ---------------------------------------------------------------------------
# Kept in their own module for readability; re-exported here so pytest picks
# them up for every test in the package. `require_seeded` is deliberately NOT
# re-exported: it is autouse, and each write module opts in explicitly rather
# than making every existing suite depend on it.

from tests.conftest_writes import (  # noqa: E402,F401
    anon_api,
    api,
    cleanup,
    db,
    facility_id,
    free_room,
    guest_id,
    manager_api,
    second_free_room,
    staff_id,
    unique,
)
