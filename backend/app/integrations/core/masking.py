"""Masking of guest PII, credentials and other sensitive values.

Used for anything that leaves the processing path towards a human: logs,
operational API responses, audit detail. The rule is "mask by default": a key
is masked when its normalised name contains any sensitive fragment, and free
text is scrubbed for e-mail addresses and long digit runs (card numbers,
phone numbers, document numbers).

This is defence in depth. The framework's primary rule is that payload values
are never logged at all; logging calls carry identifiers only.
"""

from __future__ import annotations

import re
from typing import Any

MASK = "***"

#: Fragments matched against the key with case, `_` and `-` removed.
SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "name", "email", "mail", "phone", "mobile", "fax", "address", "street",
    "city", "zip", "postal", "dob", "birth", "passport", "document", "idnumber",
    "nationalid", "card", "pan", "cvv", "cvc", "expiry", "iban", "account",
    "password", "passwd", "secret", "token", "authorization", "apikey",
    "credential", "signature", "pin", "vip", "comment", "note", "remark",
)

#: Keys that look sensitive by fragment but are operational identifiers.
NON_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"messagetype", "roomname", "propertyname", "pinned", "spanid", "capacity"}
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_DIGITS = re.compile(r"\d[\d \-]{7,}\d")


def _norm(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "")


def is_sensitive_key(key: str) -> bool:
    k = _norm(key)
    if k in NON_SENSITIVE_KEYS:
        return False
    return any(fragment in k for fragment in SENSITIVE_KEY_FRAGMENTS)


def mask_text(text: str) -> str:
    text = _EMAIL.sub(MASK, text)
    return _DIGITS.sub(MASK, text)


def mask_mapping(value: Any, *, _depth: int = 0) -> Any:
    """Recursively mask a JSON-like structure. Never mutates the input."""
    if _depth > 32:
        return MASK
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and is_sensitive_key(key):
                out[key] = MASK if item not in (None, "") else item
            else:
                out[key] = mask_mapping(item, _depth=_depth + 1)
        return out
    if isinstance(value, list):
        return [mask_mapping(item, _depth=_depth + 1) for item in value]
    if isinstance(value, str):
        return mask_text(value)
    return value
