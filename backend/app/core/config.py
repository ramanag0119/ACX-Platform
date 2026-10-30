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

    # --- BSS database ---
    # "mysql" (the HMS database of record) or "postgresql" (the original
    # Phase 1.7 target, still supported by the same models and migrations).
    DB_ENGINE: str = "mysql"

    MYSQL_USER: str = "inspironics_app"
    MYSQL_PASSWORD: str = ""
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "inspironics_app"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hms_db"
    POSTGRES_SCHEMA: str = "public"

    DATABASE_URL: str | None = None

    # --- OSS (device/operations) microservice dispatch ---
    # When OSS_ENABLED is true, the OSS-surfaced routes forward to the OSS
    # microservice instead of reading hms_db locally, and rooms get their
    # devices from `room_device_map`. Default false so HMS runs
    # exactly as before until the OSS service is wired and reachable.
    OSS_ENABLED: bool = False
    OSS_SERVICE_URL: str = "http://127.0.0.1:8001"
    OSS_TIMEOUT_SECONDS: float = 5.0
    # Optional inter-service token. Unset by default (trusted-LAN PoC). When set,
    # it is sent as `X-OSS-Service-Token` and the OSS service must be configured
    # with the same value. Never logged.
    OSS_SERVICE_TOKEN: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into the list CORSMiddleware expects."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_mysql(self) -> bool:
        return self.DB_ENGINE == "mysql"

    @property
    def db_schema(self) -> str | None:
        """The schema tables live in. MySQL has none beyond the database itself;
        on PostgreSQL `public` is the default and is left unqualified."""
        if self.is_mysql or self.POSTGRES_SCHEMA == "public":
            return None
        return self.POSTGRES_SCHEMA

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # URL.create escapes the password, so `@`, `!`, `*`, `#` are safe.
        if self.is_mysql:
            return URL.create(
                "mysql+pymysql",
                username=self.MYSQL_USER,
                password=self.MYSQL_PASSWORD,
                host=self.MYSQL_HOST,
                port=self.MYSQL_PORT,
                database=self.MYSQL_DB,
                query={"charset": "utf8mb4"},
            )
        return URL.create(
            "postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
