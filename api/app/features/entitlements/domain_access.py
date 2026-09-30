"""Which exams a person may open, and which one their screens start on.

The rule, in one place, shared by the dashboard, the station library and the study library
(each asking "which exams may I open" in its own way):

* Live entitlements first. A revoked or lapsed grant is not access — see
  `entitlements.domain.Grant.live_at`, which is why this takes the computed flag rather than
  the row.
* Then the account's own exam, chosen at sign-up. This is what a trial account has and the
  only thing it has: somebody inside their fourteen days holds no grant at all, and without
  this they would see either nothing or everything.
* Nothing else. What has been attempted or built a practice set for is deliberately not a
  source: access can lapse, and an exam somebody can no longer open should stop being offered.

Pure, and tested as such: it decides a disclosure, so it is worth being able to read on its own.
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

    `published_codes` is the catalogue, and everything is filtered through it: `users.exam_code`
    is stored unvalidated, so a code naming no published exam yields nothing rather than a dead
    option — the fail-closed half of storing a preference rather than a grant.
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
