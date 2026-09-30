"""Which generation prompt an exam gets, read from its settings rather than its code."""

from __future__ import annotations

from app.core.exam_settings import ExamSettings, GenerationSettings, StationSubtype
from app.features.generation import exam_prompts

# An exam that is none of the four platform exams, spelling out every choice:
# PLAB-style stations, the CASC summary, the PLAB blog, and two subtypes.
CUSTOM_SETTINGS = ExamSettings(
    station_subtypes=[
        StationSubtype(key="talk", label="Talking", generation_profile="ortho.communication"),
        StationSubtype(key="cv", label="Portfolio", generation_profile="ortho.portfolio"),
    ],
    generation=GenerationSettings(
        station_prompt="plab.station",
        summary_prompt="casc.summary",
        blog_prompt="plab.blog",
        default_profile="plab.station",
    ),
)


def test_custom_settings_pick_their_named_prompts() -> None:
    """Every prompt comes from the key the settings name, not from an exam code."""
    assert exam_prompts.station_system_prompt(CUSTOM_SETTINGS) == exam_prompts.PLAB_STATION_GENERATION_PROMPT
    assert exam_prompts.summary_system_prompt(CUSTOM_SETTINGS) == exam_prompts.CASC_SUMMARY_GENERATION_PROMPT
    assert exam_prompts.blog_system_prompt(CUSTOM_SETTINGS) == exam_prompts.PLAB_BLOG_PROMPT


def test_a_listed_subtype_picks_its_own_station_prompt() -> None:
    """A subtype the exam lists overrides the exam's station prompt; matching ignores case."""
    assert (
        exam_prompts.station_system_prompt(CUSTOM_SETTINGS, "TALK")
        == exam_prompts.ORTHO_COMMUNICATION_STATION_GENERATION_PROMPT
    )
    assert (
        exam_prompts.station_system_prompt(CUSTOM_SETTINGS, "cv")
        == exam_prompts.ORTHO_PORTFOLIO_STATION_GENERATION_PROMPT
    )


def test_an_unlisted_subtype_falls_back_to_the_exam_prompt() -> None:
    """A subtype the exam does not list is ignored rather than guessed at."""
    assert (
        exam_prompts.station_system_prompt(CUSTOM_SETTINGS, "clinical")
        == exam_prompts.PLAB_STATION_GENERATION_PROMPT
    )


def test_empty_settings_generate_like_a_plain_exam() -> None:
    """`{}` is a whole exam: the SCA-shaped defaults every exam used to fall back to."""
    empty = ExamSettings.model_validate({})
    assert exam_prompts.station_system_prompt(empty) == exam_prompts.SCA_STATION_GENERATION_PROMPT
    assert exam_prompts.summary_system_prompt(empty) == exam_prompts.SCA_SUMMARY_GENERATION_PROMPT
    assert exam_prompts.blog_system_prompt(empty) == exam_prompts.SCA_BLOG_PROMPT
    assert exam_prompts.unknown_prompt_keys(empty) == []


def test_unknown_keys_are_reported_by_kind() -> None:
    """A typo in any key is named, so the catalog can refuse to store it."""
    typo = ExamSettings(
        station_subtypes=[StationSubtype(key="x1", label="X", generation_profile="nope.station")],
        generation=GenerationSettings(summary_prompt="nope.summary"),
    )
    assert exam_prompts.unknown_prompt_keys(typo) == ["station:nope.station", "summary:nope.summary"]


def test_podcast_system_prompt_includes_source() -> None:
    """The podcast prompt carries the source text it was given."""
    prompt = exam_prompts.podcast_system_prompt("diabetes management summary")
    assert "diabetes management summary" in prompt
    assert "Ben:" in prompt or "ben" in prompt.lower()
