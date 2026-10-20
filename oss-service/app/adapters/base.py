"""Adapter layer base: OSS rows -> the HMS API contract.

The OSS database has a DIFFERENT shape from the HMS device tables. Each adapter
function translates OSS rows into the Pydantic contract models in
`app/schemas/*` so the forwarded JSON is identical to today's HMS responses.

### Discovery gate

The real column/table mapping cannot be written until the OSS schema is known.
Until step 1 (read-only schema discovery of the OSS DB) is done, every adapter
raises `AdapterNotMapped`, which the API layer turns into a clear 503 that says
the OSS mapping is pending -- never a fake 200 with invented data.

When the mapping doc from discovery exists, implement each adapter by:
  1. selecting from the reflected OSS models (`app/models/reflect.py`), and
  2. constructing the contract model (e.g. `DeviceRead(**mapped_fields)`).
"""

from __future__ import annotations


class AdapterNotMapped(RuntimeError):
    """An OSS adapter has not been mapped to the real OSS schema yet."""

    def __init__(self, resource: str):
        self.resource = resource
        super().__init__(
            f"OSS adapter for '{resource}' is not mapped yet. Complete OSS "
            f"schema discovery (step 1) and implement the adapter before use."
        )
