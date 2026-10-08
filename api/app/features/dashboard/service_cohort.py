"""How a sitting's candidates compare — what a GP lead opens after an examination to
decide who to review first.

The arithmetic belongs to `reviews` and is asked for through its service; this module
assembles the ranking and nothing more. Ranking is **completion before score**: a
candidate who sat three of five stations has a problem nobody has looked at, and a
candidate who scored badly has at least been assessed.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.dashboard.errors import NotAnExamSitting, SittingNotFound
from app.features.dashboard.schemas_org import CohortCandidate, CohortSummary, ConsolePerson
from app.features.identity import service as identity
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings

EXAM_MODE = "exam"

# A station a candidate finished, however it ended. Oracle: b2b counts a slot
# as complete when it has an `endedAt`, not when it has been marked — marking
# happens later and the candidate has still sat the station.
COMPLETED_SLOT_STATUSES = frozenset({"completed", "abandoned", "expired"})


async def build_cohort_summary(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> CohortSummary:
    """This sitting's candidates, ranked by completion first and then score."""
    sitting = await sittings.sitting_ref(session, org_id, sitting_id)
    if sitting is None:
        raise SittingNotFound()
    if sitting.mode != EXAM_MODE:
        raise NotAnExamSitting()

    slots = await sittings.slots_for_sitting(session, org_id, sitting_id)
    outcomes = await reviews.outcomes_for_slots(session, org_id, [slot.id for slot in slots])

    user_ids = [slot.trainee_id for slot in slots]
    people = await identity.user_refs_by_ids(session, user_ids)
    trainees = await roster.trainees_by_user_id(session, org_id, user_ids)

    by_candidate: dict[uuid.UUID, list[uuid.UUID]] = {}
    for slot in slots:
        by_candidate.setdefault(slot.trainee_id, []).append(slot.id)

    candidates: list[CohortCandidate] = []
    for user_id, slot_ids in by_candidate.items():
        finished = [
            slot.id
            for slot in slots
            if slot.trainee_id == user_id
            and (slot.exam_completed_at is not None or slot.status in COMPLETED_SLOT_STATUSES)
        ]
        candidate_outcomes = [outcomes[slot_id] for slot_id in slot_ids if slot_id in outcomes]
        marked = [outcome.score for outcome in candidate_outcomes if outcome.score is not None]
        completion = len(finished) / len(slot_ids) if slot_ids else 0.0
        assessment = sum(marked) / len(marked) if marked else None

        ref = people.get(user_id)
        trainee = trainees.get(user_id)
        shown_name, shown_email = roster.shown_identity(trainee, ref)
        candidates.append(
            CohortCandidate(
                trainee=ConsolePerson(
                    user_id=user_id,
                    name=shown_name,
                    email=shown_email,
                    trainee_id=trainee.id if trainee else None,
                ),
                rank=0,
                stations_total=len(slot_ids),
                stations_completed=len(finished),
                completion_rate=completion,
                assessment_score=assessment,
                stations_passed=sum(1 for outcome in candidate_outcomes if outcome.passed is True),
                review_priority=reviews.review_priority(
                    completion_rate=completion, assessment_score=assessment
                ),
            )
        )

    ranked = sorted(candidates, key=_ranking)
    return CohortSummary(
        sitting_id=sitting_id,
        sitting_name=sitting.name,
        cohort_size=len(ranked),
        candidates=[
            candidate.model_copy(update={"rank": index + 1}) for index, candidate in enumerate(ranked)
        ],
    )


def _ranking(candidate: CohortCandidate) -> tuple[float, float, str]:
    """Completion first, then score, then email so the order is stable.

    Negated because rank 1 is the strongest. The tie-break on email is not
    cosmetic: without it two candidates with identical numbers swap places
    between requests, and a list that reorders itself is one nobody trusts.
    """
    return (
        -candidate.completion_rate,
        -(candidate.assessment_score if candidate.assessment_score is not None else -1.0),
        candidate.trainee.email or "",
    )
