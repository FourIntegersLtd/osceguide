"""How one exam differs from another, stored on the exam row as `exams.settings`.

Per-exam behaviour used to be a branch on the exam's code: the date label, the
debrief modes, the station subtypes and which generation prompts to use. It is
data now, so an institution's own exam and a fifth platform exam behave the way
their row says, with no release. An empty `{}` reads as every default.

It lives in core because more than one slice reads it: catalog stores and
serves it, the dashboard hands it to the home screen, and generation picks its
prompts from it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The ways a debrief can be had once a consultation is marked: talking it
# through with the tutor, or sitting the consultation again as the patient
# while the tutor plays the doctor.
SessionMode = Literal["debrief", "practice_as_patient"]

# What the help dock offers: help finding a screen, and the knowledge base.
# With more than one, the dock opens on a choice between them.
HelpMode = Literal["navigate", "knowledge_base"]


def _default_session_modes() -> list[SessionMode]:
    """Both ways of having a debrief, the tutor first."""
    return ["debrief", "practice_as_patient"]


def _default_help_modes() -> list[HelpMode]:
    """The help dock finds screens and nothing else until an exam says otherwise."""
    return ["navigate"]


class StationSubtype(BaseModel):
    """One kind of station an exam is written in, when an exam has more than one.

    An author picks one before generating a station, and the generation
    profile it names steers the prompt.
    """

    model_config = ConfigDict(extra="ignore")

    key: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    generation_profile: str = Field(min_length=1, max_length=80)


# The longest prompt an exam may carry, the same limit a station template's prompt has.
MAX_PROMPT_TEXT = 20_000


class GenerationSettings(BaseModel):
    """Which generation prompts and profile an exam's content is written with.

    Each prompt is a key naming a built-in prompt in `generation.exam_prompts`,
    or the exam's own text, which wins over the key when it is set. So a new
    exam gets its own prompts from the console with no release. The defaults
    are exam-neutral: an exam that says nothing is not written as SCA.
    """

    model_config = ConfigDict(extra="ignore")

    station_prompt: str = "generic.station"
    summary_prompt: str = "generic.summary"
    blog_prompt: str = "generic.blog"
    # The generation profile a station template uses when it names none.
    default_profile: str = "generic.station"
    # The exam's own prompt texts. Empty or `None` means use the key above.
    station_prompt_text: str | None = Field(default=None, max_length=MAX_PROMPT_TEXT)
    summary_prompt_text: str | None = Field(default=None, max_length=MAX_PROMPT_TEXT)
    blog_prompt_text: str | None = Field(default=None, max_length=MAX_PROMPT_TEXT)

    @field_validator("station_prompt_text", "summary_prompt_text", "blog_prompt_text")
    @classmethod
    def _blank_is_none(cls, text: str | None) -> str | None:
        """A prompt of only whitespace is no prompt, so the key applies rather than an empty one."""
        stripped = (text or "").strip()
        return stripped or None


class PeerPracticeSettings(BaseModel):
    """How long each phase of a peer practice session runs for an exam, in seconds.

    Two candidates read the station, one consults the other, and then they
    talk it over. An exam that says nothing gets these defaults.
    """

    model_config = ConfigDict(extra="ignore")

    preparation_seconds: int = Field(default=180, ge=1, le=3600)
    consultation_seconds: int = Field(default=720, ge=1, le=7200)
    debrief_seconds: int = Field(default=900, ge=1, le=7200)


class ExamSettings(BaseModel):
    """Everything that differs between exams apart from the rubric, as data.

    Stored in `exams.settings`. Every field has a default, so `{}` is a whole,
    valid exam: an institution's own exam behaves like the defaults until it
    says otherwise. Screens and prompts read these instead of branching on an
    exam code. Unknown keys are ignored rather than refused, so a row written
    by a newer release still reads after a rollback.
    """

    model_config = ConfigDict(extra="ignore")

    # What the learner's target date is called on the dashboard and mock setup.
    date_label: str = Field(default="Exam date", min_length=1, max_length=40)
    # The choices the debrief chooser offers, in order.
    session_modes: list[SessionMode] = Field(default_factory=lambda: _default_session_modes())
    # The kinds of station an author must choose between; empty means no choice.
    station_subtypes: list[StationSubtype] = Field(default_factory=list)
    # Whether exam tips play while a consultation is being marked.
    show_tips_while_marking: bool = False
    # What the help dock offers, in order.
    help_modes: list[HelpMode] = Field(default_factory=lambda: _default_help_modes())
    # Whether the "a colleague is waiting for peer practice" email is offered.
    peer_waiting_email: bool = False
    # How long each phase of a peer practice session runs.
    peer_practice: PeerPracticeSettings = Field(default_factory=PeerPracticeSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    def subtype(self, key: str | None) -> StationSubtype | None:
        """The station subtype with this key, matched case-insensitively, or `None`."""
        wanted = (key or "").strip().lower()
        return next((subtype for subtype in self.station_subtypes if subtype.key == wanted), None)
