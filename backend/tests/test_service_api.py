"""Phase 2.5 service catalogue / service request API tests.

Run:  python -m pytest tests/test_service_api.py -q

Same infrastructure as Phases 2.2-2.4. Every assertion is cross-checked
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

# (route, RBAC module) -- the module is asserted against role_module below.
CATALOGUE = [
    (f"{V1}/service-categories", "service_setup"),
    (f"{V1}/service-items", "service_setup"),
]
TRACKING = [
    (f"{V1}/service-types", "service_tracking"),
    (f"{V1}/service-statuses", "service_tracking"),
    (f"{V1}/service-requests", "service_tracking"),
]
ALL_ENDPOINTS = CATALOGUE + TRACKING


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
    if not db.execute(text("SELECT count(*) FROM service_request")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# ---------------------------------------------------------------------------
# List endpoints and database-backed totals
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
        (f"{V1}/service-types", "SELECT count(*) FROM service_type"),
        (f"{V1}/service-statuses", "SELECT count(*) FROM service_status"),
        (f"{V1}/service-categories", "SELECT count(*) FROM service_category"),
        (f"{V1}/service-items", "SELECT count(*) FROM service_category_item"),
        (f"{V1}/service-requests", "SELECT count(*) FROM service_request"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# Catalogue shape
# ---------------------------------------------------------------------------


def test_service_types_are_the_seven_ikanos_types(client, db):
    body = client.get(f"{V1}/service-types?page_size=100").json()
    assert body["total"] == 7
    names = [t["name"] for t in body["items"]]
    assert names == list(
        db.execute(text("SELECT name FROM service_type ORDER BY id")).scalars()
    )
    assert "Room Service" in names and "Sanitation Maintenance Service" in names


def test_service_statuses_are_the_five_real_values(client):
    names = [
        s["name"] for s in client.get(f"{V1}/service-statuses").json()["items"]
    ]
    assert names == ["Pending", "Assigned", "Partially completed", "Completed", "Canceled"]


def test_service_type_detail_counts(client, db):
    body = client.get(f"{V1}/service-types/1").json()
    assert body["name"] == "Room Service"
    assert body["category_count"] == db.execute(
        text("SELECT count(*) FROM service_category WHERE service_type = 1")
    ).scalar_one()
    assert body["request_count"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE service_type = 1")
    ).scalar_one()


def test_service_category_resolves_its_type(client):
    item = client.get(f"{V1}/service-categories?page_size=100").json()["items"][0]
    assert item["service_type_name"]
    assert isinstance(item["service_type"], int)


def test_service_category_detail_item_count(client, db):
    cat_id, expected = db.execute(
        text("""SELECT category_id, count(*) FROM service_category_item
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(f"{V1}/service-categories/{cat_id}").json()["item_count"] == expected


def test_service_item_resolves_category_and_type(client, db):
    body = client.get(f"{V1}/service-items?page_size=100").json()
    item = next(i for i in body["items"] if i["item_name"] == "Wash & Fold (per kg)")
    assert item["category_name"] == "Laundry"
    assert item["service_type_name"] == "Room Service"
    assert item["price_per_unit"] == str(
        db.execute(
            text("SELECT price_per_unit FROM service_category_item "
                 "WHERE item_name = 'Wash & Fold (per kg)'")
        ).scalar_one()
    )


# ---------------------------------------------------------------------------
# Pricing boundary -- OPEN DECISION #10 must stay unresolved
# ---------------------------------------------------------------------------


def test_price_per_unit_is_a_real_column_and_may_be_null(client, db):
    body = client.get(f"{V1}/service-items?page_size=100").json()
    priced = [i for i in body["items"] if i["price_per_unit"] is not None]
    assert len(priced) == db.execute(
        text("SELECT count(*) FROM service_category_item WHERE price_per_unit IS NOT NULL")
    ).scalar_one()
    assert priced, "some seeded items are priced"
    assert len(priced) < body["total"], "and some are deliberately unpriced"


def test_no_room_tariff_or_payment_field_is_exposed(client):
    """OPEN DECISION #10: package.price and invoice.status do not exist and
    must not appear anywhere in this domain."""
    raw = client.get(f"{V1}/service-requests?page_size=100").text.lower()
    for forbidden in ("tariff", "room_price", "package_price", "payment", "invoice"):
        assert forbidden not in raw
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("ServiceItemRead", "ServiceRequestRead", "ServiceRequestDetail"):
        fields = set(schema[name]["properties"])
        assert not fields & {"price", "tariff", "sla", "priority", "duration",
                             "availability", "payment_status", "invoice_status"}


def test_service_request_amounts_are_null_as_seeded(client, db):
    """net/total amounts are real columns but the schema encodes no rule for
    computing them; the seed leaves them NULL and the API must not fabricate."""
    assert db.execute(
        text("SELECT count(*) FROM service_request WHERE total_amount IS NOT NULL")
    ).scalar_one() == 0
    for r in client.get(f"{V1}/service-requests?page_size=100").json()["items"]:
        assert r["net_amount"] is None
        assert r["total_tax"] is None
        assert r["total_amount"] is None


def test_no_priority_field_exists(client, db):
    cols = db.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='service_request'")
    ).scalars().all()
    assert "priority" not in cols
    body = client.get(f"{V1}/service-requests").json()
    assert all("priority" not in r for r in body["items"])


# ---------------------------------------------------------------------------
# Service request shape and relationships
# ---------------------------------------------------------------------------


def test_service_request_resolves_every_relationship(client, db):
    body = client.get(f"{V1}/service-requests?page_size=100").json()
    sr = next(r for r in body["items"] if r["ref_number"] == "SR-2026-0002")
    assert sr["service_type_name"] == "Food Order"
    assert sr["category_name"] == "Main Course"
    assert sr["status_name"] == "Assigned"
    assert sr["amenity_name"] == "205"
    assert sr["stay_ref_number"] == "STY-2026-0002"
    assert sr["department_name"] == "Food & Beverage"
    assert sr["requester"]["name"] == "Meera Krishnan"
    assert sr["assignee"]["name"] == "Fatima Sheikh"
    assert sr["request_source"] == "ikanos"


def test_status_names_match_the_lookup(client, db):
    lookup = dict(db.execute(text("SELECT id, name FROM service_status")).all())
    for r in client.get(f"{V1}/service-requests?page_size=100").json()["items"]:
        if r["status"] is not None:
            assert r["status_name"] == lookup[r["status"]]


def test_seeded_requests_span_the_status_vocabulary(client):
    statuses = {
        r["status_name"]
        for r in client.get(f"{V1}/service-requests?page_size=100").json()["items"]
    }
    assert {"Pending", "Assigned", "Completed", "Canceled"} <= statuses


def test_request_detail_includes_line_items(client, db):
    request_id, expected = db.execute(
        text("""SELECT service_request_id, count(*) FROM service_request_item
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    body = client.get(f"{V1}/service-requests/{request_id}").json()
    assert body["item_count"] == expected == len(body["items"])
    for item in body["items"]:
        assert item["item_name"]
        assert item["quantity"] is None or item["quantity"] > 0


def test_partially_completed_request_has_items_in_differing_states(client, db):
    """This is what 'Partially completed' actually means in the schema."""
    request_id = db.execute(
        text("""SELECT sr.id FROM service_request sr JOIN service_status s
                ON s.id = sr.status WHERE s.name = 'Partially completed' LIMIT 1""")
    ).scalar_one()
    body = client.get(f"{V1}/service-requests/{request_id}").json()
    assert len({i["status_name"] for i in body["items"]}) > 1


def test_request_detail_404(client):
    r = client.get(f"{V1}/service-requests/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "path", [f"{V1}/service-categories", f"{V1}/service-items", f"{V1}/service-requests"]
)
def test_uuid_detail_404(client, path):
    assert client.get(f"{path}/{uuid.uuid4()}").status_code == 404


@pytest.mark.parametrize(
    "path", [f"{V1}/service-types", f"{V1}/service-statuses"]
)
def test_integer_detail_404(client, path):
    assert client.get(f"{path}/9999").status_code == 404


@pytest.mark.parametrize(
    "path", [f"{V1}/service-categories", f"{V1}/service-items", f"{V1}/service-requests"]
)
def test_malformed_uuid_is_422(client, path):
    r = client.get(f"{path}/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_requests_by_service_type(client, db):
    body = client.get(f"{V1}/service-requests?service_type=4&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE service_type = 4")
    ).scalar_one()
    assert all(r["service_type"] == 4 for r in body["items"])


def test_filter_requests_by_status(client, db):
    body = client.get(f"{V1}/service-requests?status=1&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE status = 1")
    ).scalar_one()
    assert all(r["status_name"] == "Pending" for r in body["items"])


def test_filter_requests_by_assignee(client, db):
    assignee, expected = db.execute(
        text("""SELECT assigned_to, count(*) FROM service_request
                WHERE assigned_to IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    body = client.get(f"{V1}/service-requests?assigned_to={assignee}&page_size=100").json()
    assert body["total"] == expected


def test_filter_requests_by_stay(client, db):
    stay_id = db.execute(
        text("SELECT stay_id FROM service_request WHERE stay_id IS NOT NULL LIMIT 1")
    ).scalar_one()
    body = client.get(f"{V1}/service-requests?stay_id={stay_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE stay_id = :s"), {"s": stay_id}
    ).scalar_one()


def test_filter_requests_by_request_source(client, db):
    body = client.get(f"{V1}/service-requests?request_source=ikanos&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE request_source = 'ikanos'")
    ).scalar_one()


def test_filter_requests_unassigned(client, db):
    body = client.get(f"{V1}/service-requests?unassigned=true").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request WHERE assigned_to IS NULL")
    ).scalar_one()


def test_filter_requests_by_date_range(client, db):
    body = client.get(f"{V1}/service-requests?created_from=2099-01-01T00:00:00Z").json()
    assert body["total"] == 0
    body = client.get(f"{V1}/service-requests?created_to=2099-01-01T00:00:00Z").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_request")
    ).scalar_one()


def test_filter_items_by_price_presence(client, db):
    priced = client.get(f"{V1}/service-items?has_price=true&page_size=100").json()
    unpriced = client.get(f"{V1}/service-items?has_price=false&page_size=100").json()
    total = db.execute(text("SELECT count(*) FROM service_category_item")).scalar_one()
    assert priced["total"] + unpriced["total"] == total
    assert all(i["price_per_unit"] is not None for i in priced["items"])
    assert all(i["price_per_unit"] is None for i in unpriced["items"])


def test_filter_items_by_category(client, db):
    cat_id, expected = db.execute(
        text("""SELECT category_id, count(*) FROM service_category_item
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    body = client.get(f"{V1}/service-items?category_id={cat_id}&page_size=100").json()
    assert body["total"] == expected


def test_filter_categories_by_service_type(client, db):
    body = client.get(f"{V1}/service-categories?service_type=4&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM service_category WHERE service_type = 4")
    ).scalar_one()


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/service-requests?facility_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "query", ["service_type=abc", "status=abc", "assigned_to=not-a-uuid",
              "created_from=not-a-date", "unassigned=maybe"]
)
def test_invalid_filter_values_are_422(client, query):
    r = client.get(f"{V1}/service-requests?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    r = client.get(f"{path}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_the_catalogue(client):
    total = client.get(f"{V1}/service-items").json()["total"]
    first = client.get(f"{V1}/service-items?page=1&page_size=10").json()
    second = client.get(f"{V1}/service-items?page=2&page_size=10").json()
    assert len(first["items"]) == 10
    assert first["total"] == second["total"] == total
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/service-items?page=999").json()
    assert body["items"] == [] and body["total"] > 0


# ---------------------------------------------------------------------------
# RBAC -- driven by role_module_permission, not by role names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_rbac_modules_are_real_registry_entries(db, path, module):
    assert db.execute(
        text("SELECT count(*) FROM role_module WHERE module_name = :m"), {"m": module}
    ).scalar_one() == 1


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_unauthenticated_is_401(anon, path, module):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_admin_is_allowed_everywhere(client, path, module):
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
    assert r.status_code == (200 if granted else 403), (
        f"{path} ({module}): database says granted={granted}, API said {r.status_code}"
    )
    if not granted:
        assert r.json()["error"]["code"] == "forbidden"
        assert module in r.json()["error"]["message"]


def test_manager_can_track_but_not_configure(anon, manager_headers, db):
    """The KT handbook split, enforced by data: Manager runs operations,
    Admin owns catalogue configuration."""
    assert db.execute(
        text("""SELECT count(*) FROM role r
                JOIN role_module_permission p ON p.role_id = r.id
                JOIN role_module m ON m.id = p.module_id
                WHERE r.role_type = 'manager' AND m.module_name = 'service_setup'""")
    ).scalar_one() == 0

    assert anon.get(f"{V1}/service-requests", headers=manager_headers).status_code == 200
    assert anon.get(f"{V1}/service-types", headers=manager_headers).status_code == 200
    assert anon.get(f"{V1}/service-items", headers=manager_headers).status_code == 403
    assert anon.get(f"{V1}/service-categories", headers=manager_headers).status_code == 403


# ---------------------------------------------------------------------------
# Credential safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [f"{V1}/service-requests?page_size=100", f"{V1}/service-items?page_size=100"],
)
def test_no_credential_leaks_through_person_references(client, path):
    raw = client.get(path).text.lower()
    for needle in ("password", "hash", "token", "secret", "seed-no-login", "metadata"):
        assert needle not in raw, f"{needle!r} leaked from {path}"


def test_person_references_expose_only_id_name_emp_id(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert set(schema["UserRef"]["properties"]) == {"id", "name", "emp_id"}


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_phase_2_5_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/service-types", f"{V1}/service-types/{{service_type_id}}",
        f"{V1}/service-statuses", f"{V1}/service-statuses/{{status_id}}",
        f"{V1}/service-categories", f"{V1}/service-categories/{{category_id}}",
        f"{V1}/service-items", f"{V1}/service-items/{{item_id}}",
        f"{V1}/service-requests", f"{V1}/service-requests/{{request_id}}",
    } <= paths


SERVICE_WRITES = {
    (f"{V1}/service-requests", "post"),
    (f"{V1}/service-requests/{{request_id}}", "patch"),
    (f"{V1}/service-requests/{{request_id}}/items", "put"),
    (f"{V1}/service-requests/{{request_id}}/cancel", "post"),
    (f"{V1}/service-categories", "post"),
    (f"{V1}/service-categories/{{category_id}}", "patch"),
    (f"{V1}/service-items", "post"),
    (f"{V1}/service-items/{{item_id}}", "patch"),
}


def test_service_write_surface_is_exactly_the_intended_set(client):
    """Phase 3.0 makes service requests and the catalogue writable.

    `service-types` and `service-statuses` stay read-only: both are seeded
    IKANOS lookups, not operator data.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get" and "service" in path
    }
    assert found == SERVICE_WRITES, found ^ SERVICE_WRITES


def test_service_lookups_stay_read_only(client):
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/service-types", f"{V1}/service-statuses")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"


def test_earlier_phase_endpoints_still_work(client, anon, admin_headers):
    """Phase 2.5 must not disturb 2.1-2.4."""
    assert anon.get("/health").status_code == 200
    assert anon.get(f"{V1}/health/db").status_code == 200
    for path in (f"{V1}/facilities", f"{V1}/rooms", f"{V1}/users", f"{V1}/roles"):
        assert client.get(path).status_code == 200
    assert anon.get(f"{V1}/auth/me", headers=admin_headers).status_code == 200
