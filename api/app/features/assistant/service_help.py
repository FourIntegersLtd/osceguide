"""Versioned help guides; no dependency on the retired Flask/Firestore app."""

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.core.errors import NotFound
from app.features.assistant.schemas import HelpArticle, HelpCategory


@lru_cache(maxsize=1)
def _catalogue() -> tuple[list[HelpCategory], list[HelpArticle]]:
    data = json.loads(Path(__file__).with_name("help_content.json").read_text())
    categories = [
        HelpCategory.model_validate(row) for row in data["categories"] if row.get("published", True)
    ]
    titles = {row.slug: row.title for row in categories}
    articles = [HelpArticle.model_validate(row) for row in data["articles"] if row.get("published", True)]
    for article in articles:
        article.id = article.slug
        article.category_title = titles.get(article.category_slug, "")
    for category in categories:
        category.id = category.slug
    return categories, articles


def list_articles(exam_code: str, category: str | None = None) -> list[HelpArticle]:
    return sorted(
        (
            row
            for row in _catalogue()[1]
            if ("all" in row.exam_codes or exam_code in row.exam_codes)
            and (category is None or row.category_slug == category)
        ),
        key=lambda row: (row.sort_order, row.title),
    )


def list_categories(exam_code: str) -> list[HelpCategory]:
    counts = Counter(row.category_slug for row in list_articles(exam_code))
    return sorted(
        (
            row.model_copy(update={"article_count": counts[row.slug]})
            for row in _catalogue()[0]
            if "all" in row.exam_codes or exam_code in row.exam_codes
        ),
        key=lambda row: (row.sort_order, row.title),
    )


def read_article(slug: str, exam_code: str) -> HelpArticle:
    article = next((row for row in list_articles(exam_code) if row.slug == slug), None)
    if article is None:
        raise NotFound("Help article not found")
    visible = {row.slug for row in list_articles(exam_code)}
    return article.model_copy(
        update={"related_slugs": [slug for slug in article.related_slugs if slug in visible]}
    )
