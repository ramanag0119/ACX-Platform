"""Tests for HMS Occupancy Module - Available Room Defaults to Ready to Occupy.

Validates all 12 testing requirements from Section 8 of the requirement prompt:
1. Creating an eligible Available room defaults its condition to Ready to Occupy.
2. Existing eligible rooms with missing conditions are handled consistently.
3. Rooms with Need Maintenance retain that condition.
4. Rooms with Under Maintenance retain that condition.
5. Rooms with Sanitation retain that condition.
6. Occupied rooms are not incorrectly assigned Ready to Occupy.
7. Allocated rooms follow the established business rules.
8. Resolving a blocking condition produces the correct result.
9. The API returns the correct Room Status and Room Condition.
10. Dynamic data-driven master data lookup without hardcoded IDs.
11. Check-out workflow releases room to Available and defaults condition to Ready to Occupy.
12. Non-room amenities are not assigned Ready to Occupy.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Amenity,
    AmenityCondition,
    AmenityConditionStatus,
    AmenityStatus,
    AmenityType,
    Facility,
    Package,
    PropertyChain,
    RoomAllocation,
    Stay,
)
from app.services.facility_write import create_room
from app.services.occupancy import (
    ensure_available_room_default_condition,
    get_ready_to_occupy_condition,
    list_occupancy,
)

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module")
def client(admin_headers) -> TestClient:
    with TestClient(app, headers=admin_headers) as c:
        yield c


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def test_1_create_eligible_available_room_defaults_to_ready_to_occupy(db):
    """1. Creating an eligible Available room defaults its condition to Ready to Occupy."""
    facility = db.execute(select(Facility)).scalars().first()
    atype = db.execute(
        select(AmenityType).where(AmenityType.amenity_category == "room")
    ).scalars().first()
    pkg = db.execute(select(Package)).scalars().first()
    chain = db.execute(select(PropertyChain)).scalars().first()
    avail_status = db.execute(
        select(AmenityStatus.id).where(AmenityStatus.amenity_status_name == "Available")
    ).scalar_one()

    test_room_name = f"T{uuid.uuid4().hex[:4].upper()}"
    room = None
    try:
        room = create_room(
            db,
            data={
                "name": test_room_name,
                "amenity_type_id": atype.id,
                "package_id": pkg.id,
                "property_chain_id": chain.id,
                "facility_id": facility.id,
                "status": avail_status,
            },
            actor_id=facility.created_by,
            facility_id=facility.id,
        )

        assert room.status == avail_status

        # Verify condition row in amenity_condition_status
        cond_row = db.execute(
            select(AmenityConditionStatus, AmenityCondition.display_name, AmenityCondition.name)
            .join(AmenityCondition, AmenityCondition.id == AmenityConditionStatus.amenity_condition_id)
            .where(
                AmenityConditionStatus.amenity_id == room.id,
                AmenityConditionStatus.status == 1,
            )
        ).first()

        assert cond_row is not None
        cond_status, display_name, name = cond_row
        assert "ready" in (display_name or name).lower()
    finally:
        if room:
            db.execute(delete(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id))
            db.execute(delete(Amenity).where(Amenity.id == room.id))
            db.commit()


def test_2_existing_eligible_room_missing_condition_handled_consistently(db):
    """2. Existing eligible rooms with Available status and no condition are handled consistently."""
    # Find an available room
    room = db.execute(
        select(Amenity)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
        .where(AmenityType.amenity_category == "room", Amenity.name == "308")
    ).scalar_one()

    # Temporarily remove any existing condition
    orig_conds = db.execute(
        select(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id)
    ).scalars().all()
    orig_data = [(c.amenity_condition_id, c.status) for c in orig_conds]

    try:
        db.execute(delete(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id))
        db.commit()

        # Call ensure_available_room_default_condition
        cond_status = ensure_available_room_default_condition(db, room.id)
        db.commit()

        assert cond_status is not None
        assert cond_status.status == 1

        ready_cond = get_ready_to_occupy_condition(db)
        assert cond_status.amenity_condition_id == ready_cond.id
    finally:
        db.execute(delete(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id))
        for cid, st in orig_data:
            db.add(AmenityConditionStatus(amenity_id=room.id, amenity_condition_id=cid, status=st))
        db.commit()


def test_3_room_with_need_maintenance_retains_condition(client, db):
    """3. Rooms with Need Maintenance retain that condition."""
    room = db.execute(select(Amenity).where(Amenity.name == "102")).scalar_one()
    res = client.get(f"{V1}/occupancy/{room.id}")
    assert res.status_code == 200
    data = res.json()

    condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
    assert "Need Maintenance" in condition_names
    assert "Ready to Occupy" not in condition_names


def test_4_room_with_under_maintenance_retains_condition(client, db):
    """4. Rooms with Under Maintenance retain that condition."""
    room = db.execute(select(Amenity).where(Amenity.name == "104")).scalar_one()
    res = client.get(f"{V1}/occupancy/{room.id}")
    assert res.status_code == 200
    data = res.json()

    condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
    assert "Under Maintenance" in condition_names
    assert "Ready to Occupy" not in condition_names


def test_5_room_with_sanitation_retains_condition(client, db):
    """5. Rooms with Sanitation retain that condition."""
    room = db.execute(select(Amenity).where(Amenity.name == "103")).scalar_one()
    res = client.get(f"{V1}/occupancy/{room.id}")
    assert res.status_code == 200
    data = res.json()

    condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
    assert any("sanitation" in name.lower() for name in condition_names)
    assert "Ready to Occupy" not in condition_names


def test_6_occupied_rooms_not_assigned_ready_to_occupy(client, db):
    """6. Occupied rooms are not incorrectly assigned Ready to Occupy."""
    # Room 101 has an in-house stay
    room = db.execute(select(Amenity).where(Amenity.name == "101")).scalar_one()
    res = client.get(f"{V1}/occupancy/{room.id}")
    assert res.status_code == 200
    data = res.json()

    assert data["occupancy_status"] == "Occupied"
    condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
    assert "Ready to Occupy" not in condition_names


def test_7_allocated_rooms_follow_business_rules(client, db):
    """7. Allocated rooms follow the established business rules and are not defaulted to Ready to Occupy."""
    # Room 301 has a pending stay allocation (STY-2026-0003)
    room = db.execute(select(Amenity).where(Amenity.name == "301")).scalar_one()
    res = client.get(f"{V1}/occupancy/{room.id}")
    assert res.status_code == 200
    data = res.json()

    assert data["occupancy_status"] == "Allotted"
    condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
    assert "Ready to Occupy" not in condition_names


def test_8_resolving_blocking_condition_produces_correct_result(client, db):
    """8. Resolving a blocking condition transitions room to Available with Ready to Occupy."""
    room = db.execute(select(Amenity).where(Amenity.name == "104")).scalar_one()
    ready_cond = get_ready_to_occupy_condition(db)

    # Save original conditions
    orig_conds = db.execute(
        select(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id)
    ).scalars().all()
    orig_data = [(c.amenity_condition_id, c.status) for c in orig_conds]
    orig_status = room.status

    try:
        # Resolve maintenance by selecting Ready to Occupy
        put_res = client.put(
            f"{V1}/occupancy/{room.id}/conditions",
            json={"condition_ids": [ready_cond.id]},
        )
        assert put_res.status_code == 200

        # Verify room state
        res = client.get(f"{V1}/occupancy/{room.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["occupancy_status"] == "Available"
        condition_names = [c["display_name"] or c["name"] for c in data["conditions"]]
        assert "Ready to Occupy" in condition_names
    finally:
        # Restore
        db.execute(delete(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id))
        for cid, st in orig_data:
            db.add(AmenityConditionStatus(amenity_id=room.id, amenity_condition_id=cid, status=st))
        room = db.get(Amenity, room.id)
        room.status = orig_status
        db.commit()


def test_9_api_returns_authoritative_status_and_condition(client, db):
    """9. The API returns the correct Room Status and Room Condition separately."""
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Available&page_size=100")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] > 0
    for item in data["items"]:
        assert item["occupancy_status"] == "Available"
        cond_names = [c["display_name"] or c["name"] for c in item["conditions"]]
        assert len(cond_names) > 0, f"Available room {item['room_name']} has no active condition"
        # If room has no operational alert (like Device Offline), its condition is Ready to Occupy
        if "Device Offline" not in cond_names:
            assert "Ready to Occupy" in cond_names


def test_10_no_hardcoded_condition_ids_or_labels(db):
    """10. Dynamic data-driven master-data lookup retrieves Ready to Occupy without hardcoding."""
    cond = get_ready_to_occupy_condition(db)
    assert cond is not None
    assert cond.is_active is True
    assert (cond.display_name == "Ready to Occupy" or cond.name in ("Ready for occupant", "Ready to Occupy"))


def test_11_check_out_workflow_defaults_room_condition_to_ready(client, db):
    """11. Checking out a stay releases the room to Available and defaults condition to Ready to Occupy."""
    # Find room 202 (Available) and allocate a temporary stay
    room = db.execute(select(Amenity).where(Amenity.name == "202")).scalar_one()
    booker = db.execute(select(Stay.booking_user_id)).scalars().first()

    now = datetime.now(UTC)
    stay = Stay(
        id=uuid.uuid4(),
        internal_stay_ref_number=f"STY-TEST-{uuid.uuid4().hex[:4]}",
        status="active",
        booking_user_id=booker,
        expected_checkin_time=now,
        expected_checkout_time=now + timedelta(days=1),
        actual_checkin_time=now,
        no_of_guests=1,
        created_by=booker,
        modified_by=booker,
    )
    db.add(stay)
    db.flush()
    alloc = RoomAllocation(
        id=uuid.uuid4(),
        stay_id=stay.id,
        room_id=room.id,
        package_id=room.package_id,
        status=1,
        created_by=booker,
    )
    db.add(alloc)
    room.status = 1  # Occupied
    # Clear conditions for occupied room
    db.execute(delete(AmenityConditionStatus).where(AmenityConditionStatus.amenity_id == room.id))
    db.commit()

    try:
        # Check out via API
        co_res = client.post(f"{V1}/stays/{stay.id}/check-out", json={})
        assert co_res.status_code == 200

        # Verify room status is Available and condition defaulted to Ready to Occupy
        occ_res = client.get(f"{V1}/occupancy/{room.id}")
        assert occ_res.status_code == 200
        occ_data = occ_res.json()

        assert occ_data["occupancy_status"] == "Available"
        cond_names = [c["display_name"] or c["name"] for c in occ_data["conditions"]]
        assert "Ready to Occupy" in cond_names
    finally:
        db.execute(delete(RoomAllocation).where(RoomAllocation.stay_id == stay.id))
        db.execute(delete(Stay).where(Stay.id == stay.id))
        room = db.get(Amenity, room.id)
        room.status = 0
        ensure_available_room_default_condition(db, room)
        db.commit()


def test_12_non_room_amenities_not_assigned_ready_to_occupy(client, db):
    """12. Non-room amenities (gym, restaurant) are not assigned Ready to Occupy."""
    non_rooms = db.execute(
        select(Amenity)
        .join(AmenityType, AmenityType.id == Amenity.amenity_type_id)
        .where(AmenityType.amenity_category != "room")
    ).scalars().all()

    assert len(non_rooms) > 0
    for amenity in non_rooms:
        res = client.get(f"{V1}/occupancy/{amenity.id}")
        assert res.status_code == 200
        data = res.json()
        cond_names = [c["display_name"] or c["name"] for c in data["conditions"]]
        assert "Ready to Occupy" not in cond_names
