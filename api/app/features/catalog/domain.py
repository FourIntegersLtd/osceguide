"""The exams the platform publishes, and what an organisation offering one means.

Two concepts that b2c and b2b both called an exam:

- An **Exam** is a published assessment framework — SCA, PLAB 2, CASC, FRCS
  Orth. There are four, they are the same for everyone, and each binds one
  `osce_assessment` framework id. This replaces b2c's `app_type` string and the
  4x20 `COLLECTION_MAPPING` it indexed.
- A **Programme** is one organisation saying it runs one of them. This is what
  b2b's `b2b_exams` rows actually were.

Merging them would make the four frameworks org-scoped or make programmes
global; ADR 0011 keeps them apart.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownExam(LookupError):
    """An exam code with no published framework. Never guessed at."""


@dataclass(frozen=True)
class Exam:
    code: str
    name: str
    framework_id: str
    # The marking model is a property of the exam, so changing it is a row
    # rather than an edit in two backends that then disagree — which is what
    # b2c (gpt-5-mini) and b2b (gpt-4o) do today.
    feedback_model_key: str
    default_reading_seconds: int
    default_simulation_seconds: int
    station_attempt_limit: int


PUBLISHED_EXAMS: tuple[Exam, ...] = (
    Exam(
        code="sca",
        name="RCGP Simulated Consultation Assessment",
        framework_id="sca-rcgp-v1",
        feedback_model_key="default",
        default_reading_seconds=3 * 60,
        default_simulation_seconds=15 * 60,
        station_attempt_limit=3,
    ),
    Exam(
        code="plab",
        name="GMC PLAB 2",
        framework_id="plab2-gmc-v1",
        feedback_model_key="default",
        default_reading_seconds=90,
        default_simulation_seconds=10 * 60,
        station_attempt_limit=3,
    ),
    Exam(
        code="casc",
        name="RCPsych CASC",
        framework_id="casc-rcpsych-v1",
        feedback_model_key="default",
        default_reading_seconds=90,
        default_simulation_seconds=10 * 60,
        station_attempt_limit=3,
    ),
    Exam(
        code="ortho",
        name="FRCS Trauma & Orthopaedics",
        framework_id="ortho-frcs-v1",
        feedback_model_key="default",
        default_reading_seconds=2 * 60,
        default_simulation_seconds=11 * 60,
        station_attempt_limit=3,
    ),
)

_BY_CODE = {exam.code: exam for exam in PUBLISHED_EXAMS}


def exam_by_code(code: str) -> Exam:
    key = (code or "").strip().lower()
    try:
        return _BY_CODE[key]
    except KeyError as exc:
        raise UnknownExam(f"No published exam {code!r}. Known codes: {', '.join(sorted(_BY_CODE))}.") from exc


OFFERABLE_PROGRAMME_STATUSES = frozenset({"active"})


@dataclass(frozen=True)
class ProgrammeRef:
    exam_code: str
    status: str

    @property
    def is_offerable(self) -> bool:
        return self.status.strip().lower() in OFFERABLE_PROGRAMME_STATUSES
