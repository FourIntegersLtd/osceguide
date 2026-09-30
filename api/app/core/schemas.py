"""Response shapes shared by more than one slice.

A slice's own `schemas.py` may not import another slice's (`test_schemas_are_not_rows`
enforces this), and two slices returning identically named response models makes
FastAPI qualify both in `openapi.json`, renaming a type platform-web already
imports. A shape genuinely shared by more than one route lives here instead,
where every slice's `schemas.py` may import it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecordFieldRead(BaseModel):
    """One column of a `records` block: the key in each record, and its heading."""

    key: str
    label: str


class AudienceBlockRead(BaseModel):
    """One block of a section, as one audience may read it."""

    id: str
    label: str
    type: str
    role: str
    value: Any
    # A `records` block's template-declared `{key, label}` columns, in order;
    # None for every other type, and for records that left them to the data.
    fields: list[RecordFieldRead] | None = None


class AudienceSectionRead(BaseModel):
    """A station's content, grouped by its template's sections, for one audience.

    The one read model every screen that shows a candidate, a patient actor or
    an examiner a station's material is built from. Shared here rather than
    owned by `stations`: `attempts` and `peer_practice` both build one, and a
    slice's `schemas.py` may not import another slice's.
    """

    id: str
    title: str
    audience: str
    blocks: list[AudienceBlockRead]


class InvitationRead(BaseModel):
    """A re-sent invitation. The token itself is never returned; it goes only to
    the address it was minted for.

    Shared by roster's and tenancy's resend routes.
    """

    email: str
    invited_to: str


# --- A rubric's rating and a result's totals, read by attempts, reviews and dashboards ---

# A rating in its native units, as a route returns it: a scale word ("G"), a number or a yes/no.
RatingValueRead = bool | int | float | str


class RatingRead(BaseModel):
    """How a rubric rates a competency, for a screen that draws a rating control or reads a value."""

    kind: str
    # The competency field that holds the rating (`score`, `competent`); a
    # review path ends in it.
    field: str
    # Best first, for a `rag` or `scale` rating; empty otherwise.
    scale: list[str] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    step: str = "number"


class ReviewFieldRead(BaseModel):
    """One rating a reviewer may set, and the flat `field_values` path it is saved under."""

    # `domain.competency.<rating field>` for a competency, `domain.<rating field>` for a whole domain.
    path: str
    domain_id: str
    domain_label: str
    # Null for the whole-domain rating.
    competency_id: str | None = None
    label: str
    # What earns each rating value, keyed by value; empty when the rubric gives none.
    descriptors: dict[str, str] = Field(default_factory=dict)


class ReviewFormRead(BaseModel):
    """What an examiner or GP lead can rate on a slot, generated from the sitting's rubric."""

    rubric_version_id: str | None
    rating: RatingRead
    fields: list[ReviewFieldRead] = Field(default_factory=list)
    # A review cannot be completed until every one of these domains is rated.
    required_domains: list[str] = Field(default_factory=list)


class DomainTotalRead(BaseModel):
    """One answered domain of a result, in the display's domain aggregate."""

    id: str
    label: str
    value: float | None
    counts: dict[str, int] = Field(default_factory=dict)
    passed: bool | None = None


class ResultTotalsRead(BaseModel):
    """One result's numbers: the station total out of its maximum, pass, and critical concerns."""

    total: float | None
    max: float | None
    fraction: float | None
    passed: bool | None
    critical_count: int
    domains: list[DomainTotalRead] = Field(default_factory=list)


class TrialCandidateRead(BaseModel):
    """One row of the trial-attempt picker (rubrics plan §8, R-6): just enough to choose it by.

    Answered by `attempts.service_trial.trial_candidates` and returned by
    `rubrics`' trial-candidates routes — shared here rather than owned by
    either slice's own `schemas.py`, which `test_schemas_are_not_rows` forbids
    importing across a slice boundary. Not `AttemptRead`: a picker shows only
    what a person recognises an attempt by, never the attempt's own detail.
    """

    id: uuid.UUID
    # The candidate's name, or their email when they never set one.
    candidate_label: str
    # `None` for an attempt whose station has since been removed.
    station_title: str | None
    created_at: datetime
    turn_count: int
