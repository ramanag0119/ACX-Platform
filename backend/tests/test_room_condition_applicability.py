"""Tests for data-driven, status-specific room condition applicability.

Validates that:
- Only database-configured applicable conditions are returned for each room status
  (Ready to Occupy, Available, Allocated, Occupied).
- Backend validates submitted condition IDs against the room's authoritative status.
- Inapplicable or inactive conditions are rejected with HTTP 422.
- Setting a condition does not mutate room status.
- Database-backed configuration in room_status_condition_applicability drives the options.
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


def _get_room_by_name(db, name: str):
    return db.execute(
        text("SELECT id, name, status FROM amenity WHERE name = :n"),
        {"n": name},
    ).one()


def test_applicable_conditions_available_room(client, db):
    """Available room (105) returns only conditions configured for Available status."""
    room = _get_room_by_name(db, "105")
    res = client.get(f"{V1}/occupancy/{room.id}/applicable-conditions")
    assert res.status_code == 200
    conditions = res.json()
    assert len(conditions) > 0

    condition_names = [c["name"].lower() for c in conditions]
    # Available room should have readiness/maintenance conditions
    assert any("dirty" in n or "maintenance" in n for n in condition_names)
    # Available room must NEVER allow Guest Assistance Required
    assert not any("guest assistance" in n for n in condition_names)

    for c in conditions:
        assert c["is_applicable"] is True
        assert c["is_active"] is True


def test_applicable_conditions_occupied_room(client, db):
    """Occupied room (101) returns guest-stay conditions and excludes Ready for occupant."""
    room = _get_room_by_name(db, "101")
    res = client.get(f"{V1}/occupancy/{room.id}/applicable-conditions")
    assert res.status_code == 200
    conditions = res.json()
    assert len(conditions) > 0

    condition_names = [c["name"].lower() for c in conditions]
    # Occupied room supports Guest Assistance Required
    assert any("guest assistance" in n for n in condition_names)
    # Occupied room must NEVER offer Ready for occupant as a selectable condition
    assert not any("ready for occupant" in n for n in condition_names)
    # Occupied room must NEVER offer Under maintenance (room is occupied by guest)
    assert not any("under maintenance" in n for n in condition_names)


def test_applicable_conditions_allocated_room(client, db):
    """Allocated room (108) returns conditions relevant to pre-checkin assignment."""
    room = _get_room_by_name(db, "108")
    res = client.get(f"{V1}/occupancy/{room.id}/applicable-conditions")
    assert res.status_code == 200
    conditions = res.json()
    assert len(conditions) > 0

    condition_names = [c["name"].lower() for c in conditions]
    # Allocated room must NEVER offer Guest Assistance Required (no checked-in guest yet)
    assert not any("guest assistance" in n for n in condition_names)


def test_applicable_conditions_query_param_by_status(client):
    """GET /amenity-conditions?room_status=Occupied returns filtered conditions."""
    res = client.get(f"{V1}/amenity-conditions?room_status=Occupied")
    assert res.status_code == 200
    conditions = res.json()["items"]
    condition_names = [c["name"].lower() for c in conditions]
    assert any("guest assistance" in n for n in condition_names)
    assert not any("ready for occupant" in n for n in condition_names)

    res_avail = client.get(f"{V1}/amenity-conditions?room_status=Available")
    assert res_avail.status_code == 200
    avail_conditions = res_avail.json()["items"]
    avail_names = [c["name"].lower() for c in avail_conditions]
    assert not any("guest assistance" in n for n in avail_names)


def test_reject_inapplicable_condition_update(client, db):
    """Setting Guest Assistance Required (6) on an Available room (105) must be rejected with 422."""
    room = _get_room_by_name(db, "105")
    # Condition 6 is Guest Assistance Required, not applicable to Available
    res = client.put(
        f"{V1}/occupancy/{room.id}/conditions",
        json={"condition_ids": [6]},
    )
    assert res.status_code == 422
    assert "not applicable" in res.json()["error"]["message"].lower()


def test_reject_ready_condition_on_occupied_room(client, db):
    """Setting Ready for occupant (5) on an Occupied room (101) must be rejected."""
    room = _get_room_by_name(db, "101")
    # Condition 5 is Ready for occupant
    res = client.put(
        f"{V1}/occupancy/{room.id}/conditions",
        json={"condition_ids": [5]},
    )
    # Rejected either by occupancy rule (409) or condition applicability (422)
    assert res.status_code in (409, 422)


def test_condition_update_does_not_mutate_room_status(client, db, cleanup):
    """Setting a condition on an Available room must NOT alter room.status."""
    room = _get_room_by_name(db, "105")
    orig_status = room.status

    # Record cleanup
    orig_conds = db.execute(
        text("SELECT amenity_condition_id, status FROM amenity_condition_status WHERE amenity_id = :i"),
        {"i": room.id},
    ).all()
    cleanup.sql("DELETE FROM amenity_condition_status WHERE amenity_id = :i", {"i": room.id})
    for cid, st in orig_conds:
        cleanup.sql(
            "INSERT INTO amenity_condition_status (amenity_id, amenity_condition_id, status) "
            "VALUES (:i, :c, :s) ON CONFLICT (amenity_id, amenity_condition_id) DO UPDATE SET status = EXCLUDED.status",
            {"i": room.id, "c": cid, "s": st},
        )

    # Set condition 1 (Dirty) - applicable to Available
    res = client.put(
        f"{V1}/occupancy/{room.id}/conditions",
        json={"condition_ids": [1]},
    )
    assert res.status_code == 200

    # Verify room status in DB remains exactly orig_status (0)
    current_status = db.execute(
        text("SELECT status FROM amenity WHERE id = :i"),
        {"i": room.id},
    ).scalar_one()
    assert current_status == orig_status


def test_reject_invalid_condition_id(client, db):
    """Non-existent condition IDs must be rejected with 422."""
    room = _get_room_by_name(db, "105")
    res = client.put(
        f"{V1}/occupancy/{room.id}/conditions",
        json={"condition_ids": [99999]},
    )
    assert res.status_code == 422


def test_status_specific_database_driven(db):
    """Verify that room_status_condition_applicability table rows exist and drive applicability."""
    rows = db.execute(
        text("SELECT room_status, condition_id, is_applicable FROM room_status_condition_applicability WHERE is_active = true")
    ).all()
    assert len(rows) > 0
    statuses = {r[0] for r in rows}
    assert "Occupied" in statuses
    assert "Available" in statuses
    assert "Allocated" in statuses
    assert "Ready to Occupy" in statuses
