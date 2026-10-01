from collections import Counter
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_principal
from app.core.errors import NotFound, register_error_handlers
from app.features.assistant import service_help
from app.features.assistant.router_help import router


@pytest.mark.parametrize("exam", ["sca", "plab", "casc", "ortho"])
def test_categories_articles_and_related_links(exam):
    articles = service_help.list_articles(exam)
    assert articles
    counts = Counter(row.category_slug for row in articles)
    for category in service_help.list_categories(exam):
        assert category.article_count == counts[category.slug]
        assert {a.slug for a in service_help.list_articles(exam, category.slug)} == {
            a.slug for a in articles if a.category_slug == category.slug
        }
    for article in articles:
        detail = service_help.read_article(article.slug, exam)
        assert detail.body_md
        assert all(service_help.read_article(slug, exam) for slug in detail.related_slugs)


def test_search_matches_a_fragment_of_the_title_or_the_body():
    """`search` is a plain case-insensitive substring test over the cached catalogue,
    not a database query — there is no database behind the help articles."""
    all_articles = service_help.list_articles("sca")
    target = next(a for a in all_articles if a.body_md)
    fragment = target.title.split()[0]

    by_title = service_help.list_articles("sca", search=fragment.upper())
    assert target.slug in {a.slug for a in by_title}

    assert service_help.list_articles("sca", search="no-such-fragment-anywhere") == []


def test_exam_specific_articles_are_not_exposed_to_other_exams():
    specific = next(a for a in service_help.list_articles("sca") if a.exam_codes == ["sca"])
    with pytest.raises(NotFound):
        service_help.read_article(specific.slug, "plab")


def test_browser_endpoint_contract():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(user_id="test")
    with TestClient(app) as client:
        categories = client.get("/api/v1/help/categories?exam_code=sca")
        assert categories.status_code == 200
        category = categories.json()["categories"][0]
        articles = client.get(
            "/api/v1/help/articles", params={"exam_code": "sca", "category": category["slug"]}
        )
        assert articles.status_code == 200
        slug = articles.json()["articles"][0]["slug"]
        searched = client.get("/api/v1/help/articles", params={"exam_code": "sca", "search": "no-match-xyz"})
        assert searched.status_code == 200
        assert searched.json()["articles"] == []
        detail = client.get(f"/api/v1/help/articles/{slug}?exam_code=sca")
        assert detail.status_code == 200
        assert detail.json()["article"]["body_md"]
        assert client.get("/api/v1/help/articles/missing").status_code == 404
        # An exam nothing was written for, and no exam at all, both get the
        # guides written for every exam and none written for one.
        for query in ("?exam_code=an-institutions-own-exam", ""):
            general = client.get(f"/api/v1/help/articles{query}")
            assert general.status_code == 200
            assert general.json()["articles"]
            assert all("all" in article["exam_codes"] for article in general.json()["articles"])
