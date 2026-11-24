"""Give role.notification_preferences its `[]` default and back-fill NULLs

Revision ID: a4d6e802c159
Revises: f2a7c91d3b56
Create Date: 2026-11-19 00:00:00.000000

A correction to e5b9c3d71f48, not a new feature.

e5b9c3d71f48 added `role.notification_preferences` as plain nullable JSON and
justified the missing default like this:

    MySQL 8 rejects a literal DEFAULT on a JSON column [...] The column is
    nullable and every reader defaults it -- `RoleRead.notification_preferences`
    is `Field(default_factory=list)` -- so a NULL reads as [] either way.

The second half of that is WRONG. Pydantic's `default_factory` fires when a
field is ABSENT, not when it is present and None. The ORM hands over
`notification_preferences=None`, and `list[str]` rejects None, so building a
RoleRead raised:

    pydantic_core.ValidationError: 1 validation error for RoleRead

on every role read -- 11 failures across test_access_api,
test_auth_api and test_employee_role_flow.

The first half was also too pessimistic. MySQL forbids a LITERAL default on
JSON, but has allowed an EXPRESSION default since 8.0.13:

    prefs JSON DEFAULT (JSON_ARRAY())      -- verified on this 8.4.13 server

So the column can carry exactly the `server_default="[]"` the model declares.

This revision does both halves:
  1. back-fills existing NULL rows with an empty array;
  2. attaches DEFAULT (JSON_ARRAY()) so new rows never arrive NULL.

An empty preference list is the documented default, not business content --
nothing is invented here. Any role that has genuinely chosen preferences keeps
them: the back-fill is NULL-guarded.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a4d6e802c159"
down_revision = "f2a7c91d3b56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Existing rows: NULL -> []. Guarded, so a real preference list is kept.
    op.execute(
        sa.text(
            "UPDATE role SET notification_preferences = JSON_ARRAY() "
            "WHERE notification_preferences IS NULL"
        )
    )
    # 2. Future rows. Expression default -- MySQL 8.0.13+; parentheses required.
    op.execute(
        sa.text(
            "ALTER TABLE role MODIFY COLUMN notification_preferences "
            "JSON DEFAULT (JSON_ARRAY())"
        )
    )


def downgrade() -> None:
    """Drop the default. The back-filled `[]` values are LEFT IN PLACE.

    They are indistinguishable from a role that legitimately has no
    preferences, and reverting them to NULL would reintroduce the
    ValidationError this revision exists to fix.
    """
    op.execute(
        sa.text(
            "ALTER TABLE role MODIFY COLUMN notification_preferences JSON NULL"
        )
    )
