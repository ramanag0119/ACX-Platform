"""Phase 3.0 write tests: service requests and the service catalogue.

Run:  python -m pytest tests/test_service_write_api.py -q
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX

STATUS_PENDING, STATUS_ASSIGNED, STATUS_COMPLETED, STATUS_CANCELLED = 1, 2, 4, 5


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM service_request")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def room_service(db):
    """(service_type id, a category of that type) straight from the seeded rows."""
    return db.execute(
        text("SELECT service_type, id FROM service_category ORDER BY category_name LIMIT 1")
    ).one()


@pytest.fixture(scope="module")
def priced_item(db):
    return db.execute(
        text("SELECT i.id, i.category_id, c.service_type, i.price_per_unit "
             "FROM service_category_item i "
             "JOIN service_category c ON c.id = i.category_id "
             "WHERE i.price_per_unit IS NOT NULL LIMIT 1")
    ).one()


def _track(cleanup, request_id) -> None:
    cleanup.sql("DELETE FROM service_request_item WHERE service_request_id = :value",
                {"value": request_id})
    cleanup.add("service_request", request_id)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_request_persists_with_a_generated_reference(api, db, room_service, cleanup):
    service_type, category_id = room_service
    r = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id),
              "description": "Write test request"},
    )
    assert r.status_code == 201
    body = r.json()
    _track(cleanup, body["id"])

    assert body["ref_number"].startswith("SR-")
    row = db.execute(
        text("SELECT status, description, created_by, updated_by, request_source "
             "FROM service_request WHERE id = :i"),
        {"i": body["id"]},
    ).one()
    assert row.status == STATUS_PENDING
    assert row.description == "Write test request"
    assert row.created_by is not None and row.updated_by is not None
    assert row.request_source == "ikanos"


def test_created_request_appears_in_the_list(api, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])

    listed = api.get(f"{V1}/service-requests?page_size=100").json()
    assert created["id"] in [item["id"] for item in listed["items"]]


def test_naming_an_assignee_creates_the_request_already_assigned(
    api, db, room_service, staff_id, cleanup
):
    """Every seeded row with an assignee sits at Assigned or beyond."""
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id),
              "assigned_to": str(staff_id)},
    ).json()
    _track(cleanup, created["id"])

    assert created["status"] == STATUS_ASSIGNED
    assert created["assignee"]["id"] == str(staff_id)


def test_item_lines_persist_and_copy_the_catalogue_price(api, db, priced_item, cleanup):
    item_id, category_id, service_type, price = priced_item
    created = api.post(
        f"{V1}/service-requests",
        json={
            "service_type": service_type,
            "category_id": str(category_id),
            "items": [{"item_id": str(item_id), "quantity": 3}],
        },
    ).json()
    _track(cleanup, created["id"])

    assert created["item_count"] == 1
    line = db.execute(
        text("SELECT quantity, price_per_unit FROM service_request_item "
             "WHERE service_request_id = :i"),
        {"i": created["id"]},
    ).one()
    assert line.quantity == 3
    assert line.price_per_unit == price, "the catalogue price is copied at creation"

    # net_amount is quantity x price, the only arithmetic the schema supports.
    net = db.execute(
        text("SELECT net_amount FROM service_request WHERE id = :i"), {"i": created["id"]}
    ).scalar_one()
    assert net == price * 3


def test_a_category_from_another_service_type_is_rejected(api, db, room_service):
    service_type, _category_id = room_service
    other = db.execute(
        text("SELECT id FROM service_category WHERE service_type <> :t LIMIT 1"),
        {"t": service_type},
    ).scalar_one()
    r = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(other)},
    )
    assert r.status_code == 422
    assert "different service type" in r.json()["error"]["message"]


def test_unknown_service_type_is_rejected(api):
    r = api.post(f"{V1}/service-requests", json={"service_type": 999})
    assert r.status_code == 422


def test_unknown_room_reference_is_rejected(api, room_service):
    service_type, category_id = room_service
    r = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id),
              "amenity_id": str(uuid.uuid4())},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Update / assign / complete / cancel
# ---------------------------------------------------------------------------


def test_assigning_an_existing_request_moves_it_to_assigned(
    api, db, room_service, staff_id, cleanup
):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])
    assert created["status"] == STATUS_PENDING

    r = api.patch(
        f"{V1}/service-requests/{created['id']}", json={"assigned_to": str(staff_id)}
    )
    assert r.status_code == 200
    assert r.json()["status"] == STATUS_ASSIGNED
    row = db.execute(
        text("SELECT status, assigned_to FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).one()
    assert row.status == STATUS_ASSIGNED
    assert row.assigned_to == staff_id


def test_completing_stamps_completed_on_and_leaving_clears_it(
    api, db, room_service, cleanup
):
    """The invariant every seeded row holds: completed_on <=> status 4."""
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])

    api.patch(f"{V1}/service-requests/{created['id']}", json={"status": STATUS_COMPLETED})
    assert db.execute(
        text("SELECT completed_on FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() is not None

    api.patch(f"{V1}/service-requests/{created['id']}", json={"status": STATUS_PENDING})
    db.rollback()
    assert db.execute(
        text("SELECT completed_on FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() is None


def test_status_reason_persists(api, db, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])

    api.patch(
        f"{V1}/service-requests/{created['id']}",
        json={"status": STATUS_CANCELLED, "status_reason": "Guest withdrew"},
    )
    assert db.execute(
        text("SELECT status_reason FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() == "Guest withdrew"


def test_cancel_endpoint_records_the_reason(api, db, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])

    r = api.post(
        f"{V1}/service-requests/{created['id']}/cancel", json={"reason": "Not required"}
    )
    assert r.status_code == 200
    row = db.execute(
        text("SELECT status, status_reason FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).one()
    assert row.status == STATUS_CANCELLED
    assert row.status_reason == "Not required"


def test_cancelling_a_completed_request_is_rejected(api, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])
    api.patch(f"{V1}/service-requests/{created['id']}", json={"status": STATUS_COMPLETED})

    r = api.post(f"{V1}/service-requests/{created['id']}/cancel", json={})
    assert r.status_code == 422
    assert "completed" in r.json()["error"]["message"]


def test_expected_date_round_trips(api, db, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])

    when = datetime.now(UTC) + timedelta(hours=6)
    api.patch(
        f"{V1}/service-requests/{created['id']}", json={"expected_date": when.isoformat()}
    )
    stored = db.execute(
        text("SELECT expected_date FROM service_request WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one()
    assert stored is not None


def test_replacing_item_lines_removes_the_old_ones(api, db, priced_item, cleanup):
    item_id, category_id, service_type, _price = priced_item
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id),
              "items": [{"item_id": str(item_id), "quantity": 1}]},
    ).json()
    _track(cleanup, created["id"])

    r = api.put(
        f"{V1}/service-requests/{created['id']}/items",
        json={"items": [{"item_id": str(item_id), "quantity": 5}]},
    )
    assert r.status_code == 200
    db.rollback()
    rows = db.execute(
        text("SELECT quantity FROM service_request_item WHERE service_request_id = :i"),
        {"i": created["id"]},
    ).scalars().all()
    assert rows == [5], "lines are replaced, not appended"


def test_update_unknown_request_is_404(api):
    r = api.patch(f"{V1}/service-requests/{uuid.uuid4()}", json={"description": "x"})
    assert r.status_code == 404


def test_invalid_status_is_rejected(api, room_service, cleanup):
    service_type, category_id = room_service
    created = api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    ).json()
    _track(cleanup, created["id"])
    r = api.patch(f"{V1}/service-requests/{created['id']}", json={"status": 9})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def test_create_category_and_item_persist(api, db, unique, cleanup):
    service_type = db.execute(text("SELECT id FROM service_type LIMIT 1")).scalar_one()

    category = api.post(
        f"{V1}/service-categories",
        json={"category_name": f"Test Category {unique}", "service_type": service_type},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    item = api.post(
        f"{V1}/service-items",
        json={"item_name": f"Test Item {unique}", "category_id": category_id,
              "price_per_unit": "125.50"},
    )
    assert item.status_code == 201
    cleanup.add("service_category_item", item.json()["id"])
    cleanup.add("service_category", category_id)

    assert db.execute(
        text("SELECT price_per_unit FROM service_category_item WHERE id = :i"),
        {"i": item.json()["id"]},
    ).scalar_one() == 125.50


def test_duplicate_category_name_is_409(api, db, unique, cleanup):
    service_type = db.execute(text("SELECT id FROM service_type LIMIT 1")).scalar_one()
    name = f"Dup Category {unique}"
    first = api.post(
        f"{V1}/service-categories",
        json={"category_name": name, "service_type": service_type},
    ).json()
    cleanup.add("service_category", first["id"])

    r = api.post(
        f"{V1}/service-categories",
        json={"category_name": name, "service_type": service_type},
    )
    assert r.status_code == 409


def test_update_item_price(api, db, unique, cleanup):
    service_type = db.execute(text("SELECT id FROM service_type LIMIT 1")).scalar_one()
    category_id = api.post(
        f"{V1}/service-categories",
        json={"category_name": f"Priced Cat {unique}", "service_type": service_type},
    ).json()["id"]
    item_id = api.post(
        f"{V1}/service-items",
        json={"item_name": f"Priced Item {unique}", "category_id": category_id},
    ).json()["id"]
    cleanup.add("service_category_item", item_id)
    cleanup.add("service_category", category_id)

    r = api.patch(f"{V1}/service-items/{item_id}", json={"price_per_unit": "99.00"})
    assert r.status_code == 200
    assert db.execute(
        text("SELECT price_per_unit FROM service_category_item WHERE id = :i"),
        {"i": item_id},
    ).scalar_one() == 99


def test_negative_price_is_rejected(api, db, unique, cleanup):
    service_type = db.execute(text("SELECT id FROM service_type LIMIT 1")).scalar_one()
    category_id = api.post(
        f"{V1}/service-categories",
        json={"category_name": f"Neg Cat {unique}", "service_type": service_type},
    ).json()["id"]
    cleanup.add("service_category", category_id)

    r = api.post(
        f"{V1}/service-items",
        json={"item_name": f"Neg {unique}", "category_id": category_id,
              "price_per_unit": "-5"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_anonymous_cannot_write(anon_api, room_service):
    service_type, category_id = room_service
    r = anon_api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    )
    assert r.status_code == 401


def test_duty_manager_may_track_requests_but_not_edit_the_catalogue(
    manager_api, db, room_service, unique, cleanup
):
    """Seeded grants: service_tracking yes, service_setup no."""
    service_type, category_id = room_service
    created = manager_api.post(
        f"{V1}/service-requests",
        json={"service_type": service_type, "category_id": str(category_id)},
    )
    assert created.status_code == 201
    _track(cleanup, created.json()["id"])

    denied = manager_api.post(
        f"{V1}/service-categories",
        json={"category_name": f"No {unique}", "service_type": service_type},
    )
    assert denied.status_code == 403


def test_a_failed_item_line_rolls_the_request_back(api, db, room_service):
    service_type, category_id = room_service
    before = db.execute(text("SELECT count(*) FROM service_request")).scalar_one()

    r = api.post(
        f"{V1}/service-requests",
        json={
            "service_type": service_type,
            "category_id": str(category_id),
            "items": [{"item_id": str(uuid.uuid4()), "quantity": 1}],
        },
    )
    assert r.status_code == 422
    db.rollback()
    assert db.execute(text("SELECT count(*) FROM service_request")).scalar_one() == before
