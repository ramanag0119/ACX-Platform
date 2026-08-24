"""Phase 2.1 FastAPI foundation tests.

Run:  python -m pytest tests/test_health_api.py -q

Covers the two health endpoints, the versioning prefix, CORS, the centralised
error envelope and OpenAPI availability. No business API is exercised because
none exists yet.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import API_VERSION, app, create_app

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Application initialisation
# ---------------------------------------------------------------------------


def test_create_app_returns_an_isolated_instance():
    other = create_app()
    assert isinstance(other, FastAPI)
    assert other is not app
    assert other.title == settings.APP_NAME


def test_api_v1_prefix_is_configured():
    assert V1 == "/api/v1"


# ---------------------------------------------------------------------------
# GET /health -- liveness
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == settings.APP_NAME
    assert body["env"] == settings.APP_ENV
    assert body["version"] == API_VERSION


def test_health_does_not_touch_the_database(client, monkeypatch):
    """Liveness must stay green even if PostgreSQL is unreachable -- that is
    the entire point of separating it from readiness."""

    def exploding_db():
        raise OperationalError("SELECT 1", {}, Exception("database is down"))

    app.dependency_overrides[get_db] = exploding_db
    try:
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/health/db -- readiness, backed by a real query
# ---------------------------------------------------------------------------


def test_db_health_returns_ok(client):
    r = client.get(f"{V1}/health/db")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "hms_db"
    assert body["schema_name"] == settings.POSTGRES_SCHEMA


def test_db_health_values_come_from_postgres_not_from_code(client):
    """Every field must match what the database itself reports."""
    body = client.get(f"{V1}/health/db").json()

    session = SessionLocal()
    try:
        database = session.execute(text("SELECT current_database()")).scalar_one()
        version = session.execute(text("SHOW server_version")).scalar_one()
        revision = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    finally:
        session.close()

    assert body["database"] == database
    assert body["server_version"] == version
    assert body["alembic_revision"] == revision


def test_db_health_reports_the_applied_migration(client):
    body = client.get(f"{V1}/health/db").json()
    assert body["alembic_revision"] == "0e2687233b59"


def test_db_health_measures_real_latency(client):
    body = client.get(f"{V1}/health/db").json()
    assert isinstance(body["latency_ms"], (int, float))
    assert body["latency_ms"] > 0, "a real round trip cannot take zero time"


def test_db_health_is_503_when_the_database_is_unreachable(client):
    """The status must be derived, never hardcoded to ok."""

    def exploding_db():
        raise OperationalError("SELECT 1", {}, Exception("database is down"))

    app.dependency_overrides[get_db] = exploding_db
    try:
        r = client.get(f"{V1}/health/db")
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


def test_db_health_is_not_mounted_at_the_unversioned_path(client):
    """Phase 1's /health/db moved under /api/v1; it must not linger."""
    assert client.get("/health/db").status_code == 404


# ---------------------------------------------------------------------------
# Centralised error handling
# ---------------------------------------------------------------------------


def test_unknown_route_uses_the_error_envelope(client):
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "not_found"
    assert isinstance(body["error"]["message"], str)


def test_method_not_allowed_uses_the_error_envelope(client):
    r = client.post("/health")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "method_not_allowed"


def test_internal_errors_do_not_leak_details(client):
    """An unexpected exception must not return its type or traceback."""
    isolated = create_app()

    @isolated.get("/boom")
    def boom():
        raise RuntimeError("secret connection string in the message")

    with TestClient(isolated, raise_server_exceptions=False) as c:
        r = c.get("/boom")

    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error."
    assert "secret" not in r.text and "RuntimeError" not in r.text


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_allows_the_local_frontend_origin(client):
    origin = "http://localhost:8080"
    r = client.options(
        f"{V1}/health/db",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


def test_cors_does_not_allow_an_unknown_origin(client):
    r = client.get(f"{V1}/health/db", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_configured_origins_include_the_vite_dev_ports():
    origins = settings.cors_origins
    assert "http://localhost:8080" in origins  # vite.config.ts pins 8080
    assert "http://localhost:5173" in origins  # vite default


# ---------------------------------------------------------------------------
# OpenAPI / Swagger
# ---------------------------------------------------------------------------


def test_swagger_ui_is_served(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_openapi_schema_documents_both_health_endpoints(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == settings.APP_NAME
    assert schema["info"]["version"] == API_VERSION
    assert "/health" in schema["paths"]
    assert f"{V1}/health/db" in schema["paths"]


#: The authoritative API surface. Each phase adds its block here and nothing
#: else may appear, so this is the single place the stop condition is enforced.
DELIVERED_PATHS = {
    # Phase 2.1 -- foundation
    "/health",
    f"{V1}/health/db",
    # Phase 2.2 -- facility and property hierarchy
    f"{V1}/facilities",
    f"{V1}/facilities/{{facility_id}}",
    f"{V1}/properties",
    f"{V1}/properties/{{property_id}}",
    f"{V1}/buildings",
    f"{V1}/buildings/{{building_id}}",
    f"{V1}/floors",
    f"{V1}/floors/{{floor_id}}",
    f"{V1}/rooms",
    f"{V1}/rooms/{{room_id}}",
    # Phase 2.3 -- users, roles, modules, permissions
    f"{V1}/users",
    f"{V1}/users/{{user_id}}",
    f"{V1}/users/{{user_id}}/permissions",
    f"{V1}/roles",
    f"{V1}/roles/{{role_id}}",
    f"{V1}/roles/{{role_id}}/permissions",
    f"{V1}/modules",
    f"{V1}/modules/{{module_id}}",
    f"{V1}/permissions",
    f"{V1}/permissions/{{role_id}}/{{module_id}}",
    # Phase 2.4 -- HMS Web authentication
    f"{V1}/auth/login",
    f"{V1}/auth/me",
    # Phase 2.5 -- service catalogue and service requests
    f"{V1}/service-types",
    f"{V1}/service-types/{{service_type_id}}",
    f"{V1}/service-statuses",
    f"{V1}/service-statuses/{{status_id}}",
    f"{V1}/service-categories",
    f"{V1}/service-categories/{{category_id}}",
    f"{V1}/service-items",
    f"{V1}/service-items/{{item_id}}",
    f"{V1}/service-requests",
    f"{V1}/service-requests/{{request_id}}",
    # Phase 2.6 -- device inventory, firmware and health
    f"{V1}/device-types",
    f"{V1}/device-types/{{device_type_id}}",
    f"{V1}/devices",
    f"{V1}/devices/{{device_id}}",
    f"{V1}/devices/{{device_id}}/health",
    f"{V1}/firmware",
    f"{V1}/firmware/{{firmware_id}}",
    # Phase 2.7 -- alerts, incidents, notifications
    f"{V1}/alert-types",
    f"{V1}/alert-types/{{alert_type_id}}",
    f"{V1}/alerts",
    f"{V1}/alerts/{{alert_id}}",
    f"{V1}/alerts/{{alert_id}}/incidents",
    f"{V1}/incidents",
    f"{V1}/incidents/{{incident_id}}",
    f"{V1}/value-alerts",
    f"{V1}/value-alerts/{{value_alert_id}}",
    f"{V1}/notification-templates",
    f"{V1}/notification-templates/{{template_id}}",
    f"{V1}/notifications",
    f"{V1}/notifications/{{notification_id}}",
    f"{V1}/activities",
    f"{V1}/activities/{{activity_id}}",
    # Phase 2.8 -- stays (reservations), invoices, room occupancy
    f"{V1}/stays",
    f"{V1}/stays/{{stay_id}}",
    f"{V1}/stays/{{stay_id}}/occupants",
    f"{V1}/stays/{{stay_id}}/room-allocations",
    f"{V1}/stays/{{stay_id}}/documents",
    f"{V1}/invoices",
    f"{V1}/invoices/{{invoice_id}}",
    f"{V1}/occupancy",
    f"{V1}/occupancy/{{amenity_id}}",
    f"{V1}/amenity-statuses",
    f"{V1}/amenity-conditions",
    # Phase 2.9 -- telemetry, energy statistics, daily KPI points
    f"{V1}/device-params",
    f"{V1}/device-params/{{param_id}}",
    f"{V1}/device-stats",
    f"{V1}/device-stats/{{stat_id}}",
    f"{V1}/device-current-stats",
    f"{V1}/device-current-stats/{{current_stat_id}}",
    f"{V1}/other-device-readings",
    f"{V1}/other-device-readings/{{reading_id}}",
    f"{V1}/energy-stats",
    f"{V1}/energy-stats/summary",
    f"{V1}/daily-data-points",
    f"{V1}/daily-data-points/{{metric_date}}/{{metric_type}}",
    # Phase 3.0 -- write workflows, plus the reads those screens needed
    # Access
    f"{V1}/users/{{user_id}}/password",
    f"{V1}/users/{{user_id}}/deactivate",
    f"{V1}/users/{{user_id}}/reactivate",
    f"{V1}/departments",
    f"{V1}/departments/{{department_id}}",
    f"{V1}/job-functions",
    f"{V1}/job-functions/{{function_id}}",
    # Service requests
    f"{V1}/service-requests/{{request_id}}/items",
    f"{V1}/service-requests/{{request_id}}/cancel",
    # Stay lifecycle
    f"{V1}/stays/{{stay_id}}/check-in",
    f"{V1}/stays/{{stay_id}}/check-out",
    f"{V1}/stays/{{stay_id}}/extend",
    f"{V1}/stays/{{stay_id}}/status",
    f"{V1}/stays/{{stay_id}}/cancel",
    f"{V1}/stays/{{stay_id}}/documents/approval",
    f"{V1}/room-allocations/{{allocation_id}}",
    f"{V1}/stay-occupants/{{occupant_id}}",
    f"{V1}/occupancy/{{amenity_id}}/conditions",
    # Devices and firmware
    f"{V1}/devices/{{device_id}}/commission",
    f"{V1}/devices/{{device_id}}/decommission",
    f"{V1}/devices/{{device_id}}/maintenance",
    f"{V1}/firmware/{{firmware_id}}/assign",
    f"{V1}/limit-configs",
    f"{V1}/limit-configs/{{config_id}}",
    # Room catalogue
    f"{V1}/amenity-types",
    f"{V1}/amenity-types/{{amenity_type_id}}",
    f"{V1}/packages",
    f"{V1}/packages/{{package_id}}",
    f"{V1}/features",
    f"{V1}/features/{{feature_id}}",
    # Marketing
    f"{V1}/offers",
    f"{V1}/offers/{{offer_id}}",
    f"{V1}/events",
    f"{V1}/events/{{event_id}}",
    f"{V1}/holidays",
    f"{V1}/holidays/types",
    f"{V1}/holidays/{{occasion_id}}",
    # Job orders -- `job_order` + `job_order_amenity` + `job_order_device`.
    # One path each for the collection and the row; GET/POST share the first and
    # GET/PATCH/DELETE the second, which is why only two entries appear.
    f"{V1}/job-orders",
    f"{V1}/job-orders/{{job_order_id}}",
    # Services Planning -- `maintenance_request` + recurrence / amenity /
    # assignee. GET/POST share the collection and GET/PATCH/DELETE the row;
    # `cancel` is its own path because it is a state transition, not an edit.
    f"{V1}/maintenance-requests",
    f"{V1}/maintenance-requests/{{request_id}}",
    f"{V1}/maintenance-requests/{{request_id}}/cancel",
}


def test_openapi_exposes_only_the_phases_delivered_so_far(client):
    assert set(client.get("/openapi.json").json()["paths"]) == DELIVERED_PATHS


@pytest.mark.parametrize(
    "domain",
    # Each phase removes what it delivers: users/roles (2.3), auth/login (2.4),
    # services (2.5), devices/firmware (2.6). The rest is still future work.
    # `guests`/`bookings` remain here on purpose: Phase 2.8 found no such
    # table and deliberately did NOT invent the routes, so this now asserts
    # that decision holds. `stays`/`occupancy` left when 2.8 delivered them,
    # `device-stats`/`energy` when 2.9 did. `telemetry` STAYS: Phase 2.9 found
    # no telemetry table and exposed the real `device_param`/`device_stat`
    # pair instead, so this asserts the invented abstraction never appears.
    ["logout", "refresh", "guests", "bookings",
     "telemetry", "mqtt", "dashboard"],
)
def test_later_phase_domains_are_not_exposed_yet(client, domain):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(domain in p for p in paths), f"{domain} belongs to a later phase"


def test_db_health_documents_its_503_response(client):
    schema = client.get("/openapi.json").json()
    responses = schema["paths"][f"{V1}/health/db"]["get"]["responses"]
    assert "200" in responses and "503" in responses
