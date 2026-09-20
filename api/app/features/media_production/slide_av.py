"""Slide deck audio + video regeneration (B2C MoviePy parity via b2c_slide_service)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.features.media_production.b2c_slide_service import SlideService
from app.features.media_production.errors import AvUnavailable


def _prepare_slide_payload(
    content: dict[str, Any],
    media_id: str,
    exam_code: str | None,
) -> dict[str, Any]:
    payload = dict(content)
    payload["slide_id"] = str(payload.get("slide_id") or media_id)
    app_type = payload.get("app_type") or exam_code or "sca"
    payload["app_type"] = str(app_type).lower()
    if not payload.get("topic"):
        payload["topic"] = payload.get("title") or "untitled_slides"
    return payload


def regenerate_slide_av(
    settings: Settings,
    content: dict[str, Any],
    work_dir: Path,
    media_id: str,
    exam_code: str | None = None,
) -> dict[str, Any]:
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    slide_data = _prepare_slide_payload(content, media_id, exam_code)
    svc = SlideService(firestore_service=None, settings=settings)
    svc.slides_base_dir = work_dir

    topic = str(slide_data.get("topic", "untitled_slides"))
    topic_folder = svc._create_topic_folder(topic, media_id)
    json_path = svc._save_slides_json(slide_data, topic_folder, media_id)

    audio_result, audio_code = svc.generate_audio_for_slides(media_id, str(json_path))
    if audio_code != 200:
        message = audio_result.get("error") if isinstance(audio_result, dict) else "Audio generation failed"
        raise AvUnavailable(str(message))

    video_result, video_code = svc.create_video_from_slides(media_id, str(json_path))
    if video_code != 200:
        message = video_result.get("error") if isinstance(video_result, dict) else "Video generation failed"
        raise AvUnavailable(str(message))

    with json_path.open(encoding="utf-8") as handle:
        updated = json.load(handle)

    if isinstance(updated, dict):
        return updated
    return slide_data
