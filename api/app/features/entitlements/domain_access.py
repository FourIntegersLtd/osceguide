"""Which exams a person may open, and which one their screens start on.

The retiring client never asked this: `sca.osceguide.com` set an `appType` that
every request carried, so there was one exam for the whole session and no
switcher anywhere in the product. On one domain that fact has to be derived,
and each screen went on to derive it differently — the dashboard from what had
been attempted, the station library from the whole published catalogue, peer
practice from whichever exam sorted first. The result was an exam picker on
four screens of a product where almost nobody holds two exams, over a
catalogue that included exams the person had not bought.

The rule, in one place:

* **Live entitlements first.** A revoked or lapsed grant is not access — see
  `entitlements.domain.Grant.live_at`, which is why this takes the computed
  flag rather than the row.
* **Then the account's own exam**, chosen at sign-up. This is what a trial
  account has and the only thing it has: somebody inside their fourteen days
  holds no grant at all, and without this they would see either nothing or
  everything.
* **Nothing else.** What has been attempted or built a practice set for is
  deliberately not a source. Access can lapse, and an exam somebody can no
  longer open should stop being offered rather than linger because they once
  sat a station.

Pure, and tested as such: it decides a disclosure, so it is worth being able to
read on its own.

It lives in `entitlements` rather than beside the dashboard that first needed it
because three slices ask the same question — the dashboard answering "which
exams may I open", the station library deciding whose catalogue to show, and the
study library deciding what may be read — and this is the lowest slice all three
sit above.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ExamAccess:
    """What the client needs to stop asking each screen to guess."""

    codes: tuple[str, ...]
    current: str | None


def exam_access(
    *,
    live_entitlement_codes: Iterable[str],
    account_exam_code: str | None,
    published_codes: Sequence[str],
) -> ExamAccess:
    """The exams this person may open, most-entitled first.

    `published_codes` is the catalogue, and everything is filtered through it:
    `users.exam_code` is stored unvalidated, because `identity` sits below
    `catalog` and cannot resolve one. A code naming no published exam therefore
    yields nothing rather than a dead option — which is the fail-closed half of
    storing a preference rather than a grant.
    """
    published = set(published_codes)

    ordered: list[str] = []
    for code in live_entitlement_codes:
        if code and code in published and code not in ordered:
            ordered.append(code)

    trial = account_exam_code if account_exam_code in published else None
    if trial and trial not in ordered:
        ordered.append(trial)

    # The account's own exam wins the opening screen when they hold it, because
    # it is the one they said they were sitting. Otherwise the first thing they
    # actually have access to.
    current = trial if trial in ordered else (ordered[0] if ordered else None)
    return ExamAccess(codes=tuple(ordered), current=current)
