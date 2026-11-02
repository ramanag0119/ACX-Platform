"""The OSS DB is externally owned: HMS may read it, never write it."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.session import get_db

requires_db = pytest.mark.skipif(
    not settings.is_db_configured, reason="OSS database not configured"
)


@requires_db
def test_sessions_are_read_only():
    db = next(get_db())
    try:
        assert db.execute(text("SHOW transaction_read_only")).scalar() == "on"
        # Even a session-local temp table is refused, so no write can reach OSS.
        with pytest.raises(DBAPIError):
            db.execute(text("CREATE TEMP TABLE _oss_write_probe (x int)"))
    finally:
        db.close()
