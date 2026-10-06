"""Publishing rules, ported from the legacy content service as the oracle.

Source: `backend/b2b-api/app/features/content/station_templates/service.py`
(:101, :166, :212, :330, :363) and `station_instances/service.py` (:132, :257).
The vocabulary changes; the decisions do not.
"""

from __future__ import annotations

import pytest

from app.features.stations import domain
from app.features.stations.domain import Status


def version(status: Status, number: int = 1) -> domain.VersionRef:
    return domain.VersionRef(number=number, status=status)


# --------------------------------------------------------------------------
# Editing and deleting
# --------------------------------------------------------------------------


def test_a_draft_may_be_edited_in_place() -> None:
    domain.ensure_editable(version(Status.DRAFT))


@pytest.mark.parametrize("status", [Status.PUBLISHED, Status.ARCHIVED])
def test_anything_published_is_immutable(status: Status) -> None:
    """Oracle: service.py:212. A published version is what attempts were built
    against, so editing it would rewrite history."""
    with pytest.raises(domain.NotEditable):
        domain.ensure_editable(version(status))


def test_only_a_draft_may_be_deleted() -> None:
    domain.ensure_deletable(version(Status.DRAFT))
    with pytest.raises(domain.NotDeletable):
        domain.ensure_deletable(version(Status.PUBLISHED))


def test_the_reading_brief_is_editable_on_any_live_version() -> None:
    """Oracle: service.py:247-258. The one documented exception — a brief is
    presentation, not content, and correcting it must not need a new version."""
    domain.ensure_brief_editable(version(Status.PUBLISHED))
    domain.ensure_brief_editable(version(Status.DRAFT))
    with pytest.raises(domain.NotEditable):
        domain.ensure_brief_editable(version(Status.ARCHIVED))


# --------------------------------------------------------------------------
# Publishing and archiving
# --------------------------------------------------------------------------


def test_publishing_a_draft_moves_it_to_published() -> None:
    assert domain.publish(version(Status.DRAFT)) is Status.PUBLISHED


def test_publishing_twice_is_refused() -> None:
    """Oracle: service.py:101."""
    with pytest.raises(domain.AlreadyPublished):
        domain.publish(version(Status.PUBLISHED))


def test_only_a_published_version_may_be_archived() -> None:
    """Oracle: service.py:363. Archiving a draft would hide something nobody
    ever used, which is a delete wearing another name."""
    assert domain.archive(version(Status.PUBLISHED)) is Status.ARCHIVED
    with pytest.raises(domain.NotArchivable):
        domain.archive(version(Status.DRAFT))


# --------------------------------------------------------------------------
# Seeding a new version
# --------------------------------------------------------------------------


def test_a_new_version_is_seeded_from_the_latest_published() -> None:
    """Oracle: service.py:166. Not the latest *version* — an abandoned draft
    must not become the basis of the next one."""
    existing = [version(Status.DRAFT, 3), version(Status.PUBLISHED, 2), version(Status.ARCHIVED, 1)]
    assert domain.seed_version(existing).number == 2


def test_with_nothing_published_the_latest_version_seeds_the_next() -> None:
    existing = [version(Status.DRAFT, 2), version(Status.DRAFT, 1)]
    assert domain.seed_version(existing).number == 2


def test_the_first_version_has_nothing_to_seed_from() -> None:
    assert domain.seed_version([]) is None


def test_the_next_version_number_follows_the_highest_seen() -> None:
    assert domain.next_version_number([version(Status.ARCHIVED, 7), version(Status.DRAFT, 3)]) == 8
    assert domain.next_version_number([]) == 1


# --------------------------------------------------------------------------
# Binding an instance to a template
# --------------------------------------------------------------------------


def test_an_instance_may_only_bind_a_published_template_version() -> None:
    """Oracle: station_instances/service.py:132 and re-checked at :257."""
    domain.ensure_bindable(version(Status.PUBLISHED))
    with pytest.raises(domain.TemplateNotPublished):
        domain.ensure_bindable(version(Status.DRAFT))


def test_a_circuit_may_only_reference_a_published_station() -> None:
    domain.ensure_usable_in_circuit(version(Status.PUBLISHED))
    with pytest.raises(domain.StationNotPublished):
        domain.ensure_usable_in_circuit(version(Status.DRAFT))


def test_a_new_draft_is_refused_while_a_draft_is_open() -> None:
    with pytest.raises(domain.DraftExists, match="v2 is still a draft"):
        domain.ensure_no_open_draft([version(Status.PUBLISHED, 1), version(Status.DRAFT, 2)])


def test_a_new_draft_is_allowed_when_every_version_is_published_or_archived() -> None:
    domain.ensure_no_open_draft([version(Status.PUBLISHED, 1), version(Status.ARCHIVED, 2)])
