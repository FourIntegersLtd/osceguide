"""What a station may be bound to, and what a circuit may use.

The draft/published/archived machinery these rules sit on top of is shared with
templates, rubrics and feedback templates, so it lives in `app.core.lifecycle`
and is re-exported here: callers in this slice say `domain.publish(...)` as
they always did. What is left below is the part that is genuinely about
stations.

`tests/unit/test_stations_domain.py` carries the assertions.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.lifecycle import (
    AlreadyPublished,
    LifecycleError,
    NotArchivable,
    NotDeletable,
    NotEditable,
    Status,
    VersionRef,
    archive,
    ensure_brief_editable,
    ensure_deletable,
    ensure_editable,
    next_version_number,
    publish,
    seed_version,
)

__all__ = [
    "AlreadyPublished",
    "DraftExists",
    "LifecycleError",
    "NotArchivable",
    "NotDeletable",
    "NotEditable",
    "StationNotPublished",
    "Status",
    "TemplateNotPublished",
    "VersionRef",
    "archive",
    "ensure_bindable",
    "ensure_brief_editable",
    "ensure_deletable",
    "ensure_editable",
    "ensure_no_open_draft",
    "ensure_usable_in_circuit",
    "next_version_number",
    "publish",
    "seed_version",
]


class TemplateNotPublished(LifecycleError):
    """A station was built on a station template version that is still a draft."""


class StationNotPublished(LifecycleError):
    """A circuit or an attempt named a station version that is still a draft."""


class DraftExists(LifecycleError):
    """A new draft was asked for while the station already has one."""


def ensure_no_open_draft(existing: Sequence[VersionRef]) -> None:
    """Refuse a second draft: two open at once means one's edits are silently left behind."""
    for version in existing:
        if version.status is Status.DRAFT:
            raise DraftExists(f"v{version.number} is still a draft. Publish or delete it first.")


def ensure_bindable(template_version: VersionRef) -> None:
    """Refuse to build a station on a template version that is not published."""
    if template_version.status is not Status.PUBLISHED:
        raise TemplateNotPublished("A station can only be built on a published template version.")


def ensure_usable_in_circuit(station_version: VersionRef) -> None:
    """Refuse to schedule a station version that is not published.

    A station's patient material must never reach a trainee before their attempt, and a draft
    version is exactly the material still being written.
    """
    if station_version.status is not Status.PUBLISHED:
        raise StationNotPublished("A circuit can only use a published station.")
