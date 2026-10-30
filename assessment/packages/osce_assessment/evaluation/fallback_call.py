"""One Anthropic-style tool call, shared by the evaluator and live coverage.

The client is injected; this module imports no vendor SDK.
"""

from __future__ import annotations

from typing import Any

from ..contracts import EvaluationPolicy
from ..schemas.strict import inline_refs


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
) -> dict[str, Any]:
    """Ask the fallback model to call the recording tool and return its input object, or raise ``error``."""
    response = client.messages.create(
        model=policy.fallback_model,
        max_tokens=policy.fallback_max_tokens,
        # Claude 5.5 models answer 400 to any temperature but their default.
        **({} if policy.fallback_temperature is None else {"temperature": policy.fallback_temperature}),
        # A forced tool_choice ("tool" or "any") is a 400 on claude-sonnet-5-5, and strict tools
        # refuse our schemas (grammar too large), so the prompt asks for the tool instead.
        system=f"{system}\n\nAnswer by calling {name}.",
        messages=[{"role": "user", "content": user}],
        tools=[{"name": name, "description": description, "input_schema": inline_refs(schema)}],
    )
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise error(f"fallback reply cut off at max_tokens={policy.fallback_max_tokens}")
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use":
            value = getattr(block, "input", None)
            if not isinstance(value, dict):
                raise error("tool input was not an object")
            return value
    raise error("no tool_use block in response")
