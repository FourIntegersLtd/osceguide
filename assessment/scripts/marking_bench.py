#!/usr/bin/env python3
"""Marking bench: score the same transcripts with several primary models and compare the marks.

    run     mark every case once per arm through the engine's own LLMEvaluator, with no
            fallback, so a schema failure counts against the model that made it
    report  compare each arm with a baseline arm: rating agreement, mean absolute
            per-domain difference, schema failures, cost per mark and latency

An arm is a model id (a ``claude-`` id is marked through the engine's fallback path);
repeat one (``gpt-6-luna,gpt-6-luna``) to measure its run-to-run
noise, which is the bar a cheaper model has to stay within. Arms are labelled
``model#n`` in the output.

A cases file is a JSON list of ``{"attempt_id", "rubric": {"framework", "system_prompt"},
"turns": [{"role", "message", "seq"}]}``: the rubric frozen on an attempt and its turns,
exactly what platform-api's scoring job hands the engine. Use test data only (staging,
fixtures), never production transcripts.

Examples (OPENAI_API_KEY, and ANTHROPIC_API_KEY for a claude- arm, in the environment):
    poetry run python scripts/marking_bench.py run --cases cases.json --arms gpt-6-luna,gpt-6-luna,gpt-5.6-luna --out runs.json
    poetry run python scripts/marking_bench.py report runs.json --baseline gpt-6-luna#1
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_bench import PRICES  # noqa: E402
from osce_assessment.contracts import CompetencyFramework, EvaluationPolicy, Scenario, ScenarioSource  # noqa: E402
from parity_run import to_engine_transcript  # noqa: E402


class _Recording:
    """An OpenAI or Anthropic client that remembers each call's token usage and latency."""

    def __init__(self, client: Any) -> None:
        self.usage: list[tuple[int, int, int]] = []
        self.seconds = 0.0
        self._client = client
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._openai))
        self.messages = SimpleNamespace(create=self._anthropic)

    def _timed(self, create: Any, kwargs: dict[str, Any]) -> Any:
        started = time.monotonic()
        try:
            return create(**kwargs)
        finally:
            self.seconds += time.monotonic() - started

    def _openai(self, **kwargs: Any) -> Any:
        response = self._timed(self._client.chat.completions.create, kwargs)
        u = response.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        self.usage.append((u.prompt_tokens, cached, u.completion_tokens))
        return response

    def _anthropic(self, **kwargs: Any) -> Any:
        response = self._timed(self._client.messages.create, kwargs)
        u = response.usage
        cached = getattr(u, "cache_read_input_tokens", 0) or 0
        self.usage.append((u.input_tokens + cached, cached, u.output_tokens))
        return response


def cost(model: str, usage: list[tuple[int, int, int]]) -> float | None:
    """Dollars for the recorded usage at list price, or None for a model with no price row."""
    if model not in PRICES:
        return None
    rate_in, rate_cached, rate_out = PRICES[model]
    return sum(((p - c) * rate_in + c * rate_cached + o * rate_out) / 1e6 for p, c, o in usage)


def mark(case: dict[str, Any], model: str, effort: str | None) -> dict[str, Any]:
    """One case marked by one model, as the scoring job does it (no examiner context, title "Station")."""
    from openai import OpenAI

    from osce_assessment.contracts import (
        AIInteractionProfile, AssessmentAttempt, AssessmentDefinition, InteractionMode, ScenarioRef,
    )
    from osce_assessment.evaluation import LLMEvaluator
    from osce_assessment.testing import StaticFrameworkProvider

    framework = CompetencyFramework.model_validate(case["rubric"]["framework"])
    # A claude- arm is marked by the fallback path alone, as when the primary fails.
    fallback = model.startswith("claude-")
    policy = EvaluationPolicy(
        framework_id=framework.id, openai_model="none" if fallback else model,
        openai_reasoning_effort=None if fallback else effort, anthropic_model=model if fallback else None,
        system_prompt_override=case["rubric"].get("system_prompt") or None,
    )
    attempt = AssessmentAttempt(attempt_id=case["attempt_id"], definition=AssessmentDefinition(
        id="bench", version="1", framework_id=framework.id,
        scenario_ref=ScenarioRef(source=ScenarioSource.INLINE, scenario_id="bench"),
        interaction_profile=AIInteractionProfile(mode=InteractionMode.PATIENT), evaluation_policy=policy,
        snapshot_at=datetime.now(timezone.utc),
    ), candidate_ref="")
    turns = [("user" if t["role"] in {"user", "doctor", "candidate"} else "assistant", t["message"]) for t in case["turns"]]
    if fallback:
        from anthropic import Anthropic

        client = _Recording(Anthropic())
        evaluator = LLMEvaluator(framework_provider=StaticFrameworkProvider(framework),
                                 primary_client=lambda: None, fallback_client=lambda: client)
    else:
        client = _Recording(OpenAI())
        evaluator = LLMEvaluator(framework_provider=StaticFrameworkProvider(framework), primary_client=lambda: client)
    row: dict[str, Any] = {"case": case["attempt_id"], "model": model}
    try:
        result = evaluator.evaluate(attempt, to_engine_transcript(case["attempt_id"], turns), policy,
                                    Scenario(id="bench", source=ScenarioSource.INLINE, title="Station"))
        row["payload"] = result.result
    except Exception as exc:  # noqa: BLE001 - a failure is a result here
        row["error"] = str(exc)[:500]
    row.update(seconds=round(client.seconds, 1), usage=client.usage, dollars=cost(model, client.usage))
    return row


def cmd_run(args: argparse.Namespace) -> int:
    cases = json.loads(Path(args.cases).read_text())
    seen: dict[str, int] = {}
    arms = []
    for model in args.arms.split(","):
        seen[model] = seen.get(model, 0) + 1
        arms.append((f"{model}#{seen[model]}", model))
    jobs = [(label, model, case) for label, model in arms for case in cases]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(lambda job: {"arm": job[0], **mark(job[2], job[1], args.effort)}, jobs))
    frameworks = {c["attempt_id"]: c["rubric"]["framework"] for c in cases}
    Path(args.out).write_text(json.dumps({"effort": args.effort, "frameworks": frameworks, "runs": rows}))
    failed = sum(1 for r in rows if "error" in r)
    print(f"{len(rows)} marks, {failed} failed -> {args.out}")
    return 0


def ratings(framework: dict[str, Any], payload: dict[str, Any]) -> dict[tuple[str, str], float | None]:
    """Each competency's rating as a fraction of the scale (best = 1), keyed (domain, competency)."""
    rating, field = framework.get("rating") or {"kind": "rag"}, framework.get("rating_field") or "score"
    scale = framework.get("scale") or []
    out: dict[tuple[str, str], float | None] = {}
    for competency in framework["competencies"]:
        domain = competency["domain_id"]
        local = competency["id"].removeprefix(f"{domain}.")
        value = ((payload.get(domain) or {}).get(local) or {}).get(field)
        if rating["kind"] == "boolean":
            out[(domain, local)] = None if value is None else float(bool(value))
        elif rating["kind"] == "range" and isinstance(value, (int, float)):
            lo, hi = float(rating["minimum"]), float(rating["maximum"])
            out[(domain, local)] = (float(value) - lo) / (hi - lo)
        elif value in scale and len(scale) > 1:
            out[(domain, local)] = 1 - scale.index(value) / (len(scale) - 1)
        else:
            out[(domain, local)] = None
    return out


def domain_means(marks: dict[tuple[str, str], float | None]) -> dict[str, float]:
    by_domain: dict[str, list[float]] = {}
    for (domain, _), value in marks.items():
        if value is not None:
            by_domain.setdefault(domain, []).append(value)
    return {d: statistics.fmean(v) for d, v in by_domain.items()}


def compare(framework: dict[str, Any], base: dict[str, Any], other: dict[str, Any]) -> tuple[float, float]:
    """(share of competencies rated identically, mean absolute per-domain difference) for one case."""
    a, b = ratings(framework, base), ratings(framework, other)
    same = [a[k] == b[k] for k in a if a[k] is not None or b[k] is not None]
    da, db = domain_means(a), domain_means(b)
    diffs = [abs(da[d] - db[d]) for d in da if d in db]
    return (statistics.fmean(same) if same else 1.0), (statistics.fmean(diffs) if diffs else 0.0)


def cmd_report(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.runs).read_text())
    frameworks, runs = data["frameworks"], data["runs"]
    by_arm: dict[str, dict[str, dict[str, Any]]] = {}
    for row in runs:
        by_arm.setdefault(row["arm"], {})[row["case"]] = row
    base = by_arm[args.baseline]
    print(f"effort={data['effort']} baseline={args.baseline}")
    print(f"{'arm':<18}{'fails':>6}{'agree':>8}{'dom|d|':>8}{'$/mark':>9}{'p50 s':>7}{'max s':>7}")
    for arm, cases in by_arm.items():
        fails = sum(1 for r in cases.values() if "error" in r)
        pairs = [compare(frameworks[c], base[c]["payload"], r["payload"])
                 for c, r in cases.items() if "payload" in r and "payload" in base.get(c, {})]
        dollars = [r["dollars"] for r in cases.values() if r.get("dollars") is not None and "payload" in r]
        seconds = [r["seconds"] for r in cases.values() if "payload" in r]
        agree = statistics.fmean(p[0] for p in pairs) if pairs else float("nan")
        diff = statistics.fmean(p[1] for p in pairs) if pairs else float("nan")
        price = f"{statistics.fmean(dollars):.4f}" if dollars else "n/a"
        p50 = f"{statistics.median(seconds):.0f}" if seconds else "-"
        top = f"{max(seconds):.0f}" if seconds else "-"
        print(f"{arm:<18}{fails:>6}{agree:>8.2f}{diff:>8.3f}{price:>9}{p50:>7}{top:>7}")
        for case, row in cases.items():
            if "error" in row:
                print(f"    {case}: {row['error'][:160]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="mark every case with every arm")
    run.add_argument("--cases", required=True)
    run.add_argument("--arms", required=True, help="comma-separated model ids; repeat one to measure its noise")
    run.add_argument("--effort", default="low", help="reasoning effort sent to every arm")
    run.add_argument("--parallel", type=int, default=6)
    run.add_argument("--out", required=True)
    report = sub.add_parser("report", help="compare each arm with a baseline arm")
    report.add_argument("runs")
    report.add_argument("--baseline", default="gpt-6-luna#1")
    args = parser.parse_args(argv)
    return cmd_run(args) if args.command == "run" else cmd_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
