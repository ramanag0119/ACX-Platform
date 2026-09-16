"""HMS demo seed runner.

    python -m seeds.run_seed              seed, then print the row-count report
    python -m seeds.run_seed --report     report only, insert nothing

Properties this runner guarantees:

  * **One transaction.** Every step runs inside a single transaction. Any
    failure rolls the whole thing back, so a partial demo dataset can never be
    left behind. The exact failing step and error are reported.
  * **Idempotent.** Every row is addressed by a deterministic id or a natural
    key, so a second run updates the same rows instead of inserting copies.
  * **No FK bypass.** Constraints stay fully enabled; steps run in dependency
    order. `session_replication_role` is never touched.
  * **No schema change.** The runner only ever issues DML.

Database credentials come from `app.core.config` (.env). Nothing is hardcoded.
"""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import APPROVED_TABLES
from seeds.steps import (
    activity,
    alerts,
    devices,
    facility,
    operations,
    people,
    reference_data,
    rooms,
    services,
    stays,
    telemetry,
)

#: Steps in strict dependency order. A child step never runs before the step
#: that creates its parents.
STEPS = [
    ("1  reference / lookup data", reference_data.seed, False),
    ("2  organisation, facility, property hierarchy", facility.seed, True),
    ("3  departments, users, roles, permissions", people.seed, True),
    ("4  amenity types, packages, rooms", rooms.seed, True),
    ("5  stays, occupants, allocations, invoices", stays.seed, True),
    ("6  service catalogue, requests, maintenance", services.seed, True),
    ("7  firmware, devices, MQTT, commands", devices.seed, True),
    ("8  telemetry, health, energy, dashboard KPIs", telemetry.seed, True),
    ("9  alerts, incidents, value alerts", alerts.seed, True),
    ("10 activity feed and notification dispatch", activity.seed, True),
    ("11 job orders, keys, scheduler, marketing", operations.seed, True),
]

def run_seed(session: Session) -> "OrderedDict[str, int]":
    """Execute every step. Raises on the first failure; the caller rolls back."""
    ctx: dict = {}
    reported: OrderedDict[str, int] = OrderedDict()

    for label, step, needs_ctx in STEPS:
        print(f"  -> {label}")
        try:
            counts = step(session, ctx) if needs_ctx else step(session)
        except Exception as exc:  # noqa: BLE001 - re-raised after annotation
            raise RuntimeError(f"seed step failed: {label} :: {exc}") from exc
        for table, n in counts.items():
            reported[table] = reported.get(table, 0) + n
    return reported


def row_counts(session: Session) -> "OrderedDict[str, int]":
    counts: OrderedDict[str, int] = OrderedDict()
    for table in APPROVED_TABLES:
        counts[table] = session.execute(
            text(f'SELECT count(*) FROM public."{table}"')
        ).scalar_one()
    return counts


def schema_fingerprint(session: Session) -> dict[str, int]:
    q = lambda sql: session.execute(text(sql)).scalar_one()  # noqa: E731
    return {
        "tables": q(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name<>'alembic_version'"
        ),
        "enums": q(
            "SELECT count(*) FROM pg_type t JOIN pg_namespace n "
            "ON n.oid=t.typnamespace WHERE n.nspname='public' AND t.typtype='e'"
        ),
        "foreign_keys": q(
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE table_schema='public' AND constraint_type='FOREIGN KEY'"
        ),
        "indexes": q("SELECT count(*) FROM pg_indexes WHERE schemaname='public'"),
    }


def print_report(session: Session) -> None:
    counts = row_counts(session)
    seeded = {t: n for t, n in counts.items() if n}
    empty = [t for t, n in counts.items() if not n]

    print()
    print("=" * 52)
    print(f"{'table_name':<34}{'row_count':>10}")
    print("-" * 52)
    for table, n in counts.items():
        marker = " " if n else "."
        print(f"{marker}{table:<33}{n:>10}")
    print("-" * 52)
    print(f"{'TOTAL':<34}{sum(counts.values()):>10}")
    print("=" * 52)
    print(f"approved tables      : {len(counts)}")
    print(f"tables with rows     : {len(seeded)}")
    print(f"tables left empty    : {len(empty)}")
    if empty:
        print(f"empty                : {', '.join(empty)}")

    fp = schema_fingerprint(session)
    print()
    print("schema fingerprint   : "
          f"tables={fp['tables']} enums={fp['enums']} "
          f"fks={fp['foreign_keys']} indexes={fp['indexes']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the HMS demo dataset.")
    parser.add_argument(
        "--report",
        action="store_true",
        help="print the row-count report without inserting anything",
    )
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        if args.report:
            print_report(session)
            return 0

        before = schema_fingerprint(session)
        print("seeding HMS demo dataset ...")
        try:
            reported = run_seed(session)
            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            print(f"\nFAILED - transaction rolled back, no partial data written.\n{exc}",
                  file=sys.stderr)
            return 1

        print(f"\ncommitted {sum(reported.values())} demo records "
              f"across {len(reported)} tables")

        after = schema_fingerprint(session)
        if before != after:
            print(f"\nWARNING: schema fingerprint changed!\n"
                  f"  before={before}\n  after ={after}", file=sys.stderr)
            return 1

        print_report(session)
        return 0
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
