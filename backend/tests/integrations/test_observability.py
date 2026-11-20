"""Read-only observability API (docs/HTNG_FIAS_OBSERVABILITY_API_DESIGN.md).

Repository-level tests run on BOTH backends (in-memory and the disposable
MySQL behind INTEGRATION_TEST_MYSQL_URL). All data is synthetic; the
"approved" decision register below exists only inside these tests.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from app.api.deps import get_current_user
from app.integrations import observability as obs
from app.integrations.adapters.base import AdapterReadiness, AdapterStatus
from app.integrations.config import IntegrationSettings
from app.integrations.core.envelope import CanonicalEnvelope, Direction, Protocol
from app.integrations.core.errors import PermanentFailure, TransientFailure
from app.integrations.core.hashing import payload_hash
from app.integrations.domain.approvals import (
    DECISIONS,
    REQUIRED_FOR_LIVE_WRITES,
    Decision,
    DecisionStatus,
    LiveWriteGate,
)
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.activity import MessageQuery
from app.integrations.processing.repository import InMemoryIntegrationRepository, OutboxDraft
from app.integrations.runtime import IntegrationRuntime

from .conftest import CLIENT_A, CLIENT_B, FACILITY_A, FACILITY_B, build_stack
from .test_api import PREFIX, user

T = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
OBS = f"{PREFIX}/observability"
GUEST = {"room": "101", "guest_name": "Jane Roe", "email": "jane.roe@example.invalid", "card": "4111111111111111"}


# ------------------------------------------------------------------ seeding
def put(repo, *, protocol, key, at, facility=FACILITY_A, client=CLIENT_A, outcome="pending",
        code="hms_business_rule", retries=0, emit=None):
    """Accept one synthetic inbound message and drive it to `outcome`
    (pending | succeeded | dead_letter | retry_wait) with `retries` failed
    attempts first. Seed processed messages in time order, pending ones last."""
    body = {**GUEST, "key": key}
    env = CanonicalEnvelope(
        idempotency_key=key, correlation_id=f"corr-{key}", facility_id=facility, client_id=client,
        protocol=protocol, message_type="test.guest_arrival", direction=Direction.INBOUND,
        schema_version="t/1", received_at=at, payload_hash=payload_hash(body), body=body,
    )
    repo.accept(env, wire_bytes=None, max_attempts=10)
    if outcome == "pending":
        return env.message_id
    now = at
    for _ in range(retries):
        now += timedelta(seconds=1)
        (claim,) = repo.claim(worker_id="w", now=now, lease_seconds=30, limit=1)
        assert claim.message.message_id == env.message_id
        repo.record_failure(claim, now=now, error=TransientFailure("t", code="hms_unavailable"),
                            retry_at=now + timedelta(seconds=1))
        now += timedelta(seconds=1)
    now += timedelta(seconds=1)
    (claim,) = repo.claim(worker_id="w", now=now, lease_seconds=30, limit=1)
    assert claim.message.message_id == env.message_id
    if outcome == "succeeded":
        with repo.completion(claim, clock=lambda: now) as ctx:
            if emit:
                ctx.add_outbox(OutboxDraft(protocol, "test.receipt", {"ok": True}))
    elif outcome == "dead_letter":
        repo.record_failure(claim, now=now, error=PermanentFailure("Jane Roe failed", code=code), retry_at=None)
    elif outcome == "retry_wait":
        repo.record_failure(claim, now=now, error=TransientFailure("t", code=code),
                            retry_at=now + timedelta(days=365))
    return env.message_id


def seed_world(repo):
    """HTNG: 2 succeeded (one retried twice, one with outbound), 1 dead letter, 1 pending.
    FIAS: 1 succeeded, 1 retry_wait, 1 dead letter in FACILITY_B, 1 pending."""
    ids = {}
    ids["h_ok1"] = put(repo, protocol=Protocol.HTNG, key="h1", at=T, outcome="succeeded", retries=2)
    ids["h_ok2"] = put(repo, protocol=Protocol.HTNG, key="h2", at=T + timedelta(minutes=1), outcome="succeeded",
                       emit=True)
    ids["h_dlq"] = put(repo, protocol=Protocol.HTNG, key="h3", at=T + timedelta(minutes=2), outcome="dead_letter")
    ids["f_ok"] = put(repo, protocol=Protocol.FIAS, key="f1", at=T + timedelta(minutes=3), outcome="succeeded")
    ids["f_rw"] = put(repo, protocol=Protocol.FIAS, key="f2", at=T + timedelta(minutes=4), outcome="retry_wait",
                      code="hms_unavailable")
    ids["f_dlq_b"] = put(repo, protocol=Protocol.FIAS, key="f3", at=T + timedelta(minutes=5), outcome="dead_letter",
                         facility=FACILITY_B, client=CLIENT_B)
    ids["h_pend"] = put(repo, protocol=Protocol.HTNG, key="h4", at=T + timedelta(minutes=6))
    ids["f_pend"] = put(repo, protocol=Protocol.FIAS, key="f4", at=T + timedelta(minutes=7))
    return ids


def runtime_for(repo, **kw) -> IntegrationRuntime:
    stack = build_stack()
    defaults = dict(
        settings=IntegrationSettings(ENABLED=False, HTNG_INBOUND_ENABLED=False),
        gateway=stack.gateway, repository=repo, metrics=IntegrationMetrics(),
        live_write_gate=LiveWriteGate(enabled_flag=False),
    )
    defaults.update(kw)
    return IntegrationRuntime(**defaults)


# --------------------------------------------------- activity (both backends)
def test_protocol_activity_counts_are_per_protocol_and_facility_scoped(repo):
    seed_world(repo)
    act = repo.protocol_activity(facility_scope={FACILITY_A})
    h, f = act["htng"], act["fias"]
    assert h.inbound == {"SUCCEEDED": 2, "DEAD_LETTER": 1, "PENDING": 1}
    assert f.inbound == {"SUCCEEDED": 1, "RETRY_WAIT": 1, "PENDING": 1}  # FACILITY_B dead letter excluded
    assert h.outbound == {"PENDING": 1} and f.outbound == {}
    assert (h.retried_messages, h.extra_attempts) == (1, 2)
    assert h.latest_failure["error_code"] == "hms_business_rule" and h.latest_failure["status"] == "DEAD_LETTER"
    assert f.latest_failure["status"] == "RETRY_WAIT" and f.latest_failure["dead_lettered_at"] is None
    assert h.oldest_pending_at == T + timedelta(minutes=6)
    assert h.last_succeeded_at is not None and h.last_succeeded_at > T
    # Facility B sees only its own dead letter.
    only_b = repo.protocol_activity(facility_scope={FACILITY_B})
    assert set(only_b) == {"fias"} and only_b["fias"].inbound == {"DEAD_LETTER": 1}
    assert repo.protocol_activity(facility_scope=set()) == {}


def test_search_is_filtered_ordered_paginated_and_scoped(repo):
    ids = seed_world(repo)
    window = dict(received_from=T - timedelta(hours=1), received_to=T + timedelta(hours=1))
    rows, total = repo.search_messages(MessageQuery(**window, page_size=3), facility_scope={FACILITY_A})
    assert total == 7
    keys = [r.received_at for r in rows]
    assert keys == sorted(keys, reverse=True)
    pages = []
    for page in (1, 2, 3):
        got, t2 = repo.search_messages(MessageQuery(**window, page=page, page_size=3), facility_scope={FACILITY_A})
        assert t2 == 7
        pages += [r.message_id for r in got]
    assert len(pages) == 7 and len(set(pages)) == 7 and ids["f_dlq_b"] not in pages
    htng, total = repo.search_messages(MessageQuery(**window, protocols=frozenset({"htng"})),
                                       facility_scope={FACILITY_A})
    assert total == 4 and {str(r.protocol) for r in htng} == {"htng"}
    dlq, total = repo.search_messages(MessageQuery(**window, statuses=frozenset({"DEAD_LETTER"})),
                                      facility_scope=None)
    assert {r.message_id for r in dlq} == {ids["h_dlq"], ids["f_dlq_b"]}
    # A requested facility outside the scope yields nothing (the API answers 403 first).
    none, total = repo.search_messages(MessageQuery(**window, facility_ids=frozenset({FACILITY_B})),
                                       facility_scope={FACILITY_A})
    assert none == [] and total == 0
    narrow, total = repo.search_messages(
        MessageQuery(received_from=T + timedelta(minutes=2), received_to=T + timedelta(minutes=4)),
        facility_scope={FACILITY_A})
    assert total == 3


def test_message_query_bounds():
    with pytest.raises(ValueError):
        MessageQuery(received_from=T, received_to=T, page_size=101)
    with pytest.raises(ValueError):
        MessageQuery(received_from=T, received_to=T, page=10_000, page_size=100)
    with pytest.raises(ValueError):
        MessageQuery(received_from=T.replace(tzinfo=None), received_to=T)
    with pytest.raises(ValueError):
        MessageQuery(received_from=T, received_to=T - timedelta(seconds=1))


# ----------------------------------------------------------------- overview
def test_overview_has_independent_protocol_entries_with_measured_counts(repo):
    seed_world(repo)
    view = obs.build_overview(runtime_for(repo), facility_scope={FACILITY_A}, now=T + timedelta(minutes=10))
    h, f = view["protocols"]["htng"], view["protocols"]["fias"]
    assert h["protocol"] == "htng" and f["protocol"] == "fias"
    assert h["messages"]["status"] == "measured" and h["messages"]["basis"] == "retained_rows"
    assert h["messages"]["inbound"]["succeeded"] == 2 and h["messages"]["inbound"]["failed_dead_letter"] == 1
    assert h["messages"]["outbound"]["pending"] == 1
    assert f["messages"]["inbound"]["retry_wait"] == 1 and f["messages"]["inbound"]["failed_dead_letter"] == 0
    assert h["last_error"]["error"] == {"code": "hms_business_rule", "category": "permanent"}
    shared = view["overview"]["messages"]
    assert (shared["processed"], shared["pending"], shared["failed_dead_letter"]) == (3, 3, 1)
    assert shared["last_successful_exchange_at"] is not None


def test_processing_classification_from_durable_backlog():
    repo = InMemoryIntegrationRepository()
    rt = runtime_for(repo)
    assert obs.build_overview(rt, facility_scope=None, now=T)["protocols"]["fias"]["processing"]["status"] == "idle"
    put(repo, protocol=Protocol.FIAS, key="p", at=T)
    within = obs.build_overview(rt, facility_scope=None, now=T + timedelta(seconds=60), stall_seconds=900)
    assert within["protocols"]["fias"]["processing"]["status"] == "backlog_within_threshold"
    assert within["protocols"]["fias"]["processing"]["oldest_pending_age_seconds"] == 60.0
    stalled = obs.build_overview(rt, facility_scope=None, now=T + timedelta(hours=1), stall_seconds=900)
    assert stalled["protocols"]["fias"]["processing"]["status"] == "backlog_stalled"
    assert stalled["protocols"]["htng"]["processing"]["status"] == "idle"


class _DownRepository(InMemoryIntegrationRepository):
    def protocol_activity(self, *, facility_scope):
        raise OperationalError("SELECT 1", {}, Exception("db down"))


def test_missing_telemetry_is_null_never_zero():
    view = obs.build_overview(runtime_for(_DownRepository()), facility_scope={FACILITY_A}, now=T)
    for p in ("htng", "fias"):
        e = view["protocols"][p]
        assert e["messages"]["status"] == "not_available"
        assert e["messages"]["inbound"] is None and e["messages"]["outbound"] is None
        assert e["processing"]["status"] == "not_available"
        assert e["processing"]["oldest_pending_age_seconds"] is None
        assert e["authentication"]["status"] == "not_available" and e["authentication"]["enabled_clients"] is None
        assert e["last_error"] is None
        assert e["processing"]["worker_heartbeat"]["observed"] is False
    shared = view["overview"]["messages"]
    assert shared["status"] == "not_available"
    assert all(shared[k] is None for k in ("processed", "pending", "failed_dead_letter"))
    fias = view["protocols"]["fias"]
    assert fias["transport"]["status"] == "not_observable" and fias["transport"]["active_connections"] is None
    assert fias["intake_rejections"]["status"] == "not_observable"
    assert fias["intake_rejections"]["rejected_by_category"] is None


def test_fias_link_status_only_from_explicitly_tagged_transports():
    repo = InMemoryIntegrationRepository()
    probes = {
        "fias-1": lambda: {"state": "connected", "connections": 3, "last_error_code": "Peer said: Jane Roe"},
        "fias-2": lambda: {"state": "disconnected", "connections": 1},
    }
    untagged = obs.build_overview(runtime_for(repo, transports=probes), facility_scope=None, now=T)
    assert untagged["protocols"]["fias"]["transport"]["status"] == "not_observable"
    tagged = obs.build_overview(runtime_for(repo, transports=probes,
                                            transport_protocols={"fias-1": "fias", "fias-2": "fias"}),
                                facility_scope=None, now=T)
    t = tagged["protocols"]["fias"]["transport"]
    assert t["status"] == "degraded" and t["active_connections"] == 1
    assert t["links"][0]["last_error_code"] == "redacted"  # free text never passes
    assert "Jane" not in json.dumps(tagged)

    def broken():
        raise RuntimeError("boom")

    t = obs.build_overview(runtime_for(repo, transports={"fias-1": broken}, transport_protocols={"fias-1": "fias"}),
                           facility_scope=None, now=T)["protocols"]["fias"]["transport"]
    assert t["status"] == "disconnected" and t["links"][0]["state"] == "probe_failed"


def test_worker_heartbeat_is_reported_with_its_scope():
    rt = runtime_for(InMemoryIntegrationRepository())
    rt.metrics.heartbeat("inbound_worker", T)
    hb = obs.build_overview(rt, facility_scope=None, now=T)["protocols"]["htng"]["processing"]["worker_heartbeat"]
    assert hb == {"scope": "this_api_process", "observed": True,
                  "last": {"inbound_worker": T.isoformat(), "outbox_relay": None, "integration_service": None}}


def test_safe_identifier():
    assert obs.safe_identifier("hms_business_rule") == "hms_business_rule"
    assert obs.safe_identifier("transient") == "transient"
    for bad in ("Jane Roe", "x" * 80, "password=hunter2", "UPPER", "a b", "<x>"):
        assert obs.safe_identifier(bad) == "redacted"
    assert obs.safe_identifier(None) is None


# ---------------------------------------------------------------- readiness
def _approved_register(*, without_evidence: str | None = None) -> dict[str, Decision]:
    ids = set(obs.BUSINESS_DECISIONS) | set(obs.DBA_DECISIONS) | set(REQUIRED_FOR_LIVE_WRITES)
    for v in obs.VENDOR_DECISIONS.values():
        ids |= set(v)
    return {i: Decision(i, "TEST-ONLY", DecisionStatus.APPROVED,
                        None if i == without_evidence else "TEST-ONLY evidence reference")
            for i in ids}


def _all_green_runtime(register):
    statuses = [
        AdapterStatus(Protocol.HTNG, AdapterReadiness.READY, "verified", ("a",), ("b",)),
        AdapterStatus(Protocol.FIAS, AdapterReadiness.READY, "verified", ("a",), ()),
    ]
    return SimpleNamespace(
        settings=IntegrationSettings(ENABLED=True, HTNG_INBOUND_ENABLED=True, LIVE_DOMAIN_WRITES=True,
                                     ACTOR_USER_ID=str(uuid.uuid4())),
        gateway=SimpleNamespace(adapters=SimpleNamespace(statuses=lambda: statuses)),
        repository=InMemoryIntegrationRepository(), metrics=IntegrationMetrics(),
        live_write_gate=LiveWriteGate(enabled_flag=True, register=register),
        htng_adapter=object(), transports={}, transport_protocols={},
        persistence_probe=lambda: {"integration_inbound_messages": True},
        admin=SimpleNamespace(auth_coverage=lambda **_: {
            "htng": {"enabled_clients": 1, "enabled_mappings": 1},
            "fias": {"enabled_clients": 1, "enabled_mappings": 1}}),
    )


def test_real_register_is_never_production_ready_and_keeps_dimensions_separate(repo):
    assert not any(d.status is DecisionStatus.APPROVED for d in DECISIONS.values())
    seed_world(repo)
    view = obs.build_overview(runtime_for(repo), facility_scope={FACILITY_A}, now=T,
                              certification={"htng": "passed", "fias": "passed"})
    for p, vendor_ids in obs.VENDOR_DECISIONS.items():
        r = view["protocols"][p]["readiness"]
        assert set(r) == {"transport", "authentication", "processing", "synthetic_certification",
                          "vendor_validation", "business_approval", "dba_schema_approval",
                          "production_readiness"}
        assert r["synthetic_certification"]["status"] == "passed"
        assert r["vendor_validation"]["status"] == "pending"  # synthetic PASS does not validate a vendor
        assert set(vendor_ids) <= set(r["vendor_validation"]["pending_decisions"])
        assert r["business_approval"]["status"] == "pending" and r["dba_schema_approval"]["status"] == "pending"
        assert r["production_readiness"]["status"] == "not_ready"
        assert "vendor_validation_pending" in r["production_readiness"]["reasons"]
    assert view["overview"]["readiness_classification"] == "vendor_validation_pending"


def test_production_ready_only_when_everything_is_explicitly_satisfied():
    register = _approved_register()
    green = obs.build_overview(_all_green_runtime(register), facility_scope=None, now=T, register=register,
                               certification={"htng": "passed", "fias": "passed"})
    assert {p: e["readiness"]["production_readiness"]["status"] for p, e in green["protocols"].items()} == {
        "htng": "ready", "fias": "ready"}
    assert green["overview"]["readiness_classification"] == "production_ready"

    # No certification result reported -> not ready.
    no_cert = obs.build_overview(_all_green_runtime(register), facility_scope=None, now=T, register=register)
    assert no_cert["overview"]["readiness_classification"] != "production_ready"
    assert no_cert["protocols"]["htng"]["readiness"]["synthetic_certification"]["status"] == "not_reported"

    # One vendor decision "approved" without evidence -> that protocol stays pending.
    weak = _approved_register(without_evidence="HF-11")
    view = obs.build_overview(_all_green_runtime(weak), facility_scope=None, now=T, register=weak,
                              certification={"htng": "passed", "fias": "passed"})
    fias = view["protocols"]["fias"]["readiness"]
    assert fias["vendor_validation"]["status"] == "pending" and "HF-11" in fias["vendor_validation"]["pending_decisions"]
    assert fias["production_readiness"]["status"] == "not_ready"
    assert view["protocols"]["htng"]["readiness"]["production_readiness"]["status"] == "ready"
    assert view["overview"]["readiness_classification"] == "partially_ready"

    # A TEST_ONLY adapter never counts as vendor-validated, whatever the register says.
    rt = _all_green_runtime(register)
    rt.gateway = SimpleNamespace(adapters=SimpleNamespace(statuses=lambda: [
        AdapterStatus(Protocol.HTNG, AdapterReadiness.TEST_ONLY, "synthetic", ("a",), ()),
        AdapterStatus(Protocol.FIAS, AdapterReadiness.READY, "verified", ("a",), ())]))
    view = obs.build_overview(rt, facility_scope=None, now=T, register=register,
                              certification={"htng": "passed", "fias": "passed"})
    assert view["protocols"]["htng"]["readiness"]["vendor_validation"]["status"] == "pending"


# ---------------------------------------------------------------------- API
def test_observability_endpoints_require_authentication_and_permission(env):
    _, client, current, _ = env
    current["user"] = user(facilities=[FACILITY_A], read=False)
    for path in ("/overview", "/messages", "/dlq"):
        assert client.get(OBS + path).status_code == 403
    client.app.dependency_overrides.pop(get_current_user)
    for path in ("/overview", "/messages", "/dlq"):
        assert client.get(OBS + path).status_code == 401


def test_endpoints_are_read_only(env):
    stack, client, current, _ = env
    seed_world(stack.repo)
    current["user"] = user(facilities=[FACILITY_A, FACILITY_B], write=True)

    def snapshot():
        msgs = sorted((str(m.message_id), str(m.status), m.attempt_count)
                      for m in stack.repo.list_messages(facility_scope=None, limit=1000))
        return (msgs, len(stack.repo.list_audit(facility_scope=None, limit=1000)),
                len(stack.repo.list_outbox(facility_scope=None, limit=1000)), stack.metrics.snapshot()["counters"])

    before = snapshot()
    win = {"received_from": (T - timedelta(hours=1)).isoformat(), "received_to": (T + timedelta(hours=1)).isoformat()}
    assert client.get(f"{OBS}/overview").status_code == 200
    assert client.get(f"{OBS}/messages", params=win).status_code == 200
    assert client.get(f"{OBS}/dlq").status_code == 200
    assert snapshot() == before
    for path in ("/overview", "/messages", "/dlq"):
        assert client.post(OBS + path, json={}).status_code == 405
        assert client.delete(OBS + path).status_code == 405


def test_overview_api_is_facility_isolated(env):
    stack, client, current, _ = env
    seed_world(stack.repo)
    current["user"] = user(facilities=[FACILITY_A])
    a = client.get(f"{OBS}/overview").json()
    assert a["protocols"]["fias"]["messages"]["inbound"]["failed_dead_letter"] == 0
    assert a["protocols"]["fias"]["last_error"]["status"] == "RETRY_WAIT"
    current["user"] = user(facilities=[FACILITY_B])
    b = client.get(f"{OBS}/overview").json()
    assert b["protocols"]["fias"]["messages"]["inbound"] == {
        "total": 1, "by_status": {"DEAD_LETTER": 1}, "pending": 0, "succeeded": 0, "retry_wait": 0,
        "failed_dead_letter": 1}
    assert b["protocols"]["htng"]["messages"]["inbound"]["total"] == 0
    current["user"] = user(facilities=[])
    none = client.get(f"{OBS}/overview").json()
    assert none["overview"]["messages"]["processed"] == 0 and none["protocols"]["htng"]["last_error"] is None


def test_overview_api_shape_and_no_secret_or_pii(env):
    stack, client, current, _ = env
    seed_world(stack.repo)
    bad_secret = "S3cret-Value-That-Must-Not-Appear"
    r = client.post(f"{PREFIX}/htng/inbound", content=b"<x/>",
                    headers={"content-type": "text/xml", "X-Integration-Client": "pms-a",
                             "X-Integration-Secret": bad_secret})
    assert r.status_code == 401
    body = client.get(f"{OBS}/overview").json()
    assert set(body) == {"generated_at", "facility_scope", "overview", "protocols", "other_protocols"}
    assert set(body["overview"]) == {"htng_status", "fias_status", "readiness_classification", "messages"}
    htng = body["protocols"]["htng"]
    assert htng["transport"]["status"] == "enabled"  # env enables the synthetic test endpoint
    assert htng["intake_rejections"]["status"] == "observed"
    assert sum(htng["intake_rejections"]["auth_failures_by_reason"].values()) == 1
    assert body["protocols"]["fias"]["transport"]["status"] == "not_observable"  # env's link is untagged
    text = json.dumps(body)
    for forbidden in (bad_secret, "Jane", "jane.roe", "4111111111111111", "pms-a", stack.secrets["pms-a"],
                      "payload_hash", "idempotency", "lease_owner"):
        assert forbidden not in text


def test_message_search_api_pagination_filters_and_isolation(env):
    stack, client, current, _ = env
    ids = seed_world(stack.repo)
    win = {"received_from": (T - timedelta(hours=1)).isoformat(), "received_to": (T + timedelta(hours=1)).isoformat()}
    r = client.get(f"{OBS}/messages", params={**win, "page_size": 3})
    assert r.status_code == 200
    page = r.json()
    assert set(page) == {"items", "page", "page_size", "total", "window"}
    assert page["total"] == 7 and page["page"] == 1 and len(page["items"]) == 3
    seen = []
    for n in (1, 2, 3):
        seen += [i["message_id"] for i in client.get(f"{OBS}/messages", params={**win, "page_size": 3,
                                                                              "page": n}).json()["items"]]
    assert len(set(seen)) == 7 and str(ids["f_dlq_b"]) not in seen
    item = page["items"][0]
    assert set(item) == {"message_id", "protocol", "facility_id", "direction", "message_type", "status",
                         "received_at", "completed_at", "attempt_count", "retry_count", "max_attempts",
                         "next_attempt_at", "correlation_id", "error"}
    fias = client.get(f"{OBS}/messages", params={**win, "protocol": "fias", "status": "RETRY_WAIT"}).json()
    assert fias["total"] == 1 and fias["items"][0]["error"] == {"code": "hms_unavailable", "category": "transient"}
    retried = [i for i in client.get(f"{OBS}/messages", params={**win, "protocol": "htng"}).json()["items"]
               if i["message_id"] == str(ids["h_ok1"])]
    assert retried[0]["retry_count"] == 2
    # Facility filter outside the caller's scope is refused, inside is honoured.
    assert client.get(f"{OBS}/messages", params={**win, "facility_id": str(FACILITY_B)}).status_code == 403
    assert client.get(f"{OBS}/messages", params={**win, "facility_id": str(FACILITY_A)}).json()["total"] == 7
    # Validation and bounds.
    assert client.get(f"{OBS}/messages", params={**win, "status": "BOGUS"}).status_code == 422
    assert client.get(f"{OBS}/messages", params={**win, "protocol": "test"}).status_code == 422
    assert client.get(f"{OBS}/messages", params={**win, "page_size": 101}).status_code == 422
    assert client.get(f"{OBS}/messages", params={**win, "page": 102, "page_size": 100}).status_code == 422
    assert client.get(f"{OBS}/messages", params={"received_from": (T - timedelta(days=40)).isoformat(),
                                                  "received_to": T.isoformat()}).status_code == 422
    assert client.get(f"{OBS}/messages", params={"received_from": "2026-11-10T08:00:00",
                                                  "received_to": "2026-11-10T09:00:00"}).status_code == 422
    assert client.get(f"{OBS}/messages", params={"facility_id": "not-a-uuid"}).status_code == 422
    text = client.get(f"{OBS}/messages", params=win).text
    for forbidden in ("Jane", "jane.roe", "4111111111111111", "payload_hash", "idempotency", "ordering_key",
                      "client_id", "lease_owner"):
        assert forbidden not in text


def test_dlq_api_visibility_and_redrive_eligibility(env):
    stack, client, current, _ = env
    ids = seed_world(stack.repo)
    current["user"] = user(facilities=[FACILITY_A])
    page = client.get(f"{OBS}/dlq").json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["message_id"] == str(ids["h_dlq"]) and item["protocol"] == "htng"
    assert (item["failure_category"], item["failure_code"]) == ("permanent", "hms_business_rule")
    assert item["last_attempt_at"] is not None and item["retry_count"] == 0
    assert item["redrive"] == {"state_eligible": True, "caller_has_permission": False, "eligible": False}
    assert "Jane" not in json.dumps(page)
    current["user"] = user(facilities=[FACILITY_A, FACILITY_B], write=True)
    both = client.get(f"{OBS}/dlq").json()
    assert both["total"] == 2 and all(i["redrive"]["eligible"] for i in both["items"])
    assert client.get(f"{OBS}/dlq", params={"protocol": "fias"}).json()["total"] == 1
    assert client.get(f"{OBS}/dlq", params={"facility_id": str(FACILITY_A)}).json()["total"] == 1
    # Read-only: the DLQ is unchanged after viewing.
    assert {str(m.status) for m in stack.repo.list_messages(facility_scope=None, limit=100)
            if m.message_id in (ids["h_dlq"], ids["f_dlq_b"])} == {"DEAD_LETTER"}


# ------------------------------------------------- authentication coverage
def test_auth_coverage_is_facility_scoped(mysql_engine):
    from app.integrations.admin import IntegrationAdmin
    from app.integrations.security.clients import generate_secret

    from .conftest import reset_mysql_schema, seed_mysql_clients

    reset_mysql_schema(mysql_engine)
    seed_mysql_clients(mysql_engine, {"pms-a": generate_secret(), "pms-b": generate_secret(),
                                      "pms-off": generate_secret()})
    admin = IntegrationAdmin(mysql_engine)
    a = admin.auth_coverage(facility_scope={FACILITY_A})
    assert a == {"htng": {"enabled_clients": 1, "enabled_mappings": 1},
                 "fias": {"enabled_clients": 1, "enabled_mappings": 1}}
    # FACILITY_B: pms-b's two enabled mappings; pms-a's mapping there is disabled.
    assert admin.auth_coverage(facility_scope={FACILITY_B})["fias"] == {"enabled_clients": 1, "enabled_mappings": 2}
    assert admin.auth_coverage(facility_scope=set())["htng"] == {"enabled_clients": 0, "enabled_mappings": 0}
    text = json.dumps(admin.auth_coverage(facility_scope=None))
    assert "pms-" not in text
