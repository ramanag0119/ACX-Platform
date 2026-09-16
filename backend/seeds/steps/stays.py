"""Step 5 - stays, occupants, room allocations, documents, invoices, imports.

`stay` IS the reservation -- there is no `booking` table. Six stays cover the
lifecycle states the `stay_status` enum actually supports:

    pending · active · checkout pending · checked out · cancelled

Chain proven here:  app_user (guest) -> stay -> room_allocation -> amenity
                                        stay -> stay_user
                                        stay -> stay_package
                                        stay -> invoice

NOTE: `invoice` has no `status` column and `package` has no `price`. Amounts on
the invoice come from `service_category_item.price_per_unit`, the only price
that exists in IKANOS. Payment state is NOT modelled -- OPEN DECISION #10.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    ImportJob,
    Invoice,
    RoomAllocation,
    Stay,
    StayPackage,
    StayUser,
    UserDocument,
)
from seeds.helpers import DEMO_NOW, days, did, hours, upsert

# key, guest, room, package, status, expected in/out offsets (days),
# actual in/out offsets or None, no_of_guests
STAYS = [
    ("STY-2026-0001", "aarav.sharma", "101", "deluxe", "active",
     -2, +1, -2, None, 2),
    ("STY-2026-0002", "meera.krishnan", "205", "premium", "active",
     -1, +3, -1, None, 1),
    ("STY-2026-0003", "daniel.foster", "301", "golden", "pending",
     +2, +6, None, None, 2),
    ("STY-2026-0004", "priya.nair", "102", "deluxe", "checked out",
     -9, -6, -9, -6, 1),
    ("STY-2026-0005", "chen.wei", None, "standard", "cancelled",
     +4, +7, None, None, 1),
    ("STY-2026-0006", "ishaan.gupta", "106", "deluxe", "checkout pending",
     -3, 0, -3, None, 3),
]

# Extra occupants sharing a stay, to exercise stay_user as a real many-side.
EXTRA_OCCUPANTS = [
    ("STY-2026-0001", "priya.nair", "101"),
    ("STY-2026-0006", "chen.wei", "106"),
]

# (stay, guest, attachment key, approval status)
DOCUMENTS = [
    ("STY-2026-0001", "aarav.sharma", "guest-doc-aarav", "approved"),
    ("STY-2026-0002", "meera.krishnan", "guest-doc-meera", "approved"),
    ("STY-2026-0003", "daniel.foster", "guest-doc-daniel", "pending"),
]

# Invoices only where a stay actually consumed something.
# net / tax / total are consistent: total = net + tax, tax = 18% GST.
INVOICES = [
    ("INV-2026-0001", "STY-2026-0004", "priya.nair", Decimal("1250.00")),
    ("INV-2026-0002", "STY-2026-0001", "aarav.sharma", Decimal("2400.00")),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    system = ctx["system_user"]
    users = ctx["users"]
    rooms = ctx["rooms"]
    packages = ctx["packages"]

    stays: dict[str, Stay] = {}
    n_alloc = 0
    for ref_no, guest_key, room, pkg, status, exp_in, exp_out, act_in, act_out, pax in STAYS:
        guest = users[guest_key]
        stay = upsert(
            session,
            Stay,
            {"id": did("stay", ref_no)},
            internal_stay_ref_number=ref_no,
            external_stay_ref_number=f"PMS-{ref_no.split('-')[-1]}",
            booking_user_id=guest.id,
            no_of_rooms=1,
            no_of_guests=pax,
            expected_checkin_time=DEMO_NOW + days(exp_in),
            expected_checkout_time=DEMO_NOW + days(exp_out),
            actual_checkin_time=None if act_in is None else DEMO_NOW + days(act_in),
            actual_checkout_time=None if act_out is None else DEMO_NOW + days(act_out),
            comments=f"Demo stay {ref_no}",
            gst="33AAAAA0000A1Z5" if pax > 1 else None,
            checkout_initiated_by=(
                guest.id if status in ("checkout pending", "checked out") else None
            ),
            document_approval_status="approved" if status != "pending" else "pending",
            status=status,
            request_source="ikanos",
            created_by=users["rahul.das"].id,
            modified_by=users["rahul.das"].id,
        )
        stays[ref_no] = stay

        upsert(
            session,
            StayUser,
            {"id": did("stay_user", f"{ref_no}:{guest_key}")},
            app_user_id=guest.id,
            room_id=rooms[room].id if room else None,
            stay_id=stay.id,
            is_key_required=1,
            status=1,
            created_by=users["rahul.das"].id,
        )

        upsert(
            session,
            StayPackage,
            {"id": did("stay_package", ref_no)},
            stay_id=stay.id,
            package_id=packages[pkg].id,
            status=1,
        )

        # A cancelled stay never got a room, which is why room is None there.
        if room:
            upsert(
                session,
                RoomAllocation,
                {"id": did("room_allocation", f"{ref_no}:{room}")},
                stay_id=stay.id,
                room_id=rooms[room].id,
                package_id=packages[pkg].id,
                status=1,
                created_by=users["rahul.das"].id,
            )
            n_alloc += 1

    ctx["stays"] = stays
    counts["stay"] = len(stays)
    counts["stay_package"] = len(stays)
    counts["room_allocation"] = n_alloc

    n_occupants = len(stays)
    for ref_no, guest_key, room in EXTRA_OCCUPANTS:
        upsert(
            session,
            StayUser,
            {"id": did("stay_user", f"{ref_no}:{guest_key}")},
            app_user_id=users[guest_key].id,
            room_id=rooms[room].id,
            stay_id=stays[ref_no].id,
            is_key_required=0,
            status=1,
            created_by=users["rahul.das"].id,
        )
        n_occupants += 1
    counts["stay_user"] = n_occupants

    for ref_no, guest_key, attachment_key, approval in DOCUMENTS:
        upsert(
            session,
            UserDocument,
            {"id": did("user_document", f"{ref_no}:{guest_key}")},
            app_user_id=users[guest_key].id,
            attachment_id=ctx[f"attachment:{attachment_key}"].id,
            stay_id=stays[ref_no].id,
            document_approval_status=approval,
            status=1,
        )
    counts["user_document"] = len(DOCUMENTS)

    for invoice_no, ref_no, guest_key, net in INVOICES:
        guest = users[guest_key]
        tax = (net * Decimal("0.18")).quantize(Decimal("0.01"))
        upsert(
            session,
            Invoice,
            {"id": did("invoice", invoice_no)},
            invoice_number=invoice_no,
            invoice_date=DEMO_NOW - days(1),
            invoice_due_date=DEMO_NOW + days(14),
            billing_user_id=guest.id,
            billing_user_name=f"{guest.first_name} {guest.last_name}",
            billing_address="Demo billing address, Chennai",
            facility_id=facility.id,
            facility_name=facility.name,
            facility_address="Ikanos Grand, Chennai 600096",
            facility_image_id=ctx["attachment:facility-logo"].id,
            stay_id=stays[ref_no].id,
            net_amount=net,
            total_tax=tax,
            total_amount=net + tax,
            created_by=users["rahul.das"].id,
            # No `status`: `invoices` has no status column. OPEN DECISION #10.
        )
    counts["invoice"] = len(INVOICES)

    imports = [
        ("bulk-bookings-aug", "August group bookings", "booking", "success",
         12, 12, 0, "bookings-aug.csv", None),
        ("bulk-bookings-sep", "September group bookings", "booking", "error",
         10, 7, 3, "bookings-sep.csv", "bookings-sep-errors.csv"),
        ("bulk-job-orders", "Q3 device installations", "job order", "queued",
         None, None, None, "job-orders-q3.csv", None),
    ]
    for key, name, entity, status, total, ok, bad, in_file, err_file in imports:
        upsert(
            session,
            ImportJob,
            {"id": did("import_job", key)},
            import_job_name=name,
            entity_type=entity,
            import_status=status,
            total_records=total,
            success_count=ok,
            error_count=bad,
            import_file_name=in_file,
            error_file_name=err_file,
            completed_on=DEMO_NOW - hours(6) if status != "queued" else None,
            created_by=users["kavya.iyer"].id,
        )
    counts["import_job"] = len(imports)

    return counts
