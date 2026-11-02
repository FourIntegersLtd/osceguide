"""Study material: slides, summaries, blogs and the search over them."""

from __future__ import annotations

import pytest

from app.features.media import domain


@pytest.mark.parametrize("kind", ["slide_deck", "summary", "blog", "podcast"])
def test_the_four_kinds(kind: str) -> None:
    assert domain.normalize_kind(kind) == kind


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(domain.UnknownMediaKind):
        domain.normalize_kind("interpretive-dance")


# --------------------------------------------------------------------------
# Publication
# --------------------------------------------------------------------------


def test_a_draft_is_not_readable_by_everyone() -> None:
    assert not domain.is_public(status="draft")
    assert domain.is_public(status="published")


def test_only_a_draft_may_be_produced_from_a_brief() -> None:
    assert domain.is_editable(status="draft")
    assert not domain.is_editable(status="published")


def test_publishing_a_draft_is_allowed() -> None:
    assert domain.publish(status="draft") == "published"


def test_publishing_twice_is_refused() -> None:
    with pytest.raises(domain.AlreadyPublished):
        domain.publish(status="published")


# --------------------------------------------------------------------------
# Slugs
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Chest Pain in Primary Care", "chest-pain-in-primary-care"),
        ("  Spaced   Out  ", "spaced-out"),
        ("Punctuation!? Removed.", "punctuation-removed"),
        ("Hyphen--Collapse", "hyphen-collapse"),
    ],
)
def test_a_slug_is_derived_from_the_title(title: str, slug: str) -> None:
    assert domain.slugify(title) == slug


def test_a_title_with_nothing_usable_is_refused() -> None:
    """Better an error than a blank URL somebody has to guess at."""
    with pytest.raises(domain.UnusableTitle):
        domain.slugify("!!!")


def test_a_long_title_is_truncated_at_a_word_boundary() -> None:
    slug = domain.slugify("word " * 60)
    assert len(slug) <= domain.MAX_SLUG
    assert not slug.endswith("-")


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


def test_a_query_is_trimmed() -> None:
    assert domain.clean_query("  chest pain  ") == "chest pain"


def test_an_empty_query_is_refused() -> None:
    """Searching for nothing would return everything, expensively."""
    with pytest.raises(domain.EmptyQuery):
        domain.clean_query("   ")


def test_a_query_is_capped() -> None:
    with pytest.raises(domain.QueryTooLong):
        domain.clean_query("x" * (domain.MAX_QUERY + 1))
