"""Engine and session factory for the OSS PostgreSQL.

The engine is built lazily: it is created on first use, not at import, so the
service can start and serve /health even when `OSS_DATABASE_URL` is not set yet
(the scaffold state, before the real OSS database is wired in).

`OssDbNotConfigured` is raised when a data route is reached without a configured
database; the API layer maps it to a clear 503 rather than a 500.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


class OssDbNotConfigured(RuntimeError):
    """The OSS database URL has not been provided (OSS_DATABASE_URL unset)."""


_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _ensure_engine() -> sessionmaker:
    global _engine, _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal
    url = settings.oss_database_url
    if url is None:
        raise OssDbNotConfigured(
            "OSS_DATABASE_URL is not set. Put the OSS database connection in "
            "oss-service/.env before using the data routes."
        )
    _engine = create_engine(
        url,
        # The OSS DB is externally owned and strictly read-only for HMS: every
        # session starts read-only, so PostgreSQL itself rejects any write.
        connect_args={"options": "-c default_transaction_read_only=on"},
        pool_pre_ping=True,
        echo=settings.DEBUG and settings.APP_ENV == "development",
    )
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session_factory = _ensure_engine()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
