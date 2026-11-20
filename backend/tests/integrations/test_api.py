"""Integration API: authorization, facility scoping, redrive, HTNG inbound, startup.

Uses the real app factory and the real `require_permission` dependency chain;
only `get_current_user` (which needs the seeded HMS database) is overridden,
and the integration runtime is an in-memory one.
"""

from __future__ import annotations

import subprocess
import sys
import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.platform import Platform
from app.integrations.config import IntegrationSettings
from app.integrations.core.envelope import Direction, Protocol
from app.integrations.core.errors import PermanentFailure
from app.integrations.domain.approvals import LiveWriteGate
from app.integrations.runtime import IntegrationRuntime, set_runtime
from app.integrations.simulators.fixtures import generic_arrival_soap
from app.integrations.transport.soap import parse_soap
from app.main import create_app
from app.services.auth import AuthenticatedUser

from .conftest import CTX, FACILITY_A, build_stack, json_msg

PREFIX = "/api/v1/integrations"


def user(*, facilities, read=True, write=False):
    return AuthenticatedUser(
        id=uuid.uuid4(), user_name="op", first_name="Op", last_name=None, email=None, is_staff=1,
        role_types=["admin"], platform=Platform.HMS_WEB, facility_ids=list(facilities),
        permissions=[{"module_name": "facility_management", "read_access": int(read), "write_access": int(write)}],
    )


def env_impl():
    """Shared by the `env` fixture in conftest.py."""
    stack = build_stack()
    settings = IntegrationSettings(ENABLED=True, HTNG_INBOUND_ENABLED=True, MAX_MESSAGE_BYTES=4096)
    htng = stack.gateway.adapters.get(Protocol.HTNG, Direction.INBOUND)
    runtime = IntegrationRuntime(
        settings=settings, gateway=stack.gateway, repository=stack.repo, metrics=stack.metrics,
        live_write_gate=LiveWriteGate(enabled_flag=False), htng_adapter=htng,
        transports={"fias-link": lambda: {"state": "disconnected"}},
    )
    set_runtime(runtime)
    app = create_app()
    current = {"user": user(facilities=[FACILITY_A])}
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    with TestClient(app) as client:
        yield stack, client, current, runtime
    set_runtime(None)


def seed(stack, n=1, prop="HOTEL-A", client="pms-a"):
    ids = []
    for i in range(n):
        r = stack.gateway.receive(json_msg(f"{prop}-{i}", prop=prop, body={"room": "101", "guest_name": "Jane Roe"}),
                                  protocol=Protocol.TEST, client=stack.auth(client), context=CTX)
        ids.append(r.message_id)
    return ids


def dead_letter(stack, prop="HOTEL-A", client="pms-a"):
    stack.handlers["test.guest_arrival"].failures.append(PermanentFailure("bad"))
    (mid,) = seed(stack, prop=prop, client=client)
    stack.worker.run_once()
    return mid


# --- auth ---------------------------------------------------------------
def test_public_health_exposes_nothing(env):
    _, client, _, _ = env
    r = client.get(f"{PREFIX}/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_operator_endpoints_require_authentication():
    set_runtime(None)
    app = create_app()  # no override: real bearer dependency
    with TestClient(app) as client:
        for path in ("/readiness", "/adapters", "/messages", "/dlq", "/outbox", "/metrics", "/audit"):
            assert client.get(PREFIX + path).status_code == 401
        assert client.post(f"{PREFIX}/messages/{uuid.uuid4()}/redrive", json={"reason": "x" * 20}).status_code == 401


def test_permission_required(env):
    _, client, current, _ = env
    current["user"] = user(facilities=[FACILITY_A], read=False)
    assert client.get(f"{PREFIX}/messages").status_code == 403


# --- readiness / status ---------------------------------------------------------------
def test_readiness_reports_components_and_not_ready(env):
    _, client, _, _ = env
    r = client.get(f"{PREFIX}/readiness")
    assert r.status_code == 503  # TEST_ONLY adapters are never "ready"
    body = r.json()
    assert "no_adapter_ready" in body["reasons"]
    comps = body["components"]
    assert comps["persistence"]["status"] == "in_memory"
    assert comps["vendor_endpoints"] == "not_configured"
    assert comps["live_domain_writes"]["open"] is False
    assert comps["transports"]["fias-link"]["state"] == "disconnected"


def test_adapter_status_lists_blocking_decisions(env):
    _, client, _, _ = env
    rows = {a["protocol"]: a for a in client.get(f"{PREFIX}/adapters").json()}
    assert rows["fias"]["readiness"] == "test_only" and rows["fias"]["blocking_decisions"] == ["HF-11"]


# --- messages / scoping ---------------------------------------------------------------
def test_messages_are_facility_scoped_and_metadata_only(env):
    stack, client, current, _ = env
    seed(stack, 2)
    seed(stack, 1, prop="HOTEL-B", client="pms-b")
    rows = client.get(f"{PREFIX}/messages").json()
    assert len(rows) == 2 and {r["facility_id"] for r in rows} == {str(FACILITY_A)}
    assert "body" not in rows[0] and "Jane" not in str(rows)
    current["user"] = user(facilities=[])
    assert client.get(f"{PREFIX}/messages").json() == []


def test_message_detail_is_masked_and_cross_facility_is_404(env):
    stack, client, current, _ = env
    (mid,) = seed(stack)
    (other,) = seed(stack, prop="HOTEL-B", client="pms-b")
    detail = client.get(f"{PREFIX}/messages/{mid}").json()
    assert detail["body_masked"]["guest_name"] == "***" and detail["body_masked"]["room"] == "101"
    assert client.get(f"{PREFIX}/messages/{other}").status_code == 404
    assert client.get(f"{PREFIX}/messages/{uuid.uuid4()}").status_code == 404


def test_status_filter_validated(env):
    _, client, _, _ = env
    assert client.get(f"{PREFIX}/messages?status=BOGUS").status_code == 422
    assert client.get(f"{PREFIX}/messages?limit=1000").status_code == 422


# --- DLQ / redrive ---------------------------------------------------------------
def test_redrive_requires_write_reason_and_scope(env):
    stack, client, current, _ = env
    mid = dead_letter(stack)
    other = dead_letter(stack, prop="HOTEL-B", client="pms-b")
    assert [r["message_id"] for r in client.get(f"{PREFIX}/dlq").json()] == [str(mid)]

    url = f"{PREFIX}/messages/{mid}/redrive"
    assert client.post(url, json={"reason": "vendor fixed the record"}).status_code == 403  # read-only user
    current["user"] = user(facilities=[FACILITY_A], write=True)
    assert client.post(url, json={}).status_code == 422
    assert client.post(url, json={"reason": "short"}).status_code == 422
    assert client.post(f"{PREFIX}/messages/{other}/redrive", json={"reason": "vendor fixed the record"}).status_code == 404

    r = client.post(url, json={"reason": "vendor fixed the record"})
    assert r.status_code == 200 and r.json()["status"] == "PENDING"
    assert client.post(url, json={"reason": "vendor fixed the record"}).status_code == 409
    audit = client.get(f"{PREFIX}/audit").json()
    assert audit[0]["action"] == "message.redrive" and audit[0]["reason"] == "vendor fixed the record"
    assert audit[0]["actor_id"] == str(current["user"].id)


def test_outbox_and_metrics(env):
    stack, client, _, _ = env
    seed(stack)
    stack.worker.run_once()
    rows = client.get(f"{PREFIX}/outbox").json()
    assert len(rows) == 1 and rows[0]["status"] == "PENDING" and "body" not in rows[0]
    assert client.get(f"{PREFIX}/outbox?status=SENT").json() == []
    m = client.get(f"{PREFIX}/metrics").json()
    assert m["messages_by_status"] == {"SUCCEEDED": 1}
    assert any(k.startswith("intake_accepted") for k in m["counters"])


# --- HTNG inbound ---------------------------------------------------------------
def soap(ref="r1", prop="HOTEL-A"):
    return generic_arrival_soap(message_ref=ref, property_code=prop, room="101", stay_ref="s1", guest_name="Jane")


def hdr(stack, code="pms-a"):
    return {"X-Integration-Client": code, "X-Integration-Secret": stack.secrets[code],
            "Content-Type": "text/xml; charset=utf-8"}


def test_htng_inbound_accepts_and_acknowledges_with_profile_response(env):
    stack, client, _, _ = env
    r = client.post(f"{PREFIX}/htng/inbound", content=soap(), headers=hdr(stack))
    assert r.status_code == 200 and r.headers["X-Correlation-ID"]
    ack = parse_soap(r.content).body
    assert ack[0].text == "accepted"
    dup = client.post(f"{PREFIX}/htng/inbound", content=soap(), headers=hdr(stack))
    assert parse_soap(dup.content).body[0].text == "duplicate"
    assert len(stack.repo.list_messages(facility_scope=None)) == 1


def test_htng_inbound_auth_failures(env):
    stack, client, _, _ = env
    assert client.post(f"{PREFIX}/htng/inbound", content=soap()).status_code == 401
    bad = {**hdr(stack), "X-Integration-Secret": "x" * 40}
    r = client.post(f"{PREFIX}/htng/inbound", content=soap(), headers=bad)
    assert r.status_code == 401 and b"Authentication failed" in r.content
    assert client.post(f"{PREFIX}/htng/inbound", content=soap(), headers=hdr(stack, "pms-off")).status_code == 401


def test_htng_inbound_rejections_map_to_faults(env):
    stack, client, _, _ = env
    assert client.post(f"{PREFIX}/htng/inbound", content=soap(prop="HOTEL-B"), headers=hdr(stack)).status_code == 403
    xxe = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    r = client.post(f"{PREFIX}/htng/inbound", content=xxe, headers=hdr(stack))
    assert r.status_code == 400 and b"passwd" not in r.content
    assert client.post(f"{PREFIX}/htng/inbound", content=b"x" * 5000, headers=hdr(stack)).status_code == 413
    assert stack.repo.list_messages(facility_scope=None) == []


def test_htng_inbound_disabled_by_default(env):
    stack, client, _, runtime = env
    runtime.settings = IntegrationSettings()  # all defaults: disabled
    r = client.post(f"{PREFIX}/htng/inbound", content=soap(), headers=hdr(stack))
    assert r.status_code == 503 and stack.repo.list_messages(facility_scope=None) == []


# --- startup ---------------------------------------------------------------
def test_app_startup_does_not_import_simulators_or_build_runtime():
    code = (
        "import sys\n"
        "from fastapi.testclient import TestClient\n"
        "import app.main as m\n"
        "import app.integrations.runtime as rt\n"
        "with TestClient(m.app) as c:\n"
        "    assert c.get('/health').status_code == 200\n"
        "    assert c.get('/api/v1/integrations/health').status_code == 200\n"
        "assert not any(k.startswith('app.integrations.simulators') for k in sys.modules), 'simulator imported'\n"
        "assert rt._runtime is None, 'runtime built at startup'\n"
        "print('OK')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)  # noqa: S603 - fixed code
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().endswith("OK")


def test_integration_routes_mounted_without_breaking_existing_routes():
    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/health" in paths and "/api/v1/health/db" in paths
    assert f"{PREFIX}/messages/{{message_id}}/redrive" in paths
