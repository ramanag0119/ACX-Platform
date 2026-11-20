"""MySQL-backed client and facility-mapping stores (candidate tables, HF-39)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.integrations.core.envelope import Protocol
from app.integrations.processing.sql_models import FacilityMappingRow, IntegrationClientRow
from app.integrations.security.clients import IntegrationClient
from app.integrations.security.facility import CaseSensitivity, FacilityMapping, normalize_code


def _protocols(raw: str) -> frozenset[Protocol] | None:
    out = set()
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        try:
            out.add(Protocol(part))
        except ValueError:
            return None  # misconfigured row: fail closed
    return frozenset(out)


class SqlClientStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_by_code(self, code: str) -> IntegrationClient | None:
        with Session(self._engine) as s:
            row = s.execute(
                select(IntegrationClientRow).where(IntegrationClientRow.client_code == code)
            ).scalar_one_or_none()
            # The default collation is case-insensitive; client codes are exact.
            if row is None or row.client_code != code:
                return None
            protocols = _protocols(row.protocols)
            return IntegrationClient(
                id=row.id,
                code=row.client_code,
                enabled=bool(row.enabled) and protocols is not None,
                protocols=protocols or frozenset(),
                secret_hash=row.secret_hash,
                secondary_secret_hash=row.secondary_secret_hash,
                secondary_expires_at=row.secondary_expires_on,
            )


class SqlFacilityMappingStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find(self, client_id: uuid.UUID, code: str, policy: CaseSensitivity) -> list[FacilityMapping]:
        wanted = normalize_code(code, policy)
        with Session(self._engine) as s:
            rows = s.execute(
                select(FacilityMappingRow).where(
                    FacilityMappingRow.client_id == client_id,
                    FacilityMappingRow.normalized_property_code == wanted,
                )
            ).scalars().all()
        return [
            FacilityMapping(
                client_id=r.client_id,
                external_property_code=r.external_property_code,
                facility_id=r.facility_id,
                enabled=bool(r.enabled),
            )
            for r in rows
            # Defence in depth against a non-binary collation on the column.
            if r.normalized_property_code == wanted
        ]

    def facilities_for_client(self, client_id: uuid.UUID) -> set[uuid.UUID]:
        with Session(self._engine) as s:
            return set(
                s.execute(
                    select(FacilityMappingRow.facility_id).where(
                        FacilityMappingRow.client_id == client_id, FacilityMappingRow.enabled.is_(True)
                    )
                ).scalars().all()
            )
