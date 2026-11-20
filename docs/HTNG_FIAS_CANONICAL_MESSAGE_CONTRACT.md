# HTNG / FIAS — Canonical Message Contract

Source: `backend/app/integrations/core/envelope.py`, `core/hashing.py`, `core/lifecycle.py`.

## 1. `CanonicalEnvelope` (frozen Pydantic v2 model)

| Field | Type / rule | Meaning |
|---|---|---|
| `message_id` | UUID4 | internal id (also DB primary key) |
| `external_message_id` | str ≤128, optional | vendor's id, when the spec defines one |
| `idempotency_key` | str 1–200, **required** | scoped by (client, facility); see §3 |
| `ordering_key` | str 1–200, optional | set by the handler (`MessageHandler.ordering_key`); same (client, facility, key) messages are processed in arrival order (stays: `stay:<external_stay_ref>`) — round 2 |
| `correlation_id` | str ≤64, `[A-Za-z0-9._:-]` | accepted from caller only if safe, else generated |
| `facility_id` | UUID | **resolved** HMS facility — never taken from the payload |
| `client_id` | UUID | authenticated integration client |
| `protocol` | `fias` / `htng` / `test` | |
| `message_type` | `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){0,4}$` | canonical HMS name, not a vendor record name |
| `direction` | `inbound` / `outbound` | |
| `schema_version` | str ≤64 | `<spec name>/<version>` or `<profile>/<version>` |
| `received_at` | aware datetime, normalised to UTC | naive datetimes rejected |
| `payload_ref` | optional | reserved for external payload storage (unused) |
| `payload_hash` | 64 hex | SHA-256 of canonical body bytes |
| `status`, `retry_count`, `error_category`, `trace` | | lifecycle / diagnostics |
| `body` | dict, **excluded from `repr`** | canonical body |

`envelope.metadata()` returns everything except `body` — the only form used for logs and
operational APIs.

Other models: `DecodedMessage` (adapter output, untrusted), `OutboundRequest`,
`IntakeResult` (`accepted` / `duplicate` / `rejected` + safe error dict).

## 2. Canonical message types in use

| Type | Status | Handler |
|---|---|---|
| `stay.check_in` | registered in production runtime; **gated** | `domain/stays.py` |
| `stay.check_out` | registered in production runtime; **gated** | `domain/stays.py` |
| `test.guest_arrival`, `test.guest_departure`, `test.room_state`, `test.receipt` | TEST fixtures only | tests / simulator |

`stay.*` body: `external_stay_ref` (str ≤100, required), `occurred_at` (ISO-8601 with
offset, optional). No vendor message is mapped onto `stay.*` yet: that mapping needs a
verified FIAS record set or HTNG profile.

## 3. Hashing and idempotency

* Canonical JSON: sorted keys, `(",", ":")` separators, UTF-8, no NaN/∞, UUID → str,
  aware datetime → UTC ISO, Decimal → exact string, naive datetime / sets / non-string
  keys rejected.
* `payload_hash = sha256(canonical_json(body))`.
* Idempotency fingerprint = `sha256(canonical_json({"message_type", "body"}))`.
* Same (client, facility, key) + same fingerprint → `duplicate` (original message id).
  Same key + different fingerprint → `idempotency_conflict` (rejected).
* Bodies are stored as canonical **TEXT**, never as MySQL JSON (MySQL re-orders keys —
  demonstrated by `test_mysql_json_type_reorders_keys_which_is_why_bodies_are_stored_as_text`).

## 4. Lifecycle

```text
RECEIVED -> VALIDATED -> PENDING -> PROCESSING -> SUCCEEDED
   |            |                    |  |  ^
   v            v                    |  +--+ (lease expired, re-claimed)
REJECTED     REJECTED                +-> RETRY_WAIT -> PROCESSING
                                     +-> DEAD_LETTER -(redrive)-> PENDING
```

RECEIVED/VALIDATED exist in memory during intake; rejected messages are **not persisted**
(only a metadata audit event for security rejections). Persisted rows start at PENDING.
Transitions are enforced by `assert_transition` in both repositories.

## 5. Error taxonomy (`core/errors.py`)

`transient` (retried, bounded) · `permanent` · `validation` · `protocol` · `security` ·
`conflict` · `unsupported` · `vendor_blocked` · `approval_blocked` · `lease_lost`.
Unknown exceptions → `transient` with only the exception **type** recorded. Error
messages never include payload values.
