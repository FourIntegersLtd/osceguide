"""Ports: the boundaries between the engine and everything it does not own.

Each port is a ``typing.Protocol`` so implementations need no base class.
Sink and evaluator methods may be synchronous or return an awaitable; the
runtime awaits whichever it gets.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol, runtime_checkable

from .framework import CompetencyFramework
from .models import (
    AIInteractionProfile,
    AssessmentAttempt,
    AssessmentDefinition,
    AssessmentResult,
    EvaluationPolicy,
    MessageRole,
    Scenario,
    ScenarioRef,
    Transcript,
    TranscriptMessage,
)

MessageCallback = Callable[[MessageRole, str], Awaitable[None] | None]


@runtime_checkable
class ScenarioProvider(Protocol):
    """Resolves a scenario reference to its content (library, org-owned, ...)."""

    def resolve(
        self, scenario_ref: ScenarioRef, attempt_context: Mapping[str, str]
    ) -> Scenario:
        """Return the scenario that the reference points to."""
        ...


@runtime_checkable
class FrameworkProvider(Protocol):
    """Resolves a framework id to its definition (platform catalogue, org-authored, ...)."""

    def get(self, framework_id: str) -> CompetencyFramework:
        """Return the framework with this id."""
        ...


@runtime_checkable
class ProfileBuilder(Protocol):
    """Renders a definition plus a resolved scenario into finished instructions.

    This is the only place that needs to understand a scenario's shape, which
    is why it belongs with the templates and authoring tools rather than with
    the interaction. An organisation defining its own station shape supplies
    the template that renders it; nothing downstream is affected.
    """

    def build(
        self, definition: AssessmentDefinition, scenario: Scenario
    ) -> AIInteractionProfile:
        """Return the finished instructions for this definition and scenario."""
        ...


@runtime_checkable
class InteractionAdapter(Protocol):
    """Executes the real-time interaction (LiveKit today; anything later).

    ``run`` drives the interaction to its natural end and reports every turn
    through ``on_message`` as it happens, so a crash mid-way still leaves a
    partial transcript behind.
    """

    async def connect(self) -> None:
        """Open the connection to the interaction."""
        ...

    async def send_greeting(self, text: str) -> None:
        """Say the opening greeting before the interaction runs."""
        ...

    async def run(
        self, profile: AIInteractionProfile, on_message: MessageCallback
    ) -> None:
        """Run the interaction to its end, passing each turn to ``on_message``."""
        ...

    async def disconnect(self) -> None:
        """Close the connection, whether the interaction ended well or not."""
        ...


@runtime_checkable
class TranscriptSink(Protocol):
    """Receives every message as it is captured, then the completed transcript."""

    def append(
        self, attempt_id: str, message: TranscriptMessage
    ) -> Awaitable[None] | None:
        """Store one message as soon as it is captured."""
        ...

    def complete(
        self, attempt_id: str, transcript: Transcript
    ) -> Awaitable[None] | None:
        """Store the completed transcript."""
        ...


@runtime_checkable
class Evaluator(Protocol):
    """Scores a transcript against a policy. Receives the resolved scenario too,
    because marking needs the station's title and any examiner-only material."""

    def evaluate(
        self,
        attempt: AssessmentAttempt,
        transcript: Transcript,
        policy: EvaluationPolicy,
        scenario: Scenario,
    ) -> AssessmentResult | Awaitable[AssessmentResult]:
        """Return the result of marking this transcript against the policy."""
        ...


@runtime_checkable
class ResultSink(Protocol):
    """Stores a finished assessment result."""

    def save_result(
        self, result: AssessmentResult, attempt_context: Mapping[str, str]
    ) -> Awaitable[None] | None:
        """Save the result for this attempt."""
        ...
