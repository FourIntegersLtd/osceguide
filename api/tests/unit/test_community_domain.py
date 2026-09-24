"""Posting, liking and removing community content.

b2c has no authorisation on any of these routes: `add_comment`,
`delete_comment` and every `community/*` route carries no decorator at all, so
anyone can delete anyone's post. The rules are written down here.
"""

from __future__ import annotations

import pytest

from app.features.community import domain
from app.features.community import errors as community_errors
from app.features.stations import errors as station_errors

AUTHOR = "author-1"
OTHER = "other-1"


def test_an_author_may_delete_their_own_post() -> None:
    domain.ensure_removable(author_id=AUTHOR, actor_id=AUTHOR, actor_is_admin=False)


def test_someone_else_may_not() -> None:
    """b2c's delete routes have no decorator at all."""
    with pytest.raises(domain.NotYours):
        domain.ensure_removable(author_id=AUTHOR, actor_id=OTHER, actor_is_admin=False)


def test_an_admin_may_remove_anything() -> None:
    """Moderation has to be possible, and it is not the same as authorship."""
    domain.ensure_removable(author_id=AUTHOR, actor_id=OTHER, actor_is_admin=True)


def test_empty_content_is_refused() -> None:
    with pytest.raises(domain.EmptyContent):
        domain.ensure_postable("   ")


def test_content_has_a_limit() -> None:
    with pytest.raises(domain.ContentTooLong):
        domain.ensure_postable("x" * (domain.MAX_CONTENT + 1))


def test_ordinary_content_is_accepted() -> None:
    domain.ensure_postable("How do I approach a chest pain station?")


def test_content_is_trimmed_but_not_otherwise_altered() -> None:
    assert domain.clean("  Some  spacing  kept  ") == "Some  spacing  kept"


# ------------------------------------------------------------------- tags


def test_tags_are_trimmed_lowered_and_deduplicated() -> None:
    """The legacy client's tags were lowercase specialty keys; a filter that
    matched "Cardiology" but not "cardiology" would read as a bug."""
    assert domain.clean_tags(["  Cardiology ", "cardiology", "Neurology"]) == [
        "cardiology",
        "neurology",
    ]


def test_blank_tags_are_dropped_not_stored() -> None:
    assert domain.clean_tags(["", "   ", "sca"]) == ["sca"]
    assert domain.clean_tags([]) == []


def test_an_over_long_tag_is_refused() -> None:
    with pytest.raises(domain.TagTooLong):
        domain.clean_tags(["x" * (domain.MAX_TAG_LENGTH + 1)])


def test_over_many_tags_are_refused() -> None:
    with pytest.raises(domain.TooManyTags):
        domain.clean_tags([f"tag-{i}" for i in range(domain.MAX_TAGS + 1)])


def test_duplicates_do_not_count_towards_the_limit() -> None:
    """Deduplication happens before the count is judged: five spellings of one
    tag are one tag, not a refusal."""
    assert domain.clean_tags(["one", " ONE "] * domain.MAX_TAGS) == ["one"]


def test_the_filter_tag_is_normalized_the_way_tags_are_stored() -> None:
    assert domain.normalize_tag("  Cardiology ") == "cardiology"


def test_the_mirrored_station_error_shares_the_stations_code() -> None:
    """S3: `community` declares its own `StationNotFound` so its routes
    document their own errors, but the code is the contract the client
    switches on — two classes sharing one code must not drift."""
    assert community_errors.StationNotFound.code == station_errors.StationNotFound.code
    assert community_errors.StationNotFound.code == "station_not_found"
