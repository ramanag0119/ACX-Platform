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
from app.core.config import settings
from app.db.session import get_db
from app.services import device_type_map
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


def test_incidents_and_value_alerts_stay_in_hms():
    # OSS has no table for either; HMS owns them with the writes that drive them.
    for path in ("/api/v1/incidents", "/api/v1/incidents/abc", "/api/v1/value-alerts"):
        assert not oss_routes.is_oss_read_path(path)
    proxied = {r.prefix for r in oss_proxy.oss_proxy_routers}
    assert not proxied & {"/incidents", "/value-alerts"}


def test_every_oss_prefix_has_a_proxy_router():
    # The registry and the dispatch layer must not drift apart.
    proxied = {r.prefix for r in oss_proxy.oss_proxy_routers}
    assert proxied == set(oss_routes.OSS_READ_PREFIXES)


def test_oss_subpath_strips_the_v1_prefix():
    assert oss_routes.oss_subpath("/api/v1/devices/1") == "/devices/1"
    assert oss_routes.oss_subpath("/devices") == "/devices"


def test_oss_domain_for_picks_the_serving_microservice():
    assert oss_routes.oss_domain_for("/api/v1/devices/abc/health") == "device"
    assert oss_routes.oss_domain_for("/device-stats") == "telemetry"
    assert oss_routes.oss_domain_for("/alerts/1") == "alert"
    assert oss_routes.oss_domain_for("/incidents/1") is None
    assert oss_routes.oss_domain_for("/energy-stats") == "energy"
    assert oss_routes.oss_domain_for("/api/v1/occupancy") is None


def test_oss_url_for_falls_back_to_the_single_service(monkeypatch):
    monkeypatch.setattr(oss_client.settings, "OSS_SERVICE_URL", "http://oss:8001")
    monkeypatch.setattr(oss_client.settings, "OSS_ALERT_SERVICE_URL", "http://oss:8003")
    monkeypatch.setattr(oss_client.settings, "OSS_ENERGY_SERVICE_URL", None)
    assert oss_client.settings.oss_url_for("alert") == "http://oss:8003"
    assert oss_client.settings.oss_url_for("energy") == "http://oss:8001"
    assert oss_client.settings.oss_url_for(None) == "http://oss:8001"


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


def test_proxy_falls_back_to_stored_when_oss_unavailable(monkeypatch):
    """A list route serves stored BSS data rather than failing the screen.

    This replaced an earlier assertion that the proxy returned 503 here. The
    503 was the whole problem: OSS runs as its own process, so a restart blanked
    device screens even though HMS held the data. Detail routes still 503 --
    see the next test for why that one must not fall back.
    """
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()

    def boom(*a, **k):
        raise oss_client.OssUnavailable("down")
    monkeypatch.setattr(oss_client, "forward", boom)
    r = TestClient(app).get("/devices")
    assert r.status_code == 200
    assert r.headers["X-HMS-Data-Source"] == "stored"
    assert "items" in r.json()


def test_proxy_503_when_oss_unavailable_and_no_stored_form(monkeypatch):
    """Detail routes keep failing loudly.

    An id minted by OSS addresses a row in `insp_iot`; it does not identify a
    BSS row, so a "stored" lookup could only 404 or hit an unrelated record.
    """
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()

    def boom(*a, **k):
        raise oss_client.OssUnavailable("down")
    monkeypatch.setattr(oss_client, "forward", boom)
    r = TestClient(app).get("/devices/9d1c1a2e-0000-0000-0000-000000000000")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "oss_unavailable"


def test_live_responses_are_labelled_live(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (200, {"items": [], "page": 1, "page_size": 20, "total": 0}),
    )
    r = TestClient(app).get("/devices")
    assert r.headers["X-HMS-Data-Source"] == "live"


def test_oss_error_is_passed_through_not_masked_by_stored_data(monkeypatch):
    """OSS answering 500 is a real error; stale rows must not hide it."""
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (500, {"error": {"code": "oss_boom", "message": "x"}}),
    )
    r = TestClient(app).get("/devices")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "oss_boom"


def test_oss_404_is_passed_through(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (404, {"error": {"code": "not_found", "message": "x"}}),
    )
    assert TestClient(app).get("/devices/abc").status_code == 404


def test_resource_with_no_oss_source_falls_back_to_stored(monkeypatch):
    """`oss_adapter_not_mapped` means OSS has no table for this, permanently.

    `/other-device-readings` has no third-party-meter table in insp_iot, while
    HMS holds real rows. Falling back is not masking an outage -- OSS answered,
    and its answer was "I cannot serve this at all".
    """
    app = FastAPI()
    app.include_router(oss_proxy._build("/other-device-readings", "caleido_network"))
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (
            503,
            {"error": {"code": oss_proxy.NO_OSS_SOURCE, "message": "no source"}},
        ),
    )
    r = TestClient(app).get("/other-device-readings")
    assert r.status_code == 200
    assert r.headers["X-HMS-Data-Source"] == "stored"


def test_strict_mode_never_reads_oss_data_from_mysql(monkeypatch):
    """OSS_FALLBACK_TO_STORED=false must make the rule absolute.

    This is the mode the MySQL cleanup requires: once the duplicated OSS
    tables are dropped there is nothing to fall back to, so strict mode has to
    be switched on BEFORE they are removed and verified to fail cleanly.
    """
    monkeypatch.setattr(settings, "OSS_FALLBACK_TO_STORED", False)
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()

    def boom(*a, **k):
        raise oss_client.OssUnavailable("down")
    monkeypatch.setattr(oss_client, "forward", boom)

    r = TestClient(app).get("/devices")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "oss_unavailable"
    assert "X-HMS-Data-Source" not in r.headers


def test_strict_mode_also_refuses_the_no_source_fallback(monkeypatch):
    """Even a permanently unmapped resource must not read MySQL in strict mode."""
    monkeypatch.setattr(settings, "OSS_FALLBACK_TO_STORED", False)
    app = FastAPI()
    app.include_router(oss_proxy._build("/other-device-readings", "caleido_network"))
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (
            503,
            {"error": {"code": oss_proxy.NO_OSS_SOURCE, "message": "no source"}},
        ),
    )
    r = TestClient(app).get("/other-device-readings")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == oss_proxy.NO_OSS_SOURCE


def test_fallback_is_on_by_default():
    """The shipped default keeps screens working through an OSS restart."""
    assert settings.OSS_FALLBACK_TO_STORED is True


def test_unmapped_detail_path_still_503s(monkeypatch):
    """No stored form exists for a detail route, so the 503 must survive."""
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _User()
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (
            503,
            {"error": {"code": oss_proxy.NO_OSS_SOURCE, "message": "no source"}},
        ),
    )
    r = TestClient(app).get("/devices/abc")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == oss_proxy.NO_OSS_SOURCE


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
    # This app stubs the database out entirely, so the DB-backed device-type
    # translation is stubbed too. Its own behaviour is covered against real
    # reference rows in tests/test_device_type_map_and_fallback.py.
    monkeypatch.setattr(device_type_map, "by_name", lambda db: {})
    monkeypatch.setattr(device_type_map, "name_for_bss_id", lambda db, v: None)
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


# --------------------------------------------------------------------------
# /health/oss: which OSS domain services are reachable
# --------------------------------------------------------------------------

def _health_client() -> TestClient:
    from app.api.v1.endpoints import health
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_oss_health_is_disabled_when_dispatch_is_off(monkeypatch):
    monkeypatch.setattr(settings, "OSS_ENABLED", False)
    r = _health_client().get("/health/oss")
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "status": "disabled", "domains": []}


def test_oss_health_reports_each_domain(monkeypatch):
    monkeypatch.setattr(settings, "OSS_ENABLED", True)
    monkeypatch.setattr(oss_client, "probe", lambda d: (f"http://oss/{d}", 1.5))
    r = _health_client().get("/health/oss")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert [d["domain"] for d in body["domains"]] == list(oss_routes.OSS_DOMAIN_PREFIXES)


def test_oss_health_is_503_and_names_the_unreachable_domain(monkeypatch):
    monkeypatch.setattr(settings, "OSS_ENABLED", True)
    monkeypatch.setattr(
        oss_client, "probe",
        lambda d: (f"http://oss/{d}", None if d == "telemetry" else 1.5),
    )
    r = _health_client().get("/health/oss")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    down = [d["domain"] for d in body["domains"] if d["status"] == "unreachable"]
    assert down == ["telemetry"]
