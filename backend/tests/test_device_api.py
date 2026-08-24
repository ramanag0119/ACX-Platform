"""Phase 2.6 device inventory / firmware / health API tests.

Run:  python -m pytest tests/test_device_api.py -q

Same infrastructure as Phases 2.2-2.5. Every assertion is cross-checked
against a direct SQL query. Skipped wholesale when the database is unseeded.
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app

V1 = settings.API_V1_PREFIX

# (route, RBAC module) -- the module is asserted against role_module below.
NETWORK = [
    (f"{V1}/device-types", "caleido_network"),
    (f"{V1}/devices", "caleido_network"),
]
FIRMWARE = [(f"{V1}/firmware", "firmware_management")]
ALL_ENDPOINTS = NETWORK + FIRMWARE


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
    if not db.execute(text("SELECT count(*) FROM device")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def hub_id(db):
    """The 101 Intellihub -- an Active hub that parents three children."""
    return str(
        db.execute(
            text("SELECT id FROM device WHERE device_uid = 'DEV101HUB'")
        ).scalar_one()
    )


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
        (f"{V1}/device-types", "SELECT count(*) FROM device_type"),
        (f"{V1}/devices", "SELECT count(*) FROM device"),
        (f"{V1}/firmware", "SELECT count(*) FROM firmware"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# Device types -- the 4 real families
# ---------------------------------------------------------------------------


def test_device_types_are_the_four_caleido_families(client, db):
    body = client.get(f"{V1}/device-types").json()
    assert body["total"] == 4
    assert [(t["name"], t["device_short_code"]) for t in body["items"]] == [
        (n, c)
        for n, c in db.execute(
            text("SELECT name, device_short_code FROM device_type ORDER BY id")
        ).all()
    ]
    codes = {t["device_short_code"] for t in body["items"]}
    assert codes == {"HUB", "AIR", "MIK", "KLE"}


def test_device_type_detail_counts(client, db):
    body = client.get(f"{V1}/device-types/1").json()
    assert body["name"] == "Intellihub"
    assert body["device_count"] == db.execute(
        text("SELECT count(*) FROM device WHERE device_type = 1")
    ).scalar_one()
    assert body["firmware_count"] == db.execute(
        text("SELECT count(*) FROM firmware WHERE device_type_id = 1")
    ).scalar_one()


def test_device_type_404(client):
    r = client.get(f"{V1}/device-types/9999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Device inventory shape and relationships
# ---------------------------------------------------------------------------


def test_device_resolves_type_location_and_firmware(client, db, hub_id):
    body = client.get(f"{V1}/devices/{hub_id}").json()
    assert body["device_type_name"] == "Intellihub"
    assert body["device_short_code"] == "HUB"
    assert body["amenity_name"] == "101"
    # Location resolves through the Phase 2.2 property_chain projection.
    assert body["building_name"] == "Tower A"
    assert body["floor_name"] == "Floor 1"
    assert body["current_firmware"] == db.execute(
        text("""SELECT f.firmware_version FROM device d
                JOIN firmware f ON f.id = d.current_firmware_version
                WHERE d.id = :i"""),
        {"i": hub_id},
    ).scalar_one()


def test_device_parent_child_hierarchy(client, db, hub_id):
    """Sensors carry their hub id in parent_device_id."""
    body = client.get(f"{V1}/devices/{hub_id}").json()
    assert body["parent_device_id"] is None
    assert body["parent_device"] is None
    assert body["child_count"] == db.execute(
        text("SELECT count(*) FROM device WHERE parent_device_id = :i"), {"i": hub_id}
    ).scalar_one()
    assert {c["device_type_name"] for c in body["child_devices"]} == {
        "Mikos", "AirQ", "Kleio"
    }

    child_id = body["child_devices"][0]["id"]
    child = client.get(f"{V1}/devices/{child_id}").json()
    assert child["parent_device"]["id"] == hub_id
    assert child["child_count"] == 0


def test_device_status_is_four_independent_columns(client, db):
    """There is no single status field and no device_status table."""
    body = client.get(f"{V1}/devices?page_size=100").json()
    health = {d["health_status"] for d in body["items"]}
    config = {d["device_config_status"] for d in body["items"]}
    # `device.health_status` is NULLABLE: a device that has never reported has
    # no health at all, so None is a legitimate third value here -- the same
    # rule test_filter_contract.py applies to the health_status filter.
    assert health <= {"Active", "Inactive", None}
    assert config <= {
        "configured", "bad_configuration", "commissioned",
        "decommissioned", "under_maintenance", "missing",
    }
    assert health == set(
        db.execute(text("SELECT DISTINCT health_status FROM device")).scalars().all()
    )
    for d in body["items"]:
        assert isinstance(d["is_power_off"], (bool, type(None)))
        assert isinstance(d["status"], (int, type(None)))


def test_seeded_devices_span_several_config_statuses(client):
    config = {
        d["device_config_status"]
        for d in client.get(f"{V1}/devices?page_size=100").json()["items"]
    }
    assert len(config) >= 4, "demo should exercise several configuration states"


def test_firmware_up_to_date_is_derived_not_stored(client, db):
    """There is no is_latest column; currency is current vs expected."""
    cols = db.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='firmware'")
    ).scalars().all()
    assert "is_latest" not in cols

    for d in client.get(f"{V1}/devices?page_size=100").json()["items"]:
        if d["current_firmware_version"] and d["expected_firmware_version"]:
            assert d["firmware_up_to_date"] == (
                d["current_firmware_version"] == d["expected_firmware_version"]
            )


def test_device_404(client):
    r = client.get(f"{V1}/devices/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("path", [f"{V1}/devices", f"{V1}/firmware"])
def test_malformed_uuid_is_422(client, path):
    r = client.get(f"{path}/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Security -- credentials and unbounded metadata must never appear
# ---------------------------------------------------------------------------


def test_authentication_code_is_never_returned(client, db):
    """Every seeded device HAS an authentication_code; none may be exposed."""
    assert db.execute(
        text("SELECT count(*) FROM device WHERE authentication_code IS NOT NULL")
    ).scalar_one() == 14
    raw = client.get(f"{V1}/devices?page_size=100").text.lower()
    for needle in ("authentication_code", "auth", "password", "token", "secret"):
        assert needle not in raw, f"{needle!r} leaked from /devices"


def test_device_metadata_bag_is_not_exposed(client, hub_id, db):
    body = client.get(f"{V1}/devices/{hub_id}").json()
    assert "metadata" not in body
    assert db.execute(
        text("SELECT metadata FROM device WHERE id = :i"), {"i": hub_id}
    ).scalar_one() is not None, "the row does carry metadata we chose to withhold"


def test_openapi_device_schemas_declare_no_sensitive_fields(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("DeviceRead", "DeviceDetail", "DeviceRef"):
        fields = set(schema[name]["properties"])
        assert not fields & {"authentication_code", "metadata", "password_hash"}


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_by_device_type(client, db):
    body = client.get(f"{V1}/devices?device_type=4&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device WHERE device_type = 4")
    ).scalar_one()
    assert all(d["device_type_name"] == "Kleio" for d in body["items"])


def test_filter_by_health_status(client, db):
    for value in ("Active", "Inactive"):
        body = client.get(f"{V1}/devices?health_status={value}&page_size=100").json()
        assert body["total"] == db.execute(
            text("SELECT count(*) FROM device WHERE health_status = :v"), {"v": value}
        ).scalar_one()
        assert all(d["health_status"] == value for d in body["items"])


def test_filter_by_config_status(client, db):
    body = client.get(
        f"{V1}/devices?device_config_status=commissioned&page_size=100"
    ).json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device WHERE device_config_status = 'commissioned'")
    ).scalar_one()


def test_filter_by_amenity(client, db):
    amenity_id, expected = db.execute(
        text("SELECT amenity_id, count(*) FROM device GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    body = client.get(f"{V1}/devices?amenity_id={amenity_id}&page_size=100").json()
    assert body["total"] == expected


def test_filter_by_floor_uses_the_property_chain(client, db):
    floor_id = str(
        db.execute(
            text("SELECT id FROM property WHERE property_name = 'Floor 1'")
        ).scalar_one()
    )
    body = client.get(f"{V1}/devices?floor_id={floor_id}&page_size=100").json()
    assert body["total"] == db.execute(
        text("""SELECT count(*) FROM device d
                JOIN amenity a ON a.id = d.amenity_id
                JOIN property_chain pc ON pc.id = a.property_chain_id
                WHERE pc.level_two_id = :f"""),
        {"f": floor_id},
    ).scalar_one()
    assert all(d["floor_name"] == "Floor 1" for d in body["items"])


def test_filter_by_building(client, db):
    building_id = str(
        db.execute(
            text("SELECT id FROM property WHERE property_name = 'Tower A'")
        ).scalar_one()
    )
    body = client.get(f"{V1}/devices?building_id={building_id}&page_size=100").json()
    assert body["total"] > 0
    assert all(d["building_name"] == "Tower A" for d in body["items"])


def test_filter_standalone_vs_child(client, db):
    standalone = client.get(f"{V1}/devices?is_standalone=true&page_size=100").json()
    children = client.get(f"{V1}/devices?is_standalone=false&page_size=100").json()
    assert standalone["total"] == db.execute(
        text("SELECT count(*) FROM device WHERE parent_device_id IS NULL")
    ).scalar_one()
    assert standalone["total"] + children["total"] == db.execute(
        text("SELECT count(*) FROM device")
    ).scalar_one()


def test_filter_by_device_uid(client, db):
    body = client.get(f"{V1}/devices?device_uid=DEV101HUB").json()
    assert body["total"] == 1
    assert body["items"][0]["device_uid"] == "DEV101HUB"


def test_filter_by_model_and_manufacturer(client, db):
    body = client.get(f"{V1}/devices?manufacturer_name=Caleido&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device WHERE manufacturer_name = 'Caleido'")
    ).scalar_one()
    model = db.execute(text("SELECT model FROM device LIMIT 1")).scalar_one()
    by_model = client.get(f"{V1}/devices?model={model}&page_size=100").json()
    assert by_model["total"] == db.execute(
        text("SELECT count(*) FROM device WHERE model = :m"), {"m": model}
    ).scalar_one()


def test_filter_firmware_outdated(client, db):
    body = client.get(f"{V1}/devices?firmware_outdated=true&page_size=100").json()
    assert body["total"] == db.execute(
        text("""SELECT count(*) FROM device
                WHERE current_firmware_version <> expected_firmware_version""")
    ).scalar_one()
    assert all(d["firmware_up_to_date"] is False for d in body["items"])


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/devices?facility_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "query", ["device_type=abc", "is_standalone=maybe", "parent_device_id=nope",
              "firmware_outdated=perhaps"]
)
def test_invalid_filter_values_are_422(client, query):
    r = client.get(f"{V1}/devices?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Device health
# ---------------------------------------------------------------------------


def test_device_health_reports_current_state_and_history(client, db, hub_id):
    body = client.get(f"{V1}/devices/{hub_id}/health").json()
    assert body["device_id"] == hub_id
    assert body["health_status"] == "Active"
    assert body["health_sample_count"] == db.execute(
        text("SELECT count(*) FROM device_health_stat WHERE device_id = :i"),
        {"i": hub_id},
    ).scalar_one()
    assert body["recent_samples"]
    assert all(
        s["device_health_status"] in {"Active", "Inactive"}
        for s in body["recent_samples"]
    )


def test_last_reported_on_is_derived_from_health_stats(client, db, hub_id):
    """There is no last_seen column; this value must equal MAX(created_on)."""
    cols = db.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='device'")
    ).scalars().all()
    assert "last_seen" not in cols

    expected = db.execute(
        text("SELECT max(created_on) FROM device_health_stat WHERE device_id = :i"),
        {"i": hub_id},
    ).scalar_one()
    body = client.get(f"{V1}/devices/{hub_id}/health").json()
    assert body["last_reported_on"].startswith(expected.isoformat()[:19])


def test_health_sample_limit_is_bounded(client, hub_id):
    assert len(
        client.get(f"{V1}/devices/{hub_id}/health?sample_limit=5").json()["recent_samples"]
    ) == 5
    assert client.get(f"{V1}/devices/{hub_id}/health?sample_limit=101").status_code == 422
    assert client.get(f"{V1}/devices/{hub_id}/health?sample_limit=0").status_code == 422


def test_battery_cycles_appear_only_for_devices_that_have_them(client, db):
    lock_id = str(
        db.execute(
            text("""SELECT d.id FROM device d JOIN battery_life_stat b
                    ON b.device_id = d.id LIMIT 1""")
        ).scalar_one()
    )
    lock = client.get(f"{V1}/devices/{lock_id}/health").json()
    assert lock["battery_cycles"], "Kleio locks carry battery_life_stat rows"
    assert lock["battery_cycles"][0]["cycle_number"] > 0

    hub = db.execute(
        text("""SELECT d.id FROM device d WHERE d.device_type = 1
                AND NOT EXISTS (SELECT 1 FROM battery_life_stat b
                                WHERE b.device_id = d.id) LIMIT 1""")
    ).scalar_one()
    assert client.get(f"{V1}/devices/{hub}/health").json()["battery_cycles"] == []


def test_operation_history_comes_from_sensor_operation_stat(client, db, hub_id):
    body = client.get(f"{V1}/devices/{hub_id}/health").json()
    assert len(body["operation_history"]) == db.execute(
        text("SELECT count(*) FROM sensor_operation_stat WHERE device_id = :i"),
        {"i": hub_id},
    ).scalar_one()


def test_inactive_device_health_reflects_it(client, db):
    device_id = str(
        db.execute(
            text("SELECT id FROM device WHERE health_status = 'Inactive' LIMIT 1")
        ).scalar_one()
    )
    body = client.get(f"{V1}/devices/{device_id}/health").json()
    assert body["health_status"] == "Inactive"
    assert body["is_power_off"] is True


def test_device_health_404(client):
    assert client.get(f"{V1}/devices/{uuid.uuid4()}/health").status_code == 404


def test_health_endpoint_reads_no_telemetry(client, hub_id):
    """Health is computed from `device` alone. Readings live behind the
    Phase 2.9 telemetry routes, so no device_stat field may leak in here."""
    body = client.get(f"{V1}/devices/{hub_id}/health").json()
    for forbidden in ("device_param", "param_name", "device_param_value", "voltage",
                      "device_stats", "telemetry"):
        assert forbidden not in str(body).lower()


# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------


def test_firmware_list_resolves_device_type(client, db):
    body = client.get(f"{V1}/firmware?page_size=100").json()
    assert body["total"] == db.execute(text("SELECT count(*) FROM firmware")).scalar_one()
    assert all(f["device_type_name"] for f in body["items"])
    assert {f["status"] for f in body["items"]} <= {"active", "decommissioned"}


def test_firmware_detail_usage_counts(client, db):
    firmware_id, expected = db.execute(
        text("""SELECT current_firmware_version, count(*) FROM device
                WHERE current_firmware_version IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    body = client.get(f"{V1}/firmware/{firmware_id}").json()
    assert body["devices_running"] == expected
    assert body["devices_expecting"] == db.execute(
        text("SELECT count(*) FROM device WHERE expected_firmware_version = :f"),
        {"f": firmware_id},
    ).scalar_one()


def test_firmware_filters(client, db):
    body = client.get(f"{V1}/firmware?status=decommissioned&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM firmware WHERE status = 'decommissioned'")
    ).scalar_one()
    by_type = client.get(f"{V1}/firmware?device_type_id=1&page_size=100").json()
    assert by_type["total"] == db.execute(
        text("SELECT count(*) FROM firmware WHERE device_type_id = 1")
    ).scalar_one()


def test_firmware_404(client):
    assert client.get(f"{V1}/firmware/{uuid.uuid4()}").status_code == 404


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    r = client.get(f"{path}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_the_inventory(client):
    total = client.get(f"{V1}/devices").json()["total"]
    first = client.get(f"{V1}/devices?page=1&page_size=5").json()
    second = client.get(f"{V1}/devices?page=2&page_size=5").json()
    assert len(first["items"]) == 5
    assert first["total"] == second["total"] == total
    assert {d["id"] for d in first["items"]}.isdisjoint({d["id"] for d in second["items"]})


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/devices?page=999").json()
    assert body["items"] == [] and body["total"] > 0


# ---------------------------------------------------------------------------
# RBAC -- driven by role_module_permission, never by role names
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


def test_malformed_token_is_401(anon):
    r = anon.get(f"{V1}/devices", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


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


def test_manager_can_view_the_network_but_not_firmware(anon, manager_headers, db):
    """The seeded Duty Manager holds caleido_network read (write=false) and no
    firmware_management grant at all."""
    row = db.execute(
        text("""SELECT p.read_access, p.write_access FROM role r
                JOIN role_module_permission p ON p.role_id = r.id
                JOIN role_module m ON m.id = p.module_id
                WHERE r.role_type = 'manager' AND m.module_name = 'caleido_network'""")
    ).one()
    assert row.read_access is True and row.write_access is False
    assert db.execute(
        text("""SELECT count(*) FROM role r
                JOIN role_module_permission p ON p.role_id = r.id
                JOIN role_module m ON m.id = p.module_id
                WHERE r.role_type = 'manager' AND m.module_name = 'firmware_management'""")
    ).scalar_one() == 0

    assert anon.get(f"{V1}/devices", headers=manager_headers).status_code == 200
    assert anon.get(f"{V1}/device-types", headers=manager_headers).status_code == 200
    assert anon.get(f"{V1}/firmware", headers=manager_headers).status_code == 403


def test_device_health_is_protected_too(anon, manager_headers, client, db, hub_id):
    assert anon.get(f"{V1}/devices/{hub_id}/health").status_code == 401
    assert anon.get(
        f"{V1}/devices/{hub_id}/health", headers=manager_headers
    ).status_code == 200
    assert client.get(f"{V1}/devices/{hub_id}/health").status_code == 200


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_phase_2_6_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/device-types", f"{V1}/device-types/{{device_type_id}}",
        f"{V1}/devices", f"{V1}/devices/{{device_id}}",
        f"{V1}/devices/{{device_id}}/health",
        f"{V1}/firmware", f"{V1}/firmware/{{firmware_id}}",
    } <= paths


DEVICE_WRITES = {
    (f"{V1}/devices", "post"),
    (f"{V1}/devices/{{device_id}}", "patch"),
    (f"{V1}/devices/{{device_id}}/commission", "post"),
    (f"{V1}/devices/{{device_id}}/decommission", "post"),
    (f"{V1}/devices/{{device_id}}/maintenance", "post"),
    (f"{V1}/firmware", "post"),
    (f"{V1}/firmware/{{firmware_id}}", "patch"),
    (f"{V1}/firmware/{{firmware_id}}/assign", "post"),
}


def test_device_write_surface_is_exactly_the_intended_set(client):
    """Phase 3.0 makes devices and firmware writable.

    Still absent, because no such table exists: any command, MQTT or
    telemetry-ingestion route. Firmware "push" is only
    `device.expected_firmware_version`, which /firmware/{id}/assign sets.
    """
    schema = client.get("/openapi.json").json()
    found = {
        (path, method)
        for path, ops in schema["paths"].items()
        for method in ops
        if method != "get" and ("device" in path or "firmware" in path)
    }
    assert found == DEVICE_WRITES, found ^ DEVICE_WRITES


def test_telemetry_paths_remain_read_only(client):
    """Readings come from the hub, not from an operator."""
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if path.startswith((f"{V1}/device-stats", f"{V1}/device-params",
                            f"{V1}/device-current-stats", f"{V1}/device-types")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"


def test_authentication_code_cannot_be_written(client):
    """`device.authentication_code` is a device credential: it must not appear
    in ANY schema the API accepts or returns."""
    schema = client.get("/openapi.json").json()
    assert "authentication_code" not in json.dumps(schema["components"]["schemas"])


@pytest.mark.parametrize(
    "domain",
    # alerts/incidents/notifications left this list when Phase 2.7 delivered
    # them; device-stats/energy when 2.9 did. `telemetry` and `commands` stay:
    # neither concept exists in the schema and neither was invented.
    ["telemetry", "mqtt", "commands", "dashboard", "bookings"],
)
def test_downstream_device_modules_are_not_exposed(client, domain):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(domain in p for p in paths), f"{domain} belongs to a later phase"


def test_earlier_phase_endpoints_still_work(client, anon, admin_headers):
    assert anon.get("/health").status_code == 200
    assert anon.get(f"{V1}/health/db").status_code == 200
    for path in (f"{V1}/facilities", f"{V1}/rooms", f"{V1}/users", f"{V1}/roles",
                 f"{V1}/service-requests", f"{V1}/service-items"):
        assert client.get(path).status_code == 200
    assert anon.get(f"{V1}/auth/me", headers=admin_headers).status_code == 200
