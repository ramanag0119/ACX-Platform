"""Phase 1.8 seed-data validation.

Run:  python -m pytest tests/test_seed_data.py -q

These assert that the demo dataset in `hms_db` is present, relationally
coherent, and safe to re-seed. They read the database only -- no test writes,
and none of them modifies the schema.

Skipped wholesale when the database has not been seeded, so the schema suite
still passes on a bare foundation.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.models import (
    AccessKey,
    Activity,
    ActivityNotifier,
    Amenity,
    AmenityStatus,
    AppUser,
    APPROVED_TABLES,
    Device,
    DeviceAlert,
    DeviceHealthStat,
    DeviceIncident,
    DeviceStat,
    EnergyStat,
    Facility,
    IncidentHistory,
    Invoice,
    MaintenanceRequest,
    Notification,
    NotificationReceiver,
    Organisation,
    Package,
    Property,
    PropertyChain,
    Role,
    RoleModule,
    RoleModulePermission,
    RoomAllocation,
    ServiceCategoryItem,
    ServiceRequest,
    Stay,
    StayUser,
    UserDeviceAcl,
    UserRole,
)
from app.models.enums import ALL_ENUMS
from seeds.data import reference as ref


@pytest.fixture(scope="module")
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="module", autouse=True)
def require_seeded(session):
    n = session.execute(select(func.count()).select_from(Facility)).scalar_one()
    if not n:
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# ---------------------------------------------------------------------------
# 1-3. Seed completed, is repeatable, and created no duplicates
# ---------------------------------------------------------------------------


def test_every_approved_table_has_rows(session):
    empty = [
        t
        for t in APPROVED_TABLES
        if session.execute(text(f'SELECT count(*) FROM public."{t}"')).scalar_one() == 0
    ]
    assert not empty, f"tables left unseeded: {empty}"


def test_single_facility_and_organisation(session):
    """Re-running the seed must not add a second copy of the demo facility."""
    assert session.execute(select(func.count()).select_from(Organisation)).scalar_one() == 1
    assert session.execute(select(func.count()).select_from(Facility)).scalar_one() == 1


@pytest.mark.parametrize(
    "model,column",
    [
        (Facility, "facility_uid"),
        (Organisation, "org_uid"),
        (AppUser, "user_uid"),
        (AppUser, "user_name"),
        (Stay, "internal_stay_ref_number"),
        (Invoice, "invoice_number"),
        (ServiceRequest, "ref_number"),
        (Device, "device_uid"),
    ],
)
def test_no_duplicate_natural_keys(session, model, column):
    """The idempotency guarantee, checked at the data level."""
    col = getattr(model, column)
    dupes = session.execute(
        select(col, func.count())
        .where(col.is_not(None))
        .group_by(col)
        .having(func.count() > 1)
    ).all()
    assert not dupes, f"duplicate {model.__tablename__}.{column}: {dupes}"


# ---------------------------------------------------------------------------
# 4-6. No FK, NOT NULL or ENUM violations
# ---------------------------------------------------------------------------


def test_no_orphaned_foreign_keys(session):
    """Every FK value resolves. Re-validating the constraints proves the seed
    ran with them fully enabled -- nothing was bypassed."""
    rows = session.execute(
        text(
            """
            SELECT conrelid::regclass::text AS child, conname
            FROM pg_constraint
            WHERE contype = 'f'
              AND connamespace = 'public'::regnamespace
            ORDER BY 1, 2
            """
        )
    ).all()
    assert len(rows) == 240
    for child, conname in rows:
        # Raises if any row violates the constraint.
        session.execute(text(f'ALTER TABLE {child} VALIDATE CONSTRAINT "{conname}"'))


def test_enum_columns_hold_only_declared_labels(session):
    """A value outside the enum cannot physically exist, but this also proves
    the seed did not silently normalise capitalisation."""
    by_name = {e.name: list(e.enums) for e in ALL_ENUMS}
    cols = session.execute(
        text(
            """
            SELECT c.table_name, c.column_name, c.udt_name
            FROM information_schema.columns c
            JOIN pg_type t ON t.typname = c.udt_name
            WHERE c.table_schema = 'public' AND t.typtype = 'e'
            ORDER BY 1, 2
            """
        )
    ).all()
    assert cols, "expected enum-typed columns"
    for table, column, udt in cols:
        used = session.execute(
            text(f'SELECT DISTINCT "{column}"::text FROM public."{table}" '
                 f'WHERE "{column}" IS NOT NULL')
        ).scalars().all()
        unknown = set(used) - set(by_name[udt])
        assert not unknown, f"{table}.{column} holds undeclared values: {unknown}"


def test_reference_tables_match_the_ikanos_dump(session):
    """Lookup rows must be the real IKANOS vocabulary, not invented values."""
    checks = [
        ("amenity_status", "amenity_status_name", ref.AMENITY_STATUSES),
        ("amenity_condition", "name", ref.AMENITY_CONDITIONS),
        ("service_type", "name", ref.SERVICE_TYPES),
        ("service_status", "name", ref.SERVICE_STATUSES),
        ("alert_type", "name", ref.ALERT_TYPES),
        ("incident_status", "name", ref.INCIDENT_STATUSES),
        ("incident_event", "name", ref.INCIDENT_EVENTS),
        ("key_type", "name", ref.KEY_TYPES),
        ("entity_type", "entity_type", ref.ENTITY_TYPES),
        ("occasion_type", "occasion_type", ref.OCCASION_TYPES),
    ]
    for table, name_col, expected in checks:
        rows = session.execute(
            text(f'SELECT id, "{name_col}" FROM public."{table}" ORDER BY id')
        ).all()
        assert [(r[0], r[1]) for r in rows] == [(i, n) for i, n in expected], table


def test_role_modules_are_the_18_sidebar_modules(session):
    names = session.execute(
        select(RoleModule.module_name).order_by(RoleModule.id)
    ).scalars().all()
    assert names == [n for _i, n, _r, _w in ref.ROLE_MODULES]
    assert len(names) == 18


def test_device_params_are_the_35_ikanos_parameters(session):
    n = session.execute(text("SELECT count(*) FROM device_param")).scalar_one()
    assert n == 35
    units = session.execute(
        text("SELECT DISTINCT unit FROM device_param WHERE unit IS NOT NULL")
    ).scalars().all()
    assert "kWh" in units and "V" in units and "Hz" in units


def test_all_239_countries_present(session):
    n = session.execute(text("SELECT count(*) FROM country")).scalar_one()
    assert n == 239


# ---------------------------------------------------------------------------
# 7-8. Parent-child relationships and workflow chains
# ---------------------------------------------------------------------------


def test_chain_facility_to_property_to_chain_to_room(session):
    room = session.execute(
        select(Amenity).where(Amenity.name == "101")
    ).scalar_one()
    chain = session.get(PropertyChain, room.property_chain_id)
    assert chain is not None
    tower = session.get(Property, chain.level_one_id)
    floor = session.get(Property, chain.level_two_id)
    assert tower.property_name == "Tower A"
    assert floor.property_name == "Floor 1"
    assert room.facility_id == tower.facility_id


def test_chain_user_to_role_to_module_permission(session):
    admin = session.execute(
        select(AppUser).where(AppUser.user_name == "arjun.menon")
    ).scalar_one()
    link = session.execute(
        select(UserRole).where(UserRole.app_user_id == admin.id)
    ).scalar_one()
    role = session.get(Role, link.role_id)
    assert role.role_type == "admin"
    perms = session.execute(
        select(RoleModulePermission).where(RoleModulePermission.role_id == role.id)
    ).scalars().all()
    assert len(perms) == 18, "the administrator role must reach every module"
    assert all(p.read_access for p in perms)


def test_chain_guest_to_stay_to_room_allocation(session):
    stay = session.execute(
        select(Stay).where(Stay.internal_stay_ref_number == "STY-2026-0001")
    ).scalar_one()
    assert stay.status == "active"
    guest = session.get(AppUser, stay.booking_user_id)
    assert guest.is_staff == 0
    alloc = session.execute(
        select(RoomAllocation).where(RoomAllocation.stay_id == stay.id)
    ).scalar_one()
    room = session.get(Amenity, alloc.room_id)
    assert room.name == "101"
    occupants = session.execute(
        select(StayUser).where(StayUser.stay_id == stay.id)
    ).scalars().all()
    assert len(occupants) == 2, "stay 0001 has a second occupant"


def test_stay_lifecycle_states_are_represented(session):
    states = set(session.execute(select(Stay.status)).scalars().all())
    assert {"pending", "active", "checked out", "cancelled"} <= states


def test_cancelled_stay_has_no_room_allocation(session):
    stay = session.execute(
        select(Stay).where(Stay.status == "cancelled")
    ).scalars().first()
    allocs = session.execute(
        select(RoomAllocation).where(RoomAllocation.stay_id == stay.id)
    ).scalars().all()
    assert not allocs


def test_chain_service_catalogue_to_request_to_item(session):
    sr = session.execute(
        select(ServiceRequest).where(ServiceRequest.ref_number == "SR-2026-0002")
    ).scalar_one()
    assert sr.stay_id is not None and sr.amenity_id is not None
    items = session.execute(
        text("SELECT item_id, quantity FROM service_request_item "
             "WHERE service_request_id = :sid"),
        {"sid": sr.id},
    ).all()
    assert items
    for item_id, qty in items:
        item = session.get(ServiceCategoryItem, item_id)
        assert item is not None and qty > 0


def test_service_statuses_span_the_real_vocabulary(session):
    used = set(session.execute(select(ServiceRequest.status)).scalars().all())
    assert len(used) >= 4, "demo should exercise several service statuses"
    assert used <= {1, 2, 3, 4, 5}


def test_chain_device_to_device_stats(session):
    device = session.execute(
        select(Device).where(Device.device_name.is_not(None),
                             Device.health_status == "Active")
    ).scalars().first()
    n = session.execute(
        select(func.count()).select_from(DeviceStat)
        .where(DeviceStat.device_id == device.id)
    ).scalar_one()
    assert n > 0
    health = session.execute(
        select(func.count()).select_from(DeviceHealthStat)
        .where(DeviceHealthStat.device_id == device.id)
    ).scalar_one()
    assert health > 0


def test_offline_device_reports_no_telemetry(session):
    """The 106 hub is offline; an offline device must not be emitting stats."""
    offline = session.execute(
        select(Device).where(Device.health_status == "Inactive")
    ).scalars().all()
    assert offline, "demo should include offline devices"
    for device in offline:
        n = session.execute(
            select(func.count()).select_from(DeviceStat)
            .where(DeviceStat.device_id == device.id)
        ).scalar_one()
        assert n == 0, f"{device.device_uid} is Inactive but reported telemetry"


def test_chain_device_to_alert_to_incident_to_history(session):
    incident = session.execute(
        select(DeviceIncident).where(DeviceIncident.latest_alert_id.is_not(None))
    ).scalars().first()
    alert = session.get(DeviceAlert, incident.latest_alert_id)
    assert alert is not None
    # An incident must agree with the alert it was raised from.
    assert alert.device_id == incident.device_id
    assert alert.amenity_id == incident.amenity_id
    assert alert.alert_type == incident.alert_type
    history = session.execute(
        select(IncidentHistory).where(IncidentHistory.incident_id == incident.id)
    ).scalars().all()
    assert history, "every incident needs an audit trail"


def test_alert_severity_uses_only_the_two_real_values(session):
    used = set(session.execute(select(DeviceAlert.alert_severity)).scalars().all())
    assert used <= {"warning", "critical"}
    assert "Info" not in used


def test_incident_statuses_span_unread_to_resolved(session):
    used = set(
        session.execute(select(DeviceIncident.current_incident_status)).scalars().all()
    )
    assert {1, 4} <= used, "expect at least an Unread and a Resolved incident"


def test_chain_user_to_notification(session):
    receiver = session.execute(
        select(NotificationReceiver)
        .where(NotificationReceiver.app_user_id.is_not(None))
    ).scalars().first()
    notification = session.get(Notification, receiver.notification_id)
    assert notification is not None
    user = session.get(AppUser, receiver.app_user_id)
    assert receiver.email == user.email
    results = session.execute(
        text("SELECT count(*) FROM notification_result WHERE receiver_id = :rid"),
        {"rid": receiver.id},
    ).scalar_one()
    assert results > 0


def test_activity_feed_has_per_user_read_state(session):
    activity = session.execute(select(Activity)).scalars().first()
    notifiers = session.execute(
        select(ActivityNotifier).where(ActivityNotifier.activity_id == activity.id)
    ).scalars().all()
    assert notifiers
    assert all(n.status in {"0", "1", "2"} for n in notifiers)


def test_chain_device_to_energy_stats(session):
    rows = session.execute(
        select(EnergyStat).order_by(EnergyStat.hour)
    ).scalars().all()
    assert rows, "energy_stat must be populated"
    # hour is "hours elapsed since 2000", so it is far larger than a year count
    # and strictly increasing across the demo window.
    assert rows[0].hour > 200000
    hours_seen = {r.hour for r in rows}
    assert len(hours_seen) >= 24, "expect at least a day of hourly readings"
    for row in rows:
        assert session.get(Amenity, row.amenity_id) is not None


def test_chain_stay_to_key_to_acl(session):
    key = session.execute(
        select(AccessKey).where(AccessKey.stay_id.is_not(None))
    ).scalars().first()
    acl = session.get(UserDeviceAcl, key.user_device_acl_id)
    assert acl is not None
    assert acl.stay_id == key.stay_id
    assert acl.end_time > acl.start_time


def test_maintenance_request_types_are_the_three_real_values(session):
    used = set(
        session.execute(select(MaintenanceRequest.maintenance_request_type))
        .scalars().all()
    )
    assert used <= {"scheduled", "planned", "disinfection"}
    assert len(used) == 3


def test_room_statuses_cover_the_four_ikanos_values(session):
    used = set(session.execute(select(Amenity.status)).scalars().all())
    assert used == {0, 1, 2, 3}, "demo should show every amenity status"
    names = {
        s.id: s.amenity_status_name
        for s in session.execute(select(AmenityStatus)).scalars().all()
    }
    assert names[0] == "Available" and names[1] == "Occupied"


# ---------------------------------------------------------------------------
# Fields the blueprint refuses to invent must stay unpopulated / absent
# ---------------------------------------------------------------------------


def test_no_price_was_smuggled_onto_package(session):
    """`packages` has no price column, and none may hide in metadata either.
    OPEN DECISION #10 is still unresolved."""
    cols = session.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='package'")
    ).scalars().all()
    assert "price" not in cols
    assert not any("price" in c or "rate" in c or "tariff" in c for c in cols)


def test_only_service_items_carry_a_price(session):
    """`service_category_item.price_per_unit` is the only price in the schema."""
    priced = session.execute(
        text("SELECT table_name, column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND column_name LIKE '%%price%%'")
    ).all()
    assert {(t, c) for t, c in priced} == {
        ("service_category_item", "price_per_unit"),
        ("service_request_item", "price_per_unit"),
    }
    n = session.execute(
        select(func.count()).select_from(ServiceCategoryItem)
        .where(ServiceCategoryItem.price_per_unit.is_not(None))
    ).scalar_one()
    assert n > 0


def test_invoice_has_no_payment_status(session):
    cols = session.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name='invoice'")
    ).scalars().all()
    assert "status" not in cols
    # Amounts are still internally consistent: total = net + tax.
    for inv in session.execute(select(Invoice)).scalars().all():
        assert inv.total_amount == inv.net_amount + inv.total_tax


def test_seed_used_synthetic_identities_only(session):
    """Every demo identity must be unmistakably fake."""
    emails = session.execute(
        select(AppUser.email).where(AppUser.email.is_not(None))
    ).scalars().all()
    assert emails
    assert all(e.endswith(".invalid") for e in emails), (
        "demo emails must use the reserved .invalid TLD"
    )
    phones = session.execute(select(AppUser.phone_number)).scalars().all()
    assert all(p.startswith("+9100000") for p in phones)
    hashes = session.execute(
        select(AppUser.password_hash).where(AppUser.password_hash.is_not(None))
    ).scalars().all()
    assert all(h == "!seed-no-login" for h in hashes), (
        "the seed must never write a usable credential"
    )
