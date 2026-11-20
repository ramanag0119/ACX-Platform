"""Client / credential / mapping administration on a DISPOSABLE MySQL database."""

from __future__ import annotations

import io
import json
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.integrations.admin import MAX_OVERLAP, AdminConflict, IntegrationAdmin
from app.integrations.cli import main as cli_main
from app.integrations.core.envelope import Protocol
from app.integrations.core.errors import (
    AuthenticationFailed,
    FacilityAuthorizationError,
    NotFoundInScope,
    ValidationFailed,
)
from app.integrations.processing.sql_repository import SqlIntegrationRepository
from app.integrations.security.clients import AuthenticatedClient, ClientAuthenticator
from app.integrations.security.facility import FacilityResolver
from app.integrations.security.sql_stores import SqlClientStore, SqlFacilityMappingStore

from .conftest import FACILITY_A, FACILITY_B, T0, Clock, build_stack, reset_mysql_schema


@pytest.fixture
def setup(mysql_engine):
    reset_mysql_schema(mysql_engine)
    clock = Clock()
    admin = IntegrationAdmin(mysql_engine, clock=clock)
    auth = ClientAuthenticator(SqlClientStore(mysql_engine), clock=clock)
    repo = SqlIntegrationRepository(mysql_engine)
    return mysql_engine, clock, admin, auth, repo


def audit_blob(repo):
    events = repo.list_audit(facility_scope=None, limit=200)
    return json.dumps([(e.action, e.actor_id, e.detail) for e in events])


def test_client_created_disabled_and_secret_never_stored(setup):
    _, _, admin, auth, repo = setup
    issued = admin.create_client("pms-x", ["fias"], actor="ops.1")
    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate("pms-x", issued.secret, protocol=Protocol.FIAS)
    assert exc.value.reason == "client_disabled"
    admin.set_client_enabled("pms-x", True, actor="ops.1")
    assert auth.authenticate("pms-x", issued.secret, protocol=Protocol.FIAS).code == "pms-x"
    with pytest.raises(AuthenticationFailed):
        auth.authenticate("pms-x", issued.secret, protocol=Protocol.HTNG)
    blob = audit_blob(repo)
    assert "client.created" in blob and "client.enabled" in blob and issued.secret not in blob


def test_rotation_overlap_expiry_and_revoke(setup):
    _, clock, admin, auth, repo = setup
    first = admin.create_client("pms-r", ["htng"], actor="ops")
    admin.set_client_enabled("pms-r", True, actor="ops")
    second = admin.rotate_secret("pms-r", overlap=timedelta(hours=1), actor="ops")
    assert second.previous_valid_until == T0 + timedelta(hours=1)
    for s in (first.secret, second.secret):
        assert auth.authenticate("pms-r", s, protocol=Protocol.HTNG)
    clock.advance(3601)
    with pytest.raises(AuthenticationFailed):
        auth.authenticate("pms-r", first.secret, protocol=Protocol.HTNG)
    third = admin.rotate_secret("pms-r", overlap=timedelta(hours=1), actor="ops")
    admin.revoke_previous_secret("pms-r", actor="ops")
    with pytest.raises(AuthenticationFailed):
        auth.authenticate("pms-r", second.secret, protocol=Protocol.HTNG)
    assert auth.authenticate("pms-r", third.secret, protocol=Protocol.HTNG)
    blob = audit_blob(repo)
    assert blob.count("client.secret_rotated") == 2 and "client.previous_secret_revoked" in blob
    assert not any(s.secret in blob for s in (first, second, third))


def test_rotation_without_overlap_invalidates_immediately(setup):
    _, _, admin, auth, _ = setup
    first = admin.create_client("pms-z", ["fias"], actor="ops")
    admin.set_client_enabled("pms-z", True, actor="ops")
    admin.rotate_secret("pms-z", overlap=timedelta(0), actor="ops")
    with pytest.raises(AuthenticationFailed):
        auth.authenticate("pms-z", first.secret, protocol=Protocol.FIAS)


@pytest.mark.parametrize("call,exc", [
    (lambda a: a.create_client("bad code", ["fias"], actor="o"), ValidationFailed),
    (lambda a: a.create_client("pms-q", ["smtp"], actor="o"), ValidationFailed),
    (lambda a: a.create_client("pms-q", ["test"], actor="o"), ValidationFailed),
    (lambda a: a.rotate_secret("nobody", overlap=timedelta(0), actor="o"), NotFoundInScope),
    (lambda a: a.set_client_enabled("nobody", True, actor="o"), NotFoundInScope),
])
def test_admin_validation(setup, call, exc):
    with pytest.raises(exc):
        call(setup[2])


def test_overlap_bounds_and_duplicate_client(setup):
    admin = setup[2]
    admin.create_client("pms-d", ["fias"], actor="o")
    with pytest.raises(AdminConflict):
        admin.create_client("pms-d", ["fias"], actor="o")
    with pytest.raises(ValidationFailed):
        admin.rotate_secret("pms-d", overlap=MAX_OVERLAP + timedelta(seconds=1), actor="o")
    with pytest.raises(ValidationFailed):
        admin.rotate_secret("pms-d", overlap=timedelta(seconds=-1), actor="o")


def test_mapping_lifecycle_scoped_and_audited(setup):
    engine, _, admin, _, repo = setup
    issued = admin.create_client("pms-m", ["fias"], actor="o")
    view = admin.create_mapping("pms-m", "HOTEL-M", FACILITY_A, actor="u1", facility_scope={FACILITY_A})
    assert view.enabled is False
    resolver = FacilityResolver(SqlFacilityMappingStore(engine))
    client = AuthenticatedClient(issued.client_id, "pms-m", frozenset({Protocol.FIAS}))
    with pytest.raises(FacilityAuthorizationError):
        resolver.resolve(client, "HOTEL-M")  # disabled until enabled
    admin.set_mapping_enabled(view.mapping_id, True, actor="u1", reason="go-live ok", facility_scope={FACILITY_A})
    assert resolver.resolve(client, "HOTEL-M") == FACILITY_A
    with pytest.raises(NotFoundInScope):
        admin.set_mapping_enabled(view.mapping_id, False, actor="u2", reason="x" * 10, facility_scope={FACILITY_B})
    with pytest.raises(NotFoundInScope):
        admin.create_mapping("pms-m", "HOTEL-N", FACILITY_B, actor="u1", facility_scope={FACILITY_A})
    with pytest.raises(AdminConflict):
        admin.create_mapping("pms-m", "HOTEL-M", FACILITY_A, actor="u1", facility_scope=None)
    with pytest.raises(ValidationFailed):
        admin.create_mapping("pms-m", "HOTEL-U", uuid.uuid4(), actor="u1", facility_scope=None)
    with pytest.raises(ValidationFailed):
        admin.create_mapping("pms-m", "has space", FACILITY_A, actor="u1", facility_scope=None)
    assert [m.external_property_code for m in admin.list_mappings(facility_scope={FACILITY_A})] == ["HOTEL-M"]
    assert admin.list_mappings(facility_scope={FACILITY_B}) == []
    assert admin.list_mappings(facility_scope=set()) == []
    events = repo.list_audit(facility_scope={FACILITY_A})
    assert [e.action for e in events][:2] == ["mapping.enabled", "mapping.created"]
    assert events[0].reason == "go-live ok"


def test_cli_prints_secret_once_and_errors_cleanly(setup, capsys):
    admin = setup[2]
    out = io.StringIO()
    rc = cli_main(["create-client", "--code", "pms-c", "--protocol", "fias", "--actor", "ops"], admin=admin, out=out)
    assert rc == 0 and "secret (shown once)" in out.getvalue() and "DISABLED" in out.getvalue()
    out = io.StringIO()
    rc = cli_main(["rotate-secret", "--code", "pms-c", "--overlap-hours", "2", "--actor", "ops"], admin=admin, out=out)
    assert rc == 0 and "previous secret valid until" in out.getvalue()
    for cmd in ("enable-client", "disable-client", "revoke-previous-secret"):
        assert cli_main([cmd, "--code", "pms-c", "--actor", "ops"], admin=admin, out=io.StringIO()) == 0
    assert cli_main(["enable-client", "--code", "nobody", "--actor", "ops"], admin=admin) == 2
    assert "not_found" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli_main(["create-client", "--code", "x"], admin=admin)  # --actor and --protocol required


def test_mapping_api_scoped_rbac_and_audit(setup):
    from app.integrations.config import IntegrationSettings
    from app.integrations.domain.approvals import LiveWriteGate
    from app.integrations.runtime import IntegrationRuntime, set_runtime
    from app.main import create_app

    from .test_api import user

    _, _, admin, _, repo = setup
    admin.create_client("pms-api", ["fias"], actor="o")
    stack = build_stack(repo)
    set_runtime(IntegrationRuntime(settings=IntegrationSettings(), gateway=stack.gateway, repository=repo,
                                   metrics=stack.metrics, live_write_gate=LiveWriteGate(enabled_flag=False),
                                   admin=admin))
    app = create_app()
    current = {"user": user(facilities=[FACILITY_A], write=False)}
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    url = "/api/v1/integrations/mappings"
    try:
        with TestClient(app) as c:
            body = {"client_code": "pms-api", "external_property_code": "H-API", "facility_id": str(FACILITY_A)}
            assert c.post(url, json=body).status_code == 403
            current["user"] = user(facilities=[FACILITY_A], write=True)
            r = c.post(url, json=body)
            assert r.status_code == 201 and r.json()["enabled"] is False
            mid = r.json()["mapping_id"]
            assert c.post(url, json=body).status_code == 409
            other = {**body, "external_property_code": "H-B", "facility_id": str(FACILITY_B)}
            assert c.post(url, json=other).status_code == 404
            assert c.patch(f"{url}/{mid}", json={"enabled": True}).status_code == 422
            r = c.patch(f"{url}/{mid}", json={"enabled": True, "reason": "vendor go-live"})
            assert r.status_code == 200 and r.json()["enabled"] is True
            assert [m["external_property_code"] for m in c.get(url).json()] == ["H-API"]
            current["user"] = user(facilities=[FACILITY_B], write=True)
            assert c.get(url).json() == []
            assert c.patch(f"{url}/{mid}", json={"enabled": False, "reason": "not mine to change"}).status_code == 404
    finally:
        set_runtime(None)
    actions = [e.action for e in repo.list_audit(facility_scope={FACILITY_A})]
    assert actions[:2] == ["mapping.enabled", "mapping.created"]
