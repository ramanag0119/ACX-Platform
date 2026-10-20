"""OSS dispatch layer tests (HMS side).

Cover the schema-independent behaviour that must hold regardless of the OSS DB:
the path registry, the client's failure policy, the occupancy "unknown != zero"
rule, and that the proxy enforces RBAC BEFORE forwarding.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints import oss_proxy
from app.core import oss_routes
from app.services import occupancy as occ
from app.services import oss_client


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
# client failure policy
# --------------------------------------------------------------------------

def test_device_count_none_when_oss_unreachable(monkeypatch):
    def boom(*a, **k):
        raise oss_client.OssUnavailable("down")
    monkeypatch.setattr(oss_client, "forward", boom)
    assert oss_client.device_count(uuid.uuid4()) is None  # UNKNOWN, not 0


def test_device_count_none_on_non_200(monkeypatch):
    monkeypatch.setattr(oss_client, "forward", lambda *a, **k: (503, {"error": {}}))
    assert oss_client.device_count(uuid.uuid4()) is None


def test_device_count_reads_total_on_success(monkeypatch):
    monkeypatch.setattr(
        oss_client, "forward",
        lambda *a, **k: (200, {"items": [], "page": 1, "page_size": 1, "total": 3}),
    )
    assert oss_client.device_count(uuid.uuid4()) == 3


# --------------------------------------------------------------------------
# occupancy composition: unknown != zero
# --------------------------------------------------------------------------

def test_resolve_device_count_unknown_on_oss_failure(monkeypatch):
    monkeypatch.setattr(occ.settings, "OSS_ENABLED", True)
    monkeypatch.setattr(occ.oss_client, "device_count", lambda amenity_id: None)
    # db is unused on the OSS branch.
    assert occ._resolve_device_count(None, uuid.uuid4()) is None


def test_resolve_device_count_passes_through_oss_value(monkeypatch):
    monkeypatch.setattr(occ.settings, "OSS_ENABLED", True)
    monkeypatch.setattr(occ.oss_client, "device_count", lambda amenity_id: 2)
    assert occ._resolve_device_count(None, uuid.uuid4()) == 2


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
