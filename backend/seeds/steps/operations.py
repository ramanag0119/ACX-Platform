"""Step 11 - job orders, digital keys, scheduler, marketing and occasions.

Covers the remaining approved tables that carry meaningful workflow data:

    job_order -> job_order_device / job_order_amenity
    user_device_acl -> access_key -> lock_activity_log
    scheduler_job -> scheduler_job_execution
    promo_code -> promo_code_amenity
    occasion_type -> occasion          (occasion_type = 'Holiday' IS Holidays)
    facility_event

NOTE: `occasion` has NO `lock_message` column, which is what the HMS Holidays
screen is built around. Nothing is invented -- `notification_template` carries
the hub message, exactly as the blueprint records under OPEN DECISION #5.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    AccessKey,
    FacilityEvent,
    JobOrder,
    JobOrderAmenity,
    JobOrderDevice,
    LockActivityLog,
    Occasion,
    PromoCode,
    PromoCodeAmenity,
    SchedulerJob,
    SchedulerJobExecution,
    UserDeviceAcl,
)
from seeds.helpers import DEMO_NOW, days, did, hours, upsert

# key_type ids: 1 Primary, 2 Shared, 3 Staff, 4 Default
PRIMARY_KEY, SHARED_KEY, STAFF_KEY, DEFAULT_KEY = 1, 2, 3, 4

# (key, reference, type_of_work, status, assignee, devices, rooms, days offset)
JOB_ORDERS = [
    ("jo-install-301", "JO-2026-0001", "installation", "pending", "vikram.rao",
     [], ["301", "302"], +5),
    ("jo-replace-106hub", "JO-2026-0002", "replacement", "pending", "vikram.rao",
     ["106-hub"], ["106"], +1),
    ("jo-troubleshoot-104", "JO-2026-0003", "troubleshoot", "completed",
     "vikram.rao", ["104-kle"], ["104"], -3),
]

# (key, stay, guest, room, lock device, key type)
KEYS = [
    ("key-101-primary", "STY-2026-0001", "aarav.sharma", "101", "101-kle", PRIMARY_KEY),
    ("key-101-shared", "STY-2026-0001", "priya.nair", "101", "101-kle", SHARED_KEY),
    ("key-205-primary", "STY-2026-0002", "meera.krishnan", "205", "205-kle", PRIMARY_KEY),
    ("key-106-primary", "STY-2026-0006", "ishaan.gupta", "106", "106-kle", PRIMARY_KEY),
]

# Staff key tied to a maintenance request rather than a stay.
STAFF_KEYS = [
    ("key-104-staff", "vikram.rao", "104", "104-kle", "mr-hvac-quarterly"),
]

# (key, lock device, room, user, stay, event, mode, hours ago)
LOCK_EVENTS = [
    ("lock-101-in", "101-kle", "101", "aarav.sharma", "STY-2026-0001",
     "unlocked", "app", 47),
    ("lock-101-close", "101-kle", "101", "aarav.sharma", "STY-2026-0001",
     "locked", "app", 46),
    ("lock-101-keypad", "101-kle", "101", "priya.nair", "STY-2026-0001",
     "unlocked", "keypad", 20),
    ("lock-205-in", "205-kle", "205", "meera.krishnan", "STY-2026-0002",
     "unlocked", "app", 23),
    ("lock-106-in", "106-kle", "106", "ishaan.gupta", "STY-2026-0006",
     "unlocked", "keypad", 40),
]

# (key, job_key, job_name, status, dynamic, schedule payload)
SCHEDULER_JOBS = [
    ("checkout-reminder", "hms.checkout.reminder", "Checkout reminder", "active",
     0, {"cron": "0 * * * *", "template": "PreCheckoutNotification"}),
    ("stay-expiry", "hms.stay.expiry", "Stay expiry sweep", "active",
     0, {"cron": "*/15 * * * *"}),
    ("housekeeping-daily", "hms.housekeeping.daily", "Daily housekeeping plan",
     "active", 0, {"cron": "0 5 * * *"}),
    ("sanitation-weekly", "hms.sanitation.weekly", "Weekly sanitation plan",
     "inactive", 1, {"cron": "0 6 * * 2,5"}),
    ("device-health-sweep", "hms.device.health", "Device health sweep", "active",
     0, {"cron": "*/5 * * * *"}),
]

# (scheduler job key, hours ago, status, duration ms)
EXECUTIONS = [
    ("checkout-reminder", 1, "passed", 412),
    ("checkout-reminder", 2, "passed", 388),
    ("stay-expiry", 1, "passed", 96),
    ("device-health-sweep", 1, "passed", 145),
    ("device-health-sweep", 2, "failed", 30012),
    ("housekeeping-daily", 7, "passed", 2310),
]

# (key, offer name, code, discount %, max, min, rooms, offered by, icon, status)
PROMO_CODES = [
    ("monsoon", "Monsoon Getaway", "MONSOON25", 25, Decimal("2500.00"),
     Decimal("4000.00"), ["301", "302", "303"], "Ikanos Grand",
     "offer-icon-monsoon", 1),
    ("corporate", "Corporate Long Stay", "CORP15", 15, Decimal("5000.00"),
     Decimal("10000.00"), ["201", "202", "203"], "Inspornics Hospitality",
     "offer-icon-corporate", 1),
    ("earlybird", "Early Bird", "EARLY10", 10, Decimal("1000.00"),
     Decimal("2000.00"), ["101", "102"], "Ikanos Grand", None, 0),  # withdrawn
]

# (key, name, venue, start offset days, expected, interested, cancelled?)
EVENTS = [
    ("newyear-gala", "New Year Gala Dinner", "Grand Ballroom", +14, 250, 96, False),
    ("tech-summit", "Chennai Tech Summit", "Conference Room 1", +30, 120, 41, False),
    ("wine-tasting", "Wine Tasting Evening", "Rooftop Lounge", +7, 60, 12, True),
]

# (key, name, occasion_type id, month, day, start, end, repeatable)
OCCASIONS = [
    ("diwali", "Diwali", 4, 11, 8, date(2026, 11, 8), date(2026, 11, 10), True),
    ("christmas", "Christmas", 4, 12, 25, date(2026, 12, 25), date(2026, 12, 26), True),
    ("newyear", "New Year", 4, 1, 1, date(2027, 1, 1), date(2027, 1, 1), True),
    ("pongal", "Pongal", 1, 1, 14, date(2027, 1, 14), date(2027, 1, 17), True),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    users = ctx["users"]
    rooms = ctx["rooms"]
    stays = ctx["stays"]
    devices = ctx["devices"]
    amenity_types = ctx["amenity_types"]

    # ---- job orders ---------------------------------------------------------
    n_jo_devices = n_jo_amenities = 0
    for key, ref_no, work, status, assignee, device_keys, room_names, offset in JOB_ORDERS:
        job = upsert(
            session,
            JobOrder,
            {"id": did("job_order", key)},
            order_reference=ref_no,
            description=f"Demo job order {ref_no}",
            type_of_work=work,
            work_commence=DEMO_NOW + days(offset),
            estimated_completion_date=DEMO_NOW + days(offset + 1),
            authentication_code=f"JOB{ref_no[-4:]}",
            assigned_to=users[assignee].id,
            job_order_status=status,
            completed_on=DEMO_NOW + days(offset) if status == "completed" else None,
            status=1,
            created_by=users["kavya.iyer"].id,
        )
        for device_key in device_keys:
            upsert(
                session,
                JobOrderDevice,
                {"job_order_id": job.id, "device_id": devices[device_key].id},
            )
            n_jo_devices += 1
        for room_name in room_names:
            upsert(
                session,
                JobOrderAmenity,
                {"job_order_id": job.id, "amenity_id": rooms[room_name].id},
            )
            n_jo_amenities += 1
    counts["job_order"] = len(JOB_ORDERS)
    counts["job_order_device"] = n_jo_devices
    counts["job_order_amenity"] = n_jo_amenities

    # ---- access control -----------------------------------------------------
    # A key is always backed by a time-boxed ACL; end_time is why a key expires
    # automatically at checkout.
    n_acl = n_keys = 0
    for key, stay_ref, user_key, room, lock_key, key_type in KEYS:
        stay = stays[stay_ref]
        lock = devices[lock_key]
        acl = upsert(
            session,
            UserDeviceAcl,
            {"id": did("user_device_acl", key)},
            app_user_id=users[user_key].id,
            device_type_id=lock.device_type,
            device_id=lock.id,
            amenity_type_id=rooms[room].amenity_type_id,
            amenity_id=rooms[room].id,
            stay_id=stay.id,
            start_time=stay.expected_checkin_time,
            end_time=stay.expected_checkout_time,
            status_id=1,
            created_by=users["rahul.das"].id,
        )
        n_acl += 1
        upsert(
            session,
            AccessKey,
            {"id": did("access_key", key)},
            user_device_acl_id=acl.id,
            app_key=f"AK{n_keys:08d}",
            keypad_key=f"{100000 + n_keys * 7:06d}",
            key_type=key_type,
            device_id=lock.id,
            stay_id=stay.id,
            status=1,
            created_by=users["rahul.das"].id,
        )
        n_keys += 1

    for key, user_key, room, lock_key, maintenance_key in STAFF_KEYS:
        lock = devices[lock_key]
        maintenance = ctx[f"maintenance:{maintenance_key}"]
        acl = upsert(
            session,
            UserDeviceAcl,
            {"id": did("user_device_acl", key)},
            app_user_id=users[user_key].id,
            device_type_id=lock.device_type,
            device_id=lock.id,
            amenity_type_id=rooms[room].amenity_type_id,
            amenity_id=rooms[room].id,
            stay_id=None,
            start_time=DEMO_NOW,
            end_time=DEMO_NOW + days(3),
            status_id=1,
            created_by=users["kavya.iyer"].id,
        )
        n_acl += 1
        upsert(
            session,
            AccessKey,
            {"id": did("access_key", key)},
            user_device_acl_id=acl.id,
            app_key=f"AK{n_keys:08d}",
            keypad_key=f"{100000 + n_keys * 7:06d}",
            key_type=STAFF_KEY,
            device_id=lock.id,
            stay_id=None,
            maintenance_request_id=maintenance.id,
            status=1,
            created_by=users["kavya.iyer"].id,
        )
        n_keys += 1
    counts["user_device_acl"] = n_acl
    counts["access_key"] = n_keys

    for key, lock_key, room, user_key, stay_ref, event, mode, hours_ago in LOCK_EVENTS:
        moment = DEMO_NOW - hours(hours_ago)
        upsert(
            session,
            LockActivityLog,
            {"lock_id": devices[lock_key].id, "timestamp": moment},
            app_user_id=users[user_key].id,
            event=event,
            unlock_mode=mode if event == "unlocked" else None,
            amenity_id=rooms[room].id,
            stay_id=stays[stay_ref].id,
            facility_id=facility.id,
            key_type=PRIMARY_KEY,
            created_on=moment,
            updated_on=moment,
        )
    counts["lock_activity_log"] = len(LOCK_EVENTS)

    # ---- scheduler ----------------------------------------------------------
    jobs = {}
    for key, job_key, job_name, status, dynamic, payload in SCHEDULER_JOBS:
        jobs[key] = upsert(
            session,
            SchedulerJob,
            {"id": did("scheduler_job", key)},
            job_key=job_key,
            job_name=job_name,
            job_data=payload,
            status=status,
            is_dynamic_job=dynamic,
        )
    counts["scheduler_job"] = len(jobs)

    for job_key, hours_ago, status, duration in EXECUTIONS:
        moment = DEMO_NOW - hours(hours_ago)
        upsert(
            session,
            SchedulerJobExecution,
            {"scheduler_job_id": jobs[job_key].id, "job_execution_date": moment},
            job_response=(
                b'{"ok": true}' if status == "passed" else b'{"error": "timeout"}'
            ),
            status=status,
            job_run_duration=duration,
            created_on=moment,
            updated_on=moment,
        )
    counts["scheduler_job_execution"] = len(EXECUTIONS)

    # ---- marketing ----------------------------------------------------------
    n_promo_rooms = 0
    for (key, name, code, discount, max_value, min_value, room_names,
         offered_by, icon_key, status) in PROMO_CODES:
        promo = upsert(
            session,
            PromoCode,
            {"id": did("promo_code", key)},
            offer_name=name,
            promo_code=code,
            start_time=DEMO_NOW - days(10),
            expiry_time=DEMO_NOW + days(45),
            discount_percentage=discount,
            max_discount_value=max_value,
            min_order_value=min_value,
            promo_code_icon=ctx[f"attachment:{icon_key}"].id if icon_key else None,
            promo_code_description=f"{name} demo offer",
            offered_by=offered_by,
            status=status,  # 0 = withdrawn
            created_by=users["kavya.iyer"].id,
        )
        for room_name in room_names:
            upsert(
                session,
                PromoCodeAmenity,
                {"promo_code_id": promo.id, "amenity_id": rooms[room_name].id},
                status=1,
                created_by=users["kavya.iyer"].id,
            )
            n_promo_rooms += 1
    counts["promo_code"] = len(PROMO_CODES)
    counts["promo_code_amenity"] = n_promo_rooms

    for key, name, venue, offset, expected, interested, cancelled in EVENTS:
        upsert(
            session,
            FacilityEvent,
            {"id": did("facility_event", key)},
            facility_id=facility.id,
            name=name,
            venue=venue,  # free text in IKANOS, not an amenity FK
            chief_guests="Demo Chief Guest",
            description=f"{name} at Ikanos Grand Chennai",
            expected_attendees=expected,
            interested_attendees=interested,
            start_date_time=DEMO_NOW + days(offset),
            end_date_time=DEMO_NOW + days(offset) + hours(4),
            image_id=ctx["attachment:event-image-newyear"].id if key == "newyear-gala" else None,
            cancellation_reason="Venue unavailable" if cancelled else None,
            status=0 if cancelled else 1,
            created_by=users["kavya.iyer"].id,
        )
    counts["facility_event"] = len(EVENTS)

    for key, name, otype, month, day, start, end, repeatable in OCCASIONS:
        upsert(
            session,
            Occasion,
            {"id": did("occasion", key)},
            occasion_name=name,
            occasion_type=otype,
            is_repeatable=repeatable,
            # The hub message. There is NO lock_message column in IKANOS.
            notification_template=f"Wishing you a happy {name} from Ikanos Grand.",
            facility_id=facility.id,
            month=month,
            day_of_month=day,
            notify_to_hub=True,
            occasion_start_date=start,
            occasion_end_date=end,
            status=1,
            created_by=users["kavya.iyer"].id,
        )
    counts["occasion"] = len(OCCASIONS)

    # Facility default key user -- the Default Key Settings module.
    facility.default_key_user = users["rahul.das"].id
    session.flush()

    return counts
