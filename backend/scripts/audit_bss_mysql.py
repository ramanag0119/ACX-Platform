r"""Read-only structural audit of the BSS MySQL database (`inspironics_app`).

    ..\.venv\Scripts\python.exe -m scripts.audit_bss_mysql

ANALYSIS ONLY. The session is opened `READ ONLY`, every statement is a SELECT
against `information_schema` plus `SHOW` / `COUNT(*)`, and a guard rejects any
statement whose first keyword could mutate. Nothing is written, and the engine
never commits.

Writes `scripts/bss_mysql_schema.json` so later phases do not need to re-query.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings

OUT = Path(__file__).resolve().parent / "bss_mysql_schema.json"
FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "rename", "replace", "grant", "revoke", "set",
}


def q(sql: str) -> str:
    """Refuse anything that is not a read."""
    head = sql.strip().split(None, 1)[0].lower()
    if head in FORBIDDEN:
        raise RuntimeError(f"refusing to run a mutating statement: {head}")
    return sql


def main() -> int:
    if not settings.MYSQL_PASSWORD:
        print("MYSQL_PASSWORD is empty. Supply it from the vault:")
        print("  secure-local\\run_with_secret.py -- python -m scripts.audit_bss_mysql")
        return 2

    from app.db.session import CONNECT_ARGS

    engine = create_engine(
        settings.sqlalchemy_url, connect_args=CONNECT_ARGS, echo=False
    )
    db = settings.MYSQL_DATABASE
    report: dict = {"database": db}

    with engine.connect() as conn:
        conn.execute(text("SET SESSION TRANSACTION READ ONLY"))

        report["server_version"] = conn.execute(text("SELECT VERSION()")).scalar_one()
        report["current_user"] = conn.execute(text("SELECT CURRENT_USER()")).scalar_one()
        report["ssl_cipher"] = conn.execute(
            text("SELECT VARIABLE_VALUE FROM performance_schema.session_status "
                 "WHERE VARIABLE_NAME='Ssl_cipher'")
        ).scalar()
        report["grants"] = [r[0] for r in conn.execute(text("SHOW GRANTS"))]
        report["db_collation"] = conn.execute(
            text("SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                 "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=:d"),
            {"d": db},
        ).mappings().first()
        report["sql_mode"] = conn.execute(text("SELECT @@sql_mode")).scalar()

        def rows(sql, **p):
            return [dict(r) for r in conn.execute(text(q(sql)), p or {}).mappings()]

        tables = rows(
            "SELECT TABLE_NAME, TABLE_TYPE, ENGINE, TABLE_ROWS, DATA_LENGTH,"
            " INDEX_LENGTH, TABLE_COLLATION, TABLE_COMMENT, AUTO_INCREMENT"
            " FROM information_schema.TABLES WHERE TABLE_SCHEMA=:d"
            " ORDER BY TABLE_NAME", d=db)
        columns = rows(
            "SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE,"
            " DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA,"
            " CHARACTER_SET_NAME, COLLATION_NAME, COLUMN_COMMENT"
            " FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=:d"
            " ORDER BY TABLE_NAME, ORDINAL_POSITION", d=db)
        indexes = rows(
            "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX,"
            " COLUMN_NAME, INDEX_TYPE, CARDINALITY"
            " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=:d"
            " ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX", d=db)
        fks = rows(
            "SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME,"
            " k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME,"
            " r.UPDATE_RULE, r.DELETE_RULE"
            " FROM information_schema.KEY_COLUMN_USAGE k"
            " JOIN information_schema.REFERENTIAL_CONSTRAINTS r"
            "   ON r.CONSTRAINT_SCHEMA=k.TABLE_SCHEMA"
            "  AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME"
            " WHERE k.TABLE_SCHEMA=:d AND k.REFERENCED_TABLE_NAME IS NOT NULL"
            " ORDER BY k.TABLE_NAME, k.ORDINAL_POSITION", d=db)
        constraints = rows(
            "SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE"
            " FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=:d"
            " ORDER BY TABLE_NAME", d=db)

        report["views"] = rows(
            "SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA=:d", d=db)
        report["routines"] = rows(
            "SELECT ROUTINE_NAME, ROUTINE_TYPE FROM information_schema.ROUTINES"
            " WHERE ROUTINE_SCHEMA=:d", d=db)
        report["triggers"] = rows(
            "SELECT TRIGGER_NAME, EVENT_OBJECT_TABLE, ACTION_TIMING,"
            " EVENT_MANIPULATION FROM information_schema.TRIGGERS"
            " WHERE TRIGGER_SCHEMA=:d", d=db)

        # ENUM definitions, which MySQL stores inline in COLUMN_TYPE.
        report["enums"] = [
            {"table": c["TABLE_NAME"], "column": c["COLUMN_NAME"],
             "definition": c["COLUMN_TYPE"]}
            for c in columns if c["DATA_TYPE"] in ("enum", "set")
        ]

        # TABLE_ROWS is an InnoDB estimate; count exactly.
        exact: dict[str, object] = {}
        for t in tables:
            if t["TABLE_TYPE"] != "BASE TABLE":
                continue
            name = t["TABLE_NAME"]
            try:
                exact[name] = conn.execute(
                    text(f"SELECT COUNT(*) FROM `{name}`")
                ).scalar_one()
            except Exception as exc:
                exact[name] = f"error: {type(exc).__name__}"

        alembic = None
        if any(t["TABLE_NAME"] == "alembic_version" for t in tables):
            alembic = conn.execute(
                text("SELECT version_num FROM alembic_version")).scalar()
        report["alembic_revision"] = alembic

    by_table: dict[str, dict] = {
        t["TABLE_NAME"]: {**t, "exact_rows": exact.get(t["TABLE_NAME"]),
                          "columns": [], "indexes": defaultdict(list),
                          "foreign_keys": [], "constraints": [],
                          "referenced_by": []}
        for t in tables
    }
    for c in columns:
        by_table[c["TABLE_NAME"]]["columns"].append(c)
    for i in indexes:
        by_table[i["TABLE_NAME"]]["indexes"][i["INDEX_NAME"]].append(i)
    for f in fks:
        by_table[f["TABLE_NAME"]]["foreign_keys"].append(f)
        if f["REFERENCED_TABLE_NAME"] in by_table:
            by_table[f["REFERENCED_TABLE_NAME"]]["referenced_by"].append(f)
    for c in constraints:
        by_table[c["TABLE_NAME"]]["constraints"].append(c)
    for t in by_table.values():
        t["indexes"] = dict(t["indexes"])

    report["tables"] = by_table
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"database     : {db}")
    print(f"server       : MySQL {report['server_version']}")
    print(f"TLS cipher   : {report['ssl_cipher'] or 'NOT ENCRYPTED'}")
    print(f"collation    : {report['db_collation']}")
    print(f"sql_mode     : {report['sql_mode']}")
    print(f"tables       : {len(by_table)}   views: {len(report['views'])}")
    print(f"FK columns   : {len(fks)}   enum columns: {len(report['enums'])}")
    print(f"routines     : {len(report['routines'])}  triggers: {len(report['triggers'])}")
    print(f"alembic      : {alembic or 'none'}")
    nonempty = {k: v for k, v in exact.items() if isinstance(v, int) and v}
    print(f"rows         : {sum(nonempty.values())} across {len(nonempty)} non-empty tables")
    for k, v in sorted(nonempty.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {k:<42} {v:>9}")
    print(f"\nFull dump -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
