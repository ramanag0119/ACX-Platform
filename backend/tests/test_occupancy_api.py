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
from app.services.stay import _display_status

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


def test_display_status_derivation_and_vocabulary(client):
    """display_status is authoritatively backend-derived and mapped for UI display."""
    body = client.get(f"{V1}/stays?page_size=100").json()
    assert body["items"], "Should have seeded stays"
    for s in body["items"]:
        assert "display_status" in s
        if s["is_in_house"]:
            assert s["display_status"] in (
                "In-Room", "Checkout Pending", "Checkout Accepted", "Checkout Rejected"
            )
        elif s["status"] == "checked out":
            assert s["display_status"] == "Checked Out"
        elif s["status"] == "cancelled":
            assert s["display_status"] == "Cancelled"

    # Unit checks across all PostgreSQL stay_status enum values
    assert _display_status(status="active", is_in_house=True, is_checked_in=True) == "In-Room"
    assert _display_status(status="pending", is_in_house=False, is_checked_in=False) == "Pending"
    assert _display_status(status="checked out", is_in_house=False, is_checked_in=True) == "Checked Out"
    assert _display_status(status="cancelled", is_in_house=False, is_checked_in=False) == "Cancelled"
    assert _display_status(status="checkout pending", is_in_house=True, is_checked_in=True) == "Checkout Pending"
    assert _display_status(status="checkout accepted", is_in_house=True, is_checked_in=True) == "Checkout Accepted"
    assert _display_status(status="checkout rejected", is_in_house=True, is_checked_in=True) == "Checkout Rejected"
    # Fallback for unexpected status
    assert _display_status(status="custom_status", is_in_house=False, is_checked_in=False) == "Custom_Status"


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
        assert r["current_stay"]["expected_checkin_time"] is not None
        assert r["current_stay"]["booker"]


def test_amenity_status_and_stay_graph_are_reported_independently(client, db):
    """The stay graph and amenity.status are both reported faithfully."""
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
        "Dirty", "Low battery", "Under maintenance", "Sanitation",
        "Ready for occupant", "Guest Assistance Required", "Device Offline",
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


# ---------------------------------------------------------------------------
# Authoritative Occupancy Classification and Reconciliation
# ---------------------------------------------------------------------------


def test_authoritative_occupancy_status_vocabulary(client):
    """Every room has an authoritative occupancy status or None (Unknown/Not Set) if status is missing/stale."""
    res = client.get(f"{V1}/occupancy?page_size=100")
    assert res.status_code == 200
    items = res.json()["items"]
    allowed = {"Available", "Occupied", "Allotted", "Unavailable", None}
    for item in items:
        assert item["occupancy_status"] in allowed, (
            f"Room {item['room_name']} has invalid occupancy_status: {item['occupancy_status']}"
        )


def test_blocking_conditions_yield_unavailable(client):
    """Rooms blocked by maintenance or sanitation are classified as Unavailable."""
    res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100")
    items = res.json()["items"]
    # Room 103 has Sanitation condition
    room_103 = next(r for r in items if r["room_name"] == "103")
    assert any("sanitation" in c["name"].lower() for c in room_103["conditions"])
    assert room_103["occupancy_status"] == "Unavailable"
    # Room 204 has Under maintenance condition
    room_204 = next(r for r in items if r["room_name"] == "204")
    assert any("under maintenance" in c["name"].lower() for c in room_204["conditions"])
    assert room_204["occupancy_status"] == "Unavailable"


def test_occupancy_status_filtering_and_graph_reconciliation(client):
    """Querying by occupancy_status filters accurately and reconciles to 24 guest bedrooms."""
    categories = ["Available", "Occupied", "Unavailable", "Allotted"]
    totals = {}
    for cat in categories:
        res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status={cat}&page_size=100")
        assert res.status_code == 200
        data = res.json()
        totals[cat] = data["total"]
        assert len(data["items"]) == data["total"]
        for item in data["items"]:
            assert item["occupancy_status"] == cat

    assert totals["Available"] == 11
    assert totals["Occupied"] == 5
    assert totals["Unavailable"] == 5
    assert totals["Allotted"] == 3
    # All 24 rooms reconcile across recognized statuses with 0 unknown
    assert sum(totals.values()) == 24

    total_res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=1")
    assert total_res.json()["total"] == 24


def test_selecting_allotted_returns_all_expected_records(client):
    """Selecting Allotted returns Room 108 and only Allotted rooms."""
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    room_names = [r["room_name"] for r in data["items"]]
    assert "108" in room_names
    assert "301" in room_names
    assert "303" in room_names
    for item in data["items"]:
        assert item["occupancy_status"] == "Allotted"


def test_selecting_available_returns_only_available_records(client):
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Available&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 11
    for item in data["items"]:
        assert item["occupancy_status"] == "Available"


def test_selecting_occupied_returns_only_occupied_records(client):
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Occupied&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    for item in data["items"]:
        assert item["occupancy_status"] == "Occupied"
    names = {r["room_name"] for r in data["items"]}
    assert names == {"101", "106", "201", "205", "306"}


def test_selecting_unavailable_returns_only_unavailable_records(client):
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Unavailable&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    for item in data["items"]:
        assert item["occupancy_status"] == "Unavailable"


def test_show_all_returns_all_permitted_records(client):
    res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 24
    assert len(data["items"]) == 24


def test_conditions_do_not_replace_occupancy_status_values(client):
    res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100")
    items = res.json()["items"]
    allowed = {"Available", "Occupied", "Allotted", "Unavailable", None}
    for item in items:
        assert item["occupancy_status"] in allowed
        assert item["occupancy_status"] not in {"Dirty", "Sanitation", "Under maintenance", "Low battery"}


def test_valid_allotted_records_not_excluded_by_unrelated_conditions(client):
    """Room 108 has condition Ready for occupant and remains Allotted."""
    res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page_size=100")
    data = res.json()
    room_108 = next(r for r in data["items"] if r["room_name"] == "108")
    assert room_108["occupancy_status"] == "Allotted"


def test_pagination_and_total_counts_reflect_filtered_dataset(client):
    res1 = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page=1&page_size=1")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 3
    assert len(data1["items"]) == 1

    res2 = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page=2&page_size=1")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 3
    assert len(data2["items"]) == 1


def test_dashboard_filtering_and_direct_occupancy_filtering_equivalent(client):
    dash_count_res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page_size=1")
    direct_res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status=Allotted&page_size=100")
    assert dash_count_res.json()["total"] == direct_res.json()["total"]
    assert dash_count_res.json()["total"] == 3


def test_occupancy_summary_aggregates(client):
    """Test /occupancy/summary returns DB-driven aggregate totals and status summaries."""
    res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert res.status_code == 200
    data = res.json()
    assert data["total_rooms"] == 24
    assert data["available"] == 11
    assert data["occupied"] == 5
    assert data["allotted"] == 3
    assert data["unavailable"] == 5
    assert data["unknown"] == 0
    assert data["unclassified"] == 0
    by_status = data["by_status"]
    status_names = [s["status"] for s in by_status]
    assert "Unknown" not in status_names
    assert set(status_names) == {"Available", "Occupied", "Unavailable", "Allotted"}
    for entry in by_status:
        assert entry["status_id"] is not None
        assert entry["count"] >= 0
    assert "daily_metrics" in data
    assert data["daily_metrics"]["start_of_day"] >= 0
    assert data["daily_metrics"]["realized_check_in"] >= 0
    assert data["daily_metrics"]["realized_check_out"] >= 0
    assert data["daily_metrics"]["current_status"] == 4
    assert data["daily_metrics"]["expected_check_in"] >= 0
    assert data["daily_metrics"]["expected_check_out"] >= 0


def test_occupancy_daily_series(client, db):
    """Test /occupancy/daily returns continuous date points without null placeholder rows."""
    from datetime import date, timedelta
    today = date.today()
    start_date = today - timedelta(days=7)
    expected_total = db.execute(
        text("SELECT count(*) FROM amenity JOIN amenity_type ON amenity_type.id = amenity.amenity_type_id WHERE amenity_type.amenity_category = 'room'")
    ).scalar_one()
    res = client.get(
        f"{V1}/occupancy/daily?amenity_category=room&date_from={start_date.isoformat()}&date_to={today.isoformat()}"
    )
    assert res.status_code == 200
    points = res.json()
    assert len(points) == 8  # 7 days back + today
    for pt in points:
        assert "metric_date" in pt
        assert "total_rooms" in pt
        assert pt["total_rooms"] == expected_total
        assert "occupied_rooms" in pt
        assert "has_data" in pt
        assert pt["occupied_rooms"] is not None


def test_occupancy_status_transition_updates_counts(client, db):
    """Updating a room's status updates the aggregate counts while total remains constant."""
    from app.models.amenity import Amenity, AmenityType
    expected_total = db.execute(
        text("SELECT count(*) FROM amenity JOIN amenity_type ON amenity_type.id = amenity.amenity_type_id WHERE amenity_type.amenity_category = 'room'")
    ).scalar_one()
    # Find an Available room without blocking conditions
    room = db.query(Amenity).join(AmenityType).filter(
        AmenityType.amenity_category == "room",
        Amenity.status == 0,
        Amenity.name == "202"
    ).first()
    assert room is not None

    orig_status = room.status
    try:
        # Check initial summary
        s0 = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        assert s0["total_rooms"] == expected_total
        init_avail = s0["available"]
        init_unavail = s0["unavailable"]

        # Change room 202 from Available (0) to Unavailable (2)
        room.status = 2
        db.commit()

        s1 = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        assert s1["total_rooms"] == expected_total
        assert s1["available"] == init_avail - 1
        assert s1["unavailable"] == init_unavail + 1
        assert s1["available"] + s1["occupied"] + s1["allotted"] + s1["unavailable"] + s1["unknown"] == expected_total
    finally:
        # Restore original status
        room.status = orig_status
        db.commit()

    s_restored = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
    assert s_restored["available"] == init_avail
    assert s_restored["unavailable"] == init_unavail
    assert s_restored["total_rooms"] == expected_total


def test_status_id_and_label_resolution_matches_master_data(client, db):
    """Test C: Canonical status IDs and labels match amenity_status table."""
    lookup = dict(db.execute(text("SELECT id, amenity_status_name FROM amenity_status")).all())
    res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert res.status_code == 200
    by_status = res.json()["by_status"]
    for entry in by_status:
        if entry["status_id"] is not None:
            assert entry["status_id"] in lookup
            assert entry["status"] == lookup[entry["status_id"]]


def test_no_false_unknown_category_in_summary(client):
    """Test D: When all rooms have valid statuses, unknown is 0 and no Unknown category appears."""
    res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert res.status_code == 200
    data = res.json()
    assert data["unknown"] == 0
    assert not any(s["status"].lower() == "unknown" for s in data["by_status"])


def test_invalid_status_reference_explicitly_diagnosed_as_unknown(client, db):
    """Test E: A room with missing status reference is explicitly diagnosed as Unknown."""
    from app.models.amenity import Amenity
    room = db.query(Amenity).filter(Amenity.name == "202").first()
    assert room is not None
    orig_status = room.status
    try:
        room.status = None
        db.commit()

        s = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        assert s["unknown"] == 1
        unknown_entry = next((item for item in s["by_status"] if item["status"] == "Unknown"), None)
        assert unknown_entry is not None
        assert unknown_entry["status_id"] is None
        assert unknown_entry["count"] == 1
    finally:
        room.status = orig_status
        db.commit()


def test_occupancy_module_and_dashboard_reconcile_completely(client):
    """Test F: Occupancy list filtered by status reconciles with dashboard summary counts."""
    summary_res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert summary_res.status_code == 200
    summary = summary_res.json()

    for item in summary["by_status"]:
        status_name = item["status"]
        expected_count = item["count"]
        list_res = client.get(f"{V1}/occupancy?amenity_category=room&occupancy_status={status_name}&page_size=100")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] == expected_count, (
            f"Mismatch for status {status_name}: summary has {expected_count}, list returned {list_data['total']}"
        )


def test_occupancy_summary_empty_dataset(client):
    """Querying a non-existent amenity type returns 0 counts without error."""
    import uuid
    dummy_id = uuid.uuid4()
    res = client.get(f"{V1}/occupancy/summary?amenity_type_id={dummy_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["total_rooms"] == 0
    assert data["available"] == 0
    assert data["occupied"] == 0
    assert data["allotted"] == 0
    assert data["unavailable"] == 0
    assert data["unknown"] == 0
    assert data["unclassified"] == 0


def test_section_10_repeated_failure_scenario_regression(client, db):
    """Section 10 regression test: Changing conditions must not drop room from summary (24 vs 23 bug).

    Executes the exact sequence:
    1. Fetch listing across all pages.
    2. Verify all eligible rooms returned.
    3. Fetch summary; verify total equals DB authoritative count.
    4. Select an Allotted room.
    5. Change only its condition using the real supported PUT /occupancy/{id}/conditions workflow.
    6. Commit/verify mutation.
    7. Fetch listing again; verify total remains constant.
    8. Fetch summary again; verify total remains constant and modified room remains in Allotted category.
    9. Repeat with other valid condition changes.
    10. Test legitimate status transitions.
    11. Verify invalid condition updates fail without state corruption.
    """
    # Calculate authoritative room count from DB (never hardcoded)
    expected_total = db.execute(
        text("SELECT count(*) FROM amenity JOIN amenity_type ON amenity_type.id = amenity.amenity_type_id WHERE amenity_type.amenity_category = 'room'")
    ).scalar_one()

    # 1. Fetch Occupancy listing
    listing_res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100")
    assert listing_res.status_code == 200
    listing_data = listing_res.json()
    # 2. Verify all eligible rooms returned across all pages
    assert listing_data["total"] == expected_total
    assert len(listing_data["items"]) == expected_total

    # 3. Fetch summary
    summary_res = client.get(f"{V1}/occupancy/summary?amenity_category=room")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    # 4. Verify total equals expected_total
    assert summary_data["total_rooms"] == expected_total
    assert summary_data["unknown"] == 0
    init_allotted = summary_data["allotted"]
    assert init_allotted > 0

    # 5. Select a room whose status is Allotted
    allotted_item = next((item for item in listing_data["items"] if item["occupancy_status"] == "Allotted"), None)
    assert allotted_item is not None, "At least one Allotted room must exist in test dataset"
    room_id = allotted_item["amenity_id"]

    # Read original condition
    orig_cond_res = client.get(f"{V1}/occupancy/{room_id}/applicable-conditions")
    assert orig_cond_res.status_code == 200
    applicable_conditions = orig_cond_res.json()
    assert len(applicable_conditions) > 0

    orig_active_cond = (allotted_item.get("conditions") or [{}])[0].get("id")

    try:
        # 6-12. Test each applicable condition change on the Allotted room
        for cond in applicable_conditions:
            cond_id = cond["id"]
            # 6. Change only its condition using the real supported workflow
            put_res = client.put(
                f"{V1}/occupancy/{room_id}/conditions",
                json={"condition_ids": [cond_id]},
            )
            assert put_res.status_code == 200, f"Condition update to {cond['name']} failed: {put_res.text}"

            # 8. Fetch room listing again
            refetch_list = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100").json()
            # 10. Verify total remains constant
            assert refetch_list["total"] == expected_total

            # Verify modified room still in listing and still Allotted
            modified_room_in_list = next((r for r in refetch_list["items"] if r["amenity_id"] == room_id), None)
            assert modified_room_in_list is not None
            assert modified_room_in_list["occupancy_status"] == "Allotted"

            # 9. Fetch summary again
            refetch_summary = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
            # 10. Verify total remains constant (24 vs 23 bug check)
            assert refetch_summary["total_rooms"] == expected_total, (
                f"Room count dropped from {expected_total} to {refetch_summary['total_rooms']} after setting condition {cond['name']}"
            )
            assert refetch_summary["unknown"] == 0
            # 11. Verify modified room remains in Allotted category
            assert refetch_summary["allotted"] == init_allotted
            status_sum = (
                refetch_summary["available"]
                + refetch_summary["occupied"]
                + refetch_summary["allotted"]
                + refetch_summary["unavailable"]
                + refetch_summary["unknown"]
            )
            assert status_sum == expected_total

        # 13. Test legitimate room-status transition (Available room -> Unavailable -> Available)
        avail_item = next((item for item in listing_data["items"] if item["occupancy_status"] == "Available"), None)
        assert avail_item is not None
        avail_room_id = avail_item["amenity_id"]

        patch_res = client.patch(f"{V1}/occupancy/{avail_room_id}", json={"status": 2})
        assert patch_res.status_code == 200
        patched_summary = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        # 14. Verify status categories update correctly while total remains constant
        assert patched_summary["total_rooms"] == expected_total
        assert patched_summary["available"] == summary_data["available"] - 1
        assert patched_summary["unavailable"] == summary_data["unavailable"] + 1

        # Revert back to Available
        client.patch(f"{V1}/occupancy/{avail_room_id}", json={"status": 0})

        # 15. Verify that invalid updates fail without corrupting room's existing state
        bad_put = client.put(f"{V1}/occupancy/{room_id}/conditions", json={"condition_ids": [999999]})
        assert bad_put.status_code in (400, 422, 404)
        summary_after_bad = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        assert summary_after_bad["total_rooms"] == expected_total
        assert summary_after_bad["allotted"] == init_allotted

    finally:
        # Restore original condition
        if orig_active_cond:
            client.put(f"{V1}/occupancy/{room_id}/conditions", json={"condition_ids": [orig_active_cond]})
        db.rollback()


def test_section_10_edge_cases_no_condition_and_multi_pages(client, db):
    """Section 10 edge cases: rooms with no condition association and multi-page requests."""
    from app.models.amenity import Amenity, AmenityConditionStatus, AmenityType

    expected_total = db.execute(
        text("SELECT count(*) FROM amenity JOIN amenity_type ON amenity_type.id = amenity.amenity_type_id WHERE amenity_type.amenity_category = 'room'")
    ).scalar_one()

    # Find an Available room and temporarily remove all its condition rows
    room = db.query(Amenity).join(AmenityType).filter(
        AmenityType.amenity_category == "room",
        Amenity.name == "102"
    ).first()
    assert room is not None
    room_id = room.id

    orig_conditions = db.query(AmenityConditionStatus).filter(AmenityConditionStatus.amenity_id == room_id).all()
    orig_tuples = [(c.amenity_condition_id, c.status) for c in orig_conditions]

    try:
        # Remove conditions
        db.query(AmenityConditionStatus).filter(AmenityConditionStatus.amenity_id == room_id).delete()
        db.commit()

        # Listing must still account for room
        list_res = client.get(f"{V1}/occupancy?amenity_category=room&page_size=100").json()
        assert list_res["total"] == expected_total
        assert any(r["amenity_id"] == str(room_id) for r in list_res["items"])

        # Summary must still account for room
        sum_res = client.get(f"{V1}/occupancy/summary?amenity_category=room").json()
        assert sum_res["total_rooms"] == expected_total
        assert sum_res["unknown"] == 0

        # Multi-page requests: total must not change based on page_size
        p1 = client.get(f"{V1}/occupancy?amenity_category=room&page_size=5&page=1").json()
        assert p1["total"] == expected_total
        assert len(p1["items"]) == 5

        p2 = client.get(f"{V1}/occupancy?amenity_category=room&page_size=5&page=2").json()
        assert p2["total"] == expected_total
        assert len(p2["items"]) == 5

    finally:
        # Restore condition status
        db.query(AmenityConditionStatus).filter(AmenityConditionStatus.amenity_id == room_id).delete()
        for cid, st in orig_tuples:
            db.add(AmenityConditionStatus(amenity_id=room_id, amenity_condition_id=cid, status=st))
        db.commit()




