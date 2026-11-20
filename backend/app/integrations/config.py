"""Integration settings, read from the environment with the INTEGRATION_ prefix.

Every switch that could change production behaviour defaults to OFF:

* INTEGRATION_ENABLED               inbound endpoints accept traffic
* INTEGRATION_LIVE_DOMAIN_WRITES    domain adapters may call HMS write services
                                    (ALSO needs HF-01/02/05/19 approved in code,
                                    see app/integrations/domain/approvals.py)
* INTEGRATION_STORE_RAW_WIRE_PAYLOAD keep the raw wire bytes (HF-21 pending)
* INTEGRATION_SIMULATOR_ENABLED     the local test simulators may start
* INTEGRATION_HTNG_INBOUND_ENABLED  the HTNG SOAP inbound endpoint is served
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INTEGRATION_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENABLED: bool = False
    LIVE_DOMAIN_WRITES: bool = False
    STORE_RAW_WIRE_PAYLOAD: bool = False
    SIMULATOR_ENABLED: bool = False
    HTNG_INBOUND_ENABLED: bool = False

    #: Upper bound for one protocol message (one FIAS frame / one SOAP body).
    MAX_MESSAGE_BYTES: int = Field(default=256 * 1024, ge=1024, le=16 * 1024 * 1024)

    #: Worker lease. A worker that has not finished inside this window loses
    #: the message; its late writes are refused by the lease token (fencing).
    WORKER_LEASE_SECONDS: int = Field(default=60, ge=5, le=3600)

    RETRY_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=50)
    RETRY_BASE_SECONDS: float = Field(default=5.0, gt=0, le=3600)
    RETRY_MAX_SECONDS: float = Field(default=900.0, gt=0, le=86400)

    #: HMS app_user that integration-originated writes are stamped with
    #: (created_by / modified_by). HF-18: no integration principal is approved,
    #: so this is unset and live domain writes cannot run without it.
    ACTOR_USER_ID: str | None = None

    #: Delete SUCCEEDED inbound and SENT outbound rows (with payloads and
    #: idempotency keys) older than N days. None = never (HF-21 sets N).
    #: Duplicate protection for a message lasts exactly this long.
    RETENTION_DAYS: int | None = Field(default=None, ge=1, le=3650)

    #: Per-client request limit on the HTNG endpoint, per minute, per API
    #: process. None = no limit. Vendor message volumes are an external
    #: prerequisite (blocker BLK-V7), not an HF decision.
    HTNG_RATE_LIMIT_PER_MINUTE: int | None = Field(default=None, ge=1, le=100000)

    #: Vendor SOAP endpoint for HTNG OUTBOUND delivery (HF-24). None = no
    #: outbound sender: HTNG outbox rows stay PENDING. HTTPS only. Even when set,
    #: the relay registers the sender only if the HTNG adapter is not BLOCKED
    #: (an approved profile, HF-07 / HF-08, is registered).
    HTNG_OUTBOUND_ENDPOINT_URL: str | None = None
    HTNG_OUTBOUND_SOAP_VERSION: Literal["1.1", "1.2"] = "1.1"
    HTNG_OUTBOUND_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=120)

    #: FIAS TCP link owned by the integration service (HF-25 / HF-26). OFF by
    #: default. When ON the service refuses to start unless the link can be
    #: built from APPROVED contracts: a verified FIAS specification (HF-11) and
    #: verified framing / link rules (HF-06). Neither exists today.
    FIAS_LINK_ENABLED: bool = False
    FIAS_LINK_MODE: Literal["client", "listener"] = "client"
    FIAS_LINK_HOST: str | None = None
    FIAS_LINK_PORT: int | None = Field(default=None, ge=1, le=65535)
    #: Listener mode only: IP addresses / CIDR networks allowed to connect.
    FIAS_LINK_ALLOWED_PEERS: list[str] = Field(default_factory=list)
    #: Integration client the link is bound to (authenticated once at start).
    FIAS_LINK_CLIENT_CODE: str | None = None
    FIAS_LINK_CLIENT_SECRET: str | None = None


    @model_validator(mode="after")
    def _consistent(self) -> "IntegrationSettings":
        if self.RETRY_MAX_SECONDS < self.RETRY_BASE_SECONDS:
            raise ValueError("INTEGRATION_RETRY_MAX_SECONDS must be >= INTEGRATION_RETRY_BASE_SECONDS")
        if self.HTNG_INBOUND_ENABLED and not self.ENABLED:
            raise ValueError("INTEGRATION_HTNG_INBOUND_ENABLED requires INTEGRATION_ENABLED")
        if self.HTNG_OUTBOUND_ENDPOINT_URL is not None:
            from urllib.parse import urlsplit

            if urlsplit(self.HTNG_OUTBOUND_ENDPOINT_URL).scheme != "https":
                raise ValueError("INTEGRATION_HTNG_OUTBOUND_ENDPOINT_URL must use https")
        if self.FIAS_LINK_ENABLED:
            if not self.ENABLED:
                raise ValueError("INTEGRATION_FIAS_LINK_ENABLED requires INTEGRATION_ENABLED")
            if self.FIAS_LINK_PORT is None:
                raise ValueError("INTEGRATION_FIAS_LINK_PORT is required when the FIAS link is enabled")
            if self.FIAS_LINK_MODE == "client" and not self.FIAS_LINK_HOST:
                raise ValueError("INTEGRATION_FIAS_LINK_HOST is required in client mode")
            if self.FIAS_LINK_MODE == "listener" and not self.FIAS_LINK_ALLOWED_PEERS:
                raise ValueError("INTEGRATION_FIAS_LINK_ALLOWED_PEERS is required in listener mode")
            if not (self.FIAS_LINK_CLIENT_CODE and self.FIAS_LINK_CLIENT_SECRET):
                raise ValueError("INTEGRATION_FIAS_LINK_CLIENT_CODE / _SECRET are required (link authentication)")
        if self.LIVE_DOMAIN_WRITES and not self.ACTOR_USER_ID:
            raise ValueError("INTEGRATION_LIVE_DOMAIN_WRITES requires INTEGRATION_ACTOR_USER_ID (HF-18)")
        if self.ACTOR_USER_ID:
            import uuid

            try:
                uuid.UUID(self.ACTOR_USER_ID)
            except ValueError:
                raise ValueError("INTEGRATION_ACTOR_USER_ID must be a UUID") from None
        return self


@lru_cache
def get_integration_settings() -> IntegrationSettings:
    return IntegrationSettings()
