"""Summary and standalone podcast audio (ElevenLabs Eleven v4 dialogue, scripted by an LLM)."""

from __future__ import annotations

import io
import re
import shutil
import time
from pathlib import Path
from typing import Any

import httpx
from moviepy.config import FFMPEG_BINARY
from pydub import AudioSegment

from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.podcast_script import generate_script, split_script
from app.features.media_production.s3 import upload_file
from app.features.media_production.summary_text import format_summary_for_podcast

ELEVENLABS_DIALOGUE_URL = "https://api.elevenlabs.io/v1/text-to-dialogue"
# The dialogue endpoint documents a 2,000 character cap per request; stay inside it
# and join the chunks ourselves.
DIALOGUE_CHUNK_CHARS = 2000
DIALOGUE_STABILITY = 0.5
_SUMMARY_SECTIONS = ("red_flags", "examinations", "brief_management", "psychosocial_aspects")
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 8


def ffmpeg_binary() -> str:
    """The system ffmpeg when there is one, else the copy MoviePy bundles: the api's Railway
    image installs no system packages, so a worker there has only the bundled one."""
    return shutil.which("ffmpeg") or str(FFMPEG_BINARY)


AudioSegment.converter = ffmpeg_binary()


def mp3_audio(mp3: bytes) -> AudioSegment:
    """Decodes mp3 bytes. Naming the codec stops pydub asking ffprobe, which the bundled ffmpeg lacks."""
    return AudioSegment.from_file(io.BytesIO(mp3), format="mp3", codec="mp3")


def _require_av_settings(settings: Settings) -> None:
    """Refuses up front if the API keys or bucket a podcast job needs are not configured,
    rather than failing partway through with a less useful error.
    """
    if not settings.elevenlabs_api_key.strip():
        raise AvUnavailable("ElevenLabs API key is not configured")
    if not settings.openai_api_key.strip() and not settings.anthropic_api_key.strip():
        raise AvUnavailable()
    if not settings.aws_s3_bucket.strip():
        raise AvUnavailable("S3 bucket is not configured")


def _sentences(line: str, limit: int) -> list[str]:
    """`line` cut at sentence ends into pieces of at most `limit` characters."""
    pieces: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", line):
        if current and len(current) + 1 + len(sentence) > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _chunks(turns: list[tuple[str, str]], limit: int = DIALOGUE_CHUNK_CHARS) -> list[list[tuple[str, str]]]:
    """Groups consecutive turns into requests of at most `limit` characters, in order."""
    chunks: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    size = 0
    for speaker, line in turns:
        for piece in _sentences(line, limit):
            if current and size + len(piece) > limit:
                chunks.append(current)
                current, size = [], 0
            if not re.search(r"\w", re.sub(r"\[[^\]]*\]", "", piece)):
                continue  # only a tag or punctuation: ElevenLabs refuses a line with no words
            current.append((speaker, piece))
            size += len(piece)
    if current:
        chunks.append(current)
    return chunks


def _voice_ids(settings: Settings) -> dict[str, str]:
    """The ElevenLabs voice id for each host."""
    return {"Ben": settings.elevenlabs_voice_ben, "Michelle": settings.elevenlabs_voice_michelle}


def dialogue_mp3(settings: Settings, client: httpx.Client, chunk: list[tuple[str, str]]) -> bytes:
    """One chunk of dialogue voiced by both hosts, retrying rate limits and transient errors."""
    voices = _voice_ids(settings)
    body = {
        "inputs": [{"text": line, "voice_id": voices[speaker]} for speaker, line in chunk],
        "model_id": settings.elevenlabs_model_id,
        "settings": {"stability": DIALOGUE_STABILITY},
    }
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        response = client.post(
            ELEVENLABS_DIALOGUE_URL,
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json=body,
        )
        if response.status_code in _RETRY_STATUSES and attempt < _MAX_ATTEMPTS:
            time.sleep(min(2**attempt, 30))
            continue
        if response.status_code >= 400:
            raise AvUnavailable(f"ElevenLabs returned {response.status_code}: {response.text[:300]}")
        return response.content
    raise AvUnavailable("ElevenLabs did not respond")


def synthesize_podcast_mp3(settings: Settings, script: str, work_dir: Path, basename: str) -> Path:
    """Voices the script with ElevenLabs and joins the chunks into one mp3 file."""
    turns = split_script(script)
    if not turns:
        raise AvUnavailable("Script did not contain Ben/Michelle dialogue")

    combined = AudioSegment.empty()
    with httpx.Client(timeout=httpx.Timeout(180.0)) as client:
        for chunk in _chunks(turns):
            combined += mp3_audio(dialogue_mp3(settings, client, chunk))
    mp3 = work_dir / f"{basename}.mp3"
    combined.set_frame_rate(44100).set_channels(2).export(mp3, format="mp3", bitrate="192k")
    return mp3


def produce_summary_podcast(
    settings: Settings,
    *,
    title: str,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
    regenerate_script: bool = False,
) -> dict[str, Any]:
    """Scripts and voices a summary item as a Ben-and-Michelle podcast, uploads the mp3, and
    returns the item's content updated with the script, its audio URL, and a completed status.
    """
    _require_av_settings(settings)
    work_dir.mkdir(parents=True, exist_ok=True)
    if not any(content.get(key) for key in _SUMMARY_SECTIONS):
        raise AvUnavailable("Summary has no clinical content to discuss")
    formatted = format_summary_for_podcast(title, content)
    script = content.get("script")
    if regenerate_script or not isinstance(script, str) or not script.strip():
        script = generate_script(settings, formatted)
    safe = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or media_id
    mp3 = synthesize_podcast_mp3(settings, script, work_dir, safe)
    url = upload_file(settings, mp3, f"podcasts/v4/{safe}.mp3")
    return {**content, "script": script, "podcast_url": url, "status": "completed"}


def produce_podcast_episode_audio(
    settings: Settings,
    *,
    title: str,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
    regenerate_script: bool = False,
) -> dict[str, Any]:
    """Scripts and voices a standalone podcast episode, uploads the mp3, and returns the
    item's content updated with the script, its audio URL, and a completed status.
    """
    _require_av_settings(settings)
    work_dir.mkdir(parents=True, exist_ok=True)
    script = content.get("script")
    if regenerate_script or not isinstance(script, str) or not script.strip():
        script = generate_script(settings, str(content.get("body_md") or title))
    safe = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or media_id
    mp3 = synthesize_podcast_mp3(settings, script, work_dir, safe)
    url = upload_file(settings, mp3, f"podcasts/v4/episodes/{media_id}.mp3")
    return {**content, "script": script, "audio_url": url, "status": "completed"}
