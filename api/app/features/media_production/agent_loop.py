"""A model that works by calling tools, seeing what came back and deciding what to do next.

The loop is the same whatever is being produced: it hands the model its tools, runs the ones it
calls, shows it the results and stops when a tool says the work is done, when
whoever is watching says stop, or when a limit is reached. The limits are enforced here, not asked
of the model.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Final, cast

from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.media_production.errors import AvUnavailable

log = get_logger(__name__)

# The model that calls the tools: it must take both tool calls and pictures.
PRODUCE_MODEL = "gpt-6.1-sol"
# Its turns choose the next tool, which needs little thought; the judgements that need care (each
# claim's verdict, the script's reading) are made by other calls. At its default effort a run spent
# most of its time thinking between tools.
PRODUCE_EFFORT: Final = "low"
_MODEL_SECONDS = 300
_NUDGE = "Call a tool to answer."


@dataclass(frozen=True)
class ToolOutput:
    """What a tool hands back: words for the model, and whether the work is done."""

    text: str
    done: bool = False


Handler = Callable[[dict[str, Any]], Awaitable[ToolOutput]]


@dataclass(frozen=True)
class Tool:
    """One thing the model may do: its name, when to use it, its arguments, and the code that does it."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler


@dataclass(frozen=True)
class ToolCall:
    """One tool the model asked for, with its arguments still as the JSON text it wrote."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class Reply:
    """One turn of the model: what it said, the tools it called, and the tokens the turn cost."""

    text: str
    calls: tuple[ToolCall, ...]
    tokens: int


@dataclass(frozen=True)
class Limits:
    """How far a run may go before it is ended whatever the model wants."""

    turns: int = 120
    seconds: float = 3600
    tokens: int = 6_000_000


@dataclass(frozen=True)
class RunResult:
    """How a run ended (`finished`, `stopped`, `silent`, or the limit it reached) and what it used."""

    ended: str
    turns: int
    tokens: int


Turn = Callable[[list[dict[str, Any]], list[dict[str, Any]]], Awaitable[Reply]]
# Told each tool's name, what it answered and the tokens used so far; answers whether to go on.
OnStep = Callable[[str, str, int], Awaitable[bool]]


def openai_turn(settings: Settings) -> Turn:
    """One turn of this deployment's tool-calling model."""
    if not settings.openai_api_key.strip():
        raise AvUnavailable("Producing needs OPENAI_API_KEY on this environment")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=_MODEL_SECONDS, max_retries=1)

    async def turn(messages: list[dict[str, Any]], specs: list[dict[str, Any]]) -> Reply:
        """Sends the conversation so far and reads back what the model said and called."""
        response = await client.chat.completions.create(
            model=PRODUCE_MODEL,
            messages=cast(Any, messages),
            tools=cast(Any, specs),
            tool_choice="auto",
            reasoning_effort=PRODUCE_EFFORT,
        )
        message = response.choices[0].message
        calls = tuple(
            ToolCall(id=asked.id, name=asked.function.name, arguments=asked.function.arguments)
            for asked in message.tool_calls or []
            if asked.type == "function"
        )
        return Reply(
            text=message.content or "",
            calls=calls,
            tokens=response.usage.total_tokens if response.usage else 0,
        )

    return turn


async def _called(tools: dict[str, Tool], call: ToolCall) -> ToolOutput:
    """Runs one tool. Whatever goes wrong is told to the model in words, so it can try another way."""
    tool = tools.get(call.name)
    if tool is None:
        return ToolOutput(text=f"There is no tool called {call.name}.")
    try:
        arguments = json.loads(call.arguments or "{}")
    except ValueError:
        arguments = None
    if not isinstance(arguments, dict):
        return ToolOutput(text=f"{call.name} was not run: its arguments were not a JSON object.")
    try:
        return await tool.handler(arguments)
    except Exception as error:  # noqa: BLE001 - a failed tool is the model's to work around
        log.warning("produce tool failed", tool=call.name, error=str(error))
        return ToolOutput(text=f"{call.name} failed: {error}")


def _shown(pictures: tuple[bytes, ...]) -> dict[str, Any]:
    """The message that puts pictures in front of the model, after the opening that names them."""
    parts: list[dict[str, Any]] = [{"type": "text", "text": "The pictures named above, in order."}]
    for picture in pictures:
        encoded = base64.b64encode(picture).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}})
    return {"role": "user", "content": parts}


async def run(
    turn: Turn,
    *,
    system: str,
    opening: str,
    tools: list[Tool],
    limits: Limits,
    on_step: OnStep,
    shown: tuple[bytes, ...] = (),
) -> RunResult:
    """Lets the model work with `tools` until one says it is done, a step says stop, or a limit is hit.
    `shown` are pictures put in front of the model with the opening."""
    by_name = {tool.name: tool for tool in tools}
    specs = [
        {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
        }
        for tool in tools
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": opening},
    ]
    if shown:
        messages.append(_shown(shown))
    started = time.monotonic()
    tokens = 0
    silent = False
    for turns in range(1, limits.turns + 1):
        if time.monotonic() - started > limits.seconds:
            return RunResult("time", turns - 1, tokens)
        if tokens > limits.tokens:
            return RunResult("tokens", turns - 1, tokens)
        reply = await turn(messages, specs)
        tokens += reply.tokens
        if not reply.calls:
            if silent:
                return RunResult("silent", turns, tokens)
            silent = True
            messages += [{"role": "assistant", "content": reply.text}, {"role": "user", "content": _NUDGE}]
            continue
        silent = False
        messages.append(
            {
                "role": "assistant",
                "content": reply.text or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in reply.calls
                ],
            }
        )
        for call in reply.calls:
            output = await _called(by_name, call)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output.text})
            going = await on_step(call.name, output.text, tokens)
            if output.done:
                return RunResult("finished", turns, tokens)
            if not going:
                return RunResult("stopped", turns, tokens)
    return RunResult("turns", limits.turns, tokens)
