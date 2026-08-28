"""Phase 3.0 write tests: the stay lifecycle, allocation and room state.

Run:  python -m pytest tests/test_stay_write_api.py -q

The room-state mapping asserted here is the one the seeded data already holds:
allocated -> Allotted (3), checked in -> Occupied (1), checked out or cancelled
-> Available (0). Every assertion is checked against PostgreSQL directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX

ROOM_AVAILABLE, ROOM_OCCUPIED, ROOM_ALLOTTED = 0, 1, 3


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM stay")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


def _stay_payload(guest_id, **overrides) -> dict:
    checkin = datetime.now(UTC) + timedelta(days=1)
    payload = {
        "booking_user_id": str(guest_id),
        "expected_checkin_time": checkin.isoformat(),
        "expected_checkout_time": (checkin + timedelta(days=2)).isoformat(),
        "no_of_guests": 2,
    }
    payload.update(overrides)
    return payload


def _room_status(db, room_id) -> int:
    db.rollback()  # this session must not hold a stale snapshot
    return db.execute(
        text("SELECT status FROM amenity WHERE id = :i"), {"i": room_id}
    ).scalar_one()


def _track_stay(cleanup, stay_id) -> None:
    cleanup.sql("DELETE FROM stay_user WHERE stay_id = :value", {"value": stay_id})
    cleanup.sql("DELETE FROM room_allocation WHERE stay_id = :value", {"value": stay_id})
    cleanup.add("stay", stay_id)


def _restore_room(cleanup, db, room_id) -> None:
    """Put a seeded room's status back exactly as it was."""
    original = db.execute(
        text("SELECT status FROM amenity WHERE id = :i"), {"i": room_id}
    ).scalar_one()
    cleanup.sql(
        "UPDATE amenity SET status = :status WHERE id = :value",
        {"status": original, "value": room_id},
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_stay_persists_with_a_generated_reference(api, db, guest_id, cleanup):
    r = api.post(f"{V1}/stays", json=_stay_payload(guest_id))
    assert r.status_code == 201
    body = r.json()
    _track_stay(cleanup, body["id"])

    assert body["internal_stay_ref_number"].startswith("STY-")
    row = db.execute(
        text("SELECT status, no_of_guests, created_by, request_source "
             "FROM stay WHERE id = :i"),
        {"i": body["id"]},
    ).one()
    assert row.status == "pending"
    assert row.no_of_guests == 2
    assert row.created_by is not None
    assert row.request_source == "ikanos"


def test_created_stay_is_visible_through_the_read_endpoint(api, guest_id, cleanup):
    created = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, created["id"])

    listed = api.get(f"{V1}/stays?page_size=100").json()
    assert created["id"] in [item["id"] for item in listed["items"]]
    assert api.get(f"{V1}/stays/{created['id']}").status_code == 200


def test_create_stay_with_rooms_allocates_and_marks_them_allotted(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    r = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    )
    assert r.status_code == 201
    body = r.json()
    _track_stay(cleanup, body["id"])

    assert len(body["room_allocations"]) == 1
    assert body["room_count"] == 1
    assert _room_status(db, free_room) == ROOM_ALLOTTED


def test_checkout_before_checkin_is_rejected_by_validation(api, guest_id):
    checkin = datetime.now(UTC) + timedelta(days=2)
    r = api.post(
        f"{V1}/stays",
        json=_stay_payload(
            guest_id,
            expected_checkin_time=checkin.isoformat(),
            expected_checkout_time=(checkin - timedelta(days=1)).isoformat(),
        ),
    )
    assert r.status_code == 422
    assert "after" in r.json()["error"]["message"]


def test_unknown_booking_user_is_rejected(api):
    r = api.post(f"{V1}/stays", json=_stay_payload(uuid.uuid4()))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Check-in / check-out
# ---------------------------------------------------------------------------


def test_check_in_activates_the_stay_and_occupies_the_room(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(f"{V1}/stays/{stay['id']}/check-in", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "active"
    assert body["is_checked_in"] is True
    assert body["actual_checkin_time"] is not None

    row = db.execute(
        text("SELECT status, actual_checkin_time FROM stay WHERE id = :i"),
        {"i": stay["id"]},
    ).one()
    assert row.status == "active"
    assert row.actual_checkin_time is not None
    assert _room_status(db, free_room) == ROOM_OCCUPIED


def test_check_in_without_a_room_is_rejected(api, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(f"{V1}/stays/{stay['id']}/check-in", json={})
    assert r.status_code == 422
    assert "Allocate a room" in r.json()["error"]["message"]


def test_double_check_in_is_409(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    assert api.post(f"{V1}/stays/{stay['id']}/check-in", json={}).status_code == 200
    r = api.post(f"{V1}/stays/{stay['id']}/check-in", json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_check_out_closes_the_stay_and_releases_the_room(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])
    api.post(f"{V1}/stays/{stay['id']}/check-in", json={})

    r = api.post(f"{V1}/stays/{stay['id']}/check-out", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "checked out"
    assert body["actual_checkout_time"] is not None

    assert db.execute(
        text("SELECT status FROM stay WHERE id = :i"), {"i": stay["id"]}
    ).scalar_one() == "checked out"
    assert _room_status(db, free_room) == ROOM_AVAILABLE


def test_check_out_before_check_in_is_409(api, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])
    r = api.post(f"{V1}/stays/{stay['id']}/check-out", json={})
    assert r.status_code == 409


def test_check_in_on_an_unknown_stay_is_404(api):
    r = api.post(f"{V1}/stays/{uuid.uuid4()}/check-in", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Extend, status, documents, cancel
# ---------------------------------------------------------------------------


def test_extend_moves_the_expected_checkout_forward(api, db, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    new_checkout = datetime.fromisoformat(stay["expected_checkout_time"]) + timedelta(days=3)
    r = api.post(
        f"{V1}/stays/{stay['id']}/extend",
        json={"expected_checkout_time": new_checkout.isoformat()},
    )
    assert r.status_code == 200
    stored = db.execute(
        text("SELECT expected_checkout_time FROM stay WHERE id = :i"), {"i": stay["id"]}
    ).scalar_one()
    assert stored.date() == new_checkout.date()


def test_extending_backwards_is_rejected(api, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    earlier = datetime.fromisoformat(stay["expected_checkout_time"]) - timedelta(days=1)
    r = api.post(
        f"{V1}/stays/{stay['id']}/extend",
        json={"expected_checkout_time": earlier.isoformat()},
    )
    assert r.status_code == 422
    assert "later" in r.json()["error"]["message"]


def test_status_endpoint_walks_the_checkout_approval_flow(api, db, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    for status_value in ("checkout pending", "checkout accepted", "checkout rejected"):
        r = api.post(f"{V1}/stays/{stay['id']}/status", json={"status": status_value})
        assert r.status_code == 200, r.text
        assert db.execute(
            text("SELECT status FROM stay WHERE id = :i"), {"i": stay["id"]}
        ).scalar_one() == status_value


def test_status_endpoint_refuses_the_terminal_states(api, guest_id, cleanup):
    """Those must go through check-out / cancel so rooms are released with them."""
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    for status_value in ("checked out", "cancelled"):
        r = api.post(f"{V1}/stays/{stay['id']}/status", json={"status": status_value})
        assert r.status_code == 422
        assert "action" in r.json()["error"]["message"]


def test_invalid_status_value_is_rejected_by_the_schema(api, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])
    r = api.post(f"{V1}/stays/{stay['id']}/status", json={"status": "checked-in"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_document_approval_persists(api, db, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(
        f"{V1}/stays/{stay['id']}/documents/approval",
        json={"document_approval_status": "approved"},
    )
    assert r.status_code == 200
    assert db.execute(
        text("SELECT document_approval_status FROM stay WHERE id = :i"), {"i": stay["id"]}
    ).scalar_one() == "approved"


def test_cancel_releases_rooms(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])
    assert _room_status(db, free_room) == ROOM_ALLOTTED

    r = api.post(f"{V1}/stays/{stay['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert _room_status(db, free_room) == ROOM_AVAILABLE


def test_cancelling_an_in_house_stay_is_409(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])
    api.post(f"{V1}/stays/{stay['id']}/check-in", json={})

    r = api.post(f"{V1}/stays/{stay['id']}/cancel")
    assert r.status_code == 409
    assert "check it out" in r.json()["error"]["message"]


# ---------------------------------------------------------------------------
# Allocation and reallocation
# ---------------------------------------------------------------------------


def test_allocate_room_after_creation(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(
        f"{V1}/stays/{stay['id']}/room-allocations", json={"room_id": str(free_room)}
    )
    assert r.status_code == 201
    assert len(r.json()) == 1
    assert db.execute(
        text("SELECT count(*) FROM room_allocation WHERE stay_id = :s AND room_id = :r"),
        {"s": stay["id"], "r": free_room},
    ).scalar_one() == 1
    assert _room_status(db, free_room) == ROOM_ALLOTTED


def test_double_booking_the_same_room_is_409(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    first = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, first["id"])

    second = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, second["id"])

    r = api.post(
        f"{V1}/stays/{second['id']}/room-allocations", json={"room_id": str(free_room)}
    )
    assert r.status_code == 409
    assert "already allocated" in r.json()["error"]["message"]


def test_allocating_the_same_room_twice_to_one_stay_is_409(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(
        f"{V1}/stays/{stay['id']}/room-allocations", json={"room_id": str(free_room)}
    )
    assert r.status_code == 409


def test_reallocation_moves_the_stay_and_swaps_both_room_states(
    api, db, guest_id, free_room, second_free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    _restore_room(cleanup, db, second_free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])
    api.post(f"{V1}/stays/{stay['id']}/check-in", json={})
    allocation_id = stay["room_allocations"][0]["id"]

    r = api.patch(
        f"{V1}/room-allocations/{allocation_id}", json={"room_id": str(second_free_room)}
    )
    assert r.status_code == 200

    assert db.execute(
        text("SELECT room_id FROM room_allocation WHERE id = :i"), {"i": allocation_id}
    ).scalar_one() == second_free_room
    # The old room is free again and the new one carries the in-house state.
    assert _room_status(db, free_room) == ROOM_AVAILABLE
    assert _room_status(db, second_free_room) == ROOM_OCCUPIED


def test_reallocating_into_an_occupied_room_is_409_and_changes_nothing(
    api, db, guest_id, free_room, second_free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    _restore_room(cleanup, db, second_free_room)
    first = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, first["id"])
    second = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(second_free_room)])
    ).json()
    _track_stay(cleanup, second["id"])

    r = api.patch(
        f"{V1}/room-allocations/{second['room_allocations'][0]['id']}",
        json={"room_id": str(free_room)},
    )
    assert r.status_code == 409
    # Rolled back: the second stay still holds its original room.
    assert db.execute(
        text("SELECT room_id FROM room_allocation WHERE id = :i"),
        {"i": second["room_allocations"][0]["id"]},
    ).scalar_one() == second_free_room
    assert _room_status(db, second_free_room) == ROOM_ALLOTTED


def test_reallocating_to_the_same_room_is_rejected(
    api, db, guest_id, free_room, cleanup
):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    r = api.patch(
        f"{V1}/room-allocations/{stay['room_allocations'][0]['id']}",
        json={"room_id": str(free_room)},
    )
    assert r.status_code == 422


def test_release_allocation_frees_the_room(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    r = api.delete(f"{V1}/room-allocations/{stay['room_allocations'][0]['id']}")
    assert r.status_code == 204
    assert db.execute(
        text("SELECT count(*) FROM room_allocation WHERE stay_id = :s"),
        {"s": stay["id"]},
    ).scalar_one() == 0
    assert _room_status(db, free_room) == ROOM_AVAILABLE


def test_releasing_an_in_house_room_is_409(api, db, guest_id, free_room, cleanup):
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])
    api.post(f"{V1}/stays/{stay['id']}/check-in", json={})

    r = api.delete(f"{V1}/room-allocations/{stay['room_allocations'][0]['id']}")
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Occupants
# ---------------------------------------------------------------------------


def test_add_and_remove_an_occupant(api, db, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])

    r = api.post(f"{V1}/stays/{stay['id']}/occupants", json={"guest_id": str(guest_id)})
    assert r.status_code == 201
    occupants = r.json()
    assert len(occupants) == 1

    assert db.execute(
        text("SELECT count(*) FROM stay_user WHERE stay_id = :s"), {"s": stay["id"]}
    ).scalar_one() == 1

    removed = api.delete(f"{V1}/stay-occupants/{occupants[0]['id']}")
    assert removed.status_code == 204
    db.rollback()
    assert db.execute(
        text("SELECT count(*) FROM stay_user WHERE stay_id = :s"), {"s": stay["id"]}
    ).scalar_one() == 0


def test_the_same_occupant_twice_is_409(api, guest_id, cleanup):
    stay = api.post(f"{V1}/stays", json=_stay_payload(guest_id)).json()
    _track_stay(cleanup, stay["id"])
    api.post(f"{V1}/stays/{stay['id']}/occupants", json={"guest_id": str(guest_id)})
    r = api.post(f"{V1}/stays/{stay['id']}/occupants", json={"guest_id": str(guest_id)})
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Room state (Occupancy screen)
# ---------------------------------------------------------------------------


def test_set_dnd_and_power_save(api, db, free_room, cleanup):
    cleanup.sql(
        "UPDATE amenity SET is_dnd = NULL, power_save_mode = NULL WHERE id = :value",
        {"value": free_room},
    )
    r = api.patch(f"{V1}/occupancy/{free_room}", json={"is_dnd": 1, "power_save_mode": 1})
    assert r.status_code == 200
    row = db.execute(
        text("SELECT is_dnd, power_save_mode FROM amenity WHERE id = :i"),
        {"i": free_room},
    ).one()
    assert row.is_dnd == 1
    assert row.power_save_mode == 1


def test_marking_a_room_unavailable_while_a_stay_holds_it_is_409(
    api, db, guest_id, free_room, cleanup
):
    """The guard that keeps room state and the stay graph in step."""
    _restore_room(cleanup, db, free_room)
    stay = api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    ).json()
    _track_stay(cleanup, stay["id"])

    r = api.patch(f"{V1}/occupancy/{free_room}", json={"status": 2})
    assert r.status_code == 409
    assert "still holds this room" in r.json()["error"]["message"]


def test_room_conditions_are_replaced_not_appended(api, db, free_room, cleanup):
    original = db.execute(
        text("SELECT amenity_condition_id FROM amenity_condition_status WHERE amenity_id = :i"),
        {"i": free_room},
    ).scalars().all()
    cleanup.sql(
        "DELETE FROM amenity_condition_status WHERE amenity_id = :value",
        {"value": free_room},
    )
    for condition_id in original:
        cleanup.sql(
            "INSERT INTO amenity_condition_status (amenity_id, amenity_condition_id, status) "
            "VALUES (:value, :c, 1) ON CONFLICT DO NOTHING",
            {"value": free_room, "c": condition_id},
        )

    r = api.put(f"{V1}/occupancy/{free_room}/conditions", json={"condition_ids": [1, 3]})
    assert r.status_code == 200
    db.rollback()
    stored = set(
        db.execute(
            text("SELECT amenity_condition_id FROM amenity_condition_status "
                 "WHERE amenity_id = :i"),
            {"i": free_room},
        ).scalars()
    )
    assert stored == {1, 3}

    api.put(f"{V1}/occupancy/{free_room}/conditions", json={"condition_ids": [4]})
    db.rollback()
    stored = set(
        db.execute(
            text("SELECT amenity_condition_id FROM amenity_condition_status "
                 "WHERE amenity_id = :i"),
            {"i": free_room},
        ).scalars()
    )
    assert stored == {4}, "conditions must be replaced, not accumulated"


def test_unknown_condition_is_rejected(api, free_room):
    r = api.put(f"{V1}/occupancy/{free_room}/conditions", json={"condition_ids": [99]})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# RBAC and transaction safety
# ---------------------------------------------------------------------------


def test_anonymous_cannot_run_the_stay_workflow(anon_api, guest_id):
    assert anon_api.post(f"{V1}/stays", json=_stay_payload(guest_id)).status_code == 401
    assert anon_api.post(f"{V1}/stays/{uuid.uuid4()}/check-in", json={}).status_code == 401


def test_duty_manager_can_run_the_stay_workflow(manager_api, db, guest_id, free_room, cleanup):
    """`bookings` and `occupancy` write are both in the seeded manager grants."""
    _restore_room(cleanup, db, free_room)
    created = manager_api.post(
        f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(free_room)])
    )
    assert created.status_code == 201
    _track_stay(cleanup, created.json()["id"])
    assert manager_api.post(
        f"{V1}/stays/{created.json()['id']}/check-in", json={}
    ).status_code == 200


def test_a_failed_room_in_create_rolls_the_stay_back(api, db, guest_id):
    before = db.execute(text("SELECT count(*) FROM stay")).scalar_one()
    r = api.post(f"{V1}/stays", json=_stay_payload(guest_id, room_ids=[str(uuid.uuid4())]))
    assert r.status_code == 422
    db.rollback()
    assert db.execute(text("SELECT count(*) FROM stay")).scalar_one() == before


def test_seeded_stays_are_untouched_by_this_module(db):
    """The six seeded stays must still be exactly as Phase 1.8 left them."""
    db.rollback()
    rows = dict(
        db.execute(
            text("SELECT internal_stay_ref_number, status FROM stay "
                 "WHERE internal_stay_ref_number LIKE 'STY-2026-000%' "
                 "AND length(internal_stay_ref_number) = 13 ORDER BY 1")
        ).all()
    )
    assert rows["STY-2026-0001"] == "active"
    assert rows["STY-2026-0003"] == "pending"
    assert rows["STY-2026-0004"] == "checked out"
    assert rows["STY-2026-0005"] == "cancelled"
