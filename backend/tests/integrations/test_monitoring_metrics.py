"""GET /api/v1/integrations/observability/metrics -- windowed per-protocol aggregates
for the HTNG / FIAS monitoring charts.

Repository-level tests run on BOTH stores (memory and the disposable MySQL).
Values are hand-checkable from `seed_world` in test_observability.py:

  HTNG (facility A): h1 SUCCEEDED after 2 retries (received T, done T+5s), h2
  SUCCEEDED (T+1m, done +1s, emits one outbox row), h3 DEAD_LETTER (T+2m), h4
  PENDING (T+6m).  FIAS: f1 SUCCEEDED (T+3m, +1s), f2 RETRY_WAIT (T+4m), f3
  DEAD_LETTER in facility B (T+5m), f4 PENDING (T+7m).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import OperationalError

from app.api.deps import get_current_user
from app.integrations import observability as obs
from app.integrations.core.envelope import Protocol
from app.integrations.processing.activity import METRIC_RANGES, metrics_window
from app.integrations.processing.repository import InMemoryIntegrationRepository

from .conftest import FACILITY_A, FACILITY_B
from .test_api import PREFIX, user
from .test_observability import T, put, runtime_for, seed_world

NOW = T + timedelta(minutes=10)  # 08:10 UTC
OBS = f"{PREFIX}/observability"


def metrics(repo, protocol, *, scope=frozenset({FACILITY_A}), range_key="1h", now=NOW, facility_ids=None, tz=0):
    return obs.build_metrics(runtime_for(repo), protocol=protocol, range_key=range_key, now=now,
                             facility_ids=facility_ids, facility_scope=None if scope is None else set(scope),
                             tz_offset_minutes=tz)


# ------------------------------------------------------------------ windows
def test_window_alignment_and_bucket_counts():
    start, end, bucket = metrics_window("1h", NOW)
    assert (start, end, bucket) == (T - timedelta(minutes=45), T + timedelta(minutes=15), 300)
    for key, (span, b) in METRIC_RANGES.items():
        s, e, bb = metrics_window(key, NOW)
        assert (e - s).total_seconds() == span and bb == b and span // b <= 30
    # daily buckets follow the viewer's local day (India, UTC+05:30)
    s, e, _ = metrics_window("7d", datetime(2026, 11, 20, 10, 0, tzinfo=UTC), 330)
    assert e == datetime(2026, 11, 20, 18, 30, tzinfo=UTC)  # local midnight of 21 Nov
    assert s == e - timedelta(days=7)


# -------------------------------------------------- cohort KPIs (both stores)
def test_htng_kpis_status_distribution_and_success_rate(repo):
    seed_world(repo)
    m = metrics(repo, "htng")
    assert m["status"] == "measured" and m["protocol"] == "htng" and m["basis"] == "retained_rows"
    k = m["kpis"]
    assert (k["inbound_total"], k["processed"], k["failed"], k["queued"], k["awaiting_retry"]) == (4, 2, 1, 1, 0)
    assert k["inbound_total"] == k["processed"] + k["failed"] + k["queued"]  # cohort identity
    assert k["success_rate"] == round(2 / 3, 4)
    assert (k["retried_messages"], k["extra_attempts"]) == (1, 2)
    assert (k["outbound_total"], k["outbound_sent"], k["outbound_queued"], k["outbound_failed"]) == (1, 0, 1, 0)
    dist = {d["status"]: d["count"] for d in m["status_distribution"]["inbound"]}
    assert dist == {"SUCCEEDED": 2, "PENDING": 1, "DEAD_LETTER": 1}  # only statuses that exist
    assert sum(d["share"] for d in m["status_distribution"]["inbound"]) == pytest.approx(1.0, abs=1e-3)
    assert m["errors"] == [{"category": "permanent", "code": "hms_business_rule", "count": 1}]
    assert m["message_types"] == [{"message_type": "test.guest_arrival", "count": 4}]


def test_fias_is_isolated_from_htng_and_by_facility(repo):
    seed_world(repo)
    a = metrics(repo, "fias")
    assert (a["kpis"]["inbound_total"], a["kpis"]["processed"], a["kpis"]["failed"], a["kpis"]["awaiting_retry"]) == (3, 1, 0, 1)
    assert a["kpis"]["success_rate"] == 1.0
    assert a["errors"] == [{"category": "transient", "code": "hms_unavailable", "count": 1}]
    b = metrics(repo, "fias", scope={FACILITY_B})
    assert (b["kpis"]["inbound_total"], b["kpis"]["failed"]) == (1, 1)
    both = metrics(repo, "fias", scope={FACILITY_A, FACILITY_B}, facility_ids=frozenset({FACILITY_B}))
    assert both["kpis"]["inbound_total"] == 1  # requested facility narrows within scope
    none = metrics(repo, "fias", scope=set())
    assert none["kpis"]["inbound_total"] == 0 and none["series"][0]["received"] == 0


# ------------------------------------------------------- series (both stores)
def test_series_are_event_counts_in_the_right_buckets(repo):
    seed_world(repo)
    m = metrics(repo, "htng")
    s = m["series"]
    assert len(s) == 12 and s[0]["bucket_start"] == (T - timedelta(minutes=45)).isoformat()
    by_i = {i: b for i, b in enumerate(s) if any(b[k] for k in ("received", "processed", "failed", "outbound_created"))}
    # 08:00, 08:01, 08:02 fall in bucket 9 (08:00-08:05); 08:06 in bucket 10
    assert by_i[9]["received"] == 3 and by_i[10]["received"] == 1
    assert by_i[9]["processed"] == 2 and by_i[9]["failed"] == 1  # by COMPLETION time
    assert by_i[9]["retried_received"] == 1 and by_i[9]["outbound_created"] == 1
    assert by_i[9]["avg_latency_seconds"] == 3.0  # (5 s + 1 s) / 2
    assert all(b["avg_latency_seconds"] is None for i, b in enumerate(s) if i != 9)  # never 0 for "no data"
    assert sum(b["received"] for b in s) == m["kpis"]["inbound_total"]


def test_latency_is_end_to_end_with_nearest_rank_percentiles(repo):
    seed_world(repo)
    lat = metrics(repo, "htng")["latency"]
    assert lat["basis"] == "received_to_completed"
    assert lat["count"] == 2 and lat["avg"] == 3.0 and lat["p50"] == 1.0 and lat["p95"] == 5.0 and lat["max"] == 5.0


def test_date_range_filter_excludes_older_messages(repo):
    old = put(repo, protocol=Protocol.HTNG, key="old", at=T - timedelta(days=2), outcome="succeeded")
    assert old
    seed_world(repo)
    assert metrics(repo, "htng", range_key="24h")["kpis"]["inbound_total"] == 4
    week = metrics(repo, "htng", range_key="7d")
    assert week["kpis"]["inbound_total"] == 5 and len(week["series"]) == 7


def test_empty_dataset_reports_zero_counts_and_null_rates():
    m = metrics(InMemoryIntegrationRepository(), "htng")
    k = m["kpis"]
    assert k["inbound_total"] == 0 and k["processed"] == 0
    assert k["success_rate"] is None  # no completed message: a rate is undefined, not 0 %
    assert m["latency"]["count"] == 0 and m["latency"]["avg"] is None and m["latency"]["p95"] is None
    assert len(m["series"]) == 12 and all(b["received"] == 0 for b in m["series"])
    assert m["status_distribution"]["inbound"] == [] and m["errors"] == []


class _Down(InMemoryIntegrationRepository):
    def metrics(self, query, *, facility_scope):
        raise OperationalError("SELECT 1", {}, Exception("db down"))


def test_unavailable_store_is_null_never_zero():
    m = metrics(_Down(), "fias")
    assert m["status"] == "not_available"
    assert m["kpis"] is None and m["latency"] is None and m["series"] == [] and m["errors"] is None


def test_unsupported_metrics_are_listed_explicitly():
    fias = {u["metric"] for u in metrics(InMemoryIntegrationRepository(), "fias")["unavailable"]}
    htng = {u["metric"] for u in metrics(InMemoryIntegrationRepository(), "htng")["unavailable"]}
    assert {"ack_statistics", "connection_history", "timeout_statistics", "parse_failures",
            "retry_attempt_timeline", "processing_latency", "worker_health"} <= fias
    assert "ack_statistics" not in htng and "endpoint_availability_history" in htng


# ----------------------------------------------------------------------- API
def test_metrics_api_auth_rbac_scope_and_validation(env):
    _, client, current, _ = env
    url = f"{OBS}/metrics"
    current["user"] = user(facilities=[FACILITY_A])
    ok = client.get(url, params={"protocol": "htng", "range": "24h", "tz_offset_minutes": 330})
    assert ok.status_code == 200
    body = ok.json()
    assert body["window"]["range"] == "24h" and body["window"]["bucket_seconds"] == 3600 and len(body["series"]) == 24
    for bad in ({"protocol": "test"}, {"protocol": "htng", "range": "90d"}, {},
                {"protocol": "htng", "tz_offset_minutes": 2000}, {"protocol": "htng", "facility_id": "x"}):
        assert client.get(url, params=bad).status_code == 422, bad
    assert client.get(url, params={"protocol": "htng", "facility_id": str(FACILITY_B)}).status_code == 403
    assert client.post(url, json={}).status_code == 405
    current["user"] = user(facilities=[FACILITY_A], read=False)
    assert client.get(url, params={"protocol": "htng"}).status_code == 403
    client.app.dependency_overrides.pop(get_current_user)
    assert client.get(url, params={"protocol": "htng"}).status_code == 401


def test_metrics_api_counts_only_the_callers_facility_and_returns_no_rows(env):
    from .test_api import seed

    stack, client, current, _ = env
    current["user"] = user(facilities=[FACILITY_A])
    seed(stack, n=2)  # Protocol.TEST messages in facility A: not HTNG / FIAS
    body = client.get(f"{OBS}/metrics", params={"protocol": "htng", "range": "1h"}).json()
    assert body["kpis"]["inbound_total"] == 0  # protocol isolation
    text = str(body)
    for forbidden in ("Jane", "payload", "secret", "idempotency", "correlation"):
        assert forbidden not in text
