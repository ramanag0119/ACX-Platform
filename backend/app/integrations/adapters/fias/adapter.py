"""FIASAdapter -- FIAS records <-> canonical messages.

With `PRODUCTION_SPECIFICATION is None` (today) the adapter is BLOCKED:
`status()` reports HF-11 and `decode`/`encode` raise
`VendorSpecificationBlocked`. It becomes READY only when constructed with a
fully verified specification. A provisional specification is accepted only
with `allow_unverified=True` outside production (tests and the simulator).
"""

from __future__ import annotations

from app.core.config import settings as app_settings
from app.integrations.adapters.base import (
    AdapterReadiness,
    AdapterStatus,
    BaseProtocolAdapter,
    TransportContext,
)
from app.integrations.adapters.fias.codec import parse_record, serialize_record
from app.integrations.adapters.fias.spec import (
    BLOCKING_DECISION,
    PRODUCTION_SPECIFICATION,
    FiasSpecification,
)
from app.integrations.core.envelope import DecodedMessage, Direction, OutboundRequest, Protocol
from app.integrations.core.errors import (
    UnsupportedMessage,
    ValidationFailed,
    VendorSpecificationBlocked,
)


class FIASAdapter(BaseProtocolAdapter):
    protocol = Protocol.FIAS

    def __init__(
        self,
        specification: FiasSpecification | None = PRODUCTION_SPECIFICATION,
        *,
        allow_unverified: bool = False,
        app_env: str | None = None,
    ) -> None:
        env = app_env if app_env is not None else app_settings.APP_ENV
        if specification is not None and not specification.is_verified():
            if not allow_unverified:
                raise VendorSpecificationBlocked(
                    "FIAS specification contains unverified elements.", decision=BLOCKING_DECISION
                )
            if env == "production":
                raise VendorSpecificationBlocked(
                    "Unverified FIAS specifications cannot be used in production.",
                    decision=BLOCKING_DECISION,
                )
        self._spec = specification

    # ----------------------------------------------------------------- status
    def status(self) -> AdapterStatus:
        if self._spec is None:
            return AdapterStatus(
                protocol=self.protocol,
                readiness=AdapterReadiness.BLOCKED,
                specification=None,
                inbound_message_types=(),
                outbound_message_types=(),
                blocking_decisions=(BLOCKING_DECISION,),
            )
        return AdapterStatus(
            protocol=self.protocol,
            readiness=AdapterReadiness.READY if self._spec.is_verified() else AdapterReadiness.TEST_ONLY,
            specification=f"{self._spec.name} {self._spec.version}",
            inbound_message_types=tuple(sorted(self.message_types(Direction.INBOUND))),
            outbound_message_types=tuple(sorted(self.message_types(Direction.OUTBOUND))),
            blocking_decisions=() if self._spec.is_verified() else (BLOCKING_DECISION,),
        )

    def message_types(self, direction: Direction) -> frozenset[str]:
        if self._spec is None:
            return frozenset()
        return frozenset(r.message_type for r in self._spec.active_records() if direction in r.directions)

    def _require_spec(self) -> FiasSpecification:
        if self._spec is None:
            raise VendorSpecificationBlocked(
                "No verified FIAS specification is configured.", decision=BLOCKING_DECISION
            )
        return self._spec

    # ----------------------------------------------------------------- decode
    def decode(self, raw: bytes, context: TransportContext) -> DecodedMessage:
        spec = self._require_spec()
        record = parse_record(raw, spec)
        rec = record.spec

        body = {rec.field(fid).name: value for fid, value in record.fields.items()}

        property_code = record.fields.get(rec.property_field) if rec.property_field else None

        idempotency_key = None
        if rec.idempotency_fields:
            parts = [record.fields.get(fid, "") for fid in rec.idempotency_fields]
            if not all(parts):
                raise ValidationFailed(
                    "Fields forming the idempotency key are missing.",
                    code="idempotency_fields_missing",
                    detail={"record_id": rec.record_id, "field_ids": list(rec.idempotency_fields)},
                )
            idempotency_key = f"{rec.record_id}:" + ":".join(parts)

        return DecodedMessage(
            protocol=self.protocol,
            message_type=rec.message_type,
            schema_version=f"{spec.name}/{spec.version}",
            property_code=property_code,
            idempotency_key=idempotency_key,
            external_message_id=idempotency_key,
            body=body,
        )

    # ----------------------------------------------------------------- encode
    def encode(self, request: OutboundRequest) -> bytes:
        spec = self._require_spec()
        rec = spec.record_for_type(request.message_type, Direction.OUTBOUND)
        if rec is None or rec not in spec.active_records():
            raise UnsupportedMessage(
                "No outbound FIAS record is defined for this message type.",
                detail={"message_type": request.message_type},
            )
        values: dict[str, str] = {}
        for name, value in request.body.items():
            fs = rec.field_by_name(name)
            if fs is None:
                raise ValidationFailed(
                    "Body has a field the record does not define.",
                    code="unknown_body_field",
                    detail={"field": name},
                )
            if value is None:
                continue
            if not isinstance(value, str):
                raise ValidationFailed(
                    "FIAS field values must be text.", code="field_not_text", detail={"field": name}
                )
            values[fs.field_id] = value
        return serialize_record(rec, values, spec)
