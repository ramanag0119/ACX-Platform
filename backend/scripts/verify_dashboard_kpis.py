"""Assert that every dashboard number equals what PostgreSQL says.

    python -m scripts.verify_dashboard_kpis            # arjun.menon (admin)
    python -m scripts.verify_dashboard_kpis kavya.iyer # a manager's grants

Phase 11 connected the dashboard to the real APIs. This script is the check
that it stayed connected: for each widget it issues the SAME request the
widget issues, and compares the envelope's `total` with an independent SQL
COUNT. A hardcoded or drifted figure shows up as a MISMATCH row, and the
script exits non-zero.

It talks to a RUNNING backend on 127.0.0.1:8000, so it exercises the real
router, the real RBAC dependency and the real service layer -- not a test
client. Tokens are minted through the token service for a real seeded user,
because no seeded account has a usable password hash (every row carries the
Phase 1.8 `!seed-no-login` sentinel) and inventing a credential is forbidden.

Nothing here writes to the database.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import text

from app.core.security import create_access_token
from app.db.session import SessionLocal

BASE = "http://127.0.0.1:8000/api/v1"

#: (label, endpoint, query params, equivalent SQL). The params are exactly what
#: the widget sends; the SQL is written from the schema, not from the service
#: layer, so the two are genuinely independent.
CHECKS: list[tuple[str, str, dict, str]] = [
    ("KPI Devices", "/devices", {},
     "select count(*) from device"),
    ("KPI Devices Active", "/devices", {"health_status": "Active"},
     "select count(*) from device where health_status = 'Active'"),
    ("KPI Devices Inactive", "/devices", {"health_status": "Inactive"},
     "select count(*) from device where health_status = 'Inactive'"),
    ("KPI Firmware outdated", "/devices", {"firmware_outdated": "true"},
     "select count(*) from device where current_firmware_version "
     "is distinct from expected_firmware_version"),
    ("KPI Device alerts", "/alerts", {},
     "select count(*) from device_alert"),
    ("KPI Alerts critical", "/alerts", {"alert_severity": "critical"},
     "select count(*) from device_alert where alert_severity = 'critical'"),
    ("KPI Alerts warning", "/alerts", {"alert_severity": "warning"},
     "select count(*) from device_alert where alert_severity = 'warning'"),
    ("KPI Active value alerts", "/value-alerts", {"status": 0},
     "select count(*) from value_alert where status = 0"),
    ("KPI Incidents", "/incidents", {},
     "select count(*) from device_incident"),
    ("KPI Incidents unassigned", "/incidents", {"unassigned": "true"},
     "select count(*) from device_incident where assigned_to is null"),
    # In-house occupancy is the Phase 2.8 definition, NOT amenity.status.
    ("KPI Rooms in house", "/occupancy", {"is_occupied": "true"},
     "select count(distinct ra.room_id) from room_allocation ra "
     "join stay st on st.id = ra.stay_id "
     "where st.actual_checkin_time is not null "
     "and st.actual_checkout_time is null"),
    ("KPI Rooms total", "/occupancy", {},
     "select count(*) from amenity"),
    ("KPI Stays in house", "/stays", {"is_in_house": "true"},
     "select count(*) from stay where actual_checkin_time is not null "
     "and actual_checkout_time is null"),
    ("KPI Stays total", "/stays", {},
     "select count(*) from stay"),
    ("KPI Service requests", "/service-requests", {},
     "select count(*) from service_request"),
    ("KPI Service unassigned", "/service-requests", {"unassigned": "true"},
     "select count(*) from service_request where assigned_to is null"),
    ("KPI Activities", "/activities", {},
     "select count(*) from activity"),
    ("Notifications panel", "/notifications", {},
     "select count(*) from notification"),
]

#: Occupancy chart slices: one exact COUNT per `amenity_status` row.
STATUS_SLICES = ["Available", "Occupied", "Unavailable", "Allotted"]


def _token(username: str) -> str:
    session = SessionLocal()
    try:
        user_id = session.execute(
            text("SELECT id FROM app_user WHERE user_name = :u"), {"u": username}
        ).scalar_one_or_none()
    finally:
        session.close()
    if user_id is None:
        raise SystemExit(
            f"seeded user {username!r} is absent; run `python -m seeds.run_seed`"
        )
    return create_access_token(user_id)[0]


def _get(path: str, token: str, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)
    except urllib.error.URLError as exc:
        raise SystemExit(f"cannot reach {BASE}: {exc.reason}. Is uvicorn running?")


def main() -> int:
    username = sys.argv[1] if len(sys.argv) > 1 else "arjun.menon"
    token = _token(username)
    session = SessionLocal()

    status, me = _get("/auth/me", token)
    if status != 200:
        raise SystemExit(f"GET /auth/me answered {status}")
    print(f"as {me['user_name']} (role_types={me['role_types']})\n")

    checks = list(CHECKS)
    # The four chart slices, resolved through the lookup table rather than by
    # assuming which id means what.
    for name in STATUS_SLICES:
        status_id = session.execute(
            text("SELECT id FROM amenity_status WHERE amenity_status_name = :n"),
            {"n": name},
        ).scalar_one_or_none()
        if status_id is None:
            print(f"  note: amenity_status {name!r} is not a row; slice skipped")
            continue
        checks.append((
            f"Occupancy slice {name}", "/occupancy", {"status": status_id},
            "select count(*) from amenity a join amenity_status s on s.id = a.status "
            f"where s.amenity_status_name = '{name}'",
        ))

    print(f"{'widget / KPI':28s} {'API':>8s} {'SQL':>8s}  verdict")
    print("-" * 58)

    mismatches = 0
    skipped = 0
    for label, path, params, query in checks:
        code, body = _get(path, token, page_size=1, **params)
        if code == 403:
            # A role without the module grant is a correct answer, not a failure.
            print(f"{label:28s} {'403':>8s} {'-':>8s}  no grant, skipped")
            skipped += 1
            continue
        if code != 200:
            print(f"{label:28s} {code:>8} {'-':>8s}  UNEXPECTED {json.dumps(body)[:60]}")
            mismatches += 1
            continue
        api = body["total"]
        sql = session.execute(text(query)).scalar_one()
        ok = api == sql
        mismatches += 0 if ok else 1
        print(f"{label:28s} {api:>8} {sql:>8}  {'match' if ok else 'MISMATCH'}")

    # The energy tile: a stored SUM and COUNT, with no unit anywhere.
    code, summary = _get("/energy-stats/summary", token, group_by="day")
    if code == 403:
        print(f"{'Energy tile':28s} {'403':>8s} {'-':>8s}  no grant, skipped")
        skipped += 1
    else:
        sql_sum, sql_count = session.execute(
            text("select coalesce(sum(energy_consumed), 0), count(*) from energy_stat")
        ).one()
        sum_ok = abs(summary["total_energy_consumed"] - float(sql_sum)) < 1e-6
        count_ok = summary["reading_count"] == sql_count
        mismatches += (0 if sum_ok else 1) + (0 if count_ok else 1)
        print(f"{'Energy tile SUM':28s} {round(summary['total_energy_consumed'], 3):>8} "
              f"{round(float(sql_sum), 3):>8}  {'match' if sum_ok else 'MISMATCH'}")
        print(f"{'Energy tile readings':28s} {summary['reading_count']:>8} "
              f"{sql_count:>8}  {'match' if count_ok else 'MISMATCH'}")
        # energy_stat has no unit column; the API must keep saying so.
        assert summary["energy_unit"] is None, "energy_unit must stay null"
        print(f"{'Energy tile unit':28s} {'null':>8} {'n/a':>8}  none stored, none shown")

    session.close()
    print(f"\n{mismatches} mismatch(es), {skipped} skipped for lack of a module grant.")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
