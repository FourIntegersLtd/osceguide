"""Ben's narration for slide decks: one ElevenLabs line per slide moment, trimmed so that
the length of the file is the length of the speech and nothing else. A line already voiced
into the same folder is reused, so re-rendering a deck's look does not pay for its voice again."""

from __future__ import annotations

import hashlib
import io
import wave
from pathlib import Path

import httpx
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.podcast_tts import dialogue_mp3

SILENCE_THRESHOLD_DBFS = -45.0
LEAD_IN_MS = 40
# A breath between one moment and the next, inside the clip, so cuts never clip a word.
TAIL_PAUSE_MS = 300
SAMPLE_RATE = 44100


def _trim_silence(speech: AudioSegment) -> AudioSegment:
    """Drops the silence ElevenLabs puts before and after a line, keeping a short lead-in."""
    start = detect_leading_silence(speech, silence_threshold=SILENCE_THRESHOLD_DBFS)
    end = detect_leading_silence(speech.reverse(), silence_threshold=SILENCE_THRESHOLD_DBFS)
    voiced = speech[max(0, start - LEAD_IN_MS) : len(speech) - end]
    return voiced if len(voiced) > 0 else speech


def speak(
    settings: Settings, text: str, folder: Path, client: httpx.Client | None = None
) -> tuple[Path, float]:
    """Voices `text` as Ben into a wav file in `folder`; returns the file and its exact length in seconds."""
    if not text.strip():
        raise AvUnavailable("Nothing to narrate")
    destination = folder / f"{hashlib.sha256(text.strip().encode()).hexdigest()[:32]}.wav"
    if destination.exists():
        with wave.open(str(destination), "rb") as stored:
            return destination, stored.getnframes() / stored.getframerate()
    if not settings.elevenlabs_api_key.strip():
        raise AvUnavailable("ELEVENLABS_API_KEY is not set")
    owned = client is None
    http = client or httpx.Client(timeout=httpx.Timeout(180.0))
    try:
        mp3 = dialogue_mp3(settings, http, [("Ben", text.strip())])
    finally:
        if owned:
            http.close()
    speech = _trim_silence(AudioSegment.from_mp3(io.BytesIO(mp3)))
    pause = AudioSegment.silent(duration=TAIL_PAUSE_MS, frame_rate=speech.frame_rate)
    clip = (speech + pause).set_channels(2).set_frame_rate(SAMPLE_RATE).set_sample_width(2)
    # Written under another name first: a half-written file must never be taken for a voiced line.
    partial = destination.with_suffix(".partial")
    clip.export(partial, format="wav")
    partial.replace(destination)
    return destination, clip.frame_count() / SAMPLE_RATE
