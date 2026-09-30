"""The evaluator hands the engine a transcript it can read, whoever spoke it.

A peer session's transcript names its speakers `doctor` and `patient`; the
engine knows only `user` and `assistant`. On staging every peer session was
transcribed and then refused marking with "'doctor' is not a valid MessageRole".
"""

from types import SimpleNamespace
from typing import Any

from osce_assessment.contracts.models import MessageRole

from app.features.attempts.evaluator import EngineEvaluator


class RecordingEngine:
    """Keeps the transcript it was asked to mark and returns fixed marks."""

    def __init__(self) -> None:
        self.roles: list[MessageRole] = []

    def evaluate(self, attempt: Any, transcript: Any, policy: Any, scenario: Any) -> SimpleNamespace:
        self.roles = [message.role for message in transcript.messages]
        return SimpleNamespace(result={"overall": "pass"}, model="test-model")


async def test_a_peer_sessions_doctor_and_patient_are_marked() -> None:
    engine = RecordingEngine()
    evaluator = EngineEvaluator(lambda framework: engine)

    marked = await evaluator.evaluate(
        rubric={"framework": {"id": "sca"}, "system_prompt": "Mark it."},
        policy_version="platform-default@1",
        transcript=[
            {"role": "doctor", "message": "What brings you in today?"},
            {"role": "patient", "message": "My blood pressure readings have been high."},
        ],
    )

    assert engine.roles == [MessageRole.USER, MessageRole.ASSISTANT]
    assert marked == {"overall": "pass", "model_used": "test-model"}
