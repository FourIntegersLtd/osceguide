"""The request and response shapes for the platform-admin content generation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateStationRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=4000)
    exam_code: str = Field(min_length=2, max_length=32)
    ortho_station_type: str | None = Field(
        default=None,
        max_length=32,
        description="When exam_code is ortho: clinical, communication, prioritisation, or portfolio.",
    )


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=4000)
    exam_code: str | None = Field(default=None, max_length=32)


class GenerateResult(BaseModel):
    content: dict[str, Any]
