"""READ-ONLY OSS schema discovery (plan step 1).

Introspects the OSS database and prints every table with its columns, primary
keys and foreign keys, so the OSS->contract mapping can be written before any
adapter is implemented. It issues ONLY catalog SELECTs (via SQLAlchemy
reflection) -- it never writes, and it never prints the connection password.

PRE-CONDITION: the DB owner has authorised access and `OSS_DATABASE_URL` is set
in oss-service/.env (or the environment).

Run (from oss-service/):
    PYTHONPATH=. python tools/discover_schema.py              # human-readable
    PYTHONPATH=. python tools/discover_schema.py --json > schema.json

Next: fill tools/SCHEMA_MAPPING_TEMPLATE.md from the output, then implement the
adapters in app/adapters/* against the reflected tables.
"""

from __future__ import annotations

import json
import sys

from sqlalchemy import inspect

from app.core.config import settings
from app.models.reflect import _engine  # read-only engine builder


def main() -> int:
    if settings.oss_database_url is None:
        print(
            "OSS_DATABASE_URL is not set. Put the OSS connection in "
            "oss-service/.env first (never commit it).",
            file=sys.stderr,
        )
        return 2

    insp = inspect(_engine())
    as_json = "--json" in sys.argv[1:]
    schema: dict[str, dict] = {}

    for table in sorted(insp.get_table_names()):
        cols = [
            {
                "name": c["name"],
                "type": str(c["type"]),
                "nullable": c.get("nullable"),
            }
            for c in insp.get_columns(table)
        ]
        pk = insp.get_pk_constraint(table).get("constrained_columns", [])
        fks = [
            {
                "columns": fk.get("constrained_columns"),
                "refers_to": f"{fk.get('referred_table')}({fk.get('referred_columns')})",
            }
            for fk in insp.get_foreign_keys(table)
        ]
        schema[table] = {"columns": cols, "primary_key": pk, "foreign_keys": fks}

    if as_json:
        print(json.dumps(schema, indent=2, default=str))
    else:
        for table, meta in schema.items():
            print(f"\n== {table}  (pk: {', '.join(meta['primary_key']) or '-'})")
            for c in meta["columns"]:
                null = "" if c["nullable"] else " NOT NULL"
                print(f"   {c['name']:<32} {c['type']}{null}")
            for fk in meta["foreign_keys"]:
                print(f"   FK {fk['columns']} -> {fk['refers_to']}")
        print(f"\n{len(schema)} tables discovered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
