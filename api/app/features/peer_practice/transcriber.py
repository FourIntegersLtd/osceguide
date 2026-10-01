"""Turning a recorded peer consultation into text.

Behind `core.ports.Transcriber`, so which service listens is one decision in
one place. Uses the OpenAI client that is already declared and locked, which
keeps the port closed without a new dependency or a second API key.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.ports import TranscriptionFailed
from app.core.settings import get_settings

# A consultation is minutes of speech, and the recording is fetched whole
# before it is sent on. Generous, because the alternative to waiting is
# throwing away the only record of the session.
_FETCH_TIMEOUT = httpx.Timeout(120.0)

# Which model listens is one decision in one place, as `tutor_memory`'s
# summariser is for summaries.
TRANSCRIPTION_MODEL = "gpt-4o-transcribe"


class OpenAITranscriber:
    """A `Transcriber` that fetches the recording and sends it to OpenAI's transcription model."""

    async def transcribe(self, *, audio_url: str) -> str:
        """Fetch the recording at this URL and return its speech as text."""
        audio = await _fetch(audio_url)
        client = _client()

        def call() -> Any:
            """Run the (synchronous) OpenAI transcription call."""
            return client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                # The name is what the API reads the container format from,
                # and LiveKit's audio-only egress writes Ogg.
                file=("consultation.ogg", audio, "audio/ogg"),
                response_format="text",
            )

        try:
            # The OpenAI client is synchronous and this runs inside the job
            # worker's loop, so it goes to a thread rather than blocking every
            # other job on the same worker for the length of a consultation.
            transcription = await asyncio.to_thread(call)
        except Exception as exc:  # noqa: BLE001 - the SDK raises several unrelated types
            raise TranscriptionFailed(f"The transcription service refused the recording: {exc}") from exc

        text = transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
        if not text.strip():
            # Silence is a real outcome — a pair who never spoke — but it is
            # not something to mark, and saying so here means the caller does
            # not have to tell an empty transcript from a failed one.
            raise TranscriptionFailed("The recording contained no speech")
        return str(text)


async def _fetch(audio_url: str) -> bytes:
    """Download the recording's bytes from its URL."""
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise TranscriptionFailed(f"The recording could not be fetched: {exc}") from exc
    return response.content


def _client() -> Any:
    """Build the OpenAI client, refusing early if there is no key or SDK to use it with."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise TranscriptionFailed("No OpenAI key is configured, so nothing can be transcribed")
    try:
        from openai import OpenAI  # optional dependency
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise TranscriptionFailed("The OpenAI SDK is not installed") from exc
    return OpenAI(api_key=settings.openai_api_key)


def build_transcriber() -> OpenAITranscriber:
    """The production `Transcriber` implementation."""
    return OpenAITranscriber()
