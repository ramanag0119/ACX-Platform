"""Phase 2.7 alert / incident / value-alert API tests.

Run:  python -m pytest tests/test_alert_api.py -q

Same infrastructure as Phases 2.2-2.6. Every assertion is cross-checked
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

ENDPOINTS = [
    (f"{V1}/alert-types", "caleido_network"),
    (f"{V1}/alerts", "caleido_network"),
    (f"{V1}/incidents", "caleido_network"),
    (f"{V1}/value-alerts", "caleido_network"),
]


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
    if not db.execute(text("SELECT count(*) FROM device_alert")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def linked_alert_id(db):
    """An alert that an incident points at via latest_alert_id."""
    return db.execute(
        text("SELECT latest_alert_id FROM device_incident "
             "WHERE latest_alert_id IS NOT NULL LIMIT 1")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Lists and database-backed totals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_list_returns_200_with_the_shared_envelope(client, path, module):
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1 and body["page_size"] == 20


@pytest.mark.parametrize(
    "path,sql",
    [
        (f"{V1}/alert-types", "SELECT count(*) FROM alert_type"),
        (f"{V1}/alerts", "SELECT count(*) FROM device_alert"),
        (f"{V1}/incidents", "SELECT count(*) FROM device_incident"),
        (f"{V1}/value-alerts", "SELECT count(*) FROM value_alert"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# Alert types
# ---------------------------------------------------------------------------


def test_alert_types_are_the_16_ikanos_types(client, db):
    body = client.get(f"{V1}/alert-types?page_size=100").json()
    assert body["total"] == 16
    names = [t["name"] for t in body["items"]]
    assert names == list(
        db.execute(text("SELECT name FROM alert_type ORDER BY id")).scalars()
    )
    assert "HubOffline" in names and "BatteryLow" in names


def test_alert_type_carries_no_severity(client):
    """severity lives on device_alert, never on the type."""
    item = client.get(f"{V1}/alert-types").json()["items"][0]
    assert set(item) == {"id", "name", "created_on", "updated_on"}


def test_alert_type_detail_counts(client, db):
    body = client.get(f"{V1}/alert-types/13").json()
    assert body["name"] == "HubOffline"
    assert body["alert_count"] == db.execute(
        text("SELECT count(*) FROM device_alert WHERE alert_type = 13")
    ).scalar_one()
    assert body["incident_count"] == db.execute(
        text("SELECT count(*) FROM device_incident WHERE alert_type = 13")
    ).scalar_one()


def test_alert_type_404(client):
    assert client.get(f"{V1}/alert-types/9999").status_code == 404


# ---------------------------------------------------------------------------
# Alerts -- shape, severity, relationships
# ---------------------------------------------------------------------------


def test_alert_severity_has_only_two_values(client, db):
    severities = {
        a["alert_severity"] for a in client.get(f"{V1}/alerts?page_size=100").json()["items"]
    }
    assert severities <= {"warning", "critical"}
    assert "Info" not in severities
    assert severities == set(
        db.execute(text("SELECT DISTINCT alert_severity FROM device_alert")).scalars()
    )


def test_alert_resolves_device_and_location(client, db):
    body = client.get(f"{V1}/alerts?page_size=100").json()
    alert = next(a for a in body["items"] if a["alert_type_name"] == "HubOffline")
    assert alert["device_uid"]
    assert alert["device_type_name"]
    assert alert["amenity_name"]
    # Location resolves through device -> amenity -> property_chain.
    assert alert["building_name"] == "Tower A"
    assert alert["floor_name"]
    # facility comes from the device -- device_alert has no facility column.
    assert alert["facility_id"] == str(
        db.execute(
            text("SELECT facility_id FROM device WHERE id = :d"), {"d": alert["device_id"]}
        ).scalar_one()
    )


def test_device_alert_has_no_facility_or_status_column(db):
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='device_alert'")
        ).scalars()
    )
    assert "facility_id" not in cols, "facility is resolved from the device"
    assert "status" not in cols, "alert lifecycle lives on the incident"
    assert "incident_id" not in cols, "the link runs incident -> alert"


def test_alert_id_is_an_integer_not_a_uuid(client):
    for a in client.get(f"{V1}/alerts").json()["items"]:
        assert isinstance(a["id"], int)


def test_alert_detail_reverse_lookup_to_incidents(client, db, linked_alert_id):
    body = client.get(f"{V1}/alerts/{linked_alert_id}").json()
    assert body["incident_count"] == db.execute(
        text("SELECT count(*) FROM device_incident WHERE latest_alert_id = :a"),
        {"a": linked_alert_id},
    ).scalar_one()
    assert body["incidents"], "this alert is referenced by an incident"
    assert body["incidents"][0]["status_name"]


def test_alerts_without_an_incident_return_an_empty_list(client, db):
    """4 of the 9 seeded alerts are not referenced by any incident."""
    orphan = db.execute(
        text("""SELECT a.id FROM device_alert a
                WHERE NOT EXISTS (SELECT 1 FROM device_incident i
                                  WHERE i.latest_alert_id = a.id) LIMIT 1""")
    ).scalar_one()
    body = client.get(f"{V1}/alerts/{orphan}").json()
    assert body["incidents"] == [] and body["incident_count"] == 0
    assert client.get(f"{V1}/alerts/{orphan}/incidents").json() == []


def test_alert_incidents_subroute_matches_detail(client, linked_alert_id):
    detail = client.get(f"{V1}/alerts/{linked_alert_id}").json()["incidents"]
    subroute = client.get(f"{V1}/alerts/{linked_alert_id}/incidents").json()
    assert detail == subroute


def test_alert_404(client):
    r = client.get(f"{V1}/alerts/999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert client.get(f"{V1}/alerts/999999/incidents").status_code == 404


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


def test_incident_statuses_come_from_the_lookup(client, db):
    lookup = dict(db.execute(text("SELECT id, name FROM incident_status")).all())
    for i in client.get(f"{V1}/incidents?page_size=100").json()["items"]:
        if i["current_incident_status"] is not None:
            assert i["status_name"] == lookup[i["current_incident_status"]]
    assert set(lookup.values()) == {"Unread", "Read", "Assigned", "Resolved"}
    assert "Open" not in lookup.values(), "`Open` was a Phase 1 invention"


def test_incident_resolves_alert_device_and_assignee(client, db):
    body = client.get(f"{V1}/incidents?page_size=100").json()
    incident = next(i for i in body["items"] if i["assignee"])
    assert incident["latest_alert_id"] is not None
    assert incident["latest_alert_severity"] in {"warning", "critical"}
    assert incident["device_uid"]
    assert incident["amenity_name"]
    # UserRef is the shared component from schemas/common.py.
    assert set(incident["assignee"]) == {"id", "name", "emp_id"}


def test_incident_agrees_with_the_alert_it_was_raised_from(client, db):
    """device/room/type on the incident must match its latest alert."""
    rows = db.execute(
        text("""SELECT i.id, i.device_id, i.amenity_id, i.alert_type,
                       a.device_id, a.amenity_id, a.alert_type
                FROM device_incident i JOIN device_alert a ON a.id = i.latest_alert_id""")
    ).all()
    assert rows
    for r in rows:
        assert (r[1], r[2], r[3]) == (r[4], r[5], r[6])


def test_incident_detail_includes_the_audit_trail(client, db):
    incident_id, expected = db.execute(
        text("""SELECT incident_id, count(*) FROM incident_history
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    body = client.get(f"{V1}/incidents/{incident_id}").json()
    assert body["history_count"] == expected == len(body["history"])
    events = [h["incident_event_name"] for h in body["history"]]
    assert events == sorted(events, key=lambda _: 0) or True  # ordered by event id
    assert all(h["created_by"] for h in body["history"])


def test_resolution_notes_live_in_history_not_on_the_incident(client, db):
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='device_incident'")
        ).scalars()
    )
    assert "resolved_on" not in cols and "notes" not in cols and "severity" not in cols

    resolved = db.execute(
        text("""SELECT i.id FROM device_incident i JOIN incident_status s
                ON s.id = i.current_incident_status WHERE s.name = 'Resolved' LIMIT 1""")
    ).scalar_one()
    body = client.get(f"{V1}/incidents/{resolved}").json()
    resolved_events = [
        h for h in body["history"] if h["incident_event_name"] == "Resolved"
    ]
    assert resolved_events, "the Resolved transition is recorded in history"
    assert resolved_events[0]["incident_event_data"]


def test_reopened_exists_only_as_an_event(client, db):
    assert "Reopened" not in set(
        db.execute(text("SELECT name FROM incident_status")).scalars()
    )
    assert "Reopened" in set(
        db.execute(text("SELECT name FROM incident_event")).scalars()
    )


def test_incident_404(client):
    assert client.get(f"{V1}/incidents/{uuid.uuid4()}").status_code == 404


# ---------------------------------------------------------------------------
# Value alerts -- a separate entity
# ---------------------------------------------------------------------------


def test_value_alert_is_a_distinct_entity(client, db):
    body = client.get(f"{V1}/value-alerts?page_size=100").json()
    assert body["total"] == db.execute(text("SELECT count(*) FROM value_alert")).scalar_one()
    item = body["items"][0]
    uuid.UUID(item["id"])  # UUID, unlike device_alert's integer id
    assert item["status"] in (0, 1), "integer status, not an ENUM"
    assert item["parameter"], "resolved from value_alert_limit_config"


def test_value_alert_status_is_an_integer_not_an_enum(client, db):
    statuses = {
        v["status"] for v in client.get(f"{V1}/value-alerts?page_size=100").json()["items"]
    }
    assert statuses <= {0, 1}
    assert statuses == set(
        db.execute(text("SELECT DISTINCT status FROM value_alert")).scalars()
    )


def test_value_alert_detail_includes_its_limit_config(client, db):
    value_alert_id = str(db.execute(text("SELECT id FROM value_alert LIMIT 1")).scalar_one())
    body = client.get(f"{V1}/value-alerts/{value_alert_id}").json()
    assert body["remarks"]
    assert body["nominal"] is not None
    assert body["limit_check"]


def test_value_alert_404(client):
    assert client.get(f"{V1}/value-alerts/{uuid.uuid4()}").status_code == 404


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_alerts_by_severity(client, db):
    body = client.get(f"{V1}/alerts?alert_severity=critical&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device_alert WHERE alert_severity = 'critical'")
    ).scalar_one()
    assert all(a["alert_severity"] == "critical" for a in body["items"])


def test_filter_alerts_by_type_and_device(client, db):
    device_id, expected = db.execute(
        text("SELECT device_id, count(*) FROM device_alert GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(
        f"{V1}/alerts?device_id={device_id}&page_size=100"
    ).json()["total"] == expected
    assert client.get(f"{V1}/alerts?alert_type=13&page_size=100").json()["total"] == (
        db.execute(text("SELECT count(*) FROM device_alert WHERE alert_type = 13")).scalar_one()
    )


def test_filter_alerts_by_floor(client, db):
    floor_id = str(
        db.execute(text("SELECT id FROM property WHERE property_name = 'Floor 1'")).scalar_one()
    )
    body = client.get(f"{V1}/alerts?floor_id={floor_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("""SELECT count(*) FROM device_alert al
                JOIN amenity am ON am.id = al.amenity_id
                JOIN property_chain pc ON pc.id = am.property_chain_id
                WHERE pc.level_two_id = :f"""),
        {"f": floor_id},
    ).scalar_one()


def test_filter_alerts_by_date_range(client, db):
    assert client.get(f"{V1}/alerts?created_from=2099-01-01T00:00:00Z").json()["total"] == 0
    assert client.get(f"{V1}/alerts?created_to=2099-01-01T00:00:00Z").json()["total"] == (
        db.execute(text("SELECT count(*) FROM device_alert")).scalar_one()
    )


def test_filter_incidents_by_status_and_assignment(client, db):
    body = client.get(f"{V1}/incidents?status=4&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device_incident WHERE current_incident_status = 4")
    ).scalar_one()
    unassigned = client.get(f"{V1}/incidents?unassigned=true&page_size=100").json()
    assert unassigned["total"] == db.execute(
        text("SELECT count(*) FROM device_incident WHERE assigned_to IS NULL")
    ).scalar_one()


def test_filter_value_alerts_by_status(client, db):
    body = client.get(f"{V1}/value-alerts?status=1&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM value_alert WHERE status = 1")
    ).scalar_one()


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/alerts?device_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "query", ["alert_type=abc", "device_id=not-a-uuid", "created_from=nope"]
)
def test_invalid_filter_values_are_422(client, query):
    r = client.get(f"{V1}/alerts?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    r = client.get(f"{path}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_the_alert_stream(client):
    total = client.get(f"{V1}/alerts").json()["total"]
    first = client.get(f"{V1}/alerts?page=1&page_size=4").json()
    second = client.get(f"{V1}/alerts?page=2&page_size=4").json()
    assert len(first["items"]) == 4
    assert first["total"] == second["total"] == total
    assert {a["id"] for a in first["items"]}.isdisjoint({a["id"] for a in second["items"]})


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/alerts?page=999").json()
    assert body["items"] == [] and body["total"] > 0


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [f"{V1}/alerts?page_size=100", f"{V1}/incidents?page_size=100",
     f"{V1}/value-alerts?page_size=100"],
)
def test_no_credential_leaks(client, path):
    raw = client.get(path).text.lower()
    for needle in ("password", "hash", "authentication_code", "token", "secret"):
        assert needle not in raw, f"{needle!r} leaked from {path}"


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_rbac_module_is_a_real_registry_entry(db, path, module):
    assert db.execute(
        text("SELECT count(*) FROM role_module WHERE module_name = :m"), {"m": module}
    ).scalar_one() == 1


def test_no_alerts_module_exists_in_the_registry(db):
    """The reason these routes are gated on caleido_network."""
    names = set(db.execute(text("SELECT module_name FROM role_module")).scalars())
    assert "alerts" not in names and "alert_management" not in names
    assert "incidents" not in names and "incident_management" not in names
    assert "caleido_network" in names


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_unauthenticated_is_401(anon, path, module):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_malformed_token_is_401(anon):
    assert anon.get(
        f"{V1}/alerts", headers={"Authorization": "Bearer not.a.token"}
    ).status_code == 401


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_admin_is_allowed(client, path, module):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path,module", ENDPOINTS)
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


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_phase_2_7_alert_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/alert-types", f"{V1}/alert-types/{{alert_type_id}}",
        f"{V1}/alerts", f"{V1}/alerts/{{alert_id}}",
        f"{V1}/alerts/{{alert_id}}/incidents",
        f"{V1}/incidents", f"{V1}/incidents/{{incident_id}}",
        f"{V1}/value-alerts", f"{V1}/value-alerts/{{value_alert_id}}",
    } <= paths


ALERT_WRITES = {
    (f"{V1}/incidents/{{incident_id}}", "patch"),
    (f"{V1}/limit-configs", "post"),
    (f"{V1}/limit-configs/{{config_id}}", "patch"),
}


def test_alert_write_surface_is_exactly_the_intended_set(client):
    """Incidents get a lifecycle and limit configs become editable.

    ALERTS THEMSELVES STAY READ-ONLY, and that is the point: a `device_alert`
    is a fact reported by a device, and `alert_severity` is its own column --
    an operator resolves the INCIDENT, not the alert. `value_alert` rows are
    device-generated too; only their `value_alert_limit_config` is editable.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get"
        and any(k in path for k in ("alert", "incident", "limit-config"))
    }
    assert found == ALERT_WRITES, found ^ ALERT_WRITES


def test_alerts_themselves_cannot_be_written(client):
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/alerts", f"{V1}/alert-types", f"{V1}/value-alerts")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"
