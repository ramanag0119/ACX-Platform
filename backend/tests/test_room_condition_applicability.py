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


def _get_condition_by_name(db, name: str):
    return db.execute(
        text("SELECT id, name, display_name FROM amenity_condition WHERE lower(name) = lower(:n)"),
        {"n": name},
    ).one()


def _get_status_id(db, name: str) -> int:
    return db.execute(
        text("SELECT id FROM amenity_status WHERE lower(amenity_status_name) = lower(:n)"),
        {"n": name},
    ).scalar_one()


def test_condition_update_synchronizes_room_status(client, db):
    """Updating condition on an unallocated room synchronizes room status according to business rules.
    - Setting a blocking condition (Dirty, Under maintenance) transitions status to Unavailable.
    - Setting a readiness condition (Ready for occupant) transitions status to Available.
    - Setting a non-blocking device condition (Low battery) preserves status.
    """
    room = _get_room_by_name(db, "105")
    avail_id = _get_status_id(db, "Available")
    unavail_id = _get_status_id(db, "Unavailable")

    dirty_cond = _get_condition_by_name(db, "Dirty")
    ready_cond = _get_condition_by_name(db, "Ready for occupant")
    battery_cond = _get_condition_by_name(db, "Low battery")

    orig_status = room.status
    orig_conds = db.execute(
        text("SELECT amenity_condition_id, status FROM amenity_condition_status WHERE amenity_id = :i"),
        {"i": room.id},
    ).all()

    try:
        # Step 1: Ensure room is Available, set Low Battery (non-blocking) -> status stays Available
        db.execute(text("UPDATE amenity SET status = :s WHERE id = :i"), {"s": avail_id, "i": room.id})
        db.commit()

        res = client.put(f"{V1}/occupancy/{room.id}/conditions", json={"condition_ids": [battery_cond.id]})
        assert res.status_code == 200
        status_after_battery = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": room.id}).scalar_one()
        assert status_after_battery == avail_id

        # Step 2: Set Dirty (blocking condition) -> status transitions to Unavailable
        res = client.put(f"{V1}/occupancy/{room.id}/conditions", json={"condition_ids": [dirty_cond.id]})
        assert res.status_code == 200
        status_after_dirty = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": room.id}).scalar_one()
        assert status_after_dirty == unavail_id

        # Step 3: Set Ready for occupant (resolving blocking condition) -> status transitions to Available
        res = client.put(f"{V1}/occupancy/{room.id}/conditions", json={"condition_ids": [ready_cond.id]})
        assert res.status_code == 200
        status_after_ready = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": room.id}).scalar_one()
        assert status_after_ready == avail_id
    finally:
        db.execute(text("DELETE FROM amenity_condition_status WHERE amenity_id = :i"), {"i": room.id})
        for cid, st in orig_conds:
            db.execute(
                text("INSERT INTO amenity_condition_status (amenity_id, amenity_condition_id, status) VALUES (:i, :c, :s)"),
                {"i": room.id, "c": cid, "s": st},
            )
        db.execute(text("UPDATE amenity SET status = :s WHERE id = :i"), {"s": orig_status, "i": room.id})
        db.commit()


def test_occupied_room_condition_update_preserves_occupied_status(client, db):
    """Updating condition on an Occupied room preserves Occupied status (does not make it Available or Unavailable)."""
    room = _get_room_by_name(db, "101")
    occupied_id = _get_status_id(db, "Occupied")
    dirty_cond = _get_condition_by_name(db, "Dirty")

    orig_conds = db.execute(
        text("SELECT amenity_condition_id, status FROM amenity_condition_status WHERE amenity_id = :i"),
        {"i": room.id},
    ).all()

    try:
        res = client.put(f"{V1}/occupancy/{room.id}/conditions", json={"condition_ids": [dirty_cond.id]})
        assert res.status_code == 200

        current_status = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": room.id}).scalar_one()
        assert current_status == occupied_id
    finally:
        db.execute(text("DELETE FROM amenity_condition_status WHERE amenity_id = :i"), {"i": room.id})
        for cid, st in orig_conds:
            db.execute(
                text("INSERT INTO amenity_condition_status (amenity_id, amenity_condition_id, status) VALUES (:i, :c, :s)"),
                {"i": room.id, "c": cid, "s": st},
            )
        db.commit()


def test_arbitrary_room_status_synchronization(client, db):
    """Verify condition-status synchronization on arbitrary rooms (not hardcoded to 204 or 105)."""
    avail_id = _get_status_id(db, "Available")
    unavail_id = _get_status_id(db, "Unavailable")
    maint_cond = _get_condition_by_name(db, "Under maintenance")
    ready_cond = _get_condition_by_name(db, "Ready for occupant")

    candidate = db.execute(
        text("""
            SELECT id, name, status FROM amenity
            WHERE status = :av
              AND name != '202'
              AND id NOT IN (SELECT room_id FROM room_allocation)
            LIMIT 1
        """),
        {"av": avail_id},
    ).first()

    if candidate is None:
        pytest.skip("No unallocated available room found for arbitrary room test")

    rid = candidate.id
    orig_status = candidate.status
    orig_conds = db.execute(
        text("SELECT amenity_condition_id, status FROM amenity_condition_status WHERE amenity_id = :i"),
        {"i": rid},
    ).all()

    try:
        # Put Under Maintenance -> must transition to Unavailable
        res = client.put(f"{V1}/occupancy/{rid}/conditions", json={"condition_ids": [maint_cond.id]})
        assert res.status_code == 200
        st1 = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": rid}).scalar_one()
        assert st1 == unavail_id

        # Resolve with Ready for occupant -> must transition to Available
        res = client.put(f"{V1}/occupancy/{rid}/conditions", json={"condition_ids": [ready_cond.id]})
        assert res.status_code == 200
        st2 = db.execute(text("SELECT status FROM amenity WHERE id = :i"), {"i": rid}).scalar_one()
        assert st2 == avail_id
    finally:
        db.execute(text("DELETE FROM amenity_condition_status WHERE amenity_id = :i"), {"i": rid})
        for cid, st in orig_conds:
            db.execute(
                text("INSERT INTO amenity_condition_status (amenity_id, amenity_condition_id, status) VALUES (:i, :c, :s)"),
                {"i": rid, "c": cid, "s": st},
            )
        db.execute(text("UPDATE amenity SET status = :s WHERE id = :i"), {"s": orig_status, "i": rid})
        db.commit()


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


def test_occupancy_summary_counts_match_database_state(client, db):
    """Verify that GET /occupancy/summary counts match persisted room counts in the database."""
    res = client.get(f"{V1}/occupancy/summary")
    assert res.status_code == 200
    summary = res.json()

    total_amenities = db.execute(text("SELECT count(*) FROM amenity")).scalar_one()
    assert summary["total_rooms"] == total_amenities
    assert summary["available"] >= 0
    assert summary["occupied"] >= 0
    assert summary["unavailable"] >= 0
    assert summary["allotted"] >= 0
    assert summary["total_rooms"] == (
        summary["available"] + summary["occupied"] + summary["unavailable"] + summary["allotted"]
    )


def test_need_maintenance_display_label_is_database_driven(client, db):
    """Verify that condition 1 (Dirty) exposes display_name 'Need Maintenance' from DB in master data and occupancy."""
    # 1. Master data check
    res_conds = client.get(f"{V1}/amenity-conditions")
    assert res_conds.status_code == 200
    dirty_cond = next((c for c in res_conds.json()["items"] if c["id"] == 1 or c["name"] == "Dirty"), None)
    assert dirty_cond is not None
    assert dirty_cond["display_name"] == "Need Maintenance"

    # 2. Occupancy room check for room with Dirty condition (e.g. 102 or 208)
    res_occ = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100")
    assert res_occ.status_code == 200
    room_102 = next((r for r in res_occ.json()["items"] if r["room_name"] == "102"), None)
    if room_102:
        cond_102 = next((c for c in room_102["conditions"] if c["id"] == 1 or c["name"] == "Dirty"), None)
        assert cond_102 is not None
        assert cond_102["display_name"] == "Need Maintenance"
        assert room_102["room_status"] == "Need Maintenance"
