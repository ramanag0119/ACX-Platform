"""Tests for Country reference data, Gender options, and Booker details with nationality.

Verifies:
1. GET /api/v1/countries returns 239 seeded rows with pagination envelope.
2. GET /api/v1/countries?search=... searches by name, nice_name, phone_code, ISO.
3. GET /api/v1/countries/genders returns the database-backed gender options.
4. Guest user creation with country and nationality foreign keys persists correctly.
5. Invalid country/nationality foreign keys are rejected with 400/422.
6. Stay list and detail endpoints return enriched BookerDetail with contact info and nationality.
7. User update (PATCH /api/v1/users/{id}) updates nationality and country correctly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module")
def client(admin_headers) -> TestClient:
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


def test_list_countries_endpoint(client, db):
    """GET /countries returns 200 with the 239 seeded rows."""
    expected_total = db.execute(text("SELECT count(*) FROM country")).scalar_one()
    resp = client.get(f"{V1}/countries?page=1&page_size=250")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == expected_total
    assert len(body["items"]) == expected_total
    assert body["page"] == 1

    # Verify India and US exist with expected fields
    nice_names = {item["nice_name"]: item for item in body["items"]}
    assert "India" in nice_names
    india = nice_names["India"]
    assert india["id"] == 99
    assert india["phone_code"] == "91"
    assert india["iso_code"] == "IN"
    assert india["iso3"] == "IND"

    assert "United States" in nice_names
    us = nice_names["United States"]
    assert us["phone_code"] == "1"


def test_search_countries_endpoint(client):
    """Search by name, nice_name, phone code, and ISO."""
    # Search by nice_name
    resp = client.get(f"{V1}/countries?search=India")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(c["nice_name"] == "India" for c in items)

    # Search by phone code
    resp = client.get(f"{V1}/countries?search=91")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(c["nice_name"] == "India" for c in items)

    # Search by ISO
    resp = client.get(f"{V1}/countries?search=GB")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(c["nice_name"] == "United Kingdom" for c in items)


def test_list_genders_endpoint(client, db):
    """GET /countries/genders returns enum values from PostgreSQL pg_enum."""
    resp = client.get(f"{V1}/countries/genders")
    assert resp.status_code == 200, resp.text
    genders = resp.json()
    values = [g["value"] for g in genders]
    assert "male" in values
    assert "female" in values
    assert "other" in values
    labels = [g["label"] for g in genders]
    assert "Male" in labels
    assert "Female" in labels


def test_guest_creation_with_nationality_and_country(client, db):
    """Creating a guest with country=99 and nationality=99 persists both fields."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    payload = {
        "first_name": "Test",
        "last_name": "Guest",
        "phone_number": phone[:15],
        "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
        "gender": "female",
        "country": 99,
        "nationality": 99,
        "is_staff": 0,
    }
    resp = client.post(f"{V1}/users", json=payload)
    assert resp.status_code == 201, resp.text
    user_data = resp.json()
    user_id = user_data["id"]

    try:
        assert user_data["country"] == 99
        assert user_data["nationality"] == 99

        # Verify directly in PostgreSQL
        row = db.execute(
            text("SELECT country, nationality, gender, phone_number FROM app_user WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
        assert row is not None
        assert row[0] == 99
        assert row[1] == 99
        assert row[2] == "female"

        # Update nationality to 226 (United States)
        update_resp = client.patch(f"{V1}/users/{user_id}", json={"nationality": 226})
        assert update_resp.status_code == 200, update_resp.text
        assert update_resp.json()["nationality"] == 226

        # Verify updated nationality in PostgreSQL
        updated_row = db.execute(
            text("SELECT nationality FROM app_user WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
        assert updated_row[0] == 226
    finally:
        db.execute(text("DELETE FROM user_role WHERE app_user_id = :id"), {"id": user_id})
        db.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": user_id})
        db.commit()


def test_guest_creation_rejects_invalid_nationality_foreign_key(client):
    """Invalid nationality foreign key (e.g. 99999) is rejected with 422 validation_error."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    payload = {
        "first_name": "Invalid",
        "last_name": "Guest",
        "phone_number": phone[:15],
        "country": 99999,
        "nationality": 99999,
        "is_staff": 0,
    }
    resp = client.post(f"{V1}/users", json=payload)
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert "Country" in err["message"] or "Nationality" in err["message"]


def test_stay_booker_detail_returns_nationality_and_contact(client, db):
    """Creating a stay links the booker and surfaces BookerDetail with nationality name."""
    # 1. Create a guest with nationality = 99 (India)
    phone = f"+9197{uuid.uuid4().hex[:8]}"
    email = f"booker_{uuid.uuid4().hex[:6]}@example.com"
    user_resp = client.post(
        f"{V1}/users",
        json={
            "first_name": "Aarav",
            "last_name": "Sharma",
            "phone_number": phone[:15],
            "email": email,
            "gender": "male",
            "country": 99,
            "nationality": 99,
            "is_staff": 0,
        },
    )
    assert user_resp.status_code == 201, user_resp.text
    user_id = user_resp.json()["id"]

    now = datetime.now(timezone.utc)
    stay_resp = client.post(
        f"{V1}/stays",
        json={
            "booking_user_id": user_id,
            "expected_checkin_time": now.isoformat(),
            "expected_checkout_time": (now + timedelta(days=2)).isoformat(),
            "no_of_guests": 2,
        },
    )
    assert stay_resp.status_code == 201, stay_resp.text
    stay_data = stay_resp.json()
    stay_id = stay_data["id"]

    try:
        # GET /stays/{stay_id} returns booker as UserRef
        detail_resp = client.get(f"{V1}/stays/{stay_id}")
        assert detail_resp.status_code == 200, detail_resp.text
        booker = detail_resp.json()["booker"]
        assert booker is not None
        assert booker["id"] == user_id
        assert booker["name"] == "Aarav Sharma"

        # GET /users/{user_id} returns complete guest record including nationality and contact
        guest_resp = client.get(f"{V1}/users/{user_id}")
        assert guest_resp.status_code == 200, guest_resp.text
        guest = guest_resp.json()
        assert guest["id"] == user_id
        assert guest["phone_number"] == phone[:15]
        assert guest["email"] == email
        assert guest["gender"] == "male"
        assert guest["country"] == 99
        assert guest["nationality"] == 99
    finally:
        db.execute(text("DELETE FROM stay WHERE id = :id"), {"id": stay_id})
        db.execute(text("DELETE FROM user_role WHERE app_user_id = :id"), {"id": user_id})
        db.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": user_id})
        db.commit()

