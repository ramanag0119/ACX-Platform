"""Application configuration, loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from app.core.vault import MySQLCredentials, get_mysql_credentials


@lru_cache
def _bss_credentials() -> MySQLCredentials:
    """BSS MySQL credentials, read from the vault once per process.

    Cached because the vault is opened by deriving a key from the master
    password, which is deliberately slow; re-running that per property access
    would make every request pay for it.
    """
    return get_mysql_credentials()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "HMS Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"

    # --- Authentication (Phase 2.4) ---
    # The default below is a DEVELOPMENT-ONLY value. `assert_production_ready()`
    # refuses to let it be used outside development, so it can never silently
    # become a production signing key.
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DEV_JWT_SECRET: ClassVar[str] = "dev-only-insecure-secret-change-me"

    def assert_production_ready(self) -> None:
        """Fail fast rather than sign tokens with the shipped dev secret."""
        if self.APP_ENV != "development" and self.JWT_SECRET_KEY == self.DEV_JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET_KEY is still the development default. "
                "Set it from the environment before running outside development."
            )

    # Origins allowed to call the API from a browser. The default covers the
    # local Vite dev server: vite.config.ts pins port 8080, and 5173 is Vite's
    # own default. Comma-separated so it can be overridden from .env.
    CORS_ORIGINS: str = (
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # --- BSS database: MySQL, and only MySQL ---
    # There is deliberately no engine switch and no generic DATABASE_URL
    # override. A second supported engine is a second runtime path that has to
    # be kept working, and a free-form URL is a way for a stale environment to
    # silently point the application at the retired PostgreSQL `hms_db`. The
    # BSS database of record is MySQL `inspironics_app`; nothing else can be
    # selected from configuration.
    #
    # Host, port, user, password and database name are NOT read from `.env`.
    # They come from the KeePass vault in `backend/etc/` (see app/core/vault.py)
    # and are exposed below as properties, so there is exactly one place a
    # credential can come from and `.env` holds nothing that reaches the
    # database. The MYSQL_* properties keep their old names so existing callers
    # (verify_schema, the scripts, migrations/env.py) are unaffected.
    #
    # The OSS/FleetExplorer database (`insp_iot`, PostgreSQL) is NOT configured
    # here. It belongs to the OSS microservice (`oss-service/`), which owns its
    # own settings and opens it read-only. HMS reaches OSS data over its API.

    @property
    def MYSQL_USER(self) -> str:  # noqa: N802 - kept for call-site compatibility
        return _bss_credentials().username

    @property
    def MYSQL_PASSWORD(self) -> str:  # noqa: N802
        return _bss_credentials().password

    @property
    def MYSQL_HOST(self) -> str:  # noqa: N802
        return _bss_credentials().host

    @property
    def MYSQL_PORT(self) -> int:  # noqa: N802
        return _bss_credentials().port

    @property
    def MYSQL_DATABASE(self) -> str:  # noqa: N802
        return _bss_credentials().database

    # --- MySQL TLS ---
    # Path to the CA bundle that signed the server certificate. With it set,
    # the server certificate is verified. Without it the connection can still
    # be encrypted, but nothing proves who is on the other end -- so that case
    # has to be opted into explicitly via MYSQL_SSL_VERIFY_CERT=false.
    #
    # The path comes from the SAME vault entry as the credential it protects
    # (`MYSQL_BSS` -> `SSL_CA_Path`), so the host, the login and the trust
    # anchor for that host are rotated together. `MYSQL_SSL_CA` in `.env` is
    # kept as an OVERRIDE for a machine whose bundle sits elsewhere; when it is
    # empty -- the normal case -- the vault value is used. Reading the field
    # under a different attribute name is what lets `MYSQL_SSL_CA` below stay
    # the single accessor every caller already uses.
    MYSQL_SSL_CA_OVERRIDE: str = Field(default="", validation_alias="MYSQL_SSL_CA")

    @property
    def MYSQL_SSL_CA(self) -> str:  # noqa: N802 - kept for call-site compatibility
        """The CA bundle path: the `.env` override if set, else the vault's."""
        return self.MYSQL_SSL_CA_OVERRIDE or _bss_credentials().ssl_ca

    #: Verify the server certificate against MYSQL_SSL_CA. Defaults to true so
    #: verification is never silently lost; set false only for local work.
    MYSQL_SSL_VERIFY_CERT: bool = True
    #: Also require the certificate's hostname to match MYSQL_HOST. On by
    #: default, to match MYSQL_SSL_VERIFY_CERT: verifying that a certificate
    #: chains to a trusted CA without also checking WHO it names leaves the
    #: connection open to any host holding some other certificate from that
    #: same CA. Set false only for a host whose certificate does not carry the
    #: address it is reached at, and treat that as a defect to be fixed on the
    #: server rather than a setting to leave off.
    MYSQL_SSL_VERIFY_IDENTITY: bool = True

    # --- OSS (device/operations) microservice dispatch ---
    # When OSS_ENABLED is true, the OSS-surfaced routes forward to the OSS
    # microservice instead of reading them from BSS, and rooms get their
    # devices from `room_device_map`. Default false so HMS runs
    # exactly as before until the OSS service is wired and reachable.
    OSS_ENABLED: bool = False
    OSS_SERVICE_URL: str = "http://127.0.0.1:8001"
    # Per-domain OSS service URLs, for when each domain runs as its own
    # process (ecosystem.config.js sets these). Unset -> OSS_SERVICE_URL.
    OSS_DEVICE_SERVICE_URL: str | None = None
    OSS_TELEMETRY_SERVICE_URL: str | None = None
    OSS_ALERT_SERVICE_URL: str | None = None
    OSS_ENERGY_SERVICE_URL: str | None = None
    OSS_TIMEOUT_SECONDS: float = 5.0

    #: What happens when OSS cannot answer an OSS-surfaced read.
    #:
    #:   true  (default) -- serve the stored BSS copy and label the response
    #:                      `X-HMS-Data-Source: stored`. A device screen keeps
    #:                      working through an OSS restart.
    #:   false (strict)  -- never read OSS-domain data from MySQL. The request
    #:                      fails with 503 instead, so "OSS data comes only
    #:                      through OSS APIs" holds with no exception.
    #:
    #: Strict mode is what the final MySQL cleanup requires: once the stored
    #: copies are dropped there is nothing to fall back TO, so the fallback must
    #: be switched off BEFORE those tables are removed, not after. Defaulted to
    #: true because that is the behaviour already specified and verified; flip
    #: it to false as the first step of the cleanup and confirm nothing breaks.
    #:
    #: Only ever consulted when OSS_ENABLED is true -- with dispatch off, the
    #: local BSS routers serve these paths directly and no fallback exists.
    OSS_FALLBACK_TO_STORED: bool = True
    # Optional inter-service token. Unset by default (trusted-LAN PoC). When set,
    # it is sent as `X-OSS-Service-Token` and the OSS service must be configured
    # with the same value. Never logged.
    OSS_SERVICE_TOKEN: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into the list CORSMiddleware expects."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def oss_url_for(self, domain: str | None) -> str:
        """Base URL of the OSS service for `domain`, falling back to OSS_SERVICE_URL."""
        url = getattr(self, f"OSS_{domain.upper()}_SERVICE_URL", None) if domain else None
        return url or self.OSS_SERVICE_URL

    @property
    def mysql_ssl_args(self) -> dict:
        """PyMySQL TLS keyword arguments for the BSS connection.

        PyMySQL only negotiates TLS when one of `ssl_ca` / `ssl_cert` /
        `ssl_key` / `ssl_verify_cert` / `ssl_verify_identity` is truthy, or
        when `ssl` is a NON-EMPTY dict -- `ssl={}` is falsy and silently
        yields a plaintext socket, which is why the unverified branch below
        passes real keys rather than an empty dict.
        """
        ca_path = self.MYSQL_SSL_CA
        if ca_path:
            # A path that does not resolve is checked HERE rather than left to
            # PyMySQL, which reports a missing bundle as a generic SSL
            # handshake failure -- indistinguishable from a server that is
            # genuinely untrusted, and the one case an operator must not
            # confuse for the other.
            if not Path(ca_path).is_file():
                raise RuntimeError(
                    f"MYSQL_SSL_CA points at {ca_path!r}, which is not a file.\n"
                    "Correct `SSL_CA_Path` on the MYSQL_BSS vault entry (or the "
                    "MYSQL_SSL_CA override in .env) to the PEM bundle that "
                    "signed the server certificate."
                )
            return {
                "ssl_ca": ca_path,
                "ssl_verify_cert": self.MYSQL_SSL_VERIFY_CERT,
                "ssl_verify_identity": self.MYSQL_SSL_VERIFY_IDENTITY,
            }
        if self.MYSQL_SSL_VERIFY_CERT:
            raise RuntimeError(
                "MySQL TLS is required but no CA bundle is configured.\n"
                "Set `SSL_CA_Path` on the MYSQL_BSS vault entry to the PEM file "
                "that signed the server certificate (export it from the MySQL "
                "host, e.g. its `ca.pem`), or set MYSQL_SSL_VERIFY_CERT=false "
                "to accept an encrypted-but-unverified connection for local "
                "work only."
            )
        # Explicitly opted out of verification: still encrypt. A non-empty dict
        # is required here or PyMySQL would fall back to plaintext.
        return {"ssl": {"check_hostname": False, "verify_mode": False}}

    @property
    def sqlalchemy_url(self) -> URL:
        """The one BSS database URL. Always MySQL, built from the vault entry.

        `URL.create` escapes the password, so `@`, `!`, `*`, `#` are safe, and
        SQLAlchemy masks it in `repr()` so it cannot leak through a traceback.
        """
        creds = _bss_credentials()
        return URL.create(
            "mysql+pymysql",
            username=creds.username,
            password=creds.password,
            host=creds.host,
            port=creds.port,
            database=creds.database,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
