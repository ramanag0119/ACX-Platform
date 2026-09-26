"""rename service status 3 to In Progress

Revision ID: 7c4e2b9a1d53
Revises: 0e2687233b59
Create Date: 2026-09-26 12:00:00.000000

`service_status` id 3 was seeded with the IKANOS label "Partially completed".
The business calls that stage "In Progress". Only the label changes: the id is
kept, so every `service_request.status`, `service_request_item.status` and
`maintenance_request.maintenance_request_status` that points at 3 follows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7c4e2b9a1d53'
down_revision: Union[str, Sequence[str], None] = '0e2687233b59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename(name: str) -> None:
    op.execute(
        sa.text("UPDATE service_status SET name = :name WHERE id = 3").bindparams(name=name)
    )


def upgrade() -> None:
    _rename("In Progress")


def downgrade() -> None:
    _rename("Partially completed")
