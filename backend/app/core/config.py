"""Application configuration, loaded from environment / .env."""

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hms_db"
    POSTGRES_SCHEMA: str = "public"

    DATABASE_URL: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into the list CORSMiddleware expects."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
