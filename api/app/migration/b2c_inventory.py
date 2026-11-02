"""Every consumer Firestore collection, and what the copy does with it.

The per-feature importers each named their own collections, and anything no
importer named was simply never copied — station-comment drift, transcripts and
payments all went missing that way. This is the single list. `import_b2c_all.py`
lists the live root collections and refuses to run if one is not accounted for
here, so a new collection is a loud failure rather than a silent gap.

A collection is either copied by a step (`COPIED`) or skipped with the reason
written down (`SKIPPED`). Per-exam names that do not exist yet in Firestore are
listed anyway: the b2c-api constants define them, and they must copy the day
they appear.
"""

from __future__ import annotations

from app.migration.b2c_media_sources import (
    B2C_MEDIA_BLOG_COLLECTIONS,
    B2C_MEDIA_SLIDE_COLLECTIONS,
    B2C_MEDIA_SUMMARY_COLLECTIONS,
)
from app.migration.b2c_social_sources import (
    B2C_COMMENT_COLLECTIONS,
    B2C_COMMUNITY_QUESTION_COLLECTIONS,
    B2C_COMMUNITY_REPLY_COLLECTIONS,
    B2C_MARKETPLACE_POST_COLLECTIONS,
    B2C_MARKETPLACE_SESSION_COLLECTIONS,
)
from app.migration.b2c_station_sources import B2C_STATION_COLLECTIONS
from app.migration.b2c_user_sources import B2C_USER_COLLECTIONS


def _per_exam(sca: str, prefix_others: str) -> dict[str, str]:
    """`{exam: collection}` for the b2c naming rule: bare for SCA, `<exam>_` otherwise."""
    return {"sca": sca, **{exam: f"{exam}_{prefix_others}" for exam in ("plab", "casc", "ortho")}}


TRANSCRIPT_COLLECTIONS = _per_exam("transcripts", "transcripts")
FEEDBACK_COLLECTIONS = _per_exam("feedbacks", "feedbacks")
DEBRIEF_COLLECTIONS = _per_exam("debriefs", "debriefs")
PAYMENT_COLLECTIONS = _per_exam("sca_payments", "payments")
REFERRAL_COLLECTIONS = _per_exam("referrals", "referrals")
CONTACT_MESSAGE_COLLECTIONS = _per_exam("messages", "messages")
FEATURE_REQUEST_COLLECTIONS = _per_exam("features", "features")
MOCK_COLLECTIONS = _per_exam("mocks", "mocks")
CV_COLLECTIONS = {"ortho": "ortho_cvs"}
HUMAN_PRACTICE_SESSION_COLLECTIONS = _per_exam("sca_human_practice_sessions", "human_practice_sessions")
HUMAN_PRACTICE_FEEDBACK_COLLECTIONS = _per_exam("sca_human_practice_feedback", "human_practice_feedback")
LIVE_COVERAGE_COLLECTION = "live_coverage_completed"
PARTNER_ARRIVAL_COLLECTION = "partner_referral_arrivals"
PARTNER_REPORTER_COLLECTION = "partner_reporters"

# step name -> {collection: exam or ""}
COPIED: dict[str, dict[str, str]] = {
    "users": {collection_name: exam for exam, collection_name in B2C_USER_COLLECTIONS.items()},
    "stations": {collection_name: exam for exam, collection_name in B2C_STATION_COLLECTIONS.items()},
    "media": {
        collection_name: exam
        for collection_map in (
            B2C_MEDIA_SUMMARY_COLLECTIONS,
            B2C_MEDIA_BLOG_COLLECTIONS,
            B2C_MEDIA_SLIDE_COLLECTIONS,
        )
        for exam, collection_name in collection_map.items()
    },
    "community": {
        collection_name: exam
        for collection_map in (
            B2C_COMMUNITY_QUESTION_COLLECTIONS,
            B2C_COMMUNITY_REPLY_COLLECTIONS,
            B2C_COMMENT_COLLECTIONS,
        )
        for exam, collection_name in collection_map.items()
    },
    "marketplace": {
        collection_name: exam
        for collection_map in (B2C_MARKETPLACE_POST_COLLECTIONS, B2C_MARKETPLACE_SESSION_COLLECTIONS)
        for exam, collection_name in collection_map.items()
    },
    "attempts": {
        collection_name: exam
        for collection_map in (TRANSCRIPT_COLLECTIONS, FEEDBACK_COLLECTIONS)
        for exam, collection_name in collection_map.items()
    },
    # A mock is a user's named bundle of stations: a station set here ("My sessions").
    "mocks": {collection_name: exam for exam, collection_name in MOCK_COLLECTIONS.items()},
    "live_coverage": {LIVE_COVERAGE_COLLECTION: ""},
    "debriefs": {collection_name: exam for exam, collection_name in DEBRIEF_COLLECTIONS.items()},
    "payments": {collection_name: exam for exam, collection_name in PAYMENT_COLLECTIONS.items()},
    "referrals": {collection_name: exam for exam, collection_name in REFERRAL_COLLECTIONS.items()},
    "partners": {PARTNER_ARRIVAL_COLLECTION: "", PARTNER_REPORTER_COLLECTION: ""},
    "cvs": {collection_name: exam for exam, collection_name in CV_COLLECTIONS.items()},
    "site_messages": {
        collection_name: exam
        for collection_map in (CONTACT_MESSAGE_COLLECTIONS, FEATURE_REQUEST_COLLECTIONS)
        for exam, collection_name in collection_map.items()
    },
    "peer_practice": {
        collection_name: exam
        for collection_map in (HUMAN_PRACTICE_SESSION_COLLECTIONS, HUMAN_PRACTICE_FEEDBACK_COLLECTIONS)
        for exam, collection_name in collection_map.items()
    },
}

_RUNTIME = "live worker/runtime state with an expiry, not a record of anything"
_NO_TABLE = "platform-api has no table for it yet"

SKIPPED: dict[str, str] = {
    "livekit_voice_sessions": _RUNTIME,
    "livekit_sessions_in_progress": _RUNTIME,
    "gpt_live_user_leases": _RUNTIME,
    "password_reset_tokens": "single-use reset tokens; copying them would re-open old links",
    "partner_pilot_config": "demo seed config for the partner dashboard",
    "no_show_standby_opt_ins": _NO_TABLE,
    "help_articles": _NO_TABLE,
    "help_categories": _NO_TABLE,
    "help_requests": _NO_TABLE,
    **{
        collection_name: "a transient matchmaking queue (entries expire in minutes)"
        for collection_name in _per_exam("sca_human_practice_queue", "human_practice_queue").values()
    },
}

# The retired pre-Supabase B2B arm. B2B data is owned by b2b-api, not this copy.
SKIPPED_PREFIXES: dict[str, str] = {"b2b_": "legacy B2B Firestore arm; B2B data is migrated from b2b-api"}


def step_for(collection: str) -> str | None:
    """Which copy step reads this collection, or None if no step claims it."""
    for step, collections in COPIED.items():
        if collection in collections:
            return step
    return None


def skip_reason(collection: str) -> str | None:
    """Why this collection is deliberately not copied, or None if it is (or is unaccounted for)."""
    if collection in SKIPPED:
        return SKIPPED[collection]
    for prefix, reason in SKIPPED_PREFIXES.items():
        if collection.startswith(prefix):
            return reason
    return None


def unaccounted(live_collections: list[str]) -> list[str]:
    """Live collections this file neither copies nor explains skipping. Should always be empty."""
    return [
        collection
        for collection in live_collections
        if step_for(collection) is None and skip_reason(collection) is None
    ]
