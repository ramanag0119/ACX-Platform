"""Phase B telemetry adapter tests (pure inference + read-only integration)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters import telemetry_adapter as ta
from app.core.config import settings
from app.main import create_app

client = TestClient(create_app())
requires_db = pytest.mark.skipif(
    not settings.is_db_configured, reason="OSS database not configured"
)


def test_infer_data_type_from_actual_values():
    # Inference from the real value's type -- no hardcoded per-key mapping.
    assert ta._infer_data_type(5) == "Integer"
    assert ta._infer_data_type(1.2) == "Double"
    assert ta._infer_data_type("x") == "String"


@requires_db
def test_current_stats_snapshot_shape():
    b = client.get("/device-current-stats").json()
    assert b["total"] >= 1
    row = b["items"][0]
    assert row["device_uid"] and isinstance(row["device_stats"], dict)
    # detail by the real record_id round-trips
    assert client.get(f"/device-current-stats/{row['id']}").status_code == 200


@requires_db
def test_params_registry_derived():
    b = client.get("/device-params").json()
    assert b["total"] >= 1
    names = {i["param_name"] for i in b["items"]}
    assert "voltage" in names or "active_energy" in names
    for i in b["items"]:
        assert i["unit"] is None           # no OSS unit source -> null, not invented
        assert i["data_type"] in ("Integer", "Double", "String")


@requires_db
def test_stats_explode_pagination_and_filter():
    full = client.get("/device-stats", params={"page_size": 1}).json()
    assert full["total"] > 1 and len(full["items"]) == 1
    volt = client.get("/device-stats", params={"param_name": "voltage", "page_size": 5}).json()
    assert all(i["param_name"] == "voltage" for i in volt["items"])
    # device_param_id matches the /device-params registry id for that name
    params = {p["param_name"]: p["id"] for p in client.get("/device-params", params={"page_size": 100}).json()["items"]}
    for i in volt["items"]:
        assert i["device_param_id"] == params["voltage"]


@requires_db
def test_stats_values_returned_as_stored():
    i = client.get("/device-stats", params={"page_size": 1}).json()["items"][0]
    assert isinstance(i["device_param_value"], str)  # as stored, no conversion


@requires_db
def test_unsupported_telemetry_resources_503():
    assert client.get("/device-stats/5").status_code == 503          # no stable id
    assert client.get("/other-device-readings").status_code == 503   # no OSS table


@requires_db
def test_missing_param_404():
    assert client.get("/device-params/99999").status_code == 404
