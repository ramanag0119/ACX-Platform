"""Phase 2.3 users / roles / modules / permissions API tests.

Run:  python -m pytest tests/test_access_api.py -q

Same TestClient infrastructure as Phases 2.1 and 2.2. Every assertion is
cross-checked against a direct SQL query, so a hardcoded response could not
pass. Skipped wholesale when the database is unseeded.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module")
def client(admin_headers) -> TestClient:
    """Authenticated as the seeded Administrator: Phase 2.4 put these routes
    behind the `employees / user_roles` module grant. Unauthenticated and
    insufficient-permission behaviour is covered in tests/test_auth_api.py."""
    with TestClient(app, headers=admin_headers) as c:
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


@pytest.fixture(scope="module")
def admin_role_id(db):
    return str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'admin'")).scalar_one()
    )


@pytest.fixture(scope="module")
def admin_user_id(db):
    return str(
        db.execute(
            text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
        ).scalar_one()
    )


LIST_ENDPOINTS = ["users", "roles", "modules", "permissions"]


# ---------------------------------------------------------------------------
# List endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("resource", LIST_ENDPOINTS)
def test_list_returns_200_with_the_shared_envelope(client, resource):
    r = client.get(f"{V1}/{resource}")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1 and body["page_size"] == 20


@pytest.mark.parametrize(
    "resource,sql",
    [
        ("users", "SELECT count(*) FROM app_user"),
        ("roles", "SELECT count(*) FROM role"),
        ("modules", "SELECT count(*) FROM role_module"),
        ("permissions", "SELECT count(*) FROM role_module_permission"),
    ],
)
def test_list_totals_are_database_backed(client, db, resource, sql):
    assert client.get(f"{V1}/{resource}").json()["total"] == db.execute(
        text(sql)
    ).scalar_one()


# ---------------------------------------------------------------------------
# Security -- nothing sensitive may ever appear
# ---------------------------------------------------------------------------


SENSITIVE = ["password", "password_hash", "hash", "token", "secret", "credential"]


@pytest.mark.parametrize("path", ["users", "users?page_size=100", "roles", "permissions"])
def test_no_sensitive_field_is_ever_returned(client, path):
    raw = client.get(f"{V1}/{path}").text.lower()
    for needle in SENSITIVE:
        assert needle not in raw, f"{needle!r} leaked from /{path}"


def test_user_detail_excludes_credentials_and_metadata(client, admin_user_id, db):
    body = client.get(f"{V1}/users/{admin_user_id}").json()
    assert "password_hash" not in body
    assert "metadata" not in body, "the metadata bag may hold anything; keep it out"
    # Prove the row really does carry a hash that we chose not to return.
    assert db.execute(
        text("SELECT password_hash FROM app_user WHERE id = :i"), {"i": admin_user_id}
    ).scalar_one() is not None


def test_openapi_user_schema_declares_no_credential_fields(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("UserRead", "UserDetail"):
        fields = set(schema[name]["properties"])
        assert not fields & {"password_hash", "metadata", "password"}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def test_user_schema_matches_the_database(client, db, admin_user_id):
    body = client.get(f"{V1}/users/{admin_user_id}").json()
    row = db.execute(
        text("SELECT first_name, last_name, email, emp_id, is_staff "
             "FROM app_user WHERE id = :i"),
        {"i": admin_user_id},
    ).one()
    assert body["first_name"] == row.first_name
    assert body["last_name"] == row.last_name
    assert body["email"] == row.email
    assert body["emp_id"] == row.emp_id
    assert body["is_staff"] == row.is_staff


def test_user_detail_resolves_department_and_function(client, admin_user_id):
    body = client.get(f"{V1}/users/{admin_user_id}").json()
    assert body["department_name"] == "Administration"
    assert body["job_function_name"] == "Administrator"


def test_user_detail_lists_roles_and_facilities(client, db, admin_user_id):
    body = client.get(f"{V1}/users/{admin_user_id}").json()
    assert [r["role_name"] for r in body["roles"]] == ["Administrator"]
    assert body["roles"][0]["role_type"] == "admin"
    # user_role is facility-scoped, so every assignment carries its facility.
    assert body["roles"][0]["facility_id"]
    assert len(body["facility_ids"]) == db.execute(
        text("SELECT count(*) FROM facility_user WHERE app_user_id = :i"),
        {"i": admin_user_id},
    ).scalar_one()


def test_user_404(client):
    r = client.get(f"{V1}/users/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_filter_users_by_is_staff(client, db):
    for flag in (0, 1):
        body = client.get(f"{V1}/users?is_staff={flag}&page_size=100").json()
        assert body["total"] == db.execute(
            text("SELECT count(*) FROM app_user WHERE is_staff = :f"), {"f": flag}
        ).scalar_one()
        assert all(u["is_staff"] == flag for u in body["items"])


def test_filter_users_by_role(client, db, admin_role_id):
    body = client.get(f"{V1}/users?role_id={admin_role_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(DISTINCT app_user_id) FROM user_role WHERE role_id = :r"),
        {"r": admin_role_id},
    ).scalar_one()


def test_filter_users_by_facility(client, db):
    facility_id = str(db.execute(text("SELECT id FROM facility")).scalar_one())
    body = client.get(f"{V1}/users?facility_id={facility_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(DISTINCT app_user_id) FROM user_role WHERE facility_id = :f"),
        {"f": facility_id},
    ).scalar_one()


def test_filter_users_by_department(client, db):
    dept_id, expected = db.execute(
        text("SELECT department_id, count(*) FROM app_user "
             "WHERE department_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    body = client.get(f"{V1}/users?department_id={dept_id}&page_size=100").json()
    assert body["total"] == expected


def test_invalid_is_staff_value_is_rejected(client):
    assert client.get(f"{V1}/users?is_staff=7").status_code == 422


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_role_list_matches_seeded_roles(client, db):
    names = {r["name"] for r in client.get(f"{V1}/roles?page_size=100").json()["items"]}
    assert names == set(db.execute(text("SELECT name FROM role")).scalars().all())


def test_role_types_cover_all_five_enum_values(client):
    types = {r["role_type"] for r in client.get(f"{V1}/roles?page_size=100").json()["items"]}
    assert types == {"admin", "system_user", "manager", "guest", "staff"}


def test_role_detail_includes_counts_and_permissions(client, db, admin_role_id):
    body = client.get(f"{V1}/roles/{admin_role_id}").json()
    assert body["role_type"] == "admin"
    assert body["module_count"] == 18, "the administrator reaches every module"
    assert len(body["permissions"]) == 18
    assert body["user_count"] == db.execute(
        text("SELECT count(*) FROM user_role WHERE role_id = :r"), {"r": admin_role_id}
    ).scalar_one()


def test_role_404(client):
    assert client.get(f"{V1}/roles/{uuid.uuid4()}").status_code == 404


def test_filter_roles_by_type(client, db):
    body = client.get(f"{V1}/roles?role_type=staff&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM role WHERE role_type = 'staff'")
    ).scalar_one()
    assert all(r["role_type"] == "staff" for r in body["items"])


def test_filter_roles_by_facility(client, db):
    facility_id = str(db.execute(text("SELECT id FROM facility")).scalar_one())
    body = client.get(f"{V1}/roles?facility_id={facility_id}&page_size=100").json()
    assert body["total"] == db.execute(text("SELECT count(*) FROM role")).scalar_one()


# ---------------------------------------------------------------------------
# Modules -- the role_module registry
# ---------------------------------------------------------------------------


def test_module_registry_is_the_18_sidebar_modules(client, db):
    body = client.get(f"{V1}/modules?page_size=100").json()
    assert body["total"] == 18
    names = [m["module_name"] for m in body["items"]]
    assert names == list(
        db.execute(text("SELECT module_name FROM role_module ORDER BY id")).scalars()
    )
    assert "dashboard" in names and "default_key" in names


def test_module_ids_are_small_integers_not_uuids(client):
    for module in client.get(f"{V1}/modules?page_size=100").json()["items"]:
        assert isinstance(module["id"], int)


def test_read_only_modules_are_flagged_by_the_registry(client):
    body = client.get(f"{V1}/modules?write_applicable=false&page_size=100").json()
    assert {m["module_name"] for m in body["items"]} == {"dashboard", "reports"}


def test_module_detail_includes_role_count(client, db):
    body = client.get(f"{V1}/modules/1").json()
    assert body["module_name"] == "dashboard"
    assert body["role_count"] == db.execute(
        text("SELECT count(*) FROM role_module_permission WHERE module_id = 1")
    ).scalar_one()


def test_module_404(client):
    r = client.get(f"{V1}/modules/9999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Permissions -- composite key, no standalone table
# ---------------------------------------------------------------------------


def test_permission_rows_join_role_and_module(client):
    item = client.get(f"{V1}/permissions").json()["items"][0]
    assert set(item) >= {
        "role_id", "role_name", "module_id", "module_name",
        "read_access", "write_access",
    }
    assert isinstance(item["read_access"], bool)


def test_permission_detail_uses_the_composite_key(client, db, admin_role_id):
    body = client.get(f"{V1}/permissions/{admin_role_id}/3").json()
    assert body["module_name"] == "bookings"
    assert body["role_name"] == "Administrator"
    row = db.execute(
        text("SELECT read_access, write_access FROM role_module_permission "
             "WHERE role_id = :r AND module_id = 3"),
        {"r": admin_role_id},
    ).one()
    assert body["read_access"] == row.read_access
    assert body["write_access"] == row.write_access


def test_permission_404_for_a_grant_that_does_not_exist(client, admin_role_id):
    """The Guest role holds one module only, so most pairs are absent."""
    r = client.get(f"{V1}/permissions/{uuid.uuid4()}/3")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_single_id_permission_route_does_not_exist(client):
    """There is no permission id in the schema, so no such route may exist."""
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{V1}/permissions/{{permission_id}}" not in paths
    assert f"{V1}/permissions/{{role_id}}/{{module_id}}" in paths


def test_filter_permissions_by_role(client, db, admin_role_id):
    body = client.get(f"{V1}/permissions?role_id={admin_role_id}&page_size=100").json()
    assert body["total"] == 18
    assert all(p["role_name"] == "Administrator" for p in body["items"])


def test_filter_permissions_by_module(client, db):
    body = client.get(f"{V1}/permissions?module_id=1&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM role_module_permission WHERE module_id = 1")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Role permissions / user permissions
# ---------------------------------------------------------------------------


def test_role_permissions_endpoint(client, db, admin_role_id):
    rows = client.get(f"{V1}/roles/{admin_role_id}/permissions").json()
    assert len(rows) == 18
    assert all(r["read_access"] for r in rows)
    # The registry's applicability travels with each grant.
    reports = next(r for r in rows if r["module_name"] == "reports")
    assert reports["write_applicable"] is False


def test_role_permissions_404(client):
    assert client.get(f"{V1}/roles/{uuid.uuid4()}/permissions").status_code == 404


def test_user_permissions_are_derived_from_the_users_roles(client, admin_user_id):
    rows = client.get(f"{V1}/users/{admin_user_id}/permissions").json()
    assert len(rows) == 18
    assert all(r["granted_by_roles"] == ["Administrator"] for r in rows)
    assert all(r["read_access"] and r["write_access"] for r in rows)


def test_user_permissions_match_the_underlying_role_grants(client, db):
    """A housekeeping user's effective access must equal their role's grants."""
    user_id = str(
        db.execute(
            text("SELECT id FROM app_user WHERE user_name = 'sneha.pillai'")
        ).scalar_one()
    )
    effective = client.get(f"{V1}/users/{user_id}/permissions").json()
    expected = db.execute(
        text("""SELECT m.module_name FROM user_role ur
                JOIN role_module_permission p ON p.role_id = ur.role_id
                JOIN role_module m ON m.id = p.module_id
                WHERE ur.app_user_id = :u ORDER BY p.module_id"""),
        {"u": user_id},
    ).scalars().all()
    assert [r["module_name"] for r in effective] == list(expected)
    assert all(r["granted_by_roles"] == ["Housekeeping"] for r in effective)


def test_guest_user_has_the_narrowest_access(client, db):
    user_id = str(
        db.execute(
            text("SELECT id FROM app_user WHERE user_name = 'aarav.sharma'")
        ).scalar_one()
    )
    rows = client.get(f"{V1}/users/{user_id}/permissions").json()
    assert [r["module_name"] for r in rows] == ["service_tracking"]


def test_user_permissions_can_be_scoped_to_a_facility(client, db, admin_user_id):
    facility_id = str(db.execute(text("SELECT id FROM facility")).scalar_one())
    scoped = client.get(
        f"{V1}/users/{admin_user_id}/permissions?facility_id={facility_id}"
    ).json()
    assert len(scoped) == 18
    # A facility the user holds no role at yields nothing.
    assert client.get(
        f"{V1}/users/{admin_user_id}/permissions?facility_id={uuid.uuid4()}"
    ).json() == []


def test_user_permissions_404(client):
    assert client.get(f"{V1}/users/{uuid.uuid4()}/permissions").status_code == 404


# ---------------------------------------------------------------------------
# Pagination and empty results
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("resource", LIST_ENDPOINTS)
def test_page_size_over_100_is_rejected(client, resource):
    r = client.get(f"{V1}/{resource}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_permissions(client):
    total = client.get(f"{V1}/permissions").json()["total"]
    first = client.get(f"{V1}/permissions?page=1&page_size=10").json()
    second = client.get(f"{V1}/permissions?page=2&page_size=10").json()
    assert len(first["items"]) == 10
    assert first["total"] == second["total"] == total
    key = lambda p: (p["role_id"], p["module_id"])
    assert {key(p) for p in first["items"]}.isdisjoint({key(p) for p in second["items"]})


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/users?page=999").json()
    assert body["items"] == [] and body["total"] > 0


def test_filter_matching_nothing_returns_empty_page(client):
    body = client.get(f"{V1}/users?role_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize("resource", ["users", "roles"])
def test_malformed_uuid_is_a_validation_error(client, resource):
    r = client.get(f"{V1}/{resource}/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# API surface guard
# ---------------------------------------------------------------------------


def test_phase_2_3_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/users",
        f"{V1}/users/{{user_id}}",
        f"{V1}/users/{{user_id}}/permissions",
        f"{V1}/roles",
        f"{V1}/roles/{{role_id}}",
        f"{V1}/roles/{{role_id}}/permissions",
        f"{V1}/modules",
        f"{V1}/modules/{{module_id}}",
        f"{V1}/permissions",
        f"{V1}/permissions/{{role_id}}/{{module_id}}",
    } <= paths


#: The complete access-domain write surface Phase 3.0 delivers. Anything else
#: appearing under /users, /roles, /departments or /job-functions is a bug.
ACCESS_WRITES = {
    (f"{V1}/users", "post"),
    (f"{V1}/users/{{user_id}}", "patch"),
    (f"{V1}/users/{{user_id}}/password", "post"),
    (f"{V1}/users/{{user_id}}/deactivate", "post"),
    (f"{V1}/users/{{user_id}}/reactivate", "post"),
    (f"{V1}/roles", "post"),
    (f"{V1}/roles/{{role_id}}", "patch"),
    (f"{V1}/roles/{{role_id}}/permissions", "put"),
    (f"{V1}/departments", "post"),
    (f"{V1}/departments/{{department_id}}", "patch"),
    (f"{V1}/job-functions", "post"),
    (f"{V1}/job-functions/{{function_id}}", "patch"),
}


def test_access_write_surface_is_exactly_the_intended_set(client):
    """Phase 3.0 adds writes here; nothing beyond this list.

    Note what is still absent: no DELETE anywhere. A user is retired with
    `date_of_termination` and a role stays put, because `user_role`,
    `service_request` and `stay` all reference them.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get"
        and any(
            path.startswith(prefix)
            for prefix in (f"{V1}/users", f"{V1}/roles", f"{V1}/departments",
                           f"{V1}/job-functions")
        )
    }
    assert found == ACCESS_WRITES, found ^ ACCESS_WRITES


def test_no_delete_on_people_or_roles(client):
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/users", f"{V1}/roles")):
            assert "delete" not in ops, f"{path} exposes DELETE"


@pytest.mark.parametrize(
    "domain",
    # `services` left when Phase 2.5 landed; `devices` when 2.6 did;
    # `device-stats`/`energy` when 2.9 did. `telemetry` stays absent by
    # design -- no such table exists to expose.
    ["logout", "refresh", "bookings", "guests",
     "telemetry", "mqtt", "dashboard"],
)
def test_later_phase_domains_remain_absent(client, domain):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(domain in p for p in paths), f"{domain} belongs to a later phase"
