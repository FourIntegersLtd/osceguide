"""Incremental coverage detection for a consultation that is still running.

This is not the evaluator. ``evaluator.py`` grades a finished transcript against
a framework's schema and produces the mark. This module answers a smaller,
cheaper question, repeatedly, while the consultation is still going: *which
assessed behaviours has the doctor demonstrated so far, and where?*

Three properties make it safe to put on a learner's screen mid-consultation:

* **Monotonic.** A competency only ever moves forward (absent -> partial ->
  covered) and is frozen once covered. Nothing a learner has earned is taken
  away, so the panel never flickers or appears to change its mind.
* **Grounded.** A competency is only recorded when the model returns a quote
  that is actually present in the doctor's own words. An ungrounded item is
  dropped rather than shown, because an invented quote on screen is worse than
  a missing tick.
* **Coverage, not grade.** The states are presence states. No RAG score is
  produced here; grading stays in ``evaluator.py``, which remains the single
  authority on the mark.

Only competencies in domains the framework marks ``live`` are considered.
Whole-consultation judgements — "avoids repetition", "structures the
consultation" — cannot be decided from a window of turns, so the rubric's
author leaves their domain un-live.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from typing import Any

from pydantic import Field

from ..contracts import EvaluationPolicy, FrameworkProvider, MessageRole, TranscriptMessage
from ..contracts._base import Frozen
from ..schemas.strict import inline_refs, to_strict_json_schema

logger = logging.getLogger(__name__)

ClientFactory = Callable[[], Any | None]

# How many recent turns the detector is shown by default.
DEFAULT_WINDOW_TURNS = 8

# Longer than this and it is a summary, not a quote.
MAX_QUOTE_WORDS = 40


class CoverageState(str, Enum):
    """How far a competency has got. Absence is the implicit third state."""

    PARTIAL = "partial"
    COVERED = "covered"


_ORDER = {CoverageState.PARTIAL: 1, CoverageState.COVERED: 2}


class CoverageItem(Frozen):
    """One competency the doctor has demonstrated, and the words that did it."""

    competency_id: str = Field(min_length=1)
    state: CoverageState
    quote: str = Field(min_length=1)
    seq: int = Field(ge=0)


class CoverageSnapshot(Frozen):
    """Everything demonstrated so far in one attempt."""

    framework_id: str = Field(min_length=1)
    items: tuple[CoverageItem, ...] = ()
    last_seq: int = -1

    @property
    def by_id(self) -> dict[str, CoverageItem]:
        return {item.competency_id: item for item in self.items}

    def covered_ids(self) -> frozenset[str]:
        return frozenset(i.competency_id for i in self.items if i.state is CoverageState.COVERED)


class LiveCoverageError(RuntimeError):
    """No provider produced a usable answer for this pass."""


def live_competency_ids(framework: Any, domains: Sequence[str] | None = None) -> tuple[str, ...]:
    """Competency ids the detector may report, in framework order.

    Which domains those are is the framework's own business: a domain marks
    itself `live` when its competencies can be decided from a window of turns.
    This was a pair of literal domain ids, which meant a rubric that did not
    happen to call its domains `tasks` and `relating_to_others` got no live
    coverage at all.
    """
    wanted = set(domains) if domains is not None else set(framework.live_domain_ids)
    return tuple(c.id for c in framework.competencies if c.domain_id in wanted)


def recent_window(messages: Sequence[TranscriptMessage], *, turns: int = DEFAULT_WINDOW_TURNS) -> tuple[TranscriptMessage, ...]:
    """The last ``turns`` messages, oldest first."""
    if turns <= 0:
        return ()
    return tuple(messages[-turns:])


def render_window(messages: Iterable[TranscriptMessage]) -> str:
    """The excerpt the detector reads, labelled the way the marker labels it."""
    labels = {MessageRole.USER: "DOCTOR", MessageRole.ASSISTANT: "PATIENT"}
    blocks = []
    for message in messages:
        text = message.message.strip()
        if not text:
            continue
        label = labels[message.role]
        blocks.append(f"<{label}>\n{text}\n</{label}>")
    return "\n\n".join(blocks)


SYSTEM_PROMPT = """<role>
You are watching a clinical consultation as it happens and noting which assessed behaviours the doctor has demonstrated so far.
</role>

<task>
You are given the behaviours that have NOT yet been demonstrated, and the most recent exchanges of a consultation that is still going on. Decide which of those behaviours the doctor has demonstrated in this excerpt.
</task>

<rules>
- Judge only the excerpt you are given. Earlier parts of the consultation have already been assessed; do not try to account for them.
- Only the DOCTOR's words count. Never credit a behaviour because of something the PATIENT said.
- Record a behaviour only once the doctor has actually done it, not when they appear to be about to.
- "covered" means done properly. "partial" means begun or done incompletely - for example asking about the patient's ideas but not their concerns or expectations.
- `quote` must be copied VERBATIM from a DOCTOR line in the excerpt. Do not paraphrase it, do not tidy up the grammar, and do not quote the patient. Keep it short - a sentence, not a speech.
- If nothing new was demonstrated, return an empty list. That is the correct and most common answer.
- Do not judge how well anything was done. You are recording what happened, not grading it. There is no score here.
</rules>"""


def _result_schema(open_ids: Sequence[str]) -> dict[str, Any]:
    """Output shape, constrained to the competencies still open this pass."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["newly_demonstrated"],
        "properties": {
            "newly_demonstrated": {
                "type": "array",
                "description": "Behaviours the doctor demonstrated in this excerpt. Empty if none.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["competency_id", "state", "quote"],
                    "properties": {
                        "competency_id": {"type": "string", "enum": list(open_ids)},
                        "state": {"type": "string", "enum": [s.value for s in CoverageState]},
                        "quote": {
                            "type": "string",
                            "description": "The doctor's own words, copied verbatim from the excerpt.",
                        },
                    },
                },
            }
        },
    }


_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _SPACE.sub(" ", _PUNCT.sub("", text.lower())).strip()


def _doctor_text(messages: Iterable[TranscriptMessage]) -> str:
    return _normalise(" ".join(m.message for m in messages if m.role is MessageRole.USER))


def _is_grounded(quote: str, doctor_text: str) -> bool:
    """True when the quote is really in the doctor's words."""
    normalised = _normalise(quote)
    return bool(normalised) and normalised in doctor_text


class LiveCoverageDetector:
    """Detects newly demonstrated competencies from a window of recent turns."""

    def __init__(
        self,
        *,
        framework_provider: FrameworkProvider,
        primary_client: ClientFactory,
        fallback_client: ClientFactory | None = None,
        domains: Sequence[str] | None = None,
        require_grounded_quotes: bool = True,
    ) -> None:
        self._frameworks = framework_provider
        self._primary = primary_client
        self._fallback = fallback_client
        # None means "whichever domains the framework declares live".
        self._domains = tuple(domains) if domains is not None else None
        self._require_grounded = require_grounded_quotes

    def detect(
        self,
        *,
        snapshot: CoverageSnapshot,
        messages: Sequence[TranscriptMessage],
        policy: EvaluationPolicy,
        window_turns: int = DEFAULT_WINDOW_TURNS,
    ) -> CoverageSnapshot:
        """A new snapshot including anything demonstrated in the latest turns.

        Returns the snapshot unchanged when there is nothing to look at, when
        every live competency is already covered, or when no provider answers.
        A failed pass is never fatal: the consultation carries on and the next
        turn tries again.
        """
        framework = self._frameworks.get(snapshot.framework_id)
        window = recent_window(messages, turns=window_turns)
        if not any(m.role is MessageRole.USER for m in window):
            return snapshot  # nothing the doctor said; nothing can be earned

        open_ids = self._open_ids(framework, snapshot)
        if not open_ids:
            return snapshot

        payload = self._ask(framework, open_ids, window, policy)
        if payload is None:
            return snapshot

        return self._merge(snapshot, payload, window)

    # -- internals -----------------------------------------------------------

    def _open_ids(self, framework: Any, snapshot: CoverageSnapshot) -> tuple[str, ...]:
        covered = snapshot.covered_ids()
        return tuple(i for i in live_competency_ids(framework, self._domains) if i not in covered)

    def _user_prompt(self, framework: Any, open_ids: Sequence[str], window: Sequence[TranscriptMessage]) -> str:
        labels = {c.id: c.label for c in framework.competencies}
        listed = "\n".join(f"- {cid}: {labels.get(cid, cid)}" for cid in open_ids)
        return (
            "<not_yet_demonstrated>\n"
            f"{listed}\n"
            "</not_yet_demonstrated>\n\n"
            "<excerpt>\n"
            f"{render_window(window)}\n"
            "</excerpt>"
        )

    def _ask(
        self,
        framework: Any,
        open_ids: Sequence[str],
        window: Sequence[TranscriptMessage],
        policy: EvaluationPolicy,
    ) -> dict[str, Any] | None:
        system = policy.system_prompt_override or SYSTEM_PROMPT
        user = self._user_prompt(framework, open_ids, window)
        schema = _result_schema(open_ids)
        name = "live_coverage"

        primary = self._primary()
        if primary is not None:
            try:
                return self._call_primary(primary, policy, schema, name, system, user)
            except Exception as exc:  # noqa: BLE001 — a missed pass is not fatal
                logger.warning("live coverage primary %s failed: %s", policy.primary_model, exc)

        if policy.fallback_model and self._fallback is not None:
            fallback = self._fallback()
            if fallback is not None:
                try:
                    return self._call_fallback(fallback, policy, schema, name, system, user)
                except Exception as exc:  # noqa: BLE001 — logged; the next turn retries
                    logger.warning("live coverage fallback %s failed: %s", policy.fallback_model, exc)
        return None

    @staticmethod
    def _call_primary(client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": policy.primary_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": to_strict_json_schema(schema), "strict": True},
            },
            "timeout": policy.timeout_s,
        }
        if policy.primary_reasoning_effort is not None:
            kwargs["reasoning_effort"] = policy.primary_reasoning_effort
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        if getattr(message, "refusal", None):
            raise LiveCoverageError(f"refused: {message.refusal}")
        content = getattr(message, "content", None)
        if not content:
            raise LiveCoverageError("empty response")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise LiveCoverageError("structured output was not an object")
        return parsed

    @staticmethod
    def _call_fallback(client: Any, policy: EvaluationPolicy, schema: dict[str, Any], name: str, system: str, user: str) -> dict[str, Any]:
        response = client.messages.create(
            model=policy.fallback_model,
            max_tokens=policy.fallback_max_tokens,
            temperature=policy.fallback_temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": name, "description": "Record newly demonstrated behaviours.", "input_schema": inline_refs(schema)}],
            tool_choice={"type": "tool", "name": name},
        )
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                value = getattr(block, "input", None)
                if not isinstance(value, dict):
                    raise LiveCoverageError("tool input was not an object")
                return value
        raise LiveCoverageError("no tool_use block in response")

    def _merge(
        self,
        snapshot: CoverageSnapshot,
        payload: dict[str, Any],
        window: Sequence[TranscriptMessage],
    ) -> CoverageSnapshot:
        """Fold reported items into the snapshot, forwards only and grounded only."""
        framework = self._frameworks.get(snapshot.framework_id)
        allowed = set(live_competency_ids(framework, self._domains))
        current = snapshot.by_id
        doctor_text = _doctor_text(window)
        last_seq = max((m.seq for m in window), default=snapshot.last_seq)
        changed = False

        for raw in payload.get("newly_demonstrated") or []:
            if not isinstance(raw, dict):
                continue
            competency_id = str(raw.get("competency_id") or "")
            quote = str(raw.get("quote") or "").strip()
            try:
                state = CoverageState(str(raw.get("state") or ""))
            except ValueError:
                logger.warning("live coverage: unknown state %r for %s", raw.get("state"), competency_id)
                continue

            if competency_id not in allowed:
                logger.warning("live coverage: %r is not a live competency; dropped", competency_id)
                continue
            if not quote:
                continue
            if len(quote.split()) > MAX_QUOTE_WORDS:
                logger.warning("live coverage: quote for %s is a summary, not a quote; dropped", competency_id)
                continue
            if self._require_grounded and not _is_grounded(quote, doctor_text):
                logger.warning("live coverage: quote for %s is not in the doctor's words; dropped", competency_id)
                continue

            existing = current.get(competency_id)
            if existing is not None and _ORDER[state] <= _ORDER[existing.state]:
                continue  # never move backwards, never churn an equal state

            seq = _earning_seq(quote, window, default=last_seq)
            current[competency_id] = CoverageItem(
                competency_id=competency_id, state=state, quote=quote, seq=seq
            )
            changed = True

        if not changed and last_seq <= snapshot.last_seq:
            return snapshot

        ordered = tuple(sorted(current.values(), key=lambda i: (i.seq, i.competency_id)))
        return CoverageSnapshot(framework_id=snapshot.framework_id, items=ordered, last_seq=last_seq)


def _earning_seq(quote: str, window: Sequence[TranscriptMessage], *, default: int) -> int:
    """The seq of the doctor turn the quote came from, so the feed can order itself."""
    normalised = _normalise(quote)
    for message in window:
        if message.role is MessageRole.USER and normalised and normalised in _normalise(message.message):
            return message.seq
    return default
