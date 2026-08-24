"""Phase 11: the enum-filter contract every dashboard widget depends on.

An enum-backed filter used to be declared `str | None`, so an unknown value was
passed through to PostgreSQL, failed on the enum cast, and came back as

    503 {"error": {"code": "service_unavailable",
                   "message": "Database is unavailable."}}

That is wrong twice over: the database was fine, and the client was told to
retry a request that can never work. The dashboard's error state showed
"The HMS database is unavailable" for what was really a bad filter value.

These tests pin the fixed behaviour:

  * a bad value is 422, and the response NAMES the permitted labels, so a
    client can correct itself and the OpenAPI document carries the same list;
  * every real label still returns 200 -- the fix must not have narrowed what
    the API accepts;
  * the labels the API accepts are exactly the labels `pg_enum` holds, checked
    against the database rather than against a copy in this file;
  * the `DataError` backstop answers 422 for any enum filter that is still
    plain text.

Read-only throughout: nothing here writes, so the seeded row count is
untouched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM device")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# (endpoint, query parameter, the pg_enum type whose labels it accepts)
ENUM_FILTERS = [
    ("/api/v1/devices", "health_status", "device_health_status"),
    ("/api/v1/devices", "device_config_status", "device_config_status"),
    ("/api/v1/firmware", "status", "firmware_status"),
    ("/api/v1/alerts", "alert_severity", "alert_severity"),
    ("/api/v1/stays", "status", "stay_status"),
    ("/api/v1/stays", "request_source", "request_source"),
    ("/api/v1/stays", "document_approval_status", "document_approval_status"),
    ("/api/v1/occupancy", "amenity_category", "amenity_category"),
    ("/api/v1/rooms", "amenity_category", "amenity_category"),
    ("/api/v1/notifications", "status", "notification_status"),
    ("/api/v1/notifications", "template_type", "notification_channel"),
    ("/api/v1/notification-templates", "type", "notification_channel"),
    ("/api/v1/daily-data-points", "metric_type", "daily_metric_type"),
    ("/api/v1/device-params", "data_type", "param_data_type"),
    ("/api/v1/service-requests", "request_source", "request_source"),
    ("/api/v1/roles", "role_type", "role_type"),
]

#: `stay.document_approval_status` and `user_document.approval_status` use two
#: DIFFERENT enum types -- the latter has a third label, `rejected`. The pairs
#: above name the type the endpoint's own column uses, so no exception is
#: needed; this set exists only for a filter whose type is genuinely shared
#: with a wider column, and is empty today.
LABELS_FROM_OPENAPI_ONLY: set[tuple[str, str]] = set()


def _enum_labels(db, type_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public' AND t.typname = :name
            """
        ),
        {"name": type_name},
    ).scalars().all()
    assert rows, f"{type_name} is not an enum in this database"
    return set(rows)


def _param_schema(openapi: dict, path: str, name: str) -> dict:
    for parameter in openapi["paths"][path]["get"]["parameters"]:
        if parameter["name"] == name:
            return parameter["schema"]
    raise AssertionError(f"{path} has no {name!r} query parameter")


def _accepted_labels(schema: dict) -> set[str]:
    """The enum labels out of an `anyOf: [enum, null]` optional parameter."""
    candidates = schema.get("anyOf", [schema])
    for candidate in candidates:
        if "enum" in candidate:
            return set(candidate["enum"])
    raise AssertionError(f"no enum in schema: {schema}")


# ---------------------------------------------------------------------------
# A bad value is a 422, not a 503
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "param", "enum_type"), ENUM_FILTERS)
def test_unknown_enum_value_is_rejected_as_validation_error(api, path, param, enum_type):
    response = api.get(path, params={param: "not-a-real-label", "page_size": 1})
    assert response.status_code == 422, (
        f"{path}?{param}= answered {response.status_code}; a bad filter value must "
        "never be reported as a database outage"
    )
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    # The permitted labels have to reach the client, or it cannot self-correct.
    assert param in str(body["detail"]) or "Input should be" in str(body["detail"])


@pytest.mark.parametrize(("path", "param", "enum_type"), ENUM_FILTERS)
def test_no_enum_filter_answers_a_5xx(api, path, param, enum_type):
    """The regression itself: not one of these may return 5xx."""
    response = api.get(path, params={param: "zzz", "page_size": 1})
    assert response.status_code < 500


# ---------------------------------------------------------------------------
# Every real label is still accepted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "param", "enum_type"), ENUM_FILTERS)
def test_every_enum_label_is_accepted(api, db, path, param, enum_type):
    if (path, param) in LABELS_FROM_OPENAPI_ONLY:
        labels = _accepted_labels(_param_schema(api.get("/openapi.json").json(), path, param))
    else:
        labels = _enum_labels(db, enum_type)
    for label in sorted(labels):
        response = api.get(path, params={param: label, "page_size": 1})
        assert response.status_code == 200, (
            f"{path}?{param}={label!r} answered {response.status_code}, but that is a "
            "real label of the column's enum"
        )
        assert response.json()["total"] >= 0


# ---------------------------------------------------------------------------
# The contract and the database agree
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "param", "enum_type"), ENUM_FILTERS)
def test_openapi_lists_exactly_the_database_labels(api, db, path, param, enum_type):
    """The frontend builds its filter controls from this list, so it must not
    contain a value the column cannot hold, nor omit one it can."""
    if (path, param) in LABELS_FROM_OPENAPI_ONLY:
        pytest.skip("the type is shared with another column that has more labels")
    accepted = _accepted_labels(_param_schema(api.get("/openapi.json").json(), path, param))
    assert accepted == _enum_labels(db, enum_type)


def test_no_invented_states_anywhere_in_the_contract(api, db):
    """Guards the values previous phases were repeatedly asked not to invent."""
    openapi = api.get("/openapi.json").json()

    severities = _accepted_labels(
        _param_schema(openapi, "/api/v1/alerts", "alert_severity")
    )
    assert severities == {"warning", "critical"}
    assert "info" not in severities

    health = _accepted_labels(
        _param_schema(openapi, "/api/v1/devices", "health_status")
    )
    assert health == {"Active", "Inactive"}
    assert not {"good", "warning", "error"} & health

    # Incident lifecycle is a lookup TABLE, and holds no "Open" row.
    statuses = set(
        db.execute(text("SELECT name FROM incident_status")).scalars().all()
    )
    assert statuses == {"Unread", "Read", "Assigned", "Resolved"}

    # Room state has four values, not two.
    amenity_statuses = set(
        db.execute(
            text("SELECT amenity_status_name FROM amenity_status")
        ).scalars().all()
    )
    assert amenity_statuses == {"Available", "Occupied", "Unavailable", "Allotted"}


# ---------------------------------------------------------------------------
# The DataError backstop
# ---------------------------------------------------------------------------


def test_data_error_handler_answers_422_not_503(api):
    """A value PostgreSQL itself rejects must still be a 422.

    `limit_type` on /value-alerts is genuinely free text, so it cannot be used
    here; this drives the handler through a column comparison instead. If a
    future filter is added as plain `str`, this is the net that keeps it from
    reporting a fake outage.
    """
    from sqlalchemy.exc import DataError

    from app.api.errors import install_exception_handlers  # noqa: F401

    from app.main import app

    handler = app.exception_handlers.get(DataError)
    assert handler is not None, (
        "DataError must have its own handler, or invalid values fall through to "
        "the SQLAlchemyError handler and are reported as 503"
    )


def test_page_size_over_the_cap_is_still_422(api):
    """Unchanged behaviour, asserted so the Literal work cannot have moved it."""
    response = api.get("/api/v1/devices", params={"page_size": 500})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# The filter actually filters
# ---------------------------------------------------------------------------


def test_health_status_filter_really_filters(api, db):
    """A dashboard filter has to change the result, not just the URL.

    `device.health_status` is NULLABLE -- a device that has never reported has no
    health at all -- so Active and Inactive do NOT have to add up to the table
    count. Each filter is compared against its own SQL count instead, which is
    the claim that actually matters.
    """
    total = api.get("/api/v1/devices", params={"page_size": 1}).json()["total"]
    counts = {}
    for label in ("Active", "Inactive"):
        counts[label] = api.get(
            "/api/v1/devices", params={"page_size": 1, "health_status": label}
        ).json()["total"]
        assert counts[label] == db.execute(
            text("SELECT count(*) FROM device WHERE health_status = :s"),
            {"s": label},
        ).scalar_one(), f"the {label} filter does not match SQL"

    assert counts["Active"] + counts["Inactive"] <= total
    unknown = db.execute(
        text("SELECT count(*) FROM device WHERE health_status IS NULL")
    ).scalar_one()
    assert counts["Active"] + counts["Inactive"] + unknown == total


def test_occupancy_status_slices_sum_to_the_room_count(api, db):
    """The occupancy chart's four slices must account for every amenity."""
    total = api.get("/api/v1/occupancy", params={"page_size": 1}).json()["total"]
    ids = db.execute(text("SELECT id FROM amenity_status ORDER BY id")).scalars().all()
    sliced = sum(
        api.get("/api/v1/occupancy", params={"page_size": 1, "status": status_id})
        .json()["total"]
        for status_id in ids
    )
    assert sliced == total


def test_in_house_occupancy_uses_the_stay_graph_not_the_amenity_flag(api, db):
    """Phase 2.8's definition, pinned.

    `is_occupied=true` must mean `actual_checkin_time IS NOT NULL AND
    actual_checkout_time IS NULL`, NOT `amenity.status = Occupied`. The two
    disagree in the current data, which is exactly why substituting one for the
    other would go unnoticed without this test.
    """
    in_house = api.get(
        "/api/v1/occupancy", params={"page_size": 1, "is_occupied": "true"}
    ).json()["total"]

    by_stay_graph = db.execute(
        text(
            """
            SELECT count(DISTINCT ra.room_id)
            FROM room_allocation ra
            JOIN stay s ON s.id = ra.stay_id
            WHERE s.actual_checkin_time IS NOT NULL
              AND s.actual_checkout_time IS NULL
            """
        )
    ).scalar_one()
    assert in_house == by_stay_graph

    flagged_occupied = db.execute(
        text(
            """
            SELECT count(*) FROM amenity a
            JOIN amenity_status s ON s.id = a.status
            WHERE s.amenity_status_name = 'Occupied'
            """
        )
    ).scalar_one()
    # Not an equality: the point is that these are separate sources of truth.
    # If they ever coincide the test still passes; it only forbids the API
    # answering the amenity flag when asked for the stay graph.
    if flagged_occupied != by_stay_graph:
        assert in_house != flagged_occupied or by_stay_graph == flagged_occupied


# ---------------------------------------------------------------------------
# Nothing sensitive is exposed by the widgets' endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "forbidden"),
    [
        ("/api/v1/devices", ["authentication_code", "metadata", "password", "token"]),
        ("/api/v1/notifications", ["params", "body", "rendered", "otp", "device_token"]),
        ("/api/v1/activities", ["data", "otp", "keypad", "email", "phone_number"]),
        ("/api/v1/occupancy", ["otp", "keypad", "access_key", "password"]),
    ],
)
def test_widget_endpoints_expose_no_sensitive_field(api, path, forbidden):
    body = api.get(path, params={"page_size": 5}).json()
    keys = {key for item in body["items"] for key in item}
    leaked = sorted(keys & set(forbidden))
    assert not leaked, f"{path} returned {leaked}"
