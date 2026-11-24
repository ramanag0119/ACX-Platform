"""Add the missing ix_invoice_currency_id index

Revision ID: f2a7c91d3b56
Revises: e5b9c3d71f48
Create Date: 2026-11-18 00:00:00.000000

A correction to d8e4f1a6b207, not a new feature.

`app/models/stay.py` declares the column with `index=True`:

    currency_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("currency.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )

so SQLAlchemy expects an index named `ix_invoice_currency_id`. d8e4f1a6b207
added the column and its foreign key but not that index. MySQL auto-creates an
index to back the FK -- `fk_invoice_currency_id_currency` -- which satisfies
the constraint but carries the wrong name, so
`test_indexes_match_the_models` correctly reported it missing.

The test was right and the migration was incomplete; this closes the gap
rather than relaxing the assertion.

Only `invoice` is affected. `package.currency_id` and
`service_category_item.currency_id` do not declare `index=True`, so they need
nothing -- confirmed against the models, not assumed.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2a7c91d3b56"
down_revision = "e5b9c3d71f48"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_invoice_currency_id"


def _indexes(conn) -> set[str]:
    return {i["name"] for i in sa.inspect(conn).get_indexes("invoice")}


def upgrade() -> None:
    conn = op.get_bind()
    if INDEX_NAME not in _indexes(conn):
        op.create_index(INDEX_NAME, "invoice", ["currency_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if INDEX_NAME in _indexes(conn):
        op.drop_index(INDEX_NAME, table_name="invoice")
