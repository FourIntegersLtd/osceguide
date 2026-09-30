"""The request and response shapes for the platform-admin content generation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateStationRequest(BaseModel):
    """What to draft a station about, for which exam, and which of its station subtypes."""

    prompt: str = Field(min_length=8, max_length=4000)
    exam_code: str = Field(min_length=2, max_length=32)
    station_subtype: str | None = Field(
        default=None,
        max_length=40,
        description="One of the exam's `settings.station_subtypes` keys; ignored if the exam lists none.",
    )


class GenerateTextRequest(BaseModel):
    """What to draft a summary, blog, deck or podcast about, and optionally for which exam."""

    prompt: str = Field(min_length=8, max_length=4000)
    exam_code: str | None = Field(default=None, max_length=32)


class GenerateResult(BaseModel):
    """The model's draft, normalised to the content type's draft keys."""

    content: dict[str, Any]
