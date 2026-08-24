"""Step 2 - organisation, facility, attachments and the property hierarchy.

Demo scenario: one organisation operating one facility, "Ikanos Grand Chennai".

The blueprint (§12.6) flags a bootstrap problem: `organisation.created_by`,
`facility.created_by` and `app_user.created_by` are all NOT NULL and all point
at `app_user`. IKANOS solves it with a first user row whose `created_by` points
at itself. That is exactly what `_bootstrap_user` does here -- PostgreSQL checks
a non-deferred FK after the row lands, so a self-referencing insert is legal.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    AppUser,
    Facility,
    Organisation,
    Property,
    PropertyChain,
    PropertyType,
)
from seeds.helpers import did, upsert

#: One facility only. `daily_dual_data_point`'s primary key is
#: (metric_date, metric_type) and excludes facility_id, so a second facility
#: could not have its own dashboard KPIs. Blueprint OPEN DECISION #6.
FACILITY_UID = "ikg"


def _bootstrap_user(session: Session) -> AppUser:
    """The self-referencing first user that breaks the created_by cycle."""
    uid = did("app_user", "system.bootstrap")
    obj = session.get(AppUser, uid)
    if obj is None:
        obj = AppUser(
            id=uid,
            created_by=uid,  # self-reference, as IKANOS does
            user_uid="demo-uid-system-bootstrap",
            first_name="System",
            last_name="Bootstrap",
            email="system@hms-demo.invalid",
            phone_number="+910000000000",
            is_child=0,
            is_staff=1,
            user_name="system",
        )
        session.add(obj)
        session.flush()
    return obj


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}

    system = _bootstrap_user(session)
    ctx["system_user"] = system
    counts["app_user"] = 1  # the rest are added by the people step

    org = upsert(
        session,
        Organisation,
        {"id": did("organisation", "inspornics")},
        name="Inspornics Hospitality",
        org_uid="ins",
        created_by=system.id,
    )
    counts["organisation"] = 1

    facility = upsert(
        session,
        Facility,
        {"id": did("facility", FACILITY_UID)},
        org_id=org.id,
        facility_uid=FACILITY_UID,
        name="Ikanos Grand Chennai",
        city="Chennai",
        state="Tamil Nadu",
        pin_code="600096",
        guest_rooms=24,
        email="frontdesk@hms-demo.invalid",
        additional_email="ops@hms-demo.invalid",
        google_map_link="https://maps.example.invalid/ikanos-grand-chennai",
        cloud_details={"region": "ap-south-1", "tier": "demo"},
        created_by=system.id,
        # currency_id is left NULL: there is no `currencies` table in IKANOS,
        # so there is nothing to point at. Blueprint OPEN DECISION #1.
    )
    ctx["facility"] = facility
    counts["facility"] = 1

    attachments = [
        ("facility-logo", "ikanos-grand-logo.png", "/uploads/demo/ikanos-grand-logo.png"),
        ("offer-icon-monsoon", "monsoon-offer.png", "/uploads/demo/monsoon-offer.png"),
        ("offer-icon-corporate", "corporate-offer.png", "/uploads/demo/corporate-offer.png"),
        ("event-image-newyear", "new-year-gala.jpg", "/uploads/demo/new-year-gala.jpg"),
        ("guest-doc-aarav", "aarav-passport.jpg", "/uploads/demo/aarav-passport.jpg"),
        ("guest-doc-meera", "meera-aadhaar.jpg", "/uploads/demo/meera-aadhaar.jpg"),
        ("guest-doc-daniel", "daniel-passport.jpg", "/uploads/demo/daniel-passport.jpg"),
        ("service-icon-breakfast", "breakfast.png", "/uploads/demo/breakfast.png"),
    ]
    for key, file_name, file_path in attachments:
        obj = upsert(
            session,
            Attachment,
            {"id": did("attachment", key)},
            facility_id=facility.id,
            file_name=file_name,
            file_path=file_path,
            created_by=system.id,
        )
        ctx[f"attachment:{key}"] = obj
    counts["attachment"] = len(attachments)

    facility.facility_image_id = ctx["attachment:facility-logo"].id
    session.flush()

    # ---- property hierarchy -------------------------------------------------
    # levels = 2 -> property_chain uses level_one (tower) + level_two (floor).
    ptype = upsert(
        session,
        PropertyType,
        {"id": did("property_type", "hotel-building")},
        property_type_name="Hotel Building",
        levels=2,
        facility_id=facility.id,
        status=1,
        property_type_image_id=None,
    )
    counts["property_type"] = 1

    tower = upsert(
        session,
        Property,
        {"id": did("property", "tower-a")},
        property_name="Tower A",
        property_type_id=ptype.id,
        facility_id=facility.id,
        status=1,
        created_by=system.id,
    )
    floors = {}
    for n in (1, 2, 3):
        floors[n] = upsert(
            session,
            Property,
            {"id": did("property", f"tower-a-floor-{n}")},
            property_name=f"Floor {n}",
            property_type_id=ptype.id,
            facility_id=facility.id,
            status=1,
            created_by=system.id,
        )
    counts["property"] = 1 + len(floors)

    chains = {}
    for n, floor in floors.items():
        chains[n] = upsert(
            session,
            PropertyChain,
            {"id": did("property_chain", f"tower-a-floor-{n}")},
            level_one_id=tower.id,
            level_two_id=floor.id,
            level_three_id=None,
            facility_id=facility.id,
            status=1,
            created_by=system.id,
        )
    ctx["chains"] = chains
    ctx["tower"] = tower
    ctx["floors"] = floors
    counts["property_chain"] = len(chains)

    return counts
