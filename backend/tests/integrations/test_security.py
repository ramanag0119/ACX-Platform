"""Adversarial security tests: authentication, facility isolation, leakage."""

from __future__ import annotations

import json
import logging

import pytest

from app.integrations.core.envelope import IntakeOutcome, Protocol
from app.integrations.core.errors import AuthenticationFailed, FacilityAuthorizationError, ValidationFailed
from app.integrations.security.clients import (
    ClientAuthenticator,
    InMemoryClientStore,
    IntegrationClient,
    generate_secret,
    hash_secret,
)
from app.integrations.security.facility import (
    CaseSensitivity,
    FacilityMapping,
    FacilityResolver,
    InMemoryFacilityMappingStore,
)

from .conftest import CLIENT_A, CTX, FACILITY_A, FACILITY_B, json_msg


# --- authentication ---------------------------------------------------------
def _auth(stack, code, secret, protocol=Protocol.TEST):
    return stack.gateway.authenticate(code, secret, protocol=protocol)


@pytest.mark.parametrize("code,secret", [(None, None), ("pms-a", None), (None, "x" * 40), ("", ""), ("pms-a", "")])
def test_missing_credentials_fail_closed(stack, code, secret):
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(stack, code, secret)
    assert exc.value.reason == "missing_credentials"


def test_invalid_secret_is_rejected(stack):
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(stack, "pms-a", generate_secret())
    assert exc.value.reason == "invalid_secret"


def test_secret_of_another_client_is_rejected(stack):
    with pytest.raises(AuthenticationFailed):
        _auth(stack, "pms-a", stack.secrets["pms-b"])


def test_unknown_client_is_rejected_with_same_public_error(stack):
    with pytest.raises(AuthenticationFailed) as unknown:
        _auth(stack, "nobody", generate_secret())
    with pytest.raises(AuthenticationFailed) as wrong:
        _auth(stack, "pms-a", generate_secret())
    assert unknown.value.as_dict() == wrong.value.as_dict()
    assert unknown.value.reason == "unknown_client"


def test_disabled_client_is_rejected_even_with_correct_secret(stack):
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(stack, "pms-off", stack.secrets["pms-off"])
    assert exc.value.reason == "client_disabled"


def test_protocol_not_permitted_for_client():
    secret = generate_secret()
    store = InMemoryClientStore([IntegrationClient(CLIENT_A, "fias-only", True, frozenset({Protocol.FIAS}),
                                                   hash_secret(secret))])
    auth = ClientAuthenticator(store)
    assert auth.authenticate("fias-only", secret, protocol=Protocol.FIAS).client_id == CLIENT_A
    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate("fias-only", secret, protocol=Protocol.HTNG)
    assert exc.value.reason == "protocol_not_permitted"


def test_no_store_means_no_access():
    with pytest.raises(AuthenticationFailed) as exc:
        ClientAuthenticator(None).authenticate("pms-a", generate_secret(), protocol=Protocol.TEST)
    assert exc.value.reason == "no_client_store_configured"


def test_misconfigured_hash_fails_closed():
    store = InMemoryClientStore([IntegrationClient(CLIENT_A, "pms-a", True, frozenset({Protocol.TEST}), "plaintext")])
    with pytest.raises(AuthenticationFailed) as exc:
        ClientAuthenticator(store).authenticate("pms-a", "plaintext" * 5, protocol=Protocol.TEST)
    assert exc.value.reason == "client_secret_misconfigured"


@pytest.mark.parametrize("code", ["a", "bad code", "x" * 80, "../etc", "pms-a\n"])
def test_malformed_client_codes_rejected(stack, code):
    with pytest.raises(AuthenticationFailed):
        _auth(stack, code, generate_secret())


def test_oversized_secret_rejected(stack):
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(stack, "pms-a", "x" * 10_000)
    assert exc.value.reason == "secret_too_long"


def test_short_secrets_cannot_be_provisioned():
    with pytest.raises(ValueError):
        hash_secret("short")


def test_hash_never_contains_secret_and_repr_hides_it():
    secret = generate_secret()
    h = hash_secret(secret)
    assert secret not in h and h.startswith("sha256$")
    client = IntegrationClient(CLIENT_A, "c1", True, frozenset(), h)
    assert h not in repr(client)


def test_auth_failures_are_audited_without_secret(stack):
    secret = generate_secret()
    with pytest.raises(AuthenticationFailed):
        _auth(stack, "pms-a", secret)
    events = stack.repo.list_audit(facility_scope=None)
    assert events[0].action == "client.authentication_failed"
    assert secret not in json.dumps(events[0].detail)
    assert stack.metrics.get("auth_failures", protocol="test", reason="invalid_secret") == 1


# --- facility resolution ---------------------------------------------------------
def test_unmapped_property_rejected(stack):
    r = stack.gateway.receive(json_msg(prop="HOTEL-Z"), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.error["code"] == "property_not_mapped"


def test_disabled_mapping_rejected(stack):
    r = stack.gateway.receive(json_msg(prop="HOTEL-A2"), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.error["code"] == "property_mapping_disabled"


def test_missing_property_code_rejected(stack):
    r = stack.gateway.receive(json_msg(prop=None), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.error["code"] == "property_code_missing"


def test_unauthorized_facility_other_clients_mapping_not_usable(stack):
    # HOTEL-B is mapped only for client B; client A must not reach facility B.
    r = stack.gateway.receive(json_msg(prop="HOTEL-B"), protocol=Protocol.TEST, client=stack.auth("pms-a"), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.error["category"] == "security"


def test_same_external_code_resolves_per_client(stack):
    ra = stack.gateway.receive(json_msg("m-1", prop="HOTEL-A"), protocol=Protocol.TEST, client=stack.auth("pms-a"), context=CTX)
    rb = stack.gateway.receive(json_msg("m-1", prop="HOTEL-A"), protocol=Protocol.TEST, client=stack.auth("pms-b"), context=CTX)
    assert stack.repo.get(ra.message_id, facility_scope=None).facility_id == FACILITY_A
    assert stack.repo.get(rb.message_id, facility_scope=None).facility_id == FACILITY_B


def test_ambiguous_mapping_rejected():
    store = InMemoryFacilityMappingStore([FacilityMapping(CLIENT_A, "H1", FACILITY_A),
                                          FacilityMapping(CLIENT_A, "H1", FACILITY_B)])
    from app.integrations.security.clients import AuthenticatedClient

    client = AuthenticatedClient(CLIENT_A, "c", frozenset())
    with pytest.raises(FacilityAuthorizationError) as exc:
        FacilityResolver(store).resolve(client, "H1")
    assert exc.value.code == "property_mapping_ambiguous"


def test_case_sensitivity_is_exact_by_default_hf05():
    from app.integrations.security.clients import AuthenticatedClient

    store = InMemoryFacilityMappingStore([FacilityMapping(CLIENT_A, "Hotel-A", FACILITY_A)])
    client = AuthenticatedClient(CLIENT_A, "c", frozenset())
    exact = FacilityResolver(store)
    assert exact.case_sensitivity is CaseSensitivity.EXACT
    assert exact.resolve(client, "Hotel-A") == FACILITY_A
    with pytest.raises(FacilityAuthorizationError):
        exact.resolve(client, "HOTEL-A")
    insensitive = FacilityResolver(store, case_sensitivity=CaseSensitivity.INSENSITIVE)
    assert insensitive.resolve(client, "HOTEL-A") == FACILITY_A


@pytest.mark.parametrize("code", ["has space", "", "x" * 33, "tab\tx", "é"])
def test_malformed_property_codes(code):
    from app.integrations.security.clients import AuthenticatedClient

    resolver = FacilityResolver(InMemoryFacilityMappingStore())
    with pytest.raises((ValidationFailed, FacilityAuthorizationError)):
        resolver.resolve(AuthenticatedClient(CLIENT_A, "c", frozenset()), code)


# --- scope smuggling ---------------------------------------------------------------
@pytest.mark.parametrize("body", [
    {"facility_id": str(FACILITY_B)},
    {"stay": {"guest": {"facilityId": str(FACILITY_B)}}},
    {"rooms": [{"room": "1"}, {"FACILITY-UUID": str(FACILITY_B)}]},
    {"facility_id": "not-a-uuid"},
    {"property_code": "HOTEL-B"},
    {"nested": [{"hotelCode": "HOTEL-B"}]},
])
def test_payload_facility_scope_smuggling_rejected(stack, body):
    r = stack.gateway.receive(json_msg(body=body), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED
    assert r.error["code"] in ("payload_facility_mismatch", "payload_property_mismatch")
    assert stack.repo.list_messages(facility_scope=None) == []


def test_matching_payload_facility_is_allowed(stack):
    body = {"facility_id": str(FACILITY_A), "property_code": "HOTEL-A", "x": {"facility_id": None}}
    r = stack.gateway.receive(json_msg(body=body), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.ACCEPTED


def test_link_bound_property_cannot_be_overridden_by_message(stack):
    from app.integrations.adapters.base import TransportContext

    ctx = TransportContext(transport="tcp", bound_property_code="HOTEL-A")
    r = stack.gateway.receive(json_msg(prop="HOTEL-B"), protocol=Protocol.TEST, client=stack.auth("pms-b"), context=ctx)
    assert r.error["code"] == "link_property_mismatch"


def test_deeply_nested_payload_rejected(stack):
    body: dict = {}
    cur = body
    for _ in range(40):
        cur["n"] = {}
        cur = cur["n"]
    r = stack.gateway.receive(json_msg(body=body), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    assert r.outcome is IntakeOutcome.REJECTED and r.error["code"] == "payload_too_deep"


# --- cross-facility idempotency / access ------------------------------------------
def test_idempotency_is_scoped_per_client_and_facility(stack):
    a = stack.gateway.receive(json_msg("same-key", prop="HOTEL-A"), protocol=Protocol.TEST, client=stack.auth("pms-a"), context=CTX)
    b = stack.gateway.receive(json_msg("same-key", prop="HOTEL-B"), protocol=Protocol.TEST, client=stack.auth("pms-b"), context=CTX)
    assert a.outcome is IntakeOutcome.ACCEPTED and b.outcome is IntakeOutcome.ACCEPTED
    assert a.message_id != b.message_id


def test_cross_facility_message_access_is_not_found(stack):
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    from app.integrations.core.errors import NotFoundInScope

    with pytest.raises(NotFoundInScope):
        stack.repo.get(r.message_id, facility_scope={FACILITY_B})
    with pytest.raises(NotFoundInScope):
        stack.repo.get(r.message_id, facility_scope=set())
    assert stack.repo.list_messages(facility_scope={FACILITY_B}) == []
    assert stack.repo.get(r.message_id, facility_scope={FACILITY_A}).message_id == r.message_id


def test_unauthorized_redrive_out_of_scope(stack):
    from app.integrations.core.errors import NotFoundInScope, PermanentFailure

    stack.handlers["test.guest_arrival"].failures.append(PermanentFailure("boom"))
    r = stack.gateway.receive(json_msg(), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    stack.worker.run_once()
    with pytest.raises(NotFoundInScope):
        stack.repo.redrive(r.message_id, facility_scope={FACILITY_B}, actor_id="u", reason="operator retry", now=stack.clock())
    assert stack.repo.get(r.message_id, facility_scope=None).status == "DEAD_LETTER"


# --- leakage ---------------------------------------------------------------
def test_no_pii_or_secret_in_logs_or_results(stack, caplog):
    caplog.set_level(logging.DEBUG)
    pii = {"guest_name": "Zebulon Quixotic", "email": "zq@private.example", "card": "4111111111111111"}
    ok = stack.gateway.receive(json_msg("m-pii", body=pii), protocol=Protocol.TEST, client=stack.auth(), context=CTX)
    bad = stack.gateway.receive(json_msg("m-pii2", prop="HOTEL-B", body=pii), protocol=Protocol.TEST,
                                client=stack.auth(), context=CTX)
    stack.handlers["test.guest_arrival"].failures.append(RuntimeError("Zebulon Quixotic 4111111111111111"))
    stack.worker.run_once()
    with pytest.raises(AuthenticationFailed):
        stack.gateway.authenticate("pms-a", "WRONG-" + "s" * 40, protocol=Protocol.TEST)
    blob = caplog.text + json.dumps(ok.model_dump(mode="json")) + json.dumps(bad.model_dump(mode="json"))
    blob += json.dumps([e.detail for e in stack.repo.list_audit(facility_scope=None)])
    blob += json.dumps([m.as_public_dict() for m in stack.repo.list_messages(facility_scope=None)])
    for secret_value in ("Zebulon", "zq@private.example", "4111111111111111", stack.secrets["pms-a"], "WRONG-"):
        assert secret_value not in blob
    assert ok.outcome is IntakeOutcome.ACCEPTED and bad.outcome is IntakeOutcome.REJECTED


@pytest.mark.parametrize("code", ["evil\nINJECTED", "x\x1b[31mred", "a" * 64 + "\n"])
def test_audit_never_stores_malformed_client_codes(stack, code):
    with pytest.raises(AuthenticationFailed):
        _auth(stack, code, generate_secret())
    assert stack.repo.list_audit(facility_scope=None)[0].actor_id is None


def test_audit_keeps_well_formed_client_code(stack):
    with pytest.raises(AuthenticationFailed):
        _auth(stack, "pms-a", generate_secret())
    assert stack.repo.list_audit(facility_scope=None)[0].actor_id == "pms-a"


# --- credential rotation overlap --------------------------------------------------
def _rotating_auth(now, *, expires_in_seconds):
    from datetime import timedelta

    old, new = generate_secret(), generate_secret()
    client = IntegrationClient(CLIENT_A, "rot", True, frozenset({Protocol.TEST}), hash_secret(new),
                               secondary_secret_hash=hash_secret(old),
                               secondary_expires_at=now + timedelta(seconds=expires_in_seconds))
    return ClientAuthenticator(InMemoryClientStore([client]), clock=lambda: now), old, new


def test_previous_secret_accepted_during_overlap_only():
    from .conftest import T0

    auth, old, new = _rotating_auth(T0, expires_in_seconds=60)
    assert auth.authenticate("rot", new, protocol=Protocol.TEST).client_id == CLIENT_A
    assert auth.authenticate("rot", old, protocol=Protocol.TEST).client_id == CLIENT_A
    expired, old2, _ = _rotating_auth(T0, expires_in_seconds=0)
    with pytest.raises(AuthenticationFailed):
        expired.authenticate("rot", old2, protocol=Protocol.TEST)


def test_disabled_client_rejects_previous_secret_too():
    from dataclasses import replace

    from .conftest import T0

    auth, old, _ = _rotating_auth(T0, expires_in_seconds=60)
    store = auth._store  # noqa: SLF001
    store.replace(replace(store.get_by_code("rot"), enabled=False))
    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate("rot", old, protocol=Protocol.TEST)
    assert exc.value.reason == "client_disabled"
