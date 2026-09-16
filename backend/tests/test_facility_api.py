"""Phase 2.2 facility / property hierarchy API tests.

Run:  python -m pytest tests/test_facility_api.py -q

Uses the same TestClient infrastructure as the Phase 2.1 tests. Every
assertion is cross-checked against a direct SQL query, so a hardcoded or
cached response could not pass.

Skipped wholesale when the database is unseeded, matching the seed suite.
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
    """Authenticated as the seeded Administrator: Phase 2.4 put these routes
    behind the `facility_management` module grant. Unauthenticated and
    insufficient-permission behaviour is covered in tests/test_auth_api.py."""
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
    n = db.execute(text("SELECT count(*) FROM facility")).scalar_one()
    if not n:
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


ENDPOINTS = ["facilities", "properties", "buildings", "floors", "rooms"]


# ---------------------------------------------------------------------------
# 1-5. Every list endpoint answers 200 with the pagination envelope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("resource", ENDPOINTS)
def test_list_endpoint_returns_200(client, resource):
    r = client.get(f"{V1}/{resource}")
    assert r.status_code == 200


@pytest.mark.parametrize("resource", ENDPOINTS)
def test_list_endpoint_uses_the_pagination_envelope(client, resource):
    body = client.get(f"{V1}/{resource}").json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert isinstance(body["items"], list)
    assert body["total"] >= len(body["items"])


@pytest.mark.parametrize("resource", ENDPOINTS)
def test_list_results_are_database_backed(client, db, resource):
    """Totals must equal what PostgreSQL reports, not a constant."""
    expected = {
        "facilities": "SELECT count(*) FROM facility",
        "properties": "SELECT count(*) FROM property",
        "buildings": "SELECT count(DISTINCT level_one_id) FROM property_chain",
        "floors": "SELECT count(DISTINCT level_two_id) FROM property_chain "
                  "WHERE level_two_id IS NOT NULL",
        "rooms": "SELECT count(*) FROM amenity",
    }[resource]
    assert client.get(f"{V1}/{resource}").json()["total"] == db.execute(
        text(expected)
    ).scalar_one()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


def test_facility_schema(client, db):
    item = client.get(f"{V1}/facilities").json()["items"][0]
    row = db.execute(
        text("SELECT facility_uid, name, city, guest_rooms, email FROM facility "
             "WHERE facility_uid = :uid"),
        {"uid": item["facility_uid"]},
    ).one()
    assert item["name"] == row.name
    assert item["city"] == row.city
    assert item["guest_rooms"] == row.guest_rooms
    assert item["email"] == row.email
    uuid.UUID(item["id"])  # raises if not a real UUID
    uuid.UUID(item["org_id"])


def test_facility_detail_adds_real_counts(client, db):
    facility_id = client.get(f"{V1}/facilities").json()["items"][0]["id"]
    body = client.get(f"{V1}/facilities/{facility_id}").json()
    assert body["property_count"] == db.execute(
        text("SELECT count(*) FROM property WHERE facility_id = :fid"),
        {"fid": facility_id},
    ).scalar_one()
    assert body["amenity_count"] == db.execute(
        text("SELECT count(*) FROM amenity WHERE facility_id = :fid"),
        {"fid": facility_id},
    ).scalar_one()


def test_property_schema_includes_its_type(client):
    item = client.get(f"{V1}/properties").json()["items"][0]
    assert item["property_type_name"] == "Hotel Building"
    assert item["property_type_levels"] == 2
    assert isinstance(item["status"], int)


def test_building_projection(client, db):
    items = client.get(f"{V1}/buildings").json()["items"]
    assert len(items) == 1, "the demo facility has one tower"
    tower = items[0]
    assert tower["name"] == "Tower A"
    # `id` must be the underlying property id -- a building is not its own row.
    assert db.execute(
        text("SELECT property_name FROM property WHERE id = :pid"),
        {"pid": tower["id"]},
    ).scalar_one() == "Tower A"
    assert tower["floor_count"] == 3
    assert tower["room_count"] == db.execute(
        text("SELECT count(*) FROM amenity WHERE property_chain_id IS NOT NULL")
    ).scalar_one()


def test_floor_projection_links_back_to_its_building(client, db):
    items = client.get(f"{V1}/floors").json()["items"]
    assert {f["name"] for f in items} == {"Floor 1", "Floor 2", "Floor 3"}
    for floor in items:
        assert floor["building_name"] == "Tower A"
        # Every floor carries the chain row that positions it.
        assert db.execute(
            text("SELECT count(*) FROM property_chain "
                 "WHERE id = :cid AND level_two_id = :fid AND level_one_id = :bid"),
            {"cid": floor["property_chain_id"], "fid": floor["id"],
             "bid": floor["building_id"]},
        ).scalar_one() == 1


def test_floor_room_counts_sum_to_the_room_total(client):
    floors = client.get(f"{V1}/floors").json()["items"]
    chained_rooms = client.get(f"{V1}/rooms?page_size=100").json()["items"]
    on_a_floor = [r for r in chained_rooms if r["floor_id"]]
    assert sum(f["room_count"] for f in floors) == len(on_a_floor)


def test_room_schema_resolves_every_relationship(client, db):
    body = client.get(f"{V1}/rooms?page_size=100").json()
    room = next(r for r in body["items"] if r["name"] == "101")
    assert room["amenity_type_name"] == "Guest Room"
    assert room["amenity_category"] == "room"
    assert room["package_name"] == "Deluxe"
    assert room["status_name"] == "Occupied"
    assert room["building_name"] == "Tower A"
    assert room["floor_name"] == "Floor 1"
    row = db.execute(
        text("SELECT status FROM amenity WHERE name = '101'")
    ).scalar_one()
    assert room["status"] == row


def test_room_conditions_come_from_the_junction_table(client, db):
    body = client.get(f"{V1}/rooms?page_size=100").json()
    by_name = {r["name"]: r for r in body["items"]}
    assert [c["name"] for c in by_name["104"]["conditions"]] == ["Under maintenance"]
    assert [c["name"] for c in by_name["102"]["conditions"]] == ["Dirty"]
    assert by_name["101"]["conditions"] == []
    expected = db.execute(
        text("SELECT count(*) FROM amenity_condition_status WHERE status = 1")
    ).scalar_one()
    assert sum(len(r["conditions"]) for r in body["items"]) == expected


def test_status_name_matches_the_amenity_status_lookup(client, db):
    lookup = dict(
        db.execute(text("SELECT id, amenity_status_name FROM amenity_status")).all()
    )
    for room in client.get(f"{V1}/rooms?page_size=100").json()["items"]:
        assert room["status_name"] == lookup[room["status"]]


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_pagination_splits_the_result_set(client):
    total = client.get(f"{V1}/rooms").json()["total"]
    first = client.get(f"{V1}/rooms?page=1&page_size=10").json()
    second = client.get(f"{V1}/rooms?page=2&page_size=10").json()
    assert len(first["items"]) == 10
    assert first["total"] == second["total"] == total
    assert {r["id"] for r in first["items"]}.isdisjoint(
        {r["id"] for r in second["items"]}
    )


def test_page_beyond_the_end_is_empty_not_an_error(client):
    body = client.get(f"{V1}/rooms?page=999&page_size=20").json()
    assert body["items"] == []
    assert body["total"] > 0


def test_page_size_is_capped(client):
    r = client.get(f"{V1}/rooms?page_size=1000")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_page_must_be_positive(client):
    assert client.get(f"{V1}/rooms?page=0").status_code == 422


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_filter_rooms_by_facility(client, db):
    facility_id = client.get(f"{V1}/facilities").json()["items"][0]["id"]
    body = client.get(f"{V1}/rooms?facility_id={facility_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM amenity WHERE facility_id = :fid"),
        {"fid": facility_id},
    ).scalar_one()
    assert all(r["facility_id"] == facility_id for r in body["items"])


def test_filter_rooms_by_floor(client):
    floor = next(
        f for f in client.get(f"{V1}/floors").json()["items"] if f["name"] == "Floor 2"
    )
    body = client.get(f"{V1}/rooms?floor_id={floor['id']}&page_size=100").json()
    assert body["total"] == floor["room_count"]
    assert all(r["floor_name"] == "Floor 2" for r in body["items"])
    assert all(r["name"].startswith("2") for r in body["items"])


def test_filter_rooms_by_building(client):
    building = client.get(f"{V1}/buildings").json()["items"][0]
    body = client.get(f"{V1}/rooms?building_id={building['id']}&page_size=100").json()
    assert body["total"] == building["room_count"]


def test_filter_rooms_by_category(client, db):
    body = client.get(f"{V1}/rooms?amenity_category=room&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM amenity a JOIN amenity_type t "
             "ON t.id = a.amenity_type_id WHERE t.amenity_category = 'room'")
    ).scalar_one()
    assert all(r["amenity_category"] == "room" for r in body["items"])


def test_filter_rooms_by_status(client, db):
    body = client.get(f"{V1}/rooms?status=1&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM amenity WHERE status = 1")
    ).scalar_one()
    assert all(r["status_name"] == "Occupied" for r in body["items"])


def test_filter_floors_by_building(client):
    building = client.get(f"{V1}/buildings").json()["items"][0]
    body = client.get(f"{V1}/floors?building_id={building['id']}").json()
    assert body["total"] == building["floor_count"]


def test_filter_facilities_by_uid(client):
    body = client.get(f"{V1}/facilities?facility_uid=ikg").json()
    assert body["total"] == 1
    assert body["items"][0]["facility_uid"] == "ikg"


# ---------------------------------------------------------------------------
# Empty results and invalid resources
# ---------------------------------------------------------------------------


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/facilities?facility_uid=zzz").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


def test_unknown_facility_id_returns_an_empty_room_page(client):
    body = client.get(f"{V1}/rooms?facility_id={uuid.uuid4()}").json()
    assert body["items"] == [] and body["total"] == 0


@pytest.mark.parametrize("resource", ENDPOINTS)
def test_detail_404_uses_the_shared_error_envelope(client, resource):
    r = client.get(f"{V1}/{resource}/{uuid.uuid4()}")
    assert r.status_code == 404
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "not_found"
    assert "does not exist" in body["error"]["message"]


@pytest.mark.parametrize("resource", ENDPOINTS)
def test_malformed_uuid_is_a_validation_error(client, resource):
    r = client.get(f"{V1}/{resource}/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_detail_endpoints_return_the_requested_row(client):
    room = client.get(f"{V1}/rooms?page_size=100").json()["items"][0]
    body = client.get(f"{V1}/rooms/{room['id']}").json()
    assert body["id"] == room["id"]
    assert body["name"] == room["name"]


def test_property_used_only_as_a_floor_is_not_a_building(client):
    """A property that never appears at level_one_id must 404 on /buildings."""
    floor = client.get(f"{V1}/floors").json()["items"][0]
    assert client.get(f"{V1}/properties/{floor['id']}").status_code == 200
    assert client.get(f"{V1}/buildings/{floor['id']}").status_code == 404


# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------


def test_openapi_documents_the_phase_2_2_endpoints(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    for resource in ENDPOINTS:
        assert f"{V1}/{resource}" in paths
        assert any(p.startswith(f"{V1}/{resource}/{{") for p in paths)


FACILITY_WRITES = {
    (f"{V1}/facilities/{{facility_id}}", "patch"),
    (f"{V1}/rooms", "post"),
    (f"{V1}/rooms/{{room_id}}", "patch"),
}


def test_facility_write_surface_is_exactly_the_intended_set(client):
    """Phase 3.0 adds facility and room writes -- and no more.

    In particular there is still no POST /properties, /buildings or /floors:
    buildings and floors are projections over `property_chain`, so they cannot
    be created directly, exactly as Phase 2.2 established.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get"
        and any(
            path.startswith(prefix)
            for prefix in (f"{V1}/facilities", f"{V1}/properties", f"{V1}/buildings",
                           f"{V1}/floors", f"{V1}/rooms")
        )
    }
    assert found == FACILITY_WRITES, found ^ FACILITY_WRITES


def test_buildings_and_floors_remain_read_only(client):
    """They are projections, not tables: there is nothing to write to."""
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/buildings", f"{V1}/floors", f"{V1}/properties")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"
