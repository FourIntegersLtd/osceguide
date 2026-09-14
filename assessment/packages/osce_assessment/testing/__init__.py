"""Test doubles for every port, so consumers can test against the engine offline."""

from .examples import example_payload_for
from .doubles import (
    FakeEvaluator,
    InMemoryResultSink,
    InMemoryTranscriptSink,
    SimpleProfileBuilder,
    StaticFrameworkProvider,
    StaticScenarioProvider,
)

__all__ = [
    "FakeEvaluator",
    "InMemoryResultSink",
    "InMemoryTranscriptSink",
    "SimpleProfileBuilder",
    "StaticFrameworkProvider",
    "StaticScenarioProvider",
    "example_payload_for",
]
