"""What a candidate may read about a station they are sitting, or have sat.

The station document is built from the station's template: `sections[]`, each naming an audience
(`candidate`, `patient` or `examiner`) and a list of blocks. The brief and the review are both a
list of `AudienceSectionRead` — the same read model `stations/schemas.py` defines once and
`peer_practice` reuses — projected to the audiences that screen may read, rather than named per-exam
fields. This is what keeps a template whose author gave a block a name nobody wrote into a legacy
allowlist (`ortho_management_plan`, say) rendering, where the old field-shaped schemas would have
dropped it silently.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.schemas import AudienceSectionRead


class PatientIdentityRead(BaseModel):
    """Who the candidate is about to speak to, for the consultation header."""

    name_line: str | None = None
    gender: str | None = None


class AttemptBriefRead(BaseModel):
    """The reading-time screen, keyed on the attempt rather than the station.

    Keyed on the attempt because that is what the entitlement check has already been made against;
    the library itself is browsable by everyone but carries no content. `sections` are the
    candidate-audience sections of the station's template, in template order.
    """

    attempt_id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID
    station_version_id: uuid.UUID
    station_title: str
    set_entry_id: uuid.UUID | None = None
    patient: PatientIdentityRead
    sections: list[AudienceSectionRead] = []


class AttemptReviewRead(BaseModel):
    """The management step: what the candidate should have covered.

    `sections` are the candidate-audience sections again, followed by every examiner-audience
    section — the model answer and the marking guidance, readable once the consultation is over and
    not one moment before.
    """

    attempt_id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID
    station_version_id: uuid.UUID
    station_title: str
    set_entry_id: uuid.UUID | None = None
    sections: list[AudienceSectionRead] = []


class AttemptHistoryItem(BaseModel):
    """One row of "what have I sat", with its station named.

    `has_result` rather than a status the client has to interpret: "is there
    feedback to open" is the only question every screen listing these asks.
    """

    id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID | None = None
    station_version_id: uuid.UUID | None = None
    station_title: str | None = None
    set_entry_id: uuid.UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None
    has_result: bool = False
