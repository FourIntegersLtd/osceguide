"""What a marked result adds up to, in the rubric's own units.

Every number a screen or a report shows about a mark comes from here: a
rating as a fraction of the best one, a domain's value, the station total,
whether it passed, how many critical concerns it raised, and how several
reviewers' ratings combine into one. Nothing here knows an exam: the rubric
(`RubricStructure`) says how a competency is rated and the resolved display
(`domain.resolved_display`) says how the numbers are aggregated and judged.

The aggregates (plan §4):

- `ragCounts`: how many of each scale value a domain holds (`rating_counts`);
  as one number, the share of the best value, out of 100.
- `ragShare`: the share of competencies on the best value, out of 100.
- `sum`: the ratings added up (a boolean counts 1 when met; a scale value
  counts its fraction).
- `mean`: the ratings' average, in the rating's units.
- `percentAchieved`: the mean fraction of the best rating, out of 100.

A nullable domain the result left null is not in the result at all, so it is
left out of every aggregate and of `requireEveryDomain`.

Pure: no session, no models, no I/O.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from app.features.rubrics.domain import scoring_domain_ids
from app.features.rubrics.structure import FieldSpec, RatingSpec, RubricStructure

__all__ = [
    # Re-exported so other slices can type and scope their arguments through this public module.
    "RubricStructure",
    "scoring_domain_ids",
    "rating_percent",
    "InvalidRating",
    "RatingValue",
    "combine_reviewers",
    "critical_count",
    "domain_fraction",
    "domain_value",
    "normalise_rating",
    "passed",
    "rating_counts",
    "rating_fraction",
    "rating_tone",
    "ratings_from_paths",
    "ratings_in",
    "result_totals",
    "tone_for_fraction",
    "total_fraction",
    "total_value",
    "texts_by_role",
    "weakest_domain_tones",
    "worst_rating",
]

# A rating in its native units: a scale word ("G"), a number (7, 0.75) or a yes/no.
RatingValue = str | float | int | bool

# Whole domains' ratings: domain id -> the competency ratings the result holds in it.
DomainRatings = Mapping[str, Sequence[RatingValue]]

# Floating point sums (0.1 + 0.2) must not fail a pass line they meet exactly.
_PASS_TOLERANCE = 1e-9


class InvalidRating(ValueError):
    """A value that is not a rating this rubric allows. Reviews map this to 422."""


# --- One rating -------------------------------------------------------------------


def is_valid_rating(rating: RatingSpec, value: Any) -> bool:
    """Whether `value` is a rating of this kind, exactly as a marker would store it."""
    if rating.is_enumerated:
        return isinstance(value, str) and value in rating.scale
    if rating.kind == "boolean":
        return isinstance(value, bool)
    # A range: a real number (never a bool, which Python counts as 1) within bounds.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if rating.step == "integer" and value != int(value):
        return False
    minimum = rating.minimum if rating.minimum is not None else -math.inf
    maximum = rating.maximum if rating.maximum is not None else math.inf
    return bool(minimum <= value <= maximum)


def normalise_rating(structure: RubricStructure, raw: Any) -> RatingValue:
    """A rating typed by a person, as the rubric stores it, or `InvalidRating`.

    Forgiving about how it was typed and strict about what it is: " g " is a
    `G` on an R/A/G scale, "7" is 7 on a 0..10 range, "true" is a met boolean.
    """
    rating = structure.rating
    if rating.is_enumerated and isinstance(raw, str):
        # A scale word is matched without regard to case or spacing.
        wanted = raw.strip().casefold()
        for scale_value in rating.scale:
            if scale_value.casefold() == wanted:
                return scale_value
    elif rating.kind == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
            return raw.strip().lower() == "true"
    elif rating.kind == "range":
        number = _as_number(raw)
        if number is not None and is_valid_rating(rating, number):
            return int(number) if rating.step == "integer" else number
    raise InvalidRating(f"{raw!r} is not a rating on this rubric; it must be {_describe(rating)}.")


def rating_fraction(structure: RubricStructure, value: Any) -> float | None:
    """One rating as a fraction of the best one (0..1), or None if it is not a rating.

    - A scale value by its position, best first, in whole percent: with G, A,
      R that is 1, 0.66 and 0.33, which is the 100/66/33 an institution has
      always ranked on (an amber sits nearer a green than a red does to it).
    - A range as the value over the maximum (7 of 10 is 0.7), the same
      fraction the display's tones are written against.
    - A boolean as 1 or 0.
    """
    rating = structure.rating
    if not is_valid_rating(rating, value):
        return None
    if rating.is_enumerated:
        count = len(rating.scale)
        position_from_worst = count - rating.scale.index(value)
        return math.floor(100 * position_from_worst / count) / 100
    if rating.kind == "boolean":
        return 1.0 if value else 0.0
    maximum = rating.maximum or 1
    return float(value) / maximum


def rating_percent(structure: RubricStructure, value: Any) -> float | None:
    """One rating as 0-100 of the best one (G 100, A 66, R 33), or None if it is not a rating."""
    fraction = rating_fraction(structure, value)
    # Rounded so 0.66 reads as 66.0 rather than 66.00000000000001.
    return None if fraction is None else round(fraction * 100, 6)


def rating_tone(structure: RubricStructure, display: Mapping[str, Any], value: Any) -> str | None:
    """The tone (good, fair, poor...) the display gives one rating, or None if it is not a rating.

    A tone that names a scale `value` matches that value; the rest are read
    highest `atLeast` first against the rating's fraction.
    """
    fraction = rating_fraction(structure, value)
    if fraction is None:
        return None
    tones = [tone for tone in display.get("tones") or [] if isinstance(tone, Mapping)]
    for tone in tones:
        if "value" in tone and tone["value"] == value:
            return str(tone["tone"])
    for tone in sorted(tones, key=lambda entry: float(entry.get("atLeast") or 0), reverse=True):
        if "value" not in tone and fraction + _PASS_TOLERANCE >= float(tone.get("atLeast") or 0):
            return str(tone["tone"])
    return None


# --- Reading ratings out of a result or a review -----------------------------------


def ratings_in(structure: RubricStructure, result: Mapping[str, Any]) -> dict[str, list[RatingValue]]:
    """Every competency rating a marked result holds, grouped by domain, in rubric order.

    A domain the result left null (or never answered) is absent, not empty: a
    nullable domain that does not apply takes no part in any aggregate. A
    rating that is not valid for the rubric is skipped rather than guessed at.
    """
    rating_field = structure.rating.field
    by_domain: dict[str, list[RatingValue]] = {}
    for domain in structure.domains:
        domain_answer = result.get(domain.id)
        if not isinstance(domain_answer, Mapping):
            continue
        domain_ratings: list[RatingValue] = []
        for competency in domain.competencies:
            competency_answer = domain_answer.get(competency.id)
            if not isinstance(competency_answer, Mapping):
                continue
            value = competency_answer.get(rating_field)
            if is_valid_rating(structure.rating, value):
                domain_ratings.append(cast(RatingValue, value))
        by_domain[domain.id] = domain_ratings
    return by_domain


def rating_path_parts(structure: RubricStructure, path: str) -> list[str] | None:
    """The segments of a review path before its rating field, or None if it is not a rating path.

    A review stores `domain.competency.<rating field>` for a competency and
    `domain.<rating field>` for a whole domain (`tasks.safety_net.score`,
    `tasks.score`; `competent` in place of `score` on a boolean rubric).
    """
    suffix = f".{structure.rating.field}"
    if not isinstance(path, str) or not path.endswith(suffix):
        return None
    stem = path[: -len(suffix)].strip()
    return [part for part in stem.split(".") if part] or None


def ratings_from_paths(
    structure: RubricStructure, field_values: Mapping[str, Any]
) -> dict[str, list[RatingValue]]:
    """A review's ratings grouped by domain (competency and domain-level paths alike)."""
    by_domain: dict[str, list[RatingValue]] = {}
    for path, value in field_values.items():
        parts = rating_path_parts(structure, path)
        if parts is None or not is_valid_rating(structure.rating, value):
            continue
        by_domain.setdefault(parts[0], []).append(value)
    return by_domain


# --- Combining ------------------------------------------------------------------


def combine_reviewers(structure: RubricStructure, values: Sequence[Any]) -> RatingValue | None:
    """Several ratings of one thing as one, or None when none of them is a rating.

    - A scale: the most common value; a tie goes to the worse value, because a
      split is the one worth a conversation. Three greens and a red is a green
      domain with a red skill in it, not an amber that describes neither.
    - A range: the mean.
    - A boolean: the majority; a tie is not met.
    """
    rating = structure.rating
    valid_values = [value for value in values if is_valid_rating(rating, value)]
    if not valid_values:
        return None
    if rating.is_enumerated:
        counts = Counter(valid_values)
        most_common_count = max(counts.values())
        tied_values = [value for value in rating.scale if counts.get(value) == most_common_count]
        # The scale is best first, so the last tied value is the worst.
        return tied_values[-1]
    if rating.kind == "boolean":
        met_count = sum(1 for value in valid_values if value is True)
        return met_count > len(valid_values) - met_count
    return sum(float(value) for value in valid_values) / len(valid_values)


def worst_rating(structure: RubricStructure, values: Sequence[Any]) -> RatingValue | None:
    """The worst of several ratings, or None when none of them is a rating.

    For a headline across different things (a station's domains, a
    candidate's stations), where one weak part is what a reader must see:
    the last scale value present, the lowest number, or not met if any is not.
    Reviewers rating the *same* thing combine by `combine_reviewers` instead.
    """
    rating = structure.rating
    valid_values = [value for value in values if is_valid_rating(rating, value)]
    if not valid_values:
        return None
    if rating.is_enumerated:
        # The scale is best first, so the worst present value has the highest index.
        return cast(RatingValue, max(valid_values, key=lambda value: rating.scale.index(value)))
    if rating.kind == "boolean":
        return all(value is True for value in valid_values)
    return min(float(value) for value in valid_values)


def rating_counts(structure: RubricStructure, ratings: Sequence[Any]) -> dict[str, int]:
    """How many of each scale value a set of ratings holds, best first; empty for a non-scale rating."""
    if not structure.rating.is_enumerated:
        return {}
    counts = Counter(value for value in ratings if is_valid_rating(structure.rating, value))
    return {scale_value: counts.get(scale_value, 0) for scale_value in structure.rating.scale}


def _aggregate(structure: RubricStructure, aggregate: str, ratings: Sequence[Any]) -> float | None:
    """A set of ratings under one aggregate (see the module docstring), or None if there are none."""
    rating = structure.rating
    valid_ratings = [value for value in ratings if is_valid_rating(rating, value)]
    if not valid_ratings:
        return None
    fractions = [rating_fraction(structure, value) or 0.0 for value in valid_ratings]
    if aggregate in ("ragCounts", "ragShare"):
        best_count = sum(1 for fraction in fractions if fraction >= 1)
        return 100 * best_count / len(valid_ratings)
    if aggregate == "percentAchieved":
        return 100 * sum(fractions) / len(fractions)
    # `sum` and `mean` work in the rating's own units where it has them.
    units = [
        float(value) if rating.kind == "range" else fraction
        for value, fraction in zip(valid_ratings, fractions, strict=True)
    ]
    if aggregate == "mean":
        return sum(units) / len(units)
    return sum(units)


def domain_value(
    structure: RubricStructure, display: Mapping[str, Any], ratings: Sequence[Any]
) -> float | None:
    """One domain's value under the display's domain aggregate, or None when it holds no rating."""
    return _aggregate(structure, str(display["domain"]["aggregate"]), ratings)


def total_value(
    structure: RubricStructure, display: Mapping[str, Any], ratings_by_domain: DomainRatings
) -> float | None:
    """The station total under the display's total aggregate, across every answered domain."""
    every_rating = [value for domain_ratings in ratings_by_domain.values() for value in domain_ratings]
    return _aggregate(structure, str(display["total"]["aggregate"]), every_rating)


def total_fraction(display: Mapping[str, Any], total: float | None) -> float | None:
    """A station total as a fraction (0..1) of the most it could be, for ranking and trends.

    Comparable across rubric versions and exams: a total of 38 out of 50 and
    one of 76% are both about three quarters. A `ragShare` total has no
    maximum of its own; it is already out of 100.
    """
    if total is None:
        return None
    maximum = display["total"].get("max")
    if maximum is None:
        maximum = 100
    return float(total) / float(maximum) if maximum else None


def domain_fraction(display: Mapping[str, Any], value: float | None) -> float | None:
    """A domain's value as a fraction (0..1) of the most it could be; see `total_fraction`."""
    if value is None:
        return None
    maximum = display["domain"].get("max")
    if maximum is None:
        maximum = 100
    return float(value) / float(maximum) if maximum else None


def tone_for_fraction(display: Mapping[str, Any], fraction: float | None) -> str | None:
    """The display tone a fraction of the maximum falls in, or None for no fraction or no tones."""
    if fraction is None:
        return None
    tones = [tone for tone in display.get("tones") or [] if isinstance(tone, Mapping)]
    for tone in sorted(tones, key=lambda entry: float(entry.get("atLeast") or 0), reverse=True):
        if fraction + _PASS_TOLERANCE >= float(tone.get("atLeast") or 0):
            return str(tone["tone"])
    return None


def passed(
    structure: RubricStructure, display: Mapping[str, Any], ratings_by_domain: DomainRatings
) -> bool | None:
    """Whether a result passes, or None when the rubric sets no pass line or nothing is rated.

    Pass means the total is at or above `total.passAtLeast`; with
    `requireEveryDomain`, every answered domain must also be at or above
    `domain.passAtLeast` (PLAB 2 fails a station with one weak domain however
    high the total).
    """
    total_pass_line = display["total"].get("passAtLeast")
    total = total_value(structure, display, ratings_by_domain)
    if total_pass_line is None or total is None:
        return None
    if total + _PASS_TOLERANCE < float(total_pass_line):
        return False
    domain_pass_line = display["domain"].get("passAtLeast")
    if display["total"].get("requireEveryDomain") and domain_pass_line is not None:
        for domain_ratings in ratings_by_domain.values():
            value = domain_value(structure, display, domain_ratings)
            if value is None or value + _PASS_TOLERANCE < float(domain_pass_line):
                return False
    return True


# --- One result, whole ----------------------------------------------------------------


@dataclass(frozen=True)
class DomainTotal:
    """One answered domain of a result: its value under the domain aggregate and whether it passed."""

    id: str
    label: str
    value: float | None
    # How many of each scale value (best first); empty unless the rating is a scale.
    counts: Mapping[str, int]
    # None when the display sets no domain pass line.
    passed: bool | None


@dataclass(frozen=True)
class ResultTotals:
    """Everything a screen shows about one result's numbers, in the rubric's units."""

    total: float | None
    maximum: float | None
    fraction: float | None
    passed: bool | None
    critical_count: int
    domains: tuple[DomainTotal, ...]


def result_totals(
    structure: RubricStructure, display: Mapping[str, Any], result: Mapping[str, Any]
) -> ResultTotals:
    """A marked result's domains, total, pass and critical count, as the display reads them."""
    ratings_by_domain = ratings_in(structure, result)
    domain_pass_line = display["domain"].get("passAtLeast")
    domain_totals: list[DomainTotal] = []
    for domain in structure.domains:
        if domain.id not in ratings_by_domain:
            continue
        value = domain_value(structure, display, ratings_by_domain[domain.id])
        domain_totals.append(
            DomainTotal(
                id=domain.id,
                label=domain.title,
                value=value,
                counts=rating_counts(structure, ratings_by_domain[domain.id]),
                passed=None
                if domain_pass_line is None or value is None
                else value + _PASS_TOLERANCE >= float(domain_pass_line),
            )
        )
    total = total_value(structure, display, ratings_by_domain)
    return ResultTotals(
        total=total,
        maximum=display["total"].get("max"),
        fraction=total_fraction(display, total),
        passed=passed(structure, display, ratings_by_domain),
        critical_count=critical_count(structure, display, result),
        domains=tuple(domain_totals),
    )


# --- Reading a result aloud ------------------------------------------------------------


def weakest_domain_tones(
    structure: RubricStructure, display: Mapping[str, Any], result: Mapping[str, Any]
) -> dict[str, str]:
    """Each answered domain's title and the display's word for its weakest rating ("good", "poor").

    For someone who talks about a result rather than scores it (the tutor):
    words, not numbers. A domain with no tone falls back to the rating itself.
    """
    ratings_by_domain = ratings_in(structure, result)
    tones: dict[str, str] = {}
    for domain in structure.domains:
        weakest = worst_rating(structure, ratings_by_domain.get(domain.id, []))
        if weakest is not None:
            tones[domain.title] = rating_tone(structure, display, weakest) or str(weakest)
    return tones


def texts_by_role(
    structure: RubricStructure, result: Mapping[str, Any], *, roles: Collection[str]
) -> dict[str, list[str]]:
    """The written answers of every field whose role is in `roles`, grouped by role, in rubric order.

    Walks sections, domains and each competency alike. A string answer is one
    text; a list gives each non-empty string, or each entry's `text`.
    """
    collected: dict[str, list[str]] = {role: [] for role in roles}
    for section in structure.sections:
        if section.kind == "field":
            _texts_in(section.fields, result, collected)
            continue
        section_answer = result.get(section.id)
        if not isinstance(section_answer, Mapping):
            continue
        _texts_in(section.fields, section_answer, collected)
        for competency in section.competencies:
            competency_answer = section_answer.get(competency.id)
            if isinstance(competency_answer, Mapping):
                _texts_in(section.competency_fields, competency_answer, collected)
    return collected


def _texts_in(
    fields: Sequence[FieldSpec], answer: Mapping[str, Any], collected: dict[str, list[str]]
) -> None:
    """Add each wanted field's texts from `answer` to its role's list in `collected`."""
    for spec in fields:
        if spec.role not in collected:
            continue
        value = answer.get(spec.id)
        entries = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for entry in entries:
            text = entry.get("text") if isinstance(entry, Mapping) else entry
            if isinstance(text, str) and text.strip():
                collected[spec.role].append(text.strip())


# --- Critical concerns ---------------------------------------------------------------


def critical_count(structure: RubricStructure, display: Mapping[str, Any], result: Mapping[str, Any]) -> int:
    """How many critical concerns a result raises.

    Each non-empty field whose role is `flag` counts once (wherever the rubric
    puts it: on a competency, a domain, a section or at the top), and so does
    each competency rating in the `poor` tone.
    """
    poor_ratings = sum(
        1
        for domain_ratings in ratings_in(structure, result).values()
        for value in domain_ratings
        if rating_tone(structure, display, value) == "poor"
    )
    return poor_ratings + _flag_count(structure, result)


def _flag_count(structure: RubricStructure, result: Mapping[str, Any]) -> int:
    """How many `flag` fields in a result hold something."""
    flag_total = 0
    for section in structure.sections:
        section_answer = result.get(section.id)
        if section.kind == "field":
            # A lone field sits at the top of the result under its own id.
            flag_total += sum(
                1 for spec in section.fields if spec.role == "flag" and not _is_empty(result.get(spec.id))
            )
            continue
        if not isinstance(section_answer, Mapping):
            continue
        flag_total += _flags_in(section.fields, section_answer)
        for competency in section.competencies:
            competency_answer = section_answer.get(competency.id)
            if isinstance(competency_answer, Mapping):
                flag_total += _flags_in(section.competency_fields, competency_answer)
    return flag_total


def _flags_in(fields: Sequence[FieldSpec], answer: Mapping[str, Any]) -> int:
    """Non-empty `flag` fields among `fields`, looking inside groups too."""
    flag_total = 0
    for spec in fields:
        value = answer.get(spec.id)
        if spec.role == "flag" and not _is_empty(value):
            flag_total += 1
        elif spec.type == "group" and isinstance(value, Mapping):
            flag_total += _flags_in(spec.fields, value)
    return flag_total


# --- Small helpers -----------------------------------------------------------------


def _is_empty(value: Any) -> bool:
    """Whether a field holds nothing worth counting: null, blank text or an empty list or object."""
    if value is None or value is False:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def _as_number(raw: Any) -> float | None:
    """A number from a number or its text, or None (a bool is not a number here)."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw.strip())
        except ValueError:
            return None
    return None


def _describe(rating: RatingSpec) -> str:
    """The ratings a rubric allows, in words, for a refusal."""
    if rating.is_enumerated:
        return "one of " + ", ".join(rating.scale)
    if rating.kind == "boolean":
        return "true or false"
    number_kind = "a whole number" if rating.step == "integer" else "a number"
    return f"{number_kind} from {rating.minimum:g} to {rating.maximum:g}"
