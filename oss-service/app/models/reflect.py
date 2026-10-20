"""Reflection helper for the (externally-owned, differently-shaped) OSS schema.

The OSS database is NOT managed by this service and its schema differs from the
HMS device tables, so models are not hand-written up front. Step 1 of the plan
is a read-only discovery pass: reflect the live OSS schema and record a mapping
(OSS table/column -> HMS contract field) that the adapters then implement.

`reflect_oss_metadata()` and `automap_oss()` are the discovery tools. They do
nothing until `OSS_DATABASE_URL` is configured; they never write.

Discovery usage (once authorised + OSS_DATABASE_URL set), read-only:

    from app.models.reflect import reflect_oss_metadata
    md = reflect_oss_metadata()
    for t in sorted(md.tables):
        print(t, [c.name for c in md.tables[t].columns])
"""

from __future__ import annotations

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.db.session import OssDbNotConfigured


def _engine() -> Engine:
    url = settings.oss_database_url
    if url is None:
        raise OssDbNotConfigured("OSS_DATABASE_URL is not set; cannot reflect the OSS schema.")
    # Read-only use: reflection issues only SELECTs against the catalog.
    return create_engine(url, pool_pre_ping=True)


def reflect_oss_metadata() -> MetaData:
    """Reflect every table in the OSS database (read-only)."""
    md = MetaData()
    md.reflect(bind=_engine())
    return md


def automap_oss():
    """Return an automap base whose classes mirror the reflected OSS tables.

    Requires primary keys on the reflected tables. Used to build adapters once
    the mapping doc from discovery exists.
    """
    from sqlalchemy.ext.automap import automap_base

    base = automap_base()
    base.prepare(autoload_with=_engine())
    return base
