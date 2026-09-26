"""Summary and standalone podcast audio (Cartesia + OpenAI script)."""

from __future__ import annotations

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
    if not settings.openai_api_key.strip() or not settings.cartesia_api_key.strip():
        raise AvUnavailable()
    if not settings.aws_s3_bucket.strip():
        raise AvUnavailable("S3 bucket is not configured")


def generate_script(settings: Settings, source_text: str) -> str:
    from openai import OpenAI  # noqa: PLC0415 - optional dependency

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = PODCAST_PROMPT.format(text=source_text)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You create a natural medical podcast between Ben and Michelle (UK GPs). "
                    'Use the format Ben: "..." and Michelle: "...".'
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _split_script(script: str) -> list[tuple[str, str]]:
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
