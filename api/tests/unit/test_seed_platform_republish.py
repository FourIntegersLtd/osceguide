"""`seed_platform.py --republish`: when an exam's bound rubric is republished, and which gaps it names.

Republishing adds a new version rather than editing the bound one, so a
version a candidate was marked against never changes. It must fire when the
seed moved on (a version 1 rubric, or a new prompt) and stay quiet when the
bound rubric already is the seed, so a second run writes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from seed_platform import needs_republish, undescribed  # noqa: E402

V2_STRUCTURE = {
    "schemaVersion": 2,
    "rating": {"kind": "rag", "field": "score", "scale": ["G", "A", "R"]},
    "sections": [
        {
            "kind": "domain",
            "id": "tasks",
            "title": "Tasks",
            "competencies": [
                {"id": "discovers_ice", "label": "Discovers ICE", "descriptors": {"G": "All three."}},
                {"id": "opens", "label": "Opens", "descriptors": {}},
            ],
            "competencyFields": [{"id": "score", "type": "rating", "role": "rating"}],
        },
        {
            "kind": "section",
            "id": "feedback",
            "title": "Feedback",
            "fields": [{"id": "notes", "type": "list"}],
        },
    ],
}
SPEC = {"structure": V2_STRUCTURE, "system_prompt": "Mark it."}


def test_a_rubric_that_already_is_the_seed_is_left_alone() -> None:
    assert needs_republish(V2_STRUCTURE, "Mark it.", SPEC) is False


def test_a_version_1_rubric_is_republished() -> None:
    version_1 = {"scale": ["R", "A", "G"], "domains": [{"id": "tasks", "label": "Tasks", "competencies": []}]}
    assert needs_republish(version_1, "Mark it.", SPEC) is True


def test_a_changed_prompt_alone_is_republished() -> None:
    assert needs_republish(V2_STRUCTURE, "Mark it differently.", SPEC) is True


def test_competencies_with_no_anchors_are_named_by_domain() -> None:
    assert undescribed(V2_STRUCTURE) == ["tasks.opens"]


def test_a_range_rating_has_no_anchors_to_miss() -> None:
    ranged = {**V2_STRUCTURE, "rating": {"kind": "range", "field": "score", "minimum": 0, "maximum": 10}}
    assert undescribed(ranged) == []
