# HTNG / FIAS — Security Design (as implemented)

## 1. Integration client authentication (`security/clients.py`)

* Client = one vendor link: `client_code` + generated secret (`secrets.token_urlsafe(32)`).
* Stored as `sha256$<hex>` — appropriate because secrets are machine-generated 256-bit
  tokens, not passwords. Secrets < 32 or > 512 characters are refused.
* One constant-time comparison per attempt, against a dummy digest for unknown codes.
* Missing store, missing credentials, unknown/disabled client, wrong secret, malformed
  hash, protocol not permitted → **the same** `AuthenticationFailed`; the internal reason
  goes to metrics and the audit trail only.
* No development bypass and no wildcard client exist.
* TCP links authenticate once per link (client bound to the link); HTTP authenticates
  per request via `X-Integration-Client` / `X-Integration-Secret`.
* **Pending:** WS-Security / mTLS for HTNG (HF-08), vendor network path and TLS
  termination (HF-24), credential storage location (HF-22).

## 2. Facility isolation (`security/facility.py`, `exchange/gateway.py`)

* External property code → facility via a mapping **owned by the client**; codes are not
  globally unique (same code maps differently per client — tested).
* Missing / ambiguous / disabled / foreign mapping → rejected (`security` category).
* Exact case matching by default (HF-05 pending). MySQL column uses `utf8mb4_bin` so the
  default case-insensitive collation cannot silently widen matches (tested).
* Scope smuggling: any `facility_id`/`facilityId`/`facility_uuid` or `property_code`/
  `hotelCode` key **at any depth** must match the resolved scope, else rejected.
* A link bound to one property rejects messages naming another.
* Operators: every list/get/redrive/audit query is filtered by `user.facility_ids`;
  out-of-scope records return 404 like missing ones. Idempotency keys are unique per
  (client, facility, key), so keys cannot collide across facilities or clients.

## 3. Operator API authorisation

Existing HMS JWT + `require_permission("facility_management", read|write)`. Read for
inspection, write for redrive. No integration module exists in `role_module`; adding one
is a seed/schema change (HF-39). Redrive requires a 10–500 character reason and writes
an audit event in the same transaction.

## 4. Data protection

* Bodies are excluded from `repr` and from every list endpoint; message detail returns
  `body_masked` only (`core/masking.py`: key-fragment masking + e-mail / long-digit
  scrubbing).
* Logs carry ids, codes and categories only. `test_no_pii_or_secret_in_logs_or_results`
  asserts guest name, e-mail, card number and the client secret appear in no log line,
  intake result, audit row or message listing.
* Sensitive storage is separated: `integration_inbound_payloads` vs metadata table.
  Raw wire bytes are stored only with `INTEGRATION_STORE_RAW_WIRE_PAYLOAD=true`
  (default off). **Encryption at rest and purge (`retain_until`) are not implemented** —
  HF-21.
* SOAP faults from vendors are truncated to 256 characters and masked before use.

## 5. XML security (`transport/xml_security.py`)

Size checked before parsing; expat pre-pass rejects any DOCTYPE, entity declaration,
external entity, and enforces depth/element/attribute limits and a namespace allow-list;
only then does ElementTree build the tree. Covers XXE, billion laughs, parameter
entities, external DTDs (all tested). No new dependency was added.

## 6. Adversarial test coverage

`tests/integrations/test_security.py`, `test_api.py`, `test_htng_adapter.py`:
missing / invalid / disabled / unknown credentials, protocol scoping, unauthorized
facility, payload and nested facility mismatch, link-property override, cross-facility
message access, cross-facility and cross-client idempotency, unauthorized and
out-of-scope redrive, sensitive-data leakage, XXE through the HTTP endpoint.

## 7. Round 2 (2026-11-20) — fixes and additions

| Item | Change | Tests |
|---|---|---|
| D1 audit injection | failed-auth audit stores the client code only if it is well-formed | `test_audit_never_stores_malformed_client_codes` |
| D3 `$` anchoring | `re.match(^…$)` accepted a trailing newline (client codes, property codes, message types, **correlation ids → log/header injection**). All validators now use `fullmatch` | `test_validators_reject_trailing_newline_everywhere`, `test_correlation_id_with_trailing_newline_is_replaced` |
| Credential rotation | previous secret valid only inside a 0–7 day overlap; two constant-time comparisons on every attempt; revoke early; CLI-only, audited, secret never stored or logged | `test_admin.py`, `test_previous_secret_accepted_during_overlap_only` |
| Mapping management | facility-scoped API, created disabled, enable/disable needs a reason, audited in the same transaction | `test_mapping_api_scoped_rbac_and_audit` |
| HTNG rate limit | optional per-client limit (429) | `test_htng_rate_limit_per_client` |
| TCP listener | mandatory peer allow-list, single owner | `test_transport_server.py` |
| Domain audit | `domain.stay.*` audit row committed atomically with the HMS change | `test_handler_audit_is_written_atomically_with_success` |

## 8. Known gaps

HF-08 (HTNG message security, incl. timestamp/nonce replay protection — replay of the
*same* message is covered by idempotency within the retention window), HF-21 (payload
encryption), HF-22 (secret storage), HF-23 (audit retention), HF-24 (network path / TLS
for the TCP link). Rate limiting is per API process.
