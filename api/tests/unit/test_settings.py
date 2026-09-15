import pytest
from pydantic import ValidationError

from app.core.settings import AppEnv, Settings


def test_local_fills_a_dev_jwt_secret() -> None:
    settings = Settings(_env_file=None, app_env=AppEnv.local, jwt_secret="")
    assert settings.jwt_secret
    assert settings.is_deployed is False


@pytest.mark.parametrize("env", [AppEnv.staging, AppEnv.production])
def test_deployed_environments_refuse_missing_secrets(env: AppEnv) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET, WORKER_SECRET"):
        Settings(_env_file=None, app_env=env, jwt_secret="", worker_secret="")


def test_deployed_environment_starts_with_all_secrets() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnv.production,
        jwt_secret="x",
        worker_secret="y",
        database_url="postgresql://u:p@h/db",
    )
    assert settings.log_json is True


def test_cors_origins_accept_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins="https://a.com, https://b.com")  # type: ignore[arg-type]
    assert settings.cors_origins == ["https://a.com", "https://b.com"]
