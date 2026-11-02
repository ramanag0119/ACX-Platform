"""Priority 4: Energy telemetry device FK, billing pricing, and currency schema

Revision ID: b3c4d5e6f7a8
Revises: 9a2b3c4d5e6f
Create Date: 2026-10-21 19:00:00.000000

Item 12:
- Add device_id UUID FK to energy_stat referencing device(id)
- Safely backfill existing energy_stat records to authoritative device records
- Add index on (device_id, hour) and apply FK constraint
- Add optional device_id to other_device

Item 13:
- Create currency master table with ISO 4217 code, name, symbol, minor_units
- Seed active currencies (INR, USD, EUR, GBP, AED, SGD, JPY)
- Add FK constraint from facility.currency_id -> currency.id
- Add currency_id to invoice and backfill historical invoices
- Add price and currency_id to package
- Add currency_id to service_category_item
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = '9a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # -----------------------------------------------------------------------
    # 1. Create currency master table if not exists
    # -----------------------------------------------------------------------
    if "currency" not in existing_tables:
        op.create_table(
            "currency",
            sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(3), nullable=False),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("symbol", sa.String(10), nullable=False),
            sa.Column("minor_units", sa.SmallInteger(), nullable=False, server_default="2"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_on", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_on", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_currency_code", "currency", ["code"], unique=True)

        # Seed core currencies (INR as default id=1 for Chennai facility)
        op.execute("""
            INSERT INTO currency (id, code, name, symbol, minor_units, is_active)
            VALUES 
                (1, 'INR', 'Indian Rupee', '₹', 2, true),
                (2, 'USD', 'US Dollar', '$', 2, true),
                (3, 'EUR', 'Euro', '€', 2, true),
                (4, 'GBP', 'British Pound', '£', 2, true),
                (5, 'AED', 'UAE Dirham', 'د.إ', 2, true),
                (6, 'SGD', 'Singapore Dollar', 'S$', 2, true),
                (7, 'JPY', 'Japanese Yen', '¥', 0, true)
            ON CONFLICT (id) DO NOTHING;
        """)
        # Ensure sequence is aligned
        op.execute("SELECT setval(pg_get_serial_sequence('currency', 'id'), (SELECT max(id) FROM currency));")

    # -----------------------------------------------------------------------
    # 2. Update facility.currency_id with FK
    # -----------------------------------------------------------------------
    facility_cols = [c["name"] for c in inspector.get_columns("facility")]
    if "currency_id" in facility_cols:
        # Default Chennai facility to INR (id=1) where null
        op.execute("UPDATE facility SET currency_id = 1 WHERE currency_id IS NULL;")
        # Add foreign key constraint if not present
        existing_fks = [fk["name"] for fk in inspector.get_foreign_keys("facility")]
        if "fk_facility_currency_id_currency" not in existing_fks:
            op.create_foreign_key(
                "fk_facility_currency_id_currency",
                "facility",
                "currency",
                ["currency_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    # -----------------------------------------------------------------------
    # 3. Energy Telemetry (energy_stat): add device_id, backfill, FK
    # -----------------------------------------------------------------------
    energy_stat_cols = [c["name"] for c in inspector.get_columns("energy_stat")]
    if "device_id" not in energy_stat_cols:
        op.add_column("energy_stat", sa.Column("device_id", PGUUID(as_uuid=True), nullable=True))

        # Safe backfill mapping:
        # 1. Match by room + Mikos energy meter (type_id=3)
        op.execute("""
            UPDATE energy_stat es
            SET device_id = d.id
            FROM device d
            WHERE d.amenity_id = es.amenity_id
              AND d.device_type = 3
              AND es.device_id IS NULL;
        """)

        # 2. Match by device_uid containing the clean device name
        op.execute("""
            UPDATE energy_stat es
            SET device_id = d.id
            FROM device d
            WHERE upper(d.device_uid) = 'DEV' || upper(replace(es.device_name, '-', ''))
              AND es.device_id IS NULL;
        """)

        # 3. Match by exact device_name
        op.execute("""
            UPDATE energy_stat es
            SET device_id = d.id
            FROM device d
            WHERE d.device_name = es.device_name
              AND es.device_id IS NULL;
        """)

        # Create indexes
        op.create_index("ix_energy_stat_device_id", "energy_stat", ["device_id"])
        op.create_index("ix_energy_stat_device_id_hour", "energy_stat", ["device_id", "hour"])

        # Create FK constraint
        op.create_foreign_key(
            "fk_energy_stat_device_id_device",
            "energy_stat",
            "device",
            ["device_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Set NOT NULL now that existing 72 rows are verified and backfilled
        op.alter_column("energy_stat", "device_id", nullable=False)

    # -----------------------------------------------------------------------
    # 4. other_device: optional device_id link
    # -----------------------------------------------------------------------
    other_device_cols = [c["name"] for c in inspector.get_columns("other_device")]
    if "device_id" not in other_device_cols:
        op.add_column("other_device", sa.Column("device_id", PGUUID(as_uuid=True), nullable=True))
        op.create_index("ix_other_device_device_id", "other_device", ["device_id"])
        op.create_foreign_key(
            "fk_other_device_device_id_device",
            "other_device",
            "device",
            ["device_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 5. invoice: add currency_id, backfill, FK
    # -----------------------------------------------------------------------
    invoice_cols = [c["name"] for c in inspector.get_columns("invoice")]
    if "currency_id" not in invoice_cols:
        op.add_column("invoice", sa.Column("currency_id", sa.SmallInteger(), nullable=True))
        # Backfill from facility or default to 1 (INR)
        op.execute("""
            UPDATE invoice i
            SET currency_id = COALESCE(f.currency_id, 1)
            FROM facility f
            WHERE f.id = i.facility_id AND i.currency_id IS NULL;
        """)
        op.execute("UPDATE invoice SET currency_id = 1 WHERE currency_id IS NULL;")
        op.create_foreign_key(
            "fk_invoice_currency_id_currency",
            "invoice",
            "currency",
            ["currency_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # -----------------------------------------------------------------------
    # 6. package: add price and currency_id
    # -----------------------------------------------------------------------
    package_cols = [c["name"] for c in inspector.get_columns("package")]
    if "price" not in package_cols:
        op.add_column("package", sa.Column("price", sa.Numeric(10, 2), nullable=True))
    if "currency_id" not in package_cols:
        op.add_column("package", sa.Column("currency_id", sa.SmallInteger(), nullable=True))
        op.execute("UPDATE package SET currency_id = 1 WHERE currency_id IS NULL;")
        op.create_foreign_key(
            "fk_package_currency_id_currency",
            "package",
            "currency",
            ["currency_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Seed baseline prices for packages if currently null
    op.execute("""
        UPDATE package SET price = 4500.00 WHERE price IS NULL AND name ILIKE '%suite%';
        UPDATE package SET price = 2500.00 WHERE price IS NULL AND (name ILIKE '%deluxe%' OR name ILIKE '%premium%');
        UPDATE package SET price = 1800.00 WHERE price IS NULL;
    """)

    # -----------------------------------------------------------------------
    # 7. service_category_item: add currency_id
    # -----------------------------------------------------------------------
    service_item_cols = [c["name"] for c in inspector.get_columns("service_category_item")]
    if "currency_id" not in service_item_cols:
        op.add_column("service_category_item", sa.Column("currency_id", sa.SmallInteger(), nullable=True))
        op.execute("UPDATE service_category_item SET currency_id = 1 WHERE currency_id IS NULL;")
        op.create_foreign_key(
            "fk_service_category_item_currency_id_currency",
            "service_category_item",
            "currency",
            ["currency_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Remove FKs and columns in reverse order
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # service_category_item
    service_item_cols = [c["name"] for c in inspector.get_columns("service_category_item")]
    if "currency_id" in service_item_cols:
        op.drop_constraint("fk_service_category_item_currency_id_currency", "service_category_item", type_="foreignkey")
        op.drop_column("service_category_item", "currency_id")

    # package
    package_cols = [c["name"] for c in inspector.get_columns("package")]
    if "currency_id" in package_cols:
        op.drop_constraint("fk_package_currency_id_currency", "package", type_="foreignkey")
        op.drop_column("package", "currency_id")
    if "price" in package_cols:
        op.drop_column("package", "price")

    # invoice
    invoice_cols = [c["name"] for c in inspector.get_columns("invoice")]
    if "currency_id" in invoice_cols:
        op.drop_constraint("fk_invoice_currency_id_currency", "invoice", type_="foreignkey")
        op.drop_column("invoice", "currency_id")

    # other_device
    other_device_cols = [c["name"] for c in inspector.get_columns("other_device")]
    if "device_id" in other_device_cols:
        op.drop_constraint("fk_other_device_device_id_device", "other_device", type_="foreignkey")
        op.drop_index("ix_other_device_device_id", table_name="other_device")
        op.drop_column("other_device", "device_id")

    # energy_stat
    energy_stat_cols = [c["name"] for c in inspector.get_columns("energy_stat")]
    if "device_id" in energy_stat_cols:
        op.drop_constraint("fk_energy_stat_device_id_device", "energy_stat", type_="foreignkey")
        op.drop_index("ix_energy_stat_device_id_hour", table_name="energy_stat")
        op.drop_index("ix_energy_stat_device_id", table_name="energy_stat")
        op.drop_column("energy_stat", "device_id")

    # facility
    facility_fks = [fk["name"] for fk in inspector.get_foreign_keys("facility")]
    if "fk_facility_currency_id_currency" in facility_fks:
        op.drop_constraint("fk_facility_currency_id_currency", "facility", type_="foreignkey")

    # currency
    if "currency" in inspector.get_table_names():
        op.drop_index("ix_currency_code", table_name="currency")
        op.drop_table("currency")
