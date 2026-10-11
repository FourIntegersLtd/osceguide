"""WebVTT captions for a narrated slide deck, from the timings the render stored.

`slide_av` writes onto each slide when it is on screen (`start_time`), how long Ben's opening
line runs (`intro_duration`) and when and how long each row's line runs
(`bullet_audio_segments`, offsets within the slide). Those are exactly the numbers the burned-in
captions were cut from, so a track built from them matches the picture. A slide missing any of
them gets no cues: a caption at a guessed time is worse than none.
"""

from __future__ import annotations

from typing import Any

from app.features.media_production.slide_av import LEAD_IN, caption_chunks
from app.features.media_production.slide_voice import TAIL_PAUSE_MS


def _stamp(seconds: float) -> str:
    """Write a time in seconds the way a caption file does, as hours:minutes:seconds.milliseconds."""
    millis = round(seconds * 1000)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    return f"{hours:02}:{minutes:02}:{rest // 1000:02}.{rest % 1000:03}"


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _slide_cues(slide: dict[str, Any]) -> list[tuple[float, float, str]]:
    """Every caption line of one slide, as (start, end, text) on the deck's clock."""
    start = _number(slide.get("start_time"))
    intro_seconds = _number(slide.get("intro_duration"))
    intro = (slide.get("narration") or {}).get("intro")
    if start is None or intro_seconds is None or not isinstance(intro, str) or not intro.strip():
        return []
    tail = TAIL_PAUSE_MS / 1000
    lines = [(intro, LEAD_IN, intro_seconds)]
    for segment in slide.get("bullet_audio_segments") or []:
        offset, seconds, text = (
            _number(segment.get("start_time")),
            _number(segment.get("duration")),
            segment.get("text"),
        )
        if offset is None or seconds is None or not isinstance(text, str):
            return []
        lines.append((text, offset, seconds))
    return [
        (start + begin, end + start, chunk)
        for text, offset, seconds in lines
        for begin, end, chunk in caption_chunks(text, offset, seconds - tail)
    ]


def deck_captions_vtt(content: dict[str, Any]) -> str | None:
    """The deck's captions, or `None` when it has no video or no slide carries timings."""
    slides = content.get("slides")
    if not content.get("final_video_url") or not isinstance(slides, list):
        return None
    cues = [cue for slide in slides if isinstance(slide, dict) for cue in _slide_cues(slide)]
    if not cues:
        return None
    body = "\n\n".join(f"{_stamp(begin)} --> {_stamp(end)}\n{text}" for begin, end, text in cues)
    return f"WEBVTT\n\n{body}\n"
