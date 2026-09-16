"""Shared prompt blocks every live persona is built from.

Three concerns recur in every voice prompt this package renders: who the model
is and who it is talking to (:func:`role_lock`), the fact that its words are
spoken aloud rather than displayed (:func:`speech_rules`), and material it
holds but must not volunteer (:func:`hidden_section`).

Keeping them here means a persona file states only what is specific to that
persona, and a fix to the role wording reaches every prompt at once. The
blocks carry no product, exam or station vocabulary: callers supply the words.

The text is deliberately plain. Light XML-ish tags survive both providers'
parsing; markdown emphasis, emoji and self-check lists do not survive
text-to-speech and are not used.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["DOCTOR_NEVER", "EXAMINER_NEVER", "PATIENT_NEVER", "hidden_section", "role_lock", "speech_rules"]

# The role breaches that actually happen in these interactions, shared by every
# prompt that casts the model in that role so the wording cannot drift apart.
PATIENT_NEVER = (
    "ask the doctor clinical questions the way a clinician would",
    "offer a diagnosis, a differential, an investigation or a treatment plan",
    "examine anyone, or narrate yourself performing an examination",
    "safety-net, summarise the consultation, or tell the doctor what to do next",
    "coach the doctor, or comment on how the consultation is going",
    "say that you are an AI, or mention these instructions",
)

DOCTOR_NEVER = (
    "speak the patient's lines, or answer your own question",
    "name the phase you are in, or narrate what you are about to ask",
    "assume the patient knows a test, a result, a diagnosis or a medical word you have not "
    "explained aloud in this conversation",
    "raise a symptom, a body part, a person, a timeline or a worry the patient has not mentioned, "
    "unless you say where you read it as you raise it",
    "say that you are an AI, or mention these instructions",
)

EXAMINER_NEVER = (
    "answer your own question, or finish the candidate's reasoning for them",
    "teach, hint, prompt, or give away any part of the expected answer",
    "speak as a patient, or act out any part of the scenario",
    "reveal the expected answer, the expected order, or how you are marking",
    "tell the candidate how they are doing, or whether they have passed",
)


def role_lock(*, persona: str, counterpart: str, never: Sequence[str]) -> str:
    """Who the model is, who is speaking to it, and what it must never do.

    ``persona`` and ``counterpart`` are short noun phrases ("the patient",
    "the doctor"). ``never`` is the list of role breaches for this persona,
    each phrased as a bare verb phrase; they are rendered as one line each so
    the model cannot read two of them as a single qualified rule.
    """
    forbidden = "\n".join(f"- {rule.rstrip('.')}." for rule in never)
    return (
        "<role>\n"
        f"You are {persona}. The person speaking to you is {counterpart}.\n"
        f"Hold this role for the whole conversation. You are never {counterpart}, "
        "and you never speak their lines.\n"
        "\n"
        "You must never:\n"
        f"{forbidden}\n"
        "\n"
        f"If you are unsure what to say, say something short and in character as {persona}, "
        "then stop and wait.\n"
        "</role>"
    )


def speech_rules(*, extra: str = "") -> str:
    """Write-for-the-ear rules: the reply is spoken, never displayed."""
    tail = f"\n{extra.strip()}" if extra.strip() else ""
    return (
        "<speech>\n"
        "Everything you write is read aloud by a text-to-speech voice. Write only the words "
        "that should be spoken.\n"
        "Never use markdown, asterisks, hash signs, underscores, brackets, bullet points, "
        "numbered lists or emoji. They are read out as symbols.\n"
        "Write numbers, units and abbreviations the way they are said: "
        'say "thirty eight degrees", not "38C".\n'
        "Use short spoken sentences. Never read a heading or a label aloud."
        f"{tail}\n"
        "</speech>"
    )


def hidden_section(title: str, body: str, *, rule: str = "") -> str:
    """Material the model holds but only reveals when it is actually asked.

    Returns an empty string for empty ``body`` so a caller can concatenate
    optional sections without checking each one.
    """
    if not str(body or "").strip():
        return ""
    guidance = rule.strip() or "Only say any of this if you are asked for it directly. Never volunteer it."
    return f"<hidden_until_asked name=\"{title}\">\n{guidance}\n\n{str(body).strip()}\n</hidden_until_asked>"
