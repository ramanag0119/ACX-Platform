"""Fixtures for the HTNG/FIAS integration suites.

These suites need NO seeded HMS database. Most run fully in memory. The MySQL
suites run only when INTEGRATION_TEST_MYSQL_URL points at a DISPOSABLE MySQL
database, and they refuse to run against the configured HMS database name.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings as app_settings
from app.integrations.adapters.base import (
    AdapterReadiness,
    AdapterStatus,
    BaseProtocolAdapter,
    TransportContext,
)
from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry
from app.integrations.core.envelope import (
    CanonicalEnvelope,
    DecodedMessage,
    Direction,
    OutboundRequest,
    Protocol,
)
from app.integrations.core.errors import IntegrationError, ProtocolError
from app.integrations.core.hashing import payload_hash
from app.integrations.core.retry import RetryPolicy
from app.integrations.exchange.dispatcher import MessageDispatcher
from app.integrations.exchange.gateway import ExchangeGateway
from app.integrations.exchange.registry import (
    AdapterRegistry,
    HandlerContext,
    HandlerRegistry,
    HandlerResult,
    MessageHandler,
)
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.repository import InMemoryIntegrationRepository, OutboxDraft
from app.integrations.processing.worker import InboundWorker, OutboxRelay
from app.integrations.security.clients import (
    ClientAuthenticator,
    InMemoryClientStore,
    IntegrationClient,
    generate_secret,
    hash_secret,
)
from app.integrations.security.facility import (
    FacilityMapping,
    FacilityResolver,
    InMemoryFacilityMappingStore,
)
from app.integrations.simulators.fixtures import PROVISIONAL_TEST_FIAS_SPEC, PROVISIONAL_TEST_XML_PROFILE

T0 = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)

FACILITY_A = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
FACILITY_B = uuid.UUID("bbbbbbbb-0000-4000-8000-000000000002")
CLIENT_A = uuid.UUID("cccccccc-0000-4000-8000-00000000000a")
CLIENT_B = uuid.UUID("cccccccc-0000-4000-8000-00000000000b")
CLIENT_OFF = uuid.UUID("cccccccc-0000-4000-8000-00000000000f")


class Clock:
    def __init__(self, start: datetime = T0) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> datetime:
        self.now = self.now + timedelta(seconds=seconds)
        return self.now


class JsonTestAdapter(BaseProtocolAdapter):
    """Protocol.TEST adapter: the wire format is a JSON object. Used to test the
    exchange without depending on any FIAS/HTNG fixture."""

    protocol = Protocol.TEST

    def __init__(self, inbound=("test.guest_arrival", "test.guest_departure"), outbound=("test.receipt",)):
        self._in = frozenset(inbound)
        self._out = frozenset(outbound)

    def decode(self, raw: bytes, context: TransportContext) -> DecodedMessage:
        try:
            doc = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ProtocolError("not json", code="malformed_json") from None
        if not isinstance(doc, dict) or doc.get("type") not in self._in:
            raise ProtocolError("unknown type", code="unknown_type")
        return DecodedMessage(
            protocol=Protocol.TEST,
            message_type=doc["type"],
            schema_version="json-test/1",
            property_code=doc.get("property"),
            idempotency_key=doc.get("id"),
            external_message_id=doc.get("id"),
            body=doc.get("body", {}),
        )

    def encode(self, request: OutboundRequest) -> bytes:
        return json.dumps({"type": request.message_type, "body": request.body}, sort_keys=True).encode()

    def message_types(self, direction: Direction) -> frozenset[str]:
        return self._in if direction is Direction.INBOUND else self._out

    def status(self) -> AdapterStatus:
        return AdapterStatus(Protocol.TEST, AdapterReadiness.TEST_ONLY, "json-test/1",
                             tuple(sorted(self._in)), tuple(sorted(self._out)))


class RecordingHandler(MessageHandler):
    """Records envelopes; fails with queued errors; optionally emits outbox."""

    def __init__(self, message_type: str, *, emit: OutboxDraft | None = None) -> None:
        self.message_type = message_type
        self.seen: list[CanonicalEnvelope] = []
        self.failures: list[BaseException] = []
        self.emit = emit
        self.before_return = None
        #: When set, messages are ordered per body[ordered_by] (e.g. "room").
        self.ordered_by: str | None = None

    def ordering_key(self, body):
        if self.ordered_by and body.get(self.ordered_by):
            return f"{self.ordered_by}:{body[self.ordered_by]}"
        return None

    def handle(self, envelope: CanonicalEnvelope, ctx: HandlerContext) -> HandlerResult:
        self.seen.append(envelope)
        if self.failures:
            raise self.failures.pop(0)
        if self.before_return is not None:
            self.before_return(envelope, ctx)
        if self.emit is not None:
            ctx.emit(self.emit)
        return HandlerResult(summary={"ok": True})


@dataclass
class Stack:
    clock: Clock
    repo: object
    gateway: ExchangeGateway
    worker: InboundWorker
    relay: OutboxRelay
    handlers: dict[str, RecordingHandler]
    secrets: dict[str, str]
    clients: dict[str, object]
    mappings: InMemoryFacilityMappingStore
    metrics: IntegrationMetrics
    sent: list = field(default_factory=list)

    def auth(self, code: str = "pms-a", protocol: Protocol = Protocol.TEST):
        return self.gateway.authenticate(code, self.secrets[code], protocol=protocol)


class RecordingSender:
    def __init__(self, sink: list, failures: list | None = None) -> None:
        self.sink = sink
        self.failures = failures if failures is not None else []

    def send(self, payload: bytes, *, claim) -> None:
        if self.failures:
            raise self.failures.pop(0)
        self.sink.append(payload)


def build_stack(repo=None, *, clock: Clock | None = None, policy: RetryPolicy | None = None,
                store_wire: bool = False, max_attempts: int = 3, client_rows=None, mapping_rows=None) -> Stack:
    clock = clock or Clock()
    repo = repo or InMemoryIntegrationRepository()
    secrets = {"pms-a": generate_secret(), "pms-b": generate_secret(), "pms-off": generate_secret()}
    all_protocols = frozenset({Protocol.TEST, Protocol.FIAS, Protocol.HTNG})
    clients = {
        "pms-a": IntegrationClient(CLIENT_A, "pms-a", True, all_protocols, hash_secret(secrets["pms-a"])),
        "pms-b": IntegrationClient(CLIENT_B, "pms-b", True, all_protocols, hash_secret(secrets["pms-b"])),
        "pms-off": IntegrationClient(CLIENT_OFF, "pms-off", False, all_protocols, hash_secret(secrets["pms-off"])),
    }
    store = client_rows or InMemoryClientStore(list(clients.values()))
    mappings = mapping_rows or InMemoryFacilityMappingStore([
        FacilityMapping(CLIENT_A, "HOTEL-A", FACILITY_A),
        FacilityMapping(CLIENT_A, "HOTEL-A2", FACILITY_B, enabled=False),
        FacilityMapping(CLIENT_B, "HOTEL-B", FACILITY_B),
        # Same external code, different client, different facility.
        FacilityMapping(CLIENT_B, "HOTEL-A", FACILITY_B),
    ])
    adapters = AdapterRegistry()
    adapters.register(JsonTestAdapter())
    adapters.register(FIASAdapter(PROVISIONAL_TEST_FIAS_SPEC, allow_unverified=True, app_env="test"))
    registry = SchemaRegistry(allow_unverified=True, app_env="test")
    registry.register(PROVISIONAL_TEST_XML_PROFILE)
    adapters.register(HTNGAdapter(registry, profile_id="acx-generic-xml-test", version="0"))

    handlers = {
        "test.guest_arrival": RecordingHandler(
            "test.guest_arrival",
            emit=OutboxDraft(Protocol.TEST, "test.receipt", {"outcome": "ok"}),
        ),
        "test.guest_departure": RecordingHandler("test.guest_departure"),
    }
    registry_h = HandlerRegistry()
    for h in handlers.values():
        registry_h.register(h)
    metrics = IntegrationMetrics()
    gateway = ExchangeGateway(
        adapters=adapters,
        handlers=registry_h,
        authenticator=ClientAuthenticator(store),
        resolver=FacilityResolver(mappings),
        repository=repo,
        metrics=metrics,
        max_message_bytes=64 * 1024,
        max_attempts=max_attempts,
        store_wire_payload=store_wire,
        clock=clock,
    )
    policy = policy or RetryPolicy(max_attempts=max_attempts, base_delay_seconds=10, max_delay_seconds=60)
    worker = InboundWorker(repository=repo, dispatcher=MessageDispatcher(registry_h), policy=policy,
                           worker_id="w1", lease_seconds=30, clock=clock, metrics=metrics)
    sent: list = []
    relay = OutboxRelay(repository=repo, adapters=adapters, senders={Protocol.TEST: RecordingSender(sent)},
                        policy=policy, worker_id="r1", lease_seconds=30, clock=clock, metrics=metrics)
    return Stack(clock, repo, gateway, worker, relay, handlers, secrets, clients, mappings, metrics, sent)


def json_msg(msg_id="m-1", *, type_="test.guest_arrival", prop="HOTEL-A", body=None) -> bytes:
    doc = {"type": type_, "id": msg_id, "property": prop,
           "body": body if body is not None else {"room": "101", "guest_name": "Jane Roe"}}
    return json.dumps(doc).encode()


def make_envelope(*, facility=FACILITY_A, client=CLIENT_A, key="k-1", body=None, mtype="test.guest_arrival",
                  received_at=T0) -> CanonicalEnvelope:
    body = body if body is not None else {"room": "101"}
    return CanonicalEnvelope(
        idempotency_key=key, correlation_id="corr-1", facility_id=facility, client_id=client,
        protocol=Protocol.TEST, message_type=mtype, direction=Direction.INBOUND, schema_version="t/1",
        received_at=received_at, payload_hash=payload_hash(body), body=body,
    )


CTX = TransportContext(transport="test")


@pytest.fixture
def stack() -> Stack:
    return build_stack()


@pytest.fixture
def env():
    """(stack, TestClient, current-user holder, runtime) for API tests."""
    from .test_api import env_impl

    yield from env_impl()


# ---------------------------------------------------------------------------
# Disposable MySQL
# ---------------------------------------------------------------------------

MYSQL_URL_ENV = "INTEGRATION_TEST_MYSQL_URL"


def mysql_engine_or_skip():
    url = os.environ.get(MYSQL_URL_ENV)
    if not url:
        pytest.skip(f"{MYSQL_URL_ENV} not set; MySQL persistence tests need a DISPOSABLE database")
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    if parsed.database in (None, "", app_settings.MYSQL_DATABASE):
        pytest.fail("refusing to run destructive integration tests against the configured HMS database")
    return create_engine(
        url,
        isolation_level="READ COMMITTED",
        connect_args={"init_command": "SET time_zone = '+00:00'"},
        pool_size=10,
        max_overflow=10,
    )


def reset_mysql_schema(engine) -> None:
    """Drop/create the integration tables plus a facility STUB (test-only) and a
    scratch table that stands in for an HMS domain table."""
    from sqlalchemy import text

    from app.integrations.processing.sql_models import create_integration_tables, drop_integration_tables

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_domain_effects"))
        drop_integration_tables(conn)
        conn.execute(text("DROP TABLE IF EXISTS facility"))
        # TEST STUB with the same key type as facility.id (CHAR(36) on MySQL).
        conn.execute(text("CREATE TABLE facility (id CHAR(36) NOT NULL PRIMARY KEY) ENGINE=InnoDB"))
        conn.execute(text("CREATE TABLE test_domain_effects (id INT AUTO_INCREMENT PRIMARY KEY, "
                          "message_id CHAR(36) NOT NULL) ENGINE=InnoDB"))
        create_integration_tables(conn)
        for fid in (FACILITY_A, FACILITY_B):
            conn.execute(text("INSERT INTO facility (id) VALUES (:id)"), {"id": str(fid)})


def seed_mysql_clients(engine, secrets: dict[str, str]) -> None:
    from sqlalchemy.orm import Session

    from app.integrations.processing.sql_models import FacilityMappingRow, IntegrationClientRow

    with Session(engine) as s, s.begin():
        for cid, code, enabled in ((CLIENT_A, "pms-a", True), (CLIENT_B, "pms-b", True), (CLIENT_OFF, "pms-off", False)):
            s.add(IntegrationClientRow(id=cid, client_code=code, secret_hash=hash_secret(secrets[code]),
                                       enabled=enabled, protocols="test,fias,htng"))
        s.flush()
        for client, code, fac, enabled in (
            (CLIENT_A, "HOTEL-A", FACILITY_A, True),
            (CLIENT_A, "HOTEL-A2", FACILITY_B, False),
            (CLIENT_B, "HOTEL-B", FACILITY_B, True),
            (CLIENT_B, "HOTEL-A", FACILITY_B, True),
        ):
            s.add(FacilityMappingRow(client_id=client, external_property_code=code,
                                     normalized_property_code=code, facility_id=fac, enabled=enabled))


@pytest.fixture(scope="session")
def mysql_engine():
    engine = mysql_engine_or_skip()
    yield engine
    engine.dispose()


@pytest.fixture(params=["memory", "mysql"])
def repo(request):
    """Every repository-contract test runs against BOTH implementations."""
    if request.param == "memory":
        return InMemoryIntegrationRepository()
    engine = request.getfixturevalue("mysql_engine")
    reset_mysql_schema(engine)
    seed_mysql_clients(engine, {"pms-a": generate_secret(), "pms-b": generate_secret(), "pms-off": generate_secret()})
    from app.integrations.processing.sql_repository import SqlIntegrationRepository

    return SqlIntegrationRepository(engine)


def raise_(exc: IntegrationError):
    raise exc


@pytest.fixture(scope="module")
def hms_engine():
    """Seeded HMS schema on a DISPOSABLE MySQL (needs INTEGRATION_TEST_HMS_DB_URL)."""
    from .test_hms_domain_mysql import hms_engine_impl

    yield from hms_engine_impl()
