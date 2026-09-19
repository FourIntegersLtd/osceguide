"""Platform-admin content generation. Requires OPENAI_API_KEY in local/deployed env."""

from __future__ import annotations

import json
from typing import Any

from app.core.settings import Settings
from app.features.generation.errors import GenerationUnavailable


async def generate_station(*, prompt: str, exam_code: str, settings: Settings) -> dict[str, Any]:
    return await _json_completion(
        settings=settings,
        system=(
            "You author OSCE clinical stations. Return JSON with keys: "
            "title, candidate_brief, patient_brief, management_plan (optional string)."
        ),
        user=f"Exam: {exam_code}\n\n{prompt}",
    )


async def generate_summary(*, prompt: str, exam_code: str | None, settings: Settings) -> dict[str, Any]:
    exam = exam_code or "sca"
    return await _json_completion(
        settings=settings,
        system=(
            "You author A-to-Z clinical summaries. Return JSON with keys: "
            "title, summary, body_md, red_flags (array), examinations (array), brief_management (array)."
        ),
        user=f"Exam: {exam}\n\n{prompt}",
    )


async def generate_blog(*, prompt: str, exam_code: str | None, settings: Settings) -> dict[str, Any]:
    exam = exam_code or "sca"
    return await _json_completion(
        settings=settings,
        system="You author short medical exam articles. Return JSON with keys: title, summary, body_md.",
        user=f"Exam: {exam}\n\n{prompt}",
    )


async def generate_slide_deck(*, prompt: str, exam_code: str | None, settings: Settings) -> dict[str, Any]:
    exam = exam_code or "sca"
    return await _json_completion(
        settings=settings,
        system=(
            "You author slide decks for medical exams. Return JSON with keys: "
            "title, summary, slides (array of {title, body})."
        ),
        user=f"Exam: {exam}\n\n{prompt}",
    )


async def _json_completion(*, settings: Settings, system: str, user: str) -> dict[str, Any]:
    if not settings.openai_api_key.strip():
        raise GenerationUnavailable()
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or "{}"
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise GenerationUnavailable("Model did not return a JSON object")
    return parsed
