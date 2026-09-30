"""What the catalog routes accept and return: exams and programmes."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.core.exam_settings import ExamSettings


class ExamRead(BaseModel):
    id: uuid.UUID
    # Who wrote it: `platform` is the consumer catalogue, `org` is an
    # institution's own. `org_id` is set only for the latter.
    owner_kind: str = "platform"
    org_id: uuid.UUID | None = None
    code: str
    name: str
    status: str
    rubric_version_id: uuid.UUID | None = None
    # The rubric version's id: what a result is recorded under. Empty while the
    # exam is a draft with no rubric named yet.
    framework_id: str
    default_reading_seconds: int
    default_simulation_seconds: int
    station_attempt_limit: int
    partner_pilot: bool = False
    settings: ExamSettings = Field(default_factory=ExamSettings)


class CreateExam(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    default_reading_seconds: int = Field(gt=0, le=3600)
    default_simulation_seconds: int = Field(gt=0, le=7200)
    station_attempt_limit: int = Field(default=3, gt=0, le=100)
    rubric_version_id: uuid.UUID | None = None
    partner_pilot: bool = False
    # Omitted, the exam behaves like the defaults (`ExamSettings()`).
    settings: ExamSettings | None = None


class UpdateExam(BaseModel):
    """Everything but the code, which existing plans and ref ids depend on."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_reading_seconds: int | None = Field(default=None, gt=0, le=3600)
    default_simulation_seconds: int | None = Field(default=None, gt=0, le=7200)
    station_attempt_limit: int | None = Field(default=None, gt=0, le=100)
    rubric_version_id: uuid.UUID | None = None
    partner_pilot: bool | None = None
    # Replaces the whole settings object; there is no partial merge.
    settings: ExamSettings | None = None


class ProgrammeRead(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    exam_code: str
    exam_name: str
    # Whether the exam behind this programme is the institution's own or one
    # the platform published. The programme's own status is separate and the
    # institution's alone.
    exam_owner_kind: str = "platform"
    status: str
    source: str


class CreateProgramme(BaseModel):
    """The exam this programme groups sittings under.

    By code, resolved in the institution's own scope first: a school that has
    written its own `plab` gets that one, not the platform's.
    """

    exam_code: str = Field(min_length=1, max_length=32)


class UpdateProgramme(BaseModel):
    status: str = Field(pattern="^(draft|active|retired)$")


class PlatformCatalogueExamRead(BaseModel):
    """One published platform exam, as an institution choosing what to import sees it."""

    exam_id: uuid.UUID
    code: str
    title: str
    # Published library stations for this exam: what the institution gets to use.
    station_count: int
    # Whether this institution already runs it, by import or as a programme.
    already_imported: bool


class PlatformCatalogueRead(BaseModel):
    """The published platform exams an institution may import. Small, so never paged."""

    items: list[PlatformCatalogueExamRead]


class ImportPlatformExam(BaseModel):
    """Which published platform exam to bring into the institution."""

    platform_exam_id: uuid.UUID


class ImportedExamRead(BaseModel):
    """The exam now in the institution, shaped as `GET /orgs/{org_slug}/exams` lists it."""

    exam: ExamRead
