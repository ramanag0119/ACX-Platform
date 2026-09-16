"""Step 8 - telemetry, health, battery, energy and dashboard KPIs.

Telemetry uses the IKANOS EAV pair: `device_param` names the parameter and its
unit, `device_stat` holds one row per parameter per reading. The invented
`energy_data` / `sensor_reading` tables do not exist and nothing here recreates
them.

Energy is hourly only. `energy_stat.hour` is "hours elapsed since 2000" -- read
from the column comment in the dump, not a timestamp. There is no `avg_power`
or `max_power`: those are query-time derivations in the approved design.

Chains proven here:  device -> device_stat -> device_param
                     device -> device_health_stat
                     device -> energy_stat -> amenity
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    BatteryLifeStat,
    DailyDualDataPoint,
    DeviceCurrentStat,
    DeviceHealthStat,
    DeviceStat,
    EnergyStat,
    OtherDevice,
    SensorOperationStat,
)
from seeds.helpers import DEMO_NOW, days, did, hours, ikanos_hour, upsert

#: 12 hours of readings, on the hour. Enough for a chart, small enough to stay
#: fast and readable during a demo.
READING_HOURS = 12

# device_param ids per device type, from the real IKANOS device_params table.
# (param_id, base value, per-hour drift)
PARAMS_BY_TYPE = {
    1: [  # Intellihub
        (11, 37.140, 0.42),   # active_energy kWh
        (12, 41.20, 0.15),    # temperature C
        (25, 259.0, -0.35),   # voltage V
        (26, 0.35, 0.01),     # current Amps
        (27, 0.370, 0.006),   # active_power KW
    ],
    2: [  # AirQ
        (1, 24.5, 0.12),      # room_temperature
        (2, 104.0, 1.8),      # air_quality (IAQ)
        (3, 29.8, 0.35),      # humidity r.h
        (4, 99960.0, 3.0),    # pressure Pa
    ],
    3: [  # Mikos
        (5, 258.0, -0.30),    # voltage V
        (6, 0.42, 0.015),     # current Amps
        (7, 4.960, 0.21),     # active_energy kWh
        (18, 0.070, 0.004),   # active_power KW
        (21, 50.1, -0.02),    # frequency Hz
    ],
    4: [  # Kleio
        (8, 100.0, -0.55),    # battery_percentage
        (9, 0.0, 0.0),        # lock_status (0 = closed)
        (10, 31.5, 0.08),     # temperature
    ],
}

# Rooms whose Mikos/Intellihub feed the hourly energy rollup.
ENERGY_SOURCES = [("101", "101-mik"), ("205", "205-mik"), ("106", "106-mik")]

#: daily_dual_data_point.metric_type -- these five ARE the Caleido At Work KPIs.
KPI_SERIES = [
    ("smart room", 11.0, 14.0),
    ("service request", 5.0, 7.0),
    ("checkout", 2.0, 6.0),
    ("booking", 4.0, 6.0),
    ("guest room", 18.0, 24.0),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    devices = ctx["devices"]
    rooms = ctx["rooms"]

    # ---- device_stat --------------------------------------------------------
    # Natural key (device_id, device_param_id, timestamp) makes this idempotent
    # without abusing legacy_id, which belongs to IKANOS migration.
    n_stats = 0
    for key, device in devices.items():
        if device.health_status != "Active":
            continue  # an inactive device reports nothing -- that is the point
        for param_id, base, drift in PARAMS_BY_TYPE[device.device_type]:
            for h in range(READING_HOURS):
                moment = DEMO_NOW - hours(READING_HOURS - h)
                value = base + drift * h
                upsert(
                    session,
                    DeviceStat,
                    {
                        "device_id": device.id,
                        "device_param_id": param_id,
                        "timestamp": moment,
                    },
                    device_param_value=f"{value:.3f}",
                    is_other_device=None,
                    created_on=moment,
                    updated_on=moment,
                )
                n_stats += 1
    counts["device_stat"] = n_stats

    # ---- device_current_stat -----------------------------------------------
    n_current = 0
    for key, device in devices.items():
        latest = {}
        for param_id, base, drift in PARAMS_BY_TYPE[device.device_type]:
            latest[str(param_id)] = round(base + drift * (READING_HOURS - 1), 3)
        upsert(
            session,
            DeviceCurrentStat,
            {"id": did("device_current_stat", key)},
            device_id=device.id,
            device_stats={
                "params": latest,
                "health": device.health_status,
                "captured_at": DEMO_NOW.isoformat(),
            },
            is_other_device=None,
        )
        n_current += 1
    counts["device_current_stat"] = n_current

    # ---- device_health_stat -------------------------------------------------
    n_health = 0
    for key, device in devices.items():
        for h in range(READING_HOURS):
            moment = DEMO_NOW - hours(READING_HOURS - h)
            temp = device.device_temperature or Decimal("0.00")
            upsert(
                session,
                DeviceHealthStat,
                {"device_id": device.id, "created_on": moment},
                device_health_status=device.health_status or "Inactive",
                device_temperature=temp,
                updated_on=moment,
            )
            n_health += 1
    counts["device_health_stat"] = n_health

    # ---- battery_life_stat (Kleio locks only) -------------------------------
    n_battery = 0
    for key, device in devices.items():
        if device.device_type != 4:
            continue
        for cycle in (1, 2, 3):
            upsert(
                session,
                BatteryLifeStat,
                {"device_id": device.id, "cycle_number": cycle},
                initial_battery_percentage=Decimal("100.00"),
                latest_battery_percentage=Decimal("100.00") - Decimal(cycle * 12),
                battery_life=Decimal("180.00") - Decimal(cycle * 15),
            )
            n_battery += 1
    counts["battery_life_stat"] = n_battery

    # ---- sensor_operation_stat ("Smart Rooms Online") -----------------------
    n_sensor = 0
    for key, device in devices.items():
        for d in range(3):
            stats_date = (DEMO_NOW - days(d)).date()
            pct = Decimal("99.20") if device.health_status == "Active" else Decimal("6.40")
            upsert(
                session,
                SensorOperationStat,
                {"device_id": device.id, "stats_date": stats_date},
                amenity_id=device.amenity_id,
                operation_percentage=pct,
            )
            n_sensor += 1
    counts["sensor_operation_stat"] = n_sensor

    # ---- energy_stat (hourly, composite natural PK) -------------------------
    n_energy = 0
    for room_name, device_key in ENERGY_SOURCES:
        device = devices[device_key]
        # device_name is varchar(11) in IKANOS.
        device_name = device_key[:11]
        for h in range(24):
            moment = DEMO_NOW - hours(24 - h)
            # A plausible daily load curve; the 106 meter is offline so it
            # reports near-zero.
            if device.health_status != "Active":
                consumed = 0.02
            else:
                hour_of_day = moment.hour
                peak = 1.0 if 7 <= hour_of_day <= 22 else 0.35
                consumed = round(0.42 * peak + (h % 5) * 0.03, 3)
            upsert(
                session,
                EnergyStat,
                {
                    "device_name": device_name,
                    "facility_id": facility.id,
                    "amenity_id": rooms[room_name].id,
                    "hour": ikanos_hour(moment),
                },
                energy_consumed=consumed,
            )
            n_energy += 1
    counts["energy_stat"] = n_energy

    # ---- other_device (third-party meters) ----------------------------------
    n_other = 0
    for meter in ("MAINS-DG-01", "MAINS-EB-01"):
        for h in range(6):
            moment = DEMO_NOW - hours(6 - h)
            upsert(
                session,
                OtherDevice,
                {"device_name": meter, "timestamp": moment},
                msg_id=f"{meter}-{h:02d}",
                voltage=241.5 + h * 0.4,
                current=12.4 + h * 0.2,
                power=2.98 + h * 0.05,
                power_factor=0.98,
                all_energy=14820.0 + h * 3.1,
                thirty_day_energy=920.0 + h * 3.1,
                today_energy=31.0 + h * 3.1,
                current_hour_energy=3.1,
                ec=None,
                msg_string={"meter": meter, "seeded": True},
            )
            n_other += 1
    counts["other_device"] = n_other

    # ---- daily_dual_data_point (dashboard KPI pairs) ------------------------
    n_kpi = 0
    for metric_type, numerator, denominator in KPI_SERIES:
        for d in range(7):
            metric_date = (DEMO_NOW - days(d)).date()
            upsert(
                session,
                DailyDualDataPoint,
                {"metric_date": metric_date, "metric_type": metric_type},
                dp_1=Decimal(str(round(numerator - d * 0.5, 2))),
                dp_2=Decimal(str(denominator)),
                facility_id=facility.id,
            )
            n_kpi += 1
    counts["daily_dual_data_point"] = n_kpi

    return counts
