"""Group D - people, authentication and RBAC (9 tables).

Blueprint §5, tables 25-33.

`app_user` is one identity table for guests AND staff -- IKANOS has no
`employee` table; staff are `users` rows with `is_staff = 1`.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, HMSBase, SmallIntLookupPk, TimestampMixin, UUIDPk
from app.models import enums
from app.models.facility import user_fk


class AppUser(HMSBase, UUIDPk):
    """One identity table for guests and staff.
    IKANOS `users` + `user_login_details` (MERGE) + `user_metadata` (MERGE).
    ADAPT -- also absorbs the Phase 1 `employee` table.

    `users` has no `facility_id` [FACT] -- scope comes from `facility_user`
    and `user_role`. There is no `is_active` column, so the documented
    LOGIN.USER_INACTIVE error has no backing column (OPEN DECISION #12).
    """

    __tablename__ = "app_user"

    user_uid: Mapped[str] = mapped_column(String(72), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    country: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("country.id", ondelete="RESTRICT"), nullable=True
    )
    phone_number: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    alternate_phone_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    gender: Mapped[str | None] = mapped_column(enums.gender, nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_child: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Replaces the Phase 1 `employee` table.
    is_staff: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1", index=True
    )
    date_of_joining: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    date_of_termination: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supervisor: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
    address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    nationality: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("country.id", ondelete="RESTRICT"), nullable=True
    )
    marital_status: Mapped[str | None] = mapped_column(
        enums.marital_status, nullable=True
    )
    # IKANOS `function_id`; renamed for the `job_function` table rename.
    job_function_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_function.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("department.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )
    emp_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # MERGE: absorbed `user_login_details` (1:1 on the PK).
    user_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # MERGE: absorbed `user_metadata`.
    user_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("ix_app_user_metadata_gin", "metadata", postgresql_using="gin"),
    )


class UserToken(HMSBase, UUIDPk):
    """API session tokens with explicit expiry. IKANOS `user_tokens`. USE."""

    __tablename__ = "user_token"

    token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    is_expired: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="false"
    )
    expired_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserDevice(HMSBase, UUIDPk):
    """Registered device and its push token.
    IKANOS `user_devices`. USE -- replaces the Phase 1 `fcm_token`."""

    __tablename__ = "user_device"

    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=False, index=True
    )
    mobile_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_os: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_mobile_token: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_token_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_token.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stay.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class Role(HMSBase, UUIDPk):
    """Named role within a facility. IKANOS `roles`. USE.

    The Phase 1 `permissions JSONB` column is gone -- permissions live in
    `role_module_permission`.
    """

    __tablename__ = "role"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_type: Mapped[str] = mapped_column(
        enums.role_type, nullable=False, server_default="staff"
    )
    status: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, server_default="1"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=False
    )


class UserRole(Base, TimestampMixin):
    """Which role a user holds AT WHICH FACILITY. IKANOS `user_roles`. ADAPT.

    The 3-column composite PK is the correction: the Phase 1
    `app_user_user_role` had only (app_user_id, user_role_id), so one user
    could not hold different roles at different facilities.
    """

    __tablename__ = "user_role"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        primary_key=True,
    )
    app_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        user_fk(ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="CASCADE"), nullable=True
    )


class RoleModule(Base, TimestampMixin, SmallIntLookupPk):
    """The module registry. IKANOS `role_modules`. USE.

    18 seeded rows that match the HMS sidebar exactly: dashboard, occupancy,
    bookings, service_tracking, service_planning, facility_management,
    user_roles, service_setup, employees, job_order, offers, events,
    caleido_network, firmware_management, reports, tickets, holidays,
    default_key.
    """

    __tablename__ = "role_module"

    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    read_applicable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    write_applicable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class RoleModulePermission(Base, TimestampMixin):
    """Read/write access per role per module.
    IKANOS `role_module_permissions`. USE."""

    __tablename__ = "role_module_permission"

    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("role.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    module_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("role_module.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    read_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    write_access: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Department(HMSBase, UUIDPk):
    """Staff department. IKANOS `departments`. ADAPT."""

    __tablename__ = "department"

    department_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    department_key: Mapped[str | None] = mapped_column(
        enums.department_key, nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )


class JobFunction(HMSBase, UUIDPk):
    """Staff function. IKANOS `functions`. ADAPT (renamed -- SQL keyword).

    Scoped to FACILITY, not department. The Phase 1 FK
    `job_function.department_id -> department.id` was wrong: `functions` has
    no `department_id` column [FACT]. A user links to `department_id` and
    `function_id` independently.
    """

    __tablename__ = "job_function"

    function_name: Mapped[str] = mapped_column(String(100), nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("facility.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    function_key: Mapped[str | None] = mapped_column(enums.function_key, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), user_fk(ondelete="RESTRICT"), nullable=True
    )
