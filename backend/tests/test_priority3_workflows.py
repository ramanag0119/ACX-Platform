"""Integration and persistence tests for HMS Priority 3 Workflows:
1. Service Tracking -- Database-driven aggregate counts
2. Tickets -- Quantity fetched from actual database records
3. User Roles -- Role notification preferences persisted correctly
4. Reservations -- Bulk Upload fully integrated with backend
5. Key Settings -- Settings fetched, saved, and reset through backend APIs

Run: python -m pytest tests/test_priority3_workflows.py -q
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import settings

V1 = settings.API_V1_PREFIX

pytestmark = pytest.mark.usefixtures("require_seeded")


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM app_user")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


# ===========================================================================
# 1. Service Tracking -- Database-driven aggregate counts
# ===========================================================================


def test_service_tracking_summary_aggregates(api, db):
    """Aggregate counts in tracking summary must match actual database records."""
    r = api.get(f"{V1}/service-requests/summary")
    assert r.status_code == 200
    data = r.json()

    # Verify global counts against database
    db_total = db.execute(text("SELECT count(*) FROM service_request")).scalar() or 0
    db_completed = db.execute(
        text(
            "SELECT count(*) FROM service_request sr "
            "JOIN service_status ss ON ss.id = sr.status "
            "WHERE ss.name = 'Completed'"
        )
    ).scalar() or 0
    db_pending = db_total - db_completed

    assert data["total_services"] == db_total
    assert data["total_completed"] == db_completed
    assert data["total_pending"] == db_pending
    assert "by_type" in data
    assert len(data["by_type"]) > 0

    # Verify each service type has database-consistent metrics
    for item in data["by_type"]:
        st_id = item["service_type_id"]
        st_total = db.execute(
            text("SELECT count(*) FROM service_request WHERE service_type = :st_id"),
            {"st_id": st_id},
        ).scalar() or 0
        assert item["total_count"] == st_total
        assert item["completed_count"] + item["pending_count"] == st_total


# ===========================================================================
# 2. Tickets -- Database-driven quantity
# ===========================================================================


def test_ticket_list_quantity_aggregation(api, db):
    """Tickets endpoint must return actual database-calculated quantities from items."""
    r = api.get(f"{V1}/service-requests?page=1&page_size=10")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0

    for req in items:
        req_id = req["id"]
        # Actual database item quantity sum
        expected_qty = db.execute(
            text("SELECT sum(quantity) FROM service_request_item WHERE service_request_id = :rid"),
            {"rid": req_id},
        ).scalar()

        if expected_qty is not None:
            assert req["quantity"] == int(expected_qty)
        else:
            assert req["quantity"] is None or req["quantity"] == 0


# ===========================================================================
# 3. User Roles -- Role notification preferences persisted correctly
# ===========================================================================


def test_role_notification_preferences_crud(api, db, unique, cleanup):
    """Notification preferences must persist in role table and survive updates and reloads."""
    role_name = f"Test Role Notif {unique}"
    prefs = ["email", "sms"]

    # Create role with preferences
    r_create = api.post(
        f"{V1}/roles",
        json={
            "name": role_name,
            "role_type": "staff",
            "notification_preferences": prefs,
        },
    )
    assert r_create.status_code == 201
    created = r_create.json()
    cleanup.add("role", created["id"])

    assert created["notification_preferences"] == prefs

    # Verify directly in PostgreSQL
    db_prefs = db.execute(
        text("SELECT notification_preferences FROM role WHERE id = :rid"),
        {"rid": created["id"]},
    ).scalar()
    assert db_prefs == prefs

    # Reload via GET endpoint
    r_get = api.get(f"{V1}/roles")
    assert r_get.status_code == 200
    matched = [r for r in r_get.json()["items"] if r["id"] == created["id"]]
    assert len(matched) == 1
    assert matched[0]["notification_preferences"] == prefs

    # Update preferences
    new_prefs = ["push", "silent"]
    r_patch = api.patch(
        f"{V1}/roles/{created['id']}",
        json={"notification_preferences": new_prefs},
    )
    assert r_patch.status_code == 200
    updated = r_patch.json()
    assert updated["notification_preferences"] == new_prefs

    # Verify update in PostgreSQL
    db_updated = db.execute(
        text("SELECT notification_preferences FROM role WHERE id = :rid"),
        {"rid": created["id"]},
    ).scalar()
    assert db_updated == new_prefs


# ===========================================================================
# 4. Reservations -- Bulk Upload fully integrated with backend
# ===========================================================================


def test_bulk_upload_reservations_and_template(api, db, unique, cleanup):
    """Bulk upload processes CSV, persists Stays and records an ImportJob."""
    # 1. Download template
    r_tmpl = api.get(f"{V1}/stays/bulk-upload/template")
    assert r_tmpl.status_code == 200
    assert "guest_name" in r_tmpl.text
    assert "room_number" in r_tmpl.text

    # 2. Find an available room
    room = db.execute(
        text("SELECT id, name FROM amenity WHERE status = 0 LIMIT 1")
    ).fetchone()
    if not room:
        room = db.execute(text("SELECT id, name FROM amenity LIMIT 1")).fetchone()
    room_name = room[1]

    # Prepare CSV content
    guest_email = f"guest_{unique[:8]}@example.com"
    checkin = (datetime.now(UTC) + timedelta(days=20)).strftime("%Y-%m-%d 14:00")
    checkout = (datetime.now(UTC) + timedelta(days=23)).strftime("%Y-%m-%d 11:00")

    csv_data = (
        "guest_name,guest_email,guest_phone_number,room_number,checkin_date,checkout_date,no_of_guests,comments\n"
        f"Test Booker {unique[:6]},{guest_email},+919876543210,{room_name},{checkin},{checkout},2,Ocean view please\n"
    )

    # 3. Post bulk upload file
    files = {"file": ("bulk_test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    r_upload = api.post(f"{V1}/stays/bulk-upload", files=files)
    assert r_upload.status_code == 200
    upload_res = r_upload.json()

    assert upload_res["total_records"] == 1
    assert upload_res["success_count"] == 1
    assert upload_res["error_count"] == 0
    assert upload_res["status"] == "success"

    job_id = upload_res["import_job_id"]
    cleanup.add("import_job", job_id)

    # Verify ImportJob in PostgreSQL
    db_job = db.execute(
        text("SELECT entity_type, import_status, success_count FROM import_job WHERE id = :jid"),
        {"jid": job_id},
    ).fetchone()
    assert db_job is not None
    assert db_job[0] == "booking"
    assert db_job[1] == "success"
    assert db_job[2] == 1

    # Verify Stay record created in PostgreSQL
    created_stay = db.execute(
        text(
            "SELECT s.id, s.internal_stay_ref_number FROM stay s "
            "JOIN app_user u ON u.id = s.booking_user_id "
            "WHERE u.email = :email"
        ),
        {"email": guest_email},
    ).fetchone()
    assert created_stay is not None
    cleanup.sql("DELETE FROM room_allocation WHERE stay_id = :sid", {"sid": created_stay[0]})
    cleanup.sql("DELETE FROM stay_user WHERE stay_id = :sid", {"sid": created_stay[0]})
    cleanup.add("stay", created_stay[0])

    # 4. Check last report endpoint
    r_last = api.get(f"{V1}/stays/bulk-upload/last-report")
    assert r_last.status_code == 200
    last_report = r_last.json()
    assert last_report is not None
    assert last_report["id"] == str(job_id)


# ===========================================================================
# 5. Key Settings -- Settings fetched, saved, and reset through backend APIs
# ===========================================================================


def test_key_settings_crud_and_reset(api, db, cleanup):
    """Key settings must load from facility, persist updates, and execute Reset."""
    # 1. GET key settings
    r_get = api.get(f"{V1}/key-settings")
    assert r_get.status_code == 200
    settings_data = r_get.json()
    assert "facility_id" in settings_data
    assert "active_keys_count" in settings_data

    orig_manager = settings_data["default_key_user"]
    facility_id = settings_data["facility_id"]

    # 2. Pick a staff user
    staff_user = db.execute(
        text("SELECT id, first_name, last_name, email FROM app_user WHERE is_staff = 1 LIMIT 1")
    ).fetchone()
    staff_id = str(staff_user[0])

    # 3. Update key settings (Save)
    r_put = api.put(f"{V1}/key-settings", json={"default_key_user": staff_id})
    assert r_put.status_code == 200
    updated = r_put.json()
    assert updated["default_key_user"] == staff_id
    assert updated["manager_name"] is not None

    # Verify persistence in facility table
    db_facility_mgr = db.execute(
        text("SELECT default_key_user FROM facility WHERE id = :fid"),
        {"fid": facility_id},
    ).scalar()
    assert str(db_facility_mgr) == staff_id

    # 4. Reset key settings
    r_reset = api.post(f"{V1}/key-settings/reset")
    assert r_reset.status_code == 200
    reset_data = r_reset.json()
    assert reset_data["default_key_user"] is None
    assert reset_data["active_keys_count"] == 0

    # Verify in PostgreSQL
    db_reset_mgr = db.execute(
        text("SELECT default_key_user FROM facility WHERE id = :fid"),
        {"fid": facility_id},
    ).scalar()
    assert db_reset_mgr is None

    # Restore original manager if there was one
    if orig_manager:
        db.execute(
            text("UPDATE facility SET default_key_user = :uid WHERE id = :fid"),
            {"uid": orig_manager, "fid": facility_id},
        )
        db.commit()
