"""Versioned help guides; no dependency on the retired Flask/Firestore app."""

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.core.errors import NotFound
from app.features.assistant.schemas import HelpArticle, HelpCategory


@lru_cache(maxsize=1)
def _catalogue() -> tuple[list[HelpCategory], list[HelpArticle]]:
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


def list_articles(exam_code: str, category: str | None = None) -> list[HelpArticle]:
    return sorted(
        (
            article
            for article in _catalogue()[1]
            if ("all" in article.exam_codes or exam_code in article.exam_codes)
            and (category is None or article.category_slug == category)
        ),
        key=lambda article: (article.sort_order, article.title),
    )


def list_categories(exam_code: str) -> list[HelpCategory]:
    counts = Counter(article.category_slug for article in list_articles(exam_code))
    return sorted(
        (
            category.model_copy(update={"article_count": counts[category.slug]})
            for category in _catalogue()[0]
            if "all" in category.exam_codes or exam_code in category.exam_codes
        ),
        key=lambda category: (category.sort_order, category.title),
    )


def read_article(slug: str, exam_code: str) -> HelpArticle:
    candidate = next((article for article in list_articles(exam_code) if article.slug == slug), None)
    if candidate is None:
        raise NotFound("Help article not found")
    visible = {article.slug for article in list_articles(exam_code)}
    return candidate.model_copy(
        update={"related_slugs": [related for related in candidate.related_slugs if related in visible]}
    )
