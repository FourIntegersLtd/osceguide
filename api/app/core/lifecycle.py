"""The publishing lifecycle: draft, published, archived.

One state machine for every versioned thing the platform stores — station
templates, stations, rubrics, feedback templates — because they are the same
decision. A draft is yours to change, a published version is what attempts were
built against and is therefore immutable, and an archived one is retired but
still referenced by the attempts that used it.

It lives in `core` rather than in one slice because four slices now need it
and the alternative is four copies that drift. It is pure: no session, no
model, no knowledge of what is being versioned.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "AlreadyPublished",
    "LifecycleError",
    "NotArchivable",
    "NotDeletable",
    "NotEditable",
    "Status",
    "VersionRef",
    "archive",
    "ensure_brief_editable",
    "ensure_deletable",
    "ensure_editable",
    "next_version_number",
    "publish",
    "seed_version",
]


class Status(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LifecycleError(Exception):
    """Base for refusals; the service maps each to an AppError."""


class NotEditable(LifecycleError):
    pass


class NotDeletable(LifecycleError):
    pass


class AlreadyPublished(LifecycleError):
    pass


class NotArchivable(LifecycleError):
    pass


@dataclass(frozen=True)
class VersionRef:
    number: int
    status: Status


def ensure_editable(version: VersionRef) -> None:
    if version.status is not Status.DRAFT:
        raise NotEditable(
            "Only a draft can be edited. Published content is what past attempts were "
            "assessed against; create a new version instead."
        )


def ensure_deletable(version: VersionRef) -> None:
    if version.status is not Status.DRAFT:
        raise NotDeletable("Only a draft can be deleted. Archive a published version instead.")


def ensure_brief_editable(version: VersionRef) -> None:
    """The documented exception.

    A reading brief is what a candidate is shown before the station starts. It
    is presentation rather than assessed content, so correcting a typo in one
    must not require a new version and a fresh publish.
    """
    if version.status is Status.ARCHIVED:
        raise NotEditable("An archived version cannot be changed at all.")


def publish(version: VersionRef) -> Status:
    if version.status is Status.PUBLISHED:
        raise AlreadyPublished("That version is already published.")
    if version.status is Status.ARCHIVED:
        raise NotEditable("An archived version cannot be republished.")
    return Status.PUBLISHED


def archive(version: VersionRef) -> Status:
    if version.status is not Status.PUBLISHED:
        raise NotArchivable(
            "Only a published version can be archived. A draft that is not wanted is deleted."
        )
    return Status.ARCHIVED


def seed_version(existing: Sequence[VersionRef]) -> VersionRef | None:
    """Which version a new draft copies from.

    The latest *published* one, not the latest overall: an abandoned draft
    must not silently become the basis of everything after it.
    """
    if not existing:
        return None
    published = [version for version in existing if version.status is Status.PUBLISHED]
    pool = published or list(existing)
    return max(pool, key=lambda version: version.number)


def next_version_number(existing: Sequence[VersionRef]) -> int:
    return max((version.number for version in existing), default=0) + 1
