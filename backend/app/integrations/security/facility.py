"""External property code -> HMS facility, scoped to the authenticated client.

Rules (see docs/HTNG_FIAS_FACILITY_MAPPING.md):

* A mapping belongs to ONE integration client. The same external code may map
  to different facilities for different clients; codes are never assumed to
  be globally unique.
* Missing, ambiguous and disabled mappings are all rejected.
* Case sensitivity is decision HF-05 (pending). Until it is approved the
  resolver compares codes EXACTLY. `CaseSensitivity.INSENSITIVE` exists so the
  approved answer can be switched on in configuration, but it is not the default.
* A facility id that appears INSIDE a payload is never trusted. If a payload
  carries facility or property identifiers anywhere (at any nesting depth),
  they must agree with the resolved facility / property code, or the message
  is rejected (scope smuggling).
"""

from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing import Protocol as TypingProtocol

from app.integrations.core.errors import FacilityAuthorizationError, ValidationFailed
from app.integrations.security.clients import AuthenticatedClient

PROPERTY_CODE_PATTERN = re.compile(r"^[\x21-\x7e]{1,32}$")  # printable ASCII, no spaces

#: Normalised payload keys that carry a facility identifier.
FACILITY_ID_KEYS = frozenset({"facilityid", "facilityuuid", "hmsfacilityid"})
#: Normalised payload keys that carry an external property code.
PROPERTY_CODE_KEYS = frozenset({"propertycode", "hotelcode", "externalpropertycode"})


class CaseSensitivity(StrEnum):
    EXACT = "exact"
    INSENSITIVE = "insensitive"


def normalize_code(code: str, policy: CaseSensitivity) -> str:
    return code if policy is CaseSensitivity.EXACT else code.casefold()


@dataclass(frozen=True)
class FacilityMapping:
    client_id: uuid.UUID
    external_property_code: str
    facility_id: uuid.UUID
    enabled: bool = True


class FacilityMappingStore(TypingProtocol):
    def find(
        self, client_id: uuid.UUID, code: str, policy: CaseSensitivity
    ) -> list[FacilityMapping]: ...

    def facilities_for_client(self, client_id: uuid.UUID) -> set[uuid.UUID]: ...


class InMemoryFacilityMappingStore:
    def __init__(self, mappings: list[FacilityMapping] | None = None) -> None:
        self._lock = threading.Lock()
        self._rows: list[FacilityMapping] = list(mappings or [])

    def add(self, mapping: FacilityMapping) -> None:
        with self._lock:
            self._rows.append(mapping)

    def find(self, client_id, code, policy):
        wanted = normalize_code(code, policy)
        with self._lock:
            return [
                m for m in self._rows
                if m.client_id == client_id
                and normalize_code(m.external_property_code, policy) == wanted
            ]

    def facilities_for_client(self, client_id):
        with self._lock:
            return {m.facility_id for m in self._rows if m.client_id == client_id and m.enabled}


class FacilityResolver:
    def __init__(
        self, store: FacilityMappingStore, *, case_sensitivity: CaseSensitivity = CaseSensitivity.EXACT
    ) -> None:
        self._store = store
        self.case_sensitivity = case_sensitivity

    def resolve(self, client: AuthenticatedClient, property_code: str | None) -> uuid.UUID:
        if not property_code:
            raise FacilityAuthorizationError(
                "Message carries no property code and the link is not bound to one.",
                code="property_code_missing",
            )
        if not PROPERTY_CODE_PATTERN.fullmatch(property_code):
            raise ValidationFailed("Property code is malformed.", code="property_code_malformed")

        matches = self._store.find(client.client_id, property_code, self.case_sensitivity)
        if not matches:
            raise FacilityAuthorizationError(
                "Property code is not mapped for this integration client.",
                code="property_not_mapped",
            )
        if len(matches) > 1:
            raise FacilityAuthorizationError(
                "Property code is ambiguous for this integration client.",
                code="property_mapping_ambiguous",
            )
        mapping = matches[0]
        if not mapping.enabled:
            raise FacilityAuthorizationError(
                "Property mapping is disabled.", code="property_mapping_disabled"
            )
        return mapping.facility_id

    def assert_authorized(self, client_id: uuid.UUID, facility_id: uuid.UUID) -> None:
        """For callers that name a facility directly (e.g. outbound requests)."""
        if facility_id not in self._store.facilities_for_client(client_id):
            raise FacilityAuthorizationError(
                "Integration client is not authorized for this facility.",
                code="facility_not_authorized",
            )

    def assert_no_scope_smuggling(
        self, body: Any, *, facility_id: uuid.UUID, property_code: str | None
    ) -> None:
        expected_code = (
            normalize_code(property_code, self.case_sensitivity) if property_code else None
        )
        for key, value in _walk(body):
            k = key.lower().replace("_", "").replace("-", "")
            if k in FACILITY_ID_KEYS:
                if value is None:
                    continue
                try:
                    supplied = uuid.UUID(str(value))
                except ValueError:
                    raise FacilityAuthorizationError(
                        "Payload facility identifier is malformed.", code="payload_facility_mismatch"
                    ) from None
                if supplied != facility_id:
                    raise FacilityAuthorizationError(
                        "Payload facility identifier does not match the authorized facility.",
                        code="payload_facility_mismatch",
                    )
            elif k in PROPERTY_CODE_KEYS:
                if value is None:
                    continue
                if expected_code is None or not isinstance(value, str) or (
                    normalize_code(value, self.case_sensitivity) != expected_code
                ):
                    raise FacilityAuthorizationError(
                        "Payload property code does not match the authorized property.",
                        code="payload_property_mismatch",
                    )


def _walk(value: Any, depth: int = 0):
    """Yield (key, value) for every object member at any depth."""
    if depth > 32:
        raise ValidationFailed("Payload nesting is too deep.", code="payload_too_deep")
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key, item
            yield from _walk(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item, depth + 1)
