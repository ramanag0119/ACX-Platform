"""OSS service scaffold tests — run WITHOUT the OSS database.

They prove the service boots, liveness works, the contract models import, and
data routes degrade cleanly (503) before the OSS schema is mapped. Real adapter
tests come after step-1 schema discovery.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_liveness_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "HMS OSS Service"


def test_db_health_reflects_configuration():
    from app.core.config import settings
    r = client.get("/health/db")
    if settings.is_db_configured:
        assert r.status_code == 200
        assert r.json()["database"]
    else:
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "oss_not_configured"


def test_device_types_route_behaviour():
    from app.core.config import settings
    r = client.get("/device-types")
    if settings.is_db_configured:
        # Phase A implemented -> real data.
        assert r.status_code == 200
        assert "items" in r.json()
    else:
        # No DB -> clean 503 (not configured), never a 500.
        assert r.status_code == 503
        assert r.json()["error"]["code"] in {"oss_not_configured", "oss_adapter_not_mapped"}


def test_openapi_exposes_the_oss_surface():
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/device-types", "/devices", "/device-params", "/device-stats",
              "/device-current-stats", "/other-device-readings", "/alert-types",
              "/alerts", "/energy-stats"):
        assert p in paths, f"missing OSS path {p}"
    # HMS/BSS data must NOT be here: mixed KPIs, and incidents / value alerts,
    # which OSS has no table for.
    for p in ("/daily-data-points", "/incidents", "/value-alerts"):
        assert p not in paths, f"BSS path {p} served by OSS"


def test_contract_schemas_import():
    from app.schemas.device import DeviceRead  # noqa: F401
    from app.schemas.telemetry import DeviceStatRead  # noqa: F401
    from app.schemas.alert import ValueAlertRead  # noqa: F401
    from app.schemas.energy import EnergyStatRead  # noqa: F401


def test_service_token_gate(monkeypatch):
    """When OSS_SERVICE_TOKEN is set, data routes require the header (401),
    and the token check runs BEFORE the DB (a correct token still 503s on the
    unconfigured DB rather than 401)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "OSS_SERVICE_TOKEN", "s3cret")

    # Missing/wrong token -> 401, regardless of DB/adapter state.
    assert client.get("/device-types").status_code == 401
    assert client.get("/device-types", headers={"X-OSS-Service-Token": "nope"}).status_code == 401

    # Correct token passes the gate (NOT 401); the route then runs normally.
    ok = client.get("/device-types", headers={"X-OSS-Service-Token": "s3cret"})
    assert ok.status_code != 401


def test_health_never_token_gated(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OSS_SERVICE_TOKEN", "s3cret")
    assert client.get("/health").status_code == 200  # probes must not need the token


def test_domain_process_serves_only_its_routes():
    from app.api.router import build_api_router
    paths = {r.path for r in build_api_router(["alert"]).routes}
    assert any(p.startswith("/alerts") for p in paths)
    assert not any(p.startswith("/devices") or p.startswith("/energy-stats") for p in paths)


def test_unknown_domain_fails_fast():
    import pytest
    from app.api.router import build_api_router
    with pytest.raises(ValueError):
        build_api_router(["devices"])


def test_refuses_to_start_without_a_token_outside_development(monkeypatch):
    import pytest
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "OSS_SERVICE_TOKEN", None)
    with pytest.raises(RuntimeError, match="OSS_SERVICE_TOKEN"):
        create_app()

    monkeypatch.setattr(settings, "OSS_SERVICE_TOKEN", "s3cret")
    create_app()
