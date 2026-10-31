"""One plain-text model reply for the assistant's written answers: Claude first, OpenAI second.

Plain text only. Structured replies go through the engine's `ask_by_tool` (marking), not here.
"""

from collections.abc import Sequence

from app.core.llm import CLAUDE_HAIKU, OPENAI_FAST, claude_reply, first_that_answers, openai_reply
from app.core.settings import Settings

_TIMEOUT_SECONDS = 45


class ModelUnavailable(RuntimeError):
    """No model is configured, or every one that was asked failed or answered nothing."""


async def complete(
    settings: Settings, system: str, messages: Sequence[dict[str, str]], *, max_tokens: int
) -> str:
    """The reply from Claude Haiku; from OpenAI when Claude has no key, fails or answers nothing."""
    turns = list(messages)

    async def from_claude(key: str) -> str:
        """Claude Haiku's reply."""
        # effort low: thinking counts against max_tokens, and grounded answers need little.
        return await claude_reply(
            key,
            system=system,
            messages=turns,
            max_tokens=max_tokens,
            timeout=_TIMEOUT_SECONDS,
            model=CLAUDE_HAIKU,
            effort="low",
        )

    async def from_openai(key: str) -> str:
        """The fallback's reply."""
        # reasoning low: grounded answers need a little thought, not the model default.
        return await openai_reply(
            key,
            system=system,
            messages=turns,
            max_tokens=max_tokens,
            reasoning_effort="low",
            model=OPENAI_FAST,
            timeout=_TIMEOUT_SECONDS,
        )

    try:
        return (
            await first_that_answers(
                [
                    ("claude", settings.anthropic_api_key, from_claude),
                    ("openai", settings.openai_api_key, from_openai),
                ]
            )
        ).strip()
    except Exception as exc:  # noqa: BLE001 - no key, or the last provider's failure (already logged)
        raise ModelUnavailable() from exc
