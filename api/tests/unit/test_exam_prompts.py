"""B2C prompt resolvers."""

from __future__ import annotations

from app.features.generation import exam_prompts


def test_station_system_prompt_sca() -> None:
    prompt = exam_prompts.station_system_prompt("sca")
    assert "UK primary care" in prompt
    assert "Anti-plagiarism" in prompt


def test_station_system_prompt_ortho_clinical() -> None:
    prompt = exam_prompts.station_system_prompt("ortho", "clinical")
    assert "Orthopaedic ST3" in prompt


def test_summary_system_prompt_casc() -> None:
    prompt = exam_prompts.summary_system_prompt("casc")
    assert "psychiatrist" in prompt.lower()


def test_blog_system_prompt_plab() -> None:
    prompt = exam_prompts.blog_system_prompt("plab")
    assert "PLAB" in prompt


def test_podcast_system_prompt_includes_source() -> None:
    prompt = exam_prompts.podcast_system_prompt("diabetes management summary")
    assert "diabetes management summary" in prompt
    assert "Ben:" in prompt or "ben" in prompt.lower()
