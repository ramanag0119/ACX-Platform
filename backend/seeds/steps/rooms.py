"""Step 4 - amenity types, packages, features and the room inventory.

24 guest rooms across 3 floors plus 3 non-room amenities, covering all four
IKANOS amenity statuses and all four amenity conditions.

NOTE: `package` has NO price column. The blueprint records that `packages` has
no price anywhere in the IKANOS dump and that room tariff has no source
(OPEN DECISION #10). No price is seeded, simulated, or stashed in metadata.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AmenityConditionStatus,
    AmenityType,
    Feature,
    Package,
    PackageFeature,
    SubPackage,
)
from seeds.helpers import did, upsert

# amenity_status ids from IKANOS: 0 Available, 1 Occupied, 2 Unavailable, 3 Allotted
AVAILABLE, OCCUPIED, UNAVAILABLE, ALLOTTED = 0, 1, 2, 3

# amenity_condition ids: 1 Dirty, 2 Low battery, 3 Under maintenance, 4 Sanitation
DIRTY, LOW_BATTERY, UNDER_MAINTENANCE, SANITATION = 1, 2, 3, 4

AMENITY_TYPES = [
    ("guest-room", "Guest Room", "room"),
    ("suite", "Suite", "room"),
    ("restaurant", "Restaurant", "restaurant"),
    ("gym", "Gym", "others"),
    ("conference", "Conference Room", "others"),
]

# (key, name, amenity_type, is_sub_package)
PACKAGES = [
    ("standard", "Standard", "guest-room", False),
    ("deluxe", "Deluxe", "guest-room", False),
    ("premium", "Premium", "suite", False),
    ("golden", "Golden", "suite", False),
    ("room-only", "Room Only", "guest-room", True),
    ("breakfast", "Breakfast Included", "guest-room", True),
    ("half-board", "Half Board", "guest-room", True),
    ("full-board", "Full Board", "guest-room", True),
]

SUB_PACKAGE_LINKS = [
    ("standard", "room-only"),
    ("standard", "breakfast"),
    ("deluxe", "breakfast"),
    ("deluxe", "half-board"),
    ("premium", "half-board"),
    ("premium", "full-board"),
    ("golden", "full-board"),
]

# (key, name, is_smart_feature, device_type id or None)
FEATURES = [
    ("wifi", "High-speed WiFi", False, None),
    ("minibar", "Mini Bar", False, None),
    ("smart-lock", "Smart Door Lock", True, 4),      # Kleio
    ("air-quality", "Air Quality Monitor", True, 2),  # AirQ
    ("smart-metering", "Smart Energy Metering", True, 3),  # Mikos
    ("room-automation", "Room Automation Hub", True, 1),   # Intellihub
]

PACKAGE_FEATURES = {
    "standard": ["wifi", "smart-lock"],
    "deluxe": ["wifi", "minibar", "smart-lock", "air-quality"],
    "premium": ["wifi", "minibar", "smart-lock", "air-quality", "smart-metering"],
    "golden": ["wifi", "minibar", "smart-lock", "air-quality", "smart-metering",
               "room-automation"],
}

# Room plan: floor -> [(number, package, status)]
# Statuses are spread so Occupancy, Room View and the Dashboard all have
# something meaningful to render.
ROOM_PLAN = {
    1: [("101", "deluxe", OCCUPIED), ("102", "deluxe", AVAILABLE),
        ("103", "standard", AVAILABLE), ("104", "standard", UNAVAILABLE),
        ("105", "standard", AVAILABLE), ("106", "deluxe", OCCUPIED),
        ("107", "standard", AVAILABLE), ("108", "standard", ALLOTTED)],
    2: [("201", "premium", OCCUPIED), ("202", "deluxe", AVAILABLE),
        ("203", "deluxe", AVAILABLE), ("204", "standard", UNAVAILABLE),
        ("205", "premium", OCCUPIED), ("206", "deluxe", AVAILABLE),
        ("207", "standard", AVAILABLE), ("208", "standard", AVAILABLE)],
    3: [("301", "golden", ALLOTTED), ("302", "golden", AVAILABLE),
        ("303", "premium", AVAILABLE), ("304", "premium", AVAILABLE),
        ("305", "deluxe", AVAILABLE), ("306", "deluxe", AVAILABLE),
        ("307", "standard", AVAILABLE), ("308", "standard", AVAILABLE)],
}

SUITE_PACKAGES = {"premium", "golden"}

# (room, condition id) -- the Occupancy condition badges
ROOM_CONDITIONS = [
    ("104", UNDER_MAINTENANCE),
    ("204", UNDER_MAINTENANCE),
    ("102", DIRTY),
    ("206", DIRTY),
    ("103", SANITATION),
    ("106", LOW_BATTERY),
]

# Non-room amenities. `name` is varchar(6) in IKANOS, so these stay short.
NON_ROOM = [
    ("REST01", "restaurant", "standard", AVAILABLE),
    ("GYM01", "gym", "standard", AVAILABLE),
    ("CONF01", "conference", "standard", OCCUPIED),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    system = ctx["system_user"]
    chains = ctx["chains"]

    amenity_types = {}
    for key, name, category in AMENITY_TYPES:
        amenity_types[key] = upsert(
            session,
            AmenityType,
            {"id": did("amenity_type", key)},
            name=name,
            facility_id=facility.id,
            status=1,
            amenity_category=category,
            created_by=system.id,
        )
    ctx["amenity_types"] = amenity_types
    counts["amenity_type"] = len(amenity_types)

    packages = {}
    for key, name, atype, is_sub in PACKAGES:
        packages[key] = upsert(
            session,
            Package,
            {"id": did("package", key)},
            facility_id=facility.id,
            name=name,
            description=f"{name} package",
            status=1,
            amenity_type=amenity_types[atype].id,
            is_sub_package=is_sub,
            created_by=system.id,
            # No `price`: the column does not exist. OPEN DECISION #10.
        )
    ctx["packages"] = packages
    counts["package"] = len(packages)

    for parent, child in SUB_PACKAGE_LINKS:
        upsert(
            session,
            SubPackage,
            {"parent_package_id": packages[parent].id,
             "sub_package_id": packages[child].id},
            created_by=system.id,
        )
    counts["sub_package"] = len(SUB_PACKAGE_LINKS)

    features = {}
    for key, name, is_smart, device_type in FEATURES:
        features[key] = upsert(
            session,
            Feature,
            {"id": did("feature", key)},
            facility_id=facility.id,
            feature_name=name,
            is_smart_feature=is_smart,
            device_type=device_type,
            status=1,
            created_by=system.id,
        )
    counts["feature"] = len(features)

    n_pkg_features = 0
    for pkg_key, feature_keys in PACKAGE_FEATURES.items():
        for feature_key in feature_keys:
            upsert(
                session,
                PackageFeature,
                {"id": did("package_feature", f"{pkg_key}:{feature_key}")},
                package_id=packages[pkg_key].id,
                feature_id=features[feature_key].id,
                status=1,
                created_by=system.id,
            )
            n_pkg_features += 1
    counts["package_feature"] = n_pkg_features

    rooms: dict[str, Amenity] = {}
    for floor, plan in ROOM_PLAN.items():
        for number, package_key, status in plan:
            atype = "suite" if package_key in SUITE_PACKAGES else "guest-room"
            rooms[number] = upsert(
                session,
                Amenity,
                {"id": did("amenity", number)},
                name=number,
                amenity_type_id=amenity_types[atype].id,
                facility_id=facility.id,
                property_chain_id=chains[floor].id,
                package_id=packages[package_key].id,
                status=status,
                is_dnd=1 if number == "205" else 0,
                power_save_mode=0,
                amenity_metadata={"floor": floor, "view": "city", "seeded": True},
                created_by=system.id,
            )

    for name, atype, package_key, status in NON_ROOM:
        rooms[name] = upsert(
            session,
            Amenity,
            {"id": did("amenity", name)},
            name=name,
            amenity_type_id=amenity_types[atype].id,
            facility_id=facility.id,
            property_chain_id=chains[1].id,
            package_id=packages[package_key].id,
            status=status,
            amenity_metadata={"floor": 1, "seeded": True},
            created_by=system.id,
        )

    ctx["rooms"] = rooms
    counts["amenity"] = len(rooms)

    for number, condition_id in ROOM_CONDITIONS:
        upsert(
            session,
            AmenityConditionStatus,
            {"amenity_id": rooms[number].id, "amenity_condition_id": condition_id},
            status=1,
        )
    counts["amenity_condition_status"] = len(ROOM_CONDITIONS)

    return counts
