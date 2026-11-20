# HTNG / FIAS — HTNG Schema Support

## 1. Documentation gate result

| Searched for | Found |
|---|---|
| HTNG WSDL (`*.wsdl`) | **none** (repo, all branches, workspace) |
| HTNG XSD (`*.xsd`) | **none** |
| Vendor implementation guide / SOAP examples | **none** |
| Security profile (WS-Security, mTLS) | **none** |
| Approved message definitions / version / profile | **none** |

**Conclusion:** no HTNG version, profile, namespace, operation or SOAPAction is claimed.
The production `SchemaRegistry` is empty; the production `HTNGAdapter` is **BLOCKED on
HF-07** (and HF-08 for security).

## 2. Implemented foundation

| Capability | Status | Where |
|---|---|---|
| Safe XML parsing (no DTD/entities, size/depth/element/attribute limits, namespace allow-list) | implemented, tested | `transport/xml_security.py` |
| SOAP 1.1 / 1.2 envelope parse/build, fault parsing (truncated + masked) | implemented, tested | `transport/soap.py` |
| SOAP over HTTP(S) client: HTTPS-only (loopback opt-in for tests), timeouts, error classification | implemented, tested (httpx MockTransport) | `transport/soap.py` |
| Schema profile + registry, versioned (`profile_id/version`), verification gate, production refuses unverified | implemented, tested | `adapters/htng/schema.py` |
| Structural validator (required paths, namespaces) | implemented, tested | `schema.py` |
| XSD validator | **refuses**: needs an XSD library not approved (HF-39) and an approved XSD (HF-07) | `schema.py` |
| `HTNGAdapter` decode/encode/ack via profile | implemented; **blocked in production** | `adapters/htng/adapter.py` |
| Outbound SOAP sender for the outbox | implemented, tested | `adapters/htng/sender.py` |
| Inbound endpoint `POST /api/v1/integrations/htng/inbound` | implemented; **disabled by default** (`INTEGRATION_ENABLED`, `INTEGRATION_HTNG_INBOUND_ENABLED`) | `api/router.py` |

SOAP namespaces used are the W3C ones (`http://schemas.xmlsoap.org/soap/envelope/`,
`http://www.w3.org/2003/05/soap-envelope`); nothing HTNG-specific is hard-coded.

## 3. Generic TEST profile (not HTNG)

`PROVISIONAL_TEST_XML_PROFILE`, namespace `urn:acx:test:generic-xml:v1`,
operations `GuestArrival` (inbound) and `RoomStateNotice` (outbound), status
`PROVISIONAL_TEST`. Tests using it prove the plumbing only; **they are not evidence of
HTNG compatibility.**

## 4. Missing inputs (exact list)

1. HTNG release and message set (e.g. which specification family and version) — HF-07.
2. WSDL + XSD bundle for each operation in scope — HF-07.
3. SOAP version, sync vs async pattern, which side hosts endpoints — HF-07.
4. Security profile: WS-Security token type, signing/encryption, mTLS — HF-08.
5. Vendor endpoint URLs and network path — HF-24.
6. Acknowledgement / response semantics per operation — HF-07.
7. An approved XSD validation library (e.g. `xmlschema` or `lxml`) — HF-39.
8. Vendor test environment and certification process — HF-09.

## 5. To enable HTNG

Register a `SchemaProfile` with `VERIFIED_OFFICIAL` status built from the approved XSDs
(validator = XSD-backed), mappers to canonical `stay.*` types, response builders per the
vendor's acknowledgement rules, then enable the endpoint flags and configure client
credentials and mappings.
