"""The service-token guard still works when a token IS configured.

`tests/conftest.py` blanks `OSS_SERVICE_TOKEN` for the suite so the adapter
tests can reach their routes. That convenience must not be able to hide a
regression in the guard itself, so these tests build an app with a token
explicitly configured and assert both halves of the contract:

    no / wrong header -> 401        correct header -> not 401
    /health          -> never gated (probes must work regardless)

Nothing here reads or writes `oss-service/.env`; the token is injected into a
`Settings` instance for the duration of a single test.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import security
from app.api.health import router as health_router

TOKEN = "unit-test-token-not-a-real-secret"


@pytest.fixture
def gated_client(monkeypatch) -> TestClient:
    """An app whose data route carries the real `require_service_token` gate."""
    monkeypatch.setattr(security.settings, "OSS_SERVICE_TOKEN", TOKEN, raising=False)

    app = FastAPI()
    app.include_router(health_router)  # ungated, as in app/main.py

    @app.get("/guarded", dependencies=[Depends(security.require_service_token)])
    def _guarded():
        return {"ok": True}

    return TestClient(app)


def test_missing_token_is_rejected(gated_client):
    assert gated_client.get("/guarded").status_code == 401


def test_wrong_token_is_rejected(gated_client):
    r = gated_client.get("/guarded", headers={"X-OSS-Service-Token": "wrong"})
    assert r.status_code == 401


def test_correct_token_is_accepted(gated_client):
    r = gated_client.get("/guarded", headers={"X-OSS-Service-Token": TOKEN})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_health_is_never_gated(gated_client):
    """Liveness must answer without a token or orchestrator probes break."""
    assert gated_client.get("/health").status_code == 200


def test_suite_runs_with_the_guard_disabled():
    """Document the conftest contract: the suite itself has no token set."""
    from app.core.config import settings

    assert not settings.OSS_SERVICE_TOKEN, (
        "tests/conftest.py must blank OSS_SERVICE_TOKEN before app import"
    )
