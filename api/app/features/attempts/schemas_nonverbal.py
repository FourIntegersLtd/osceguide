"""Request and response shapes for non-verbal feedback (camera measurements, consent, the read)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NonverbalSampleIn(BaseModel):
    """One second of capture, measured in the candidate's browser."""

    at_ms: int = Field(ge=0)
    face: bool
    away: bool
    yaw: int = Field(ge=-90, le=90)
    pitch: int = Field(ge=-90, le=90)
    smile: int = Field(ge=0, le=100)
    nod: bool


class NonverbalBatchIn(BaseModel):
    """Up to 30 samples, numbered so a repeat post is ignored."""

    seq: int = Field(ge=0, le=400)
    client_sent_at_ms: int
    samples: list[NonverbalSampleIn] = Field(min_length=1, max_length=30)


class NonverbalConsentIn(BaseModel):
    """Turn non-verbal feedback on (with the wording version shown) or off."""

    consented: bool
    version: str


class NonverbalObservationRead(BaseModel):
    """One thing seen at one moment, in the words said then, with a suggestion."""

    at_seconds: int
    quote: str
    behaviour: str
    suggestion: str


class NonverbalSummaryRead(BaseModel):
    """The written section shown on the feedback screen."""

    summary: str
    strengths: list[str]
    observations: list[NonverbalObservationRead]
    facing_percent: int
    nods: int


class NonverbalLingoRead(BaseModel):
    """The exam's own words the cues are shown under."""

    heading: str
    attention_label: str
    listening_label: str
    rapport_label: str


class NonverbalRead(BaseModel):
    """What the candidate may see of non-verbal feedback for one attempt."""

    lingo: NonverbalLingoRead
    supported: bool
    consented: bool = False
    consent_version: str
    state: Literal["none", "pending", "ready", "insufficient", "failed"] = "none"
    summary: NonverbalSummaryRead | None = None
