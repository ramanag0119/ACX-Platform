"""Wiring: the production runtime and a hook for tests.

The default runtime is built lazily on first use by an integration endpoint,
never at import, and never at application start-up -- so importing app.main
opens no socket, starts no worker and touches no integration table.

Production wiring today:
  FIASAdapter()                     BLOCKED (no verified spec, HF-11)
  HTNGAdapter(empty registry)       BLOCKED (no approved profile, HF-07)
  stay.check_in / stay.check_out    registered, but the domain adapter is
                                    gated (live writes off, HF-01/02/05/19/18)
  repository / stores               MySQL candidate tables (absent until HF-39)
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import SchemaRegistry
from app.integrations.config import IntegrationSettings, get_integration_settings
from app.integrations.domain.approvals import LiveWriteGate
from app.integrations.domain.stays import CHECK_IN, CHECK_OUT, StayDomainAdapter, StayEventHandler
from app.integrations.exchange.gateway import ExchangeGateway
from app.integrations.exchange.registry import AdapterRegistry, HandlerRegistry
from app.integrations.metrics import IntegrationMetrics
from app.integrations.processing.repository import IntegrationRepository
from app.integrations.security.clients import ClientAuthenticator
from app.integrations.security.facility import FacilityResolver

if TYPE_CHECKING:
    from app.integrations.admin import IntegrationAdmin


@dataclass
class IntegrationRuntime:
    settings: IntegrationSettings
    gateway: ExchangeGateway
    repository: IntegrationRepository
    metrics: IntegrationMetrics
    live_write_gate: LiveWriteGate
    htng_adapter: HTNGAdapter | None = None
    #: name -> callable returning a transport health dict
    transports: dict[str, Callable[[], dict]] = field(default_factory=dict)
    #: transport name -> protocol it carries. The observability overview
    #: attributes a transport to a protocol ONLY through this map; an
    #: untagged transport is never guessed from its name.
    transport_protocols: dict[str, str] = field(default_factory=dict)
    #: returns {table: present}; raises on database failure
    persistence_probe: Callable[[], dict[str, bool]] | None = None
    #: SQL-backed administration (mappings). None for in-memory runtimes.
    admin: "IntegrationAdmin | None" = None


def _actor(settings: IntegrationSettings) -> uuid.UUID | None:
    if not settings.ACTOR_USER_ID:
        return None
    try:
        return uuid.UUID(settings.ACTOR_USER_ID)
    except ValueError:
        return None


def build_default_runtime(settings: IntegrationSettings | None = None) -> IntegrationRuntime:
    from app.db.session import engine
    from app.integrations.admin import IntegrationAdmin
    from app.integrations.processing.sql_repository import SqlIntegrationRepository, table_presence
    from app.integrations.security.sql_stores import SqlClientStore, SqlFacilityMappingStore

    settings = settings or get_integration_settings()
    metrics = IntegrationMetrics()
    repository = SqlIntegrationRepository(engine)

    adapters = AdapterRegistry()
    adapters.register(FIASAdapter())
    htng = HTNGAdapter(SchemaRegistry())
    adapters.register(htng)

    gate = LiveWriteGate(enabled_flag=settings.LIVE_DOMAIN_WRITES)
    stay_adapter = StayDomainAdapter(gate=gate, resolver=None, actor_id=_actor(settings))
    handlers = HandlerRegistry()
    handlers.register(StayEventHandler(CHECK_IN, stay_adapter))
    handlers.register(StayEventHandler(CHECK_OUT, stay_adapter))

    gateway = ExchangeGateway(
        adapters=adapters,
        handlers=handlers,
        authenticator=ClientAuthenticator(SqlClientStore(engine)),
        resolver=FacilityResolver(SqlFacilityMappingStore(engine)),
        repository=repository,
        metrics=metrics,
        max_message_bytes=settings.MAX_MESSAGE_BYTES,
        max_attempts=settings.RETRY_MAX_ATTEMPTS,
        store_wire_payload=settings.STORE_RAW_WIRE_PAYLOAD,
    )
    return IntegrationRuntime(
        settings=settings,
        gateway=gateway,
        repository=repository,
        metrics=metrics,
        live_write_gate=gate,
        htng_adapter=htng,
        persistence_probe=lambda: table_presence(engine),
        admin=IntegrationAdmin(engine),
    )


_lock = threading.Lock()
_runtime: IntegrationRuntime | None = None


def get_runtime() -> IntegrationRuntime:
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = build_default_runtime()
        return _runtime


def set_runtime(runtime: IntegrationRuntime | None) -> None:
    """Test hook. Passing None resets to lazy default construction."""
    global _runtime
    with _lock:
        _runtime = runtime
