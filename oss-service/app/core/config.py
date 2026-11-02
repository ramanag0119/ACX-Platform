"""OSS microservice configuration, loaded from environment / .env.
 
The OSS service reads the existing, separately shaped OSS PostgreSQL
(device/operations database). Connection details come from environment
variables or a local .env file and must never be hard-coded or logged.
 
When the OSS database is not configured, the service can still start and
serve its health endpoint, while data routes report that the data layer
is not configured.
"""
 
from functools import lru_cache
 
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
 
 
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
 
    APP_NAME: str = "HMS OSS Service"
    APP_ENV: str = "development"
    DEBUG: bool = False
 
    # --- Existing OSS PostgreSQL database ---
    # Prefer discrete settings so passwords with special characters are safe.
    # OSS_DATABASE_URL takes precedence when explicitly provided.
    OSS_DATABASE_URL: str | None = None
    OSS_DB_USER: str | None = None
    OSS_DB_PASSWORD: str | None = None
    OSS_DB_HOST: str | None = None
    OSS_DB_PORT: int = 5432
    OSS_DB_NAME: str | None = None
 
    # Local development should bind to localhost by default.
    HOST: str = "127.0.0.1"
    PORT: int = 8001
 
    # Optional HMS-to-OSS service authentication.
    # Configure the same strong token in both services before enabling
    # authenticated inter-service calls.
    OSS_SERVICE_TOKEN: str | None = None
 
    # Which domains this process serves: any of device, telemetry, alert,
    # energy (comma-separated). PM2 runs one process per domain; the default
    # serves all of them from a single process.
    OSS_DOMAINS: str = "device,telemetry,alert,energy"
 
    @property
    def oss_domains(self) -> list[str]:
        """OSS_DOMAINS parsed into a list of domain names."""
        return [d.strip() for d in self.OSS_DOMAINS.split(",") if d.strip()]
 
    @property
    def oss_database_url(self) -> str | URL | None:
        """Return a SQLAlchemy URL, or None when the OSS DB is unconfigured."""
 
        # An explicitly configured full URL takes precedence.
        if self.OSS_DATABASE_URL:
            return self.OSS_DATABASE_URL
 
        # Build the URL safely from individual settings. URL.create handles
        # special characters in the password without manual URL encoding.
        if (
            self.OSS_DB_HOST
            and self.OSS_DB_NAME
            and self.OSS_DB_USER
        ):
            return URL.create(
                drivername="postgresql+psycopg2",
                username=self.OSS_DB_USER,
                password=self.OSS_DB_PASSWORD or "",
                host=self.OSS_DB_HOST,
                port=self.OSS_DB_PORT,
                database=self.OSS_DB_NAME,
            )
 
        return None
 
    @property
    def is_db_configured(self) -> bool:
        """Indicate whether sufficient settings exist to configure a DB URL."""
        return self.oss_database_url is not None
 
 
@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
 
 
settings = get_settings()