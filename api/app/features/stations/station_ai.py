"""OpenAI structured parse helpers for station autogeneration."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.generation.errors import GenerationUnavailable

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

# o3 primary, claude-sonnet-4-5 fallback: the legacy pairing (b2c's
# `ai_service._get_model_details`), restored after a regression left this
# hardcoded to gpt-4o.
STATION_AUTOGENERATE_MODEL = "o3"
STATION_AUTOGENERATE_FALLBACK_MODEL = "claude-sonnet-4-5"
PARSE_TIMEOUT_SEC = 480
# Room for the whole answer. Transcribing a long station document writes most
# of the document back out, which 4096 tokens cut off part-way.
FALLBACK_MAX_TOKENS = 32_000


async def parse_ai_structured(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    settings: Settings,
    model: str = STATION_AUTOGENERATE_MODEL,
    log_prefix: str = "[PLATFORM_AUTOGENERATE]",
) -> tuple[TModel | None, str]:
    """Structured parse against `model`, falling back to Anthropic when the primary refuses or times out."""
    if not settings.openai_api_key.strip() and not settings.anthropic_api_key.strip():
        return None, "No model provider is configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)"

    parsed, err = await _parse_with_openai(
        messages, response_model, settings=settings, model=model, log_prefix=log_prefix
    )
    if parsed is not None:
        return parsed, ""
    if not settings.anthropic_api_key.strip():
        return None, err
    logger.warning(
        "%s falling back to %s after primary failure: %s",
        log_prefix,
        STATION_AUTOGENERATE_FALLBACK_MODEL,
        err,
    )
    return await _parse_with_anthropic(
        messages,
        response_model,
        settings=settings,
        model=STATION_AUTOGENERATE_FALLBACK_MODEL,
        log_prefix=log_prefix,
    )


async def _parse_with_openai(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    settings: Settings,
    model: str,
    log_prefix: str,
) -> tuple[TModel | None, str]:
    """Call OpenAI beta.chat.completions.parse. Returns (parsed, error_message)."""
    if not settings.openai_api_key.strip():
        return None, "OpenAI is not configured (set OPENAI_API_KEY)"

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            response_format=response_model,
            timeout=PARSE_TIMEOUT_SEC,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            refusal = response.choices[0].message.refusal
            return None, f"Structured parse returned empty: {refusal or 'unknown'}"
        logger.debug(
            "%s parse ok model=%s responseModel=%s finishReason=%s",
            log_prefix,
            model,
            response_model.__name__,
            response.choices[0].finish_reason,
        )
        return parsed, ""
    except Exception as exc:
        logger.warning(
            "%s structured parse failed model=%s responseModel=%s error=%s",
            log_prefix,
            model,
            response_model.__name__,
            exc,
            exc_info=True,
        )
        return None, str(exc)


async def _parse_with_anthropic(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    settings: Settings,
    model: str,
    log_prefix: str,
) -> tuple[TModel | None, str]:
    """The same structured-output contract via Anthropic's tool-use, for the fallback model."""
    from anthropic import AsyncAnthropic, omit

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = "\n".join(message["content"] for message in messages if message["role"] == "system")
    user_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message["role"] != "system"
    ]
    tool_name = "emit_result"
    try:
        response = await client.messages.create(  # type: ignore[call-overload]
            model=model,
            max_tokens=FALLBACK_MAX_TOKENS,
            system=system or omit,
            messages=user_messages,
            tools=[
                {
                    "name": tool_name,
                    "description": f"Return {response_model.__name__} as structured data.",
                    "input_schema": response_model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            timeout=PARSE_TIMEOUT_SEC,
        )
        if response.stop_reason == "max_tokens":
            return None, "Fallback model ran out of room before it finished its answer"
        tool_use = next((block for block in response.content if block.type == "tool_use"), None)
        if tool_use is None:
            return None, "Fallback model returned no structured result"
        parsed = response_model.model_validate(tool_use.input)
        logger.debug(
            "%s parse ok (fallback) model=%s responseModel=%s", log_prefix, model, response_model.__name__
        )
        return parsed, ""
    except Exception as exc:
        logger.warning(
            "%s fallback structured parse failed model=%s responseModel=%s error=%s",
            log_prefix,
            model,
            response_model.__name__,
            exc,
            exc_info=True,
        )
        return None, str(exc)


async def generate_station_autogenerate(
    messages: list[dict[str, str]],
    *,
    settings: Settings,
    log_prefix: str = "[PLATFORM_AUTOGENERATE]",
    model: str = STATION_AUTOGENERATE_MODEL,
) -> tuple[StationContentAutogenerateModel | None, str]:
    """Generate station instance content via structured parse."""
    parsed, err = await parse_ai_structured(
        messages,
        StationContentAutogenerateModel,
        settings=settings,
        model=model,
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
