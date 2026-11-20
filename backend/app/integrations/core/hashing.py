"""Deterministic canonical JSON and payload hashing.

Idempotency compares hashes, so the same logical payload must ALWAYS produce
the same bytes. Two things break that if left alone:

* dict ordering -- `{"a":1,"b":2}` and `{"b":2,"a":1}` serialise differently;
* MySQL's JSON type -- it re-orders object keys (by length, then bytes) and may
  re-format numbers when the document is read back.

So: the hash is computed ONCE, here, from canonical bytes (sorted keys, no
insignificant whitespace, UTF-8, no NaN/Infinity), and the persistence layer
stores those exact canonical bytes as TEXT -- never as a MySQL JSON column -- so
a stored body re-hashes to the same value. A hash is never re-derived from a
document that went through MySQL JSON.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any


class CanonicalizationError(ValueError):
    """The value cannot be represented deterministically."""


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError("NaN/Infinity cannot be hashed deterministically.")
        return value
    if isinstance(value, Decimal):
        # Decimal('1.10') and Decimal('1.1') are different source values; keep
        # the exact text rather than converting through float.
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise CanonicalizationError("Naive datetimes are ambiguous; use timezone-aware values.")
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("Object keys must be strings.")
            out[key] = _normalize(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    raise CanonicalizationError(f"Unsupported type for canonical JSON: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_hash(body: Any) -> str:
    return sha256_hex(canonical_json(body))


def idempotency_fingerprint(message_type: str, body: Any) -> str:
    """What "the same message" means for idempotency: same type AND same body."""
    return payload_hash({"message_type": message_type, "body": body})
