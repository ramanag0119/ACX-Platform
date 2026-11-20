"""Specification-driven FIAS record parser and serializer.

Both are pure functions of (bytes | fields, FiasSpecification). Error
messages name record ids and field ids only -- never field VALUES, which can be
guest names, room numbers or card data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.integrations.adapters.fias.spec import FiasSpecification, RecordSpec, VerificationStatus
from app.integrations.core.envelope import Direction
from app.integrations.core.errors import ProtocolError, UnsupportedMessage, ValidationFailed


@dataclass(frozen=True)
class ParsedRecord:
    record_id: str
    spec: RecordSpec
    #: field_id -> value
    fields: dict[str, str] = field(repr=False)


def parse_record(payload: bytes, spec: FiasSpecification) -> ParsedRecord:
    g = spec.grammar
    if not payload:
        raise ValidationFailed("Record is empty.", code="empty_record")
    try:
        text = payload.decode(g.encoding, errors="strict")
    except UnicodeDecodeError:
        raise ProtocolError("Record is not valid for the configured encoding.", code="bad_encoding") from None
    if any(ord(ch) < 0x20 for ch in text):
        raise ProtocolError("Record contains control characters.", code="control_characters")

    sep = g.field_separator.decode(g.encoding)
    if len(text) < g.record_id_length:
        raise ProtocolError("Record is shorter than a record id.", code="record_too_short")
    record_id = text[: g.record_id_length]
    rest = text[g.record_id_length :]

    rec = spec.record(record_id)
    if rec is None or rec.status in (VerificationStatus.UNSUPPORTED, VerificationStatus.REJECTED):
        raise UnsupportedMessage("Record type is not supported.", detail={"record_id": _safe_id(record_id)})
    if Direction.INBOUND not in rec.directions:
        raise UnsupportedMessage(
            "Record type is not accepted inbound.", detail={"record_id": record_id}
        )

    if rest:
        if g.separator_after_record_id:
            if not rest.startswith(sep):
                raise ProtocolError("Missing separator after record id.", code="missing_separator")
            rest = rest[len(sep) :]
        if g.trailing_separator and rest.endswith(sep):
            rest = rest[: -len(sep)]
    tokens = rest.split(sep) if rest else []

    values: dict[str, str] = {}
    for token in tokens:
        if len(token) < g.field_id_length:
            raise ProtocolError("Field token is shorter than a field id.", code="bad_field_token")
        fid, value = token[: g.field_id_length], token[g.field_id_length :]
        if fid in values:
            raise ProtocolError("Duplicate field id.", code="duplicate_field", detail={"field_id": fid})
        fs = rec.field(fid)
        if fs is None:
            if rec.unknown_fields == "reject":
                raise ValidationFailed(
                    "Unknown field for this record.", code="unknown_field", detail={"field_id": _safe_id(fid)}
                )
            continue
        _validate_value(rec, fs.field_id, value)
        values[fid] = value

    missing = [f.field_id for f in rec.fields if f.mandatory and not values.get(f.field_id)]
    if missing:
        raise ValidationFailed(
            "Mandatory fields are missing.",
            code="missing_mandatory_fields",
            detail={"record_id": record_id, "field_ids": missing},
        )
    return ParsedRecord(record_id=record_id, spec=rec, fields=values)


def _validate_value(rec: RecordSpec, field_id: str, value: str) -> None:
    fs = rec.field(field_id)
    assert fs is not None
    if len(value) > fs.max_length:
        raise ValidationFailed(
            "Field value is too long.", code="field_too_long",
            detail={"record_id": rec.record_id, "field_id": field_id},
        )
    if fs.pattern is not None and value and not re.fullmatch(fs.pattern, value):
        raise ValidationFailed(
            "Field value has an invalid format.", code="field_invalid_format",
            detail={"record_id": rec.record_id, "field_id": field_id},
        )


def _safe_id(value: str) -> str:
    """Record/field ids are echoed in errors; keep them short and printable."""
    return "".join(ch if 0x21 <= ord(ch) <= 0x7E else "?" for ch in value[:8])


def serialize_record(rec: RecordSpec, values: dict[str, str], spec: FiasSpecification) -> bytes:
    """field_id -> value  =>  record bytes, per the grammar."""
    if Direction.OUTBOUND not in rec.directions:
        raise UnsupportedMessage("Record type is not sent outbound.", detail={"record_id": rec.record_id})
    g = spec.grammar
    sep = g.field_separator.decode(g.encoding)
    for fid in values:
        if rec.field(fid) is None:
            raise ValidationFailed("Unknown field for this record.", code="unknown_field", detail={"field_id": fid})
    missing = [f.field_id for f in rec.fields if f.mandatory and not values.get(f.field_id)]
    if missing:
        raise ValidationFailed(
            "Mandatory fields are missing.", code="missing_mandatory_fields",
            detail={"record_id": rec.record_id, "field_ids": missing},
        )
    parts: list[str] = []
    for f in rec.fields:  # declaration order; deterministic output
        if f.field_id not in values or values[f.field_id] == "":
            continue
        value = values[f.field_id]
        if not isinstance(value, str):
            raise ValidationFailed("Field values must be text.", code="field_not_text", detail={"field_id": f.field_id})
        if sep in value or any(ord(ch) < 0x20 for ch in value):
            raise ValidationFailed(
                "Field value contains a separator or control character.",
                code="field_contains_separator", detail={"field_id": f.field_id},
            )
        _validate_value(rec, f.field_id, value)
        parts.append(f.field_id + value)

    text = rec.record_id
    if parts:
        if g.separator_after_record_id:
            text += sep
        text += sep.join(parts)
        if g.trailing_separator:
            text += sep
    try:
        return text.encode(g.encoding, errors="strict")
    except UnicodeEncodeError:
        raise ValidationFailed("Value cannot be encoded for this link.", code="unencodable") from None
