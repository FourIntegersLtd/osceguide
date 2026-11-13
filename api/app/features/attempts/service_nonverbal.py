"""Non-verbal feedback: who may use it, taking the browser's batches, and what the candidate reads.

Candidate-only and never part of a mark. The video stays in the browser; only per-second numbers arrive.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener
from app.core.events import publish_after_commit, user_topic
from app.core.logging import get_logger
from app.core.ports import SummaryFailed, TranscriptSummariser
from app.features.attempts import domain, errors, repository, service
from app.features.attempts import repository_nonverbal as store
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain_nonverbal import PATIENT_ROLE, build_facts
from app.features.attempts.domain_nonverbal_lingo import lingo_for
from app.features.attempts.models import Attempt
from app.features.attempts.schemas_nonverbal import (
    NonverbalBatchIn,
    NonverbalLingoRead,
    NonverbalObservationRead,
    NonverbalRead,
    NonverbalSummaryRead,
)
from app.features.attempts.service_coverage import PRACTICE_KINDS, framework_for
from app.features.attempts.service_reads import _ensure_visible, _require
from app.features.tenancy import service as tenancy

log = get_logger(__name__)

CONSENT_VERSION = "2026-11"

# Published to the candidate's `/me/events` topic once the written section (or its absence) is stored,
# so the feedback screen learns without asking.
NONVERBAL = "nonverbal"

MAX_STRENGTHS = 2
MAX_OBSERVATIONS = 4

FEEDBACK_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_STRENGTHS},
        "observations": {
            "type": "array",
            "maxItems": MAX_OBSERVATIONS,
            "items": {
                "type": "object",
                "properties": {
                    "turn_seq": {"type": "integer"},
                    "behaviour": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["turn_seq", "behaviour", "suggestion"],
            },
        },
    },
    "required": ["summary", "strengths", "observations"],
}

PROMPT = (
    "You are writing a short, kind coaching note on a clinician's non-verbal communication in a "
    "practice consultation held over a webcam. You are given the transcript. Some turns carry a "
    "bracketed non-verbal note measured by software, and the first line gives overall measurements. "
    "Use only those measurements. Describe what the clinician visibly did and when, linked to what was "
    "being said. Never state or imply what they felt, thought or intended, and never use the words "
    "empathy, emotion, anxious, nervous, bored, cold or uninterested about the clinician. Do not give "
    "a score. Do not comment on appearance. Each observation must refer to one turn that has a "
    "bracketed note, by its turn number, and give one practical suggestion. A note on a patient turn "
    "describes the clinician while listening to the patient; a note on a clinician turn describes "
    "them while speaking. If the measurements show nothing to improve, return no observations and say "
    "so in the summary. Plain English, second person, British spelling. Summary: at most 50 words."
)


async def _supported(session: AsyncSession, attempt: Attempt) -> bool:
    """A practice attempt, and for an organisation's self-practice only where the organisation allows it."""
    if attempt.kind not in PRACTICE_KINDS:
        return False
    return attempt.org_id is None or await tenancy.nonverbal_enabled(session, attempt.org_id)


def _summary_read(facts: dict[str, Any], feedback: dict[str, Any] | None) -> NonverbalSummaryRead | None:
    """The written section from a stored summary's facts and feedback, or None when none was written."""
    if not feedback:
        return None
    notable = {turn["seq"]: turn for turn in facts.get("notable_turns", [])}
    observations = [
        NonverbalObservationRead(
            at_seconds=int(notable[item["turn_seq"]]["start_seconds"]),
            quote=str(notable[item["turn_seq"]]["quote"]),
            behaviour=str(item["behaviour"]),
            suggestion=str(item["suggestion"]),
        )
        for item in feedback.get("observations", [])
        if item.get("turn_seq") in notable
    ]
    return NonverbalSummaryRead(
        summary=str(feedback.get("summary", "")),
        strengths=[str(text) for text in feedback.get("strengths", [])],
        observations=observations,
        facing_percent=int(facts.get("facing_percent", 0)),
        nods=int(facts.get("nods_total", 0)),
    )


async def read(session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID) -> NonverbalRead:
    """The candidate's non-verbal state for this attempt; refuses anyone but its owner."""
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=False)
    consent = await store.consent_for(session, requester_id)
    row = await store.summary_for(session, attempt_id)
    if row is not None:
        state = row.state
    else:
        state = "pending" if await store.has_batches(session, attempt_id) else "none"
    return NonverbalRead(
        lingo=NonverbalLingoRead(**lingo_for(framework_for(attempt))),
        supported=await _supported(session, attempt),
        consented=consent is not None and consent.withdrawn_at is None,
        consent_version=CONSENT_VERSION,
        state=state,
        summary=_summary_read(row.facts, row.feedback) if row is not None else None,
    )


async def set_consent(
    session: AsyncSession, user_id: uuid.UUID, *, consented: bool, version: str, now: datetime
) -> NonverbalRead:
    """Turn consent on, or off and delete every stored non-verbal row of this person's attempts."""
    if consented:
        if version != CONSENT_VERSION:
            raise errors.NonverbalConsentVersionStale()
        await store.upsert_consent(session, user_id, version=version, at=now)
    else:
        await store.withdraw_consent(session, user_id, at=now)
        await store.delete_all_for_attempts(session, await repository.attempt_ids_for_user(session, user_id))
    return NonverbalRead(
        lingo=NonverbalLingoRead(**lingo_for(None)),
        supported=True,
        consented=consented,
        consent_version=CONSENT_VERSION,
    )


async def accept_batch(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
    batch: NonverbalBatchIn,
    now: datetime,
) -> None:
    """Store one batch of measurements, or drop it quietly when the consultation is over."""
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=False)
    if not await _supported(session, attempt):
        raise errors.NonverbalNotAvailable()
    consent = await store.consent_for(session, requester_id)
    if consent is None or consent.withdrawn_at is not None:
        raise errors.NonverbalConsentRequired()
    deadline = await service.attempt_deadline(session, attempt)
    open_status = domain.Status(attempt.status) in (domain.Status.CREATED, domain.Status.RUNNING)
    if not open_status or (deadline is not None and now > deadline):
        log.warning("nonverbal.late_batch_refused", attempt_id=str(attempt_id), seq=batch.seq)
        return
    await store.add_batch(
        session,
        attempt_id,
        seq=batch.seq,
        skew_ms=int(now.timestamp() * 1000) - batch.client_sent_at_ms,
        samples=[sample.model_dump() for sample in batch.samples],
        at=now,
    )


@dataclass(frozen=True)
class _Prepared:
    """What the model call needs, read in a short session so none is open while it thinks."""

    user_id: uuid.UUID
    facts: dict[str, Any]
    transcript: list[dict[str, object]]
    instructions: str


def _model_transcript(facts: dict[str, Any], turns: list[Any]) -> list[dict[str, object]]:
    """The turns the model reads: an overall line first, a bracketed note on each notable turn."""
    notes = {turn["seq"]: turn["note"] for turn in facts["notable_turns"]}
    opening = "yes" if facts["smiled_in_opening"] else "no"
    out: list[dict[str, object]] = [
        {
            "role": "note",
            "message": (
                f"Overall: facing the screen {facts['facing_percent']}% of the time; "
                f"{facts['nods_total']} nods; smiled in the first 30 seconds: {opening}."
            ),
        }
    ]
    for turn in turns:
        note = f" [non-verbal, turn {turn.seq}: {notes[turn.seq]}]" if turn.seq in notes else ""
        role = "patient" if turn.role == PATIENT_ROLE else "clinician"
        out.append({"role": role, "message": f"{turn.message}{note}"})
    return out


async def _prepare(session: AsyncSession, attempt_id: uuid.UUID) -> _Prepared | None:
    """Facts and model input for an attempt still owed a summary; None when nothing is owed."""
    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None or await store.summary_for(session, attempt_id) is not None:
        return None
    batches = await store.batches_for(session, attempt_id)
    if not batches:
        return None
    if not await _supported(session, attempt):
        # The organisation switched the feature off after the video was captured: keep nothing.
        await store.delete_batches(session, [attempt_id])
        return None
    turns = await transcripts.chunks_for(session, attempt_id)
    facts = build_facts(
        [(batch.skew_ms, batch.samples) for batch in batches],
        [(turn.seq, turn.role, turn.message, turn.spoken_at) for turn in turns],
    )
    lingo = lingo_for(framework_for(attempt))
    instructions = (
        f"{PROMPT}\nThis exam calls these skills: {lingo['attention_label']}; "
        f"{lingo['listening_label']}; {lingo['rapport_label']}. Use those names where you name a skill."
    )
    return _Prepared(attempt.user_id, facts, _model_transcript(facts, turns), instructions)


async def _store(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    prepared: _Prepared,
    *,
    state: str,
    feedback: dict[str, Any] | None,
    model_used: str | None,
    now: datetime,
) -> bool:
    """Write the outcome, delete the raw per-second batches and tell the candidate's open screen.

    Stores nothing, and answers False, when the batches are already gone or consent is no longer live:
    the person withdrew (or erased their data) while the model was thinking, and a summary written now
    would outlive the erasure.
    """
    consent = await store.consent_for(session, prepared.user_id)
    if consent is None or consent.withdrawn_at is not None:
        await store.delete_batches(session, [attempt_id])
        return False
    if await store.delete_batches(session, [attempt_id]) == 0:
        return False
    await store.save_summary(
        session,
        attempt_id,
        state=state,
        facts=prepared.facts,
        feedback=feedback,
        model_used=model_used,
        at=now,
    )
    publish_after_commit(session, user_topic(prepared.user_id), NONVERBAL, {"attempt_id": str(attempt_id)})
    return True


def _clean_feedback(raw: dict[str, object], facts: dict[str, Any]) -> dict[str, Any]:
    """Keep the model's words, drop what it may not decide.

    Observations about a turn that is not notable are dropped; `at_seconds` and the quote are not kept
    from the model at all, the read fills them from the facts.
    """
    summary = str(raw.get("summary") or "").strip()
    if not summary:
        raise SummaryFailed("the non-verbal summary had no text")
    notable = {turn["seq"] for turn in facts["notable_turns"]}
    items = raw.get("observations")
    strengths = raw.get("strengths")
    observations = [
        {
            "turn_seq": item["turn_seq"],
            "behaviour": str(item["behaviour"]),
            "suggestion": str(item["suggestion"]),
        }
        for item in (items if isinstance(items, list) else [])
        if isinstance(item, dict)
        and item.get("turn_seq") in notable
        and item.get("behaviour")
        and item.get("suggestion")
    ]
    return {
        "summary": summary,
        "strengths": [str(text) for text in (strengths if isinstance(strengths, list) else [])][
            :MAX_STRENGTHS
        ],
        "observations": observations[:MAX_OBSERVATIONS],
    }


async def summarise(
    open_session: SessionOpener,
    attempt_id: uuid.UUID,
    *,
    summariser: TranscriptSummariser,
    now: datetime,
) -> bool:
    """Write the non-verbal section for a finished consultation. Returns whether a summary row was stored.

    Two short sessions with the model call between them, so no connection is held while it thinks.
    Too little video stores `insufficient` without calling the model. A model failure raises, for the
    queue to retry; `record_failed` is what the last try writes.
    """
    async with open_session() as session:
        prepared = await _prepare(session, attempt_id)
        if prepared is None:
            return False
        if prepared.facts["insufficient"]:
            return await _store(
                session, attempt_id, prepared, state="insufficient", feedback=None, model_used=None, now=now
            )
    raw = await summariser.summarise(
        kind="nonverbal",
        transcript=prepared.transcript,
        schema=FEEDBACK_SCHEMA,
        instructions=prepared.instructions,
    )
    feedback = _clean_feedback(raw, prepared.facts)
    model_used = raw.get("model_used")
    async with open_session() as session:
        return await _store(
            session,
            attempt_id,
            prepared,
            state="ready",
            feedback=feedback,
            model_used=str(model_used) if model_used else None,
            now=now,
        )


async def record_failed(open_session: SessionOpener, attempt_id: uuid.UUID, *, now: datetime) -> None:
    """After the last retry: keep the facts, store `failed`, drop the raw batches, tell the candidate."""
    async with open_session() as session:
        prepared = await _prepare(session, attempt_id)
        if prepared is not None:
            await _store(
                session, attempt_id, prepared, state="failed", feedback=None, model_used=None, now=now
            )


# A batch that lands after its summary job ran, or for an attempt that never finished, is read by no
# job. Past this age nothing is going to.
ORPHAN_BATCH_AGE = timedelta(hours=24)
ORPHAN_SWEEP_BATCH = 200


async def sweep_orphan_batches(open_session: SessionOpener, *, now: datetime) -> int:
    """Delete raw batches no summary job will read. Answers how many attempts were cleared."""
    async with open_session() as session:
        ids = await store.orphan_batch_attempt_ids(
            session,
            cutoff=now - ORPHAN_BATCH_AGE,
            open_statuses=[domain.Status.CREATED, domain.Status.RUNNING],
            limit=ORPHAN_SWEEP_BATCH,
        )
        await store.delete_batches(session, ids)
    return len(ids)
