"""Which exams a person may open, and which one their screens start on.

A disclosure rule, so the refusals are the point: an exam somebody's access to
has lapsed must stop being offered, and a preference naming no published exam
must yield nothing rather than everything.
"""

from __future__ import annotations

import itertools

from app.features.entitlements.domain_access import exam_access

PUBLISHED = ["sca", "plab", "casc", "ortho"]


def test_a_trial_account_gets_the_exam_it_was_opened_for() -> None:
    """The case with no entitlement at all.

    Somebody inside their fourteen days holds no grant, and this is the only
    answer they have. Without it the screens see nothing and offer the whole
    catalogue instead.
    """
    access = exam_access(live_entitlement_codes=[], account_exam_code="plab", published_codes=PUBLISHED)

    assert access.codes == ("plab",)
    assert access.current == "plab"


def test_a_subscriber_gets_what_they_hold() -> None:
    access = exam_access(live_entitlement_codes=["sca"], account_exam_code="sca", published_codes=PUBLISHED)

    assert access.codes == ("sca",)
    assert access.current == "sca"


def test_the_account_exam_is_where_the_screens_open() -> None:
    """Somebody holding two exams starts on the one they signed up to sit."""
    access = exam_access(
        live_entitlement_codes=["plab", "sca"], account_exam_code="sca", published_codes=PUBLISHED
    )

    assert set(access.codes) == {"plab", "sca"}
    assert access.current == "sca"


def test_the_signup_exam_does_not_beat_a_live_grant_for_another_exam() -> None:
    """Signed up for plab, then bought sca: the screens open on sca.

    The sign-up exam is appended for a trial browse, so it is always in `codes`; letting that
    decide `current` made every screen ask about an exam the person holds no grant for, and the
    marketplace refused them `not_entitled`. It still stays browsable.
    """
    access = exam_access(live_entitlement_codes=["sca"], account_exam_code="plab", published_codes=PUBLISHED)

    assert access.codes == ("sca", "plab")
    assert access.current == "sca"


def test_a_lapsed_exam_is_not_offered() -> None:
    """Only live grants reach this — the caller filters, and here is why.

    `entitlements.list_for_user` answers with every row somebody has ever held,
    revoked and expired included. An exam they can no longer open must not stay
    in the switcher because they once had it.
    """
    access = exam_access(live_entitlement_codes=[], account_exam_code=None, published_codes=PUBLISHED)

    assert access.codes == ()
    assert access.current is None


def test_a_preference_naming_no_published_exam_yields_nothing() -> None:
    """`users.exam_code` is stored unvalidated, so this is the fail-closed half.

    `identity` sits below `catalog` and cannot resolve a code at sign-up, so a
    typo or a retired exam lands in the column. It must not become an option.
    """
    access = exam_access(live_entitlement_codes=[], account_exam_code="mrcp", published_codes=PUBLISHED)

    assert access.codes == ()
    assert access.current is None


def test_a_retired_exam_somebody_still_holds_is_not_offered() -> None:
    """The catalogue is the filter for grants too, not only for the preference."""
    access = exam_access(live_entitlement_codes=["mrcgp"], account_exam_code=None, published_codes=PUBLISHED)

    assert access.codes == ()
    assert access.current is None


def test_an_exam_is_offered_once_however_many_ways_it_is_held() -> None:
    access = exam_access(
        live_entitlement_codes=["sca", "sca"], account_exam_code="sca", published_codes=PUBLISHED
    )

    assert access.codes == ("sca",)


def test_the_first_live_grant_opens_it_when_the_account_names_no_exam() -> None:
    """An institution's member registers without one and gets theirs from the org."""
    access = exam_access(
        live_entitlement_codes=["casc", "plab"], account_exam_code=None, published_codes=PUBLISHED
    )

    assert access.codes == ("casc", "plab")
    assert access.current == "casc"


def test_the_opening_exam_is_always_one_the_person_holds_when_they_hold_any() -> None:
    """The invariant behind the marketplace refusal: every screen asks about `current`.

    For every mix of live grants and sign-up exam, `current` is a live-held exam if there is one,
    and the sign-up exam only when nothing is held (a trial).
    """
    for live in itertools.chain.from_iterable(
        itertools.combinations(PUBLISHED, n) for n in range(len(PUBLISHED) + 1)
    ):
        for account in [None, "bogus", *PUBLISHED]:
            access = exam_access(
                live_entitlement_codes=live, account_exam_code=account, published_codes=PUBLISHED
            )
            if live:
                assert access.current in live, (live, account)
                assert set(live) <= set(access.codes)
            else:
                assert access.current == (account if account in PUBLISHED else None), (live, account)
