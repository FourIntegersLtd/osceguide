"""Structured parse of station autogeneration: Claude first, OpenAI second."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.llm import OPENAI_STRONG, NoModelKey, claude_reply, first_that_answers
from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.generation.errors import GenerationUnavailable

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class _ParseFailed(Exception):
    """A provider's parse failed; the message is what the caller shows."""


PARSE_TIMEOUT_SEC = 480
# Room for the whole answer. Transcribing a long station document writes most
# of the document back out, which 4096 tokens cut off part-way.
CLAUDE_MAX_TOKENS = 32_000


async def parse_ai_structured(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    settings: Settings,
    openai_model: str = OPENAI_STRONG,
    log_prefix: str = "[PLATFORM_AUTOGENERATE]",
) -> tuple[TModel | None, str]:
    """Structured parse by Claude first, then by OpenAI's `openai_model` when Claude is missing or fails.

    A double failure reports Claude's error, the first provider's.
    """

    claude_failure: list[_ParseFailed] = []

    async def by_claude(api_key: str) -> TModel:
        """Claude's parse, remembering why it failed for the report if OpenAI fails too."""
        try:
            return await _parse_with_anthropic(
                messages, response_model, api_key=api_key, log_prefix=log_prefix
            )
        except _ParseFailed as failure:
            claude_failure.append(failure)
            raise

    async def by_openai(api_key: str) -> TModel:
        """OpenAI's parse, asked when Claude has no key or failed."""
        return await _parse_with_openai(
            messages, response_model, api_key=api_key, model=openai_model, log_prefix=log_prefix
        )

    try:
        parsed = await first_that_answers(
            [
                ("claude", settings.anthropic_api_key, by_claude),
                ("openai", settings.openai_api_key, by_openai),
            ]
        )
    except NoModelKey:
        return None, "No model provider is configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)"
    except _ParseFailed as failure:
        return None, str((claude_failure or [failure])[0])
    return parsed, ""


async def _parse_with_openai(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    api_key: str,
    model: str,
    log_prefix: str,
) -> TModel:
    """Call OpenAI beta.chat.completions.parse; `_ParseFailed` when it fails or parses nothing."""
    from openai import AsyncOpenAI

    try:
        async with AsyncOpenAI(api_key=api_key) as client:
            response = await client.beta.chat.completions.parse(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                response_format=response_model,
                timeout=PARSE_TIMEOUT_SEC,
            )
    except Exception as exc:
        logger.warning(
            "%s structured parse failed model=%s responseModel=%s error=%s",
            log_prefix,
            model,
            response_model.__name__,
            exc,
            exc_info=True,
        )
        raise _ParseFailed(str(exc)) from exc
    parsed = response.choices[0].message.parsed
    if parsed is None:
        refusal = response.choices[0].message.refusal
        raise _ParseFailed(f"Structured parse returned empty: {refusal or 'unknown'}")
    logger.debug(
        "%s parse ok model=%s responseModel=%s finishReason=%s",
        log_prefix,
        model,
        response_model.__name__,
        response.choices[0].finish_reason,
    )
    return parsed


async def _parse_with_anthropic(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    api_key: str,
    log_prefix: str,
) -> TModel:
    """The structured parse by Claude: the response model's schema (a few KB) goes in `output_config`."""
    system = "\n".join(message["content"] for message in messages if message["role"] == "system")
    user_messages = [message for message in messages if message["role"] != "system"]
    try:
        text = await claude_reply(
            api_key,
            system=system,
            messages=user_messages,
            max_tokens=CLAUDE_MAX_TOKENS,
            timeout=PARSE_TIMEOUT_SEC,
            schema=response_model.model_json_schema(),
        )
        parsed = response_model.model_validate_json(text)
    except Exception as exc:
        logger.warning(
            "%s Claude structured parse failed responseModel=%s error=%s",
            log_prefix,
            response_model.__name__,
            exc,
            exc_info=True,
        )
        raise _ParseFailed(str(exc)) from exc
    logger.debug("%s parse ok (claude) responseModel=%s", log_prefix, response_model.__name__)
    return parsed


async def generate_station_autogenerate(
    messages: list[dict[str, str]],
    *,
    settings: Settings,
    log_prefix: str = "[PLATFORM_AUTOGENERATE]",
    openai_model: str = OPENAI_STRONG,
) -> tuple[StationContentAutogenerateModel | None, str]:
    """Generate station instance content via structured parse."""
    parsed, err = await parse_ai_structured(
        messages,
        StationContentAutogenerateModel,
        settings=settings,
        openai_model=openai_model,
        log_prefix=log_prefix,
    )
    if parsed is None and not settings.openai_api_key.strip() and not settings.anthropic_api_key.strip():
        raise GenerationUnavailable()
    return parsed, err


# --- Pydantic models for OpenAI structured parse in station autogeneration.


class StationContentBlockModel(BaseModel):
    """One template block value in AI autogenerate output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    block_id: str = Field(
        alias="blockId",
        description="Template block id from templateStructure",
    )
    value: str | list[str] | int | float | bool = Field(
        description="Block value: text, option string, list of strings, checklist ids, or scale number",
    )


class StationContentAutogenerateModel(BaseModel):
    """AI output for station instance content autogenerate."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str = Field(description="Suggested station title")
    blocks: list[StationContentBlockModel] = Field(
        description="One entry per template blockId with a populated value",
    )

    def content_map(self) -> dict[str, str | list[str] | int | float | bool]:
        return {block.block_id: block.value for block in self.blocks}
