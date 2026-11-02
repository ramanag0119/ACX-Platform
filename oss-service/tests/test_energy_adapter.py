"""Phase D energy adapter tests (read-only integration)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app

client = TestClient(create_app())
requires_db = pytest.mark.skipif(
    not settings.is_db_configured, reason="OSS database not configured"
)


@requires_db
def test_energy_unsupported_pending_calculation():
    # active_energy is a cumulative counter; hourly consumption needs a
    # confirmed rule -> explicit 503, never fabricated numbers.
    r = client.get("/energy-stats")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "oss_adapter_not_mapped"
    assert client.get("/energy-stats/summary").status_code == 503
