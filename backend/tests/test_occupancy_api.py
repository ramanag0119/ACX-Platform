"""Phase 2.8 stay / occupancy / invoice API tests.

Run:  python -m pytest tests/test_occupancy_api.py -q

Same infrastructure as Phases 2.2-2.7. Every assertion is cross-checked
against a direct SQL query. Skipped wholesale when the database is unseeded.
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

BOOKINGS = [
    (f"{V1}/stays", "bookings"),
    (f"{V1}/invoices", "bookings"),
]
OCCUPANCY = [
    (f"{V1}/occupancy", "occupancy"),
    (f"{V1}/amenity-statuses", "occupancy"),
    (f"{V1}/amenity-conditions", "occupancy"),
]
ALL_ENDPOINTS = BOOKINGS + OCCUPANCY

#: The literal definition used by the API: checked in, not yet checked out.
IN_HOUSE_SQL = (
    "actual_checkin_time IS NOT NULL AND actual_checkout_time IS NULL"
)


@pytest.fixture(scope="module")
def client(admin_headers) -> TestClient:
    with TestClient(app, headers=admin_headers) as c:
        yield c


@pytest.fixture(scope="module")
def anon() -> TestClient:
    with TestClient(app) as c:
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
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def active_stay_id(db):
    return str(
        db.execute(
            text("SELECT id FROM stay WHERE internal_stay_ref_number = 'STY-2026-0001'")
        ).scalar_one()
    )


# ---------------------------------------------------------------------------
# Schema reality -- the concepts that do NOT exist
# ---------------------------------------------------------------------------


def test_no_booking_guest_or_occupancy_table_exists(db):
    """Documents why /bookings and /guests were not implemented."""
    tables = set(
        db.execute(
            text("SELECT table_name FROM information_schema.tables "
                 "WHERE table_schema = 'public'")
        ).scalars()
    )
    for absent in ("booking", "bookings", "reservation", "guest", "guests",
                   "occupancy", "check_in", "check_out", "room_assignment"):
        assert absent not in tables
    for present in ("stay", "stay_user", "room_allocation", "amenity"):
        assert present in tables


def test_no_bookings_or_guests_route_was_invented(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert f"{V1}/bookings" not in paths
    assert f"{V1}/guests" not in paths
    assert f"{V1}/stays" in paths


def test_stay_has_no_facility_column(db):
    """Which is why facility filters go through room_allocation."""
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='stay'")
        ).scalars()
    )
    assert "facility_id" not in cols
    assert {"actual_checkin_time", "actual_checkout_time"} <= cols


# ---------------------------------------------------------------------------
# Lists and database-backed totals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_list_returns_200_with_the_shared_envelope(client, path, module):
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1 and body["page_size"] == 20


@pytest.mark.parametrize(
    "path,sql",
    [
        (f"{V1}/stays", "SELECT count(*) FROM stay"),
        (f"{V1}/invoices", "SELECT count(*) FROM invoice"),
        (f"{V1}/occupancy", "SELECT count(*) FROM amenity"),
        (f"{V1}/amenity-statuses", "SELECT count(*) FROM amenity_status"),
        (f"{V1}/amenity-conditions", "SELECT count(*) FROM amenity_condition"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# Stay lifecycle -- check-in / check-out representation
# ---------------------------------------------------------------------------


def test_stay_statuses_span_the_real_vocabulary(client, db):
    statuses = {s["status"] for s in client.get(f"{V1}/stays?page_size=100").json()["items"]}
    assert statuses <= {
        "pending", "active", "checkout accepted", "checkout pending",
        "checkout rejected", "checked out", "cancelled",
    }
    assert {"pending", "active", "checked out", "cancelled"} <= statuses


def test_check_in_and_out_are_timestamp_columns_not_tables(client, db):
    body = client.get(f"{V1}/stays?page_size=100").json()
    for s in body["items"]:
        assert s["expected_checkin_time"] and s["expected_checkout_time"]
        # Derived flags must match the raw timestamps exactly.
        assert s["is_checked_in"] == (s["actual_checkin_time"] is not None)
        assert s["is_in_house"] == (
            s["actual_checkin_time"] is not None and s["actual_checkout_time"] is None
        )


def test_in_house_count_matches_sql(client, db):
    body = client.get(f"{V1}/stays?is_in_house=true&page_size=100").json()
    assert body["total"] == db.execute(
        text(f"SELECT count(*) FROM stay WHERE {IN_HOUSE_SQL}")
    ).scalar_one()
    assert all(s["is_in_house"] for s in body["items"])


def test_pending_stay_has_not_checked_in(client, db):
    body = client.get(f"{V1}/stays?status=pending&page_size=100").json()
    for s in body["items"]:
        assert s["actual_checkin_time"] is None
        assert s["is_checked_in"] is False


def test_checked_out_stay_has_both_timestamps(client):
    body = client.get(f"{V1}/stays?status=checked out&page_size=100").json()
    assert body["items"]
    for s in body["items"]:
        assert s["actual_checkin_time"] and s["actual_checkout_time"]
        assert s["is_in_house"] is False


def test_cancelled_stay_has_no_room_allocation(client, db):
    stay = client.get(f"{V1}/stays?status=cancelled&page_size=100").json()["items"][0]
    assert stay["room_count"] == 0
    assert client.get(f"{V1}/stays/{stay['id']}/room-allocations").json() == []


# ---------------------------------------------------------------------------
# Stay relationships
# ---------------------------------------------------------------------------


def test_stay_detail_resolves_every_sub_resource(client, db, active_stay_id):
    body = client.get(f"{V1}/stays/{active_stay_id}").json()
    assert body["internal_stay_ref_number"] == "STY-2026-0001"
    assert body["booker"]["name"] == "Aarav Sharma"
    assert body["occupant_count"] == len(body["occupants"]) == db.execute(
        text("SELECT count(*) FROM stay_user WHERE stay_id = :s"), {"s": active_stay_id}
    ).scalar_one()
    assert body["room_count"] == len(body["room_allocations"])
    assert body["room_allocations"][0]["room_name"] == "101"
    assert body["room_allocations"][0]["building_name"] == "Tower A"
    assert body["room_allocations"][0]["floor_name"] == "Floor 1"
    assert body["packages"] and body["packages"][0]["package_name"]
    assert body["documents"] and body["documents"][0]["attachment_id"]
    assert body["invoices"]


def test_guest_to_stay_relationship(client, db, active_stay_id):
    """stay_user is the guest <-> stay link; guests are app_user rows."""
    occupants = client.get(f"{V1}/stays/{active_stay_id}/occupants").json()
    assert len(occupants) == 2, "stay 0001 has a second occupant"
    for o in occupants:
        assert set(o["guest"]) == {"id", "name", "emp_id"}
        assert db.execute(
            text("SELECT is_staff FROM app_user WHERE id = :u"), {"u": o["guest"]["id"]}
        ).scalar_one() == 0, "occupants are guests, not staff"


def test_stay_to_room_allocation_relationship(client, db):
    rows = db.execute(
        text("""SELECT ra.stay_id, ra.room_id, am.name FROM room_allocation ra
                JOIN amenity am ON am.id = ra.room_id""")
    ).all()
    assert rows
    for stay_id, room_id, room_name in rows:
        allocations = client.get(f"{V1}/stays/{stay_id}/room-allocations").json()
        assert any(a["room_id"] == str(room_id) and a["room_name"] == room_name
                   for a in allocations)


def test_stay_documents_expose_only_a_pointer(client, db, active_stay_id):
    docs = client.get(f"{V1}/stays/{active_stay_id}/documents").json()
    assert docs
    for d in docs:
        assert set(d) == {"id", "guest", "attachment_id", "document_approval_status",
                          "status", "created_on"}
        assert d["document_approval_status"] in {"approved", "rejected", "pending"}
    # No document type or number exists in the schema.
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='user_document'")
        ).scalars()
    )
    assert "document_type" not in cols and "document_number" not in cols


def test_stay_404_on_every_sub_resource(client):
    missing = uuid.uuid4()
    for suffix in ("", "/occupants", "/room-allocations", "/documents"):
        r = client.get(f"{V1}/stays/{missing}{suffix}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Occupancy -- and the deliberate non-reconciliation
# ---------------------------------------------------------------------------


def test_occupancy_row_resolves_room_type_package_and_location(client):
    body = client.get(f"{V1}/occupancy?page_size=100").json()
    room = next(r for r in body["items"] if r["room_name"] == "101")
    assert room["amenity_type_name"] == "Guest Room"
    assert room["amenity_category"] == "room"
    assert room["package_name"] == "Deluxe"
    assert room["status_name"] == "Occupied"
    assert room["building_name"] == "Tower A"
    assert room["floor_name"] == "Floor 1"


def test_status_name_matches_the_amenity_status_lookup(client, db):
    lookup = dict(db.execute(text("SELECT id, amenity_status_name FROM amenity_status")).all())
    for r in client.get(f"{V1}/occupancy?page_size=100").json()["items"]:
        if r["status"] is not None:
            assert r["status_name"] == lookup[r["status"]]


def test_current_stay_is_derived_from_the_stay_graph(client, db):
    body = client.get(f"{V1}/occupancy?page_size=100").json()
    with_stay = [r for r in body["items"] if r["current_stay"]]
    expected = db.execute(
        text(f"""SELECT count(DISTINCT ra.room_id) FROM room_allocation ra
                 JOIN stay s ON s.id = ra.stay_id WHERE {IN_HOUSE_SQL}""")
    ).scalar_one()
    assert len(with_stay) == expected
    for r in with_stay:
        assert r["current_stay"]["actual_checkin_time"] is not None
        assert r["current_stay"]["booker"]


def test_amenity_status_and_stay_graph_are_reported_independently(client, db):
    """The schema does not keep them in step, and neither does the API.

    In the seeded data more amenities are flagged Occupied than have a guest
    in house. Both numbers are reported faithfully rather than reconciled.
    """
    body = client.get(f"{V1}/occupancy?page_size=100").json()
    flagged_occupied = [r for r in body["items"] if r["status_name"] == "Occupied"]
    actually_in_house = [r for r in body["items"] if r["current_stay"]]

    assert len(flagged_occupied) == db.execute(
        text("SELECT count(*) FROM amenity WHERE status = 1")
    ).scalar_one()
    assert len(actually_in_house) == db.execute(
        text(f"""SELECT count(DISTINCT ra.room_id) FROM room_allocation ra
                 JOIN stay s ON s.id = ra.stay_id WHERE {IN_HOUSE_SQL}""")
    ).scalar_one()
    # They genuinely differ in the seeded data -- that is the finding.
    assert len(flagged_occupied) != len(actually_in_house)


def test_is_occupied_filter_queries_the_stay_graph_not_the_flag(client, db):
    occupied = client.get(f"{V1}/occupancy?is_occupied=true&page_size=100").json()
    assert occupied["total"] == db.execute(
        text(f"""SELECT count(DISTINCT ra.room_id) FROM room_allocation ra
                 JOIN stay s ON s.id = ra.stay_id WHERE {IN_HOUSE_SQL}""")
    ).scalar_one()
    assert all(r["current_stay"] for r in occupied["items"])

    vacant = client.get(f"{V1}/occupancy?is_occupied=false&page_size=100").json()
    assert occupied["total"] + vacant["total"] == db.execute(
        text("SELECT count(*) FROM amenity")
    ).scalar_one()


def test_occupancy_conditions_come_from_the_junction(client, db):
    body = client.get(f"{V1}/occupancy?page_size=100").json()
    by_name = {r["room_name"]: r for r in body["items"]}
    assert [c["name"] for c in by_name["104"]["conditions"]] == ["Under maintenance"]
    assert by_name["101"]["conditions"] == []
    assert sum(len(r["conditions"]) for r in body["items"]) == db.execute(
        text("SELECT count(*) FROM amenity_condition_status WHERE status = 1")
    ).scalar_one()


def test_occupancy_detail_lists_occupants_and_devices(client, db):
    amenity_id = str(
        db.execute(text("SELECT id FROM amenity WHERE name = '101'")).scalar_one()
    )
    body = client.get(f"{V1}/occupancy/{amenity_id}").json()
    assert body["current_stay"]["internal_stay_ref_number"] == "STY-2026-0001"
    assert body["occupants"]
    assert body["device_count"] == db.execute(
        text("SELECT count(*) FROM device WHERE amenity_id = :a"), {"a": amenity_id}
    ).scalar_one()


def test_occupancy_detail_of_a_vacant_room(client, db):
    amenity_id = str(
        db.execute(
            text("""SELECT a.id FROM amenity a WHERE NOT EXISTS (
                        SELECT 1 FROM room_allocation ra JOIN stay s ON s.id = ra.stay_id
                        WHERE ra.room_id = a.id
                          AND s.actual_checkin_time IS NOT NULL
                          AND s.actual_checkout_time IS NULL) LIMIT 1""")
        ).scalar_one()
    )
    body = client.get(f"{V1}/occupancy/{amenity_id}").json()
    assert body["current_stay"] is None
    assert body["occupants"] == []


def test_occupancy_404(client):
    r = client.get(f"{V1}/occupancy/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_amenity_lookups_are_the_real_vocabularies(client):
    statuses = client.get(f"{V1}/amenity-statuses").json()["items"]
    assert [s["amenity_status_name"] for s in statuses] == [
        "Available", "Occupied", "Unavailable", "Allotted"
    ]
    assert statuses[0]["id"] == 0, "id 0 is a real, meaningful id"
    conditions = client.get(f"{V1}/amenity-conditions").json()["items"]
    assert [c["name"] for c in conditions] == [
        "Dirty", "Low battery", "Under maintenance", "Sanitation"
    ]


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


def test_invoice_has_no_payment_status(client, db):
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='invoice'")
        ).scalars()
    )
    assert "status" not in cols
    for i in client.get(f"{V1}/invoices?page_size=100").json()["items"]:
        assert "status" not in i
        assert "payment_status" not in i


def test_invoice_resolves_its_stay_and_amounts_are_consistent(client, db):
    body = client.get(f"{V1}/invoices?page_size=100").json()
    assert body["items"]
    for i in body["items"]:
        assert i["stay_ref_number"]
        assert float(i["total_amount"]) == pytest.approx(
            float(i["net_amount"]) + float(i["total_tax"])
        )


def test_filter_invoices_by_stay(client, db):
    stay_id, expected = db.execute(
        text("SELECT stay_id, count(*) FROM invoice GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(f"{V1}/invoices?stay_id={stay_id}").json()["total"] == expected


def test_invoice_404(client):
    assert client.get(f"{V1}/invoices/{uuid.uuid4()}").status_code == 404


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_stays_by_status(client, db):
    body = client.get(f"{V1}/stays?status=active&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM stay WHERE status = 'active'")
    ).scalar_one()


def test_filter_stays_by_facility_via_room_allocation(client, db):
    facility_id = str(db.execute(text("SELECT id FROM facility")).scalar_one())
    body = client.get(f"{V1}/stays?facility_id={facility_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("""SELECT count(DISTINCT s.id) FROM stay s
                JOIN room_allocation ra ON ra.stay_id = s.id
                JOIN amenity a ON a.id = ra.room_id
                WHERE a.facility_id = :f"""),
        {"f": facility_id},
    ).scalar_one()


def test_filter_stays_by_room_and_floor(client, db):
    room_id, expected = db.execute(
        text("SELECT room_id, count(*) FROM room_allocation GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(
        f"{V1}/stays?room_id={room_id}&page_size=100"
    ).json()["total"] == expected

    floor_id = str(
        db.execute(text("SELECT id FROM property WHERE property_name = 'Floor 1'")).scalar_one()
    )
    assert client.get(f"{V1}/stays?floor_id={floor_id}&page_size=100").json()["total"] == (
        db.execute(
            text("""SELECT count(DISTINCT s.id) FROM stay s
                    JOIN room_allocation ra ON ra.stay_id = s.id
                    JOIN amenity a ON a.id = ra.room_id
                    JOIN property_chain pc ON pc.id = a.property_chain_id
                    WHERE pc.level_two_id = :f"""),
            {"f": floor_id},
        ).scalar_one()
    )


def test_filter_stays_by_guest_matches_any_occupant(client, db):
    """Not just the booker -- stay_user is the occupant link."""
    guest_id, expected = db.execute(
        text("""SELECT app_user_id, count(DISTINCT stay_id) FROM stay_user
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(
        f"{V1}/stays?guest_id={guest_id}&page_size=100"
    ).json()["total"] == expected


def test_filter_stays_by_ref_number_and_source(client, db):
    body = client.get(f"{V1}/stays?ref_number=STY-2026-0002").json()
    assert body["total"] == 1
    assert client.get(f"{V1}/stays?request_source=ikanos&page_size=100").json()["total"] == (
        db.execute(text("SELECT count(*) FROM stay WHERE request_source = 'ikanos'")).scalar_one()
    )


def test_filter_occupancy_by_floor_and_category(client, db):
    floor_id = str(
        db.execute(text("SELECT id FROM property WHERE property_name = 'Floor 2'")).scalar_one()
    )
    body = client.get(f"{V1}/occupancy?floor_id={floor_id}&page_size=100").json()
    assert all(r["floor_name"] == "Floor 2" for r in body["items"])
    rooms = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100").json()
    assert rooms["total"] == db.execute(
        text("""SELECT count(*) FROM amenity a JOIN amenity_type t
                ON t.id = a.amenity_type_id WHERE t.amenity_category = 'room'""")
    ).scalar_one()


def test_filter_occupancy_by_condition(client, db):
    body = client.get(f"{V1}/occupancy?condition_id=3&page_size=100").json()
    assert body["total"] == db.execute(
        text("""SELECT count(*) FROM amenity_condition_status
                WHERE amenity_condition_id = 3 AND status = 1""")
    ).scalar_one()


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/stays?facility_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "query", ["is_in_house=maybe", "room_id=not-a-uuid", "expected_checkin_from=nope"]
)
def test_invalid_stay_filters_are_422(client, query):
    r = client.get(f"{V1}/stays?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("query", ["status=abc", "is_occupied=maybe", "condition_id=xyz"])
def test_invalid_occupancy_filters_are_422(client, query):
    assert client.get(f"{V1}/occupancy?{query}").status_code == 422


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    r = client.get(f"{path}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_occupancy(client):
    total = client.get(f"{V1}/occupancy").json()["total"]
    first = client.get(f"{V1}/occupancy?page=1&page_size=10").json()
    second = client.get(f"{V1}/occupancy?page=2&page_size=10").json()
    assert len(first["items"]) == 10
    assert first["total"] == second["total"] == total
    assert {r["amenity_id"] for r in first["items"]}.isdisjoint(
        {r["amenity_id"] for r in second["items"]}
    )


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/occupancy?page=999").json()
    assert body["items"] == [] and body["total"] > 0


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [f"{V1}/stays?page_size=100", f"{V1}/occupancy?page_size=100",
     f"{V1}/invoices?page_size=100"],
)
def test_no_credential_or_contact_leaks(client, path):
    raw = client.get(path).text.lower()
    for needle in ("password", "hash", "token", "secret", "authentication_code",
                   '"metadata"', '"email"', '"phone"'):
        assert needle not in raw, f"{needle!r} leaked from {path}"


def test_guest_references_are_narrow(client, active_stay_id):
    body = client.get(f"{V1}/stays/{active_stay_id}").json()
    assert set(body["booker"]) == {"id", "name", "emp_id"}
    for o in body["occupants"]:
        assert set(o["guest"]) == {"id", "name", "emp_id"}


# ---------------------------------------------------------------------------
# RBAC -- two distinct modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_rbac_module_is_a_real_registry_entry(db, path, module):
    assert db.execute(
        text("SELECT count(*) FROM role_module WHERE module_name = :m"), {"m": module}
    ).scalar_one() == 1


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_unauthenticated_is_401(anon, path, module):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_malformed_token_is_401(anon):
    assert anon.get(
        f"{V1}/stays", headers={"Authorization": "Bearer not.a.token"}
    ).status_code == 401


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_admin_is_allowed(client, path, module):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_manager_access_follows_the_database_grants(
    anon, manager_headers, db, path, module
):
    granted = db.execute(
        text("""SELECT count(*) FROM role r
                JOIN role_module_permission p ON p.role_id = r.id
                JOIN role_module m ON m.id = p.module_id
                WHERE r.role_type = 'manager' AND m.module_name = :m
                  AND p.read_access"""),
        {"m": module},
    ).scalar_one() > 0
    r = anon.get(path, headers=manager_headers)
    assert r.status_code == (200 if granted else 403)


def test_occupancy_and_bookings_are_separately_gated(db):
    """Housekeeping holds occupancy read-only but no bookings grant at all --
    the reason the two domains are not merged behind one module."""
    housekeeping = dict(
        db.execute(
            text("""SELECT m.module_name, p.read_access FROM role r
                    JOIN role_module_permission p ON p.role_id = r.id
                    JOIN role_module m ON m.id = p.module_id
                    WHERE r.name = 'Housekeeping'""")
        ).all()
    )
    assert housekeeping.get("occupancy") is True
    assert "bookings" not in housekeeping


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_phase_2_8_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/stays", f"{V1}/stays/{{stay_id}}",
        f"{V1}/stays/{{stay_id}}/occupants",
        f"{V1}/stays/{{stay_id}}/room-allocations",
        f"{V1}/stays/{{stay_id}}/documents",
        f"{V1}/invoices", f"{V1}/invoices/{{invoice_id}}",
        f"{V1}/occupancy", f"{V1}/occupancy/{{amenity_id}}",
        f"{V1}/amenity-statuses", f"{V1}/amenity-conditions",
    } <= paths


STAY_WRITES = {
    (f"{V1}/stays", "post"),
    (f"{V1}/stays/{{stay_id}}", "patch"),
    (f"{V1}/stays/{{stay_id}}/check-in", "post"),
    (f"{V1}/stays/{{stay_id}}/check-out", "post"),
    (f"{V1}/stays/{{stay_id}}/extend", "post"),
    (f"{V1}/stays/{{stay_id}}/status", "post"),
    (f"{V1}/stays/{{stay_id}}/documents/approval", "post"),
    (f"{V1}/stays/{{stay_id}}/cancel", "post"),
    (f"{V1}/stays/{{stay_id}}/room-allocations", "post"),
    (f"{V1}/stays/{{stay_id}}/occupants", "post"),
    (f"{V1}/stay-occupants/{{occupant_id}}", "delete"),
    (f"{V1}/room-allocations/{{allocation_id}}", "patch"),
    (f"{V1}/room-allocations/{{allocation_id}}", "delete"),
    (f"{V1}/occupancy/{{amenity_id}}", "patch"),
    (f"{V1}/occupancy/{{amenity_id}}/conditions", "put"),
}


def test_stay_write_surface_is_exactly_the_intended_set(client):
    """Phase 3.0 delivers the stay lifecycle.

    INVOICES STAY READ-ONLY. `invoice` stores net_amount / total_tax /
    total_amount, but the schema holds no room rate (`package` has no price),
    no tariff and no tax rate, so the figures cannot be derived. That is
    OPEN DECISION #10, still unresolved -- generating an invoice would mean
    inventing the amounts.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get"
        and any(
            k in path
            for k in ("stay", "occupancy", "invoice", "amenity-status",
                      "amenity-condition", "room-allocation")
        )
    }
    assert found == STAY_WRITES, found ^ STAY_WRITES


def test_invoices_and_amenity_lookups_stay_read_only(client):
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/invoices", f"{V1}/amenity-statuses",
                            f"{V1}/amenity-conditions")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"


def test_earlier_phase_endpoints_still_work(client, anon, admin_headers):
    assert anon.get("/health").status_code == 200
    for path in (f"{V1}/facilities", f"{V1}/rooms", f"{V1}/users", f"{V1}/roles",
                 f"{V1}/service-requests", f"{V1}/devices", f"{V1}/alerts",
                 f"{V1}/notifications"):
        assert client.get(path).status_code == 200
    assert anon.get(f"{V1}/auth/me", headers=admin_headers).status_code == 200
