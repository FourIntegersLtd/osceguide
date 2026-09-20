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


def test_exam_specific_articles_are_not_exposed_to_other_exams():
    specific = next(a for a in service_help.list_articles("sca") if a.app_types == ["sca"])
    with pytest.raises(NotFound):
        service_help.read_article(specific.slug, "plab")


def test_browser_endpoint_contract():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_principal] = lambda: SimpleNamespace(user_id="test")
    with TestClient(app) as client:
        categories = client.get("/api/v1/help/categories?app_type=sca")
        assert categories.status_code == 200
        category = categories.json()["categories"][0]
        articles = client.get(
            "/api/v1/help/articles", params={"app_type": "sca", "category": category["slug"]}
        )
        assert articles.status_code == 200
        slug = articles.json()["articles"][0]["slug"]
        detail = client.get(f"/api/v1/help/articles/{slug}?app_type=sca")
        assert detail.status_code == 200
        assert detail.json()["article"]["body_md"]
        assert client.get("/api/v1/help/articles/missing").status_code == 404
        assert client.get("/api/v1/help/categories?app_type=invalid").status_code == 422
