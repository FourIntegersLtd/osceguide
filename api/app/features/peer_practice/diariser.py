"""Recovering who said what from a single mixed recording.

A room-composite egress is one track: both voices, already mixed. Speaker
identity is not in the audio, so it is recovered afterwards from what was
said — a doctor asks the questions, a patient answers them. This is lossy,
knowingly so: per-participant egress would remove the guesswork at the cost
of two uploads to stitch.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.ports import TranscriptionFailed
from app.core.settings import get_settings
from app.features.peer_practice.transcript_prompt import (
    HUMAN_TRANSCRIPT_CONVERSION_PROMPT,
    TURNS_SCHEMA,
)

_TIMEOUT_SECONDS = 180
# Cheap and small on purpose: this is not judgement, it is cutting a block of
# text where a speaker changes.
DIARISATION_MODEL = "gpt-4o-mini"


async def to_turns(raw_transcript: str) -> list[dict[str, str]]:
    """Split raw speech into `doctor` / `patient` turns, in order.

    The roles are named for what `attempts` already understands: its worker
    treats `doctor` as the candidate, so nothing has to be translated between
    here and the marking.
    """
    if not raw_transcript.strip():
        raise TranscriptionFailed("There is no transcript to split into turns")
    client = _client()

    def call() -> str:
        response = client.chat.completions.create(
            model=DIARISATION_MODEL,
            messages=[
                {"role": "system", "content": HUMAN_TRANSCRIPT_CONVERSION_PROMPT},
                {"role": "user", "content": raw_transcript},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "turns", "schema": TURNS_SCHEMA, "strict": False},
            },
            timeout=_TIMEOUT_SECONDS,
        )
        return str(response.choices[0].message.content or "")

    try:
        parsed = json.loads(await asyncio.to_thread(call))
    except Exception as exc:  # noqa: BLE001 - every failure here is the same failure
        raise TranscriptionFailed(f"The transcript could not be split into turns: {exc}") from exc
    return _clean(parsed)


def _clean(parsed: Any) -> list[dict[str, str]]:
    messages = parsed.get("messages") if isinstance(parsed, dict) else None
    if not isinstance(messages, list):
        raise TranscriptionFailed("The diarised transcript was not a list of turns")
    turns: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        message = str(item.get("message") or "").strip()
        # An unknown role is dropped rather than guessed: a patient's words
        # attributed to the doctor would be marked as the doctor's.
        if role in {"doctor", "patient"} and message:
            turns.append({"role": role, "message": message})
    if not turns:
        raise TranscriptionFailed("No turns could be recovered from the transcript")
    return turns


def _client() -> Any:
    settings = get_settings()
    if not settings.openai_api_key:
        raise TranscriptionFailed("No OpenAI key is configured, so turns cannot be recovered")
    try:
        from openai import OpenAI  # noqa: PLC0415 - optional dependency
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise TranscriptionFailed("The OpenAI SDK is not installed") from exc
    return OpenAI(api_key=settings.openai_api_key)
