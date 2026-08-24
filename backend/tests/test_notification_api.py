"""Phase 2.7 notification / activity-feed API tests.

Run:  python -m pytest tests/test_notification_api.py -q

The security block below is the important part of this file: the seeded
template registry contains OTP and keypad-key templates, so the rendered body
and its merge params would carry secrets in a real install. Those columns must
never reach the API.
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
    (f"{V1}/notification-templates", "dashboard"),
    (f"{V1}/notifications", "dashboard"),
    (f"{V1}/activities", "dashboard"),
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
    if not db.execute(text("SELECT count(*) FROM notification")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def notification_id(db):
    return db.execute(text("SELECT min(id) FROM notification")).scalar_one()


@pytest.fixture(scope="module")
def activity_id(db):
    return db.execute(text("SELECT min(id) FROM activity")).scalar_one()


# ---------------------------------------------------------------------------
# Lists and database-backed totals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_list_returns_200_with_the_shared_envelope(client, path, module):
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "page", "page_size", "total"}


@pytest.mark.parametrize(
    "path,sql",
    [
        (f"{V1}/notification-templates", "SELECT count(*) FROM notification_template"),
        (f"{V1}/notifications", "SELECT count(*) FROM notification"),
        (f"{V1}/activities", "SELECT count(*) FROM activity"),
    ],
)
def test_totals_are_database_backed(client, db, path, sql):
    assert client.get(path).json()["total"] == db.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------------------
# SECURITY -- the headline of this phase
# ---------------------------------------------------------------------------


def test_the_seeded_registry_really_does_contain_secret_bearing_templates(db):
    """Justifies every exclusion below."""
    names = set(db.execute(text("SELECT name FROM notification_template")).scalars())
    assert {"OTPTemplate", "KeySMSTemplate", "MaintenanceKeypadKey"} <= names


WITHHELD_KEYS = {
    "params", "body", "log", "data", "device_token", "email", "phone",
    "password", "password_hash",
}


def _all_keys(node) -> set[str]:
    """Every key anywhere in a nested JSON document."""
    if isinstance(node, dict):
        return set(node) | set().union(*(_all_keys(v) for v in node.values()), set())
    if isinstance(node, list):
        return set().union(*(_all_keys(v) for v in node), set())
    return set()


@pytest.mark.parametrize(
    "path",
    [f"{V1}/notifications?page_size=100", f"{V1}/activities?page_size=100",
     f"{V1}/notification-templates?page_size=100"],
)
def test_no_secret_bearing_field_is_returned(client, path):
    """Assert on FIELD NAMES, not raw substrings.

    A substring scan gives false positives: the template registry legitimately
    contains "otp" in `OTPTemplate` and the literal "email" as a channel VALUE.
    Neither is a secret -- the secret would live in `notification_result.body`,
    which is what the withheld-key set actually guards.
    """
    leaked = _all_keys(client.get(path).json()) & WITHHELD_KEYS
    assert not leaked, f"{sorted(leaked)} leaked from {path}"


def test_template_registry_exposes_only_metadata_never_content(client):
    """A template row names a handlebars file; it never carries rendered text."""
    for t in client.get(f"{V1}/notification-templates?page_size=100").json()["items"]:
        assert set(t) == {"id", "name", "type", "path", "created_on", "updated_on"}
        assert t["path"].endswith(".hbs"), "a file reference, not message content"


def test_notification_detail_withholds_body_params_and_contact(
    client, db, notification_id
):
    body = client.get(f"{V1}/notifications/{notification_id}").json()
    assert "params" not in body
    for receiver in body["receivers"]:
        assert set(receiver) == {"id", "app_user_id", "name", "results"}
        assert "email" not in receiver and "phone" not in receiver
        assert "device_token" not in receiver and "data" not in receiver
        for result in receiver["results"]:
            assert set(result) == {"id", "type", "status", "created_on"}
            assert "body" not in result and "log" not in result

    # Prove the withheld columns really are populated in the database.
    assert db.execute(
        text("SELECT count(*) FROM notification_result WHERE body IS NOT NULL")
    ).scalar_one() > 0
    assert db.execute(
        text("SELECT count(*) FROM notification_receiver WHERE device_token IS NOT NULL")
    ).scalar_one() > 0


def test_activity_data_bag_is_withheld(client, db, activity_id):
    body = client.get(f"{V1}/activities/{activity_id}").json()
    assert "data" not in body
    assert db.execute(
        text("SELECT count(*) FROM activity WHERE data IS NOT NULL")
    ).scalar_one() > 0


def test_openapi_schemas_declare_no_secret_fields(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("NotificationRead", "NotificationDetail", "NotificationReceiverRead",
                 "NotificationResultRead", "ActivityRead", "ActivityDetail"):
        fields = set(schemas[name]["properties"])
        assert not fields & {"params", "body", "log", "data", "device_token",
                             "email", "phone"}


# ---------------------------------------------------------------------------
# Two systems, two status vocabularies
# ---------------------------------------------------------------------------


def test_dispatch_status_is_delivery_state(client, db):
    statuses = {
        n["status"] for n in client.get(f"{V1}/notifications?page_size=100").json()["items"]
    }
    assert statuses <= {"pending", "processing", "processed", "error"}
    assert statuses == set(
        db.execute(text("SELECT DISTINCT status FROM notification")).scalars()
    )


def test_activity_notifier_status_is_read_state(client, db, activity_id):
    body = client.get(f"{V1}/activities/{activity_id}").json()
    assert body["notifiers"]
    for n in body["notifiers"]:
        assert n["status"] in {"0", "1", "2"}
        assert n["status_label"] in {"unread", "read", "clear"}


def test_the_two_status_vocabularies_are_different(client, db):
    dispatch = set(db.execute(text("SELECT DISTINCT status FROM notification")).scalars())
    feed = set(db.execute(text("SELECT DISTINCT status FROM activity_notifier")).scalars())
    assert dispatch.isdisjoint(feed), "delivery state and read state are separate"


def test_unread_count_matches_the_notifier_rows(client, db):
    for a in client.get(f"{V1}/activities?page_size=100").json()["items"]:
        assert a["unread_count"] == db.execute(
            text("SELECT count(*) FROM activity_notifier "
                 "WHERE activity_id = :a AND status = '0'"),
            {"a": a["id"]},
        ).scalar_one()


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_notification_resolves_its_template(client, db, notification_id):
    body = client.get(f"{V1}/notifications/{notification_id}").json()
    if body["template_id"]:
        assert body["template_name"]
        assert body["template_type"] in {
            "email", "sms", "push notification", "silent notification"
        }


def test_reference_id_has_no_foreign_key(db):
    """The notification -> alert/incident link the frontend might expect
    does not exist in the schema."""
    fks = db.execute(
        text("""SELECT count(*) FROM information_schema.key_column_usage k
                JOIN information_schema.table_constraints c
                  ON c.constraint_name = k.constraint_name
                WHERE k.table_name = 'notification'
                  AND k.column_name = 'reference_id'
                  AND c.constraint_type = 'FOREIGN KEY'""")
    ).scalar_one()
    assert fks == 0


def test_notification_receiver_links_to_a_real_user(client, db, notification_id):
    body = client.get(f"{V1}/notifications/{notification_id}").json()
    for receiver in body["receivers"]:
        if receiver["app_user_id"]:
            assert db.execute(
                text("SELECT count(*) FROM app_user WHERE id = :u"),
                {"u": receiver["app_user_id"]},
            ).scalar_one() == 1


def test_template_detail_counts_its_notifications(client, db):
    template_id, expected = db.execute(
        text("""SELECT template_id, count(*) FROM notification
                WHERE template_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(
        f"{V1}/notification-templates/{template_id}"
    ).json()["notification_count"] == expected


def test_activity_resolves_type_entity_and_actor(client, db, activity_id):
    body = client.get(f"{V1}/activities/{activity_id}").json()
    assert body["activity_type_name"]
    assert body["entity_type_name"] in {
        "Booking", "Occupancy", "Service Requests", "Maintenance Requests", "Default Key"
    }
    assert body["actor"] and set(body["actor"]) == {"id", "name", "emp_id"}
    assert isinstance(body["entity_id"], int), "polymorphic, no FK"


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_notifications_by_status(client, db):
    body = client.get(f"{V1}/notifications?status=processed&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM notification WHERE status = 'processed'")
    ).scalar_one()


def test_filter_notifications_by_recipient(client, db):
    user_id, expected = db.execute(
        text("""SELECT app_user_id, count(DISTINCT notification_id)
                FROM notification_receiver WHERE app_user_id IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(
        f"{V1}/notifications?app_user_id={user_id}&page_size=100"
    ).json()["total"] == expected


def test_filter_templates_by_channel(client, db):
    body = client.get(f"{V1}/notification-templates?type=sms&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM notification_template WHERE type = 'sms'")
    ).scalar_one()
    assert all(t["type"] == "sms" for t in body["items"])


def test_filter_activities_by_entity_type(client, db):
    body = client.get(f"{V1}/activities?entity_type_id=3&page_size=100").json()
    assert body["total"] == db.execute(
        text("SELECT count(*) FROM activity WHERE entity_type_id = 3")
    ).scalar_one()


def test_filter_activities_by_recipient_and_unread(client, db):
    user_id, expected = db.execute(
        text("""SELECT app_user_id, count(*) FROM activity_notifier
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    ).one()
    assert client.get(
        f"{V1}/activities?app_user_id={user_id}&page_size=100"
    ).json()["total"] == expected
    unread = client.get(f"{V1}/activities?unread_only=true&page_size=100").json()
    assert unread["total"] == db.execute(
        text("""SELECT count(DISTINCT activity_id) FROM activity_notifier
                WHERE status = '0'""")
    ).scalar_one()


def test_filter_matching_nothing_returns_an_empty_page(client):
    body = client.get(f"{V1}/activities?actor_id={uuid.uuid4()}").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


@pytest.mark.parametrize(
    "query", ["entity_type_id=abc", "actor_id=not-a-uuid", "unread_only=maybe"]
)
def test_invalid_filter_values_are_422(client, query):
    r = client.get(f"{V1}/activities?{query}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# 404 and pagination
# ---------------------------------------------------------------------------


def test_notification_404(client):
    r = client.get(f"{V1}/notifications/999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_activity_404(client):
    assert client.get(f"{V1}/activities/999999").status_code == 404


def test_template_404(client):
    assert client.get(f"{V1}/notification-templates/{uuid.uuid4()}").status_code == 404


def test_malformed_uuid_is_422(client):
    r = client.get(f"{V1}/notification-templates/not-a-uuid")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_page_size_over_100_is_rejected(client, path, module):
    assert client.get(f"{path}?page_size=101").status_code == 422


def test_pagination_splits_the_template_registry(client):
    first = client.get(f"{V1}/notification-templates?page=1&page_size=8").json()
    second = client.get(f"{V1}/notification-templates?page=2&page_size=8").json()
    assert len(first["items"]) == 8
    assert {t["id"] for t in first["items"]}.isdisjoint({t["id"] for t in second["items"]})


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_no_notification_module_exists_in_the_registry(db):
    """Documents WHY these routes are gated on `dashboard` -- an assumption,
    not a database fact. See docs/PHASE2_7_ALERTS.md."""
    names = set(db.execute(text("SELECT module_name FROM role_module")).scalars())
    for absent in ("notifications", "notification", "notification_management",
                   "alerts", "activity"):
        assert absent not in names
    assert "dashboard" in names


@pytest.mark.parametrize("path,module", ENDPOINTS)
def test_unauthenticated_is_401(anon, path, module):
    r = anon.get(path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


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


def test_phase_2_7_notification_routes_are_registered(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        f"{V1}/notification-templates", f"{V1}/notification-templates/{{template_id}}",
        f"{V1}/notifications", f"{V1}/notifications/{{notification_id}}",
        f"{V1}/activities", f"{V1}/activities/{{activity_id}}",
    } <= paths


def test_notification_routes_are_read_only(client):
    """No delivery engine was built: nothing here sends anything."""
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        if any(k in path for k in ("notification", "activit")):
            assert set(ops) == {"get"}, f"{path} exposes a non-GET method"


def test_earlier_phase_endpoints_still_work(client, anon, admin_headers):
    assert anon.get("/health").status_code == 200
    for path in (f"{V1}/facilities", f"{V1}/rooms", f"{V1}/users", f"{V1}/roles",
                 f"{V1}/service-requests", f"{V1}/devices", f"{V1}/firmware"):
        assert client.get(path).status_code == 200
    assert anon.get(f"{V1}/auth/me", headers=admin_headers).status_code == 200
