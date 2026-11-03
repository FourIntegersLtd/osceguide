"""A new place that builds a bucket link has to be added here on purpose.

The bucket link stored in a row is permanent. That every read signs it, and every write strips the
signature, is asserted over HTTP (`test_media_signed_urls.py`, `test_station_signed_urls.py`), where a
missing call fails on the response itself. What an HTTP test cannot see is a new file that starts
minting raw links, so this lists the only files that may.
"""

from __future__ import annotations

from tests.guards._scan import APP_ROOT, python_files, rel

# Builds or parses a bucket link in order to STORE it or to sign it.
BUILDS_STORED_LINKS = {
    "app/core/object_urls.py",
    "app/features/media_production/s3.py",
    "app/features/media_production/slide_av.py",
    "app/features/media_production/slide_pictures.py",
    "app/migration/bucket_moves.py",  # writes the platform bucket's host into a link it moves
}


def test_only_known_files_build_a_bucket_link() -> None:
    builders = {rel(path) for path in python_files(APP_ROOT) if ".amazonaws.com" in path.read_text()}
    unknown = {name for name in builders if name not in BUILDS_STORED_LINKS and "/generation/" not in name}

    assert not unknown, (
        f"{sorted(unknown)} build a raw bucket link; return it through service_storage.sign_urls"
    )
