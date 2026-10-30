#!/usr/bin/env python3
"""Parity harness: drive a room with scripted audio, then compare two transcripts.

    play     join a room as the candidate and play a WAV (works for a legacy-routed
             room and an assessment-routed room alike; the backends create the rooms)
    compare  normalise two stored transcripts (legacy b2c, legacy b2b, or engine
             shape), compare shape and counts, and optionally score both with the
             shared evaluator and compare the result sections

Examples:
    poetry run python scripts/parity_run.py play --room unified_abc --identity user-1 --wav turn.wav --linger 30
    poetry run python scripts/parity_run.py compare legacy.json new.json --framework rubric.json --evaluate --model gpt-6-luna
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))

from osce_assessment.contracts import (  # noqa: E402
    AIInteractionProfile, AssessmentAttempt, AssessmentDefinition, EvaluationPolicy, InteractionMode, MessageRole, Scenario, ScenarioRef,
    ScenarioSource, Transcript, TranscriptMessage,
)

DOCTOR_ROLES = {"user", "doctor", "gp", "trainee", "candidate"}


def normalise(doc: dict[str, Any] | list[Any]) -> list[tuple[str, str]]:
    """``[(user|assistant, text)]`` from any of the three stored shapes."""
    if isinstance(doc, list):
        entries = doc  # legacy b2b slot transcript
    elif isinstance(doc.get("transcript_message"), list):
        entries = doc["transcript_message"]  # legacy b2c
    elif isinstance(doc.get("messages"), list):
        entries = doc["messages"]  # engine Transcript
    elif isinstance(doc.get("transcript"), (list, dict)):
        return normalise(doc["transcript"])
    else:
        raise ValueError("unrecognised transcript shape")
    out: list[tuple[str, str]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        text = str(e.get("message") or "").strip()
        if not text:
            continue
        role = "user" if str(e.get("role") or "").strip().lower() in DOCTOR_ROLES else "assistant"
        out.append((role, text))
    return out


def shape_report(name: str, turns: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "name": name,
        "turns": len(turns),
        "user_turns": sum(1 for r, _ in turns if r == "user"),
        "assistant_turns": sum(1 for r, _ in turns if r == "assistant"),
        "starts_with": turns[0][0] if turns else None,
        "alternates": all(a[0] != b[0] for a, b in zip(turns, turns[1:])),
        "user_words": sum(len(t.split()) for r, t in turns if r == "user"),
    }


def to_engine_transcript(attempt_id: str, turns: list[tuple[str, str]]) -> Transcript:
    now = datetime.now(timezone.utc)
    return Transcript(
        attempt_id=attempt_id,
        messages=tuple(TranscriptMessage(role=MessageRole(r), message=t, timestamp=now, message_id=f"{attempt_id}-{i}", seq=i) for i, (r, t) in enumerate(turns)),
        complete=True,
    )


def evaluate(turns: list[tuple[str, str]], *, framework: "CompetencyFramework", model: str, reasoning_effort: str | None, station: str) -> dict[str, Any]:
    from openai import OpenAI

    from osce_assessment.evaluation import LLMEvaluator
    from osce_assessment.testing import StaticFrameworkProvider

    framework_id = framework.id

    anthropic_client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        anthropic_client = anthropic.Anthropic()
    policy = EvaluationPolicy(framework_id=framework_id, primary_model=model, primary_reasoning_effort=reasoning_effort, fallback_model="claude-sonnet-5-5" if anthropic_client else None)
    scenario = Scenario(id="parity", source=ScenarioSource.INLINE, title=station)
    attempt = AssessmentAttempt(
        attempt_id="parity",
        definition=AssessmentDefinition(id="parity", version="1", framework_id=framework_id, scenario_ref=ScenarioRef(source=ScenarioSource.INLINE, scenario_id="parity"),
                                        interaction_profile=AIInteractionProfile(mode=InteractionMode.PATIENT), evaluation_policy=policy, snapshot_at=datetime.now(timezone.utc)),
        candidate_ref="",
    )
    evaluator = LLMEvaluator(framework_provider=StaticFrameworkProvider(framework), primary_client=lambda: OpenAI(), fallback_client=lambda: anthropic_client)
    result = evaluator.evaluate(attempt, to_engine_transcript("parity", turns), policy, scenario)
    return {"sections": sorted(result.result), "provider": result.provider, "model": result.model, "fallback_used": result.raw_metadata.get("fallback_used")}


def cmd_compare(args: argparse.Namespace) -> int:
    legacy = normalise(json.loads(Path(args.legacy).read_text()))
    new = normalise(json.loads(Path(args.new).read_text()))
    reports = [shape_report("legacy", legacy), shape_report("new", new)]
    verdict = {"same_turn_count": reports[0]["turns"] == reports[1]["turns"], "same_role_counts": (reports[0]["user_turns"], reports[0]["assistant_turns"]) == (reports[1]["user_turns"], reports[1]["assistant_turns"])}
    if args.evaluate:
        from osce_assessment.contracts import CompetencyFramework

        framework = CompetencyFramework.model_validate(json.loads(Path(args.framework).read_text()))
        scored = [evaluate(t, framework=framework, model=args.model, reasoning_effort=args.reasoning_effort, station=args.station) for t in (legacy, new)]
        verdict["same_sections"] = scored[0]["sections"] == scored[1]["sections"]
        reports[0]["evaluation"], reports[1]["evaluation"] = scored
    print(json.dumps({"reports": reports, "verdict": verdict}, indent=2))
    return 0 if all(verdict.values()) else 1


async def _play(args: argparse.Namespace) -> None:
    from livekit import api, rtc

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "e2e"))
    from _harness import play_wav  # noqa: E402

    url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
    jwt = api.AccessToken(key, secret).with_identity(args.identity).with_grants(api.VideoGrants(room_join=True, room=args.room)).to_jwt()
    room = rtc.Room()
    await room.connect(url, jwt)
    try:
        await asyncio.sleep(args.wait_before)
        await play_wav(room, args.wav)
        await asyncio.sleep(args.linger)
        print(json.dumps({"room": args.room, "agents": sorted(p.identity for p in room.remote_participants.values())}))
    finally:
        await room.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    play = sub.add_parser("play", help="join a room as the candidate and play a WAV")
    play.add_argument("--room", required=True)
    play.add_argument("--identity", required=True)
    play.add_argument("--wav", required=True)
    play.add_argument("--wait-before", type=float, default=5.0)
    play.add_argument("--linger", type=float, default=30.0)
    compare = sub.add_parser("compare", help="compare two stored transcripts")
    compare.add_argument("legacy")
    compare.add_argument("new")
    # A framework is authored data now, so the bench is handed one as a file
    # rather than naming one the engine used to ship.
    compare.add_argument("--framework", help="path to a JSON CompetencyFramework (required with --evaluate)")
    compare.add_argument("--evaluate", action="store_true")
    compare.add_argument("--model", default="gpt-6-luna")
    compare.add_argument("--reasoning-effort", default="low")
    compare.add_argument("--station", default="Parity station")
    args = parser.parse_args(argv)
    if args.command == "play":
        asyncio.run(_play(args))
        return 0
    return cmd_compare(args)


if __name__ == "__main__":
    sys.exit(main())
