"""Renders a transcript for the debrief tutor.

Lines carried short ``msg_N`` ids and a mapping back to their transcript
message ids, so the tutor could name a line and the client highlight it. The
live insights panel that consumed those ids is gone, and an id the tutor is
told never to read out and nothing else reads is only a thing to leak into
speech, so the transcript is now rendered plainly. The tutor still quotes the
moment it means; it quotes the words rather than an id.
"""
from typing import List, Dict, Optional

class TranscriptFormatter:
    DEFAULT_TRANSCRIPT = """
    ## Consultation Transcript
    No transcript available. This might be because:
    - The consultation was very brief
    - There were technical issues
    - The recording is still processing

    Let's focus on general consultation skills and strategies."""

    @staticmethod
    def format(transcript: Optional[Dict]) -> str:
        """Formats a transcript object into a markdown string."""
        try:
            if not TranscriptFormatter._is_valid_transcript(transcript):
                return TranscriptFormatter.DEFAULT_TRANSCRIPT

            messages = transcript.get("transcript_message", [])
            formatted_messages = TranscriptFormatter._format_messages(messages)

            if formatted_messages:
                messages_text = "\n\n".join(formatted_messages)
                return "## Consultation Transcript\n\n" + messages_text
            return TranscriptFormatter.DEFAULT_TRANSCRIPT

        except Exception:
            return TranscriptFormatter.DEFAULT_TRANSCRIPT

    @staticmethod
    def _is_valid_transcript(transcript: Optional[Dict]) -> bool:
        """
        Validates the transcript object structure.

        Args:
            transcript: Dictionary containing transcript data

        Returns:
            Boolean indicating if transcript is valid
        """
        return bool(
            transcript
            and "transcript_message" in transcript
            and isinstance(transcript["transcript_message"], list)
            and len(transcript["transcript_message"]) > 0
        )

    @staticmethod
    def _format_messages(messages: List[Dict[str, str]]) -> List[str]:
        """
        Formats individual transcript messages.

        Args:
            messages: List of TranscriptMessageModel dictionaries containing:
                - role: str (user/assistant)
                - message: str
                - timestamp: str

        Returns:
            List of formatted message strings
        """
        formatted_messages = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            message = msg.get("message", "").strip()
            if not message:
                continue

            role = "Patient" if msg.get("role") == "assistant" else "Doctor"
            formatted_messages.append(f"## {role}\n{message}")

        return formatted_messages
