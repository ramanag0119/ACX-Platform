"""Phase 2.4 HMS Web authentication and RBAC tests.

Run:  python -m pytest tests/test_auth_api.py -q

Uses real seeded users throughout. No fake user is created, no credential is
invented, and no row is written.

On the credential gap: no seeded account holds a usable password hash, so
`POST /auth/login` cannot succeed for anyone. That is asserted directly
(`test_no_seeded_account_has_a_usable_credential`). To still prove the login
FLOW is correct -- including the platform boundary -- the tests that need a
successful credential check monkeypatch `verify_password`, which simulates an
operator having provisioned a hash. Nothing touches the database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import text

from app.core.config import settings
from app.core.platform import HMS_WEB_ROLE_TYPES, Platform, platform_for
from app.core.security import (
    SEED_NO_LOGIN_SENTINEL,
    create_access_token,
    has_usable_credential,
    hash_password,
    verify_password,
)
from app.db.session import SessionLocal
from app.main import app
from app.services import auth as auth_service

V1 = settings.API_V1_PREFIX
LOGIN = f"{V1}/auth/login"
ME = f"{V1}/auth/me"


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM app_user")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# ---------------------------------------------------------------------------
# The credential limitation, asserted rather than worked around
# ---------------------------------------------------------------------------


def test_no_seeded_account_has_a_usable_credential(db):
    """The headline Phase 2.4 finding.

    `app_user.password_hash` exists as a column, but every seeded row holds the
    Phase 1.8 `!seed-no-login` sentinel or NULL. No account can authenticate
    until an operator provisions a real hash.
    """
    report = auth_service.credential_availability(db)
    assert report["accounts"] == 13
    assert report["with_usable_credential"] == 0
    assert report["usable_usernames"] == []


def test_sentinel_never_verifies(db):
    stored = db.execute(
        text("SELECT password_hash FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    assert stored == SEED_NO_LOGIN_SENTINEL
    for attempt in ("", "password", SEED_NO_LOGIN_SENTINEL, "admin123"):
        assert verify_password(attempt, stored) is False
    assert has_usable_credential(stored) is False


def test_verify_password_never_raises_on_malformed_hashes():
    """A malformed hash is an unusable credential, not a 500."""
    for stored in (None, "", "not-a-hash", "$2b$broken", SEED_NO_LOGIN_SENTINEL):
        assert verify_password("anything", stored) is False


def test_password_hashing_round_trips():
    """The verifier is real bcrypt -- it works the moment a hash is provisioned."""
    hashed = hash_password("correct horse battery staple")
    assert has_usable_credential(hashed)
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.parametrize("username", ["arjun.menon", "kavya.iyer"])
def test_login_currently_fails_for_every_seeded_account(client, username):
    r = client.post(LOGIN, json={"username": username, "password": "anything"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# Login flow -- with a simulated provisioned credential
# ---------------------------------------------------------------------------


@pytest.fixture
def provisioned(monkeypatch):
    """Simulate an operator having set a real password hash.

    Only the verifier is stubbed; user lookup, role loading and the platform
    boundary all still run against the real database.
    """
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, stored: True)


@pytest.mark.parametrize(
    "username,expected_role_type",
    [("arjun.menon", "admin"), ("kavya.iyer", "manager")],
)
def test_hms_web_roles_can_log_in(client, provisioned, username, expected_role_type):
    r = client.post(LOGIN, json={"username": username, "password": "provisioned"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role_types"] == [expected_role_type]


@pytest.mark.parametrize(
    "username,role_type,platform",
    [
        ("sneha.pillai", "staff", "mobile"),          # Housekeeping
        ("vikram.rao", "staff", "mobile"),            # Technician
        ("aarav.sharma", "guest", "guest_mobile"),    # Guest
    ],
)
def test_non_web_platforms_are_rejected_even_with_correct_credentials(
    client, provisioned, db, username, role_type, platform
):
    """The platform boundary, not a password failure: these accounts prove
    ownership and are still refused HMS Web."""
    actual = db.execute(
        text("""SELECT DISTINCT r.role_type FROM app_user u
                JOIN user_role ur ON ur.app_user_id = u.id
                JOIN role r ON r.id = ur.role_id WHERE u.user_name = :n"""),
        {"n": username},
    ).scalars().all()
    assert list(actual) == [role_type], "seeded role_type changed; update the boundary"

    r = client.post(LOGIN, json={"username": username, "password": "provisioned"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    assert platform.replace("_", " ") in r.json()["error"]["message"]


def test_service_account_cannot_use_hms_web(client, provisioned, db):
    """`system_user` is not in the KT handbook and is never interactive."""
    assert db.execute(
        text("SELECT role_type FROM role WHERE name = 'System'")
    ).scalar_one() == "system_user"
    r = client.post(LOGIN, json={"username": "system", "password": "provisioned"})
    assert r.status_code == 403


def test_unknown_user_and_wrong_password_are_indistinguishable(client):
    unknown = client.post(LOGIN, json={"username": "nobody", "password": "x"})
    wrong = client.post(LOGIN, json={"username": "arjun.menon", "password": "x"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json(), "response must not reveal account existence"


@pytest.mark.parametrize(
    "payload",
    [{}, {"username": "arjun.menon"}, {"password": "x"},
     {"username": "", "password": "x"}, {"username": "a", "password": ""}],
)
def test_malformed_login_payload_is_a_validation_error(client, payload):
    r = client.post(LOGIN, json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_login_never_echoes_the_password(client):
    r = client.post(LOGIN, json={"username": "arjun.menon", "password": "hunter2"})
    assert "hunter2" not in r.text


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def test_token_carries_identity_only(db):
    """No role, no permission, no email, no credential in the JWT."""
    user_id = db.execute(
        text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    token, _ = create_access_token(user_id)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert set(payload) == {"sub", "typ", "iat", "exp"}
    assert payload["sub"] == str(user_id)
    blob = str(payload).lower()
    for forbidden in ("password", "hash", "role", "permission", "email", "seed-no-login"):
        assert forbidden not in blob


def test_valid_token_is_accepted(client, admin_headers):
    assert client.get(ME, headers=admin_headers).status_code == 200


def test_missing_token_is_401(client):
    r = client.get(ME)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "header",
    ["", "Bearer", "Bearer ", "Bearer not.a.token", "Basic abc123",
     "Bearer aaaa.bbbb.cccc"],
)
def test_malformed_token_is_401(client, header):
    r = client.get(ME, headers={"Authorization": header})
    assert r.status_code == 401


def test_expired_token_is_401(client, db):
    user_id = db.execute(
        text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    token, _ = create_access_token(user_id, expires_minutes=-1)
    r = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_signed_with_another_key_is_401(client, db):
    user_id = db.execute(
        text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    forged = jwt.encode(
        {"sub": str(user_id), "typ": "access",
         "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())},
        "attacker-key",
        algorithm="HS256",
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_non_access_token_type_is_rejected(client, db):
    """A future refresh token must not be usable as an access token."""
    user_id = db.execute(
        text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    token = jwt.encode(
        {"sub": str(user_id), "typ": "refresh",
         "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_a_deleted_user_is_401(client):
    token, _ = create_access_token(uuid.uuid4())
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_a_non_web_role_is_rejected_at_request_time(client, staff_headers):
    """A valid signature is not enough -- the boundary is re-checked per request,
    so a token cannot outlive the authority that justified it."""
    assert client.get(ME, headers=staff_headers).status_code == 401


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------


def test_me_reports_database_backed_authorization(client, admin_headers, db):
    body = client.get(ME, headers=admin_headers).json()
    assert body["user_name"] == "arjun.menon"
    assert body["platform"] == "hms_web"
    assert body["role_types"] == ["admin"]
    assert [r["role_name"] for r in body["roles"]] == ["Administrator"]
    assert len(body["permissions"]) == db.execute(
        text("""SELECT count(*) FROM role_module_permission p
                JOIN user_role ur ON ur.role_id = p.role_id
                JOIN app_user u ON u.id = ur.app_user_id
                WHERE u.user_name = 'arjun.menon'""")
    ).scalar_one()


def test_me_never_returns_a_credential(client, admin_headers):
    raw = client.get(ME, headers=admin_headers).text.lower()
    for needle in ("password", "hash", "secret", "seed-no-login"):
        assert needle not in raw


def test_manager_me_shows_the_narrower_grant_set(client, manager_headers):
    body = client.get(ME, headers=manager_headers).json()
    assert body["role_types"] == ["manager"]
    modules = {p["module_name"] for p in body["permissions"]}
    assert "employees" in modules
    assert "user_roles" not in modules, "KT handbook: Manager has NO role administration"


# ---------------------------------------------------------------------------
# RBAC on the protected Phase 2.2 / 2.3 endpoints
# ---------------------------------------------------------------------------


PROTECTED = [
    (f"{V1}/users", "employees"),
    (f"{V1}/roles", "user_roles"),
    (f"{V1}/modules", "user_roles"),
    (f"{V1}/permissions", "user_roles"),
    (f"{V1}/facilities", "facility_management"),
    (f"{V1}/properties", "facility_management"),
    (f"{V1}/buildings", "facility_management"),
    (f"{V1}/floors", "facility_management"),
    (f"{V1}/rooms", "facility_management"),
]


@pytest.mark.parametrize("path,module", PROTECTED)
def test_protected_endpoints_require_a_token(client, path, module):
    r = client.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("path,module", PROTECTED)
def test_admin_is_allowed_everywhere(client, admin_headers, path, module):
    assert client.get(path, headers=admin_headers).status_code == 200


@pytest.mark.parametrize("path,module", PROTECTED)
def test_manager_access_follows_the_database_grants(
    client, manager_headers, db, path, module
):
    """Allowed or denied purely by what role_module_permission says."""
    granted = db.execute(
        text("""SELECT count(*) FROM role r
                JOIN role_module_permission p ON p.role_id = r.id
                JOIN role_module m ON m.id = p.module_id
                WHERE r.role_type = 'manager' AND m.module_name = :m
                  AND p.read_access"""),
        {"m": module},
    ).scalar_one() > 0

    r = client.get(path, headers=manager_headers)
    assert r.status_code == (200 if granted else 403), (
        f"{path} ({module}): database says granted={granted}, API said {r.status_code}"
    )
    if not granted:
        assert r.json()["error"]["code"] == "forbidden"
        assert module in r.json()["error"]["message"]


def test_manager_is_denied_role_administration(client, manager_headers):
    """The KT handbook rule, enforced by the data rather than a role-name check."""
    for path in (f"{V1}/roles", f"{V1}/modules", f"{V1}/permissions"):
        assert client.get(path, headers=manager_headers).status_code == 403


def test_manager_is_allowed_employees(client, manager_headers):
    assert client.get(f"{V1}/users", headers=manager_headers).status_code == 200


def test_health_endpoints_stay_public(client):
    """Liveness and readiness must not require a token."""
    assert client.get("/health").status_code == 200
    assert client.get(f"{V1}/health/db").status_code == 200


def test_require_permission_rejects_an_unknown_access_column():
    from app.api.deps import require_permission

    with pytest.raises(ValueError, match="read.*write"):
        require_permission("employees", "delete")


def test_rbac_module_names_are_real_registry_entries(db):
    """Every module this phase gates on must exist in `role_module`."""
    registry = auth_service.module_names(db)
    for _path, module in PROTECTED:
        assert module in registry, f"{module} is not a real role_module row"


# ---------------------------------------------------------------------------
# Platform boundary declaration
# ---------------------------------------------------------------------------


def test_platform_boundary_matches_the_kt_handbook():
    assert HMS_WEB_ROLE_TYPES == {"admin", "manager"}
    assert platform_for("admin") is Platform.HMS_WEB
    assert platform_for("manager") is Platform.HMS_WEB
    assert platform_for("staff") is Platform.MOBILE
    assert platform_for("guest") is Platform.GUEST_MOBILE
    assert platform_for("system_user") is Platform.SERVICE


def test_technician_is_not_a_role_type_in_the_database(db):
    """KT handbook vs database mismatch, asserted so it cannot be forgotten."""
    enum_values = db.execute(
        text("""SELECT e.enumlabel FROM pg_type t JOIN pg_enum e
                ON e.enumtypid = t.oid WHERE t.typname = 'role_type'""")
    ).scalars().all()
    assert "technician" not in enum_values
    assert db.execute(
        text("SELECT role_type FROM role WHERE name = 'Technician'")
    ).scalar_one() == "staff"


def test_no_mobile_or_guest_login_routes_exist(client):
    paths = client.get("/openapi.json").json()["paths"]
    for forbidden in ("/staff/login", "/technician/login", "/guest/login",
                      "/mobile/login", "/auth/register"):
        assert not any(forbidden in p for p in paths)


def test_only_login_and_me_were_added(client):
    auth_paths = {p for p in client.get("/openapi.json").json()["paths"] if "/auth" in p}
    assert auth_paths == {LOGIN, ME}


# ---------------------------------------------------------------------------
# Configuration safety
# ---------------------------------------------------------------------------


def test_jwt_settings_come_from_configuration():
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_dev_secret_is_refused_outside_development(monkeypatch):
    """The shipped development key can never silently sign production tokens."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", settings.DEV_JWT_SECRET)
    with pytest.raises(RuntimeError, match="development default"):
        settings.assert_production_ready()


def test_openapi_documents_the_bearer_scheme(client):
    schema = client.get("/openapi.json").json()
    assert "HTTPBearer" in schema.get("components", {}).get("securitySchemes", {})
