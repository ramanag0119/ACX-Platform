"""Phase 3.0 write tests: users, roles, permissions, departments, functions.

Run:  python -m pytest tests/test_access_write_api.py -q

Every test creates its own rows and deletes them again, so the seeded 1,792
records are untouched. Each workflow is verified against PostgreSQL directly --
a fake success response could not pass.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX

pytestmark = pytest.mark.usefixtures("require_seeded")


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM app_user")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


def _writable_module(db) -> int:
    """A module whose `write_applicable` is true -- read from the registry."""
    return db.execute(
        text("SELECT id FROM role_module WHERE write_applicable IS TRUE ORDER BY id LIMIT 1")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Departments and job functions
# ---------------------------------------------------------------------------


def test_create_department_persists_to_postgres(api, db, unique, cleanup):
    name = f"Test Dept {unique}"
    r = api.post(f"{V1}/departments", json={"department_name": name})
    assert r.status_code == 201
    body = r.json()
    cleanup.add("department", body["id"])

    # The row is really there, with the facility and audit columns filled in.
    row = db.execute(
        text("SELECT department_name, facility_id, created_by, status "
             "FROM department WHERE id = :i"),
        {"i": body["id"]},
    ).one()
    assert row.department_name == name
    assert row.facility_id is not None
    assert row.created_by is not None
    assert row.status == 1


def test_created_department_appears_in_the_list_endpoint(api, unique, cleanup):
    name = f"Listed Dept {unique}"
    created = api.post(f"{V1}/departments", json={"department_name": name}).json()
    cleanup.add("department", created["id"])

    body = api.get(f"{V1}/departments?page_size=100").json()
    assert name in [item["department_name"] for item in body["items"]]


def test_duplicate_department_is_409(api, unique, cleanup):
    name = f"Dup Dept {unique}"
    first = api.post(f"{V1}/departments", json={"department_name": name}).json()
    cleanup.add("department", first["id"])

    r = api.post(f"{V1}/departments", json={"department_name": name})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_update_department_persists(api, db, unique, cleanup):
    created = api.post(f"{V1}/departments", json={"department_name": f"Old {unique}"}).json()
    cleanup.add("department", created["id"])

    r = api.patch(
        f"{V1}/departments/{created['id']}", json={"department_name": f"New {unique}"}
    )
    assert r.status_code == 200
    assert db.execute(
        text("SELECT department_name FROM department WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == f"New {unique}"


def test_update_unknown_department_is_404(api):
    r = api.patch(f"{V1}/departments/{uuid.uuid4()}", json={"department_name": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_create_job_function_persists(api, db, unique, cleanup):
    r = api.post(f"{V1}/job-functions", json={"function_name": f"Test Fn {unique}"})
    assert r.status_code == 201
    cleanup.add("job_function", r.json()["id"])
    assert db.execute(
        text("SELECT count(*) FROM job_function WHERE id = :i"), {"i": r.json()["id"]}
    ).scalar_one() == 1


# ---------------------------------------------------------------------------
# Roles and the permission matrix
# ---------------------------------------------------------------------------


def test_create_role_with_permissions_persists_both_tables(api, db, unique, cleanup):
    module_id = _writable_module(db)
    r = api.post(
        f"{V1}/roles",
        json={
            "name": f"Test Role {unique}",
            "role_type": "staff",
            "permissions": [
                {"module_id": module_id, "read_access": True, "write_access": True}
            ],
        },
    )
    assert r.status_code == 201
    role_id = r.json()["id"]
    cleanup.sql("DELETE FROM role_module_permission WHERE role_id = :value",
                {"value": role_id})
    cleanup.add("role", role_id)

    grant = db.execute(
        text("SELECT read_access, write_access FROM role_module_permission "
             "WHERE role_id = :r AND module_id = :m"),
        {"r": role_id, "m": module_id},
    ).one()
    assert grant.read_access is True
    assert grant.write_access is True


def test_replace_permission_matrix_is_idempotent_and_persists(api, db, unique, cleanup):
    module_id = _writable_module(db)
    role_id = api.post(f"{V1}/roles", json={"name": f"Matrix Role {unique}"}).json()["id"]
    cleanup.sql("DELETE FROM role_module_permission WHERE role_id = :value",
                {"value": role_id})
    cleanup.add("role", role_id)

    payload = {"permissions": [{"module_id": module_id, "read_access": True,
                                "write_access": False}]}
    first = api.put(f"{V1}/roles/{role_id}/permissions", json=payload)
    assert first.status_code == 200
    second = api.put(f"{V1}/roles/{role_id}/permissions", json=payload)
    assert second.status_code == 200

    # Upsert, not insert: still exactly one row for that (role, module).
    assert db.execute(
        text("SELECT count(*) FROM role_module_permission "
             "WHERE role_id = :r AND module_id = :m"),
        {"r": role_id, "m": module_id},
    ).scalar_one() == 1


def test_write_without_read_is_rejected(api, db, unique, cleanup):
    module_id = _writable_module(db)
    role_id = api.post(f"{V1}/roles", json={"name": f"Bad Matrix {unique}"}).json()["id"]
    cleanup.sql("DELETE FROM role_module_permission WHERE role_id = :value",
                {"value": role_id})
    cleanup.add("role", role_id)

    r = api.put(
        f"{V1}/roles/{role_id}/permissions",
        json={"permissions": [{"module_id": module_id, "read_access": False,
                               "write_access": True}]},
    )
    assert r.status_code == 422
    assert "read access" in r.json()["error"]["message"]


def test_write_on_a_read_only_module_is_rejected(api, db, unique, cleanup):
    """`role_module.write_applicable` is false for dashboard and reports."""
    module_id = db.execute(
        text("SELECT id FROM role_module WHERE write_applicable IS FALSE ORDER BY id LIMIT 1")
    ).scalar_one()
    role_id = api.post(f"{V1}/roles", json={"name": f"RO Module {unique}"}).json()["id"]
    cleanup.sql("DELETE FROM role_module_permission WHERE role_id = :value",
                {"value": role_id})
    cleanup.add("role", role_id)

    r = api.put(
        f"{V1}/roles/{role_id}/permissions",
        json={"permissions": [{"module_id": module_id, "read_access": True,
                               "write_access": True}]},
    )
    assert r.status_code == 422
    assert "does not support write" in r.json()["error"]["message"]


def test_unknown_module_in_matrix_is_rejected(api, unique, cleanup):
    role_id = api.post(f"{V1}/roles", json={"name": f"Ghost Module {unique}"}).json()["id"]
    cleanup.add("role", role_id)
    r = api.put(
        f"{V1}/roles/{role_id}/permissions",
        json={"permissions": [{"module_id": 9999, "read_access": True}]},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _new_user_payload(unique: str, **overrides) -> dict:
    payload = {
        "first_name": "Write",
        "last_name": "Test",
        "phone_number": "+919000000001",
        "email": f"write.test{unique}@example.test",
        "is_staff": 1,
    }
    payload.update(overrides)
    return payload


def test_create_user_persists_and_generates_a_uid(api, db, unique, cleanup):
    r = api.post(f"{V1}/users", json=_new_user_payload(unique))
    assert r.status_code == 201
    body = r.json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value", {"value": body["id"]})
    cleanup.add("app_user", body["id"])

    assert body["user_uid"], "a uid must be generated when none is supplied"
    row = db.execute(
        text("SELECT first_name, phone_number, created_by FROM app_user WHERE id = :i"),
        {"i": body["id"]},
    ).one()
    assert row.first_name == "Write"
    assert row.created_by is not None


def test_create_user_never_returns_the_credential(api, unique, cleanup):
    r = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=f"cred.test{unique}",
                               password="SecurePass#2026"),
    )
    assert r.status_code == 201
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": r.json()["id"]})
    cleanup.add("app_user", r.json()["id"])

    lowered = r.text.lower()
    assert "password" not in lowered
    assert "securepass" not in lowered
    assert "hash" not in lowered


def test_password_is_stored_as_a_bcrypt_hash_not_plaintext(api, db, unique, cleanup):
    created = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=f"hash.test{unique}",
                               password="SecurePass#2026"),
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])

    stored = db.execute(
        text("SELECT password_hash FROM app_user WHERE id = :i"), {"i": created["id"]}
    ).scalar_one()
    assert stored != "SecurePass#2026"
    assert stored.startswith("$2"), "bcrypt hashes start with $2"


def test_a_user_created_with_a_manager_role_can_actually_log_in(
    api, db, unique, cleanup, anon_api
):
    """The whole loop, end to end.

    Phase 2.4 reported that no seeded account holds a usable password. This
    proves the credential path works for a user created through the API,
    without touching a single seeded row.
    """
    module_id = _writable_module(db)
    role_id = api.post(
        f"{V1}/roles",
        json={
            "name": f"Login Role {unique}",
            # HMS Web is admin/manager only -- Phase 2.4's platform boundary.
            "role_type": "manager",
            "permissions": [{"module_id": module_id, "read_access": True}],
        },
    ).json()["id"]
    cleanup.sql("DELETE FROM role_module_permission WHERE role_id = :value",
                {"value": role_id})

    username = f"login.test{unique}"
    password = "LoginTest#2026"
    created = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=username, password=password,
                               role_ids=[role_id]),
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])
    cleanup.add("role", role_id)

    r = anon_api.post(f"{V1}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()
    assert token["access_token"] and token["token_type"] == "bearer"

    # And the token really works.
    me = anon_api.get(
        f"{V1}/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["user_name"] == username
    assert me.json()["platform"] == "hms_web"


def test_wrong_password_is_401(api, db, unique, cleanup, anon_api):
    username = f"badpass.test{unique}"
    created = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=username, password="RightPass#2026"),
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])

    r = anon_api.post(
        f"{V1}/auth/login", json={"username": username, "password": "WrongPass#2026"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_a_staff_role_still_cannot_reach_hms_web(api, db, unique, cleanup, anon_api):
    """Creating a login does not bypass the platform boundary."""
    role_id = api.post(
        f"{V1}/roles", json={"name": f"Mobile Role {unique}", "role_type": "staff"}
    ).json()["id"]
    username = f"mobile.test{unique}"
    created = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=username, password="MobilePass#2026",
                               role_ids=[role_id]),
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])
    cleanup.add("role", role_id)

    r = anon_api.post(
        f"{V1}/auth/login", json={"username": username, "password": "MobilePass#2026"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_duplicate_username_is_409(api, unique, cleanup):
    username = f"dup.user{unique}"
    first = api.post(
        f"{V1}/users", json=_new_user_payload(unique, user_name=username)
    ).json()
    cleanup.add("app_user", first["id"])

    r = api.post(f"{V1}/users", json=_new_user_payload(unique, user_name=username))
    assert r.status_code == 409


def test_role_assignment_writes_user_role_rows(api, db, unique, cleanup):
    role_id = api.post(f"{V1}/roles", json={"name": f"Assigned Role {unique}"}).json()["id"]
    created = api.post(
        f"{V1}/users", json=_new_user_payload(unique, role_ids=[role_id])
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])
    cleanup.add("role", role_id)

    assert db.execute(
        text("SELECT count(*) FROM user_role WHERE app_user_id = :u AND role_id = :r"),
        {"u": created["id"], "r": role_id},
    ).scalar_one() == 1
    assert [role["role_id"] for role in created["roles"]] == [role_id]


def test_patch_replaces_roles_rather_than_appending(api, db, unique, cleanup):
    first_role = api.post(f"{V1}/roles", json={"name": f"First {unique}"}).json()["id"]
    second_role = api.post(f"{V1}/roles", json={"name": f"Second {unique}"}).json()["id"]
    created = api.post(
        f"{V1}/users", json=_new_user_payload(unique, role_ids=[first_role])
    ).json()
    cleanup.sql("DELETE FROM user_role WHERE app_user_id = :value",
                {"value": created["id"]})
    cleanup.add("app_user", created["id"])
    cleanup.add("role", first_role)
    cleanup.add("role", second_role)

    api.patch(f"{V1}/users/{created['id']}", json={"role_ids": [second_role]})
    rows = db.execute(
        text("SELECT role_id FROM user_role WHERE app_user_id = :u"),
        {"u": created["id"]},
    ).scalars().all()
    assert [str(r) for r in rows] == [second_role]


def test_patch_only_changes_what_was_sent(api, db, unique, cleanup):
    created = api.post(
        f"{V1}/users", json=_new_user_payload(unique, address="Original address")
    ).json()
    cleanup.add("app_user", created["id"])

    api.patch(f"{V1}/users/{created['id']}", json={"last_name": "Changed"})
    row = db.execute(
        text("SELECT last_name, address, first_name FROM app_user WHERE id = :i"),
        {"i": created["id"]},
    ).one()
    assert row.last_name == "Changed"
    assert row.address == "Original address", "an omitted field must not be nulled"
    assert row.first_name == "Write"


def test_deactivate_sets_a_termination_date_and_keeps_the_row(api, db, unique, cleanup):
    created = api.post(f"{V1}/users", json=_new_user_payload(unique)).json()
    cleanup.add("app_user", created["id"])

    r = api.post(f"{V1}/users/{created['id']}/deactivate")
    assert r.status_code == 200
    assert db.execute(
        text("SELECT date_of_termination FROM app_user WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() is not None

    api.post(f"{V1}/users/{created['id']}/reactivate")
    assert db.execute(
        text("SELECT date_of_termination FROM app_user WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() is None


def test_set_password_endpoint_persists_a_new_hash(api, db, unique, cleanup, anon_api):
    username = f"reset.test{unique}"
    created = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, user_name=username, password="FirstPass#2026"),
    ).json()
    cleanup.add("app_user", created["id"])

    before = db.execute(
        text("SELECT password_hash FROM app_user WHERE id = :i"), {"i": created["id"]}
    ).scalar_one()

    r = api.post(f"{V1}/users/{created['id']}/password", json={"password": "SecondPass#2026"})
    assert r.status_code == 204

    after = db.execute(
        text("SELECT password_hash FROM app_user WHERE id = :i"), {"i": created["id"]}
    ).scalar_one()
    assert after != before


def test_password_for_a_user_without_a_username_is_rejected(api, unique, cleanup):
    created = api.post(f"{V1}/users", json=_new_user_payload(unique)).json()
    cleanup.add("app_user", created["id"])
    r = api.post(f"{V1}/users/{created['id']}/password", json={"password": "NoLogin#2026"})
    assert r.status_code == 422
    assert "username" in r.json()["error"]["message"]


def test_unknown_department_reference_is_rejected(api, unique):
    r = api.post(
        f"{V1}/users", json=_new_user_payload(unique, department_id=str(uuid.uuid4()))
    )
    assert r.status_code == 422


def test_short_password_is_rejected_by_the_schema(api, unique):
    r = api.post(f"{V1}/users", json=_new_user_payload(unique, password="short"))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_unknown_field_is_rejected(api, unique):
    r = api.post(f"{V1}/users", json=_new_user_payload(unique, salary=100000))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_anonymous_cannot_write(anon_api, unique):
    for path, payload in (
        (f"{V1}/departments", {"department_name": f"Nope {unique}"}),
        (f"{V1}/users", {"first_name": "N", "phone_number": "+910000000000"}),
        (f"{V1}/roles", {"name": f"Nope {unique}"}),
    ):
        r = anon_api.post(path, json=payload)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthorized"


def test_duty_manager_may_maintain_staff_but_not_grant_privileges(
    manager_api, api, unique, cleanup
):
    """The seeded split: `employees` yes, `user_roles` no. Enforced by data."""
    created = manager_api.post(f"{V1}/users", json=_new_user_payload(unique))
    assert created.status_code == 201
    cleanup.add("app_user", created.json()["id"])

    assert manager_api.post(f"{V1}/roles", json={"name": f"No {unique}"}).status_code == 403
    assert manager_api.post(
        f"{V1}/users/{created.json()['id']}/password", json={"password": "Nope#2026"}
    ).status_code == 403


def test_forbidden_response_uses_the_shared_envelope(manager_api, unique):
    r = manager_api.post(f"{V1}/roles", json={"name": f"No {unique}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


# ---------------------------------------------------------------------------
# Transaction safety
# ---------------------------------------------------------------------------


def test_a_failed_role_assignment_rolls_back_the_whole_user(api, db, unique):
    """One transaction: a bad role id must leave no user behind."""
    before = db.execute(text("SELECT count(*) FROM app_user")).scalar_one()

    r = api.post(
        f"{V1}/users",
        json=_new_user_payload(unique, role_ids=[str(uuid.uuid4())]),
    )
    assert r.status_code == 422

    db.rollback()  # drop this session's snapshot before re-reading
    assert db.execute(text("SELECT count(*) FROM app_user")).scalar_one() == before


def test_a_failed_permission_entry_rolls_back_the_whole_role(api, db, unique):
    before = db.execute(text("SELECT count(*) FROM role")).scalar_one()

    r = api.post(
        f"{V1}/roles",
        json={
            "name": f"Rollback Role {unique}",
            "permissions": [{"module_id": 9999, "read_access": True}],
        },
    )
    assert r.status_code == 422

    db.rollback()
    assert db.execute(text("SELECT count(*) FROM role")).scalar_one() == before
