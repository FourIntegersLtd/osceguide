"""URLs of our object-storage bucket, and the two rules that keep paid media from leaking.

A produced file is stored as a plain `https://<bucket>.s3.<region>.amazonaws.com/<key>` URL and is
saved that way in a row's `content`. That raw form is a permanent link, so a read for a learner swaps
each one for a short-lived signed link (`sign_bucket_urls`), and a write throws any signature back
off (`strip_signatures`) so an expiring link is never what gets stored.

Everything here is pure: it parses and rewrites text and never touches the network. Signing itself
is the caller's job (`media_production.service_storage`), passed in as `sign_key`.

Two rules a link must pass before it is signed, because the text being rewritten is partly written
by authors: it must be on our bucket (in any spelling of the host S3 has used) and under a folder the
surface it is read through is allowed to hand out. Anything else comes back exactly as it was.

A key is read from a link with `unquote_plus`: every key this code writes is made of `a-z0-9_-./`
(see `slide_av`, `podcast_tts`, `domain_photos`), so a `+` or `%20` in a stored link can only be a
space that a console or a browser encoded, and `unquote_plus` is its inverse.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote_plus

_KEY_CHARACTERS = r"""[^\s"'<>)\]?]+"""
_QUERY_CHARACTERS = r"""[^\s"'<>)\]]*"""


def _origins(bucket: str, region: str) -> str:
    """Every spelling of this bucket's address S3 has handed out, as one regex group.

    Virtual-host and path style, regional and global, plus the old dashed regional host.
    """
    bucket_part = re.escape(bucket)
    region_part = re.escape(region)
    spellings = (
        rf"{bucket_part}\.s3\.{region_part}\.amazonaws\.com/",
        rf"{bucket_part}\.s3\.amazonaws\.com/",
        rf"{bucket_part}\.s3-{region_part}\.amazonaws\.com/",
        rf"s3\.{region_part}\.amazonaws\.com/{bucket_part}/",
        rf"s3\.amazonaws\.com/{bucket_part}/",
        rf"s3-{region_part}\.amazonaws\.com/{bucket_part}/",
    )
    return "https?://(?:" + "|".join(spellings) + ")"


def bucket_link_pattern(bucket: str, region: str) -> re.Pattern[str]:
    """Matches one of this bucket's links inside any text, including a link embedded in markdown.

    Group `key` is the link's path, still encoded.
    """
    return re.compile(_origins(bucket, region) + rf"(?P<key>{_KEY_CHARACTERS})")


def _whole_link_pattern(bucket: str, region: str) -> re.Pattern[str]:
    """Matches a string that is nothing but one of this bucket's links, spaces in the key included."""
    return re.compile(_origins(bucket, region) + r'(?P<key>[^?"\'<>\n]+)')


def object_key(encoded_path: str) -> str:
    """The key a link's path names: `+` and `%XX` decoded (see the module note)."""
    return unquote_plus(encoded_path.lstrip("/"))


def gated_key(encoded_key: str, allowed_prefixes: tuple[str, ...]) -> str | None:
    """The key a link's path names when it may be signed here, else None.

    None for a key outside `allowed_prefixes` (the surface reading it has no business handing that file out).
    """
    key = object_key(encoded_key)
    return key if key.startswith(allowed_prefixes) else None


def map_strings(value: Any, change: Callable[[str], str]) -> Any:
    """A copy of any JSON-shaped value with `change` applied to every string in it."""
    if isinstance(value, str):
        return change(value)
    if isinstance(value, dict):
        return {name: map_strings(item, change) for name, item in value.items()}
    if isinstance(value, list):
        return [map_strings(item, change) for item in value]
    return value


def strip_signatures(value: Any, *, bucket: str, region: str) -> Any:
    """The value with every signed link on this bucket cut back to its unsigned form.

    A signed link to anywhere else is somebody else's and is left alone.
    """
    signed = re.compile(
        "("
        + _origins(bucket, region)
        + _KEY_CHARACTERS
        + r")\?"
        + _QUERY_CHARACTERS
        + "X-Amz-Signature="
        + _QUERY_CHARACTERS
    )
    return map_strings(value, lambda text: signed.sub(r"\1", text) if "X-Amz-Signature=" in text else text)


def remove_bucket_links(value: Any, *, bucket: str, region: str) -> Any:
    """The value with every link on this bucket, signed or not, cut out of its strings.

    For text that is read by a model rather than shown to a person: it needs the words, and a link in
    a prompt is a working file address for whoever can read that prompt or its logs.
    """
    embedded = bucket_link_pattern(bucket, region)
    return map_strings(
        strip_signatures(value, bucket=bucket, region=region), lambda text: embedded.sub("", text)
    )


def sign_bucket_urls(
    value: Any,
    *,
    bucket: str,
    region: str,
    allowed_prefixes: tuple[str, ...],
    sign_key: Callable[[str], str],
) -> Any:
    """The value with each of this bucket's links under `allowed_prefixes` replaced by `sign_key(key)`.

    A link already signed is stripped first, so signing twice cannot stack two signatures.
    """
    embedded = bucket_link_pattern(bucket, region)
    whole = _whole_link_pattern(bucket, region)

    def swap_one(link: str, encoded_key: str) -> str:
        """Gives a link its signed form, or leaves it as it was when it may not be signed here."""
        key = gated_key(encoded_key, allowed_prefixes)
        return link if key is None else sign_key(key)

    def swap(text: str) -> str:
        """Signs a string that is one link, or every link inside a longer string."""
        single = whole.fullmatch(text)
        if single:
            return swap_one(text, single["key"])
        return embedded.sub(lambda match: swap_one(match.group(0), match["key"]), text)

    return map_strings(strip_signatures(value, bucket=bucket, region=region), swap)
