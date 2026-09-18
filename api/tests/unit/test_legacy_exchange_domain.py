"""The rule that reads a legacy token's address.

`sub` is not the join. one subject is a Firestore document id, the other a Supabase
row id, and one person holds several of those — which is the whole
reason the migration merges on email. These pin that the rule agrees with
`normalize_email`, because the day they disagree every exchange silently
misses the row the import created.
"""

from __future__ import annotations

import pytest

from app.features.identity.domain import (
    LEGACY_PROVIDERS,
    LegacyTokenUnusable,
    legacy_email,
    normalize_email,
)


def test_the_address_is_read_from_the_claim_both_backends_set() -> None:
    assert legacy_email({"sub": "firestore-doc-id", "email": "doctor@example.com"}) == ("doctor@example.com")


@pytest.mark.parametrize("raw", ["Doctor@Example.com", "  doctor@example.com  ", "DOCTOR@EXAMPLE.COM"])
def test_the_address_is_normalised_the_way_the_migration_merged_it(raw: str) -> None:
    assert legacy_email({"email": raw}) == normalize_email(raw) == "doctor@example.com"


@pytest.mark.parametrize("claims", [{}, {"email": None}, {"email": ""}, {"email": "   "}, {"email": 7}])
def test_a_token_with_no_usable_address_is_refused(claims: dict[str, object]) -> None:
    # Refused rather than defaulted: a token with no address must not be
    # traded for somebody else's session.
    with pytest.raises(LegacyTokenUnusable):
        legacy_email(claims)


def test_the_provider_set_is_closed() -> None:
    # It selects the verifying secret, so an open set would let a caller pick
    # the key its token is checked against.
    assert LEGACY_PROVIDERS == ("consumer", "institution")
