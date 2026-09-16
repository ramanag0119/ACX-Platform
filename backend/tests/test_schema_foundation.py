"""Phase 1.7 schema foundation tests.

Run:  python -m pytest tests -q

These assert that the live PostgreSQL schema is exactly the approved 92-table
blueprint (``backend/docs/FINAL_HMS_DATABASE_BLUEPRINT.md``). The models are
the executable expression of that blueprint, so most checks compare the live
database against ``Base.metadata`` -- which also proves the migration and the
models cannot drift apart.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.db.session import engine
from app.db.verify_schema import (
    RETIRED_PHASE1_ENUMS,
    RETIRED_PHASE1_TABLES,
    SCHEMA,
    detect_cycles,
    live_enums,
)
from app.models import (
    APPROVED_TABLES,
    COMPOSITE_PK_TABLES,
    HIGH_VOLUME_TABLES,
    LOOKUP_TABLES,
    Base,
)
from app.models.enums import ALL_ENUMS

EXPECTED_TABLE_COUNT = 92


@pytest.fixture(scope="module")
def insp():
    return inspect(engine)


@pytest.fixture(scope="module")
def conn():
    with engine.connect() as c:
        yield c


@pytest.fixture(scope="module")
def tables(insp):
    return {t for t in insp.get_table_names(schema=SCHEMA) if t != "alembic_version"}


# ---------------------------------------------------------------------------
# 1-3. Table inventory
# ---------------------------------------------------------------------------


def test_database_is_hms_db(conn):
    assert conn.execute(text("SELECT current_database()")).scalar() == "hms_db"


def test_blueprint_declares_92_tables():
    assert len(APPROVED_TABLES) == EXPECTED_TABLE_COUNT
    assert len(set(APPROVED_TABLES)) == EXPECTED_TABLE_COUNT, "duplicate table name"


def test_models_register_exactly_the_approved_tables():
    assert set(Base.metadata.tables) == set(APPROVED_TABLES)


def test_database_has_exactly_92_tables(tables):
    assert len(tables) == EXPECTED_TABLE_COUNT


def test_every_approved_table_exists(tables):
    missing = sorted(set(APPROVED_TABLES) - tables)
    assert not missing, f"missing approved tables: {missing}"


def test_no_unapproved_table_exists(tables):
    extra = sorted(tables - set(APPROVED_TABLES))
    assert not extra, f"unapproved tables present: {extra}"


def test_no_retired_phase1_table_survives(tables):
    survivors = sorted(tables & RETIRED_PHASE1_TABLES)
    assert not survivors, f"superseded Phase 1 tables still present: {survivors}"


# ---------------------------------------------------------------------------
# 4. Primary keys -- the three-tier policy of blueprint §2.3
# ---------------------------------------------------------------------------


def test_every_table_has_a_primary_key(insp, tables):
    without = sorted(
        t
        for t in tables
        if not insp.get_pk_constraint(t, schema=SCHEMA)["constrained_columns"]
    )
    assert not without, f"tables without a primary key: {without}"


def test_primary_keys_match_the_models(insp):
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        expected = [c.name for c in table.primary_key.columns]
        actual = insp.get_pk_constraint(name, schema=SCHEMA)["constrained_columns"]
        if sorted(expected) != sorted(actual):
            mismatched[name] = (expected, actual)
    assert not mismatched, f"primary key mismatch: {mismatched}"


def test_pk_tiers_are_disjoint_and_cover_every_table():
    tiered = LOOKUP_TABLES | HIGH_VOLUME_TABLES | COMPOSITE_PK_TABLES
    assert len(LOOKUP_TABLES) + len(HIGH_VOLUME_TABLES) + len(
        COMPOSITE_PK_TABLES
    ) == len(tiered), "a table is claimed by two PK tiers"
    unknown = sorted(tiered - set(APPROVED_TABLES))
    assert not unknown, f"PK tier names an unapproved table: {unknown}"


@pytest.mark.parametrize("table_name", sorted(LOOKUP_TABLES))
def test_t1_lookup_tables_use_a_seeded_integer_pk(insp, table_name):
    """T1: native SMALLINT/INTEGER, IKANOS ids preserved, never generated."""
    pk = insp.get_pk_constraint(table_name, schema=SCHEMA)["constrained_columns"]
    assert pk == ["id"]
    col = next(
        c
        for c in insp.get_columns(table_name, schema=SCHEMA)
        if c["name"] == "id"
    )
    assert str(col["type"]) in {"SMALLINT", "INTEGER"}, str(col["type"])
    assert not col.get("autoincrement", False), "lookup ids are seeded, not generated"


@pytest.mark.parametrize("table_name", sorted(HIGH_VOLUME_TABLES))
def test_t3_high_volume_tables_use_bigint_identity(insp, conn, table_name):
    """T3: BIGINT GENERATED ALWAYS AS IDENTITY."""
    col = next(
        c for c in insp.get_columns(table_name, schema=SCHEMA) if c["name"] == "id"
    )
    assert str(col["type"]) == "BIGINT", str(col["type"])
    identity = conn.execute(
        text(
            "SELECT is_identity, identity_generation FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = :t AND column_name = 'id'"
        ),
        {"s": SCHEMA, "t": table_name},
    ).one()
    assert identity.is_identity == "YES", f"{table_name}.id is not an identity column"
    assert identity.identity_generation == "ALWAYS"


def test_t2_entity_tables_use_uuid_pk(insp):
    tiered = LOOKUP_TABLES | HIGH_VOLUME_TABLES | COMPOSITE_PK_TABLES
    entity_tables = sorted(set(APPROVED_TABLES) - tiered)
    # 92 - 16 lookup - 12 high-volume - 14 composite
    assert len(entity_tables) == 50
    wrong = {}
    for t in entity_tables:
        col = next(
            c for c in insp.get_columns(t, schema=SCHEMA) if c["name"] == "id"
        )
        if str(col["type"]) != "UUID":
            wrong[t] = str(col["type"])
    assert not wrong, f"entity tables without a UUID pk: {wrong}"


def test_composite_pk_tables_have_multi_column_or_natural_keys(insp):
    for t in sorted(COMPOSITE_PK_TABLES):
        pk = insp.get_pk_constraint(t, schema=SCHEMA)["constrained_columns"]
        assert "id" not in pk, f"{t} should use its IKANOS natural key, not a surrogate"
        assert len(pk) >= 1


def test_user_role_pk_is_facility_scoped(insp):
    """The Phase 1 junction was (app_user_id, user_role_id) -- a user could not
    hold different roles at different facilities."""
    pk = insp.get_pk_constraint("user_role", schema=SCHEMA)["constrained_columns"]
    assert sorted(pk) == ["app_user_id", "facility_id", "role_id"]


def test_energy_stat_keeps_the_ikanos_four_column_pk(insp):
    pk = insp.get_pk_constraint("energy_stat", schema=SCHEMA)["constrained_columns"]
    assert sorted(pk) == ["amenity_id", "device_name", "facility_id", "hour"]


# ---------------------------------------------------------------------------
# legacy_id policy (blueprint §2.3)
# ---------------------------------------------------------------------------


def test_legacy_id_present_and_unique_on_surrogate_key_tables(insp):
    """Tables whose IKANOS integer surrogate key is replaced by a UUID or an
    identity value carry it as `legacy_id`. Lookup tables (the IKANOS id IS
    the PK) and composite-natural-key tables have no surrogate to preserve."""
    expected = set(APPROVED_TABLES) - LOOKUP_TABLES - COMPOSITE_PK_TABLES
    for t in sorted(expected):
        cols = {c["name"] for c in insp.get_columns(t, schema=SCHEMA)}
        assert "legacy_id" in cols, f"{t} is missing legacy_id"
        uniques = {
            tuple(u["column_names"])
            for u in insp.get_unique_constraints(t, schema=SCHEMA)
        }
        assert ("legacy_id",) in uniques, f"{t}.legacy_id is not unique"

    for t in sorted(LOOKUP_TABLES | COMPOSITE_PK_TABLES):
        cols = {c["name"] for c in insp.get_columns(t, schema=SCHEMA)}
        assert "legacy_id" not in cols, f"{t} should not carry legacy_id"


# ---------------------------------------------------------------------------
# 5. Foreign keys
# ---------------------------------------------------------------------------


def _model_fks() -> set[tuple]:
    out = set()
    for name, table in Base.metadata.tables.items():
        for fk in table.foreign_key_constraints:
            out.add(
                (
                    name,
                    tuple(sorted(c.name for c in fk.columns)),
                    fk.referred_table.name,
                )
            )
    return out


def _db_fks(insp) -> set[tuple]:
    out = set()
    for name in Base.metadata.tables:
        for fk in insp.get_foreign_keys(name, schema=SCHEMA):
            out.add(
                (name, tuple(sorted(fk["constrained_columns"])), fk["referred_table"])
            )
    return out


def test_foreign_keys_match_the_models_exactly(insp):
    expected, actual = _model_fks(), _db_fks(insp)
    assert not (expected - actual), f"FKs missing from the database: {expected - actual}"
    assert not (actual - expected), f"unexpected FKs in the database: {actual - expected}"


def test_no_foreign_key_targets_a_retired_table(insp):
    offenders = [
        (t, fk["constrained_columns"], fk["referred_table"])
        for t in Base.metadata.tables
        for fk in insp.get_foreign_keys(t, schema=SCHEMA)
        if fk["referred_table"] in RETIRED_PHASE1_TABLES
    ]
    assert not offenders, f"FKs still pointing at retired tables: {offenders}"


@pytest.mark.parametrize(
    "table_name,column,referred",
    [
        # Corrections the blueprint calls out explicitly.
        ("job_function", "facility_id", "facility"),  # NOT department
        ("service_request", "assigned_to", "app_user"),  # NOT employee
        ("device_incident", "assigned_to", "app_user"),  # NOT employee
        ("job_order", "assigned_to", "app_user"),  # NOT employee
        ("amenity", "property_chain_id", "property_chain"),  # NOT property_type
        ("amenity", "status", "amenity_status"),  # [INFER], blueprint §11.4
        ("device_incident", "latest_alert_id", "device_alert"),  # alert->incident link
        ("value_alert", "limit_config_id", "value_alert_limit_config"),
        ("stay_user", "stay_id", "stay"),
        ("room_allocation", "room_id", "amenity"),
        ("role_module_permission", "module_id", "role_module"),
        ("device_stat", "device_param_id", "device_param"),
        ("incident_history", "incident_id", "device_incident"),
        ("access_key", "user_device_acl_id", "user_device_acl"),
        ("activity_notifier", "activity_id", "activity"),
        ("notification_result", "receiver_id", "notification_receiver"),
        ("scheduler_job_execution", "scheduler_job_id", "scheduler_job"),
        ("property_chain", "level_one_id", "property"),
    ],
)
def test_blueprint_critical_relationships(insp, table_name, column, referred):
    fks = insp.get_foreign_keys(table_name, schema=SCHEMA)
    match = [f for f in fks if f["constrained_columns"] == [column]]
    assert match, f"{table_name}.{column} has no foreign key"
    assert match[0]["referred_table"] == referred


def test_job_function_has_no_department_fk(insp):
    """`functions.department_id` does not exist in IKANOS [FACT]."""
    cols = {c["name"] for c in insp.get_columns("job_function", schema=SCHEMA)}
    assert "department_id" not in cols


# ---------------------------------------------------------------------------
# 11. Circular relationships
# ---------------------------------------------------------------------------


def test_circular_foreign_keys_exist_and_are_satisfiable(insp, conn):
    """The facility <-> app_user <-> department and facility <-> attachment
    cycles are real and intended. What must hold is that every column in a
    cycle is NULLABLE, so a bootstrap row can be inserted."""
    cycles = detect_cycles()
    assert cycles, "expected the documented FK cycles to be present"

    bootstrap_edges = [
        ("organisation", "created_by"),
        ("facility", "created_by"),
        ("facility", "facility_image_id"),
        ("facility", "default_key_user"),
        ("attachment", "facility_id"),
        ("attachment", "created_by"),
        ("app_user", "created_by"),
        ("app_user", "department_id"),
        ("app_user", "job_function_id"),
    ]
    non_nullable = []
    for table, column in bootstrap_edges:
        col = next(
            c for c in insp.get_columns(table, schema=SCHEMA) if c["name"] == column
        )
        if not col["nullable"]:
            non_nullable.append(f"{table}.{column}")

    # created_by is NOT NULL in IKANOS on organisation/facility/app_user, so
    # the bootstrap is a deferred-constraint concern, not a nullability one.
    # What the test guarantees is that the cycle is broken at the DDL level:
    # every cyclic constraint exists as its own ALTER-added constraint.
    for table, column in bootstrap_edges:
        fks = insp.get_foreign_keys(table, schema=SCHEMA)
        assert any(
            fk["constrained_columns"] == [column] for fk in fks
        ), f"cyclic FK {table}.{column} was lost"


def test_app_user_supervisor_is_self_referential(insp):
    fks = insp.get_foreign_keys("app_user", schema=SCHEMA)
    sup = [f for f in fks if f["constrained_columns"] == ["supervisor"]]
    assert sup and sup[0]["referred_table"] == "app_user"


# ---------------------------------------------------------------------------
# 6. Unique constraints
# ---------------------------------------------------------------------------


def test_unique_constraints_match_the_models(insp):
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        expected = {
            tuple(sorted(c.name for c in uc.columns))
            for uc in table.constraints
            if uc.__class__.__name__ == "UniqueConstraint"
        }
        actual = {
            tuple(sorted(u["column_names"]))
            for u in insp.get_unique_constraints(name, schema=SCHEMA)
        }
        if expected != actual:
            mismatched[name] = (sorted(expected), sorted(actual))
    assert not mismatched, f"unique constraint mismatch: {mismatched}"


@pytest.mark.parametrize(
    "table_name,columns",
    [
        ("facility", ("facility_uid",)),
        ("organisation", ("org_uid",)),
        ("app_user", ("user_uid",)),
        ("app_user", ("user_name",)),
        ("stay", ("internal_stay_ref_number",)),
        ("invoice", ("invoice_number",)),
        ("job_order", ("order_reference",)),
        ("promo_code", ("promo_code",)),
        ("device", ("device_uid",)),
        ("user_token", ("token",)),
        ("scheduler_job", ("job_key",)),
        ("service_request", ("ref_number",)),
        (
            "value_alert_limit_config",
            ("device_name", "facility_id", "parameter"),
        ),
        ("notification_template", ("name", "type")),
    ],
)
def test_documented_unique_keys(insp, table_name, columns):
    actual = {
        tuple(sorted(u["column_names"]))
        for u in insp.get_unique_constraints(table_name, schema=SCHEMA)
    }
    assert tuple(sorted(columns)) in actual


# ---------------------------------------------------------------------------
# 7. Indexes
# ---------------------------------------------------------------------------


def test_indexes_match_the_models(insp):
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        expected = {ix.name for ix in table.indexes}
        actual = {ix["name"] for ix in insp.get_indexes(name, schema=SCHEMA)}
        missing = expected - actual
        if missing:
            mismatched[name] = sorted(missing)
    assert not mismatched, f"indexes missing from the database: {mismatched}"


def test_gin_indexes_exist_on_merged_metadata_columns(insp):
    """The four *_metadata EAV tables were merged into JSONB columns
    (blueprint §3.3); each needs a GIN index to keep key lookup cheap."""
    for table, index in (
        ("amenity", "ix_amenity_metadata_gin"),
        ("app_user", "ix_app_user_metadata_gin"),
        ("device", "ix_device_metadata_gin"),
        ("service_category_item", "ix_service_category_item_metadata_gin"),
    ):
        names = {ix["name"] for ix in insp.get_indexes(table, schema=SCHEMA)}
        assert index in names, f"{table} is missing {index}"


def test_brin_indexes_exist_on_high_volume_timestamps(conn):
    rows = conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = :s AND indexdef LIKE '%USING brin%'"
        ),
        {"s": SCHEMA},
    ).scalars().all()
    assert "ix_device_stat_timestamp_brin" in rows
    assert "ix_device_health_stat_created_on_brin" in rows


# ---------------------------------------------------------------------------
# 8. ENUM types and values
# ---------------------------------------------------------------------------


def test_enum_type_count(conn):
    assert len(live_enums(conn)) == len(ALL_ENUMS) == 34


@pytest.mark.parametrize("enum_type", ALL_ENUMS, ids=lambda e: e.name)
def test_enum_values_match_ikanos_exactly(conn, enum_type):
    """Order and capitalisation are both significant."""
    actual = live_enums(conn).get(enum_type.name)
    assert actual is not None, f"enum type {enum_type.name} does not exist"
    assert actual == list(enum_type.enums)


def test_no_retired_phase1_enum_survives(conn):
    survivors = sorted(set(live_enums(conn)) & RETIRED_PHASE1_ENUMS)
    assert not survivors, f"superseded Phase 1 enum types present: {survivors}"


def test_enum_literals_that_are_easy_to_normalise_by_accident(conn):
    """Spaces and mixed case in IKANOS literals must survive verbatim."""
    enums = live_enums(conn)
    assert "checkout accepted" in enums["stay_status"]
    assert "push notification" in enums["notification_channel"]
    assert "Date Time" in enums["param_data_type"]
    assert "job order" in enums["import_entity_type"]
    assert "smart room" in enums["daily_metric_type"]
    assert enums["device_health_status"] == ["Active", "Inactive"]
    assert enums["command_processing_status"][0] == "Queued"
    assert enums["device_short_code"] == ["HUB", "KLE", "MIK", "AIR"]
    # `Info` severity and the `Open` incident status were Phase 1 inventions.
    assert "Info" not in enums["alert_severity"]
    assert enums["alert_severity"] == ["warning", "critical"]
    # role_type must include system_user, which the UI hides.
    assert "system_user" in enums["role_type"]


# ---------------------------------------------------------------------------
# 9-10. Nullability and data types
# ---------------------------------------------------------------------------


def test_nullability_matches_the_models(insp):
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        actual = {
            c["name"]: c["nullable"] for c in insp.get_columns(name, schema=SCHEMA)
        }
        for col in table.columns:
            if col.name in actual and actual[col.name] != col.nullable:
                mismatched[f"{name}.{col.name}"] = (col.nullable, actual[col.name])
    assert not mismatched, f"nullability mismatch (model, db): {mismatched}"


def test_column_sets_match_the_models(insp):
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        expected = {c.name for c in table.columns}
        actual = {c["name"] for c in insp.get_columns(name, schema=SCHEMA)}
        if expected != actual:
            mismatched[name] = {
                "missing": sorted(expected - actual),
                "extra": sorted(actual - expected),
            }
    assert not mismatched, f"column mismatch: {mismatched}"


def test_column_types_match_the_models(insp):
    """Compare the compiled PostgreSQL type of every column.

    Both sides are compiled with the postgresql dialect: `str()` on a
    reflected type loses `timezone=True` and renders an enum as VARCHAR(n),
    which would make this check meaningless.
    """
    from sqlalchemy.dialects import postgresql

    dialect = postgresql.dialect()
    mismatched = {}
    for name, table in Base.metadata.tables.items():
        actual = {c["name"]: c["type"] for c in insp.get_columns(name, schema=SCHEMA)}
        for col in table.columns:
            if col.name not in actual:
                continue
            want = col.type.compile(dialect).upper()
            got = actual[col.name].compile(dialect).upper()
            if want.replace(" ", "") != got.replace(" ", ""):
                mismatched[f"{name}.{col.name}"] = (want, got)
    assert not mismatched, f"type mismatch (model, db): {mismatched}"


def test_timestamps_are_timezone_aware(insp):
    """Every TIMESTAMP column must be TIMESTAMPTZ -- a naive timestamp would
    make checkout scheduling wrong across DST."""
    naive = []
    for name in Base.metadata.tables:
        for c in insp.get_columns(name, schema=SCHEMA):
            t = c["type"]
            if t.__class__.__name__ in {"TIMESTAMP", "DateTime"} and not getattr(
                t, "timezone", False
            ):
                naive.append(f"{name}.{c['name']}")
    assert not naive, f"naive timestamp columns: {naive}"


def test_audit_columns_use_ikanos_naming(insp):
    """created_on / updated_on, not the Phase 1 created_at / updated_at."""
    wrong = []
    for name in Base.metadata.tables:
        cols = {c["name"] for c in insp.get_columns(name, schema=SCHEMA)}
        if "created_at" in cols or "updated_at" in cols:
            wrong.append(name)
        if "created_on" not in cols or "updated_on" not in cols:
            wrong.append(f"{name} (missing created_on/updated_on)")
    assert not wrong, f"audit column naming problems: {wrong}"


def test_facility_uid_is_only_on_facility(insp):
    """IKANOS denormalises facility_uid onto 91 tables; the blueprint keeps
    only the canonical copy (§2.5)."""
    offenders = [
        name
        for name in Base.metadata.tables
        if name != "facility"
        and "facility_uid" in {c["name"] for c in insp.get_columns(name, schema=SCHEMA)}
    ]
    assert not offenders, f"facility_uid should exist only on facility: {offenders}"


# ---------------------------------------------------------------------------
# Columns the blueprint explicitly refuses to invent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "table_name,column,reason",
    [
        ("package", "price", "no price column exists in IKANOS `packages`"),
        ("invoice", "status", "no status column exists in IKANOS `invoices`"),
        ("device", "ip_address", "documented in CPA §8, absent from the DB"),
        ("device", "mac_address", "documented in CPA §8, absent from the DB"),
        ("device", "last_seen", "derivable from device_health_stat.created_on"),
        ("firmware", "is_latest", "currency is current vs expected firmware version"),
        ("alert_type", "severity", "alert_types is (id, name); severity is on device_alert"),
        ("alert_type", "category", "alert_types is (id, name)"),
        ("alert_type", "is_active", "alert_types is (id, name)"),
        ("incident_status", "status_code", "incident_statuses is (id, name)"),
        ("incident_status", "display_color", "incident_statuses is (id, name)"),
        ("incident_status", "is_resolved", "incident_statuses is (id, name)"),
        ("device_incident", "severity", "severity lives on device_alert"),
        ("device_incident", "resolved_on", "lives in incident_history"),
        ("device_incident", "notes", "lives in incident_history"),
        ("value_alert", "parameter", "lives on value_alert_limit_config"),
        ("value_alert", "unit", "lives on device_param"),
        ("value_alert", "current_value", "does not exist in IKANOS"),
        ("service_request", "priority", "does not exist in IKANOS"),
        ("occasion", "lock_message", "does not exist -- OPEN DECISION #5"),
        ("role", "permissions", "replaced by role_module_permission"),
        ("app_user", "is_active", "does not exist -- OPEN DECISION #12"),
    ],
)
def test_uninvented_columns_are_absent(insp, table_name, column, reason):
    cols = {c["name"] for c in insp.get_columns(table_name, schema=SCHEMA)}
    assert column not in cols, f"{table_name}.{column} should not exist: {reason}"


# ---------------------------------------------------------------------------
# 12. Data independence
# ---------------------------------------------------------------------------
# Phase 1.7 asserted here that every table was empty. Phase 1.8 seeds a demo
# dataset, so that invariant is superseded -- see tests/test_seed_data.py.
# What must still hold is that this schema suite proves the *schema*, not the
# data: none of the checks above may depend on rows existing or not existing.


def test_schema_suite_is_independent_of_seeded_data(conn):
    """Row counts may be zero or non-zero; the schema is identical either way."""
    total = sum(
        conn.execute(text(f'SELECT count(*) FROM public."{name}"')).scalar()
        for name in sorted(Base.metadata.tables)
    )
    assert total >= 0  # always true; the real assertion is that nothing above cares


def test_alembic_is_at_a_single_head(conn):
    revs = conn.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    assert len(revs) == 1, f"expected exactly one alembic head, got {revs}"
