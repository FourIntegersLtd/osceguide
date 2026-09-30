"""Generation response normalizers."""

from __future__ import annotations

from app.features.generation.normalizers import normalize_blog_response, normalize_summary_response


def test_normalize_summary_response_maps_b2c_fields() -> None:
    raw = {
        "name": "Asthma",
        "red_flags": ["Severe breathlessness"],
        "examinations": ["Peak flow"],
        "brief_management": ["SABA PRN"],
        "psychosocial_aspects": ["School impact"],
    }
    out = normalize_summary_response(raw)
    assert out["title"] == "Asthma"
    assert out["red_flags"] == ["Severe breathlessness"]
    assert "## Red flags" in out["body_md"]
    assert out["psychosocial_aspects"] == ["School impact"]


def test_normalize_blog_response_maps_content_to_body_md() -> None:
    out = normalize_blog_response({"title": "Tips", "content": "# Hello\n\nParagraph.", "url": "tips"})
    assert out["body_md"] == "# Hello\n\nParagraph."
    assert out["url"] == "tips"
    assert out["summary"]
