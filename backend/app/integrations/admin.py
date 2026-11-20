"""Integration administration: clients, credentials, facility mappings.

Every change writes an `integration_audit_events` row IN THE SAME TRANSACTION,
so the audit trail cannot disagree with the data.

Lifecycle rules:
* Clients and mappings are created DISABLED and must be enabled explicitly.
* A secret is generated here, returned exactly once, and only its hash stored.
* Rotation keeps the previous secret valid for a bounded overlap window
  (0 .. MAX_OVERLAP) so the vendor can switch without an outage; it can be
  revoked early. Only one previous secret is kept.
* Mapping codes are normalised with the configured case policy (EXACT until
  HF-05 is decided).

Who may call these is decided by the caller: facility mappings are exposed on
the operator API (facility-scoped, write permission); client and credential
operations are CLI-only (`python -m app.integrations.cli`), never HTTP.
Storage of the issued secret on the vendor side is HF-22.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.core.envelope import Protocol, utcnow
from app.integrations.core.errors import (
    ErrorCategory,
    IntegrationError,
    NotFoundInScope,
    ValidationFailed,
)
from app.integrations.processing.sql_models import (
    AuditEventRow,
    FacilityMappingRow,
    IntegrationClientRow,
)
from app.integrations.security.clients import CLIENT_CODE_PATTERN, generate_secret, hash_secret
from app.integrations.security.facility import PROPERTY_CODE_PATTERN, CaseSensitivity, normalize_code

MAX_OVERLAP = timedelta(days=7)


class AdminConflict(IntegrationError):
    category = ErrorCategory.CONFLICT
    code = "conflict"


@dataclass(frozen=True)
class IssuedSecret:
    client_id: uuid.UUID
    client_code: str
    #: Shown ONCE. Never logged, never stored.
    secret: str
    previous_valid_until: datetime | None


@dataclass(frozen=True)
class MappingView:
    mapping_id: uuid.UUID
    client_code: str
    external_property_code: str
    facility_id: uuid.UUID
    enabled: bool

    def as_dict(self) -> dict:
        return {
            "mapping_id": str(self.mapping_id),
            "client_code": self.client_code,
            "external_property_code": self.external_property_code,
            "facility_id": str(self.facility_id),
            "enabled": self.enabled,
        }


def _protocols(values: list[str] | tuple[str, ...]) -> str:
    try:
        parsed = sorted({str(Protocol(v)) for v in values} - {str(Protocol.TEST)})
    except ValueError:
        raise ValidationFailed("Unknown protocol.", code="unknown_protocol") from None
    if not parsed:
        raise ValidationFailed("At least one protocol is required.", code="protocol_required")
    return ",".join(parsed)


class IntegrationAdmin:
    def __init__(
        self,
        engine: Engine,
        *,
        case_sensitivity: CaseSensitivity = CaseSensitivity.EXACT,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._engine = engine
        self._policy = case_sensitivity
        self._clock = clock

    @contextmanager
    def _tx(self) -> Iterator[Session]:
        with Session(self._engine, expire_on_commit=False) as s, s.begin():
            yield s

    def _audit(self, s: Session, action: str, actor: str, *, facility_id=None, reason=None, detail=None) -> None:
        s.add(AuditEventRow(
            occurred_on=self._clock(), actor_type="user", actor_id=str(actor)[:64], action=action,
            facility_id=facility_id, message_id=None, reason=reason, detail=detail or None,
        ))

    @staticmethod
    def _client(s: Session, code: str) -> IntegrationClientRow:
        row = s.execute(
            select(IntegrationClientRow).where(IntegrationClientRow.client_code == code).with_for_update()
        ).scalar_one_or_none()
        if row is None or row.client_code != code:
            raise NotFoundInScope("Integration client not found.")
        return row

    # ------------------------------------------------------------- clients
    def create_client(self, code: str, protocols: list[str], *, actor: str) -> IssuedSecret:
        if not CLIENT_CODE_PATTERN.fullmatch(code or ""):
            raise ValidationFailed("Client code is malformed.", code="client_code_malformed")
        secret = generate_secret()
        client_id = uuid.uuid4()
        try:
            with self._tx() as s:
                s.add(IntegrationClientRow(
                    id=client_id, client_code=code, secret_hash=hash_secret(secret),
                    enabled=False, protocols=_protocols(protocols),
                ))
                s.flush()
                self._audit(s, "client.created", actor, detail={"client_code": code, "protocols": protocols})
        except IntegrityError:
            raise AdminConflict("Client code already exists.") from None
        return IssuedSecret(client_id, code, secret, None)

    def set_client_enabled(self, code: str, enabled: bool, *, actor: str) -> None:
        with self._tx() as s:
            row = self._client(s, code)
            row.enabled = enabled
            self._audit(s, "client.enabled" if enabled else "client.disabled", actor, detail={"client_code": code})

    def rotate_secret(self, code: str, *, overlap: timedelta, actor: str) -> IssuedSecret:
        if not (timedelta(0) <= overlap <= MAX_OVERLAP):
            raise ValidationFailed("Rotation overlap must be between 0 and 7 days.", code="overlap_out_of_range")
        secret = generate_secret()
        now = self._clock()
        with self._tx() as s:
            row = self._client(s, code)
            until = now + overlap if overlap > timedelta(0) else None
            row.secondary_secret_hash = row.secret_hash if until else None
            row.secondary_expires_on = until
            row.secret_hash = hash_secret(secret)
            self._audit(s, "client.secret_rotated", actor,
                        detail={"client_code": code, "previous_valid_until": until.isoformat() if until else None})
            client_id = row.id
        return IssuedSecret(client_id, code, secret, until)

    def revoke_previous_secret(self, code: str, *, actor: str) -> None:
        with self._tx() as s:
            row = self._client(s, code)
            row.secondary_secret_hash = None
            row.secondary_expires_on = None
            self._audit(s, "client.previous_secret_revoked", actor, detail={"client_code": code})

    # ------------------------------------------------------------ mappings
    def create_mapping(
        self, client_code: str, external_code: str, facility_id: uuid.UUID, *,
        actor: str, facility_scope: set[uuid.UUID] | None,
    ) -> MappingView:
        if facility_scope is not None and facility_id not in facility_scope:
            raise NotFoundInScope("Facility not found.")
        if not PROPERTY_CODE_PATTERN.fullmatch(external_code or ""):
            raise ValidationFailed("Property code is malformed.", code="property_code_malformed")
        mapping_id = uuid.uuid4()
        try:
            with self._tx() as s:
                client = self._client(s, client_code)
                s.add(FacilityMappingRow(
                    id=mapping_id, client_id=client.id, external_property_code=external_code,
                    normalized_property_code=normalize_code(external_code, self._policy),
                    facility_id=facility_id, enabled=False, created_by=str(actor)[:64],
                ))
                s.flush()
                self._audit(s, "mapping.created", actor, facility_id=facility_id,
                            detail={"mapping_id": str(mapping_id), "client_code": client_code,
                                    "external_property_code": external_code})
        except IntegrityError as exc:
            errno = getattr(getattr(exc, "orig", None), "args", (None,))[0]
            if errno == 1452:
                raise ValidationFailed("Facility does not exist.", code="facility_unknown") from None
            raise AdminConflict("This property code is already mapped for the client.") from None
        return MappingView(mapping_id, client_code, external_code, facility_id, False)

    def set_mapping_enabled(
        self, mapping_id: uuid.UUID, enabled: bool, *, actor: str, reason: str | None,
        facility_scope: set[uuid.UUID] | None,
    ) -> MappingView:
        with self._tx() as s:
            row = s.execute(
                select(FacilityMappingRow, IntegrationClientRow.client_code)
                .join(IntegrationClientRow, IntegrationClientRow.id == FacilityMappingRow.client_id)
                .where(FacilityMappingRow.id == mapping_id).with_for_update()
            ).one_or_none()
            if row is None or (facility_scope is not None and row[0].facility_id not in facility_scope):
                raise NotFoundInScope("Mapping not found.")
            mapping, client_code = row
            mapping.enabled = enabled
            self._audit(s, "mapping.enabled" if enabled else "mapping.disabled", actor,
                        facility_id=mapping.facility_id, reason=reason,
                        detail={"mapping_id": str(mapping_id)})
            return MappingView(mapping.id, client_code, mapping.external_property_code,
                               mapping.facility_id, enabled)

    def auth_coverage(self, *, facility_scope: set[uuid.UUID] | None) -> dict[str, dict[str, int]]:
        """Read-only: per protocol, how many ENABLED clients hold at least one
        ENABLED mapping to a facility in scope, and how many such mappings.

        Only facility-scoped facts are returned -- no client codes, no secret
        material, nothing about clients mapped solely to other facilities."""
        out = {str(p): {"enabled_clients": 0, "enabled_mappings": 0} for p in (Protocol.HTNG, Protocol.FIAS)}
        if facility_scope is not None and not facility_scope:
            return out
        # Aggregated in SQL: one row per distinct `protocols` value (a handful),
        # however many clients or mappings exist.
        stmt = (
            select(
                IntegrationClientRow.protocols,
                func.count(func.distinct(IntegrationClientRow.id)),
                func.count(FacilityMappingRow.id),
            )
            .join(FacilityMappingRow, FacilityMappingRow.client_id == IntegrationClientRow.id)
            .where(IntegrationClientRow.enabled.is_(True), FacilityMappingRow.enabled.is_(True))
            .group_by(IntegrationClientRow.protocols)
        )
        if facility_scope is not None:
            stmt = stmt.where(FacilityMappingRow.facility_id.in_(list(facility_scope)))
        with self._tx() as s:
            for protocols, n_clients, n_mappings in s.execute(stmt).all():
                for p in (protocols or "").split(","):
                    if p in out:
                        out[p]["enabled_clients"] += int(n_clients)
                        out[p]["enabled_mappings"] += int(n_mappings)
        return out

    def list_mappings(self, *, facility_scope: set[uuid.UUID] | None) -> list[MappingView]:
        stmt = (
            select(FacilityMappingRow, IntegrationClientRow.client_code)
            .join(IntegrationClientRow, IntegrationClientRow.id == FacilityMappingRow.client_id)
            .order_by(IntegrationClientRow.client_code, FacilityMappingRow.external_property_code)
        )
        if facility_scope is not None:
            if not facility_scope:
                return []
            stmt = stmt.where(FacilityMappingRow.facility_id.in_(list(facility_scope)))
        with self._tx() as s:
            return [
                MappingView(m.id, code, m.external_property_code, m.facility_id, bool(m.enabled))
                for m, code in s.execute(stmt).all()
            ]
