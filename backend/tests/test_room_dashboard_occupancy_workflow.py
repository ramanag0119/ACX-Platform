"""Comprehensive verification of HMS Room in House Dashboard, Occupancy Calculations,
and Check-in/Check-out Room Status Synchronization.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    RoomAllocation,
    RoomStatusConditionApplicability,
    Stay,
)
from app.services import occupancy as svc

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


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM stay")).scalar_one():
        pytest.skip("Database is not seeded; run `python -m seeds.run_seed`")


# ===========================================================================
# 1. Dashboard KPI Tests
# ===========================================================================

def test_dashboard_kpi_total_room_count_includes_guest_rooms_only(client, db):
    """Total room count with amenity_category=room returns exactly 24 guest rooms."""
    res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=1")
    assert res.status_code == 200
    assert res.json()["total"] == 24

    # Direct DB verification: guest rooms only
    db_guest_rooms = db.execute(
        text(
            "SELECT count(*) FROM amenity a "
            "JOIN amenity_type at ON at.id = a.amenity_type_id "
            "WHERE at.amenity_category = 'room'"
        )
    ).scalar_one()
    assert db_guest_rooms == 24


def test_dashboard_kpi_excludes_non_room_facilities(client, db):
    """Non-room facilities (restaurant, gym, conference room) are excluded from guest room query."""
    # All amenities = 27 (24 guest rooms + 3 non-rooms)
    all_amenities_res = client.get(f"{V1}/occupancy?page_size=1")
    assert all_amenities_res.status_code == 200
    assert all_amenities_res.json()["total"] == 27

    room_amenities_res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=1")
    assert room_amenities_res.status_code == 200
    assert room_amenities_res.json()["total"] == 24

    # Non-room categories exist and remain separate
    other_amenities = db.execute(
        text(
            "SELECT a.name, at.name, at.amenity_category FROM amenity a "
            "JOIN amenity_type at ON at.id = a.amenity_type_id "
            "WHERE at.amenity_category != 'room'"
        )
    ).fetchall()
    assert len(other_amenities) == 3
    non_room_categories = {row[2] for row in other_amenities}
    assert "restaurant" in non_room_categories
    assert "others" in non_room_categories


def test_dashboard_kpi_occupied_amenity_flag_includes_guest_rooms_only(client, db):
    """Occupied amenity flag query with amenity_category=room excludes non-room facilities."""
    occupied_status_id = db.execute(
        text("SELECT id FROM amenity_status WHERE amenity_status_name = 'Occupied'")
    ).scalar_one()

    # Unfiltered count includes CONF01 (conference room)
    all_occupied_res = client.get(f"{V1}/occupancy?status={occupied_status_id}&page_size=1")
    assert all_occupied_res.status_code == 200
    assert all_occupied_res.json()["total"] == 5

    # Filtered count includes guest rooms only = 4
    room_occupied_res = client.get(
        f"{V1}/occupancy?status={occupied_status_id}&amenity_category=room&page_size=1"
    )
    assert room_occupied_res.status_code == 200
    assert room_occupied_res.json()["total"] == 4


def test_dashboard_kpi_room_in_house_counts_distinct_physical_rooms(client, db):
    """Room in House KPI counts distinct rooms associated with active in-house stays."""
    res = client.get(f"{V1}/occupancy?is_occupied=true&amenity_category=room&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4

    distinct_room_ids = {r["amenity_id"] for r in data["items"]}
    assert len(distinct_room_ids) == 4

    # Verify against actual DB stay records
    db_distinct_in_house_rooms = db.execute(
        text(
            "SELECT count(DISTINCT ra.room_id) FROM stay s "
            "JOIN room_allocation ra ON ra.stay_id = s.id "
            "JOIN amenity a ON a.id = ra.room_id "
            "JOIN amenity_type at ON at.id = a.amenity_type_id "
            "WHERE at.amenity_category = 'room' "
            "AND s.actual_checkin_time IS NOT NULL "
            "AND s.actual_checkout_time IS NULL"
        )
    ).scalar_one()
    assert db_distinct_in_house_rooms == 4


def test_stay_counts_remain_separate_from_room_counts(client, db):
    """Stays count endpoint (/stays?is_in_house=true) and room count (/occupancy?is_occupied=true) remain separate."""
    stays_res = client.get(f"{V1}/stays?is_in_house=true&page_size=1")
    assert stays_res.status_code == 200

    rooms_res = client.get(f"{V1}/occupancy?is_occupied=true&amenity_category=room&page_size=1")
    assert rooms_res.status_code == 200

    assert stays_res.json()["total"] >= 1
    assert rooms_res.json()["total"] >= 1


# ===========================================================================
# 2. Occupancy Statistics Tests
# ===========================================================================

def test_occupancy_statistics_mutually_exclusive_and_exhaustive(client):
    """Available + Occupied + Unavailable + Allotted = Total guest rooms (24)."""
    res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert res.status_code == 200
    data = res.json()

    assert data["total_rooms"] == 24
    assert data["available"] == 12
    assert data["occupied"] == 4
    assert data["unavailable"] == 5
    assert data["allotted"] == 3
    assert data["unknown"] == 0

    assert data["available"] + data["occupied"] + data["unavailable"] + data["allotted"] == 24


def test_occupancy_statistics_reconciles_room_201_and_306(client):
    """Room 201 is Available (no in-house stay) and Room 306 is Occupied (active in-house stay)."""
    # Room 201
    res_avail = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Available&page_size=100")
    assert res_avail.status_code == 200
    avail_rooms = {r["room_name"] for r in res_avail.json()["items"]}
    assert "201" in avail_rooms
    assert "306" not in avail_rooms

    # Room 306
    res_occ = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Occupied&page_size=100")
    assert res_occ.status_code == 200
    occ_rooms = {r["room_name"] for r in res_occ.json()["items"]}
    assert "306" in occ_rooms
    assert "201" not in occ_rooms
    assert occ_rooms == {"101", "106", "205", "306"}


# ===========================================================================
# 3. Check-In & Check-Out Status Synchronization Tests
# ===========================================================================

def _track_stay(cleanup, stay_id) -> None:
    cleanup.sql("DELETE FROM stay_user WHERE stay_id = :value", {"value": stay_id})
    cleanup.sql("DELETE FROM room_allocation WHERE stay_id = :value", {"value": stay_id})
    cleanup.add("stay", stay_id)


def _restore_room(cleanup, db, room_id) -> None:
    original = db.execute(
        text("SELECT status FROM amenity WHERE id = :i"), {"i": room_id}
    ).scalar_one()
    cleanup.sql(
        "UPDATE amenity SET status = :status WHERE id = :value",
        {"status": original, "value": room_id},
    )


def test_check_in_synchronizes_room_status_to_occupied(client, db, guest_id, free_room, cleanup):
    """Check-in stamps actual_checkin_time, sets stay to active, and sets room to Occupied."""
    _restore_room(cleanup, db, free_room)

    checkin = datetime.now(UTC) + timedelta(days=1)
    stay_res = client.post(
        f"{V1}/stays",
        json={
            "booking_user_id": str(guest_id),
            "expected_checkin_time": checkin.isoformat(),
            "expected_checkout_time": (checkin + timedelta(days=2)).isoformat(),
            "no_of_guests": 1,
            "room_ids": [str(free_room)],
        },
    )
    assert stay_res.status_code == 201
    stay_id = stay_res.json()["id"]
    _track_stay(cleanup, stay_id)

    # Initially allocated room is Allotted (3)
    db.rollback()
    room_status = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": free_room}).scalar_one()
    assert room_status == 3

    # Check in
    cin_res = client.post(f"{V1}/stays/{stay_id}/check-in", json={})
    assert cin_res.status_code == 200
    stay_data = cin_res.json()
    assert stay_data["status"] == "active"
    assert stay_data["actual_checkin_time"] is not None

    # Room is now Occupied (1)
    db.rollback()
    room_status_after = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": free_room}).scalar_one()
    assert room_status_after == 1


def test_bypassing_check_in_via_status_endpoint_is_rejected(client, db, guest_id, free_room, cleanup):
    """Attempting to set stay status to active via /status endpoint is rejected."""
    _restore_room(cleanup, db, free_room)

    checkin = datetime.now(UTC) + timedelta(days=1)
    stay_res = client.post(
        f"{V1}/stays",
        json={
            "booking_user_id": str(guest_id),
            "expected_checkin_time": checkin.isoformat(),
            "expected_checkout_time": (checkin + timedelta(days=2)).isoformat(),
            "no_of_guests": 1,
            "room_ids": [str(free_room)],
        },
    )
    assert stay_res.status_code == 201
    stay_id = stay_res.json()["id"]
    _track_stay(cleanup, stay_id)

    status_res = client.post(f"{V1}/stays/{stay_id}/status", json={"status": "active"})
    assert status_res.status_code == 422
    assert "check_in" in status_res.json()["error"]["message"]


def test_checkout_releases_room_to_available_and_records_checkout_timestamp(client, db, guest_id, free_room, cleanup):
    """Checkout stamps actual_checkout_time, moves stay to checked out, and synchronizes room to Available."""
    _restore_room(cleanup, db, free_room)

    checkin = datetime.now(UTC) + timedelta(days=1)
    stay_res = client.post(
        f"{V1}/stays",
        json={
            "booking_user_id": str(guest_id),
            "expected_checkin_time": checkin.isoformat(),
            "expected_checkout_time": (checkin + timedelta(days=2)).isoformat(),
            "no_of_guests": 1,
            "room_ids": [str(free_room)],
        },
    )
    assert stay_res.status_code == 201
    stay_id = stay_res.json()["id"]
    _track_stay(cleanup, stay_id)

    # Check in first
    client.post(f"{V1}/stays/{stay_id}/check-in", json={})

    # Checkout
    cout_res = client.post(f"{V1}/stays/{stay_id}/check-out", json={})
    assert cout_res.status_code == 200
    cout_data = cout_res.json()
    assert cout_data["status"] == "checked out"
    assert cout_data["actual_checkout_time"] is not None

    # Room is now Available (0)
    db.rollback()
    room_status = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": free_room}).scalar_one()
    assert room_status == 0


def test_checkout_pending_stay_preserves_occupied_state(client, db):
    """A stay in 'checkout pending' status remains in-house until checkout is finalized."""
    # STY-2026-0006 is seeded as 'checkout pending' in room 106
    stay_row = db.execute(
        text("SELECT status, actual_checkin_time, actual_checkout_time FROM stay WHERE internal_stay_ref_number = 'STY-2026-0006'")
    ).mappings().one()
    assert stay_row["status"] == "checkout pending"
    assert stay_row["actual_checkin_time"] is not None
    assert stay_row["actual_checkout_time"] is None

    # Room 106 must remain Occupied
    room_106 = db.execute(
        text("SELECT status FROM amenity WHERE name = '106'")
    ).scalar_one()
    assert room_106 == 1  # Occupied
