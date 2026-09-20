"""The agent must start even when nobody polls the HTTP health endpoint."""

from unittest.mock import Mock

from hosting import gunicorn_config, supervisor


def test_gunicorn_starts_supervision_after_worker_initialization(monkeypatch):
    start = Mock()
    monkeypatch.setattr(supervisor, "_start_once", start)

    gunicorn_config.post_worker_init(Mock())

    start.assert_called_once_with()
