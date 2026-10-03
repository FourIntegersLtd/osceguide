"""Turns a slide deck into a narrated teaching video.

Ben's words are written per slide moment (`slide_narration`), voiced one line at a time
(`slide_voice`) and laid end to end; every row of a slide appears as its own line starts, so
speech and slide cannot drift. The frames are drawn by `slide_scenes` and piped to ffmpeg.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import wave
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.podcast_tts import ffmpeg_binary
from app.features.media_production.s3 import s3_client
from app.features.media_production.slide_narration import (
    is_question,
    item_words,
    narrate_slide,
    plan_deck,
    spoken_notes,
)
from app.features.media_production.slide_scenes import (
    ASSETS,
    COUNTDOWN_SECONDS,
    HEIGHT,
    WIDTH,
    Painter,
    Row,
    Scene,
    resolve_image_path,
)
from app.features.media_production.slide_voice import SAMPLE_RATE, TAIL_PAUSE_MS, speak

logger = logging.getLogger(__name__)

FPS = 24
# A scene opens with a crossfade from the one before, and Ben starts once it has settled.
LEAD_IN = 0.5
CROSSFADE = 0.4
# A row starts to appear just before its line is spoken, and takes this long to settle.
ROW_LEAD = 0.2
ROW_FADE = 0.25
SCENE_TAIL = 0.35
CAPTION_CHARACTERS = 72
# ElevenLabs allows three requests at once.
VOICE_WORKERS = 3
NARRATION_WORKERS = 4
S3_FOLDER = "teaching_videos/v2"

_AUDIO_TAG = re.compile(r"\[[^\]]*\]")


@dataclass
class _Take:
    """One scene, what Ben says over it, and (once scheduled) when everything in it happens."""

    scene: Scene
    lines: list[tuple[str, int | None]]  # what is said, and the row that appears as it starts
    slide: dict[str, Any] | None = None
    rows_from_start: bool = False
    countdown: bool = False
    start: float = 0.0
    duration: float = 0.0
    line_starts: list[float] = field(default_factory=list)
    events: list[tuple[float, int, int]] = field(default_factory=list)  # time, rows shown, active row
    captions: list[tuple[float, float, str]] = field(default_factory=list)
    countdown_at: float | None = None


def _prepare_slide_payload(
    content: dict[str, Any],
    media_id: str,
    exam_code: str | None,
) -> dict[str, Any]:
    """Fills in the fields rendering needs but a stored item may not carry yet: a slide id, an
    exam-derived app type, and a fallback topic taken from the title.
    """
    slide_payload = dict(content)
    slide_payload["slide_id"] = str(slide_payload.get("slide_id") or media_id)
    app_type = slide_payload.get("app_type") or exam_code or "sca"
    slide_payload["app_type"] = str(app_type).lower()
    if not slide_payload.get("topic"):
        slide_payload["topic"] = slide_payload.get("title") or "untitled_slides"
    return slide_payload


# Poppins has no subscript digits; CHA₂DS₂-VASc would draw as boxes.
_PLAIN_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _flowing(text: object) -> str:
    """Text with its stored line breaks and runs of spaces removed (the renderer does the wrapping),
    and subscript digits made plain."""
    return " ".join(str(text or "").translate(_PLAIN_DIGITS).split())


def _rows(slide: dict[str, Any]) -> list[Row]:
    """The slide's bullets as rows, in the order `slide_items` narrates them."""
    strong = tuple(_flowing(phrase) for phrase in slide.get("highlights") or [])
    rows: list[Row] = []
    for bullet in slide.get("bullets") or []:
        text, subs = (
            (bullet.get("text"), bullet.get("sub_bullets") or [])
            if isinstance(bullet, dict)
            else (bullet, [])
        )
        parent = len(rows)
        rows.append(Row(_flowing(text), gap=34, strong=strong))
        for sub in subs:
            sub_text = sub.get("text") if isinstance(sub, dict) else sub
            rows.append(
                Row(
                    _flowing(sub_text),
                    size=33,
                    indent=58,
                    gap=16,
                    marker="dash",
                    parent=parent,
                    strong=strong,
                )
            )
    return rows


def _slide_take(painter: Painter, slide: dict[str, Any], counter: str, deck_dir: Path) -> _Take:
    """One stored slide as a scene with Ben's lines: a list, a paragraph, a question or a bare title."""
    narration = slide["narration"]
    intro, title, rows = narration["intro"], _flowing(slide.get("title")), _rows(slide)
    images = [
        resolve_image_path(str(url), ASSETS / "slides", deck_dir) for url in slide.get("image_urls") or []
    ]
    image_left = slide.get("layout") == "text_image_left"
    if rows:
        callouts = {
            index: (_flowing(entry["value"]), _flowing(entry["label"]))
            for index, entry in enumerate(narration.get("callouts") or [])
            if entry
        }
        scene = Scene(
            painter,
            title=title,
            rows=rows,
            counter=counter,
            callouts=callouts,
            images=images,
            image_left=image_left,
        )
        lines: list[tuple[str, int | None]] = [(intro, None)]
        lines += [(line, index) for index, line in enumerate(narration["items"])]
        return _Take(scene, lines, slide)
    explanation = _flowing(slide.get("explanation"))
    if explanation:
        paragraph = [Row(explanation, marker="")]
        scene = Scene(
            painter, title=title, rows=paragraph, counter=counter, images=images, image_left=image_left
        )
        return _Take(scene, [(intro, None)], slide, rows_from_start=True)
    asks = is_question(slide)
    terms = [Row(_flowing(term)) for term in slide.get("highlights") or [] if _flowing(term)]
    if terms and not asks and not any(path.exists() for path in images):
        # A picture slide whose pictures are missing would be a bare title under Ben's voice:
        # its key terms are shown instead.
        scene = Scene(painter, title=title, rows=terms, counter=counter)
        return _Take(scene, [(intro, None)], slide, rows_from_start=True)
    scene = Scene(
        painter,
        kind="question" if asks else "content",
        title=title,
        eyebrow="Question" if asks else "",
        counter=counter,
        images=images,
    )
    return _Take(scene, [(intro, None)], slide, countdown=asks)


def _storyboard(
    painter: Painter, content: dict[str, Any], plan: dict[str, Any], deck_dir: Path
) -> list[_Take]:
    """Every scene of the talk in order: the slides, a card before each section, the recap, the sign-off."""
    slides = content["slides"]
    sections = {section["before"]: section for section in plan["sections"]}
    numbered = len(slides) + len(sections) + 1
    takes: list[_Take] = []
    for number, slide in enumerate(slides, 1):
        section = sections.get(number)
        if section:
            part = f"Part {list(sections).index(number) + 1} of {len(sections)}"
            card = Scene(
                painter,
                kind="card",
                title=section["title"],
                eyebrow=part,
                counter=f"{len(takes) + 1} / {numbered}",
            )
            takes.append(_Take(card, [(section["line"], None)]))
        takes.append(_slide_take(painter, slide, f"{len(takes) + 1} / {numbered}", deck_dir))
    recap_rows = [
        Row(takeaway["text"], size=46, gap=46, marker=str(number))
        for number, takeaway in enumerate(plan["takeaways"], 1)
    ]
    recap = Scene(
        painter,
        title="Three things to remember",
        rows=recap_rows,
        eyebrow="",
        counter=f"{numbered} / {numbered}",
    )
    recap_lines: list[tuple[str, int | None]] = [(plan["recap_intro"], None)]
    recap_lines += [(takeaway["line"], index) for index, takeaway in enumerate(plan["takeaways"])]
    takes.append(_Take(recap, recap_lines))
    goodbye = Scene(painter, kind="card", title="Thanks for watching", eyebrow="OSCE Guide")
    takes.append(_Take(goodbye, [(plan["signoff"], None)]))
    return takes


def _caption_chunks(text: str, start: float, voiced: float) -> list[tuple[float, float, str]]:
    """Ben's line as short captions, each on screen for its share of the time the line takes.

    The split is by clause and the timing by length, which follows speech closely without
    needing word timestamps from the voice.
    """
    spoken = re.sub(r"\s+([,.;:!?])", r"\1", " ".join(_AUDIO_TAG.sub(" ", text).split()))
    chunks: list[str] = []
    current = ""
    for clause in re.split(r"(?<=[.!?…,;:—–])\s+", spoken):
        pieces = [""]
        for word in clause.split():
            if pieces[-1] and len(pieces[-1]) + 1 + len(word) > CAPTION_CHARACTERS:
                pieces.append("")
            pieces[-1] = f"{pieces[-1]} {word}".strip()
        for piece in pieces:
            if current and len(current) + 1 + len(piece) > CAPTION_CHARACTERS:
                chunks.append(current)
                current = ""
            current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    length = sum(len(chunk) for chunk in chunks) or 1
    timed: list[tuple[float, float, str]] = []
    for chunk in chunks:
        end = start + voiced * len(chunk) / length
        timed.append((start, end, chunk))
        start = end
    return timed


def _voice_lines(settings: Settings, takes: list[_Take], voice_dir: Path) -> dict[str, tuple[Path, float]]:
    """Ben's recording of every distinct line in the talk: its wav file and exact length."""
    voice_dir.mkdir(parents=True, exist_ok=True)
    texts = list(dict.fromkeys(text for take in takes for text, _ in take.lines))
    with httpx.Client(timeout=httpx.Timeout(180.0)) as client, ThreadPoolExecutor(VOICE_WORKERS) as pool:
        voiced = list(pool.map(lambda text: speak(settings, text, voice_dir, client), texts))
    return dict(zip(texts, voiced, strict=True))


def _schedule(
    takes: list[_Take], voiced: dict[str, tuple[Path, float]]
) -> tuple[float, list[tuple[float, Path]]]:
    """Fixes when every scene, row, caption and line of speech happens.

    Returns the talk's length and where each recording sits on the soundtrack.
    """
    clock = 0.0
    soundtrack: list[tuple[float, Path]] = []
    for take in takes:
        take.start = clock
        take.events = [(0.0, len(take.scene.rows), 0)] if take.rows_from_start else [(0.0, 0, -1)]
        local = LEAD_IN
        for text, row in take.lines:
            recording, seconds = voiced[text]
            if row is not None:
                take.events.append((local - ROW_LEAD, row + 1, row))
            take.line_starts.append(local)
            take.captions += _caption_chunks(text, local, seconds - TAIL_PAUSE_MS / 1000)
            soundtrack.append((clock + local, recording))
            local += seconds
        if take.countdown:
            take.countdown_at = local
            local += COUNTDOWN_SECONDS
        take.duration = local + SCENE_TAIL
        clock += take.duration
    return clock, soundtrack


def _write_soundtrack(soundtrack: list[tuple[float, Path]], total: float, destination: Path) -> None:
    """Lays each recording at its exact offset on one wav, silence in between."""
    frame = b"\0" * 4  # one silent stereo 16-bit sample
    with wave.open(str(destination), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        written = 0
        for offset, recording in soundtrack:
            with wave.open(str(recording), "rb") as line:
                if (line.getnchannels(), line.getsampwidth(), line.getframerate()) != (2, 2, SAMPLE_RATE):
                    raise AvUnavailable(f"Unexpected audio format in {recording.name}")
                speech = line.readframes(line.getnframes())
            gap = max(0, round(offset * SAMPLE_RATE) - written)
            out.writeframes(frame * gap + speech)
            written += gap + len(speech) // 4
        out.writeframes(frame * max(0, round(total * SAMPLE_RATE) - written))


def _take_frame(take: _Take, local: float, deck_fraction: float) -> Image.Image:
    """The scene as it looks `local` seconds in."""
    current = max((index for index, event in enumerate(take.events) if event[0] <= local), default=0)
    since, shown, active = local - take.events[current][0], take.events[current][1], take.events[current][2]
    caption = next((text for start, end, text in take.captions if start <= local < end), "")
    image = take.scene.paint(shown, active, caption)
    if current and since < ROW_FADE:
        _, shown_before, active_before = take.events[current - 1]
        image = Image.blend(take.scene.paint(shown_before, active_before, caption), image, since / ROW_FADE)
    remaining = None
    if take.countdown_at is not None and local >= take.countdown_at:
        remaining = max(0.0, COUNTDOWN_SECONDS - (local - take.countdown_at))
    return take.scene.finish(image, local / take.duration, remaining, deck_fraction)


def _frame(takes: list[_Take], starts: list[float], total: float, moment: float) -> Image.Image:
    """The picture at `moment` seconds into the talk, crossfading in from the scene before."""
    index = max(0, bisect_right(starts, moment) - 1)
    take, local = takes[index], moment - starts[index]
    image = _take_frame(take, local, moment / total)
    if index and local < CROSSFADE:
        before = takes[index - 1]
        mix = local / CROSSFADE
        eased = mix * mix * (3 - 2 * mix)
        image = Image.blend(_take_frame(before, before.duration, moment / total), image, eased)
    return image


def _film(takes: list[_Take], total: float, soundtrack: Path, destination: Path) -> None:
    """Draws every frame and has ffmpeg encode them with the soundtrack into an mp4."""
    command = [ffmpeg_binary(), "-y", "-loglevel", "error"]
    command += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-"]
    command += ["-i", str(soundtrack), "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    command += ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"]
    command.append(str(destination))
    starts = [take.start for take in takes]
    encoder_log = destination.with_suffix(".ffmpeg.log")
    with encoder_log.open("wb") as errors:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)  # noqa: S603 - fixed arguments
        try:
            assert encoder.stdin is not None
            for number in range(round(total * FPS)):
                encoder.stdin.write(_frame(takes, starts, total, number / FPS).tobytes())
            encoder.stdin.close()
        except BrokenPipeError:
            pass  # ffmpeg stopped early: its exit code and log say why
        finally:
            status = encoder.wait()
    if status != 0:
        raise AvUnavailable(f"ffmpeg failed: {encoder_log.read_text(errors='replace')[-600:]}")


def upload_video(settings: Settings, video: Path, payload: dict[str, Any]) -> str:
    """Stores the finished video in S3 as a playable mp4 and answers its public URL."""
    topic = re.sub(r"[^a-z0-9_-]", "_", str(payload["topic"]).lower())[:50]
    key = f"{S3_FOLDER}/{payload['app_type']}/{topic}_{payload['slide_id']}.mp4"
    try:
        with video.open("rb") as handle:
            s3_client(settings).upload_fileobj(
                handle, settings.aws_s3_bucket, key, ExtraArgs={"ContentType": "video/mp4"}
            )
    except Exception as error:
        raise AvUnavailable(f"Failed to upload video to S3: {error}") from error
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def _record_timings(take: _Take, voiced: dict[str, tuple[Path, float]]) -> None:
    """Writes onto the stored slide when it and each of its rows are on screen."""
    slide = take.slide
    if slide is None:
        return
    slide["start_time"] = round(take.start, 2)
    slide["end_time"] = round(take.start + take.duration, 2)
    slide["audio_duration"] = round(take.duration, 2)
    slide["intro_duration"] = round(voiced[take.lines[0][0]][1], 2)
    slide["bullet_audio_segments"] = [
        {
            "bullet_index": row,
            "text": text,
            "start_time": round(start, 2),
            "duration": round(voiced[text][1], 2),
        }
        for (text, row), start in zip(take.lines, take.line_starts, strict=True)
        if row is not None
    ]
    slide["has_pause"] = take.countdown
    slide["pause_duration"] = COUNTDOWN_SECONDS if take.countdown else None
    slide["audio_url"] = None


def regenerate_slide_av(
    settings: Settings,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
    exam_code: str | None = None,
    upload: bool = True,
    voice_dir: Path | None = None,
) -> dict[str, Any]:
    """Re-renders a slide deck's narrated video, returning its updated content.

    `work_dir` is emptied first, so a previous, possibly failed, run cannot leave files for
    this one to pick up by accident. Voiced lines are kept in `voice_dir` and reused by text;
    it defaults to a folder inside `work_dir`, which means nothing is reused.
    """
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    payload = _prepare_slide_payload(content, media_id, exam_code)
    slides = payload.get("slides")
    if not isinstance(slides, list) or not slides or not all(isinstance(slide, dict) for slide in slides):
        raise AvUnavailable("This deck has no slides to render")
    payload["slides"] = slides = [dict(slide) for slide in slides]

    with ThreadPoolExecutor(NARRATION_WORKERS) as pool:
        plan = pool.submit(plan_deck, settings, payload)
        words = item_words(slides)
        narrations = list(pool.map(lambda slide: narrate_slide(settings, slide, len(slides), words), slides))
        payload["presentation"] = plan.result()
    for slide, narration in zip(slides, narrations, strict=True):
        slide["narration"] = narration
        # The notes the deck was written from stay as the source of its facts; the notes shown
        # with the slide become what Ben actually says.
        slide.setdefault("source_notes", slide.get("speaker_notes", ""))
        slide["speaker_notes"] = spoken_notes(narration)

    font_dir = Path(settings.media_av_font_dir) if settings.media_av_font_dir.strip() else None
    takes = _storyboard(Painter(font_dir), payload, payload["presentation"], work_dir)
    voiced = _voice_lines(settings, takes, voice_dir or work_dir / "voice")
    total, soundtrack = _schedule(takes, voiced)
    soundtrack_path = work_dir / "soundtrack.wav"
    _write_soundtrack(soundtrack, total, soundtrack_path)
    video = work_dir / f"teaching_video_{payload['slide_id']}.mp4"
    logger.info("Rendering %s: %d scenes, %.0f seconds", video.name, len(takes), total)
    _film(takes, total, soundtrack_path, video)

    for take in takes:
        _record_timings(take, voiced)
    if upload:
        payload["final_video_url"] = upload_video(settings, video, payload)
    payload["total_duration"] = round(total, 2)
    payload["status"] = "completed"
    payload["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {**payload, "local_video_path": str(video)}
