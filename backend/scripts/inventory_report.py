r"""Complete BSS database inventory report. READ-ONLY.

    .venv\Scripts\python.exe -m scripts.inventory_report            offline + live counts
    .venv\Scripts\python.exe -m scripts.inventory_report --offline  structure only

Writes `backend/docs/BSS_INVENTORY_REPORT.md`.

For every table: name, exact row count, column count, primary key, and outbound
foreign keys -- grouped by functional module.

WHY TWO MODES. Structure (tables, columns, PKs, FKs, modules) comes from the
SQLAlchemy models, so the report can be produced with no database at all. Only
the row counts need a live connection; without one they are reported as
"unavailable" rather than guessed, and the report says so at the top.

NOTHING IS MODIFIED. The session is opened READ ONLY, every statement is a
SELECT against `information_schema` or a `COUNT(*)`, and the connection is
never committed. No INSERT/UPDATE/DELETE/DDL is issued anywhere in this file.
"""

from __future__ import annotations

import argparse
import collections
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.db.base import Base
from app.models import APPROVED_TABLES

OUT = Path(__file__).resolve().parents[1] / "docs" / "BSS_INVENTORY_REPORT.md"

#: model module -> functional module, following the blueprint's table groups.
MODULE_LABEL = {
    "facility": "A. Organisation, Facility & Identity",
    "amenity": "B. Rooms, Amenities & Packages",
    "stay": "C. Guests, Stays & Billing",
    "service": "D. Service Requests & Catalogue",
    "job_order": "E. Job Orders & Workforce",
    "maintenance": "F. Maintenance",
    "device": "G. Devices, Telemetry & IoT",
    "alert": "H. Alerts & Incidents",
    "access": "I. Access Control & Digital Keys",
    "marketing": "J. Marketing, Offers & Holidays",
    "people": "K. People, Roles & Permissions",
    "activity": "L. Activity & Audit",
    "scheduler": "M. Scheduling & Tasks",
    "reporting": "N. Reporting & Analytics",
}
UNCLASSIFIED = "Z. Unclassified"


def table_owner() -> dict[str, str]:
    """table name -> the model module that declares it."""
    owner: dict[str, str] = {}
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        owner.setdefault(cls.__tablename__, cls.__module__.rsplit(".", 1)[-1])
    return owner


def live_row_counts() -> tuple[dict[str, int] | None, str]:
    """Exact COUNT(*) per table, or (None, reason) when the DB is unreachable."""
    try:
        from sqlalchemy import create_engine, text

        from app.core.config import settings
        from app.db.session import CONNECT_ARGS

        engine = create_engine(
            settings.sqlalchemy_url, connect_args=CONNECT_ARGS, echo=False
        )
        counts: dict[str, int] = {}
        with engine.connect() as conn:
            # Belt and braces: the server itself refuses writes on this session.
            conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
            names = [
                r[0] for r in conn.execute(text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
                ))
            ]
            for name in names:
                counts[name] = conn.execute(
                    text(f"SELECT COUNT(*) FROM `{name}`")
                ).scalar_one()
        return counts, ""
    except Exception as exc:  # unreachable DB, vault error, anything
        return None, f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="skip the database entirely; structure only")
    args = parser.parse_args()

    counts, reason = (None, "skipped (--offline)") if args.offline else live_row_counts()

    owner = table_owner()
    approved = set(APPROVED_TABLES)
    groups: dict[str, list] = collections.defaultdict(list)

    for name, table in sorted(Base.metadata.tables.items()):
        module = MODULE_LABEL.get(owner.get(name, ""), UNCLASSIFIED)
        groups[module].append({
            "name": name,
            "columns": len(table.columns),
            "pk": [c.name for c in table.primary_key.columns],
            "fks": [
                f"`{fk.parent.name}` -> `{fk.column.table.name}.{fk.column.name}`"
                for fk in sorted(table.foreign_keys, key=lambda f: f.parent.name)
            ],
            "approved": name in approved,
            "rows": None if counts is None else counts.get(name),
        })

    total_tables = sum(len(v) for v in groups.values())
    total_cols = sum(t["columns"] for v in groups.values() for t in v)
    total_fks = sum(len(t["fks"]) for v in groups.values() for t in v)

    L: list[str] = []
    L.append("# BSS Database Inventory Report")
    L.append("")
    L.append(f"**Database:** `inspironics_app` (MySQL) &nbsp;|&nbsp; "
             f"**Generated:** {datetime.now(UTC):%Y-%m-%d %H:%M UTC}")
    L.append("")
    L.append("> **READ-ONLY.** Nothing was modified, deleted, truncated or migrated. "
             "Structure is derived from the SQLAlchemy models; row counts come from "
             "`COUNT(*)` on a session opened `READ ONLY`.")
    L.append("")
    if counts is None:
        L.append(f"> **Row counts unavailable** — {reason}. Every other field is exact. "
                 "Re-run without `--offline` once the database is reachable.")
        L.append("")

    L.append("## Summary")
    L.append("")
    L.append(f"- **Total tables:** {total_tables}")
    L.append(f"- **Total columns:** {total_cols}")
    L.append(f"- **Total foreign key relationships:** {total_fks}")
    if counts is not None:
        L.append(f"- **Total rows:** {sum(counts.values()):,} "
                 f"across {sum(1 for v in counts.values() if v):,} non-empty tables")
    L.append("")
    L.append("### Tables per functional module")
    L.append("")
    for module in sorted(groups):
        n = len(groups[module])
        rows = ""
        if counts is not None:
            tot = sum(t["rows"] or 0 for t in groups[module])
            rows = f" — {tot:,} rows"
        L.append(f"- **{module}** — {n} tables{rows}")
    L.append("")

    for module in sorted(groups):
        L.append(f"## {module}")
        L.append("")
        for t in groups[module]:
            flag = "" if t["approved"] else "  ⚠️ *not in APPROVED_TABLES*"
            L.append(f"### `{t['name']}`{flag}")
            L.append("")
            rows = "unavailable" if t["rows"] is None else f"{t['rows']:,}"
            L.append(f"- **Rows:** {rows}")
            L.append(f"- **Columns:** {t['columns']}")
            L.append(f"- **Primary key:** "
                     f"{', '.join(f'`{c}`' for c in t['pk']) if t['pk'] else '*(none)*'}")
            if t["fks"]:
                L.append(f"- **Foreign keys ({len(t['fks'])}):**")
                for fk in t["fks"]:
                    L.append(f"  - {fk}")
            else:
                L.append("- **Foreign keys:** *none*")
            L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"  tables {total_tables}   columns {total_cols}   FKs {total_fks}")
    print(f"  row counts: {'live' if counts is not None else 'UNAVAILABLE -- ' + reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
