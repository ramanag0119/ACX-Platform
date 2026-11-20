# HTNG / FIAS — Integration Architecture (as implemented)

All code is in `backend/app/integrations/`. Every statement here maps to code and tests;
planned-only items are marked **not implemented**.

## 1. Layers

```text
 External PMS / vendor test system
        |                              |
   FIAS-style TCP                 HTNG SOAP/HTTP
        |                              |
 transport/framing.py            transport/soap.py
 transport/tcp.py                transport/xml_security.py
 (FramedStream, TcpLink,          api/router.py  POST /integrations/htng/inbound
  LinkPump, LinkOutboundSender)
        |                              |
 adapters/fias/  FIASAdapter     adapters/htng/  HTNGAdapter
   spec.py (data, verification)     schema.py (SchemaProfile, SchemaRegistry)
   codec.py (parse/serialize)       sender.py (HtngSoapSender)
        |                              |
        +--------------+---------------+
                       |
        exchange/gateway.py  ExchangeAdapter / ExchangeGateway
          1 size guard  2 client protocol check  3 adapter lookup
          4 decode  5 property code -> facility (client scoped)
          6 payload scope-smuggling check  7 handler exists
          8 idempotency key present  9 envelope + persist (idempotent)
                       |
        processing/repository.py  IntegrationRepository
          InMemoryIntegrationRepository | sql_repository.SqlIntegrationRepository
                       |
        processing/worker.py  InboundWorker  (claim, lease, fence, retry, DLQ)
                       |
        exchange/dispatcher.py  MessageDispatcher -> exchange/registry.HandlerRegistry
                       |
        domain/stays.py  StayDomainAdapter  --(LiveWriteGate)-->  app.services.stays_write
                       |
        outbox  -> processing/worker.py OutboxRelay -> adapter.encode -> sender
```

Supporting: `security/` (clients, facility resolver, SQL stores), `core/` (envelope,
errors, hashing, lifecycle, retry, masking, correlation), `metrics.py`, `runtime.py`,
`api/router.py`, `simulators/` (test-only).

## 2. Responsibilities and boundaries

| Component | Does | Never does |
|---|---|---|
| Transport | bytes, framing, timeouts, reconnect, backpressure | parse records, authenticate, touch DB |
| Protocol adapter | wire ↔ `DecodedMessage` / `OutboundRequest` | resolve facilities, call HMS services, persist |
| ExchangeGateway | authenticate, authorise facility, validate, idempotent persist, enqueue outbound | run business logic |
| Worker | lease, dispatch, fenced completion, retry / DLQ | decide business rules |
| Domain adapter | call **existing** HMS services after gates | write HMS tables directly |

`ExchangeAdapter` is the protocol-independent exchange boundary defined in this
repository (no prior meaning existed); it is unrelated to Microsoft Exchange.

## 3. Key design decisions

* **Vendor semantics are data, not code.** FIAS grammar/records (`FiasSpecification`) and
  HTNG operations (`SchemaProfile`) carry a `VerificationStatus`. Production registries are
  empty → both adapters are `BLOCKED` (HF-11, HF-07). Provisional specs require
  `allow_unverified=True` and are refused when `APP_ENV=production`.
* **Intake is cheap, processing is durable.** Intake only validates and persists; HMS
  work happens in the worker, so vendor bursts never hold HMS write locks.
* **Fencing with savepoints.** Completion holds a `SELECT … FOR UPDATE` on the message row
  inside an outer transaction; the session joins with `create_savepoint`, so an HMS
  service's own `db.commit()` releases only a savepoint. Domain change + SUCCEEDED +
  outbox commit together, after re-checking the lease token and expiry.
* **Separate metadata.** Integration tables are on `INTEGRATION_METADATA`, not
  `Base.metadata`, so Alembic autogenerate and `verify_schema` are unaffected (HF-39).
* **Lazy runtime.** Importing `app.main` builds nothing; the runtime is built on first use
  of an operator endpoint. No worker, link or simulator is started by the API (tested).

## 4. Process model

`python -m app.integrations.service` runs the inbound worker, outbox relay and retention
purge in a loop (graceful stop, bounded error back-off, refuses to start unless
`INTEGRATION_ENABLED=true`). Both TCP roles exist: `TcpLink` (HMS connects) and
`transport/tcp_server.TcpListenerLink` (HMS listens; peer allow-list, single owner).
**Not wired:** PM2/systemd supervision (HF-25/26) and which TCP role a FIAS link uses (HF-06)
— no link is started by the service until a verified spec and role exist.

## 5. Ordering

Handlers declare an `ordering_key` (stays: `stay:<external_stay_ref>`). A message is not
claimable while an earlier message (by `received_on`, then id) with the same
(client, facility, key) is PENDING, PROCESSING, RETRY_WAIT or — by default —
DEAD_LETTER. Unordered messages (key NULL) are unaffected. Final policy for dead-lettered
predecessors: HF-27 (`dead_letter_blocks_ordering` switch).

## 6. Administration

`admin.IntegrationAdmin` (clients, rotation, mappings; audited in-transaction),
`cli.py` (client/credential operations, never HTTP), mapping endpoints on the operator API.
Health: `processing/health.py` → `GET /integrations/facilities/health`.
