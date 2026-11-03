"""Every folder the platform keeps in its object-storage bucket, named once.

The platform has a bucket of its own, `BUCKET`, private, and everything in it is ours: a folder is
`<kind>/<exam>/...`, so a second exam adds its own folder under each kind and nothing else changes. The
legacy site's bucket, `LEGACY_BUCKET`, is a different bucket: a stored link on its host is never signed
here, and `app.migration.bucket_moves` rewrites such a link to the file's place in this one. When the last
legacy user has moved, the whole old bucket is deleted and nothing here changes.

`Settings.aws_s3_bucket` returns `BUCKET`; there is no environment variable for it, so every service that
writes or signs links (api and worker, staging and production) uses the same bucket by construction.
"""

from __future__ import annotations

BUCKET = "osceguide-platform"
REGION = "eu-west-2"
LEGACY_BUCKET = "osceguide"

MARKETING = "marketing/"
DECKS = "teaching_videos/"
# The pictures a deck is drawn from. Signed on read like the decks they belong to.
DECK_PICTURES = f"{DECKS}sca/pictures"
PODCASTS = "podcasts/"
STATION_IMAGES = "station_images/"
# Photos uploaded before images were filed by exam: one folder per station, kept so they still show.
STATIONS = "stations/"
PEER_PRACTICE = "peer_practice/"
AVATARS = "avatars/"
ARCHIVE = "archive/"


def exam_folder(root: str, exam_code: str | None, *, fallback: str = "general") -> str:
    """`<root><exam>`, for the exam's files of that kind; `<root><fallback>` when the item has no exam."""
    return f"{root}{(exam_code or fallback).strip().lower()}"


def peer_practice_recording_key(exam_code: str, session_id: object) -> str:
    """Where a practice session's audio lives."""
    return f"{PEER_PRACTICE}{exam_code}/{session_id}/consultation.ogg"
