"""HTNG-style certification scenarios (SYNTHETIC SOAP messages; not HTNG operations).

Reuses tests/integrations/test_api.env_impl (real app factory + inbound endpoint +
in-memory engine + the PROVISIONAL generic XML profile). Official HTNG operation
contracts are registered as BLOCKED.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta

from app.integrations.core.envelope import MessageStatus
from app.integrations.core.errors import TransientFailure
from app.integrations.simulators.fixtures import TEST_XML_NS, generic_arrival_soap
from app.integrations.transport.soap import parse_soap

from .core import Category, scenario

URL = "/api/v1/integrations/htng/inbound"
T, E = Category.TRANSPORT, Category.ENGINE


@contextmanager
def htng_env(ctx):
    from app.integrations.runtime import set_runtime

    from ..test_api import env_impl

    gen = env_impl()
    stack, client, _, runtime = next(gen)
    ctx.secrets.extend(stack.secrets.values())
    ctx.evidence.adapter = "HTNGAdapter(profile=acx-generic-xml-test/0, PROVISIONAL)"
    try:
        yield stack, client, runtime
    finally:
        gen.close()
        set_runtime(None)


def headers(stack, ctype="text/xml; charset=utf-8", code="pms-a", secret=None, cid=None):
    h = {"X-Integration-Client": code, "X-Integration-Secret": secret or stack.secrets[code], "Content-Type": ctype}
    if cid:
        h["X-Correlation-ID"] = cid
    return h


def soap11(ref="c-1", prop="HOTEL-A", extra=""):
    return generic_arrival_soap(message_ref=ref, property_code=prop, room="101", stay_ref="SYN-STAY-1", extra=extra)


def soap12(ref="c12-1", prop="HOTEL-A"):
    return (f'<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" xmlns:t="{TEST_XML_NS}"><e:Body>'
            f"<t:GuestArrival><t:MessageRef>{ref}</t:MessageRef><t:PropertyCode>{prop}</t:PropertyCode>"
            "<t:Room>101</t:Room><t:StayRef>SYN-STAY-1</t:StayRef></t:GuestArrival></e:Body></e:Envelope>").encode()


def record(ctx, r, ref=None):
    ctx.evidence.input_ref = ref
    ctx.evidence.correlation_id = r.headers.get("X-Correlation-ID")
    ctx.evidence.response = {"http_status": r.status_code, "content_type": r.headers.get("content-type", "")}
    if r.content:
        try:
            msg = parse_soap(r.content)
            ctx.evidence.response["soap_version"] = str(msg.version)
            if msg.fault:
                ctx.evidence.response["fault_code"] = msg.fault.code
            elif msg.body is not None and len(msg.body):
                ctx.evidence.processing_result = msg.body[0].text
        except Exception:  # noqa: BLE001 - non-SOAP body recorded as such
            ctx.evidence.response["body"] = "non-SOAP"


@scenario("HTNG-SYN-001", "htng", T, "Valid SOAP 1.1 request accepted and acknowledged",
          expected={"http": 200, "ack": "accepted", "soap": "1.1"}, evidence=("correlation_id", "response"))
def _valid11(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(), headers=headers(stack))
        record(ctx, r, "c-1")
        ctx.expect(r.status_code == 200, f"status {r.status_code}")
        ctx.expect(ctx.evidence.response.get("soap_version") == "1.1", "ack not SOAP 1.1")
        ctx.expect(ctx.evidence.processing_result == "accepted", "ack outcome not accepted")


@scenario("HTNG-SYN-002", "htng", T, "Valid SOAP 1.2 request answered in SOAP 1.2",
          expected={"http": 200, "ack": "accepted", "soap": "1.2"}, evidence=("response",))
def _valid12(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap12(), headers=headers(stack, "application/soap+xml"))
        record(ctx, r, "c12-1")
        ctx.expect(r.status_code == 200 and ctx.evidence.response.get("soap_version") == "1.2", str(ctx.evidence.response))


@scenario("HTNG-SYN-003", "htng", T, "SOAP 1.1 fault on rejection",
          expected={"http": 401, "fault": "soap:Client"}, evidence=("response",))
def _fault11(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(), headers=headers(stack, secret="w" * 40))
        record(ctx, r)
        ctx.expect(r.status_code == 401 and ctx.evidence.response.get("fault_code") == "soap:Client", str(ctx.evidence.response))


@scenario("HTNG-SYN-004", "htng", T, "SOAP 1.2 fault on rejection",
          expected={"http": 403, "fault": "env:Sender"}, evidence=("response",))
def _fault12(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap12(prop="HOTEL-B"), headers=headers(stack, "application/soap+xml"))
        record(ctx, r)
        ctx.expect(r.status_code == 403 and ctx.evidence.response.get("fault_code") == "env:Sender", str(ctx.evidence.response))


@scenario("HTNG-SYN-005", "htng", T, "Invalid XML rejected without persistence",
          expected={"http": 400, "persisted": 0}, evidence=("response",))
def _invalid_xml(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=b"<not-closed>", headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 400 and not stack.repo.list_messages(facility_scope=None), str(ctx.evidence.response))


@scenario("HTNG-SYN-006", "htng", T, "Unsupported Content-Type rejected (415)",
          expected={"http": 415}, evidence=("response",))
def _ctype(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(), headers=headers(stack, "application/json"))
        record(ctx, r)
        ctx.expect(r.status_code == 415, f"status {r.status_code}")


@scenario("HTNG-SYN-007", "htng", E, "Unauthorized client rejected and audited without secret",
          expected={"http": 401, "audit": "client.authentication_failed"}, evidence=("response", "audit_actions"))
def _unauth(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(), headers=headers(stack, code="pms-off", secret=stack.secrets["pms-off"]))
        record(ctx, r)
        ctx.evidence.audit_actions = [e.action for e in stack.repo.list_audit(facility_scope=None)]
        ctx.expect(r.status_code == 401 and "client.authentication_failed" in ctx.evidence.audit_actions, "not rejected/audited")


@scenario("HTNG-SYN-008", "htng", E, "Cross-facility request rejected (security)",
          expected={"http": 403, "persisted": 0}, evidence=("response",))
def _cross(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(prop="HOTEL-B"), headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 403 and not stack.repo.list_messages(facility_scope=None), "cross-facility accepted")


@scenario("HTNG-SYN-009", "htng", E, "Duplicate request acknowledged as duplicate, stored once",
          expected={"ack": "duplicate", "messages": 1}, evidence=("processing_result",))
def _dup(ctx):
    with htng_env(ctx) as (stack, client, _):
        client.post(URL, content=soap11("d-1"), headers=headers(stack))
        r = client.post(URL, content=soap11("d-1"), headers=headers(stack))
        record(ctx, r, "d-1")
        ctx.expect(ctx.evidence.processing_result == "duplicate", "second request not a duplicate")
        ctx.expect(len(stack.repo.list_messages(facility_scope=None)) == 1, "stored twice")


@scenario("HTNG-SYN-010", "htng", E, "Correlation ID propagated to response and stored message; unsafe IDs replaced",
          expected={"echo": True, "stored": True, "unsafe_replaced": True}, evidence=("correlation_id",))
def _corr(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11("k-1"), headers=headers(stack, cid="cert-corr-42"))
        record(ctx, r, "k-1")
        stored = [m.correlation_id for m in stack.repo.list_messages(facility_scope=None)]
        bad = client.post(URL, content=soap11("k-2"), headers=headers(stack, cid="bad\tid"))
        ctx.expect(r.headers.get("X-Correlation-ID") == "cert-corr-42" and stored == ["cert-corr-42"], "not propagated")
        ctx.expect(bad.headers.get("X-Correlation-ID") != "bad\tid", "unsafe correlation id echoed")


@scenario("HTNG-SYN-011", "htng", E, "Database outage during intake answers 503 (retryable) and stores nothing",
          expected={"http": 503}, evidence=("response",))
def _outage(ctx):
    with htng_env(ctx) as (stack, client, _):
        def down(*a, **k):
            raise ConnectionError("database down")

        stack.repo.accept = down
        r = client.post(URL, content=soap11(), headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 503, f"status {r.status_code}")


@scenario("HTNG-SYN-012", "htng", E, "Transient processing failure retried then recovered",
          expected={"first": "RETRY_WAIT", "final": "SUCCEEDED"}, evidence=("retry_dlq",))
def _retry(ctx):
    with htng_env(ctx) as (stack, client, _):
        stack.handlers["test.guest_arrival"].failures.append(TransientFailure("synthetic outage"))
        client.post(URL, content=soap11("r-1"), headers=headers(stack))
        stack.worker.run_once()
        first = stack.repo.list_messages(facility_scope=None)[0].status
        stack.clock.advance(timedelta(seconds=11).total_seconds())
        stack.worker.run_once()
        final = stack.repo.list_messages(facility_scope=None)[0]
        ctx.evidence.retry_dlq = {"first": str(first), "final": str(final.status), "attempts": final.attempt_count}
        ctx.expect(first is MessageStatus.RETRY_WAIT and final.status is MessageStatus.SUCCEEDED, str(ctx.evidence.retry_dlq))


@scenario("HTNG-SYN-013", "htng", T, "Malformed SOAP envelope (no Body) rejected",
          expected={"http": 400}, evidence=("response",))
def _nobody(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=b'<e:Envelope xmlns:e="http://schemas.xmlsoap.org/soap/envelope/"/>',
                        headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 400, f"status {r.status_code}")


@scenario("HTNG-SYN-014", "htng", T, "Unexpected namespace inside the payload rejected",
          expected={"http": 400}, evidence=("response",))
def _ns(ctx):
    with htng_env(ctx) as (stack, client, _):
        r = client.post(URL, content=soap11(extra='<z:X xmlns:z="urn:unexpected">1</z:X>'), headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 400 and not stack.repo.list_messages(facility_scope=None), f"status {r.status_code}")


@scenario("HTNG-SYN-015", "htng", T, "Structural validation failure (synthetic profile: required element missing)",
          expected={"http": 400}, evidence=("response",))
def _structural(ctx):
    with htng_env(ctx) as (stack, client, _):
        body = soap11("s-1").replace(b"<t:StayRef>SYN-STAY-1</t:StayRef>", b"")
        r = client.post(URL, content=body, headers=headers(stack))
        record(ctx, r)
        ctx.expect(r.status_code == 400, f"status {r.status_code}")


@scenario("HTNG-OFF-001", "htng", Category.VENDOR, "Official HTNG operation contracts (decode/encode/ack per vendor profile)",
          expected={"all_cases": "pass"}, requires=("vendor",), blocked_by=("HF-07", "HF-08"))
def _off_ops(ctx):  # pragma: no cover - never executed while blocked
    raise AssertionError("unreachable")


@scenario("HTNG-OFF-002", "htng", Category.VENDOR, "Official XSD validation of inbound and outbound messages",
          expected={"all_valid": True}, requires=("vendor",), blocked_by=("HF-07", "HF-39"))
def _off_xsd(ctx):  # pragma: no cover
    raise AssertionError("unreachable")


