# HTNG / FIAS — Certification Scenario Catalog

Generated from the registry (`backend/tests/integrations/certification/`) on 2026-11-20.
"Last run" is the sprint run `--label sprint-full` with the disposable seeded HMS database.

Validation types: **generic transport validation** (wire/SOAP/TCP behaviour, synthetic
messages) · **shared-engine validation** (auth, isolation, idempotency, ordering, retry, DLQ) ·
**HMS workflow validation** (real `stays_write` on a disposable seeded MySQL) · **official
vendor contract validation** (BLOCKED until vendor material exists; can never be PASS).

All HTNG-SYN and FIAS-SYN messages are **synthetic test assumptions** (generic XML namespace
`urn:acx:test:…`, synthetic "Z*" records with STX/ETX *test* markers). They are not HTNG
operations or FIAS records and prove nothing about vendor compatibility.

| ID | Protocol | Validation type | Description | Expected | Requires | Blocked by | Last run |
|---|---|---|---|---|---|---|---|
| FIAS-OFF-001 | fias | official vendor contract validation | Official FIAS record contracts (records, fields, samples) | all_cases=pass | vendor | HF-11 | BLOCKED |
| FIAS-OFF-002 | fias | official vendor contract validation | Official FIAS framing and ACK/NAK behaviour | ack=per manual | vendor | HF-06 | BLOCKED |
| FIAS-OFF-003 | fias | official vendor contract validation | Official FIAS heartbeat, link start-up and resync | link=per manual | vendor | HF-06 | BLOCKED |
| FIAS-SYN-001 | fias | generic transport validation | Valid synthetic frame accepted over TCP and processed | intake=accepted; processing=SUCCEEDED | - | - | PASS |
| FIAS-SYN-002 | fias | generic transport validation | Multiple frames in one TCP write all accepted in order | outcomes=['accepted', 'accepted', 'accepted'] | - | - | PASS |
| FIAS-SYN-003 | fias | generic transport validation | Frame split across several TCP writes reassembled | outcomes=['accepted'] | - | - | PASS |
| FIAS-SYN-004 | fias | generic transport validation | Malformed frame rejected permanently; link continues | outcomes=['rejected', 'accepted']; retryable=False | - | - | PASS |
| FIAS-SYN-005 | fias | generic transport validation | Unsupported encoding: non-ASCII byte rejected; non-ASCII-compatible grammar refused | frame=bad_encoding; grammar=ValueError | - | - | PASS |
| FIAS-SYN-006 | fias | generic transport validation | Oversized frame dropped and counted; link stays up | outcomes=['accepted']; framing_errors=>=1 | - | - | PASS |
| FIAS-SYN-007 | fias | shared-engine validation | Duplicate message detected | second=duplicate | - | - | PASS |
| FIAS-SYN-008 | fias | shared-engine validation | Same-entity messages processed strictly in arrival order (incl. same-instant arrivals) | order=['o-0', 'o-1', 'o-2', 'o-3'] | - | - | PASS |
| FIAS-SYN-009 | fias | generic transport validation | Connection interruption: partial frame discarded, resent frame accepted | outcomes=['accepted']; connections=2 | - | - | PASS |
| FIAS-SYN-010 | fias | generic transport validation | Reconnection after peer disconnect restores the link | connections=>=2; state_after=connected | - | - | PASS |
| FIAS-SYN-011 | fias | shared-engine validation | Database outage during intake: frame retried by the pump, not lost | outcomes=['accepted']; intake_retries=2 | - | - | PASS |
| FIAS-SYN-012 | fias | shared-engine validation | Worker crash: lease expiry hands the message to a healthy worker | crashed_claims=1; final=SUCCEEDED | - | - | PASS |
| FIAS-SYN-013 | fias | shared-engine validation | Wrong property on a property-bound link rejected (security) | code=link_property_mismatch | - | - | PASS |
| FIAS-SYN-014 | fias | shared-engine validation | Invalid client credentials refused for the FIAS protocol | error=AuthenticationFailed | - | - | PASS |
| FIAS-SYN-015 | fias | shared-engine validation | Dead-letter then audited redrive recovers the message | after_failure=DEAD_LETTER; audit=message.redrive; final=SUCCEEDED | - | - | PASS |
| HMS-SYN-001 | hms | HMS workflow validation | Check-in updates the real stay and room, with audit | stay_status=active; room_status=Occupied; audit=domain.stay.check_in | hms_db | - | PASS |
| HMS-SYN-002 | hms | HMS workflow validation | Check-out after check-in closes the stay, with audit | stay_status=checked out; audit=['domain.stay.check_out', 'domain.stay.check_in'] | hms_db | - | PASS |
| HMS-SYN-003 | hms | HMS workflow validation | Duplicate check-in message processed once | second=duplicate; check_in_audits=1 | hms_db | - | PASS |
| HMS-SYN-004 | hms | HMS workflow validation | Check-out before check-in rejected by the real HMS rule; later check-in waits | check_out=DEAD_LETTER/hms_business_rule; check_in=PENDING; stay=pending | hms_db | - | PASS |
| HMS-SYN-005 | hms | HMS workflow validation | Repeated check-in (new message id) for an in-house stay is a no-op | status=SUCCEEDED; already_applied=True; stay=active | hms_db | - | PASS |
| HMS-SYN-006 | hms | HMS workflow validation | Cross-facility event rejected; stay unchanged | intake=rejected/security; stay=unchanged | hms_db | - | PASS |
| HMS-SYN-007 | hms | HMS workflow validation | Audit event carries facility, message, actor and stay reference | audit={'facility': 'matches', 'message_id': 'set', 'actor_type': 'system', 'stay_id': 'set'} | hms_db | - | PASS |
| HMS-SYN-008 | hms | HMS workflow validation | Lost lease rolls back the real HMS change (failed transaction) | lease_lost=1; stay_after_failure=pending; stay_after_recovery=active | hms_db | - | PASS |
| HMS-SYN-009 | hms | HMS workflow validation | Worker crash: lease expiry recovery completes the real check-in | before_expiry=0; stay=active | hms_db | - | PASS |
| HMS-SYN-010 | hms | HMS workflow validation | Retry recovers a transient miss; unknown stay ends in DLQ and is redriven with audit | recovered=SUCCEEDED; unknown=DEAD_LETTER; audit=message.redrive | hms_db | - | PASS |
| HTNG-OFF-001 | htng | official vendor contract validation | Official HTNG operation contracts (decode/encode/ack per vendor profile) | all_cases=pass | vendor | HF-07, HF-08 | BLOCKED |
| HTNG-OFF-002 | htng | official vendor contract validation | Official XSD validation of inbound and outbound messages | all_valid=True | vendor | HF-07, HF-39 | BLOCKED |
| HTNG-SYN-001 | htng | generic transport validation | Valid SOAP 1.1 request accepted and acknowledged | http=200; ack=accepted; soap=1.1 | - | - | PASS |
| HTNG-SYN-002 | htng | generic transport validation | Valid SOAP 1.2 request answered in SOAP 1.2 | http=200; ack=accepted; soap=1.2 | - | - | PASS |
| HTNG-SYN-003 | htng | generic transport validation | SOAP 1.1 fault on rejection | http=401; fault=soap:Client | - | - | PASS |
| HTNG-SYN-004 | htng | generic transport validation | SOAP 1.2 fault on rejection | http=403; fault=env:Sender | - | - | PASS |
| HTNG-SYN-005 | htng | generic transport validation | Invalid XML rejected without persistence | http=400; persisted=0 | - | - | PASS |
| HTNG-SYN-006 | htng | generic transport validation | Unsupported Content-Type rejected (415) | http=415 | - | - | PASS |
| HTNG-SYN-007 | htng | shared-engine validation | Unauthorized client rejected and audited without secret | http=401; audit=client.authentication_failed | - | - | PASS |
| HTNG-SYN-008 | htng | shared-engine validation | Cross-facility request rejected (security) | http=403; persisted=0 | - | - | PASS |
| HTNG-SYN-009 | htng | shared-engine validation | Duplicate request acknowledged as duplicate, stored once | ack=duplicate; messages=1 | - | - | PASS |
| HTNG-SYN-010 | htng | shared-engine validation | Correlation ID propagated to response and stored message; unsafe IDs replaced | echo=True; stored=True; unsafe_replaced=True | - | - | PASS |
| HTNG-SYN-011 | htng | shared-engine validation | Database outage during intake answers 503 (retryable) and stores nothing | http=503 | - | - | PASS |
| HTNG-SYN-012 | htng | shared-engine validation | Transient processing failure retried then recovered | first=RETRY_WAIT; final=SUCCEEDED | - | - | PASS |
| HTNG-SYN-013 | htng | generic transport validation | Malformed SOAP envelope (no Body) rejected | http=400 | - | - | PASS |
| HTNG-SYN-014 | htng | generic transport validation | Unexpected namespace inside the payload rejected | http=400 | - | - | PASS |
| HTNG-SYN-015 | htng | generic transport validation | Structural validation failure (synthetic profile: required element missing) | http=400 | - | - | PASS |
