"""Phase D energy adapter tests (read-only integration).

`/energy-stats` previously returned 503 because hourly consumption could not be
derived from the cumulative `active_energy` counter without an unverified unit.
It is now computed by integrating `active_power` -- whose kW scale IS verifiable
from the payload -- over IST hours. These tests pin that behaviour, including
the properties that protect a billing-adjacent number: IST bucketing, no
invented unit, and no integration across outages.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.adapters import energy_adapter as svc
from app.core.config import settings
from app.db.session import get_db
from app.main import create_app

client = TestClient(create_app())
requires_db = pytest.mark.skipif(
    not settings.is_db_configured, reason="OSS database not configured"
)


@pytest.fixture
def db():
    gen = get_db()
    session = next(gen)
    try:
        yield session
    finally:
        gen.close()


@requires_db
def test_energy_stats_returns_hourly_rows():
    r = client.get("/energy-stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 0
    for item in body["items"]:
        assert item["energy_consumed"] >= 0
        # Never claim a unit OSS does not declare.
        assert item["energy_unit"] is None


@requires_db
def test_hour_and_hour_timestamp_round_trip_in_ist(db):
    """`hour` must address exactly the IST bucket `hour_timestamp` names."""
    rows, _ = svc.list_energy_stats(db, page=1, page_size=50)
    for r in rows:
        assert svc.HOUR_EPOCH + timedelta(hours=r["hour"]) == r["hour_timestamp"]
        # IST hour starts land on :00 of an IST hour, i.e. :30 past a UTC hour.
        assert r["hour_timestamp"].utcoffset() == timedelta(hours=5, minutes=30)
        assert r["hour_timestamp"].minute == 0


@requires_db
def test_readings_fall_inside_their_own_bucket(db):
    """Guards against an off-by-one-offset bucketing bug (UTC vs IST)."""
    rows, _ = svc.list_energy_stats(db, page=1, page_size=50)
    for r in rows:
        start = r["hour_timestamp"]
        end = start + timedelta(hours=1)
        assert start <= r["created_on"] < end
        assert start <= r["updated_on"] < end


@requires_db
def test_energy_matches_an_independent_trapezoidal_integral(db):
    """The adapter's number must equal a hand-rolled integral of active_power."""
    from sqlalchemy import text

    expected = {
        row[0]: float(row[1])
        for row in db.execute(
            text(
                """
                WITH s AS (
                  SELECT device_uid, recorded_at,
                         (param_data->>'active_power')::numeric p,
                         lag((param_data->>'active_power')::numeric)
                           OVER (PARTITION BY device_uid ORDER BY recorded_at) prev_p,
                         EXTRACT(EPOCH FROM (recorded_at -
                           lag(recorded_at) OVER (PARTITION BY device_uid
                                                  ORDER BY recorded_at)))/3600.0 dt
                  FROM insp_device_performance
                  WHERE param_data ? 'active_power')
                SELECT device_uid, sum(((p + prev_p)/2)*dt)
                FROM s WHERE dt > 0 AND dt <= :max_dt
                GROUP BY device_uid
                """
            ),
            {"max_dt": svc.MAX_INTERVAL_HOURS},
        )
    }

    rows, _ = svc.list_energy_stats(db, page=1, page_size=500)
    actual: dict[str, float] = {}
    for r in rows:
        actual[r["device_uid"]] = actual.get(r["device_uid"], 0.0) + r["energy_consumed"]

    assert actual.keys() == expected.keys()
    for uid, value in actual.items():
        assert value == pytest.approx(expected[uid], abs=1e-5)


@requires_db
def test_long_gaps_are_not_integrated(db):
    """An outage must not be turned into consumption nobody measured."""
    assert svc.MAX_INTERVAL_HOURS <= 1.0
    rows, _ = svc.list_energy_stats(db, page=1, page_size=500)
    for r in rows:
        # A bucket is one hour; capped intervals can never exceed that.
        span = (r["updated_on"] - r["created_on"]).total_seconds() / 3600.0
        assert span < 1.0


@requires_db
def test_summary_groupings_agree_on_the_total():
    totals = set()
    for group_by in ("hour", "day", "device"):
        r = client.get("/energy-stats/summary", params={"group_by": group_by})
        assert r.status_code == 200
        body = r.json()
        assert body["group_by"] == group_by
        assert body["energy_unit"] is None
        totals.add(round(body["total_energy_consumed"], 6))
    # Regrouping the same readings cannot change how much energy there was.
    assert len(totals) == 1


@requires_db
def test_room_filters_are_rejected_not_ignored():
    """OSS has no rooms; silently ignoring the filter would return wrong rows."""
    r = client.get("/energy-stats", params={"amenity_id": "11111111-1111-1111-1111-111111111111"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "oss_adapter_not_mapped"


@requires_db
def test_unsupported_group_by_is_rejected():
    r = client.get("/energy-stats/summary", params={"group_by": "amenity"})
    assert r.status_code == 503
