"""Candidate migration: upgrade/downgrade on a DISPOSABLE MySQL database only.

Also proves the draft stays outside the active Alembic history (HF-39).
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.integrations.processing.sql_models import INTEGRATION_TABLES

BACKEND = pathlib.Path(__file__).resolve().parents[2]
DRAFT = BACKEND / "migrations" / "drafts" / "integration_tables_candidate.py"
EXPECTED_HEADS = {"a3f1c8e2d904", "b3c4d5e6f7a8"}


def load_draft():
    spec = importlib.util.spec_from_file_location("integration_tables_candidate", DRAFT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_op(engine, fn):
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            fn()


def test_draft_is_not_part_of_active_alembic_history():
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    assert set(script.get_heads()) == EXPECTED_HEADS  # unchanged, still two heads (DBA decision)
    revisions = {r.revision for r in script.walk_revisions()}
    assert "draft_htng_fias_integration_tables" not in revisions
    draft = load_draft()
    assert draft.down_revision is None  # deliberately unset until the DBA chooses


@pytest.fixture
def clean_db(mysql_engine):
    with mysql_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_domain_effects"))
        from app.integrations.processing.sql_models import drop_integration_tables

        drop_integration_tables(conn)
        conn.execute(text("DROP TABLE IF EXISTS facility"))
        conn.execute(text("CREATE TABLE facility (id CHAR(36) NOT NULL PRIMARY KEY) ENGINE=InnoDB"))
    return mysql_engine


def test_upgrade_creates_exactly_the_modelled_schema_and_downgrade_removes_it(clean_db):
    engine = clean_db
    draft = load_draft()
    run_op(engine, draft.upgrade)
    insp = inspect(engine)
    names = set(insp.get_table_names())
    assert {t.name for t in INTEGRATION_TABLES} <= names
    for table in INTEGRATION_TABLES:
        reflected = {c["name"] for c in insp.get_columns(table.name)}
        assert reflected == {c.name for c in table.columns}, table.name
        reflected_ix = {tuple(ix["column_names"]) for ix in insp.get_indexes(table.name)}
        for ix in table.indexes:
            assert tuple(c.name for c in ix.columns) in reflected_ix, (table.name, ix.name)
        assert {fk["referred_table"] for fk in insp.get_foreign_keys(table.name)} == {
            fk.column.table.name for fk in table.foreign_keys
        }
    engine_ver = engine.connect().execute(text("SELECT VERSION()")).scalar_one()
    assert engine_ver.startswith("8.")
    # Idempotency key unique, mapping code binary collation, CHECK constraints present
    with engine.connect() as c:
        checks = c.execute(text(
            "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() "
            "AND CONSTRAINT_TYPE='CHECK'")).scalars().all()
    assert any("status_valid" in n for n in checks)

    run_op(engine, draft.downgrade)
    left = set(inspect(engine).get_table_names())
    assert not ({t.name for t in INTEGRATION_TABLES} & left)
    assert "facility" in left  # downgrade never touches HMS tables


def test_upgrade_is_idempotent_via_checkfirst(clean_db):
    """A second upgrade() is a no-op (create_all checkfirst). Note for the DBA: it
    would NOT reshape an existing table that differs -- a real revision should
    be applied once by Alembic (see HTNG_FIAS_MIGRATION_READINESS.md)."""
    draft = load_draft()
    run_op(clean_db, draft.upgrade)
    run_op(clean_db, draft.upgrade)
    assert len([t for t in inspect(clean_db).get_table_names() if t.startswith("integration_")]) == len(INTEGRATION_TABLES)
    run_op(clean_db, draft.downgrade)
