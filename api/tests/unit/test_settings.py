import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.settings import AppEnv, Settings

DEPLOYED = dict(
    jwt_secret="x" * 32,
    worker_secret="y",
    database_url="postgresql://u:p@h/db",
    cors_origins=["https://app.example.com"],
    livekit_url="wss://lk.example.com",
    livekit_api_key="k",
    livekit_api_secret="s",
    stripe_webhook_secret="whsec",
    resend_api_key="re",
    openai_api_key="sk",
    # A structurally valid Fernet key (32 raw bytes, base64 urlsafe-encoded),
    # generated the same way `.env.example` tells a deployer to.
    payout_details_key="6cPODgYlKDgonNz1cBKWl39dFazTwpMyf4VLADcjQH8=",
    mfa_secret_key="bYrouRlioj3ZSZOXp3gtQxtfrPzxG_Es6HT95Kajh9Q=",
)


def test_local_fills_working_defaults() -> None:
    settings = Settings(_env_file=None, app_env=AppEnv.local, jwt_secret="")
    assert settings.jwt_secret
    assert settings.database_url.startswith("postgresql")
    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]
    assert settings.is_deployed is False


@pytest.mark.parametrize("env", [AppEnv.staging, AppEnv.production])
def test_deployed_environments_refuse_missing_secrets(env: AppEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """Named one by one, so the message says what to go and set.

    The ambient environment is cleared first: the test suite exports
    `DATABASE_URL` for its container, and a settings test that passes only
    because of that proves nothing about a real deployment.
    """
    for name in ("DATABASE_URL", "CORS_ORIGINS", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET, WORKER_SECRET, DATABASE_URL, CORS_ORIGINS"):
        Settings(_env_file=None, app_env=env, jwt_secret="", worker_secret="")


def test_a_deployed_environment_does_not_inherit_the_local_database() -> None:
    """The old check compared against a non-empty default, so it could never fire."""
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, app_env=AppEnv.production, **{**DEPLOYED, "database_url": ""})


def test_a_deployed_environment_refuses_a_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="32 characters"):
        Settings(_env_file=None, app_env=AppEnv.production, **{**DEPLOYED, "jwt_secret": "short"})


def test_deployed_environment_starts_with_all_secrets() -> None:
    settings = Settings(_env_file=None, app_env=AppEnv.production, **DEPLOYED)
    assert settings.log_json is True
    assert settings.cors_origins == ["https://app.example.com"]


def test_cors_origins_accept_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins="https://a.com, https://b.com")  # type: ignore[arg-type]
    assert settings.cors_origins == ["https://a.com", "https://b.com"]


def test_cors_origins_parse_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The form `.env.example` uses. It used to fail before the validator ran."""
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com,https://b.com")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://a.com", "https://b.com"]


def test_the_example_env_file_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import PROJECT_ROOT

    for name in ("APP_ENV", "DATABASE_URL", "REDIS_URL", "CORS_ORIGINS", "JWT_SECRET", "WORKER_SECRET"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")
    assert settings.app_env is AppEnv.local
    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]


def test_mail_defaults_use_the_one_domain_resend_has_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resend refuses any sender off a domain verified there (403), and it fails
    in the queue where nobody sees it: every email the outbox sent failed once
    while the sender was on a domain that was not the verified one. So the
    sender is only ever a domain verified in Resend, which is osceguide.com.
    The support address is the one platform-web shows people and `.env.example`
    hands a new developer, read from both sources: a domain move that leaves
    either behind sends people to a dead mailbox while CI stays green.

    The addresses are cleared from the environment first: these are the declared
    defaults, so a stale `SUPPORT_EMAIL` on a developer's machine or left behind
    by an earlier test must not decide whether this passes.
    """
    from app.core.settings import PROJECT_ROOT

    monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    settings = Settings(_env_file=None, app_env=AppEnv.local)
    web_support = Path(__file__).parents[3] / "web/src/foundation/support.ts"
    assert settings.email_from == "OSCE Guide <hello@osceguide.com>"
    assert settings.support_email == "hello@osceguide.com"
    shown = re.search(r'SUPPORT_EMAIL = "([^"]+)"', web_support.read_text())
    assert shown and shown.group(1) == settings.support_email
    assert Settings(_env_file=PROJECT_ROOT / ".env.example").support_email == settings.support_email


def test_the_sender_follows_the_support_mailbox_unless_email_from_names_another(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A domain move is one value: the sender is derived from the support
    mailbox, so a new `SUPPORT_EMAIL` cannot leave the sender on a domain
    Resend no longer verifies. An explicit `EMAIL_FROM` still wins, for a
    deployment whose sender and reply-to inbox are different mailboxes.

    Blank is not a value. A space-padded `EMAIL_FROM` is the operator clearing
    it, not a sender, and a blank `SUPPORT_EMAIL` refuses to start rather than
    sending as `OSCE Guide <>`. Both were harmless while the sender carried its
    own literal.
    """
    monkeypatch.setenv("SUPPORT_EMAIL", "help@osceguide.com")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    assert Settings(_env_file=None, app_env=AppEnv.local).email_from == "OSCE Guide <help@osceguide.com>"
    monkeypatch.setenv("EMAIL_FROM", "OSCE Guide <noreply@osceguide.com>")
    settings = Settings(_env_file=None, app_env=AppEnv.local)
    assert settings.email_from == "OSCE Guide <noreply@osceguide.com>"
    assert settings.support_email == "help@osceguide.com"
    monkeypatch.setenv("EMAIL_FROM", "   ")
    assert Settings(_env_file=None, app_env=AppEnv.local).email_from == "OSCE Guide <help@osceguide.com>"
    # The field is named for what it is, so a caller must be able to set it by
    # that name: with only the `EMAIL_FROM` alias, `extra="ignore"` drops this
    # silently and a test would read the derived sender and still pass.
    override = Settings(_env_file=None, app_env=AppEnv.local, email_from_override="Ops <ops@osceguide.com>")
    assert override.email_from == "Ops <ops@osceguide.com>"
    for blank in ("", "   "):
        monkeypatch.setenv("SUPPORT_EMAIL", blank)
        with pytest.raises(ValidationError, match="SUPPORT_EMAIL must not be blank"):
            Settings(_env_file=None, app_env=AppEnv.local)


def test_openai_marks_first_unless_the_provider_is_switched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKING_PRIMARY_PROVIDER", raising=False)
    assert Settings(_env_file=None, app_env=AppEnv.local).marking_primary_provider == "openai"
    monkeypatch.setenv("MARKING_PRIMARY_PROVIDER", "anthropic")
    assert Settings(_env_file=None, app_env=AppEnv.local).marking_primary_provider == "anthropic"


def test_an_unknown_marking_provider_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKING_PRIMARY_PROVIDER", "gemini")
    with pytest.raises(ValidationError, match="marking_primary_provider"):
        Settings(_env_file=None, app_env=AppEnv.local)
