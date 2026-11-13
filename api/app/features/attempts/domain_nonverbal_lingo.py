"""Which of an exam's own words the non-verbal cues are shown under. Pure: no I/O."""

from __future__ import annotations

from typing import Any

DEFAULT_LABEL = "Non-verbal communication"

_ATTENTION = ("responsive", "attentive", "engag", "relating", "interpersonal", "rapport", "communicat")
_LISTENING = ("responsive", "listen", "relating", "interpersonal", "communicat")
_RAPPORT = ("rapport", "empath", "relating", "interpersonal", "communicat")


def _first_match(items: list[dict[str, Any]], stems: tuple[str, ...]) -> dict[str, Any] | None:
    """The first item whose lower-cased label contains the earliest stem that any item matches."""
    for stem in stems:
        for item in items:
            if stem in str(item.get("label", "")).lower():
                return item
    return None


def _label(framework: dict[str, Any], stems: tuple[str, ...]) -> tuple[str, str | None]:
    """The label for one cue group and the domain id it came from (None when it fell to the default)."""
    competencies = list(framework.get("competencies") or [])
    domains = list(framework.get("domains") or [])
    hit = _first_match(competencies, stems)
    if hit is not None:
        return str(hit["label"]), hit.get("domain_id")
    hit = _first_match(domains, stems)
    if hit is not None:
        return str(hit["label"]), hit.get("id")
    return DEFAULT_LABEL, None


def lingo_for(framework: dict[str, Any] | None) -> dict[str, str]:
    """The four labels the web shows, taken from the attempt's frozen framework.

    Per cue group: the first competency matching a stem (stems in priority order), else the first
    domain matching one, else "Non-verbal communication". The heading is the domain label of the
    attention match.
    """
    framework = framework or {}
    attention, domain_id = _label(framework, _ATTENTION)
    heading = DEFAULT_LABEL
    if domain_id is not None:
        for domain in framework.get("domains") or []:
            if domain.get("id") == domain_id:
                heading = str(domain["label"])
    return {
        "heading": heading,
        "attention_label": attention,
        "listening_label": _label(framework, _LISTENING)[0],
        "rapport_label": _label(framework, _RAPPORT)[0],
    }
