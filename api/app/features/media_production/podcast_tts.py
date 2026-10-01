"""Summary and standalone podcast audio (Cartesia + OpenAI script)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pydub import AudioSegment

from app.core.settings import Settings
from app.features.generation.service import PODCAST_PROMPT
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.s3 import upload_file
from app.features.media_production.summary_text import format_summary_for_podcast


def _require_av_settings(settings: Settings) -> None:
    """Refuses up front if the API keys or bucket a podcast job needs are not configured,
    rather than failing partway through with a less useful error.
    """
    if not settings.openai_api_key.strip() or not settings.cartesia_api_key.strip():
        raise AvUnavailable()
    if not settings.aws_s3_bucket.strip():
        raise AvUnavailable("S3 bucket is not configured")


PODCAST_SCRIPT_MODEL = "o3"
PODCAST_SCRIPT_FALLBACK_MODEL = "claude-sonnet-4-5"

logger = logging.getLogger(__name__)

_PODCAST_SYSTEM_PROMPT = (
    "You create a natural medical podcast between Ben and Michelle (UK GPs). "
    'Use the format Ben: "..." and Michelle: "...".'
)


def generate_script(settings: Settings, source_text: str) -> str:
    """Asks the model to turn `source_text` into a two-host Ben-and-Michelle dialogue script.

    Tries `o3` first, falling back to `claude-sonnet-4-5` when the primary fails.
    """
    prompt = PODCAST_PROMPT.format(text=source_text)
    if settings.openai_api_key.strip():
        from openai import OpenAI  # optional dependency

        client = OpenAI(api_key=settings.openai_api_key)
        try:
            response = client.chat.completions.create(
                model=PODCAST_SCRIPT_MODEL,
                messages=[
                    {"role": "system", "content": _PODCAST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            logger.warning(
                "Podcast script generation via %s failed, falling back to %s",
                PODCAST_SCRIPT_MODEL,
                PODCAST_SCRIPT_FALLBACK_MODEL,
                exc_info=True,
            )

    from anthropic import Anthropic  # optional dependency

    fallback_client = Anthropic(api_key=settings.anthropic_api_key)
    fallback_response = fallback_client.messages.create(
        model=PODCAST_SCRIPT_FALLBACK_MODEL,
        max_tokens=4096,
        system=_PODCAST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return next((block.text for block in fallback_response.content if block.type == "text"), "").strip()


def _split_script(script: str) -> list[tuple[str, str]]:
    """Breaks a `Ben: "..."` / `Michelle: "..."` script into (speaker, line) pairs, one per turn."""
    text = re.sub(r"\bben:", "Ben:", script, flags=re.IGNORECASE)
    text = re.sub(r"\bmichelle:", "Michelle:", text, flags=re.IGNORECASE)
    parts = re.split(r"\n*(Ben|Michelle):\s*", text)
    if parts and not parts[0].strip():
        parts = parts[1:]
    segments: list[tuple[str, str]] = []
    for index in range(0, len(parts), 2):
        if index + 1 >= len(parts):
            break
        speaker = parts[index]
        line = parts[index + 1].strip().strip('"')
        if speaker in ("Ben", "Michelle") and line:
            segments.append((speaker, line))
    return segments


def synthesize_podcast_mp3(settings: Settings, script: str, work_dir: Path, basename: str) -> Path:
    """Voices each speaker's turn with Cartesia and stitches the results into one mp3 file."""
    from cartesia import Cartesia

    client = Cartesia(api_key=settings.cartesia_api_key)
    voices = {
        "Ben": "39b376fc-488e-4d0c-8b37-e00b72059fdd",
        "Michelle": "694f9389-aac1-45b6-b726-9d9369183238",
    }
    out_fmt = {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 22050}
    audio_dir = work_dir / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    segments = _split_script(script)
    if not segments:
        raise AvUnavailable("Script did not contain Ben/Michelle dialogue")

    # Voice each turn as its own short wav file first, in speaker order, so a
    # failure partway through only loses the remaining turns, not the ones
    # already synthesised.
    wavs: list[Path] = []
    for index, (speaker, line) in enumerate(segments):
        wav = audio_dir / f"seg_{index}.wav"
        audio_bytes = client.tts.bytes(
            model_id="sonic-2",
            transcript=line,
            voice_id=voices[speaker],
            output_format=out_fmt,
        )
        wav.write_bytes(audio_bytes)
        wavs.append(wav)

    # Concatenate the per-turn wavs in order and export as one mp3.
    combined = AudioSegment.empty()
    for wav in wavs:
        combined += AudioSegment.from_wav(wav)
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
) -> dict[str, Any]:
    """Scripts and voices a summary item as a Ben-and-Michelle podcast, uploads the mp3, and
    returns the item's content updated with the script, its audio URL, and a completed status.
    """
    _require_av_settings(settings)
    work_dir.mkdir(parents=True, exist_ok=True)
    formatted = format_summary_for_podcast(title, content)
    script = content.get("script")
    if not isinstance(script, str) or not script.strip():
        script = generate_script(settings, formatted)
    safe = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or media_id
    mp3 = synthesize_podcast_mp3(settings, script, work_dir, safe)
    key = f"podcasts/{safe}.mp3"
    url = upload_file(settings, mp3, key)
    return {**content, "script": script, "podcast_url": url, "status": "completed"}


def produce_podcast_episode_audio(
    settings: Settings,
    *,
    title: str,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
) -> dict[str, Any]:
    """Scripts and voices a standalone podcast episode, uploads the mp3, and returns the
    item's content updated with the script, its audio URL, and a completed status.
    """
    _require_av_settings(settings)
    work_dir.mkdir(parents=True, exist_ok=True)
    script = content.get("script")
    if not isinstance(script, str) or not script.strip():
        script = generate_script(settings, str(content.get("body_md") or title))
    safe = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or media_id
    mp3 = synthesize_podcast_mp3(settings, script, work_dir, safe)
    key = f"podcasts/episodes/{media_id}.mp3"
    url = upload_file(settings, mp3, key)
    return {**content, "script": script, "audio_url": url, "status": "completed"}
