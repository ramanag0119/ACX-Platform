"""Phase C alert/incident adapter tests (read-only integration)."""

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
def test_alert_types_and_alerts_lists():
    # Supported resources return a valid page (empty is correct, not an error).
    for path in ("/alert-types", "/alerts"):
        b = client.get(path).json()
        assert "items" in b and "total" in b and b["total"] >= 0


@requires_db
def test_unsupported_resources_return_503_not_fake_data():
    # No device_incident / value-alert tables, no stable alert id -> explicit 503.
    assert client.get("/alerts/1").status_code == 503
    assert client.get("/alerts/1/incidents").status_code == 503
    assert client.get("/incidents").status_code == 503
    assert client.get("/value-alerts").status_code == 503


@requires_db
def test_missing_alert_type_404():
    assert client.get("/alert-types/999999").status_code == 404
