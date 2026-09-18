"""Ports for the parts of the system that speak to a model.

Separated from `ports.py` for the reason the file cap exists: the two halves
are read at different times. Everything here is a request to an LLM — marking a
transcript, rendering a prompt, summarising a conversation, embedding text —
and each is a Protocol so a slice can be tested without an API key.

Every one speaks plain dicts rather than engine contracts, so `app/core` stays
free of `osce_assessment` and the API starts without it installed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


class EvaluationFailed(Exception):
    """The evaluator could not produce a valid result."""


@runtime_checkable
class Evaluator(Protocol):
    """Marks a transcript against a rubric.

    The backend evaluates, always. The LiveKit worker delivers a transcript and
    stops: it cannot import an evaluator, and it is never told the evaluation
    policy, so marking cannot be influenced by whatever ran the conversation.

    `rubric` is the whole thing — the framework, its marking instructions, its
    clock — frozen onto the attempt when it was rendered. It used to be a
    `framework_id` the adapter looked up against the four frameworks the engine
    shipped, which is why a rubric anyone authored could not be marked with.
    Passing it whole also means a re-mark reproduces the original rather than
    using whatever the rubric says by then.
    """

    async def evaluate(
        self,
        *,
        rubric: dict[str, object],
        policy_version: str,
        transcript: list[dict[str, object]],
    ) -> dict[str, object]:
        """Return the engine's result payload, already schema-valid.

        Raises EvaluationFailed rather than returning a partial result: a
        half-marked attempt shown to a candidate is worse than one not yet marked.
        """
        ...


class RenderFailed(Exception):
    """A station could not be rendered into instructions at all."""


@runtime_checkable
class ProfileRenderer(Protocol):
    """Turns a resolved station into the instructions the AI is given.

    The backend renders every prompt; the worker holds no templates and is
    handed finished text. That is the boundary the whole assessment layer is
    built on — a transport that had to understand a station's shape would need
    changing every time an organisation invented a new one.

    Speaks dicts rather than engine contracts for the same reason `Evaluator`
    does: `app/core` stays free of the engine, so the API starts and the suite
    runs without it installed.
    """

    def render(
        self,
        *,
        station: dict[str, object],
        layout: Sequence[Mapping[str, Any]] | None = None,
        greeting: str | None = None,
        mode: str,
    ) -> dict[str, object]:
        """Return `{"instructions", "greeting", "examiner_context"}`.

        `layout` is the station template's ordered block list, which says what
        each block of the station is for. It replaces the `exam_code` this used
        to take: the renderer branched on that string to pick one of three
        formatters, so a new exam could not have a document shape of its own
        without a change here and in the engine.

        Raises `RenderFailed` rather than returning empty instructions: the
        worker refuses a job with none, and it should fail here where somebody
        can read the reason, not on connect.
        """
        ...


class SummaryFailed(Exception):
    """The model could not produce a summary in the shape asked for."""


@runtime_checkable
class TranscriptSummariser(Protocol):
    """Turns a finished conversation into a small structured record.

    A port for the same reason `Evaluator` is one: which model writes a summary
    is a backend decision, and a slice should be testable without an API key.
    Speaks dicts rather than schemas so `app/core` stays free of the engine.

    `schema` is the JSON schema the result must satisfy and `instructions` is
    the system prompt; both are the caller's, because what a debrief summary
    should contain is a tutoring decision, not an adapter's.
    """

    async def summarise(
        self,
        *,
        kind: str,
        transcript: list[dict[str, object]],
        schema: dict[str, object],
        instructions: str,
    ) -> dict[str, object]:
        """Return a payload valid against `schema`, or raise `SummaryFailed`.

        Raising rather than returning a partial record: half a summary written
        into somebody's memory is worse than none, because the tutor will speak
        from it as though it were complete.
        """
        ...


@runtime_checkable
class TutorPromptRenderer(Protocol):
    """Renders what is on file about one learner into a tutor's instructions.

    The backend renders every prompt — the same boundary the assessment side is
    built on. The worker is handed finished text and holds no templates, so the
    brief's shape can change without touching anything downstream.

    `labels` are this product's words for its own material ("the condition
    summaries", "the slides"), which is what keeps the engine free of product
    vocabulary.
    """

    def render(self, *, brief: dict[str, object], labels: Mapping[str, str]) -> str:
        """Return the instructions. Raises `RenderFailed` if it produced none."""
        ...
