"""Platform-admin content generation. Requires OPENAI_API_KEY in local/deployed env."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exam_settings import ExamSettings
from app.core.settings import Settings
from app.features.catalog import service as catalog
from app.features.generation import exam_prompts
from app.features.generation.errors import GenerationUnavailable
from app.features.generation.normalizers import (
    normalize_blog_response,
    normalize_podcast_response,
    normalize_slide_deck_response,
    normalize_summary_response,
)

_STATION_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). Keys:\n"
    "- title (string)\n"
    "- candidate_brief (string)\n"
    "- patient_brief (string)\n"
    "- management_plan (string, optional)\n"
)

_SUMMARY_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). Use summary field names:\n"
    "- name (condition name)\n"
    "- red_flags (array of strings)\n"
    "- examinations (array of strings)\n"
    "- brief_management (array of strings)\n"
    "- psychosocial_aspects (array of strings)\n"
)

_BLOG_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). Keys:\n"
    "- title (string)\n"
    "- content (string, Markdown article body)\n"
    "- url (string, URL slug from title, e.g. top-tips-for-the-sca-exam)\n"
)

_SLIDE_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). AI-generated fields:\n"
    "- topic (string)\n"
    "- about (string, 50-300 chars)\n"
    "- slides (array of objects with title, layout, bullets, highlights, speaker_notes, "
    "optional explanation)\n"
    "Do not include slide_id, timestamps, or audio/video URLs.\n"
)

_PODCAST_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). Keys:\n"
    "- script (string): full Ben/Michelle dialogue as plain text, matching the format "
    "in the system prompt.\n"
)


async def generate_station(
    *,
    prompt: str,
    exam_code: str,
    session: AsyncSession,
    station_subtype: str | None = None,
    settings: Settings,
) -> dict[str, Any]:
    """Drafts a new station for a platform admin to review, as raw JSON matching the station schema.

    The prompt is the one the exam's settings name, or its subtype's when one is given.
    """
    exam_settings = await catalog.exam_settings_for_code(session, exam_code)
    system = exam_prompts.station_system_prompt(exam_settings, station_subtype) + _STATION_JSON_APPENDIX
    return await _json_completion(
        settings=settings,
        system=system,
        user=f"Exam: {exam_code}\n\n{prompt}",
    )


def _exam_line(exam_code: str | None) -> str:
    """The line telling the model which exam a draft is for, or nothing when none was chosen."""
    return f"Exam: {exam_code}\n\n" if exam_code else ""


async def generate_summary(
    *, prompt: str, exam_code: str | None, session: AsyncSession, settings: Settings
) -> dict[str, Any]:
    """Drafts a condition summary, normalised to the platform's summary draft keys."""
    exam_settings = await catalog.exam_settings_for_code(session, exam_code)
    system = exam_prompts.summary_system_prompt(exam_settings) + _SUMMARY_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}{prompt}",
    )
    return normalize_summary_response(raw)


async def generate_blog(
    *, prompt: str, exam_code: str | None, session: AsyncSession, settings: Settings
) -> dict[str, Any]:
    """Drafts a blog post, normalised to the platform's blog draft keys."""
    exam_settings = await catalog.exam_settings_for_code(session, exam_code)
    system = exam_prompts.blog_system_prompt(exam_settings) + _BLOG_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}{prompt}",
    )
    return normalize_blog_response(raw)


async def generate_slide_deck(*, prompt: str, exam_code: str | None, settings: Settings) -> dict[str, Any]:
    """Drafts a slide deck, normalised to the platform's slide deck draft keys."""
    system = exam_prompts.slide_system_prompt() + _SLIDE_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}{prompt}",
    )
    return normalize_slide_deck_response(raw)


async def generate_podcast(*, prompt: str, exam_code: str | None, settings: Settings) -> dict[str, Any]:
    """Drafts a two-host podcast script from source material, normalised to the platform's `script` key."""
    system = exam_prompts.podcast_system_prompt(prompt) + _PODCAST_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}Source material:\n{prompt}",
    )
    return normalize_podcast_response(raw)


GENERATION_MODEL = "o3"
GENERATION_FALLBACK_MODEL = "claude-sonnet-4-5"


async def _json_completion(*, settings: Settings, system: str, user: str) -> dict[str, Any]:
    """Calls the LLM with the given system and user messages and parses its reply as a JSON object.

    Refuses before calling out if no API key is configured, and refuses again if the model's
    reply is not itself a JSON object, so callers never have to guard against a malformed shape.
    Tries `o3` first, falling back to `claude-sonnet-4-5` when the primary fails.
    """
    if not settings.openai_api_key.strip() and not settings.anthropic_api_key.strip():
        raise GenerationUnavailable()

    text: str | None = None
    if settings.openai_api_key.strip():
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.chat.completions.create(
                model=GENERATION_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = response.choices[0].message.content or "{}"
        except Exception:  # noqa: BLE001 - any failure of the first provider falls through to the second
            text = None

    if text is None:
        if not settings.anthropic_api_key.strip():
            raise GenerationUnavailable()
        from anthropic import AsyncAnthropic

        fallback_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        fallback_response = await fallback_client.messages.create(
            model=GENERATION_FALLBACK_MODEL,
            max_tokens=4096,
            system=system + "\n\nRespond with a single JSON object and nothing else.",
            messages=[{"role": "user", "content": user}],
        )
        text = next((block.text for block in fallback_response.content if block.type == "text"), "{}")

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise GenerationUnavailable("Model did not return a JSON object")
    return parsed


def station_system_prompt(exam_settings: ExamSettings, station_subtype: str | None = None) -> str:
    """Exam-level station generation prompt, for other slices to compose with."""
    return exam_prompts.station_system_prompt(exam_settings, station_subtype)


def station_prompt_for_key(prompt_key: str | None) -> str:
    """The station prompt a generation profile key names, for other slices to compose with."""
    return exam_prompts.station_prompt_for_key(prompt_key)


def unknown_prompt_keys(exam_settings: ExamSettings) -> list[str]:
    """The prompt and profile keys in these settings that no prompt registry holds."""
    return exam_prompts.unknown_prompt_keys(exam_settings)
