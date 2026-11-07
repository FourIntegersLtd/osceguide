"""Application settings.

One `Settings` object, read once from the environment (and `.env` in local
development). Secrets and deployment-specific values have no defaults outside
local/test: the validator at the bottom refuses to start a staging or
production process with any of them missing. Local and test get working
defaults filled in by the same validator.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final, Literal

from fastapi import Depends
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core import bucket_layout

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    """Which environment this process is running as."""

    local = "local"
    test = "test"
    staging = "staging"
    production = "production"


# Local development only. Production origins are configuration, not code: a
# deploy that forgot to set CORS_ORIGINS used to accept credentialed requests
# from localhost, and staging accepted production's origin.
_LOCAL_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3100",
    "http://127.0.0.1:3100",
)
_LOCAL_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/osce_platform"
_LOCAL_JWT_SECRET = "dev-only-jwt-secret-change-me"  # noqa: S105 — local and test only
# A real Fernet key (32 url-safe base64 bytes), fixed rather than generated per
# process: local and test data must decrypt the same way across restarts, and
# nobody should mistake this for a secret worth protecting.
_LOCAL_PAYOUT_DETAILS_KEY = "6cPODgYlKDgonNz1cBKWl39dFazTwpMyf4VLADcjQH8="  # noqa: S105
# A different local Fernet key from the payout one, so a dump encrypted under
# one cannot be read as the other during development.
_LOCAL_MFA_SECRET_KEY = "bYrouRlioj3ZSZOXp3gtQxtfrPzxG_Es6HT95Kajh9Q="  # noqa: S105


SENDER_NAME: Final = "OSCE Guide"


# The values a deployed process refuses to start without, named once so the
# validator, `docs/ENVIRONMENT.md` and `.env.example` cannot disagree about
# what they are. The example drifted from this list for weeks.
REQUIRED_WHEN_DEPLOYED: Final[tuple[str, ...]] = (
    "JWT_SECRET",
    "WORKER_SECRET",
    "DATABASE_URL",
    "CORS_ORIGINS",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "STRIPE_WEBHOOK_SECRET",
    "RESEND_API_KEY",
    "OPENAI_API_KEY",
    "PAYOUT_DETAILS_KEY",
    "MFA_SECRET_KEY",
)


class Settings(BaseSettings):
    """Everything the process reads from the environment, in one typed object."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # A field with a `validation_alias` would otherwise be settable only by
        # that alias, and `extra="ignore"` would swallow `Settings(field=...)`
        # in a test without a word.
        populate_by_name=True,
    )

    app_env: AppEnv = AppEnv.local
    app_name: str = "OSCE Guide Platform API"

    # --- Persistence ---
    database_url: str = ""
    database_pool_size: int = 10
    database_echo: bool = False
    database_pool_timeout_seconds: float = 5.0
    database_max_overflow: int = 10
    # True behind PgBouncer in transaction mode: psycopg must not use server-side prepared statements.
    database_pgbouncer: bool = False
    # Direct Postgres for alembic and procrastinate (LISTEN/NOTIFY, DDL); "" => `database_url`.
    database_direct_url: str = ""

    redis_url: str = "redis://localhost:6379/0"
    redis_disabled: bool = False

    # How many proxies of ours sit in front of the app. The rate limiter counts
    # by the address this many hops from the right of `X-Forwarded-For` — the
    # one our own proxy observed — rather than the leftmost, which the caller
    # writes and can forge. 1 matches a single load balancer; raise it only if
    # you actually run more trusted hops. See `core.rate_limit.caller_key`.
    trusted_proxy_hops: int = 1

    # --- Identity ---
    jwt_secret: str = ""
    jwt_issuer: str = "osce-guide"
    jwt_access_ttl_seconds: int = 15 * 60
    # A stream ticket is redeemed the instant it is minted; a minute is for a
    # slow network, not for keeping. See `core.streams`.
    stream_ticket_ttl_seconds: int = 60
    jwt_refresh_ttl_seconds: int = 30 * 24 * 60 * 60

    # --- LiveKit workers calling back into this API ---
    worker_secret: str = ""
    worker_secret_header: str = "X-Worker-Secret"  # noqa: S105 — a header name, not a secret

    # --- The legacy login bridge (deleted at decommission) ---
    # Nobody's password came across in the migration, so a person who already
    # had an account has no credential here. `POST /auth/exchange-legacy`
    # verifies the token their current login gave them and issues a platform
    # pair in return. Named for the two arms the platform serves rather than
    # for the backends being retired, because the vocabulary outlives them.
    # These secrets are read only to *verify*, never to mint, and leaving one
    # unset disables that arm's exchange rather than trusting anything — which
    # is why neither has a default.
    legacy_consumer_jwt_secret: str = ""
    legacy_institution_jwt_secret: str = ""

    # --- The SSO broker (Clerk) ---
    # Partner sign-in is delegated to Clerk, which brokers to the institution's
    # own provider (Microsoft, for the first partner). The secret verifies the
    # session token the callback is handed; the publishable key names the
    # frontend. Neither is one of the required ten: a deployment without them
    # simply cannot offer SSO, and `sso/clerk.py` refuses the flow rather than
    # trusting an unverified token — the same fail-closed shape as Stripe and
    # the worker guard. The organisation's `issuer` carries its Clerk frontend
    # domain, so one secret serves every partner.
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # Direct OIDC to Microsoft Entra, for an institution that brings its own
    # tenant rather than going through Clerk. One multi-tenant app
    # registration serves every institution — `organization_sso.issuer`
    # carries the *institution's* Entra tenant id. Also not one of the
    # required ten; `sso/entra.py` refuses the flow rather than trusting an
    # unverified token, same as Clerk above.
    entra_client_id: str = ""
    entra_client_secret: str = ""

    # LiveKit. `voice_backend_label` is the key the worker looks this API up by
    # in its own VOICE_BACKENDS_JSON, so all three deployments can coexist
    # under different labels during a cutover.
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_routing_mode: str = "self-hosted"
    livekit_agent_namespace: str = ""
    livekit_token_ttl_seconds: int = 60 * 60
    # An exam join token: longer than reading plus one consultation. A connected room is not cut off
    # when it expires, and a dropped candidate fetches a fresh one (`JoinRoom` rejoins on its own).
    livekit_exam_token_ttl_seconds: int = 15 * 60
    # A training token carries the mic right, so a saved one must not outlive a mute or a closed room.
    livekit_training_token_ttl_seconds: int = 300
    voice_backend_label: str = "platform"

    # LiveKit Cloud concurrency is metered and shared across every product, so
    # past the cap sessions are served from our own workers rather than
    # refused. 50 is the LiveKit Cloud Scale plan's Inference concurrency. The
    # legacy backends share this Redis key during coexistence, so their
    # LIVEKIT_CLOUD_MAX_CONCURRENT must agree or they undercount.
    livekit_cloud_overflow_enabled: bool = False
    livekit_cloud_max_concurrent: int = 50
    livekit_cloud_slot_pending_ttl_seconds: int = 300
    livekit_cloud_slot_ttl_seconds: int = 2100

    # Gates `identity.jobs.send_engagement_emails`, the daily nudge to a
    # signed-up person who never ran a practice station. Off by default so a
    # freshly migrated environment — staging, or prod before this ships —
    # cannot fire it on real inboxes until the owner turns it on deliberately.
    engagement_email_enabled: bool = False

    # Our own assessment workers' seats: nodes x LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS
    # in assessment-platform's k8s config (3 x 6 in production). Past these and
    # Cloud's, a candidate waits in line instead of joining a room no worker
    # will take. A waiter whose screen stops refreshing leaves the line after
    # the TTL, which must outlast a stream reconnecting after a network blip.
    livekit_self_hosted_seats: int = 18
    livekit_queue_waiter_ttl_seconds: int = 90

    # Email. Resend refuses a sender off the one domain verified there,
    # osceguide.com, with a 403 — in the queue, where nobody sees it. The
    # sender is the `email_from` property: the support mailbox unless this
    # names another, so a domain move is one value to change.
    resend_api_key: str = ""
    email_from_override: str = Field(default="", validation_alias="EMAIL_FROM")

    # Stripe. The webhook secret is per endpoint, and without it webhooks are
    # refused rather than trusted.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Mixpanel's Query API, read-only, used to corroborate the partner arrival
    # ledger (G-1). Off unless enabled, and a missing secret reports the
    # reconciliation as unconfigured rather than failing: the ledger in this
    # database is what a partner is paid on, Mixpanel only checks it.
    mixpanel_api_secret: str = ""
    mixpanel_query_api_enabled: bool = False

    # A referrer's bank details (A1) are the one plaintext this platform would
    # otherwise store that a database dump could turn straight into fraud, so
    # they are encrypted at rest under this key (Fernet, symmetric). See
    # `app.core.secrets_at_rest`.
    payout_details_key: str = ""

    # Encrypts a TOTP shared secret at rest. A database dump must not hand
    # over the second factor. Recovery codes are hashed, not encrypted.
    # See `app.core.secrets_at_rest`.
    mfa_secret_key: str = ""

    # Marking. One default for every exam, rather than b2c's gpt-5-mini and
    # b2b's gpt-4o producing results nobody can compare (E-2). The effort is
    # set explicitly: unset means "medium" under any gpt-5 model, which is a
    # cost decision nobody made. gpt-6-luna replaced gpt-5-mini (shutdown
    # 2026-12-11) by owner decision 2026-10-31; it marks harsher (bench 2026-10-24).
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # The clinical guideline library (`tutor_memory/guidelines.py`). Both unset means the
    # tutor and the help chat answer from our own material alone.
    clinical_buddy_url: str = "https://api.clinicalbuddy.co.uk"
    clinical_buddy_service_key: str = ""
    # Which provider marks first (scoring and live coverage); the other answers if it fails or has no key.
    marking_llm_timeout_seconds: float = 180.0
    marking_llm_max_retries: int = 2
    marking_primary_provider: Literal["openai", "anthropic"] = "openai"
    marking_primary_model: str = "gpt-6-luna"
    marking_primary_effort: str = "low"
    marking_fallback_model: str = "claude-sonnet-5-5"

    # Slide/podcast audio-video production. Optional: missing values refuse the
    # AV jobs rather than the process. Not in REQUIRED_WHEN_DEPLOYED.
    cartesia_api_key: str = ""
    # Podcast voices. Defaults are ElevenLabs premade British voices (George, Alice);
    # override with voices from your own library.
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_v4"
    elevenlabs_voice_ben: str = "L0Dsvb3SLTyegXwtm47J"
    elevenlabs_voice_michelle: str = "KLON7Nwan8mJxpF2R8Yw"
    aws_region: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    media_av_font_dir: str = ""

    # --- Background jobs ---
    worker_concurrency: int = 4
    # How often an idle worker looks for work that has become due. procrastinate
    # notifies on a job being written, but a job *scheduled* for later cannot be
    # notified about — the worker only finds it by polling. The default of five
    # seconds is fine for marking and much too slow for an examination clock,
    # where it is five seconds of a candidate sitting in silence.
    worker_fetch_job_polling_seconds: float = 1.0
    # How often a worker records that it is alive. The exam-day board calls the
    # worker down after six missed beats.
    worker_heartbeat_seconds: float = 10.0
    # The database's size budget, in MiB: the host's quota (the free plan's 500 MB flips the database
    # read-only). The Ops screen and the daily reading measure against it; 60% writes an audit row,
    # 80% also reports to Sentry.
    database_size_budget_mb: int = 500

    # --- Exam-day capacity (see docs/ENVIRONMENT.md) ---
    # Comma lists. "" for `worker_queues` => every queue; `worker_exclude_queues` is removed from it.
    worker_queues: str = ""
    worker_exclude_queues: str = ""
    sign_in_per_address_per_minute: int = 2000
    auth_status_cache_seconds: int = 30
    library_cache_seconds: int = 300
    outbox_delivery_batch: int = 100
    outbox_send_concurrency: int = 5
    max_request_body_bytes: int = 26 * 1024 * 1024
    sentry_traces_sample_rate: float = 0.05
    attempt_deadline_grace_seconds: int = 120
    # Succeeded jobs, and with them their events, are deleted this many days after they finish. Failed
    # jobs are kept: staff retry them from the Ops screen.
    job_history_retention_days: int = 14

    # --- HTTP ---
    # `NoDecode`: pydantic-settings would otherwise JSON-decode a `list[str]`
    # from the environment before the validator below sees it, so the
    # comma-separated form in `.env.example` failed at startup.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    frontend_url: str = "http://localhost:3000"
    # This API's own public address. SAML needs it: the service provider's
    # entity id and its assertion consumer URL are absolute, are pasted into
    # an institution's IdP, and are checked against every response (E-20).
    public_api_url: str = "http://localhost:8002"
    # Where a safety report (abuse, no-show) lands. The retiring backend sent
    # these straight to an inbox; this queues the same email through the
    # notification outbox rather than an ad-hoc send inside the request.
    support_email: str = "hello@osceguide.com"

    # --- Observability ---
    log_level: str = "INFO"
    sentry_dsn: str = ""
    # The git commit this process was built from. Railway sets
    # RAILWAY_GIT_COMMIT_SHA on every deploy; it is empty locally. `/health`
    # reports it so anyone can see what staging or production is running, and
    # the promote workflow refuses a commit staging is not running.
    git_commit_sha: str = Field(default="", validation_alias="RAILWAY_GIT_COMMIT_SHA")

    @property
    def aws_s3_bucket(self) -> str:
        """The platform's file bucket. Fixed in code (`core.bucket_layout`), never an environment setting."""
        return bucket_layout.BUCKET

    @property
    def is_deployed(self) -> bool:
        return self.app_env in (AppEnv.staging, AppEnv.production)

    @property
    def log_json(self) -> bool:
        return self.is_deployed

    @property
    def email_from(self) -> str:
        """Who the outbox sends as: the support mailbox, unless `EMAIL_FROM` names
        another for a deployment whose sender and reply-to inbox differ."""
        return self.email_from_override.strip() or f"{SENDER_NAME} <{self.support_email}>"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, raw_origins: object) -> object:
        """Accept `CORS_ORIGINS` as a comma-separated string, as `.env` writes it."""
        # Allow CORS_ORIGINS="https://a.com,https://b.com" in the environment.
        if isinstance(raw_origins, str):
            return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        return raw_origins

    @field_validator("support_email")
    @classmethod
    def _refuse_a_blank_support_mailbox(cls, address: str) -> str:
        """Blank was once only a dead reply-to. The sender is derived from it now,
        so it would send every email as `OSCE Guide <>`. Refuse to start instead.
        """
        if not address.strip():
            raise ValueError("SUPPORT_EMAIL must not be blank: the email sender is derived from it")
        return address.strip()

    @model_validator(mode="after")
    def _require_secrets_when_deployed(self) -> Settings:
        """Fill in local/test defaults, or refuse to start a deployed process missing a secret."""
        if self.app_env == AppEnv.local or self.app_env == AppEnv.test:
            self.jwt_secret = self.jwt_secret or _LOCAL_JWT_SECRET
            self.database_url = self.database_url or _LOCAL_DATABASE_URL
            self.cors_origins = self.cors_origins or list(_LOCAL_CORS_ORIGINS)
            self.payout_details_key = self.payout_details_key or _LOCAL_PAYOUT_DETAILS_KEY
            self.mfa_secret_key = self.mfa_secret_key or _LOCAL_MFA_SECRET_KEY
            return self
        present = {
            "JWT_SECRET": self.jwt_secret,
            "WORKER_SECRET": self.worker_secret,
            "DATABASE_URL": self.database_url,
            "CORS_ORIGINS": ",".join(self.cors_origins),
            "LIVEKIT_URL": self.livekit_url,
            "LIVEKIT_API_KEY": self.livekit_api_key,
            "LIVEKIT_API_SECRET": self.livekit_api_secret,
            "STRIPE_WEBHOOK_SECRET": self.stripe_webhook_secret,
            "RESEND_API_KEY": self.resend_api_key,
            "OPENAI_API_KEY": self.openai_api_key,
            "PAYOUT_DETAILS_KEY": self.payout_details_key,
            "MFA_SECRET_KEY": self.mfa_secret_key,
        }
        missing = [name for name in REQUIRED_WHEN_DEPLOYED if not present[name].strip()]
        if missing:
            raise ValueError(
                f"{self.app_env.value} requires these environment variables: {', '.join(missing)}"
            )
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in a deployed environment")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
