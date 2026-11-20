"""Facility health view on BOTH repositories, and its API scoping."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.integrations.core.envelope import Protocol
from app.integrations.core.errors import PermanentFailure, TransientFailure
from app.integrations.processing.repository import OutboxDraft

from .conftest import CLIENT_A, CLIENT_B, FACILITY_A, FACILITY_B, T0, make_envelope


def _seed(repo):
    for i, key in enumerate(["ok1", "ok2", "retry", "dead", "pending"]):
        repo.accept(make_envelope(key=key, received_at=T0 + timedelta(seconds=i)), wire_bytes=None, max_attempts=3)
    repo.accept(make_envelope(key="b", facility=FACILITY_B, client=CLIENT_B, received_at=T0 + timedelta(seconds=6)),
                wire_bytes=None, max_attempts=3)
    now = T0 + timedelta(seconds=10)
    claims = {c.message.idempotency_key: c for c in repo.claim(worker_id="w", now=now, lease_seconds=60, limit=4)}
    with repo.completion(claims["ok1"], clock=lambda: now + timedelta(milliseconds=250)) as ctx:
        ctx.add_outbox(OutboxDraft(Protocol.TEST, "test.receipt", {}, None))
    with repo.completion(claims["ok2"], clock=lambda: now + timedelta(seconds=2)):
        pass
    repo.record_failure(claims["retry"], now=now, error=TransientFailure("x"), retry_at=now + timedelta(minutes=5))
    repo.record_failure(claims["dead"], now=now, error=PermanentFailure("x"), retry_at=None)
    return now


def test_facility_health_counts_backlog_latency_and_clients(repo):
    now = _seed(repo)
    rows = repo.facility_health(facility_scope={FACILITY_A}, now=now + timedelta(seconds=5),
                                window=timedelta(hours=1))
    assert len(rows) == 1
    h = rows[0].as_dict(now + timedelta(seconds=5))
    assert h["facility_id"] == str(FACILITY_A)
    assert h["inbound_by_status"] == {"DEAD_LETTER": 1, "PENDING": 1, "RETRY_WAIT": 1, "SUCCEEDED": 2}
    assert h["pending"] == 2 and h["retrying"] == 1 and h["failed_dead_letter"] == 1
    assert h["outbound_by_status"] == {"PENDING": 1} and h["outbound_total"] == 1
    assert h["oldest_pending_age_seconds"] == 13.0  # "retry" message received at T0+2s
    lat = h["latency_ms"]
    assert lat["samples"] == 2 and lat["max"] == 11000.0 and lat["p50"] in (10250.0, 11000.0)
    (client,) = h["clients"]
    assert client["client_id"] == str(CLIENT_A)
    assert client["last_received_at"].startswith("2026-11-19T12:00:04")
    assert client["last_succeeded_at"].startswith("2026-11-19T12:00:12")


def test_facility_health_is_scoped(repo):
    now = _seed(repo)
    both = repo.facility_health(facility_scope=None, now=now, window=timedelta(hours=1))
    assert [str(h.facility_id) for h in both] == sorted([str(FACILITY_A), str(FACILITY_B)])
    assert repo.facility_health(facility_scope=set(), now=now, window=timedelta(hours=1)) == []
    only_b = repo.facility_health(facility_scope={FACILITY_B}, now=now, window=timedelta(hours=1))
    assert [h.facility_id for h in only_b] == [FACILITY_B]


def test_latency_window_excludes_old_completions(repo):
    now = _seed(repo)
    rows = repo.facility_health(facility_scope={FACILITY_A}, now=now + timedelta(hours=2),
                                window=timedelta(minutes=30))
    assert rows[0].as_dict(now)["latency_ms"]["samples"] == 0


def test_health_endpoint_scoped_and_exposes_links_and_auth_failures(env):
    stack, client, current, _ = env
    from .test_api import PREFIX, seed, user

    seed(stack, 2)
    seed(stack, 1, prop="HOTEL-B", client="pms-b")
    from app.integrations.core.errors import AuthenticationFailed

    with pytest.raises(AuthenticationFailed):
        stack.gateway.authenticate("pms-a", "x" * 40, protocol=Protocol.TEST)
    body = client.get(f"{PREFIX}/facilities/health?window_minutes=30").json()
    assert [f["facility_id"] for f in body["facilities"]] == [str(FACILITY_A)]
    assert body["facilities"][0]["pending"] == 2
    assert body["transports"]["fias-link"]["state"] == "disconnected"
    assert any("invalid_secret" in k for k in body["auth_failures"])
    current["user"] = user(facilities=[])
    assert client.get(f"{PREFIX}/facilities/health").json()["facilities"] == []
    assert client.get(f"{PREFIX}/facilities/health?window_minutes=0").status_code == 422

