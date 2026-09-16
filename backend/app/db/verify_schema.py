"""Phase 1.7 - schema verification and inventory report.

Compares the live PostgreSQL schema against the approved 92-table blueprint
(``backend/docs/FINAL_HMS_DATABASE_BLUEPRINT.md``) as expressed by the models.

Run:  python -m app.db.verify_schema
Exit code is 0 when the schema matches, 1 otherwise.
"""

from __future__ import annotations

import sys

from sqlalchemy import inspect, text

from app.db.session import engine
from app.models import (
    APPROVED_TABLES,
    COMPOSITE_PK_TABLES,
    HIGH_VOLUME_TABLES,
    LOOKUP_TABLES,
    Base,
)
from app.models.enums import ALL_ENUMS

SCHEMA = "public"

#: Tables from the superseded Phase 1 39-table foundation. None may survive.
RETIRED_PHASE1_TABLES = frozenset(
    {
        "booking",
        "employee",
        "occupant",
        "food_category",
        "food_menu",
        "holiday",
        "event",
        "offer",
        "fcm_token",
        "limit_config",
        "value_alerts",
        "current_incident_status",
        "maintenance_schedule",
        "scheduled_task",
        "energy_data",
        "sensor_reading",
        "energy_aggregate",
        "device_uptime",
        "device_health_log",
        "app_user_user_role",
    }
)

#: The 13 Phase 1 enum types. Zero of them matched IKANOS; none may survive.
RETIRED_PHASE1_ENUMS = frozenset(
    {
        "aggregate_interval",
        "device_status",
        "device_type",
        "incident_status",
        "job_order_type",
        "limit_type",
        "notification_type",
        "scheduled_task_status",
        "scheduled_task_type",
    }
)


def live_tables(insp) -> set[str]:
    return {
        t for t in insp.get_table_names(schema=SCHEMA) if t != "alembic_version"
    }


def live_enums(conn) -> dict[str, list[str]]:
    rows = conn.execute(
        text(
            """
            SELECT t.typname, e.enumlabel
            FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE n.nspname = :schema AND t.typtype = 'e'
            ORDER BY t.typname, e.enumsortorder
            """
        ),
        {"schema": SCHEMA},
    )
    out: dict[str, list[str]] = {}
    for name, label in rows:
        out.setdefault(name, []).append(label)
    return out


def detect_cycles() -> list[list[str]]:
    """Foreign-key cycles among the model tables.

    Cycles are expected and legitimate here (facility <-> app_user <->
    department, facility <-> attachment); they are reported, not treated as
    errors. The migration breaks them with deferred ALTER TABLE statements.
    """
    graph: dict[str, set[str]] = {
        name: {fk.column.table.name for fk in table.foreign_keys}
        - {name}  # ignore self-references
        for name, table in Base.metadata.tables.items()
    }
    cycles: list[list[str]] = []
    seen: set[str] = set()

    def walk(node: str, path: list[str], onstack: set[str]) -> None:
        for nxt in sorted(graph.get(node, ())):
            if nxt in onstack:
                cycle = path[path.index(nxt) :] + [nxt]
                key = tuple(sorted(set(cycle)))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
                continue
            if len(path) > 6:
                continue
            walk(nxt, path + [nxt], onstack | {nxt})

    for start in sorted(graph):
        walk(start, [start], {start})
    return cycles


def main() -> int:
    ok = True
    insp = inspect(engine)

    with engine.connect() as conn:
        db = conn.execute(text("SELECT current_database()")).scalar()
        tables = live_tables(insp)
        enums = live_enums(conn)

        n_fk = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.table_constraints "
                "WHERE table_schema = :s AND constraint_type = 'FOREIGN KEY'"
            ),
            {"s": SCHEMA},
        ).scalar()
        n_uq = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.table_constraints "
                "WHERE table_schema = :s AND constraint_type = 'UNIQUE'"
            ),
            {"s": SCHEMA},
        ).scalar()
        n_ix = conn.execute(
            text("SELECT count(*) FROM pg_indexes WHERE schemaname = :s"),
            {"s": SCHEMA},
        ).scalar()
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    approved = set(APPROVED_TABLES)

    print(f"database            : {db}")
    print(f"alembic revision    : {rev}")
    print(f"tables              : {len(tables)} (expected 92)")
    print(f"enum types          : {len(enums)} (expected {len(ALL_ENUMS)})")
    print(f"foreign keys        : {n_fk}")
    print(f"unique constraints  : {n_uq}")
    print(f"indexes             : {n_ix}")
    print()
    print(f"PK tiers            : lookup {len(LOOKUP_TABLES)} · composite "
          f"{len(COMPOSITE_PK_TABLES)} · high-volume {len(HIGH_VOLUME_TABLES)} · "
          f"uuid {92 - len(LOOKUP_TABLES) - len(COMPOSITE_PK_TABLES) - len(HIGH_VOLUME_TABLES)}")
    print()

    missing = sorted(approved - tables)
    extra = sorted(tables - approved)
    retired = sorted(tables & RETIRED_PHASE1_TABLES)
    retired_enums = sorted(set(enums) & RETIRED_PHASE1_ENUMS)

    for label, items in (
        ("MISSING approved tables", missing),
        ("UNAPPROVED tables present", extra),
        ("RETIRED Phase 1 tables still present", retired),
        ("RETIRED Phase 1 enum types still present", retired_enums),
    ):
        if items:
            ok = False
            print(f"FAIL  {label}: {items}")

    for e in ALL_ENUMS:
        got = enums.get(e.name)
        if got is None:
            ok = False
            print(f"FAIL  enum type missing: {e.name}")
        elif got != list(e.enums):
            ok = False
            print(f"FAIL  enum {e.name}: expected {list(e.enums)}, got {got}")

    cycles = detect_cycles()
    print(f"foreign-key cycles  : {len(cycles)} (expected; handled by deferred FKs)")
    for c in cycles[:8]:
        print("    " + " -> ".join(c))

    print()
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
