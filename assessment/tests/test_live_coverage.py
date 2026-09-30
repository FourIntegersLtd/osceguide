"""Live coverage detection: monotonic, grounded, and never a grade."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from osce_assessment.contracts import (
    Competency,
    CompetencyDomain,
    CompetencyFramework,
    EvaluationPolicy,
    MessageRole,
    TranscriptMessage,
)
from osce_assessment.evaluation.live_coverage import (
    CoverageItem,
    CoverageSnapshot,
    CoverageState,
    LiveCoverageDetector,
    live_competency_ids,
    recent_window,
)
from osce_assessment.testing import StaticFrameworkProvider

FIXED = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def _competency(cid: str, domain: str) -> Competency:
    return Competency(id=cid, label=cid.replace("_", " "), domain_id=domain)


# A rubric of the shape live coverage exists for: two domains whose competencies
# can be judged from a window of turns, and one whose competencies cannot. Which
# is which is the framework's own declaration, not a list in the engine.
FRAMEWORK = CompetencyFramework(
    id="live-rubric-v1",
    label="Live rubric",
    domains=(
        CompetencyDomain(id="global_skills", label="Global skills", live=False),
        CompetencyDomain(id="tasks", label="Tasks", live=True),
        CompetencyDomain(id="relating_to_others", label="Relating to others", live=True),
    ),
    competencies=(
        _competency("structures_consultation", "global_skills"),
        _competency("avoids_repetition", "global_skills"),
        _competency("discovers_ice", "tasks"),
        _competency("provides_safety_net", "tasks"),
        _competency("opens_consultation", "relating_to_others"),
        _competency("identifies_cues", "relating_to_others"),
    ),
    system_prompt="Mark the consultation.",
)
FRAMEWORKS = StaticFrameworkProvider(FRAMEWORK)
SCA = FRAMEWORK.id

# What the doctor actually says in the window the tests use.
ASKED_CONCERN = "what has been worrying you about it"
OPENED = "hello I am doctor Chen, can I check your name and date of birth"


def msg(role: MessageRole, text: str, seq: int) -> TranscriptMessage:
    return TranscriptMessage(role=role, message=text, timestamp=FIXED, message_id=f"m{seq}", seq=seq)


def window() -> tuple[TranscriptMessage, ...]:
    return (
        msg(MessageRole.ASSISTANT, "I've had this pain for a fortnight.", 0),
        msg(MessageRole.USER, OPENED, 1),
        msg(MessageRole.USER, ASKED_CONCERN, 2),
        msg(MessageRole.ASSISTANT, "I'm frightened it might be my heart.", 3),
    )


def policy(**overrides) -> EvaluationPolicy:
    base = dict(framework_id=SCA, primary_model="fast-model", fallback_model="fallback-model", version="live-1")
    base.update(overrides)
    return EvaluationPolicy(**base)


def snapshot(*items: CoverageItem) -> CoverageSnapshot:
    return CoverageSnapshot(framework_id=SCA, items=items, last_seq=-1)


class FakePrimary:
    """The slice of an OpenAI-style client the detector touches."""

    def __init__(self, *, payload=None, error=None) -> None:
        self.calls: list[dict] = []
        self._payload, self._error = payload, error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        message = SimpleNamespace(content=json.dumps(self._payload), refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeFallback:
    """The slice of an Anthropic-style client the detector touches."""

    def __init__(self, *, payload=None) -> None:
        self.calls: list[dict] = []
        self._payload = payload
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=self._payload)])


def detector(primary=None, fallback=None, **kwargs) -> LiveCoverageDetector:
    return LiveCoverageDetector(
        framework_provider=FRAMEWORKS,
        primary_client=lambda: primary,
        fallback_client=lambda: fallback,
        **kwargs,
    )


def reported(*items: dict) -> dict:
    return {"newly_demonstrated": list(items)}


# --- which competencies are even eligible ---------------------------------------


def test_only_competencies_in_live_domains_are_eligible() -> None:
    """Which domains those are is the rubric author's call, not a constant here."""
    ids = set(live_competency_ids(FRAMEWORK))

    assert "discovers_ice" in ids and "provides_safety_net" in ids
    # Whole-consultation judgements cannot be decided from a window of turns.
    assert "avoids_repetition" not in ids
    assert "structures_consultation" not in ids
    assert FRAMEWORK.live_domain_ids == ("tasks", "relating_to_others")


def test_the_model_is_only_offered_competencies_that_are_still_open() -> None:
    primary = FakePrimary(payload=reported())
    already = CoverageItem(competency_id="discovers_ice", state=CoverageState.COVERED, quote="q", seq=0)

    detector(primary).detect(snapshot=snapshot(already), messages=window(), policy=policy())

    schema = primary.calls[0]["response_format"]["json_schema"]["schema"]
    offered = schema["properties"]["newly_demonstrated"]["items"]["properties"]["competency_id"]["enum"]
    assert "discovers_ice" not in offered
    assert "provides_safety_net" in offered


def test_no_provider_call_when_the_doctor_has_not_spoken() -> None:
    primary = FakePrimary(payload=reported())
    only_patient = (msg(MessageRole.ASSISTANT, "It still hurts.", 0),)

    result = detector(primary).detect(snapshot=snapshot(), messages=only_patient, policy=policy())

    assert primary.calls == []
    assert result.items == ()


# --- grounding ------------------------------------------------------------------


def test_a_competency_is_recorded_with_the_doctors_own_words() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "discovers_ice", "state": "partial", "quote": ASKED_CONCERN}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    item = result.by_id["discovers_ice"]
    assert item.state is CoverageState.PARTIAL
    assert item.quote == ASKED_CONCERN
    assert item.seq == 2  # the doctor turn it came from, so the feed can order itself


def test_an_invented_quote_is_dropped_rather_than_shown() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "provides_safety_net", "state": "covered", "quote": "come back if you get chest pain"}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_the_patients_words_never_earn_the_doctor_a_competency() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "identifies_cues", "state": "covered", "quote": "I'm frightened it might be my heart"}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_a_summary_dressed_up_as_a_quote_is_dropped() -> None:
    essay = " ".join(["word"] * 60)
    primary = FakePrimary(payload=reported(
        {"competency_id": "opens_consultation", "state": "covered", "quote": essay}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_grounding_can_be_relaxed_deliberately() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "provides_safety_net", "state": "covered", "quote": "not in the window"}
    ))

    result = detector(primary, require_grounded_quotes=False).detect(
        snapshot=snapshot(), messages=window(), policy=policy()
    )

    assert "provides_safety_net" in result.by_id


# --- monotonicity ---------------------------------------------------------------


def test_partial_is_upgraded_to_covered() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "discovers_ice", "state": "covered", "quote": ASKED_CONCERN}
    ))
    earlier = CoverageItem(competency_id="discovers_ice", state=CoverageState.PARTIAL, quote="older", seq=0)

    result = detector(primary).detect(snapshot=snapshot(earlier), messages=window(), policy=policy())

    assert result.by_id["discovers_ice"].state is CoverageState.COVERED


def test_a_covered_competency_is_never_taken_away() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "opens_consultation", "state": "partial", "quote": OPENED}
    ))
    done = CoverageItem(competency_id="opens_consultation", state=CoverageState.COVERED, quote=OPENED, seq=1)

    result = detector(primary).detect(snapshot=snapshot(done), messages=window(), policy=policy())

    assert result.by_id["opens_consultation"].state is CoverageState.COVERED


def test_an_unchanged_partial_does_not_churn_its_quote() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "discovers_ice", "state": "partial", "quote": ASKED_CONCERN}
    ))
    earlier = CoverageItem(competency_id="discovers_ice", state=CoverageState.PARTIAL, quote="the first one", seq=0)

    result = detector(primary).detect(snapshot=snapshot(earlier), messages=window(), policy=policy())

    assert result.by_id["discovers_ice"].quote == "the first one"


# --- robustness -----------------------------------------------------------------


def test_a_competency_outside_the_framework_is_ignored() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "not_a_competency", "state": "covered", "quote": OPENED}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_a_global_skill_is_refused_even_if_the_model_reports_one() -> None:
    primary = FakePrimary(payload=reported(
        {"competency_id": "avoids_repetition", "state": "covered", "quote": OPENED}
    ))

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_a_failed_pass_leaves_the_snapshot_alone_so_the_consultation_carries_on() -> None:
    primary = FakePrimary(error=RuntimeError("upstream down"))
    earlier = CoverageItem(competency_id="discovers_ice", state=CoverageState.PARTIAL, quote="q", seq=0)

    result = detector(primary, fallback=None).detect(
        snapshot=snapshot(earlier), messages=window(), policy=policy()
    )

    assert result.by_id["discovers_ice"].state is CoverageState.PARTIAL


def test_the_fallback_answers_when_the_primary_fails() -> None:
    primary = FakePrimary(error=RuntimeError("upstream down"))
    fallback = FakeFallback(payload=reported(
        {"competency_id": "opens_consultation", "state": "covered", "quote": OPENED}
    ))

    result = detector(primary, fallback).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.by_id["opens_consultation"].state is CoverageState.COVERED
    assert fallback.calls


def test_nothing_new_is_the_ordinary_answer() -> None:
    primary = FakePrimary(payload=reported())

    result = detector(primary).detect(snapshot=snapshot(), messages=window(), policy=policy())

    assert result.items == ()


def test_detection_stops_once_every_live_competency_is_covered() -> None:
    primary = FakePrimary(payload=reported())
    everything = tuple(
        CoverageItem(competency_id=cid, state=CoverageState.COVERED, quote="q", seq=0)
        for cid in live_competency_ids(FRAMEWORK)
    )

    detector(primary).detect(snapshot=snapshot(*everything), messages=window(), policy=policy())

    assert primary.calls == []


# --- windowing ------------------------------------------------------------------


def test_the_window_is_the_most_recent_turns() -> None:
    messages = tuple(msg(MessageRole.USER, f"turn {i}", i) for i in range(10))

    assert [m.seq for m in recent_window(messages, turns=3)] == [7, 8, 9]
    assert recent_window(messages, turns=0) == ()


# --- what this is not -----------------------------------------------------------


def test_coverage_states_carry_no_rag_grade() -> None:
    # Red is a judgement about quality, which only the end-of-consultation
    # evaluator makes. Nothing here can put one on a learner's screen.
    assert {s.value for s in CoverageState} == {"partial", "covered"}
