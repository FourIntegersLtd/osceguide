"""Posting, liking and removing community content.

b2c has no authorisation on any of these routes: `add_comment`,
`delete_comment` and every `community/*` route carries no decorator at all, so
anyone can delete anyone's post. The rules are written down here.
"""

from __future__ import annotations

import pytest

from app.features.community import domain

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


def test_liking_twice_is_the_same_as_liking_once() -> None:
    """A like is a fact about a person, not a counter to increment — which is
    what b2c does, so a double tap counts twice."""
    assert domain.apply_like(already_liked=False) is True
    assert domain.apply_like(already_liked=True) is True


def test_unliking_removes_it() -> None:
    assert domain.apply_unlike(already_liked=True) is False
    assert domain.apply_unlike(already_liked=False) is False


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
