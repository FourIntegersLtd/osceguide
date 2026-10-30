"""The model adapter behind `core.ports.TranscriptSummariser`.

Structured output, because a summary that has to be parsed out of prose is a
summary that will one day be parsed wrongly and written into somebody's memory
as fact. The schema and the instructions come from the caller: what a debrief
summary should contain is a tutoring decision, not an adapter's.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.core.ports import SummaryFailed, TranscriptSummariser
from app.core.settings import get_settings

log = get_logger(__name__)

SUMMARY_MODEL = "gpt-6-luna"
SUMMARY_REASONING_EFFORT = "low"
SUMMARY_TIMEOUT_SECONDS = 120


class OpenAISummariser:
    """Asks for JSON and refuses anything else."""

    def __init__(self, client: Any, model: str = SUMMARY_MODEL) -> None:
        self._client = client
        self._model = model

    async def summarise(
        self,
        *,
        kind: str,
        transcript: list[dict[str, object]],
        schema: dict[str, object],
        instructions: str,
    ) -> dict[str, object]:
        """Turn a transcript into the shape `schema` describes, tagged with which model wrote it."""
        import asyncio

        body = "\n".join(f"{turn.get('role')}: {turn.get('message')}" for turn in transcript)
        if not body.strip():
            raise SummaryFailed(f"there is no {kind} transcript to summarise")

        def _call() -> str:
            """One blocking request for the raw JSON text the model returns."""
            response = self._client.chat.completions.create(
                model=self._model,
                reasoning_effort=SUMMARY_REASONING_EFFORT,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": body},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": kind, "schema": schema, "strict": False},
                },
                timeout=SUMMARY_TIMEOUT_SECONDS,
            )
            return str(response.choices[0].message.content or "")

        try:
            raw = await asyncio.to_thread(_call)
            parsed = json.loads(raw)
        except Exception as exc:  # noqa: BLE001 - every failure here is the same failure
            raise SummaryFailed(f"the {kind} summary could not be produced: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SummaryFailed(f"the {kind} summary was not an object")
        parsed["model_used"] = self._model
        return parsed


def build_summariser() -> TranscriptSummariser:
    """Wire the model client, or say plainly that it is not configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise SummaryFailed("No OPENAI_API_KEY, so nothing can be summarised.")
    try:
        from openai import OpenAI  # optional dependency
    except ImportError as exc:
        raise SummaryFailed("The openai package is not installed.") from exc
    return OpenAISummariser(OpenAI(api_key=settings.openai_api_key))
