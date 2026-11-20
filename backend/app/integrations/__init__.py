"""HTNG + FIAS integration framework.

Layering (outer to inner). Each layer only talks to the one below it:

    transport/     bytes on a wire: TCP framing, SOAP over HTTP, safe XML
    adapters/      protocol <-> canonical: FIASAdapter, HTNGAdapter
    exchange/      ExchangeGateway: auth, facility resolution, idempotency,
                   routing to handlers, outbound requests
    processing/    durable inbound queue, worker leases, retry, DLQ, outbox
    domain/        approval-gated adapters around the EXISTING HMS services
    api/           FastAPI operational endpoints

Vendor protocol semantics are NOT encoded anywhere in this package. FIAS
record grammars and HTNG schema profiles are supplied as data
(`adapters/fias/spec.py`, `adapters/htng/schema.py`) and the production
registries are empty until official documentation is supplied
(decisions HF-07 / HF-11). See docs/HTNG_FIAS_*.md.
"""
