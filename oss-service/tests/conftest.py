"""Test-only configuration for the OSS service suite.

WHY THIS FILE EXISTS
--------------------
Every test module builds its client at import time with no auth header::

    client = TestClient(create_app())

`app/api/security.py::require_service_token` activates as soon as
`OSS_SERVICE_TOKEN` is set, so once a real token was configured in
`oss-service/.env` those requests started returning 401 before ever reaching an
adapter -- 21 tests failed on `assert 401 == 200/404/503` or on a `KeyError`
parsing an error envelope. The adapters themselves were never at fault.

WHAT THIS DOES -- AND WHAT IT DELIBERATELY DOES NOT
---------------------------------------------------
`OSS_SERVICE_TOKEN` is blanked in the environment **of the pytest process
only**, before `app.core.config` is first imported. An environment variable
takes precedence over `.env` in pydantic-settings, so the suite runs with the
guard inert while the file on disk keeps its real token.

This changes NOTHING about runtime security:

  * `oss-service/.env` is not read, written or modified here;
  * the running uvicorn/PM2 services load that file and therefore still
    REQUIRE `X-OSS-Service-Token` on every data route;
  * `app/main.py` still refuses to start outside `APP_ENV=development`
    without a token, and that check is untouched.

`tests/test_service_token.py` asserts the guard still rejects/accepts
correctly when a token IS configured, so disabling it here cannot silently
hide a regression in the guard itself.

The same pattern is already used by the HMS backend suite
(`backend/tests/conftest.py`, which pins `OSS_ENABLED=false` before import).
"""

from __future__ import annotations

import os

# MUST happen before any `app.*` import pulls in the cached Settings singleton.
# Forced rather than `setdefault`: the point is to override whatever
# `oss-service/.env` holds, and a stray exported token in a developer shell or
# CI runner would otherwise reintroduce the 401s this file exists to prevent.
os.environ["OSS_SERVICE_TOKEN"] = ""
