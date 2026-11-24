"""BSS-06 part 1: `currency` master table + its FK columns (MySQL 8.4 port)

Revision ID: d8e4f1a6b207
Revises: c7a1b2d3e4f5
Create Date: 2026-11-18 00:00:00.000000

WHY THIS EXISTS
---------------
`currency` is declared by `app/models/facility.py::Currency` and joined by four
service modules, but no MySQL migration ever created it. It exists only in
`b3c4d5e6f7a8`, which sits on the abandoned PostgreSQL branch and cannot run on
MySQL (`ON CONFLICT`, `pg_get_serial_sequence`, `UPDATE ... FROM`, `PGUUID`).

The absence blocks three separate things, all with the same error
(`1146 Table 'currency' doesn't exist`):

  * `app/services/stay.py:438,476` -- every StayDetail response joins Currency,
    so EVERY stay write endpoint fails. This is what blocks BSS-04.
  * `app/services/service.py:188`  -- the service catalogue price join.
  * `seeds/run_seed.py` step 1     -- the seed runner cannot run at all.

SCOPE -- CURRENCY ONLY
----------------------
Measured against the live schema, the ORM is ahead by one table and seven
columns. This revision closes the FOUR that are currency, and nothing else:

    currency                              (table)   <- created here
    invoice.currency_id                             <- added here
    package.currency_id                             <- added here
    service_category_item.currency_id               <- added here
    facility.currency_id                            <- column already exists;
                                                       only the FK is added

DELIBERATELY NOT INCLUDED -- these are not currency objects and are not
approved:

    energy_stat.device_id          (b3c4 item 12)
    other_device.device_id         (b3c4 item 12)
    package.price                  (b3c4 item 13, but a PRICE not a currency)
    role.notification_preferences  (revision 9a2b3c4d5e6f)

`package.price` is the near miss. b3c4 adds it alongside `package.currency_id`
AND back-fills it with invented amounts (4500 / 2500 / 1800 by room name).
Those numbers are not derived from anything in the schema -- they are a pricing
decision wearing a migration's clothes. Porting them would silently set hotel
room rates. `app/services/catalog.py:323` still needs the column, so it stays a
reported gap, not a guess made here.

THE TWO HEADS ARE STILL NOT MERGED. This extends c7a1b2d3e4f5 (the occupancy
head). `b3c4d5e6f7a8` remains a separate head and is untouched.

POSTGRESQL -> MYSQL 8.4 PORT
----------------------------
    ON CONFLICT (id) DO NOTHING
        -> INSERT ... AS new ON DUPLICATE KEY UPDATE id = currency.id
           (a deliberate no-op: the row is left exactly as found)
    setval(pg_get_serial_sequence('currency','id'), ...)
        -> dropped entirely. `Currency` inherits SmallIntLookupPk, which is
           `autoincrement=False` -- these ids are seeded, never generated, like
           every other lookup table here. There is no sequence to align.
    UPDATE invoice i SET ... FROM facility f WHERE f.id = i.facility_id
        -> UPDATE invoice i JOIN facility f ON f.id = i.facility_id SET ...
    sa.DateTime(timezone=True), server_default=sa.text("now()")
        -> mysql.DATETIME(fsp=6), server_default CURRENT_TIMESTAMP(6)
    sa.Boolean, server_default="true"
        -> server_default=sa.text("1"); MySQL stores Boolean as TINYINT(1) and
           STRICT_TRANS_TABLES rejects the string 'true' as a default

DATA SAFETY
-----------
* The seven seeded currencies are copied VERBATIM from b3c4d5e6f7a8 -- ISO 4217
  code, name, symbol and minor_units. Nothing is invented. JPY keeps
  minor_units = 0, which is correct and is the one value a careless re-typing
  would get wrong.
* Every added column is NULLABLE and back-filled to 1 (INR), matching b3c4.
  No existing row is deleted and no existing value is overwritten -- the
  back-fills all carry `WHERE currency_id IS NULL`.
* All four FKs are ON DELETE RESTRICT, so a currency that is in use cannot be
  removed out from under live billing rows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = "d8e4f1a6b207"
down_revision = "c7a1b2d3e4f5"
branch_labels = None
depends_on = None


#: Matches the fsp(6) DATETIME default used by every other table here.
NOW6 = sa.text("CURRENT_TIMESTAMP(6)")

#: id of the default currency the back-fills use. 1 = INR, per b3c4d5e6f7a8.
DEFAULT_CURRENCY_ID = 1

#: (table, fk_name) for the three columns this revision adds, plus facility
#: whose column already exists and only needs the constraint.
_FK_TARGETS = (
    ("invoice", "fk_invoice_currency_id_currency"),
    ("package", "fk_package_currency_id_currency"),
    ("service_category_item", "fk_service_category_item_currency_id_currency"),
    ("facility", "fk_facility_currency_id_currency"),
)


def _has_fk(inspector, table: str, name: str) -> bool:
    return name in {fk["name"] for fk in inspector.get_foreign_keys(table)}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ------------------------------------------------------------------
    # 1. currency master table
    # ------------------------------------------------------------------
    if "currency" not in inspector.get_table_names():
        op.create_table(
            "currency",
            # autoincrement=False to match Currency(SmallIntLookupPk): the
            # IKANOS integer id IS the key and is seeded.
            sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=False),
            sa.Column("code", sa.String(3), nullable=False),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("symbol", sa.String(10), nullable=False),
            sa.Column(
                "minor_units", sa.SmallInteger(), nullable=False, server_default="2"
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
            ),
            sa.Column(
                "created_on", mysql.DATETIME(fsp=6), server_default=NOW6, nullable=False
            ),
            sa.Column(
                "updated_on", mysql.DATETIME(fsp=6), server_default=NOW6, nullable=False
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_0900_ai_ci",
        )
        # Currency.code is declared unique=True, index=True on the model.
        op.create_index("ix_currency_code", "currency", ["code"], unique=True)

    # Seed, verbatim from b3c4d5e6f7a8. The ON DUPLICATE clause is a no-op, so
    # re-running never rewrites a row an operator may have corrected.
    op.execute(
        sa.text(
            """
            INSERT INTO currency (id, code, name, symbol, minor_units, is_active)
            VALUES
                (1, 'INR', 'Indian Rupee',       '₹',   2, 1),
                (2, 'USD', 'US Dollar',          '$',   2, 1),
                (3, 'EUR', 'Euro',               '€',   2, 1),
                (4, 'GBP', 'British Pound',      '£',   2, 1),
                (5, 'AED', 'UAE Dirham',         'د.إ', 2, 1),
                (6, 'SGD', 'Singapore Dollar',   'S$',  2, 1),
                (7, 'JPY', 'Japanese Yen',       '¥',   0, 1)
            AS new
            ON DUPLICATE KEY UPDATE id = currency.id
            """
        )
    )

    # ------------------------------------------------------------------
    # 2. the three missing currency_id columns
    # ------------------------------------------------------------------
    for table in ("invoice", "package", "service_category_item"):
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "currency_id" not in cols:
            op.add_column(
                table, sa.Column("currency_id", sa.SmallInteger(), nullable=True)
            )

    # ------------------------------------------------------------------
    # 3. back-fill. Every statement is NULL-guarded, so an existing value is
    #    never overwritten and a re-run is a no-op.
    # ------------------------------------------------------------------
    # facility first: invoice inherits from it.
    op.execute(
        sa.text(
            f"UPDATE facility SET currency_id = {DEFAULT_CURRENCY_ID} "
            "WHERE currency_id IS NULL"
        )
    )
    # invoice takes its facility's currency; anything unmatched falls back.
    op.execute(
        sa.text(
            """
            UPDATE invoice i
              JOIN facility f ON f.id = i.facility_id
               SET i.currency_id = COALESCE(f.currency_id, :default_id)
             WHERE i.currency_id IS NULL
            """
        ).bindparams(default_id=DEFAULT_CURRENCY_ID)
    )
    for table in ("invoice", "package", "service_category_item"):
        op.execute(
            sa.text(
                f"UPDATE {table} SET currency_id = {DEFAULT_CURRENCY_ID} "
                "WHERE currency_id IS NULL"
            )
        )

    # ------------------------------------------------------------------
    # 4. foreign keys. RESTRICT: a currency in use cannot be deleted.
    # ------------------------------------------------------------------
    inspector = sa.inspect(conn)       # re-reflect; columns changed above
    for table, fk_name in _FK_TARGETS:
        if not _has_fk(inspector, table, fk_name):
            op.create_foreign_key(
                fk_name, table, "currency", ["currency_id"], ["id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    """Drop the four FKs, the three added columns, then the table.

    `facility.currency_id` is NOT dropped: the column pre-dates this revision
    (it was already in the live schema), so removing it would take away
    something this revision never added. Only its constraint goes.

    Every step is guarded, so a downgrade against a partially-upgraded schema
    completes instead of aborting half-way.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table, fk_name in _FK_TARGETS:
        if _has_fk(inspector, table, fk_name):
            op.drop_constraint(fk_name, table, type_="foreignkey")

    for table in ("service_category_item", "package", "invoice"):
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "currency_id" in cols:
            op.drop_column(table, "currency_id")

    if "currency" in sa.inspect(conn).get_table_names():
        op.drop_table("currency")
