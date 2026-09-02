"""Platform boundary: which database roles may use the HMS Web application.

The IKANOS KT Handbook defines five business roles and splits them across three
client applications:

    Admin       -> HMS Web
    Manager     -> HMS Web
    Staff       -> Mobile application
    Technician  -> Mobile application
    Guest       -> Separate guest mobile application

The boundary below is derived from `role.role_type`, the database's OWN
vocabulary, not from role display names. Names are free text and an operator
can rename "Duty Manager" tomorrow; `role_type` is a constrained ENUM and is
therefore the only safe thing to gate on.

TWO MISMATCHES between the handbook and the database, reported not resolved:

  1. There is NO `technician` value in the `role_type` enum. The seeded
     "Technician" role has role_type='staff'. The boundary still lands
     correctly (Technician -> staff -> Mobile), but Technician is not
     separable from other staff at the type level -- only by role name.

  2. `system_user` exists in the enum and is seeded ("System"), but does not
     appear in the handbook at all. It is treated as a non-interactive service
     account and is EXCLUDED from HMS Web login. Granting a service account an
     interactive web session would be a security decision the handbook never
     authorises.
"""

from __future__ import annotations

from enum import Enum

#: `role.role_type` values permitted to authenticate against HMS Web.
HMS_WEB_ROLE_TYPES: frozenset[str] = frozenset({"admin", "manager"})


class Platform(str, Enum):
    HMS_WEB = "hms_web"
    MOBILE = "mobile"
    GUEST_MOBILE = "guest_mobile"
    SERVICE = "service"


#: role_type -> the client application that owns it.
ROLE_TYPE_PLATFORM: dict[str, Platform] = {
    "admin": Platform.HMS_WEB,
    "manager": Platform.HMS_WEB,
    "staff": Platform.MOBILE,        # includes the seeded "Technician" role
    "guest": Platform.GUEST_MOBILE,
    "system_user": Platform.SERVICE,  # not in the handbook; never interactive
}


def platform_for(role_type: str) -> Platform | None:
    return ROLE_TYPE_PLATFORM.get(role_type)


def is_hms_web_role(role_type: str) -> bool:
    return role_type in HMS_WEB_ROLE_TYPES
