"""HMS workflow certification scenarios: real `stays_write` on a DISPOSABLE seeded MySQL.

Reuses tests/integrations/test_e2e_hms_simulation.build (synthetic "ZI"/"ZO" records —
TEST ASSUMPTION, not FIAS) and the seeded synthetic stays PMS-0001/0003/0004 from the
repository's own seed. Requires INTEGRATION_TEST_HMS_DB_URL; otherwise NOT RUN.
Live writes are possible here only because build() uses a TEST-ONLY approval register.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.integrations.adapters.base import TransportContext
from app.integrations.core.envelope import IntakeOutcome, MessageStatus, Protocol
from app.integrations.domain.stays import CHECK_IN

from .core import Category, scenario

H = Category.HMS
REQ = ("hms_db",)


def world(ctx):
    from ..test_e2e_hms_simulation import build

    engine = ctx.env.hms_engine()
    gateway, worker, repo, clock, facility_id, secret, _ = build(engine)
    ctx.secrets.append(secret)
    ctx.evidence.adapter = "FIASAdapter(ACX-SYNTHETIC-STAY-TEST/0, PROVISIONAL) -> StayDomainAdapter -> stays_write"
    client = gateway.authenticate("pms-sim", secret, protocol=Protocol.FIAS)
    return engine, gateway, worker, repo, clock, facility_id, client


def send(gw, client, rid, ref, stay_ref, prop="HOTEL-SIM"):
    return gw.receive(f"{rid}|MI{ref}|PC{prop}|SR{stay_ref}|".encode(), protocol=Protocol.FIAS, client=client,
                      context=TransportContext(transport="direct"))


def state(engine, ref):
    from ..test_hms_domain_mysql import stay

    s = stay(engine, ref)
    return {"stay_status": s[0], "checked_in": s[1] is not None, "checked_out": s[2] is not None, "room_status": s[3]}


def reset(engine, ref, status, checkin=None, checkout=None, room="Allotted"):
    from ..test_hms_domain_mysql import reset_stay

    reset_stay(engine, ref, status, checkin, checkout, room)


def process(worker, clock, times=2):
    clock.advance(1)
    for _ in range(times):
        worker.run_once()


def audit(repo, facility_id):
    return [e.action for e in repo.list_audit(facility_scope={facility_id})]


def msg_status(repo, ext):
    for m in repo.list_messages(facility_scope=None, limit=200):
        if m.external_message_id == ext:
            return m
    return None


@scenario("HMS-SYN-001", "hms", H, "Check-in updates the real stay and room, with audit",
          expected={"stay_status": "active", "room_status": "Occupied", "audit": "domain.stay.check_in"},
          evidence=("hms_before", "hms_after", "audit_actions"), requires=REQ)
def _checkin(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    ctx.evidence.hms_before = state(engine, "PMS-0003")
    r = send(gw, client, "ZI", "h1-in", "PMS-0003")
    ctx.evidence.correlation_id = r.correlation_id
    process(worker, clock)
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.evidence.audit_actions = audit(repo, fid)
    ctx.expect(ctx.evidence.hms_after["stay_status"] == "active" and ctx.evidence.hms_after["room_status"] == "Occupied",
               str(ctx.evidence.hms_after))
    ctx.expect("domain.stay.check_in" in ctx.evidence.audit_actions, "no audit")


@scenario("HMS-SYN-002", "hms", H, "Check-out after check-in closes the stay, with audit",
          expected={"stay_status": "checked out", "audit": ["domain.stay.check_out", "domain.stay.check_in"]},
          evidence=("hms_after", "audit_actions"), requires=REQ)
def _checkout(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    send(gw, client, "ZI", "h2-in", "PMS-0003")
    send(gw, client, "ZO", "h2-out", "PMS-0003")
    process(worker, clock, 3)
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.evidence.audit_actions = audit(repo, fid)
    ctx.expect(ctx.evidence.hms_after["stay_status"] == "checked out", str(ctx.evidence.hms_after))
    ctx.expect(ctx.evidence.audit_actions[:2] == ["domain.stay.check_out", "domain.stay.check_in"], str(ctx.evidence.audit_actions))


@scenario("HMS-SYN-003", "hms", H, "Duplicate check-in message processed once",
          expected={"second": "duplicate", "check_in_audits": 1}, evidence=("processing_result", "audit_actions"), requires=REQ)
def _dup(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    send(gw, client, "ZI", "h3-in", "PMS-0003")
    r = send(gw, client, "ZI", "h3-in", "PMS-0003")
    process(worker, clock)
    ctx.evidence.processing_result = str(r.outcome)
    ctx.evidence.audit_actions = audit(repo, fid)
    ctx.expect(r.outcome is IntakeOutcome.DUPLICATE and ctx.evidence.audit_actions.count("domain.stay.check_in") == 1,
               str(ctx.evidence.audit_actions))


@scenario("HMS-SYN-004", "hms", H, "Check-out before check-in rejected by the real HMS rule; later check-in waits",
          expected={"check_out": "DEAD_LETTER/hms_business_rule", "check_in": "PENDING", "stay": "pending"},
          evidence=("retry_dlq", "hms_after"), requires=REQ)
def _out_of_order(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    send(gw, client, "ZO", "h4-out", "PMS-0003")
    send(gw, client, "ZI", "h4-in", "PMS-0003")
    process(worker, clock, 3)
    out, inn = msg_status(repo, "ZO:h4-out"), msg_status(repo, "ZI:h4-in")
    ctx.evidence.retry_dlq = {"check_out": f"{out.status}/{out.last_error_code}", "check_in": str(inn.status)}
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.expect(out.status is MessageStatus.DEAD_LETTER and out.last_error_code == "hms_business_rule"
               and inn.status is MessageStatus.PENDING and ctx.evidence.hms_after["stay_status"] == "pending",
               str(ctx.evidence.retry_dlq))


@scenario("HMS-SYN-005", "hms", H, "Repeated check-in (new message id) for an in-house stay is a no-op",
          expected={"status": "SUCCEEDED", "already_applied": True, "stay": "active"},
          evidence=("hms_before", "hms_after", "observations"), requires=REQ)
def _repeat(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0001", "active", datetime(2026, 8, 15, 12, tzinfo=UTC), None, "Occupied")
    ctx.evidence.hms_before = state(engine, "PMS-0001")
    send(gw, client, "ZI", "h5-again", "PMS-0001")
    process(worker, clock)
    ctx.evidence.hms_after = state(engine, "PMS-0001")
    detail = [e.detail for e in repo.list_audit(facility_scope={fid}) if e.action == "domain.stay.check_in"]
    ctx.evidence.observations.append(f"already_applied={detail[0].get('already_applied') if detail else None}")
    ctx.expect(msg_status(repo, "ZI:h5-again").status is MessageStatus.SUCCEEDED and detail
               and detail[0].get("already_applied") is True and ctx.evidence.hms_after == ctx.evidence.hms_before,
               str(ctx.evidence.observations))


@scenario("HMS-SYN-006", "hms", H, "Cross-facility event rejected; stay unchanged",
          expected={"intake": "rejected/security", "stay": "unchanged"}, evidence=("failure_code", "hms_after"), requires=REQ)
def _cross(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    before = state(engine, "PMS-0003")
    r = send(gw, client, "ZI", "h6-x", "PMS-0003", prop="HOTEL-OTHER")
    process(worker, clock)
    ctx.evidence.failure_code = r.error["code"] if r.error else None
    ctx.evidence.failure_category = r.error["category"] if r.error else None
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.expect(r.outcome is IntakeOutcome.REJECTED and ctx.evidence.failure_category == "security"
               and ctx.evidence.hms_after == before, str(r.error))


@scenario("HMS-SYN-007", "hms", H, "Audit event carries facility, message, actor and stay reference",
          expected={"audit": {"facility": "matches", "message_id": "set", "actor_type": "system", "stay_id": "set"}},
          evidence=("audit_actions", "observations"), requires=REQ)
def _audit(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    r = send(gw, client, "ZI", "h7-in", "PMS-0003")
    process(worker, clock)
    ev = [e for e in repo.list_audit(facility_scope={fid}) if e.action == "domain.stay.check_in"]
    ctx.evidence.audit_actions = [e.action for e in ev]
    ctx.expect(len(ev) == 1, "expected one audit event")
    e = ev[0]
    ctx.evidence.observations.append(f"actor_type={e.actor_type} has_stay_id={'stay_id' in e.detail}")
    ctx.expect(e.facility_id == fid and e.message_id == r.message_id and e.actor_type == "system"
               and "stay_id" in e.detail, "audit fields incomplete")


@scenario("HMS-SYN-008", "hms", H, "Lost lease rolls back the real HMS change (failed transaction)",
          expected={"lease_lost": 1, "stay_after_failure": "pending", "stay_after_recovery": "active"},
          evidence=("hms_after", "retry_dlq"), requires=REQ)
def _rollback(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    send(gw, client, "ZI", "h8-in", "PMS-0003")
    clock.advance(1)
    real = repo.completion

    def overrun(claim, *, clock):
        times = iter([clock(), clock() + timedelta(seconds=120)])
        return real(claim, clock=lambda: next(times))

    repo.completion = overrun
    lost = worker.run_once().lease_lost
    after_failure = state(engine, "PMS-0003")
    repo.completion = real
    clock.advance(31)
    worker.run_once()
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.evidence.retry_dlq = {"lease_lost": lost, "stay_after_failure": after_failure["stay_status"]}
    ctx.expect(lost == 1 and after_failure["stay_status"] == "pending" and after_failure["room_status"] == "Allotted"
               and ctx.evidence.hms_after["stay_status"] == "active", str(ctx.evidence.retry_dlq))


@scenario("HMS-SYN-009", "hms", H, "Worker crash: lease expiry recovery completes the real check-in",
          expected={"before_expiry": 0, "stay": "active"}, evidence=("hms_after", "retry_dlq"), requires=REQ)
def _crash(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    send(gw, client, "ZI", "h9-in", "PMS-0003")
    clock.advance(1)
    repo.claim(worker_id="crashed", now=clock(), lease_seconds=30, limit=5)
    early = worker.run_once().claimed
    clock.advance(31)
    worker.run_once()
    ctx.evidence.hms_after = state(engine, "PMS-0003")
    ctx.evidence.retry_dlq = {"claimed_before_expiry": early, "attempts": msg_status(repo, "ZI:h9-in").attempt_count}
    ctx.expect(early == 0 and ctx.evidence.hms_after["stay_status"] == "active", str(ctx.evidence.retry_dlq))


@scenario("HMS-SYN-010", "hms", H, "Retry recovers a transient miss; unknown stay ends in DLQ and is redriven with audit",
          expected={"recovered": "SUCCEEDED", "unknown": "DEAD_LETTER", "audit": "message.redrive"},
          evidence=("retry_dlq", "audit_actions"), requires=REQ)
def _retry_dlq(ctx):
    engine, gw, worker, repo, clock, fid, client = world(ctx)
    reset(engine, "PMS-0003", "pending")
    adapter = gw.handlers.get(CHECK_IN)._adapter  # noqa: SLF001 - reuse the real resolver, wrapped
    real_resolver = adapter._resolver  # noqa: SLF001
    calls = {"n": 0}

    class FlakyOnce:
        def resolve_stay(self, session, **kw):
            calls["n"] += 1
            return None if calls["n"] == 1 else real_resolver.resolve_stay(session, **kw)

    adapter._resolver = FlakyOnce()  # noqa: SLF001
    send(gw, client, "ZI", "h10-in", "PMS-0003")
    send(gw, client, "ZI", "h10-unknown", "PMS-9999")
    for _ in range(4):
        process(worker, clock, 1)
        clock.advance(65)
    rec, unk = msg_status(repo, "ZI:h10-in"), msg_status(repo, "ZI:h10-unknown")
    repo.redrive(unk.message_id, facility_scope={fid}, actor_id="cert-operator",
                 reason="certification redrive of unknown stay", now=clock())
    ctx.evidence.audit_actions = audit(repo, fid)
    ctx.evidence.retry_dlq = {"recovered": str(rec.status), "recovered_attempts": rec.attempt_count,
                              "unknown": f"{unk.status}/{unk.last_error_code}"}
    adapter._resolver = real_resolver  # noqa: SLF001
    ctx.expect(rec.status is MessageStatus.SUCCEEDED and rec.attempt_count == 2
               and unk.status is MessageStatus.DEAD_LETTER and "message.redrive" in ctx.evidence.audit_actions,
               str(ctx.evidence.retry_dlq))
