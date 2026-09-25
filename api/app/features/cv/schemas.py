"""The public shape of a CV. Declared here, mapped in the service.

`StructuredCv` does double duty on purpose: it is the model the extraction asks
the LLM to fill *and* the shape the API returns, so what is stored is exactly
what was requested and the client reads the same type the model was held to.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StructuredCv(BaseModel):
    """The sections a CV is read into. A section with nothing in it is null."""

    summary: str | None = Field(default=None, description="Personal summary and career overview")
    experience: str | None = Field(default=None, description="Clinical experience, roles, rotations")
    education: str | None = Field(default=None, description="Medical school, degrees, qualifications")
    research: str | None = Field(default=None, description="Research projects and interests")
    publications: str | None = Field(default=None, description="Papers, presentations, abstracts")
    audits: str | None = Field(default=None, description="Audit and quality-improvement work")
    teaching: str | None = Field(default=None, description="Teaching, supervision, education")
    leadership: str | None = Field(default=None, description="Leadership and management roles")
    achievements: str | None = Field(default=None, description="Awards, prizes, recognition")
    skills: str | None = Field(default=None, description="Clinical competencies, languages")
    grants: str | None = Field(default=None, description="Research funding and scholarships")
    courses: str | None = Field(default=None, description="Professional development courses")


class CvUploadResult(BaseModel):
    """What an upload answers with, before the model has read it.

    The row exists and is `processing`; the structured sections arrive later, read back from the
    list. The message sets the expectation that this is not instant.
    """

    id: uuid.UUID
    status: str
    message: str


class CvRead(BaseModel):
    id: uuid.UUID
    status: str
    original_filename: str
    uploaded_at: datetime
    completed_at: datetime | None = None
    structured: StructuredCv | None = None
    error: str | None = None


class CvList(BaseModel):
    cvs: list[CvRead] = Field(default_factory=list)
    total: int
