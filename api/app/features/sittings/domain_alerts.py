"""What a watching human should be told, as stable codes.

Distinct from `domain_run`, which decides what a circuit does next: this
decides what somebody supervising an exam needs to notice, and the two change
for different reasons — a new step changes how the exam runs, a new alert
changes how it is supervised.

Codes rather than sentences, so a client never has to match on English to
decide whether a consultation has ended.
"""

from __future__ import annotations

from datetime import datetime

from app.features.sittings.domain_run import RunPhase

# Alerts the exam-day board raises so nobody has to notice them by watching.
NO_RUNNING_ATTEMPT = "no_running_attempt"
ATTEMPT_FAILED = "attempt_failed"
CLOCK_OVERDUE = "clock_overdue"
VOICE_FAULT = "voice_fault"

# A dispatched agent takes a moment to join and fetch its bootstrap. Below this
# the silence is normal, above it somebody should look.
ALERT_GRACE_SECONDS = 20

# Statuses that mean the patient arrived and the recording is under way.
_ATTEMPT_UNDER_WAY = frozenset({"running", "interaction_complete", "evaluated"})


def alerts_for(
    *,
    phase: str | None,
    phase_started_at: datetime | None,
    phase_ends_at: datetime | None,
    paused_at: datetime | None,
    attempt_status: str | None,
    auto_advance: bool,
    now: datetime,
    grace_seconds: int = ALERT_GRACE_SECONDS,
    voice_fault: bool = False,
) -> list[str]:
    """What is wrong with this circuit right now, as stable codes."""
    if paused_at is not None:
        # Nothing is overdue and no patient is expected while the clock is
        # deliberately stopped.
        return []

    alerts: list[str] = []
    # Compared by value, not identity: callers hold the stored string, and
    # `RunPhase` is a `StrEnum` precisely so this reads the same either way.
    if phase == RunPhase.SIMULATION:
        if attempt_status == "failed":
            alerts.append(ATTEMPT_FAILED)
        elif attempt_status not in _ATTEMPT_UNDER_WAY:
            started = phase_started_at
            if started is not None and (now - started).total_seconds() > grace_seconds:
                alerts.append(NO_RUNNING_ATTEMPT)

    # Only a circuit meant to move on by itself is overdue: with auto-advance
    # off, the clock running out is a human's cue to advance, not a fault (R-14).
    overdue = phase_ends_at is not None and (now - phase_ends_at).total_seconds() > grace_seconds
    if phase is not None and auto_advance and overdue:
        # A late clock the voice service caused says so, rather than blaming the worker (R-16).
        alerts.append(VOICE_FAULT if voice_fault else CLOCK_OVERDUE)

    return alerts
