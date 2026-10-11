from __future__ import annotations

from app.features.media_production.captions import deck_captions_vtt


def _slide(**extra: object) -> dict:
    return {
        "start_time": 10.0,
        "intro_duration": 4.0,
        "narration": {"intro": "Over sixty, with bone pain.", "items": ["Anaemia is common."]},
        "bullet_audio_segments": [
            {"bullet_index": 0, "text": "Anaemia is common.", "start_time": 5.0, "duration": 2.0}
        ],
        **extra,
    }


def test_captions_follow_the_stored_timings_on_the_decks_clock() -> None:
    vtt = deck_captions_vtt({"final_video_url": "https://v/x.mp4", "slides": [_slide()]})

    assert vtt == (
        "WEBVTT\n\n"
        "00:00:10.500 --> 00:00:14.200\nOver sixty, with bone pain.\n\n"
        "00:00:15.000 --> 00:00:16.700\nAnaemia is common.\n"
    )


def test_a_slide_without_timings_gets_no_cues_and_a_deck_without_any_gets_no_track() -> None:
    untimed = {"narration": {"intro": "Hello."}}
    assert deck_captions_vtt({"final_video_url": "https://v/x.mp4", "slides": [untimed]}) is None
    assert deck_captions_vtt({"slides": [_slide()]}) is None  # no video
    mixed = deck_captions_vtt({"final_video_url": "https://v/x.mp4", "slides": [untimed, _slide()]})
    assert mixed is not None and mixed.count("-->") == 2
