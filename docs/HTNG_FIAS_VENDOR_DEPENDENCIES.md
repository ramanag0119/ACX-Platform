# HTNG / FIAS — Vendor Dependencies

Nothing below has been supplied. Each item blocks the named capability; everything
else is implemented and tested on synthetic fixtures.

| # | Needed from vendor | Blocks | Decision |
|---|---|---|---|
| V-1 | Target PMS product, version, hosting | choosing FIAS vs HTNG vs REST | HF-03 / HF-04 |
| V-2 | Official FIAS interface manual + licensed record set | any FIAS record parsing/serialising | HF-11 |
| V-3 | FIAS link rules: listening side, framing, encoding, ACK/NAK, sequence, heartbeat, resync, reconnect | production TCP link behaviour | HF-06 |
| V-4 | FIAS property-code format and case rules | verified mapping behaviour | HF-05 |
| V-5 | HTNG release/profile, WSDL + XSD bundle, operations in scope | any HTNG operation | HF-07 |
| V-6 | HTNG security profile (WS-Security, mTLS, certificates) | HTNG exposure | HF-08 |
| V-7 | Endpoint URLs, network path, IP ranges, TLS termination | connectivity | HF-24 |
| V-8 | Test environment / simulator, test credentials, certification steps | vendor interoperability evidence | HF-09 |
| V-9 | Message examples for every record/operation in scope | contract fixtures | HF-07 / HF-11 |
| V-10 | Room-status, reservation-status and code-list vocabularies | domain mapping | HF-31 / HF-37 |
