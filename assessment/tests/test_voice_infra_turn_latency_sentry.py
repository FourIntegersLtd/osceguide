"""Turn detection selection, latency formatting and Sentry init; ported oracles."""

from __future__ import annotations

from voice_infra import sentry
from voice_infra.latency import UserTurnMetrics, format_assistant_latency_log_parts
from voice_infra.turn_handling import turn_detector_version


def _clear(monkeypatch) -> None:
    for var in ("OSCE_LIVEKIT_HOSTING", "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID"):
        monkeypatch.delenv(var, raising=False)


def test_self_hosted_uses_local_mini(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "self-hosted")
    assert turn_detector_version() == "v1-mini"


def test_railway_uses_local_mini_even_if_cloud_declared(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "cloud")
    assert turn_detector_version() == "v1-mini"


def test_cloud_hosting_uses_inference_v1(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "cloud")
    assert turn_detector_version() == "v1"


def test_local_default_is_mini(monkeypatch) -> None:
    _clear(monkeypatch)
    assert turn_detector_version() == "v1-mini"


def test_latency_parts_include_sdk_fields() -> None:
    parts = format_assistant_latency_log_parts(
        room="room-1",
        assistant_report={"e2e_latency": 11.8, "llm_node_ttft": 0.45, "tts_node_ttfb": 0.21, "playback_latency": 0.05},
        user_metrics=UserTurnMetrics(end_of_turn_delay_ms=500.0, transcription_delay_ms=320.0, on_user_turn_completed_delay_ms=12.0),
    )
    assert parts == [
        "room=room-1", "e2e_latency=11800ms", "transcription=320ms", "eou_delay=500ms",
        "user_turn_completed=12ms", "llm_ttft=450ms", "tts_ttfb=210ms", "playback_latency=50ms",
    ]


def test_latency_parts_omit_missing() -> None:
    assert format_assistant_latency_log_parts(room=None, assistant_report={"e2e_latency": 1.5}, user_metrics=UserTurnMetrics()) == ["e2e_latency=1500ms"]


def test_init_sentry_skips_without_dsn(monkeypatch) -> None:
    sentry._reset_for_tests()
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv("SENTRY_VERIFY_ERROR", "1")
    monkeypatch.setattr(sentry, "load_dotenv", lambda: None)
    assert sentry.init_sentry() is False


def test_init_sentry_calls_sdk_once(monkeypatch) -> None:
    sentry._reset_for_tests()
    monkeypatch.setenv("SENTRY_DSN", "https://key@example.ingest.sentry.io/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_VERIFY_ERROR", "1")
    monkeypatch.setattr(sentry, "load_dotenv", lambda: None)
    called: dict = {}
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kwargs: called.update(kwargs))
    tags: dict = {}
    monkeypatch.setattr(sentry.sentry_sdk, "set_tag", lambda k, v: tags.__setitem__(k, v))
    assert sentry.init_sentry(worker="assessment") is True
    assert called["send_default_pii"] is False and called["include_local_variables"] is False
    assert "voice_infra" in called["in_app_include"] and "osce_assessment" in called["in_app_include"]
    assert tags == {"livekit.worker": "assessment"}
    assert sentry.init_sentry() is True
    sentry._reset_for_tests()


def test_verify_error_helper(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_VERIFY_ERROR", "1")
    monkeypatch.setenv("SENTRY_VERIFY_MARKER", "m")
    try:
        sentry.raise_sentry_verify_error_if_requested()
    except RuntimeError as error:
        assert str(error) == "Sentry test error m"
    else:
        raise AssertionError("expected RuntimeError")
    monkeypatch.delenv("SENTRY_VERIFY_ERROR")
    sentry.raise_sentry_verify_error_if_requested()
