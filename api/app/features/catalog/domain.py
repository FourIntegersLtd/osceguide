"""What an exam is, and what an organisation offering one means.

Two concepts that b2c and b2b both called an exam:

- An **Exam** is a published assessment framework — SCA, PLAB 2, or whatever a
  platform admin writes next. It names the rubric version it is marked
  against. This replaces b2c's `app_type` string and the 4x20
  `COLLECTION_MAPPING` it indexed.
- A **Programme** is one organisation saying it runs one of them. This is what
  b2b's `b2b_exams` rows actually were.

Merging them would make the frameworks org-scoped or make programmes global;
ADR 0011 keeps them apart, and ADR 0016 makes the exams themselves authored.

Nothing here is a list of exams. There used to be a frozen tuple of four,
mirrored by a seed in a migration and pinned to it by a unit test, and adding a
fifth exam meant editing all three and shipping. An exam is now a row a
platform admin writes, so this module holds only the rules that govern one.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "OFFERABLE_PROGRAMME_STATUSES",
    "ExamStatus",
    "InvalidExamCode",
    "NotOfferable",
    "NotPublishable",
    "NotRetirable",
    "ProgrammeRef",
    "ensure_offerable",
    "ensure_publishable",
    "ensure_retirable",
    "normalise_code",
]

# A code appears in URLs, in a plan's `exam_code`, and in a partner ref id, so
# it is constrained rather than left as free text.
_CODE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")


class InvalidExamCode(ValueError):
    """A code that could not be used in a URL or a ref id."""


class NotPublishable(Exception):
    """An exam that is not ready to be offered to anyone."""


class NotRetirable(Exception):
    pass


class NotOfferable(LookupError):
    """An exam exists but is not published, so nothing may be built on it."""


class ExamStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


def normalise_code(raw: str) -> str:
    """The canonical spelling of an exam code.

    Case and surrounding space are not meaningful, so they are removed once
    here rather than at each of the dozen call sites that look an exam up.
    """
    code = (raw or "").strip().lower()
    if not _CODE.match(code):
        raise InvalidExamCode(
            f"{raw!r} is not a usable exam code: two to thirty-two characters, "
            "lower-case letters, digits, hyphens and underscores, starting with a letter."
        )
    return code


def ensure_publishable(status: str, rubric_version_id: uuid.UUID | None) -> ExamStatus:
    """An exam may only be published once it is clear what it is marked against.

    Without this an exam could be offered, attempted and then found to have no
    rubric at the moment somebody's transcript was due to be scored.
    """
    if ExamStatus(status) is ExamStatus.RETIRED:
        raise NotPublishable("A retired exam cannot be published again.")
    if rubric_version_id is None:
        raise NotPublishable("An exam cannot be published until it names the rubric it is marked against.")
    return ExamStatus.PUBLISHED


def ensure_retirable(status: str) -> ExamStatus:
    if ExamStatus(status) is not ExamStatus.PUBLISHED:
        raise NotRetirable("Only a published exam can be retired. A draft is simply not offered.")
    return ExamStatus.RETIRED


def ensure_offerable(status: str) -> None:
    """What may be built on: entitlements, programmes, stations, plans.

    A draft is invisible to everyone but its author, and a retired exam keeps
    its past attempts readable without accepting new ones.
    """
    if ExamStatus(status) is not ExamStatus.PUBLISHED:
        raise NotOfferable(f"That exam is {status}, so nothing new can be built on it.")


OFFERABLE_PROGRAMME_STATUSES = frozenset({"active"})


@dataclass(frozen=True)
class ProgrammeRef:
    exam_code: str
    status: str

    @property
    def is_offerable(self) -> bool:
        return self.status.strip().lower() in OFFERABLE_PROGRAMME_STATUSES
