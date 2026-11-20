"""OutboxRelay sender for HTNG over SOAP/HTTP.

The SOAP action comes from the approved profile's OperationSpec, never from
a hard-coded table. The vendor endpoint itself is configuration (HF-24); no
endpoint is configured in the repository.
"""

from __future__ import annotations

from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.transport.soap import SoapEndpoint, SoapTransport


class HtngSoapSender:
    def __init__(self, transport: SoapTransport, endpoint: SoapEndpoint, adapter: HTNGAdapter) -> None:
        self._transport = transport
        self._endpoint = endpoint
        self._adapter = adapter

    def send(self, payload: bytes, *, claim) -> None:
        self._transport.call(
            self._endpoint,
            payload,
            soap_action=self._adapter.soap_action_for(claim.record.message_type),
            correlation_id=claim.record.correlation_id,
        )
