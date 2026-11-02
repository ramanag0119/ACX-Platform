"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

#: Timestamps are stored in UTC; pin the MySQL session clock to match so
#: CURRENT_TIMESTAMP defaults agree with the values the app writes.
#:
#: TLS is folded in from `settings.mysql_ssl_args` because the BSS server runs
#: `require_secure_transport=ON`. `migrations/env.py` imports this same dict,
#: so Alembic connects with identical transport settings -- there is no second
#: place where TLS could drift out of sync.
CONNECT_ARGS: dict = {
    "init_command": "SET time_zone = '+00:00'",
    **settings.mysql_ssl_args,
}

engine = create_engine(
    settings.sqlalchemy_url,
    connect_args=CONNECT_ARGS,
    # MySQL's default REPEATABLE READ would pin each session to its first
    # snapshot, so it would not see rows other requests committed.
    isolation_level="READ COMMITTED",
    pool_pre_ping=True,
    echo=settings.DEBUG and settings.APP_ENV == "development",
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
