"""The opening line each live persona speaks before its prompt takes over.

A session says one of these aloud and only then does the model start
generating, so these words are the first thing a candidate hears and the first
thing the model reads back as its own. That makes them persona content in
exactly the way the role reminders are, and it is why they live here: both
backends kept private copies, and both drifted out of character. One list
asked the candidate to confirm they were ready for "the next case"; the other
had the patient inviting the doctor into the room.

A greeting has three jobs and no others: signal that the session is live, sound
like the person speaking it, and hand the turn straight back. It never opens the
clinical content. The patient's opening sentence is held until the doctor asks
what brought them in, and the prompt says so.
"""

from __future__ import annotations

__all__ = ["DEBRIEF_GREETING", "EXAMINER_GREETINGS", "PATIENT_GREETINGS"]

PATIENT_GREETINGS = (
    "Hello, doctor.",
    "Hi, doctor.",
    "Hello, doctor. Thanks for seeing me.",
    "Hello. Thank you for seeing me today.",
    "Hi. Thanks for fitting me in.",
)
"""What a patient says as they sit down. Nothing here directs the consultation:
a patient does not tell a doctor to begin, and does not know they are a case."""

EXAMINER_GREETINGS = (
    "Good morning. I'm Athena, your examiner for this station. Are you ready to begin?",
    "Good morning, I'm Athena and I'll be examining you today. Ready when you are?",
    "Good morning. I'm Athena, today's examiner. Shall we begin?",
)
"""An examination does open with the examiner directing it, so these legitimately
do what the patient greetings must not. The examiner prompt assumes this
introduction has been made and starts from the first question."""

DEBRIEF_GREETING = (
    "Hello doctor, I'm Athena... well done on getting through that case. "
    "We'll hear how it felt, then walk through your management plan together, "
    "and we can practise any moment you found tricky. How do you think it went?"
)
"""The tutor opens the debrief with a one-line map of it, then asks before it tells, as the prompt does."""
