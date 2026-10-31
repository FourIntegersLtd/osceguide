"""Calling a language model, for every slice that asks Claude first and OpenAI second.

claude-sonnet-5-5 and claude-haiku-5-5 answer 400 to any temperature but their default and to a
forced `tool_choice`, and they think by default with the thinking counted in `max_tokens`, so the
caller gives headroom (or sends `effort="low"`). The system prompt carries a cache breakpoint. A
schema, when given, goes in `output_config.format`: that only compiles for a small schema (about
7KB), and a larger one silently fails over to OpenAI, so a large one needs the engine's
`ask_by_tool` instead (`osce_assessment.evaluation.anthropic_call`).
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Literal, TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

CLAUDE_SONNET = "claude-sonnet-5-5"
CLAUDE_HAIKU = "claude-haiku-5-5"
# OpenAI by tier: STRONG writes and judges, FAST cuts and splits.
OPENAI_STRONG = "gpt-6.1-sol"
OPENAI_FAST = "gpt-6-luna"

Effort = Literal["low", "medium", "high", "xhigh", "max"]
# Claude's grammar for a schema tops out near 7KB; warn well before.
_SCHEMA_WARN_BYTES = 6_000

T = TypeVar("T")


class LlmReplyUnusable(Exception):
    """A model answered, but with a cut-off, a refusal or nothing."""


class NoModelKey(Exception):
    """Every key offered was blank, so no model could be asked."""


async def claude_reply(
    api_key: str,
    *,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
    model: str = CLAUDE_SONNET,
    schema: dict[str, Any] | None = None,
    effort: Effort | None = None,
) -> str:
    """The text of Claude's reply; with `schema` it is JSON that fits the schema."""
    from anthropic import AsyncAnthropic  # optional dependency

    output_config: dict[str, Any] = {}
    if schema is not None:
        from anthropic import transform_schema

        transformed = transform_schema(schema)
        size = len(json.dumps(transformed))
        if size > _SCHEMA_WARN_BYTES:
            logger.warning("llm_schema_near_grammar_limit", bytes=size, model=model)
        output_config["format"] = {"type": "json_schema", "schema": transformed}
    if effort is not None:
        output_config["effort"] = effort
    extra: dict[str, Any] = {"output_config": output_config} if output_config else {}
    async with AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=1) as client:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,  # type: ignore[arg-type]  # plain dicts, not MessageParam
            **extra,
        )
    if response.stop_reason in ("max_tokens", "refusal"):
        raise LlmReplyUnusable(f"Claude stopped with {response.stop_reason}")
    text = next((block.text for block in response.content if block.type == "text"), "")
    if not text.strip():
        raise LlmReplyUnusable("Claude's reply was empty")
    return text


async def openai_reply(
    api_key: str,
    *,
    system: str,
    messages: list[dict[str, str]],
    model: str,
    timeout: float,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> str:
    """The text of an OpenAI chat reply; `response_format` asks for a JSON object or a schema.

    `max_tokens` is sent as `max_completion_tokens`. An empty reply raises `LlmReplyUnusable`, as
    Claude's does, so `first_that_answers` moves on.
    """
    from openai import AsyncOpenAI  # optional dependency

    extra: dict[str, Any] = {}
    if max_tokens is not None:
        extra["max_completion_tokens"] = max_tokens
    if reasoning_effort is not None:
        extra["reasoning_effort"] = reasoning_effort
    if response_format is not None:
        extra["response_format"] = response_format
    async with AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1) as client:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],  # type: ignore[list-item]  # plain dicts
            **extra,
        )
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise LlmReplyUnusable("OpenAI's reply was empty")
    return text


async def first_that_answers(attempts: Sequence[tuple[str, str, Callable[[str], Awaitable[T]]]]) -> T:
    """The first answer, asking `(name, api_key, ask)` in order and skipping blank keys.

    A failure is logged and the next is tried; the last one's failure is raised. No usable key is
    `NoModelKey`.
    """
    usable = [(name, key, ask) for name, key, ask in attempts if key.strip()]
    if not usable:
        raise NoModelKey("No model key is configured")
    for name, key, ask in usable[:-1]:
        try:
            return await ask(key)
        except Exception:  # noqa: BLE001 - any failure falls through to the next provider
            logger.warning("llm_attempt_failed_falling_back", provider=name, exc_info=True)
    _, key, ask = usable[-1]
    return await ask(key)


def json_object(text: str) -> dict[str, Any] | None:
    """The JSON object in a model reply (Claude sometimes fences it), or None if there is none."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
