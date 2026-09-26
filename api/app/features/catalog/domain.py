"""What an exam is, and what an organisation offering one means.

- An **Exam** is an assessment framework, written by the platform or an
  institution, naming the rubric version it is marked against.
- A **Programme** is one organisation saying it runs one of them.

See ADR 0011 and ADR 0016 for why these stay separate and exams are authored.

An exam has an **owner**, the same split stations and rubrics carry: a
platform exam is the consumer catalogue everyone can see; an org exam is an
institution's own, written without asking us and invisible outside it. Neither
arm gates the other.

This module holds only the rules that govern an exam.
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
    "NotOwned",
    "NotPublishable",
    "NotRetirable",
    "OwnerKind",
    "ProgrammeRef",
    "ensure_offerable",
    "ensure_owned_by",
    "ensure_publishable",
    "ensure_retirable",
    "normalise_code",
    "owner_of",
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


class NotOwned(PermissionError):
    """An exam exists but belongs to somebody else, so it cannot be edited."""


class OwnerKind(StrEnum):

    PLATFORM = "platform"
    ORG = "org"


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


def owner_of(org_id: uuid.UUID | None) -> OwnerKind:
    """Who is writing this exam. The platform has no org; an institution does."""
    return OwnerKind.PLATFORM if org_id is None else OwnerKind.ORG


def ensure_owned_by(exam_org_id: uuid.UUID | None, actor_org_id: uuid.UUID | None) -> None:
    """Only an exam's own owner may edit, publish or retire it.

    Reading is wider than writing: an institution reads the platform catalogue
    as well as its own, but a platform admin cannot edit Ashford's exam, and
    Ashford cannot edit ours.
    """
    if exam_org_id != actor_org_id:
        raise NotOwned("That exam belongs to a different owner.")


def ensure_offerable(status: str) -> None:
    """What may be built on: entitlements, programmes, stations, plans.

    A draft is invisible to everyone but its owner, and a retired exam keeps
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
