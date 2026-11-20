"""End-to-end PMS simulation into the REAL HMS stay services (DISPOSABLE MySQL only).

FIAS-style:  loopback simulator --TCP--> TcpLink --> LinkPump --> FIASAdapter
             --> ExchangeGateway --> SqlIntegrationRepository --> InboundWorker
             --> StayDomainAdapter --> app.services.stays_write --> audit
HTNG-style:  HTTP POST (SOAP 1.2) --> /integrations/htng/inbound --> same engine

Record ids "ZI"/"ZO" and the XML namespace below are SYNTHETIC TEST ASSUMPTIONS — not
FIAS or HTNG definitions. The live-write gate is opened only by a TEST-ONLY register.
Requires INTEGRATION_TEST_HMS_DB_URL (see test_hms_domain_mysql.py).
"""

from __future__ import annotations

import asyncio
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.integrations.adapters.base import TransportContext
from app.integrations.adapters.fias.adapter import FIASAdapter
from app.integrations.adapters.fias.spec import (
    FieldSpec,
    FiasSpecification,
    RecordSpec,
    VerificationStatus,
    WireGrammar,
)
from app.integrations.adapters.htng.adapter import HTNGAdapter
from app.integrations.adapters.htng.schema import (
    MappedInbound,
    OperationSpec,
    SchemaProfile,
    SchemaRegistry,
    StructuralValidator,
)
from app.integrations.config import IntegrationSettings
from app.integrations.core.envelope import Direction, IntakeOutcome, MessageStatus, Protocol
from app.integrations.core.retry import RetryPolicy
from app.integrations.domain.approvals import LiveWriteGate
from app.integrations.domain.stays import CHECK_IN, CHECK_OUT, StayDomainAdapter, StayEventHandler
from app.integrations.exchange.dispatcher import MessageDispatcher
from app.integrations.exchange.gateway import ExchangeGateway
from app.integrations.exchange.registry import AdapterRegistry, HandlerRegistry
from app.integrations.processing.sql_repository import SqlIntegrationRepository
from app.integrations.processing.worker import InboundWorker
from app.integrations.security.clients import (
    ClientAuthenticator,
    InMemoryClientStore,
    IntegrationClient,
    generate_secret,
    hash_secret,
)
from app.integrations.security.facility import FacilityMapping, FacilityResolver, InMemoryFacilityMappingStore
from app.integrations.simulators.fias_simulator import FiasTestSimulator
from app.integrations.simulators.fixtures import provisional_test_framer
from app.integrations.transport.soap import parse_soap
from app.integrations.transport.tcp import LinkPump, ReconnectPolicy, TcpLink, TcpSettings

from .conftest import Clock
from .test_hms_domain_mysql import ExternalRefResolver, _test_only_register, reset_stay, stay

CLIENT = uuid.UUID("cccccccc-0000-4000-8000-0000000000e3")
P = VerificationStatus.PROVISIONAL_TEST
SRC = "SYNTHETIC TEST ASSUMPTION (test_e2e_hms_simulation.py)"
IN = frozenset({Direction.INBOUND})

STAY_SPEC = FiasSpecification(
    name="ACX-SYNTHETIC-STAY-TEST", version="0",
    grammar=WireGrammar("ascii", 2, b"|", 2, P, SRC),
    records=tuple(
        RecordSpec(rid, mtype, IN, (
            FieldSpec("MI", "message_ref", mandatory=True, max_length=40),
            FieldSpec("PC", "property_code", mandatory=True, max_length=32),
            FieldSpec("SR", "external_stay_ref", mandatory=True, max_length=40),
        ), P, SRC, idempotency_fields=("MI",), property_field="PC")
        for rid, mtype in (("ZI", CHECK_IN), ("ZO", CHECK_OUT))
    ),
)

NS = "urn:acx:test:synthetic-stay:v1"


def _map(el):
    def t(name):
        node = el.find(f"{{{NS}}}{name}")
        return node.text if node is not None else None

    return MappedInbound(message_type=CHECK_IN, property_code=t("PropertyCode"),
                         idempotency_key=t("MessageRef"), external_message_id=t("MessageRef"),
                         body={"external_stay_ref": t("StayRef")})


STAY_PROFILE = SchemaProfile(
    profile_id="acx-synthetic-stay", version="0", namespaces=frozenset({NS}), status=P, source=SRC,
    operations=(OperationSpec(
        root=(NS, "CheckIn"), message_type=CHECK_IN, direction=Direction.INBOUND,
        validator=StructuralValidator(required_paths=(f"{{{NS}}}MessageRef", f"{{{NS}}}StayRef"),
                                      allowed_namespaces=frozenset({NS})),
        inbound_mapper=_map,
        response_builder=lambda outcome, cid: _ack(outcome),
    ),),
)


def _ack(outcome):
    el = ET.Element(f"{{{NS}}}Receipt")
    ET.SubElement(el, f"{{{NS}}}Outcome").text = outcome
    return el


def build(engine):
    with engine.begin() as c:
        for t in ("integration_audit_events", "integration_outbox_messages", "integration_idempotency_keys",
                  "integration_inbound_payloads", "integration_inbound_messages"):
            c.execute(text(f"DELETE FROM {t}"))  # noqa: S608 - fixed table-name constants
        facility_id = uuid.UUID(c.execute(text("SELECT id FROM facility LIMIT 1")).scalar_one())
        actor = uuid.UUID(c.execute(text("SELECT id FROM app_user WHERE user_name='system'")).scalar_one())
        if not c.execute(text("SELECT COUNT(*) FROM integration_clients WHERE id=:i"), {"i": str(CLIENT)}).scalar_one():
            c.execute(text("INSERT INTO integration_clients (id, client_code, secret_hash, enabled, protocols) "
                           "VALUES (:i, 'pms-sim', :h, 1, 'fias,htng')"),
                      {"i": str(CLIENT), "h": hash_secret(generate_secret())})
    secret = generate_secret()
    clock = Clock(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    repo = SqlIntegrationRepository(engine)
    domain = StayDomainAdapter(gate=LiveWriteGate(enabled_flag=True, register=_test_only_register()),
                               resolver=ExternalRefResolver(), actor_id=actor)
    handlers = HandlerRegistry()
    handlers.register(StayEventHandler(CHECK_IN, domain))
    handlers.register(StayEventHandler(CHECK_OUT, domain))
    adapters = AdapterRegistry()
    adapters.register(FIASAdapter(STAY_SPEC, allow_unverified=True, app_env="test"))
    reg = SchemaRegistry(allow_unverified=True, app_env="test")
    reg.register(STAY_PROFILE)
    htng = HTNGAdapter(reg, profile_id="acx-synthetic-stay", version="0")
    adapters.register(htng)
    store = InMemoryClientStore([IntegrationClient(CLIENT, "pms-sim", True,
                                                   frozenset({Protocol.FIAS, Protocol.HTNG}), hash_secret(secret))])
    gateway = ExchangeGateway(
        adapters=adapters, handlers=handlers, authenticator=ClientAuthenticator(store),
        resolver=FacilityResolver(InMemoryFacilityMappingStore([FacilityMapping(CLIENT, "HOTEL-SIM", facility_id)])),
        repository=repo, clock=clock,
    )
    worker = InboundWorker(repository=repo, dispatcher=MessageDispatcher(handlers),
                           policy=RetryPolicy(max_attempts=3, base_delay_seconds=10, max_delay_seconds=60),
                           worker_id="sim-worker", lease_seconds=30, clock=clock)
    return gateway, worker, repo, clock, facility_id, secret, htng


def statuses(repo):
    return {m.external_message_id: m.status for m in repo.list_messages(facility_scope=None, limit=200)}


def test_fias_style_tcp_into_real_stay_services(hms_engine):
    reset_stay(hms_engine, "PMS-0003", "pending", None, None, "Allotted")
    gateway, worker, repo, clock, facility_id, secret, _ = build(hms_engine)
    client = gateway.authenticate("pms-sim", secret, protocol=Protocol.FIAS)
    results = []
    outage = {"left": 2}
    real_accept = repo.accept

    def flaky_accept(envelope, **kw):  # database outage during intake of one frame
        if envelope.external_message_id == "ZI:ci-1" and outage["left"]:
            outage["left"] -= 1
            raise ConnectionError("database down")
        return real_accept(envelope, **kw)

    repo.accept = flaky_accept

    async def go():
        sim = FiasTestSimulator(enabled=True)
        port = await sim.start()
        link = TcpLink(TcpSettings(host="127.0.0.1", port=port, read_timeout=0.2,
                                   reconnect=ReconnectPolicy(base_delay_seconds=0.05)), provisional_test_framer)
        stop = asyncio.Event()

        def receive(frame):
            r = gateway.receive(frame, protocol=Protocol.FIAS, client=client,
                                context=TransportContext(transport="tcp", bound_property_code="HOTEL-SIM"))
            if not r.retryable:  # record final outcomes; transient retries are counted by the pump
                results.append(r)
            return r

        async def fast(_):
            await asyncio.sleep(0.01)

        pump = LinkPump(link, receive, sleep=fast)
        tasks = [asyncio.create_task(link.run()), asyncio.create_task(pump.run(stop=stop))]
        await link.wait_connected(3)
        await sim.wait_for_client(3)
        await sim.send_record(b"ZI|MIci-1|PCHOTEL-SIM|SRPMS-0003|")   # valid (survives DB outage)
        await sim.send_record(b"ZI|MIci-1|PCHOTEL-SIM|SRPMS-0003|")   # duplicate
        await sim.send_record(b"garbage")                             # malformed
        await sim.send_record(b"ZI|MIx-1|PCHOTEL-OTHER|SRPMS-0003|")  # other property on a bound link
        for _ in range(300):
            if len(results) >= 4:
                break
            await asyncio.sleep(0.02)
        await sim.drop_clients()                                      # connection interruption
        for _ in range(300):
            if link.health.connections >= 2 and sim._streams:  # noqa: SLF001 - test-only
                break
            await asyncio.sleep(0.02)
        await sim.send_record(b"ZO|MIco-1|PCHOTEL-SIM|SRPMS-0003|")   # after reconnect
        for _ in range(300):
            if len(results) >= 5:
                break
            await asyncio.sleep(0.02)
        stop.set()
        await link.stop()
        await asyncio.wait_for(asyncio.gather(*tasks), 5)
        await sim.stop()
        return pump

    pump = asyncio.run(asyncio.wait_for(go(), 30))
    outcomes = [r.outcome for r in results]
    assert outcomes == [IntakeOutcome.ACCEPTED, IntakeOutcome.DUPLICATE, IntakeOutcome.REJECTED,
                        IntakeOutcome.REJECTED, IntakeOutcome.ACCEPTED]
    assert pump.intake_retries == 2                       # outage retried, frame not lost
    assert results[2].error["code"] == "unsupported_message" and not results[2].retryable
    assert results[3].error["code"] == "link_property_mismatch"

    clock.advance(1)  # real time passes between intake and processing
    # Worker crash: a dead worker claims everything and never finishes.
    crashed = worker.__class__(repository=repo, dispatcher=worker._dispatcher, policy=worker._policy,  # noqa: SLF001
                               worker_id="crashed", lease_seconds=30, clock=clock)
    claims = repo.claim(worker_id=crashed.worker_id, now=clock(), lease_seconds=30, limit=10)
    assert len(claims) == 1  # only the check-in: same-stay check-out waits behind it (ordering)
    assert worker.run_once().claimed == 0
    clock.advance(31)                                      # lease expiry -> recovery
    worker.run_once()
    worker.run_once()
    st = statuses(repo)
    assert st["ZI:ci-1"] is MessageStatus.SUCCEEDED and st["ZO:co-1"] is MessageStatus.SUCCEEDED
    status, checkin, checkout, _ = stay(hms_engine, "PMS-0003")
    assert status == "checked out" and checkin is not None and checkout is not None
    actions = [e.action for e in repo.list_audit(facility_scope={facility_id})]
    assert actions[:2] == ["domain.stay.check_out", "domain.stay.check_in"]
    assert sum(1 for m in repo.list_messages(facility_scope=None) if m.external_message_id == "ZI:ci-1") == 1


def test_htng_style_soap12_into_real_stay_services(hms_engine):
    from app.api.deps import get_current_user  # noqa: F401
    from app.integrations.domain.approvals import LiveWriteGate as Gate
    from app.integrations.metrics import IntegrationMetrics
    from app.integrations.runtime import IntegrationRuntime, set_runtime
    from app.main import create_app

    reset_stay(hms_engine, "PMS-0003", "pending", None, None, "Allotted")
    gateway, worker, repo, clock, facility_id, secret, htng = build(hms_engine)
    set_runtime(IntegrationRuntime(
        settings=IntegrationSettings(ENABLED=True, HTNG_INBOUND_ENABLED=True), gateway=gateway, repository=repo,
        metrics=IntegrationMetrics(), live_write_gate=Gate(enabled_flag=False), htng_adapter=htng))

    def soap(ref, prop="HOTEL-SIM"):
        return (f'<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" xmlns:s="{NS}"><e:Body>'
                f"<s:CheckIn><s:MessageRef>{ref}</s:MessageRef><s:PropertyCode>{prop}</s:PropertyCode>"
                f"<s:StayRef>PMS-0003</s:StayRef></s:CheckIn></e:Body></e:Envelope>").encode()

    hdr = {"X-Integration-Client": "pms-sim", "X-Integration-Secret": secret,
           "Content-Type": "application/soap+xml; charset=utf-8"}
    try:
        with TestClient(create_app()) as c:
            url = "/api/v1/integrations/htng/inbound"
            assert c.post(url, content=soap("h-0"), headers={**hdr, "X-Integration-Secret": "y" * 40}).status_code == 401
            assert c.post(url, content=soap("h-x", prop="HOTEL-OTHER"), headers=hdr).status_code == 403
            r = c.post(url, content=soap("h-1"), headers=hdr)
            assert r.status_code == 200 and parse_soap(r.content).body[0].text == "accepted"
            dup = c.post(url, content=soap("h-1"), headers=hdr)
            assert parse_soap(dup.content).body[0].text == "duplicate"
    finally:
        set_runtime(None)
    worker.run_once()
    assert statuses(repo)["h-1"] is MessageStatus.SUCCEEDED
    assert stay(hms_engine, "PMS-0003")[0] == "active"
    assert [e.action for e in repo.list_audit(facility_scope={facility_id})][0] == "domain.stay.check_in"
    assert json.dumps([m.as_public_dict() for m in repo.list_messages(facility_scope=None)]).count("h-1") == 1
    _ = timedelta  # imported for readers adjusting lease scenarios
