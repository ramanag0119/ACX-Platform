"""Phase 3.0 write tests: devices, firmware, incidents, limit configuration.

Run:  python -m pytest tests/test_device_write_api.py -q
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM device")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture(scope="module")
def device_type_id(db):
    return db.execute(text("SELECT id FROM device_type ORDER BY id LIMIT 1")).scalar_one()


@pytest.fixture(scope="module")
def room_id(db):
    return db.execute(text("SELECT id FROM amenity ORDER BY name LIMIT 1")).scalar_one()


def _device_payload(device_type_id, room_id, unique, **overrides) -> dict:
    payload = {
        "device_type": device_type_id,
        "amenity_id": str(room_id),
        "device_name": f"TEST{unique}",
        "manufacturer_name": "Test Manufacturer",
        "mfg_date": datetime.now(UTC).isoformat(),
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def test_create_device_persists_and_generates_a_uid(
    api, db, device_type_id, room_id, unique, cleanup
):
    r = api.post(f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique))
    assert r.status_code == 201
    body = r.json()
    cleanup.add("device", body["id"])

    assert body["device_uid"]
    row = db.execute(
        text("SELECT device_name, device_config_status, created_by, facility_id "
             "FROM device WHERE id = :i"),
        {"i": body["id"]},
    ).one()
    assert row.device_name == f"TEST{unique}"
    assert row.device_config_status == "configured", "a new device is not yet commissioned"
    assert row.created_by is not None
    assert row.facility_id is not None


def test_created_device_appears_in_the_list(api, device_type_id, room_id, unique, cleanup):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    listed = api.get(f"{V1}/devices?page_size=100").json()
    assert created["id"] in [item["id"] for item in listed["items"]]


def test_authentication_code_cannot_be_supplied(api, device_type_id, room_id, unique):
    """It is a device credential: the schema accepts no such field from a client."""
    r = api.post(
        f"{V1}/devices",
        json=_device_payload(
            device_type_id, room_id, unique, authentication_code="stolen-secret"
        ),
    )
    assert r.status_code == 422


def test_device_response_never_contains_the_credential(
    api, device_type_id, room_id, unique, cleanup
):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    )
    cleanup.add("device", created.json()["id"])
    assert "authentication_code" not in created.text
    assert "metadata" not in created.text


def test_commission_then_decommission_persists(
    api, db, device_type_id, room_id, unique, cleanup
):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    assert api.post(f"{V1}/devices/{created['id']}/commission").status_code == 200
    assert db.execute(
        text("SELECT device_config_status FROM device WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "commissioned"

    r = api.post(f"{V1}/devices/{created['id']}/decommission", json={})
    assert r.status_code == 200
    db.rollback()
    assert db.execute(
        text("SELECT device_config_status FROM device WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "decommissioned"

    # The row survives: telemetry and job orders reference it.
    assert db.execute(
        text("SELECT count(*) FROM device WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == 1


def test_commissioning_twice_is_409(api, device_type_id, room_id, unique, cleanup):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    api.post(f"{V1}/devices/{created['id']}/commission")
    r = api.post(f"{V1}/devices/{created['id']}/commission")
    assert r.status_code == 409


def test_maintenance_flag(api, db, device_type_id, room_id, unique, cleanup):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    assert api.post(f"{V1}/devices/{created['id']}/maintenance").status_code == 200
    assert db.execute(
        text("SELECT device_config_status FROM device WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "under_maintenance"


def test_update_device_appliance_and_room(
    api, db, device_type_id, room_id, unique, cleanup
):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    r = api.patch(
        f"{V1}/devices/{created['id']}", json={"appliance_name": "Refrigerator"}
    )
    assert r.status_code == 200
    assert db.execute(
        text("SELECT appliance_name FROM device WHERE id = :i"), {"i": created["id"]}
    ).scalar_one() == "Refrigerator"


def test_device_cannot_be_its_own_parent(api, device_type_id, room_id, unique, cleanup):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])

    r = api.patch(
        f"{V1}/devices/{created['id']}", json={"parent_device_id": created["id"]}
    )
    assert r.status_code == 422


def test_unknown_room_is_rejected(api, device_type_id, unique):
    r = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, uuid.uuid4(), unique)
    )
    assert r.status_code == 422


def test_unknown_device_is_404(api):
    assert api.patch(f"{V1}/devices/{uuid.uuid4()}", json={"model": "x"}).status_code == 404
    assert api.post(f"{V1}/devices/{uuid.uuid4()}/commission").status_code == 404


def test_invalid_config_status_is_rejected(api, device_type_id, room_id, unique, cleanup):
    created = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", created["id"])
    r = api.patch(f"{V1}/devices/{created['id']}", json={"device_config_status": "broken"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------


def _firmware_payload(device_type_id, unique, **overrides) -> dict:
    payload = {
        "device_type_id": device_type_id,
        "firmware_version": f"9.9.{unique[:3]}",
        "firmware_filename": f"test-{unique}.bin",
        "firmware_url": f"https://firmware.internal/test-{unique}.bin",
        "crc": f"CRC{unique.upper()}",
        "release_notes": "Write test build",
    }
    payload.update(overrides)
    return payload


def test_create_firmware_persists(api, db, device_type_id, unique, cleanup):
    r = api.post(f"{V1}/firmware", json=_firmware_payload(device_type_id, unique))
    assert r.status_code == 201
    cleanup.add("firmware", r.json()["id"])

    row = db.execute(
        text("SELECT firmware_version, status, uploaded_by FROM firmware WHERE id = :i"),
        {"i": r.json()["id"]},
    ).one()
    assert row.status == "active"
    assert row.uploaded_by is not None


def test_duplicate_version_for_a_device_type_is_409(api, device_type_id, unique, cleanup):
    first = api.post(f"{V1}/firmware", json=_firmware_payload(device_type_id, unique))
    cleanup.add("firmware", first.json()["id"])

    r = api.post(f"{V1}/firmware", json=_firmware_payload(device_type_id, unique))
    assert r.status_code == 409


def test_assign_firmware_sets_the_expected_version(
    api, db, device_type_id, room_id, unique, cleanup
):
    """That column IS the assignment -- no command table exists."""
    firmware = api.post(
        f"{V1}/firmware", json=_firmware_payload(device_type_id, unique)
    ).json()
    device = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", device["id"])
    cleanup.add("firmware", firmware["id"])

    r = api.post(
        f"{V1}/firmware/{firmware['id']}/assign", json={"device_ids": [device["id"]]}
    )
    assert r.status_code == 200
    # The column holds the firmware ID; the read model joins it to the version.
    assert str(db.execute(
        text("SELECT expected_firmware_version FROM device WHERE id = :i"),
        {"i": device["id"]},
    ).scalar_one()) == firmware["id"]


def test_assigning_to_the_wrong_device_type_is_rejected(
    api, db, device_type_id, room_id, unique, cleanup
):
    other_type = db.execute(
        text("SELECT id FROM device_type WHERE id <> :t LIMIT 1"), {"t": device_type_id}
    ).scalar_one()
    firmware = api.post(
        f"{V1}/firmware", json=_firmware_payload(device_type_id, unique)
    ).json()
    device = api.post(
        f"{V1}/devices", json=_device_payload(other_type, room_id, unique)
    ).json()
    cleanup.add("device", device["id"])
    cleanup.add("firmware", firmware["id"])

    r = api.post(
        f"{V1}/firmware/{firmware['id']}/assign", json={"device_ids": [device["id"]]}
    )
    assert r.status_code == 422
    assert "device type" in r.json()["error"]["message"]


def test_decommissioning_firmware_still_expected_by_a_device_is_409(
    api, device_type_id, room_id, unique, cleanup
):
    firmware = api.post(
        f"{V1}/firmware", json=_firmware_payload(device_type_id, unique)
    ).json()
    device = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.sql("UPDATE device SET expected_firmware_version = NULL WHERE id = :value",
                {"value": device["id"]})
    cleanup.add("device", device["id"])
    cleanup.add("firmware", firmware["id"])

    api.post(f"{V1}/firmware/{firmware['id']}/assign", json={"device_ids": [device["id"]]})
    r = api.patch(f"{V1}/firmware/{firmware['id']}", json={"status": "decommissioned"})
    assert r.status_code == 409
    assert "still the expected version" in r.json()["error"]["message"]


def test_assigning_a_decommissioned_build_is_409(api, device_type_id, unique, cleanup):
    firmware = api.post(
        f"{V1}/firmware",
        json=_firmware_payload(device_type_id, unique, status="decommissioned"),
    ).json()
    cleanup.add("firmware", firmware["id"])

    r = api.post(
        f"{V1}/firmware/{firmware['id']}/assign", json={"device_ids": [str(uuid.uuid4())]}
    )
    assert r.status_code == 409


def test_a_failed_assignment_rolls_back_every_device(
    api, db, device_type_id, room_id, unique, cleanup
):
    """Two devices, the second unknown: neither may end up assigned."""
    firmware = api.post(
        f"{V1}/firmware", json=_firmware_payload(device_type_id, unique)
    ).json()
    device = api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    ).json()
    cleanup.add("device", device["id"])
    cleanup.add("firmware", firmware["id"])

    r = api.post(
        f"{V1}/firmware/{firmware['id']}/assign",
        json={"device_ids": [device["id"], str(uuid.uuid4())]},
    )
    assert r.status_code == 404
    db.rollback()
    assert db.execute(
        text("SELECT expected_firmware_version FROM device WHERE id = :i"),
        {"i": device["id"]},
    ).scalar_one() is None


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


@pytest.fixture
def incident(db, cleanup):
    """A seeded incident, with its original state restored afterwards."""
    row = db.execute(
        text("SELECT id, current_incident_status, assigned_to FROM device_incident "
             "ORDER BY created_on LIMIT 1")
    ).one()
    cleanup.sql(
        "UPDATE device_incident SET current_incident_status = :status, assigned_to = :who "
        "WHERE id = :value",
        {"status": row.current_incident_status, "who": row.assigned_to, "value": row.id},
    )
    cleanup.sql(
        "DELETE FROM incident_history WHERE incident_id = :value AND created_on > now() - "
        "interval '1 hour'",
        {"value": row.id},
    )
    return row.id


def test_resolving_an_incident_persists_and_writes_history(api, db, incident):
    # Start from a known status so the transition is real regardless of order.
    api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 2})
    db.rollback()
    before = db.execute(
        text("SELECT count(*) FROM incident_history WHERE incident_id = :i"), {"i": incident}
    ).scalar_one()

    r = api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 4})
    assert r.status_code == 200
    assert r.json()["current_incident_status"] == 4

    db.rollback()
    assert db.execute(
        text("SELECT current_incident_status FROM device_incident WHERE id = :i"),
        {"i": incident},
    ).scalar_one() == 4
    after = db.execute(
        text("SELECT count(*) FROM incident_history WHERE incident_id = :i"), {"i": incident}
    ).scalar_one()
    assert after == before + 1, "every transition appends an incident_history row"


def test_assigning_an_incident_moves_it_to_assigned(api, db, incident, staff_id):
    api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 1})
    r = api.patch(f"{V1}/incidents/{incident}", json={"assigned_to": str(staff_id)})
    assert r.status_code == 200
    assert r.json()["current_incident_status"] == 3
    db.rollback()
    row = db.execute(
        text("SELECT current_incident_status, assigned_to FROM device_incident WHERE id = :i"),
        {"i": incident},
    ).one()
    assert row.current_incident_status == 3
    assert row.assigned_to == staff_id


def test_reopening_a_resolved_incident_records_the_reopened_event(api, db, incident):
    api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 4})
    api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 2})
    db.rollback()

    latest_event = db.execute(
        text("""SELECT e.name FROM incident_history h
                JOIN incident_event e ON e.id = h.incident_event_id
                WHERE h.incident_id = :i ORDER BY h.id DESC LIMIT 1"""),
        {"i": incident},
    ).scalar_one()
    assert latest_event == "Reopened"


def test_invalid_incident_status_is_rejected(api, incident):
    r = api.patch(f"{V1}/incidents/{incident}", json={"current_incident_status": 9})
    assert r.status_code == 422


def test_unknown_incident_is_404(api):
    r = api.patch(f"{V1}/incidents/{uuid.uuid4()}", json={"current_incident_status": 2})
    assert r.status_code == 404


def test_alerts_themselves_have_no_write_route(api, db):
    alert_id = db.execute(text("SELECT id FROM device_alert LIMIT 1")).scalar_one()
    r = api.patch(f"{V1}/alerts/{alert_id}", json={"alert_severity": "warning"})
    assert r.status_code == 405


# ---------------------------------------------------------------------------
# Limit configuration
# ---------------------------------------------------------------------------


def test_create_and_list_limit_config(api, db, unique, cleanup):
    device = db.execute(
        text("SELECT id, device_name FROM device WHERE device_name IS NOT NULL LIMIT 1")
    ).one()

    r = api.post(
        f"{V1}/limit-configs",
        json={
            # UNIQUE (device_name, parameter, facility_id): use a parameter the
            # seeded configs do not already cover for this device.
            "parameter": f"test_param_{unique}",
            "device_name": device.device_name,
            "device_id": str(device.id),
            "is_percentage_value": True,
            "nominal": "230",
            "limit_low_percentage": "10",
            "limit_high_percentage": "20",
            "remarks": f"Write test {unique}",
        },
    )
    assert r.status_code == 201
    cleanup.add("value_alert_limit_config", r.json()["id"])

    listed = api.get(f"{V1}/limit-configs?page_size=100").json()
    assert r.json()["id"] in [item["id"] for item in listed["items"]]
    assert db.execute(
        text("SELECT nominal FROM value_alert_limit_config WHERE id = :i"),
        {"i": r.json()["id"]},
    ).scalar_one() == 230


def test_low_above_high_is_rejected(api, db, unique):
    device_name = db.execute(
        text("SELECT device_name FROM device WHERE device_name IS NOT NULL LIMIT 1")
    ).scalar_one()
    r = api.post(
        f"{V1}/limit-configs",
        json={
            "parameter": f"bad_param_{unique}",
            "device_name": device_name,
            "is_percentage_value": False,
            "limit_low_value": "250",
            "limit_high_value": "200",
            "remarks": f"Bad {unique}",
        },
    )
    assert r.status_code == 422
    assert "below the high" in r.json()["error"]["message"]


def test_update_limit_config(api, db, unique, cleanup):
    device_name = db.execute(
        text("SELECT device_name FROM device WHERE device_name IS NOT NULL LIMIT 1")
    ).scalar_one()
    created = api.post(
        f"{V1}/limit-configs",
        json={"parameter": f"edit_param_{unique}", "device_name": device_name,
              "is_percentage_value": False, "limit_low_value": "1",
              "limit_high_value": "10", "remarks": f"Edit {unique}"},
    ).json()
    cleanup.add("value_alert_limit_config", created["id"])

    r = api.patch(f"{V1}/limit-configs/{created['id']}", json={"limit_high_value": "15"})
    assert r.status_code == 200
    assert db.execute(
        text("SELECT limit_high_value FROM value_alert_limit_config WHERE id = :i"),
        {"i": created["id"]},
    ).scalar_one() == 15


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


def test_anonymous_cannot_write(anon_api, device_type_id, room_id, unique):
    r = anon_api.post(f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique))
    assert r.status_code == 401


def test_duty_manager_cannot_change_the_device_network(
    manager_api, db, device_type_id, room_id, unique
):
    """Read the grant, do not assume it.

    The seeded Duty Manager holds `caleido_network` with read_access true and
    write_access FALSE, and no `firmware_management` grant at all -- so every
    write in this module is refused for them. The assertion is derived from the
    database so it stays true if the seeded grants change.
    """
    writable = {
        row[0]
        for row in db.execute(
            text(
                """SELECT rm.module_name FROM app_user u
                   JOIN user_role ur ON ur.app_user_id = u.id
                   JOIN role_module_permission p ON p.role_id = ur.role_id
                   JOIN role_module rm ON rm.id = p.module_id
                   WHERE u.user_name = 'kavya.iyer' AND p.write_access IS TRUE"""
            )
        ).all()
    }
    assert "caleido_network" not in writable
    assert "firmware_management" not in writable

    device = manager_api.post(
        f"{V1}/devices", json=_device_payload(device_type_id, room_id, unique)
    )
    assert device.status_code == 403
    assert device.json()["error"]["code"] == "forbidden"

    firmware = manager_api.post(
        f"{V1}/firmware", json=_firmware_payload(device_type_id, unique)
    )
    assert firmware.status_code == 403
