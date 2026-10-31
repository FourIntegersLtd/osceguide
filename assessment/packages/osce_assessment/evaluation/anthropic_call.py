"""One Anthropic tool call, shared by the evaluator and live coverage.

The client is injected; this module imports no vendor SDK.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contracts import EvaluationPolicy
from ..schemas.strict import inline_refs

# Corrections sent back in the same conversation when a reply misses the schema.
_MAX_CORRECTIONS = 2
_MAX_LISTED = 20


def ask_by_tool(
    client: Any,
    policy: EvaluationPolicy,
    *,
    schema: dict[str, Any],
    name: str,
    description: str,
    system: str,
    user: str,
    error: type[Exception],
    check: Callable[[dict[str, Any]], list[str]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Ask the Anthropic model to call the recording tool; return its input object and the corrections it needed.

    With ``check`` (the schema problems of a reply), a reply that misses is answered in the same
    conversation: its own tool call, then a ``tool_result`` with ``is_error`` listing the problems,
    up to twice. The last reply is returned either way, for the caller to validate and refuse; each
    correction is described in the returned list. Raises ``error`` on a cut-off, a refusal, an empty
    reply, or no tool call after the corrections.
    """
    tool = {"name": name, "description": description, "input_schema": inline_refs(schema)}
    # A forced tool_choice ("tool" or "any") is a 400 on claude-sonnet-5-5, and strict tools refuse
    # our schemas (grammar too large), so the prompt asks for the tool instead. The cache breakpoint
    # on the system prompt covers the tool too, so a correction re-reads both from the cache.
    system_blocks = [
        {"type": "text", "text": f"{system}\n\nAnswer by calling {name}.", "cache_control": {"type": "ephemeral"}}
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
    corrections: list[str] = []
    for round_number in range(_MAX_CORRECTIONS + 1 if check is not None else 1):
        response = client.messages.create(
            model=policy.anthropic_model,
            max_tokens=policy.anthropic_max_tokens,
            # Claude 5.5 models answer 400 to any temperature but their default.
            **({} if policy.anthropic_temperature is None else {"temperature": policy.anthropic_temperature}),
            system=system_blocks,
            messages=list(messages),
            tools=[tool],
        )
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "max_tokens":
            raise error(f"anthropic reply cut off at max_tokens={policy.anthropic_max_tokens}")
        content = list(getattr(response, "content", []) or [])
        # An empty turn cannot be echoed back (a 400), and a refusal will not change on a retry.
        if stop_reason == "refusal" or not content:
            raise error("anthropic refused to answer" if stop_reason == "refusal" else "anthropic reply was empty")
        calls = [block for block in content if getattr(block, "type", None) == "tool_use"]
        last_round = check is None or round_number == _MAX_CORRECTIONS
        if calls:
            value = getattr(calls[0], "input", None)
            if not isinstance(value, dict):
                raise error("tool input was not an object")
            problems = check(value) if check is not None else []
            if not problems or last_round:
                return value, corrections
        elif last_round:
            raise error("no tool_use block in response")
        else:
            problems = []
        corrections.append("; ".join(problems[:10]) or "no tool call")
        messages += [{"role": "assistant", "content": content}, {"role": "user", "content": _correction_reply(name, calls, problems)}]
    raise error("anthropic gave no reply")  # pragma: no cover - the loop always runs once


def _correction_reply(name: str, calls: list[Any], problems: list[str]) -> str | list[dict[str, Any]]:
    """The user turn that answers a reply off the schema: an error result per tool call, or a nudge to call the tool."""
    if not calls:
        return f"You did not call {name}. Call it now with the assessment."
    listed = "\n".join(f"- {problem}" for problem in problems[:_MAX_LISTED])
    return [
        {
            "type": "tool_result",
            "tool_use_id": call.id,
            "is_error": True,
            "content": f"The input did not match the schema:\n{listed}\nCall {name} again with a corrected input.",
        }
        for call in calls
    ]
