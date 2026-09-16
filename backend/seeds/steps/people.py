"""Step 3 - departments, functions, users, roles and RBAC permissions.

All identities are synthetic. Every email uses the reserved `.invalid` TLD
(RFC 2606) so no address can ever resolve to a real mailbox, and every phone
number is inside the reserved +91 00000 demo range.

Chain proven here:  app_user -> user_role -> role -> role_module_permission
                    -> role_module
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    Department,
    FacilityUser,
    JobFunction,
    Role,
    RoleModulePermission,
    UserDevice,
    UserRole,
    UserToken,
)
from seeds.data import reference as ref
from seeds.helpers import DEMO_NOW, days, did, upsert

INDIA = 99  # country id 99 = INDIA, from the real IKANOS countries table
USA = 226   # country id 226 = UNITED STATES

DEPARTMENTS = [
    ("front-office", "Front Office", None),
    ("housekeeping", "Housekeeping", None),
    ("maintenance", "Maintenance", None),
    ("food-and-beverage", "Food & Beverage", None),
    ("administration", "Administration", "admin"),
]

JOB_FUNCTIONS = [
    ("general-manager", "General Manager", None),
    ("supervisor", "Supervisor", None),
    ("service-staff", "Service Staff", None),
    ("technician", "Technician", None),
    ("administrator", "Administrator", "admin"),
]

# (key, name, description, role_type) -- role_type covers all 5 enum values.
ROLES = [
    ("administrator", "Administrator", "Full access to every module", "admin"),
    ("manager", "Duty Manager", "Operations oversight", "manager"),
    ("front-desk", "Front Desk", "Bookings, occupancy and tickets", "staff"),
    ("housekeeping", "Housekeeping", "Service tracking and planning", "staff"),
    ("technician", "Technician", "Devices, job orders and alerts", "staff"),
    ("guest", "Guest", "Guest-scoped room and service access", "guest"),
    ("system", "System", "Internal service account", "system_user"),
]

# Module access per role, expressed as module_name -> (read, write).
# "*" means every one of the 18 modules.
ROLE_MODULE_ACCESS: dict[str, dict[str, tuple[bool, bool]]] = {
    "administrator": {"*": (True, True)},
    "manager": {
        "dashboard": (True, False), "occupancy": (True, True), "bookings": (True, True),
        "service_tracking": (True, True), "service_planning": (True, True),
        "employees": (True, True), "job_order": (True, True), "offers": (True, True),
        "events": (True, True), "reports": (True, False), "tickets": (True, True),
        "holidays": (True, True), "caleido_network": (True, False),
    },
    "front-desk": {
        "dashboard": (True, False), "occupancy": (True, True), "bookings": (True, True),
        "tickets": (True, True), "service_tracking": (True, False),
        "default_key": (True, True),
    },
    "housekeeping": {
        "dashboard": (True, False), "occupancy": (True, False),
        "service_tracking": (True, True), "service_planning": (True, True),
    },
    "technician": {
        "dashboard": (True, False), "caleido_network": (True, True),
        "firmware_management": (True, True), "job_order": (True, True),
        "service_tracking": (True, True),
    },
    "guest": {"service_tracking": (True, True)},
    "system": {"*": (True, True)},
}

# (key, first, last, email, phone, is_staff, dept, function, role, emp_id)
STAFF = [
    ("arjun.menon", "Arjun", "Menon", "arjun.menon@hms-demo.invalid", "+910000000101",
     "administration", "administrator", "administrator", "EMP-0001"),
    ("kavya.iyer", "Kavya", "Iyer", "kavya.iyer@hms-demo.invalid", "+910000000102",
     "front-office", "general-manager", "manager", "EMP-0002"),
    ("rahul.das", "Rahul", "Das", "rahul.das@hms-demo.invalid", "+910000000103",
     "front-office", "service-staff", "front-desk", "EMP-0003"),
    ("sneha.pillai", "Sneha", "Pillai", "sneha.pillai@hms-demo.invalid", "+910000000104",
     "housekeeping", "supervisor", "housekeeping", "EMP-0004"),
    ("vikram.rao", "Vikram", "Rao", "vikram.rao@hms-demo.invalid", "+910000000105",
     "maintenance", "technician", "technician", "EMP-0005"),
    ("fatima.sheikh", "Fatima", "Sheikh", "fatima.sheikh@hms-demo.invalid", "+910000000106",
     "housekeeping", "service-staff", "housekeeping", "EMP-0006"),
]

# (key, first, last, email, phone, country, gender)
GUESTS = [
    ("aarav.sharma", "Aarav", "Sharma", "aarav.sharma@hms-demo.invalid",
     "+910000000201", INDIA, "male"),
    ("meera.krishnan", "Meera", "Krishnan", "meera.krishnan@hms-demo.invalid",
     "+910000000202", INDIA, "female"),
    ("daniel.foster", "Daniel", "Foster", "daniel.foster@hms-demo.invalid",
     "+910000000203", USA, "male"),
    ("priya.nair", "Priya", "Nair", "priya.nair@hms-demo.invalid",
     "+910000000204", INDIA, "female"),
    ("chen.wei", "Chen", "Wei", "chen.wei@hms-demo.invalid",
     "+910000000205", INDIA, "other"),
    ("ishaan.gupta", "Ishaan", "Gupta", "ishaan.gupta@hms-demo.invalid",
     "+910000000206", INDIA, "male"),
]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    system = ctx["system_user"]

    departments = {}
    for key, name, dept_key in DEPARTMENTS:
        departments[key] = upsert(
            session,
            Department,
            {"id": did("department", key)},
            department_name=name,
            facility_id=facility.id,
            status=1,
            department_key=dept_key,
            created_by=system.id,
        )
    ctx["departments"] = departments
    counts["department"] = len(departments)

    functions = {}
    for key, name, fn_key in JOB_FUNCTIONS:
        functions[key] = upsert(
            session,
            JobFunction,
            {"id": did("job_function", key)},
            function_name=name,
            facility_id=facility.id,  # facility-scoped, NOT department-scoped
            status=1,
            function_key=fn_key,
            created_by=system.id,
        )
    ctx["functions"] = functions
    counts["job_function"] = len(functions)

    roles = {}
    for key, name, description, role_type in ROLES:
        roles[key] = upsert(
            session,
            Role,
            {"id": did("role", key)},
            facility_id=facility.id,
            name=name,
            description=description,
            role_type=role_type,
            status=1,
            created_by=system.id,
        )
    ctx["roles"] = roles
    counts["role"] = len(roles)

    n_perms = 0
    module_ids = {name: mid for mid, name, _r, _w in ref.ROLE_MODULES}
    for role_key, access in ROLE_MODULE_ACCESS.items():
        if "*" in access:
            read_write = {name: access["*"] for name in module_ids}
        else:
            read_write = access
        for module_name, (can_read, can_write) in read_write.items():
            upsert(
                session,
                RoleModulePermission,
                {"role_id": roles[role_key].id, "module_id": module_ids[module_name]},
                read_access=can_read,
                write_access=can_write,
            )
            n_perms += 1
    counts["role_module_permission"] = n_perms

    # ---- users --------------------------------------------------------------
    # The bootstrap user now gets its department and function, which is only
    # possible after both tables exist.
    system.department_id = departments["administration"].id
    system.job_function_id = functions["administrator"].id
    session.flush()

    users: dict[str, AppUser] = {"system": system}

    for key, first, last, email, phone, dept, fn, role_key, emp_id in STAFF:
        users[key] = upsert(
            session,
            AppUser,
            {"id": did("app_user", key)},
            user_uid=f"demo-uid-{key}",
            first_name=first,
            last_name=last,
            email=email,
            phone_number=phone,
            country=INDIA,
            nationality=INDIA,
            is_child=0,
            is_staff=1,
            emp_id=emp_id,
            date_of_joining=DEMO_NOW - days(400),
            department_id=departments[dept].id,
            job_function_id=functions[fn].id,
            user_name=key,
            # Synthetic placeholder -- NOT a usable credential. Real hashes are
            # written by the auth layer in a later phase.
            password_hash="!seed-no-login",
            user_metadata={"seeded": True, "demo_role": role_key},
            created_by=system.id,
        )

    for key, first, last, email, phone, country, gender in GUESTS:
        users[key] = upsert(
            session,
            AppUser,
            {"id": did("app_user", key)},
            user_uid=f"demo-uid-{key}",
            first_name=first,
            last_name=last,
            email=email,
            phone_number=phone,
            country=country,
            nationality=country,
            gender=gender,
            is_child=0,
            is_staff=0,
            user_name=key,
            password_hash="!seed-no-login",
            user_metadata={"seeded": True, "demo_role": "guest"},
            created_by=system.id,
        )

    # Sneha's supervisor relationship, to exercise the self-reference.
    users["fatima.sheikh"].supervisor = users["sneha.pillai"].id
    session.flush()

    ctx["users"] = users
    counts["app_user"] = len(users)

    for user in users.values():
        upsert(
            session,
            FacilityUser,
            {"facility_id": facility.id, "app_user_id": user.id},
            status=1,
            created_by=system.id,
        )
    counts["facility_user"] = len(users)

    role_of = {key: role for key, _f, _l, _e, _p, _d, _fn, role, _emp in STAFF}
    role_of["system"] = "system"
    for key, _f, _l, _e, _p, _c, _g in GUESTS:
        role_of[key] = "guest"

    for key, role_key in role_of.items():
        upsert(
            session,
            UserRole,
            {
                "facility_id": facility.id,
                "app_user_id": users[key].id,
                "role_id": roles[role_key].id,
            },
            created_by=system.id,
        )
    counts["user_role"] = len(role_of)

    # ---- sessions and push registrations ------------------------------------
    tokens = {}
    for key in ("arjun.menon", "kavya.iyer", "rahul.das"):
        tokens[key] = upsert(
            session,
            UserToken,
            {"id": did("user_token", key)},
            token=str(did("user_token_value", key)),
            app_user_id=users[key].id,
            is_expired=False,
            expired_on=DEMO_NOW + days(7),
        )
    counts["user_token"] = len(tokens)

    devices = [
        ("arjun.menon", "Pixel 8", "Android 15", True),
        ("kavya.iyer", "iPhone 15", "iOS 18", True),
        ("aarav.sharma", "OnePlus 12", "Android 14", True),
        ("meera.krishnan", "iPhone 13", "iOS 17", True),
    ]
    for key, model, os_name, is_mobile in devices:
        upsert(
            session,
            UserDevice,
            {"id": did("user_device", key)},
            app_user_id=users[key].id,
            mobile_model=model,
            mobile_os=os_name,
            device_token=f"demo-fcm-{key}",
            is_mobile_token=is_mobile,
            user_token_id=tokens[key].id if key in tokens else None,
            status=1,
        )
    counts["user_device"] = len(devices)

    return counts
