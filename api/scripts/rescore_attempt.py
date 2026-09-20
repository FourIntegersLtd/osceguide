"""One-off: mark an attempt that finished interaction but has no result."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import UTC, datetime

from app.core.db import job_session
from app.features.attempts.evaluator import build_evaluator
from app.features.attempts.jobs import PLATFORM_DEFAULT_POLICY, score_attempt_now
from app.features.attempts.scoring import enqueue_scoring
from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts


async def _run(attempt_id: uuid.UUID, *, queue_only: bool) -> None:
    async with job_session() as session:
        attempt = await repository.attempt_by_id(session, attempt_id)
        if attempt is None:
            raise SystemExit(f"No attempt {attempt_id}")

        turns = await transcripts.chunks_for(session, attempt_id)
        if not turns:
            raise SystemExit("Attempt has no transcript chunks")

        await repository.set_status(
            session,
            attempt_id,
            status="interaction_complete",
            at=datetime.now(UTC),
            reason=None,
        )

        if queue_only:
            await enqueue_scoring(session, attempt, now=datetime.now(UTC))
            print(f"Queued score_attempt for {attempt_id}")
            return

        evaluator = build_evaluator()
        wrote = await score_attempt_now(
            session,
            attempt_id,
            evaluator=evaluator,
            policy_version=PLATFORM_DEFAULT_POLICY,
            framework_id=str((attempt.definition or {}).get("framework_id") or ""),
            now=datetime.now(UTC),
        )
        print(f"score_attempt_now wrote={wrote} for {attempt_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt_id", type=uuid.UUID)
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Enqueue for the worker instead of scoring inline",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.attempt_id, queue_only=args.queue))


if __name__ == "__main__":
    main()
