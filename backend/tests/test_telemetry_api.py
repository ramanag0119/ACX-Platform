"""Phase 2.9 telemetry / energy API tests.

Run:  python -m pytest tests/test_telemetry_api.py -q

Same infrastructure as Phases 2.2-2.8. Every assertion is cross-checked
against a direct SQL query. Skipped wholesale when the database is unseeded.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.services.energy import ENERGY_EPOCH, hour_to_timestamp

V1 = settings.API_V1_PREFIX

TELEMETRY = [
    (f"{V1}/device-params", "caleido_network"),
    (f"{V1}/device-stats", "caleido_network"),
    (f"{V1}/device-current-stats", "caleido_network"),
    (f"{V1}/other-device-readings", "caleido_network"),
]
ENERGY = [
    (f"{V1}/energy-stats", "reports"),
    (f"{V1}/daily-data-points", "reports"),
]
ALL_ENDPOINTS = TELEMETRY + ENERGY


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
    if not db.execute(text("SELECT count(*) FROM device_stat")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# ---------------------------------------------------------------------------
# Schema reality
# ---------------------------------------------------------------------------


def test_no_telemetry_or_tariff_table_exists(db):
    """Documents why /telemetry was not created and why nothing is costed."""
    tables = set(
        db.execute(
            text("SELECT table_name FROM information_schema.tables "
                 "WHERE table_schema = 'public'")
        ).scalars()
    )
    for absent in ("telemetry", "sensor_reading", "meter_reading", "meter",
                   "tariff", "carbon", "energy", "hourly_stat", "daily_stat"):
        assert absent not in tables
    for present in ("device_param", "device_stat", "device_current_stat",
                    "energy_stat", "daily_dual_data_point", "other_device"):
        assert present in tables


def test_no_telemetry_route_was_invented(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert f"{V1}/telemetry" not in paths
    assert f"{V1}/device-stats" in paths


def test_device_stat_value_column_is_text(db):
    """Which is why no numeric aggregation is offered over device_stat."""
    data_type = db.execute(
        text("SELECT data_type FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='device_stat' "
             "AND column_name='device_param_value'")
    ).scalar_one()
    assert data_type == "character varying"


def test_energy_stat_has_composite_pk_and_no_unit_or_device_fk(db, client):
    cols = set(
        db.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='energy_stat'")
        ).scalars()
    )
    assert "unit" not in cols and "device_id" not in cols
    assert "id" not in cols, "composite natural key, no surrogate id"
    # ...therefore no single-id detail route may exist.
    paths = set(client.get("/openapi.json").json()["paths"])
    assert f"{V1}/energy-stats/{{energy_stat_id}}" not in paths
    assert f"{V1}/energy-stats/summary" in paths


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
        (f"{V1}/device-params", "SELECT count(*) FROM device_param"),
        (f"{V1}/device-stats", "SELECT count(*) FROM device_stat"),
        (f"{V1}/device-current-stats", "SELECT count(*) FROM device_current_stat"),
        (f"{V1}/other-device-readings", "SELECT count(*) FROM other_device"),
        (f"{V1}/energy-stats", "SELECT count(*) FROM energy_stat"),
        (f"{V1}/daily-data-points", "SELECT count(*) FROM daily_dual_data_point"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# Parameter registry
# ---------------------------------------------------------------------------


def test_parameter_registry_is_the_35_real_rows(client, db):
    body = client.get(f"{V1}/device-params?page_size=100").json()
    assert body["total"] == 35
    for p in body["items"]:
        assert p["device_type_name"] and p["device_short_code"]
        assert p["data_type"] in {"Integer", "Double", "String", "Date Time", None}


def test_units_are_only_those_actually_stored(client, db):
    body = client.get(f"{V1}/device-params?page_size=100").json()
    api_units = {(p["param_name"], p["unit"]) for p in body["items"]}
    db_units = {
        (n, u)
        for n, u in db.execute(text("SELECT param_name, unit FROM device_param")).all()
    }
    assert api_units == db_units
    # Some parameters genuinely carry no unit -- that must survive as null.
    assert any(u is None for _n, u in api_units)


def test_param_name_is_not_unique(client, db):
    """Intellihub has four rows named relay_status -- reported, not corrected."""
    dupes = db.execute(
        text("""SELECT param_name, count(*) FROM device_param
                GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC""")
    ).all()
    assert dupes, "the registry really does repeat names"
    relay = client.get(f"{V1}/device-params?param_name=relay_status&page_size=100").json()
    assert relay["total"] == db.execute(
        text("SELECT count(*) FROM device_param WHERE param_name = 'relay_status'")
    ).scalar_one()
    assert relay["total"] > 1


def test_param_detail_reading_count(client, db):
    param_id, expected = db.execute(
        text("""SELECT device_param_id, count(*) FROM device_stat
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(f"{V1}/device-params/{param_id}").json()["reading_count"] == expected


def test_param_404(client):
    assert client.get(f"{V1}/device-params/9999").status_code == 404


def test_filter_params_by_device_type_and_unit(client, db):
    body = client.get(f"{V1}/device-params?device_type=4&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device_param WHERE device_type = 4")
    ).scalar_one()
    unitless = client.get(f"{V1}/device-params?has_unit=false&page_size=100").json()
    assert unitless["total"] == db.execute(
        text("SELECT count(*) FROM device_param WHERE unit IS NULL")
    ).scalar_one()


# ---------------------------------------------------------------------------
# device_stat readings
# ---------------------------------------------------------------------------


def test_reading_resolves_device_param_and_location(client, db):
    body = client.get(f"{V1}/device-stats?page_size=100").json()
    reading = body["items"][0]
    assert reading["param_name"] and reading["data_type"]
    assert reading["device_uid"]
    assert reading["amenity_name"], "room resolved from the device"
    assert reading["facility_id"], "facility resolved from the device"
    row = db.execute(
        text("SELECT device_param_value FROM device_stat WHERE id = :i"),
        {"i": reading["id"]},
    ).scalar_one()
    assert reading["device_param_value"] == row


def test_reading_values_are_returned_as_strings(client):
    for r in client.get(f"{V1}/device-stats?page_size=100").json()["items"]:
        assert r["device_param_value"] is None or isinstance(r["device_param_value"], str)


def test_unit_travels_with_the_reading(client, db):
    body = client.get(f"{V1}/device-stats?param_name=active_energy&page_size=100").json()
    assert body["total"] > 0
    for r in body["items"]:
        assert r["unit"] == "kWh", "active_energy is kWh in device_param"


def test_filter_readings_by_device_and_param(client, db):
    device_id, expected = db.execute(
        text("SELECT device_id, count(*) FROM device_stat GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(
        f"{V1}/device-stats?device_id={device_id}&page_size=100"
    ).json()["total"] == expected

    param_id, expected = db.execute(
        text("""SELECT device_param_id, count(*) FROM device_stat
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(
        f"{V1}/device-stats?device_param_id={param_id}&page_size=100"
    ).json()["total"] == expected


def test_filter_readings_by_floor_and_facility(client, db):
    floor_id = str(
        db.execute(text("SELECT id FROM property WHERE property_name = 'Floor 1'")).scalar_one()
    )
    assert client.get(f"{V1}/device-stats?floor_id={floor_id}&page_size=100").json()["total"] == (
        db.execute(
            text("""SELECT count(*) FROM device_stat ds
                    JOIN device d ON d.id = ds.device_id
                    JOIN amenity a ON a.id = d.amenity_id
                    JOIN property_chain pc ON pc.id = a.property_chain_id
                    WHERE pc.level_two_id = :f"""),
            {"f": floor_id},
        ).scalar_one()
    )


def test_filter_readings_by_timestamp_range(client, db):
    assert client.get(
        f"{V1}/device-stats?timestamp_from=2099-01-01T00:00:00Z"
    ).json()["total"] == 0
    assert client.get(
        f"{V1}/device-stats?timestamp_to=2099-01-01T00:00:00Z"
    ).json()["total"] == db.execute(text("SELECT count(*) FROM device_stat")).scalar_one()


def test_reading_404(client):
    r = client.get(f"{V1}/device-stats/99999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_inactive_devices_report_no_readings(client, db):
    """Consistent with Phase 2.6: an offline device emits nothing."""
    device_id = str(
        db.execute(
            text("SELECT id FROM device WHERE health_status = 'Inactive' LIMIT 1")
        ).scalar_one()
    )
    assert client.get(f"{V1}/device-stats?device_id={device_id}").json()["total"] == 0


# ---------------------------------------------------------------------------
# Snapshots and third-party meters
# ---------------------------------------------------------------------------


def test_current_stat_returns_the_snapshot_payload(client, db):
    body = client.get(f"{V1}/device-current-stats?page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM device_current_stat")
    ).scalar_one()
    item = body["items"][0]
    assert isinstance(item["device_stats"], dict)
    assert item["device_uid"]


def test_other_device_readings_are_numeric_and_unjoinable(client, db):
    body = client.get(f"{V1}/other-device-readings?page_size=100").json()
    item = body["items"][0]
    assert isinstance(item["voltage"], float)
    assert isinstance(item["today_energy"], float)
    # No FK exists on this table, so no device/facility/amenity is exposed.
    assert "device_id" not in item and "facility_id" not in item
    assert db.execute(
        text("""SELECT count(*) FROM information_schema.table_constraints
                WHERE table_name = 'other_device' AND constraint_type = 'FOREIGN KEY'""")
    ).scalar_one() == 0


def test_other_device_raw_payload_is_withheld(client, db):
    for item in client.get(f"{V1}/other-device-readings?page_size=100").json()["items"]:
        assert "msg_string" not in item
    assert db.execute(
        text("SELECT count(*) FROM other_device WHERE msg_string IS NOT NULL")
    ).scalar_one() > 0


def test_other_device_404(client):
    assert client.get(f"{V1}/other-device-readings/99999999").status_code == 404


# ---------------------------------------------------------------------------
# Energy -- and everything that is NOT calculated
# ---------------------------------------------------------------------------


def test_energy_hour_is_not_a_timestamp_and_the_derivation_is_correct(client, db):
    body = client.get(f"{V1}/energy-stats?page_size=100").json()
    for row in body["items"]:
        assert row["hour"] > 200000, "hours since 2000, not a year or a unix time"
        expected = hour_to_timestamp(row["hour"])
        assert datetime.fromisoformat(row["hour_timestamp"]) == expected
    # Cross-check the epoch against PostgreSQL itself.
    hour, pg_ts = db.execute(
        text("""SELECT hour, timestamp '2000-01-01 00:00:00+00' + (hour || ' hours')::interval
                FROM energy_stat ORDER BY hour LIMIT 1""")
    ).one()
    assert hour_to_timestamp(hour).replace(tzinfo=None) == pg_ts


def test_energy_unit_is_always_null(client):
    """`energy_stat` stores no unit -- callers must not assume kWh."""
    for row in client.get(f"{V1}/energy-stats?page_size=100").json()["items"]:
        assert row["energy_unit"] is None
        assert isinstance(row["energy_consumed"], float)


def test_no_cost_carbon_or_efficiency_is_ever_returned(client):
    raw = client.get(f"{V1}/energy-stats?page_size=100").text.lower()
    summary = client.get(f"{V1}/energy-stats/summary?group_by=day").text.lower()
    for forbidden in ("cost", "tariff", "carbon", "co2", "saving", "efficiency",
                      "currency", "price", "baseline", "kwh"):
        assert forbidden not in raw, f"{forbidden!r} appeared in /energy-stats"
        assert forbidden not in summary, f"{forbidden!r} appeared in the summary"


def test_energy_resolves_its_room_and_floor(client, db):
    row = client.get(f"{V1}/energy-stats?page_size=100").json()["items"][0]
    assert row["amenity_name"]
    assert row["building_name"] == "Tower A"
    assert row["device_name"], "free text; there is no FK to device"


def test_energy_summary_is_only_sum_and_count(client, db):
    body = client.get(f"{V1}/energy-stats/summary?group_by=day").json()
    assert body["energy_unit"] is None
    db_total, db_count = db.execute(
        text("SELECT sum(energy_consumed), count(*) FROM energy_stat")
    ).one()
    assert body["reading_count"] == db_count
    assert body["total_energy_consumed"] == pytest.approx(float(db_total))
    assert sum(b["reading_count"] for b in body["buckets"]) == db_count


@pytest.mark.parametrize("group_by", ["hour", "day", "amenity", "device"])
def test_energy_summary_group_by_options(client, db, group_by):
    body = client.get(f"{V1}/energy-stats/summary?group_by={group_by}").json()
    assert body["group_by"] == group_by
    assert body["bucket_count"] == len(body["buckets"]) > 0
    # The total is invariant across groupings -- it is the same SUM.
    assert body["total_energy_consumed"] == pytest.approx(
        float(db.execute(text("SELECT sum(energy_consumed) FROM energy_stat")).scalar_one())
    )


def test_energy_summary_by_amenity_matches_sql(client, db):
    body = client.get(f"{V1}/energy-stats/summary?group_by=amenity").json()
    expected = {
        str(a): (float(total), n)
        for a, total, n in db.execute(
            text("""SELECT amenity_id, sum(energy_consumed), count(*)
                    FROM energy_stat GROUP BY 1""")
        ).all()
    }
    assert len(body["buckets"]) == len(expected)
    for bucket in body["buckets"]:
        total, n = expected[bucket["bucket"]]
        assert bucket["total_energy_consumed"] == pytest.approx(total)
        assert bucket["reading_count"] == n
        assert bucket["bucket_label"], "room name is resolved"


def test_energy_summary_rejects_an_unknown_grouping(client):
    r = client.get(f"{V1}/energy-stats/summary?group_by=month")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_energy_filters(client, db):
    device_name, expected = db.execute(
        text("SELECT device_name, count(*) FROM energy_stat GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(
        f"{V1}/energy-stats?device_name={device_name}&page_size=100"
    ).json()["total"] == expected

    amenity_id, expected = db.execute(
        text("SELECT amenity_id, count(*) FROM energy_stat GROUP BY 1 ORDER BY 2 DESC LIMIT 1")
    ).one()
    assert client.get(
        f"{V1}/energy-stats?amenity_id={amenity_id}&page_size=100"
    ).json()["total"] == expected


def test_energy_timestamp_filter_converts_to_hour(client, db):
    """Note the quote(): an ISO timestamp carries a `+` offset, which is a
    literal space in a query string unless encoded."""
    max_hour = db.execute(text("SELECT max(hour) FROM energy_stat")).scalar_one()
    future = quote(hour_to_timestamp(max_hour + 10).isoformat())
    assert client.get(f"{V1}/energy-stats?timestamp_from={future}").json()["total"] == 0
    past = quote(hour_to_timestamp(0).isoformat())
    assert client.get(
        f"{V1}/energy-stats?timestamp_from={past}&page_size=100"
    ).json()["total"] == db.execute(text("SELECT count(*) FROM energy_stat")).scalar_one()


def test_unencoded_timestamp_offset_is_a_clean_422(client, db):
    """A `+` offset that the caller forgot to encode must fail loudly through
    the shared error envelope, not silently match nothing."""
    raw = hour_to_timestamp(0).isoformat()
    assert "+" in raw
    r = client.get(f"{V1}/energy-stats?timestamp_from={raw}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Daily KPI points
# ---------------------------------------------------------------------------


def test_daily_metric_types_are_the_five_real_values(client, db):
    types = {
        d["metric_type"]
        for d in client.get(f"{V1}/daily-data-points?page_size=100").json()["items"]
    }
    assert types == {"smart room", "service request", "checkout", "booking", "guest room"}


def test_daily_data_point_composite_detail_route(client, db):
    metric_date, metric_type = db.execute(
        text("SELECT metric_date, metric_type FROM daily_dual_data_point LIMIT 1")
    ).one()
    body = client.get(f"{V1}/daily-data-points/{metric_date}/{metric_type}").json()
    assert body["metric_type"] == metric_type
    assert float(body["dp_2"]) >= float(body["dp_1"]), "numerator within denominator"


def test_daily_data_point_404(client):
    r = client.get(f"{V1}/daily-data-points/1999-01-01/smart room")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_filter_daily_points_by_type_and_date(client, db):
    body = client.get(
        f"{V1}/daily-data-points?metric_type=smart room&page_size=100"
    ).json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM daily_dual_data_point WHERE metric_type = 'smart room'")
    ).scalar_one()
    assert client.get(
        f"{V1}/daily-data-points?metric_date_from=2099-01-01"
    ).json()["total"] == 0


# ---------------------------------------------------------------------------
# Pagination, empty results, invalid input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    r = client.get(f"{path}?page_size=101")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_the_reading_stream(client):
    total = client.get(f"{V1}/device-stats").json()["total"]
    first = client.get(f"{V1}/device-stats?page=1&page_size=50").json()
    second = client.get(f"{V1}/device-stats?page=2&page_size=50").json()
    assert len(first["items"]) == 50
    assert first["total"] == second["total"] == total
    assert {r["id"] for r in first["items"]}.isdisjoint({r["id"] for r in second["items"]})


def test_page_beyond_the_end_is_empty(client):
    body = client.get(f"{V1}/device-stats?page=999").json()
    assert body["items"] == [] and body["total"] > 0


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/device-stats?device_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "path,query",
    [
        (f"{V1}/device-stats", "device_param_id=abc"),
        (f"{V1}/device-stats", "device_id=not-a-uuid"),
        (f"{V1}/device-stats", "timestamp_from=nope"),
        (f"{V1}/energy-stats", "hour_from=abc"),
        (f"{V1}/daily-data-points", "metric_date_from=nope"),
    ],
)
def test_invalid_filters_are_422(client, path, query):
    r = client.get(f"{path}?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [f"{V1}/device-stats?page_size=100", f"{V1}/device-current-stats?page_size=100",
     f"{V1}/energy-stats?page_size=100", f"{V1}/other-device-readings?page_size=100"],
)
def test_no_credential_or_metadata_leaks(client, path):
    raw = client.get(path).text.lower()
    for needle in ("authentication_code", "password", "hash", "token", "secret",
                   '"metadata"', "msg_string"):
        assert needle not in raw, f"{needle!r} leaked from {path}"


def test_openapi_telemetry_schemas_declare_no_sensitive_fields(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("DeviceStatRead", "DeviceCurrentStatRead", "OtherDeviceReadingRead",
                 "EnergyStatRead"):
        fields = set(schemas[name]["properties"])
        assert not fields & {"authentication_code", "metadata", "msg_string",
                             "password_hash"}


# ---------------------------------------------------------------------------
# RBAC -- two distinct modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_rbac_module_is_a_real_registry_entry(db, path, module):
    assert db.execute(
        text("SELECT count(*) FROM role_module WHERE module_name = :m"), {"m": module}
    ).scalar_one() == 1


def test_no_energy_or_telemetry_module_exists(db):
    """Why energy is gated on `reports` and telemetry on `caleido_network`."""
    names = set(db.execute(text("SELECT module_name FROM role_module")).scalars())
    for absent in ("energy", "telemetry", "device_stats", "power", "energy_view"):
        assert absent not in names
    assert {"reports", "caleido_network"} <= names


@pytest.mark.parametrize("path,module", ALL_ENDPOINTS)
def test_unauthenticated_is_401(anon, path, module):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_summary_route_is_protected_too(anon):
    assert anon.get(f"{V1}/energy-stats/summary").status_code == 401


def test_malformed_token_is_401(anon):
    assert anon.get(
        f"{V1}/device-stats", headers={"Authorization": "Bearer not.a.token"}
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


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_phase_2_9_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/device-params", f"{V1}/device-params/{{param_id}}",
        f"{V1}/device-stats", f"{V1}/device-stats/{{stat_id}}",
        f"{V1}/device-current-stats", f"{V1}/device-current-stats/{{current_stat_id}}",
        f"{V1}/other-device-readings", f"{V1}/other-device-readings/{{reading_id}}",
        f"{V1}/energy-stats", f"{V1}/energy-stats/summary",
        f"{V1}/daily-data-points",
        f"{V1}/daily-data-points/{{metric_date}}/{{metric_type}}",
    } <= paths


def test_phase_2_9_is_read_only(client):
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if any(k in path for k in ("device-stat", "device-param", "device-current",
                                   "other-device", "energy", "daily-data")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"


@pytest.mark.parametrize("domain", ["mqtt", "websocket", "commands", "ingest", "dashboard"])
def test_downstream_domains_remain_absent(client, domain):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(domain in p for p in paths), f"{domain} belongs to a later phase"


def test_earlier_phase_endpoints_still_work(client, anon, admin_headers):
    assert anon.get("/health").status_code == 200
    for path in (f"{V1}/facilities", f"{V1}/rooms", f"{V1}/users", f"{V1}/roles",
                 f"{V1}/service-requests", f"{V1}/devices", f"{V1}/alerts",
                 f"{V1}/notifications", f"{V1}/stays", f"{V1}/occupancy"):
        assert client.get(path).status_code == 200
    assert anon.get(f"{V1}/auth/me", headers=admin_headers).status_code == 200
