# HTNG / FIAS — FIAS Protocol Support Matrix

## 1. Documentation gate result

| Searched for | Where | Found |
|---|---|---|
| Official FIAS manual / interface specification | all branches of this repo; workspace `Insp Total Work/` (depth 6, `*fias*`) | **none** |
| Vendor record definitions / licensed record set | same | **none** |
| Vendor message examples / approved fixtures | same | **none** |
| Earlier internal assumptions | `../HMS-Frontend/ACX-Platform` (untracked earlier work) | yes — audited below |

**Conclusion:** no FIAS behaviour can be verified. `PRODUCTION_SPECIFICATION = None`
(`backend/app/integrations/adapters/fias/spec.py`); the production `FIASAdapter` is
**BLOCKED on HF-11** and refuses every decode/encode.

## 2. What is implemented without vendor semantics

| Capability | Status | Where |
|---|---|---|
| Spec-as-data model (grammar, records, fields, mandatory, length, pattern, direction, idempotency fields, property field) with per-item `VerificationStatus` and `source` | implemented, tested | `spec.py` |
| Generic parser / serializer driven only by the spec | implemented, tested | `codec.py` |
| Rejection of malformed, unknown, unsupported, oversize, badly encoded, control-char, duplicate-field input; values never echoed | implemented, tested | `codec.py` |
| `FIASAdapter` (canonical mapping, idempotency key from declared fields only, link-bound property) | implemented; **blocked in production** | `adapter.py` |
| TCP transport, framing, link supervision | implemented, tested; **no default framing** | `transport/` |

## 3. Protocol support matrix

| Element | Supported in production | Reason |
|---|---|---|
| Framing (start/end markers) | **No** | unverified (HF-06). `DelimitedFramer` requires explicit markers |
| Record grammar (separator, id lengths, encoding) | **No** | unverified |
| Any inbound record | **No** | no verified record list (HF-11; legacy HF-05) |
| Any outbound record | **No** | same |
| ACK/NAK, sequence numbers | **No** | unverified (HF-06); links send nothing automatically |
| Link start/end, heartbeat, resync | **No** | unverified (HF-06) |
| Which side listens | **No** | undecided (HF-06); both `TcpLink` (client) and `TcpListenerLink` (listener) exist |
| Date/time formats, room-status vocabulary | **No** | unverified (HF-30, HF-37) |

## 4. Audit of earlier assumptions

| Assumption (earlier work) | Classification | Kept as |
|---|---|---|
| STX (0x02) / ETX (0x03) framing, "RFC/Standard" | **Provisional test assumption** — no document | TEST framer only (`simulators/fixtures.py`), labelled |
| ACK 0x06 / NAK 0x15 bytes | **Unsupported** | not implemented |
| Record `GI` guest check-in | **Provisional test assumption** | not encoded anywhere |
| Record `GO` guest check-out | **Provisional test assumption** | not encoded |
| Record `GC` guest change | **Provisional test assumption** | not encoded |
| Record `WR` room status | **Provisional test assumption** | not encoded |
| Pipe-delimited fields with 2-char field ids | **Provisional test assumption** | used only by the synthetic TEST grammar |
| Any field-id meanings (RN, GN, …) | **Rejected** for production | synthetic fixtures use deliberately non-FIAS ids |

None was verified by an official document or a vendor example.

## 5. TEST fixture (not FIAS)

`PROVISIONAL_TEST_FIAS_SPEC`: grammar ascii / `|` / 2+2 char ids; records `ZA`
(`test.guest_arrival`), `ZD` (`test.guest_departure`) inbound; `ZS` (`test.room_state`),
`ZK` (`test.receipt`) outbound. Every item `PROVISIONAL_TEST`. A test asserts no `GI/GO/GC/WR`
id is present.

## 6. To enable FIAS

1. Obtain the licensed manual and record list (HF-11, HF-03/04).
2. Encode grammar + records in `spec.py` as `VERIFIED_OFFICIAL` with section references.
3. Add vendor-example fixtures and contract tests per record.
4. Decide link role, heartbeat, ACK and resync; implement a `responder` and listener if needed.
5. Map verified records to canonical `stay.*` types; decide idempotency per record (HF-27).
