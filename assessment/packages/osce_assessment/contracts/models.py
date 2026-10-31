"""Serialisable domain models.

Three layers, in the order they exist in time:

* ``AssessmentDefinition`` — what should be assessed. Versioned; frozen once an
  attempt snapshots it.
* ``AssessmentAttempt`` — what happened when one candidate ran one definition.
* ``AssessmentResult`` — what the evaluator concluded from that attempt.

``Scenario``, ``AIInteractionProfile`` and ``EvaluationPolicy`` are the parts
of a definition. ``Transcript`` is what the interaction produced.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ._base import Frozen


class ScenarioSource(str, Enum):
    """Where a scenario comes from: the shared library, an organisation, or inline in the request."""

    LIBRARY = "library"
    ORG = "org"
    INLINE = "inline"


class InteractionMode(str, Enum):
    """Whether the AI plays the patient or acts as a tutor."""

    PATIENT = "patient"
    TUTOR = "tutor"


class RuntimeHint(str, Enum):
    """Which kind of voice pipeline the profile prefers: separate speech stages or one realtime model."""

    PIPELINE = "pipeline"
    REALTIME = "realtime"


class MessageRole(str, Enum):
    """Who said a transcript message: the user or the assistant."""

    USER = "user"
    ASSISTANT = "assistant"


class AttemptStatus(str, Enum):
    """How far an attempt has got, from created through to evaluated."""

    CREATED = "created"
    RUNNING = "running"
    INTERACTION_COMPLETE = "interaction_complete"
    EVALUATED = "evaluated"
    FAILED = "failed"


class ScenarioRef(Frozen):
    """Where to fetch a scenario from. Resolved by a ``ScenarioProvider``."""

    source: ScenarioSource
    scenario_id: str = Field(min_length=1)


class Scenario(Frozen):
    """The case content the AI plays and the candidate is briefed on."""

    id: str
    source: ScenarioSource
    title: str
    patient_brief: dict[str, Any] = Field(default_factory=dict)
    patient_gender: str | None = None
    candidate_brief: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    # Extra material the marker should see alongside the transcript, e.g. the
    # expected answers for an interview-style station. Appended verbatim.
    examiner_context: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AIInteractionProfile(Frozen):
    """How the AI behaves during the interaction.

    ``instructions`` is *rendered* text, not a template. A ``ProfileBuilder``
    produces it from a resolved scenario before the interaction starts, which
    is what keeps knowledge of a scenario's shape out of the transport layer:
    whoever runs the interaction receives finished instructions and never has
    to know what fields a scenario has.
    """

    mode: InteractionMode
    instructions: str = ""
    voice: str | None = None
    # Names of the tools the interaction exposes to the model. The transport
    # maps each name to an implementation it owns; ``tool_context`` carries the
    # rendered data those tools need (say, a mapping of the short line ids
    # used in the instructions to message ids), opaque to the engine.
    tools: tuple[str, ...] = ()
    tool_context: dict[str, Any] = Field(default_factory=dict)
    greeting: str | None = None
    max_tool_steps: int = Field(default=5, ge=0)
    runtime_hint: RuntimeHint = RuntimeHint.PIPELINE


class EvaluationPolicy(Frozen):
    """How a transcript is scored against a competency framework.

    Scoring only. The *shape* of the result belongs to the framework named in
    ``framework_id``, which carries the competencies, the scale and any result
    schema. Keeping shape out of here is what lets one framework be scored by
    several policies, so two consumers can mark the identical interaction
    differently without the engine branching on who they are.

    Consumers choose the policy; the engine only executes it.
    """

    framework_id: str
    # ``primary_*`` is the OpenAI slot (strict json_schema) and ``fallback_*`` the Anthropic slot
    # (tool call); ``first_provider`` picks which is asked first, the other answers if it fails.
    first_provider: Literal["openai", "anthropic"] = "openai"
    openai_model: str
    openai_reasoning_effort: str | None = None
    anthropic_model: str | None = None
    # Claude 5.5 thinks by default and its thinking counts here: 7500 cut 7 of 16 SCA marks short.
    anthropic_max_tokens: int = Field(default=16000, gt=0)
    # None sends no temperature: Claude 5.5 models refuse any value but their default.
    anthropic_temperature: float | None = Field(default=None, ge=0.0)
    timeout_s: int = Field(default=480, gt=0)
    system_prompt_override: str | None = None
    version: str = "1"


class AssessmentDefinition(Frozen):
    """What should be assessed.

    ``evaluation_policy`` is what scores the attempt and is required wherever
    an evaluator runs. A deployment that only runs the interaction (a worker)
    is handed a definition without it, so the transport never learns how the
    transcript will be marked.
    """

    id: str
    version: str
    framework_id: str
    scenario_ref: ScenarioRef
    interaction_profile: AIInteractionProfile
    evaluation_policy: EvaluationPolicy | None = None
    snapshot_at: datetime


class AssessmentAttempt(BaseModel):
    """One candidate's one run of one definition.

    ``attempt_context`` is opaque to the engine: correlation ids the consumer
    needs back (whatever they are) go in as strings and come out unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    attempt_id: str
    definition: AssessmentDefinition
    candidate_ref: str
    attempt_context: dict[str, str] = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    status: AttemptStatus = AttemptStatus.CREATED


class TranscriptMessage(Frozen):
    """One line of the conversation, with who said it, when, and its position in order."""

    role: MessageRole
    message: str
    timestamp: datetime
    message_id: str
    seq: int = Field(ge=0)


class Transcript(Frozen):
    """The ordered messages of one attempt, and whether the conversation has finished."""

    attempt_id: str
    messages: tuple[TranscriptMessage, ...] = ()
    complete: bool = False
    runtime_label: str | None = None


class AssessmentResult(Frozen):
    """The scored outcome, always tied to the attempt and the policy version.

    ``result`` is plain data so the contract stays serialisable. Its shape is
    owned by the competency framework named in ``framework_id``, which can
    check a competency-to-score mapping via ``validate_scores``.
    """

    attempt_id: str
    framework_id: str
    policy_version: str
    result: dict[str, Any]
    provider: str
    model: str
    generated_at: datetime
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
