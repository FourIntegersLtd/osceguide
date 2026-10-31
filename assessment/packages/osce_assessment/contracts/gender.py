"""One reading of a station's patient gender, shared by platform-api and the voice worker."""

from __future__ import annotations

import re

_MALE = frozenset({"m", "male", "man", "boy", "mr"})
_FEMALE = frozenset({"f", "female", "woman", "girl", "mrs", "ms", "miss"})
_WORDS = re.compile(r"[a-z]+")


def parse_gender(raw: object) -> str | None:
    """`"male"` or `"female"` from free text, else None.

    The first word decides, never a substring: "female" contains "male", and "Male, 45",
    "male (54)", " (F) " and "Mrs." all begin with the word that says which. A value that also
    names the other gender ("M/F", "male or female") is ambiguous, so it is None.
    """
    words = _WORDS.findall(str(raw or "").lower())
    if not words or (_MALE.intersection(words) and _FEMALE.intersection(words)):
        return None
    if words[0] in _MALE:
        return "male"
    if words[0] in _FEMALE:
        return "female"
    return None
