"""Slide deck audio + video regeneration (B2C MoviePy parity via b2c_slide_service)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable
from app.features.media_production.slide_renderer import SlideService


def _prepare_slide_payload(
    content: dict[str, Any],
    media_id: str,
    exam_code: str | None,
) -> dict[str, Any]:
    """Fills in the fields `SlideService` needs but a stored item may not carry yet: a slide
    id, an exam-derived app type, and a fallback topic taken from the title.
    """
    slide_payload = dict(content)
    slide_payload["slide_id"] = str(slide_payload.get("slide_id") or media_id)
    app_type = slide_payload.get("app_type") or exam_code or "sca"
    slide_payload["app_type"] = str(app_type).lower()
    if not slide_payload.get("topic"):
        slide_payload["topic"] = slide_payload.get("title") or "untitled_slides"
    return slide_payload


def regenerate_slide_av(
    settings: Settings,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
    exam_code: str | None = None,
) -> dict[str, Any]:
    """Re-renders a slide deck's narration audio and video, returning its updated content.

    Delegates the actual rendering to the ported B2C `SlideService`, giving it a clean
    scratch directory each time so a previous, possibly-failed run cannot leave stale files
    behind for the next one to pick up by accident.
    """
    # Start from a clean scratch directory: a previous, possibly-failed run
    # must not leave stale files behind for this one to pick up by accident.
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    slide_data = _prepare_slide_payload(content, media_id, exam_code)
    slide_service = SlideService(settings=settings)
    slide_service.slides_base_dir = work_dir

    topic = str(slide_data.get("topic", "untitled_slides"))
    topic_folder = slide_service._create_topic_folder(topic, media_id)
    json_path = slide_service._save_slides_json(slide_data, topic_folder, media_id)

    # Render narration audio first: the video step reads its output back in.
    audio_result, audio_code = slide_service.generate_audio_for_slides(media_id, str(json_path))
    if audio_code != 200:
        message = audio_result.get("error") if isinstance(audio_result, dict) else "Audio generation failed"
        raise AvUnavailable(str(message))

    video_result, video_code = slide_service.create_video_from_slides(media_id, str(json_path))
    if video_code != 200:
        message = video_result.get("error") if isinstance(video_result, dict) else "Video generation failed"
        raise AvUnavailable(str(message))

    with json_path.open(encoding="utf-8") as handle:
        updated = json.load(handle)

    if isinstance(updated, dict):
        return updated
    return slide_data
