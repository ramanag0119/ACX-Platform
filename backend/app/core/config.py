"""Application configuration, loaded from environment / .env."""

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


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
    # The OSS/FleetExplorer database (`insp_iot`, PostgreSQL) is NOT configured
    # here. It belongs to the OSS microservice (`oss-service/`), which owns its
    # own settings and opens it read-only. HMS reaches OSS data over its API.
    MYSQL_USER: str = "inspironics_app"
    MYSQL_PASSWORD: str = ""
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "inspironics_app"

    # --- MySQL TLS ---
    # Path to the CA bundle that signed the server certificate. With it set,
    # the server certificate is verified. Without it the connection can still
    # be encrypted, but nothing proves who is on the other end -- so that case
    # has to be opted into explicitly via MYSQL_SSL_VERIFY_CERT=false.
    MYSQL_SSL_CA: str = ""
    #: Verify the server certificate against MYSQL_SSL_CA. Defaults to true so
    #: verification is never silently lost; set false only for local work.
    MYSQL_SSL_VERIFY_CERT: bool = True
    #: Also require the certificate's hostname to match MYSQL_HOST. Off by
    #: default: the server presents MySQL's auto-generated certificate, whose
    #: CN is not a hostname and which carries no SAN, so identity verification
    #: could never succeed against it.
    MYSQL_SSL_VERIFY_IDENTITY: bool = False

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
        if self.MYSQL_SSL_CA:
            return {
                "ssl_ca": self.MYSQL_SSL_CA,
                "ssl_verify_cert": self.MYSQL_SSL_VERIFY_CERT,
                "ssl_verify_identity": self.MYSQL_SSL_VERIFY_IDENTITY,
            }
        if self.MYSQL_SSL_VERIFY_CERT:
            raise RuntimeError(
                "MySQL TLS is required but no CA bundle is configured.\n"
                "Set MYSQL_SSL_CA to the PEM file that signed the server "
                "certificate (export it from the MySQL host, e.g. its "
                "`ca.pem`), or set MYSQL_SSL_VERIFY_CERT=false to accept an "
                "encrypted-but-unverified connection for local work only."
            )
        # Explicitly opted out of verification: still encrypt. A non-empty dict
        # is required here or PyMySQL would fall back to plaintext.
        return {"ssl": {"check_hostname": False, "verify_mode": False}}

    @property
    def sqlalchemy_url(self) -> URL:
        """The one BSS database URL. Always MySQL, built from the parts above.

        `URL.create` escapes the password, so `@`, `!`, `*`, `#` are safe, and
        SQLAlchemy masks it in `repr()` so it cannot leak through a traceback.
        """
        return URL.create(
            "mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=self.MYSQL_PORT,
            database=self.MYSQL_DATABASE,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
