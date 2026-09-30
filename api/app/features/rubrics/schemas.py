"""What the rubrics routes accept and return: rubrics and their versions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import RatingRead, ResultTotalsRead

# Re-exported so `router.py`/`router_org.py` can name it while importing only
# their own slice's `schemas` (`tests/guards/test_routers_are_thin.py`); the
# trial-candidate picker (R-6) is answered by `attempts.service_trial`, but
# the row shape itself lives in `core` since both slices' routes return it
# (`tests/guards/test_schemas_are_not_rows.py`).
from app.core.schemas import TrialCandidateRead as TrialCandidateRead


class RubricProblemRead(BaseModel):
    """One reason a structure cannot be published yet, at the place it applies."""

    # Index-based, e.g. `sections[0].competencies[1].id`; empty for the whole structure.
    path: str
    message: str


class RubricVersionRead(BaseModel):
    id: uuid.UUID
    rubric_id: uuid.UUID
    version: int
    status: str
    structure: dict[str, Any]
    system_prompt: str
    pacing: dict[str, Any]
    marking_layout: dict[str, Any] | None = None
    # Derived from `structure` on the way out, never stored: what the marker is
    # actually asked to fill. Read-only, so an author can see what their
    # domains and competencies came to without running an attempt.
    result_schema: dict[str, Any]
    # Every reason this version could not be published as it stands. A draft is
    # saved while invalid (plan §8), so this is how its author sees what is left.
    problems: list[RubricProblemRead] = Field(default_factory=list)
    published_at: datetime | None = None


class RubricRead(BaseModel):
    id: uuid.UUID
    owner_kind: str
    org_id: uuid.UUID | None = None
    title: str
    current_version_id: uuid.UUID | None = None
    versions: list[RubricVersionRead] = Field(default_factory=list)


class CreateRubric(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    structure: dict[str, Any]
    system_prompt: str = Field(min_length=1)
    pacing: dict[str, Any]
    marking_layout: dict[str, Any] | None = None


class RenameRubric(BaseModel):
    """A rubric's new title (R-7): set once at creation, changed later from the builder header."""

    title: str = Field(min_length=1, max_length=200)

    # Refuse a title that is empty once whitespace is trimmed off, same as a
    # station template's (`stations.schemas.UpdateStationTemplateVersion.title_is_visible`).
    @field_validator("title")
    @classmethod
    def title_is_visible(cls, title: str) -> str:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("A title needs at least one character.")
        return cleaned


class EditRubricVersion(BaseModel):
    structure: dict[str, Any]
    system_prompt: str = Field(min_length=1)
    pacing: dict[str, Any]
    marking_layout: dict[str, Any] | None = None


class RubricDraft(BaseModel):
    """A structure being written, sent to be checked, previewed or given draft instructions."""

    structure: dict[str, Any]


class RubricPreviewRead(BaseModel):
    """What a draft structure comes to, whether or not it can be published yet.

    When it is invalid, only `problems` is filled: nothing can be derived from
    a structure that cannot be parsed.
    """

    valid: bool
    problems: list[RubricProblemRead] = Field(default_factory=list)
    # The structure as version 2 (a version 1 one upgraded), when it parses.
    structure: dict[str, Any] | None = None
    # What the marker is asked to fill.
    result_schema: dict[str, Any] = Field(default_factory=dict)
    # The whole stored result, system-written fields included.
    display_schema: dict[str, Any] = Field(default_factory=dict)
    # How feedback and the dashboard read a result: every gap filled.
    display: dict[str, Any] = Field(default_factory=dict)
    rating: RatingRead | None = None
    # A made-up result `result_schema` accepts, to draw the feedback with.
    sample_result: dict[str, Any] | None = None
    # `sample_result`'s numbers, by this rubric's own display rules.
    sample_totals: ResultTotalsRead | None = None


class CopyRubric(BaseModel):
    """Start a new rubric of one's own: from a published one, or blank when no source is named."""

    source_rubric_id: uuid.UUID | None = None
    # Which published version to copy; the source's current version when left out.
    source_version: int | None = Field(default=None, ge=1)
    # "<source title> (copy)", or "Untitled rubric" for a blank one, when left out.
    title: str | None = Field(default=None, min_length=1, max_length=200)


class RubricStartingPointRead(BaseModel):
    """One thing a new rubric can start from: blank, a platform rubric or one of the org's own."""

    kind: Literal["blank", "platform", "own"]
    # Null for blank; otherwise what `CopyRubric.source_rubric_id` takes.
    rubric_id: uuid.UUID | None = None
    # The published version a copy would take.
    version: int | None = None
    title: str
    rating_kind: str
    domains: list[str] = Field(default_factory=list)
    competency_count: int = 0


class RubricStartingPointsRead(BaseModel):
    """Every starting point, blank first, then the platform's rubrics, then the org's own."""

    items: list[RubricStartingPointRead]


class DraftInstructionRead(BaseModel):
    """Suggested wording for one place in a structure that carries instructions."""

    # Index-based, as a problem's path is: `sections[0].competencies[1]`.
    path: str
    # Qualified by ids: `data_gathering.history_taking`, `data_gathering.*.score`.
    key: str
    kind: Literal["domain", "competency", "section", "field"]
    # A field's role; the same as `kind` otherwise.
    role: str
    text: str
    # `rubric`: the copied rubric's own wording for this key; `generic`: by role.
    source: Literal["rubric", "generic"]
    # Whether the author has already written instructions here.
    has_instructions: bool


class DraftInstructionsRead(BaseModel):
    """Draft instructions for a structure, in authored order."""

    items: list[DraftInstructionRead]
