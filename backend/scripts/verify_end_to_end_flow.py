"""End-to-End Database-Driven Reservation and Nationality Verification Script.

Executes the verification flow mandated by the user:
1. Verifies /countries and /countries/genders endpoints.
2. Creates a guest with foreign key nationality & country.
3. Verifies persistence in PostgreSQL table `app_user`.
4. Creates a stay linked to the guest.
5. Verifies retrieving the reservation and user.
6. Simulates edit reservation flow: updates guest nationality to 226 (United States).
7. Verifies PostgreSQL persistence of the update.
8. Verifies invalid foreign key rejection.
9. Cleans up test records cleanly.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app

V1 = settings.API_V1_PREFIX


def main():
    print("=" * 70)
    print("HMS END-TO-END RESERVATION DATA FLOW & NATIONALITY VERIFICATION")
    print("=" * 70)

    db = SessionLocal()
    admin_id = db.execute(
        text("SELECT id FROM app_user WHERE user_name = 'arjun.menon'")
    ).scalar_one()
    token, _ = create_access_token(admin_id)
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app, headers=headers)

    try:
        # Step 1: Verify Countries API
        print("\n[Step 1] Fetching country reference data from GET /api/v1/countries...")
        resp = client.get(f"{V1}/countries?page=1&page_size=250")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        countries_data = resp.json()
        print(f" -> Found {countries_data['total']} seeded countries in PostgreSQL.")
        assert countries_data["total"] == 239, f"Expected 239 countries, found {countries_data['total']}"
        india = next(c for c in countries_data["items"] if c["id"] == 99)
        us = next(c for c in countries_data["items"] if c["id"] == 226)
        print(f" -> Verified India: id={india['id']}, phone_code=+{india['phone_code']}, iso={india['iso_code']}")
        print(f" -> Verified United States: id={us['id']}, phone_code=+{us['phone_code']}, iso={us['iso_code']}")

        # Step 2: Verify Genders API
        print("\n[Step 2] Fetching gender reference options from GET /api/v1/countries/genders...")
        g_resp = client.get(f"{V1}/countries/genders")
        assert g_resp.status_code == 200, f"Failed: {g_resp.text}"
        genders = g_resp.json()
        print(f" -> Database pg_enum gender options: {genders}")
        assert any(g["value"] == "male" for g in genders)
        assert any(g["value"] == "female" for g in genders)
        assert any(g["value"] == "other" for g in genders)

        # Step 3: Create Guest with Nationality and Country IDs
        print("\n[Step 3] Submitting Guest Creation with Nationality ID (99) and Country ID (99)...")
        phone = f"+9199{uuid.uuid4().hex[:8]}"[:15]
        email = f"e2e_guest_{uuid.uuid4().hex[:6]}@example.com"
        create_guest_payload = {
            "first_name": "Rohan",
            "last_name": "Verma",
            "phone_number": phone,
            "email": email,
            "gender": "male",
            "country": 99,
            "nationality": 99,
            "address": "Bengaluru",
            "is_staff": 0,
        }
        print(f" -> Request Payload (POST /users):\n{create_guest_payload}")
        guest_resp = client.post(f"{V1}/users", json=create_guest_payload)
        assert guest_resp.status_code == 201, f"Failed: {guest_resp.text}"
        guest_data = guest_resp.json()
        guest_id = guest_data["id"]
        print(f" -> Response Status: 201 Created | Guest ID: {guest_id}")
        print(f" -> Response Data: nationality={guest_data['nationality']}, country={guest_data['country']}")

        # Step 4: Verify Persistence in PostgreSQL
        print("\n[Step 4] Directly inspecting PostgreSQL database table `app_user`...")
        row = db.execute(
            text("SELECT id, first_name, last_name, phone_number, email, gender, country, nationality, address FROM app_user WHERE id = :id"),
            {"id": guest_id},
        ).fetchone()
        assert row is not None
        print(f" -> Persisted row in PostgreSQL: {row}")
        assert row[6] == 99, f"Expected country 99, got {row[6]}"
        assert row[7] == 99, f"Expected nationality 99, got {row[7]}"
        print(" -> SUCCESS: Nationality 99 (India) and Country 99 verified directly in PostgreSQL.")

        # Step 5: Create Stay Linked to Booker
        print("\n[Step 5] Creating reservation linked to booker...")
        now = datetime.now(timezone.utc)
        stay_payload = {
            "booking_user_id": guest_id,
            "expected_checkin_time": now.isoformat(),
            "expected_checkout_time": (now + timedelta(days=3)).isoformat(),
            "no_of_guests": 2,
            "comments": "Automated E2E Verification Stay",
        }
        stay_resp = client.post(f"{V1}/stays", json=stay_payload)
        assert stay_resp.status_code == 201, f"Failed: {stay_resp.text}"
        stay_data = stay_resp.json()
        stay_id = stay_data["id"]
        print(f" -> Created stay: id={stay_id}, ref={stay_data['internal_stay_ref_number']}")

        # Step 6: Retrieve Stay & Guest
        print("\n[Step 6] Retrieving stay via GET /api/v1/stays/{id} and user via GET /api/v1/users/{id}...")
        stay_get = client.get(f"{V1}/stays/{stay_id}").json()
        assert stay_get["booker"]["id"] == guest_id
        assert stay_get["booker"]["name"] == "Rohan Verma"
        print(f" -> Verified stay booker reference: {stay_get['booker']}")

        user_get = client.get(f"{V1}/users/{guest_id}").json()
        assert user_get["nationality"] == 99
        assert user_get["country"] == 99
        print(f" -> Verified user record: nationality={user_get['nationality']}, country={user_get['country']}, phone={user_get['phone_number']}")

        # Step 7: Update Flow - Change Nationality to 226 (United States)
        print("\n[Step 7] Simulating Edit Reservation Flow: Updating nationality to 226 (United States)...")
        update_payload = {
            "nationality": 226,
            "country": 226,
            "phone_number": f"+1555{uuid.uuid4().hex[:6]}"[:15],
        }
        update_resp = client.patch(f"{V1}/users/{guest_id}", json=update_payload)
        assert update_resp.status_code == 200, f"Failed: {update_resp.text}"
        print(f" -> Updated user response: nationality={update_resp.json()['nationality']}, country={update_resp.json()['country']}")

        # Verify updated nationality in PostgreSQL
        updated_row = db.execute(
            text("SELECT country, nationality, phone_number FROM app_user WHERE id = :id"),
            {"id": guest_id},
        ).fetchone()
        assert updated_row[0] == 226
        assert updated_row[1] == 226
        print(f" -> Verified updated row in PostgreSQL: country={updated_row[0]}, nationality={updated_row[1]}")
        print(" -> SUCCESS: Nationality successfully updated to 226 in PostgreSQL.")

        # Step 8: Test Invalid Foreign Key Validation
        print("\n[Step 8] Testing backend validation against invalid foreign key (nationality=999999)...")
        invalid_resp = client.post(
            f"{V1}/users",
            json={
                "first_name": "Invalid",
                "phone_number": "+919876543299",
                "nationality": 999999,
                "is_staff": 0,
            },
        )
        assert invalid_resp.status_code == 422
        print(f" -> Backend correctly rejected invalid nationality: {invalid_resp.json()['error']['message']}")

        # Step 9: Teardown Test Records
        print("\n[Step 9] Cleaning up test records...")
        db.execute(text("DELETE FROM stay WHERE id = :id"), {"id": stay_id})
        db.execute(text("DELETE FROM user_role WHERE app_user_id = :id"), {"id": guest_id})
        db.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": guest_id})
        db.commit()
        print(" -> Cleaned up test stay and guest successfully.")

        print("\n" + "=" * 70)
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
