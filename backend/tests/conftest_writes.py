"""Fixtures for the Phase 3.0 write tests.

Every write test creates its own rows and removes them again, so the 1,792
seeded records are exactly as many after the suite as before. Nothing seeded is
mutated except where a test explicitly restores the original value.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(scope="module")
def db() -> Iterator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def api(admin_headers) -> Iterator[TestClient]:
    """Administrator client: holds every module grant."""
    with TestClient(app, headers=admin_headers) as client:
        yield client


@pytest.fixture(scope="module")
def manager_api(manager_headers) -> Iterator[TestClient]:
    """Duty Manager client: 13 grants, no user_roles / facility_management."""
    with TestClient(app, headers=manager_headers) as client:
        yield client


@pytest.fixture(scope="module")
def anon_api() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module", autouse=True)
def require_seeded(db):
    if not db.execute(text("SELECT count(*) FROM amenity")).scalar_one():
        pytest.skip("database is not seeded; run `python -m seeds.run_seed`")


@pytest.fixture
def unique() -> str:
    """A short suffix so parallel or repeated runs cannot collide."""
    return uuid.uuid4().hex[:8]


class Cleanup:
    """Deletes rows a test created.

    Statements run in REGISTRATION order, so a test registers the most
    dependent row first (the link table, then the parent) and foreign keys are
    never violated on the way out.
    """

    def __init__(self) -> None:
        self._statements: list[tuple[str, dict]] = []

    def add(self, table: str, row_id, column: str = "id") -> None:
        self._statements.append(
            (f"DELETE FROM {table} WHERE {column} = :value", {"value": row_id})
        )

    def sql(self, statement: str, params: dict | None = None) -> None:
        self._statements.append((statement, params or {}))

    def run(self) -> None:
        """Best-effort teardown.

        Each statement commits on its own, and the list is retried once, so an
        ordering surprise (a row that gained a dependent mid-test) cannot leave
        everything after it behind. Anything still undeletable is reported
        loudly rather than silently inflating the row count.
        """
        remaining = list(self._statements)
        for _attempt in range(2):
            failed: list[tuple[str, dict]] = []
            for statement, params in remaining:
                session = SessionLocal()
                try:
                    session.execute(text(statement), params)
                    session.commit()
                except Exception:  # noqa: BLE001 -- retried, then reported
                    session.rollback()
                    failed.append((statement, params))
                finally:
                    session.close()
            remaining = failed
            if not remaining:
                return
        for statement, params in remaining:
            print(f"WARNING: test cleanup failed: {statement} {params}")


@pytest.fixture
def cleanup() -> Iterator[Cleanup]:
    tracker = Cleanup()
    try:
        yield tracker
    finally:
        tracker.run()


# --- Handles on seeded reference data --------------------------------------


@pytest.fixture(scope="module")
def facility_id(db):
    return db.execute(text("SELECT id FROM facility LIMIT 1")).scalar_one()


@pytest.fixture(scope="module")
def guest_id(db):
    return db.execute(
        text("SELECT id FROM app_user WHERE is_staff = 0 ORDER BY first_name LIMIT 1")
    ).scalar_one()


@pytest.fixture(scope="module")
def staff_id(db):
    return db.execute(
        text("SELECT id FROM app_user WHERE is_staff = 1 ORDER BY first_name LIMIT 1")
    ).scalar_one()


@pytest.fixture
def free_room(db):
    """A room no live stay holds, so allocation tests start from a clean slate."""
    return db.execute(
        text(
            """
            SELECT a.id
            FROM amenity a
            JOIN amenity_type t ON t.id = a.amenity_type_id
            WHERE t.amenity_category = 'room'
              AND NOT EXISTS (
                  SELECT 1 FROM room_allocation ra
                  JOIN stay s ON s.id = ra.stay_id
                  WHERE ra.room_id = a.id
                    AND s.status IN ('pending','active','checkout pending',
                                     'checkout accepted','checkout rejected')
              )
            ORDER BY a.name
            LIMIT 1
            """
        )
    ).scalar_one()


@pytest.fixture
def second_free_room(db, free_room):
    return db.execute(
        text(
            """
            SELECT a.id
            FROM amenity a
            JOIN amenity_type t ON t.id = a.amenity_type_id
            WHERE t.amenity_category = 'room'
              AND a.id <> :taken
              AND NOT EXISTS (
                  SELECT 1 FROM room_allocation ra
                  JOIN stay s ON s.id = ra.stay_id
                  WHERE ra.room_id = a.id
                    AND s.status IN ('pending','active','checkout pending',
                                     'checkout accepted','checkout rejected')
              )
            ORDER BY a.name
            LIMIT 1
            """
        ),
        {"taken": free_room},
    ).scalar_one()
