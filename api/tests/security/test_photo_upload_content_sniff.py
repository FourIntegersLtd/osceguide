"""SEC-013: a station photo is checked by its bytes, not only by its name.

The extension is a claim the uploader makes. A `.png` that is really HTML or
SVG would be stored in the public images bucket, so the leading bytes must be a
PNG or JPEG signature before the file is accepted.
"""

from __future__ import annotations

import pytest

from app.features.stations import domain_photos

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_HEADER = b"\xff\xd8\xff\xe0\x00\x10JF"


@pytest.mark.parametrize("header", [PNG_HEADER, JPEG_HEADER])
def test_a_real_png_or_jpeg_is_accepted(header: bytes) -> None:
    domain_photos.ensure_real_image(header)


@pytest.mark.parametrize(
    "header",
    [
        b"<script>a",
        b"<svg xml",
        b"<!DOCTYP",
        b"GIF89a\x01\x00",
        b"",
    ],
)
def test_a_file_that_only_claims_to_be_an_image_is_refused(header: bytes) -> None:
    domain_photos.validate_upload(filename="photo.png", size=1024)  # the name passes
    with pytest.raises(domain_photos.InvalidPhoto):
        domain_photos.ensure_real_image(header)  # the bytes do not


def test_the_sniff_reads_enough_bytes_for_either_signature() -> None:
    assert len(PNG_HEADER) <= domain_photos.SNIFF_BYTES
