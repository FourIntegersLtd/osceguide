"""Actor material available to the owner after a consultation finishes."""

from pydantic import Field

from app.features.attempts.schemas_material import PatientReviewRead


class PatientRoleplayRead(PatientReviewRead):
    opening_sentence: str | None = None
    expanded_history: str | None = None
    persona: str | None = None
    family_social_history: list[str] = Field(default_factory=list)
    past_med_history_allergies: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
