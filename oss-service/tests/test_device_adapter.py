"""Phase A device adapter tests.

Pure-mapping tests always run. Integration tests run read-only against the
configured OSS database and SKIP when it is not configured, so CI without the
OSS DB stays green. They never write.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters import device_adapter as da
from app.core.config import settings
from app.main import create_app

client = TestClient(create_app())

requires_db = pytest.mark.skipif(
    not settings.is_db_configured, reason="OSS database not configured"
)


# ---- pure mapping (no DB) ----

def test_short_code_is_null_no_oss_source():
    # OSS has no short-code column; it is served as null, never fabricated.
    assert da._short_code("IntelliHub") is None
    assert da._short_code(None) is None


def test_health_label_is_as_stored():
    # No OSS health-status lookup -> value returned as stored, not relabelled.
    assert da._health_label(1) == "1"
    assert da._health_label(None) is None


# ---- integration (read-only) ----

@requires_db
def test_device_types_registry_shape():
    b = client.get("/device-types").json()
    assert b["total"] >= 1
    names = {i["name"] for i in b["items"]}
    assert {"AirQ", "IntelliHub", "Mikos", "Kleio"} & names
    # ids are the derived stable ordinal, 1-based and unique.
    ids = [i["id"] for i in b["items"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids))


@requires_db
def test_device_type_detail_and_missing():
    b = client.get("/device-types/1").json()
    assert "device_count" in b and "firmware_count" in b
    assert client.get("/device-types/99999").status_code == 404


@requires_db
def test_devices_list_fields_and_pagination():
    b = client.get("/devices", params={"page": 1, "page_size": 2}).json()
    assert b["page"] == 1 and b["page_size"] == 2 and len(b["items"]) <= 2
    row = b["items"][0]
    # Contract fields present; facility/amenity nullable for OSS.
    for f in ("id", "device_uid", "device_name", "device_type_name",
              "device_short_code", "facility_id", "amenity_id", "created_on"):
        assert f in row


@requires_db
def test_devices_filter_by_type_and_empty_result():
    typed = client.get("/devices", params={"device_type": "1"}).json()
    assert all(i["device_type"] == 1 for i in typed["items"])
    empty = client.get("/devices", params={"q": "__no_such_device__"}).json()
    assert empty["total"] == 0 and empty["items"] == []


@requires_db
def test_device_detail_parent_child():
    items = client.get("/devices").json()["items"]
    child = next((i for i in items if i["parent_device_id"]), None)
    if child:
        d = client.get(f"/devices/{child['id']}").json()
        assert d["parent_device"] is not None
    hub = next((i for i in items if not i["parent_device_id"]), None)
    if hub:
        d = client.get(f"/devices/{hub['id']}").json()
        assert "child_devices" in d and d["child_count"] == len(d["child_devices"])


@requires_db
def test_device_health_links_by_uid():
    # a sensor device_uid (numeric) has health rows
    items = client.get("/devices").json()["items"]
    sensor = next((i for i in items if i["device_uid"] and i["device_uid"].isdigit()), None)
    if sensor:
        h = client.get(f"/devices/{sensor['id']}/health").json()
        assert h["health_sample_count"] > 0
        # Returned as stored (string) or null -- not an invented label.
        assert h["health_status"] is None or isinstance(h["health_status"], str)


@requires_db
def test_amenity_filter_unsupported_503():
    r = client.get("/devices", params={"amenity_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 503


@requires_db
def test_missing_device_404():
    assert client.get("/devices/11111111-1111-1111-1111-111111111111").status_code == 404
