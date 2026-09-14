"""Renders a transcript for the debrief tutor, with an id mapping for highlights."""
from typing import List, Dict, Optional, Union

class TranscriptFormatter:
    DEFAULT_TRANSCRIPT = """
    ## Consultation Transcript
    No transcript available. This might be because:
    - The consultation was very brief
    - There were technical issues
    - The recording is still processing

    Let's focus on general consultation skills and strategies."""

    @staticmethod
    def format(transcript: Optional[Dict]) -> tuple[str, dict]:
        """
        Formats a transcript object into a markdown string and creates an ID mapping.

        Args:
            transcript: Dictionary containing transcript data with transcript_message list

        Returns:
            A tuple containing the formatted markdown string and a dictionary mapping simple IDs to UUIDs.
        """
        id_mapping = {}
        try:
            if not TranscriptFormatter._is_valid_transcript(transcript):
                return TranscriptFormatter.DEFAULT_TRANSCRIPT, id_mapping

            messages = transcript.get("transcript_message", [])
            id_mapping = TranscriptFormatter._get_id_mapping(messages)

            formatted_messages = TranscriptFormatter._format_messages(messages)

            if formatted_messages:
                messages_text = "\n\n".join(formatted_messages)
                return "## Consultation Transcript\n\n" + messages_text, id_mapping
            return TranscriptFormatter.DEFAULT_TRANSCRIPT, id_mapping

        except Exception as e:
            return TranscriptFormatter.DEFAULT_TRANSCRIPT, id_mapping

    @staticmethod
    def _get_id_mapping(messages: List[Dict[str, str]]) -> Dict[str, str]:
        """Creates a mapping from simple IDs to UUIDs."""
        return {
            f"msg_{idx}": msg.get("transcript_message_id")
            for idx, msg in enumerate(messages)
            if isinstance(msg, dict) and msg.get("transcript_message_id")
        }

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
                - transcript_message_id: str
            
        Returns:
            List of formatted message strings with transcript message IDs
        """
        formatted_messages = []
        
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
                
            message = msg.get("message", "").strip()
            if not message:
                continue

            # Use simple msg_id for the prompt, but the real ID is in the mapping
            simple_id = f"msg_{idx}"
            role = "Patient" if msg.get("role") == "assistant" else "Doctor"
            formatted_messages.append(f"## {role} [ID:{simple_id}]\n{message}")

        return formatted_messages