"""Occupancy: room_status_condition_applicability + amenity_condition flags (MySQL)

Revision ID: c7a1b2d3e4f5
Revises: a3f1c8e2d904
Create Date: 2026-11-18 02:05:00.000000

WHY THIS EXISTS INSTEAD OF 8f1e3c5a7b92
---------------------------------------
`/occupancy` and `/occupancy/summary` return 503 in production:

    Table 'inspironics_app.room_status_condition_applicability' doesn't exist

The table is defined in revision 8f1e3c5a7b92, which sits on the OTHER Alembic
branch (7c4e2b9a1d53 -> 8f1e3c5a7b92 -> 9a2b3c4d5e6f -> b3c4d5e6f7a8). Reaching
it by merging the heads would also apply the Priority-4 revision, creating
`currency`, `energy_stat.device_id`, `other_device.device_id`,
`invoice.currency_id`, `package.price`, `package.currency_id`,
`service_category_item.currency_id` and `role.notification_preferences` --
seven objects that were NOT approved.

So this revision re-expresses ONLY the occupancy half of 8f1e3c5a7b92, on top
of the current head. The two heads are deliberately left unmerged; resolving
them stays a separate, separately-approved change.

The business rules and seed values are copied VERBATIM from 8f1e3c5a7b92 --
not re-derived. They decide which room conditions block check-in and which
block readiness, so inventing them would silently change hotel operations.

POSTGRESQL -> MYSQL 8.4 PORT
----------------------------
    ON CONFLICT (...) DO UPDATE SET x = EXCLUDED.x
        -> INSERT ... AS new ON DUPLICATE KEY UPDATE x = new.x
           (`VALUES(x)` is deprecated since 8.0.20; the row alias is the
           supported form on 8.4)
    server_default="true" / "false" on Boolean
        -> sa.text("1") / sa.text("0"); MySQL stores Boolean as TINYINT(1) and
           STRICT_TRANS_TABLES rejects the string 'true' as a default
    sa.DateTime(timezone=True), server_default=sa.func.now()
        -> mysql.DATETIME(fsp=6), server_default CURRENT_TIMESTAMP(6), matching
           every other table in this schema (see app/db/types.py NOW)
    updated_on = now()  in the upsert clause
        -> CURRENT_TIMESTAMP(6)
    DROP TABLE ... CASCADE
        -> DROP TABLE (MySQL has no CASCADE on DROP TABLE)

DATA SAFETY
-----------
* `amenity_condition` ids 1-5 already exist with exactly the names used here,
  so the upsert only fills the four new columns; no existing name is rewritten.
* ids 6 and 7 ('Guest Assistance Required', 'Device Offline') are NEW lookup
  rows. They are required: the applicability seed references condition_id 6
  and 7, and the FK would fail without them.
* `amenity_status` ids 0-3 (Available / Occupied / Unavailable / Allotted) all
  exist, satisfying the amenity_status_id FK.
* Nothing is deleted or updated outside those four new columns.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "c7a1b2d3e4f5"
down_revision = "a3f1c8e2d904"
branch_labels = None
depends_on = None


#: Matches the fsp(6) DATETIME default used by every other table here.
NOW6 = sa.text("CURRENT_TIMESTAMP(6)")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ------------------------------------------------------------------
    # 1. amenity_condition: four policy columns
    # ------------------------------------------------------------------
    cond_cols = {c["name"] for c in inspector.get_columns("amenity_condition")}

    if "display_name" not in cond_cols:
        op.add_column(
            "amenity_condition",
            sa.Column("display_name", sa.String(100), nullable=True),
        )
    for flag in ("applicable_to_occupied", "applicable_to_vacant", "is_active"):
        if flag not in cond_cols:
            op.add_column(
                "amenity_condition",
                sa.Column(
                    flag, sa.Boolean(), server_default=sa.text("1"), nullable=False
                ),
            )

    # Seed / backfill the master data. ids 1-5 exist already (names identical),
    # so those rows only gain the new flags; 6 and 7 are inserted.
    op.execute(
        sa.text(
            """
            INSERT INTO amenity_condition
                (id, name, display_name, applicable_to_occupied,
                 applicable_to_vacant, is_active)
            VALUES
                (1, 'Dirty',                     'Need Maintenance',          1, 1, 1),
                (2, 'Low battery',               'Low Battery',               1, 1, 1),
                (3, 'Under maintenance',         'Under Maintenance',         0, 1, 1),
                (4, 'Sanitation',                'Sanitation Required',       1, 1, 1),
                (5, 'Ready for occupant',        'Ready to Occupy',           0, 1, 1),
                (6, 'Guest Assistance Required', 'Guest Assistance Required', 1, 0, 1),
                (7, 'Device Offline',            'Device Offline',            1, 1, 1)
            AS new
            ON DUPLICATE KEY UPDATE
                display_name           = new.display_name,
                applicable_to_occupied = new.applicable_to_occupied,
                applicable_to_vacant   = new.applicable_to_vacant,
                is_active              = new.is_active
            """
        )
    )

    # ------------------------------------------------------------------
    # 2. room_status_condition_applicability
    # ------------------------------------------------------------------
    if "room_status_condition_applicability" not in inspector.get_table_names():
        op.create_table(
            "room_status_condition_applicability",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_status", sa.String(50), nullable=False),
            sa.Column(
                "amenity_status_id",
                sa.SmallInteger(),
                sa.ForeignKey("amenity_status.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "condition_id",
                sa.SmallInteger(),
                sa.ForeignKey("amenity_condition.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "is_applicable", sa.Boolean(), server_default=sa.text("1"), nullable=False
            ),
            sa.Column(
                "is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False
            ),
            sa.Column(
                "blocks_checkin", sa.Boolean(), server_default=sa.text("0"), nullable=False
            ),
            sa.Column(
                "blocks_readiness", sa.Boolean(), server_default=sa.text("0"), nullable=False
            ),
            sa.Column(
                "created_on", mysql.DATETIME(fsp=6), server_default=NOW6, nullable=False
            ),
            sa.Column(
                "updated_on", mysql.DATETIME(fsp=6), server_default=NOW6, nullable=False
            ),
            sa.UniqueConstraint(
                "room_status", "condition_id", name="uq_room_status_condition"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_0900_ai_ci",
        )

    # The 42-row seed below is made idempotent by ON DUPLICATE KEY UPDATE, which
    # needs `uq_room_status_condition` to exist to have anything to collide on.
    # The create_table above is skipped when the table is already present, so a
    # half-built table left by an interrupted run would reach the seed with no
    # unique key -- and INSERT ... ON DUPLICATE KEY would then append 42 fresh
    # rows on EVERY run instead of updating in place. Silent duplication in a
    # policy table is worse than a failed migration: `_has_blocking_condition`
    # would still return the right answer, so nobody would notice until the
    # duplicates were counted. Refuse instead.
    uq_names = {
        uc["name"] for uc in sa.inspect(conn).get_unique_constraints(
            "room_status_condition_applicability"
        )
    }
    # MySQL reports a UNIQUE constraint as an index, so check both reflections.
    uq_names |= {
        ix["name"]
        for ix in sa.inspect(conn).get_indexes("room_status_condition_applicability")
        if ix.get("unique")
    }
    if "uq_room_status_condition" not in uq_names:
        raise RuntimeError(
            "room_status_condition_applicability exists but is missing the "
            "unique key uq_room_status_condition(room_status, condition_id). "
            "The 42-row policy seed is upsert-based and would insert duplicates "
            "instead of updating. Inspect the table and either add the key or "
            "drop the table so this revision can recreate it."
        )

    # Policy rows, verbatim from 8f1e3c5a7b92.
    op.execute(
        sa.text(
            """
            INSERT INTO room_status_condition_applicability
                (room_status, amenity_status_id, condition_id,
                 is_applicable, is_active, blocks_checkin, blocks_readiness)
            VALUES
                ('Ready to Occupy', 0, 1, 1, 1, 1, 1),
                ('Ready to Occupy', 0, 2, 1, 1, 0, 0),
                ('Ready to Occupy', 0, 3, 1, 1, 1, 1),
                ('Ready to Occupy', 0, 4, 1, 1, 1, 1),
                ('Ready to Occupy', 0, 5, 1, 1, 0, 0),
                ('Ready to Occupy', 0, 6, 0, 1, 0, 0),
                ('Ready to Occupy', 0, 7, 1, 1, 0, 0),

                ('Available', 0, 1, 1, 1, 1, 1),
                ('Available', 0, 2, 1, 1, 0, 0),
                ('Available', 0, 3, 1, 1, 1, 1),
                ('Available', 0, 4, 1, 1, 1, 1),
                ('Available', 0, 5, 1, 1, 0, 0),
                ('Available', 0, 6, 0, 1, 0, 0),
                ('Available', 0, 7, 1, 1, 0, 0),

                ('Allocated', 3, 1, 1, 1, 1, 1),
                ('Allocated', 3, 2, 1, 1, 0, 0),
                ('Allocated', 3, 3, 1, 1, 1, 1),
                ('Allocated', 3, 4, 1, 1, 1, 1),
                ('Allocated', 3, 5, 1, 1, 0, 0),
                ('Allocated', 3, 6, 0, 1, 0, 0),
                ('Allocated', 3, 7, 1, 1, 0, 0),

                ('Allotted', 3, 1, 1, 1, 1, 1),
                ('Allotted', 3, 2, 1, 1, 0, 0),
                ('Allotted', 3, 3, 1, 1, 1, 1),
                ('Allotted', 3, 4, 1, 1, 1, 1),
                ('Allotted', 3, 5, 1, 1, 0, 0),
                ('Allotted', 3, 6, 0, 1, 0, 0),
                ('Allotted', 3, 7, 1, 1, 0, 0),

                ('Occupied', 1, 1, 1, 1, 0, 0),
                ('Occupied', 1, 2, 1, 1, 0, 0),
                ('Occupied', 1, 3, 0, 1, 0, 0),
                ('Occupied', 1, 4, 1, 1, 0, 0),
                ('Occupied', 1, 5, 0, 1, 0, 0),
                ('Occupied', 1, 6, 1, 1, 0, 0),
                ('Occupied', 1, 7, 1, 1, 0, 0),

                ('Unavailable', 2, 1, 1, 1, 1, 1),
                ('Unavailable', 2, 2, 1, 1, 0, 0),
                ('Unavailable', 2, 3, 1, 1, 1, 1),
                ('Unavailable', 2, 4, 1, 1, 1, 1),
                ('Unavailable', 2, 5, 0, 1, 0, 0),
                ('Unavailable', 2, 6, 0, 1, 0, 0),
                ('Unavailable', 2, 7, 1, 1, 0, 0)
            AS new
            ON DUPLICATE KEY UPDATE
                amenity_status_id = new.amenity_status_id,
                is_applicable     = new.is_applicable,
                is_active         = new.is_active,
                blocks_checkin    = new.blocks_checkin,
                blocks_readiness  = new.blocks_readiness,
                updated_on        = CURRENT_TIMESTAMP(6)
            """
        )
    )


def downgrade() -> None:
    """Drop the table and the four columns.

    The two `amenity_condition` rows this revision inserts (ids 6 and 7) are
    intentionally LEFT IN PLACE. Once operations has used them they may be
    referenced by `amenity_condition_status`, and deleting a lookup row that
    live data points at would cascade into real records. An unused lookup row
    is harmless; a deleted one is not.

    Every step is guarded the way `upgrade()` guards its own, so a downgrade run
    against a partially-upgraded schema completes instead of aborting half-way
    and leaving the revision marked as still applied.
    """
    conn = op.get_bind()

    if "room_status_condition_applicability" in sa.inspect(conn).get_table_names():
        op.drop_table("room_status_condition_applicability")

    cond_cols = {c["name"] for c in sa.inspect(conn).get_columns("amenity_condition")}
    for flag in ("is_active", "applicable_to_vacant", "applicable_to_occupied", "display_name"):
        if flag in cond_cols:
            op.drop_column("amenity_condition", flag)
