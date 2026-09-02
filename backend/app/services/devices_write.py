"""Write logic for devices, firmware, incidents and value-alert limit configs.

Schema facts that shape this, all verified against the seeded rows:

* `device.device_config_status` is the commissioning lifecycle enum:
  configured | bad_configuration | commissioned | decommissioned |
  under_maintenance | missing. Decommissioning sets that value -- there is no
  separate device_status table and no delete, because `device_stat`,
  `device_alert` and `job_order_device` all reference the row.
* `device.authentication_code` is a device credential. It is never accepted
  from a request and never returned, so it cannot be set or read through the UI.
* Firmware assignment IS `device.expected_firmware_version`, which despite its
  name is a UUID FK to `firmware.id` (the read projection joins it to expose the
  version text as `expected_firmware`). The hub compares it with
  `current_firmware_version` and pulls the build; there is no command or queue
  table, so nothing is "pushed" from here.
* `firmware` has a UNIQUE (device_type_id, firmware_version) shape in the
  seeded data, so a duplicate version for a device type is a 409.
* Incident lifecycle is `device_incident.current_incident_status` against the
  `incident_status` lookup (1 Unread, 2 Read, 3 Assigned, 4 Resolved), and every
  transition appends an `incident_history` row keyed to the matching
  `incident_event` (which carries the same four names plus Reopened).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Amenity,
    AppUser,
    Device,
    DeviceIncident,
    DeviceType,
    Facility,
    Firmware,
    IncidentEvent,
    IncidentStatus,
    ValueAlertLimitConfig,
)
from app.services.limit_config import bool_to_yesno, bool_to_yn, flag_to_bool
from app.services.writes import (
    Conflict,
    Invalid,
    apply_changes,
    ensure_unique,
    next_reference,
    require_exists,
    require_row,
    transaction,
)

CONFIG_COMMISSIONED = "commissioned"
CONFIG_DECOMMISSIONED = "decommissioned"

INCIDENT_RESOLVED = 4


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def create_device(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> Device:
    with transaction(db):
        if db.get(DeviceType, data["device_type"]) is None:
            raise Invalid(f"Device type {data['device_type']} does not exist.")
        room = db.get(Amenity, data["amenity_id"])
        if room is None:
            raise Invalid(f"Room {data['amenity_id']} does not exist.")
        require_exists(db, Device, data.get("parent_device_id"), "Parent device")

        device_uid = data.pop("device_uid", None)
        if device_uid:
            ensure_unique(db, Device, Device.device_uid, device_uid, "Device UID")
        else:
            device_uid = next_reference(db, Device, Device.device_uid, "DEV", width=6)

        device = Device(
            id=uuid.uuid4(),
            device_uid=device_uid,
            facility_id=data.pop("facility_id", None) or room.facility_id or facility_id,
            # A newly registered device is configured but not yet commissioned.
            device_config_status=data.pop("device_config_status", None) or "configured",
            mfg_date=data.pop("mfg_date", None) or None,
            created_by=actor_id,
            **data,
        )
        if device.mfg_date is None:
            # `device.mfg_date` is NOT NULL in the schema.
            raise Invalid("mfg_date is required: the schema stores it NOT NULL.")
        db.add(device)
    db.refresh(device)
    return device


def update_device(db: Session, device_id: uuid.UUID, *, changes: dict) -> Device:
    with transaction(db):
        device = require_row(db, Device, device_id, "Device")
        require_exists(db, Amenity, changes.get("amenity_id"), "Room")
        if changes.get("parent_device_id") == device_id:
            raise Invalid("A device cannot be its own parent.")
        require_exists(db, Device, changes.get("parent_device_id"), "Parent device")

        if changes.get("expected_firmware_version"):
            _assert_firmware_matches_device(
                db, device, changes["expected_firmware_version"]
            )
        apply_changes(device, changes)
    db.refresh(device)
    return device


def _assert_firmware_matches_device(db: Session, device: Device, firmware_id) -> None:
    """`expected_firmware_version` holds a firmware ID, and the build must be
    for this device's own device type."""
    firmware = db.get(Firmware, firmware_id)
    if firmware is None:
        raise Invalid(f"Firmware {firmware_id} does not exist.")
    if firmware.device_type_id != device.device_type:
        raise Invalid("That firmware is built for a different device type.")


def set_device_config_status(
    db: Session, device_id: uuid.UUID, *, config_status: str
) -> Device:
    """Commission, decommission or flag a device for maintenance."""
    with transaction(db):
        device = require_row(db, Device, device_id, "Device")
        if device.device_config_status == config_status:
            raise Conflict(f"This device is already '{config_status}'.")
        device.device_config_status = config_status
    db.refresh(device)
    return device


# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------


def create_firmware(db: Session, *, data: dict, actor_id: uuid.UUID) -> Firmware:
    with transaction(db):
        if db.get(DeviceType, data["device_type_id"]) is None:
            raise Invalid(f"Device type {data['device_type_id']} does not exist.")

        clash = db.execute(
            select(Firmware.id)
            .where(Firmware.device_type_id == data["device_type_id"])
            .where(Firmware.firmware_version == data["firmware_version"])
        ).scalars().first()
        if clash is not None:
            raise Conflict(
                f"Firmware {data['firmware_version']} already exists for this device type."
            )

        firmware = Firmware(
            id=uuid.uuid4(),
            uploaded_by=actor_id,
            created_by=actor_id,
            updated_by=actor_id,
            **data,
        )
        db.add(firmware)
    db.refresh(firmware)
    return firmware


def update_firmware(
    db: Session, firmware_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> Firmware:
    with transaction(db):
        firmware = require_row(db, Firmware, firmware_id, "Firmware")
        if changes.get("status") == "decommissioned":
            in_use = db.execute(
                select(Device.device_name).where(
                    Device.expected_firmware_version == firmware.id
                )
            ).scalars().first()
            if in_use:
                raise Conflict(
                    "This firmware is still the expected version for at least one "
                    f"device ({in_use}). Reassign those devices first."
                )
        apply_changes(firmware, changes)
        firmware.updated_by = actor_id
    db.refresh(firmware)
    return firmware


def assign_firmware(
    db: Session, firmware_id: uuid.UUID, *, device_ids: list[uuid.UUID]
) -> list[Device]:
    """Set `expected_firmware_version` on each device, in one transaction.

    This is the whole of what the schema supports: the hub reads the expected
    version and fetches the build itself. No command row is written because no
    command table exists.
    """
    updated: list[Device] = []
    with transaction(db):
        firmware = require_row(db, Firmware, firmware_id, "Firmware")
        if firmware.status == "decommissioned":
            raise Conflict("Decommissioned firmware cannot be assigned.")

        for device_id in device_ids:
            device = require_row(db, Device, device_id, "Device")
            if device.device_type != firmware.device_type_id:
                raise Invalid(
                    f"Device {device.device_name or device.device_uid} is not the "
                    "device type this firmware is built for."
                )
            # The column stores the firmware ID, not the version string.
            device.expected_firmware_version = firmware.id
            updated.append(device)
    for device in updated:
        db.refresh(device)
    return updated


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


def update_incident(
    db: Session, incident_id: uuid.UUID, *, changes: dict, actor_id: uuid.UUID
) -> DeviceIncident:
    """Acknowledge, assign or resolve an incident, recording the history row."""
    from app.models import IncidentHistory  # local import: history is write-only

    with transaction(db):
        incident = require_row(db, DeviceIncident, incident_id, "Incident")
        require_exists(db, AppUser, changes.get("assigned_to"), "Assignee")

        new_status = changes.get("current_incident_status")
        if new_status is not None and db.get(IncidentStatus, new_status) is None:
            raise Invalid(f"Incident status {new_status} does not exist.")

        # Naming an assignee moves an unread/read incident to Assigned, which is
        # what the seeded rows show.
        if changes.get("assigned_to") and new_status is None:
            if incident.current_incident_status in (None, 1, 2):
                new_status = 3
                changes["current_incident_status"] = new_status

        previous_status = incident.current_incident_status
        apply_changes(incident, changes)
        incident.updated_by = actor_id

        if new_status is not None and new_status != previous_status:
            event = _event_for_status(db, new_status, previous_status)
            if event is not None:
                db.add(
                    IncidentHistory(
                        # `id` is a BIGINT identity column -- let PostgreSQL fill it.
                        incident_id=incident_id,
                        incident_event_id=event,
                        created_by=actor_id,
                    )
                )
    db.refresh(incident)
    return incident


def _event_for_status(db: Session, new_status: int, previous_status: int | None) -> int | None:
    """Match the status to an `incident_event` row by name.

    `incident_status` and `incident_event` carry the same four names, plus
    'Reopened' on the event side -- which is what moving back out of Resolved
    is. The mapping is looked up, never hardcoded to an id.
    """
    status_row = db.get(IncidentStatus, new_status)
    if status_row is None:
        return None
    wanted = "Reopened" if previous_status == INCIDENT_RESOLVED else status_row.name
    event_id = db.execute(
        select(IncidentEvent.id).where(IncidentEvent.name == wanted)
    ).scalars().first()
    if event_id is None:
        event_id = db.execute(
            select(IncidentEvent.id).where(IncidentEvent.name == status_row.name)
        ).scalars().first()
    return event_id


# ---------------------------------------------------------------------------
# Value-alert limit configuration
# ---------------------------------------------------------------------------


def create_limit_config(
    db: Session, *, data: dict, actor_id: uuid.UUID, facility_id: uuid.UUID
) -> ValueAlertLimitConfig:
    """A monitoring threshold for one parameter on one device."""
    with transaction(db):
        require_exists(db, Device, data.get("device_id"), "Device")
        require_exists(db, Facility, data.get("facility_id"), "Facility")
        _validate_limits(data)

        target_facility = data.get("facility_id") or facility_id
        clash = db.execute(
            select(ValueAlertLimitConfig.id)
            .where(ValueAlertLimitConfig.device_name == data["device_name"])
            .where(ValueAlertLimitConfig.parameter == data["parameter"])
            .where(ValueAlertLimitConfig.facility_id == target_facility)
        ).scalars().first()
        if clash is not None:
            raise Conflict(
                f"A limit configuration for {data['parameter']} on "
                f"{data['device_name']} already exists."
            )

        # The two flags are IKANOS text columns, not booleans.
        if "limit_check" in data:
            data["limit_check"] = bool_to_yn(data["limit_check"])
        if "is_percentage_value" in data:
            data["is_percentage_value"] = bool_to_yesno(data["is_percentage_value"])

        row = ValueAlertLimitConfig(
            id=uuid.uuid4(),
            facility_id=data.pop("facility_id", None) or facility_id,
            **data,
        )
        db.add(row)
    db.refresh(row)
    return row


def update_limit_config(
    db: Session, config_id: uuid.UUID, *, changes: dict
) -> ValueAlertLimitConfig:
    with transaction(db):
        row = require_row(db, ValueAlertLimitConfig, config_id, "Limit configuration")
        merged = {
            "is_percentage_value": row.is_percentage_value,
            "limit_low_percentage": row.limit_low_percentage,
            "limit_high_percentage": row.limit_high_percentage,
            "limit_low_value": row.limit_low_value,
            "limit_high_value": row.limit_high_value,
            **changes,
        }
        _validate_limits(merged)
        if "limit_check" in changes:
            changes["limit_check"] = bool_to_yn(changes["limit_check"])
        if "is_percentage_value" in changes:
            changes["is_percentage_value"] = bool_to_yesno(changes["is_percentage_value"])
        apply_changes(row, changes)
    db.refresh(row)
    return row


def _validate_limits(data: dict) -> None:
    """Whichever pair the config uses, low must be below high.

    `is_percentage_value` selects which pair of columns is meaningful -- the
    schema stores both, so the flag is what tells them apart.
    """
    if flag_to_bool(data.get("is_percentage_value")):
        low, high, label = (
            data.get("limit_low_percentage"),
            data.get("limit_high_percentage"),
            "percentage",
        )
    else:
        low, high, label = (
            data.get("limit_low_value"),
            data.get("limit_high_value"),
            "value",
        )
    if low is not None and high is not None and low >= high:
        raise Invalid(f"The low {label} limit must be below the high {label} limit.")
