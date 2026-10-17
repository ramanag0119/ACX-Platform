"""Tests for the database-driven employee and role forms and role authorization flow."""

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
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="module")
def admin_client(admin_headers) -> TestClient:
    with TestClient(app, headers=admin_headers) as c:
        yield c


@pytest.fixture(scope="module")
def manager_client(manager_headers) -> TestClient:
    with TestClient(app, headers=manager_headers) as c:
        yield c


def test_assignable_roles_for_admin(admin_client):
    r = admin_client.get(f"{V1}/users/roles")
    assert r.status_code == 200
    roles = r.json()
    assert isinstance(roles, list)
    assert len(roles) > 0
    role_types = {role["role_type"] for role in roles}
    role_names = {role["name"] for role in roles}
    
    # Excludes system_user and guest
    assert "system_user" not in role_types
    assert "guest" not in role_types
    assert "System" not in role_names
    assert "Guest" not in role_names
    
    # Admin can assign admin, manager, staff
    assert "admin" in role_types
    assert "staff" in role_types
    assert "manager" in role_types


def test_assignable_roles_for_manager(manager_client):
    r = manager_client.get(f"{V1}/users/roles")
    assert r.status_code == 200
    roles = r.json()
    assert isinstance(roles, list)
    assert len(roles) > 0
    role_types = {role["role_type"] for role in roles}
    
    # Privileged administrative and system roles are NOT exposed to manager
    assert "admin" not in role_types
    assert "system_user" not in role_types
    assert "guest" not in role_types
    
    # Manager sees staff and manager roles
    assert "staff" in role_types
    assert "manager" in role_types


def test_role_types_endpoint(admin_client, manager_client):
    # Admin gets full set of non-system role types
    r_admin = admin_client.get(f"{V1}/roles/types")
    assert r_admin.status_code == 200
    admin_types = {t["value"] for t in r_admin.json()}
    assert admin_types == {"staff", "manager", "admin", "guest"}
    
    # Manager is denied /roles/types because manager lacks user_roles grant
    r_mgr = manager_client.get(f"{V1}/roles/types")
    assert r_mgr.status_code == 403


def test_user_list_includes_projected_role_name_and_id(admin_client):
    r = admin_client.get(f"{V1}/users?is_staff=1&page_size=10")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0
    
    # Ensure role_name and role_id are populated
    staff_with_roles = [u for u in items if u["role_name"] is not None]
    assert len(staff_with_roles) > 0
    for u in staff_with_roles:
        assert isinstance(u["role_id"], str)
        assert isinstance(u["role_name"], str)


def test_manager_cannot_assign_admin_role(manager_client, db):
    admin_role_id = str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'admin' LIMIT 1")).scalar_one()
    )
    payload = {
        "first_name": "Unauthorized",
        "last_name": "AdminAssign",
        "phone_number": "+919876543210",
        "is_staff": 1,
        "role_ids": [admin_role_id],
    }
    r = manager_client.post(f"{V1}/users", json=payload)
    assert r.status_code == 422
    assert "not authorized to assign administrative roles" in r.json()["error"]["message"]


def test_cannot_assign_system_user_role(admin_client, db):
    sys_role_id = str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'system_user' LIMIT 1")).scalar_one()
    )
    payload = {
        "first_name": "System",
        "last_name": "AssignAttempt",
        "phone_number": "+919876543211",
        "is_staff": 1,
        "role_ids": [sys_role_id],
    }
    r = admin_client.post(f"{V1}/users", json=payload)
    assert r.status_code == 422
    assert "reserved" in r.json()["error"]["message"]


def test_cannot_assign_guest_role_to_staff(admin_client, db):
    guest_role_id = str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'guest' LIMIT 1")).scalar_one()
    )
    payload = {
        "first_name": "Staff",
        "last_name": "WithGuestRole",
        "phone_number": "+919876543212",
        "is_staff": 1,
        "role_ids": [guest_role_id],
    }
    r = admin_client.post(f"{V1}/users", json=payload)
    assert r.status_code == 422
    assert "Guest role cannot be assigned to staff" in r.json()["error"]["message"]


def test_successful_staff_creation_with_role_and_country(admin_client, db):
    staff_role_id = str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'staff' AND name = 'Front Desk' LIMIT 1")).scalar_one()
    )
    # India is id 99 in country table
    india_id = 99
    
    unique_suffix = uuid.uuid4().hex[:6]
    payload = {
        "first_name": "FrontDesk",
        "last_name": f"User{unique_suffix}",
        "phone_number": f"+9198765{unique_suffix[:5]}",
        "country": india_id,
        "is_staff": 1,
        "role_ids": [staff_role_id],
    }
    r = admin_client.post(f"{V1}/users", json=payload)
    assert r.status_code == 201
    created = r.json()
    user_id = created["id"]
    
    # Verify in created response
    assert created["country"] == india_id
    assert created["role_name"] == "Front Desk"
    assert created["role_id"] == staff_role_id
    assert len(created["roles"]) == 1
    assert created["roles"][0]["role_id"] == staff_role_id
    
    # Verify in DB
    user_row = db.execute(
        text("SELECT country, phone_number FROM app_user WHERE id = :id"),
        {"id": user_id},
    ).mappings().one()
    assert user_row["country"] == india_id
    
    role_row = db.execute(
        text("SELECT role_id FROM user_role WHERE app_user_id = :id"),
        {"id": user_id},
    ).mappings().one()
    assert str(role_row["role_id"]) == staff_role_id
    
    # Verify GET /users/{id}
    detail = admin_client.get(f"{V1}/users/{user_id}").json()
    assert detail["country"] == india_id
    assert detail["roles"][0]["role_id"] == staff_role_id
    assert detail["roles"][0]["role_name"] == "Front Desk"
    
    # Verify UPDATE role and country
    housekeeping_role_id = str(
        db.execute(text("SELECT id FROM role WHERE role_type = 'staff' AND name = 'Housekeeping' LIMIT 1")).scalar_one()
    )
    update_payload = {
        "role_ids": [housekeeping_role_id],
    }
    r_patch = admin_client.patch(f"{V1}/users/{user_id}", json=update_payload)
    assert r_patch.status_code == 200
    updated = r_patch.json()
    assert updated["role_name"] == "Housekeeping"
    assert updated["role_id"] == housekeeping_role_id
    assert updated["roles"][0]["role_id"] == housekeeping_role_id
    
    # Verify DB updated
    updated_role_row = db.execute(
        text("SELECT role_id FROM user_role WHERE app_user_id = :id"),
        {"id": user_id},
    ).mappings().one()
    assert str(updated_role_row["role_id"]) == housekeeping_role_id
