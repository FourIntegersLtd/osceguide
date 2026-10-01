"""Request and response shapes for the assistant routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints


class StartSession(BaseModel):
    session_type: str = Field(min_length=1, max_length=32)
    extras: dict[str, Any] = Field(default_factory=dict)
    # SEC-007: the consulting-doctor demo names the station it plays by id, and
    # the server loads its material from the database. The station content in
    # `extras` is no longer trusted to build the prompt — it was authored by
    # whoever called this route, so it was a way to steer the system prompt.
    station_version_id: uuid.UUID | None = None


class SessionRead(BaseModel):
    id: uuid.UUID
    session_type: str
    status: str
    room_name: str | None
    created_at: datetime


class RoomGrant(BaseModel):
    """What the browser needs to join this session's room, and nothing more.

    The same three fields `voice` returns for a circuit's room. Restated here
    rather than imported because a router may name only its own slice's
    schemas, and the response shape is this route's contract either way.
    """

    token: str
    server_url: str
    room: str


class WorkerSessionPayload(BaseModel):
    """`{"session": {...}}` — the shape `livekit_assistant_worker` validates.

    Its paths are hardcoded in the worker rather than configured per backend, so
    this API must mount them exactly. Noted in the README.
    """

    session: dict[str, Any]


class SceneRequest(BaseModel):
    phase: str | None = None
    question: str | None = None
    patientLine: str | None = None  # noqa: N815 - the worker's own spelling


class SceneInstructions(BaseModel):
    instructions: str


class OnboardingScene(BaseModel):
    """One demo scenario. The spelling is the worker's and the browser's."""

    patientLine: str  # noqa: N815 - the contract's own spelling
    question: str


class AssistantPersona(BaseModel):
    assistantName: str  # noqa: N815 - the contract's own spelling


class OnboardingScenes(BaseModel):
    scenes: list[OnboardingScene]
    persona: AssistantPersona


class AssistantTranscriptPost(BaseModel):
    session_id: str
    worker_type: str
    candidate_ref: str = ""
    transcript: dict[str, Any]


class SessionComplete(BaseModel):
    end_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class Accepted(BaseModel):
    status: str = "accepted"


# --- Help catalogue and knowledge chat contracts.

# Which exam's help to show: any exam's code, lowercased. An institution's own
# exam is as valid here as a platform one; it simply has no guides written
# only for it, so it sees the guides written for every exam.
HelpExamCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=64)
]


class HelpCategory(BaseModel):
    id: str = ""
    slug: str
    title: str
    description: str = ""
    icon_key: str = "book"
    sort_order: int = 0
    exam_codes: list[str]
    article_count: int = 0


class HelpArticle(BaseModel):
    id: str = ""
    slug: str
    title: str
    summary: str = ""
    exam_codes: list[str]
    category_slug: str
    category_title: str = ""
    sort_order: int = 0
    body_md: str
    related_slugs: list[str] = Field(default_factory=list)


class HelpCategories(BaseModel):
    categories: list[HelpCategory]


class HelpArticles(BaseModel):
    articles: list[HelpArticle]


class HelpArticleDetail(BaseModel):
    article: HelpArticle


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class KnowledgeChat(BaseModel):
    # The exam the learner is studying. Without one there is nothing to ground an answer in.
    exam_code: HelpExamCode | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class KnowledgeReply(BaseModel):
    reply: str
