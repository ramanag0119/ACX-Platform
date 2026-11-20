# HTNG / FIAS — Vendor Onboarding Checklist

One copy per vendor / PMS / property. Nothing may be marked "interoperable" until
section E has real vendor test evidence.

## A. Identity and scope

| Item | Value | Evidence (document / email ref) |
|---|---|---|
| Vendor and PMS product name, version | | |
| Hosting (on-prem / cloud) | | |
| Protocol (FIAS / HTNG / other) and version | | |
| Properties in scope + their external property codes | | |
| Property-code format and case rules (HF-05) | | |
| Operations / records in scope, per direction | | |
| System of record per entity (HF-01/HF-02) | | |

## B. Documentation (must be official)

| Item | FIAS | HTNG | Received |
|---|---|---|---|
| Interface manual / specification + licensed record set | ✓ | | ☐ |
| Framing, encoding, ACK/NAK, sequence, heartbeat, resync rules | ✓ | | ☐ |
| Which side listens; reconnect expectations | ✓ | | ☐ |
| WSDL + XSD bundle, SOAP version, namespaces | | ✓ | ☐ |
| Vendor profile (which operations/elements are actually used) | | ✓ | ☐ |
| Security profile (WS-Security, mTLS, certificates) | | ✓ | ☐ |
| Fault / error semantics and retry expectations | ✓ | ✓ | ☐ |
| Sample request/response messages for every operation, incl. error cases | ✓ | ✓ | ☐ |

## C. Connectivity and security

| Item | Value |
|---|---|
| Connection method (TCP client / TCP listener / HTTPS endpoint) | |
| Host / port / URL per environment | |
| Network path (LAN, VPN, public + mTLS), allow-listed IPs (HF-24) | |
| Authentication method; client created via `python -m app.integrations.cli create-client` | |
| Secret delivery channel and storage (HF-22) | |
| Rotation schedule and overlap window | |

## D. HMS configuration

1. DBA has applied the approved migration (HF-39).
2. Client created DISABLED → secret delivered → `enable-client`.
3. Facility mappings created via `POST /api/v1/integrations/mappings` (created disabled) →
   reviewed → `PATCH … {"enabled": true, "reason": …}`.
4. Verified spec / profile encoded with `VERIFIED_OFFICIAL` status and source references
   (`adapters/fias/spec.py` or a `SchemaProfile`).
5. Live writes remain off until HF-01/02/05/19 approved and `INTEGRATION_ACTOR_USER_ID` set.

## E. Contract tests and acceptance

1. Put the vendor's official samples under
   `backend/tests/integrations/vendor_contracts/<vendor>/` with a `manifest.json`
   (format in `test_vendor_contracts.py`). They run against the **production** adapters.
2. All cases pass; negative samples produce the documented error codes.
3. Vendor test environment run: link up, inbound samples accepted, outbound samples
   accepted by the vendor, duplicate re-send handled, disconnect/reconnect observed.
4. Record evidence (dates, environment, message ids, vendor sign-off) here.
5. Certification / acceptance criteria from the vendor: ________
