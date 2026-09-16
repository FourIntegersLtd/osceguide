"""Application settings.

One `Settings` object, read once from the environment (and `.env` in local
development). Secrets have no defaults outside local/test: the validator at
the bottom refuses to start a staging or production process with a missing
secret, which is how the "worker guard fails open" class of bug is prevented.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    local = "local"
    test = "test"
    staging = "staging"
    production = "production"


_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://staging.osceguide.com",
    "https://osceguide.com",
    "https://www.osceguide.com",
    "https://app.osceguide.com",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.local
    app_name: str = "OSCE Guide Platform API"

    # --- Persistence ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/osce_platform"
    database_pool_size: int = 10
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    redis_disabled: bool = False

    # --- Identity ---
    jwt_secret: str = ""
    jwt_issuer: str = "osce-guide"
    jwt_access_ttl_seconds: int = 15 * 60
    jwt_refresh_ttl_seconds: int = 30 * 24 * 60 * 60

    # --- LiveKit workers calling back into this API ---
    worker_secret: str = ""
    worker_secret_header: str = "X-Worker-Secret"  # noqa: S105 - header name, not a secret

    # --- Background jobs ---
    worker_concurrency: int = 4

    # --- HTTP ---
    cors_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_CORS_ORIGINS))
    frontend_url: str = "http://localhost:3000"

    # --- Observability ---
    log_level: str = "INFO"
    sentry_dsn: str = ""

    @property
    def is_deployed(self) -> bool:
        return self.app_env in (AppEnv.staging, AppEnv.production)

    @property
    def log_json(self) -> bool:
        return self.is_deployed

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # Allow CORS_ORIGINS="https://a.com,https://b.com" in the environment.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _require_secrets_when_deployed(self) -> Settings:
        if self.app_env == AppEnv.local or self.app_env == AppEnv.test:
            if not self.jwt_secret:
                self.jwt_secret = "dev-only-jwt-secret-change-me"  # noqa: S105 - local dev only
            return self
        missing = [
            name
            for name, value in (
                ("JWT_SECRET", self.jwt_secret),
                ("WORKER_SECRET", self.worker_secret),
                ("DATABASE_URL", self.database_url),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                f"{self.app_env.value} requires these environment variables: {', '.join(missing)}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
