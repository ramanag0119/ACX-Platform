"""Step 7 - firmware, devices, MQTT transport and the command queue.

14 devices. Three rooms are fully instrumented with the real IKANOS device
family -- Intellihub (hub) parenting a Mikos, an AirQ and a Kleio -- plus two
standalone units that exercise the decommissioned and under_maintenance states.

Device states covered:
    health_status         Active / Inactive
    device_config_status  commissioned / configured / bad_configuration /
                          decommissioned / under_maintenance / missing

NOTE: `ip_address`, `mac_address` and `last_seen` are NOT columns in IKANOS and
are not seeded. Connectivity is expressed by `health_status`, and "last seen"
is derived from `device_health_stat.created_on`.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    CommandType,
    Device,
    DeviceCommand,
    Firmware,
    MqttBroker,
    MqttTopic,
)
from seeds.helpers import DEMO_NOW, days, did, hours, upsert

HUB, AIRQ, MIKOS, KLEIO = 1, 2, 3, 4  # device_type ids from IKANOS

# (key, device_type, version, is_current_default, status)
FIRMWARE = [
    ("hub-2-4-1", HUB, "2.4.1", True, "active"),
    ("hub-2-5-0", HUB, "2.5.0", False, "active"),
    ("airq-1-8-3", AIRQ, "1.8.3", True, "active"),
    ("mikos-3-1-2", MIKOS, "3.1.2", True, "active"),
    ("mikos-3-0-9", MIKOS, "3.0.9", False, "decommissioned"),
    ("kleio-4-2-0", KLEIO, "4.2.0", True, "active"),
]

# (key, room, device_type, parent key or None, health, config_status,
#  firmware key, appliance name, temperature)
DEVICES = [
    # Room 101 -- fully healthy suite
    ("101-hub", "101", HUB, None, "Active", "commissioned", "hub-2-4-1",
     "Room Controller", Decimal("41.20")),
    ("101-mik", "101", MIKOS, "101-hub", "Active", "commissioned", "mikos-3-1-2",
     "Energy Meter", Decimal("38.50")),
    ("101-air", "101", AIRQ, "101-hub", "Active", "commissioned", "airq-1-8-3",
     "Air Quality Sensor", Decimal("34.10")),
    ("101-kle", "101", KLEIO, "101-hub", "Active", "commissioned", "kleio-4-2-0",
     "Door Lock", Decimal("31.50")),
    # Room 205 -- AirQ reporting poor air quality, Mikos running hot
    ("205-hub", "205", HUB, None, "Active", "commissioned", "hub-2-4-1",
     "Room Controller", Decimal("43.80")),
    ("205-mik", "205", MIKOS, "205-hub", "Active", "commissioned", "mikos-3-1-2",
     "Energy Meter", Decimal("66.00")),
    ("205-air", "205", AIRQ, "205-hub", "Active", "commissioned", "airq-1-8-3",
     "Air Quality Sensor", Decimal("35.90")),
    ("205-kle", "205", KLEIO, "205-hub", "Active", "commissioned", "kleio-4-2-0",
     "Door Lock", Decimal("30.20")),
    # Room 106 -- hub offline, so its children cannot report either
    ("106-hub", "106", HUB, None, "Inactive", "missing", "hub-2-4-1",
     "Room Controller", None),
    ("106-mik", "106", MIKOS, "106-hub", "Inactive", "configured", "mikos-3-1-2",
     "Energy Meter", None),
    ("106-air", "106", AIRQ, "106-hub", "Inactive", "configured", "airq-1-8-3",
     "Air Quality Sensor", None),
    ("106-kle", "106", KLEIO, "106-hub", "Active", "commissioned", "kleio-4-2-0",
     "Door Lock", Decimal("29.80")),
    # Standalone units
    ("104-kle", "104", KLEIO, None, "Inactive", "under_maintenance", "kleio-4-2-0",
     "Door Lock", None),
    ("rest-mik", "REST01", MIKOS, None, "Active", "bad_configuration", "mikos-3-0-9",
     "Kitchen Energy Meter", Decimal("52.40")),
]

# (key, device, command_type id, processing status)
COMMANDS = [
    ("cmd-key-101", "101-kle", 1, "Processed"),      # Keys
    ("cmd-key-205", "205-kle", 1, "Processed"),      # Keys
    ("cmd-dnd-205", "205-hub", 5, "Processed"),      # SetDNDMode
    ("cmd-fw-106", "106-hub", 2, "Error"),           # FirmwareUpdates
    ("cmd-checkout-106", "106-hub", 3, "Queued"),    # Checkout
    ("cmd-maint-104", "104-kle", 6, "Processing"),   # MaintenanceMode
    ("cmd-defaultkey", "101-kle", 9, "Processed"),   # DefaultKey
]

TOPIC_TYPES = ["DeviceData", "DeviceAlert", "DeviceHealth", "LastWill"]


def seed(session: Session, ctx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    facility = ctx["facility"]
    system = ctx["system_user"]
    users = ctx["users"]
    rooms = ctx["rooms"]

    firmware = {}
    for key, device_type, version, _is_default, status in FIRMWARE:
        firmware[key] = upsert(
            session,
            Firmware,
            {"id": did("firmware", key)},
            device_type_id=device_type,
            firmware_version=version,
            firmware_filename=f"{key}.bin",
            firmware_url=f"https://firmware.example.invalid/demo/{key}.bin",
            firmware_size=Decimal("512.00"),
            crc=f"crc32:{key}",
            release_date=DEMO_NOW - days(90),
            release_notes=f"Demo release notes for {version}",
            decommission_reason=(
                "Superseded by 3.1.2" if status == "decommissioned" else None
            ),
            status=status,
            uploaded_by=users["vikram.rao"].id,
            created_by=users["vikram.rao"].id,
            updated_by=users["vikram.rao"].id,
        )
    ctx["firmware"] = firmware
    counts["firmware"] = len(firmware)

    devices: dict[str, Device] = {}
    # Two passes: hubs first, so a child can point at its parent.
    for pass_no in (0, 1):
        for (key, room, device_type, parent_key, health, config_status,
             fw_key, appliance, temperature) in DEVICES:
            is_child = parent_key is not None
            if (pass_no == 0) == is_child:
                continue
            # 106's hub is missing, so its children advertise a newer expected
            # firmware they have not been able to take.
            expected = firmware["hub-2-5-0"] if key == "106-hub" else firmware[fw_key]
            devices[key] = upsert(
                session,
                Device,
                {"id": did("device", key)},
                device_uid=f"DEV{key.upper().replace('-', '')}"[:16],
                part_number=f"PN-{device_type}-000{pass_no}",
                model=f"MDL-{device_type}",
                manufacturer_name="Caleido",
                mfg_date=DEMO_NOW - days(365),
                parent_device_id=devices[parent_key].id if parent_key else None,
                device_type=device_type,
                device_name=f"{room}{'HUB' if device_type == HUB else ''}"[:100] or key,
                appliance_name=appliance,
                facility_id=facility.id,
                amenity_id=rooms[room].id,
                authentication_code=f"AUTH{key[:12]}",
                health_status=health,
                device_temperature=temperature,
                current_firmware_version=firmware[fw_key].id,
                expected_firmware_version=expected.id,
                device_config_status=config_status,
                is_power_off=health == "Inactive",
                installed_on=DEMO_NOW - days(300),
                operational_mode=2 if device_type == HUB else 1,
                is_other_device=None,
                status=1,
                device_metadata={"room": room, "seeded": True},
                created_by=users["vikram.rao"].id,
            )
    ctx["devices"] = devices
    counts["device"] = len(devices)

    broker = upsert(
        session,
        MqttBroker,
        {"id": did("mqtt_broker", "primary")},
        facility_id=facility.id,
        broker_name="ikanos-demo-broker",
        broker_ip="10.20.0.11",
        broker_vpn_ip="10.99.0.11",
        broker_port=1883,
        broker_user_name="caleido",
        # Placeholder only. IKANOS stores this in clear text; HMS must encrypt
        # it at rest before any real credential is written (OPEN DECISION #14).
        broker_password="!seed-placeholder",
    )
    counts["mqtt_broker"] = 1

    n_topics = 0
    for hub_key in ("101-hub", "205-hub", "106-hub"):
        for topic_type in TOPIC_TYPES:
            upsert(
                session,
                MqttTopic,
                {"id": did("mqtt_topic", f"{hub_key}:{topic_type}")},
                mqtt_broker_id=broker.id,
                device_id=devices[hub_key].id,
                topic_name=f"ikg/{hub_key}/{topic_type.lower()}"[:50],
                topic_type=topic_type,
            )
            n_topics += 1
    counts["mqtt_topic"] = n_topics

    for key, device_key, command_type, status in COMMANDS:
        upsert(
            session,
            DeviceCommand,
            {"id": did("device_command", key)},
            device_id=devices[device_key].id,
            command_type=command_type,
            command_data={"demo": True, "command": key},
            processing_status=status,
            created_by=users["vikram.rao"].id,
        )
    counts["device_command"] = len(COMMANDS)

    return counts
