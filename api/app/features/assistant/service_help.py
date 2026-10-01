"""Versioned help guides; no dependency on the retired Flask/Firestore app."""

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.core.errors import NotFound
from app.features.assistant.schemas import HelpArticle, HelpCategory


@lru_cache(maxsize=1)
def _catalogue() -> tuple[list[HelpCategory], list[HelpArticle]]:
    """The help catalogue, parsed once and cached: categories and articles, published only."""
    catalogue_json = json.loads(Path(__file__).with_name("help_content.json").read_text())
    categories = [
        HelpCategory.model_validate(raw_category)
        for raw_category in catalogue_json["categories"]
        if raw_category.get("published", True)
    ]
    titles = {category.slug: category.title for category in categories}
    articles = [
        HelpArticle.model_validate(raw_article)
        for raw_article in catalogue_json["articles"]
        if raw_article.get("published", True)
    ]
    for article in articles:
        article.id = article.slug
        article.category_title = titles.get(article.category_slug, "")
    for category in categories:
        category.id = category.slug
    return categories, articles


def all_articles() -> list[HelpArticle]:
    """Every published article, for every exam, for the tutor's material index."""
    return list(_catalogue()[1])


def list_articles(
    exam_code: str | None, category: str | None = None, search: str | None = None
) -> list[HelpArticle]:
    """This exam's published articles, in this category if one is given.

    An article is written either for every exam or for the exams it lists.
    With no exam, or one no article names, only the first kind is returned.

    `search` matches a fragment of the title or the body, case-insensitively —
    this catalogue is a small, cached, in-memory list rather than a database
    table, so the match is a plain substring test rather than an `ILIKE`.
    """
    term = search.strip().lower() if search else None
    return sorted(
        (
            article
            for article in _catalogue()[1]
            if ("all" in article.exam_codes or exam_code in article.exam_codes)
            and (category is None or article.category_slug == category)
            and (term is None or term in article.title.lower() or term in article.body_md.lower())
        ),
        key=lambda article: (article.sort_order, article.title),
    )


def list_categories(exam_code: str | None) -> list[HelpCategory]:
    """This exam's categories, each carrying how many of its articles apply."""
    counts = Counter(article.category_slug for article in list_articles(exam_code))
    return sorted(
        (
            category.model_copy(update={"article_count": counts[category.slug]})
            for category in _catalogue()[0]
            if "all" in category.exam_codes or exam_code in category.exam_codes
        ),
        key=lambda category: (category.sort_order, category.title),
    )


def read_article(slug: str, exam_code: str | None) -> HelpArticle:
    """One article by slug, with any related link this exam cannot see removed."""
    candidate = next((article for article in list_articles(exam_code) if article.slug == slug), None)
    if candidate is None:
        raise NotFound("Help article not found")
    visible = {article.slug for article in list_articles(exam_code)}
    return candidate.model_copy(
        update={"related_slugs": [related for related in candidate.related_slugs if related in visible]}
    )
