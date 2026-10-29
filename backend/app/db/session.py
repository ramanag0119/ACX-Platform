"""Database engine and session factories for OSS (PostgreSQL) and BSS (MySQL)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# --- OSS (PostgreSQL 18 - hms_db) Engine & Session ---
engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    echo=settings.DEBUG and settings.APP_ENV == "development",
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Backward-compatible aliases for OSS
oss_engine = engine
OssSessionLocal = SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Primary request-scoped session for PostgreSQL (OSS platform data)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_oss_db() -> Generator[Session, None, None]:
    """Explicitly named generator for OSS database sessions."""
    yield from get_db()


# --- BSS (MySQL 8.0 - hms_bss) Engine & Session (Lazy Initialization) ---
_bss_engine = None
_BssSessionLocal = None


def get_bss_engine():
    global _bss_engine, _BssSessionLocal
    if _bss_engine is None:
        _bss_engine = create_engine(
            settings.bss_sqlalchemy_url,
            pool_pre_ping=True,
            echo=settings.DEBUG and settings.APP_ENV == "development",
        )
        _BssSessionLocal = sessionmaker(bind=_bss_engine, autocommit=False, autoflush=False)
    return _bss_engine


def get_bss_db() -> Generator[Session, None, None]:
    """Request-scoped session for MySQL 8.0 (BSS commercial data)."""
    global _BssSessionLocal
    if _BssSessionLocal is None:
        get_bss_engine()
    db = _BssSessionLocal()
    try:
        yield db
    finally:
        db.close()

