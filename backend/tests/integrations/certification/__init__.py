"""TEST-ONLY integration certification harness.

Lives under tests/ on purpose: it is never imported by the application, exposes no
API, and runs only from the CLI (`python -m tests.integrations.certification`) or
pytest. It REUSES the existing adapters, transports, gateway, worker, simulators and
the real HMS stay services; it adds no transport or processing engine of its own.

Synthetic scenarios prove engineering behaviour only. They are never vendor
certification: official-contract scenarios are BLOCKED until vendor documents and
samples exist (HF-06, HF-07, HF-08, HF-11).
"""
