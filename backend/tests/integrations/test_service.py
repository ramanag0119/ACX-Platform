"""Integration service loop, retention purge (both repositories), HTNG rate limit."""

from __future__ import annotations

import threading
from datetime import timedelta


from app.integrations.core.envelope import MessageStatus, Protocol
from app.integrations.core.errors import PermanentFailure
from app.integrations.processing.repository import OutboxDraft
from app.integrations.service import IntegrationService, ServiceSettings

from .conftest import CLIENT_A, CTX, FACILITY_A, T0, build_stack, json_msg, make_envelope


def service(stack, **kw):
    settings = ServiceSettings(poll_interval_seconds=0.01, error_backoff_base_seconds=0.01,
                               error_backoff_max_seconds=0.05, **kw)
    return IntegrationService(worker=stack.worker, relay=stack.relay, settings=settings, metrics=stack.metrics,
                              purge=lambda before: stack.repo.purge_completed(before=before, now=stack.clock()),
                              clock=stack.clock)


def test_iteration_processes_inbound_and_outbound(stack):
    stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    svc = service(stack)
    assert svc.run_iteration() is True   # worker processes, then relay sends the emitted receipt
    assert len(stack.sent) == 1
    assert svc.run_iteration() is False  # idle
    assert stack.sent and stack.metrics.last_heartbeat("integration_service") == stack.clock()


def test_run_loop_stops_gracefully(stack):
    svc = service(stack)
    t = threading.Thread(target=svc.run)
    t.start()
    svc.stop()
    t.join(2)
    assert not t.is_alive() and svc.iterations >= 1


def test_loop_survives_errors_with_bounded_backoff(stack):
    calls = {"n": 0}
    real = stack.worker.run_once

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise ConnectionError("database down")
        return real(**kw)

    stack.worker.run_once = flaky
    svc = service(stack)
    t = threading.Thread(target=svc.run)
    t.start()
    for _ in range(200):
        if calls["n"] > 4:
            break
        threading.Event().wait(0.01)
    svc.stop()
    t.join(2)
    assert calls["n"] > 4 and stack.metrics.get("service_errors", type="ConnectionError") == 3
    svc._errors_in_row = 10  # noqa: SLF001
    assert svc.backoff_seconds() == 0.05


def test_purge_is_disabled_without_retention(stack):
    svc = service(stack)  # retention None
    stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    stack.worker.run_once()
    stack.clock.advance(10 * 86400)
    svc.run_iteration()
    assert len(stack.repo.list_messages(facility_scope=None)) == 1


def test_purge_runs_on_interval_when_configured(stack):
    svc = service(stack, retention=timedelta(days=1), purge_interval_seconds=3600)
    stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    stack.worker.run_once()
    stack.clock.advance(2 * 86400)
    svc.run_iteration()
    assert stack.repo.list_messages(facility_scope=None) == []
    assert stack.metrics.get("retention_purged_inbound") == 1


# --- purge contract (both repositories) ---------------------------------------------
def test_purge_removes_only_old_completed_rows(repo):
    for i, key in enumerate(["old-ok", "new-ok", "dead", "pending"]):
        repo.accept(make_envelope(key=key, received_at=T0 + timedelta(seconds=i)), wire_bytes=None, max_attempts=3)
    claims = {c.message.idempotency_key: c for c in repo.claim(worker_id="w", now=T0 + timedelta(seconds=5),
                                                                 lease_seconds=86400 * 10, limit=3)}
    with repo.completion(claims["old-ok"], clock=lambda: T0 + timedelta(seconds=5)) as ctx:
        ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
    with repo.completion(claims["new-ok"], clock=lambda: T0 + timedelta(days=3)):
        pass
    repo.record_failure(claims["dead"], now=T0, error=PermanentFailure("x"), retry_at=None)
    (oc,) = repo.claim_outbox(worker_id="r", now=T0 + timedelta(seconds=6), lease_seconds=60, limit=5)
    repo.mark_outbox_sent(oc, now=T0 + timedelta(seconds=7))

    counts = repo.purge_completed(before=T0 + timedelta(days=1), now=T0 + timedelta(days=4))
    assert counts == {"inbound": 1, "outbox": 1}
    left = {m.idempotency_key: m.status for m in repo.list_messages(facility_scope=None)}
    assert left == {"new-ok": MessageStatus.SUCCEEDED, "dead": MessageStatus.DEAD_LETTER,
                    "pending": MessageStatus.PENDING}
    assert repo.list_outbox(facility_scope=None) == []
    # The purged message's idempotency key is released: the retention window
    # is also the duplicate-protection window (documented).
    again = repo.accept(make_envelope(key="old-ok", received_at=T0 + timedelta(days=4)), wire_bytes=None, max_attempts=3)
    assert str(again.outcome) == "accepted"
    assert repo.list_audit(facility_scope=None)[0].action == "retention.purge"


def test_service_main_refuses_when_disabled():
    from app.integrations.config import IntegrationSettings
    from app.integrations.domain.approvals import LiveWriteGate
    from app.integrations.runtime import IntegrationRuntime, set_runtime
    from app.integrations.service import main

    s = build_stack()
    set_runtime(IntegrationRuntime(settings=IntegrationSettings(), gateway=s.gateway, repository=s.repo,
                                   metrics=s.metrics, live_write_gate=LiveWriteGate(enabled_flag=False)))
    try:
        assert main() == 3
    finally:
        set_runtime(None)


# --- HTNG rate limit -----------------------------------------------------------------
def test_htng_rate_limit_per_client(env):
    from app.integrations.api import router as router_mod
    from app.integrations.config import IntegrationSettings

    from .test_api import PREFIX, hdr, soap

    stack, client, _, runtime = env
    runtime.settings = IntegrationSettings(ENABLED=True, HTNG_INBOUND_ENABLED=True, HTNG_RATE_LIMIT_PER_MINUTE=2)
    router_mod._RATE_LIMITER = router_mod._MinuteRateLimiter(clock=lambda: 120.0)  # noqa: SLF001
    codes = [client.post(f"{PREFIX}/htng/inbound", content=soap(f"r{i}"), headers=hdr(stack)).status_code
             for i in range(3)]
    assert codes == [200, 200, 429]
    assert client.post(f"{PREFIX}/htng/inbound", content=soap("rb", prop="HOTEL-B"),
                       headers=hdr(stack, "pms-b")).status_code == 200  # other client unaffected
    router_mod._RATE_LIMITER = router_mod._MinuteRateLimiter()  # noqa: SLF001


def test_rate_limiter_window_resets():
    from app.integrations.api.router import _MinuteRateLimiter

    now = {"t": 0.0}
    rl = _MinuteRateLimiter(clock=lambda: now["t"])
    assert [rl.allow("c", 1), rl.allow("c", 1)] == [True, False]
    now["t"] = 60.0
    assert rl.allow("c", 1) is True



def test_mapping_api_unavailable_without_sql_admin(env):
    from .test_api import PREFIX

    _, client, _, _ = env
    assert client.get(f"{PREFIX}/mappings").status_code == 503


_ = (CLIENT_A, FACILITY_A)
