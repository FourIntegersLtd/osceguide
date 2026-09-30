"""A trial mark: a rubric version, draft or not, marked against a sample transcript (plan §8, Stage 4).

The real engine and the same snapshot an attempt would freeze, so what the
builder shows is what a candidate would get once the version is published. But
nothing is stored: no attempt, no result row, no transcript. The marks live
only in the stream that carried them.

Everything that can be refused is refused in `prepare_trial`, before the
stream opens: a stream that answers 200 and then fails reads as a success.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.logging import get_logger
from app.core.pagination import Page
from app.core.ports import Evaluator
from app.core.sse import frame
from app.features.attempts import errors, repository, repository_transcript
from app.features.attempts.evaluator import trial_evaluator
from app.features.attempts.schemas import TrialCandidateRead, TrialMarkRead
from app.features.identity import service as identity
from app.features.rubrics import errors as rubric_errors
from app.features.rubrics import service_marking
from app.features.stations import service_reads as stations

log = get_logger(__name__)

# How often a trial still marking says so. A mark takes a minute or so; a
# snapshot every few seconds keeps the builder's timer honest and the
# connection from being closed by a proxy as idle.
TICK_SECONDS = 5.0
# What the engine is told this marking is, in place of an attempt's policy version.
TRIAL_POLICY_VERSION = "trial"

# Who counts as the candidate in a pasted transcript, by the first word of the speaker.
CANDIDATE_SPEAKERS = frozenset(
    {"candidate", "doctor", "dr", "user", "you", "trainee", "student", "clinician"}
)
# `Speaker: text`, the speaker at most three words, so a sentence with a colon
# in it ("The plan is: rest") is not read as a new speaker.
# What `prepare_trial` refuses with, besides auth and the rate limit, for the route's documented responses.
REFUSALS = (
    rubric_errors.RubricNotFound,
    rubric_errors.RubricVersionNotFound,
    rubric_errors.InvalidRubricError,
    errors.TrialTranscriptInvalid,
    errors.AttemptNotFound,
    errors.MarkerUnavailable,
)
# `trial_evaluator` is re-exported: a router reaches its slice only through `service*` (tests/guards).
__all__ = [
    "REFUSALS",
    "TrialPlan",
    "parse_transcript",
    "prepare_trial",
    "trial_candidates",
    "trial_evaluator",
    "trial_stream",
]
_SPEAKER_LINE = re.compile(r"^\s*([A-Za-z][\w'.-]*(?:\s+[A-Za-z][\w'.-]*){0,2})\s*:\s*(.*)$")


@dataclass(frozen=True)
class TrialPlan:
    """Everything a trial marks with, read before its stream opens."""

    snapshot: dict[str, Any]
    scoring_rubric: service_marking.ScoringRubric
    rubric_version_id: uuid.UUID
    turns: list[dict[str, Any]]


def parse_transcript(text: str) -> list[dict[str, Any]]:
    """A pasted transcript as the turns the evaluator reads: role, message and order.

    One turn per `Speaker: text` line. A line with no speaker continues the
    turn before it, since pasted transcripts wrap. Refused when the first line
    names no speaker or the candidate never speaks: there would be nothing to mark.
    """
    turns: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _SPEAKER_LINE.match(line)
        if match:
            speaker_first_word = match.group(1).split()[0].lower().rstrip(".")
            role = "candidate" if speaker_first_word in CANDIDATE_SPEAKERS else "patient"
            turns.append({"role": role, "message": match.group(2).strip()})
        elif turns:
            turns[-1]["message"] = f"{turns[-1]['message']} {line.strip()}".strip()
        else:
            raise errors.TrialTranscriptInvalid(
                "Start each turn with its speaker, for example `Doctor: Hello, I'm Dr Patel.`"
            )
    spoken = [turn for turn in turns if turn["message"]]
    _require_candidate(spoken)
    return [{**turn, "seq": index} for index, turn in enumerate(spoken)]


def _require_candidate(turns: list[dict[str, Any]]) -> None:
    """Refuse a transcript in which the candidate never says anything."""
    if not any(turn["role"] in {"candidate", "doctor", "user"} for turn in turns):
        raise errors.TrialTranscriptInvalid("The transcript has no line from the candidate to mark.")


async def prepare_trial(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    rubric_id: uuid.UUID,
    version: int,
    transcript: str | None,
    attempt_id: uuid.UUID | None,
    rate_key: str,
) -> TrialPlan:
    """Check everything a trial needs and read it, refusing before any stream opens.

    The version must be the owner's own and markable; the transcript either
    pasted or one of the owner's own attempts (a platform trial: an attempt
    outside any organisation). Counted against the trial allowance last, so a
    refused request costs nothing.
    """
    if (transcript is None) == (attempt_id is None):
        raise errors.TrialTranscriptInvalid("Give either a transcript or an attempt_id, not both.")
    snapshot, scoring_rubric = await service_marking.trial_rubric(session, org_id, rubric_id, version)
    if transcript is not None:
        turns = parse_transcript(transcript)
    else:
        turns = await _attempt_turns(session, org_id, attempt_id)  # type: ignore[arg-type]  # checked above
    await rate_limit.check(rate_limit.TRIAL_MARK, rate_key)
    return TrialPlan(
        snapshot=snapshot,
        scoring_rubric=scoring_rubric,
        rubric_version_id=uuid.UUID(str(scoring_rubric.version_id)),
        turns=turns,
    )


async def _attempt_turns(
    session: AsyncSession, org_id: uuid.UUID | None, attempt_id: uuid.UUID
) -> list[dict[str, Any]]:
    """An attempt's transcript, if the attempt is this owner's. Another's reads as not found."""
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None or attempt.org_id != org_id:
        raise errors.AttemptNotFound()
    chunks = await repository_transcript.chunks_for(session, attempt_id)
    turns = [{"role": chunk.role, "message": chunk.message, "seq": chunk.seq} for chunk in chunks]
    if not turns:
        raise errors.TrialTranscriptInvalid("That attempt has no transcript to mark.")
    _require_candidate(turns)
    return turns


async def trial_candidates(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None,
) -> Page[TrialCandidateRead]:
    """A page of attempts this owner could trial-mark with (rubrics plan §8, R-6).

    Scoped exactly as `prepare_trial`/`_attempt_turns` scope a trial's own
    `attempt_id`, so nothing offered here is later refused as
    `attempt_not_found`. `search` matches the candidate's name or email, or
    the station's title, resolved to ids by the owning slices
    (`identity.service.user_ids_matching`, `stations.service_reads.version_ids_matching_title`)
    rather than joined here, which is what keeps this slice's repository from
    reaching into another slice's tables.
    """
    term = (search or "").strip()
    searched = bool(term)
    matching_user_ids: list[uuid.UUID] = []
    matching_station_version_ids: list[uuid.UUID] = []
    if searched:
        matching_user_ids = await identity.user_ids_matching(session, term)
        matching_station_version_ids = await stations.version_ids_matching_title(session, term)
    attempts, next_cursor = await repository.trial_candidates(
        session,
        org_id,
        limit=limit,
        cursor=cursor,
        matching_user_ids=matching_user_ids,
        matching_station_version_ids=matching_station_version_ids,
        searched=searched,
    )
    items = await _candidate_reads(session, org_id, attempts)
    return Page(items=items, next_cursor=next_cursor)


async def _candidate_reads(
    session: AsyncSession, org_id: uuid.UUID | None, attempts: list[Any]
) -> list[TrialCandidateRead]:
    """One page of attempts turned into picker rows, each field batched rather than read per row."""
    user_ids = {attempt.user_id for attempt in attempts}
    station_version_ids = {attempt.station_version_id for attempt in attempts if attempt.station_version_id}
    attempt_ids = [attempt.id for attempt in attempts]
    users = await identity.user_refs_by_ids(session, list(user_ids))
    stations_by_version = await stations.summaries_by_version_id(session, org_id, list(station_version_ids))
    turn_counts = await repository_transcript.chunk_counts_for(session, attempt_ids)
    reads: list[TrialCandidateRead] = []
    for attempt in attempts:
        user = users.get(attempt.user_id)
        label = (user.name.strip() if user and user.name.strip() else None) or (
            user.email if user else "Unknown candidate"
        )
        summary = stations_by_version.get(attempt.station_version_id) if attempt.station_version_id else None
        reads.append(
            TrialCandidateRead(
                id=attempt.id,
                candidate_label=label,
                station_title=summary.title if summary else None,
                created_at=attempt.created_at,
                turn_count=turn_counts.get(attempt.id, 0),
            )
        )
    return reads


async def trial_stream(
    plan: TrialPlan, evaluator: Evaluator, *, tick_seconds: float = TICK_SECONDS
) -> AsyncIterator[str]:
    """`connected`, a `marking` snapshot every tick, then one `marked` or `failed` snapshot, then close.

    The marking runs as a task beside the stream. A client that disconnects
    ends the generator, which cancels the task; the engine's thread finishes
    its call on its own, and its answer is dropped.
    """
    started = time.monotonic()

    def snapshot(status: str, **outcome: Any) -> str:
        """One `snapshot` frame of the trial as it stands."""
        read = TrialMarkRead(
            status=status,
            elapsed_seconds=round(time.monotonic() - started, 1),
            rubric_version_id=plan.rubric_version_id,
            turn_count=len(plan.turns),
            **outcome,
        )
        return frame("snapshot", read.model_dump_json())

    yield frame("connected", "{}")
    marking = asyncio.create_task(
        evaluator.evaluate(rubric=plan.snapshot, policy_version=TRIAL_POLICY_VERSION, transcript=plan.turns)
    )
    try:
        while True:
            yield snapshot("marking")
            finished, _ = await asyncio.wait({marking}, timeout=tick_seconds)
            if finished:
                break
        try:
            marks = dict(marking.result())
        except Exception as exc:  # noqa: BLE001 - any failure to mark is reported, not raised mid-stream
            log.warning("trial mark failed", rubric_version=str(plan.rubric_version_id), error=str(exc))
            yield snapshot("failed", error=str(exc) or type(exc).__name__)
            return
        model_used = marks.pop("model_used", None)
        model_name = str(model_used) if model_used else None
        try:
            totals = service_marking.totals_read(plan.scoring_rubric, marks)
        except Exception as exc:  # noqa: BLE001 - marks the rubric cannot total are shown, with why
            yield snapshot(
                "failed", marks=marks, model_used=model_name, error=f"The marks could not be totalled: {exc}"
            )
            return
        yield snapshot("marked", marks=marks, totals=totals, model_used=model_name)
    finally:
        if not marking.done():
            marking.cancel()
