"""Write logic for Job Order Management (`job_order` + its two link tables).

Schema facts behind each rule:

* `order_reference` is String(20) NOT NULL **UNIQUE**, so a duplicate is a 409
  rather than a raw IntegrityError. Left out of the payload, the server
  continues the seeded `JO-YYYY-NNNN` sequence with `next_yearly_reference` --
  the same helper stays, invoices and service requests already use.
* `authentication_code` is String(20) **NOT NULL** but the Create Job form has
  no field for it. The seed derives it from the reference
  (`authentication_code=f"JOB{ref_no[-4:]}"`), and this module follows that
  exact convention instead of inventing a new format or asking the user for a
  value the screen never collects.
* `type_of_work` is the `job_order_type_of_work` enum
  (installation | replacement | troubleshoot). The form's "Fresh Installation"
  radio maps to `installation`; the mapping lives in the frontend, which is
  where the label exists.
* `job_order_amenity` and `job_order_device` are composite-PK link tables with
  **no `status` column**, unlike `maintenance_request_amenity`. So links cannot
  be soft-deleted; replacing a list means deleting the rows and re-inserting.
* `job_order.status` is the soft-delete flag. A hard DELETE is impossible while
  links exist -- both link tables reference `job_order.id` ON DELETE RESTRICT --
  so removal is `status = 0`, matching /holidays, the catalogue and
  /maintenance-requests.

WHAT THE SCREEN ASKS FOR THAT THE SCHEMA CANNOT STORE:

* The create form pairs each room with a Caleido Network value in one table row.
  `job_order_amenity` and `job_order_device` are two INDEPENDENT many-to-many
  tables, so the pairing is not storable -- a job order covers a set of rooms
  and a set of devices. The frontend resolves each pair to the devices of that
  type installed in that room and sends the two sets; the pairing itself is not
  persisted, and nothing here pretends otherwise.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AppUser,
    Device,
    JobOrder,
    JobOrderAmenity,
    JobOrderDevice,
)
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    next_yearly_reference,
    require_exists,
    require_row,
    transaction,
)

LIVE = 1
REMOVED = 0
#: The seeded reference format: JO-2026-0001.
REFERENCE_PREFIX = "JO"
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"


def _derive_authentication_code(order_reference: str) -> str:
    """`JOB` + the reference's last four characters.

    Taken from the seed (`f"JOB{ref_no[-4:]}"`), not invented: the column is
    NOT NULL and no screen collects it. String(20) is never exceeded because the
    result is at most seven characters.
    """
    return f"JOB{order_reference[-4:]}"


def _validate_rooms(db: Session, amenity_ids: list[uuid.UUID]) -> None:
    """Every room must exist. Duplicates would violate the composite PK."""
    if not amenity_ids:
        return
    if len(set(amenity_ids)) != len(amenity_ids):
        raise Invalid("amenity_ids contains the same room twice.")
    found = set(
        db.execute(select(Amenity.id).where(Amenity.id.in_(amenity_ids))).scalars().all()
    )
    missing = [str(i) for i in amenity_ids if i not in found]
    if missing:
        raise Invalid(f"These rooms do not exist: {', '.join(missing)}.")


def _validate_devices(db: Session, device_ids: list[uuid.UUID]) -> None:
    if not device_ids:
        return
    if len(set(device_ids)) != len(device_ids):
        raise Invalid("device_ids contains the same device twice.")
    found = set(
        db.execute(select(Device.id).where(Device.id.in_(device_ids))).scalars().all()
    )
    missing = [str(i) for i in device_ids if i not in found]
    if missing:
        raise Invalid(f"These devices do not exist: {', '.join(missing)}.")


def _replace_rooms(db: Session, job_order_id: uuid.UUID, amenity_ids: list[uuid.UUID]) -> None:
    """`job_order_amenity` has no status column, so the rows are replaced."""
    db.execute(delete(JobOrderAmenity).where(JobOrderAmenity.job_order_id == job_order_id))
    for amenity_id in amenity_ids:
        db.add(JobOrderAmenity(job_order_id=job_order_id, amenity_id=amenity_id))


def _replace_devices(db: Session, job_order_id: uuid.UUID, device_ids: list[uuid.UUID]) -> None:
    db.execute(delete(JobOrderDevice).where(JobOrderDevice.job_order_id == job_order_id))
    for device_id in device_ids:
        db.add(JobOrderDevice(job_order_id=job_order_id, device_id=device_id))


def create_job_order(
    db: Session, *, data: dict, actor_id: uuid.UUID
) -> JobOrder:
    """Insert `job_order` plus one link row per room and per device, atomically."""
    rooms: list[uuid.UUID] = data.pop("amenity_ids", None) or []
    devices: list[uuid.UUID] = data.pop("device_ids", None) or []

    require_exists(db, AppUser, data.get("assigned_to"), "Assignee")
    _validate_rooms(db, rooms)
    _validate_devices(db, devices)

    reference = (data.pop("order_reference", None) or "").strip()
    if reference:
        ensure_unique(
            db, JobOrder, JobOrder.order_reference, reference, "Job order reference"
        )
    else:
        reference = next_yearly_reference(
            db,
            JobOrder.order_reference,
            REFERENCE_PREFIX,
            year=data["work_commence"].year,
        )

    with transaction(db):
        job = JobOrder(
            **data,
            order_reference=reference,
            authentication_code=_derive_authentication_code(reference),
            # A new job order always opens as pending work; `completed_on` stays
            # null until it reaches `completed`.
            job_order_status=STATUS_PENDING,
            status=LIVE,
            created_by=actor_id,
        )
        db.add(job)
        db.flush()
        if rooms:
            _replace_rooms(db, job.id, rooms)
        if devices:
            _replace_devices(db, job.id, devices)
    return job


def update_job_order(
    db: Session, job_order_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> JobOrder:
    job = require_row(db, JobOrder, job_order_id, "Job order")
    if job.status == REMOVED:
        raise Conflict("This job order has been removed and cannot be edited.")

    rooms = changes.pop("amenity_ids", None)
    devices = changes.pop("device_ids", None)

    if "assigned_to" in changes:
        require_exists(db, AppUser, changes["assigned_to"], "Assignee")
    if rooms is not None:
        _validate_rooms(db, rooms)
    if devices is not None:
        _validate_devices(db, devices)
    if changes.get("order_reference"):
        ensure_unique(
            db, JobOrder, JobOrder.order_reference, changes["order_reference"],
            "Job order reference", exclude_id=job_order_id,
        )

    commence = changes.get("work_commence", job.work_commence)
    completion = changes.get("estimated_completion_date", job.estimated_completion_date)
    if commence and completion and completion < commence:
        raise Invalid("estimated_completion_date cannot be before work_commence.")

    with transaction(db):
        apply_changes(job, changes)
        if rooms is not None:
            _replace_rooms(db, job.id, rooms)
        if devices is not None:
            _replace_devices(db, job.id, devices)
        # Same completion invariant the service and maintenance requests use:
        # the timestamp is stamped on reaching completed and cleared on leaving.
        if job.job_order_status == STATUS_COMPLETED:
            if job.completed_on is None:
                job.completed_on = datetime.now(UTC)
        else:
            job.completed_on = None
    return job


def remove_job_order(db: Session, job_order_id: uuid.UUID) -> JobOrder:
    """The project's soft delete: `status = 0`. Nothing is physically deleted.

    `job_order` has no `updated_by` column, so unlike `maintenance_request` there
    is nowhere to record who removed it; no column is invented for that.

    `job_order_amenity` and `job_order_device` both reference this row ON DELETE
    RESTRICT, so a hard DELETE is not possible without dropping the links first
    -- which would destroy the record of what the job covered. The links are
    kept and the row drops out of every list unless `include_removed=true`.
    """
    job = require_row(db, JobOrder, job_order_id, "Job order")
    if job.status == REMOVED:
        raise Conflict("This job order has already been removed.")
    with transaction(db):
        job.status = REMOVED
    return job
