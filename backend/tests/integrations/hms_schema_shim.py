"""TEST-ONLY: build the HMS schema on a DISPOSABLE MySQL database.

The repository cannot create its own schema on MySQL: several boolean columns
carry PostgreSQL-style server defaults ('true' / 'false'), which MySQL rejects
with error 1067 (pre-existing defect, see HTNG_FIAS_REPOSITORY_BASELINE.md §4).

This shim copies `Base.metadata` and rewrites ONLY those boolean defaults to
1 / 0 on the copy. The application models are not modified. Its sole purpose is
to let integration tests drive the REAL `app.services.stays_write` functions
against real tables. It must never be used against the HMS database.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, MetaData, text
from sqlalchemy.engine import Engine


def _is_json(col_type) -> bool:
    return isinstance(col_type, JSON) or isinstance(getattr(col_type, "impl", None), JSON)


#: Every rewrite the shim performs, as (table, object, issue). This list IS the
#: evidence of why the HMS schema cannot be bootstrapped on MySQL as-is.
REWRITES: list[tuple[str, str, str]] = []


def mysql_compatible_hms_metadata() -> MetaData:
    from app.models import Base

    REWRITES.clear()
    copy = MetaData(naming_convention=Base.metadata.naming_convention)
    for table in Base.metadata.sorted_tables:
        table.to_metadata(copy)
    for table in copy.tables.values():
        for column in table.columns:
            default = column.server_default
            if default is None:
                continue
            raw = str(getattr(default, "arg", "")).strip("'\"").lower()
            if isinstance(column.type, Boolean) and raw in ("true", "false"):
                column.server_default = type(default)(text("1" if raw == "true" else "0"))
                REWRITES.append((table.name, column.name, "1067: BOOL default 'true'/'false'"))
            elif _is_json(column.type) or column.type.__class__.__name__ in ("Text", "LargeBinary"):
                column.server_default = None
                REWRITES.append((table.name, column.name, "1101: literal default on JSON/TEXT/BLOB"))
        for index in list(table.indexes):
            if any(_is_json(c.type) for c in index.columns):
                table.indexes.discard(index)
                REWRITES.append((table.name, index.name or "?", "3152: index directly on JSON column"))
    return copy


def create_hms_schema(engine: Engine) -> MetaData:
    if engine.url.database in (None, "", "inspironics_app"):
        raise RuntimeError("refusing to build the HMS schema outside a disposable database")
    md = mysql_compatible_hms_metadata()
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for (name,) in conn.execute(text(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
        )).all():
            conn.execute(text(f"DROP TABLE `{name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    md.create_all(engine)
    return md
