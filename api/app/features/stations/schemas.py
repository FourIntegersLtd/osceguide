from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StationVersionRead(BaseModel):
    id: uuid.UUID
    station_id: uuid.UUID
    version: int
    status: str
    content: dict[str, Any]
    published_at: datetime | None = None


class LibraryStationRead(BaseModel):
    """Platform library row for browse lists — no station content."""

    id: uuid.UUID
    title: str
    exam_code: str
    version_id: uuid.UUID
    version: int
    published_at: datetime | None = None


class StationRead(BaseModel):
    id: uuid.UUID
    title: str
    owner_kind: str
    exam_code: str
    status: str
    version: int
    content: dict[str, Any] | None = None
    current_version_id: uuid.UUID | None = None


class CreateStation(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    exam_code: str = Field(min_length=1, max_length=32)
    content: dict[str, Any]


class UpdateVersion(BaseModel):
    content: dict[str, Any]
