"""Render a transcript the way the marker expects to read it.

Both backends render the same shape today: each turn as a tagged block, the
candidate as DOCTOR and the simulated patient as PATIENT, blocks separated by
a blank line. One renderer keeps that identical for every consumer.
"""

from __future__ import annotations

from ..contracts import MessageRole, Transcript

_LABELS = {MessageRole.USER: "DOCTOR", MessageRole.ASSISTANT: "PATIENT"}


def render_transcript_for_marking(transcript: Transcript) -> str:
    blocks = []
    for message in transcript.messages:
        text = message.message.strip()
        if not text:
            continue
        label = _LABELS[message.role]
        blocks.append(f"<{label}>\n{text}\n</{label}>")
    return "\n\n".join(blocks)
