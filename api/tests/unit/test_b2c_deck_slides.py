from app.features.media_production.summary_text import format_summary_for_podcast


def test_format_summary_for_podcast_includes_sections() -> None:
    text = format_summary_for_podcast(
        "Chest pain",
        {
            "red_flags": ["Tear"],
            "examinations": ["ECG"],
            "brief_management": ["Aspirin"],
            "psychosocial_aspects": ["Anxiety"],
        },
    )
    assert "Chest pain" in text
    assert "Tear" in text
    assert "ECG" in text
