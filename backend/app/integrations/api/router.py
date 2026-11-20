"""Integration operations API, mounted under /api/v1/integrations.

Operator endpoints reuse the HMS JWT + `require_permission` RBAC. There is no
integration module in `role_module` yet (adding one is a seed/schema change,
HF-39), so the existing `facility_management` grant is used: read for
inspection, write for redrive. Every operator query is scoped to the caller's
`facility_ids`; records outside that scope answer 404 exactly like missing ones.

    GET  /integrations/health              public liveness -- no data
    GET  /integrations/readiness           persistence, adapters, workers, transports
    GET  /integrations/adapters            adapter readiness and blocking decisions
    GET  /integrations/messages            inbound messages (metadata only)
    GET  /integrations/messages/{id}       one message, body MASKED
    GET  /integrations/dlq                 dead-lettered messages
    POST /integrations/messages/{id}/redrive   reason required, audited
    GET  /integrations/outbox              outbound queue
    GET  /integrations/metrics             counters
    GET  /integrations/audit               privileged-action audit trail
    GET  /integrations/observability/overview   dashboard model (HTNG / FIAS / shared, readiness)
    GET  /integrations/observability/messages   paginated metadata search (Page envelope)
    GET  /integrations/observability/dlq        paginated dead letters + redrive eligibility
    GET  /integrations/observability/metrics    windowed per-protocol aggregates for the monitoring charts
    POST /integrations/htng/inbound        vendor SOAP endpoint (disabled by default)

Vendor endpoint health is reported as "not_configured": no vendor endpoint
exists until HF-07 / HF-24 are resolved.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
import xml.etree.ElementTree as ET
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import require_permission
from app.integrations.adapters.base import AdapterReadiness, TransportContext
from app.integrations.core.envelope import IntakeOutcome, MessageStatus, Protocol, utcnow
from app.integrations.core.errors import (
    AuthenticationFailed,
    ErrorCategory,
    IntegrationError,
    InvalidTransition,
    NotFoundInScope,
    ValidationFailed,
)
from app.integrations.core.masking import mask_mapping
from app.integrations.observability import (
    DEFAULT_STALL_SECONDS,
    build_metrics,
    build_overview,
    dlq_item,
    message_item,
    scope_check,
)
from app.integrations.processing.activity import MAX_PAGE_SIZE, MessageQuery
from app.integrations.runtime import IntegrationRuntime, get_runtime
from app.integrations.transport.soap import SOAP11_NS, SOAP12_NS, SoapVersion
from app.integrations.transport.xml_security import qname
from app.services.auth import AuthenticatedUser

RBAC_MODULE = "facility_management"

# Serialise SOAP 1.1 faults with the conventional "soap" prefix so the
# QName in faultcode ("soap:Client") resolves.
ET.register_namespace("soap", SOAP11_NS)
ET.register_namespace("env", SOAP12_NS)

router = APIRouter(prefix="/integrations", tags=["integrations"])

def runtime_dependency() -> IntegrationRuntime:
    return get_runtime()


Runtime = Annotated[IntegrationRuntime, Depends(runtime_dependency)]
Reader = Annotated[AuthenticatedUser, Depends(require_permission(RBAC_MODULE, "read"))]
Writer = Annotated[AuthenticatedUser, Depends(require_permission(RBAC_MODULE, "write"))]

PERSISTENCE_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Integration persistence is not available (tables not provisioned: HF-39, or database down).",
)


def _scope(user: AuthenticatedUser) -> set[uuid.UUID]:
    return set(user.facility_ids)


def _http(error: IntegrationError) -> HTTPException:
    if isinstance(error, NotFoundInScope):
        return HTTPException(status_code=404, detail="Not found.")
    if error.category is ErrorCategory.CONFLICT:
        return HTTPException(status_code=409, detail=error.message)
    if isinstance(error, InvalidTransition):
        return HTTPException(status_code=409, detail=error.message)
    if isinstance(error, ValidationFailed):
        return HTTPException(status_code=422, detail=error.message)
    if error.category is ErrorCategory.SECURITY:
        return HTTPException(status_code=403, detail=error.message)
    return HTTPException(status_code=400, detail=error.message)


def _persist(call):
    try:
        return call()
    except IntegrationError as exc:
        raise _http(exc) from None
    except SQLAlchemyError:
        raise PERSISTENCE_UNAVAILABLE from None


# ------------------------------------------------------------------- health
@router.get("/health", summary="Integration liveness (public, no data)")
def integration_health() -> dict:
    return {"status": "ok"}


@router.get("/readiness", summary="Integration readiness")
def integration_readiness(rt: Runtime, _user: Reader) -> JSONResponse:
    reasons: list[str] = []
    persistence: dict = {"status": "unknown"}
    if rt.persistence_probe is None:
        persistence = {"status": "in_memory"}
    else:
        try:
            tables = rt.persistence_probe()
            missing = sorted(t for t, ok in tables.items() if not ok)
            persistence = {"status": "ok" if not missing else "tables_missing", "missing_tables": missing}
            if missing:
                reasons.append("integration_tables_missing (HF-39)")
        except SQLAlchemyError:
            persistence = {"status": "database_unavailable"}
            reasons.append("database_unavailable")

    adapters = [
        {
            "protocol": str(s.protocol),
            "readiness": str(s.readiness),
            "blocking_decisions": list(s.blocking_decisions),
        }
        for s in rt.gateway.adapters.statuses()
    ]
    if not any(a["readiness"] == AdapterReadiness.READY for a in adapters):
        reasons.append("no_adapter_ready")
    if not rt.settings.ENABLED:
        reasons.append("integration_disabled (INTEGRATION_ENABLED=false)")

    workers = {
        name: (rt.metrics.last_heartbeat(name).isoformat() if rt.metrics.last_heartbeat(name) else None)
        for name in ("inbound_worker", "outbox_relay")
    }
    body = {
        "status": "ready" if not reasons else "not_ready",
        "reasons": reasons,
        "components": {
            "persistence": persistence,
            "adapters": adapters,
            "workers": workers,
            "transports": {name: probe() for name, probe in rt.transports.items()},
            "vendor_endpoints": "not_configured",
            "live_domain_writes": {
                "open": rt.live_write_gate.is_open(),
                "blocking": rt.live_write_gate.blocking(),
            },
        },
    }
    return JSONResponse(status_code=200 if not reasons else 503, content=body)


@router.get("/adapters", summary="Adapter status")
def adapter_status(rt: Runtime, _user: Reader) -> list[dict]:
    return [
        {
            "protocol": str(s.protocol),
            "readiness": str(s.readiness),
            "specification": s.specification,
            "inbound_message_types": list(s.inbound_message_types),
            "outbound_message_types": list(s.outbound_message_types),
            "blocking_decisions": list(s.blocking_decisions),
        }
        for s in rt.gateway.adapters.statuses()
    ]


# ------------------------------------------------------------------ messages
StatusFilter = Literal["PENDING", "PROCESSING", "SUCCEEDED", "RETRY_WAIT", "DEAD_LETTER"]


@router.get("/messages", summary="Inbound messages (metadata only)")
def list_messages(
    rt: Runtime,
    user: Reader,
    status_filter: Annotated[StatusFilter | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict]:
    statuses = {MessageStatus(status_filter)} if status_filter else None
    rows = _persist(lambda: rt.repository.list_messages(facility_scope=_scope(user), statuses=statuses, limit=limit))
    return [r.as_public_dict() for r in rows]


@router.get("/messages/{message_id}", summary="One inbound message (masked body)")
def get_message(message_id: uuid.UUID, rt: Runtime, user: Reader) -> dict:
    msg = _persist(lambda: rt.repository.get(message_id, facility_scope=_scope(user)))
    body = _persist(lambda: rt.repository.load_body(message_id))
    return {**msg.as_public_dict(), "body_masked": mask_mapping(body)}


@router.get("/dlq", summary="Dead-lettered messages")
def dead_letters(
    rt: Runtime, user: Reader, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[dict]:
    rows = _persist(
        lambda: rt.repository.list_messages(
            facility_scope=_scope(user), statuses={MessageStatus.DEAD_LETTER}, limit=limit
        )
    )
    return [r.as_public_dict() for r in rows]


class RedriveRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


@router.post("/messages/{message_id}/redrive", summary="Redrive a dead-lettered message")
def redrive(message_id: uuid.UUID, payload: RedriveRequest, rt: Runtime, user: Writer) -> dict:
    msg = _persist(
        lambda: rt.repository.redrive(
            message_id,
            facility_scope=_scope(user),
            actor_id=str(user.id),
            reason=payload.reason,
            now=utcnow(),
        )
    )
    rt.metrics.inc("redrive", message_type=msg.message_type)
    return msg.as_public_dict()


@router.get("/outbox", summary="Outbound queue")
def outbox(
    rt: Runtime,
    user: Reader,
    status_filter: Annotated[
        Literal["PENDING", "PROCESSING", "SENT", "RETRY_WAIT", "DEAD_LETTER"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict]:
    statuses = {status_filter} if status_filter else None
    rows = _persist(lambda: rt.repository.list_outbox(facility_scope=_scope(user), statuses=statuses, limit=limit))
    return [r.as_public_dict() for r in rows]


@router.get("/metrics", summary="Integration counters")
def metrics(rt: Runtime, user: Reader) -> dict:
    counts = _persist(lambda: rt.repository.counts_by_status(facility_scope=_scope(user)))
    return {**rt.metrics.snapshot(), "messages_by_status": counts}


@router.get("/facilities/health", summary="Per-facility integration health")
def facility_health(
    rt: Runtime,
    user: Reader,
    window_minutes: Annotated[int, Query(ge=1, le=7 * 24 * 60)] = 60,
) -> dict:
    """Counts, backlog age, DLQ and latency per facility in the caller's scope,
    plus per-client last received / last succeeded and link states."""
    now = utcnow()
    rows = _persist(lambda: rt.repository.facility_health(
        facility_scope=_scope(user), now=now, window=timedelta(minutes=window_minutes)))
    return {
        "generated_at": now.isoformat(),
        "window_minutes": window_minutes,
        "facilities": [r.as_dict(now) for r in rows],
        "transports": {name: probe() for name, probe in rt.transports.items()},
        "auth_failures": {k: v for k, v in rt.metrics.snapshot()["counters"].items()
                          if k.startswith("auth_failures")},
    }


# ------------------------------------------------------------ observability
# Read-only dashboard API (docs/HTNG_FIAS_OBSERVABILITY_API_DESIGN.md). Same
# JWT + RBAC (`facility_management` read) and facility scope as every operator
# endpoint above. No payloads, no client codes, no secrets, no write actions.
SEARCH_DEFAULT_WINDOW = timedelta(days=7)
SEARCH_MAX_WINDOW = timedelta(days=31)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
ProtocolFilter = Literal["htng", "fias"]


def _aware(value: datetime | None, name: str) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{name} must include a timezone offset.")
    return value


def _facility_filter(requested: list[uuid.UUID] | None, user: AuthenticatedUser) -> frozenset[uuid.UUID] | None:
    if not requested:
        return None
    if scope_check(requested, _scope(user)):
        raise HTTPException(status_code=403, detail="A requested facility is outside your facility scope.")
    return frozenset(requested)


def _page(rows, total: int, page: int, page_size: int, item, frm: datetime, to: datetime) -> dict:
    """The HMS `Page` envelope (app/schemas/common.py) plus the window applied."""
    return {
        "items": [item(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "window": {"received_from": frm.isoformat(), "received_to": to.isoformat()},
    }


def _query(**kwargs) -> MessageQuery:
    try:
        return MessageQuery(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/observability/overview", summary="Integration dashboard overview (read-only)")
def observability_overview(
    rt: Runtime,
    user: Reader,
    stall_threshold_seconds: Annotated[int, Query(ge=60, le=86400)] = DEFAULT_STALL_SECONDS,
) -> dict:
    return build_overview(rt, facility_scope=_scope(user), now=utcnow(), stall_seconds=stall_threshold_seconds)


@router.get("/observability/messages", summary="Message search (metadata only, paginated)")
def observability_messages(
    rt: Runtime,
    user: Reader,
    protocol: Annotated[list[ProtocolFilter] | None, Query()] = None,
    status_filter: Annotated[list[StatusFilter] | None, Query(alias="status")] = None,
    facility_id: Annotated[list[uuid.UUID] | None, Query(max_length=50)] = None,
    received_from: datetime | None = None,
    received_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> dict:
    to = _aware(received_to, "received_to") or utcnow()
    frm = _aware(received_from, "received_from") or (to - SEARCH_DEFAULT_WINDOW)
    if to - frm > SEARCH_MAX_WINDOW:
        raise HTTPException(status_code=422, detail=f"The date window may not exceed {SEARCH_MAX_WINDOW.days} days.")
    query = _query(
        received_from=frm, received_to=to,
        protocols=frozenset(protocol) if protocol else None,
        statuses=frozenset(status_filter) if status_filter else None,
        facility_ids=_facility_filter(facility_id, user),
        page=page, page_size=page_size,
    )
    rows, total = _persist(lambda: rt.repository.search_messages(query, facility_scope=_scope(user)))
    return _page(rows, total, page, page_size, message_item, frm, to)


@router.get("/observability/dlq", summary="Dead-letter visibility (read-only, paginated)")
def observability_dlq(
    rt: Runtime,
    user: Reader,
    protocol: Annotated[list[ProtocolFilter] | None, Query()] = None,
    facility_id: Annotated[list[uuid.UUID] | None, Query(max_length=50)] = None,
    received_from: datetime | None = None,
    received_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> dict:
    # Dead letters stay until redriven, so there is no default date window: the
    # status predicate uses the (facility_id, status, received_on) index and the
    # page is LIMITed.
    to = _aware(received_to, "received_to") or utcnow()
    frm = _aware(received_from, "received_from") or _EPOCH
    query = _query(
        received_from=frm, received_to=to,
        protocols=frozenset(protocol) if protocol else None,
        statuses=frozenset({"DEAD_LETTER"}),
        facility_ids=_facility_filter(facility_id, user),
        page=page, page_size=page_size,
    )
    rows, total = _persist(lambda: rt.repository.search_messages(query, facility_scope=_scope(user)))
    may_redrive = user.may(RBAC_MODULE, "write")
    return _page(rows, total, page, page_size, lambda m: dlq_item(m, caller_may_redrive=may_redrive), frm, to)


MetricsRange = Literal["1h", "24h", "7d", "30d"]


@router.get("/observability/metrics", summary="Windowed protocol metrics for the monitoring charts (read-only)")
def observability_metrics(
    rt: Runtime,
    user: Reader,
    protocol: ProtocolFilter,
    range_key: Annotated[MetricsRange, Query(alias="range")] = "24h",
    facility_id: Annotated[list[uuid.UUID] | None, Query(max_length=50)] = None,
    tz_offset_minutes: Annotated[int, Query(ge=-840, le=840)] = 0,
) -> dict:
    """Server-side aggregates (COUNT / AVG / GROUP BY over a bounded window) for
    one protocol, scoped to the caller's facilities. No message rows are
    returned. Same JWT, RBAC and facility rules as every observability endpoint:
    a requested facility outside the caller's scope answers 403."""
    return build_metrics(rt, protocol=protocol, range_key=range_key, now=utcnow(),
                         facility_ids=_facility_filter(facility_id, user), facility_scope=_scope(user),
                         tz_offset_minutes=tz_offset_minutes)


@router.get("/audit", summary="Privileged-action audit trail")
def audit(rt: Runtime, user: Reader, limit: Annotated[int, Query(ge=1, le=200)] = 50) -> list[dict]:
    rows = _persist(lambda: rt.repository.list_audit(facility_scope=_scope(user), limit=limit))
    return [
        {
            "action": e.action,
            "actor_type": e.actor_type,
            "actor_id": e.actor_id,
            "facility_id": str(e.facility_id) if e.facility_id else None,
            "message_id": str(e.message_id) if e.message_id else None,
            "reason": e.reason,
            "detail": e.detail,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in rows
    ]


# ------------------------------------------------------- facility mappings
class MappingCreate(BaseModel):
    client_code: str = Field(min_length=2, max_length=64)
    external_property_code: str = Field(min_length=1, max_length=32)
    facility_id: uuid.UUID


class MappingUpdate(BaseModel):
    enabled: bool
    reason: str = Field(min_length=10, max_length=500)


def _admin(rt: IntegrationRuntime):
    if rt.admin is None:
        raise PERSISTENCE_UNAVAILABLE
    return rt.admin


@router.get("/mappings", summary="Facility mappings in my facilities")
def list_mappings(rt: Runtime, user: Reader) -> list[dict]:
    admin = _admin(rt)
    return [m.as_dict() for m in _persist(lambda: admin.list_mappings(facility_scope=_scope(user)))]


@router.post("/mappings", status_code=201, summary="Create a facility mapping (created DISABLED, audited)")
def create_mapping(payload: MappingCreate, rt: Runtime, user: Writer) -> dict:
    admin = _admin(rt)
    view = _persist(lambda: admin.create_mapping(
        payload.client_code, payload.external_property_code, payload.facility_id,
        actor=str(user.id), facility_scope=_scope(user),
    ))
    return view.as_dict()


@router.patch("/mappings/{mapping_id}", summary="Enable or disable a facility mapping (audited)")
def update_mapping(mapping_id: uuid.UUID, payload: MappingUpdate, rt: Runtime, user: Writer) -> dict:
    admin = _admin(rt)
    view = _persist(lambda: admin.set_mapping_enabled(
        mapping_id, payload.enabled, actor=str(user.id), reason=payload.reason, facility_scope=_scope(user),
    ))
    return view.as_dict()


# ---------------------------------------------------------- HTNG inbound
def soap_fault(version: SoapVersion, code: str, reason: str, http_status: int) -> Response:
    """W3C SOAP fault in the request's SOAP version.

    `code` is "Client" / "Server" (SOAP 1.1 names); SOAP 1.2 uses the
    equivalent "Sender" / "Receiver" with the Code/Value + Reason/Text shape.
    """
    if version is SoapVersion.SOAP12:
        ns = SOAP12_NS
        env = ET.Element(f"{{{ns}}}Envelope")
        fault = ET.SubElement(ET.SubElement(env, f"{{{ns}}}Body"), f"{{{ns}}}Fault")
        value = ET.SubElement(ET.SubElement(fault, f"{{{ns}}}Code"), f"{{{ns}}}Value")
        value.text = "env:" + ("Sender" if code == "Client" else "Receiver")
        text = ET.SubElement(ET.SubElement(fault, f"{{{ns}}}Reason"), f"{{{ns}}}Text")
        text.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
        text.text = reason
        media = "application/soap+xml; charset=utf-8"
    else:
        env = ET.Element(f"{{{SOAP11_NS}}}Envelope")
        fault = ET.SubElement(ET.SubElement(env, f"{{{SOAP11_NS}}}Body"), f"{{{SOAP11_NS}}}Fault")
        ET.SubElement(fault, "faultcode").text = f"soap:{code}"
        ET.SubElement(fault, "faultstring").text = reason
        media = "text/xml; charset=utf-8"
    return Response(content=ET.tostring(env, encoding="utf-8", xml_declaration=True),
                    status_code=http_status, media_type=media)


def soap11_fault(code: str, reason: str, http_status: int) -> Response:
    return soap_fault(SoapVersion.SOAP11, code, reason, http_status)


def soap_version_from_content_type(content_type: str | None) -> SoapVersion | None:
    """W3C SOAP HTTP bindings: SOAP 1.1 = text/xml, SOAP 1.2 = application/soap+xml.
    None means the media type is not a SOAP media type."""
    media = (content_type or "").split(";", 1)[0].strip().lower()
    if media == "text/xml":
        return SoapVersion.SOAP11
    if media == "application/soap+xml":
        return SoapVersion.SOAP12
    return None


class _MinuteRateLimiter:
    """Fixed-window per-client counter (per API process)."""

    def __init__(self, clock=None) -> None:
        import threading
        import time

        self._lock = threading.Lock()
        self._clock = clock or time.monotonic
        self._windows: dict[str, tuple[int, int]] = {}

    def allow(self, key: str, per_minute: int) -> bool:
        window = int(self._clock() // 60)
        with self._lock:
            current, count = self._windows.get(key, (window, 0))
            if current != window:
                current, count = window, 0
            if count >= per_minute:
                return False
            self._windows[key] = (current, count + 1)
            return True


_RATE_LIMITER = _MinuteRateLimiter()


_INTAKE_HTTP = {
    ErrorCategory.TRANSIENT: 503,
    ErrorCategory.SECURITY: 403,
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.PROTOCOL: 400,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.UNSUPPORTED: 400,
    ErrorCategory.VENDOR_BLOCKED: 503,
    ErrorCategory.APPROVAL_BLOCKED: 503,
}


@router.post("/htng/inbound", summary="HTNG SOAP inbound (disabled until HF-07)", include_in_schema=True)
async def htng_inbound(
    request: Request,
    x_integration_client: Annotated[str | None, Header()] = None,
    x_integration_secret: Annotated[str | None, Header()] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
) -> Response:
    rt = get_runtime()
    detected = soap_version_from_content_type(request.headers.get("content-type"))
    version = detected or SoapVersion.SOAP11

    def fault(code: str, reason: str, status_code: int) -> Response:
        return soap_fault(version, code, reason, status_code)

    if not (rt.settings.ENABLED and rt.settings.HTNG_INBOUND_ENABLED) or rt.htng_adapter is None:
        return fault("Server", "HTNG inbound is not enabled.", 503)
    limit = rt.settings.MAX_MESSAGE_BYTES
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        return fault("Client", "Message too large.", 413)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > limit:
            return fault("Client", "Message too large.", 413)

    from starlette.concurrency import run_in_threadpool

    try:
        client = await run_in_threadpool(
            rt.gateway.authenticate, x_integration_client, x_integration_secret, protocol=Protocol.HTNG
        )
    except AuthenticationFailed:
        return fault("Client", "Authentication failed.", 401)
    except SQLAlchemyError:
        return fault("Server", "Service unavailable.", 503)

    if rt.settings.HTNG_RATE_LIMIT_PER_MINUTE and not _RATE_LIMITER.allow(
        client.code, rt.settings.HTNG_RATE_LIMIT_PER_MINUTE
    ):
        rt.metrics.inc("rate_limited", protocol="htng", client=client.code)
        return fault("Client", "Rate limit exceeded.", 429)
    if detected is None:
        return fault("Client", "Unsupported media type: SOAP requires text/xml or application/soap+xml.", 415)

    result = await run_in_threadpool(
        lambda: rt.gateway.receive(
            bytes(raw),
            protocol=Protocol.HTNG,
            client=client,
            context=TransportContext(transport="http-soap", peer=request.client.host if request.client else None),
            correlation_id=x_correlation_id,
        )
    )
    headers = {"X-Correlation-ID": result.correlation_id}
    if result.outcome is IntakeOutcome.REJECTED:
        category = ErrorCategory(result.error["category"]) if result.error else ErrorCategory.PERMANENT
        code = "Client" if _INTAKE_HTTP.get(category, 500) < 500 else "Server"
        resp = fault(code, result.error.get("message", "Rejected.") if result.error else "Rejected.",
                     _INTAKE_HTTP.get(category, 500))
        resp.headers.update(headers)
        return resp

    ack = None
    try:
        from app.integrations.transport.soap import parse_soap

        root = parse_soap(bytes(raw)).body
        if root is not None:
            ack = rt.htng_adapter.build_response(qname(root), str(result.outcome), result.correlation_id,
                                                 version=version)
    except IntegrationError:
        ack = None
    if ack is None:
        return Response(status_code=202, headers=headers)
    media = "application/soap+xml; charset=utf-8" if version is SoapVersion.SOAP12 else "text/xml; charset=utf-8"
    return Response(content=ack, status_code=200, media_type=media, headers=headers)
