"""Turning b2b's implicit group matching into rows, once.

Lived in `roster.domain` and looked like a rule the product enforces. It is
not: b2b has no membership record and matches a trainee's `cohort` string
against a group's `label` on every circuit build, which is why renaming a group
silently empties it and nobody can be in two. The platform stores membership,
so this exists only to read the old shape at the moment a tenant crosses, and
it is deleted with the rest of `app/migration` when the last one has.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.features.roster.domain import normalize_label


def memberships_from_labels(
    *, trainees: Sequence[tuple[str, str]], groups: Sequence[tuple[str, str]]
) -> list[tuple[str, str]]:
    """`(group_id, trainee_id)` rows for every trainee whose cohort names a group.

    A trainee whose cohort matches nothing is simply not in a group, which is
    the same answer b2b gives — the difference is that here it is a fact on
    record rather than a string comparison repeated forever.
    """
    group_by_label = {normalize_label(label): group_id for group_id, label in groups}
    pairs: list[tuple[str, str]] = []
    for trainee_id, cohort in trainees:
        group_id = group_by_label.get(normalize_label(cohort))
        if group_id:
            pairs.append((group_id, trainee_id))
    return pairs
