"""FIAS specification as DATA, with an explicit verification status per item.

Nothing about FIAS is hard-coded in the parser or serializer. The record
grammar (encoding, record-id length, field separator, field-id length) and
every record definition (record id, fields, mandatory flags, canonical
mapping) are supplied in a `FiasSpecification`, and each carries a
`VerificationStatus` plus the document it came from.

PRODUCTION_SPECIFICATION is None. No official FIAS manual, vendor record list
or approved fixture exists in the repository (decision HF-11; see
docs/HTNG_FIAS_FIAS_PROTOCOL_SUPPORT.md), so the production FIAS adapter is
BLOCKED and refuses every message. When the manual is supplied, its grammar
and records are entered here with status VERIFIED_OFFICIAL and a `source`
citing the document section.

`FiasSpecification.require_verified()` refuses any specification containing a
non-verified element. Provisional specifications are accepted only by
`FIASAdapter(..., allow_unverified=True)`, which itself refuses to run when
APP_ENV is "production".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from app.integrations.core.envelope import Direction, is_valid_message_type


class VerificationStatus(StrEnum):
    VERIFIED_OFFICIAL = "verified_official"
    VERIFIED_VENDOR_EXAMPLE = "verified_vendor_example"
    PROVISIONAL_TEST = "provisional_test"
    UNSUPPORTED = "unsupported"
    REJECTED = "rejected"


VERIFIED = frozenset({VerificationStatus.VERIFIED_OFFICIAL, VerificationStatus.VERIFIED_VENDOR_EXAMPLE})


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    #: Canonical body key the value maps to.
    name: str
    mandatory: bool = False
    max_length: int = 256
    pattern: str | None = None

    def __post_init__(self) -> None:
        if not self.field_id or not self.name:
            raise ValueError("field_id and name are required")
        if self.max_length < 1:
            raise ValueError("max_length must be positive")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"invalid pattern for field {self.field_id!r}") from exc


@dataclass(frozen=True)
class RecordSpec:
    record_id: str
    message_type: str
    directions: frozenset[Direction]
    fields: tuple[FieldSpec, ...]
    status: VerificationStatus
    source: str
    #: Field ids whose values, joined, form the idempotency key. Empty means
    #: the record carries no verified unique identifier.
    idempotency_fields: tuple[str, ...] = ()
    #: Field id carrying the external property code, if the record has one.
    property_field: str | None = None
    #: "reject" (default) or "ignore" fields not listed in `fields`.
    unknown_fields: str = "reject"

    def __post_init__(self) -> None:
        if not is_valid_message_type(self.message_type):
            raise ValueError(f"invalid canonical message type {self.message_type!r}")
        ids = [f.field_id for f in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate field id in record spec")
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("duplicate canonical name in record spec")
        known = set(ids)
        for fid in self.idempotency_fields:
            if fid not in known:
                raise ValueError(f"idempotency field {fid!r} is not a declared field")
        if self.property_field is not None and self.property_field not in known:
            raise ValueError("property_field is not a declared field")
        if self.unknown_fields not in ("reject", "ignore"):
            raise ValueError("unknown_fields must be 'reject' or 'ignore'")
        if not self.directions:
            raise ValueError("a record needs at least one direction")

    def field(self, field_id: str) -> FieldSpec | None:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        return None

    def field_by_name(self, name: str) -> FieldSpec | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


@dataclass(frozen=True)
class WireGrammar:
    encoding: str
    record_id_length: int
    field_separator: bytes
    field_id_length: int
    status: VerificationStatus
    source: str
    #: Whether a separator directly after the record id / at the end is part
    #: of the grammar. Supplied by the specification, never assumed.
    separator_after_record_id: bool = True
    trailing_separator: bool = True

    def __post_init__(self) -> None:
        "".encode(self.encoding)  # LookupError for unknown codecs
        # Framing and field splitting work on BYTES (transport/framing.py,
        # adapters/fias/codec.py). That is only sound for ASCII-compatible
        # encodings, where every ASCII character is the same single byte.
        # This is a constraint of our framer, not a FIAS rule (sprint gap G4).
        if any(chr(b).encode(self.encoding, errors="strict") != bytes([b]) for b in range(0x20, 0x7F)):
            raise ValueError(f"encoding {self.encoding!r} is not ASCII-compatible; byte-level framing would be unsound")
        try:
            if self.field_separator.decode(self.encoding).encode(self.encoding) != self.field_separator:
                raise ValueError("field_separator does not round-trip in the declared encoding")
        except UnicodeDecodeError:
            raise ValueError("field_separator is not valid in the declared encoding") from None
        if self.record_id_length < 1 or self.field_id_length < 1:
            raise ValueError("record_id_length and field_id_length must be positive")
        if not self.field_separator:
            raise ValueError("field_separator is required")


@dataclass(frozen=True)
class FiasSpecification:
    name: str
    version: str
    grammar: WireGrammar
    records: tuple[RecordSpec, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ids = [r.record_id for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate record id")
        for rec in self.records:
            if len(rec.record_id) != self.grammar.record_id_length:
                raise ValueError(f"record id {rec.record_id!r} does not match record_id_length")
            for f in rec.fields:
                if len(f.field_id) != self.grammar.field_id_length:
                    raise ValueError(f"field id {f.field_id!r} does not match field_id_length")

    def record(self, record_id: str) -> RecordSpec | None:
        for rec in self.records:
            if rec.record_id == record_id:
                return rec
        return None

    def record_for_type(self, message_type: str, direction: Direction) -> RecordSpec | None:
        for rec in self.records:
            if rec.message_type == message_type and direction in rec.directions:
                return rec
        return None

    def unverified_elements(self) -> list[str]:
        out = []
        if self.grammar.status not in VERIFIED:
            out.append(f"grammar:{self.grammar.status}")
        out.extend(f"record:{r.record_id}:{r.status}" for r in self.records if r.status not in VERIFIED)
        return out

    def is_verified(self) -> bool:
        return not self.unverified_elements()

    def active_records(self) -> tuple[RecordSpec, ...]:
        """Records usable for processing (UNSUPPORTED / REJECTED are excluded)."""
        return tuple(
            r for r in self.records
            if r.status not in (VerificationStatus.UNSUPPORTED, VerificationStatus.REJECTED)
        )


#: No verified FIAS specification exists in the repository. See module docstring.
PRODUCTION_SPECIFICATION: FiasSpecification | None = None

#: Decision that blocks verified FIAS behaviour.
BLOCKING_DECISION = "HF-11"
