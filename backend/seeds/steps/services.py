"""Step 6 - service catalogue, service requests and maintenance planning.

The catalogue is generic, keyed by `service_type` -- there is no food-specific
table in IKANOS. `service_category_item.price_per_unit` is the ONLY price in
the whole schema, so it is the only place a monetary value is seeded.

Chains proven here:
    service_type -> service_category -> service_category_item
    service_request -> service_request_item
    service_request -> stay / amenity / app_user
    maintenance_request -> recurrence / amenities / assignees

NOTE: `service_request` has NO `priority` column and none is simulated.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    MaintenanceRequest,
    MaintenanceRequestAmenity,
    MaintenanceRequestAssignee,
    MaintenanceRequestRecurrence,
    RoomServiceRequest,
    RoomServiceRequestItem,
    ServiceCategory,
    ServiceCategoryItem,
    ServiceRequest,
    ServiceRequestItem,
)
from seeds.helpers import DEMO_NOW, days, did, hours, upsert

# service_type ids from IKANOS
ROOM_SERVICE, TRAVEL_DESK, BUSINESS_CENTER = 1, 2, 3
FOOD_ORDER, FACILITY_MAINT, HEALTH_FITNESS, SANITATION = 4, 5, 6, 7

# service_status ids
PENDING, ASSIGNED, PARTIALLY_COMPLETED, COMPLETED, CANCELED = 1, 2, 3, 4, 5

# (key, service_type, category_name, category_key)
CATEGORIES = [
    ("housekeeping", ROOM_SERVICE, "Housekeeping", "HOUSEKEEPING"),
    ("laundry", ROOM_SERVICE, "Laundry", "LAUNDRY"),
    ("amenities", ROOM_SERVICE, "Room Amenities", "AMENITIES"),
    ("airport-transfer", TRAVEL_DESK, "Airport Transfer", "AIRPORT_TRANSFER"),
    ("printing", BUSINESS_CENTER, "Printing & Scanning", "PRINTING"),
    ("breakfast", FOOD_ORDER, "Breakfast", "BREAKFAST"),
    ("main-course", FOOD_ORDER, "Main Course", "MAIN_COURSE"),
    ("beverages", FOOD_ORDER, "Beverages", "BEVERAGES"),
    ("electrical", FACILITY_MAINT, "Electrical", "ELECTRICAL"),
    ("plumbing", FACILITY_MAINT, "Plumbing", "PLUMBING"),
    ("hvac", FACILITY_MAINT, "HVAC", "HVAC"),
    ("gym", HEALTH_FITNESS, "Gym Session", "GYM"),
    ("room-sanitization", SANITATION, "Room Sanitization", "ROOM_SANITIZATION"),
]

# (key, category, item_name, price_per_unit or None)
ITEMS = [
    ("extra-towels", "housekeeping", "Extra Towels", None),
    ("room-cleaning", "housekeeping", "Room Cleaning", None),
    ("turndown", "housekeeping", "Turndown Service", None),
    ("wash-fold", "laundry", "Wash & Fold (per kg)", Decimal("150.00")),
    ("dry-clean", "laundry", "Dry Cleaning (per piece)", Decimal("220.00")),
    ("toiletries", "amenities", "Toiletries Refill", None),
    ("extra-pillow", "amenities", "Extra Pillow", None),
    ("sedan-pickup", "airport-transfer", "Sedan Airport Pickup", Decimal("1800.00")),
    ("suv-pickup", "airport-transfer", "SUV Airport Pickup", Decimal("2600.00")),
    ("bw-print", "printing", "B/W Print (per page)", Decimal("5.00")),
    ("continental", "breakfast", "Continental Breakfast", Decimal("650.00")),
    ("south-indian", "breakfast", "South Indian Breakfast", Decimal("550.00")),
    ("biryani", "main-course", "Hyderabadi Biryani", Decimal("480.00")),
    ("grilled-fish", "main-course", "Grilled Fish", Decimal("720.00")),
    ("filter-coffee", "beverages", "Filter Coffee", Decimal("120.00")),
    ("fresh-juice", "beverages", "Fresh Juice", Decimal("180.00")),
    ("light-repair", "electrical", "Light Fixture Repair", None),
    ("socket-repair", "electrical", "Power Socket Repair", None),
    ("leak-fix", "plumbing", "Leak Repair", None),
    ("ac-service", "hvac", "AC Servicing", None),
    ("gym-session", "gym", "Personal Training Session", Decimal("900.00")),
    ("deep-sanitize", "room-sanitization", "Deep Room Sanitization", None),
]

# (ref, service_type, category, room, stay or None, requester, assignee,
#  status, dept, completed offset hours or None)
REQUESTS = [
    ("SR-2026-0001", ROOM_SERVICE, "housekeeping", "101", "STY-2026-0001",
     "aarav.sharma", "sneha.pillai", COMPLETED, "housekeeping", -20),
    ("SR-2026-0002", FOOD_ORDER, "main-course", "205", "STY-2026-0002",
     "meera.krishnan", "fatima.sheikh", ASSIGNED, "food-and-beverage", None),
    ("SR-2026-0003", FACILITY_MAINT, "hvac", "104", None,
     "rahul.das", "vikram.rao", PENDING, "maintenance", None),
    ("SR-2026-0004", ROOM_SERVICE, "laundry", "106", "STY-2026-0006",
     "ishaan.gupta", "fatima.sheikh", PARTIALLY_COMPLETED, "housekeeping", None),
    ("SR-2026-0005", TRAVEL_DESK, "airport-transfer", "301", None,
     "daniel.foster", "rahul.das", PENDING, "front-office", None),
    ("SR-2026-0006", FOOD_ORDER, "breakfast", "102", "STY-2026-0004",
     "priya.nair", "fatima.sheikh", CANCELED, "food-and-beverage", None),
    ("SR-2026-0007", FACILITY_MAINT, "electrical", "204", None,
     "sneha.pillai", "vikram.rao", ASSIGNED, "maintenance", None),
]

# (request ref, item key, quantity, status)
REQUEST_ITEMS = [
    ("SR-2026-0001", "extra-towels", 2, COMPLETED),
    ("SR-2026-0001", "toiletries", 1, COMPLETED),
    ("SR-2026-0002", "biryani", 2, ASSIGNED),
    ("SR-2026-0002", "filter-coffee", 2, ASSIGNED),
    ("SR-2026-0004", "wash-fold", 3, COMPLETED),
    ("SR-2026-0004", "dry-clean", 2, PENDING),
    ("SR-2026-0005", "sedan-pickup", 1, PENDING),
    ("SR-2026-0006", "continental", 1, CANCELED),
]

# Guest-app room service calls -- a separate 4-value status vocabulary.
ROOM_SERVICE_CALLS = [
    ("RSR-0001", "101", "STY-2026-0001", "completed", "sneha.pillai",
     ["extra-pillow"]),
    ("RSR-0002", "205", "STY-2026-0002", "assigned", "fatima.sheikh",
     ["fresh-juice", "filter-coffee"]),
    ("RSR-0003", "106", "STY-2026-0006", "unassigned", None, ["room-cleaning"]),
]

# (key, type, category, item, rooms, assignees, status, recurring, days offset)
MAINTENANCE = [
    ("mr-hvac-quarterly", "planned", "hvac", "ac-service", ["104", "204"],
     ["vikram.rao"], ASSIGNED, False, +3),
    ("mr-weekly-sanitation", "scheduled", "room-sanitization", "deep-sanitize",
     ["103", "106"], ["sneha.pillai", "fatima.sheikh"], PENDING, True, +1),
    ("mr-disinfection-floor2", "disinfection", "room-sanitization", "deep-sanitize",
     ["204", "206"], ["fatima.sheikh"], COMPLETED, False, -4),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    system = ctx["system_user"]
    users = ctx["users"]
    rooms = ctx["rooms"]
    stays = ctx["stays"]
    departments = ctx["departments"]

    categories = {}
    for key, service_type, name, category_key in CATEGORIES:
        icon = ctx["attachment:service-icon-breakfast"].id if key == "breakfast" else None
        categories[key] = upsert(
            session,
            ServiceCategory,
            {"id": did("service_category", key)},
            service_type=service_type,
            category_name=name,
            description=f"{name} services",
            category_icon=icon,
            facility_id=facility.id,
            service_category_key=category_key,
            status=1,
            created_by=system.id,
        )
    ctx["service_categories"] = categories
    counts["service_category"] = len(categories)

    items = {}
    for key, category_key, name, price in ITEMS:
        items[key] = upsert(
            session,
            ServiceCategoryItem,
            {"id": did("service_category_item", key)},
            item_name=name,
            category_id=categories[category_key].id,
            description=name,
            price_per_unit=price,
            facility_id=facility.id,
            status=1,
            item_metadata={"seeded": True},
            created_by=system.id,
        )
    ctx["service_items"] = items
    counts["service_category_item"] = len(items)

    requests = {}
    for (ref_no, stype, category, room, stay_ref, requester, assignee,
         status, dept, done_offset) in REQUESTS:
        requests[ref_no] = upsert(
            session,
            ServiceRequest,
            {"id": did("service_request", ref_no)},
            service_type=stype,
            ref_number=ref_no,
            description=f"Demo service request {ref_no}",
            assigned_to=users[assignee].id if assignee else None,
            department_id=departments[dept].id,
            category_id=categories[category].id,
            amenity_id=rooms[room].id,
            stay_id=stays[stay_ref].id if stay_ref else None,
            app_user_id=users[requester].id,
            request_source="ikanos",
            facility_id=facility.id,
            expected_date=DEMO_NOW + hours(4),
            completed_on=None if done_offset is None else DEMO_NOW + hours(done_offset),
            status=status,
            status_reason="Guest cancelled" if status == CANCELED else None,
            created_by=users[requester].id,
            updated_by=users[assignee].id if assignee else users[requester].id,
            # No `priority`: the column does not exist in IKANOS.
        )
    ctx["service_requests"] = requests
    counts["service_request"] = len(requests)

    for ref_no, item_key, qty, status in REQUEST_ITEMS:
        item = items[item_key]
        upsert(
            session,
            ServiceRequestItem,
            {"id": did("service_request_item", f"{ref_no}:{item_key}")},
            service_request_id=requests[ref_no].id,
            item_id=item.id,
            category_id=item.category_id,
            quantity=qty,
            price_per_unit=item.price_per_unit,
            assigned_to=requests[ref_no].assigned_to,
            status=status,
        )
    counts["service_request_item"] = len(REQUEST_ITEMS)

    n_rsr_items = 0
    for key, room, stay_ref, status, assignee, item_keys in ROOM_SERVICE_CALLS:
        rsr = upsert(
            session,
            RoomServiceRequest,
            {"id": did("room_service_request", key)},
            guest_room_id=rooms[room].id,
            stay_id=stays[stay_ref].id,
            service_request_status=status,
            assigned_to=users[assignee].id if assignee else None,
            comments=f"Guest app request {key}",
            completed_on=DEMO_NOW - hours(3) if status == "completed" else None,
            created_by=users["rahul.das"].id,
        )
        for item_key in item_keys:
            upsert(
                session,
                RoomServiceRequestItem,
                {"id": did("room_service_request_item", f"{key}:{item_key}")},
                room_service_request_id=rsr.id,
                service_category_item_id=items[item_key].id,
                is_processed=1 if status == "completed" else 0,
            )
            n_rsr_items += 1
    counts["room_service_request"] = len(ROOM_SERVICE_CALLS)
    counts["room_service_request_item"] = n_rsr_items

    n_mr_amenities = n_mr_assignees = n_recurrence = 0
    for (key, mtype, category, item_key, room_list, assignees,
         status, recurring, offset) in MAINTENANCE:
        mr = upsert(
            session,
            MaintenanceRequest,
            {"id": did("maintenance_request", key)},
            maintenance_request_type=mtype,
            maintenance_start_date=(DEMO_NOW + days(offset)).date(),
            maintenance_end_date=(DEMO_NOW + days(offset)).date(),
            maintenance_start_time=DEMO_NOW + days(offset),
            maintenance_end_time=DEMO_NOW + days(offset) + hours(2),
            is_recurring=1 if recurring else 0,
            department_id=departments["maintenance"].id,
            category_id=categories[category].id,
            item_id=items[item_key].id,
            facility_id=facility.id,
            completed_on=DEMO_NOW + days(offset) if status == COMPLETED else None,
            is_room=1,
            parent_id=None,
            maintenance_request_status=status,
            under_maintenance=True if status == ASSIGNED else False,
            status=1,
            created_by=users["kavya.iyer"].id,
            updated_by=users["vikram.rao"].id,
        )
        if recurring:
            upsert(
                session,
                MaintenanceRequestRecurrence,
                {"maintenance_request_id": mr.id},
                recurrence_type="weekly",
                days_of_week=0b0010010,  # Tue + Fri
                max_no_of_occurrences=12,
            )
            n_recurrence += 1
        for room in room_list:
            upsert(
                session,
                MaintenanceRequestAmenity,
                {"id": did("maintenance_request_amenity", f"{key}:{room}")},
                maintenance_request_id=mr.id,
                amenity_id=rooms[room].id,
                status=1,
                created_by=users["kavya.iyer"].id,
            )
            n_mr_amenities += 1
        for assignee in assignees:
            upsert(
                session,
                MaintenanceRequestAssignee,
                {"id": did("maintenance_request_assignee", f"{key}:{assignee}")},
                maintenance_request_id=mr.id,
                app_user_id=users[assignee].id,
                status=1,
                created_by=users["kavya.iyer"].id,
            )
            n_mr_assignees += 1
        ctx[f"maintenance:{key}"] = mr

    counts["maintenance_request"] = len(MAINTENANCE)
    counts["maintenance_request_recurrence"] = n_recurrence
    counts["maintenance_request_amenity"] = n_mr_amenities
    counts["maintenance_request_assignee"] = n_mr_assignees

    return counts
