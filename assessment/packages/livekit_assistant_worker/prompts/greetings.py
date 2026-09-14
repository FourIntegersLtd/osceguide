"""Opening lines by session type (onboarding opens with a generated reply instead)."""

from __future__ import annotations

GREETINGS: dict[str, str] = {
    "dashboard": (
        "Hello doctor. Based on your recent consultations, we've analyzed specific areas "
        "where we think we can focus on enhancing your clinical performance. Would you "
        "like to explore these opportunities for improvement together?"
    ),
    "athena-doctor": (
        "Hello, I'm Doctor Athena... It's nice to meet you. Can you confirm your "
        "name and date of birth for me ?"
    ),
    "help": (
        "Hi, I'm Athena, your personal assistant. I'm here to help you navigate "
        "the application. Feel free to ask me anything."
    ),
}
DEFAULT_GREETING = "Hello doctor, I'm ready when you are."


def greeting_for(worker_type: str) -> str:
    return GREETINGS.get(worker_type, DEFAULT_GREETING)
