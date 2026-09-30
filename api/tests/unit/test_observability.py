"""Error reporting starts only when it is configured to.

`SENTRY_DSN` was a setting nothing read: a deployed process reported nothing
anywhere and looked configured. These pin that it is off by default, on when
a DSN is set, and that it never ships a request body.
"""

from __future__ import annotations

import pytest

from app.core import observability
from app.core.settings import AppEnv, Settings


def settings_with(dsn: str, env: AppEnv = AppEnv.test) -> Settings:
    return Settings(app_env=env, sentry_dsn=dsn)


def test_no_dsn_means_no_reporting(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[dict[str, object]] = []
    monkeypatch.setattr(observability, "get_logger", lambda _: _Silent())
    assert observability.configure_sentry(settings_with("")) is False
    assert not called


def test_a_dsn_starts_reporting(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSdk:
        @staticmethod
        def init(**kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", FakeSdk)
    assert observability.configure_sentry(settings_with("https://key@example.test/1")) is True
    assert captured["dsn"] == "https://key@example.test/1"
    assert captured["environment"] == "test"


def test_a_request_body_is_never_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body here holds passwords, legacy tokens and whole transcripts, and
    the SDK's default is to send it."""
    captured: dict[str, object] = {}

    class FakeSdk:
        @staticmethod
        def init(**kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", FakeSdk)
    observability.configure_sentry(settings_with("https://key@example.test/1"))
    assert captured["send_default_pii"] is False
    assert captured["max_request_body_size"] == "never"


class _Silent:
    def warning(self, *args: object, **kwargs: object) -> None:
        return None

    def info(self, *args: object, **kwargs: object) -> None:
        return None
