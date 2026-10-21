"""Tests for Priority 4: Database Architecture
Item 12: Energy Telemetry Device Foreign Key
Item 13: Billing/Pricing and Currency

Run: python -m pytest tests/test_priority4_database_architecture.py -v
"""

from __future__ import annotations

import uuid
from decimal import Decimal

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
# ITEM 12: Energy Telemetry Device Foreign Key
# ===========================================================================


def test_energy_stat_device_foreign_key_schema(db):
    """Verify energy_stat table has device_id column with NOT NULL and FK to device.id."""
    # Check column existence and nullability
    col_info = db.execute(
        text(
            "SELECT is_nullable, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = 'energy_stat' AND column_name = 'device_id'"
        )
    ).fetchone()
    assert col_info is not None, "device_id column missing on energy_stat table"
    assert col_info[0] == "NO", "device_id must be NOT NULL on energy_stat"
    assert col_info[1] == "uuid", "device_id must be UUID type"

    # Check foreign key constraint
    fk_info = db.execute(
        text(
            "SELECT tc.constraint_name, ccu.table_name, ccu.column_name "
            "FROM information_schema.table_constraints AS tc "
            "JOIN information_schema.constraint_column_usage AS ccu "
            "  ON ccu.constraint_name = tc.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' "
            "  AND tc.table_name = 'energy_stat' "
            "  AND ccu.table_name = 'device'"
        )
    ).fetchall()
    assert len(fk_info) > 0, "Foreign key constraint from energy_stat to device missing"
    assert fk_info[0][2] == "id", "FK must point to device(id)"


def test_energy_stat_backfill_integrity(db):
    """Historical telemetry records must be intact and properly mapped to actual devices."""
    # Verify count of records
    total_count = db.execute(text("SELECT count(*) FROM energy_stat")).scalar()
    assert total_count >= 72, f"Expected at least 72 historical energy_stat rows, found {total_count}"

    # Verify zero unresolved or NULL device_id records
    null_count = db.execute(
        text("SELECT count(*) FROM energy_stat WHERE device_id IS NULL")
    ).scalar()
    assert null_count == 0, f"Found {null_count} energy_stat rows with NULL device_id"

    # Verify every device_id references a real device
    orphan_count = db.execute(
        text(
            "SELECT count(*) FROM energy_stat es "
            "LEFT JOIN device d ON d.id = es.device_id "
            "WHERE d.id IS NULL"
        )
    ).scalar()
    assert orphan_count == 0, f"Found {orphan_count} orphaned energy_stat records"


def test_energy_stat_api_retrieval_and_device_filter(api, db):
    """GET /energy-stats must return device_id, device_uid, energy_unit and allow device_id filter."""
    # Fetch first seeded energy stat from db to get its device_id
    row = db.execute(
        text("SELECT device_id, device_name FROM energy_stat LIMIT 1")
    ).fetchone()
    assert row is not None
    target_device_id = str(row[0])

    # Query without filter
    r = api.get(f"{V1}/energy-stats?page=1&page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) > 0

    item = data["items"][0]
    assert "device_id" in item
    assert item["device_id"] is not None
    assert "device_uid" in item
    assert "energy_unit" in item
    assert item["energy_unit"] == "kWh"

    # Query with device_id filter
    r_filtered = api.get(f"{V1}/energy-stats?device_id={target_device_id}&page=1&page_size=50")
    assert r_filtered.status_code == 200
    filtered_data = r_filtered.json()
    assert len(filtered_data["items"]) > 0
    for it in filtered_data["items"]:
        assert it["device_id"] == target_device_id


def test_energy_stats_summary_with_device_filter(api, db):
    """GET /energy-stats/summary must support device_id filter."""
    row = db.execute(
        text("SELECT device_id FROM energy_stat LIMIT 1")
    ).fetchone()
    target_device_id = str(row[0])

    r = api.get(f"{V1}/energy-stats/summary?device_id={target_device_id}")
    assert r.status_code == 200
    summary = r.json()
    assert "reading_count" in summary
    assert summary["reading_count"] > 0
    assert "total_energy_consumed" in summary
    assert "energy_unit" in summary
    assert summary["energy_unit"] == "kWh"


def test_energy_stat_ingestion_valid_device_id(api, db, cleanup):
    """POST /energy-stats with valid device_id must succeed and persist FK relationship."""
    # Get a real device
    device_row = db.execute(
        text("SELECT id, device_uid, device_name FROM device LIMIT 1")
    ).fetchone()
    assert device_row is not None
    dev_id, dev_uid, dev_name = str(device_row[0]), device_row[1], device_row[2]

    payload = {
        "device_id": dev_id,
        "energy": 42.50,
        "power": 350.0,
        "voltage": 230.0,
        "current": 1.52,
    }
    r = api.post(f"{V1}/energy-stats", json=payload)
    assert r.status_code == 201, f"Ingestion failed: {r.text}"
    created = r.json()
    assert created["device_id"] == dev_id
    assert created["device_uid"] == dev_uid
    assert created["energy_consumed"] == 42.50
    assert created["energy_unit"] == "kWh"

    cleanup.sql(
        "DELETE FROM energy_stat WHERE device_name = :d AND hour = :h",
        {"d": created["device_name"], "h": created["hour"]},
    )


def test_energy_stat_ingestion_valid_device_uid_resolution(api, db, cleanup):
    """POST /energy-stats with device_uid must resolve to the authoritative device record."""
    device_row = db.execute(
        text("SELECT id, device_uid FROM device LIMIT 1")
    ).fetchone()
    dev_id, dev_uid = str(device_row[0]), device_row[1]

    payload = {
        "device_uid": dev_uid,
        "energy": 99.15,
        "power": 120.0,
    }
    r = api.post(f"{V1}/energy-stats", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["device_id"] == dev_id
    assert created["device_uid"] == dev_uid
    assert created["energy_consumed"] == 99.15

    cleanup.sql(
        "DELETE FROM energy_stat WHERE device_name = :d AND hour = :h",
        {"d": created["device_name"], "h": created["hour"]},
    )


def test_energy_stat_ingestion_unknown_device_rejected(api):
    """POST /energy-stats with non-existent device must return 422."""
    fake_id = str(uuid.uuid4())
    payload = {
        "device_id": fake_id,
        "energy": 10.0,
    }
    r = api.post(f"{V1}/energy-stats", json=payload)
    assert r.status_code == 422
    assert "not found" in r.text.lower() or "unknown device" in r.text.lower()


def test_energy_stat_ingestion_missing_identifiers_rejected(api):
    """POST /energy-stats without any device identifier must return 422."""
    payload = {
        "energy": 10.0,
    }
    r = api.post(f"{V1}/energy-stats", json=payload)
    assert r.status_code == 422
    assert "at least one device identifier" in r.text.lower()


# ===========================================================================
# ITEM 13: Billing, Pricing and Currency
# ===========================================================================


def test_currency_master_table_schema_and_seeds(db):
    """Verify currency master table exists and holds authoritative ISO 4217 currencies."""
    currencies = db.execute(
        text("SELECT id, code, name, symbol, minor_units, is_active FROM currency ORDER BY id")
    ).fetchall()
    assert len(currencies) >= 7, "Currency table should have at least 7 seeded currencies"

    currency_map = {c[1]: c for c in currencies}
    assert "INR" in currency_map
    assert currency_map["INR"][3] == "₹"
    assert currency_map["INR"][4] == 2
    assert currency_map["INR"][5] is True

    assert "USD" in currency_map
    assert currency_map["USD"][3] == "$"

    assert "EUR" in currency_map
    assert currency_map["EUR"][3] == "€"


def test_currencies_api_endpoints(api):
    """GET /currencies and GET /currencies/{id_or_code} must return authoritative currency records."""
    # List active currencies
    r = api.get(f"{V1}/currencies")
    assert r.status_code == 200
    currencies = r.json()
    assert isinstance(currencies, list)
    codes = [c["code"] for c in currencies]
    assert "INR" in codes
    assert "USD" in codes
    assert "EUR" in codes

    # Get by code
    r_code = api.get(f"{V1}/currencies/INR")
    assert r_code.status_code == 200
    inr = r_code.json()
    assert inr["code"] == "INR"
    assert inr["symbol"] == "₹"
    assert inr["id"] == 1

    # Get by id
    r_id = api.get(f"{V1}/currencies/1")
    assert r_id.status_code == 200
    assert r_id.json()["code"] == "INR"

    # Unknown currency code
    r_unknown = api.get(f"{V1}/currencies/XYZ")
    assert r_unknown.status_code == 404


def test_facility_currency_relationship_and_validation(api, db, cleanup):
    """Facility currency relationship must be enforced and validated."""
    fac = db.execute(text("SELECT id, currency_id FROM facility LIMIT 1")).fetchone()
    assert fac is not None
    fac_id = str(fac[0])
    orig_currency_id = fac[1]

    # Verify facility has a valid currency_id referencing currency(id)
    assert orig_currency_id is not None
    curr_exists = db.execute(
        text("SELECT id FROM currency WHERE id = :id"), {"id": orig_currency_id}
    ).fetchone()
    assert curr_exists is not None

    # Register restore in cleanup
    cleanup.sql(
        "UPDATE facility SET currency_id = :cid WHERE id = :fid",
        {"cid": orig_currency_id, "fid": fac_id},
    )

    # Test facility update with valid currency (USD = 2) via PATCH
    r_update = api.patch(f"{V1}/facilities/{fac_id}", json={"currency_id": 2})
    assert r_update.status_code == 200
    assert r_update.json()["currency_id"] == 2
    assert r_update.json()["currency"]["code"] == "USD"
    assert r_update.json()["currency"]["symbol"] == "$"

    # Test facility update with invalid currency_id (e.g. 999)
    r_invalid = api.patch(f"{V1}/facilities/{fac_id}", json={"currency_id": 999})
    assert r_invalid.status_code == 422
    assert "currency 999 does not exist" in r_invalid.text.lower()


def test_package_pricing_schema_and_persistence(api, db, cleanup, unique):
    """Package must support price and currency_id, with foreign key integrity."""
    # Verify package table schema
    price_col = db.execute(
        text(
            "SELECT data_type, numeric_precision, numeric_scale "
            "FROM information_schema.columns "
            "WHERE table_name = 'package' AND column_name = 'price'"
        )
    ).fetchone()
    assert price_col is not None, "price column missing on package"
    assert price_col[0] == "numeric"
    assert price_col[1] == 10
    assert price_col[2] == 2

    curr_col = db.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'package' AND column_name = 'currency_id'"
        )
    ).fetchone()
    assert curr_col is not None, "currency_id column missing on package"

    # Get amenity type for package creation
    amenity_type = db.execute(text("SELECT id FROM amenity_type LIMIT 1")).scalar_one()

    # Create package with price and currency
    pkg_name = f"Test Package {unique}"
    create_payload = {
        "name": pkg_name,
        "amenity_type": str(amenity_type),
        "price": "3500.50",
        "currency_id": 1,
    }
    r = api.post(f"{V1}/packages", json=create_payload)
    assert r.status_code == 201, f"Failed to create package: {r.text}"
    created_pkg = r.json()
    pkg_id = created_pkg["id"]
    cleanup.add("package", pkg_id)

    # Verify fields on GET /packages
    r_list = api.get(f"{V1}/packages?page=1&page_size=50")
    assert r_list.status_code == 200
    pkgs = r_list.json()["items"]
    target = next((p for p in pkgs if p["id"] == pkg_id), None)
    assert target is not None
    assert Decimal(str(target["price"])) == Decimal("3500.50")
    assert target["currency_id"] == 1
    assert target["currency_code"] == "INR"
    assert target["currency_symbol"] == "₹"

    # Update package price
    r_update = api.patch(f"{V1}/packages/{pkg_id}", json={"price": "4200.00"})
    assert r_update.status_code == 200
    updated_pkg = r_update.json()
    assert Decimal(str(updated_pkg["price"])) == Decimal("4200.00")

    # Reject invalid currency_id on package
    r_bad_curr = api.patch(f"{V1}/packages/{pkg_id}", json={"currency_id": 888})
    assert r_bad_curr.status_code == 422


def test_invoice_currency_retrieval_and_preservation(api, db):
    """Invoices must retrieve currency information and preserve historical currency."""
    inv_row = db.execute(
        text("SELECT i.id, i.stay_id FROM invoice i JOIN stay s ON s.id = i.stay_id LIMIT 1")
    ).fetchone()
    if not inv_row:
        pytest.skip("No stays with invoices in database")

    stay_id = str(inv_row[1])
    r = api.get(f"{V1}/stays/{stay_id}")
    assert r.status_code == 200
    stay_data = r.json()
    assert len(stay_data["invoices"]) > 0

    inv = stay_data["invoices"][0]
    assert "currency_id" in inv
    assert inv["currency_id"] is not None
    assert "currency_code" in inv
    assert inv["currency_code"] in ["INR", "USD", "EUR"]
    assert "currency_symbol" in inv
    assert inv["currency_symbol"] is not None
    assert "total_amount" in inv


def test_historical_invoice_preserved_when_facility_currency_changes(api, db, cleanup):
    """Updating facility base currency must NOT alter historical invoice currency or amounts."""
    # Find an existing invoice and its stay
    inv_row = db.execute(
        text(
            "SELECT i.id, i.stay_id, i.currency_id, i.total_amount, i.facility_id "
            "FROM invoice i "
            "JOIN stay s ON s.id = i.stay_id "
            "LIMIT 1"
        )
    ).fetchone()
    if not inv_row:
        pytest.skip("No invoice exists to test historical preservation")

    inv_id, stay_id, original_inv_curr_id, original_total, fac_id = (
        str(inv_row[0]),
        str(inv_row[1]),
        inv_row[2],
        inv_row[3],
        str(inv_row[4]),
    )

    # Get facility original currency
    fac_orig_curr = db.execute(
        text("SELECT currency_id FROM facility WHERE id = :fid"), {"fid": fac_id}
    ).scalar_one()

    # Register restore in cleanup
    cleanup.sql(
        "UPDATE facility SET currency_id = :cid WHERE id = :fid",
        {"cid": fac_orig_curr, "fid": fac_id},
    )

    # Change facility currency to EUR (id = 3) via PATCH
    r_change_fac = api.patch(f"{V1}/facilities/{fac_id}", json={"currency_id": 3})
    assert r_change_fac.status_code == 200

    # Fetch stay and check the invoice
    r_stay = api.get(f"{V1}/stays/{stay_id}")
    assert r_stay.status_code == 200
    stay_data = r_stay.json()
    assert len(stay_data["invoices"]) > 0
    inv_after = next(i for i in stay_data["invoices"] if i["id"] == inv_id)

    # Historical invoice currency must remain unchanged (not reinterpreted to EUR)
    assert inv_after["currency_id"] == original_inv_curr_id
    assert Decimal(str(inv_after["total_amount"])) == Decimal(str(original_total))
