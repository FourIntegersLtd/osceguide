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
from typing import Annotated

from fastapi import Depends
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

    # LiveKit. `voice_backend_label` is the key the worker looks this API up by
    # in its own VOICE_BACKENDS_JSON, so all three deployments can coexist
    # under different labels during a cutover.
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_routing_mode: str = "self-hosted"
    livekit_token_ttl_seconds: int = 60 * 60
    voice_backend_label: str = "platform"

    # LiveKit Cloud concurrency is metered and shared across every product, so
    # past the cap sessions are served from our own workers rather than
    # refused. Defaults match the legacy backends exactly: the key is shared
    # with them during coexistence, so the numbers have to agree.
    livekit_cloud_overflow_enabled: bool = False
    livekit_cloud_max_concurrent: int = 20
    livekit_cloud_slot_pending_ttl_seconds: int = 300
    livekit_cloud_slot_ttl_seconds: int = 2100

    # Email. Resend is the only provider b2c uses, and the key is the only
    # configuration it needs.
    resend_api_key: str = ""
    email_from: str = "OSCE Guide <noreply@osceguide.com>"

    # Stripe. The webhook secret is per endpoint, and without it webhooks are
    # refused rather than trusted.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Marking. One default for every exam, rather than b2c's gpt-5-mini and
    # b2b's gpt-4o producing results nobody can compare (E-2). The effort is
    # set explicitly: unset means "medium" under any gpt-5 model, which is a
    # cost decision nobody made.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    marking_primary_model: str = "gpt-5-mini"
    marking_primary_effort: str = "low"
    marking_fallback_model: str = "claude-sonnet-4-5"

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


SettingsDep = Annotated[Settings, Depends(get_settings)]
