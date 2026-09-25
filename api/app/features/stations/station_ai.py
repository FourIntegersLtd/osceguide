"""OpenAI structured parse helpers for station autogeneration."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.generation.errors import GenerationUnavailable

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

STATION_AUTOGENERATE_MODEL = "gpt-4o"
PARSE_TIMEOUT_SEC = 480


async def parse_ai_structured(
    messages: list[dict[str, str]],
    response_model: type[TModel],
    *,
    settings: Settings,
    model: str = STATION_AUTOGENERATE_MODEL,
    log_prefix: str = "[PLATFORM_AUTOGENERATE]",
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
    if parsed is None and not settings.openai_api_key.strip():
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
