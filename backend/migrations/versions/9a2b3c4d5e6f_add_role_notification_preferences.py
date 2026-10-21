"""add role notification_preferences column

Revision ID: 9a2b3c4d5e6f
Revises: 8f1e3c5a7b92
Create Date: 2026-10-21 17:40:00.000000

Persist role notification preferences as JSONB list in role table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '9a2b3c4d5e6f'
down_revision = '8f1e3c5a7b92'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    role_cols = [c["name"] for c in inspector.get_columns("role")]

    if "notification_preferences" not in role_cols:
        op.add_column(
            "role",
            sa.Column(
                "notification_preferences",
                JSONB,
                nullable=True,
                server_default="[]"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    role_cols = [c["name"] for c in inspector.get_columns("role")]

    if "notification_preferences" in role_cols:
        op.drop_column("role", "notification_preferences")
