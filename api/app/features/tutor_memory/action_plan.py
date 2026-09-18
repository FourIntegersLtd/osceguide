"""What was agreed after a debrief, and whether it has been done.

Its own module because an action plan is a small idea with two rules that
have to agree — a step ticked off here must stop appearing in the brief — and
because `domain.py` had grown past the file cap. Pure: the plan is a list the
caller read and will write back.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def mark_action_item_done(plan: Sequence[Any], step: str) -> tuple[list[Any], str | None]:
    """Tick off the step this sentence names. Returns the new plan and what matched.

    Matching is deliberately forgiving. The tutor asks its question aloud and
    the doctor answers in their own words, so the model passes back a
    paraphrase — "the safety netting one", not the sentence as written. Exact
    equality would tick off nothing, which is the state this is fixing.

    So: case-insensitive, and a containment match either way round, taking the
    first open item that matches. When nothing matches, the plan comes back
    untouched and the caller says so rather than guessing — ticking off the
    wrong step is worse than ticking off none, because the doctor is then
    asked about the thing they did and never asked about the thing they did
    not.
    """
    wanted = " ".join(step.split()).casefold()
    if not wanted:
        return list(plan), None
    updated: list[Any] = []
    matched: str | None = None
    for item in plan:
        text = item.get("text") if isinstance(item, Mapping) else item
        label = " ".join(str(text or "").split())
        already_done = bool(item.get("done")) if isinstance(item, Mapping) else False
        candidate = label.casefold()
        if (
            matched is None
            and not already_done
            and candidate
            and (candidate == wanted or wanted in candidate or candidate in wanted)
        ):
            matched = label
            updated.append({"text": label, "done": True})
            continue
        updated.append({"text": label, "done": already_done} if label else item)
    return updated, matched


def open_action_items(plans: Sequence[Any]) -> list[str]:
    """Steps that were agreed and not yet ticked off, most recent first.

    Accepts both shapes the summariser produces: `{"text": ..., "done": ...}`
    and a bare string, which is what the model returns when it ignores the
    schema's optional flag.
    """
    out: list[str] = []
    for plan in plans:
        items = plan if isinstance(plan, Sequence) and not isinstance(plan, str) else []
        for item in items:
            if isinstance(item, Mapping):
                if item.get("done"):
                    continue
                text = str(item.get("text") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                out.append(text)
    return out
