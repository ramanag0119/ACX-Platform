"""Read logic for Job Order Management.

THREE TABLES, NOT ONE (blueprint §5, tables 60-62):

    job_order           the work order itself
    job_order_amenity   the rooms it covers      (0..N, composite PK)
    job_order_device    the devices it covers    (0..N, composite PK)

`job_order` has NO `facility_id` column [FACT, recorded on the model]. Scope is
reached through `job_order_amenity -> amenity -> facility`, which is blueprint
OPEN DECISION #6. That is why `facility_id` is a FILTER here rather than a
column on the response, and why a job order with no rooms belongs to no
facility -- the seeded data has no such row, but the schema permits it.

TWO INDEPENDENT STATUS COLUMNS, deliberately kept apart, the same split
`maintenance_request` uses:

    job_order_status   enum pending | completed  -- the work lifecycle
    status             smallint 1 live / 0 removed -- the soft-delete flag

Neither link table has a `status` column of its own -- unlike
`maintenance_request_amenity` -- so links are not soft-deleted; retiring the
parent is what takes a job order out of every list.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AppUser,
    Device,
    DeviceType,
    JobOrder,
    JobOrderAmenity,
    JobOrderDevice,
)

#: `job_order.status` -- the soft-delete flag, not the work lifecycle.
LIVE = 1
REMOVED = 0


def _count(db: Session, stmt: Select) -> int:
    return db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()


def _job_stmt() -> Select:
    """One row per job order, with the assignee's name resolved by the database."""
    return select(
        JobOrder.id,
        JobOrder.order_reference,
        JobOrder.description,
        JobOrder.type_of_work,
        JobOrder.work_commence,
        JobOrder.estimated_completion_date,
        # `authentication_code` is NOT selected: it is the technician's on-site
        # code and never leaves the database. See JobOrderRead.
        JobOrder.assigned_to,
        AppUser.first_name.label("assignee_first_name"),
        AppUser.last_name.label("assignee_last_name"),
        AppUser.emp_id.label("assignee_emp_id"),
        JobOrder.job_order_status,
        JobOrder.completed_on,
        JobOrder.status,
        JobOrder.created_on,
        JobOrder.updated_on,
    ).join(AppUser, AppUser.id == JobOrder.assigned_to, isouter=True)


def list_job_orders(
    db: Session,
    *,
    page: int,
    page_size: int,
    job_order_status: str | None = None,
    type_of_work: str | None = None,
    assigned_to: uuid.UUID | None = None,
    amenity_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    search: str | None = None,
    include_removed: bool = False,
):
    """A page of job orders, newest work first.

    Soft-deleted rows stay out unless `include_removed`, the same rule every
    other list endpoint in the project follows.
    """
    stmt = _job_stmt().order_by(
        JobOrder.work_commence.desc().nullslast(), JobOrder.created_on.desc()
    )
    if not include_removed:
        # `status` is nullable with no server default; the seeded live rows carry
        # 1, so anything explicitly 0 is the only thing treated as removed.
        stmt = stmt.where(JobOrder.status.is_distinct_from(REMOVED))
    if job_order_status:
        stmt = stmt.where(JobOrder.job_order_status == job_order_status)
    if type_of_work:
        stmt = stmt.where(JobOrder.type_of_work == type_of_work)
    if assigned_to:
        stmt = stmt.where(JobOrder.assigned_to == assigned_to)
    if amenity_id:
        stmt = stmt.where(
            JobOrder.id.in_(
                select(JobOrderAmenity.job_order_id).where(
                    JobOrderAmenity.amenity_id == amenity_id
                )
            )
        )
    if device_id:
        stmt = stmt.where(
            JobOrder.id.in_(
                select(JobOrderDevice.job_order_id).where(
                    JobOrderDevice.device_id == device_id
                )
            )
        )
    if facility_id:
        # Reached through the rooms, because `job_order` has no facility column.
        stmt = stmt.where(
            JobOrder.id.in_(
                select(JobOrderAmenity.job_order_id)
                .join(Amenity, Amenity.id == JobOrderAmenity.amenity_id)
                .where(Amenity.facility_id == facility_id)
            )
        )
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(
            JobOrder.order_reference.ilike(needle)
            | JobOrder.description.ilike(needle)
        )

    total = _count(db, stmt)
    rows = (
        db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
        .mappings()
        .all()
    )
    return rows, total


def get_job_order(db: Session, job_order_id: uuid.UUID):
    return (
        db.execute(_job_stmt().where(JobOrder.id == job_order_id))
        .mappings()
        .one_or_none()
    )


def rooms_for(db: Session, job_order_ids: list[uuid.UUID]) -> dict:
    """Rooms per job order, batched -- one query for a whole page."""
    if not job_order_ids:
        return {}
    rows = db.execute(
        select(
            JobOrderAmenity.job_order_id,
            JobOrderAmenity.amenity_id,
            Amenity.name.label("room_name"),
        )
        .join(Amenity, Amenity.id == JobOrderAmenity.amenity_id)
        .where(JobOrderAmenity.job_order_id.in_(job_order_ids))
        .order_by(Amenity.name)
    ).mappings().all()
    grouped: dict = defaultdict(list)
    for row in rows:
        grouped[row["job_order_id"]].append(
            {"amenity_id": row["amenity_id"], "room_name": row["room_name"]}
        )
    return grouped


def devices_for(db: Session, job_order_ids: list[uuid.UUID]) -> dict:
    """Devices per job order, batched, with the device type the screen calls
    "Caleido Network" and the room the device sits in."""
    if not job_order_ids:
        return {}
    rows = db.execute(
        select(
            JobOrderDevice.job_order_id,
            JobOrderDevice.device_id,
            Device.device_uid,
            Device.device_name,
            Device.device_type,
            DeviceType.name.label("device_type_name"),
            Device.amenity_id,
            Amenity.name.label("room_name"),
        )
        .join(Device, Device.id == JobOrderDevice.device_id)
        .join(DeviceType, DeviceType.id == Device.device_type, isouter=True)
        .join(Amenity, Amenity.id == Device.amenity_id, isouter=True)
        .where(JobOrderDevice.job_order_id.in_(job_order_ids))
        .order_by(Amenity.name, Device.device_uid)
    ).mappings().all()
    grouped: dict = defaultdict(list)
    for row in rows:
        grouped[row["job_order_id"]].append(
            {
                "device_id": row["device_id"],
                "device_uid": row["device_uid"],
                "device_name": row["device_name"],
                "device_type": row["device_type"],
                "device_type_name": row["device_type_name"],
                "amenity_id": row["amenity_id"],
                "room_name": row["room_name"],
            }
        )
    return grouped
