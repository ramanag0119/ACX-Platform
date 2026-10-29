"""create room_status_condition_applicability table

Revision ID: 8f1e3c5a7b92
Revises: 7c4e2b9a1d53
Create Date: 2026-10-20 12:35:00.000000

Status-specific condition applicability configuration for Inspironics Ikanos HMS.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1e3c5a7b92'
down_revision = '7c4e2b9a1d53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Add columns to amenity_condition if not present
    inspector = sa.inspect(conn)
    cond_cols = [c["name"] for c in inspector.get_columns("amenity_condition")]

    if "display_name" not in cond_cols:
        op.add_column("amenity_condition", sa.Column("display_name", sa.String(100), nullable=True))
    if "applicable_to_occupied" not in cond_cols:
        op.add_column("amenity_condition", sa.Column("applicable_to_occupied", sa.Boolean(), server_default="true", nullable=False))
    if "applicable_to_vacant" not in cond_cols:
        op.add_column("amenity_condition", sa.Column("applicable_to_vacant", sa.Boolean(), server_default="true", nullable=False))
    if "is_active" not in cond_cols:
        op.add_column("amenity_condition", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))

    # Seed amenity_condition master data
    op.execute(sa.text("""
        INSERT INTO amenity_condition (id, name, display_name, applicable_to_occupied, applicable_to_vacant, is_active)
        VALUES 
            (1, 'Dirty', 'Need Maintenance', true, true, true),
            (2, 'Low battery', 'Low Battery', true, true, true),
            (3, 'Under maintenance', 'Under Maintenance', false, true, true),
            (4, 'Sanitation', 'Sanitation Required', true, true, true),
            (5, 'Ready for occupant', 'Ready to Occupy', false, true, true),
            (6, 'Guest Assistance Required', 'Guest Assistance Required', true, false, true),
            (7, 'Device Offline', 'Device Offline', true, true, true)
        ON CONFLICT (id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            applicable_to_occupied = EXCLUDED.applicable_to_occupied,
            applicable_to_vacant = EXCLUDED.applicable_to_vacant,
            is_active = EXCLUDED.is_active;
    """))

    # 2. Create room_status_condition_applicability table if not present
    tables = inspector.get_table_names()
    if "room_status_condition_applicability" not in tables:
        op.create_table(
            "room_status_condition_applicability",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_status", sa.String(50), nullable=False),
            sa.Column("amenity_status_id", sa.SmallInteger(), sa.ForeignKey("amenity_status.id", ondelete="CASCADE"), nullable=True),
            sa.Column("condition_id", sa.SmallInteger(), sa.ForeignKey("amenity_condition.id", ondelete="CASCADE"), nullable=False),
            sa.Column("is_applicable", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("blocks_checkin", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("blocks_readiness", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_on", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_on", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("room_status", "condition_id", name="uq_room_status_condition"),
        )

    # Seed amenity_status if not present (required by foreign key)
    op.execute(sa.text("""
        INSERT INTO amenity_status (id, amenity_status_name)
        VALUES 
            (0, 'Available'),
            (1, 'Occupied'),
            (2, 'Unavailable'),
            (3, 'Allotted')
        ON CONFLICT (id) DO UPDATE SET
            amenity_status_name = EXCLUDED.amenity_status_name;
    """))

    # Seed room_status_condition_applicability
    op.execute(sa.text("""
        INSERT INTO room_status_condition_applicability 
            (room_status, amenity_status_id, condition_id, is_applicable, is_active, blocks_checkin, blocks_readiness)
        VALUES
            -- Ready to Occupy
            ('Ready to Occupy', 0, 1, true, true, true, true),
            ('Ready to Occupy', 0, 2, true, true, false, false),
            ('Ready to Occupy', 0, 3, true, true, true, true),
            ('Ready to Occupy', 0, 4, true, true, true, true),
            ('Ready to Occupy', 0, 5, true, true, false, false),
            ('Ready to Occupy', 0, 6, false, true, false, false),
            ('Ready to Occupy', 0, 7, true, true, false, false),

            -- Available
            ('Available', 0, 1, true, true, true, true),
            ('Available', 0, 2, true, true, false, false),
            ('Available', 0, 3, true, true, true, true),
            ('Available', 0, 4, true, true, true, true),
            ('Available', 0, 5, true, true, false, false),
            ('Available', 0, 6, false, true, false, false),
            ('Available', 0, 7, true, true, false, false),

            -- Allocated / Allotted
            ('Allocated', 3, 1, true, true, true, true),
            ('Allocated', 3, 2, true, true, false, false),
            ('Allocated', 3, 3, true, true, true, true),
            ('Allocated', 3, 4, true, true, true, true),
            ('Allocated', 3, 5, true, true, false, false),
            ('Allocated', 3, 6, false, true, false, false),
            ('Allocated', 3, 7, true, true, false, false),

            ('Allotted', 3, 1, true, true, true, true),
            ('Allotted', 3, 2, true, true, false, false),
            ('Allotted', 3, 3, true, true, true, true),
            ('Allotted', 3, 4, true, true, true, true),
            ('Allotted', 3, 5, true, true, false, false),
            ('Allotted', 3, 6, false, true, false, false),
            ('Allotted', 3, 7, true, true, false, false),

            -- Occupied
            ('Occupied', 1, 1, true, true, false, false),
            ('Occupied', 1, 2, true, true, false, false),
            ('Occupied', 1, 3, false, true, false, false),
            ('Occupied', 1, 4, true, true, false, false),
            ('Occupied', 1, 5, false, true, false, false),
            ('Occupied', 1, 6, true, true, false, false),
            ('Occupied', 1, 7, true, true, false, false),

            -- Unavailable
            ('Unavailable', 2, 1, true, true, true, true),
            ('Unavailable', 2, 2, true, true, false, false),
            ('Unavailable', 2, 3, true, true, true, true),
            ('Unavailable', 2, 4, true, true, true, true),
            ('Unavailable', 2, 5, false, true, false, false),
            ('Unavailable', 2, 6, false, true, false, false),
            ('Unavailable', 2, 7, true, true, false, false)
        ON CONFLICT (room_status, condition_id) DO UPDATE SET
            amenity_status_id = EXCLUDED.amenity_status_id,
            is_applicable = EXCLUDED.is_applicable,
            is_active = EXCLUDED.is_active,
            blocks_checkin = EXCLUDED.blocks_checkin,
            blocks_readiness = EXCLUDED.blocks_readiness,
            updated_on = now();
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS room_status_condition_applicability CASCADE"))
