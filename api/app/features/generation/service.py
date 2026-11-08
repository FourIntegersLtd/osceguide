"""Platform-admin content generation. Requires OPENAI_API_KEY in local/deployed env."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exam_settings import ExamSettings
from app.core.jobs import allow_long_idle
from app.core.llm import (
    OPENAI_STRONG,
    NoModelKey,
    claude_reply,
    first_that_answers,
    json_object,
    openai_reply,
)
from app.core.settings import Settings
from app.features.catalog import service as catalog
from app.features.generation import exam_prompts
from app.features.generation.errors import GenerationEmpty, GenerationUnavailable
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
    "- topic (string): the deck's title, 4 to 12 words naming the condition and the clinical "
    "problem. Never the opening words of the request.\n"
    "- about (string, 50-300 chars)\n"
    "- slides (array of objects with title, layout, bullets, highlights, speaker_notes, "
    "optional explanation)\n"
    "Do not include slide_id, timestamps, or audio/video URLs.\n"
)

_PODCAST_JSON_APPENDIX = (
    "\n\nReturn a single JSON object only (no markdown). Keys:\n"
    "- title (string): the episode's title, 4 to 12 words naming the condition and the "
    "clinical problem. Never the opening words of the source material.\n"
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
        session=session,
    )


def _exam_line(exam_code: str | None) -> str:
    """The line telling the model which exam a draft is for, or nothing when none was chosen."""
    return f"Exam: {exam_code}\n\n" if exam_code else ""


_TITLE_SYSTEM = (
    "You name teaching material for UK doctors. Give it a title of 4 to 12 words naming the "
    'condition and the clinical problem, in title case, such as "HRT Bleeding: Spotting on '
    'Sequential Evorel". Never copy the opening words of the material, and never describe the '
    'patient by age. Reply as JSON: {"title": "..."}'
)
_WORDS = re.compile(r"[a-z0-9]+")


def _echoes(title: str, prompt: str) -> bool:
    """True when a title is only the opening words of the request, the way a model that did not
    name the material falls back to it."""
    words = _WORDS.findall(title.lower())
    # Prefix of the text, not of its words: the cut usually falls mid-word ("since then spo").
    return len(words) >= 3 and " ".join(_WORDS.findall(prompt.lower())).startswith(" ".join(words))


async def _titled(
    draft: dict[str, Any], key: str, prompt: str, *, settings: Settings, session: AsyncSession | None
) -> dict[str, Any]:
    """The draft with a real title under `key`: the model's own, or one asked for when it gave none,
    "Untitled", or the opening words of the request."""
    current = str(draft.get(key) or "").strip()
    if current and current != "Untitled" and not _echoes(current, prompt):
        return draft
    reply = await _json_completion(
        settings=settings, system=_TITLE_SYSTEM, user=prompt[:6000], session=session
    )
    title = str(reply.get("title") or "").strip()
    return {**draft, key: title} if title and not _echoes(title, prompt) else draft


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
        session=session,
    )
    return await _titled(normalize_summary_response(raw), "title", prompt, settings=settings, session=session)


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
        session=session,
    )
    return await _titled(normalize_blog_response(raw), "title", prompt, settings=settings, session=session)


async def generate_slide_deck(
    *, prompt: str, exam_code: str | None, session: AsyncSession | None, settings: Settings
) -> dict[str, Any]:
    """Drafts a slide deck, normalised to the platform's slide deck draft keys."""
    system = exam_prompts.slide_system_prompt() + _SLIDE_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}{prompt}",
        session=session,
    )
    deck = normalize_slide_deck_response(raw)
    if not isinstance(deck.get("slides"), list) or not deck["slides"]:
        raise GenerationEmpty()
    return await _titled(deck, "topic", prompt, settings=settings, session=session)


async def generate_podcast(
    *, prompt: str, exam_code: str | None, session: AsyncSession | None, settings: Settings
) -> dict[str, Any]:
    """Drafts a two-host podcast script from source material, normalised to the platform's `script` key."""
    system = exam_prompts.podcast_system_prompt(prompt) + _PODCAST_JSON_APPENDIX
    raw = await _json_completion(
        settings=settings,
        system=system,
        user=f"{_exam_line(exam_code)}Source material:\n{prompt}",
        session=session,
    )
    return await _titled(normalize_podcast_response(raw), "title", prompt, settings=settings, session=session)


# Room for a whole slide deck or script, with Claude's thinking counted in it.
_CLAUDE_MAX_TOKENS = 16_000
_CLAUDE_SECONDS = 300


async def _json_completion(
    *, settings: Settings, system: str, user: str, session: AsyncSession | None
) -> dict[str, Any]:
    """Calls the LLM with the given system and user messages and parses its reply as a JSON object.

    Lifts the request `session`'s idle-in-transaction limit first, since the call can take a minute.
    `session=None` (required, never defaulted) means the caller holds no transaction: nothing to lift.

    Refuses before calling out if no API key is configured, and refuses again if the model's
    reply is not itself a JSON object, so callers never have to guard against a malformed shape.
    Tries `claude-sonnet-5-5` first, falling back to `gpt-6.1-sol` when Claude fails, is cut off
    or does not answer with a JSON object.
    """

    if session is not None:
        await allow_long_idle(session)

    async def from_claude(api_key: str) -> dict[str, Any]:
        """Claude's reply as a JSON object."""
        reply = await claude_reply(
            api_key,
            system=system + "\n\nRespond with a single JSON object and nothing else.",
            messages=[{"role": "user", "content": user}],
            max_tokens=_CLAUDE_MAX_TOKENS,
            timeout=_CLAUDE_SECONDS,
        )
        return _json_object(reply)

    async def from_openai(api_key: str) -> dict[str, Any]:
        """OpenAI's reply as a JSON object, asked when Claude has no key or failed."""
        reply = await openai_reply(
            api_key,
            system=system,
            messages=[{"role": "user", "content": user}],
            model=OPENAI_STRONG,
            timeout=_CLAUDE_SECONDS,
            response_format={"type": "json_object"},
        )
        return _json_object(reply)

    try:
        return await first_that_answers(
            [
                ("claude", settings.anthropic_api_key, from_claude),
                ("openai", settings.openai_api_key, from_openai),
            ]
        )
    except GenerationUnavailable:
        raise
    except NoModelKey as exc:
        raise GenerationUnavailable() from exc
    except Exception as exc:  # noqa: BLE001 - the last provider failing, whatever the SDK raised
        raise GenerationUnavailable("The model did not answer; try again") from exc


def _json_object(text: str) -> dict[str, Any]:
    """The JSON object in a reply, or `GenerationUnavailable`."""
    parsed = json_object(text)
    if parsed is None:
        raise GenerationUnavailable("Model did not return a JSON object")
    return parsed


def podcast_script_prompt(source_text: str) -> str:
    """The Ben and Michelle dialogue prompt, for producing a podcast's audio from a summary."""
    return exam_prompts.podcast_system_prompt(source_text)


def station_system_prompt(exam_settings: ExamSettings, station_subtype: str | None = None) -> str:
    """Exam-level station generation prompt, for other slices to compose with."""
    return exam_prompts.station_system_prompt(exam_settings, station_subtype)


def station_prompt_for_key(prompt_key: str | None) -> str:
    """The station prompt a generation profile key names, for other slices to compose with."""
    return exam_prompts.station_prompt_for_key(prompt_key)


def unknown_prompt_keys(exam_settings: ExamSettings) -> list[str]:
    """The prompt and profile keys in these settings that no prompt registry holds."""
    return exam_prompts.unknown_prompt_keys(exam_settings)
