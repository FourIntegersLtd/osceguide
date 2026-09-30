"""Assembling the cohort read-out. A projection over the cohort, and nothing else.

The ranking is not recomputed here — `service_cohort` owns it, and a second
implementation of "completion before score" is how two screens come to disagree
about who is failing. What this module adds is the summary and the recommendation
sentences under it; changing the bands is a change to the product, not to this file.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.dashboard import service_cohort
from app.features.dashboard.schemas_org import CohortCandidate
from app.features.dashboard.schemas_readout import ReadoutSitting, ReadoutSummary, SittingReadout
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as rubric_scoring
from app.features.sittings import service_reads as sittings

# The four review priorities, in the order a reader works down the page. Fixed
# here so a cohort of nobody still reports four zeroes rather than an empty
# object the document has to special-case.
_PRIORITY_ORDER = ("urgent", "high", "standard", "low")

# Oracle: b2b's `METHODOLOGY`, restated for what this backend actually does and
# generated from the sitting's rubric (`_methodology`) — the arithmetic lives in
# `reviews.scoring`, and the ranking in `service_cohort._ranking`.
_RANKING_SENTENCES = (
    "A candidate's assessment score is the mean of the stations they completed; completion is "
    "tracked separately, so a candidate who sat two stations of five is not ranked as though they "
    "scored badly on five. Ranking is by completion first, then assessment score, then name."
)


async def build_readout(
    session: AsyncSession,
    org_id: uuid.UUID,
    org_slug: str,
    sitting_id: uuid.UUID,
    *,
    now: datetime,
) -> SittingReadout:
    """The read-out for one sitting.

    Raises what the cohort raises — `sitting_not_found` (404) for a sitting that
    is not this organisation's, `not_an_exam_sitting` (422) for a training one.
    A training session has no read-out to export: its candidates were not being
    assessed, and a document that ranks them would make it look like they were.
    """
    summary = await service_cohort.build_cohort_summary(session, org_id, sitting_id)
    candidates = sorted(summary.candidates, key=lambda candidate: candidate.rank)
    # Asked for the row a second time for its date, which the cohort does not
    # carry. It exists — `build_cohort_summary` has just refused the sitting that
    # does not — so this cannot come back empty.
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    assert sitting is not None
    scoring_rubric = await rubrics.scoring_rubric_for_version(session, org_id, sitting.rubric_version_id)

    complete = [candidate for candidate in candidates if candidate.completion_rate >= 1.0]
    priorities = {name: 0 for name in _PRIORITY_ORDER}
    for candidate in candidates:
        priorities[candidate.review_priority] = priorities.get(candidate.review_priority, 0) + 1

    average = _average_assessment_score(candidates)
    readout_summary = ReadoutSummary(
        cohort_size=len(candidates),
        fully_complete_count=len(complete),
        average_assessment_score=average,
        priorities=priorities,
        computed_at=now,
    )
    return SittingReadout(
        generated_at=now,
        org_slug=org_slug,
        sitting=ReadoutSitting(
            sitting_id=str(sitting_id),
            name=summary.sitting_name if sitting is None else sitting.name,
            scheduled_for=None if sitting is None else sitting.scheduled_for,
            required_station_count=max((candidate.stations_total for candidate in candidates), default=0),
        ),
        summary=readout_summary,
        recommendations=_recommendations(
            cohort_size=len(candidates),
            fully_complete=len(complete),
            average=average,
            priorities=priorities,
        ),
        candidates=candidates,
        methodology=_methodology(scoring_rubric),
    )


def _methodology(scoring_rubric: rubrics.ScoringRubric) -> str:
    """How the scores in the document were worked out, said from the sitting's own rubric.

    Nothing here names an exam: the rating kind says what a domain rating is
    worth, and the display says what a pass is.
    """
    structure = scoring_rubric.structure
    rating = structure.rating
    if rating.is_enumerated:
        worths = [
            f"{scale_value} {_whole(rubric_scoring.rating_percent(structure, scale_value))}"
            for scale_value in rating.scale
        ]
        rating_sentence = (
            f"A domain is one rating on the scale {', '.join(rating.scale)} (best first), "
            f"worth {_listed(worths)} out of 100"
        )
    elif rating.kind == "boolean":
        rating_sentence = "A domain is one competent or not-competent rating, worth 100 or 0"
    else:
        rating_sentence = (
            f"A domain is one rating from {_whole(rating.minimum)} to {_whole(rating.maximum)}, "
            "worth its share of the maximum out of 100"
        )
    sentences = [
        "An exam sitting expects one attempt at each station per candidate. Each station score is the "
        "equally-weighted mean of its domain ratings.",
        f"{rating_sentence}: the GP lead's rating where they set one, otherwise the reviewers' ratings "
        "in that domain combined (the most common value, a tie resolved to the worse one, or the mean "
        "of a number).",
    ]
    total = scoring_rubric.display["total"]
    if total.get("passAtLeast") is not None:
        out_of = f" of {_whole(total['max'])}" if total.get("max") is not None else ""
        every_domain = " and every domain meets its own pass line" if total.get("requireEveryDomain") else ""
        sentences.append(
            f"A station passes when its total ({total['aggregate']}) reaches {_whole(total['passAtLeast'])}"
            f"{out_of}{every_domain}."
        )
    else:
        sentences.append("The rubric sets no pass line, so stations are ranked but not passed or failed.")
    sentences.append(_RANKING_SENTENCES)
    return " ".join(sentences)


def _whole(number: float | int | None) -> str:
    """A number as a reader writes it: 66 rather than 66.0, and a dash for none."""
    if number is None:
        return "-"
    return str(int(number)) if float(number).is_integer() else f"{float(number):g}"


def _listed(parts: list[str]) -> str:
    """Parts joined as prose: "a, b or c"."""
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} or {parts[-1]}"


def _average_assessment_score(candidates: list[CohortCandidate]) -> float | None:
    """The cohort's mean, over the candidates who have a score at all.

    Somebody nobody has marked is not a zero in this average. Counting them as
    one would pull a cohort's figure down for work a reviewer has not done yet,
    and the resulting sentence is the one that tells an institution its
    framework is producing usable differentiation.
    """
    scored = [
        candidate.assessment_score for candidate in candidates if candidate.assessment_score is not None
    ]
    if not scored:
        return None
    return round(sum(scored) / len(scored), 1)


def _recommendations(
    *, cohort_size: int, fully_complete: int, average: float | None, priorities: dict[str, int]
) -> list[str]:
    """The closing section of the document, as sentences.

    Bands and wording carried over from b2b's `_build_recommendations`. They are
    not arbitrary: 0.5 completion is where `review_priority` already decides a
    candidate is urgent, 60 is where an amber cohort stops reading as a pass, and
    the last line exists because a document that ranks people must say who the
    ranking does not decide for.
    """
    if cohort_size == 0:
        return ["No candidates were assigned to this sitting."]

    complete_percent = round((fully_complete / cohort_size) * 100)
    lines = [
        f"{fully_complete} of {cohort_size} candidates ({complete_percent}%) completed every "
        "required station in this sitting."
    ]
    if priorities.get("low", 0) > 0:
        lines.append(
            f"{priorities['low']} candidate(s) show strong performance (low review priority) and may "
            "be suitable for streamlined sign-off."
        )
    if priorities.get("urgent", 0) > 0:
        lines.append(
            f"{priorities['urgent']} candidate(s) require urgent follow-up before a deployment "
            "decision is taken."
        )
    elif priorities.get("high", 0) > 0:
        lines.append(
            f"{priorities['high']} candidate(s) are flagged for high-priority review before sign-off."
        )

    if average is not None:
        if average >= 75.0 and complete_percent >= 60:
            lines.append(
                "Cohort averages suggest the assessment framework is producing usable "
                "differentiation for selection decisions."
            )
        elif average < 60.0 or complete_percent < 40:
            lines.append(
                "Completion or score averages are below the expected band. Consider additional "
                "coaching or a retake sitting before the final review."
            )
        else:
            lines.append("Review candidates individually; cohort averages sit in a mixed band.")

    lines.append(
        "The final decision rests with the institution's GP lead. This readout supports review priority only."
    )
    return lines
