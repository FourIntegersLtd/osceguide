"""Job metadata: what a dispatching backend must send."""

from __future__ import annotations

import json

import pytest

from livekit_assessment_worker.metadata import DispatchMetadata, MetadataError, parse_dispatch_metadata


def test_snake_case_and_camel_case_parse_identically() -> None:
    snake = parse_dispatch_metadata(json.dumps({"attempt_id": "a-1", "backend": "practice", "candidate_ref": "user-9"}))
    camel = parse_dispatch_metadata(json.dumps({"attemptId": " a-1 ", "backend": "practice", "candidateRef": "user-9"}))
    assert snake == camel == DispatchMetadata(attempt_id="a-1", backend="practice", candidate_ref="user-9")


def test_candidate_ref_is_required() -> None:
    """A room may hold other humans; without a reference nobody can be chosen safely."""
    with pytest.raises(MetadataError, match="missing \\['candidate_ref'\\]"):
        parse_dispatch_metadata('{"attempt_id": "a", "backend": "b"}')


@pytest.mark.parametrize(
    "raw",
    [None, "", "{}", '{"backend": "b"}', '{"attempt_id": "a"}', '{"attempt_id": "  ", "backend": "b", "candidate_ref": "c"}'],
)
def test_missing_required_fields_are_rejected(raw) -> None:
    with pytest.raises(MetadataError, match="missing"):
        parse_dispatch_metadata(raw)


@pytest.mark.parametrize("raw", ["not json", "[1, 2]"])
def test_malformed_metadata_is_rejected(raw) -> None:
    with pytest.raises(MetadataError):
        parse_dispatch_metadata(raw)


def test_metadata_carries_no_route_product_or_scenario_knowledge() -> None:
    """Extra keys are ignored: the worker never reads app types, org slugs or station fields.

    Routes are not on the metadata either; the backend's endpoints own them.
    """
    md = parse_dispatch_metadata(json.dumps({"attempt_id": "a", "backend": "b", "candidate_ref": "c", "station_id": "s", "org_slug": "x"}))
    assert set(md.__dataclass_fields__) == {"attempt_id", "backend", "candidate_ref"}
