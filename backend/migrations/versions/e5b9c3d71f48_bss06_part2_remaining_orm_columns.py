"""BSS-06 part 2: the four remaining ORM columns (MySQL 8.4 port)

Revision ID: e5b9c3d71f48
Revises: d8e4f1a6b207
Create Date: 2026-11-18 00:00:00.000000

WHY THIS EXISTS
---------------
After d8e4f1a6b207 the ORM is still ahead of MySQL by exactly four columns.
All four are declared in `app/models` and none exists in the database, so every
query that loads the owning entity fails with `Unknown column`. Measured on the
full suite from a clean baseline -- 159 failed / 1,193 passed -- the four
account for essentially all of it:

    energy_stat.device_id              116 failure hits
    role.notification_preferences       79
    package.price                       49
    other_device.device_id              23

(Buckets overlap; one test can hit several.)

They live only on the abandoned PostgreSQL branch -- items 12 and 13 of
b3c4d5e6f7a8, plus 9a2b3c4d5e6f -- which cannot run on MySQL. This closes the
delta to ZERO without touching that branch.

NOTHING HERE IS INVENTED
------------------------
Every value written by this revision is derived from data already in the
database, or is left NULL.

* `energy_stat.device_id` is back-filled from the Mikos energy meter in the
  SAME ROOM: `device.amenity_id = energy_stat.amenity_id AND
  device.device_type = 3`. `device_type` 3 is 'Mikos' in the `device_type`
  lookup -- verified, not assumed. On the reference data this matches 72 of
  72 rows. b3c4d5e6f7a8's two fallback strategies (device_uid pattern, exact
  device_name) are NOT ported: they are unnecessary here, and a partial match
  is something to report rather than paper over. The NOT NULL constraint is
  applied only after coverage is proven complete -- see `_assert_full_coverage`.

* `package.price` is added and LEFT ENTIRELY NULL. b3c4d5e6f7a8 back-fills it
  with 4500 / 2500 / 1800 by room name. Those are room tariffs -- a pricing
  decision, not a migration -- and `app/models/amenity.py` says so directly:

      `price` is NOT a column: `packages` has no price in the dump. [...]
      Room tariff has no source -> blueprint 11.3 / OPEN DECISION #10.

  `PackageRead.price` is `Decimal | None`, so NULL is a valid response.

* `other_device.device_id` and `role.notification_preferences` carry no
  business data: one is an optional link no service reads yet, the other an
  empty JSON list.

THE TWO HEADS REMAIN UNMERGED. This extends the MySQL head; b3c4d5e6f7a8 is
untouched and stays a separate head.

POSTGRESQL -> MYSQL 8.4 PORT
----------------------------
    postgresql.UUID / PGUUID    -> CHAR(36), matching GUID() in app/db/types.py
    JSONB                       -> JSON (app.db.types.JSONB already resolves
                                   to MySQL JSON -- same as app_user.metadata)
    UPDATE es SET ... FROM d    -> UPDATE ... JOIN ... SET
    name ILIKE '%suite%'        -> dropped with the price back-fill
    server_default="[]" on JSON -> MySQL 8 forbids a literal DEFAULT on JSON;
                                   the column is nullable and the application
                                   defaults it to [], so no server default is
                                   emitted. This is a REAL divergence from the
                                   model's `server_default="[]"` and is
                                   deliberate -- see the note in upgrade().
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5b9c3d71f48"
down_revision = "d8e4f1a6b207"
branch_labels = None
depends_on = None


#: `device_type.id` of the Mikos energy meter. Verified against the lookup
#: table rather than assumed: 1 Intellihub, 2 AirQ, 3 Mikos, 4 Kleio.
MIKOS_DEVICE_TYPE = 3


def _cols(inspector, table: str) -> set[str]:
    return {c["name"] for c in inspector.get_columns(table)}


def _indexes(inspector, table: str) -> set[str]:
    return {i["name"] for i in inspector.get_indexes(table)}


def _fks(inspector, table: str) -> set[str]:
    return {f["name"] for f in inspector.get_foreign_keys(table)}


def _assert_full_coverage(conn) -> None:
    """Refuse to apply NOT NULL while any row is still unmapped.

    The alternative is an ALTER that fails half-way through the revision, or
    -- worse -- a silent decision to invent a device for the unmatched rows.
    Reporting the gap is the only honest outcome.
    """
    missing = conn.execute(
        sa.text("SELECT COUNT(*) FROM energy_stat WHERE device_id IS NULL")
    ).scalar()
    if missing:
        total = conn.execute(sa.text("SELECT COUNT(*) FROM energy_stat")).scalar()
        raise RuntimeError(
            f"energy_stat.device_id could not be derived for {missing} of {total} "
            "rows: no Mikos device (device_type = 3) is registered in the same "
            "room. NOT NULL is NOT being applied.\n"
            "Inspect with:\n"
            "  SELECT es.amenity_id, es.device_name, COUNT(*)\n"
            "  FROM energy_stat es WHERE es.device_id IS NULL\n"
            "  GROUP BY es.amenity_id, es.device_name;\n"
            "Resolve the missing device registrations, then re-run. Do not "
            "substitute an arbitrary device -- the mapping drives energy "
            "billing."
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ------------------------------------------------------------------
    # 1. energy_stat.device_id -- derived, then constrained
    # ------------------------------------------------------------------
    if "device_id" not in _cols(inspector, "energy_stat"):
        # Added NULLABLE first so the back-fill has somewhere to land.
        op.add_column("energy_stat", sa.Column("device_id", sa.CHAR(36), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE energy_stat es
              JOIN device d
                ON d.amenity_id = es.amenity_id
               AND d.device_type = :mikos
               SET es.device_id = d.id
             WHERE es.device_id IS NULL
            """
        ).bindparams(mikos=MIKOS_DEVICE_TYPE)
    )

    _assert_full_coverage(conn)

    inspector = sa.inspect(conn)
    if "ix_energy_stat_device_id" not in _indexes(inspector, "energy_stat"):
        op.create_index("ix_energy_stat_device_id", "energy_stat", ["device_id"])
    if "ix_energy_stat_device_id_hour" not in _indexes(inspector, "energy_stat"):
        op.create_index(
            "ix_energy_stat_device_id_hour", "energy_stat", ["device_id", "hour"]
        )
    if "fk_energy_stat_device_id_device" not in _fks(inspector, "energy_stat"):
        op.create_foreign_key(
            "fk_energy_stat_device_id_device", "energy_stat", "device",
            ["device_id"], ["id"], ondelete="CASCADE",
        )

    # Only now, with every row proven mapped, does the model's NOT NULL apply.
    op.alter_column(
        "energy_stat", "device_id",
        existing_type=sa.CHAR(36), nullable=False,
    )

    # ------------------------------------------------------------------
    # 2. other_device.device_id -- optional link, no back-fill
    # ------------------------------------------------------------------
    inspector = sa.inspect(conn)
    if "device_id" not in _cols(inspector, "other_device"):
        op.add_column("other_device", sa.Column("device_id", sa.CHAR(36), nullable=True))
        op.create_index("ix_other_device_device_id", "other_device", ["device_id"])
        op.create_foreign_key(
            "fk_other_device_device_id_device", "other_device", "device",
            ["device_id"], ["id"], ondelete="SET NULL",
        )

    # ------------------------------------------------------------------
    # 3. role.notification_preferences
    # ------------------------------------------------------------------
    # The model declares server_default="[]". MySQL 8 rejects a literal
    # DEFAULT on a JSON column (it would need an expression default), so none
    # is emitted here. The column is nullable and every reader defaults it --
    # `RoleRead.notification_preferences` is
    # `Field(default_factory=list)` -- so a NULL reads as [] either way.
    inspector = sa.inspect(conn)
    if "notification_preferences" not in _cols(inspector, "role"):
        op.add_column(
            "role", sa.Column("notification_preferences", sa.JSON(), nullable=True)
        )

    # ------------------------------------------------------------------
    # 4. package.price -- COLUMN ONLY. No values. See the module docstring.
    # ------------------------------------------------------------------
    inspector = sa.inspect(conn)
    if "price" not in _cols(inspector, "package"):
        op.add_column("package", sa.Column("price", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Reverse all four, guarded so a partial state still completes.

    `energy_stat.device_id` is dropped outright. Its values are derived, not
    authored, so nothing unrecoverable is lost: a re-run of upgrade() rebuilds
    them from the same relationship.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "price" in _cols(inspector, "package"):
        op.drop_column("package", "price")

    if "notification_preferences" in _cols(inspector, "role"):
        op.drop_column("role", "notification_preferences")

    inspector = sa.inspect(conn)
    if "device_id" in _cols(inspector, "other_device"):
        if "fk_other_device_device_id_device" in _fks(inspector, "other_device"):
            op.drop_constraint(
                "fk_other_device_device_id_device", "other_device", type_="foreignkey"
            )
        if "ix_other_device_device_id" in _indexes(inspector, "other_device"):
            op.drop_index("ix_other_device_device_id", table_name="other_device")
        op.drop_column("other_device", "device_id")

    inspector = sa.inspect(conn)
    if "device_id" in _cols(inspector, "energy_stat"):
        if "fk_energy_stat_device_id_device" in _fks(inspector, "energy_stat"):
            op.drop_constraint(
                "fk_energy_stat_device_id_device", "energy_stat", type_="foreignkey"
            )
        for ix in ("ix_energy_stat_device_id_hour", "ix_energy_stat_device_id"):
            if ix in _indexes(inspector, "energy_stat"):
                op.drop_index(ix, table_name="energy_stat")
        op.drop_column("energy_stat", "device_id")
