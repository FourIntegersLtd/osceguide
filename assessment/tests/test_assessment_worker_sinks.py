"""Chunks stream best-effort; the completed transcript must be accepted or retried."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from livekit_assessment_worker import sinks
from livekit_assessment_worker.sinks import DeliveryRejected, HttpTranscriptSink
from osce_assessment.contracts import MessageRole, Transcript, TranscriptMessage
from voice_infra import BackendEndpoints

ENDPOINTS = BackendEndpoints(
    label="practice", base_url_env="PRACTICE_URL", secret_env="PRACTICE_SECRET", secret_header="X-Practice-Secret",
    slot_release_path="/r", slot_extend_path="/e", slot_payload_key="room_name",
)
MESSAGE = TranscriptMessage(role=MessageRole.USER, message="Hello", timestamp=datetime(2026, 9, 14, tzinfo=timezone.utc), message_id="m-1", seq=1)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s3cret")


def test_append_posts_one_chunk_with_the_secret_header() -> None:
    post = AsyncMock(return_value=200)
    with patch.object(sinks, "post_json", post):
        asyncio.run(HttpTranscriptSink(ENDPOINTS).append("attempt-1", MESSAGE))
    (url, payload), kwargs = post.call_args
    assert url == "https://api.test/api/worker/attempts/attempt-1/transcript-chunks"
    assert payload == {"attempt_id": "attempt-1", "message": {"role": "user", "message": "Hello", "timestamp": "2026-09-14T00:00:00Z", "message_id": "m-1", "seq": 1}}
    assert kwargs["headers"] == {"X-Practice-Secret": "s3cret"}
    assert kwargs["timeout"] == 5.0


def test_a_rejected_chunk_does_not_interrupt_the_interaction(caplog) -> None:
    with patch.object(sinks, "post_json", AsyncMock(return_value=500)):
        asyncio.run(HttpTranscriptSink(ENDPOINTS).append("attempt-1", MESSAGE))
    assert "chunk seq=1 rejected with HTTP 500" in caplog.text


def test_complete_posts_the_whole_transcript_once() -> None:
    post = AsyncMock(return_value=201)
    transcript = Transcript(attempt_id="attempt-1", messages=[MESSAGE], complete=True)
    with patch.object(sinks, "post_json", post):
        asyncio.run(HttpTranscriptSink(ENDPOINTS).complete("attempt-1", transcript))
    (url, payload), kwargs = post.call_args
    assert url == "https://api.test/api/worker/attempts/attempt-1/transcript"
    assert payload["transcript"]["messages"][0]["message"] == "Hello"
    assert payload["transcript"]["complete"] is True
    assert kwargs["timeout"] == 30.0


def test_a_rejected_transcript_raises_so_the_runtime_retries() -> None:
    transcript = Transcript(attempt_id="attempt-1", messages=[MESSAGE], complete=True)
    with patch.object(sinks, "post_json", AsyncMock(return_value=503)):
        with pytest.raises(DeliveryRejected, match="HTTP 503"):
            asyncio.run(HttpTranscriptSink(ENDPOINTS).complete("attempt-1", transcript))
