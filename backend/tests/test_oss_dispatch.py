"""OSS dispatch layer tests (HMS side).

Cover the schema-independent behaviour that must hold regardless of the OSS DB:
the path registry, occupancy's room-mapped device count, that the proxy enforces
RBAC BEFORE forwarding, and how /devices composes OSS devices with HMS rooms.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints import oss_proxy
from app.core import oss_routes
from app.db.session import get_db
from app.services import occupancy as occ
from app.services import oss_client
from app.services import room_devices


# --------------------------------------------------------------------------
# path registry
# --------------------------------------------------------------------------

def test_oss_read_paths_match_the_prefixes():
    assert oss_routes.is_oss_read_path("/api/v1/devices")
    assert oss_routes.is_oss_read_path("/api/v1/devices/abc/health")
    assert oss_routes.is_oss_read_path("/energy-stats")
    # BSS and the deliberate exception must NOT be OSS.
    assert not oss_routes.is_oss_read_path("/api/v1/occupancy")
    assert not oss_routes.is_oss_read_path("/api/v1/daily-data-points")


def test_oss_subpath_strips_the_v1_prefix():
    assert oss_routes.oss_subpath("/api/v1/devices/1") == "/devices/1"
    assert oss_routes.oss_subpath("/devices") == "/devices"


# --------------------------------------------------------------------------
# occupancy: a room's devices come from room_device_map, not from OSS
# --------------------------------------------------------------------------

def test_resolve_device_count_reads_the_room_mapping(monkeypatch):
    monkeypatch.setattr(occ.settings, "OSS_ENABLED", True)
    monkeypatch.setattr(occ.room_devices, "count_in_room", lambda db, amenity_id: 4)
    assert occ._resolve_device_count(None, uuid.uuid4()) == 4


# --------------------------------------------------------------------------
# proxy: RBAC runs BEFORE forwarding; forwards on success; 503 when OSS down
# --------------------------------------------------------------------------

class _User:
    """Minimal stand-in; require_permission only calls `.may`."""
    def may(self, module, permission):
        return module == "caleido_network" and permission == "read"


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(oss_proxy._build("/devices", "caleido_network"))
    return app


def test_proxy_401_without_authenticated_user():
    # No dependency override -> get_current_user raises 401 before any forward.
    client = TestClient(_app())
    assert client.get("/devices").status_code == 401


def test_proxy_forwards_when_authorised(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (200, {"items": [], "page": 1, "page_size": 20, "total": 0}),
    )
    r = TestClient(app).get("/devices")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_proxy_keeps_repeated_query_params(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    seen = {}

    def capture(method, subpath, *, params=None, json=None):
        seen["params"] = list(params)
        return 200, {"items": [], "page": 1, "page_size": 20, "total": 0}
    monkeypatch.setattr(oss_client, "forward", capture)
    TestClient(app).get("/devices?status=1&status=2&page=1")
    assert seen["params"] == [("status", "1"), ("status", "2"), ("page", "1")]


def test_proxy_503_when_oss_unavailable(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()

    def boom(*a, **k):
        raise oss_client.OssUnavailable("down")
    monkeypatch.setattr(oss_client, "forward", boom)
    r = TestClient(app).get("/devices")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "oss_unavailable"


def test_proxy_403_when_user_lacks_grant():
    class _NoGrant:
        def may(self, module, permission):
            return False
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _NoGrant()
    assert TestClient(app).get("/devices").status_code == 403


# --------------------------------------------------------------------------
# /devices: OSS device data + HMS room data
# --------------------------------------------------------------------------

ROOM = uuid.uuid4()
MAPPED, UNMAPPED = uuid.uuid4(), uuid.uuid4()
ROOM_211 = {
    "amenity_id": ROOM, "amenity_name": "211", "facility_id": None,
    "building_id": None, "building_name": "Main", "floor_id": None, "floor_name": "2",
}


def _devices_app(monkeypatch, *, mapped=(MAPPED,)) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(oss_proxy._build_devices("caleido_network"))
    app.dependency_overrides[get_current_user] = lambda: _User()
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(room_devices, "device_ids_at", lambda db, **f: list(mapped))
    monkeypatch.setattr(
        room_devices, "locations_for",
        lambda db, ids: {MAPPED: ROOM_211} if MAPPED in ids else {},
    )
    sent: dict = {}

    def forward(method, subpath, *, params=None, json=None):
        sent["subpath"], sent["params"] = subpath, list(params)
        device = lambda i: {"id": str(i), "amenity_id": None, "amenity_name": None}
        if subpath == "/devices":
            return 200, {"items": [device(MAPPED), device(UNMAPPED)],
                         "page": 1, "page_size": 20, "total": 2}
        return 200, device(MAPPED)
    monkeypatch.setattr(oss_client, "forward", forward)
    return TestClient(app), sent


def test_devices_get_their_room_from_hms(monkeypatch):
    client, _ = _devices_app(monkeypatch)
    items = {d["id"]: d for d in client.get("/devices").json()["items"]}
    assert items[str(MAPPED)]["amenity_id"] == str(ROOM)
    assert items[str(MAPPED)]["amenity_name"] == "211"
    # HMS does not know where an unmapped device is; it stays null.
    assert items[str(UNMAPPED)]["amenity_id"] is None


def test_room_filter_asks_oss_for_the_mapped_devices_only(monkeypatch):
    client, sent = _devices_app(monkeypatch)
    client.get(f"/devices?amenity_id={ROOM}&q=hub")
    assert ("device_ids", str(MAPPED)) in sent["params"]
    assert ("q", "hub") in sent["params"]
    # OSS has no rooms: the room filter itself is never forwarded.
    assert all(k != "amenity_id" for k, _ in sent["params"])


def test_room_with_no_devices_is_an_empty_page_without_calling_oss(monkeypatch):
    client, sent = _devices_app(monkeypatch, mapped=())
    r = client.get(f"/devices?amenity_id={ROOM}")
    assert r.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}
    assert sent == {}


def test_malformed_room_filter_is_422(monkeypatch):
    client, _ = _devices_app(monkeypatch)
    assert client.get("/devices?amenity_id=211").status_code == 422


def test_device_detail_gets_its_room(monkeypatch):
    client, sent = _devices_app(monkeypatch)
    body = client.get(f"/devices/{MAPPED}").json()
    assert sent["subpath"] == f"/devices/{MAPPED}"
    assert body["amenity_name"] == "211"
