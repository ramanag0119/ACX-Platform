"""Phase 3.0 write tests: facility, rooms, room catalogue, offers, events, holidays.

Run:  python -m pytest tests/test_catalog_write_api.py -q

These six tables had no endpoint at all before Phase 3.0, so both the reads and
the writes are new and both are exercised here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM amenity_type")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def amenity_type_id(db):
    return db.execute(text("SELECT id FROM amenity_type ORDER BY name LIMIT 1")).scalar_one()


@pytest.fixture(scope="module")
def package_id(db):
    return db.execute(text("SELECT id FROM package ORDER BY name LIMIT 1")).scalar_one()


@pytest.fixture(scope="module")
def property_chain_id(db):
    return db.execute(
        text("SELECT id FROM property_chain WHERE level_two_id IS NOT NULL LIMIT 1")
    ).scalar_one()


# ---------------------------------------------------------------------------
# The new read endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,sql",
    [
        ("amenity-types", "SELECT count(*) FROM amenity_type"),
        ("packages", "SELECT count(*) FROM package"),
        ("features", "SELECT count(*) FROM feature"),
        ("offers", "SELECT count(*) FROM promo_code"),
        ("events", "SELECT count(*) FROM facility_event"),
        ("holidays", "SELECT count(*) FROM occasion"),
    ],
)
def test_new_read_endpoints_are_database_backed(api, db, path, sql):
    body = api.get(f"{V1}/{path}?page_size=100").json()
    assert body["total"] == db.execute(text(sql)).scalar_one()


def test_packages_expose_their_features_and_room_counts(api, db):
    """`package_feature` and the rooms on that package -- both real joins."""
    body = api.get(f"{V1}/packages?page_size=100").json()
    assert body["total"] > 0
    total_links = db.execute(text("SELECT count(*) FROM package_feature")).scalar_one()
    assert sum(len(p["feature_names"]) for p in body["items"]) == total_links
    total_rooms = db.execute(
        text("SELECT count(*) FROM amenity WHERE package_id IS NOT NULL")
    ).scalar_one()
    assert sum(p["room_count"] for p in body["items"]) == total_rooms


def test_offers_expose_their_room_scope(api, db):
    body = api.get(f"{V1}/offers?page_size=100").json()
    links = db.execute(text("SELECT count(*) FROM promo_code_amenity")).scalar_one()
    assert sum(len(o["room_names"]) for o in body["items"]) == links


def test_holiday_types_come_from_the_lookup(api, db):
    body = api.get(f"{V1}/holidays/types").json()
    assert len(body) == db.execute(text("SELECT count(*) FROM occasion_type")).scalar_one()


# ---------------------------------------------------------------------------
# Amenity types, features, packages
# ---------------------------------------------------------------------------


def test_create_amenity_type_persists(api, db, unique, cleanup):
    r = api.post(
        f"{V1}/amenity-types",
        json={"name": f"Test Type {unique}", "amenity_category": "room"},
    )
    assert r.status_code == 201
    cleanup.add("amenity_type", r.json()["id"])
    assert db.execute(
        text("SELECT amenity_category FROM amenity_type WHERE id = :i"),
        {"i": r.json()["id"]},
    ).scalar_one() == "room"


def test_invalid_amenity_category_is_rejected(api, unique):
    r = api.post(
        f"{V1}/amenity-types",
        json={"name": f"Bad {unique}", "amenity_category": "penthouse"},
    )
    assert r.status_code == 422


def test_create_feature_persists(api, db, unique, cleanup):
    r = api.post(f"{V1}/features", json={"feature_name": f"Test Feature {unique}"})
    assert r.status_code == 201
    cleanup.add("feature", r.json()["id"])
    assert db.execute(
        text("SELECT count(*) FROM feature WHERE id = :i"), {"i": r.json()["id"]}
    ).scalar_one() == 1


def test_create_package_with_features_writes_the_link_rows(
    api, db, amenity_type_id, unique, cleanup
):
    feature = api.post(
        f"{V1}/features", json={"feature_name": f"Pkg Feature {unique}"}
    ).json()

    r = api.post(
        f"{V1}/packages",
        json={
            "name": f"Test Package {unique}",
            "amenity_type": str(amenity_type_id),
            "feature_ids": [feature["id"]],
        },
    )
    assert r.status_code == 201
    package_id = r.json()["id"]
    cleanup.sql("DELETE FROM package_feature WHERE package_id = :value",
                {"value": package_id})
    cleanup.add("package", package_id)
    cleanup.add("feature", feature["id"])

    assert r.json()["feature_names"] == [f"Pkg Feature {unique}"]
    assert db.execute(
        text("SELECT count(*) FROM package_feature WHERE package_id = :p"),
        {"p": package_id},
    ).scalar_one() == 1


def test_updating_package_features_replaces_them(api, db, amenity_type_id, unique, cleanup):
    first = api.post(f"{V1}/features", json={"feature_name": f"F1 {unique}"}).json()
    second = api.post(f"{V1}/features", json={"feature_name": f"F2 {unique}"}).json()
    package = api.post(
        f"{V1}/packages",
        json={"name": f"Swap Package {unique}", "amenity_type": str(amenity_type_id),
              "feature_ids": [first["id"]]},
    ).json()
    cleanup.sql("DELETE FROM package_feature WHERE package_id = :value",
                {"value": package["id"]})
    cleanup.add("package", package["id"])
    cleanup.add("feature", first["id"])
    cleanup.add("feature", second["id"])

    r = api.patch(f"{V1}/packages/{package['id']}", json={"feature_ids": [second["id"]]})
    assert r.status_code == 200
    assert r.json()["feature_names"] == [f"F2 {unique}"]
    db.rollback()
    assert db.execute(
        text("SELECT count(*) FROM package_feature WHERE package_id = :p"),
        {"p": package["id"]},
    ).scalar_one() == 1


def test_duplicate_package_name_is_409(api, amenity_type_id, unique, cleanup):
    name = f"Dup Package {unique}"
    first = api.post(
        f"{V1}/packages", json={"name": name, "amenity_type": str(amenity_type_id)}
    ).json()
    cleanup.add("package", first["id"])

    r = api.post(
        f"{V1}/packages", json={"name": name, "amenity_type": str(amenity_type_id)}
    )
    assert r.status_code == 409


def test_unknown_feature_reference_is_rejected(api, amenity_type_id, unique):
    r = api.post(
        f"{V1}/packages",
        json={"name": f"Ghost Feature {unique}", "amenity_type": str(amenity_type_id),
              "feature_ids": [str(uuid.uuid4())]},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


def test_create_room_persists_and_is_visible(
    api, db, amenity_type_id, package_id, property_chain_id, unique, cleanup
):
    name = f"T{unique[:5]}"
    r = api.post(
        f"{V1}/rooms",
        json={
            "name": name,
            "amenity_type_id": str(amenity_type_id),
            "package_id": str(package_id),
            "property_chain_id": str(property_chain_id),
        },
    )
    assert r.status_code == 201
    cleanup.add("amenity", r.json()["id"])

    body = r.json()
    assert body["name"] == name
    # A new room starts Unavailable (2), the column's own default.
    assert body["status"] == 2
    # And the building/floor projection resolves through property_chain.
    assert body["building_id"] is not None

    listed = api.get(f"{V1}/rooms?page_size=100").json()
    assert name in [item["name"] for item in listed["items"]]


def test_duplicate_room_name_in_the_same_facility_is_409(
    api, db, amenity_type_id, package_id, unique, cleanup
):
    existing = db.execute(text("SELECT name FROM amenity LIMIT 1")).scalar_one()
    r = api.post(
        f"{V1}/rooms",
        json={"name": existing, "amenity_type_id": str(amenity_type_id),
              "package_id": str(package_id)},
    )
    assert r.status_code == 409


def test_room_requires_an_existing_package(api, amenity_type_id, unique):
    r = api.post(
        f"{V1}/rooms",
        json={"name": f"NP{unique[:4]}", "amenity_type_id": str(amenity_type_id),
              "package_id": str(uuid.uuid4())},
    )
    assert r.status_code == 422


def test_update_room_name(api, db, amenity_type_id, package_id, unique, cleanup):
    created = api.post(
        f"{V1}/rooms",
        json={"name": f"U{unique[:5]}", "amenity_type_id": str(amenity_type_id),
              "package_id": str(package_id)},
    ).json()
    cleanup.add("amenity", created["id"])

    r = api.patch(f"{V1}/rooms/{created['id']}", json={"name": f"V{unique[:5]}"})
    assert r.status_code == 200
    assert db.execute(
        text("SELECT name FROM amenity WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == f"V{unique[:5]}"


def test_room_status_is_not_settable_here(api, amenity_type_id, package_id, unique, cleanup):
    """Status belongs to the occupancy workflow, which guards live stays."""
    created = api.post(
        f"{V1}/rooms",
        json={"name": f"S{unique[:5]}", "amenity_type_id": str(amenity_type_id),
              "package_id": str(package_id)},
    ).json()
    cleanup.add("amenity", created["id"])

    r = api.patch(f"{V1}/rooms/{created['id']}", json={"status": 0})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Facility
# ---------------------------------------------------------------------------


def test_update_facility_persists_and_restores(api, db, cleanup):
    facility = db.execute(text("SELECT id, city FROM facility LIMIT 1")).one()
    cleanup.sql("UPDATE facility SET city = :city WHERE id = :value",
                {"city": facility.city, "value": facility.id})

    r = api.patch(f"{V1}/facilities/{facility.id}", json={"city": "Test City"})
    assert r.status_code == 200
    assert r.json()["city"] == "Test City"
    db.rollback()
    assert db.execute(
        text("SELECT city FROM facility WHERE id = :i"), {"i": facility.id}
    ).scalar_one() == "Test City"


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


def test_create_offer_with_room_scope(api, db, unique, cleanup):
    room_id = db.execute(text("SELECT id FROM amenity ORDER BY name LIMIT 1")).scalar_one()
    start = datetime.now(UTC)
    r = api.post(
        f"{V1}/offers",
        json={
            "promo_code": f"TEST{unique.upper()}",
            "offer_name": f"Test Offer {unique}",
            "discount_percentage": "15",
            "start_time": start.isoformat(),
            "expiry_time": (start + timedelta(days=30)).isoformat(),
            "amenity_ids": [str(room_id)],
        },
    )
    assert r.status_code == 201
    offer_id = r.json()["id"]
    cleanup.sql("DELETE FROM promo_code_amenity WHERE promo_code_id = :value",
                {"value": offer_id})
    cleanup.add("promo_code", offer_id)

    assert len(r.json()["room_names"]) == 1
    assert db.execute(
        text("SELECT discount_percentage FROM promo_code WHERE id = :i"), {"i": offer_id}
    ).scalar_one() == 15


def test_duplicate_promo_code_is_409(api, unique, cleanup):
    code = f"DUP{unique.upper()}"
    first = api.post(f"{V1}/offers", json={"promo_code": code}).json()
    cleanup.add("promo_code", first["id"])
    r = api.post(f"{V1}/offers", json={"promo_code": code})
    assert r.status_code == 409


def test_offer_window_must_be_ordered(api, unique):
    start = datetime.now(UTC)
    r = api.post(
        f"{V1}/offers",
        json={"promo_code": f"WIN{unique.upper()}",
              "start_time": start.isoformat(),
              "expiry_time": (start - timedelta(days=1)).isoformat()},
    )
    assert r.status_code == 422


def test_discount_above_100_is_rejected(api, unique):
    r = api.post(
        f"{V1}/offers",
        json={"promo_code": f"BIG{unique.upper()}", "discount_percentage": "150"},
    )
    assert r.status_code == 422


def test_update_offer(api, db, unique, cleanup):
    created = api.post(f"{V1}/offers", json={"promo_code": f"UPD{unique.upper()}"}).json()
    cleanup.add("promo_code", created["id"])

    r = api.patch(f"{V1}/offers/{created['id']}", json={"offer_name": "Renamed Offer"})
    assert r.status_code == 200
    assert db.execute(
        text("SELECT offer_name FROM promo_code WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "Renamed Offer"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_create_event_persists(api, db, unique, cleanup):
    start = datetime.now(UTC) + timedelta(days=5)
    r = api.post(
        f"{V1}/events",
        json={
            "name": f"Test Event {unique}",
            "venue": "Main Hall",
            "chief_guests": "Test Guest",
            "expected_attendees": 120,
            "start_date_time": start.isoformat(),
            "end_date_time": (start + timedelta(hours=4)).isoformat(),
        },
    )
    assert r.status_code == 201
    cleanup.add("facility_event", r.json()["id"])
    row = db.execute(
        text("SELECT name, expected_attendees, facility_id FROM facility_event WHERE id = :i"),
        {"i": r.json()["id"]},
    ).one()
    assert row.expected_attendees == 120
    assert row.facility_id is not None


def test_event_window_must_be_ordered(api, unique):
    start = datetime.now(UTC)
    r = api.post(
        f"{V1}/events",
        json={"name": f"Bad Event {unique}", "start_date_time": start.isoformat(),
              "end_date_time": (start - timedelta(hours=1)).isoformat()},
    )
    assert r.status_code == 422


def test_interested_attendees_cannot_be_set(api, unique):
    """It is a guest-app counter, not an operator field."""
    r = api.post(
        f"{V1}/events", json={"name": f"Counter {unique}", "interested_attendees": 999}
    )
    assert r.status_code == 422


def test_update_event(api, db, unique, cleanup):
    created = api.post(f"{V1}/events", json={"name": f"Edit Event {unique}"}).json()
    cleanup.add("facility_event", created["id"])

    r = api.patch(f"{V1}/events/{created['id']}", json={"venue": "Rooftop"})
    assert r.status_code == 200
    assert db.execute(
        text("SELECT venue FROM facility_event WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "Rooftop"


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------


def test_create_holiday_derives_month_and_day(api, db, unique, cleanup):
    """`occasion.month` / `day_of_month` are NOT NULL and follow the start date."""
    occasion_type = api.get(f"{V1}/holidays/types").json()[0]["id"]
    start = date(2027, 3, 17)

    r = api.post(
        f"{V1}/holidays",
        json={
            "occasion_type": occasion_type,
            "occasion_name": f"Test Holiday {unique}",
            "occasion_start_date": start.isoformat(),
            "occasion_end_date": (start + timedelta(days=2)).isoformat(),
            "is_repeatable": 1,
        },
    )
    assert r.status_code == 201
    cleanup.add("occasion", r.json()["id"])

    row = db.execute(
        text("SELECT month, day_of_month, is_repeatable FROM occasion WHERE id = :i"),
        {"i": r.json()["id"]},
    ).one()
    assert row.month == 3
    assert row.day_of_month == 17
    assert row.is_repeatable == 1


def test_holiday_end_before_start_is_rejected(api, unique):
    occasion_type = api.get(f"{V1}/holidays/types").json()[0]["id"]
    r = api.post(
        f"{V1}/holidays",
        json={"occasion_type": occasion_type, "occasion_name": f"Bad {unique}",
              "occasion_start_date": "2027-03-17", "occasion_end_date": "2027-03-01"},
    )
    assert r.status_code == 422


def test_unknown_occasion_type_is_rejected(api, unique):
    r = api.post(
        f"{V1}/holidays",
        json={"occasion_type": 999, "occasion_start_date": "2027-01-01"},
    )
    assert r.status_code == 422


def test_update_holiday_recomputes_month_and_day(api, db, unique, cleanup):
    occasion_type = api.get(f"{V1}/holidays/types").json()[0]["id"]
    created = api.post(
        f"{V1}/holidays",
        json={"occasion_type": occasion_type, "occasion_name": f"Move {unique}",
              "occasion_start_date": "2027-03-17"},
    ).json()
    cleanup.add("occasion", created["id"])

    r = api.patch(
        f"{V1}/holidays/{created['id']}", json={"occasion_start_date": "2027-12-25"}
    )
    assert r.status_code == 200
    db.rollback()
    row = db.execute(
        text("SELECT month, day_of_month FROM occasion WHERE id = :i"),
        {"i": created["id"]},
    ).one()
    assert (row.month, row.day_of_month) == (12, 25)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_anonymous_cannot_write(anon_api, unique):
    assert anon_api.post(f"{V1}/features", json={"feature_name": f"X {unique}"}).status_code == 401
    assert anon_api.post(f"{V1}/offers", json={"promo_code": f"X{unique}"}).status_code == 401


def test_duty_manager_may_edit_marketing_but_not_the_facility(
    manager_api, db, unique, cleanup
):
    """Seeded grants: offers/events/holidays yes, facility_management no."""
    offer = manager_api.post(f"{V1}/offers", json={"promo_code": f"MGR{unique.upper()}"})
    assert offer.status_code == 201
    cleanup.add("promo_code", offer.json()["id"])

    event = manager_api.post(f"{V1}/events", json={"name": f"Mgr Event {unique}"})
    assert event.status_code == 201
    cleanup.add("facility_event", event.json()["id"])

    denied = manager_api.post(
        f"{V1}/amenity-types", json={"name": f"No {unique}", "amenity_category": "room"}
    )
    assert denied.status_code == 403


def test_a_failed_feature_link_rolls_the_package_back(api, db, amenity_type_id, unique):
    before = db.execute(text("SELECT count(*) FROM package")).scalar_one()
    r = api.post(
        f"{V1}/packages",
        json={"name": f"Rollback Pkg {unique}", "amenity_type": str(amenity_type_id),
              "feature_ids": [str(uuid.uuid4())]},
    )
    assert r.status_code == 422
    db.rollback()
    assert db.execute(text("SELECT count(*) FROM package")).scalar_one() == before
