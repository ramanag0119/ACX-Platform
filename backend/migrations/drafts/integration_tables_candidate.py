"""CANDIDATE MIGRATION -- NOT APPROVED -- DO NOT MOVE INTO versions/ WITHOUT DBA SIGN-OFF.

HTNG/FIAS integration tables (decision HF-39, DBA/schema authorization).

This file lives in migrations/drafts/, which Alembic does not scan
(alembic.ini: script_location = migrations, versions in migrations/versions),
so it cannot be applied by `alembic upgrade`. It has been applied ONLY to a
disposable MySQL 8.4 database by the test suite (via the same metadata).

Before it can become a real revision the DBA must decide:

1. down_revision. The repository currently has TWO Alembic heads
   (a3f1c8e2d904 and b3c4d5e6f7a8, both branching from 7c4e2b9a1d53). Whether
   this migration merges them, or a separate merge revision comes first, is a
   DBA decision -- it is deliberately left unset here.
2. The pre-existing chain does not apply to a fresh MySQL database
   (8f1e3c5a7b92 emits `BOOL NOT NULL DEFAULT 'true'`, MySQL error 1067), so
   the target database's actual revision must be confirmed first.
3. Retention/encryption for integration_inbound_payloads (HF-21) and audit
   retention (HF-23).

Reviewable DDL: docs/HTNG_FIAS_CANDIDATE_MIGRATION_MYSQL.sql (generated from
app/integrations/processing/sql_models.py with the MySQL dialect).
"""

from __future__ import annotations

from alembic import op

from app.integrations.processing.sql_models import create_integration_tables, drop_integration_tables

revision = "draft_htng_fias_integration_tables"
down_revision = None  # TO BE SET BY THE DBA -- see docstring item 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_integration_tables(op.get_bind())


def downgrade() -> None:
    drop_integration_tables(op.get_bind())
